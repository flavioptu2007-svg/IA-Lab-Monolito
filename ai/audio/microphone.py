"""Gerenciamento do microfone virtual do IA-Lab.

Cria e gerencia um null-sink + loopback no PipeWire para servir como
microfone virtual. Permite que apps de IA (STT, voice assistants)
capturem o áudio do sistema como se fosse um microfone físico.

Uso típico:
    vmic = VirtualMicrophone()
    await vmic.create()
    # ... apps usam o microfone virtual ...
    await vmic.remove()
"""

from __future__ import annotations

import contextlib
import subprocess
import time
from typing import Any

from ai.audio.exceptions import AudioDeviceError
from ai.audio.settings import audio_settings
from ai.telemetry import get_logger

logger = get_logger("ai.audio.microphone")


class VirtualMicrophone:
    """Gerenciador do microfone virtual (null-sink + loopback no PipeWire).

    Attributes:
        sink_name: Nome do sink nulo no PipeWire.
        description: Descrição amigável do dispositivo.
    """

    def __init__(self, sink_name: str | None = None, description: str | None = None) -> None:
        self._sink_name = sink_name or audio_settings.virtual_mic_name
        self._description = description or audio_settings.virtual_mic_description
        self._is_active = False

    # ── Propriedades ──────────────────────────────────────────────────────

    @property
    def sink_name(self) -> str:
        return self._sink_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def source_name(self) -> str:
        """Nome do source (microfone) que os apps devem usar."""
        return f"{self._sink_name}.monitor"

    # ── Criação ───────────────────────────────────────────────────────────

    def create(self) -> bool:
        """Cria o microfone virtual no PipeWire.

        Passos:
        1. Cria null-sink (base do microfone virtual)
        2. Cria loopback do sink padrão para o null-sink
        3. Verifica se tudo foi criado corretamente

        Returns:
            True se foi criado com sucesso.

        Raises:
            AudioDeviceError: Se PipeWire não estiver rodando.
        """
        if self._is_active:
            logger.info("Microfone virtual já está ativo")
            return True

        if not self._check_pipewire():
            raise AudioDeviceError(
                "PipeWire não está rodando",
                "Execute: systemctl --user start pipewire pipewire-pulse",
            )

        logger.info("Criando microfone virtual (%s)...", self._sink_name)

        # Remove configuração anterior se existir
        self._cleanup_previous()

        # 1. Criar null-sink
        sink_index = self._create_null_sink()
        if sink_index is None:
            return False

        # 2. Criar loopback
        loopback_index = self._create_loopback()
        if loopback_index is None:
            # Não é crítico - o null-sink já funciona como mic virtual
            logger.warning(
                "Loopback não criado. O microfone virtual existirá, "
                "mas sem áudio do sistema roteado para ele."
            )

        # 3. Verificar
        time.sleep(0.3)
        if self._sink_exists():
            self._is_active = True
            logger.info(
                "Microfone virtual criado: %s → source=%s", self._sink_name, self.source_name
            )
            return True

        logger.error("Falha ao criar microfone virtual")
        return False

    def remove(self) -> bool:
        """Remove o microfone virtual do PipeWire.

        Returns:
            True se foi removido com sucesso.
        """
        logger.info("Removendo microfone virtual (%s)...", self._sink_name)

        modules = self._find_related_modules()
        if not modules:
            logger.info("Nenhum módulo do microfone virtual encontrado")
            self._is_active = False
            return True

        for mod_id in modules:
            try:
                subprocess.run(
                    ["pactl", "unload-module", str(mod_id)], capture_output=True, timeout=3
                )
                logger.debug("Módulo %s removido", mod_id)
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.warning("Falha ao remover módulo %s: %s", mod_id, e)

        time.sleep(0.3)

        if not self._sink_exists():
            self._is_active = False
            logger.info("Microfone virtual removido")
            return True

        logger.warning("Alguns módulos podem não ter sido removidos")
        return False

    def get_status(self) -> dict[str, Any]:
        """Retorna o status atual do microfone virtual.

        Returns:
            Dicionário com informações de status.
        """
        sink_exists = self._sink_exists()
        modules = self._find_related_modules()

        sink_detail: dict[str, Any] = {}
        if sink_exists:
            try:
                result = subprocess.run(
                    ["pactl", "list", "sinks"], capture_output=True, text=True, timeout=3
                )
                # Extrai info do sink específico
                in_section = False
                for line in result.stdout.split("\n"):
                    if self._sink_name in line:
                        in_section = True
                    if in_section:
                        for key in ("Name", "Description", "State", "Mute", "Volume"):
                            if key in line:
                                sink_detail[key.lower()] = line.strip()
                        if "Formato" in line or "Sample" in line:
                            sink_detail["format"] = line.strip()
                        if not line.strip() or "Source" in line.strip():
                            break
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return {
            "active": self._is_active,
            "sink_name": self._sink_name,
            "source_name": self.source_name,
            "description": self._description,
            "sink_exists": sink_exists,
            "modules": [{"id": m, "name": self._get_module_name(m)} for m in modules],
            "details": sink_detail,
        }

    # ── Métodos internos ──────────────────────────────────────────────────

    def _check_pipewire(self) -> bool:
        """Verifica se o PipeWire está rodando."""
        try:
            result = subprocess.run(["pactl", "info"], capture_output=True, timeout=3)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _sink_exists(self) -> bool:
        """Verifica se o sink virtual já existe."""
        try:
            result = subprocess.run(
                ["pactl", "list", "sinks", "short"], capture_output=True, text=True, timeout=3
            )
            return self._sink_name in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _find_related_modules(self) -> list[int]:
        """Encontra IDs dos módulos relacionados ao microfone virtual."""
        modules: list[int] = []
        try:
            result = subprocess.run(
                ["pactl", "list", "modules", "short"], capture_output=True, text=True, timeout=3
            )
            for line in result.stdout.split("\n"):
                if self._sink_name in line.lower() or "ia-lab" in line.lower():
                    parts = line.split()
                    if parts:
                        try:
                            modules.append(int(parts[0]))
                        except ValueError:
                            continue
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return modules

    def _get_module_name(self, module_id: int) -> str:
        """Retorna o nome descritivo de um módulo."""
        try:
            result = subprocess.run(
                ["pactl", "show-module", str(module_id)], capture_output=True, text=True, timeout=3
            )
            # Extrai o nome: "module-null-sink" ou similar
            for line in result.stdout.split("\n"):
                if "name:" in line.lower() or "argument:" in line.lower():
                    return line.strip()
            return f"module-{module_id}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return f"module-{module_id}"

    def _cleanup_previous(self) -> None:
        """Remove configuração anterior se existir."""
        modules = self._find_related_modules()
        for mod_id in modules:
            with contextlib.suppress(subprocess.TimeoutExpired):
                subprocess.run(
                    ["pactl", "unload-module", str(mod_id)], capture_output=True, timeout=3
                )

    def _create_null_sink(self) -> int | None:
        """Cria o null-sink que servirá como base do microfone virtual.

        Returns:
            Index do módulo criado, ou None se falhar.
        """
        cmd = [
            "pactl",
            "load-module",
            "module-null-sink",
            f"sink_name={self._sink_name}",
            f"sink_properties=device.description={self._description}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and result.stdout.strip().isdigit():
                index = int(result.stdout.strip())
                logger.info("Null-sink criado (módulo %d)", index)
                return index

            logger.error("Falha ao criar null-sink: %s", result.stderr.strip())
            return None

        except FileNotFoundError:
            logger.error("pactl não encontrado. PipeWire/PulseAudio está instalado?")
            return None
        except subprocess.TimeoutExpired:
            logger.error("Timeout ao criar null-sink")
            return None

    def _create_loopback(self) -> int | None:
        """Cria loopback do sink padrão para o microfone virtual.

        Returns:
            Index do módulo loopback, ou None se falhar.
        """
        # Descobre o sink padrão
        try:
            result = subprocess.run(
                ["pactl", "get-default-sink"], capture_output=True, text=True, timeout=3
            )
            default_sink = result.stdout.strip()
            if not default_sink:
                logger.warning("Nenhum sink padrão encontrado para loopback")
                return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Não foi possível obter o sink padrão")
            return None

        # Cria loopback: default_sink.monitor → null_sink
        source = f"{default_sink}.monitor"

        cmd = [
            "pactl",
            "load-module",
            "module-loopback",
            f"source={source}",
            f"sink={self._sink_name}",
            "latency_msec=25",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and result.stdout.strip().isdigit():
                index = int(result.stdout.strip())
                logger.info("Loopback criado: %s → %s (módulo %d)", source, self._sink_name, index)
                return index

            logger.warning("Falha ao criar loopback: %s", result.stderr.strip())
            return None

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning("Erro ao criar loopback: %s", e)
            return None
