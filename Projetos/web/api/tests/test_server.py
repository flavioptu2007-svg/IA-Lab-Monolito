"""Tests for web/api/server.py endpoints (monolith imports stubbed)."""

import sys
import time

import pytest


class TestHealth:
    def test_health_returns_structure(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in {"ok", "degraded"}
        assert "checks" in body
        assert body["version"] == "0.1.0"


class TestProviders:
    def test_lists_expected_providers(self, client):
        resp = client.get("/api/providers")
        assert resp.status_code == 200
        names = {p["name"] for p in resp.json()["providers"]}
        assert {"glm", "ollama", "openai", "claude", "gemini"} <= names

    def test_provider_fields(self, client):
        providers = client.get("/api/providers").json()["providers"]
        for p in providers:
            assert {"name", "model", "configured", "task"} <= set(p)


class TestHistory:
    def test_empty_history(self, client):
        client.delete("/api/history")
        resp = client.get("/api/history")
        assert resp.status_code == 200
        assert resp.json() == {"history": []}

    def test_clear_history(self, client):
        resp = client.delete("/api/history")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestChat:
    def test_chat_round_trip(self, client):
        client.delete("/api/history")
        resp = client.post("/api/chat", json={"prompt": "Olá, quem é você?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["response"]
        assert body["provider"]
        assert body["latency_ms"] >= 0

        history = client.get("/api/history").json()["history"]
        assert len(history) == 1
        assert history[0]["prompt"] == "Olá, quem é você?"

    def test_chat_with_explicit_provider(self, client):
        resp = client.post("/api/chat", json={"prompt": "oi", "provider": "stub-provider"})
        assert resp.status_code == 200
        assert resp.json()["provider"] == "stub-provider"

    def test_chat_requires_prompt(self, client):
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422

    def test_chat_unknown_agent_404(self, client):
        resp = client.post("/api/chat", json={"prompt": "oi", "agent": "nao-existe"})
        assert resp.status_code == 404

    def test_chat_with_known_agent(self, client):
        resp = client.post("/api/chat", json={"prompt": "oi", "agent": "studiopedia"})
        assert resp.status_code == 200
        assert resp.json()["response"].startswith("agente stub")

    def test_history_limit(self, client):
        client.delete("/api/history")
        for i in range(3):
            client.post("/api/chat", json={"prompt": f"msg {i}"})
        history = client.get("/api/history?limit=2").json()["history"]
        assert len(history) == 2
        # most recent first
        assert history[0]["prompt"] == "msg 2"


class TestHistoryStore:
    def test_add_list_clear(self, ai_stubs):
        from api.server import HistoryEntry, HistoryStore

        store = HistoryStore()
        for i in range(3):
            store.add(
                HistoryEntry(
                    id=str(i),
                    prompt=f"p{i}",
                    response="r",
                    provider="x",
                    task_type="chat",
                    timestamp=time.time(),
                )
            )
        assert len(store.list()) == 3
        assert store.list(limit=2)[0].prompt == "p2"  # reversed (newest first)
        store.clear()
        assert store.list() == []


class TestLeituraIAIntegration:
    """O router do leituraia e o Leitor Digital precisam estar montados no app."""

    _token: str | None = None

    @classmethod
    def _auth(cls, client):
        if cls._token is None:
            resp = client.post(
                "/api/leituraia/auth/registro",
                json={
                    "nome": "Prof. Ana",
                    "email": "ana.integracao@escola.edu.br",
                    "senha": "senha123",
                    "perfil": "professor",
                },
            )
            assert resp.status_code in {201, 409}, resp.text
            if resp.status_code == 201:
                cls._token = resp.json()["access_token"]
            else:
                login = client.post(
                    "/api/leituraia/auth/login",
                    json={"email": "ana.integracao@escola.edu.br", "senha": "senha123"},
                )
                assert login.status_code == 200, login.text
                cls._token = login.json()["access_token"]
        return cls._token

    def test_routers_montados_no_app(self, client):
        paths = set(client.get("/openapi.json").json()["paths"])
        assert "/api/leituraia/biblioteca" in paths
        assert "/api/leituraia/textos/gerar" in paths
        assert "/leituraia" in paths
        assert "/leituraia/leitor/{texto_id}" in paths

    def test_biblioteca_exige_autenticacao(self, client):
        assert client.get("/api/leituraia/biblioteca").status_code == 401

    def test_biblioteca_com_token(self, client):
        token = self._auth(client)
        resp = client.get("/api/leituraia/biblioteca", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        textos = resp.json()
        assert len(textos) >= 3
        assert {"id", "titulo", "conteudo", "perguntas"} <= set(textos[0])

    def test_pagina_inicial_lista_biblioteca(self, client):
        resp = client.get("/leituraia")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        pagina = resp.text
        assert "LeituraIA Brasil" in pagina
        assert "O que é o feudalismo?" in pagina
        assert "Ler agora" in pagina
        assert "/leituraia/leitor/" in pagina

    def test_filtro_por_disciplina(self, client):
        pagina = client.get("/leituraia", params={"disciplina": "Ciências"}).text
        assert "O ciclo da água na natureza" in pagina
        assert "O que é o feudalismo?" not in pagina
        assert "<option value='Ciências' selected>" in pagina
        assert "1 texto encontrado" in pagina

    def test_filtro_por_ano(self, client):
        pagina = client.get("/leituraia", params={"ano": "6"}).text
        assert "O ciclo da água na natureza" in pagina
        assert "O que é o feudalismo?" not in pagina
        assert "<option value='6' selected>6º ano</option>" in pagina

    def test_busca_por_tema(self, client):
        pagina = client.get("/leituraia", params={"q": "feudal"}).text
        assert "O que é o feudalismo?" in pagina
        assert "O ciclo da água na natureza" not in pagina
        assert "1 texto encontrado" in pagina

    def test_filtros_combinados_sem_resultado(self, client):
        pagina = client.get(
            "/leituraia", params={"disciplina": "Matemática", "ano": "9", "q": "álgebra"}
        ).text
        assert "Nenhum texto encontrado com esses filtros" in pagina
        assert "0 textos encontrados" in pagina
        assert "Limpar filtros" in pagina

    def test_busca_escapa_html(self, client):
        pagina = client.get("/leituraia", params={"q": "<script>alert(1)</script>"}).text
        assert "<script>alert(1)</script>" not in pagina
        assert "&lt;script&gt;" in pagina

    def test_pagina_inicial_nao_expoe_gabarito(self, client):
        pagina = client.get("/leituraia").text
        assert "Durante a Idade Média, entre os séculos V e XV." not in pagina

    def test_leitor_digital_renderiza_html(self, client):
        token = self._auth(client)
        textos = client.get(
            "/api/leituraia/biblioteca", headers={"Authorization": f"Bearer {token}"}
        ).json()
        feudalismo = next(t for t in textos if t["tema"] == "Feudalismo")

        resp = client.get(f"/leituraia/leitor/{feudalismo['id']}")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        pagina = resp.text
        assert "Leitor Digital" in pagina
        assert feudalismo["titulo"] in pagina
        # Navegação de volta para a biblioteca.
        assert 'href="/leituraia"' in pagina
        # O gabarito nunca vai para a página pública.
        assert "Durante a Idade Média, entre os séculos V e XV." not in pagina
        # Registro automático da leitura embutido na página (sem login).
        assert "data-texto-id" in pagina
        assert "sendBeacon" in pagina
        assert "/leitura'" in pagina

    def test_registro_publico_pelo_leitor(self, client):
        token = self._auth(client)
        cabecalho = {"Authorization": f"Bearer {token}"}
        textos = client.get("/api/leituraia/biblioteca", headers=cabecalho).json()
        texto = textos[0]
        antes = client.get("/api/leituraia/dashboard", headers=cabecalho).json()["leituras"]

        resp = client.post(
            f"/leituraia/leitor/{texto['id']}/leitura",
            json={"tempo_segundos": 42, "completou": False, "sessao": "sessao-integracao-1"},
        )
        assert resp.status_code == 201
        assert resp.json()["total_leituras"] == antes + 1

        # A mesma sessão não conta de novo (idempotência).
        repetido = client.post(
            f"/leituraia/leitor/{texto['id']}/leitura",
            json={"tempo_segundos": 50, "completou": True, "sessao": "sessao-integracao-1"},
        )
        assert repetido.json()["total_leituras"] == antes + 1

    def test_registro_publico_texto_inexistente_404(self, client):
        resp = client.post(
            "/leituraia/leitor/nao-existe/leitura",
            json={"tempo_segundos": 10, "sessao": "x"},
        )
        assert resp.status_code == 404

    def test_leitor_texto_inexistente_404(self, client):
        assert client.get("/leituraia/leitor/nao-existe").status_code == 404


class _BloqueioMonolito:
    """Finder que esconde o pacote ``ai/`` real, simulando sua ausência.

    Só remover as entradas de ``sys.modules`` não basta: a raiz do repositório
    está em ``sys.path`` e o import seguinte reexecutaria o pacote de verdade.
    """

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "ai" or fullname.startswith("ai."):
            raise ModuleNotFoundError(f"simulado: {fullname} indisponivel", name=fullname)
        return None


class TestSemMonolito:
    """O painel precisa subir quando o pacote ai/ não está disponível."""

    @pytest.fixture
    def client_sem_ai(self, ai_stubs, monkeypatch):
        for nome in [n for n in sys.modules if n == "ai" or n.startswith("ai.")]:
            monkeypatch.delitem(sys.modules, nome, raising=False)
        monkeypatch.setattr(sys, "meta_path", [_BloqueioMonolito(), *sys.meta_path])

        from fastapi.testclient import TestClient

        from api.server import app

        with TestClient(app) as cliente:  # o context manager dispara o startup
            yield cliente

    def test_health_degrada_sem_monolito(self, client_sem_ai):
        resp = client_sem_ai.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["monolito"] == "unavailable"
        assert body["version"] == "0.1.0"

    def test_endpoints_do_monolito_retornam_503(self, client_sem_ai):
        for caminho in ("/api/providers", "/api/agents", "/api/config"):
            resp = client_sem_ai.get(caminho)
            assert resp.status_code == 503, caminho
            assert "Monolito ai/" in resp.json()["detail"]

    def test_chat_retorna_503(self, client_sem_ai):
        resp = client_sem_ai.post("/api/chat", json={"prompt": "oi"})
        assert resp.status_code == 503

    def test_rotas_do_leituraia_seguem_funcionando(self, client_sem_ai):
        assert client_sem_ai.get("/leituraia").status_code == 200
        assert client_sem_ai.get("/api/leituraia/biblioteca").status_code == 401


class TestMetricsAndConfig:
    def test_metrics_shape(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        assert "metrics" in resp.json()

    def test_config_has_no_secrets(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        body = resp.json()
        assert "rag_enabled" in body
        # no api keys may leak
        assert not any("key" in k.lower() for k in body)
