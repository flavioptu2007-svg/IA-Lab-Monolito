"""Motor principal do módulo de áudio do IA-Lab.

O AudioEngine é o orquestrador central que:
- Gerencia dispositivos de entrada/saída
- Coordena VAD, gravação, reprodução e processamento
- Expõe métodos de alto nível para STT, TTS e captura
- Coleta métricas e telemetria
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ai.audio.exceptions import AudioDeviceError
from ai.audio.settings import AudioSettings, audio_settings
from ai.telemetry import get_logger

logger = get_logger("ai.audio")


class AudioEngine:
    """Orquestrador principal do módulo de áudio.

    Responsável por:
    - Inicializar e gerenciar dispositivos de áudio
    - Fornecer interface unificada para captura e reprodução
    - Coordenar módulos especializados (VAD, STT, TTS, etc.)
    """

    def __init__(self, settings: AudioSettings | None = None) -> None:
        self._settings = settings or audio_settings
        self._initialized = False
        self._vad: Any = None
        self._stt: Any = None
        self._tts: Any = None

        # Garantir diretório temporário
        temp_dir = Path(self._settings.record_temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "AudioEngine criado (sample_rate=%s, input=%s, output=%s)",
            self._settings.sample_rate,
            self._settings.input_device,
            self._settings.output_device,
        )

    # ── Propriedades ──────────────────────────────────────────────────────

    @property
    def settings(self) -> AudioSettings:
        return self._settings

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def sample_rate(self) -> int:
        return self._settings.sample_rate

    # ── Inicialização ─────────────────────────────────────────────────────

    async def initialize(self) -> bool:
        """Inicializa o motor de áudio e verifica dispositivos.

        Returns:
            True se a inicialização foi bem-sucedida.
        """
        if self._initialized:
            return True

        logger.info("Inicializando AudioEngine...")

        # Verificar dependências do sistema
        deps_ok = await self._check_dependencies()
        if not deps_ok:
            logger.warning("Algumas dependências de áudio estão ausentes")

        # Verificar dispositivo de entrada
        input_ok = await self._check_input_device()
        output_ok = await self._check_output_device()

        if not input_ok and not output_ok:
            raise AudioDeviceError(
                "Nenhum dispositivo de áudio encontrado",
                "Verifique se o PipeWire/PulseAudio está rodando",
            )

        self._initialized = True
        logger.info("AudioEngine inicializado (input=%s, output=%s)", input_ok, output_ok)
        return True

    async def shutdown(self) -> None:
        """Libera recursos do motor de áudio."""
        self._initialized = False
        logger.info("AudioEngine finalizado")

    # ── Verificação de dependências ───────────────────────────────────────

    async def _check_dependencies(self) -> bool:
        """Verifica se as ferramentas de linha de comando estão disponíveis."""
        tools = ["pactl", "ffmpeg", "arecord", "aplay"]
        all_ok = True

        for tool in tools:
            found = self._which(tool) is not None
            if not found:
                logger.warning("Ferramenta ausente: %s", tool)
                all_ok = False

        return all_ok

    async def _check_input_device(self) -> bool:
        """Verifica se o dispositivo de entrada está acessível."""
        try:
            result = subprocess.run(
                ["pactl", "get-default-source"], capture_output=True, text=True, timeout=3
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def _check_output_device(self) -> bool:
        """Verifica se o dispositivo de saída está acessível."""
        try:
            result = subprocess.run(
                ["pactl", "get-default-sink"], capture_output=True, text=True, timeout=3
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    # ── Métodos utilitários ───────────────────────────────────────────────

    @staticmethod
    def _which(program: str) -> str | None:
        """Retorna o caminho completo de um executável ou None."""
        import shutil

        return shutil.which(program)

    def get_default_source(self) -> str | None:
        """Retorna o nome do source (microfone) padrão do sistema."""
        try:
            result = subprocess.run(
                ["pactl", "get-default-source"], capture_output=True, text=True, timeout=3
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def get_default_sink(self) -> str | None:
        """Retorna o nome do sink (alto-falante) padrão do sistema."""
        try:
            result = subprocess.run(
                ["pactl", "get-default-sink"], capture_output=True, text=True, timeout=3
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _list_devices(self, device_type: str) -> list[dict[str, Any]]:
        """Lista dispositivos de áudio via pactl.

        Args:
            device_type: 'sources' ou 'sinks'.

        Returns:
            Lista de dicionários com index, name e state.
        """
        devices: list[dict[str, Any]] = []
        try:
            result = subprocess.run(
                ["pactl", "list", device_type, "short"], capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        devices.append({"index": parts[0], "name": parts[1], "state": parts[-1]})
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return devices

    def list_sources(self) -> list[dict[str, Any]]:
        """Lista todas as fontes de entrada (microfones) disponíveis."""
        return self._list_devices("sources")

    def list_sinks(self) -> list[dict[str, Any]]:
        """Lista todos os sinks de saída (alto-falantes) disponíveis."""
        return self._list_devices("sinks")

    # ── Status / health ───────────────────────────────────────────────────

    async def get_status(self) -> dict[str, Any]:
        """Retorna o status completo do sistema de áudio.

        Returns:
            Dicionário com informações de dispositivos, dependências e config.
        """
        return {
            "initialized": self._initialized,
            "sample_rate": self._settings.sample_rate,
            "devices": {
                "default_source": self.get_default_source(),
                "default_sink": self.get_default_sink(),
                "sources": len(self.list_sources()),
                "sinks": len(self.list_sinks()),
            },
            "tools": {
                "pactl": self._which("pactl") is not None,
                "ffmpeg": self._which("ffmpeg") is not None,
                "arecord": self._which("arecord") is not None,
                "aplay": self._which("aplay") is not None,
                "sox": self._which("sox") is not None,
            },
            "temp_dir": self._settings.record_temp_dir,
            "vad_aggressiveness": self._settings.vad_aggressiveness,
            "stt_model": self._settings.stt_model,
            "tts_engine": self._settings.tts_engine,
        }
