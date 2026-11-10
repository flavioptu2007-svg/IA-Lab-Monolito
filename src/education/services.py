"""Serviços educacionais — Planos de aula, atividades, avaliações, BNCC.

SQLite configurado via UnifiedSettings; memória para instâncias de teste.
Adaptado do projeto HistóriaIA (AI/historiaia/).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import BaseModel

from src.education.enums import BNCC_SKILLS
from src.education.persistence import SQLiteEducationRepository, check_revision
from src.education.schemas import (
    ActivityCreate,
    ActivityResponse,
    ActivityUpdate,
    BNCCSkillSchema,
    CalendarEventCreate,
    CalendarEventResponse,
    EducationBase,
    EvaluationCreate,
    EvaluationResponse,
    EvaluationUpdate,
    LessonPlanCreate,
    LessonPlanResponse,
    LessonPlanUpdate,
)

logger = logging.getLogger(__name__)
Model = TypeVar("Model", bound=EducationBase)
MATERIAL_MODELS: dict[str, tuple[str, type[EducationBase]]] = {
    "lesson_plan": ("lesson_plans", LessonPlanResponse),
    "activity": ("activities", ActivityResponse),
    "evaluation": ("evaluations", EvaluationResponse),
}


def _utcnow() -> datetime:
    """Agora em UTC como datetime naive (equivalente ao removido ``utcnow()``)."""
    return datetime.now(UTC).replace(tzinfo=None)


# ═══════════════════════════════════════════════════════════════
# Store educacional (SQLite ou memória para testes)
# ═══════════════════════════════════════════════════════════════


class EducationStore:
    """Materiais educacionais; db_path=None mantém o modo em memória para testes."""

    def __init__(self, db_path: str | None = None) -> None:
        self._repository = SQLiteEducationRepository(db_path) if db_path else None
        self._lesson_plans: dict[str, LessonPlanResponse] = {}
        self._activities: dict[str, ActivityResponse] = {}
        self._evaluations: dict[str, EvaluationResponse] = {}
        self._calendar_events: dict[str, CalendarEventResponse] = {}

    def _save(self, collection: str, item: EducationBase) -> None:
        if self._repository is not None:
            self._repository.save(collection, item)
        else:
            getattr(self, "_" + collection)[item.id] = item

    def _get(self, collection: str, item_id: str, model: type[Model]) -> Model | None:
        if self._repository is not None:
            return self._repository.get(collection, item_id, model)
        return getattr(self, "_" + collection).get(item_id)

    def _all(self, collection: str, model: type[Model]) -> list[Model]:
        if self._repository is not None:
            return self._repository.all(collection, model)
        return list(getattr(self, "_" + collection).values())

    def _update(
        self, collection: str, item_id: str, data: BaseModel, model: type[Model]
    ) -> Model | None:
        changes = {**data.model_dump(exclude_unset=True), "updated_at": _utcnow()}
        if data.model_fields_set:
            changes["reviewed_at"] = None
            changes.setdefault("status", "rascunho")
        if self._repository is not None:
            return self._repository.update(collection, item_id, model, changes)
        item = self._get(collection, item_id, model)
        if item is None:
            return None
        updated = model.model_validate({**item.model_dump(), **changes})
        getattr(self, "_" + collection)[item_id] = updated
        return updated

    def _delete(self, collection: str, item_id: str) -> bool:
        if self._repository is not None:
            return self._repository.delete(collection, item_id)
        return getattr(self, "_" + collection).pop(item_id, None) is not None

    def counts(self) -> dict[str, int]:
        """Contagens sem carregar materiais completos nem depender de cache local."""
        counts = (
            self._repository.counts()
            if self._repository is not None
            else {
                name: len(getattr(self, "_" + name))
                for name in (
                    "lesson_plans",
                    "activities",
                    "evaluations",
                    "calendar_events",
                )
            }
        )
        return {
            "lesson_plans": counts.get("lesson_plans", 0),
            "activities": counts.get("activities", 0),
            "evaluations": counts.get("evaluations", 0),
            "events": counts.get("calendar_events", 0),
        }

    def create_generated_material(self, kind: str, content: dict[str, Any]) -> EducationBase:
        """Grava a saída validada da IA como rascunho, nunca como aprovada."""
        collection, model = MATERIAL_MODELS[kind]
        now = _utcnow()
        material = model.model_validate(
            {
                **content,
                "id": str(uuid.uuid4()),
                "created_at": now,
                "updated_at": now,
                "status": "rascunho",
                "is_ai_generated": True,
                "reviewed_at": None,
            }
        )
        self._save(collection, material)
        return material

    def list_materials(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Acervo unificado para reabrir e revisar materiais depois de reiniciar."""
        records: list[dict[str, Any]] = []
        for kind, (collection, model) in MATERIAL_MODELS.items():
            for item in self._all(collection, model):
                records.append({"material_type": kind, "material": item.model_dump()})
        records.sort(key=lambda item: item["material"]["updated_at"] or datetime.min, reverse=True)
        return records[offset : offset + limit]

    def review_material(
        self,
        kind: str,
        material_id: str,
        content: dict[str, Any],
        expected_updated_at: datetime,
        approve: bool,
    ) -> EducationBase | None:
        """Salva a revisão com controle de versão e aprovação explícita."""
        collection, model = MATERIAL_MODELS[kind]
        now = _utcnow()
        changes = {
            **content,
            "status": "aprovado" if approve else "rascunho",
            "reviewed_at": now if approve else None,
            "updated_at": now,
        }
        if self._repository is not None:
            return self._repository.update(
                collection, material_id, model, changes, expected_updated_at
            )
        current = self._get(collection, material_id, model)
        if current is None:
            return None
        check_revision(current, expected_updated_at)
        updated = model.model_validate({**current.model_dump(), **changes})
        getattr(self, "_" + collection)[material_id] = updated
        return updated

    # ── Planos de Aula ──────────────────────────────────────────

    def create_lesson_plan(self, data: LessonPlanCreate) -> LessonPlanResponse:
        plan_id = str(uuid.uuid4())
        now = _utcnow()
        plan = LessonPlanResponse(id=plan_id, created_at=now, updated_at=now, **data.model_dump())
        self._save("lesson_plans", plan)
        return plan

    def get_lesson_plan(self, plan_id: str) -> LessonPlanResponse | None:
        return self._get("lesson_plans", plan_id, LessonPlanResponse)

    def list_lesson_plans(
        self,
        academic_year: str | None = None,
        subject: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LessonPlanResponse]:
        plans = self._all("lesson_plans", LessonPlanResponse)
        if academic_year:
            plans = [p for p in plans if p.academic_year == academic_year]
        if subject:
            plans = [p for p in plans if p.subject == subject]
        plans.sort(key=lambda p: p.updated_at or datetime.min, reverse=True)
        return plans[offset : offset + limit]

    def update_lesson_plan(self, plan_id: str, data: LessonPlanUpdate) -> LessonPlanResponse | None:
        return self._update("lesson_plans", plan_id, data, LessonPlanResponse)

    def delete_lesson_plan(self, plan_id: str) -> bool:
        return self._delete("lesson_plans", plan_id)

    # ── Atividades ──────────────────────────────────────────────

    def create_activity(self, data: ActivityCreate) -> ActivityResponse:
        act_id = str(uuid.uuid4())
        now = _utcnow()
        activity = ActivityResponse(id=act_id, created_at=now, updated_at=now, **data.model_dump())
        self._save("activities", activity)
        return activity

    def get_activity(self, activity_id: str) -> ActivityResponse | None:
        return self._get("activities", activity_id, ActivityResponse)

    def list_activities(
        self,
        academic_year: str | None = None,
        activity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityResponse]:
        activities = self._all("activities", ActivityResponse)
        if academic_year:
            activities = [a for a in activities if a.academic_year == academic_year]
        if activity_type:
            activities = [a for a in activities if a.activity_type == activity_type]
        activities.sort(key=lambda a: a.updated_at or datetime.min, reverse=True)
        return activities[offset : offset + limit]

    def update_activity(self, activity_id: str, data: ActivityUpdate) -> ActivityResponse | None:
        return self._update("activities", activity_id, data, ActivityResponse)

    def delete_activity(self, activity_id: str) -> bool:
        return self._delete("activities", activity_id)

    # ── Avaliações ──────────────────────────────────────────────

    def create_evaluation(self, data: EvaluationCreate) -> EvaluationResponse:
        eval_id = str(uuid.uuid4())
        now = _utcnow()
        evaluation = EvaluationResponse(
            id=eval_id, created_at=now, updated_at=now, **data.model_dump()
        )
        self._save("evaluations", evaluation)
        return evaluation

    def get_evaluation(self, evaluation_id: str) -> EvaluationResponse | None:
        return self._get("evaluations", evaluation_id, EvaluationResponse)

    def list_evaluations(
        self,
        academic_year: str | None = None,
        evaluation_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EvaluationResponse]:
        evaluations = self._all("evaluations", EvaluationResponse)
        if academic_year:
            evaluations = [e for e in evaluations if e.academic_year == academic_year]
        if evaluation_type:
            evaluations = [e for e in evaluations if e.evaluation_type == evaluation_type]
        evaluations.sort(key=lambda e: e.updated_at or datetime.min, reverse=True)
        return evaluations[offset : offset + limit]

    def update_evaluation(
        self, evaluation_id: str, data: EvaluationUpdate
    ) -> EvaluationResponse | None:
        return self._update("evaluations", evaluation_id, data, EvaluationResponse)

    def delete_evaluation(self, evaluation_id: str) -> bool:
        return self._delete("evaluations", evaluation_id)

    # ── Calendário ──────────────────────────────────────────────

    def create_event(self, data: CalendarEventCreate) -> CalendarEventResponse:
        event_id = str(uuid.uuid4())
        now = _utcnow()
        raw = data.model_dump()
        # Converte date para string ISO (CalendarEventResponse espera str)
        if "event_date" in raw and hasattr(raw["event_date"], "isoformat"):
            raw["event_date"] = raw["event_date"].isoformat()
        event = CalendarEventResponse(id=event_id, created_at=now, updated_at=now, **raw)
        self._save("calendar_events", event)
        return event

    def list_events(
        self,
        academic_year: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CalendarEventResponse]:
        events = self._all("calendar_events", CalendarEventResponse)
        if academic_year:
            events = [e for e in events if e.academic_year == academic_year]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        events.sort(key=lambda e: e.event_date or "", reverse=False)
        return events[offset : offset + limit]

    def delete_event(self, event_id: str) -> bool:
        return self._delete("calendar_events", event_id)


