"""Provedor BitNet — LLM 1-bit (inferência ultra-eficiente em CPU).

Comunica-se com o servidor ``llama-server`` exposto pelo container
BitNet (porta 8080), que fornece uma API compatível com OpenAI.
"""

from __future__ import annotations

import httpx

from ai.providers.base import BaseProvider
from ai.settings import settings


class BitNetProvider(BaseProvider):
    """Integração com BitNet 1-bit LLM via llama-server.

    O BitNet roda como um servidor OpenAI-compatible na porta 8080,
    exposto pelo container ``intel-bitnet`` no docker-compose.
    """

    name = "bitnet"
    model = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.bitnet_model
        self.base_url = settings.bitnet_base_url.rstrip("/")
        # BitNet não requer API key — usa autenticação local
        self.api_key = "no-key-required"

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Envia prompt para o BitNet via OpenAI-compatible API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    async def is_available(self) -> bool:
        """Verifica se o servidor BitNet está acessível."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
