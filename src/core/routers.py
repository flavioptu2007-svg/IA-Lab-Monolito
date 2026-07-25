"""Routers centralizados — Importa e expõe todos os routers do monolito.

Uso:
    from src.core.routers import register_routers
    register_routers(app)
"""

from __future__ import annotations

from fastapi import FastAPI

from src.api.v2.chat_coraci import router as chat_v2_router
from src.api.v2.education import router as education_router
from src.api.v2.openvino import router as openvino_router


def register_routers(app: FastAPI) -> None:
    """Registra todos os routers do monolito na aplicação FastAPI."""
    app.include_router(chat_v2_router)
    app.include_router(openvino_router)
    app.include_router(education_router)
