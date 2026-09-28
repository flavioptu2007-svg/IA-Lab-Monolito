"""Testes do AIService — orquestrador de provedores de IA.

Cobre:
- choose_provider: seleção por preferência e fallback para padrão
- complete: sucesso, fallback em erro, RAG, classificação de tarefa
- billing_reason: reconhecimento de falhas de cobrança/cota (402/429)
- get_provider_status: lista de provedores configurados
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ai.service import AIService, billing_reason


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    """Erro HTTP real, como o devolvido por um provedor sem créditos."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        f"Client error '{status_code}' for url 'https://api.openai.com/v1/chat/completions'",
        request=request,
        response=response,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def service() -> AIService:
    """Retorna uma instância limpa do AIService."""
    return AIService()


# ═══════════════════════════════════════════════════════════════════════════
# choose_provider
# ═══════════════════════════════════════════════════════════════════════════


class TestChooseProvider:
    """Testes para AIService.choose_provider()."""

    def test_retorna_provider_preferido_quando_valido(self, service: AIService):
        """Deve retornar o provider preferido se ele existir no registro."""
        with patch.object(
            service, "_get_providers", return_value={"openai": MagicMock(), "ollama": MagicMock()}
        ):
            result = service.choose_provider("ollama")
            assert result == "ollama"

    def test_retorna_primary_quando_preferido_invalido(self, service: AIService):
        """Deve retornar settings.primary_provider se o preferido não existir."""
        with (
            patch.object(service, "_get_providers", return_value={"openai": MagicMock()}),
            patch("ai.service.settings") as mock_settings,
        ):
            mock_settings.primary_provider = "openai"
            result = service.choose_provider("nao_existe")
            assert result == "openai"

    def test_retorna_primary_quando_preferido_none(self, service: AIService):
        """Deve retornar settings.primary_provider se nenhum for preferido."""
        with patch("ai.service.settings") as mock_settings:
            mock_settings.primary_provider = "ollama"
            result = service.choose_provider(None)
            assert result == "ollama"

    def test_retorna_primary_quando_lista_vazia(self, service: AIService):
        """Deve retornar o primary provider mesmo com registro vazio."""
        with (
            patch.object(service, "_get_providers", return_value={}),
            patch("ai.service.settings") as mock_settings,
        ):
            mock_settings.primary_provider = "openai"
            result = service.choose_provider("ollama")
            assert result == "openai"


# ═══════════════════════════════════════════════════════════════════════════
# complete
# ═══════════════════════════════════════════════════════════════════════════


