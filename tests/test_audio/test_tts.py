"""Testes do TextToSpeech (sintese de texto para audio).

Testa criacao, propriedades, sintese (mockada), cache, gestao de voz.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from ai.audio.exceptions import TTSError
from ai.audio.tts import TextToSpeech

from .conftest import MockSubprocessResult


class TestTextToSpeechCreation:
    def test_create_with_defaults(self) -> None:
        tts = TextToSpeech()
        assert tts.engine == "espeak"
        assert tts.voice == "pt-br"
        assert tts.rate == 160
        assert tts.volume == 200

    def test_create_with_custom_params(self) -> None:
        tts = TextToSpeech(engine="edge-tts", voice="pt-BR-AntonioNeural", rate=200, volume=150)
        assert tts.engine == "edge-tts"
        assert tts.voice == "pt-BR-AntonioNeural"
        assert tts.rate == 200
        assert tts.volume == 150

    def test_properties(self) -> None:
        tts = TextToSpeech()
        assert hasattr(tts, "engine")
        assert hasattr(tts, "voice")
        assert hasattr(tts, "rate")
        assert hasattr(tts, "volume")


class TestTextToSpeechProperties:
    """Propriedades e setters com validacao."""

    def test_engine_setter_valid(self) -> None:
        tts = TextToSpeech()
        tts.engine = "edge-tts"
        assert tts.engine == "edge-tts"

    def test_engine_setter_invalid(self) -> None:
        tts = TextToSpeech()
        with pytest.raises(TTSError):
            tts.engine = "invalid-engine"

    def test_voice_setter(self) -> None:
        tts = TextToSpeech()
        tts.voice = "en-us"
        assert tts.voice == "en-us"

    def test_rate_setter_clamps(self) -> None:
        tts = TextToSpeech()
        tts.rate = 10
        assert tts.rate == 80
        tts.rate = 1000
        assert tts.rate == 450

    def test_volume_setter_clamps(self) -> None:
        tts = TextToSpeech()
        tts.volume = -10
        assert tts.volume == 0
        tts.volume = 500
        assert tts.volume == 200


class TestTextToSpeechCache:
    """Gerenciamento de cache LRU."""

    def test_cache_enabled_by_default(self) -> None:
        tts = TextToSpeech()
        assert tts.is_cache_enabled is True

    def test_enable_disable_cache(self) -> None:
        tts = TextToSpeech()
        tts.disable_cache()
        assert tts.is_cache_enabled is False
        tts.enable_cache()
        assert tts.is_cache_enabled is True

    def test_clear_cache(self) -> None:
        tts = TextToSpeech()
        tts.clear_cache()
        assert tts.cache_size == 0


class TestTextToSpeechSynthesize:
    """Sintese de texto para audio (com mocks)."""

    def test_synthesize_empty_text(self) -> None:
        tts = TextToSpeech()
        result = tts.synthesize("")
        assert result == b""

    def test_synthesize_whitespace(self) -> None:
        tts = TextToSpeech()
        result = tts.synthesize("   ")
        assert result == b""

    def test_synthesize_espeak_not_found(self) -> None:
        """Sem espeak e sem edge-tts funcional → TTSError."""
        with (
            patch("shutil.which", return_value=None),
            patch.object(
                TextToSpeech, "_synthesize_edge", side_effect=TTSError("edge indisponível", "teste")
            ),
        ):
            tts = TextToSpeech()
            with pytest.raises(TTSError):
                tts.synthesize("ola mundo")

    def test_synthesize_espeak_fallback_to_edge(self) -> None:
        """Sem espeak, mas com edge-tts funcional → usa edge-tts (fallback)."""
        with (
            patch("shutil.which", return_value=None),
            patch.object(TextToSpeech, "_synthesize_edge", return_value=b"\x00\x01" * 100),
        ):
            tts = TextToSpeech()
            result = tts.synthesize("ola mundo")
            assert result == b"\x00\x01" * 100
            assert tts.last_engine == "edge-tts"

    def test_synthesize_edge_voice_resolved(self) -> None:
        """Voz espeak ('pt-br') é mapeada para voz edge-tts válida."""
        tts = TextToSpeech()
        assert tts._resolve_edge_voice("pt-br") == "pt-BR-AntonioNeural"
        assert tts._resolve_edge_voice("en-us") == "en-US-AriaNeural"
        assert tts._resolve_edge_voice("pt-BR-AntonioNeural") == "pt-BR-AntonioNeural"


class TestTextToSpeechSynthesizeToFile:
    """Sintese com salvamento em arquivo."""

    def test_synthesize_to_file_success(self, tmp_dir: Path) -> None:
        output = tmp_dir / "output.wav"

        with (
            patch.object(TextToSpeech, "synthesize", return_value=b"\x00\x01" * 100),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MockSubprocessResult(returncode=0)
            tts = TextToSpeech()
            result = tts.synthesize_to_file("ola mundo", str(output))
            assert str(output) in result

    def test_synthesize_to_file_ffmpeg_fallback(self, tmp_dir: Path) -> None:
        """Se ffmpeg falhar, deve salvar como .raw."""
        output = tmp_dir / "output.wav"

        with (
            patch.object(TextToSpeech, "synthesize", return_value=b"\x00\x01" * 100),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            tts = TextToSpeech()
            result = tts.synthesize_to_file("ola mundo", str(output))
            assert result.endswith(".raw")


class TestTextToSpeechIsAvailable:
    """Disponibilidade dos engines."""

    def test_is_available_espeak_found(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/espeak-ng"):
            tts = TextToSpeech(engine="espeak")
            assert tts.is_available() is True

    def test_is_available_espeak_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            tts = TextToSpeech(engine="espeak")
            assert tts.is_available() is False
