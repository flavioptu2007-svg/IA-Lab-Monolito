"""Fluxo de geração, revisão e aprovação dos materiais pelo professor."""

from __future__ import annotations

from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from src.core.security import require_api_key
from src.education.generation import (
    GenerationRequest,
    InvalidGeneration,
    MaterialType,
    ReviewRequest,
    generate_material,
    validate_material,
    validate_request,
)
from src.education.persistence import MaterialConflictError
from src.education.services import get_store

router = APIRouter(
    prefix="/api/v2/education",
    tags=["education"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/generate", status_code=201)
async def generate(request: GenerationRequest):
    try:
        validate_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        content = await generate_material(request)
    except InvalidGeneration as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (httpx.HTTPError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível gerar com a IA local. Verifique se o Ollama está ativo e o modelo instalado. Nenhum rascunho foi criado.",
        ) from exc
    material = await run_in_threadpool(
        lambda: get_store().create_generated_material(request.material_type, content)
    )
    return {
        "status": "ok",
        "material_type": request.material_type,
        "material": material.model_dump(),
    }


@router.get("/materials")
def list_materials(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    materials = get_store().list_materials(limit=limit, offset=offset)
    return {"status": "ok", "materials": materials}


@router.post("/materials/{kind}/{material_id}/review")
def review(kind: MaterialType, material_id: str, request: ReviewRequest):
    try:
        material = validate_material(kind, request.content)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="Revise os campos do material: " + str(exc)
        ) from exc
    try:
        saved = get_store().review_material(
            kind, material_id, material.model_dump(), request.expected_updated_at, request.approve
        )
    except MaterialConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    return {"status": "ok", "material_type": kind, "material": saved.model_dump()}


@router.get("/tools")
def education_tools():
    from ai.agents.education_agents import read_skill
    from src.education.presentation_plugins import available_plugins

    return {
        "plugins": available_plugins(),
        "agents": [
            {"id": "education_planner", "name": "Planejamento pedagógico", "provider": "ollama"},
            {
                "id": "presentation_designer",
                "name": "Apresentações profissionais",
                "provider": "ollama",
            },
            {"id": "education_reviewer", "name": "Revisão educacional", "provider": "ollama"},
        ],
        "skills": [
            {"id": name, "content": read_skill(name)}
            for name in ("education-planning", "professional-presentations", "education-review")
        ],
    }


@router.get("/materials/presentation/{material_id}/checks")
def presentation_quality(material_id: str):
    from src.education.presentation_models import presentation_checks

    material = get_store().get_presentation(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Apresentação não encontrada")
    return {"issues": presentation_checks(material), "fact_checked": False}


@router.get("/materials/presentation/{material_id}/export/{file_format}")
def export_presentation(material_id: str, file_format: Literal["html", "pptx"]):
    from fastapi.responses import Response

    from src.education.presentation_plugins import EXPORTERS

    material = get_store().get_presentation(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Apresentação não encontrada")
    exporter, media_type = EXPORTERS[file_format]
    try:
        data = exporter(material)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="apresentacao-{material.id[:8]}.{file_format}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
