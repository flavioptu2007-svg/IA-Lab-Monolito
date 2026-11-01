"""Serviço central de IA - Orquestrador de provedores e agentes.

O AIService é responsável por:
- Roteamento inteligente de prompts para o provedor mais adequado
- Integração com RAG (Qdrant) para contexto adicional
- Fallback automático entre provedores, terminando no provedor LOCAL
  quando a nuvem falha por cobrança/cota (política de CUSTO ZERO, AGENTS.md)
- Registro de métricas e telemetria
"""

from __future__ import annotations

import re
import time
from typing import Any

from pydantic import SecretStr

from ai.providers.base import TaskType, get_default_provider_for_task
from ai.settings import settings

# ── Falhas de cobrança/cota do provedor de nuvem ──────────────────────────
# Um provedor sem créditos responde 402 ("provider billing issue") ou 429
# (cota esgotada). Sem tratamento, o usuário recebe só a exceção crua do SDK
# e nenhuma saída — mas esta máquina não pode pagar a conta (AGENTS.md,
# regra nº 1). A resposta útil é reconhecer a natureza da falha e cair para
# o provedor local, que não depende de créditos.
_BILLING_STATUS_CODES = (402, 429)
_BILLING_MARKERS = (
    "billing",
    "payment required",
    "insufficient",
    "quota",
    "no credits",
    "credit balance",
    "resource_exhausted",
)

# ── Falhas de autenticação/permissão ──────────────────────────────────────
# 401/403 sem marcador de cota são erro de credencial ou configuração: cair
# para o provedor local esconderia a causa (chave ausente/inválida), então a
# resposta é explícita em vez de "fantasiar" sucesso.
_AUTH_STATUS_CODES = (401, 403)
_AUTH_MARKERS = (
    "unauthorized",
    "invalid api key",
    "invalid_api_key",
    "invalid api-key",
    "authentication",
    "permission denied",
    "forbidden",
)

# Padrões de credencial que podem aparecer em mensagens de erro/URLs.
_SEGREDOS = (
    re.compile(r"(?i)([?&](?:key|api_key|api-key|token|access_token)=)[^&\s'\"]+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)((?:x-api-key|x-goog-api-key)['\"]?\s*[:=]\s*)[^\s,'\"}]+"),
)


def _status_code(exc: BaseException) -> int | None:
    """HTTP status da exceção (SDK da OpenAI ou httpx), quando houver."""
    codigo = getattr(exc, "status_code", None)
    if codigo is None:
        response = getattr(exc, "response", None)
        codigo = getattr(response, "status_code", None)
    return codigo if isinstance(codigo, int) else None


def redact(text: str) -> str:
    """Remove credenciais de uma mensagem antes de logar ou devolver ao cliente."""
    for padrao in _SEGREDOS:
        text = padrao.sub(r"\1***", text)
    return text


def billing_reason(exc: BaseException) -> str | None:
    """Motivo quando a falha é de cobrança/cota; ``None`` para outros erros.

    Reconhece tanto ``httpx.HTTPStatusError`` (via ``.response``) quanto as
    exceções do SDK da OpenAI (``.status_code``), além de mensagens que
    mencionam explicitamente cobrança, cota ou créditos.
    """
    status_code = _status_code(exc)
    if status_code in _BILLING_STATUS_CODES:
        return f"HTTP {status_code}"

    text = str(exc).lower()
    for marker in _BILLING_MARKERS:
        if marker in text:
            return marker
    return None


def auth_failure(exc: BaseException) -> str | None:
    """Motivo quando a falha é de autenticação/permissão; ``None`` caso contrário."""
    status_code = _status_code(exc)
    if status_code in _AUTH_STATUS_CODES:
        return f"HTTP {status_code}"

    text = str(exc).lower()
    for marker in _AUTH_MARKERS:
        if marker in text:
            return marker
    return None


