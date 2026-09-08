"""Testes do AudioEngine (motor principal de áudio).

Testa:
- Criação e inicialização
- Dependências (check_dependencies)
- Listagem de dispositivos (list_sources, list_sinks)
- get_default_source / get_default_sink
- get_status
- shutdown

Todas as operações externas (subprocess, shutil) são mockadas.
"""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import patch

import pytest

from ai.audio.core import AudioDeviceError, AudioEngine

from .conftest import MockSubprocessResult


class TestAudioEngineCreation:
    """Criação do AudioEngine."""

    def test_create_with_defaults(self) -> None:
        engine = AudioEngine()
        assert engine.sample_rate == 16000
        assert engine.is_initialized is False

    def test_create_with_custom_settings(self, isolated_audio_settings: Any) -> None:
        engine = AudioEngine(settings=isolated_audio_settings)
        assert engine.settings is isolated_audio_settings

    def test_properties(self) -> None:
        engine = AudioEngine()
        assert hasattr(engine, "settings")
        assert hasattr(engine, "is_initialized")
        assert hasattr(engine, "sample_rate")

    def test_get_default_source(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(
                returncode=0, stdout="alsa_input.pci-0000_00_1f.3.analog-stereo\n"
            )
            engine = AudioEngine()
            source = engine.get_default_source()
            assert source == "alsa_input.pci-0000_00_1f.3.analog-stereo"

    def test_get_default_source_error(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=1, stdout="")
            engine = AudioEngine()
            source = engine.get_default_source()
            assert source is None

    def test_get_default_sink(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(
                returncode=0, stdout="alsa_output.pci-0000_00_1f.3.analog-stereo\n"
            )
            engine = AudioEngine()
            sink = engine.get_default_sink()
            assert sink == "alsa_output.pci-0000_00_1f.3.analog-stereo"

    def test_get_default_sink_error(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=1, stdout="")
            engine = AudioEngine()
            sink = engine.get_default_sink()
            assert sink is None


class TestAudioEngineListDevices:
    """Listagem de dispositivos."""

    def test_list_sources(self) -> None:
        pactl_output = (
            "0\talsa_input.pci-0000_00_1f.3.analog-stereo\tRUNNING\n1\tia-lab-mic.monitor\tIDLE\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=0, stdout=pactl_output)
            engine = AudioEngine()
            sources = engine.list_sources()
            assert len(sources) == 2
            assert sources[0]["name"] == "alsa_input.pci-0000_00_1f.3.analog-stereo"
            assert sources[1]["name"] == "ia-lab-mic.monitor"

    def test_list_sinks(self) -> None:
        pactl_output = (
            "0\talsa_output.pci-0000_00_1f.3.analog-stereo\tRUNNING\n1\tia-lab-mic\tIDLE\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=0, stdout=pactl_output)
            engine = AudioEngine()
            sinks = engine.list_sinks()
            assert len(sinks) == 2
            assert sinks[0]["name"] == "alsa_output.pci-0000_00_1f.3.analog-stereo"

    def test_list_devices_empty(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=0, stdout="")
            engine = AudioEngine()
            devices = engine.list_sources()
            assert devices == []

    def test_list_devices_file_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            engine = AudioEngine()
            sources = engine.list_sources()
            assert sources == []

    def test_list_devices_timeout(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pactl", 3)):
            engine = AudioEngine()
            sinks = engine.list_sinks()
            assert sinks == []


class TestAudioEngineDependencies:
    """Verificação de dependências."""

    def test_dependencies_all_found(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/tool"):
            engine = AudioEngine()
            result = engine._which("pactl")
            assert result == "/usr/bin/tool"

    def test_dependencies_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            engine = AudioEngine()
            result = engine._which("sox")
            assert result is None


class TestAudioEngineInitializeAndShutdown:
    """Inicialização e finalização do AudioEngine."""

    @pytest.mark.asyncio
    async def test_initialize_success(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MockSubprocessResult(
                returncode=0, stdout="pci-0000_00_1f.3.analog-stereo\n"
            )
            engine = AudioEngine()
            result = await engine.initialize()
            assert result is True
            assert engine.is_initialized is True

    @pytest.mark.asyncio
    async def test_initialize_without_devices_raises(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MockSubprocessResult(returncode=1, stdout="")
            engine = AudioEngine()
            with pytest.raises(AudioDeviceError):
                await engine.initialize()
            assert engine.is_initialized is False

    @pytest.mark.asyncio
    async def test_initialize_twice(self) -> None:
        """Inicializar duas vezes não deve causar erro."""
        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MockSubprocessResult(returncode=0, stdout="device\n")
            engine = AudioEngine()
            r1 = await engine.initialize()
            r2 = await engine.initialize()
            assert r1 is True
            assert r2 is True

    @pytest.mark.asyncio
    async def test_shutdown(self) -> None:
        engine = AudioEngine()
        engine._initialized = True
        await engine.shutdown()
        assert engine.is_initialized is False


class TestAudioEngineStatus:
    """Status do AudioEngine."""

    @pytest.mark.asyncio
    async def test_get_status_structure(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MockSubprocessResult(returncode=0, stdout="default-device\n")
            engine = AudioEngine()
            engine._initialized = True
            status = await engine.get_status()

            assert "initialized" in status
            assert "sample_rate" in status
            assert "devices" in status
            assert "tools" in status
            assert "temp_dir" in status
            assert "vad_aggressiveness" in status
            assert "stt_model" in status
            assert "tts_engine" in status

    @pytest.mark.asyncio
    async def test_get_status_values(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MockSubprocessResult(returncode=0, stdout="default-device\n")
            engine = AudioEngine()
            engine._initialized = True
            status = await engine.get_status()

            assert status["initialized"] is True
            assert status["sample_rate"] == 16000
            assert status["tools"]["pactl"] is True
            assert status["tools"]["ffmpeg"] is True
            assert status["devices"]["default_source"] is not None
