"""Player de áudio com fila de reprodução e crossfade.

Suporta:
- Fila de reprodução (playlist)
- Crossfade entre faixas
- Reprodução de arquivos e buffers PCM
- Controle de volume
- Callbacks de fim de faixa
"""

from __future__ import annotations

import os
import subprocess
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from ai.audio.settings import audio_settings
from ai.telemetry import get_logger

logger = get_logger("ai.audio.player")


@dataclass
class PlaybackItem:
    """Item na fila de reprodução."""

    source: str  # Caminho do arquivo ou "-" para stdin
    audio_data: bytes | None = None  # Dados PCM para reprodução direta
    title: str = ""
    volume: float = 1.0  # 0.0 a 1.0
    crossfade_sec: float = 0.0  # Crossfade com a próxima faixa


class AudioPlayer:
    """Player de áudio com fila e crossfade.

    Attributes:
        sink: Nome do sink PulseAudio de saída.
        volume: Volume global (0.0 a 1.0).
    """

    def __init__(self, sink: str | None = None) -> None:
        self._sink = sink or audio_settings.output_device
        self._volume: float = 1.0
        self._queue: deque[PlaybackItem] = deque()
        self._is_playing = False
        self._is_paused = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._current_item: PlaybackItem | None = None
        self._on_finish_callback: Callable[[], None] | None = None

        logger.debug("AudioPlayer criado (sink=%s)", self._sink)

    # ── Propriedades ──────────────────────────────────────────────────────

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def current_item(self) -> PlaybackItem | None:
        return self._current_item

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, value))

    @property
    def sink(self) -> str:
        return self._sink

    @sink.setter
    def sink(self, value: str) -> None:
        self._sink = value

    @property
    def on_finish(self) -> Callable[[], None] | None:
        return self._on_finish_callback

    @on_finish.setter
    def on_finish(self, callback: Callable[[], None] | None) -> None:
        self._on_finish_callback = callback

    # ── Controle da fila ──────────────────────────────────────────────────

    def enqueue(
        self, source: str | bytes, title: str = "", volume: float = 1.0, crossfade_sec: float = 0.0
    ) -> None:
        """Adiciona um item à fila de reprodução.

        Args:
            source: Caminho do arquivo ou bytes de áudio PCM.
            title: Título descritivo para o item.
            volume: Volume relativo do item (0.0 a 1.0).
            crossfade_sec: Segundos de crossfade com a próxima faixa.
        """
        if isinstance(source, bytes):
            item = PlaybackItem(
                source="-",
                audio_data=source,
                title=title,
                volume=volume,
                crossfade_sec=crossfade_sec,
            )
        else:
            item = PlaybackItem(
                source=source, title=title, volume=volume, crossfade_sec=crossfade_sec
            )

        self._queue.append(item)
        logger.debug("Item enfileirado: %s (fila: %s)", title or source, len(self._queue))

    def play(self) -> None:
        """Inicia a reprodução da fila."""
        if self._is_playing and self._is_paused:
            self._is_paused = False
            logger.info("Reprodução retomada")
            return

        if self._is_playing:
            return

        if not self._queue:
            logger.warning("Fila vazia — nada para reproduzir")
            return

        self._is_playing = True
        self._is_paused = False
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._play_worker, daemon=True)
        self._thread.start()
        logger.info("Reprodução iniciada (%s itens na fila)", len(self._queue))

    def pause(self) -> None:
        """Pausa a reprodução."""
        self._is_paused = True
        logger.info("Reprodução pausada")

    def resume(self) -> None:
        """Retoma a reprodução."""
        self._is_paused = False
        logger.info("Reprodução retomada")

    def stop(self) -> None:
        """Para a reprodução e limpa a fila."""
        self._stop_event.set()
        self._is_playing = False
        self._is_paused = False
        self._queue.clear()
        self._current_item = None

        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

        logger.info("Reprodução parada e fila limpa")

    def skip(self) -> bool:
        """Pula para o próximo item na fila.

        Returns:
            True se pulou para o próximo, False se a fila acabou.
        """
        if self._queue:
            self._current_item = self._queue.popleft()
            return True
        return False

    def clear_queue(self) -> None:
        """Limpa a fila de reprodução."""
        self._queue.clear()
        logger.info("Fila limpa")

    # ── Reprodução direta ─────────────────────────────────────────────────

    def play_once(self, source: str | bytes, title: str = "", wait: bool = True) -> None:
        """Reproduz um único arquivo ou buffer PCM.

        Args:
            source: Caminho do arquivo ou bytes PCM.
            title: Título descritivo.
            wait: Se True, bloqueia até o fim da reprodução.
        """
        self.stop()
        self.enqueue(source, title=title)

        if wait:
            self.play()
            if self._thread:
                self._thread.join()
        else:
            self.play()

    def play_tone(
        self,
        frequency: float = 440.0,
        duration: float = 1.0,
        volume: float = 0.5,
        wait: bool = True,
    ) -> None:
        """Reproduz um tom senoidal simples.

        Args:
            frequency: Frequência em Hz.
            duration: Duração em segundos.
            volume: Volume (0.0 a 1.0).
            wait: Se True, bloqueia até o fim.
        """
        import numpy as np

        sample_rate = audio_settings.sample_rate
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples, endpoint=False)
        tone = (np.sin(2 * np.pi * frequency * t) * volume * 32767).astype(np.int16)
        audio_bytes = tone.tobytes()

        self.play_once(audio_bytes, title=f"Tom {frequency}Hz", wait=wait)

    # ── Worker interno ────────────────────────────────────────────────────

    def _play_worker(self) -> None:
        """Thread interna de reprodução."""
        try:
            while not self._stop_event.is_set() and self._queue:
                self._current_item = self._queue.popleft()

                if self._current_item.crossfade_sec > 0 and self._queue:
                    # Crossfade com próximo item
                    next_item = self._queue[0]
                    self._play_with_crossfade(
                        self._current_item, next_item, self._current_item.crossfade_sec
                    )
                    if self._queue:
                        self._queue.popleft()  # Remove o próximo que já foi tocado
                else:
                    self._play_item(self._current_item)

                if self._on_finish_callback:
                    self._on_finish_callback()

        except Exception as e:
            logger.error("Erro no worker de reprodução: %s", e)
        finally:
            self._is_playing = False
            self._current_item = None

    def _play_item(self, item: PlaybackItem) -> None:
        """Reproduz um único item."""
        if self._stop_event.is_set():
            return

        env = os.environ.copy()
        if self._sink and self._sink != "default":
            env["PULSE_SINK"] = self._sink

        vol = min(self._volume * item.volume, 1.0)

        if item.audio_data:
            # Reproduzir buffer PCM diretamente
            cmd = [
                "ffplay",
                "-nodisp",
                "-autoexit",
                "-volume",
                str(int(vol * 100)),
                "-f",
                "s16le",
                "-ar",
                str(audio_settings.sample_rate),
                "-ac",
                "1",
                "-i",
                "-",
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
                proc.stdin.write(item.audio_data)  # type: ignore[union-attr]
                proc.stdin.close()  # type: ignore[union-attr]
                proc.wait(timeout=audio_settings.record_max_duration)
            except FileNotFoundError:
                self._play_with_aplay(item.audio_data, vol)
            except Exception as e:
                logger.error("Erro reproduzindo buffer: %s", e)
        else:
            # Reproduzir arquivo
            if item.source.endswith((".wav", ".mp3", ".ogg", ".flac")):
                cmd = [
                    "ffplay",
                    "-nodisp",
                    "-autoexit",
                    "-volume",
                    str(int(vol * 100)),
                    item.source,
                ]
            else:
                # PCM raw
                cmd = [
                    "ffplay",
                    "-nodisp",
                    "-autoexit",
                    "-volume",
                    str(int(vol * 100)),
                    "-f",
                    "s16le",
                    "-ar",
                    str(audio_settings.sample_rate),
                    "-ac",
                    "1",
                    "-i",
                    item.source,
                ]

            try:
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    timeout=audio_settings.record_max_duration,
                )
            except FileNotFoundError:
                if os.path.exists(item.source):
                    subprocess.run(
                        ["aplay", item.source],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                    )
            except Exception as e:
                logger.error("Erro reproduzindo %s: %s", item.source, e)

    def _play_with_crossfade(
        self, current: PlaybackItem, next_item: PlaybackItem, crossfade_sec: float
    ) -> None:
        """Reproduz dois itens com crossfade usando ffmpeg."""
        if self._stop_event.is_set():
            return

        vol = min(self._volume * current.volume, 1.0)

        # Usa ffmpeg para crossfade entre dois arquivos
        if isinstance(current.source, str) and isinstance(next_item.source, str):
            # Cria filtro crossfade
            cmd = [
                "ffplay",
                "-nodisp",
                "-autoexit",
                "-volume",
                str(int(vol * 100)),
                "-i",
                current.source,
                "-i",
                next_item.source,
                "-filter_complex",
                f"[0:a][1:a]acrossfade=d={crossfade_sec}:c1=tri:c2=tri[a]",
                "-map",
                "[a]",
            ]

            try:
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=audio_settings.record_max_duration,
                )
            except Exception as e:
                logger.error("Erro no crossfade: %s", e)
                # Fallback: toca o atual sem crossfade
                self._play_item(current)

    @staticmethod
    def _play_with_aplay(audio_data: bytes, _volume: float) -> None:
        """Fallback: reproduz com aplay."""
        cmd = ["aplay", "-f", "S16_LE", "-r", str(audio_settings.sample_rate), "-c", "1"]
        try:
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            proc.stdin.write(audio_data)  # type: ignore[union-attr]
            proc.stdin.close()  # type: ignore[union-attr]
            proc.wait(timeout=30)
        except Exception as e:
            logger.error("Erro no fallback aplay: %s", e)
