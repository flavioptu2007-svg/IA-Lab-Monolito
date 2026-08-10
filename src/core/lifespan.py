"""Lifespan — Context manager de startup/shutdown para o monolito.

Substitui os decoradores ``@app.on_event(\"startup\")`` e
``@router.on_event(\"startup\")`` que são deprecated no FastAPI.

Recursos gerenciados no shutdown:
- VectorStore / Qdrant (fecha socket gRPC/REST)
- Coraci Chat SQLite (checkpoint WAL)
- AudioEngine (libera dispositivos PulseAudio/PipeWire, se inicializado)
- Cache / sessões em memória

Uso:
    from src.core.lifespan import lifespan
    app = FastAPI(lifespan=lifespan)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Gerencia o ciclo de vida da aplicação FastAPI.

    Startup (antes do ``yield``):
        - Inicializa o banco SQLite do chat Coraci
        - Carrega conversas e configurações salvas
        - Loga inicialização

    Shutdown (depois do ``yield``):
        - Fecha VectorStore / conexão Qdrant
        - Fecha SQLite Coraci (checkpoint WAL)
        - Fecha AudioEngine (se inicializado)
        - Limpa in-memory stores
    """
    # ═══════════════════════════════════════════════════════════════
    #  Startup
    # ═══════════════════════════════════════════════════════════════

    # ── Coraci Chat: init DB + load data ─────────────────────────
    try:
        from src.api.v2.chat_coraci import (
            _config,
            _conversations,
            db_load_all,
            init_db,
            load_config,
        )

        init_db()
        saved = db_load_all()
        if saved:
            _conversations.update(saved)
        _config.update(load_config())
        logger.info("Coraci chat: DB initialized, %d conversations loaded", len(saved))
    except Exception as exc:
        logger.warning("Coraci chat startup error: %s", exc)

    # ── App log ──────────────────────────────────────────────────
    logger.info("IA-Lab Unified API iniciada")

    yield  # ── Aplicação rodando ─────────────────────────────────

    # ═══════════════════════════════════════════════════════════════
    #  Shutdown — libera todos os recursos
    # ═══════════════════════════════════════════════════════════════

    shutdown_ok = True

    # 1. VectorStore / Qdrant
    try:
        from ai.memory.store import VectorStore

        vs = VectorStore()
        vs.close()
        logger.info("VectorStore: conexão Qdrant fechada")
    except Exception as exc:
        logger.warning("VectorStore: erro no shutdown: %s", exc)
        shutdown_ok = False

    # 2. Coraci Chat SQLite (checkpoint WAL)
    try:
        from src.api.v2.chat_coraci import close_db

        close_db()
        logger.info("Coraci DB: checkpoint WAL executado")
    except Exception as exc:
        logger.warning("Coraci DB: erro no shutdown: %s", exc)
        shutdown_ok = False

    # 3. AudioEngine (libera dispositivos se inicializado)
    try:
        from ai.audio import AudioEngine

        if hasattr(AudioEngine, "_instance") and AudioEngine._instance is not None:
            engine = AudioEngine()
            if hasattr(engine, "close"):
                engine.close()
                logger.info("AudioEngine: recursos liberados")
    except ImportError:
        pass  # ai.audio pode não ter dependências instaladas
    except Exception as exc:
        logger.warning("AudioEngine: erro no shutdown: %s", exc)

    # 4. AIService — limpa cache de providers
    try:
        from ai.service import AIService

        service = AIService()
        if hasattr(service, "close"):
            service.close()
            logger.info("AIService: recursos liberados")
    except Exception as exc:
        logger.warning("AIService: erro no shutdown: %s", exc)

    if shutdown_ok:
        logger.info("IA-Lab Unified API encerrada — todos os recursos liberados")
    else:
        logger.warning(
            "IA-Lab Unified API encerrada — alguns recursos podem não ter sido liberados"
        )
