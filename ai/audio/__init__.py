"""IA-Lab Audio — Módulo profissional de áudio para IA-Lab Enterprise.

Fornece pipeline completo de processamento de áudio:
- Captura e reprodução com buffer circular
- Voice Activity Detection (VAD) com WebRTC
- Speech-to-Text (STT) com speechbrain
- Text-to-Speech (TTS) com espeak/edge-tts
- Processamento de sinal (noise gate, compressor, EQ)
- Conversão entre formatos (WAV, MP3, FLAC, OGG, PCM)
- Gerenciamento de microfone virtual (PipeWire null-sink)
- Métricas e telemetria

Uso típico (engine principal):
    from ai.audio import AudioEngine

    engine = AudioEngine()
    await engine.initialize()
    status = await engine.get_status()
"""

from __future__ import annotations

# Fase 6 — Métricas
from ai.audio import effects, formats, metrics
from ai.audio.core import AudioEngine

# Fase 3 — Módulos base
from ai.audio.exceptions import (
    AudioCaptureError,
    AudioConfigError,
    AudioConversionError,
    AudioDeviceError,
    AudioError,
    AudioFormatError,
    AudioPlaybackError,
    STTError,
    TTSError,
    VADError,
)
from ai.audio.microphone import VirtualMicrophone
from ai.audio.player import AudioPlayer, PlaybackItem
from ai.audio.recorder import AudioRecorder
from ai.audio.settings import AudioSettings, audio_settings, get_audio_settings

# Fase 5 — IA e conversão
from ai.audio.stt import SpeechToText
from ai.audio.tts import TextToSpeech

# Fase 4 — Captura, reprodução e processamento
from ai.audio.vad import VoiceActivityDetector

__all__ = [
    # Engine e Config
    "AudioEngine",
    "AudioSettings",
    "audio_settings",
    "get_audio_settings",
    # Exceções
    "AudioError",
    "AudioDeviceError",
    "AudioCaptureError",
    "AudioPlaybackError",
    "AudioFormatError",
    "AudioConversionError",
    "VADError",
    "STTError",
    "TTSError",
    "AudioConfigError",
    # VAD
    "VoiceActivityDetector",
    # Captura e reprodução
    "AudioRecorder",
    "AudioPlayer",
    "PlaybackItem",
    # Processamento
    "effects",
    # IA
    "SpeechToText",
    "TextToSpeech",
    # Dispositivos
    "VirtualMicrophone",
    # Formatos
    "formats",
    # Métricas
    "metrics",
]
