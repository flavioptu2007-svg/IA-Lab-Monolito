"""Agentes, plugins e apresentações locais: estrutura, persistência e exportação."""

from __future__ import annotations

import builtins
import json
from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

import src.education.services as services
from ai.agents.education_agents import (
    EducationPlannerAgent,
    EducationReviewerAgent,
    PresentationDesignerAgent,
    read_skill,
)
from ai.providers.ollama import OllamaProvider
from ai.settings import settings
from src.api.v2.education_generation import router
from src.education.presentation_models import (
    PresentationCreate,
    PresentationResponse,
    presentation_checks,
)
from src.education.presentation_plugins import available_plugins, export_html, export_pptx
from src.education.services import EducationStore


def content():
    return {
        "title": "Fontes históricas",
        "theme": "navy",
        "slides": [
            {
                "layout": "title",
                "title": "Como conhecemos o passado?",
                "subtitle": "Fontes históricas e memória",
                "bullets": ["Investigar vestígios"],
                "speaker_notes": "Pergunte quais objetos contam histórias da comunidade.",
            },
            {
                "layout": "comparison",
                "title": "Duas fontes, duas perspectivas",
                "bullets": ["Uma carta", "Uma fotografia"],
                "speaker_notes": "Compare autoria, data e contexto.",
            },
            {
                "layout": "closing",
                "title": "Qual fonte você escolheria?",
                "bullets": ["Justifique sua escolha"],
                "speaker_notes": "Feche com uma discussão em duplas.",
            },
        ],
    }


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "api_token", SecretStr("test-token"))
    monkeypatch.setattr(services, "_store", EducationStore(str(tmp_path / "education.db")))
    app = FastAPI()
    app.include_router(router)
    with TestClient(app, headers={"X-API-Key": "test-token"}) as client:
        yield client


@pytest.fixture
def complete(monkeypatch):
    mock = AsyncMock(return_value=json.dumps(content()))
    monkeypatch.setattr(OllamaProvider, "complete", mock)
    return mock


def generate(client):
    response = client.post(
        "/api/v2/education/generate",
        json={"material_type": "presentation", "topic": "Fontes históricas", "slide_count": 3},
    )
    assert response.status_code == 201, response.text
    return response.json()["material"]


def test_generate_review_restart_and_export(client, complete, monkeypatch):
    item = generate(client)
    assert len(item["slides"]) == 3
    assert item["status"] == "rascunho"
    revised = PresentationCreate.model_validate(item).model_dump()
    revised["slides"][0]["title"] = "Título revisado"
    result = client.post(
        f"/api/v2/education/materials/presentation/{item['id']}/review",
        json={"content": revised, "expected_updated_at": item["updated_at"], "approve": True},
    )
    assert result.status_code == 200, result.text
    path = services.get_store()._repository.path
    monkeypatch.setattr(services, "_store", EducationStore(path))
    saved = client.get("/api/v2/education/materials").json()["materials"][0]
    assert saved["material_type"] == "presentation"
    assert saved["material"]["slides"][0]["title"] == "Título revisado"
    assert saved["material"]["status"] == "aprovado"
    response = client.get(f"/api/v2/education/materials/presentation/{item['id']}/export/html")
    assert response.status_code == 200
    assert "Título revisado" in response.text
    assert "Revisado pelo professor" in response.text
    assert "attachment" in response.headers["content-disposition"]
    assert complete.call_args.kwargs["system_prompt"] == read_skill("professional-presentations")


def test_requested_count_and_theme(client, complete):
    response = client.post(
        "/api/v2/education/generate",
        json={"material_type": "presentation", "topic": "Fontes históricas", "slide_count": 4},
    )
    assert response.status_code == 502
    assert client.get("/api/v2/education/materials").json()["materials"] == []
    response = client.post(
        "/api/v2/education/generate",
        json={
            "material_type": "presentation",
            "topic": "Fontes históricas",
            "slide_count": 3,
            "theme": "paper",
        },
    )
    assert response.status_code == 201
    assert response.json()["material"]["theme"] == "paper"


def test_editorial_checks_do_not_claim_fact_verification(client, complete):
    material = generate(client)
    response = client.get(f"/api/v2/education/materials/presentation/{material['id']}/checks")
    assert response.json()["fact_checked"] is False
    assert any("referências" in value for value in response.json()["issues"])
    deck = PresentationCreate.model_validate(content())
    deck.slides[0].speaker_notes = ""
    assert any("notas" in value for value in presentation_checks(deck))