# ═══════════════════════════════════════════════════════════════
# Serviço BNCC
# ═══════════════════════════════════════════════════════════════

_SKILLS_BY_YEAR: dict[str, list[str]] = {
    "EF_6": [k for k in BNCC_SKILLS if k.startswith("EF06")],
    "EF_7": [k for k in BNCC_SKILLS if k.startswith("EF07")],
    "EF_8": [k for k in BNCC_SKILLS if k.startswith("EF08")],
    "EF_9": [k for k in BNCC_SKILLS if k.startswith("EF09")],
    "EM": [k for k in BNCC_SKILLS if k.startswith("EM")],
}

_SKILLS_BY_COMPETENCE: dict[str, list[str]] = {
    "CE01": ["EF06HI01", "EF06HI02", "EF07HI01"],
    "CE02": ["EF06HI03", "EF06HI04", "EF07HI02"],
    "CE03": ["EF08HI01", "EF08HI02", "EF09HI01"],
    "CE04": ["EF07HI03", "EF08HI03", "EF09HI02"],
    "CE05": ["EF07HI04", "EF08HI04", "EF09HI03"],
    "CE06": ["EF06HI05", "EF07HI05", "EF09HI04"],
    "CE07": ["EF06HI06", "EF08HI05", "EF09HI05"],
    "CE08": ["EM13CHS101", "EM13CHS201", "EM13CHS501"],
}