class TestComplete:
    """Testes para AIService.complete()."""

    @pytest.fixture
    def mock_providers_patch(self):
        """Mock dos provedores no nível correto (lazy import dentro do método).

        Os providers são importados dentro de _get_providers() via
        from ai.providers.providers import OpenAIProvider, ...
        from ai.providers.ollama import OllamaProvider
        Por isso precisamos patch os módulos de origem.
        """
        # Cria mocks com complete() async mockado
        openai_mock = MagicMock()
        openai_mock.complete = AsyncMock(return_value="Resposta da OpenAI")

        ollama_mock = MagicMock()
        ollama_mock.complete = AsyncMock(return_value="Resposta da Ollama")

        patches = [
            patch("ai.providers.providers.OpenAIProvider", return_value=openai_mock),
            patch("ai.providers.providers.ClaudeProvider", MagicMock()),
            patch("ai.providers.providers.GeminiProvider", MagicMock()),
            patch("ai.providers.providers.GroqProvider", MagicMock()),
            patch("ai.providers.providers.GLMProvider", MagicMock()),
            patch("ai.providers.providers.PerplexityProvider", MagicMock()),
            patch("ai.providers.ollama.OllamaProvider", return_value=ollama_mock),
        ]

        for p in patches:
            p.start()

        yield {"openai": openai_mock, "ollama": ollama_mock}

        for p in patches:
            p.stop()

    @pytest.mark.asyncio
    async def test_complete_com_provider_especifico(self, service: AIService, mock_providers_patch):
        """Deve usar o provider especificado e retornar resposta."""
        with (
            patch("ai.service.settings") as mock_settings,
            patch("ai.service.get_default_provider_for_task", return_value="openai"),
        ):
            mock_settings.primary_provider = "openai"
            mock_settings.rag_enabled = False

            response = await service.complete("teste", provider="ollama")
            assert response == "Resposta da Ollama"
            mock_providers_patch["ollama"].complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_faz_fallback_em_erro(self, service: AIService, mock_providers_patch):
        """Deve fazer fallback para primary_provider quando o escolhido falhar."""
        mock_providers_patch["ollama"].complete = AsyncMock(
            side_effect=Exception("Falha na Ollama")
        )

        with (
            patch("ai.service.settings") as mock_settings,
            patch("ai.service.get_default_provider_for_task", return_value="openai"),
        ):
            mock_settings.primary_provider = "openai"
            mock_settings.rag_enabled = False

            response = await service.complete("teste", provider="ollama")
            assert response == "Resposta da OpenAI"
            mock_providers_patch["openai"].complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_sem_provider_usa_primary(
        self,
        service: AIService,
        mock_providers_patch,
    ):
        """Deve usar primary_provider quando nenhum provider é especificado."""
        with (
            patch("ai.service.settings") as mock_settings,
            patch("ai.service.get_default_provider_for_task", return_value="openai"),
        ):
            mock_settings.primary_provider = "openai"
            mock_settings.rag_enabled = False

            response = await service.complete("teste")
            assert response == "Resposta da OpenAI"

    @pytest.mark.asyncio
    async def test_complete_inclui_contexto_rag(self, service: AIService, mock_providers_patch):
        """Deve incluir contexto RAG no prompt quando habilitado.

        VectorStore é importado dentro de complete() via
        'from ai.memory.store import VectorStore', então patcheamos
        o módulo de origem.
        """
        mock_store = MagicMock()
        mock_store.search = AsyncMock(return_value=[{"text": "Documento sobre IA"}])

        with (
            patch("ai.service.settings") as mock_settings,
            patch("ai.memory.store.VectorStore", return_value=mock_store),
        ):
            mock_settings.primary_provider = "openai"
            mock_settings.rag_enabled = True

            response = await service.complete("explique IA", provider="openai")
            assert response == "Resposta da OpenAI"
            mock_store.search.assert_awaited_once_with("explique IA")

    @pytest.mark.asyncio
    async def test_complete_ignora_rag_quando_desabilitado(
        self,
        service: AIService,
        mock_providers_patch,
    ):
        """Não deve consultar RAG se rag_enabled=False."""
        with (
            patch("ai.service.settings") as mock_settings,
            patch("ai.memory.store.VectorStore") as mock_store_cls,
        ):
            mock_settings.primary_provider = "openai"
            mock_settings.rag_enabled = False

            await service.complete("teste", provider="openai", use_rag=False)
            mock_store_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_nao_quebra_quando_rag_falha(
        self,
        service: AIService,
        mock_providers_patch,
    ):
        """Deve continuar mesmo se o RAG lançar exceção."""
        mock_store = MagicMock()
        mock_store.search = AsyncMock(side_effect=Exception("Qdrant offline"))

        with (
            patch("ai.service.settings") as mock_settings,
            patch("ai.memory.store.VectorStore", return_value=mock_store),
        ):
            mock_settings.primary_provider = "openai"
            mock_settings.rag_enabled = True

            response = await service.complete("teste", provider="openai")
            assert response == "Resposta da OpenAI"

    @pytest.mark.asyncio
    async def test_complete_retorna_erro_quando_fallback_tambem_falha(
        self,
        service: AIService,
        mock_providers_patch,
    ):
        """Deve retornar mensagem de erro se todos os providers falharem."""
        mock_providers_patch["ollama"].complete = AsyncMock(side_effect=Exception("Falha Ollama"))
        mock_providers_patch["openai"].complete = AsyncMock(side_effect=Exception("Falha OpenAI"))

        with (
            patch("ai.service.settings") as mock_settings,
        ):
            mock_settings.primary_provider = "openai"
            mock_settings.rag_enabled = False

            response = await service.complete("teste", provider="ollama")
            assert "❌" in response
            assert "Falha Ollama" in response

    @pytest.mark.asyncio
    async def test_complete_lanca_erro_para_provider_inexistente(
        self,
        service: AIService,
        mock_providers_patch,
    ):
        """Deve levantar ValueError para provider não registrado."""
        with (
            patch.object(service, "_get_providers", return_value={}),
            patch("ai.service.settings") as mock_settings,
        ):
            mock_settings.rag_enabled = False

            with pytest.raises(ValueError, match="não encontrado"):
                await service.complete("teste", provider="openai")

    @pytest.mark.asyncio
    async def test_complete_classifica_task_type_automaticamente(
        self,
        service: AIService,
        mock_providers_patch,
    ):
        """Deve classificar o task_type automaticamente se não fornecido."""
        with (
            patch("ai.service.settings") as mock_settings,
            patch("ai.service.get_default_provider_for_task", return_value="openai"),
            patch("ai.classifier.TaskClassifier.classify", return_value="code") as mock_classify,
        ):
            mock_settings.primary_provider = "openai"
            mock_settings.rag_enabled = False

            await service.complete("crie uma função em Python", provider="openai")
            mock_classify.assert_called_once_with("crie uma função em Python")

    @pytest.mark.asyncio
    async def test_complete_cai_para_local_quando_nuvem_retorna_402(
        self,
        service: AIService,
        mock_providers_patch,
    ):
        """402 do provedor de nuvem deve cair para o provedor local (custo zero)."""
        mock_providers_patch["openai"].complete = AsyncMock(side_effect=_http_error(402))

        with patch("ai.service.settings") as mock_settings:
            mock_settings.primary_provider = "openai"
            mock_settings.local_provider = "ollama"
            mock_settings.rag_enabled = False

            response = await service.complete("teste", provider="openai")

        assert response == "Resposta da Ollama"
        mock_providers_patch["ollama"].complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_402_em_todos_nao_vira_erro_opaco(
        self,
        service: AIService,
        mock_providers_patch,
    ):
        """402 em todos os provedores deve virar instrução de custo zero."""
        mock_providers_patch["openai"].complete = AsyncMock(side_effect=_http_error(402))
        mock_providers_patch["ollama"].complete = AsyncMock(side_effect=_http_error(402))

        with patch("ai.service.settings") as mock_settings:
            mock_settings.primary_provider = "openai"
            mock_settings.local_provider = "ollama"
            mock_settings.ollama_base_url = "http://localhost:11434"
            mock_settings.rag_enabled = False

            response = await service.complete("teste", provider="openai")

        assert "HTTP 402" in response
        assert "custo zero" in response
        assert "ollama" in response


