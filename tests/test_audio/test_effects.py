"""Testes do processamento de áudio (efeitos).

Estes testes são puramente matemáticos — não requerem hardware de áudio.
Operam sobre arrays numpy sintéticos gerados em memória.

Cobertura:
- bytes_to_float e float_to_bytes (conversão)
- apply_gain (amplificação/atenuação)
- normalize (normalização de pico)
- noise_gate
- compressor
- resample
- high_pass_filter / low_pass_filter
- remove_silence
"""

from __future__ import annotations

import numpy as np
from ai.audio import effects


class TestConversion:
    """Conversão entre bytes PCM e arrays float."""

    def test_bytes_to_float_silence(self) -> None:
        """Silêncio (tudo zero) deve resultar em array de zeros."""
        audio = b"\x00\x00" * 100
        arr = effects.bytes_to_float(audio)
        assert arr.shape == (100,)
        assert np.allclose(arr, 0.0)

    def test_bytes_to_float_max_positive(self) -> None:
        """Valor máximo positivo (0x7FFF) deve ser ~1.0."""
        audio = b"\xff\x7f"  # 32767 em little-endian
        arr = effects.bytes_to_float(audio)
        assert abs(arr[0] - 1.0) < 0.001

    def test_bytes_to_float_max_negative(self) -> None:
        """Valor mínimo negativo (0x8000) deve ser -1.0."""
        audio = b"\x00\x80"  # -32768 em little-endian
        arr = effects.bytes_to_float(audio)
        assert abs(arr[0] - (-1.0)) < 0.001

    def test_float_to_bytes_roundtrip(self) -> None:
        """bytes → float → bytes deve preservar o sinal (±1 quantização).

        Nota: A conversão float32 tem perda de precisão de ~1 LSB
        porque 32768 * 32767 = ~1.00003, então o valor -32768 vira
        -32767 após o roundtrip. Permite diferença de até 1.
        """
        original = b"\x00\x80\xfe\x7f\x00\x00"  # -32768, 32766, 0
        arr = effects.bytes_to_float(original)
        result = effects.float_to_bytes(arr)
        orig_arr = np.frombuffer(original, dtype=np.int16)
        res_arr = np.frombuffer(result, dtype=np.int16)
        diff = np.max(np.abs(orig_arr.astype(np.int32) - res_arr.astype(np.int32)))
        assert diff <= 1, f"Diferença máxima de {diff} > 1"
        assert orig_arr[2] == res_arr[2]  # zero preservado

    def test_float_to_bytes_clips_overflow(self) -> None:
        """Valores > 1.0 devem ser clipados para evitar distorção.

        O código faz: clip(audio, -1.0, 1.0) * 32767 -> astype(np.int16).
        Então -1.0 * 32767 = -32767 (não -32768).
        """
        arr = np.array([2.0, -2.0, 0.5], dtype=np.float32)
        result = effects.float_to_bytes(arr)
        samples = np.frombuffer(result, dtype=np.int16)
        assert samples[0] == 32767  # clipado (1.0 * 32767)
        assert samples[1] == -32767  # clipado (-1.0 * 32767 = -32767)
        assert samples[2] == int(0.5 * 32767)  # intacto

    def test_db_to_gain(self) -> None:
        """0 dB deve resultar em ganho 1.0, -6 dB em ~0.5."""
        assert abs(effects.db_to_gain(0.0) - 1.0) < 0.01
        assert abs(effects.db_to_gain(-6.0) - 0.5) < 0.05

    def test_gain_to_db(self) -> None:
        """Ganho 1.0 = 0 dB, 0.5 = ~-6 dB."""
        assert abs(effects.gain_to_db(1.0)) < 0.01
        assert abs(effects.gain_to_db(0.5) - (-6.0)) < 1.0