class AIService:
    """Serviço principal de IA que orquestra provedores e tarefas."""

    def __init__(self) -> None:
        self._providers: dict[str, Any] | None = None

    def _get_providers(self) -> dict[str, Any]:
        """Inicializa e retorna o dicionário de provedores disponíveis."""
        if self._providers is not None:
            return self._providers

        from ai.providers.bitnet import BitNetProvider
        from ai.providers.ollama import OllamaProvider
        from ai.providers.providers import (
            ClaudeProvider,
            GeminiProvider,
            GLMProvider,
            GroqProvider,
            OpenAIProvider,
            PerplexityProvider,
        )

        self._providers = {
            "openai": OpenAIProvider,
            "claude": ClaudeProvider,
            "gemini": GeminiProvider,
            "groq": GroqProvider,
            "glm": GLMProvider,
            "perplexity": PerplexityProvider,
            "ollama": OllamaProvider,
            "bitnet": BitNetProvider,
        }
        return self._providers

    def choose_provider(self, preferred: str | None = None) -> str:
        """Escolhe o melhor provedor baseado na preferência ou configuração."""
        if preferred and preferred in self._get_providers():
            return preferred
        return settings.primary_provider

    def _fallback_chain(self, failed: str) -> list[str]:
        """Provedores a tentar depois de ``failed``, sem repetir e em ordem.

        Ordem: provedor primário configurado → provedor local. O local é
        sempre o último recurso porque é o único caminho de custo zero
        garantido (AGENTS.md, regra nº 1).
        """
        candidates = dict.fromkeys([settings.primary_provider, settings.local_provider])
        providers = self._get_providers()
        return [name for name in candidates if name != failed and name in providers]

    # Provedores que só funcionam com credencial configurada (os locais não).
    _CREDENCIAIS: dict[str, str] = {
        "openai": "openai_api_key",
        "claude": "claude_api_key",
        "gemini": "gemini_api_key",
        "groq": "groq_api_key",
        "glm": "glm_api_key",
        "perplexity": "perplexity_api_key",
    }

    def _tem_credencial(self, name: str) -> bool:
        """Indica se o provedor pode ser chamado (nuvem exige chave configurada).

        Sem isso, o roteamento por tarefa escolhia ``openai``/``glm`` mesmo sem
        chave e cada chamada gastava uma requisição fadada ao erro antes do
        fallback.
        """
        atributo = self._CREDENCIAIS.get(name)
        if atributo is None:
            return True  # ollama / bitnet rodam localmente
        valor = getattr(settings, atributo, None)
        if isinstance(valor, SecretStr):
            return bool(valor.get_secret_value())
        return bool(valor)

    async def complete(
        self,
        prompt: str,
        provider: str | None = None,
        task_type: TaskType | str | None = None,
        use_rag: bool = True,
    ) -> str:
        """Envia um prompt para o provedor de IA apropriado.

        Args:
            prompt: O texto do prompt.
            provider: Nome do provedor (opcional - auto-detect se omitido).
            task_type: Tipo de tarefa para roteamento inteligente.
            use_rag: Se deve buscar contexto adicional no Qdrant.

        Returns:
            A resposta gerada pela IA.
        """
        from ai.classifier import TaskClassifier
        from ai.telemetry import get_logger, request_counter, request_duration

        logger = get_logger("ai.service")

        # Determina o tipo de tarefa se não fornecido
        if task_type is None:
            task_type = TaskClassifier.classify(prompt)
        elif isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                task_type = TaskType.general

        task_type_str = task_type.value if isinstance(task_type, TaskType) else str(task_type)

        # Escolhe o provedor
        provider_name = provider or get_default_provider_for_task(task_type)
        if provider_name == "auto" or provider_name not in self._get_providers():
            provider_name = settings.primary_provider
        elif provider is None and not self._tem_credencial(provider_name):
            # O roteamento por tarefa pode apontar para nuvem sem chave: isso
            # garantia um erro (e um fallback) a cada chamada. Vai direto ao
            # primário configurado — custo zero por padrão.
            provider_name = settings.primary_provider

        # Prepara o prompt com contexto RAG se habilitado
        final_prompt = prompt
        rag_context = ""
        if use_rag and settings.rag_enabled:
            try:
                from ai.memory.store import VectorStore

                store = VectorStore()
                docs = await store.search(prompt)
                if docs:
                    rag_context = "\n\n".join(
                        f"[Documento {i + 1}] {d['text']}" for i, d in enumerate(docs)
                    )
                    final_prompt = (
                        f"Contexto relevante:\n{rag_context}\n\n"
                        f"Com base no contexto acima (se aplicável), "
                        f"responda:\n\n{prompt}"
                    )
            except Exception as e:
                logger.warning("RAG search failed: %s", e)

        # Seleciona e executa o provedor
        provider_cls = self._get_providers().get(provider_name)
        if provider_cls is None:
            raise ValueError(f"Provedor '{provider_name}' não encontrado")

        provider_instance = provider_cls()
        start = time.monotonic()

        status = "success"
        try:
            response = await provider_instance.complete(
                prompt=final_prompt,
                system_prompt=(
                    "Você é um assistente de IA especializado em desenvolvimento "
                    "de software e tecnologia. Responda de forma clara e objetiva."
                ),
            )
            return response
        except Exception as e:
            status = "error"
            reason = billing_reason(e)
            auth = None if reason else auth_failure(e)
            detalhe = redact(str(e))
            logger.error(
                "Provider %s failed%s: %s",
                provider_name,
                f" ({reason or auth})" if (reason or auth) else "",
                detalhe,
            )

            # Erro de credencial não cai para o local: o fallback responderia
            # com sucesso e esconderia a configuração quebrada.
            if auth:
                return (
                    f"❌ **Falha de autenticação no provedor {provider_name} ({auth}).**\n\n"
                    "Causa provável: chave ausente/inválida ou permissão negada. "
                    "Não houve fallback para não mascarar erro de configuração — "
                    "corrija a credencial ou peça explicitamente o provedor local "
                    f"`{settings.local_provider}`.\n\n"
                    f"Detalhe: {detalhe}"
                )

            # Fallback: primário configurado e, por último, o provedor local.
            for fallback_name in self._fallback_chain(provider_name):
                logger.info("Tentando fallback para %s...", fallback_name)
                fallback_cls = self._get_providers().get(fallback_name)
                if fallback_cls is None:
                    continue
                try:
                    return await fallback_cls().complete(prompt=prompt)
                except Exception as fallback_e:
                    logger.error("Fallback %s falhou: %s", fallback_name, redact(str(fallback_e)))

            if reason:
                return (
                    f"❌ **Provedor {provider_name} indisponível ({reason}):** {detalhe}\n\n"
                    "Causa provável: cobrança, cota ou créditos do provedor de nuvem. "
                    "Este ambiente opera em **custo zero** (AGENTS.md, regra nº 1), "
                    f"então não há cobrança a resolver: use o provedor local "
                    f"`{settings.local_provider}` (Ollama em {settings.ollama_base_url}) "
                    "ou um modelo gratuito."
                )

            return (
                f"❌ **Erro no provedor {provider_name}:** {detalhe}\n\n"
                f"Verifique se a API key está configurada e o serviço está acessível."
            )
        finally:
            elapsed = time.monotonic() - start
            request_counter.labels(
                provider=provider_name, task_type=task_type_str, status=status
            ).inc()
            request_duration.labels(provider=provider_name, task_type=task_type_str).observe(
                elapsed
            )

    async def get_provider_status(self) -> dict[str, bool]:
        """Verifica o status de todos os provedores configurados.

        ``SecretStr`` suporta ``bool()`` nativamente —
        ``bool(SecretStr(""))`` é False, ``bool(SecretStr("key"))`` é True.
        """
        status: dict[str, bool] = {}
        providers_cfg: dict[str, SecretStr | bool] = {
            "openai": settings.openai_api_key,
            "claude": settings.claude_api_key,
            "gemini": settings.gemini_api_key,
            "groq": settings.groq_api_key,
            "glm": settings.glm_api_key,
            "perplexity": settings.perplexity_api_key,
            "ollama": True,  # Local — sempre configurado
            "bitnet": True,  # Local — sempre configurado
        }

        for name, key in providers_cfg.items():
            status[name] = bool(key)

        return status
