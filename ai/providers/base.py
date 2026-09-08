"""Classes base e enumerações para provedores de IA."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum


class TaskType(StrEnum):
    """Tipos de tarefa suportados pelo classificador."""

    code = "code"
    general = "general"
    refactor = "refactor"
    architecture = "architecture"
    local = "local"
    planning = "planning"
    analysis = "analysis"
    creative = "creative"
    rag = "rag"


class BaseProvider(ABC):
    """Classe base para todos os provedores de IA."""

    name: str = ""
    model: str = ""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Envia um prompt completo para o modelo e retorna a resposta."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Verifica se o provedor está acessível no momento."""
        ...


def get_default_provider_for_task(task_type: TaskType) -> str:
    """Retorna o provedor padrão recomendado para um tipo de tarefa."""
    mapping: dict[TaskType, str] = {
        TaskType.code: "glm",
        TaskType.general: "openai",
        TaskType.refactor: "freebuff",
        TaskType.architecture: "gemini",
        TaskType.local: "ollama",
        TaskType.planning: "claude",
        TaskType.analysis: "groq",
        TaskType.creative: "perplexity",
        TaskType.rag: "openai",
    }
    return mapping.get(task_type, "openai")
