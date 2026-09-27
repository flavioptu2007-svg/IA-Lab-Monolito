"""Configuração centralizada do monolito FastAPI unificado.

Re-exporta as settings existentes de ``ai.settings`` para
compatibilidade retroativa e adiciona novas seções para
os módulos migrados (HistóriaIA, OpenVINO, BitNet, Coraci).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ai.settings import settings as legacy_settings  # noqa: F401 — re-export

logger = logging.getLogger(__name__)

# Valor default inseguro — nunca pode chegar à produção.
_INSECURE_JWT_DEFAULT = "change-me-in-production"


class UnifiedSettings(BaseSettings):
    """Settings unificadas — estende as configurações do IA-Lab
    com seções para Educação, OpenVINO e BitNet."""

    model_config = SettingsConfigDict(
        env_prefix="IA_LAB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Ambiente ───────────────────────────────────────────────
    # "production" endurece validações (falha no boot com segredo default).
    environment: Literal["development", "production", "test"] = "development"

    # ── Coraci Chat ────────────────────────────────────────────
    coraci_db_path: str = "coraci.db"
    coraci_max_history: int = 100

    # ── HistóriaIA ─────────────────────────────────────────────
    education_db_url: str = "sqlite+aiosqlite:///education.db"
    education_redis_url: str = "redis://localhost:6379/0"
    education_jwt_secret: SecretStr = SecretStr(_INSECURE_JWT_DEFAULT)
    education_jwt_algorithm: str = "HS256"

    # ── OpenVINO ───────────────────────────────────────────────
    openvino_enabled: bool = False
    openvino_model_path: str = "models/openvino"
    openvino_device: Literal["CPU", "GPU", "NPU"] = "CPU"

    # ── BitNet ─────────────────────────────────────────────────
    bitnet_enabled: bool = False
    bitnet_url: str = "http://localhost:8080"
    bitnet_model: str = "qwen3:8b"

    @model_validator(mode="after")
    def _validate_jwt_secret(self) -> UnifiedSettings:
        """Bloqueia o boot em produção com o segredo JWT default.

        - environment="production": levanta erro — o app não sobe com o
          segredo de exemplo, que é público e permitiria forjar tokens.
        - environment="development": apenas loga um warning (dev local).
        - environment="test": silencioso (suítes de teste usam o default).
        """
        if self.education_jwt_secret.get_secret_value() == _INSECURE_JWT_DEFAULT:
            if self.environment == "production":
                raise ValueError(
                    "IA_LAB_EDUCATION_JWT_SECRET não pode manter o valor padrão "
                    f"'{_INSECURE_JWT_DEFAULT}' com IA_LAB_ENVIRONMENT=production. "
                    "Defina um segredo forte (ex.: `openssl rand -hex 32`) antes "
                    "de subir a aplicação."
                )
            if self.environment == "development":
                logger.warning(
                    "IA_LAB_EDUCATION_JWT_SECRET está com o valor padrão inseguro "
                    "'%s' — configure um segredo forte antes de ir para produção.",
                    _INSECURE_JWT_DEFAULT,
                )
        return self


@lru_cache
def get_unified_settings() -> UnifiedSettings:
    """Retorna o singleton de configurações unificadas."""
    return UnifiedSettings()


unified_settings = get_unified_settings()