def list_bncc_skills(
    year: str | None = None, competence: str | None = None, query: str | None = None
) -> list[BNCCSkillSchema]:
    """Lista habilidades BNCC com filtros opcionais."""
    codes: set[str] = set()

    if year and year in _SKILLS_BY_YEAR:
        codes.update(_SKILLS_BY_YEAR[year])
    elif competence and competence in _SKILLS_BY_COMPETENCE:
        codes.update(_SKILLS_BY_COMPETENCE[competence])
    else:
        codes.update(BNCC_SKILLS.keys())

    results = []
    for code in sorted(codes):
        desc = BNCC_SKILLS.get(code, "")
        if query and query.lower() not in desc.lower() and query.lower() not in code.lower():
            continue

        # Determina ano
        ac_year = ""
        if code.startswith("EF06"):
            ac_year = "EF_6"
        elif code.startswith("EF07"):
            ac_year = "EF_7"
        elif code.startswith("EF08"):
            ac_year = "EF_8"
        elif code.startswith("EF09"):
            ac_year = "EF_9"
        elif code.startswith("EM"):
            ac_year = "EM"

        results.append(
            BNCCSkillSchema(
                code=code,
                description=desc,
                academic_year=ac_year,
                object_knowledge=_get_object_knowledge(code),
            )
        )

    return results


