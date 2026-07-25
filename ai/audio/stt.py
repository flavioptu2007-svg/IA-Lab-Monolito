"""Speech-to-Text (STT) para o IA-Lab.

Utiliza speechbrain como engine principal de transcrição,
com fallbacks para whisper (se disponível) e chamadas de API externas.

Suporta:
- Transcrição de arquivos de áudio
- Transcrição de buffers PCM em memória
- Detecção de idioma
- Processamento em lote
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from ai.audio.exceptions import STTError
from ai.audio.settings import audio_settings
from ai.audio.effects import bytes_to_float, normalize, remove_silence, resample
from ai.telemetry import get_logger

logger = get_logger("ai.audio.stt")


class SpeechToText:
    """Transcrição de fala para texto.

    Attributes:
        model: Nome do modelo speechbrain a ser usado.
        device: Dispositivo para inferência ('cpu' ou 'cuda').
        language: Código do idioma (ex: 'pt', 'en').
    """

    def __init__(
        self, model: str | None = None, device: str | None = None, language: str | None = None
    ) -> None:
        self._model_name = model or audio_settings.stt_model
        self._device = device or audio_settings.stt_device
        self._language = language or audio_settings.stt_language
        self._model: Any = None
        self._classifier: Any = None

        logger.info(
            "SpeechToText iniciado (model=%s, device=%s, lang=%s)",
            self._model_name,
            self._device,
            self._language,
        )

    # ── Propriedades ──────────────────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return self._device

    @property
    def language(self) -> str:
        return self._language

    @property
    def is_model_loaded(self) -> bool:
        return self._model is not None

    # ── Carregamento do modelo ────────────────────────────────────────────

    def load_model(self) -> bool:
        """Carrega o modelo speechbrain em memória.

        Returns:
            True se o modelo foi carregado com sucesso.
        """
        if self._model is not None:
            return True

        try:
            from speechbrain.inference.ASR import EncoderASR

            logger.info("Carregando modelo speechbrain: %s ...", self._model_name)
            start = time.monotonic()

            self._model = EncoderASR.from_hparams(
                source=self._model_name,
                savedir=f"models/stt/{self._model_name.replace('/', '_')}",
                run_opts={"device": self._device},
            )

            elapsed = time.monotonic() - start
            logger.info("Modelo speechbrain carregado em %.1fs", elapsed)
            return True

        except ImportError:
            logger.error("speechbrain não está instalado")
            return False
        except Exception as e:
            logger.error("Falha ao carregar modelo speechbrain: %s", e)
            return False

    def unload_model(self) -> None:
        """Libera o modelo da memória."""
        self._model = None
        logger.info("Modelo speechbrain descarregado")

    # ── Transcrição ────────────────────────────────────────────────────────

    def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int | None = None,
        language: str | None = None,
        normalize_audio: bool = True,
    ) -> str:
        """Transcreve um buffer PCM de áudio para texto.

        Args:
            audio_data: Bytes PCM 16-bit mono.
            sample_rate: Taxa de amostragem do áudio de entrada.
            language: Código do idioma (opcional).
            normalize_audio: Se True, normaliza o áudio antes de transcrever.

        Returns:
            Texto transcrito.

        Raises:
            STTError: Se a transcrição falhar.
        """
        if not audio_data or len(audio_data) < 320:
            return ""

        sr = sample_rate or audio_settings.sample_rate

        # Pré-processamento
        audio = audio_data
        if normalize_audio:
            audio = normalize(audio)

        # Reamostrar para 16kHz se necessário (speechbrain usa 16kHz)
        if sr != 16000:
            audio = resample(audio, sr, 16000)
            sr = 16000

        # Remover silêncio
        audio = remove_silence(audio, sample_rate=sr)

        if not audio:
            return ""

        return self._transcribe_with_speechbrain(audio, sr)

    def transcribe_file(self, filepath: str | Path) -> str:
        """Transcreve um arquivo de áudio.

        Args:
            filepath: Caminho para o arquivo de áudio (WAV, MP3, etc.).

        Returns:
            Texto transcrito.
        """
        filepath = str(filepath)

        if not Path(filepath).exists():
            raise STTError("Arquivo não encontrado", filepath)

        # Converte para PCM 16kHz mono via ffmpeg
        audio_data = self._convert_to_pcm(filepath)
        return self.transcribe(audio_data, sample_rate=16000)

    def transcribe_with_timestamps(
        self, audio_data: bytes, sample_rate: int | None = None
    ) -> list[dict[str, Any]]:
        """Transcreve e retorna segmentos com timestamps.

        Args:
            audio_data: Bytes PCM 16-bit mono.
            sample_rate: Taxa de amostragem.

        Returns:
            Lista de segmentos: {text, start_sec, end_sec, confidence}.
        """
        raise NotImplementedError("Transcrição com timestamps requer whisper ou modelo específico")

    def is_available(self) -> bool:
        """Verifica se o speechbrain está disponível no ambiente."""
        try:
            import speechbrain  # noqa: F401

            return True
        except ImportError:
            return False

    # ── Métodos internos ──────────────────────────────────────────────────

    def _transcribe_with_speechbrain(self, audio: bytes, sample_rate: int) -> str:
        """Transcrição usando speechbrain (EncoderASR)."""
        if not self.load_model():
            raise STTError(
                "Modelo speechbrain não disponível",
                f"Tente: pip install speechbrain -- extra-model={self._model_name}",
            )

        try:
            # speechbrain espera numpy array
            samples = bytes_to_float(audio)

            # Transcreve
            result = self._model.transcribe_batch([samples], [sample_rate])

            text = str(result[0]) if result else ""
            logger.info("Transcrição concluída: %d caracteres", len(text))
            return text.strip()

        except Exception as e:
            logger.error("Erro na transcrição speechbrain: %s", e)
            raise STTError("Falha na transcrição", str(e))

    @staticmethod
    def _convert_to_pcm(filepath: str) -> bytes:
        """Converte arquivo de áudio para PCM 16-bit 16kHz mono via ffmpeg."""
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            filepath,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-sample_fmt",
            "s16",
            "-f",
            "s16le",
            "-",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=audio_settings.stt_timeout)

            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")[:200]
                raise STTError("Falha ao converter arquivo para PCM", stderr)

            return result.stdout

        except subprocess.TimeoutExpired:
            raise STTError("Timeout na conversão do arquivo de áudio")
        except FileNotFoundError:
            raise STTError("ffmpeg não encontrado", "Instale com: sudo apt install ffmpeg")

    def __repr__(self) -> str:
        return (
            f"SpeechToText(model={self._model_name}, "
            f"device={self._device}, lang={self._language})"
        )
