"""Agente especializado em programação e desenvolvimento de código."""

from __future__ import annotations

from ai.agents.base import BaseAgent
from ai.providers.base import TaskType
from ai.service import AIService


class CodeAgent(BaseAgent):
    """Agente especializado em escrever e revisar código."""

    name = "code"
    description = "Escreve, revisa e refatora código-fonte"
    task_type = TaskType.code
    default_provider = "glm"
    system_prompt = (
        "Você é um engenheiro de software sênior especializado em desenvolvimento de código. "
        "Você escreve código limpo, eficiente e bem documentado. "
        "Sempre explique suas decisões técnicas e forneça exemplos de uso quando relevante. "
        "Priorize boas práticas, padrões de projeto e código testável."
    )

    async def run(self, prompt: str, provider: str | None = None, use_rag: bool = True) -> str:
        service = AIService()
        full_prompt = f"{self.system_prompt}\n\n## Tarefa\n\n{prompt}"
        return await service.complete(
            prompt=full_prompt,
            provider=provider or self.default_provider,
            task_type=self.task_type,
            use_rag=use_rag,
        )
