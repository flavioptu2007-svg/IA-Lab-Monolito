"""Testes de ``src/core/config.py`` — defaults, ambiente e guarda do segredo JWT.

Cobre (Achado 21 e quick win 11 da auditoria):

- todos os defaults de :class:`UnifiedSettings`;
- override por variável de ambiente com prefixo ``IA_LAB_`` (case-insensitive);
- carregamento de um arquivo ``.env`` explícito e a prioridade do ambiente;
- ``extra="ignore"`` para variáveis desconhecidas;
- ``SecretStr``: o segredo não aparece em ``str()``/``repr()``;
- a guarda ``_validate_jwt_secret``: falha o boot em produção com o valor
  padrão, apenas registra aviso em desenvolvimento e é silenciosa em teste;
- valores inválidos em campos ``Literal``;
- o singleton ``unified_settings`` / ``get_unified_settings`` (``lru_cache``);
- o re-export de ``ai.settings.settings``.

Nota: os testes constroem ``UnifiedSettings(_env_file=None)`` para não depender
do ``.env`` local (que é gitignored e não existe no CI).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

from ai.settings import settings as legacy_settings
from src.core import config as config_module
from src.core.config import UnifiedSettings, get_unified_settings

# Valor default inseguro (constante do módulo) e um segredo forte só de teste.
INSECURE_JWT_DEFAULT = config_module._INSECURE_JWT_DEFAULT
STRONG_JWT_SECRET = "segredo-de-teste-7f3a9c1b8d2e4f60"

#: Defaults declarados em ``UnifiedSettings`` (nenhum vindo do ambiente).
DEFAULTS: dict[str, Any] = {
    "environment": "development",
    "coraci_db_path": "coraci.db",
    "coraci_max_history": 100,
    "education_db_url": "sqlite+aiosqlite:///education.db",
    "education_redis_url": "redis://localhost:6379/0",
    "education_jwt_algorithm": "HS256",
    "openvino_enabled": False,
    "openvino_model_path": "models/openvino",
    "openvino_device": "CPU",
    "bitnet_enabled": False,
    "bitnet_url": "http://localhost:8080",
    "bitnet_model": "qwen3:8b",
}


@pytest.fixture(autouse=True)
def _sem_variaveis_ia_lab(monkeypatch: pytest.MonkeyPatch) -> None:
    """Limpa ``IA_LAB_*`` do processo: defaults puros, sem depender do shell."""
    for chave in [key for key in os.environ if key.upper().startswith("IA_LAB_")]:
        monkeypatch.delenv(chave, raising=False)


def make_settings(**overrides: Any) -> UnifiedSettings:
    """Instancia as settings ignorando o ``.env`` do diretório atual."""
    return UnifiedSettings(_env_file=None, **overrides)


# ═════════════════════════════════════════════════════════════════════════════
# Defaults
# ═════════════════════════════════════════════════════════════════════════════


class TestDefaults:
    """Sem ambiente nem ``.env``, todo campo cai no valor declarado."""

    @pytest.mark.parametrize(("campo", "esperado"), sorted(DEFAULTS.items()))
    def test_default(self, campo: str, esperado: Any):
        assert getattr(make_settings(), campo) == esperado

    def test_segredo_jwt_default_e_secret_str_insegura(self):
        settings = make_settings()
        assert isinstance(settings.education_jwt_secret, SecretStr)
        assert settings.education_jwt_secret.get_secret_value() == INSECURE_JWT_DEFAULT

    def test_config_de_env_prefixo_arquivo_e_extras(self):
        assert UnifiedSettings.model_config["env_prefix"] == "IA_LAB_"
        assert UnifiedSettings.model_config["env_file"] == ".env"
        assert UnifiedSettings.model_config["extra"] == "ignore"
        assert UnifiedSettings.model_config["case_sensitive"] is False


# ═════════════════════════════════════════════════════════════════════════════
# Override por ambiente / arquivo .env
# ═════════════════════════════════════════════════════════════════════════════


class TestOverridePorAmbiente:
    """Variáveis ``IA_LAB_*`` sobrescrevem os defaults, sem exigir prefixo exato."""

    def test_device_do_openvino(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("IA_LAB_OPENVINO_DEVICE", "GPU")
        assert make_settings().openvino_device == "GPU"

    def test_nomes_case_insensitive_e_coercao_de_tipos(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ia_lab_bitnet_enabled", "true")
        monkeypatch.setenv("ia_lab_coraci_max_history", "7")
        settings = make_settings()
        assert settings.bitnet_enabled is True
        assert settings.coraci_max_history == 7

    def test_environment_por_variavel(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("IA_LAB_ENVIRONMENT", "production")
        monkeypatch.setenv("IA_LAB_EDUCATION_JWT_SECRET", STRONG_JWT_SECRET)
        assert make_settings().environment == "production"

    def test_variavel_desconhecida_e_ignorada(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("IA_LAB_NAO_EXISTE_NO_MODELO", "1")
        make_settings()  # extra="ignore" → não levanta

    def test_env_file_explicito(self, tmp_path):
        arquivo = tmp_path / ".env"
        arquivo.write_text(
            "IA_LAB_CORACI_DB_PATH=/tmp/coraci-teste.db\nIA_LAB_BITNET_ENABLED=true\n",
            encoding="utf-8",
        )
        settings = UnifiedSettings(_env_file=arquivo)
        assert settings.coraci_db_path == "/tmp/coraci-teste.db"
        assert settings.bitnet_enabled is True

    def test_ambiente_vence_o_env_file(self, tmp_path, monkeypatch: pytest.MonkeyPatch):
        arquivo = tmp_path / ".env"
        arquivo.write_text("IA_LAB_BITNET_MODEL=modelo-do-arquivo\n", encoding="utf-8")
        monkeypatch.setenv("IA_LAB_BITNET_MODEL", "modelo-do-ambiente")
        assert UnifiedSettings(_env_file=arquivo).bitnet_model == "modelo-do-ambiente"


# ═════════════════════════════════════════════════════════════════════════════
# Guarda do segredo JWT (_validate_jwt_secret)
# ═════════════════════════════════════════════════════════════════════════════


class TestValidacaoDoSegredoJwt:
    """Produção com o segredo de exemplo não sobe; desenvolvimento só avisa."""

    def test_producao_com_default_no_ambiente_falha(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("IA_LAB_ENVIRONMENT", "production")
        monkeypatch.setenv("IA_LAB_EDUCATION_JWT_SECRET", INSECURE_JWT_DEFAULT)
        with pytest.raises(ValueError, match="IA_LAB_EDUCATION_JWT_SECRET"):
            make_settings()

    def test_producao_com_default_explicito_falha(self):
        with pytest.raises(ValueError, match="IA_LAB_EDUCATION_JWT_SECRET"):
            make_settings(environment="production", education_jwt_secret=INSECURE_JWT_DEFAULT)

    def test_producao_com_segredo_forte_sobe(self):
        settings = make_settings(environment="production", education_jwt_secret=STRONG_JWT_SECRET)
        assert settings.environment == "production"
        assert settings.education_jwt_secret.get_secret_value() == STRONG_JWT_SECRET

    def test_producao_bloqueia_apenas_o_default_exato(self):
        """A guarda é um piso: qualquer outro valor passa (não mede força)."""
        assert (
            make_settings(
                environment="production", education_jwt_secret="outro-valor"
            ).education_jwt_secret.get_secret_value()
            == "outro-valor"
        )

    def test_desenvolvimento_com_default_apenas_avisa(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.WARNING, logger="src.core.config"):
            settings = make_settings(environment="development")
        assert settings.environment == "development"
        avisos = [r for r in caplog.records if r.name == "src.core.config"]
        assert len(avisos) == 1
        assert avisos[0].levelno == logging.WARNING
        assert INSECURE_JWT_DEFAULT in avisos[0].getMessage()

    def test_desenvolvimento_com_segredo_forte_nao_avisa(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.WARNING, logger="src.core.config"):
            make_settings(environment="development", education_jwt_secret=STRONG_JWT_SECRET)
        assert [r for r in caplog.records if r.name == "src.core.config"] == []

    def test_ambiente_de_teste_e_silencioso(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.WARNING, logger="src.core.config"):
            settings = make_settings(environment="test")
        assert settings.environment == "test"
        assert [r for r in caplog.records if r.name == "src.core.config"] == []


# ═════════════════════════════════════════════════════════════════════════════
# Segredos e valores inválidos
# ═════════════════════════════════════════════════════════════════════════════


class TestSegredoNaoVaza:
    """``SecretStr`` protege o valor em logs, ``repr`` e serialização."""

    def test_str_e_repr_nao_expoem_o_valor(self):
        settings = make_settings(environment="production", education_jwt_secret=STRONG_JWT_SECRET)
        assert STRONG_JWT_SECRET not in str(settings.education_jwt_secret)
        assert STRONG_JWT_SECRET not in repr(settings.education_jwt_secret)
        assert STRONG_JWT_SECRET not in repr(settings)
        assert settings.education_jwt_secret.get_secret_value() == STRONG_JWT_SECRET


class TestValoresInvalidos:
    """Campos ``Literal`` recusam qualquer valor fora da lista."""

    def test_environment_invalido(self):
        with pytest.raises(ValidationError):
            make_settings(environment="staging")

    def test_openvino_device_invalido(self):
        with pytest.raises(ValidationError):
            make_settings(openvino_device="TPU")


# ═════════════════════════════════════════════════════════════════════════════
# Singleton e re-export
# ═════════════════════════════════════════════════════════════════════════════


class TestSingleton:
    """``get_unified_settings`` é ``lru_cache``: uma instância por processo."""

    def test_modulo_expoe_uma_instancia(self):
        assert isinstance(config_module.unified_settings, UnifiedSettings)

    def test_get_unified_settings_usa_cache(self):
        get_unified_settings.cache_clear()
        try:
            assert get_unified_settings() is get_unified_settings()
        finally:
            get_unified_settings.cache_clear()

    def test_cache_clear_reconstroi(self):
        get_unified_settings.cache_clear()
        try:
            primeiro = get_unified_settings()
            get_unified_settings.cache_clear()
            assert get_unified_settings() is not primeiro
        finally:
            get_unified_settings.cache_clear()


class TestReexport:
    """O módulo re-exporta as settings legadas de ``ai.settings``."""

    def test_legacy_settings_e_o_objeto_de_ai_settings(self):
        assert config_module.legacy_settings is legacy_settings
