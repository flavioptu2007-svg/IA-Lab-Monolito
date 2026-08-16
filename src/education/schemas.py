"""Schemas educacionais — Modelos Pydantic para planos, atividades, avaliações.

Define as estruturas de dados usadas nas APIs educacionais,
adaptadas do projeto HistóriaIA (AI/historiaia/).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════
# Base
# ═══════════════════════════════════════════════════════════════


class EducationBase(BaseModel):
    """Campos comuns a todas as entidades educacionais."""

    id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════
# BNCC — Base Nacional Comum Curricular
# ═══════════════════════════════════════════════════════════════


class BNCCSkillSchema(BaseModel):
    """Habilidade BNCC."""

    code: str = Field(..., description="Código da habilidade (ex: EF06HI01)")
    description: str = Field("", description="Descrição da habilidade")
    competence_area: str = Field(default="História", description="Área de competência")
    academic_year: str = Field("", description="Ano/série")
    object_knowledge: str = Field("", description="Objeto de conhecimento")


class BNCCFilterParams(BaseModel):
    """Parâmetros de filtro para consulta BNCC."""

    year: str | None = Field(None, description="Ano/série (ex: EF_6)")
    competence: str | None = Field(None, description="Competência (ex: CE01)")
    query: str | None = Field(None, description="Busca textual")


# ═══════════════════════════════════════════════════════════════
# Plano de Aula
# ═══════════════════════════════════════════════════════════════


class LessonMomentContent(BaseModel):
    """Conteúdo de um momento pedagógico."""

    moment: str = Field("INTRODUÇÃO", description="Tipo do momento")
    title: str = Field("", description="Título do momento")
    description: str = Field("", description="Descrição detalhada")
    duration_minutes: int = Field(15, ge=1, description="Duração em minutos")
    methodology: str = Field("", description="Metodologia/estratégia")
    resources: list[str] = Field(default_factory=list, description="Recursos necessários")
    order: int = Field(0, ge=0, description="Ordem do momento")


class LessonPlanCreate(BaseModel):
    """Schema para criação de plano de aula."""

    title: str = Field(..., min_length=1, max_length=200, description="Título do plano")
    topic: str = Field("", description="Tópico/conteúdo")
    academic_year: str = Field("EF_8", description="Ano/série")
    trimester: str = Field("T1", description="Trimestre")
    subject: str = Field("História", description="Disciplina")
    learning_objectives: list[str] = Field(
        default_factory=list, description="Objetivos de aprendizagem"
    )
    bncc_skills: list[str] = Field(default_factory=list, description="Códigos BNCC")
    resources: list[str] = Field(default_factory=list, description="Recursos/materiais")
    assessment_type: str = Field("", description="Tipo de avaliação")
    duration_minutes: int = Field(50, ge=1, description="Duração total em minutos")
    moments: list[LessonMomentContent] = Field(
        default_factory=list, description="Momentos pedagógicos"
    )


class LessonPlanResponse(EducationBase):
    """Schema de resposta para plano de aula."""

    title: str = ""
    topic: str = ""
    academic_year: str = ""
    trimester: str = ""
    subject: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    bncc_skills: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    assessment_type: str = ""
    duration_minutes: int = 50
    status: str = "rascunho"
    moments: list[LessonMomentContent] = Field(default_factory=list)
    is_ai_generated: bool = False


class LessonPlanUpdate(BaseModel):
    """Schema para atualização parcial de plano de aula."""

    title: str | None = None
    topic: str | None = None
    academic_year: str | None = None
    trimester: str | None = None
    learning_objectives: list[str] | None = None
    bncc_skills: list[str] | None = None
    resources: list[str] | None = None
    assessment_type: str | None = None
    duration_minutes: int | None = None
    status: str | None = None
    moments: list[LessonMomentContent] | None = None


# ═══════════════════════════════════════════════════════════════
# Atividade
# ═══════════════════════════════════════════════════════════════


class ActivityCreate(BaseModel):
    """Schema para criação de atividade didática."""

    title: str = Field(..., min_length=1, max_length=200, description="Título da atividade")
    activity_type: str = Field("FLASHCARD", description="Tipo de atividade")
    description: str = Field("", description="Descrição")
    content: dict[str, Any] = Field(default_factory=dict, description="Conteúdo estruturado (JSON)")
    difficulty: str = Field("MÉDIO", description="Dificuldade")
    duration_minutes: int = Field(20, ge=1, description="Duração em minutos")
    academic_year: str = Field("EF_8", description="Ano/série")
    subject: str = Field("História", description="Disciplina")
    bncc_skills: list[str] = Field(default_factory=list, description="Códigos BNCC")
    instructions: str = Field("", description="Instruções para o professor")


class ActivityResponse(EducationBase):
    """Schema de resposta para atividade."""

    title: str = ""
    activity_type: str = ""
    description: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
    difficulty: str = ""
    duration_minutes: int = 20
    academic_year: str = ""
    subject: str = ""
    bncc_skills: list[str] = Field(default_factory=list)
    instructions: str = ""
    is_ai_generated: bool = False


class ActivityUpdate(BaseModel):
    """Schema para atualização parcial de atividade."""

    title: str | None = None
    activity_type: str | None = None
    description: str | None = None
    content: dict[str, Any] | None = None
    difficulty: str | None = None
    duration_minutes: int | None = None
    bncc_skills: list[str] | None = None
    instructions: str | None = None


# ═══════════════════════════════════════════════════════════════
# Avaliação
# ═══════════════════════════════════════════════════════════════


class QuestionSchema(BaseModel):
    """Questão de uma avaliação."""

    number: int = Field(0, ge=0, description="Número da questão")
    type: str = Field("OBJETIVA", description="Tipo (OBJETIVA, DISCURSIVA, etc)")
    command: str = Field("", description="Enunciado/comando")
    options: list[str] = Field(default_factory=list, description="Alternativas (para objetivas)")
    correct_answer: str = Field("", description="Resposta correta")
    score: float = Field(1.0, ge=0, description="Valor da questão")
    skill_code: str = Field("", description="Habilidade BNCC associada")
    feedback: str = Field("", description="Feedback/Gabarito comentado")


class EvaluationCreate(BaseModel):
    """Schema para criação de avaliação."""

    title: str = Field(..., min_length=1, max_length=200, description="Título da avaliação")
    evaluation_type: str = Field("EXAM", description="Tipo de avaliação")
    description: str = Field("", description="Descrição")
    academic_year: str = Field("EF_8", description="Ano/série")
    trimester: str = Field("T1", description="Trimestre")
    subject: str = Field("História", description="Disciplina")
    bncc_skills: list[str] = Field(default_factory=list, description="Códigos BNCC")
    total_score: float = Field(10.0, ge=0, description="Pontuação total")
    passing_score: float = Field(6.0, ge=0, description="Nota para aprovação")
    duration_minutes: int = Field(50, ge=1, description="Duração em minutos")
    instructions: str = Field("", description="Instruções gerais")
    questions: list[QuestionSchema] = Field(default_factory=list, description="Questões")


class EvaluationResponse(EducationBase):
    """Schema de resposta para avaliação."""

    title: str = ""
    evaluation_type: str = ""
    description: str = ""
    academic_year: str = ""
    trimester: str = ""
    subject: str = ""
    bncc_skills: list[str] = Field(default_factory=list)
    total_score: float = 10.0
    passing_score: float = 6.0
    duration_minutes: int = 50
    status: str = "rascunho"
    instructions: str = ""
    questions: list[QuestionSchema] = Field(default_factory=list)
    is_ai_generated: bool = False


class EvaluationUpdate(BaseModel):
    """Schema para atualização parcial de avaliação."""

    title: str | None = None
    evaluation_type: str | None = None
    description: str | None = None
    bncc_skills: list[str] | None = None
    total_score: float | None = None
    passing_score: float | None = None
    duration_minutes: int | None = None
    status: str | None = None
    instructions: str | None = None
    questions: list[QuestionSchema] | None = None


# ═══════════════════════════════════════════════════════════════
# Agendamento / Calendário
# ═══════════════════════════════════════════════════════════════


class CalendarEventCreate(BaseModel):
    """Schema para criação de evento no calendário letivo."""

    title: str = Field(..., min_length=1, description="Título do evento")
    description: str = Field("", description="Descrição")
    event_date: date = Field(..., description="Data do evento")
    event_type: str = Field("AULA", description="Tipo (AULA, PROVA, FERIADO, etc)")
    academic_year: str = Field("EF_8", description="Ano/série")
    subject: str = Field("História", description="Disciplina")
    duration_minutes: int = Field(50, ge=1, description="Duração em minutos")
    lesson_plan_id: str | None = Field(None, description="ID do plano de aula associado")


class CalendarEventResponse(EducationBase):
    """Schema de resposta para evento de calendário."""

    title: str = ""
    description: str = ""
    event_date: str = ""
    event_type: str = ""
    academic_year: str = ""
    subject: str = ""
    duration_minutes: int = 50
    lesson_plan_id: str | None = None


# ═══════════════════════════════════════════════════════════════
# Escola
# ═══════════════════════════════════════════════════════════════


class SchoolSchema(BaseModel):
    """Schema para escola."""

    id: str = ""
    name: str = Field("", max_length=200, description="Nome da escola")
    short_name: str = Field("", max_length=50, description="Nome reduzido")
    cnpj: str = Field("", description="CNPJ")
    address: str = Field("", description="Endereço")
    city: str = Field("", description="Cidade")
    state: str = Field("", description="Estado (UF)")
    phone: str = Field("", description="Telefone")
    email: str = Field("", description="Email")
    is_active: bool = True
