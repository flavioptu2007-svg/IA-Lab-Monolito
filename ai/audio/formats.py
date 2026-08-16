"""Conversão entre formatos de áudio.

Utiliza ffmpeg (via subprocess) como engine principal, com suporte
a soundfile e scipy para manipulação direta de arrays numpy.

Suporta:
- Conversão entre WAV, MP3, FLAC, OGG, PCM
- Extração de metadados de arquivos de áudio
- Informações de duração, sample rate, canais
- Detecção de formato por assinatura (magic bytes)
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ai.audio.exceptions import AudioConversionError, AudioFormatError
from ai.audio.settings import audio_settings
from ai.telemetry import get_logger

logger = get_logger("ai.audio.formats")

# Formatos suportados e suas extensões
SUPPORTED_FORMATS = {
    ".wav": "WAV (PCM)",
    ".mp3": "MPEG Audio Layer III",
    ".flac": "Free Lossless Audio Codec",
    ".ogg": "Ogg Vorbis",
    ".opus": "Ogg Opus",
    ".aac": "AAC (Advanced Audio Coding)",
    ".m4a": "MPEG-4 Audio",
    ".wma": "Windows Media Audio",
    ".pcm": "PCM raw (sem header)",
    ".raw": "PCM raw (sem header)",
    ".s16le": "Signed 16-bit Little-Endian PCM",
}

# Magic bytes para detecção de formato
MAGIC_BYTES: dict[str, bytes] = {
    "wav": b"RIFF",
    "flac": b"fLaC",
    "ogg": b"OggS",
    "mp3": b"\xff\xfb",
    "opus": b"OpusHead",
}


# ── Detecção de formato ──────────────────────────────────────────────────────


def detect_format(filepath: str | bytes) -> str:
    """Detecta o formato de áudio pela extensão ou magic bytes.

    Args:
        filepath: Caminho do arquivo ou bytes do cabeçalho.

    Returns:
        Extensão do formato detectado (ex: '.wav', '.mp3').

    Raises:
        AudioFormatError: Se o formato não for detectado ou suportado.
    """
    if isinstance(filepath, bytes):
        header = filepath[:64]
    else:
        try:
            with open(filepath, "rb") as f:
                header = f.read(64)
        except FileNotFoundError:
            # Arquivo inexistente — tenta detectar pela extensao
            ext = Path(filepath).suffix.lower()
            if ext in SUPPORTED_FORMATS:
                return ext
            raise AudioFormatError("Arquivo nao encontrado", filepath) from None

    # Detecta por magic bytes
    for fmt, magic in MAGIC_BYTES.items():
        if header.startswith(magic):
            return f".{fmt}"

    # Detecta por extensão
    if isinstance(filepath, str):
        ext = Path(filepath).suffix.lower()
        if ext in SUPPORTED_FORMATS:
            return ext

    # Tenta ffprobe
    if isinstance(filepath, str):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_format", filepath],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("format_name="):
                        name = line.split("=", 1)[1].strip()
                        return f".{name.split(',')[0]}"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    raise AudioFormatError(
        "Formato de áudio não detectado", f"Primeiros bytes: {header[:16].hex()}"
    )


def get_audio_info(filepath: str) -> dict[str, Any]:
    """Obtém informações detalhadas de um arquivo de áudio via ffprobe.

    Args:
        filepath: Caminho do arquivo de áudio.

    Returns:
        Dicionário com duração, sample_rate, canais, codec, etc.

    Raises:
        AudioFormatError: Se não for possível ler o arquivo.
    """
    if not Path(filepath).exists():
        raise AudioFormatError("Arquivo não encontrado", filepath)

    info: dict[str, Any] = {
        "filename": Path(filepath).name,
        "size_bytes": Path(filepath).stat().st_size,
        "format": Path(filepath).suffix.lower(),
    }

    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        filepath,
    ]

    try:
        import json

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            data = json.loads(result.stdout)

            # Informações do formato
            fmt = data.get("format", {})
            info.update(
                {
                    "duration_sec": float(fmt.get("duration", 0)),
                    "bitrate": int(fmt.get("bit_rate", 0)),
                    "codec": fmt.get("format_name", ""),
                }
            )

            # Informações do stream de áudio
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    info.update(
                        {
                            "sample_rate": int(stream.get("sample_rate", 0)),
                            "channels": int(stream.get("channels", 0)),
                            "codec": stream.get("codec_name", info.get("codec")),
                        }
                    )
                    break

    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        logger.warning("ffprobe falhou para %s: %s", filepath, e)

    return info


# ── Conversão ────────────────────────────────────────────────────────────────


def convert(
    input_path: str | bytes,
    output_format: str,
    output_path: str | None = None,
    sample_rate: int | None = None,
    channels: int | None = None,
    bitrate: str | None = None,
) -> bytes:
    """Converte áudio entre formatos.

    Args:
        input_path: Caminho do arquivo de entrada ou bytes PCM.
        output_format: Formato de saída (ex: '.wav', '.mp3', '.flac').
        output_path: Caminho de saída (opcional — retorna bytes se omitido).
        sample_rate: Taxa de amostragem desejada.
        channels: Número de canais desejado.
        bitrate: Bitrate para formatos comprimidos (ex: '192k').

    Returns:
        Bytes do áudio convertido (se output_path for None).

    Raises:
        AudioConversionError: Se a conversão falhar.
    """
    output_format = output_format.lower()
    if not output_format.startswith("."):
        output_format = f".{output_format}"

    sr = sample_rate or audio_settings.sample_rate
    ch = channels or audio_settings.channels

    # Determina codec pelo formato
    codec_map = {
        ".wav": "pcm_s16le",
        ".mp3": "libmp3lame",
        ".flac": "flac",
        ".ogg": "libvorbis",
        ".opus": "libopus",
        ".aac": "aac",
        ".m4a": "aac",
    }
    codec = codec_map.get(output_format, "pcm_s16le")

    is_pipe = output_path is None

    cmd = ["ffmpeg", "-y"]

    if isinstance(input_path, bytes):
        # Entrada via stdin (PCM raw)
        cmd.extend(["-f", "s16le", "-ar", str(sr), "-ac", str(ch), "-i", "-"])
    else:
        cmd.extend(["-i", input_path])

    # Configurações de saída
    cmd.extend(["-ar", str(sr), "-ac", str(ch)])

    if codec == "pcm_s16le":
        cmd.extend(["-sample_fmt", "s16"])
    elif bitrate:
        cmd.extend(["-b:a", bitrate])

    if output_format in codec_map:
        cmd.extend(["-c:a", codec])

    if is_pipe:
        cmd.extend(["-f", output_format.lstrip("."), "-"])
    else:
        cmd.append(str(output_path))

    try:
        logger.debug(
            "Convertendo áudio para %s (sr=%d, ch=%d, codec=%s)", output_format, sr, ch, codec
        )

        stdin_data = input_path if isinstance(input_path, bytes) else None
        result = subprocess.run(cmd, input=stdin_data, capture_output=is_pipe, timeout=60)

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[:300]
            raise AudioConversionError(f"Falha na conversão para {output_format}", stderr)

        if is_pipe:
            out = result.stdout
            # ffmpeg em modo pipe grava tamanhos 0xFFFFFFFF no WAV (streaming).
            # Corrige os campos de tamanho para o WAV ficar válido em qualquer player.
            if output_format == ".wav" and out[:4] == b"RIFF" and len(out) > 44:
                import struct

                wav = bytearray(out)
                struct.pack_into("<I", wav, 4, len(wav) - 8)  # RIFF size
                # Encontra o chunk 'data' e corrige seu tamanho
                pos = 12
                while pos < len(wav) - 8:
                    cid = wav[pos : pos + 4]
                    csize = struct.unpack_from("<I", wav, pos + 4)[0]
                    if cid == b"data":
                        struct.pack_into("<I", wav, pos + 4, len(wav) - (pos + 8))
                        break
                    pos += 8 + csize
                out = bytes(wav)
            logger.debug("Conversão concluída: %d bytes", len(out))
            return out
        else:
            logger.debug("Arquivo salvo: %s", output_path)
            return b""

    except FileNotFoundError:
        raise AudioConversionError(
            "ffmpeg não encontrado", "Instale com: sudo apt install ffmpeg"
        ) from None
    except subprocess.TimeoutExpired:
        raise AudioConversionError("Timeout na conversão de áudio") from None


# ── Conversões específicas ───────────────────────────────────────────────────


def to_wav(
    input_path: str | bytes, output_path: str | None = None, sample_rate: int | None = None
) -> bytes:
    """Converte para WAV PCM 16-bit.

    Args:
        input_path: Caminho do arquivo ou bytes PCM.
        output_path: Caminho de saída (opcional).
        sample_rate: Taxa de amostragem.

    Returns:
        Bytes WAV se output_path for None.
    """
    return convert(input_path, ".wav", output_path, sample_rate=sample_rate)


def to_mp3(input_path: str | bytes, output_path: str | None = None, bitrate: str = "192k") -> bytes:
    """Converte para MP3.

    Args:
        input_path: Caminho do arquivo ou bytes PCM.
        output_path: Caminho de saída (opcional).
        bitrate: Bitrate (ex: '128k', '192k', '320k').

    Returns:
        Bytes MP3 se output_path for None.
    """
    return convert(input_path, ".mp3", output_path, bitrate=bitrate)


def to_flac(
    input_path: str | bytes, output_path: str | None = None, sample_rate: int | None = None
) -> bytes:
    """Converte para FLAC (compressão sem perdas).

    Args:
        input_path: Caminho do arquivo ou bytes PCM.
        output_path: Caminho de saída (opcional).
        sample_rate: Taxa de amostragem.

    Returns:
        Bytes FLAC se output_path for None.
    """
    return convert(input_path, ".flac", output_path, sample_rate=sample_rate)


def to_pcm(
    input_path: str | bytes, output_path: str | None = None, sample_rate: int | None = None
) -> bytes:
    """Converte para PCM raw 16-bit mono.

    Args:
        input_path: Caminho do arquivo ou bytes PCM.
        output_path: Caminho de saída (opcional).
        sample_rate: Taxa de amostragem.

    Returns:
        Bytes PCM se output_path for None.
    """
    return convert(
        input_path,
        ".pcm",
        output_path,
        sample_rate=sample_rate or audio_settings.sample_rate,
        channels=1,
    )


# ── Metadados úteis ──────────────────────────────────────────────────────────


def get_duration(filepath: str) -> float:
    """Retorna a duração de um arquivo de áudio em segundos.

    Args:
        filepath: Caminho do arquivo.

    Returns:
        Duração em segundos, ou 0 se não for possível determinar.
    """
    info = get_audio_info(filepath)
    return float(info.get("duration_sec", 0))


def get_sample_rate(filepath: str) -> int:
    """Retorna a taxa de amostragem de um arquivo de áudio.

    Args:
        filepath: Caminho do arquivo.

    Returns:
        Sample rate em Hz, ou 0 se não for possível determinar.
    """
    info = get_audio_info(filepath)
    return int(info.get("sample_rate", 0))


def get_human_readable_info(filepath: str) -> str:
    """Retorna uma string formatada com informações do arquivo de áudio.

    Args:
        filepath: Caminho do arquivo.

    Returns:
        String legível com as principais informações.
    """
    info = get_audio_info(filepath)

    duration = info.get("duration_sec", 0)
    minutes = int(duration // 60)
    seconds = int(duration % 60)

    size = info.get("size_bytes", 0)
    if size > 1024 * 1024:
        size_str = f"{size / (1024 * 1024):.1f} MB"
    elif size > 1024:
        size_str = f"{size / 1024:.1f} KB"
    else:
        size_str = f"{size} B"

    return (
        f"📁 {info.get('filename', 'N/A')}\n"
        f"  Formato: {info.get('format', 'N/A')}\n"
        f"  Codec:   {info.get('codec', 'N/A')}\n"
        f"  Duração: {minutes:02d}:{seconds:02d}\n"
        f"  Taxa:    {info.get('sample_rate', 'N/A')} Hz\n"
        f"  Canais:  {info.get('channels', 'N/A')}\n"
        f"  Bitrate: {info.get('bitrate', 'N/A')} bps\n"
        f"  Tamanho: {size_str}"
    )
