"""Serviço central de IA - Orquestrador de provedores e agentes.

O AIService é responsável por:
- Roteamento inteligente de prompts para o provedor mais adequado
- Integração com RAG (Qdrant) para contexto adicional
- Fallback automático entre provedores
- Registro de métricas e telemetria
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import SecretStr

from ai.providers.base import TaskType, get_default_provider_for_task
from ai.settings import settings


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
            logger.error("Provider %s failed: %s", provider_name, e)

            # Fallback: tenta o provedor primário se diferente
            if provider_name != settings.primary_provider:
                logger.info("Tentando fallback para %s...", settings.primary_provider)
                fallback_cls = self._get_providers().get(settings.primary_provider)
                if fallback_cls:
                    fallback_instance = fallback_cls()
                    try:
                        return await fallback_instance.complete(prompt=prompt)
                    except Exception as fallback_e:
                        logger.error("Fallback also failed: %s", fallback_e)

            return (
                f"❌ **Erro no provedor {provider_name}:** {e}\n\n"
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
