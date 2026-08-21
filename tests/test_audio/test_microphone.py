"""Testes do VirtualMicrophone (gerenciamento de microfone virtual PipeWire).

Testa criacao, propriedades, create/remove (mockado), status.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from ai.audio.exceptions import AudioDeviceError
from ai.audio.microphone import VirtualMicrophone

from .conftest import MockSubprocessResult


class TestVirtualMicrophoneCreation:
    def test_create_with_defaults(self) -> None:
        vmic = VirtualMicrophone()
        assert vmic.sink_name == "ia-lab-mic"
        assert vmic.description == "IA-Lab Microfone Virtual"
        assert vmic.is_active is False

    def test_create_with_custom_params(self) -> None:
        vmic = VirtualMicrophone(sink_name="custom-mic", description="Custom Mic")
        assert vmic.sink_name == "custom-mic"
        assert vmic.description == "Custom Mic"

    def test_source_name_property(self) -> None:
        vmic = VirtualMicrophone(sink_name="test-mic")
        assert vmic.source_name == "test-mic.monitor"


class TestVirtualMicrophoneCreate:
    """Criacao do microfone virtual."""

    def test_create_success(self) -> None:
        """Create com sucesso deve retornar True e ativar."""
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            # First call: pactl info (check_pipewire) -> ok
            # Second call: find modules (none) -> empty stdout
            # Third call: load-module null-sink -> returns index
            # Fourth call: get-default-sink -> returns a sink
            # Fifth call: load-module loopback -> returns index
            # Sixth call: pactl list sinks short -> contains sink name
            mock_run.side_effect = [
                MockSubprocessResult(returncode=0, stdout=""),  # check_pipewire
                MockSubprocessResult(returncode=0, stdout=""),  # cleanup_previous
                MockSubprocessResult(returncode=0, stdout="12345\n"),  # create null-sink
                MockSubprocessResult(returncode=0, stdout="default-sink\n"),  # get-default-sink
                MockSubprocessResult(returncode=0, stdout="12346\n"),  # create loopback
                MockSubprocessResult(returncode=0, stdout="ia-lab-mic\n"),  # sink_exists
            ]

            vmic = VirtualMicrophone()
            result = vmic.create()
            assert result is True
            assert vmic.is_active is True

    def test_create_pipewire_not_running(self) -> None:
        """Se PipeWire nao estiver rodando, deve levantar AudioDeviceError."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            vmic = VirtualMicrophone()
            with pytest.raises(AudioDeviceError):
                vmic.create()

    def test_create_already_active(self) -> None:
        """Create quando ja ativo deve retornar True sem recriar."""
        vmic = VirtualMicrophone()
        vmic._is_active = True
        result = vmic.create()
        assert result is True

    def test_create_null_sink_fails(self) -> None:
        """Se null-sink falhar, deve retornar False."""
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            mock_run.side_effect = [
                MockSubprocessResult(returncode=0, stdout=""),  # check_pipewire
                MockSubprocessResult(returncode=0, stdout=""),  # cleanup_previous
                MockSubprocessResult(returncode=1, stdout="", stderr="error"),  # null-sink fails
            ]

            vmic = VirtualMicrophone()
            result = vmic.create()
            assert result is False


class TestVirtualMicrophoneRemove:
    """Remocao do microfone virtual."""

    def test_remove_success(self) -> None:
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            # find_related_modules -> returns 2 modules
            # unload-module (2x)
            # sink_exists -> returns empty (removed)
            mock_run.side_effect = [
                MockSubprocessResult(returncode=0, stdout="12345\tnull-sink\n12346\tloopback\n"),
                MockSubprocessResult(returncode=0, stdout=""),
                MockSubprocessResult(returncode=0, stdout=""),
                MockSubprocessResult(returncode=0, stdout=""),  # sink not found
            ]

            vmic = VirtualMicrophone()
            vmic._is_active = True
            result = vmic.remove()
            assert result is True
            assert vmic.is_active is False

    def test_remove_no_modules(self) -> None:
        """Se nao houver modulos, deve retornar True."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(returncode=0, stdout="")

            vmic = VirtualMicrophone()
            result = vmic.remove()
            assert result is True


class TestVirtualMicrophoneStatus:
    """Status do microfone virtual."""

    def test_get_status_structure(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MockSubprocessResult(returncode=0, stdout=""),  # sink_exists -> not found
                MockSubprocessResult(returncode=0, stdout=""),  # find_related_modules
            ]

            vmic = VirtualMicrophone()
            status = vmic.get_status()

            assert "active" in status
            assert "sink_name" in status
            assert "source_name" in status
            assert "description" in status
            assert "sink_exists" in status
            assert "modules" in status

    def test_get_status_with_details(self) -> None:
        """Status deve incluir detalhes do sink quando ativo."""
        pactl_output = (
            "Sink #0\n"
            "\tName: ia-lab-mic\n"
            "\tDescription: IA-Lab Microfone Virtual\n"
            "\tState: IDLE\n"
            "\tMute: no\n"
            "\tVolume: front-left: 65536 / 100%\n"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MockSubprocessResult(returncode=0, stdout="ia-lab-mic\n"),  # sink_exists
                MockSubprocessResult(returncode=0, stdout="12345\n"),  # find_related_modules
                MockSubprocessResult(returncode=0, stdout=pactl_output),  # get_status details
            ]

            vmic = VirtualMicrophone()
            vmic._is_active = True
            status = vmic.get_status()

            assert status["sink_exists"] is True
            assert "details" in status
