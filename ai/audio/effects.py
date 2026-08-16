"""Processamento de áudio — noise gate, compressor, equalização e normalização.

Utiliza numpy para processamento eficiente de arrays de áudio.
Todos os efeitos operam sobre arrays numpy de 16-bit PCM.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as scipy_signal

from ai.audio.settings import audio_settings
from ai.telemetry import get_logger

logger = get_logger("ai.audio.effects")


# ── Utilitários de conversão ──────────────────────────────────────────────────


def bytes_to_float(audio_data: bytes) -> np.ndarray:
    """Converte bytes PCM 16-bit para array float32 normalizado (-1 a 1).

    Args:
        audio_data: Bytes PCM 16-bit little-endian.

    Returns:
        Array numpy float32 no range [-1, 1].
    """
    samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    return samples / 32768.0


def float_to_bytes(audio_array: np.ndarray) -> bytes:
    """Converte array float32 (-1 a 1) para bytes PCM 16-bit.

    Args:
        audio_array: Array numpy float32 no range [-1, 1].

    Returns:
        Bytes PCM 16-bit little-endian.
    """
    samples = np.clip(audio_array, -1.0, 1.0)
    samples_int16 = (samples * 32767).astype(np.int16)
    return samples_int16.tobytes()


def db_to_gain(db: float | np.ndarray) -> float | np.ndarray:
    """Converte dB para ganho linear (aceita escalares e arrays numpy)."""
    return 10.0 ** (db / 20.0)


def gain_to_db(gain: float | np.ndarray) -> float | np.ndarray:
    """Converte ganho linear para dB.

    Aceita escalares e arrays numpy (para uso em noise_gate, compressor).
    """
    if isinstance(gain, np.ndarray):
        result = np.full_like(gain, -100.0, dtype=np.float64)
        mask = gain > 0
        if np.any(mask):
            result[mask] = 20.0 * np.log10(gain[mask])
        return result
    if gain <= 0:
        return -100.0
    return 20.0 * np.log10(gain)


# ── Efeitos ──────────────────────────────────────────────────────────────────


def apply_gain(audio_data: bytes | np.ndarray, gain_db: float) -> bytes:
    """Aplica ganho (ou atenuação) ao sinal de áudio.

    Args:
        audio_data: Bytes PCM 16-bit ou array numpy.
        gain_db: Ganho em dB (positivo = amplifica, negativo = atenua).

    Returns:
        Áudio processado como bytes PCM 16-bit.
    """
    samples = bytes_to_float(audio_data) if isinstance(audio_data, bytes) else audio_data

    gain_linear = db_to_gain(gain_db)
    processed = samples * gain_linear

    logger.debug("Ganho aplicado: %+.1f dB (fator: %.2f)", gain_db, gain_linear)
    return float_to_bytes(processed)


def normalize(audio_data: bytes | np.ndarray, target_level_db: float = -3.0) -> bytes:
    """Normaliza o áudio para um nível alvo de pico.

    Args:
        audio_data: Bytes PCM 16-bit ou array numpy.
        target_level_db: Nível de pico alvo em dB (padrão: -3 dB).

    Returns:
        Áudio normalizado como bytes PCM 16-bit.
    """
    samples = bytes_to_float(audio_data) if isinstance(audio_data, bytes) else audio_data

    if len(samples) == 0:
        return float_to_bytes(samples)
    peak = float(np.max(np.abs(samples)))
    if peak <= 0:
        return float_to_bytes(samples)

    current_db = float(gain_to_db(peak))
    gain_needed = target_level_db - current_db

    logger.debug(
        "Normalizando: pico=%.1f dB → alvo=%.1f dB (ganho=%.1f dB)",
        current_db,
        target_level_db,
        gain_needed,
    )

    return apply_gain(samples, gain_needed)


def noise_gate(
    audio_data: bytes | np.ndarray,
    threshold_db: float | None = None,
    attack_sec: float | None = None,
    release_sec: float | None = None,
    sample_rate: int | None = None,
) -> bytes:
    """Aplica noise gate — silencia trechos abaixo do limiar.

    Args:
        audio_data: Bytes PCM 16-bit ou array numpy.
        threshold_db: Limiar em dB (padrão: configurado em settings).
        attack_sec: Tempo de attack em segundos.
        release_sec: Tempo de release em segundos.
        sample_rate: Taxa de amostragem em Hz.

    Returns:
        Áudio processado como bytes PCM 16-bit.
    """
    samples = bytes_to_float(audio_data) if isinstance(audio_data, bytes) else audio_data

    threshold = threshold_db or audio_settings.noise_gate_threshold
    attack = attack_sec or audio_settings.noise_gate_attack
    release = release_sec or audio_settings.noise_gate_release
    sr = sample_rate or audio_settings.sample_rate

    # Calcula envelope RMS
    frame_size = int(sr * 0.01)  # 10ms frames
    num_frames = len(samples) // frame_size

    if len(samples) == 0 or num_frames == 0:
        return float_to_bytes(samples)

    # RMS por frame
    frames = samples[: num_frames * frame_size].reshape(-1, frame_size)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    rms_db = np.asarray(gain_to_db(rms))

    # Gate
    gate_open = rms_db > threshold

    # Suaviza com attack/release
    attack_samples = int(attack * sr)
    release_samples = int(release * sr)

    smoothed = np.zeros(len(samples))
    current_gain = 0.0

    for i, is_open in enumerate(gate_open):
        start = i * frame_size
        end = min((i + 1) * frame_size, len(samples))

        target = 1.0 if is_open else 0.0
        transition_len = attack_samples if target > current_gain else release_samples

        for j in range(start, end):
            if transition_len > 0:
                frac = 1.0 / transition_len
                current_gain += (target - current_gain) * frac
            else:
                current_gain = target
            smoothed[j] = current_gain

    processed = samples * smoothed[: len(samples)]

    open_frames = int(np.sum(gate_open))
    logger.debug(
        "Noise gate: threshold=%.1f dB, frames abertos=%d/%d (%.0f%%)",
        threshold,
        open_frames,
        num_frames,
        100 * open_frames / num_frames,
    )

    return float_to_bytes(processed)


def compressor(
    audio_data: bytes | np.ndarray,
    threshold_db: float | None = None,
    ratio: float | None = None,
    attack_sec: float | None = None,
    release_sec: float | None = None,
    sample_rate: int | None = None,
) -> bytes:
    """Aplica compressão de faixa dinâmica.

    Args:
        audio_data: Bytes PCM 16-bit ou array numpy.
        threshold_db: Limiar em dB (padrão: config em settings).
        ratio: Taxa de compressão (ex: 4 = 4:1).
        attack_sec: Tempo de attack em segundos.
        release_sec: Tempo de release em segundos.
        sample_rate: Taxa de amostragem.

    Returns:
        Áudio comprimido como bytes PCM 16-bit.
    """
    samples = bytes_to_float(audio_data) if isinstance(audio_data, bytes) else audio_data

    threshold = threshold_db or audio_settings.compressor_threshold
    comp_ratio = ratio or audio_settings.compressor_ratio
    attack = attack_sec or audio_settings.compressor_attack
    release = release_sec or audio_settings.compressor_release
    sr = sample_rate or audio_settings.sample_rate

    if len(samples) == 0:
        return float_to_bytes(samples)

    # Converte para dB
    abs_samples = np.abs(samples)
    db_samples = np.asarray(gain_to_db(abs_samples + 1e-10))

    # Curva de compressão
    above_threshold = db_samples > threshold
    gain_reduction_db = np.zeros_like(db_samples)

    if np.any(above_threshold):
        excess = db_samples[above_threshold] - threshold
        gain_reduction_db[above_threshold] = excess * (1.0 - 1.0 / comp_ratio)

    # Suaviza com attack/release
    attack_samples = int(attack * sr)
    release_samples = int(release * sr)

    smoothed = np.zeros_like(gain_reduction_db)
    current_gain = 0.0

    for i in range(len(gain_reduction_db)):
        target = gain_reduction_db[i]
        transition = attack_samples if target < current_gain else release_samples
        frac = 1.0 / max(transition, 1)
        current_gain += (target - current_gain) * frac
        smoothed[i] = current_gain

    # Aplica ganho
    gain_linear = db_to_gain(-smoothed)
    processed = samples * gain_linear

    max_reduction = float(np.max(-smoothed))
    logger.debug(
        "Compressor: threshold=%.1f dB, ratio=%.1f:1, redução máx=%.1f dB",
        threshold,
        comp_ratio,
        max_reduction,
    )

    return float_to_bytes(processed)


def resample(audio_data: bytes | np.ndarray, original_rate: int, target_rate: int) -> bytes:
    """Reamostra o áudio para uma nova taxa de amostragem.

    Args:
        audio_data: Bytes PCM 16-bit ou array numpy.
        original_rate: Taxa de amostragem original.
        target_rate: Taxa de amostragem desejada.

    Returns:
        Áudio reamostrado como bytes PCM 16-bit.
    """
    if original_rate == target_rate:
        return audio_data if isinstance(audio_data, bytes) else float_to_bytes(audio_data)

    samples = bytes_to_float(audio_data) if isinstance(audio_data, bytes) else audio_data

    if len(samples) == 0:
        return float_to_bytes(samples)

    num_samples = max(1, round(len(samples) * target_rate / original_rate))
    resampled = scipy_signal.resample(samples, num_samples)

    logger.debug(
        "Reamostrado: %d → %d Hz (%d → %d amostras)",
        original_rate,
        target_rate,
        len(samples),
        num_samples,
    )

    return float_to_bytes(resampled)


def high_pass_filter(
    audio_data: bytes | np.ndarray, cutoff_hz: float = 80.0, sample_rate: int | None = None
) -> bytes:
    """Aplica filtro passa-alta para remover ruído de baixa frequência.

    Args:
        audio_data: Bytes PCM 16-bit ou array numpy.
        cutoff_hz: Frequência de corte em Hz (padrão: 80 Hz).
        sample_rate: Taxa de amostragem.

    Returns:
        Áudio filtrado como bytes PCM 16-bit.
    """
    samples = bytes_to_float(audio_data) if isinstance(audio_data, bytes) else audio_data

    sr = sample_rate or audio_settings.sample_rate
    nyquist = sr / 2
    normalized_cutoff = cutoff_hz / nyquist

    if len(samples) < 8:
        return float_to_bytes(samples)

    # Projeta filtro butterworth de 4ª ordem
    b, a = scipy_signal.butter(4, normalized_cutoff, btype="high", analog=False)
    filtered = scipy_signal.filtfilt(b, a, samples)

    logger.debug("Filtro passa-alta: %s Hz", cutoff_hz)
    return float_to_bytes(filtered)


def low_pass_filter(
    audio_data: bytes | np.ndarray, cutoff_hz: float = 8000.0, sample_rate: int | None = None
) -> bytes:
    """Aplica filtro passa-baixa para remover ruído de alta frequência.

    Args:
        audio_data: Bytes PCM 16-bit ou array numpy.
        cutoff_hz: Frequência de corte em Hz (padrão: 8 kHz).
        sample_rate: Taxa de amostragem.

    Returns:
        Áudio filtrado como bytes PCM 16-bit.
    """
    samples = bytes_to_float(audio_data) if isinstance(audio_data, bytes) else audio_data

    sr = sample_rate or audio_settings.sample_rate
    nyquist = sr / 2
    normalized_cutoff = cutoff_hz / nyquist

    if len(samples) < 8:
        return float_to_bytes(samples)

    b, a = scipy_signal.butter(4, normalized_cutoff, btype="low", analog=False)
    filtered = scipy_signal.filtfilt(b, a, samples)

    logger.debug("Filtro passa-baixa: %s Hz", cutoff_hz)
    return float_to_bytes(filtered)


def remove_silence(
    audio_data: bytes | np.ndarray,
    threshold_db: float = -40.0,
    min_silence_ms: int = 200,
    sample_rate: int | None = None,
) -> bytes:
    """Remove silêncios do início e fim do áudio.

    Args:
        audio_data: Bytes PCM 16-bit ou array numpy.
        threshold_db: Limiar de silêncio em dB.
        min_silence_ms: Duração mínima de silêncio para remover (ms).
        sample_rate: Taxa de amostragem.

    Returns:
        Áudio com silêncios removidos.
    """
    samples = bytes_to_float(audio_data) if isinstance(audio_data, bytes) else audio_data

    sr = sample_rate or audio_settings.sample_rate
    frame_size = int(sr * min_silence_ms / 1000)

    if len(samples) == 0 or frame_size <= 0 or len(samples) < frame_size:
        return float_to_bytes(samples)

    # RMS por frame
    num_frames = len(samples) // frame_size
    frames = samples[: num_frames * frame_size].reshape(-1, frame_size)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    rms_db = np.asarray(gain_to_db(rms))

    # Encontra primeiro e último frame acima do limiar
    active_frames = np.where(rms_db > threshold_db)[0]

    if len(active_frames) == 0:
        logger.debug("Todos os frames estão abaixo de %.1f dB — áudio vazio", threshold_db)
        return b""

    start_frame = active_frames[0]
    end_frame = active_frames[-1] + 1

    trimmed = samples[start_frame * frame_size : end_frame * frame_size]

    removed_start = start_frame * frame_size / sr
    removed_end = (len(samples) - end_frame * frame_size) / sr
    logger.debug("Silêncio removido: %.1fs início, %.1fs fim", removed_start, removed_end)

    return float_to_bytes(trimmed)
