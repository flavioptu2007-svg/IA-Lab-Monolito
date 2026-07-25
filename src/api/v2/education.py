"""Endpoints Education — API REST para recursos educacionais.

Todas as rotas são prefixadas com ``/api/v2/education``.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.education.schemas import (
    ActivityCreate,
    ActivityUpdate,
    CalendarEventCreate,
    EvaluationCreate,
    EvaluationUpdate,
    LessonPlanCreate,
    LessonPlanUpdate,
)
from src.education.services import get_bncc_competences, get_store, list_bncc_skills

router = APIRouter(prefix="/api/v2/education", tags=["education"])


# ═══════════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════════


@router.get("/health")
async def education_health():
    """Health check do módulo educacional."""
    store = get_store()
    return {
        "status": "ok",
        "module": "education",
        "version": "1.0.0",
        "stats": {
            "lesson_plans": len(store._lesson_plans),
            "activities": len(store._activities),
            "evaluations": len(store._evaluations),
            "events": len(store._calendar_events),
            "bncc_skills": 30,  # Habilidades BNCC cadastradas
        },
    }


# ═══════════════════════════════════════════════════════════════
# BNCC — Base Nacional Comum Curricular
# ═══════════════════════════════════════════════════════════════


@router.get("/bncc/skills")
async def bncc_list_skills(
    year: str | None = Query(None, description="Ano/série (ex: EF_6)"),
    competence: str | None = Query(None, description="Competência (ex: CE01)"),
    query: str | None = Query(None, description="Busca textual"),
):
    """Lista habilidades BNCC com filtros opcionais."""
    skills = list_bncc_skills(year=year, competence=competence, query=query)
    return {"status": "ok", "total": len(skills), "skills": [s.model_dump() for s in skills]}


@router.get("/bncc/competences")
async def bncc_list_competences():
    """Lista competências específicas de História (BNCC)."""
    competences = get_bncc_competences()
    return {"status": "ok", "total": len(competences), "competences": competences}


# ═══════════════════════════════════════════════════════════════
# Planos de Aula — CRUD
# ═══════════════════════════════════════════════════════════════


@router.post("/lesson-plans", status_code=201)
async def create_lesson_plan(data: LessonPlanCreate):
    """Cria um novo plano de aula."""
    store = get_store()
    plan = store.create_lesson_plan(data)
    return {"status": "ok", "lesson_plan": plan.model_dump()}


@router.get("/lesson-plans/{plan_id}")
async def get_lesson_plan(plan_id: str):
    """Obtém um plano de aula pelo ID."""
    store = get_store()
    plan = store.get_lesson_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plano de aula não encontrado")
    return {"status": "ok", "lesson_plan": plan.model_dump()}


@router.get("/lesson-plans")
async def list_lesson_plans(
    academic_year: str | None = Query(None, description="Ano/série"),
    subject: str | None = Query(None, description="Disciplina"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lista planos de aula com filtros opcionais."""
    store = get_store()
    plans = store.list_lesson_plans(
        academic_year=academic_year, subject=subject, limit=limit, offset=offset
    )
    return {"status": "ok", "total": len(plans), "lesson_plans": [p.model_dump() for p in plans]}


@router.patch("/lesson-plans/{plan_id}")
async def update_lesson_plan(plan_id: str, data: LessonPlanUpdate):
    """Atualiza parcialmente um plano de aula."""
    store = get_store()
    plan = store.update_lesson_plan(plan_id, data)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plano de aula não encontrado")
    return {"status": "ok", "lesson_plan": plan.model_dump()}


@router.delete("/lesson-plans/{plan_id}")
async def delete_lesson_plan(plan_id: str):
    """Remove um plano de aula."""
    store = get_store()
    if store.delete_lesson_plan(plan_id):
        return {"status": "ok", "deleted": True}
    raise HTTPException(status_code=404, detail="Plano de aula não encontrado")


# ═══════════════════════════════════════════════════════════════
# Atividades — CRUD
# ═══════════════════════════════════════════════════════════════


@router.post("/activities", status_code=201)
async def create_activity(data: ActivityCreate):
    """Cria uma nova atividade didática."""
    store = get_store()
    activity = store.create_activity(data)
    return {"status": "ok", "activity": activity.model_dump()}


