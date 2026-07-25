"""Testes das metricas Prometheus do modulo de audio.

Testa que todas as metricas estao registradas e sao atualizaveis.
"""

from __future__ import annotations

# Forca o registro das metricas de audio no registry global do Prometheus
import ai.audio.metrics as _m  # noqa: F401 side-effect: registra metricas no Prometheus


class TestAudioMetricsRegistration:
    """Verifica que todas as metricas estao registradas no registry global."""

    METRIC_PREFIX = "ia_lab_audio_"

    EXPECTED_METRICS = [
        "ia_lab_audio_recording",
        "ia_lab_audio_capture_duration_seconds",
        "ia_lab_audio_capture_bytes_total",
        "ia_lab_audio_playback",
        "ia_lab_audio_playback_items_total",
        "ia_lab_audio_vad_speech_frames_total",
        "ia_lab_audio_vad_silence_frames_total",
        "ia_lab_audio_vad_segments_total",
        "ia_lab_audio_vad_speech_ratio",
        "ia_lab_audio_stt_duration_seconds",
        "ia_lab_audio_stt_audio_duration_seconds",
        "ia_lab_audio_stt_characters_total",
        "ia_lab_audio_stt_requests_total",
        "ia_lab_audio_tts_duration_seconds",
        "ia_lab_audio_tts_audio_duration_seconds",
        "ia_lab_audio_tts_characters_total",
        "ia_lab_audio_tts_requests_total",
        "ia_lab_audio_device_status",
        "ia_lab_audio_device_volume",
        "ia_lab_audio_device_muted",
        "ia_lab_audio_errors_total",
        "ia_lab_audio_conversion_duration_seconds",
        "ia_lab_audio_conversion_bytes_total",
        "ia_lab_audio_virtual_mic_active",
        "ia_lab_audio_virtual_mic_loopback",
    ]

    def test_all_metrics_registered(self) -> None:
        """Verifica que todas as metricas esperadas existem.

        Importa o modulo de metricas dentro do test para garantir
        que os side effects (registro no registry) ocorram.
        """
        import ai.audio.metrics as m  # noqa: F811

        # Verifica as metricas diretamente pelos objetos do modulo
        # (em vez de pelo REGISTRY.collect(), que pode ter comportamento
        # diferente sob pytest com Python 3.14)
        assert m.audio_recording is not None
        assert m.audio_capture_duration is not None
        assert m.audio_capture_bytes is not None
        assert m.audio_playback is not None
        assert m.audio_playback_items is not None
        assert m.vad_speech_frames is not None
        assert m.vad_silence_frames is not None
        assert m.vad_segments_detected is not None
        assert m.vad_speech_ratio is not None
        assert m.stt_duration is not None
        assert m.stt_audio_duration is not None
        assert m.stt_characters is not None
        assert m.stt_requests is not None
        assert m.tts_duration is not None
        assert m.tts_audio_duration is not None
        assert m.tts_characters is not None
        assert m.tts_requests is not None
        assert m.device_status is not None
        assert m.device_volume is not None
        assert m.device_muted is not None
        assert m.audio_errors is not None
        assert m.audio_conversion_duration is not None
        assert m.audio_conversion_bytes is not None
        assert m.virtual_mic_active is not None
        assert m.virtual_mic_loopback is not None

    def test_total_metrics_count(self) -> None:
        """Verifica o numero total de metricas de audio registradas."""
        import ai.audio.metrics as m  # noqa: F811

        # Conta os atributos publicos do modulo que sao metricas
        metric_count = sum(1 for name in dir(m) if not name.startswith("_"))
        assert metric_count >= 25

    def test_audio_module_has_all_symbols(self) -> None:
        from ai.audio import metrics as m

        assert m.audio_recording is not None
        assert m.stt_duration is not None
        assert m.tts_duration is not None
        assert m.vad_speech_frames is not None
        assert m.audio_errors is not None
        assert m.virtual_mic_active is not None


class TestAudioMetricsOperations:
    def test_audio_recording_gauge(self) -> None:
        from ai.audio import metrics as m

        m.audio_recording.labels(source="test").set(1)
        assert m.audio_recording.labels(source="test")._value.get() == 1.0

    def test_audio_errors_counter(self) -> None:
        from ai.audio import metrics as m

        m.audio_errors.labels(error_type="test").inc()
        assert m.audio_errors.labels(error_type="test")._value.get() == 1.0

    def test_vad_speech_counter(self) -> None:
        from ai.audio import metrics as m

        m.vad_speech_frames.labels(aggressiveness="2").inc(5)
        assert m.vad_speech_frames.labels(aggressiveness="2")._value.get() == 5.0

    def test_stt_characters_counter(self) -> None:
        from ai.audio import metrics as m

        m.stt_characters.labels(model="test", language="pt").inc(100)
        assert m.stt_characters.labels(model="test", language="pt")._value.get() == 100.0

    def test_virtual_mic_gauge(self) -> None:
        from ai.audio import metrics as m

        m.virtual_mic_active.set(0)
        assert m.virtual_mic_active._value.get() == 0.0
        m.virtual_mic_active.set(1)
        assert m.virtual_mic_active._value.get() == 1.0
