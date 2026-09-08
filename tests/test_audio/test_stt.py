"""Testes do SpeechToText (transcricao de audio para texto).

Testa criacao, propriedades, is_available, e tratamento de erros.
Modelo real nao e carregado — usa mocks para speechbrain.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai.audio.exceptions import STTError
from ai.audio.stt import SpeechToText

from .conftest import MockSubprocessResult


class TestSpeechToTextCreation:
    def test_create_with_defaults(self) -> None:
        stt = SpeechToText()
        assert "speechbrain" in stt.model_name
        assert stt.device == "cpu"
        assert stt.language == "pt"
        assert stt.is_model_loaded is False

    def test_create_with_custom_params(self) -> None:
        stt = SpeechToText(model="custom-model", device="cuda", language="en")
        assert stt.model_name == "custom-model"
        assert stt.device == "cuda"
        assert stt.language == "en"

    def test_properties(self) -> None:
        stt = SpeechToText()
        assert hasattr(stt, "model_name")
        assert hasattr(stt, "device")
        assert hasattr(stt, "language")
        assert hasattr(stt, "is_model_loaded")


class TestSpeechToTextModelLoading:
    def test_load_model_success(self) -> None:
        pytest.importorskip("speechbrain")
        with patch("speechbrain.inference.ASR.EncoderASR"):
            stt = SpeechToText()
            result = stt.load_model()
            assert result is True

    def test_load_model_import_error(self) -> None:
        stt = SpeechToText()
        with patch("importlib.import_module", side_effect=ImportError("no module")):
            result = stt.load_model()
            assert result is False

    def test_load_model_twice(self) -> None:
        pytest.importorskip("speechbrain")
        with patch("speechbrain.inference.ASR.EncoderASR"):
            stt = SpeechToText()
            r1 = stt.load_model()
            r2 = stt.load_model()
            assert r1 is True
            assert r2 is True

    def test_unload_model(self) -> None:
        stt = SpeechToText()
        stt._model = MagicMock()
        stt.unload_model()
        assert stt.is_model_loaded is False


class TestSpeechToTextIsAvailable:
    def test_is_available_returns_bool(self) -> None:
        stt = SpeechToText()
        result = stt.is_available()
        assert isinstance(result, bool)


class TestSpeechToTextTranscribe:
    def test_transcribe_empty(self) -> None:
        stt = SpeechToText()
        result = stt.transcribe(b"")
        assert result == ""

    def test_transcribe_too_short(self) -> None:
        stt = SpeechToText()
        result = stt.transcribe(b"\x00\x01" * 50)  # 100 bytes < 320
        assert result == ""

    def test_transcribe_raises_without_model(self) -> None:
        """Transcrever sem speechbrain instalado deve levantar STTError."""
        stt = SpeechToText()
        audio = b"\x00\x01" * 1000
        with (
            patch("importlib.import_module", side_effect=ImportError("no module")),
            pytest.raises(STTError),
        ):
            stt.transcribe(audio)

    def test_transcribe_file_not_found(self) -> None:
        stt = SpeechToText()
        with pytest.raises(STTError):
            stt.transcribe_file("/nonexistent/file.wav")

    def test_transcribe_file_with_ffmpeg(self, tmp_dir: Path) -> None:
        """Se ffmpeg falhar na conversao, deve levantar STTError."""
        audio_file = tmp_dir / "test.wav"
        audio_file.write_bytes(b"\x00" * 100)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=1, stderr=b"ffmpeg error")
            stt = SpeechToText()
            with pytest.raises(STTError):
                stt.transcribe_file(str(audio_file))

    def test_transcribe_file_ffmpeg_not_found(self, tmp_dir: Path) -> None:
        audio_file = tmp_dir / "test.wav"
        audio_file.write_bytes(b"\x00" * 100)

        with patch("subprocess.run", side_effect=FileNotFoundError):
            stt = SpeechToText()
            with pytest.raises(STTError):
                stt.transcribe_file(str(audio_file))