@router.get("/activities/{activity_id}")
async def get_activity(activity_id: str):
    """Obtém uma atividade pelo ID."""
    store = get_store()
    activity = store.get_activity(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return {"status": "ok", "activity": activity.model_dump()}


@router.get("/activities")
async def list_activities(
    academic_year: str | None = Query(None, description="Ano/série"),
    activity_type: str | None = Query(None, description="Tipo de atividade"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lista atividades com filtros opcionais."""
    store = get_store()
    activities = store.list_activities(
        academic_year=academic_year, activity_type=activity_type, limit=limit, offset=offset
    )
    return {
        "status": "ok",
        "total": len(activities),
        "activities": [a.model_dump() for a in activities],
    }


@router.patch("/activities/{activity_id}")
async def update_activity(activity_id: str, data: ActivityUpdate):
    """Atualiza parcialmente uma atividade."""
    store = get_store()
    activity = store.update_activity(activity_id, data)
    if activity is None:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return {"status": "ok", "activity": activity.model_dump()}


@router.delete("/activities/{activity_id}")
async def delete_activity(activity_id: str):
    """Remove uma atividade."""
    store = get_store()
    if store.delete_activity(activity_id):
        return {"status": "ok", "deleted": True}
    raise HTTPException(status_code=404, detail="Atividade não encontrada")


# ═══════════════════════════════════════════════════════════════
# Avaliações — CRUD
# ═══════════════════════════════════════════════════════════════


@router.post("/evaluations", status_code=201)
async def create_evaluation(data: EvaluationCreate):
    """Cria uma nova avaliação."""
    store = get_store()
    evaluation = store.create_evaluation(data)
    return {"status": "ok", "evaluation": evaluation.model_dump()}


@router.get("/evaluations/{evaluation_id}")
async def get_evaluation(evaluation_id: str):
    """Obtém uma avaliação pelo ID."""
    store = get_store()
    evaluation = store.get_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    return {"status": "ok", "evaluation": evaluation.model_dump()}


@router.get("/evaluations")
async def list_evaluations(
    academic_year: str | None = Query(None, description="Ano/série"),
    evaluation_type: str | None = Query(None, description="Tipo de avaliação"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lista avaliações com filtros opcionais."""
    store = get_store()
    evaluations = store.list_evaluations(
        academic_year=academic_year, evaluation_type=evaluation_type, limit=limit, offset=offset
    )
    return {
        "status": "ok",
        "total": len(evaluations),
        "evaluations": [e.model_dump() for e in evaluations],
    }


@router.patch("/evaluations/{evaluation_id}")
async def update_evaluation(evaluation_id: str, data: EvaluationUpdate):
    """Atualiza parcialmente uma avaliação."""
    store = get_store()
    evaluation = store.update_evaluation(evaluation_id, data)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    return {"status": "ok", "evaluation": evaluation.model_dump()}


@router.delete("/evaluations/{evaluation_id}")
async def delete_evaluation(evaluation_id: str):
    """Remove uma avaliação."""
    store = get_store()
    if store.delete_evaluation(evaluation_id):
        return {"status": "ok", "deleted": True}
    raise HTTPException(status_code=404, detail="Avaliação não encontrada")


# ═══════════════════════════════════════════════════════════════
# Calendário Letivo
# ═══════════════════════════════════════════════════════════════


@router.post("/calendar", status_code=201)
async def create_calendar_event(data: CalendarEventCreate):
    """Cria um evento no calendário letivo."""
    store = get_store()
    event = store.create_event(data)
    return {"status": "ok", "event": event.model_dump()}


@router.get("/calendar")
async def list_calendar_events(
    academic_year: str | None = Query(None, description="Ano/série"),
    event_type: str | None = Query(None, description="Tipo de evento"),
    limit: int = Query(100, ge=1, le=365),
    offset: int = Query(0, ge=0),
):
    """Lista eventos do calendário letivo."""
    store = get_store()
    events = store.list_events(
        academic_year=academic_year, event_type=event_type, limit=limit, offset=offset
    )
    return {"status": "ok", "total": len(events), "events": [e.model_dump() for e in events]}


@router.delete("/calendar/{event_id}")
async def delete_calendar_event(event_id: str):
    """Remove um evento do calendário."""
    store = get_store()
    if store.delete_event(event_id):
        return {"status": "ok", "deleted": True}
    raise HTTPException(status_code=404, detail="Evento não encontrado")
