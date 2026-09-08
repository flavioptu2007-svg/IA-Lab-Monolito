"""Agente especializado em arquitetura de sistemas e design patterns."""

from __future__ import annotations

from ai.agents.base import BaseAgent
from ai.providers.base import TaskType
from ai.service import AIService


class ArchitectAgent(BaseAgent):
    """Agente especializado em arquitetura de software."""

    name = "architect"
    description = "Projeta arquiteturas de software e sistemas distribuídos"
    task_type = TaskType.architecture
    default_provider = "gemini"
    system_prompt = (
        "Você é um arquiteto de software sênior com vasta experiência em "
        "arquiteturas modernas: microsserviços, event-driven, cloud-native, "
        "e sistemas distribuídos. Você projeta soluções escaláveis, resilientes "
        "e de baixo acoplamento. Sempre considere trade-offs, custos operacionais "
        "e requisitos não-funcionais como segurança, performance e disponibilidade. "
        "Use diagramas textuais (Mermaid, ASCII) quando ajudar na visualização."
    )

    async def run(self, prompt: str, provider: str | None = None, use_rag: bool = True) -> str:
        service = AIService()
        full_prompt = f"{self.system_prompt}\n\n## Tarefa de Arquitetura\n\n{prompt}"
        return await service.complete(
            prompt=full_prompt,
            provider=provider or self.default_provider,
            task_type=self.task_type,
            use_rag=use_rag,
        )
