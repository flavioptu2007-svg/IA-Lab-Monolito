"""Conftest for web/api tests.

The API server lazy-imports the ``ai`` monolith package at request time.
These tests stub ``ai.*`` in sys.modules so the endpoints can be exercised
without the full monolith (LLM clients, Qdrant, Ollama) being available.
"""

import sys
import types
from enum import Enum
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_WEB = Path(__file__).resolve().parents[2]  # ~/Projetos/web
if str(PROJECT_WEB) not in sys.path:
    sys.path.insert(0, str(PROJECT_WEB))


class _StubTaskType(str, Enum):
    CHAT = "chat"
    CODE = "code"
    GENERAL = "general"


def _make_ai_stubs() -> dict[str, types.ModuleType]:
    """Build fake ``ai.*`` modules mirroring the monolith's public surface."""

    # ai.telemetry --------------------------------------------------------
    telemetry = types.ModuleType("ai.telemetry")
    health_status = MagicMock()
    health_status.labels.return_value = MagicMock()
    telemetry.health_status = health_status
    logger = MagicMock()
    telemetry.get_logger = MagicMock(return_value=logger)

    # ai.settings ----------------------------------------------------------
    settings_mod = types.ModuleType("ai.settings")
    settings = types.SimpleNamespace(
        primary_provider="glm",
        local_provider="ollama",
        glm_model="glm-4.7",
        glm_api_key="test-key",
        ollama_model="llama3",
        ollama_base_url="http://127.0.0.1:11434",
        openai_model="gpt-4o",
        openai_api_key="",
        claude_model="claude-sonnet",
        claude_api_key="",
        gemini_model="gemini-pro",
        gemini_api_key="",
        groq_model="llama-3",
        groq_api_key="",
        perplexity_model="sonar",
        perplexity_api_key="",
        rag_enabled=False,
        qdrant_host="localhost",
        qdrant_port=6333,
        log_level="INFO",
        health_check_timeout=1,
    )
    settings_mod.settings = settings

    # ai.memory.store -------------------------------------------------------
    memory_store = types.ModuleType("ai.memory.store")

    class VectorStore:
        def is_available(self) -> bool:
            return True

    memory_store.VectorStore = VectorStore

    # ai.service ------------------------------------------------------------
    service_mod = types.ModuleType("ai.service")

    class AIService:
        async def complete(self, **kwargs):
            return "resposta stub da IA"

        def choose_provider(self, provider=None):
            return "stub-provider"

    service_mod.AIService = AIService

    # ai.providers.base -------------------------------------------------------
    providers_base = types.ModuleType("ai.providers.base")
    providers_base.TaskType = _StubTaskType

    # ai.classifier -------------------------------------------------------------
    classifier = types.ModuleType("ai.classifier")

    class TaskClassifier:
        @staticmethod
        def classify(prompt: str) -> _StubTaskType:
            return _StubTaskType.CHAT

    classifier.TaskClassifier = TaskClassifier

    # ai.agents.base ---------------------------------------------------------
    agents_base = types.ModuleType("ai.agents.base")

    class _StubAgent:
        name = "studiopedia"
        task_type = _StubTaskType.CHAT
        default_provider = "glm"

        async def run(self, prompt, provider=None, use_rag=True):
            return f"agente stub: {prompt}"

    class _StubRegistry:
        def list_names(self):
            return ["studiopedia"]

        def create(self, name):
            if name != "studiopedia":
                raise KeyError(f"agente desconhecido: {name}")
            return _StubAgent()

    agents_base.get_agent_registry = MagicMock(return_value=_StubRegistry())

    # package root -----------------------------------------------------------
    ai_pkg = types.ModuleType("ai")
    ai_pkg.__path__ = []  # namespace-like package

    return {
        "ai": ai_pkg,
        "ai.telemetry": telemetry,
        "ai.settings": settings_mod,
        "ai.memory.store": memory_store,
        "ai.service": service_mod,
        "ai.providers.base": providers_base,
        "ai.classifier": classifier,
        "ai.agents.base": agents_base,
    }


@pytest.fixture
def ai_stubs(monkeypatch):
    """Inject the ``ai.*`` stubs into sys.modules for the duration of a test."""
    stubs = _make_ai_stubs()
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)
    return stubs


@pytest.fixture
def client(ai_stubs):
    from api.server import app

    return __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(app)
