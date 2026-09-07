"""Routers centralizados — Importa e expõe todos os routers do monolito.

Uso:
    from src.core.routers import register_routers
    register_routers(app)
"""

from __future__ import annotations

from fastapi import FastAPI

# Módulo LeituraIA Brasil (MVP de compreensão leitora com IA).
# Import opcional: o pacote `leituraia` é um projeto irmão não empacotado neste
# repositório — em CI (checkout limpo) ele não existe, então o monolito sobe
# sem as rotas de leitura em vez de falhar na collection.
try:  # pragma: no cover
    from leituraia.routes import leitor_pages
    from leituraia.routes import router as leituraia_router
except ImportError:  # leituraia ausente (CI/instalação mínima)
    leitor_pages = None  # type: ignore[assignment]
    leituraia_router = None  # type: ignore[assignment]

from src.api.v2.chat_coraci import router as chat_v2_router
from src.api.v2.education import router as education_router
from src.api.v2.openvino import router as openvino_router


def register_routers(app: FastAPI) -> None:
    """Registra todos os routers do monolito na aplicação FastAPI."""
    app.include_router(chat_v2_router)
    app.include_router(openvino_router)
    app.include_router(education_router)
    if leituraia_router is not None:
        app.include_router(leituraia_router)
    if leitor_pages is not None:
        app.include_router(leitor_pages)
