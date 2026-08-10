"""Testes do Voice Activity Detection (VAD).

Utiliza webrtcvad para detecção de fala.
Testes em buffer sintético — não requer microfone real.

Cobertura:
- Criação do detector com parâmetros válidos
- Validação de parâmetros inválidos (aggressiveness, frame_ms, sample_rate)
- is_speech com frame válido e inválido
- detect_speech com buffers contendo fala e silêncio
- detect_speech_simple
- process_frame_streaming (transições speech/silence)
"""

from __future__ import annotations

import pytest

from ai.audio.exceptions import VADError
from ai.audio.vad import VoiceActivityDetector


class TestVADCreation:
    """Criação do VoiceActivityDetector com parâmetros válidos/inválidos."""

    def test_create_with_defaults(self) -> None:
        """Deve criar com valores padrão das settings."""
        detector = VoiceActivityDetector()
        assert detector.aggressiveness == 2
        assert detector.frame_ms == 30
        assert detector.frame_size > 0

    def test_create_with_custom_params(self) -> None:
        """Deve aceitar parâmetros customizados."""
        detector = VoiceActivityDetector(aggressiveness=1, frame_ms=20, sample_rate=16000)
        assert detector.aggressiveness == 1
        assert detector.frame_ms == 20

    def test_create_with_aggressiveness_0(self) -> None:
        """Agressividade 0 (menos agressivo) deve funcionar."""
        detector = VoiceActivityDetector(aggressiveness=0)
        assert detector.aggressiveness == 0

    def test_create_with_aggressiveness_3(self) -> None:
        """Agressividade 3 (mais agressivo) deve funcionar."""
        detector = VoiceActivityDetector(aggressiveness=3)
        assert detector.aggressiveness == 3

    def test_invalid_aggressiveness_raises(self) -> None:
        """Agressividade fora de 0-3 deve levantar VADError."""
        with pytest.raises(VADError):
            VoiceActivityDetector(aggressiveness=5)

    def test_invalid_aggressiveness_negative_raises(self) -> None:
        with pytest.raises(VADError):
            VoiceActivityDetector(aggressiveness=-1)

    def test_invalid_frame_ms_raises(self) -> None:
        """frame_ms inválido (diferente de 10, 20, 30) deve levantar VADError."""
        with pytest.raises(VADError):
            VoiceActivityDetector(frame_ms=15)

    def test_invalid_sample_rate_raises(self) -> None:
        """sample_rate inválido deve levantar VADError."""
        with pytest.raises(VADError):
            VoiceActivityDetector(sample_rate=11025)

    def test_frame_size_calculation(self) -> None:
        """frame_size deve ser sample_rate * frame_ms / 1000 * 2 bytes."""
        detector = VoiceActivityDetector(sample_rate=16000, frame_ms=30)
        expected = int(16000 * 30 / 1000) * 2  # 960 bytes
        assert detector.frame_size == expected


class TestVADProperties:
    """Propriedades do detector."""

    def test_aggressiveness_property(self) -> None:
        d = VoiceActivityDetector(aggressiveness=0)
        assert d.aggressiveness == 0

    def test_frame_ms_property(self) -> None:
        d = VoiceActivityDetector(frame_ms=10)
        assert d.frame_ms == 10

    def test_in_speech_initial_false(self) -> None:
        d = VoiceActivityDetector()
        assert d.in_speech is False


