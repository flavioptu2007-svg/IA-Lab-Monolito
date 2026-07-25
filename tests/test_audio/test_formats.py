"""Testes de deteccao e conversao de formatos de audio.

Testa:
- detect_format (por extensao, magic bytes)
- get_audio_info
- convert (conversao usando ffmpeg mockado)
- Funcoes especificas: to_wav, to_mp3, to_flac, to_pcm
- Extracao de metadados: get_duration, get_sample_rate, get_human_readable_info
"""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from ai.audio.exceptions import AudioConversionError, AudioFormatError
from ai.audio.formats import (
    SUPPORTED_FORMATS,
    convert,
    detect_format,
    get_audio_info,
    get_duration,
    get_human_readable_info,
    get_sample_rate,
    to_flac,
    to_mp3,
    to_pcm,
    to_wav,
)

from .conftest import MockSubprocessResult


class TestDetectFormat:
    """Deteccao de formato por extensao e magic bytes."""

    def test_detect_by_extension_wav(self) -> None:
        assert detect_format("audio.wav") == ".wav"

    def test_detect_by_extension_mp3(self) -> None:
        assert detect_format("audio.mp3") == ".mp3"

    def test_detect_by_extension_flac(self) -> None:
        assert detect_format("audio.flac") == ".flac"

    def test_detect_by_extension_ogg(self) -> None:
        assert detect_format("audio.ogg") == ".ogg"

    def test_detect_by_extension_opus(self) -> None:
        assert detect_format("audio.opus") == ".opus"

    def test_detect_by_extension_aac(self) -> None:
        assert detect_format("audio.aac") == ".aac"

    def test_detect_by_extension_m4a(self) -> None:
        assert detect_format("audio.m4a") == ".m4a"

    def test_detect_by_magic_wav(self, small_wav_header: bytes) -> None:
        assert detect_format(small_wav_header) == ".wav"

    def test_detect_by_magic_flac(self) -> None:
        assert detect_format(b"fLaC" + b"\x00" * 20) == ".flac"

    def test_detect_by_magic_ogg(self) -> None:
        assert detect_format(b"OggS" + b"\x00" * 20) == ".ogg"

    def test_detect_by_magic_mp3(self) -> None:
        assert detect_format(b"\xff\xfb" + b"\x00" * 20) == ".mp3"

    def test_unsupported_format_raises(self) -> None:
        with pytest.raises(AudioFormatError):
            detect_format(b"\x00\x01\x02\x03" * 16)

    def test_supported_formats_list(self) -> None:
        """Verifica que todos os formatos esperados tem entrada."""
        expected = {
            ".wav",
            ".mp3",
            ".flac",
            ".ogg",
            ".opus",
            ".aac",
            ".m4a",
            ".wma",
            ".pcm",
            ".raw",
        }
        for fmt in expected:
            assert fmt in SUPPORTED_FORMATS, f"{fmt} nao esta em SUPPORTED_FORMATS"


class TestDetectFormatFromFile:
    """Deteccao a partir de arquivos reais (criados em tmp_dir)."""

    def test_detect_existing_file_by_extension(self, tmp_dir: Path) -> None:
        """Cria um arquivo e detecta pela extensao (fallback quando magic falha)."""
        filepath = tmp_dir / "audio.wav"
        filepath.write_bytes(b"\x00\x01\x02\x03" * 100)  # sem magic WAV valido
        # detect_format vai tentar magic (falha), depois extensao (ok)
        result = detect_format(str(filepath))
        assert result == ".wav"

    def test_detect_by_magic_from_file(self, tmp_dir: Path) -> None:
        """Cria arquivo com magic bytes e detecta por eles."""
        filepath = tmp_dir / "test.flac"
        filepath.write_bytes(b"fLaC" + b"\x00" * 100)
        result = detect_format(str(filepath))
        assert result == ".flac"

    def test_detect_non_existent_file_by_extension(self) -> None:
        """Arquivo inexistente com extensao conhecida usa a extensao."""
        # detect_format para string: tenta abrir como arquivo, se falhar
        # usa a extensao
        result = detect_format("nonexistent/test.ogg")
        assert result == ".ogg"


class TestGetAudioInfo:
    """Extracao de metadados de arquivos de audio."""

    @pytest.fixture
    def mock_ffprobe(self) -> Generator[MagicMock, None, None]:
        mock_data = {
            "format": {"duration": "10.5", "bit_rate": "128000", "format_name": "mp3"},
            "streams": [
                {"codec_type": "audio", "codec_name": "mp3", "sample_rate": "44100", "channels": 2}
            ],
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=0, stdout=json.dumps(mock_data))
            yield mock_run

    def test_get_audio_info_basic(self, tmp_dir: Path, mock_ffprobe: MagicMock) -> None:
        filepath = tmp_dir / "test.mp3"
        filepath.write_bytes(b"dummy")

        info = get_audio_info(str(filepath))
        assert info["duration_sec"] == 10.5
        assert info["sample_rate"] == 44100
        assert info["channels"] == 2
        assert info["codec"] == "mp3"
        assert info["bitrate"] == 128000

    def test_get_audio_info_file_not_found(self) -> None:
        with pytest.raises(AudioFormatError):
            get_audio_info("/nonexistent/file.wav")

    def test_get_audio_info_filename_and_size(self, tmp_dir: Path) -> None:
        filepath = tmp_dir / "test.wav"
        filepath.write_bytes(b"data" * 100)

        info = get_audio_info(str(filepath))
        assert info["filename"] == "test.wav"
        assert info["size_bytes"] == 400
        assert info["format"] == ".wav"