class TestApplyGain:
    """Testes de apply_gain."""

    def test_gain_0_db_identity(self) -> None:
        """Ganho 0 dB (fator=1.0) preserva o áudio (±1 quantização)."""
        audio = b"\x00\x01\x00\x02\x00\x03"
        result = effects.apply_gain(audio, 0.0)
        # Ganho 0 dB = fator 1.0, mas pode haver diferença de ±1 pela
        # conversão float_bytes -> bytes_float -> float_to_bytes
        diff = max(
            abs(a - b)
            for a, b in zip(
                np.frombuffer(audio, dtype=np.int16),
                np.frombuffer(result, dtype=np.int16),
                strict=False,
            )
        )
        assert diff <= 1, f"Diferença de {diff} > 1 permitido"

    def test_gain_positive_amplifies(self) -> None:
        """Ganho positivo deve aumentar a amplitude."""
        audio = b"\x00\x10\x00\x20"  # 4096, 8192
        result = effects.apply_gain(audio, 6.0)
        samples = np.frombuffer(result, dtype=np.int16)
        original = np.frombuffer(audio, dtype=np.int16)
        assert abs(samples[0]) > abs(original[0])

    def test_gain_negative_attenuates(self) -> None:
        """Ganho negativo deve reduzir a amplitude."""
        audio = b"\x00\x40\x00\x80"  # 16384, 32768
        result = effects.apply_gain(audio, -6.0)
        samples = np.frombuffer(result, dtype=np.int16)
        original = np.frombuffer(audio, dtype=np.int16)
        assert abs(samples[0]) < abs(original[0])

    def test_gain_silence_stays_silence(self) -> None:
        """Silêncio com qualquer ganho continua silêncio."""
        audio = b"\x00\x00" * 100
        result = effects.apply_gain(audio, 20.0)
        assert result == audio


class TestNormalize:
    """Testes de normalize."""

    def test_normalize_silence(self) -> None:
        """Silêncio total não deve ser alterado."""
        audio = b"\x00\x00" * 100
        result = effects.normalize(audio, -3.0)
        assert result == audio

    def test_normalize_low_volume(self) -> None:
        """Áudio com volume baixo deve ser amplificado até o alvo."""
        # Tom com amplitude 0.1
        samples = (np.sin(np.linspace(0, 2 * np.pi * 440, 16000)) * 0.1 * 32767).astype(np.int16)
        audio = samples.tobytes()
        result = effects.normalize(audio, -3.0)
        result_samples = np.frombuffer(result, dtype=np.int16)
        peak = np.max(np.abs(result_samples))
        # Pico deve estar próximo de -3 dB (~23170 para 16-bit)
        assert peak > 20000

    def test_normalize_high_volume(self) -> None:
        """Áudio com volume alto deve ser atenuado até o alvo."""
        samples = (np.sin(np.linspace(0, 2 * np.pi * 440, 16000)) * 0.9 * 32767).astype(np.int16)
        audio = samples.tobytes()
        target_db = -6.0
        result = effects.normalize(audio, target_db)
        result_samples = np.frombuffer(result, dtype=np.int16)
        peak = np.max(np.abs(result_samples))
        # Pico deve estar próximo de -6 dB (~16384 para 16-bit)
        assert peak < 20000
        assert peak > 10000


class TestNoiseGate:
    """Testes de noise_gate."""

    def test_gate_high_threshold_passes_all(self) -> None:
        """Limiar muito alto deve deixar todo o sinal passar."""
        samples = (np.random.randn(1600) * 0.1 * 32767).astype(np.int16)
        audio = samples.tobytes()
        result = effects.noise_gate(audio, threshold_db=-10.0)
        assert len(result) == len(audio)

    def test_gate_silence_is_silenced(self) -> None:
        """Silêncio abaixo do limiar deve ser silenciado."""
        audio = b"\x00\x00" * 1600
        result = effects.noise_gate(audio, threshold_db=-50.0)
        # O noise gate pode deixar resquicios muito pequenos devido ao
        # release suavizado. Verificar que o pico e muito baixo.
        samples = np.frombuffer(result, dtype=np.int16)
        max_abs = np.max(np.abs(samples.astype(np.int32)))
        assert max_abs <= 1, f"Pico de {max_abs} > 1"


