"""Schemas Pydantic do LeituraIA Brasil (MVP)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from leituraia.rbac import Profile

Nivel = Literal[
    "iniciante", "fundamental1", "fundamental2", "ensino_medio", "eja",
    "tea", "tdah", "dislexia",
]

NIVEL_ROTULO = {
    "iniciante": "Leitor iniciante",
    "fundamental1": "Fundamental I",
    "fundamental2": "Fundamental II",
    "ensino_medio": "Ensino Médio",
    "eja": "EJA",
    "tea": "TEA",
    "tdah": "TDAH",
    "dislexia": "Dislexia",
}

TipoQuestao = Literal[
    "multipla_escolha", "verdadeiro_falso", "dissertativa", "resposta_curta",
    "lacunas", "ordenacao", "associacao", "inferencia", "linha_tempo",
]


# ── Autenticação ─────────────────────────────────────────────────────
class RegistroRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)
    perfil: Profile = Profile.ALUNO


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class UsuarioOut(BaseModel):
    id: str
    nome: str
    email: str
    perfil: Profile


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ── Geração de textos (IA) ───────────────────────────────────────────
class GerarTextoRequest(BaseModel):
    ano: str = Field(min_length=1, max_length=10)
    disciplina: str = Field(min_length=2, max_length=60)
    tema: str = Field(min_length=2, max_length=120)
    bncc: list[str] = Field(default_factory=list)
    crmg: list[str] = Field(default_factory=list)
    palavras: int = Field(default=250, ge=80, le=1500)
    nivel: Nivel = "fundamental2"
    objetivo: str = Field(default="Compreensão leitora", max_length=200)
    idioma: str = Field(default="pt-BR", max_length=20)


class Pergunta(BaseModel):
    pergunta: str
    tipo: TipoQuestao = "multipla_escolha"
    resposta: str


class LinhaTempoItem(BaseModel):
    data: str
    evento: str


class TextoGerado(BaseModel):
    titulo: str
    texto: str
    glossario: list[str] = Field(default_factory=list)
    curiosidades: list[str] = Field(default_factory=list)
    linha_tempo: list[LinhaTempoItem] = Field(default_factory=list)
    perguntas: list[Pergunta] = Field(default_factory=list)
    resumo: str = ""
    referencias: list[str] = Field(default_factory=list)
    origem: Literal["ia", "template"] = "template"
    metadados: dict = Field(default_factory=dict)


# ── Biblioteca ───────────────────────────────────────────────────────
class TextoCreate(BaseModel):
    titulo: str = Field(min_length=2, max_length=200)
    conteudo: str = Field(min_length=30)
    autor: str = "LeituraIA Brasil"
    ano: str
    disciplina: str
    tema: str
    nivel: Nivel = "fundamental2"
    tipo: str = "expositivo"
    genero: str = "artigo didático"
    idioma: str = "pt-BR"
    tags: list[str] = Field(default_factory=list)
    bncc: list[str] = Field(default_factory=list)
    crmg: list[str] = Field(default_factory=list)
    glossario: list[str] = Field(default_factory=list)
    perguntas: list[Pergunta] = Field(default_factory=list)


class TextoOut(BaseModel):
    id: str
    titulo: str
    conteudo: str
    autor: str
    ano: str
    disciplina: str
    tema: str
    nivel: Nivel
    tipo: str
    genero: str
    idioma: str
    tags: list[str]
    bncc: list[str]
    crmg: list[str]
    glossario: list[str]
    perguntas: list[Pergunta]
    palavras: int
    tempo_leitura_min: int


class LeituraRegistro(BaseModel):
    texto_id: str
    tempo_segundos: int = Field(ge=0, le=86400)
    completou: bool = True


class DashboardOut(BaseModel):
    alunos: int
    professores: int
    leituras: int
    textos_biblioteca: int
    habilidades: list[str]
    perfis: dict[str, int]


__all__ = [
    "Nivel",
    "NIVEL_ROTULO",
    "TipoQuestao",
    "RegistroRequest",
    "LoginRequest",
    "UsuarioOut",
    "TokenPair",
    "GerarTextoRequest",
    "Pergunta",
    "LinhaTempoItem",
    "TextoGerado",
    "TextoCreate",
    "TextoOut",
    "LeituraRegistro",
    "DashboardOut",
]
