"""Testes do Aplicativo Coraci (Flask chat app).

Importa o app a partir de Aplicativo_Coraci/app.py e usa DB em memória.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "Aplicativo_Coraci"


@pytest.fixture(scope="module")
def coraci():
    """Carrega o módulo app.py do diretório Aplicativo_Coraci."""
    spec = importlib.util.spec_from_file_location("coraci_app", APP_DIR / "app.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["coraci_app"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def client(coraci):
    coraci.app.config["TESTING"] = True
    with coraci.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Página inicial
# ---------------------------------------------------------------------------


def test_index_retorna_200(client):
    resp = client.get("/")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /api/chat
# ---------------------------------------------------------------------------


def _fake_stream(events):
    def _stream(messages, model=None, temperature=None, max_tokens=None):
        for ev in events:
            yield f"data: {json.dumps(ev)}\n\n"

    return _stream


def test_chat_cria_conversa_e_transmite_resposta(client, coraci):
    with patch.object(
        coraci, "stream_chat", _fake_stream([{"type": "content", "text": "Olá"}, {"type": "done"}])
    ):
        resp = client.post("/api/chat", json={"message": "Oi"})
        assert resp.status_code == 200
        assert resp.mimetype == "text/event-stream"
        # O gerador SSE roda de forma lazy: consumir DENTRO do patch
        body = resp.get_data(as_text=True)
    assert '"type": "conv_id"' in body
    assert '"type": "content"' in body
    assert '"type": "done"' in body


def test_chat_mensagem_vazia_retorna_400(client):
    resp = client.post("/api/chat", json={"message": "   "})
    assert resp.status_code == 400


def test_chat_corpo_nao_objeto_retorna_400(client):
    resp = client.post("/api/chat", data="[1,2]", content_type="application/json")
    assert resp.status_code == 400


def test_chat_json_invalido_retorna_400(client):
    resp = client.post("/api/chat", data="não-json", content_type="application/json")
    assert resp.status_code == 400


def test_chat_persiste_resposta_do_assistente(client, coraci):
    with patch.object(
        coraci,
        "stream_chat",
        _fake_stream([{"type": "content", "text": "resposta"}, {"type": "done"}]),
    ):
        resp = client.post("/api/chat", json={"message": "pergunta"})
        resp.get_data()  # consome o SSE dentro do patch (lazy)
    assert resp.status_code == 200
    with coraci.conv_lock:
        convs = list(coraci.conversations.values())
        assert convs, "deve existir uma conversa"
        roles = [m["role"] for m in convs[0]["messages"]]
        assert roles == ["user", "assistant"]


# ---------------------------------------------------------------------------
# /api/conversations
# ---------------------------------------------------------------------------


def test_list_get_delete_conversa(client, coraci):
    with patch.object(coraci, "stream_chat", _fake_stream([{"type": "done"}])):
        client.post("/api/chat", json={"message": "Oi"}).get_data()
    conv_id = next(iter(coraci.conversations))

    resp = client.get("/api/conversations")
    assert resp.status_code == 200
    assert any(c["id"] == conv_id for c in resp.get_json())

    resp = client.get(f"/api/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == conv_id

    resp = client.get("/api/conversations/conversa-inexistente")
    assert resp.status_code == 404

    resp = client.delete(f"/api/conversations/{conv_id}")
    assert resp.status_code == 200
    assert conv_id not in coraci.conversations


def test_clear_conversations(client, coraci):
    with patch.object(coraci, "stream_chat", _fake_stream([{"type": "done"}])):
        client.post("/api/chat", json={"message": "Oi"}).get_data()
    resp = client.delete("/api/conversations")
    assert resp.status_code == 200
    assert coraci.conversations == {}


# ---------------------------------------------------------------------------
# /api/config
# ---------------------------------------------------------------------------


def test_get_config_mascara_api_key(client, coraci):
    with coraci.config_lock:
        coraci.current_config["api_key"] = "sk-super-secreta-123"
    resp = client.get("/api/config")
    assert resp.status_code == 200
    key = resp.get_json()["api_key"]
    assert "super-secreta" not in key
    assert key.startswith("sk-s")


def test_save_config_nao_persiste_api_key(tmp_path, coraci):
    config_file = tmp_path / "config.json"
    with patch.object(coraci, "CONFIG_FILE", config_file):
        coraci.save_config(
            {
                "api_base_url": "http://localhost:11434/v1",
                "api_key": "sk-test-secret",
                "model": "glm4:latest",
                "temperature": 0.7,
                "max_tokens": 4096,
                "theme": "dark",
            }
        )
    saved = json.loads(config_file.read_text())
    assert saved["api_key"] == ""


def test_load_config_env_sobrescreve_config(tmp_path, coraci, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "api_base_url": "http://file:8000/v1",
                "model": "arquivo-modelo",
                "api_key": "",
            }
        )
    )
    monkeypatch.setenv("CORACI_API_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("CORACI_MODEL", "glm4:latest")
    monkeypatch.setenv("CORACI_API_KEY", "sk-env")
    with patch.object(coraci, "CONFIG_FILE", config_file):
        cfg = coraci.load_config()
    assert cfg["api_base_url"] == "http://localhost:11434/v1"
    assert cfg["model"] == "glm4:latest"
    assert cfg["api_key"] == "sk-env"


def test_post_config_valida_atualiza(client, coraci):
    resp = client.post(
        "/api/config",
        json={"temperature": 0.2, "model": "novo-modelo", "theme": "light"},
    )
    assert resp.status_code == 200
    with coraci.config_lock:
        assert coraci.current_config["temperature"] == 0.2
        assert coraci.current_config["model"] == "novo-modelo"


def test_post_config_rejeita_temperatura_invalida(client):
    resp = client.post("/api/config", json={"temperature": "abc"})
    assert resp.status_code == 400


def test_post_config_rejeita_temperatura_fora_da_faixa(client):
    resp = client.post("/api/config", json={"temperature": 5.0})
    assert resp.status_code == 400


def test_post_config_rejeita_max_tokens_invalido(client):
    resp = client.post("/api/config", json={"max_tokens": -1})
    assert resp.status_code == 400


def test_post_config_ignora_chave_desconhecida(client, coraci):
    resp = client.post("/api/config", json={"hack": True})
    assert resp.status_code == 200
    assert "hack" not in coraci.current_config


# ---------------------------------------------------------------------------
# stream_chat — bug do temperature=0
# ---------------------------------------------------------------------------


class _FakeCompletions:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs

        class _Delta:
            def __init__(self):
                self.content = "ok"
                self.reasoning_content = None

        class _Choice:
            delta = _Delta()

        class _Chunk:
            choices = [_Choice()]

        return iter([_Chunk()])


class _FakeClient:
    def __init__(self):
        self.chat = type("C", (), {"completions": _FakeCompletions()})()


def test_stream_chat_temperature_zero_e_respeitada(coraci):
    fake = _FakeClient()
    with patch.object(coraci, "load_openai_client", return_value=fake):
        events = list(coraci.stream_chat([{"role": "user", "content": "oi"}], temperature=0))
    assert any('"type": "content"' in e for e in events)
    assert fake.chat.completions.last_kwargs["temperature"] == 0


def test_stream_chat_temperature_none_usa_config(coraci):
    fake = _FakeClient()
    with coraci.config_lock:
        coraci.current_config["temperature"] = 0.7
    with patch.object(coraci, "load_openai_client", return_value=fake):
        list(coraci.stream_chat([{"role": "user", "content": "oi"}], temperature=None))
    assert fake.chat.completions.last_kwargs["temperature"] == 0.7


def test_stream_chat_erro_gera_evento_error(coraci):
    import openai

    class _Boom:
        def create(self, **kw):
            raise openai.APIConnectionError(request=None)

    class _BoomClient:
        chat = type("C", (), {"completions": _Boom()})()

    with patch.object(coraci, "load_openai_client", return_value=_BoomClient()):
        events = list(coraci.stream_chat([{"role": "user", "content": "oi"}]))
    assert any('"type": "error"' in e for e in events)


# ---------------------------------------------------------------------------
# Persistência (usando DB temporário real)
# ---------------------------------------------------------------------------


def test_db_roundtrip(tmp_path, coraci):
    db = str(tmp_path / "test.db")
    coraci.init_db(db)
    with patch.object(coraci, "get_db_path", return_value=db):
        conv = {
            "id": "c1",
            "title": "Título",
            "created_at": "2026-01-01T00:00:00",
            "messages": [{"role": "user", "content": "oi", "timestamp": "2026-01-01T00:00:00"}],
        }
        coraci.db_save_conversation(conv)
        loaded = coraci.db_load_all()
        assert "c1" in loaded
        assert loaded["c1"]["title"] == "Título"
        assert loaded["c1"]["messages"][0]["content"] == "oi"
        coraci.db_delete_conversation("c1")
        assert "c1" not in coraci.db_load_all()
