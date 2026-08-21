"""Testes da hierarquia de exceções do módulo de áudio.

Verifica:
- Todos os 9 tipos de exceção existem e são subclasses de AudioError
- A mensagem é formatada corretamente (com/sem detalhes)
- Cada exceção pode ser instanciada e capturada como AudioError
"""

from __future__ import annotations

import pytest
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

# ── Lista completa de exceções ────────────────────────────────────────────────

ALL_EXCEPTIONS = [
    AudioError,
    AudioDeviceError,
    AudioCaptureError,
    AudioPlaybackError,
    AudioFormatError,
    AudioConversionError,
    VADError,
    STTError,
    TTSError,
    AudioConfigError,
]


class TestAudioExceptionHierarchy:
    """Verifica a hierarquia: todas herdam de AudioError."""

    @pytest.mark.parametrize("exc_cls", ALL_EXCEPTIONS)
    def test_inherits_from_audio_error(self, exc_cls: type) -> None:
        assert issubclass(exc_cls, AudioError)

    def test_audio_error_is_base(self) -> None:
        assert issubclass(AudioError, Exception)


class TestAudioErrorMessage:
    """Verifica formatação de mensagens."""

    def test_message_only(self) -> None:
        err = AudioError("Falha no áudio")
        assert str(err) == "Falha no áudio"
        assert err.message == "Falha no áudio"
        assert err.details is None

    def test_message_with_details(self) -> None:
        err = AudioError("Falha no áudio", "Microfone não encontrado")
        assert "Falha no áudio" in str(err)
        assert "Microfone não encontrado" in str(err)

    def test_device_error(self) -> None:
        err = AudioDeviceError("Dispositivo não encontrado", "source=mic1")
        assert "Dispositivo não encontrado" in str(err)
        assert "source=mic1" in str(err)
        assert isinstance(err, AudioError)

    def test_capture_error(self) -> None:
        err = AudioCaptureError("Falha ao capturar", "ffmpeg retornou 1")
        assert "Falha ao capturar" in str(err)

    def test_playback_error(self) -> None:
        err = AudioPlaybackError("Falha ao reproduzir", "sink não encontrado")
        assert "Falha ao reproduzir" in str(err)

    def test_format_error(self) -> None:
        err = AudioFormatError("Formato não suportado", ".xyz")
        assert "Formato não suportado" in str(err)

    def test_conversion_error(self) -> None:
        err = AudioConversionError("Conversão falhou", "codec não encontrado")
        assert "Conversão falhou" in str(err)

    def test_vad_error(self) -> None:
        err = VADError("VAD falhou", "frame_size inválido")
        assert "VAD falhou" in str(err)

    def test_stt_error(self) -> None:
        err = STTError("Transcrição falhou", "modelo não carregado")
        assert "Transcrição falhou" in str(err)

    def test_tts_error(self) -> None:
        err = TTSError("Síntese falhou", "espeak não encontrado")
        assert "Síntese falhou" in str(err)

    def test_config_error(self) -> None:
        err = AudioConfigError("Config inválida", "sample_rate=0")
        assert "Config inválida" in str(err)

    def test_empty_details(self) -> None:
        err = AudioError("Teste", "")
        assert str(err) == "Teste"
        assert err.details == ""


class TestAudioErrorRaiseAndCatch:
    """Verifica que exceções específicas podem ser capturadas como AudioError."""

    def test_catch_device_as_audio_error(self) -> None:
        with pytest.raises(AudioError) as exc_info:
            raise AudioDeviceError("teste")
        assert isinstance(exc_info.value, AudioDeviceError)

    def test_catch_stt_as_audio_error(self) -> None:
        with pytest.raises(AudioError):
            raise STTError("erro stt")

    def test_catch_tts_as_audio_error(self) -> None:
        with pytest.raises(AudioError):
            raise TTSError("erro tts")

    def test_catch_vad_as_audio_error(self) -> None:
        with pytest.raises(AudioError):
            raise VADError("erro vad")

    def test_catch_config_as_audio_error(self) -> None:
        with pytest.raises(AudioError):
            raise AudioConfigError("erro config")
