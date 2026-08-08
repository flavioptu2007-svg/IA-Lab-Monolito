"""Serviços educacionais — Planos de aula, atividades, avaliações, BNCC.

Armazenamento em memória com SQLite opcional via UnifiedSettings.
Adaptado do projeto HistóriaIA (AI/historiaia/).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from src.education.enums import BNCC_SKILLS
from src.education.schemas import (
    ActivityCreate,
    ActivityResponse,
    ActivityUpdate,
    BNCCSkillSchema,
    CalendarEventCreate,
    CalendarEventResponse,
    EvaluationCreate,
    EvaluationResponse,
    EvaluationUpdate,
    LessonPlanCreate,
    LessonPlanResponse,
    LessonPlanUpdate,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Agora em UTC como datetime naive (equivalente ao removido ``utcnow()``)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ═══════════════════════════════════════════════════════════════
# Store em memória (compatível com o monolito)
# ═══════════════════════════════════════════════════════════════


class EducationStore:
    """Armazenamento em memória para entidades educacionais.

    Futuramente pode ser substituído por SQLAlchemy + PostgreSQL
    quando o módulo HistóriaIA completo for integrado.
    """

    def __init__(self) -> None:
        self._lesson_plans: dict[str, LessonPlanResponse] = {}
        self._activities: dict[str, ActivityResponse] = {}
        self._evaluations: dict[str, EvaluationResponse] = {}
        self._calendar_events: dict[str, CalendarEventResponse] = {}

    # ── Planos de Aula ──────────────────────────────────────────

    def create_lesson_plan(self, data: LessonPlanCreate) -> LessonPlanResponse:
        plan_id = str(uuid.uuid4())
        now = _utcnow()
        plan = LessonPlanResponse(id=plan_id, created_at=now, updated_at=now, **data.model_dump())
        self._lesson_plans[plan_id] = plan
        return plan

    def get_lesson_plan(self, plan_id: str) -> LessonPlanResponse | None:
        return self._lesson_plans.get(plan_id)

    def list_lesson_plans(
        self,
        academic_year: str | None = None,
        subject: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LessonPlanResponse]:
        plans = list(self._lesson_plans.values())
        if academic_year:
            plans = [p for p in plans if p.academic_year == academic_year]
        if subject:
            plans = [p for p in plans if p.subject == subject]
        plans.sort(key=lambda p: p.updated_at or datetime.min, reverse=True)
        return plans[offset : offset + limit]

    def update_lesson_plan(self, plan_id: str, data: LessonPlanUpdate) -> LessonPlanResponse | None:
        plan = self._lesson_plans.get(plan_id)
        if plan is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(plan, key, value)
        plan.updated_at = _utcnow()
        return plan

    def delete_lesson_plan(self, plan_id: str) -> bool:
        return self._lesson_plans.pop(plan_id, None) is not None

    # ── Atividades ──────────────────────────────────────────────

    def create_activity(self, data: ActivityCreate) -> ActivityResponse:
        act_id = str(uuid.uuid4())
        now = _utcnow()
        activity = ActivityResponse(id=act_id, created_at=now, updated_at=now, **data.model_dump())
        self._activities[act_id] = activity
        return activity

    def get_activity(self, activity_id: str) -> ActivityResponse | None:
        return self._activities.get(activity_id)

    def list_activities(
        self,
        academic_year: str | None = None,
        activity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityResponse]:
        activities = list(self._activities.values())
        if academic_year:
            activities = [a for a in activities if a.academic_year == academic_year]
        if activity_type:
            activities = [a for a in activities if a.activity_type == activity_type]
        activities.sort(key=lambda a: a.updated_at or datetime.min, reverse=True)
        return activities[offset : offset + limit]

    def update_activity(self, activity_id: str, data: ActivityUpdate) -> ActivityResponse | None:
        activity = self._activities.get(activity_id)
        if activity is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(activity, key, value)
        activity.updated_at = _utcnow()
        return activity

    def delete_activity(self, activity_id: str) -> bool:
        return self._activities.pop(activity_id, None) is not None

    # ── Avaliações ──────────────────────────────────────────────

    def create_evaluation(self, data: EvaluationCreate) -> EvaluationResponse:
        eval_id = str(uuid.uuid4())
        now = _utcnow()
        evaluation = EvaluationResponse(
            id=eval_id, created_at=now, updated_at=now, **data.model_dump()
        )
        self._evaluations[eval_id] = evaluation
        return evaluation

    def get_evaluation(self, evaluation_id: str) -> EvaluationResponse | None:
        return self._evaluations.get(evaluation_id)

    def list_evaluations(
        self,
        academic_year: str | None = None,
        evaluation_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EvaluationResponse]:
        evaluations = list(self._evaluations.values())
        if academic_year:
            evaluations = [e for e in evaluations if e.academic_year == academic_year]
        if evaluation_type:
            evaluations = [e for e in evaluations if e.evaluation_type == evaluation_type]
        evaluations.sort(key=lambda e: e.updated_at or datetime.min, reverse=True)
        return evaluations[offset : offset + limit]

    def update_evaluation(
        self, evaluation_id: str, data: EvaluationUpdate
    ) -> EvaluationResponse | None:
        evaluation = self._evaluations.get(evaluation_id)
        if evaluation is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(evaluation, key, value)
        evaluation.updated_at = _utcnow()
        return evaluation

    def delete_evaluation(self, evaluation_id: str) -> bool:
        return self._evaluations.pop(evaluation_id, None) is not None

    # ── Calendário ──────────────────────────────────────────────

    def create_event(self, data: CalendarEventCreate) -> CalendarEventResponse:
        event_id = str(uuid.uuid4())
        now = _utcnow()
        raw = data.model_dump()
        # Converte date para string ISO (CalendarEventResponse espera str)
        if "event_date" in raw and hasattr(raw["event_date"], "isoformat"):
            raw["event_date"] = raw["event_date"].isoformat()
        event = CalendarEventResponse(id=event_id, created_at=now, updated_at=now, **raw)
        self._calendar_events[event_id] = event
        return event

    def list_events(
        self,
        academic_year: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CalendarEventResponse]:
        events = list(self._calendar_events.values())
        if academic_year:
            events = [e for e in events if e.academic_year == academic_year]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        events.sort(key=lambda e: e.event_date or "", reverse=False)
        return events[offset : offset + limit]

    def delete_event(self, event_id: str) -> bool:
        return self._calendar_events.pop(event_id, None) is not None


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
        _store = EducationStore()
    return _store
