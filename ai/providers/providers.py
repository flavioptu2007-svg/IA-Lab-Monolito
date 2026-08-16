"""Implementações de todos os provedores de IA suportados."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from ai.providers.base import BaseProvider
from ai.settings import settings

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

# ---- OpenAI ----


class OpenAIProvider(BaseProvider):
    name = "openai"
    model = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.openai_model
        self.api_key = settings.openai_api_key.get_secret_value()
        self.base_url = settings.openai_base_url.rstrip("/")

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        messages: list[ChatCompletionMessageParam] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    async def is_available(self) -> bool:
        return bool(self.api_key)


# ---- Anthropic Claude ----


class ClaudeProvider(BaseProvider):
    name = "claude"
    model = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.claude_model
        self.api_key = settings.claude_api_key.get_secret_value()
        self.base_url = settings.claude_base_url.rstrip("/")

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content_blocks = data.get("content", [])
            return content_blocks[0].get("text", "") if content_blocks else ""

    async def is_available(self) -> bool:
        return bool(self.api_key)


# ---- Gemini ----


class GeminiProvider(BaseProvider):
    name = "gemini"
    model = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.gemini_model
        self.api_key = settings.gemini_api_key.get_secret_value()
        self.base_url = settings.gemini_base_url.rstrip("/")

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        contents = [{"parts": [{"text": prompt}]}]
        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
            return ""

    async def is_available(self) -> bool:
        return bool(self.api_key)


# ---- Groq ----


class GroqProvider(BaseProvider):
    name = "groq"
    model = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.groq_model
        self.api_key = settings.groq_api_key.get_secret_value()
        self.base_url = settings.groq_base_url.rstrip("/")

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        messages: list[ChatCompletionMessageParam] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    async def is_available(self) -> bool:
        return bool(self.api_key)


# ---- GLM (Zhipu) ----


class GLMProvider(BaseProvider):
    name = "glm"
    model = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.glm_model
        self.api_key = settings.glm_api_key.get_secret_value()
        self.base_url = settings.glm_base_url.rstrip("/")

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        messages: list[ChatCompletionMessageParam] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    async def is_available(self) -> bool:
        return bool(self.api_key)


# ---- Perplexity ----


class PerplexityProvider(BaseProvider):
    name = "perplexity"
    model = ""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.perplexity_model
        self.api_key = settings.perplexity_api_key.get_secret_value()
        self.base_url = settings.perplexity_base_url.rstrip("/")

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        messages: list[ChatCompletionMessageParam] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    async def is_available(self) -> bool:
        return bool(self.api_key)
