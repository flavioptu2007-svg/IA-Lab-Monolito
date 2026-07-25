"""Voice Activity Detection (VAD) para o IA-Lab.

Utiliza webrtcvad (Google WebRTC VAD) para detectar presença de fala
em fluxos de áudio. Suporta níveis de agressividade configuráveis e
opera em buffers de 10, 20 ou 30 ms.

Uso típico:
    detector = VoiceActivityDetector(aggressiveness=2)
    is_speech = detector.is_speech(audio_frame)
    speech_chunks = detector.detect_speech(audio_buffer, sample_rate)
"""

from __future__ import annotations

from typing import Any

from ai.audio.exceptions import VADError
from ai.audio.settings import audio_settings

try:
    import webrtcvad
except ImportError:
    webrtcvad = None  # type: ignore[assignment]


class VoiceActivityDetector:
    """Detector de atividade de voz baseado no WebRTC VAD.

    Attributes:
        aggressiveness: Nível de agressividade (0=menos, 3=mais).
        frame_ms: Tamanho do frame em ms (10, 20 ou 30).
        sample_rate: Taxa de amostragem (8000, 16000, 32000, 48000).
    """

    VALID_FRAME_MS = (10, 20, 30)
    VALID_SAMPLE_RATES = (8000, 16000, 32000, 48000)

    def __init__(
        self,
        aggressiveness: int | None = None,
        frame_ms: int | None = None,
        sample_rate: int | None = None,
    ) -> None:
        if webrtcvad is None:
            raise VADError("webrtcvad não está instalado", "Execute: pip install webrtcvad")

        self._aggressiveness = (
            aggressiveness if aggressiveness is not None else audio_settings.vad_aggressiveness
        )
        self._frame_ms = frame_ms if frame_ms is not None else audio_settings.vad_frame_ms
        self._sample_rate = sample_rate if sample_rate is not None else audio_settings.sample_rate

        # Validação
        if self._aggressiveness not in (0, 1, 2, 3):
            raise VADError(
                f"aggressiveness inválido: {self._aggressiveness}",
                "Use 0 (menos agressivo) a 3 (mais agressivo)",
            )
        if self._frame_ms not in self.VALID_FRAME_MS:
            raise VADError(
                f"frame_ms inválido: {self._frame_ms}", f"Use um de {self.VALID_FRAME_MS}"
            )
        if self._sample_rate not in self.VALID_SAMPLE_RATES:
            raise VADError(
                f"sample_rate inválido: {self._sample_rate}", f"Use um de {self.VALID_SAMPLE_RATES}"
            )

        self._vad = webrtcvad.Vad(self._aggressiveness)
        self._frame_size = int(self._sample_rate * self._frame_ms / 1000) * 2  # 16-bit

        self._reset_state()

    def _reset_state(self) -> None:
        """Reseta o estado interno do detector."""
        self._speech_frames = 0
        self._silence_frames = 0
        self._in_speech = False
        self._total_frames = 0

    # ── Propriedades ──────────────────────────────────────────────────────

    @property
    def aggressiveness(self) -> int:
        return self._aggressiveness

    @property
    def frame_ms(self) -> int:
        return self._frame_ms

    @property
    def frame_size(self) -> int:
        """Tamanho de cada frame em bytes (16-bit PCM mono)."""
        return self._frame_size

    @property
    def in_speech(self) -> bool:
        """Se o estado atual indica que há fala em andamento."""
        return self._in_speech

    # ── Métodos principais ────────────────────────────────────────────────

    def is_speech(self, audio_frame: bytes) -> bool:
        """Verifica se um frame de áudio contém fala.

        Args:
            audio_frame: Frame de áudio PCM 16-bit mono, no tamanho correto.

        Returns:
            True se o frame contém atividade de voz.
        """
        if len(audio_frame) != self._frame_size:
            raise VADError(
                f"Tamanho de frame inválido: {len(audio_frame)} bytes",
                f"Esperado: {self._frame_size} bytes "
                f"(para {self._frame_ms}ms a {self._sample_rate}Hz)",
            )

        return self._vad.is_speech(audio_frame, self._sample_rate)

    def detect_speech(
        self, audio_data: bytes, sample_rate: int | None = None
    ) -> list[dict[str, Any]]:
        """Detecta segmentos de fala em um buffer de áudio.

        Args:
            audio_data: Buffer completo de áudio PCM 16-bit mono.
            sample_rate: Taxa de amostragem (padrão: configurada no init).

        Returns:
            Lista de segmentos detectados como dicionários:
                {start_frame, end_frame, start_sec, end_sec, duration_sec}
        """
        sr = sample_rate or self._sample_rate
        frame_size = int(sr * self._frame_ms / 1000) * 2
        segments: list[dict[str, Any]] = []
        current_segment: dict[str, Any] | None = None

        # Processa frame a frame
        for i in range(0, len(audio_data) - frame_size + 1, frame_size):
            frame = audio_data[i : i + frame_size]
            speech = self.is_speech(frame) if len(frame) == frame_size else False

            if speech and current_segment is None:
                # Início de um novo segmento de fala
                current_segment = {"start_frame": i // frame_size, "start_sec": i / sr}
            elif not speech and current_segment is not None:
                # Fim do segmento de fala
                current_segment["end_frame"] = i // frame_size
                current_segment["end_sec"] = i / sr
                current_segment["duration_sec"] = (
                    current_segment["end_sec"] - current_segment["start_sec"]
                )
                if current_segment["duration_sec"] >= audio_settings.vad_min_speech_duration:
                    segments.append(current_segment)
                current_segment = None

        # Se terminou em fala, fecha o segmento
        if current_segment is not None:
            current_segment["end_frame"] = len(audio_data) // frame_size
            current_segment["end_sec"] = len(audio_data) / sr
            current_segment["duration_sec"] = (
                current_segment["end_sec"] - current_segment["start_sec"]
            )
            if current_segment["duration_sec"] >= audio_settings.vad_min_speech_duration:
                segments.append(current_segment)

        self._reset_state()
        return segments

    def detect_speech_simple(self, audio_data: bytes, sample_rate: int | None = None) -> bool:
        """Detecção simples: True se qualquer frame no buffer contiver fala.

        Args:
            audio_data: Buffer de áudio PCM 16-bit mono.
            sample_rate: Taxa de amostragem.

        Returns:
            True se alguma atividade de voz for detectada.
        """
        segments = self.detect_speech(audio_data, sample_rate)
        return len(segments) > 0

    # ── Processamento de streaming ────────────────────────────────────────

    def process_frame_streaming(self, audio_frame: bytes) -> str:
        """Processa um frame em modo streaming, retornando o estado.

        Mantém estado interno sobre se está em fala ou silêncio,
        incluindo histerese (pre/post speech padding).

        Args:
            audio_frame: Frame de áudio PCM 16-bit mono.

        Returns:
            "speech" se detectou fala, "silence" se silêncio,
            "speech_start" no início da fala, "speech_end" no fim.
        """
        is_speech = self.is_speech(audio_frame)
        self._total_frames += 1

        pad_pre = int(audio_settings.vad_pre_speech_pad * 1000 / self._frame_ms)
        pad_post = int(audio_settings.vad_post_speech_pad * 1000 / self._frame_ms)
        speech_ratio = audio_settings.vad_speech_threshold

        if is_speech:
            self._speech_frames += 1
            self._silence_frames = 0
        else:
            self._silence_frames += 1

        # Calcula proporção de fala na janela
        window = max(self._speech_frames + self._silence_frames, 1)
        ratio = self._speech_frames / window

        if not self._in_speech and ratio >= speech_ratio:
            # Transição silêncio → fala
            self._in_speech = True
            self._speech_frames = pad_pre  # padding pré-fala
            return "speech_start"

        if self._in_speech and not is_speech:
            # Possível fim — espera padding pós-fala
            if self._silence_frames >= pad_post:
                self._in_speech = False
                self._reset_state()
                return "speech_end"
            return "speech"

        if self._in_speech:
            return "speech"

        return "silence"