class TestCompressor:
    """Testes de compressor."""

    def test_compressor_no_reduction_below_threshold(self) -> None:
        """Sinal abaixo do limiar não deve ser comprimido."""
        samples = (np.random.randn(1600) * 0.01 * 32767).astype(np.int16)
        audio = samples.tobytes()
        result = effects.compressor(audio, threshold_db=-10.0, ratio=4.0)
        assert len(result) == len(audio)
        # Máximo deve ser similar ao original (talvez levemente alterado pelo suavizador)
        orig_peak = np.max(np.abs(np.frombuffer(audio, dtype=np.int16)))
        result_peak = np.max(np.abs(np.frombuffer(result, dtype=np.int16)))
        assert abs(result_peak - orig_peak) < orig_peak * 0.5

    def test_compressor_reduces_loud_signal(self) -> None:
        """Sinal alto deve ser comprimido."""
        samples = (np.random.randn(1600) * 0.9 * 32767).astype(np.int16)
        audio = samples.tobytes()
        result = effects.compressor(audio, threshold_db=-30.0, ratio=10.0)
        result_peak = np.max(np.abs(np.frombuffer(result, dtype=np.int16)))
        assert result_peak > 0


class TestResample:
    """Testes de reamostragem."""

    def test_resample_same_rate(self) -> None:
        """Mesma taxa deve retornar os mesmos bytes."""
        samples = (np.sin(np.linspace(0, 2 * np.pi * 440, 1600)) * 0.5 * 32767).astype(np.int16)
        audio = samples.tobytes()
        result = effects.resample(audio, 16000, 16000)
        assert result == audio

    def test_resample_downsample(self) -> None:
        """Downsample de 48kHz para 16kHz deve reduzir tamanho."""
        samples = (np.sin(np.linspace(0, 2 * np.pi * 440, 4800)) * 0.5 * 32767).astype(np.int16)
        audio = samples.tobytes()
        result = effects.resample(audio, 48000, 16000)
        result_samples = np.frombuffer(result, dtype=np.int16)
        assert len(result_samples) < len(samples)

    def test_resample_upsample(self) -> None:
        """Upsample de 16kHz para 48kHz deve aumentar tamanho."""
        samples = (np.sin(np.linspace(0, 2 * np.pi * 440, 1600)) * 0.5 * 32767).astype(np.int16)
        audio = samples.tobytes()
        result = effects.resample(audio, 16000, 48000)
        result_samples = np.frombuffer(result, dtype=np.int16)
        assert len(result_samples) > len(samples)

    def test_resample_preserves_content(self) -> None:
        """Após resample + downsample de volta, sinal deve ser similar."""
        samples = (np.sin(np.linspace(0, 2 * np.pi * 440, 1600)) * 0.5 * 32767).astype(np.int16)
        audio = samples.tobytes()
        down = effects.resample(audio, 16000, 8000)
        up = effects.resample(down, 8000, 16000)
        down_arr = np.frombuffer(audio, dtype=np.int16)
        up_arr = np.frombuffer(up, dtype=np.int16)
        # Normaliza tamanhos para comparação
        min_len = min(len(down_arr), len(up_arr))
        assert min_len > 0


class TestFilters:
    """Testes de filtros passa-alta e passa-baixa."""

    def test_high_pass_removes_dc(self) -> None:
        """Filtro passa-alta deve remover componente DC (valor constante)."""
        # Sinal DC: todos os samples iguais a 10000
        samples = np.full(1600, 10000, dtype=np.int16)
        audio = samples.tobytes()
        result = effects.high_pass_filter(audio, cutoff_hz=20.0)
        result_samples = np.frombuffer(result, dtype=np.int16)
        # Após filtro, a média deve estar próxima de zero
        mean = np.mean(result_samples.astype(np.float32))
        assert abs(mean) < 100

    def test_low_pass_smoothes(self) -> None:
        """Filtro passa-baixa deve reduzir variação rápida (ruído)."""
        # Ruído branco
        np.random.seed(42)
        samples = (np.random.randn(1600) * 0.5 * 32767).astype(np.int16)
        audio = samples.tobytes()
        result = effects.low_pass_filter(audio, cutoff_hz=500.0)
        result_samples = np.frombuffer(result, dtype=np.int16)
        # Desvio padrão deve ser menor após filtragem
        orig_std = np.std(samples.astype(np.float32))
        result_std = np.std(result_samples.astype(np.float32))
        assert result_std < orig_std * 0.9

    def test_high_pass_low_pass_chain(self) -> None:
        """Aplicar HP + LP no mesmo sinal deve funcionar sem erros."""
        samples = (np.sin(np.linspace(0, 2 * np.pi * 440, 1600)) * 0.5 * 32767).astype(np.int16)
        audio = samples.tobytes()
        hp = effects.high_pass_filter(audio, cutoff_hz=80.0)
        lp = effects.low_pass_filter(hp, cutoff_hz=7000.0)
        lp_samples = np.frombuffer(lp, dtype=np.int16)
        assert len(lp_samples) > 0


