"""Agente especializado em criação de conteúdo e redação."""

from __future__ import annotations

from ai.agents.base import BaseAgent
from ai.providers.base import TaskType
from ai.service import AIService


class WriterAgent(BaseAgent):
    """Agente especializado em conteúdo criativo e redação."""

    name = "writer"
    description = "Cria conteúdo, artigos, documentação e textos criativos"
    task_type = TaskType.creative
    default_provider = "perplexity"
    system_prompt = (
        "Você é um redator profissional e estrategista de conteúdo. "
        "Você cria textos claros, envolventes e persuasivos adaptados "
        "ao público-alvo e ao formato solicitado. Sua escrita é precisa, "
        "bem estruturada e livre de jargões desnecessários. "
        "Você domina SEO, storytelling técnico e documentação de software."
    )

    async def run(self, prompt: str, provider: str | None = None, use_rag: bool = True) -> str:
        service = AIService()
        full_prompt = f"{self.system_prompt}\n\n## Solicitação de Conteúdo\n\n{prompt}"
        return await service.complete(
            prompt=full_prompt,
            provider=provider or self.default_provider,
            task_type=self.task_type,
            use_rag=use_rag,
        )