def _get_object_knowledge(code: str) -> str:
    """Mapeia código BNCC para objeto de conhecimento."""
    mapping: dict[str, str] = {
        "EF06HI01": "Diferentes formas de compreensão do tempo",
        "EF06HI02": "Fontes históricas",
        "EF06HI03": "Origem dos seres humanos",
        "EF06HI04": "Origem do homem americano",
        "EF06HI05": "Primeiros grupos humanos",
        "EF06HI06": "Sedentarização",
        "EF07HI01": "Modernidade",
        "EF07HI02": "Conexões Europa/América/África",
        "EF07HI03": "Estados nacionais modernos",
        "EF07HI04": "Expansão marítima",
        "EF07HI05": "Encontro entre europeus e americanos",
        "EF08HI01": "Antigo Regime",
        "EF08HI02": "Revoluções inglesas",
        "EF08HI03": "Revolução Francesa",
        "EF08HI04": "Independência do Brasil",
        "EF08HI05": "Primeiro Reinado",
        "EF09HI01": "Proclamação da República",
        "EF09HI02": "Primeira República",
        "EF09HI03": "Era Vargas",
        "EF09HI04": "Segunda Guerra Mundial",
        "EF09HI05": "Ditadura Militar",
        "EM13CHS101": "Processos políticos contemporâneos",
        "EM13CHS201": "Tecnologia e sociedade",
        "EM13CHS301": "Estado e instituições",
        "EM13CHS401": "Manifestações culturais",
        "EM13CHS501": "Conflitos e desigualdades",
    }
    return mapping.get(code, "")


def get_bncc_competences() -> list[dict[str, Any]]:
    """Retorna lista de competências BNCC."""
    from src.education.enums import BNCCCompetence

    return [
        {
            "code": comp.value.split("=")[0].strip() if "=" in str(comp) else comp.name,
            "name": comp.value,
        }
        for comp in BNCCCompetence
    ]


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_store: EducationStore | None = None


def get_store() -> EducationStore:
    """Retorna o singleton do EducationStore."""
    global _store
    if _store is None:
        from src.core.config import unified_settings

        url = unified_settings.education_db_url
        prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
        prefix = next((value for value in prefixes if url.startswith(value)), None)
        if prefix is None:
            raise ValueError("IA_LAB_EDUCATION_DB_URL deve usar sqlite:/// ou sqlite+aiosqlite:///")
        path = url[len(prefix) :]
        if not path or "?" in path or "#" in path:
            raise ValueError("Configure um caminho SQLite sem parâmetros ou fragmentos")
        _store = EducationStore(None if path == ":memory:" else path)
    return _store
