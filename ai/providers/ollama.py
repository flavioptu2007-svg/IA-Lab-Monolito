"""Provedor Ollama para modelos locais."""

from __future__ import annotations

import httpx

from ai.providers.base import BaseProvider
from ai.settings import settings


class OllamaProvider(BaseProvider):
    """Integração com servidor Ollama local."""

    name = "ollama"
    model = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.ollama_model
        self.base_url = settings.ollama_base_url.rstrip("/")

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
