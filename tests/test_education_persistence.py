"""Regressões de persistência, transações e contrato HTTP educacional."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
from threading import Barrier

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

import src.education.services as services
from src.api.v2.education import router
from src.education.schemas import (
    ActivityCreate,
    ActivityUpdate,
    CalendarEventCreate,
    EvaluationCreate,
    EvaluationUpdate,
    LessonMomentContent,
    LessonPlanCreate,
    LessonPlanUpdate,
    QuestionSchema,
)
from src.education.services import EducationStore


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "materiais" / "education.db")


def test_restart_recovers_all_materials_and_nested_content(db_path):
    store = EducationStore(db_path)
    plan = store.create_lesson_plan(
        LessonPlanCreate(
            title="Fontes históricas — revisão",
            bncc_skills=["EF06HI02"],
            moments=[LessonMomentContent(title="Analisar uma carta", resources=["Carta"])],
        )
    )
    activity = store.create_activity(
        ActivityCreate(title="Cartas", content={"itens": [{"texto": "Quem escreveu?"}]})
    )
    evaluation = store.create_evaluation(
        EvaluationCreate(
            title="Avaliação",
            questions=[QuestionSchema(command="O que é uma fonte?", correct_answer="Vestígio")],
        )
    )
    event = store.create_event(
        CalendarEventCreate(title="Aula", event_date=date(2026, 11, 20), lesson_plan_id=plan.id)
    )
    restarted = EducationStore(db_path)
    assert restarted.get_lesson_plan(plan.id) == plan
    assert restarted.get_activity(activity.id) == activity
    assert restarted.get_evaluation(evaluation.id) == evaluation
    assert restarted.list_events() == [event]
    assert restarted.counts() == {
        "lesson_plans": 1,
        "activities": 1,
        "evaluations": 1,
        "events": 1,
    }


@pytest.mark.parametrize(
    "create,get,update,delete,create_model,update_model",
    [
        (
            "create_lesson_plan",
            "get_lesson_plan",
            "update_lesson_plan",
            "delete_lesson_plan",
            LessonPlanCreate,
            LessonPlanUpdate,
        ),
        (
            "create_activity",
            "get_activity",
            "update_activity",
            "delete_activity",
            ActivityCreate,
            ActivityUpdate,
        ),
        (
            "create_evaluation",
            "get_evaluation",
            "update_evaluation",
            "delete_evaluation",
            EvaluationCreate,
            EvaluationUpdate,
        ),
    ],
)
def test_edits_and_deletes_survive_restart(
    db_path, create, get, update, delete, create_model, update_model
):
    store = EducationStore(db_path)
    original = getattr(store, create)(create_model(title="Original"))
    revised = getattr(store, update)(original.id, update_model(title="Revisado"))
    assert revised.updated_at >= original.updated_at
    assert getattr(EducationStore(db_path), get)(original.id).title == "Revisado"
    assert getattr(EducationStore(db_path), delete)(original.id)
    assert getattr(EducationStore(db_path), get)(original.id) is None
    assert not getattr(EducationStore(db_path), delete)(original.id)
    assert getattr(EducationStore(db_path), update)(original.id, update_model(title="X")) is None


def test_calendar_delete_and_filters_survive_restart(db_path):
    store = EducationStore(db_path)
    event = store.create_event(CalendarEventCreate(title="Aula", event_date=date(2026, 11, 20)))
    store.create_event(
        CalendarEventCreate(title="Prova", event_date=date(2026, 11, 19), event_type="PROVA")
    )
    restarted = EducationStore(db_path)
    assert restarted.list_events(event_type="PROVA")[0].title == "Prova"
    assert restarted.list_events()[0].title == "Prova"
    assert restarted.delete_event(event.id)
    assert EducationStore(db_path).counts()["events"] == 1


def test_filters_pagination_and_external_writes(db_path):
    first = EducationStore(db_path)
    second = EducationStore(db_path)
    first.create_lesson_plan(LessonPlanCreate(title="A", academic_year="EF_6"))
    first.create_lesson_plan(LessonPlanCreate(title="B", academic_year="EF_8"))
    second.create_lesson_plan(LessonPlanCreate(title="C", academic_year="EF_8"))
    assert [p.title for p in first.list_lesson_plans(academic_year="EF_8", limit=1, offset=1)] == [
        "B"
    ]
    assert second.counts()["lesson_plans"] == 3


def test_simultaneous_edits_keep_independent_fields(db_path):
    first = EducationStore(db_path)
    second = EducationStore(db_path)
    plan = first.create_lesson_plan(LessonPlanCreate(title="Original", topic="Antes"))
    barrier = Barrier(2)

    def edit(store, changes):
        barrier.wait(timeout=5)
        return store.update_lesson_plan(plan.id, changes)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(edit, first, LessonPlanUpdate(title="Título revisado"))
        b = pool.submit(edit, second, LessonPlanUpdate(topic="Tema revisado"))
        a.result(timeout=10)
        b.result(timeout=10)
    result = EducationStore(db_path).get_lesson_plan(plan.id)
    assert result.title == "Título revisado"
    assert result.topic == "Tema revisado"


def test_write_failure_does_not_report_saved_material(db_path):
    store = EducationStore(db_path)
    with closing(sqlite3.connect(db_path)) as db, db:
        db.execute(
            "CREATE TRIGGER refuse_insert BEFORE INSERT ON education_materials BEGIN SELECT RAISE(ABORT, 'disco indisponível'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        store.create_lesson_plan(LessonPlanCreate(title="Não gravar"))
    assert store.list_lesson_plans() == []
    assert EducationStore(db_path).counts()["lesson_plans"] == 0


def test_failed_update_rolls_back_and_preserves_review(db_path):
    store = EducationStore(db_path)
    plan = store.create_lesson_plan(LessonPlanCreate(title="Revisado pelo professor"))
    with pytest.raises(ValidationError):
        store.update_lesson_plan(plan.id, LessonPlanUpdate(title=None))
    assert EducationStore(db_path).get_lesson_plan(plan.id) == plan


def test_real_process_restart(db_path):
    code = """
