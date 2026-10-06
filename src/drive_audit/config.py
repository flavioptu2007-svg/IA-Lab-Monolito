"""Configuração e constantes da auditoria do Google Drive."""

from __future__ import annotations

import os
from pathlib import Path

REMOTE = "gdrive:"

TIPO_VOCAB: tuple[str, ...] = (
    "Atividade",
    "Plano",
    "Avaliacao",
    "Apostila",
    "Slides",
    "Artigo",
    "Backup",
    "Registro",
    "Material",
    "Outro",
)

# Termos em minúsculas e sem acento; a primeira entrada cujo termo aparecer no
# path ou no nome define o Tipo. Backup primeiro: qualquer coisa dentro de uma
# pasta de backup é classificada como Backup independente do conteúdo.
TIPO_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Backup", ("backup", "backups", "bkp", "dump", "avastcleanup", "restore")),
    (
        "Avaliacao",
        (
            "avaliacao",
            "avaliacoes",
            "prova",
            "provas",
            "teste",
            "testes",
            "exame",
            "exames",
            "simulado",
            "recuperacao",
        ),
    ),
    ("Plano", ("plano", "planos", "planejamento", "sequencia didatica")),
    (
        "Atividade",
        (
            "atividade",
            "atividades",
            "exercicio",
            "exercicios",
            "lista",
            "listas",
            "tarefa",
            "tarefas",
            "caca-palavras",
            "cruzadinha",
            "jogo",
            "jogos",
        ),
    ),
    ("Apostila", ("apostila", "apostilas", "caderno", "modulo")),
    ("Slides", ("slide", "slides", "apresentacao", "apresentacoes", "ppt", "pptx")),
    (
        "Artigo",
        (
            "artigo",
            "artigos",
            "paper",
            "papers",
            "dissertacao",
            "tese",
            "monografia",
            "ensaio",
            "resenha",
        ),
    ),
    (
        "Registro",
        (
            "registro",
            "registros",
            "ata",
            "relatorio",
            "relatorios",
            "diario",
            "frequencia",
            "chamada",
            "parecer",
        ),
    ),
    (
        "Material",
        (
            "material",
            "materiais",
            "recurso",
            "recursos",
            "mapa",
            "imagem",
            "imagens",
            "video",
            "texto",
            "textos",
        ),
    ),
)

FORBIDDEN_CHARS = '#[]{}|<>?*:"/'
MAX_ASSUNTO = 60


def workdir() -> Path:
    """Diretório local dos artefatos (não versionado)."""
    return Path(os.environ.get("DRIVE_AUDIT_DIR", "~/drive-audit")).expanduser()


def ensure_workdir() -> Path:
    """Garante que o workdir e o subdiretório de logs existem."""
    base = workdir()
    (base / "logs").mkdir(parents=True, exist_ok=True)
    return base
