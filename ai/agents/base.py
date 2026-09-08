"""Agent base e AgentRegistry para agentes especializados."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai.providers.base import TaskType


class BaseAgent(ABC):
    """Classe base para agentes especializados."""

    name: str = ""
    description: str = ""
    task_type: TaskType = TaskType.general
    default_provider: str = "openai"
    system_prompt: str = ""

    @abstractmethod
    async def run(self, prompt: str, provider: str | None = None, use_rag: bool = True) -> str:
        """Executa a tarefa do agente com o prompt fornecido."""
        ...


class AgentRegistry:
    """Registro central de agentes especializados."""

    def __init__(self) -> None:
        self._agents: dict[str, type[BaseAgent]] = {}

    def register(self, agent_cls: type[BaseAgent]) -> None:
        """Registra uma classe de agente no registry."""
        instance = agent_cls()
        self._agents[instance.name] = agent_cls

    def create(self, name: str) -> BaseAgent:
        """Cria uma instância do agente pelo nome."""
        if name not in self._agents:
            available = ", ".join(self._agents.keys())
            raise KeyError(f"Agente '{name}' não encontrado. Disponíveis: [{available}]")
        return self._agents[name]()

    def list_names(self) -> list[str]:
        """Lista todos os nomes de agentes registrados."""
        return list(self._agents.keys())


# ---- Registry global ----
_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Retorna o singleton do AgentRegistry."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
        # Registra agentes built-in
        from ai.agents.architect_agent import ArchitectAgent
        from ai.agents.code_agent import CodeAgent
        from ai.agents.writer_agent import WriterAgent

        _registry.register(CodeAgent)
        _registry.register(ArchitectAgent)
        _registry.register(WriterAgent)
        from ai.agents.audio_agent import AudioAgent

        _registry.register(AudioAgent)
    return _registry