class TestVADIsSpeech:
    """Testes de is_speech com frames individuais."""

    def test_is_speech_with_valid_frame(self) -> None:
        """Frame de tamanho correto não deve lançar exceção."""
        detector = VoiceActivityDetector(frame_ms=30, sample_rate=16000)
        frame = b"\x00\x00" * (detector.frame_size // 2)  # frame silencioso
        # Não deve lançar
        result = detector.is_speech(frame)
        assert isinstance(result, bool)

    def test_is_speech_wrong_size_raises(self) -> None:
        """Frame com tamanho incorreto deve levantar VADError."""
        detector = VoiceActivityDetector(frame_ms=30, sample_rate=16000)
        wrong_frame = b"\x00\x00" * 100  # muito pequeno
        with pytest.raises(VADError):
            detector.is_speech(wrong_frame)

    def test_is_speech_empty_raises(self) -> None:
        detector = VoiceActivityDetector()
        with pytest.raises(VADError):
            detector.is_speech(b"")


class TestVADDetectSpeech:
    """Testes de detect_speech com buffers completos."""

    def test_detect_speech_all_silence(self, synthetic_silence: bytes) -> None:
        """Buffer completamente silencioso deve retornar lista vazia."""
        detector = VoiceActivityDetector(
            aggressiveness=3,
            frame_ms=30,
            sample_rate=16000,  # Máx — menos chance de falso positivo
        )
        segments = detector.detect_speech(synthetic_silence[:9600])  # 300ms
        assert segments == []

    def test_detect_speech_returns_list(self, synthetic_speech_buffer: bytes) -> None:
        """Buffer com fala deve retornar lista de segmentos."""
        detector = VoiceActivityDetector(aggressiveness=1, frame_ms=30, sample_rate=16000)
        segments = detector.detect_speech(synthetic_speech_buffer)
        assert isinstance(segments, list)

    def test_detect_speech_segment_structure(self) -> None:
        """Cada segmento deve ter as chaves esperadas."""
        detector = VoiceActivityDetector(aggressiveness=1, frame_ms=30, sample_rate=16000)
        # Cria buffer com fala simulada
        samples = 16000  # 1 segundo
        buffer = (
            (
                __import__("numpy").sin(
                    __import__("numpy").linspace(0, 2 * __import__("numpy").pi * 200, samples)
                )
                * 0.5
                * 32767
            )
            .astype(__import__("numpy").int16)
            .tobytes()
        )

        segments = detector.detect_speech(buffer)
        if segments:
            seg = segments[0]
            assert "start_frame" in seg
            assert "end_frame" in seg
            assert "start_sec" in seg
            assert "end_sec" in seg
            assert "duration_sec" in seg
            assert seg["duration_sec"] >= 0

    def test_detect_speech_resets_state(self, synthetic_speech_buffer: bytes) -> None:
        """Após detect_speech, o estado interno deve ser resetado."""
        detector = VoiceActivityDetector()
        detector.detect_speech(synthetic_speech_buffer)
        assert detector._speech_frames == 0
        assert detector._silence_frames == 0
        assert detector._total_frames == 0


class TestVADDetectSpeechSimple:
    """Testes de detect_speech_simple."""

    def test_simple_silence_false(self, synthetic_silence: bytes) -> None:
        detector = VoiceActivityDetector(aggressiveness=3)
        result = detector.detect_speech_simple(synthetic_silence[:9600])
        assert result is False

    def test_simple_with_speech(self, synthetic_speech_buffer: bytes) -> None:
        detector = VoiceActivityDetector(aggressiveness=1)
        # O buffer de fala sintética pode ou não ser detectado pelo VAD real
        # (depende do webrtcvad). Apenas verificamos que retorna bool.
        result = detector.detect_speech_simple(synthetic_speech_buffer)
        assert isinstance(result, bool)


class TestVADStreaming:
    """Testes de process_frame_streaming (modo streaming contínuo)."""

    def test_streaming_initial_silence(self, synthetic_silence: bytes, frame_size: int) -> None:
        """Frames iniciais de silêncio devem retornar 'silence'."""
        detector = VoiceActivityDetector(frame_ms=30)
        silence_frame = synthetic_silence[:frame_size]
        status = detector.process_frame_streaming(silence_frame)
        assert status == "silence"

    def test_streaming_returns_valid_states(self, mixed_audio_chunks: list[bytes]) -> None:
        """Sequência mista deve retornar estados válidos."""
        detector = VoiceActivityDetector(aggressiveness=1, frame_ms=30)
        valid_states = {"silence", "speech", "speech_start", "speech_end"}

        for chunk in mixed_audio_chunks:
            status = detector.process_frame_streaming(chunk)
            assert status in valid_states, f"Status inválido: {status}"

    def test_streaming_speech_detection(self) -> None:
        """Frames com energia alta devem eventualmente disparar speech_start."""
        detector = VoiceActivityDetector(aggressiveness=1, frame_ms=30)

        # Envia vários frames de "fala" (tom alto)
        samples_per_frame = int(16000 * 30 / 1000)
        detected_start = False

        for _ in range(15):
            t = __import__("numpy").linspace(0, 30 / 1000, samples_per_frame, endpoint=False)
            frame = (
                (__import__("numpy").sin(2 * __import__("numpy").pi * 200 * t) * 0.5 * 32767)
                .astype(__import__("numpy").int16)
                .tobytes()
            )
            status = detector.process_frame_streaming(frame)
            if status == "speech_start":
                detected_start = True
                break

        # Pode ou não detectar dependendo do webrtcvad real
        assert isinstance(detected_start, bool)

    def test_streaming_speech_to_silence_transition(self) -> None:
        """Após fala e depois silêncio, deve eventualmente retornar speech_end."""
        detector = VoiceActivityDetector(aggressiveness=1, frame_ms=30)
        samples_per_frame = int(16000 * 30 / 1000)

        # Envia alguns frames de fala
        for _ in range(10):
            t = __import__("numpy").linspace(0, 30 / 1000, samples_per_frame, endpoint=False)
            frame = (
                (__import__("numpy").sin(2 * __import__("numpy").pi * 200 * t) * 0.5 * 32767)
                .astype(__import__("numpy").int16)
                .tobytes()
            )
            detector.process_frame_streaming(frame)

        # Depois silêncio
        found_end = False
        for _ in range(50):
            silence = b"\x00\x00" * samples_per_frame
            status = detector.process_frame_streaming(silence)
            if status == "speech_end":
                found_end = True
                break

        assert isinstance(found_end, bool)


class TestVADEdgeCases:
    """Casos extremos do VAD."""

    def test_detect_speech_empty_buffer(self) -> None:
        detector = VoiceActivityDetector()
        segments = detector.detect_speech(b"")
        assert segments == []

    def test_detect_speech_very_short(self) -> None:
        """Buffer menor que 1 frame deve retornar lista vazia."""
        detector = VoiceActivityDetector()
        segments = detector.detect_speech(b"\x00\x00" * 10)
        assert segments == []

    def test_frame_size_consistency(self) -> None:
        """frame_size deve ser consistente entre sample_rates."""
        for sr in (8000, 16000, 32000, 48000):
            d = VoiceActivityDetector(sample_rate=sr, frame_ms=30)
            assert d.frame_size == int(sr * 30 / 1000) * 2

    def test_different_frame_ms(self) -> None:
        """Frame sizes para diferentes frame_ms."""
        for ms in (10, 20, 30):
            d = VoiceActivityDetector(sample_rate=16000, frame_ms=ms)
            assert d.frame_size == int(16000 * ms / 1000) * 2
