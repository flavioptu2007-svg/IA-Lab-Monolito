"""Gravador de áudio com buffer circular e detecção de voz (VAD).

Suporta:
- Gravação contínua com buffer circular
- Parada automática por VAD
- Gravação por tempo fixo
- Salvamento em WAV e formatos comuns
- Múltiplas fontes de entrada
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from collections.abc import Callable

from ai.audio.exceptions import AudioCaptureError
from ai.audio.settings import audio_settings
from ai.audio.vad import VoiceActivityDetector
from ai.telemetry import get_logger

logger = get_logger("ai.audio.recorder")


class AudioRecorder:
    """Gravador de áudio com suporte a VAD e buffer circular.

    Attributes:
        sample_rate: Taxa de amostragem em Hz.
        channels: Número de canais (1=mono, 2=stereo).
        source: Nome do dispositivo PulseAudio de entrada.
    """

    def __init__(
        self, sample_rate: int | None = None, channels: int | None = None, source: str | None = None
    ) -> None:
        self._sample_rate = sample_rate or audio_settings.sample_rate
        self._channels = channels or audio_settings.channels
        self._source = source or audio_settings.input_device
        self._is_recording = False
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen | None = None
        self._stop_event = threading.Event()

        # Buffer circular
        buffer_seconds = audio_settings.record_buffer_seconds
        self._buffer_size = int(self._sample_rate * buffer_seconds) * 2
        self._buffer: bytearray = bytearray()

        # VAD
        self._vad: VoiceActivityDetector | None = None
        self._vad_callback: Callable[[str], None] | None = None

        # Callback de dados
        self._data_callback: Callable[[bytes], None] | None = None

        logger.debug(
            "AudioRecorder criado (rate=%s, channels=%s, source=%s)",
            self._sample_rate,
            self._channels,
            self._source,
        )

    # ── Propriedades ──────────────────────────────────────────────────────

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, value: str) -> None:
        if self._is_recording:
            raise RuntimeError("Não é possível trocar a fonte durante gravação")
        self._source = value

    @property
    def vad(self) -> VoiceActivityDetector | None:
        return self._vad

    @vad.setter
    def vad(self, detector: VoiceActivityDetector | None) -> None:
        self._vad = detector

    @property
    def data_callback(self) -> Callable[[bytes], None] | None:
        return self._data_callback

    @data_callback.setter
    def data_callback(self, callback: Callable[[bytes], None] | None) -> None:
        self._data_callback = callback

    @property
    def vad_callback(self) -> Callable[[str], None] | None:
        return self._vad_callback

    @vad_callback.setter
    def vad_callback(self, callback: Callable[[str], None] | None) -> None:
        self._vad_callback = callback

    # ── Métodos de gravação ───────────────────────────────────────────────

    def start(self, duration: float | None = None, use_vad: bool = False) -> None:
        """Inicia a gravação.

        Args:
            duration: Duração em segundos (None = contínuo).
            use_vad: Se True, para automaticamente quando VAD detectar fim de fala.
        """
        if self._is_recording:
            logger.warning("Gravação já em andamento")
            return

        self._is_recording = True
        self._stop_event.clear()
        self._buffer.clear()

        if use_vad and self._vad is None:
            self._vad = VoiceActivityDetector()

        self._thread = threading.Thread(
            target=self._record_worker, args=(duration, use_vad), daemon=True
        )
        self._thread.start()
        logger.info(
            "Gravação iniciada (source=%s, duration=%s, vad=%s)", self._source, duration, use_vad
        )

    def stop(self) -> bytes | None:
        """Para a gravação e retorna o áudio capturado.

        Returns:
            Dados de áudio PCM 16-bit mono, ou None se vazio.
        """
        if not self._is_recording:
            return None

        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        self._is_recording = False

        if self._process:
            self._process.terminate()
            self._process = None

        data = bytes(self._buffer) if self._buffer else None
        logger.info("Gravação finalizada (%s bytes capturados)", len(data) if data else 0)
        return data

    def record_fixed(self, duration: float, source: str | None = None) -> bytes:
        """Grava por uma duração fixa e retorna o áudio.

        Args:
            duration: Duração em segundos.
            source: Fonte de áudio (padrão: configurada no init).

        Returns:
            Dados PCM 16-bit mono.

        Raises:
            AudioCaptureError: Se a gravação falhar.
        """
        src = source or self._source
        logger.info("Gravando %s segundos de %s...", duration, src)

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "pulse",
            "-i",
            src,
            "-t",
            str(duration),
            "-ac",
            "1",
            "-ar",
            str(self._sample_rate),
            "-sample_fmt",
            "s16",
            "-f",
            "wav",
            "-",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=duration + 10)

            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")[:200]
                raise AudioCaptureError(f"Falha ao gravar de {src}", stderr)

            # Pular cabeçalho WAV (44 bytes) para PCM puro
            audio_data = result.stdout[44:] if len(result.stdout) > 44 else result.stdout
            logger.info("Gravação concluída: %s bytes", len(audio_data))
            return audio_data

        except subprocess.TimeoutExpired:
            raise AudioCaptureError(
                f"Timeout gravando de {src}", f"Limite de {duration + 10}s excedido"
            )
        except FileNotFoundError:
            raise AudioCaptureError("ffmpeg não encontrado", "Instale com: sudo apt install ffmpeg")

    # ── Métodos auxiliares ────────────────────────────────────────────────

    def save_to_file(self, audio_data: bytes, filepath: str | Path) -> str:
        """Salva dados PCM em um arquivo WAV.

        Args:
            audio_data: Dados PCM 16-bit mono.
            filepath: Caminho para salvar.

        Returns:
            Caminho do arquivo salvo.

        Raises:
            AudioCaptureError: Se a conversão falhar.
        """
        filepath = str(filepath)
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "s16le",
            "-ar",
            str(self._sample_rate),
            "-ac",
            "1",
            "-i",
            "-",
            "-f",
            "wav",
            filepath,
        ]

        try:
            result = subprocess.run(cmd, input=audio_data, capture_output=True, timeout=10)

            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")[:200]
                raise AudioCaptureError("Falha ao salvar arquivo de áudio", stderr)

            logger.info("Áudio salvo em: %s (%s bytes)", filepath, len(audio_data))
            return filepath

        except subprocess.TimeoutExpired:
            raise AudioCaptureError("Timeout ao salvar arquivo de áudio")

    # ── Worker interno ────────────────────────────────────────────────────

    def _record_worker(self, duration: float | None, use_vad: bool) -> None:
        """Thread interna de gravação."""
        cmd: list[str] = [
            "ffmpeg",
            "-y",
            "-f",
            "pulse",
            "-i",
            self._source,
            "-ac",
            "1",
            "-ar",
            str(self._sample_rate),
            "-sample_fmt",
            "s16",
            "-f",
            "s16le",
            "-",
        ]

        try:
            self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

            frame_size = 320  # 20ms a 16kHz
            start_time = time.monotonic()
            speech_end_time: float | None = None
            post_speech_pad = audio_settings.vad_post_speech_pad

            while not self._stop_event.is_set():
                # Verifica duração máxima
                if duration and (time.monotonic() - start_time) >= duration:
                    break

                # Lê frame
                chunk = self._process.stdout.read(frame_size)  # type: ignore[union-attr]
                if not chunk or len(chunk) < frame_size:
                    break

                # Buffer circular
                self._buffer.extend(chunk)
                if len(self._buffer) > self._buffer_size:
                    self._buffer = self._buffer[-self._buffer_size :]

                # Callback de dados
                if self._data_callback:
                    self._data_callback(chunk)

                # VAD streaming
                if use_vad and self._vad:
                    status = self._vad.process_frame_streaming(chunk)
                    if self._vad_callback:
                        self._vad_callback(status)

                    if status == "speech_end":
                        speech_end_time = time.monotonic()
                    elif status == "speech":
                        speech_end_time = None

                    # Se passou do padding pós-fala, para
                    if speech_end_time and (time.monotonic() - speech_end_time) >= post_speech_pad:
                        logger.info("VAD detectou fim de fala — parando gravação")
                        break

        except Exception as e:
            logger.error("Erro no worker de gravação: %s", e)
        finally:
            if self._process:
                self._process.terminate()
                self._process = None
