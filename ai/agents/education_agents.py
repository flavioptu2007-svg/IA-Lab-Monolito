"""Agentes locais de educação: skills empacotadas, sem fallback pago."""

from __future__ import annotations

from importlib.resources import files

from ai.agents.base import BaseAgent
from ai.providers.base import TaskType
from ai.providers.ollama import OllamaProvider


def read_skill(name: str) -> str:
    if name not in {"education-planning", "professional-presentations", "education-review"}:
        raise ValueError("Skill desconhecida")
    return files("ai.agents").joinpath("skills", name, "SKILL.md").read_text(encoding="utf-8")


class EducationPlannerAgent(BaseAgent):
    name = "education_planner"
    description = "Planeja sequências pedagógicas com IA local"
    default_provider = "ollama"
    task_type = TaskType.planning
    skill = "education-planning"

    async def run(self, prompt: str, provider: str | None = None, use_rag: bool = False) -> str:
        if provider not in (None, "ollama"):
            raise ValueError("Este agente gratuito aceita somente Ollama local")
        return await OllamaProvider().complete(
            prompt=prompt, system_prompt=read_skill(self.skill), temperature=0.4, max_tokens=4096
        )


class PresentationDesignerAgent(EducationPlannerAgent):
    name = "presentation_designer"
    description = "Estrutura slides profissionais e notas para o apresentador"
    task_type = TaskType.creative
    skill = "professional-presentations"


class EducationReviewerAgent(EducationPlannerAgent):
    name = "education_reviewer"
    description = "Aponta pendências pedagógicas sem substituir a revisão docente"
    task_type = TaskType.analysis
    skill = "education-review"
