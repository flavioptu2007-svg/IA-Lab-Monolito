"""Exceções personalizadas para o módulo de áudio do IA-Lab.

Hierarquia:
  AudioError (base)
  ├── AudioDeviceError    — Dispositivo não encontrado ou inacessível
  ├── AudioCaptureError   — Falha na captura de áudio
  ├── AudioPlaybackError  — Falha na reprodução de áudio
  ├── AudioFormatError    — Formato não suportado ou inválido
  ├── AudioConversionError— Falha na conversão entre formatos
  ├── VADError            — Erro no Voice Activity Detection
  ├── STTError            — Erro no Speech-to-Text
  ├── TTSError            — Erro no Text-to-Speech
  └── AudioConfigError    — Configuração inválida ou ausente
"""


class AudioError(Exception):
    """Exceção base para todos os erros do módulo de áudio."""

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self._format())

    def _format(self) -> str:
        if self.details:
            return f"{self.message} — {self.details}"
        return self.message


class AudioDeviceError(AudioError):
    """Dispositivo de áudio não encontrado, ocupado ou inacessível."""


class AudioCaptureError(AudioError):
    """Falha ao capturar áudio do dispositivo de entrada."""


class AudioPlaybackError(AudioError):
    """Falha ao reproduzir áudio no dispositivo de saída."""


class AudioFormatError(AudioError):
    """Formato de áudio não suportado ou inválido."""


class AudioConversionError(AudioError):
    """Falha na conversão entre formatos de áudio."""


class VADError(AudioError):
    """Erro relacionado ao Voice Activity Detection."""


class STTError(AudioError):
    """Erro no processo de Speech-to-Text (transcrição)."""


class TTSError(AudioError):
    """Erro no processo de Text-to-Speech (síntese de fala)."""


class AudioConfigError(AudioError):
    """Configuração de áudio inválida, ausente ou inconsistente."""
