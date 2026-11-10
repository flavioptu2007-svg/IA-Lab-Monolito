"""Geração local e revisão: nenhum teste chama um modelo real ou provedor pago."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

import src.education.services as services
from ai.providers.ollama import OllamaProvider
from ai.settings import settings
from src.api.v2.education import router as education_router
from src.api.v2.education_generation import router as workflow_router
from src.education.generation import CREATE_MODELS
from src.education.services import EducationStore

MATERIALS = {
    "lesson_plan": {
        "title": "Fontes históricas",
        "learning_objectives": ["Analisar fontes"],
        "moments": [{"title": "Leitura", "description": "Compare cartas de duas épocas"}],
    },
    "activity": {
        "title": "Comparação de cartas",
        "content": {"text": "Compare as cartas e identifique seus autores."},
        "instructions": "Organize a turma em duplas.",
    },
    "evaluation": {
        "title": "Avaliação de fontes",
        "questions": [
            {
                "command": "O que é uma fonte histórica?",
                "correct_answer": "Um vestígio do passado.",
                "score": 10,
            }
        ],
    },
}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "api_token", SecretStr("test-token"))
    monkeypatch.setattr(services, "_store", EducationStore(str(tmp_path / "education.db")))
    app = FastAPI()
    app.include_router(education_router)
    app.include_router(workflow_router)
    with TestClient(app, headers={"X-API-Key": "test-token"}) as client:
        yield client


@pytest.fixture
def complete(monkeypatch):
    mock = AsyncMock(return_value=json.dumps(MATERIALS["lesson_plan"]))
    monkeypatch.setattr(OllamaProvider, "complete", mock)
    return mock


def generate(client, complete, kind="lesson_plan"):
    complete.return_value = json.dumps(MATERIALS[kind])
    response = client.post(
        "/api/v2/education/generate",
        json={"material_type": kind, "topic": "Fontes históricas", "academic_year": "EF_6"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def content(item):
    fields = CREATE_MODELS[item["material_type"]].model_fields
    return {key: value for key, value in item["material"].items() if key in fields}


def review(client, item, approve=False, changes=None):
    edited = {**content(item), **(changes or {})}
    return client.post(
        f"/api/v2/education/materials/{item['material_type']}/{item['material']['id']}/review",
        json={
            "content": edited,
            "approve": approve,
            "expected_updated_at": item["material"]["updated_at"],
        },
    )


@pytest.mark.parametrize("kind", list(MATERIALS))
def test_generate_review_approve_and_reopen_after_restart(client, complete, monkeypatch, kind):
    item = generate(client, complete, kind)
    assert item["material"]["status"] == "rascunho"
    assert item["material"]["is_ai_generated"] is True
    assert item["material"]["reviewed_at"] is None
    assert item["material"]["academic_year"] == "EF_6"
    revised = review(client, item, changes={"title": "Revisado pelo professor"})
    assert revised.status_code == 200
    assert revised.json()["material"]["status"] == "rascunho"
    approved = review(client, revised.json(), approve=True)
    assert approved.status_code == 200
    assert approved.json()["material"]["reviewed_at"] is not None
    path = services.get_store()._repository.path
    monkeypatch.setattr(services, "_store", EducationStore(path))
    restored = client.get("/api/v2/education/materials").json()["materials"][0]
    assert restored["material"]["title"] == "Revisado pelo professor"
    assert restored["material"]["status"] == "aprovado"
    assert restored["material"]["is_ai_generated"] is True
    assert restored["material"]["reviewed_at"] == approved.json()["material"]["reviewed_at"]
    complete.assert_awaited_once()
    assert "professores de História" in complete.call_args.kwargs["system_prompt"]


@pytest.mark.parametrize(
    "response", ["", "Não consigo gerar", "[]", '{"title":"Incompleto"}', "null", "x" * 100001]
)
def test_invalid_generation_never_saves_a_material(client, complete, response):
    complete.return_value = response
    result = client.post("/api/v2/education/generate", json={"topic": "História"})
    assert result.status_code == 502
    assert client.get("/api/v2/education/materials").json()["materials"] == []


def test_fenced_json_and_user_choices_override_model(client, complete):
    complete.return_value = (
        "```json\n"
        + json.dumps(
            {**MATERIALS["lesson_plan"], "academic_year": "EF_9", "bncc_skills": ["INVENTADO"]}
        )
        + "\n```"
    )
    response = client.post(
        "/api/v2/education/generate",
        json={
            "topic": "Fontes",
            "academic_year": "EF_6",
            "bncc_skills": ["EF06HI02"],
            "learning_objectives": ["Comparar cartas"],
        },
    )
    assert response.status_code == 201
    result = response.json()["material"]
    assert result["bncc_skills"] == ["EF06HI02"]
    assert result["learning_objectives"] == ["Comparar cartas"]
    assert result["academic_year"] == "EF_6"


@pytest.mark.parametrize(
    "extra",
    [
        {"provider": "openai"},
        {"bncc_skills": ["INVENTADO"]},
        {"academic_year": "EF_6", "bncc_skills": ["EF09HI01"]},
        {"topic": "   "},
        {"duration_minutes": 0},
        {"material_type": "unknown"},
    ],
)
def test_invalid_request_does_not_call_ai(client, complete, extra):
    response = client.post("/api/v2/education/generate", json={"topic": "História", **extra})
    assert response.status_code == 422
    complete.assert_not_awaited()


def test_provider_unavailable_never_falls_back_or_saves(client, complete):
    complete.side_effect = httpx.ConnectError("Ollama indisponível")
    response = client.post("/api/v2/education/generate", json={"topic": "História"})
    assert response.status_code == 503
    assert client.get("/api/v2/education/materials").json()["materials"] == []
    complete.assert_awaited_once()


def test_authentication_protects_generation_listing_and_review(client, complete):
    for method, path in [
        ("POST", "/generate"),
        ("GET", "/materials"),
        ("POST", "/materials/lesson_plan/abc/review"),
    ]:
        response = client.request(
            method,
            "/api/v2/education" + path,
            headers={"X-API-Key": "wrong"},
            json={} if method == "POST" else None,
        )
        assert response.status_code == 401
    complete.assert_not_awaited()


def test_stale_review_returns_conflict_and_preserves_latest(client, complete):
    item = generate(client, complete)
    latest = review(client, item, changes={"title": "Última revisão"})
    assert latest.status_code == 200
    stale = review(client, item, approve=True, changes={"title": "Revisão antiga"})
    assert stale.status_code == 409
    current = client.get("/api/v2/education/materials").json()["materials"][0]
    assert current["material"]["title"] == "Última revisão"
    assert current["material"]["status"] == "rascunho"


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "outro"},
        {"status": "aprovado"},
        {"is_ai_generated": False},
        {"title": None},
        {"moments": []},
    ],
)
def test_invalid_review_does_not_overwrite_saved_content(client, complete, changes):
    item = generate(client, complete)
    result = review(client, item, approve=True, changes=changes)
    assert result.status_code == 422
    assert (
        client.get("/api/v2/education/materials").json()["materials"][0]["material"]
        == item["material"]
    )


def test_review_requires_version_and_handles_missing_id(client, complete):
    item = generate(client, complete)
    url = f"/api/v2/education/materials/lesson_plan/{item['material']['id']}/review"
    assert client.post(url, json={"content": content(item), "approve": True}).status_code == 422
    item["material"]["id"] = "inexistente"
    assert review(client, item).status_code == 404


@pytest.mark.parametrize(
    "kind,route",
    [("lesson_plan", "lesson-plans"), ("activity", "activities"), ("evaluation", "evaluations")],
)
def test_ordinary_patch_invalidates_approval(client, complete, kind, route):
    item = generate(client, complete, kind)
    approved = review(client, item, approve=True).json()
    result = client.patch(
        f"/api/v2/education/{route}/{item['material']['id']}", json={"title": "Modificado"}
    )
    assert result.status_code == 200
    restored = client.get("/api/v2/education/materials").json()["materials"][0]["material"]
    assert restored["status"] == "rascunho"
    assert restored["reviewed_at"] is None
    assert approved["material"]["reviewed_at"] is not None


def test_evaluation_scores_must_match_before_approval(client, complete):
    item = generate(client, complete, "evaluation")
    assert review(client, item, approve=True, changes={"total_score": 20}).status_code == 422
    assert review(client, item, approve=True, changes={"passing_score": 12}).status_code == 422


def test_new_routes_registered_in_real_app():
    from api.server import app

    paths = app.openapi()["paths"]
    assert "/api/v2/education/generate" in paths
    assert "/api/v2/education/materials/{kind}/{material_id}/review" in paths
