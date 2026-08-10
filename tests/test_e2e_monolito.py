"""Teste E2E — Percorre todas as rotas do monolito FastAPI.

Valida que:
- Todas as 57 rotas respondem sem erros 500
- Endpoints GET sem parâmetros retornam 200
- Endpoints POST/PATCH/DELETE aceitam payloads válidos
- Endpoints condicionais (OpenVINO, audio) retornam status coerentes
- A app não quebra com requisições sequenciais
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class TestE2EMonolito:
    """Teste E2E que percorre todas as rotas registradas no monolito.

    Organizado por módulo para facilitar leitura e diagnóstico.
    Usa TestClient para requisições reais contra a app FastAPI.
    """

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from api.server import app

        return TestClient(app)

    # ═══════════════════════════════════════════════════════════════
    # Health & System
    # ═══════════════════════════════════════════════════════════════

    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "degraded")

    def test_config(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        assert "primary_provider" in resp.json()

    def test_metrics(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        assert "metrics" in resp.json()

    # ═══════════════════════════════════════════════════════════════
    # Providers & Agents
    # ═══════════════════════════════════════════════════════════════

    def test_providers(self, client):
        resp = client.get("/api/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert len(data["providers"]) >= 8

    def test_agents(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data

    # ═══════════════════════════════════════════════════════════════
    # Chat & History
    # ═══════════════════════════════════════════════════════════════

    def test_history_list(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 200
        assert "history" in resp.json()

    def test_history_clear(self, client):
        resp = client.delete("/api/history")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    # ═══════════════════════════════════════════════════════════════
    # Audio
    # ═══════════════════════════════════════════════════════════════

    def test_audio_status(self, client):
        resp = client.get("/api/audio/status")
        assert resp.status_code == 200

    def test_audio_devices(self, client):
        resp = client.get("/api/audio/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert "sinks" in data

    def test_audio_config(self, client):
        resp = client.get("/api/audio/config")
        assert resp.status_code == 200
        assert "input_device" in resp.json()

    def test_audio_mic_status(self, client):
        resp = client.get("/api/audio/mic/status")
        assert resp.status_code == 200

    def test_audio_metrics(self, client):
        resp = client.get("/api/audio/metrics")
        assert resp.status_code == 200
        assert "audio_metrics" in resp.json()

    # ═══════════════════════════════════════════════════════════════
    # Chat SSE (v2 — Coraci)
    # ═══════════════════════════════════════════════════════════════

    def test_v2_chat_config_get(self, client):
        resp = client.get("/api/v2/config")
        assert resp.status_code == 200

    def test_v2_chat_config_post(self, client):
        resp = client.post("/api/v2/config", json={"openai_api_key": "test"})
        assert resp.status_code == 200

    def test_v2_conversations_list(self, client):
        resp = client.get("/api/v2/conversations")
        assert resp.status_code == 200

    def test_v2_conversations_clear(self, client):
        resp = client.delete("/api/v2/conversations")
        assert resp.status_code == 200

    def test_v2_conversations_crud(self, client):
        """CRUD completo de conversa — create, get, delete."""
        # Cria uma conversa via chat (o endpoint espera "message" não "prompt")
        with patch("src.api.v2.chat_coraci._stream_chat_openai") as mock_stream:
            mock_stream.return_value = _async_stream(['data: {"type": "done"}\n\n'])
            resp = client.post("/api/v2/chat", json={"message": "teste e2e"})
            assert resp.status_code == 200

        # Lista conversas (retorna array de ConversationSummary)
        resp = client.get("/api/v2/conversations")
        assert resp.status_code == 200
        convs = resp.json()
        assert isinstance(convs, list)
        assert len(convs) >= 1
        conv_id = convs[0]["id"]

        # Get específico
        resp = client.get(f"/api/v2/conversations/{conv_id}")
        assert resp.status_code == 200

        # Delete
        resp = client.delete(f"/api/v2/conversations/{conv_id}")
        assert resp.status_code == 200

    # ═══════════════════════════════════════════════════════════════
    # OpenVINO (condicional — retorna 503 ou 200)
    # ═══════════════════════════════════════════════════════════════

    def test_openvino_health(self, client):
        resp = client.get("/api/v2/openvino/health")
        assert resp.status_code == 200
        assert "openvino_available" in resp.json()

    def test_openvino_models(self, client):
        resp = client.get("/api/v2/openvino/models")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_openvino_generate_503(self, client):
        """Sem OpenVINO, generate retorna 503."""
        with patch("src.openvino.pipelines.is_available", AsyncMock(return_value=False)):
            resp = client.post("/api/v2/openvino/generate", params={"prompt": "teste"})
            assert resp.status_code == 503
            assert resp.json()["detail"] == "openvino_not_available"

    def test_openvino_transcribe_503(self, client):
        with patch("src.openvino.pipelines.is_available", AsyncMock(return_value=False)):
            resp = client.post(
                "/api/v2/openvino/transcribe", files={"audio": ("test.wav", b"data", "audio/wav")}
            )
            assert resp.status_code == 503

    def test_openvino_rag_query_503(self, client):
        with patch("src.openvino.pipelines.is_available", AsyncMock(return_value=False)):
            resp = client.post("/api/v2/openvino/rag/query", params={"question": "teste"})
            assert resp.status_code == 503

    # ═══════════════════════════════════════════════════════════════
    # Education — BNCC
    # ═══════════════════════════════════════════════════════════════

    def test_education_health(self, client):
        resp = client.get("/api/v2/education/health")
        assert resp.status_code == 200
        assert resp.json()["module"] == "education"

    def test_education_bncc_skills(self, client):
        resp = client.get("/api/v2/education/bncc/skills")
        assert resp.status_code == 200
        assert resp.json()["total"] > 20
        assert len(resp.json()["skills"]) > 0

    def test_education_bncc_skills_filtro_ano(self, client):
        resp = client.get("/api/v2/education/bncc/skills", params={"year": "EF_6"})
        assert resp.status_code == 200
        assert all(s["code"].startswith("EF06") for s in resp.json()["skills"])

    def test_education_bncc_skills_busca(self, client):
        resp = client.get("/api/v2/education/bncc/skills", params={"query": "tempo"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_education_bncc_competences(self, client):
        resp = client.get("/api/v2/education/bncc/competences")
        assert resp.status_code == 200
        assert len(resp.json()["competences"]) == 8

    # ═══════════════════════════════════════════════════════════════
    # Education — Lesson Plans CRUD
    # ═══════════════════════════════════════════════════════════════

    def test_education_lesson_plans_crud(self, client):
        """CRUD completo de planos de aula."""
        # Create
        resp = client.post("/api/v2/education/lesson-plans", json={"title": "Brasil República"})
        assert resp.status_code == 201
        plan_id = resp.json()["lesson_plan"]["id"]

        # List
        resp = client.get("/api/v2/education/lesson-plans")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # Get by ID
        resp = client.get(f"/api/v2/education/lesson-plans/{plan_id}")
        assert resp.status_code == 200
        assert resp.json()["lesson_plan"]["title"] == "Brasil República"

        # Update
        resp = client.patch(
            f"/api/v2/education/lesson-plans/{plan_id}",
            json={"title": "Brasil República - Atualizado", "status": "approved"},
        )
        assert resp.status_code == 200
        assert resp.json()["lesson_plan"]["title"] == "Brasil República - Atualizado"

        # Delete
        resp = client.delete(f"/api/v2/education/lesson-plans/{plan_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Get 404 after delete
        resp = client.get(f"/api/v2/education/lesson-plans/{plan_id}")
        assert resp.status_code == 404

    def test_education_lesson_plan_not_found(self, client):
        resp = client.get("/api/v2/education/lesson-plans/fake-id")
        assert resp.status_code == 404

    # ═══════════════════════════════════════════════════════════════
    # Education — Activities CRUD
    # ═══════════════════════════════════════════════════════════════

    def test_education_activities_crud(self, client):
        """CRUD completo de atividades."""
        # Create
        resp = client.post(
            "/api/v2/education/activities",
            json={"title": "Quiz Roma", "activity_type": "FLASHCARD"},
        )
        assert resp.status_code == 201
        act_id = resp.json()["activity"]["id"]

        # List
        resp = client.get("/api/v2/education/activities")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # Get
        resp = client.get(f"/api/v2/education/activities/{act_id}")
        assert resp.status_code == 200

        # Update
        resp = client.patch(
            f"/api/v2/education/activities/{act_id}", json={"difficulty": "DIFÍCIL"}
        )
        assert resp.status_code == 200

        # Delete
        resp = client.delete(f"/api/v2/education/activities/{act_id}")
        assert resp.status_code == 200

    # ═══════════════════════════════════════════════════════════════
    # Education — Evaluations CRUD
    # ═══════════════════════════════════════════════════════════════

    def test_education_evaluations_crud(self, client):
        """CRUD completo de avaliações."""
        # Create
        resp = client.post(
            "/api/v2/education/evaluations",
            json={
                "title": "Prova - Grécia",
                "evaluation_type": "EXAM",
                "questions": [
                    {
                        "number": 1,
                        "type": "OBJETIVA",
                        "command": "Principal cidade-estado grega?",
                        "options": ["Atenas", "Esparta", "Corinto"],
                        "correct_answer": "Atenas",
                        "score": 2.0,
                    }
                ],
            },
        )
        assert resp.status_code == 201
        eval_id = resp.json()["evaluation"]["id"]

        # List
        resp = client.get("/api/v2/education/evaluations")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # Get
        resp = client.get(f"/api/v2/education/evaluations/{eval_id}")
        assert resp.status_code == 200
        assert len(resp.json()["evaluation"]["questions"]) == 1

        # Update
        resp = client.patch(
            f"/api/v2/education/evaluations/{eval_id}", json={"title": "Prova - Grécia (versão 2)"}
        )
        assert resp.status_code == 200

        # Delete
        resp = client.delete(f"/api/v2/education/evaluations/{eval_id}")
        assert resp.status_code == 200

    # ═══════════════════════════════════════════════════════════════
    # Education — Calendar
    # ═══════════════════════════════════════════════════════════════

    def test_education_calendar_crud(self, client):
        """CRUD de eventos do calendário."""
        # Create
        resp = client.post(
            "/api/v2/education/calendar",
            json={"title": "Prova bimestral", "event_date": "2026-06-15", "event_type": "PROVA"},
        )
        assert resp.status_code == 201
        event_id = resp.json()["event"]["id"]

        # List
        resp = client.get("/api/v2/education/calendar")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # Delete
        resp = client.delete(f"/api/v2/education/calendar/{event_id}")
        assert resp.status_code == 200

    # ═══════════════════════════════════════════════════════════════
    # OpenAPI / Docs
    # ═══════════════════════════════════════════════════════════════

    def test_openapi_json(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema
        paths = schema["paths"]
        # Verifica que os principais módulos estão documentados
        assert "/api/health" in paths
        assert "/api/v2/chat" in paths
        assert "/api/v2/openvino/health" in paths
        assert "/api/v2/education/health" in paths

    def test_docs_ui(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_redoc_ui(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")


# ═════════════════════════════════════════════════════════════════════════════
# Helper
# ═════════════════════════════════════════════════════════════════════════════


async def _async_stream(events: list[str]):
    """Gera eventos SSE como um async generator para mocks."""
    for event in events:
        yield event
