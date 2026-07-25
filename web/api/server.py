"""Backend FastAPI para o painel web do IA-Lab Enterprise.

Fornece endpoints REST para:
- Chat com IA (roteamento inteligente)
- Agentes especializados
- Histórico de conversas (em memória)
- Métricas do Prometheus
- Health check
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="IA-Lab Enterprise API",
    version="0.1.0",
    description="API do painel de controle do IA-Lab Enterprise",
)

# CORS para desenvolvimento (React em localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Dependências internas (lazy import para evitar circular no startup) ----


def get_service():
    from ai.service import AIService

    return AIService()


def get_agent_registry():
    from ai.agents.base import get_agent_registry

    return get_agent_registry()


def get_settings():
    from ai.settings import settings

    return settings


# ---- Modelos Pydantic ----


class ChatRequest(BaseModel):
    prompt: str
    provider: str | None = None
    task_type: str | None = None
    use_rag: bool = True
    agent: str | None = None


class ChatResponse(BaseModel):
    response: str
    provider: str
    task_type: str
    latency_ms: int


class AgentInfo(BaseModel):
    name: str
    task_type: str
    default_provider: str


class HistoryEntry(BaseModel):
    id: str
    prompt: str
    response: str
    provider: str
    task_type: str
    timestamp: float
    agent: str | None = None


# ---- Armazenamento em memória (histórico, substituir por banco futuro) ----


class HistoryStore:
    def __init__(self):
        self._entries: list[HistoryEntry] = []
        self._counter = 0

    def add(self, entry: HistoryEntry) -> None:
        self._entries.append(entry)
        self._counter += 1

    def list(self, limit: int = 50) -> list[HistoryEntry]:
        return list(reversed(self._entries))[:limit]

    def clear(self) -> None:
        self._entries.clear()
        self._counter = 0


history_store = HistoryStore()

# ---- Rotas da API ----


@app.get("/api/health")
async def health():
    """Health check completo do sistema."""
    from ai.memory.store import VectorStore
    from ai.telemetry import health_status as hs

    checks: dict[str, str] = {}

    # Qdrant
    try:
        store = VectorStore()
        qdrant_ok = store.is_available()
        checks["qdrant"] = "ok" if qdrant_ok else "error"
        hs.labels(component="qdrant").set(1 if qdrant_ok else 0)
    except Exception:
        checks["qdrant"] = "error"
        hs.labels(component="qdrant").set(0)

    # Ollama (via health check do settings)
    import httpx

    try:
        cfg = get_settings()
        resp = httpx.get(f"{cfg.ollama_base_url}/api/tags", timeout=cfg.health_check_timeout)
        ollama_ok = resp.status_code == 200
        checks["ollama"] = "ok" if ollama_ok else "error"
        hs.labels(component="ollama").set(1 if ollama_ok else 0)
    except Exception:
        checks["ollama"] = "error"
        hs.labels(component="ollama").set(0)

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks, "version": "0.1.0"}


@app.get("/api/providers")
async def list_providers():
    """Lista providers disponíveis com seus status."""
    cfg = get_settings()
    providers = [
        {
            "name": "glm",
            "model": cfg.glm_model,
            "configured": bool(cfg.glm_api_key),
            "task": "code",
        },
        {"name": "ollama", "model": cfg.ollama_model, "configured": True, "task": "local"},
        {"name": "freebuff", "model": cfg.ollama_model, "configured": True, "task": "refactor"},
        {
            "name": "openai",
            "model": cfg.openai_model,
            "configured": bool(cfg.openai_api_key),
            "task": "general",
        },
        {
            "name": "claude",
            "model": cfg.claude_model,
            "configured": bool(cfg.claude_api_key),
            "task": "general",
        },
        {
            "name": "gemini",
            "model": cfg.gemini_model,
            "configured": bool(cfg.gemini_api_key),
            "task": "architecture",
        },
        {
            "name": "groq",
            "model": cfg.groq_model,
            "configured": bool(cfg.groq_api_key),
            "task": "general",
        },
        {
            "name": "perplexity",
            "model": cfg.perplexity_model,
            "configured": bool(cfg.perplexity_api_key),
            "task": "general",
        },
    ]
    return {"providers": providers}


@app.get("/api/agents")
async def list_agents():
    """Lista agentes especializados disponíveis."""
    registry = get_agent_registry()
    agents = []
    for name in registry.list_names():
        agent = registry.create(name)
        agents.append(
            {
                "name": agent.name,
                "task_type": agent.task_type.value,
                "default_provider": agent.default_provider,
                "description": (
                    f"Agente especializado em {agent.task_type.value}. "
                    f"Provider padrão: {agent.default_provider}"
                ),
            }
        )
    return {"agents": agents}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Envia uma mensagem para a IA com roteamento inteligente."""
    from ai.providers.base import TaskType
    import asyncio

    service = get_service()
    start = time.monotonic()

    try:
        # Se um agente foi especificado, usa ele em vez do chat direto
        if request.agent:
            registry = get_agent_registry()
            try:
                agent = registry.create(request.agent)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc))

            response_text = await agent.run(
                request.prompt, provider=request.provider, use_rag=request.use_rag
            )
            task_type = agent.task_type.value
            provider = request.provider or agent.default_provider or "auto"
        else:
            # TaskType a partir da string
            task_type_enum = None
            if request.task_type:
                try:
                    task_type_enum = TaskType(request.task_type)
                except ValueError:
                    task_type_enum = request.task_type

            response_text = await service.complete(
                prompt=request.prompt,
                provider=request.provider,
                task_type=task_type_enum,
                use_rag=request.use_rag,
            )

            # Extrai o provider real usado e task_type da service
            final_task = task_type_enum
            if final_task is None:
                from ai.classifier import TaskClassifier

                final_task = TaskClassifier.classify(request.prompt)
            task_type = getattr(final_task, "value", str(final_task))
            provider = request.provider or service.choose_provider(request.provider)

        latency = int((time.monotonic() - start) * 1000)

        # Histórico
        entry = HistoryEntry(
            id=str(time.time_ns()),
            prompt=request.prompt,
            response=response_text,
            provider=provider,
            task_type=task_type,
            timestamp=time.time(),
            agent=request.agent,
        )
        history_store.add(entry)

        return ChatResponse(
            response=response_text, provider=provider, task_type=task_type, latency_ms=latency
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/history")
async def get_history(limit: int = 50):
    """Retorna o histórico de conversas."""
    entries = history_store.list(limit=limit)
    return {"history": [e.model_dump() for e in entries]}


@app.delete("/api/history")
async def clear_history():
    """Limpa o histórico de conversas."""
    history_store.clear()
    return {"status": "ok"}


@app.get("/api/metrics")
async def get_metrics():
    """Retorna um snapshot das métricas Prometheus."""
    from prometheus_client.registry import REGISTRY
    from prometheus_client.openmetrics import exposition as openmetrics

    # Coleta amostras das métricas mais importantes
    samples = {}
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            key = sample.name
            labels = dict(sample.labels)
            if key not in samples:
                samples[key] = []
            samples[key].append({"labels": labels, "value": sample.value})

    return {"metrics": samples}


@app.get("/api/config")
async def get_config():
    """Retorna a configuração atual do sistema (sem secrets)."""
    cfg = get_settings()
    return {
        "primary_provider": cfg.primary_provider,
        "local_provider": cfg.local_provider,
        "providers": {
            "glm": {"model": cfg.glm_model, "configured": bool(cfg.glm_api_key)},
            "ollama": {"model": cfg.ollama_model, "configured": True},
            "openai": {"model": cfg.openai_model, "configured": bool(cfg.openai_api_key)},
            "claude": {"model": cfg.claude_model, "configured": bool(cfg.claude_api_key)},
            "gemini": {"model": cfg.gemini_model, "configured": bool(cfg.gemini_api_key)},
            "groq": {"model": cfg.groq_model, "configured": bool(cfg.groq_api_key)},
            "perplexity": {
                "model": cfg.perplexity_model,
                "configured": bool(cfg.perplexity_api_key),
            },
        },
        "rag_enabled": cfg.rag_enabled,
        "qdrant_host": cfg.qdrant_host,
        "qdrant_port": cfg.qdrant_port,
        "log_level": cfg.log_level,
    }


# ---- Startup ----


@app.on_event("startup")
async def startup():
    from ai.telemetry import get_logger

    logger = get_logger("web.api")
    logger.info("API IA-Lab Enterprise iniciada")


# ---- Ponto de entrada ----


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("web.api.server:app", host="0.0.0.0", port=port, reload=True)
