"""Contrato dos slides e verificações editoriais independentes do modelo de IA."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.education.schemas import EducationBase


class PresentationSlide(BaseModel):
    layout: Literal["title", "content", "comparison", "closing"] = "content"
    title: str = Field(min_length=1, max_length=80)
    subtitle: str = Field(default="", max_length=180)
    bullets: list[str] = Field(default_factory=list, max_length=4)
    speaker_notes: str = Field(default="", max_length=3000)
    sources: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("title")
    @classmethod
    def meaningful_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Informe o título do slide")
        return value.strip()

    @field_validator("bullets", "sources")
    @classmethod
    def concise_text(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 110 for value in values):
            raise ValueError("Tópicos e fontes devem ter entre 1 e 110 caracteres")
        return values


class PresentationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    academic_year: str = "EF_8"
    subject: str = "História"
    duration_minutes: int = Field(default=20, ge=1, le=240)
    bncc_skills: list[str] = Field(default_factory=list)
    theme: Literal["navy", "paper"] = "navy"
    slides: list[PresentationSlide] = Field(min_length=3, max_length=20)


class PresentationResponse(EducationBase, PresentationCreate):
    status: str = "rascunho"
    is_ai_generated: bool = False


def presentation_checks(deck: PresentationCreate) -> list[str]:
    """Achados editoriais; não são verificação de fatos nem aprovação automática."""
    issues = []
    if deck.slides[0].layout != "title":
        issues.append("Considere iniciar com um slide de abertura.")
    if deck.slides[-1].layout != "closing":
        issues.append("Inclua uma síntese ou pergunta de fechamento.")
    if not any(slide.sources for slide in deck.slides):
        issues.append(
            "Não há referências informadas; confira os fatos e registre as fontes utilizadas."
        )
    for number, slide in enumerate(deck.slides, 1):
        if not slide.speaker_notes.strip():
            issues.append(f"Slide {number}: acrescente notas para orientar a apresentação.")
        if not slide.bullets and not slide.subtitle.strip():
            issues.append(f"Slide {number}: inclua conteúdo além do título.")
    return issues
