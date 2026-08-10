"""Configurações centralizadas do IA-Lab Enterprise.

Carrega variáveis de ambiente com prefixo IA_LAB_ e
disponibiliza um singleton `settings` para toda a aplicação.

Melhorias aplicadas:
- ``SecretStr`` para todas as API keys (proteção contra vazamento em logs/exceções)
- ``Literal`` para provedores (validação em tempo de carregamento)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Tipos reutilizáveis ───────────────────────────────────────────

ProviderName = Literal[
    "openai", "claude", "gemini", "groq", "glm", "perplexity", "ollama", "bitnet"
]


class Settings(BaseSettings):
    """Configurações da aplicação, carregadas de env vars / .env."""

    model_config = SettingsConfigDict(
        env_prefix="IA_LAB_",  # ex: IA_LAB_OPENAI_API_KEY
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Provedor primário ---
    primary_provider: ProviderName = "openai"
    local_provider: ProviderName = "ollama"

    # --- GLM (Zhipu) ---
    glm_api_key: SecretStr = SecretStr("")
    glm_model: str = "glm-4-plus"
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"

    # --- Ollama (sem API key — autenticação local) ---
    ollama_model: str = "qwen2.5:7b"
    ollama_base_url: str = "http://localhost:11434"

    # --- OpenAI ---
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o"
    openai_base_url: str = "https://api.openai.com/v1"

    # --- Claude (Anthropic) ---
    claude_api_key: SecretStr = SecretStr("")
    claude_model: str = "claude-sonnet-4-20250514"
    claude_base_url: str = "https://api.anthropic.com/v1"

    # --- Gemini ---
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # --- Groq ---
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # --- Perplexity ---
    perplexity_api_key: SecretStr = SecretStr("")
    perplexity_model: str = "sonar-pro"
    perplexity_base_url: str = "https://api.perplexity.ai"

    # --- Freebuff / local ---
    freebuff_api_key: SecretStr = SecretStr("")
    freebuff_model: str = "deepseek-v4-flash"

    # --- BitNet (LLM 1-bit local) ---
    bitnet_model: str = "qwen3:8b"
    bitnet_base_url: str = "http://localhost:8080/v1"

    # --- RAG / Qdrant ---
    rag_enabled: bool = True
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "ia-lab-docs"

    # --- Geral ---
    log_level: str = "INFO"
    health_check_timeout: float = 5.0


@lru_cache
def get_settings() -> Settings:
    """Retorna o singleton de configurações."""
    return Settings()


settings = get_settings()
