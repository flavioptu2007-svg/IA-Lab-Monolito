"""Configuração centralizada do monolito FastAPI unificado.

Re-exporta as settings existentes de ``ai.settings`` para
compatibilidade retroativa e adiciona novas seções para
os módulos migrados (HistóriaIA, OpenVINO, BitNet, Coraci).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from ai.settings import settings as legacy_settings  # noqa: F401 — re-export


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

    # ── Coraci Chat ────────────────────────────────────────────
    coraci_db_path: str = "coraci.db"
    coraci_max_history: int = 100

    # ── HistóriaIA ─────────────────────────────────────────────
    education_db_url: str = "sqlite+aiosqlite:///education.db"
    education_redis_url: str = "redis://localhost:6379/0"
    education_jwt_secret: SecretStr = SecretStr("change-me-in-production")
    education_jwt_algorithm: str = "HS256"

    # ── OpenVINO ───────────────────────────────────────────────
    openvino_enabled: bool = False
    openvino_model_path: str = "models/openvino"
    openvino_device: Literal["CPU", "GPU", "NPU"] = "CPU"

    # ── BitNet ─────────────────────────────────────────────────
    bitnet_enabled: bool = False
    bitnet_url: str = "http://localhost:8080"
    bitnet_model: str = "qwen3:8b"


@lru_cache
def get_unified_settings() -> UnifiedSettings:
    """Retorna o singleton de configurações unificadas."""
    return UnifiedSettings()


unified_settings = get_unified_settings()
