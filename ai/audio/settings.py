"""Configurações do módulo de áudio.

Carrega variáveis de ambiente com prefixo IA_LAB_AUDIO_ e
disponibiliza um singleton `audio_settings` para o módulo de áudio.

Padrões seguem o modelo de ai/settings.py com pydantic_settings.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioSettings(BaseSettings):
    """Configurações de áudio, carregadas de env vars / .env."""

    model_config = SettingsConfigDict(
        env_prefix="IA_LAB_AUDIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Dispositivos ──────────────────────────────────────────────────────
    input_device: str = "default"
    output_device: str = "default"
    virtual_mic_name: str = "ia-lab-mic"
    virtual_mic_description: str = "IA-Lab Microfone Virtual"

    # ── Sample rate / qualidade ──────────────────────────────────────────
    sample_rate: int = 16000  # Hz (16kHz para STT)
    sample_width: int = 16  # bits (16-bit PCM)
    channels: int = 1  # mono

    # ── VAD (Voice Activity Detection) ────────────────────────────────────
    vad_aggressiveness: int = 2  # 0-3 (0=menos agressivo, 3=mais)
    vad_frame_ms: int = 30  # ms por frame (10/20/30)
    vad_speech_threshold: float = 0.5  # proporção de frames de fala
    vad_pre_speech_pad: float = 0.5  # segundos de áudio antes da fala
    vad_post_speech_pad: float = 1.0  # segundos de áudio depois da fala
    vad_min_speech_duration: float = 0.5  # duração mínima para considerar fala

    # ── Recording ─────────────────────────────────────────────────────────
    record_buffer_seconds: int = 30  # tamanho do buffer circular em segundos
    record_max_duration: int = 300  # duração máxima de gravação (5 min)
    record_temp_dir: str = "/tmp/ia-lab-audio"

    # ── STT (Speech-to-Text) ──────────────────────────────────────────────
    stt_model: str = "speechbrain/asr-wav2vec2-commonvoice-14-en"
    stt_device: str = "cpu"  # cpu ou cuda
    stt_language: str = "pt"  # idioma padrão
    stt_fallback_model: str = ""  # modelo alternativo se o principal falhar
    stt_timeout: float = 30.0  # timeout em segundos

    # ── TTS (Text-to-Speech) ──────────────────────────────────────────────
    tts_engine: str = "espeak"  # espeak, edge-tts (em ordem de fallback)
    tts_voice: str = "pt-br"  # voz / idioma
    tts_rate: int = 160  # velocidade (espeak: 80-450)
    tts_volume: int = 200  # volume (espeak: 0-200)
    tts_edge_voice: str = "pt-BR-AntonioNeural"  # voz edge-tts

    # ── Effects (processamento) ───────────────────────────────────────────
    noise_gate_threshold: float = -50.0  # dB
    noise_gate_attack: float = 0.01  # segundos
    noise_gate_release: float = 0.1  # segundos
    compressor_threshold: float = -20.0  # dB
    compressor_ratio: float = 4.0  # 4:1
    compressor_attack: float = 0.005  # segundos
    compressor_release: float = 0.2  # segundos

    # ── Logs ──────────────────────────────────────────────────────────────
    audio_log_dir: str = ""  # vazio = usa Path.home() no runtime


@lru_cache
def get_audio_settings() -> AudioSettings:
    """Retorna o singleton de configurações de áudio."""
    return AudioSettings()


audio_settings = get_audio_settings()
