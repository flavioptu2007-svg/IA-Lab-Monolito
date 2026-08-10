#!/usr/bin/env python3
"""
demo_audio.py — Demonstração completa do módulo de áudio IA-Lab.

Uso:
    python3 demo_audio.py               # Demo completa com sintese de tom
    python3 demo_audio.py --quick        # Apenas modulos que nao requerem HW
    python3 demo_audio.py --list-only    # Apenas listagem de dispositivos
    python3 demo_audio.py --vad          # Demo de VAD com audio sintetico
    python3 demo_audio.py --effects      # Demo de processamento de sinal
    python3 demo_audio.py --format       # Demo de conversao de formatos

Requer Python 3.10+ e as dependencias do modulo de audio.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from typing import Any

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]


# ── Cores para terminal ───────────────────────────────────────────────────────


class C:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def ok(text: str) -> str:
    return f"{C.GREEN}✓{C.END} {text}"


def info(text: str) -> str:
    return f"{C.CYAN}ℹ{C.END} {text}"


def warn(text: str) -> str:
    return f"{C.YELLOW}⚠{C.END} {text}"


def fail(text: str) -> str:
    return f"{C.RED}✗{C.END} {text}"


def header(text: str) -> str:
    return (
        f"\n{C.HEADER}{C.BOLD}{'=' * 60}{C.END}\n{C.BOLD}{text}{C.END}\n{C.HEADER}{'=' * 60}{C.END}"
    )


def section(text: str) -> str:
    return f"\n{C.BOLD}{C.BLUE}─── {text} ───{C.END}"


def run_demo(args: argparse.Namespace) -> int:
    """Executa a demonstracao e retorna 0 se tudo ok."""
    errors = 0

    # ── 1. AudioEngine ──────────────────────────────────────────────────────

    print(header("IA-Lab Audio Module — Demonstracao Completa"))
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Numpy:  {np.__version__ if np else 'N/A'}")

    print(section("1. AudioEngine — Status do Sistema"))

    import asyncio

    engine: Any = None

    try:
        from ai.audio import AudioEngine

        engine = AudioEngine()
        print(ok(f"AudioEngine criado (sample_rate={engine.sample_rate} Hz)"))

        async def check_audio() -> dict[str, Any]:
            await engine.initialize()
            return await engine.get_status()

        async def shutdown_audio() -> None:
            await engine.shutdown()

        status = asyncio.run(check_audio())

        print(f"  Inicializado:  {status['initialized']}")
        print(f"  Sample rate:   {status['sample_rate']} Hz")

        dev = status["devices"]
        print(f"  Source padrao: {dev.get('default_source', 'N/A')}")
        print(f"  Sink padrao:   {dev.get('default_sink', 'N/A')}")
        print(f"  Fontes:        {dev['sources']} disponiveis")
        print(f"  Sinks:         {dev['sinks']} disponiveis")

        tools = status["tools"]
        print("  Ferramentas:   ", end="")
        for tool, found in tools.items():
            print(f"{tool}={C.GREEN if found else C.RED}{found}{C.END} ", end="")
        print()

        asyncio.run(shutdown_audio())

    except Exception as e:
        print(warn(f"AudioEngine: {e}"))
        errors += 1

    # ── 2. Dispositivos ─────────────────────────────────────────────────────

    print(section("2. Dispositivos de Audio"))

    if engine is None:
        print(warn("Engine nao disponivel — pulando listagem de dispositivos"))
    else:
        try:
            sources = engine.list_sources()
            print(f"  Fontes de entrada ({len(sources)}):")
            for s in sources[:5]:
                print(f"    [{s['index']}] {s['name']}  ({s['state']})")

            sinks = engine.list_sinks()
            print(f"  Sinks de saida ({len(sinks)}):")
            for s in sinks[:5]:
                print(f"    [{s['index']}] {s['name']}  ({s['state']})")
        except Exception as e:
            print(warn(f"Dispositivos: {e}"))
            errors += 1

    # ── 3. Efeitos (processamento de sinal — puro, sem HW) ──────────────────

    if not args.quick and not args.list_only and not args.vad:
        print(section("3. Processamento de Sinal (Efeitos)"))

        try:
            from ai.audio import effects

            # Gera tom senoidal de 440Hz (1 segundo)
            sr = 16000
            duration = 1.0
            samples = int(sr * duration)
            t = np.linspace(0, duration, samples, endpoint=False)
            tone = (np.sin(2 * np.pi * 440 * t) * 0.5 * 32767).astype(np.int16)
            audio_bytes = tone.tobytes()
            print(f"  Tom 440Hz gerado: {len(audio_bytes)} bytes")

            # apply_gain
            amplified = effects.apply_gain(audio_bytes, 6.0)
            attenuated = effects.apply_gain(audio_bytes, -12.0)
            print(
                ok(f"apply_gain:  +6 dB ({len(amplified)} bytes), -12 dB ({len(attenuated)} bytes)")
            )

            # normalize
            normalized = effects.normalize(audio_bytes, -3.0)
            orig_peak = np.max(np.abs(np.frombuffer(audio_bytes, dtype=np.int16)))
            norm_peak = np.max(np.abs(np.frombuffer(normalized, dtype=np.int16)))
            print(
                ok(
                    f"normalize:   pico original={orig_peak}, pico normalizado={norm_peak} (alvo -3 dBFS)"
                )
            )

            # noise_gate
            gated = effects.noise_gate(audio_bytes, threshold_db=-30.0)
            print(ok(f"noise_gate:  threshold=-30 dB ({len(gated)} bytes)"))

            # compressor
            compressed = effects.compressor(audio_bytes, threshold_db=-20.0, ratio=4.0)
            comp_peak = np.max(np.abs(np.frombuffer(compressed, dtype=np.int16)))
            print(ok(f"compressor:  ratio=4:1, threshold=-20 dBFS (pico={comp_peak})"))

            # filters
            hp = effects.high_pass_filter(audio_bytes, cutoff_hz=300.0)
            lp = effects.low_pass_filter(audio_bytes, cutoff_hz=2000.0)
            print(ok(f"high_pass_filter:  300 Hz ({len(hp)} bytes)"))
            print(ok(f"low_pass_filter:   2000 Hz ({len(lp)} bytes)"))

            # resample
            down = effects.resample(audio_bytes, 16000, 8000)
            up = effects.resample(down, 8000, 16000)
            print(
                ok(
                    f"resample:   16000→8000 Hz ({len(down)} bytes), 8000→16000 Hz ({len(up)} bytes)"
                )
            )

            # remove_silence
            trimmed = effects.remove_silence(audio_bytes, threshold_db=-40.0)
            print(ok(f"remove_silence:  {len(audio_bytes)} → {len(trimmed)} bytes"))

        except Exception as e:
            print(warn(f"Efeitos: {e}"))
            errors += 1

    # ── 4. VAD (Voice Activity Detection) ────────────────────────────────────

    if args.vad or (not args.quick and not args.list_only and not args.format):
        print(section("4. Voice Activity Detection (VAD)"))

        try:
            from ai.audio import VoiceActivityDetector

            vad = VoiceActivityDetector(aggressiveness=1, frame_ms=30)
            print(
                ok(
                    f"VAD criado: aggressiveness={vad.aggressiveness}, frame_size={vad.frame_size} bytes"
                )
            )
            print(f"  in_speech: {vad.in_speech}")

            # Testa com frame de silencio (deve ser False)
            silence_frame = b"\x00\x00" * (vad.frame_size // 2)
            result = vad.is_speech(silence_frame)
            print(f"  Frame silencio -> is_speech: {result}")

            # Testa com frame de tom (depende do webrtcvad)
            samples_per_frame = vad.frame_size // 2
            t = np.linspace(0, 30 / 1000, samples_per_frame, endpoint=False)
            tone_frame = (np.sin(2 * np.pi * 200 * t) * 0.5 * 32767).astype(np.int16).tobytes()
            result = vad.is_speech(tone_frame)
            print(f"  Frame tom 200Hz -> is_speech: {result}")

            # detect_speech em buffer
            buf_samples = int(16000 * 2)
            t = np.linspace(0, 2.0, buf_samples, endpoint=False)
            speech_buf = (np.sin(2 * np.pi * 250 * t) * 0.4 * 32767).astype(np.int16).tobytes()
            segments = vad.detect_speech(speech_buf)
            print(f"  Segmentos detectados: {len(segments)}")
            for seg in segments[:3]:
                print(
                    f"    {seg['start_sec']:.2f}s - {seg['end_sec']:.2f}s ({seg['duration_sec']:.2f}s)"
                )

            # Streaming mode
            print("  Streaming mode:", end="")
            vad2 = VoiceActivityDetector(aggressiveness=1, frame_ms=30)
            for _ in range(8):
                status = vad2.process_frame_streaming(silence_frame)
                print(f" {status}", end="")
            print()

        except Exception as e:
            print(warn(f"VAD: {e}"))
            errors += 1

    # ── 5. TTS (Text-to-Speech) ──────────────────────────────────────────────

    if args.tts or (
        not args.quick
        and not args.list_only
        and not args.vad
        and not args.format
        and not args.effects
    ):
        print(section("5. Text-to-Speech (TTS)"))

        try:
            from ai.audio import TextToSpeech

            tts = TextToSpeech()
            available = tts.is_available()
            print(f"  Engine: {tts.engine}, Voice: {tts.voice}")
            print(f"  Disponivel: {available}")

            if available:
                audio = tts.synthesize("IA Lab Enterprise, modulo de audio profissional.")
                print(ok(f"Sintese concluida: {len(audio)} bytes PCM"))
                print(
                    f"  Cache: {tts.cache_size} entradas, hits={tts.cache_hits}, misses={tts.cache_misses}"
                )

                # Testa cache
                audio2 = tts.synthesize("IA Lab Enterprise, modulo de audio profissional.")
                print(ok(f"Cache hit: {len(audio2)} bytes, hits={tts.cache_hits}"))

                # Salva em arquivo
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tts.synthesize_to_file("Teste de sintese de voz.", f.name)
                    print(ok(f"Arquivo salvo: {f.name}"))

        except Exception as e:
            print(warn(f"TTS: {e}"))
            errors += 1

    # ── 6. STT (Speech-to-Text) ──────────────────────────────────────────────

    if (
        not args.quick
        and not args.list_only
        and not args.vad
        and not args.format
        and not args.effects
    ):
        print(section("6. Speech-to-Text (STT)"))

        try:
            from ai.audio import SpeechToText

            stt = SpeechToText()
            print(f"  Modelo: {stt.model_name}")
            print(f"  Device: {stt.device}")
            print(f"  Idioma: {stt.language}")
            print(f"  Modelo carregado: {stt.is_model_loaded}")
            print(f"  Disponivel: {stt.is_available()}")

            # Testa transcricao de buffer vazio
            result = stt.transcribe(b"")
            print(f"  Transcricao vazia: '{result}'")

            # Testa transcricao de buffer muito curto
            result = stt.transcribe(b"\x00\x01" * 50)
            print(f"  Transcricao curta: '{result}'")

        except Exception as e:
            print(warn(f"STT: {e}"))
            errors += 1

    # ── 7. Formatos ──────────────────────────────────────────────────────────

    if args.format or (not args.quick and not args.list_only):
        print(section("7. Conversao de Formatos"))

        try:
            from ai.audio import formats

            # Detecta formato por magic bytes
            fmt = formats.detect_format(b"RIFF" + b"\x00" * 60)
            print(ok(f"detect_format(WAV): {fmt}"))

            fmt = formats.detect_format(b"fLaC" + b"\x00" * 60)
            print(ok(f"detect_format(FLAC): {fmt}"))

            fmt = formats.detect_format(b"OggS" + b"\x00" * 60)
            print(ok(f"detect_format(OGG): {fmt}"))

            # Converte PCM para WAV (em memoria)
            pcm_data = b"\x00\x01\x00\x02" * 1000
            wav_data = formats.convert(pcm_data, ".wav")
            print(ok(f"convert PCM→WAV: {len(pcm_data)} → {len(wav_data)} bytes"))

            # Converte PCM para FLAC
            flac_data = formats.convert(pcm_data, ".flac")
            print(ok(f"convert PCM→FLAC: {len(pcm_data)} → {len(flac_data)} bytes"))

            # to_wav, to_mp3, to_flac, to_pcm
            wav = formats.to_wav(pcm_data)
            print(ok(f"to_wav: {len(wav)} bytes"))

            pcm = formats.to_pcm(pcm_data)
            print(ok(f"to_pcm: {len(pcm)} bytes"))

            # get_human_readable_info (se houver arquivo)
            print(info("get_human_readable_info requer arquivo real no disco"))

        except Exception as e:
            print(warn(f"Formatos: {e}"))
            errors += 1

    # ── 8. Microfone Virtual ─────────────────────────────────────────────────

    if not args.quick and not args.list_only:
        print(section("8. Microfone Virtual (PipeWire)"))

        try:
            from ai.audio import VirtualMicrophone

            vmic = VirtualMicrophone()
            print(f"  Nome sink: {vmic.sink_name}")
            print(f"  Nome source: {vmic.source_name}")
            print(f"  Descricao: {vmic.description}")
            print(f"  Ativo: {vmic.is_active}")

            status = vmic.get_status()
            print(f"  Sink existe: {status['sink_exists']}")
            print(f"  Modulos relacionados: {len(status['modules'])}")

        except Exception as e:
            print(warn(f"Microfone virtual: {e}"))
            errors += 1

    # ── 9. Metricas ──────────────────────────────────────────────────────────

    if not args.quick and not args.list_only:
        print(section("9. Metricas Prometheus"))

        try:
            from prometheus_client.registry import REGISTRY

            from ai.audio import metrics as m

            count = 0
            for metric in REGISTRY.collect():
                if metric.name.startswith("ia_lab_audio_"):
                    count += 1
                    if count <= 8:
                        print(f"  📊 {metric.name}")

            if count > 8:
                print(f"  ... e mais {count - 8} metricas")
            print(ok(f"Total: {count} metricas de audio registradas"))

            # Demonstra operacoes
            m.audio_errors.labels(error_type="demo").inc()
            m.vad_speech_frames.labels(aggressiveness="2").inc(10)
            print(ok("Operacoes de metrica: audio_errors +1, vad_speech_frames +10"))

        except Exception as e:
            print(warn(f"Metricas: {e}"))
            errors += 1

    # ── 10. Configuracoes ────────────────────────────────────────────────────

    if not args.quick and not args.list_only:
        print(section("10. Configuracoes (AudioSettings)"))

        try:
            from ai.audio import audio_settings

            print(f"  sample_rate:          {audio_settings.sample_rate}")
            print(f"  input_device:         {audio_settings.input_device}")
            print(f"  output_device:        {audio_settings.output_device}")
            print(f"  channels:             {audio_settings.channels}")
            print(f"  vad_aggressiveness:   {audio_settings.vad_aggressiveness}")
            print(f"  vad_frame_ms:         {audio_settings.vad_frame_ms}")
            print(f"  stt_model:            {audio_settings.stt_model[:50]}...")
            print(f"  tts_engine:           {audio_settings.tts_engine}")
            print(f"  tts_voice:            {audio_settings.tts_voice}")
            print(f"  noise_gate_threshold: {audio_settings.noise_gate_threshold} dB")
            print(f"  compressor_ratio:     {audio_settings.compressor_ratio}:1")

        except Exception as e:
            print(warn(f"Configuracoes: {e}"))
            errors += 1

    # ── 11. Player — Tom de teste ────────────────────────────────────────────

    if args.tone or (
        not args.quick
        and not args.list_only
        and not args.vad
        and not args.format
        and not args.effects
    ):
        print(section("11. AudioPlayer — Tom de Teste"))

        try:
            from ai.audio import AudioPlayer

            player = AudioPlayer()
            player.play_tone(frequency=440, duration=0.5, volume=0.3, wait=True)
            print(ok("Tom 440Hz reproduzido por 0.5s"))

            player.play_tone(frequency=523, duration=0.3, volume=0.3, wait=True)
            print(ok("Tom 523Hz (Dó) reproduzido por 0.3s"))

            player.play_tone(frequency=659, duration=0.3, volume=0.3, wait=True)
            print(ok("Tom 659Hz (Mi) reproduzido por 0.3s"))

        except Exception as e:
            print(warn(f"Player: {e}"))
            errors += 1

    # ── Resumo Final ─────────────────────────────────────────────────────────

    print()
    print(C.BOLD + "─" * 60 + C.END)
    if errors == 0:
        print(ok(f"{C.BOLD}Demonstracao concluida sem erros!{C.END}"))
    else:
        print(warn(f"{C.BOLD}Demonstracao concluida com {errors} erro(s){C.END}"))
    print("  total de modulos testados: 11")
    print()

    return 0 if errors == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Demonstracao completa do modulo de audio IA-Lab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--quick", action="store_true", help="Apenas modulos que nao requerem HW")
    parser.add_argument("--list-only", action="store_true", help="Apenas listagem de dispositivos")
    parser.add_argument("--vad", action="store_true", help="Apenas demonstracao de VAD")
    parser.add_argument("--effects", action="store_true", help="Apenas demonstracao de efeitos")
    parser.add_argument("--format", action="store_true", help="Apenas demonstracao de formatos")
    parser.add_argument("--tts", action="store_true", help="Inclui demonstracao de TTS")
    parser.add_argument("--tone", action="store_true", help="Inclui tom de teste no alto-falante")

    args = parser.parse_args()

    try:
        return run_demo(args)
    except KeyboardInterrupt:
        print(f"\n{warn('Interrompido pelo usuario')}")
        return 130


if __name__ == "__main__":
    sys.exit(main())
