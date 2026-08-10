"""Testes do AudioPlayer (player de áudio com fila).

Testa:
- Criação e propriedades
- Enfileiramento (enqueue) de arquivos e buffers
- Controles: play, pause, resume, stop, skip
- Fila: clear_queue, queue_size
- Reprodução direta: play_once, play_tone
- Callbacks on_finish

Todas as operações de HW/subprocess são mockadas.
"""

from __future__ import annotations

from unittest.mock import patch

from ai.audio.player import AudioPlayer, PlaybackItem


class TestPlaybackItem:
    """Dataclass PlaybackItem."""

    def test_create_minimal(self) -> None:
        item = PlaybackItem(source="test.wav")
        assert item.source == "test.wav"
        assert item.audio_data is None
        assert item.title == ""
        assert item.volume == 1.0
        assert item.crossfade_sec == 0.0

    def test_create_full(self) -> None:
        item = PlaybackItem(
            source="-", audio_data=b"\x00\x01", title="Test", volume=0.5, crossfade_sec=2.0
        )
        assert item.audio_data == b"\x00\x01"
        assert item.title == "Test"
        assert item.volume == 0.5
        assert item.crossfade_sec == 2.0


class TestAudioPlayerCreation:
    """Criação do AudioPlayer."""

    def test_create_with_defaults(self) -> None:
        player = AudioPlayer()
        assert player.is_playing is False
        assert player.is_paused is False
        assert player.queue_size == 0
        assert player.current_item is None

    def test_create_with_custom_sink(self) -> None:
        player = AudioPlayer(sink="custom-sink")
        assert player.sink == "custom-sink"


class TestAudioPlayerProperties:
    """Propriedades do AudioPlayer."""

    def test_volume_setter(self) -> None:
        player = AudioPlayer()
        player.volume = 0.5
        assert player.volume == 0.5

    def test_volume_clamps_low(self) -> None:
        player = AudioPlayer()
        player.volume = -0.5
        assert player.volume == 0.0

    def test_volume_clamps_high(self) -> None:
        player = AudioPlayer()
        player.volume = 1.5
        assert player.volume == 1.0

    def test_sink_setter(self) -> None:
        player = AudioPlayer()
        player.sink = "new-sink"
        assert player.sink == "new-sink"

    def test_on_finish_callback(self) -> None:
        player = AudioPlayer()

        def cb() -> None:
            pass

        player.on_finish = cb
        assert player.on_finish is cb


class TestAudioPlayerQueue:
    """Operações de fila."""

    def test_enqueue_file(self) -> None:
        player = AudioPlayer()
        player.enqueue("test.wav", title="Song")
        assert player.queue_size == 1

    def test_enqueue_bytes(self) -> None:
        player = AudioPlayer()
        player.enqueue(b"\x00\x01" * 100, title="Buffer")
        assert player.queue_size == 1

    def test_enqueue_multiple(self) -> None:
        player = AudioPlayer()
        player.enqueue("a.wav")
        player.enqueue("b.wav")
        player.enqueue("c.wav")
        assert player.queue_size == 3

    def test_clear_queue(self) -> None:
        player = AudioPlayer()
        player.enqueue("a.wav")
        player.enqueue("b.wav")
        player.clear_queue()
        assert player.queue_size == 0

    def test_skip_returns_bool(self) -> None:
        player = AudioPlayer()
        player.enqueue("a.wav")
        result = player.skip()
        assert result is True
        assert player.current_item is not None

    def test_skip_empty_queue(self) -> None:
        player = AudioPlayer()
        result = player.skip()
        assert result is False


class TestAudioPlayerPlaybackControl:
    """Controles de reprodução."""

    def test_play_empty_queue(self) -> None:
        player = AudioPlayer()
        player.play()  # Não deve lançar exceção
        assert player.is_playing is False

    def test_play_with_items(self) -> None:
        player = AudioPlayer()
        player.enqueue("test.wav")
        player.play()
        assert player.is_playing is True

    def test_pause(self) -> None:
        player = AudioPlayer()
        player.enqueue("test.wav")
        player.play()
        player.pause()
        assert player.is_paused is True

    def test_resume(self) -> None:
        player = AudioPlayer()
        player.enqueue("test.wav")
        player.play()
        player.pause()
        player.resume()
        assert player.is_paused is False

    def test_stop(self) -> None:
        player = AudioPlayer()
        player.enqueue("test.wav")
        player.play()
        player.stop()
        assert player.is_playing is False
        assert player.queue_size == 0

    def test_play_when_paused_resumes(self) -> None:
        """play() quando pausado retoma, não reinicia."""
        player = AudioPlayer()
        player.enqueue("test.wav")
        player.play()
        player.pause()
        player.play()  # deve retomar
        assert player.is_paused is False
        assert player.is_playing is True

    def test_play_tone(self) -> None:
        """play_tone não deve lançar exceção (cria buffer e enfileira)."""
        player = AudioPlayer()
        # Não executa realmente — apenas verifica a criação do tom
        with patch.object(player, "play_once") as mock_play:
            player.play_tone(frequency=440, duration=0.5, volume=0.5, wait=False)
            mock_play.assert_called_once()


class TestAudioPlayerPlayOnce:
    """Reprodução direta play_once."""

    def test_play_once_file(self) -> None:
        player = AudioPlayer()
        with (
            patch.object(player, "play") as mock_play,
            patch.object(player, "_thread", None),
        ):
            player.play_once("test.wav", wait=False)
            assert player.queue_size == 1
            mock_play.assert_called_once()

    def test_play_once_bytes(self) -> None:
        player = AudioPlayer()
        with patch.object(player, "play") as mock_play:
            player.play_once(b"\x00\x01" * 100, wait=False)
            assert player.queue_size == 1
            mock_play.assert_called_once()