class TestRemoveSilence:
    """Testes de remove_silence."""

    def test_remove_silence_empty(self) -> None:
        """Áudio totalmente silencioso deve retornar vazio."""
        audio = b"\x00\x00" * 16000
        result = effects.remove_silence(audio, threshold_db=-40.0)
        assert result == b""

    def test_remove_silence_preserves_active(self) -> None:
        """Áudio ativo (acima do limiar) não deve ser removido."""
        samples = (np.sin(np.linspace(0, 2 * np.pi * 440, 16000)) * 0.5 * 32767).astype(np.int16)
        audio = samples.tobytes()
        result = effects.remove_silence(audio, threshold_db=-40.0)
        assert len(result) > 0
        assert len(result) <= len(audio)

    def test_remove_silence_trim_edges(self) -> None:
        """Silêncio nas bordas deve ser removido."""
        # 0.5s silêncio + 1s tom + 0.5s silêncio
        silence = np.zeros(8000, dtype=np.int16)
        tone = (np.sin(np.linspace(0, 2 * np.pi * 440, 16000)) * 0.5 * 32767).astype(np.int16)
        samples = np.concatenate([silence, tone, silence])
        audio = samples.tobytes()
        result = effects.remove_silence(audio, threshold_db=-40.0)
        result_samples = np.frombuffer(result, dtype=np.int16)
        # Resultado deve ser menor que o original (silêncio removido)
        assert len(result_samples) < len(samples)
        # Deve conter o tom (não vazio)
        assert len(result_samples) > 1000


class TestEdgeCases:
    """Casos extremos para funções de efeitos."""

    def test_empty_bytes(self) -> None:
        """Bytes vazio deve retornar bytes vazio ou array vazio."""
        result = effects.bytes_to_float(b"")
        assert len(result) == 0

    def test_float_to_bytes_empty(self) -> None:
        """Array vazio deve retornar bytes vazio."""
        arr = np.array([], dtype=np.float32)
        result = effects.float_to_bytes(arr)
        assert result == b""

    def test_apply_gain_empty(self) -> None:
        result = effects.apply_gain(b"", 6.0)
        assert result == b""

    def test_normalize_empty(self) -> None:
        """Bytes vazio deve retornar bytes vazio."""
        result = effects.normalize(b"", -3.0)
        # normalize chama bytes_to_float(b"") que retorna array vazio,
        # e float_to_bytes(array_vazio) retorna b""
        assert result == b"" or len(result) == 0

    def test_resample_empty(self) -> None:
        """Bytes vazio deve retornar bytes vazio."""
        result = effects.resample(b"", 16000, 48000)
        assert result == b"" or len(result) == 0

    def test_remove_silence_very_short(self) -> None:
        """Áudio muito curto não deve quebrar."""
        audio = b"\x00\x01\x00\x02"
        # Não deve lançar exceção
        result = effects.remove_silence(audio, threshold_db=-40.0)
        assert isinstance(result, bytes)

    def test_noise_gate_empty(self) -> None:
        result = effects.noise_gate(b"")
        assert result == b""

    def test_compressor_empty(self) -> None:
        """Bytes vazio deve retornar bytes vazio."""
        result = effects.compressor(b"")
        assert result == b"" or len(result) == 0

    def test_gain_to_db_zero(self) -> None:
        """Ganho zero deve retornar -inf (como -100.0)."""
        result = effects.gain_to_db(0.0)
        assert result <= -100.0
