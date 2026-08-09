"""Configuração do módulo LeituraIA Brasil (MVP).

Resolução de chave/endpoint reusa o ambiente da máquina (Z.AI / GLM) e o
padrão de providers do monolito (ai/settings.py). Sem chave disponível, o
gerador cai no modo ``template`` (offline/determinístico) — ideal para
testes e demonstrações.

Variáveis de ambiente:
    LEITURAIA_BASE_URL   endpoint OpenAI-compatível (default: Z.AI coding)
    LEITURAIA_MODEL      modelo (default: glm-4.7)
    LEITURAIA_API_KEY    chave (default: ZAI_API_KEY -> OPENAI_API_KEY)
    LEITURAIA_JWT_SECRET segredo JWT (dev: valor fixo com aviso)
    LEITURAIA_OFFLINE    "1" força o modo template (sem chamada de API)
"""

from __future__ import annotations

import os

# ── Endpoint / modelo ────────────────────────────────────────────────
_BASE_URLS = [
    "LEITURAIA_BASE_URL",
    "ZAI_BASE_URL",
]
_MODELS = [
    "LEITURAIA_MODEL",
    "ZAI_MODEL",
]
_KEYS = [
    "LEITURAIA_API_KEY",
    "ZAI_API_KEY",
    "OPENAI_API_KEY",
    "DASHSCOPE_API_KEY",
]

DEFAULT_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
DEFAULT_MODEL = "glm-4.7"

# ── JWT ──────────────────────────────────────────────────────────────
_DEV_SECRET = "leituraia-dev-secret-nao-use-em-producao"
ACCESS_TOKEN_MIN = 60 * 30          # 30 min
REFRESH_TOKEN_DAYS = 7

_aviso_secreto = False


def get_base_url() -> str:
    for env in _BASE_URLS:
        v = os.environ.get(env, "").strip()
        if v:
            return v
    return DEFAULT_BASE_URL


def get_model() -> str:
    for env in _MODELS:
        v = os.environ.get(env, "").strip()
        if v:
            return v
    return DEFAULT_MODEL


def get_api_key() -> str:
    for env in _KEYS:
        v = os.environ.get(env, "").strip()
        if v:
            return v
    return ""


def is_offline() -> bool:
    """True quando o gerador deve usar apenas o modo template."""
    return os.environ.get("LEITURAIA_OFFLINE", "0") == "1"


def get_jwt_secret() -> str:
    global _aviso_secreto
    secret = os.environ.get("LEITURAIA_JWT_SECRET", "").strip()
    if secret:
        return secret
    if not _aviso_secreto:
        import logging

        logging.getLogger(__name__).warning(
            "LEITURAIA_JWT_SECRET não definida — usando segredo de desenvolvimento."
        )
        _aviso_secreto = True
    return _DEV_SECRET
