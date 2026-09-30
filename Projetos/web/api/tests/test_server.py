"""Tests for web/api/server.py endpoints (monolith imports stubbed)."""

import time


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
        resp = client.post(
            "/api/chat", json={"prompt": "oi", "provider": "stub-provider"}
        )
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
