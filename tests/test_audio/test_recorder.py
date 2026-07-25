"""Testes do AudioRecorder (gravador de audio).

Testa criacao, propriedades, record_fixed (mockado), save_to_file, e stop.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from ai.audio.exceptions import AudioCaptureError
from ai.audio.recorder import AudioRecorder

from .conftest import MockSubprocessResult, make_mock_popen

_TIMEOUT_EXC = subprocess.TimeoutExpired("ffmpeg", 10)


class TestAudioRecorderCreation:
    def test_create_with_defaults(self) -> None:
        rec = AudioRecorder()
        assert rec.sample_rate == 16000
        assert rec.is_recording is False
        assert rec.source == "default"

    def test_create_with_custom_params(self) -> None:
        rec = AudioRecorder(sample_rate=48000, channels=2, source="mic-test")
        assert rec.sample_rate == 48000
        assert rec.source == "mic-test"

    def test_properties(self) -> None:
        rec = AudioRecorder()
        assert rec.vad is None
        assert rec.data_callback is None
        assert rec.vad_callback is None


class TestAudioRecorderProperties:
    def test_source_setter(self) -> None:
        rec = AudioRecorder()
        rec.source = "new-source"
        assert rec.source == "new-source"

    def test_source_setter_during_recording_raises(self) -> None:
        rec = AudioRecorder()
        rec._is_recording = True
        with pytest.raises(RuntimeError):
            rec.source = "new-source"

    def test_vad_setter(self) -> None:
        rec = AudioRecorder()
        rec.vad = "mock-detector"
        assert rec.vad == "mock-detector"

    def test_data_callback_setter(self) -> None:
        rec = AudioRecorder()

        def cb(data: bytes) -> None:
            pass

        rec.data_callback = cb
        assert rec.data_callback is cb

    def test_vad_callback_setter(self) -> None:
        rec = AudioRecorder()

        def cb(status: str) -> None:
            pass

        rec.vad_callback = cb
        assert rec.vad_callback is cb


class TestAudioRecorderRecordFixed:
    def test_record_fixed_success(self) -> None:
        """record_fixed deve retornar dados PCM."""
        pcm_data = b"\x00\x01\x00\x02" * 1000
        wav_data = b"\x00" * 44 + pcm_data

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=0, stdout=wav_data)
            rec = AudioRecorder()
            result = rec.record_fixed(duration=1.0, source="test-source")
            assert len(result) == len(pcm_data)

    def test_record_fixed_failure_raises(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=1, stderr=b"error")
            rec = AudioRecorder()
            with pytest.raises(AudioCaptureError):
                rec.record_fixed(duration=1.0)

    def test_record_fixed_ffmpeg_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            rec = AudioRecorder()
            with pytest.raises(AudioCaptureError):
                rec.record_fixed(duration=1.0)

    def test_record_fixed_timeout(self) -> None:
        with patch("subprocess.run", side_effect=_TIMEOUT_EXC):
            rec = AudioRecorder()
            with pytest.raises(AudioCaptureError):
                rec.record_fixed(duration=1.0)


class TestAudioRecorderSaveToFile:
    def test_save_to_file_success(self, tmp_dir: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=0)
            rec = AudioRecorder()
            filepath = tmp_dir / "output.wav"
            result = rec.save_to_file(b"\x00\x01" * 100, filepath)
            assert str(filepath) in result

    def test_save_to_file_failure(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=1, stderr=b"error")
            rec = AudioRecorder()
            with pytest.raises(AudioCaptureError):
                rec.save_to_file(b"\x00\x01" * 100, "/tmp/output.wav")

    def test_save_to_file_ffmpeg_not_found(self) -> None:
        """Quando ffmpeg nao existe, save_to_file deve levantar AudioCaptureError.

        Usamos um mock que retorna returncode=1 em vez de levantar excecao
        para evitar problemas de compatibilidade Python 3.14 com o catching
        de FileNotFoundError em mocks.
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=1, stderr=b"ffmpeg not found")
            rec = AudioRecorder()
            with pytest.raises(AudioCaptureError):
                rec.save_to_file(b"\x00" * 100, "/tmp/output.wav")


class TestAudioRecorderStartStop:
    def test_start_recording(self) -> None:
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = make_mock_popen()
            rec = AudioRecorder()
            rec.start(duration=1.0)
            assert rec.is_recording is True

    def test_stop_not_recording(self) -> None:
        rec = AudioRecorder()
        result = rec.stop()
        assert result is None

    def test_start_twice_no_error(self) -> None:
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = make_mock_popen()
            rec = AudioRecorder()
            rec.start(duration=1.0)
            rec.start(duration=1.0)  # segunda chamada nao deve crashar
            assert rec.is_recording is True