import json, sys
from src.education.services import EducationStore
from src.education.schemas import LessonPlanCreate
store = EducationStore(sys.argv[1])
store.create_lesson_plan(LessonPlanCreate(title='Material entre processos'))
print(json.dumps(store.counts()))
"""
    result = subprocess.run(
        [sys.executable, "-c", code, db_path],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["lesson_plans"] == 1
    assert EducationStore(db_path).list_lesson_plans()[0].title == "Material entre processos"


@pytest.mark.parametrize("prefix", ["sqlite:///", "sqlite+aiosqlite:///"])
def test_singleton_uses_configured_database(monkeypatch, db_path, prefix):
    from src.core.config import unified_settings

    monkeypatch.setattr(unified_settings, "education_db_url", prefix + db_path)
    monkeypatch.setattr(services, "_store", None)
    plan = services.get_store().create_lesson_plan(LessonPlanCreate(title="Configurado"))
    monkeypatch.setattr(services, "_store", None)
    assert services.get_store().get_lesson_plan(plan.id).title == "Configurado"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://localhost/education",
        "sqlite:///",
        "sqlite:///education.db?mode=ro",
    ],
)
def test_invalid_configuration_does_not_fall_back_to_memory(monkeypatch, url):
    from src.core.config import unified_settings

    monkeypatch.setattr(unified_settings, "education_db_url", url)
    monkeypatch.setattr(services, "_store", None)
    with pytest.raises(ValueError):
        services.get_store()
    assert services._store is None


def test_explicit_memory_mode(monkeypatch):
    from src.core.config import unified_settings

    monkeypatch.setattr(unified_settings, "education_db_url", "sqlite:///:memory:")
    monkeypatch.setattr(services, "_store", None)
    services.get_store().create_lesson_plan(LessonPlanCreate(title="Temporário"))
    monkeypatch.setattr(services, "_store", None)
    assert services.get_store().list_lesson_plans() == []


def test_http_crud_restart_counts_and_validation(monkeypatch, db_path):
    from pydantic import SecretStr

    from ai.settings import settings

    monkeypatch.setattr(settings, "api_token", SecretStr("test-token"))
    app = FastAPI()
    app.include_router(router)
    headers = {"X-API-Key": "test-token"}
    monkeypatch.setattr(services, "_store", EducationStore(db_path))
    with TestClient(app) as client:
        assert client.get("/api/v2/education/health").status_code == 401
        result = client.post(
            "/api/v2/education/lesson-plans", json={"title": "Revisão"}, headers=headers
        )
        assert result.status_code == 201
        plan_id = result.json()["lesson_plan"]["id"]
        url = "/api/v2/education/lesson-plans/" + plan_id
        assert client.patch(url, json={"title": "Revisado"}, headers=headers).status_code == 200
        assert client.patch(url, json={"title": None}, headers=headers).status_code == 422
        monkeypatch.setattr(services, "_store", EducationStore(db_path))
        assert client.get(url, headers=headers).json()["lesson_plan"]["title"] == "Revisado"
        health = client.get("/api/v2/education/health", headers=headers).json()
        assert health["stats"]["lesson_plans"] == 1
        assert health["stats"]["bncc_skills"] == len(services.list_bncc_skills())
        assert client.delete(url, headers=headers).status_code == 200
        monkeypatch.setattr(services, "_store", EducationStore(db_path))
        assert client.get(url, headers=headers).status_code == 404
