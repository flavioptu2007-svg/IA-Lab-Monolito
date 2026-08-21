"""Testes do BitNetProvider — 8º provedor de IA (LLM 1-bit).

Cobre:
- Import e criação do provider
- Configuração via settings (model, base_url)
- complete() com AsyncOpenAI mockado
- is_available() com httpx mockado
- is_available() quando servidor offline
- Integração com AIService (registrado como 8º provider)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ai.providers.bitnet import BitNetProvider

# ═════════════════════════════════════════════════════════════════════════════
# Estrutura e Configuração
# ═════════════════════════════════════════════════════════════════════════════


class TestBitNetProviderStructure:
    """Verifica a estrutura básica do provider."""

    def test_provider_name(self):
        """O nome do provider deve ser 'bitnet'."""
        assert BitNetProvider.name == "bitnet"

    def test_instancia_com_settings_padrao(self):
        """Deve usar settings padrão quando nenhum model é fornecido."""
        with patch("ai.providers.bitnet.settings") as mock_settings:
            mock_settings.bitnet_model = "qwen3:8b"
            mock_settings.bitnet_base_url = "http://localhost:8080/v1"

            provider = BitNetProvider()
            assert provider.model == "qwen3:8b"
            assert provider.base_url == "http://localhost:8080/v1"
            assert provider.api_key == "no-key-required"

    def test_instancia_com_model_personalizado(self):
        """Deve aceitar model personalizado no construtor."""
        provider = BitNetProvider(model="bitnet-b1.58-2B-4T")
        assert provider.model == "bitnet-b1.58-2B-4T"

    def test_url_sem_barra_no_final(self):
        """A URL não deve ter barra no final."""
        with patch("ai.providers.bitnet.settings") as mock_settings:
            mock_settings.bitnet_base_url = "http://localhost:8080/v1/"
            provider = BitNetProvider()
            assert not provider.base_url.endswith("/")


# ═════════════════════════════════════════════════════════════════════════════
# complete
# ═════════════════════════════════════════════════════════════════════════════


class TestBitNetComplete:
    """Testes para BitNetProvider.complete().

    Nota: AsyncOpenAI é importado dentro do método complete() via
    'from openai import AsyncOpenAI'. Por isso o patch é em
    'openai.AsyncOpenAI' e não em 'ai.providers.bitnet.AsyncOpenAI'.
    """

    @pytest.mark.asyncio
    async def test_complete_retorna_resposta(self):
        """Deve retornar a resposta do modelo."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Resposta do BitNet"

        mock_async_client = MagicMock()
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with (
            patch("ai.providers.bitnet.settings") as mock_settings,
            patch("openai.AsyncOpenAI", return_value=mock_async_client),
        ):
            mock_settings.bitnet_model = "qwen3:8b"
            mock_settings.bitnet_base_url = "http://localhost:8080/v1"

            provider = BitNetProvider()
            response = await provider.complete("teste prompt")

            assert response == "Resposta do BitNet"
            mock_async_client.chat.completions.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_com_system_prompt(self):
        """Deve incluir system_prompt na chamada."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "resposta"

        mock_async_client = MagicMock()
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with (
            patch("ai.providers.bitnet.settings") as mock_settings,
            patch("openai.AsyncOpenAI", return_value=mock_async_client),
        ):
            mock_settings.bitnet_model = "qwen3:8b"
            mock_settings.bitnet_base_url = "http://localhost:8080/v1"

            provider = BitNetProvider()
            response = await provider.complete(
                "pergunta", system_prompt="Seja conciso", temperature=0.3, max_tokens=100
            )

            assert response == "resposta"
            mock_async_client.chat.completions.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_retorna_vazio_quando_sem_conteudo(self):
        """Deve retornar string vazia se não houver content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        mock_async_client = MagicMock()
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with (
            patch("ai.providers.bitnet.settings") as mock_settings,
            patch("openai.AsyncOpenAI", return_value=mock_async_client),
        ):
            mock_settings.bitnet_model = "qwen3:8b"
            mock_settings.bitnet_base_url = "http://localhost:8080/v1"

            provider = BitNetProvider()
            response = await provider.complete("teste")
            assert response == ""


# ═════════════════════════════════════════════════════════════════════════════
# is_available
# ═════════════════════════════════════════════════════════════════════════════


class TestBitNetAvailable:
    """Testes para BitNetProvider.is_available()."""

    @pytest.mark.asyncio
    async def test_is_available_quando_online(self):
        """Deve retornar True quando o servidor responde 200."""
        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value.status_code = 200

        with (
            patch("ai.providers.bitnet.settings") as mock_settings,
            patch("ai.providers.bitnet.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.bitnet_base_url = "http://localhost:8080/v1"

            provider = BitNetProvider()
            available = await provider.is_available()
            assert available is True

    @pytest.mark.asyncio
    async def test_is_available_quando_offline(self):
        """Deve retornar False quando o servidor não responde."""
        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("Conexão recusada")
        )

        with (
            patch("ai.providers.bitnet.settings") as mock_settings,
            patch("ai.providers.bitnet.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.bitnet_base_url = "http://localhost:8080/v1"

            provider = BitNetProvider()
            available = await provider.is_available()
            assert available is False

    @pytest.mark.asyncio
    async def test_is_available_quando_nao_200(self):
        """Deve retornar False quando o servidor retorna status != 200."""
        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value.status_code = 503

        with (
            patch("ai.providers.bitnet.settings") as mock_settings,
            patch("ai.providers.bitnet.httpx.AsyncClient", return_value=mock_client),
        ):
            mock_settings.bitnet_base_url = "http://localhost:8080/v1"

            provider = BitNetProvider()
            available = await provider.is_available()
            assert available is False


# ═════════════════════════════════════════════════════════════════════════════
# Integração com AIService
# ═════════════════════════════════════════════════════════════════════════════


class TestBitNetIntegration:
    """Verifica que o BitNet está registrado como 8º provider no AIService."""

    def test_bitnet_registrado_no_aiservice(self):
        """O BitNetProvider deve estar no dicionário _get_providers()."""
        from ai.service import AIService

        service = AIService()
        providers = service._get_providers()
        assert "bitnet" in providers
        assert providers["bitnet"].__name__ == "BitNetProvider"

    def test_aiservice_tem_8_providers(self):
        """O AIService deve ter exatamente 8 provedores registrados."""
        from ai.service import AIService

        service = AIService()
        providers = service._get_providers()
        assert len(providers) == 8
