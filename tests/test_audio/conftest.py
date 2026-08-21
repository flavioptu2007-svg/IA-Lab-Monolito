"""Fixtures compartilhadas para os testes do modulo de audio.

Fornece audio sintetico, configuracoes isoladas e helpers de mock.
"""

from __future__ import annotations

import struct
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from ai.audio.settings import AudioSettings

# ── Helpers de mock ───────────────────────────────────────────────────────────


class MockSubprocessResult:
    """Simula subprocess.CompletedProcess para testes.

    Mantem os tipos como passados — str ou bytes — para que o teste
    decida o que e apropriado para cada cenario.
    """

    def __init__(
        self, returncode: int = 0, stdout: str | bytes = "", stderr: str | bytes = ""
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def make_mock_popen(stdout_data: bytes = b"") -> MagicMock:
    """Cria um mock de subprocess.Popen com atributos padrao."""
    proc = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.read.return_value = stdout_data
    proc.stdin = MagicMock()
    proc.pid = 12345
    proc.returncode = 0
    return proc


# ── Diretorio temporario (evita tmp_path do pytest, que tem bugs com asyncio) ──


@pytest.fixture
def tmp_dir() -> Generator[Path, None, None]:
    """Cria e limpa um diretorio temporario para cada teste."""
    d = Path(tempfile.mkdtemp(prefix="ia_lab_test_"))
    yield d
    import shutil

    shutil.rmtree(d, ignore_errors=True)


# ── Audio sintetico ───────────────────────────────────────────────────────────


@pytest.fixture
def sample_rate() -> int:
    """Taxa de amostragem padrao para testes (16 kHz)."""
    return 16000


@pytest.fixture
def frame_size(sample_rate: int) -> int:
    """Tamanho do frame VAD em bytes (30ms a 16kHz, 16-bit mono)."""
    return int(sample_rate * 30 / 1000) * 2  # 960 bytes


@pytest.fixture
def synthetic_silence(sample_rate: int) -> bytes:
    """Gera 1 segundo de silencio PCM 16-bit mono."""
    return b"\x00\x00" * sample_rate


@pytest.fixture
def synthetic_sine_wave(sample_rate: int) -> bytes:
    """Gera 0.5s de tom senoidal 440Hz PCM 16-bit mono (volume moderado)."""
    duration = 0.5
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)
    tone = (np.sin(2 * np.pi * 440 * t) * 0.3 * 32767).astype(np.int16)
    return tone.tobytes()


@pytest.fixture
def synthetic_noise(sample_rate: int) -> bytes:
    """Gera 0.5s de ruido branco PCM 16-bit mono."""
    duration = 0.5
    samples = int(sample_rate * duration)
    noise = (np.random.randn(samples) * 0.1 * 32767).astype(np.int16)
    return noise.tobytes()


@pytest.fixture
def synthetic_speech_chunk(sample_rate: int, frame_size: int) -> bytes:
    """Gera um frame VAD simulando fala (energia suficiente para disparar VAD)."""
    samples_per_frame = frame_size // 2  # 16-bit = 2 bytes/sample
    t = np.linspace(0, 30 / 1000, samples_per_frame, endpoint=False)
    chunk = (np.sin(2 * np.pi * 200 * t) * 0.4 * 32767).astype(np.int16)
    return chunk.tobytes()


@pytest.fixture
def synthetic_speech_buffer(sample_rate: int) -> bytes:
    """Gera 2 segundos de audio simulando fala (tom modulado) PCM 16-bit."""
    duration = 2.0
    samples = int(sample_rate * duration)
    t = np.linspace(0, duration, samples, endpoint=False)

    # Tom modulado em frequencia (200-400Hz) para simular fala
    freq = 200 + 200 * np.sin(2 * np.pi * 2 * t)
    speech = (np.sin(2 * np.pi * freq * t) * 0.4 * 32767).astype(np.int16)
    return speech.tobytes()


@pytest.fixture
def mixed_audio_chunks(
    synthetic_speech_chunk: bytes, synthetic_silence: bytes, frame_size: int
) -> list[bytes]:
    """Sequencia de chunks alternando fala/silencio para testar VAD streaming."""
    silence_chunk = synthetic_silence[:frame_size]

    # 5 silencio, 10 fala, 5 silencio
    chunks = [silence_chunk] * 5
    chunks += [synthetic_speech_chunk] * 10
    chunks += [silence_chunk] * 5
    return chunks


@pytest.fixture
def small_wav_header() -> bytes:
    """Gera um cabecalho WAV valido (44 bytes) para 1s de audio 16kHz mono."""
    sample_rate = 16000
    bits_per_sample = 16
    channels = 1
    data_size = sample_rate * channels * bits_per_sample // 8  # 32000 bytes

    header = b"RIFF"
    header += struct.pack("<I", 36 + data_size)
    header += b"WAVE"
    header += b"fmt "
    header += struct.pack("<I", 16)
    header += struct.pack("<H", 1)  # PCM
    header += struct.pack("<H", channels)
    header += struct.pack("<I", sample_rate)
    header += struct.pack("<I", sample_rate * channels * bits_per_sample // 8)
    header += struct.pack("<H", channels * bits_per_sample // 8)
    header += struct.pack("<H", bits_per_sample)
    header += b"data"
    header += struct.pack("<I", data_size)
    return header


# ── Mocks de dependencias externas ────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_temp_dir() -> Generator[None, None, None]:
    """Mock do diretorio temporario para evitar criar pastas reais."""
    with patch("pathlib.Path.mkdir") as mock_mkdir:
        yield mock_mkdir


@pytest.fixture
def mock_subprocess_run() -> Generator[MagicMock, None, None]:
    """Mock global de subprocess.run."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MockSubprocessResult(returncode=0, stdout="test-output\n")
        yield mock_run


@pytest.fixture
def mock_subprocess_popen() -> Generator[MagicMock, None, None]:
    """Mock global de subprocess.Popen."""
    with patch("subprocess.Popen") as mock_popen:
        proc = make_mock_popen()
        mock_popen.return_value = proc
        yield mock_popen


@pytest.fixture
def mock_shutil_which() -> Generator[MagicMock, None, None]:
    """Mock de shutil.which retornando sempre caminho valido."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/test-tool"
        yield mock_which


@pytest.fixture
def isolated_audio_settings() -> Generator[AudioSettings, None, None]:
    """Fornece um AudioSettings limpo, sem poluir o cache global."""
    from ai.audio.settings import get_audio_settings

    get_audio_settings.cache_clear()
    yield AudioSettings()
