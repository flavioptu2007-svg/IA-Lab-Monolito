"""Testes de configuração do módulo de áudio.

Verifica:
- AudioSettings carrega valores padrão
- AudioSettings respeita env vars IA_LAB_AUDIO_*
- Singleton get_audio_settings funciona
- Tipos dos campos estão corretos
"""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest

from ai.audio.settings import AudioSettings, audio_settings, get_audio_settings


class TestAudioSettingsDefaults:
    """Verifica valores padrão do AudioSettings."""

    def test_default_sample_rate(self) -> None:
        settings = AudioSettings()
        assert settings.sample_rate == 16000

    def test_default_channels(self) -> None:
        settings = AudioSettings()
        assert settings.channels == 1

    def test_default_sample_width(self) -> None:
        settings = AudioSettings()
        assert settings.sample_width == 16

    def test_default_vad_aggressiveness(self) -> None:
        settings = AudioSettings()
        assert settings.vad_aggressiveness == 2

    def test_default_vad_frame_ms(self) -> None:
        settings = AudioSettings()
        assert settings.vad_frame_ms == 30

    def test_default_input_device(self) -> None:
        settings = AudioSettings()
        assert settings.input_device == "default"

    def test_default_output_device(self) -> None:
        settings = AudioSettings()
        assert settings.output_device == "default"

    def test_default_stt_model(self) -> None:
        settings = AudioSettings()
        assert "speechbrain" in settings.stt_model

    def test_default_tts_engine(self) -> None:
        settings = AudioSettings()
        assert settings.tts_engine == "espeak"

    def test_default_record_temp_dir(self) -> None:
        settings = AudioSettings()
        assert settings.record_temp_dir == "/tmp/ia-lab-audio"

    def test_default_virtual_mic_name(self) -> None:
        settings = AudioSettings()
        assert settings.virtual_mic_name == "ia-lab-mic"

    def test_noise_gate_default(self) -> None:
        settings = AudioSettings()
        assert settings.noise_gate_threshold == -50.0

    def test_compressor_default(self) -> None:
        settings = AudioSettings()
        assert settings.compressor_ratio == 4.0


class TestAudioSettingsEnvOverride:
    """Verifica que env vars sobrescrevem os defaults."""

    ENV_VARS = {
        "IA_LAB_AUDIO_SAMPLE_RATE": "48000",
        "IA_LAB_AUDIO_CHANNELS": "2",
        "IA_LAB_AUDIO_INPUT_DEVICE": "mic-test",
        "IA_LAB_AUDIO_OUTPUT_DEVICE": "speaker-test",
        "IA_LAB_AUDIO_VAD_AGGRESSIVENESS": "3",
        "IA_LAB_AUDIO_VAD_FRAME_MS": "20",
        "IA_LAB_AUDIO_STT_MODEL": "custom-model",
        "IA_LAB_AUDIO_TTS_ENGINE": "edge-tts",
        "IA_LAB_AUDIO_TTS_VOICE": "pt-BR-TesteNeural",
        "IA_LAB_AUDIO_SAMPLE_WIDTH": "24",
        "IA_LAB_AUDIO_RECORD_TEMP_DIR": "/tmp/custom-audio",
        "IA_LAB_AUDIO_VIRTUAL_MIC_NAME": "custom-mic",
    }

    @pytest.fixture(autouse=True)
    def _set_env(self) -> Generator[None, None, None]:
        """Aplica env vars para cada teste e restaura depois."""
        original = {}
        for k, v in self.ENV_VARS.items():
            original[k] = os.environ.get(k)
            os.environ[k] = v
        yield
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_sample_rate_override(self) -> None:
        settings = AudioSettings()
        assert settings.sample_rate == 48000

    def test_channels_override(self) -> None:
        settings = AudioSettings()
        assert settings.channels == 2

    def test_input_device_override(self) -> None:
        settings = AudioSettings()
        assert settings.input_device == "mic-test"

    def test_output_device_override(self) -> None:
        settings = AudioSettings()
        assert settings.output_device == "speaker-test"

    def test_vad_aggressiveness_override(self) -> None:
        settings = AudioSettings()
        assert settings.vad_aggressiveness == 3

    def test_vad_frame_ms_override(self) -> None:
        settings = AudioSettings()
        assert settings.vad_frame_ms == 20

    def test_stt_model_override(self) -> None:
        settings = AudioSettings()
        assert settings.stt_model == "custom-model"

    def test_tts_engine_override(self) -> None:
        settings = AudioSettings()
        assert settings.tts_engine == "edge-tts"

    def test_tts_voice_override(self) -> None:
        settings = AudioSettings()
        assert settings.tts_voice == "pt-BR-TesteNeural"

    def test_virtual_mic_name_override(self) -> None:
        settings = AudioSettings()
        assert settings.virtual_mic_name == "custom-mic"

    def test_temp_dir_override(self) -> None:
        settings = AudioSettings()
        assert settings.record_temp_dir == "/tmp/custom-audio"


class TestAudioSettingsSingleton:
    """Verifica o singleton get_audio_settings."""

    def test_get_audio_settings_returns_instance(self) -> None:
        settings = get_audio_settings()
        assert isinstance(settings, AudioSettings)

    def test_audio_settings_module_var(self) -> None:
        assert isinstance(audio_settings, AudioSettings)

    def test_singleton_identity(self) -> None:
        assert get_audio_settings() is get_audio_settings()

    def test_cache_clear(self) -> None:
        get_audio_settings.cache_clear()
        s1 = get_audio_settings()
        s2 = get_audio_settings()
        assert s1 is s2


class TestAudioSettingsTypes:
    """Verifica que os tipos dos campos estão corretos."""

    def test_sample_rate_is_int(self) -> None:
        assert isinstance(audio_settings.sample_rate, int)

    def test_vad_aggressiveness_is_int(self) -> None:
        assert isinstance(audio_settings.vad_aggressiveness, int)

    def test_noise_gate_threshold_is_float(self) -> None:
        assert isinstance(audio_settings.noise_gate_threshold, float)

    def test_input_device_is_str(self) -> None:
        assert isinstance(audio_settings.input_device, str)

    def test_stt_timeout_is_float(self) -> None:
        assert isinstance(audio_settings.stt_timeout, float)

    def test_record_max_duration_is_int(self) -> None:
        assert isinstance(audio_settings.record_max_duration, int)