def test_html_escapes_user_content_and_has_no_external_assets():
    deck = PresentationResponse.model_validate({**content(), "id": "abc"})
    deck.slides[0].title = '<script>alert("x")</script>'
    result = export_html(deck).decode()
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "Rascunho · revisão pendente" in result
    assert "<img" not in result
    assert "@import" not in result
    assert '<html lang="pt-BR">' in result
    assert result.count('<article class="slide') == 3


@pytest.mark.parametrize("theme", ["navy", "paper"])
def test_powerpoint_is_editable_and_has_notes(theme):
    pptx = pytest.importorskip("pptx")
    deck = PresentationResponse.model_validate({**content(), "theme": theme})
    result = export_pptx(deck)
    presentation = pptx.Presentation(BytesIO(result))
    assert len(presentation.slides) == 3
    assert abs(presentation.slide_width / presentation.slide_height - 16 / 9) < 0.001
    texts = [shape.text for shape in presentation.slides[0].shapes if shape.has_text_frame]
    assert deck.slides[0].title in texts
    assert any("RASCUNHO" in value for value in texts)
    assert deck.slides[0].speaker_notes in presentation.slides[0].notes_slide.notes_text_frame.text


def test_missing_optional_powerpoint_plugin_is_actionable(monkeypatch):
    original = builtins.__import__

    def block(name, *args, **kwargs):
        if name == "pptx":
            raise ImportError("Not installed")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block)
    with pytest.raises(RuntimeError, match="presentations"):
        export_pptx(PresentationResponse.model_validate(content()))


def test_plugin_and_skill_inventory(client):
    tools = client.get("/api/v2/education/tools").json()
    assert len(tools["plugins"]) == 2
    assert all(plugin["cost"] == "local" for plugin in tools["plugins"])
    assert {agent["provider"] for agent in tools["agents"]} == {"ollama"}
    assert len(tools["skills"]) == 3
    assert all(skill["content"] for skill in tools["skills"])
    assert available_plugins()[0]["installed"] is True
    with pytest.raises(ValueError):
        read_skill("../../not-a-skill")


@pytest.mark.parametrize(
    "agent", [EducationPlannerAgent, PresentationDesignerAgent, EducationReviewerAgent]
)
@pytest.mark.asyncio
async def test_free_agents_use_only_local_ollama(agent, complete):
    await agent().run("Preparar apresentação")
    complete.assert_awaited_once()
    with pytest.raises(ValueError, match="somente Ollama"):
        await agent().run("Preparar apresentação", provider="openai")
    assert complete.await_count == 1


def test_agents_registered():
    from ai.agents.base import get_agent_registry

    names = get_agent_registry().list_names()
    assert {"education_planner", "presentation_designer", "education_reviewer"} <= set(names)


@pytest.mark.parametrize("bullets", [["x" * 111], ["a", "b", "c", "d", "e"], [" "]])
def test_dense_or_empty_bullets_rejected(bullets):
    value = content()
    value["slides"][0]["bullets"] = bullets
    with pytest.raises(ValidationError):
        PresentationCreate.model_validate(value)


def test_presentation_routes_require_authentication(client):
    for path in [
        "/tools",
        "/materials/presentation/abc/checks",
        "/materials/presentation/abc/export/pptx",
    ]:
        assert (
            client.get("/api/v2/education" + path, headers={"X-API-Key": "wrong"}).status_code
            == 401
        )


def test_missing_material_and_unsupported_export(client):
    assert client.get("/api/v2/education/materials/presentation/abc/export/html").status_code == 404
    assert client.get("/api/v2/education/materials/presentation/abc/checks").status_code == 404
    assert client.get("/api/v2/education/materials/presentation/abc/export/exe").status_code == 422


def test_powerpoint_multiline_subtitle_is_normalized_and_fitted():
    pptx = pytest.importorskip("pptx")
    from pptx.enum.text import MSO_AUTO_SIZE

    deck = PresentationResponse.model_validate(content())
    deck.slides[0].subtitle = "Linha um\nLinha dois\nLinha três\nLinha quatro"
    presentation = pptx.Presentation(BytesIO(export_pptx(deck)))
    subtitle = next(
        shape
        for shape in presentation.slides[0].shapes
        if shape.has_text_frame and shape.text == "Linha um Linha dois Linha três Linha quatro"
    )
    assert subtitle.text_frame.auto_size == MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    assert subtitle.top + subtitle.height <= min(
        shape.top
        for shape in presentation.slides[0].shapes
        if shape.has_text_frame and shape.text.startswith("• ")
    )