# ═══════════════════════════════════════════════════════════════════════════
# billing_reason
# ═══════════════════════════════════════════════════════════════════════════


class TestBillingReason:
    """Testes para billing_reason() — detecção de falha de cobrança/cota."""

    def test_reconhece_http_402(self):
        """402 (Payment Required) é a assinatura de provedor sem créditos."""
        assert billing_reason(_http_error(402)) == "HTTP 402"

    def test_reconhece_http_429(self):
        """429 (cota esgotada) também é falha de cobrança/cota."""
        assert billing_reason(_http_error(429)) == "HTTP 429"

    def test_reconhece_status_code_do_sdk_openai(self):
        """O SDK da OpenAI expõe status_code direto na exceção."""

        class FakeAPIStatusError(Exception):
            status_code = 402

        assert billing_reason(FakeAPIStatusError("erro qualquer")) == "HTTP 402"

    def test_reconhece_mensagem_de_quota(self):
        """Mensagem textual de cota/crédito conta como falha de cobrança."""
        assert billing_reason(Exception("insufficient_quota: no credits")) == "insufficient"

    def test_erro_comum_nao_e_cobranca(self):
        """Erro de rede/timeout não deve ser classificado como cobrança."""
        assert billing_reason(Exception("connection refused")) is None
        assert billing_reason(_http_error(500)) is None


# ═══════════════════════════════════════════════════════════════════════════
# get_provider_status
# ═══════════════════════════════════════════════════════════════════════════


class TestGetProviderStatus:
    """Testes para AIService.get_provider_status()."""

    @pytest.mark.asyncio
    async def test_retorna_true_para_provider_com_chave(self, service: AIService):
        """Deve retornar True para provedores com API key configurada."""
        with patch("ai.service.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-123"
            mock_settings.claude_api_key = ""
            mock_settings.gemini_api_key = ""
            mock_settings.groq_api_key = ""
            mock_settings.glm_api_key = ""
            mock_settings.perplexity_api_key = ""

            status = await service.get_provider_status()
            assert status["openai"] is True
            assert status["claude"] is False
            assert status["bitnet"] is True  # Local provider

    @pytest.mark.asyncio
    async def test_ollama_e_bitnet_sempre_configurados(self, service: AIService):
        """Ollama e BitNet devem ser sempre considerados como configurados."""
        with patch("ai.service.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            mock_settings.claude_api_key = ""
            mock_settings.gemini_api_key = ""
            mock_settings.groq_api_key = ""
            mock_settings.glm_api_key = ""
            mock_settings.perplexity_api_key = ""

            status = await service.get_provider_status()
            assert status["ollama"] is True
            assert status["bitnet"] is True

    @pytest.mark.asyncio
    async def test_retorna_todos_os_providers(self, service: AIService):
        """Deve retornar status para todos os 8 provedores."""
        with patch("ai.service.settings") as mock_settings:
            mock_settings.openai_api_key = "k1"
            mock_settings.claude_api_key = "k2"
            mock_settings.gemini_api_key = "k3"
            mock_settings.groq_api_key = "k4"
            mock_settings.glm_api_key = "k5"
            mock_settings.perplexity_api_key = "k6"

            status = await service.get_provider_status()
            assert len(status) == 8
            assert all(v is True for v in status.values())


# ═══════════════════════════════════════════════════════════════════════════
# _get_providers (privado)
# ═══════════════════════════════════════════════════════════════════════════


class TestGetProviders:
    """Testes para o método privado _get_providers()."""

    def test_cacheia_providers_apos_primeira_chamada(self, service: AIService):
        """Deve retornar o mesmo dicionário em chamadas repetidas.

        Os imports dentro de _get_providers() são lazy (dentro do corpo do método),
        então patcheamos os módulos de origem que ele importa.
        """
        with (
            patch("ai.providers.providers.OpenAIProvider", MagicMock()),
            patch("ai.providers.providers.ClaudeProvider", MagicMock()),
            patch("ai.providers.providers.GeminiProvider", MagicMock()),
            patch("ai.providers.providers.GroqProvider", MagicMock()),
            patch("ai.providers.providers.GLMProvider", MagicMock()),
            patch("ai.providers.providers.PerplexityProvider", MagicMock()),
            patch("ai.providers.ollama.OllamaProvider", MagicMock()),
            patch("ai.providers.bitnet.BitNetProvider", MagicMock()),
        ):
            first = service._get_providers()
            second = service._get_providers()
            assert first is second  # mesma referência (cache)
            assert len(first) == 8  # 8 provedores registrados
