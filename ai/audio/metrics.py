"""Métricas Prometheus para o módulo de áudio do IA-Lab.

Fornece métricas específicas para:
- Captura e reprodução de áudio
- VAD (Voice Activity Detection)
- STT (Speech-to-Text)
- TTS (Text-to-Speech)
- Status de dispositivos
- Contagem de erros por tipo

Todas as métricas usam o prefixo ``ia_lab_audio_`` para consistência.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── Métricas de gravação ──────────────────────────────────────────────────────

audio_recording = Gauge(
    "ia_lab_audio_recording",
    "Indica se o sistema está gravando áudio no momento (1=gravando, 0=ocioso)",
    ["source"],
)

audio_capture_duration = Histogram(
    "ia_lab_audio_capture_duration_seconds",
    "Duração das sessões de captura de áudio em segundos",
    ["source"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

audio_capture_bytes = Counter(
    "ia_lab_audio_capture_bytes_total", "Total de bytes de áudio capturados", ["source", "format"]
)

# ── Métricas de reprodução ────────────────────────────────────────────────────

audio_playback = Gauge(
    "ia_lab_audio_playback",
    "Indica se o sistema está reproduzindo áudio no momento (1=reproduzindo, 0=ocioso)",
    ["sink"],
)

audio_playback_items = Counter(
    "ia_lab_audio_playback_items_total", "Total de itens reproduzidos na fila", ["sink"]
)

# ── Métricas de VAD (Voice Activity Detection) ────────────────────────────────

vad_speech_frames = Counter(
    "ia_lab_audio_vad_speech_frames_total",
    "Total de frames de áudio classificados como fala",
    ["aggressiveness"],
)

vad_silence_frames = Counter(
    "ia_lab_audio_vad_silence_frames_total",
    "Total de frames de áudio classificados como silêncio",
    ["aggressiveness"],
)

vad_segments_detected = Counter(
    "ia_lab_audio_vad_segments_total", "Total de segmentos de fala detectados", ["aggressiveness"]
)

vad_speech_ratio = Gauge(
    "ia_lab_audio_vad_speech_ratio", "Proporção atual de frames de fala na janela de detecção"
)

# ── Métricas de STT (Speech-to-Text) ─────────────────────────────────────────

stt_duration = Histogram(
    "ia_lab_audio_stt_duration_seconds",
    "Duração das transcrições de fala para texto em segundos",
    ["model"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

stt_audio_duration = Histogram(
    "ia_lab_audio_stt_audio_duration_seconds",
    "Duração do áudio transcrito em segundos",
    ["model"],
    buckets=(0.5, 1.0, 3.0, 10.0, 30.0, 60.0, 300.0),
)

stt_characters = Counter(
    "ia_lab_audio_stt_characters_total", "Total de caracteres transcritos", ["model", "language"]
)

stt_requests = Counter(
    "ia_lab_audio_stt_requests_total",
    "Total de requisições de transcrição",
    ["model", "status"],  # status: success, error
)

# ── Métricas de TTS (Text-to-Speech) ─────────────────────────────────────────

tts_duration = Histogram(
    "ia_lab_audio_tts_duration_seconds",
    "Duração das sínteses de texto para fala em segundos",
    ["engine", "voice"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

tts_audio_duration = Histogram(
    "ia_lab_audio_tts_audio_duration_seconds",
    "Duração do áudio sintetizado em segundos",
    ["engine"],
    buckets=(0.5, 1.0, 3.0, 10.0, 30.0, 60.0, 300.0),
)

tts_characters = Counter(
    "ia_lab_audio_tts_characters_total", "Total de caracteres sintetizados", ["engine", "voice"]
)

tts_requests = Counter(
    "ia_lab_audio_tts_requests_total",
    "Total de requisições de síntese de fala",
    ["engine", "status"],  # status: success, error
)

# ── Métricas de dispositivos ─────────────────────────────────────────────────

device_status = Gauge(
    "ia_lab_audio_device_status",
    "Status dos dispositivos de áudio (1=ok, 0=erro, -1=desconhecido)",
    ["device_name", "device_type"],  # device_type: source, sink, virtual_mic
)

device_volume = Gauge(
    "ia_lab_audio_device_volume",
    "Volume atual do dispositivo de áudio (0.0 a 1.0)",
    ["device_name"],
)

device_muted = Gauge(
    "ia_lab_audio_device_muted",
    "Indica se o dispositivo está mutado (1=mudo, 0=ativo)",
    ["device_name"],
)

# ── Métricas de erros ────────────────────────────────────────────────────────

audio_errors = Counter(
    "ia_lab_audio_errors_total",
    "Total de erros no módulo de áudio, categorizados por tipo",
    ["error_type"],  # error_type: capture, playback, vad, stt, tts, format, device, config
)

# ── Métricas de formato/conversão ────────────────────────────────────────────

audio_conversion_duration = Histogram(
    "ia_lab_audio_conversion_duration_seconds",
    "Duração das conversões entre formatos de áudio",
    ["from_format", "to_format"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

audio_conversion_bytes = Counter(
    "ia_lab_audio_conversion_bytes_total",
    "Total de bytes processados em conversões de áudio",
    ["from_format", "to_format"],
)

# ── Métricas de microfone virtual ────────────────────────────────────────────

virtual_mic_active = Gauge(
    "ia_lab_audio_virtual_mic_active",
    "Indica se o microfone virtual está ativo (1=ativo, 0=inativo)",
)

virtual_mic_loopback = Gauge(
    "ia_lab_audio_virtual_mic_loopback",
    "Indica se o loopback do microfone virtual está ativo (1=ativo, 0=inativo)",
)
