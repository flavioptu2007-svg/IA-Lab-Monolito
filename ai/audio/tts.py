"""Text-to-Speech (TTS) para o IA-Lab.

Utiliza espeak como engine principal (sempre disponível no Linux),
com suporte opcional a edge-tts para vozes mais naturais.

Suporta:
- Síntese de texto para áudio PCM
- Múltiplas vozes e idiomas
- Controle de velocidade e volume
- Salvamento em arquivo WAV
- Cache de frases comuns
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from ai.audio.exceptions import TTSError
from ai.audio.settings import audio_settings
from ai.telemetry import get_logger

logger = get_logger("ai.audio.tts")


class TextToSpeech:
    """Síntese de texto para fala.

    Attributes:
        engine: Engine de TTS ('espeak' ou 'edge-tts').
        voice: Nome da voz / idioma (ex: 'pt-br', 'en-us').
        rate: Velocidade de fala (espeak: 80-450).
        volume: Volume (espeak: 0-200).
    """

    def __init__(
        self,
        engine: str | None = None,
        voice: str | None = None,
        rate: int | None = None,
        volume: int | None = None,
    ) -> None:
        self._engine = engine or audio_settings.tts_engine
        self._voice = voice or audio_settings.tts_voice
        self._rate = rate or audio_settings.tts_rate
        self._volume = volume or audio_settings.tts_volume
        self._last_engine: str | None = None  # engine real após fallback

        # Cache LRU de frases
        self._cache_enabled = True

        logger.info(
            "TextToSpeech iniciado (engine=%s, voice=%s, rate=%d)",
            self._engine,
            self._voice,
            self._rate,
        )

    # ── Propriedades ──────────────────────────────────────────────────────

    @property
    def engine(self) -> str:
        return self._engine

    @engine.setter
    def engine(self, value: str) -> None:
        if value not in ("espeak", "edge-tts"):
            raise TTSError(f"Engine inválido: {value}", "Use 'espeak' ou 'edge-tts'")
        self._engine = value

    @property
    def last_engine(self) -> str | None:
        """Engine que realmente gerou o último áudio (pode diferir do configurado
        quando houve fallback — ex.: edge-tts usado no lugar de espeak)."""
        return self._last_engine

    @property
    def voice(self) -> str:
        return self._voice

    @voice.setter
    def voice(self, value: str) -> None:
        self._voice = value

    @property
    def rate(self) -> int:
        return self._rate

    @rate.setter
    def rate(self, value: int) -> None:
        self._rate = max(80, min(450, value))

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, value: int) -> None:
        self._volume = max(0, min(200, value))

    @property
    def cache_size(self) -> int:
        """Número de entradas no cache LRU."""
        info = self._synthesize_espeak.cache_info()
        return info.currsize

    @property
    def cache_hits(self) -> int:
        """Número de acertos do cache LRU."""
        info = self._synthesize_espeak.cache_info()
        return info.hits

    @property
    def cache_misses(self) -> int:
        """Número de misses do cache LRU."""
        info = self._synthesize_espeak.cache_info()
        return info.misses

    @property
    def is_cache_enabled(self) -> bool:
        return self._cache_enabled

    def enable_cache(self) -> None:
        self._cache_enabled = True

    def disable_cache(self) -> None:
        self._cache_enabled = False

    def clear_cache(self) -> None:
        """Limpa o cache de frases."""
        self._synthesize_espeak.cache_clear()
        logger.info("Cache de TTS limpo")

    @staticmethod
    def _run_async(coro):
        """Executa uma coroutine em qualquer contexto (sync ou dentro de um
        event loop já rodando — ex.: handler async do FastAPI).

        ``asyncio.run()`` falha com "cannot be called from a running event
        loop" quando chamado dentro de um loop ativo; neste caso a coroutine
        é executada numa thread separada (onde ``asyncio.run`` funciona).
        """
        import asyncio
        import concurrent.futures

        try:
            asyncio.get_running_loop()  # levanta RuntimeError se não houver loop
        except RuntimeError:
            # Sem loop ativo — execução direta (CLI/scripts)
            return asyncio.run(coro)

        # Loop ativo (FastAPI async) — roda numa thread isolada
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=120)

    # ── Síntese principal ─────────────────────────────────────────────────

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        rate: int | None = None,
        volume: int | None = None,
    ) -> bytes:
        """Sintetiza texto em áudio PCM 16-bit 16kHz mono.

        Args:
            text: Texto a ser sintetizado.
            voice: Voz/idioma (padrão: configurado no init).
            rate: Velocidade de fala.
            volume: Volume.

        Returns:
            Áudio PCM 16-bit 16kHz mono.

        Raises:
            TTSError: Se a síntese falhar.
        """
        if not text or not text.strip():
            return b""

        v = voice or self._voice
        r = rate or self._rate
        vol = volume or self._volume

        try:
            if self._engine == "espeak" or self._engine == "auto":
                return self._synthesize_espeak(text, v, r, vol)
            elif self._engine == "edge-tts":
                return self._synthesize_edge(text, v)
            else:
                raise TTSError(f"Engine não suportado: {self._engine}")
        except Exception as e:
            # Fallback: tenta o outro engine
            fallback_engine = "espeak" if self._engine != "espeak" else "edge-tts"
            logger.warning(
                "Engine %s falhou, tentando fallback %s: %s", self._engine, fallback_engine, e
            )
            try:
                if fallback_engine == "espeak":
                    result = self._synthesize_espeak(text, v, r, vol)
                else:
                    result = self._synthesize_edge(text, v)
                # Registra o engine que realmente gerou o áudio (para reporte)
                self._last_engine = fallback_engine
                return result
            except Exception as fallback_e:
                raise TTSError(
                    "Ambos os engines de TTS falharam", f"Primário: {e}; Fallback: {fallback_e}"
                ) from fallback_e

    def synthesize_to_file(self, text: str, filepath: str | Path, voice: str | None = None) -> str:
        """Sintetiza e salva em arquivo WAV.

        Args:
            text: Texto a ser sintetizado.
            filepath: Caminho do arquivo WAV de saída.
            voice: Voz/idioma.

        Returns:
            Caminho do arquivo salvo.
        """
        audio = self.synthesize(text, voice=voice)

        # Converte PCM para WAV via ffmpeg
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-i",
            "-",
            "-f",
            "wav",
            str(filepath),
        ]

        try:
            result = subprocess.run(cmd, input=audio, capture_output=True, timeout=30)
            if result.returncode != 0:
                raise TTSError("Falha ao salvar arquivo WAV", result.stderr.decode()[:200])
        except FileNotFoundError:
            # Fallback: salva como raw PCM
            raw_path = str(filepath) + ".raw"
            with open(raw_path, "wb") as f:
                f.write(audio)
            filepath = raw_path

        logger.info("Áudio TTS salvo em: %s", filepath)
        return str(filepath)

    def list_voices(self) -> list[dict[str, str]]:
        """Lista vozes disponíveis no engine atual.

        Returns:
            Lista de dicionários com name e language de cada voz.
        """
        voices: list[dict[str, str]] = []

        if self._engine in ("espeak", "auto"):
            try:
                result = subprocess.run(
                    ["espeak", "--voices"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n")[1:]:  # Pula cabeçalho
                        parts = line.split()
                        if len(parts) >= 4:
                            voices.append(
                                {"name": parts[1], "language": parts[3], "engine": "espeak"}
                            )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        if self._engine in ("edge-tts", "auto"):
            try:
                import edge_tts

                async def _list():
                    all_voices = await edge_tts.list_voices()
                    return [
                        {"name": v["ShortName"], "language": v["Locale"], "engine": "edge-tts"}
                        for v in all_voices
                    ]

                edge_voices = self._run_async(_list())
                voices.extend(edge_voices)
            except (ImportError, Exception):
                pass

        return voices

    def is_available(self) -> bool:
        """Verifica se o engine de TTS está disponível."""
        if self._engine == "espeak" or self._engine == "auto":
            return self._which("espeak") is not None
        elif self._engine == "edge-tts":
            try:
                import edge_tts  # noqa: F401

                return True
            except ImportError:
                return False
        return False

    # ── Engines internos ──────────────────────────────────────────────────

    @lru_cache(maxsize=128)  # noqa: B019  # cache intencional (self incluso); cache_clear() exposto via API
    def _synthesize_espeak(self, text: str, voice: str, rate: int, volume: int) -> bytes:
        """Síntese via espeak-ng (nativo, leve, offline).

        Cache LRU para frases repetidas.
        Uso de cache_info().currsize para tracking real de entradas.
        """

        # Espeak não suporta pipe directo para WAV confiavelmente,
        # então usamos stdout como RAW (-w - não funciona em todas versões)
        # Solução: gerar WAV em temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [
                "espeak-ng",
                "-v",
                voice,
                "-s",
                str(rate),
                "-a",
                str(volume),
                "-w",
                tmp_path,
                text,
            ]

            # Se espeak-ng não existir, tenta espeak
            if not self._which("espeak-ng"):
                cmd[0] = "espeak"

            result = subprocess.run(cmd, capture_output=True, timeout=30)

            if result.returncode != 0 or not os.path.exists(tmp_path):
                raise TTSError(
                    f"espeak falhou com código {result.returncode}", result.stderr.decode()[:200]
                )

            # Lê o WAV e converte para PCM 16kHz mono
            with open(tmp_path, "rb") as f:
                wav_data = f.read()

            # Extrai PCM do WAV (pula header de 44 bytes)
            pcm_data = wav_data[44:] if len(wav_data) > 44 else wav_data

            logger.debug(
                "espeak: %d caracteres → %d bytes PCM (voz=%s)", len(text), len(pcm_data), voice
            )

            return pcm_data

        except FileNotFoundError:
            raise TTSError(
                "espeak não encontrado", "Instale com: sudo apt install espeak espeak-ng"
            ) from None
        except subprocess.TimeoutExpired:
            raise TTSError("Timeout na síntese espeak") from None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @staticmethod
    def _extract_pcm_from_wav(wav_data: bytes) -> bytes:
        """Extrai o payload PCM de um WAV percorrendo seus chunks.

        O edge-tts gera WAV com chunks extras (ex.: 'LIST', 'fact') além de
        'fmt ' e 'data' — assumir header fixo de 44 bytes corrompe o áudio.
        Esta função localiza o chunk 'data' de forma robusta.
        """
        if len(wav_data) < 12 or wav_data[:4] != b"RIFF":
            return wav_data  # já é PCM bruto
        import struct

        pos = 12
        while pos + 8 <= len(wav_data):
            cid = wav_data[pos : pos + 4]
            csize = struct.unpack_from("<I", wav_data, pos + 4)[0]
            if cid == b"data":
                start = pos + 8
                return wav_data[start : start + csize]
            pos += 8 + csize
            if cid in (b"fmt ", b"data") and csize % 2:
                pos += 1  # alinhamento ímpar (especificação RIFF)
        return wav_data

    # Mapeia códigos de idioma espeak (ex: 'pt-br') para vozes neurais edge-tts
    _EDGE_VOICE_MAP = {
        "pt-br": "pt-BR-AntonioNeural",
        "pt": "pt-BR-AntonioNeural",
        "en-us": "en-US-AriaNeural",
        "en": "en-US-AriaNeural",
        "en-gb": "en-GB-SoniaNeural",
        "es": "es-ES-ElviraNeural",
        "fr": "fr-FR-DeniseNeural",
        "de": "de-DE-KatjaNeural",
        "it": "it-IT-ElsaNeural",
        "ja": "ja-JP-NanamiNeural",
        "zh": "zh-CN-XiaoxiaoNeural",
        "ko": "ko-KR-SunHiNeural",
        "ru": "ru-RU-SvetlanaNeural",
    }

    def _resolve_edge_voice(self, voice: str) -> str:
        """Converte voz espeak ('pt-br') em voz edge-tts ('pt-BR-AntonioNeural').

        Se a voz já estiver no formato edge-tts (ex.: contém 'Neural' ou segue
        o padrão XX-YY-Nome), usa direto; senão, procura no mapa de idiomas.
        """
        v = (voice or "").strip()
        if not v:
            return audio_settings.tts_edge_voice
        # Já é formato edge-tts (ex: 'pt-BR-AntonioNeural', 'en-US-JennyMultilingualNeural')
        if "Neural" in v or (len(v) > 8 and "-" in v and v.count("-") >= 2):
            return v
        key = v.lower()
        if key in self._EDGE_VOICE_MAP:
            return self._EDGE_VOICE_MAP[key]
        # Fallback: voz padrão edge-tts configurada
        return audio_settings.tts_edge_voice

    def _synthesize_edge(self, text: str, voice: str) -> bytes:
        """Síntese via edge-tts (vozes naturais, requer internet)."""
        try:
            import edge_tts

            edge_voice = self._resolve_edge_voice(voice)
            output_file = tempfile.mktemp(suffix=".wav")

            async def _run():
                communicate = edge_tts.Communicate(text, edge_voice)
                await communicate.save(output_file)

            self._run_async(_run())

            if not os.path.exists(output_file):
                raise TTSError("edge-tts não gerou arquivo de saída")

            with open(output_file, "rb") as f:
                wav_data = f.read()

            os.unlink(output_file)

            # Extrai o PCM percorrendo os chunks do WAV (edge-tts gera chunks
            # adicionais como LIST/fact — não é seguro assumir header fixo 44B).
            pcm_data = self._extract_pcm_from_wav(wav_data)

            logger.debug(
                "edge-tts: %d caracteres → %d bytes PCM (voz=%s)", len(text), len(pcm_data), voice
            )

            return pcm_data

        except ImportError:
            raise TTSError("edge-tts não instalado", "Instale com: pip install edge-tts") from None
        except Exception as e:
            raise TTSError("Falha na síntese edge-tts", str(e)) from e

    # ── Utilitários ───────────────────────────────────────────────────────

    @staticmethod
    def _which(program: str) -> str | None:
        import shutil

        return shutil.which(program)

    def __repr__(self) -> str:
        return f"TextToSpeech(engine={self._engine}, voice={self._voice}, rate={self._rate})"