class TestConvert:
    """Conversao entre formatos usando ffmpeg mockado."""

    @pytest.fixture
    def mock_ffmpeg(self) -> Generator[MagicMock, None, None]:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(
                returncode=0, stdout=b"\x00\x01\x02\x03" * 100
            )
            yield mock_run

    def test_convert_pcm_to_wav(self, mock_ffmpeg: MagicMock) -> None:
        result = convert(b"\x00\x00" * 100, ".wav")
        assert result is not None
        assert len(result) > 0

    def test_convert_file_to_mp3(self, tmp_dir: Path, mock_ffmpeg: MagicMock) -> None:
        input_file = tmp_dir / "input.wav"
        input_file.write_bytes(b"RIFF" + b"\x00" * 100)

        output_path = str(tmp_dir / "output.mp3")
        result = convert(str(input_file), ".mp3", output_path=output_path)
        assert result == b""  # retorna vazio quando salva em arquivo

    def test_convert_with_custom_params(self, mock_ffmpeg: MagicMock) -> None:
        result = convert(b"\x00\x00" * 100, ".flac", sample_rate=44100, channels=2, bitrate="320k")
        assert result is not None

    def test_convert_failure_raises(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(
                returncode=1, stderr=b"Unknown encoder 'invalid'"
            )
            with pytest.raises(AudioConversionError):
                convert(b"\x00\x00" * 100, ".wav")

    def test_convert_ffmpeg_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(AudioConversionError):
                convert(b"\x00\x00" * 100, ".wav")

    def test_convert_timeout(self) -> None:
        with patch("subprocess.run", side_effect=TimeoutError), pytest.raises(Exception):
            convert(b"\x00\x00" * 100, ".wav")


class TestSpecificConversions:
    """Funcoes de conversao especificas (to_wav, to_mp3, etc.)."""

    def test_to_wav(self) -> None:
        with patch("ai.audio.formats.convert") as mock_convert:
            mock_convert.return_value = b"wav-data"
            result = to_wav(b"\x00\x00" * 100)
            assert result == b"wav-data"

    def test_to_mp3(self) -> None:
        with patch("ai.audio.formats.convert") as mock_convert:
            mock_convert.return_value = b"mp3-data"
            result = to_mp3(b"\x00\x00" * 100, bitrate="128k")
            assert result == b"mp3-data"

    def test_to_flac(self) -> None:
        with patch("ai.audio.formats.convert") as mock_convert:
            mock_convert.return_value = b"flac-data"
            result = to_flac(b"\x00\x00" * 100)
            assert result == b"flac-data"

    def test_to_pcm(self) -> None:
        with patch("ai.audio.formats.convert") as mock_convert:
            mock_convert.return_value = b"pcm-data"
            result = to_pcm(b"\x00\x00" * 100)
            assert result == b"pcm-data"

    def test_to_pcm_passes_channels_1(self) -> None:
        """to_pcm deve passar channels=1 para convert()."""
        with patch("ai.audio.formats.convert") as mock_convert:
            mock_convert.return_value = b"pcm-data"
            to_pcm(b"\x00\x00" * 100)
            kwargs = mock_convert.call_args[1]
            assert kwargs.get("channels") == 1


class TestMetadataHelpers:
    """Funcoes auxiliares de metadados."""

    def test_get_duration(self) -> None:
        with patch("ai.audio.formats.get_audio_info") as mock_info:
            mock_info.return_value = {"duration_sec": 42.5}
            duration = get_duration("test.mp3")
            assert duration == 42.5

    def test_get_duration_default(self) -> None:
        with patch("ai.audio.formats.get_audio_info") as mock_info:
            mock_info.return_value = {}
            duration = get_duration("test.mp3")
            assert duration == 0

    def test_get_sample_rate(self) -> None:
        with patch("ai.audio.formats.get_audio_info") as mock_info:
            mock_info.return_value = {"sample_rate": 48000}
            sr = get_sample_rate("test.mp3")
            assert sr == 48000

    def test_get_human_readable_info(self) -> None:
        with patch("ai.audio.formats.get_audio_info") as mock_info:
            mock_info.return_value = {
                "filename": "song.mp3",
                "format": ".mp3",
                "codec": "mp3",
                "duration_sec": 180,
                "sample_rate": 44100,
                "channels": 2,
                "bitrate": 128000,
                "size_bytes": 2 * 1024 * 1024,
            }
            text = get_human_readable_info("song.mp3")
            assert "song.mp3" in text
            assert "03:00" in text
            assert "44100" in text
            assert "2.0 MB" in text
