"""Testes do módulo de Chat SSE (migrado do Coraci).

Cobre:
- Import e criação do router
- Listagem de conversas
- Chat SSE: formato dos eventos, conv_id, content, done, error
- CRUD de conversas (get, delete, clear)
- Config management (get, update)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.v2.chat_coraci import router


def _async_stream(events: list[str]):
    """Cria um async generator que produz os eventos fornecidos."""

    async def gen():
        for event in events:
            yield event

    return gen()


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def app():
    """Cria uma FastAPI app apenas com o router v2 para testes."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """TestClient para o router v2."""
    return TestClient(app)


# ═════════════════════════════════════════════════════════════════════════════
# Import e Estrutura
# ═════════════════════════════════════════════════════════════════════════════


class TestModuleStructure:
    """Verifica a estrutura básica do módulo."""

    def test_router_criado(self):
        """O módulo deve exportar um APIRouter."""
        from src.api.v2.chat_coraci import router as r

        assert r is not None
        assert r.prefix == "/api/v2"

    def test_router_tem_rotas(self):
        """O router deve ter as 8 rotas esperadas."""
        paths = sorted([route.path for route in router.routes])
        expected = sorted(
            [
                "/api/v2/chat",
                "/api/v2/config",
                "/api/v2/config/test",
                "/api/v2/conversations",
                "/api/v2/conversations/{conv_id}",
            ]
        )
        for exp in expected:
            assert exp in paths, f"Rota {exp} não encontrada no router"


# ═════════════════════════════════════════════════════════════════════════════
# Conversações (sem dados)
# ═════════════════════════════════════════════════════════════════════════════


class TestConversations:
    """Testes para o CRUD de conversas."""

    def test_listar_conversacoes_vazia(self, client):
        """Deve retornar lista vazia quando não há conversas."""
        response = client.get("/api/v2/conversations")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_conversacao_inexistente(self, client):
        """Deve retornar 404 para conversa que não existe."""
        response = client.get("/api/v2/conversations/nao-existe")
        assert response.status_code == 404
        assert "não encontrada" in response.json()["detail"]

    def test_delete_conversacao_inexistente(self, client):
        """Deve retornar ok mesmo apagando conversa que não existe."""
        response = client.delete("/api/v2/conversations/nao-existe")
        assert response.status_code == 200

    def test_limpar_conversacoes_vazia(self, client):
        """Limpar conversas vazias deve funcionar."""
        response = client.delete("/api/v2/conversations")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ═════════════════════════════════════════════════════════════════════════════
# Chat SSE - Eventos
# ═════════════════════════════════════════════════════════════════════════════


class TestChatSSE:
    """Testes para o formato dos eventos SSE do chat.

    Nota: Como o chat SSE depende de uma API OpenAI externa,
    os testes mockam o client OpenAI para verificar o formato
    dos eventos SSE.
    """

    @pytest.fixture(autouse=True)
    def setup_clean_conversations(self):
        """Limpa o cache de conversas antes de cada teste."""
        import src.api.v2.chat_coraci as chat_mod

        chat_mod._conversations.clear()
        yield

    def test_chat_requer_mensagem(self, client):
        """Mensagem vazia deve retornar 400."""
        response = client.post("/api/v2/chat", json={"message": ""})
        assert response.status_code == 400

    def test_chat_retorna_event_stream(self, client):
        """Chat deve retornar media type text/event-stream."""
        with patch(
            "src.api.v2.chat_coraci._stream_chat_openai",
            side_effect=lambda *a, **kw: _async_stream(['data: {"type": "done"}\n\n']),
        ):
            response = client.post("/api/v2/chat", json={"message": "teste"})
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    def test_chat_eventos_incluem_conv_id(self, client):
        """O primeiro evento deve ser o conv_id."""
        with patch(
            "src.api.v2.chat_coraci._stream_chat_openai",
            side_effect=lambda *a, **kw: _async_stream(['data: {"type": "done"}\n\n']),
        ):
            response = client.post("/api/v2/chat", json={"message": "ola"})
            lines = response.text.strip().split("\n")
            first_event = lines[0].removeprefix("data: ")
            import json

            parsed = json.loads(first_event)
            assert parsed["type"] == "conv_id"
            assert len(parsed["id"]) > 0  # UUID não vazio

    def test_chat_acumula_resposta_no_historico(self, client):
        """Após o chat, a resposta deve estar no histórico da conversa."""
        with patch(
            "src.api.v2.chat_coraci._stream_chat_openai",
            side_effect=lambda *a, **kw: _async_stream(
                [
                    'data: {"type": "content", "text": "Resposta do "}\n\n',
                    'data: {"type": "content", "text": "assistente"}\n\n',
                    'data: {"type": "done"}\n\n',
                ]
            ),
        ):
            response = client.post("/api/v2/chat", json={"message": "oi"})
            assert response.status_code == 200

            # Extrai o conv_id da resposta
            import json

            lines = response.text.strip().split("\n")
            conv_id_line = lines[0].removeprefix("data: ")
            conv_id = json.loads(conv_id_line)["id"]

            # Verifica que a conversa foi criada com a resposta
            conv_resp = client.get(f"/api/v2/conversations/{conv_id}")
            assert conv_resp.status_code == 200
            conv = conv_resp.json()
            assert len(conv["messages"]) == 2  # user + assistant
            assert conv["messages"][0]["role"] == "user"
            assert conv["messages"][0]["content"] == "oi"
            assert conv["messages"][1]["role"] == "assistant"
            assert conv["messages"][1]["content"] == "Resposta do assistente"

    def test_chat_com_erro_retorna_evento_error(self, client):
        """Quando o stream lança exceção, deve retornar evento error."""
        with patch(
            "src.api.v2.chat_coraci._stream_chat_openai",
            side_effect=lambda *a, **kw: _async_stream(
                ['data: {"type": "error", "text": "Falha na conexão"}\n\n']
            ),
        ):
            response = client.post("/api/v2/chat", json={"message": "teste erro"})
            assert response.status_code == 200
            assert "error" in response.text
            assert "Falha na conexão" in response.text

    def test_chat_conversa_existente_reutiliza_id(self, client):
        """Se um conversation_id for passado, deve reutilizar a conversa."""
        import src.api.v2.chat_coraci as chat_mod

        conv_id = "conv-test-123"
        chat_mod._conversations[conv_id] = {
            "id": conv_id,
            "title": "Conversa existente",
            "messages": [
                {"role": "user", "content": "msg1", "timestamp": "2024-01-01T00:00:00"},
                {"role": "assistant", "content": "resp1", "timestamp": "2024-01-01T00:00:01"},
            ],
            "created_at": "2024-01-01T00:00:00",
        }

        with patch(
            "src.api.v2.chat_coraci._stream_chat_openai",
            side_effect=lambda *a, **kw: _async_stream(
                [
                    'data: {"type": "content", "text": "nova resposta"}\n\n',
                    'data: {"type": "done"}\n\n',
                ]
            ),
        ):
            response = client.post(
                "/api/v2/chat", json={"message": "nova msg", "conversation_id": conv_id}
            )
            assert response.status_code == 200

            # Verifica que a conversa tem agora 4 mensagens
            conv_resp = client.get(f"/api/v2/conversations/{conv_id}")
            assert conv_resp.status_code == 200
            assert len(conv_resp.json()["messages"]) == 4  # 2 originais + user + assistant


# ═════════════════════════════════════════════════════════════════════════════
# Config
# ═════════════════════════════════════════════════════════════════════════════


class TestConfig:
    """Testes para o gerenciamento de configuração."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        """Reseta a config para o padrão antes de cada teste."""
        import src.api.v2.chat_coraci as chat_mod

        chat_mod._config = dict(chat_mod.DEFAULT_CONFIG)
        yield

    def test_get_config_retorna_defaults(self, client):
        """Config padrão deve ter os campos esperados."""
        response = client.get("/api/v2/config")
        assert response.status_code == 200
        data = response.json()
        assert "api_base_url" in data
        assert "model" in data
        assert "temperature" in data
        assert "max_tokens" in data
        assert "theme" in data
        assert data["model"] == "glm-5.2-colibri"

    def test_get_config_esconde_api_key(self, client):
        """A API key não deve ser exposta completamente."""
        import src.api.v2.chat_coraci as chat_mod

        chat_mod._config["api_key"] = "sk-1234567890"
        response = client.get("/api/v2/config")
        assert response.status_code == 200
        assert "sk-1234567890" not in response.json()["api_key"]
        assert "sk-" in response.json()["api_key"]  # apenas prefixo visível

    def test_update_config_altera_valores(self, client):
        """Atualizar config deve persistir os valores."""
        response = client.post("/api/v2/config", json={"model": "gpt-4", "temperature": 0.5})
        assert response.status_code == 200

        # Verifica que foi atualizado
        response = client.get("/api/v2/config")
        data = response.json()
        assert data["model"] == "gpt-4"
        assert data["temperature"] == 0.5
