"""Agente especializado em processamento de áudio e voz.

Capacidades:
- Speech-to-Text (transcrição de fala para texto)
- Text-to-Speech (síntese de texto para fala)
- Voice Activity Detection (detecção de atividade de voz)
- Processamento de sinal (noise gate, compressor, EQ)
- Gerenciamento de microfone virtual
- Conversão entre formatos de áudio
"""

from __future__ import annotations

from ai.agents.base import BaseAgent
from ai.providers.base import TaskType
from ai.service import AIService


class AudioAgent(BaseAgent):
    """Agente especializado em processamento de áudio e voz."""

    name = "audio"
    description = (
        "Processa áudio: STT, TTS, VAD, efeitos, microfone virtual e conversão de formatos"
    )
    task_type = TaskType.local
    default_provider = "ollama"
    system_prompt = (
        "Você é um engenheiro de áudio especializado em processamento de fala e som. "
        "Você domina Speech-to-Text (transcrição), Text-to-Speech (síntese de voz), "
        "Voice Activity Detection, noise gate, compressão, equalização e conversão entre "
        "formatos de áudio (WAV, MP3, FLAC, OGG, PCM). "
        "Você também gerencia microfones virtuais no PipeWire/Linux. "
        "Sempre forneça exemplos práticos de código quando relevante e explique "
        "as configurações recomendadas para cada caso de uso (STT, TTS, gravação, etc.)."
    )

    async def run(self, prompt: str, provider: str | None = None, use_rag: bool = True) -> str:
        service = AIService()
        full_prompt = f"{self.system_prompt}\n\n## Solicitação de Áudio\n\n{prompt}"
        return await service.complete(
            prompt=full_prompt,
            provider=provider or self.default_provider,
            task_type=self.task_type,
            use_rag=use_rag,
        )
