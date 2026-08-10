# IA-Lab Audio Module — Architecture Guide

> **Módulo profissional de áudio para IA-Lab Enterprise**
> Pipeline completo: captura → processamento → IA (STT/TTS) → reprodução

---

## 📋 Índice

1. [Visão Geral](#-visão-geral)
2. [Estrutura de Diretórios](#-estrutura-de-diretórios)
3. [Módulos Python (Fases 3-6)](#-módulos-python)
   - [Base: settings, exceptions, core](#31-base-settings--exceptions--core)
   - [Captura/Reprodução: vad, recorder, player, effects](#32-capturareprodução-vad--recorder--player--effects)
   - [IA: stt, tts, microphone, formats](#33-ia-stt--tts--microphone--formats)
   - [Métricas: metrics](#34-métricas-metrics)
4. [API REST — Endpoints /api/audio/*](#-api-rest)
5. [Scripts Bash (Fase 2)](#-scripts-bash)
6. [Fluxo de Dados](#-fluxo-de-dados)
7. [Configuração](#-configuração)
8. [Dependências](#-dependências)
9. [Padrões e Convenções](#-padrões-e-convenções)
10. [Exemplos de Uso](#-exemplos-de-uso)

---

## 🔭 Visão Geral

O módulo de áudio do IA-Lab Enterprise fornece um pipeline completo de processamento de áudio, desde a captura via microfone até a transcrição com IA (STT) e síntese de voz (TTS). Foi projetado seguindo **SOLID**, **Clean Code**, **DRY**, **KISS** e **YAGNI**, reutilizando os padrões estabelecidos no projeto (`ai/settings.py`, `ai/providers/base.py`, `ai/telemetry.py`).

### Arquitetura em Camadas

```
┌──────────────────────────────────────────────────────┐
│                   API REST (FastAPI)                  │
│              /api/audio/* (11 endpoints)              │
├──────────────────────────────────────────────────────┤
│              AudioAgent (BaseAgent)                   │
│          Registrado no AgentRegistry                  │
├──────────────┬───────────────────┬───────────────────┤
│  Captura     │  Processamento    │  IA Audio         │
│  AudioRecorder│ effects.*        │  SpeechToText     │
│  VoiceActivity│                  │  TextToSpeech     │
│  Detector    │  formats.*        │  VirtualMicrophone│
├──────────────┴───────────────────┴───────────────────┤
│              AudioEngine (Orquestrador)               │
├──────────────────────────────────────────────────────┤
│              AudioSettings (pydantic)                 │
│              audio_metrics (Prometheus)               │
├──────────────────────────────────────────────────────┤
│              Scripts Bash (setup/test/backup/diagnose) │
└──────────────────────────────────────────────────────┘
```

---

## 📁 Estrutura de Diretórios

```
ai/audio/                          ← Módulo principal (Python)
├── __init__.py                    ← API pública (__all__)
├── settings.py                    ← AudioSettings (pydantic, IA_LAB_AUDIO_)
├── exceptions.py                  ← Hierarquia de exceções (9 tipos)
├── core.py                        ← AudioEngine (orquestrador)
├── metrics.py                     ← 20 métricas Prometheus
├── vad.py                         ← VoiceActivityDetector (webrtcvad)
├── recorder.py                    ← AudioRecorder (buffer circular + VAD)
├── player.py                      ← AudioPlayer (fila + crossfade)
├── effects.py                     ← 8 funções de processamento (numpy/scipy)
├── stt.py                         ← SpeechToText (speechbrain)
├── tts.py                         ← TextToSpeech (espeak + edge-tts)
├── microphone.py                  ← VirtualMicrophone (PipeWire null-sink)
└── formats.py                     ← Conversão entre formatos (ffmpeg)

scripts/audio/                     ← Scripts Bash
├── setup_microfone_virtual.sh     ← Cria/remove/status do microfone virtual
├── test_microphone.sh             ← Testa captura de áudio
├── test_speaker.sh                ← Testa reprodução de áudio
├── backup_audio_config.sh         ← Backup da configuração do PipeWire
└── diagnose_audio.sh              ← Diagnóstico completo do pipeline

tests/
└── test_audio/                    ← (planejado) Testes automatizados
```

---

## 🧠 Módulos Python

### 3.1 Base: `settings` + `exceptions` + `core`

#### `ai/audio/settings.py`
```python
class AudioSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IA_LAB_AUDIO_", ...)
```

- **35 campos** configuráveis via env vars (`IA_LAB_AUDIO_*`)
- Singleton via `@lru_cache` (padrão: `get_audio_settings()`)
- Categorias: devices, sample rate, VAD, recording, STT, TTS, effects, logs
- Segue exatamente o padrão de `ai/settings.py`

#### `ai/audio/exceptions.py`
Hierarquia de exceções:
```
AudioError (base)
├── AudioDeviceError    — Dispositivo não encontrado
├── AudioCaptureError   — Falha na captura
├── AudioPlaybackError  — Falha na reprodução
├── AudioFormatError    — Formato inválido
├── AudioConversionError— Falha na conversão
├── VADError            — Erro no VAD
├── STTError            — Erro no STT
├── TTSError            — Erro no TTS
└── AudioConfigError    — Configuração inválida
```

#### `ai/audio/core.py` — `AudioEngine`
Orquestrador principal (similar a `AIService`):
- `initialize()` / `shutdown()` — ciclo de vida
- `get_default_source()` / `get_default_sink()` — dispositivos padrão
- `list_sources()` / `list_sinks()` — lista dispositivos
- `get_status()` — snapshot completo do sistema

---

### 3.2 Captura/Reprodução: `vad` + `recorder` + `player` + `effects`

#### `ai/audio/vad.py` — `VoiceActivityDetector`
- **Engine:** Google WebRTC VAD (`webrtcvad`)
- **Agressividade:** 0 (menos) a 3 (mais) — padrão: 2
- **Frame:** 10/20/30ms — padrão: 30ms
- **Métodos:**
  - `is_speech(frame)` — classifica um frame
  - `detect_speech(buffer)` — encontra segmentos de fala
  - `process_frame_streaming(frame)` — streaming com histerese (speech_start/speech/speech_end/silence)

#### `ai/audio/recorder.py` — `AudioRecorder`
- **Engine:** `ffmpeg` via subprocess (fallback: `arecord`)
- **Buffer circular:** evita perda de áudio durante processamento
- **VAD integrado:** para automaticamente quando não detecta fala (+ padding configurável)
- **Métodos:**
  - `start(duration, use_vad)` — inicia gravação em thread
  - `stop()` — para e retorna PCM
  - `record_fixed(duration)` — gravação síncrona por tempo fixo
  - `save_to_file(data, path)` — salva em WAV

#### `ai/audio/player.py` — `AudioPlayer`
- **Engine:** `ffplay` via subprocess (fallback: `aplay`)
- **Fila:** deque de `PlaybackItem` com suporte a crossfade
- **Controles:** play, pause, resume, stop, skip, clear_queue
- **Volume:** global + por item (0.0 a 1.0)
- `play_tone(freq, duration)` — gera e reproduz tom senoidal

#### `ai/audio/effects.py` — 8 funções de processamento
Todas aceitam `bytes | np.ndarray` e retornam `bytes`:
| Função | Descrição | Parâmetros |
|---|---|---|
| `apply_gain(data, dB)` | Ganho/atenuação | `gain_db: float` |
| `normalize(data, target)` | Normalização de pico | `target_level_db: float = -3` |
| `noise_gate(data, ...)` | Silencia ruído de fundo | `threshold_db, attack, release` |
| `compressor(data, ...)` | Compressão dinâmica | `threshold_db, ratio, attack, release` |
| `resample(data, orig, target)` | Reamostragem | `original_rate, target_rate` |
| `high_pass_filter(data, cutoff)` | Remove ruído低频 | `cutoff_hz: float = 80` |
| `low_pass_filter(data, cutoff)` | Remove ruído高频 | `cutoff_hz: float = 8000` |
| `remove_silence(data, ...)` | Remove silêncio início/fim | `threshold_db: float = -40` |

---

### 3.3 IA: `stt` + `tts` + `microphone` + `formats`

#### `ai/audio/stt.py` — `SpeechToText`
- **Engine primário:** `speechbrain` (`EncoderASR`)
- **Modelo:** `speechbrain/asr-wav2vec2-commonvoice-14-en`
- **Pré-processamento:** normalize → resample (16kHz) → remove_silence
- **Métodos:**
  - `transcribe(audio, sample_rate, language)` — PCM → texto
  - `transcribe_file(path)` — arquivo → texto
  - `load_model()` / `unload_model()` — gerenciamento de memória

#### `ai/audio/tts.py` — `TextToSpeech`
- **Engine primário:** `espeak-ng` (offline, sempre disponível no Linux)
- **Engine secundário:** `edge-tts` (vozes naturais, requer internet)
- **Fallback automático:** se um engine falha, tenta o outro
- **Cache LRU:** 128 entradas para frases repetidas
- **Métodos:** `synthesize(text)`, `synthesize_to_file(text, path)`, `list_voices()`

#### `ai/audio/microphone.py` — `VirtualMicrophone`
- Gerencia null-sink + loopback no PipeWire
- **Métodos:** `create()`, `remove()`, `get_status()`
- **Source name:** `ia-lab-mic.monitor` — apps de IA usam este microfone

#### `ai/audio/formats.py` — Conversão entre formatos
- **Engine:** `ffmpeg` via subprocess
- **Detecção:** magic bytes + extensão + ffprobe
- **Funções:** `convert()`, `to_wav()`, `to_mp3()`, `to_flac()`, `to_pcm()`
- **Info:** `get_audio_info(file)`, `get_duration(file)`, `get_human_readable_info(file)`

---

### 3.4 Métricas: `metrics`

20 métricas Prometheus com prefixo `ia_lab_audio_`:

| Categoria | Métricas |
|---|---|
| **Captura** | `audio_recording`, `capture_duration_seconds`, `capture_bytes_total` |
| **Reprodução** | `playback`, `playback_items_total` |
| **VAD** | `vad_speech_frames_total`, `vad_silence_frames_total`, `vad_segments_total`, `vad_speech_ratio` |
| **STT** | `stt_duration_seconds`, `stt_audio_duration_seconds`, `stt_characters_total`, `stt_requests_total` |
| **TTS** | `tts_duration_seconds`, `tts_audio_duration_seconds`, `tts_characters_total`, `tts_requests_total` |
| **Dispositivos** | `device_status`, `device_volume`, `device_muted` |
| **Microfone Virtual** | `virtual_mic_active`, `virtual_mic_loopback` |
| **Erros** | `audio_errors_total` |
| **Conversão** | `conversion_duration_seconds`, `conversion_bytes_total` |

---

## 🌐 API REST

11 endpoints sob `/api/audio/*` no `api/server.py`:

| Método | Rota | Função |
|---|---|---|
| `GET` | `/api/audio/status` | Status completo do AudioEngine |
| `GET` | `/api/audio/devices` | Lista fontes + sinks |
| `GET` | `/api/audio/config` | Config do módulo (sem secrets) |
| `GET` | `/api/audio/metrics` | Snapshot das métricas Prometheus |
| `GET` | `/api/audio/mic/status` | Status do microfone virtual |
| `POST` | `/api/audio/record` | Grava áudio (duração/VAD) |
| `POST` | `/api/audio/stt` | Transcreve áudio (base64) → texto |
| `POST` | `/api/audio/tts` | Sintetiza texto → áudio |
| `POST` | `/api/audio/effects` | Aplica efeitos em cadeia |
| `POST` | `/api/audio/mic/create` | Cria microfone virtual |
| `POST` | `/api/audio/mic/remove` | Remove microfone virtual |

**AudioAgent** (`ai/agents/audio_agent.py`) registrado no `AgentRegistry` como `"audio"`, usável via:
```json
POST /api/chat {"prompt": "...", "agent": "audio"}
```

---

## 📜 Scripts Bash

| Script | Função | Flags principais |
|---|---|---|
| `setup_microfone_virtual.sh` | Cria/remove/status do microfone virtual | `--apply`, `--remove`, `--status` |
| `test_microphone.sh` | Testa captura (lista, grava, mede, reproduz) | `--apply`, `--source`, `--list` |
| `test_speaker.sh` | Testa saída (tom senoidal, canais) | `--apply`, `--tone <Hz>`, `--sink` |
| `backup_audio_config.sh` | Backup completo do PipeWire | `--apply`, `--list`, `--clean` |
| `diagnose_audio.sh` | Diagnóstico kernel → ALSA → PipeWire → apps | `--apply`, `--quick`, `--latency` |

**Características comuns:**
- `set -euo pipefail` em todos
- **Dry-run por padrão** (use `--apply` para executar)
- Sistema de logs em `~/.local/log/audio/`
- Cores, cabeçalhos, `--help` — idêntico ao `bin/manutencao`

---

## 🔄 Fluxo de Dados

### Gravação → STT
```
Microfone (pulse/alsa)
    ↓ PCM 16-bit 16kHz mono
AudioRecorder.record_fixed()
    ↓ bytes
effects.normalize() + effects.resample() + effects.remove_silence()
    ↓ bytes limpos
SpeechToText.transcribe()
    ↓ string
Texto transcrito
```

### TTS → Reprodução
```
Texto
    ↓
TextToSpeech.synthesize()
    ↓ PCM 16-bit 16kHz mono
AudioPlayer.play_once()
    ↓ PULSE_SINK
Alto-falantes
```

### Microfone Virtual
```
App de áudio (Spotify, YouTube, etc.)
    ↓
PulseAudio Speaker (sink)
    ↓ monitor source
module-loopback (PipeWire)
    ↓
ia-lab-mic (null-sink)
    ↓ monitor source
ia-lab-mic.monitor (microfone virtual)
    ↓
App de IA (STT, voice assistant)
```

---

## ⚙️ Configuração

Todas as variáveis usam prefixo `IA_LAB_AUDIO_`:

```bash
# Dispositivos
IA_LAB_AUDIO_INPUT_DEVICE=default
IA_LAB_AUDIO_OUTPUT_DEVICE=default

# Qualidade
IA_LAB_AUDIO_SAMPLE_RATE=16000
IA_LAB_AUDIO_CHANNELS=1

# VAD
IA_LAB_AUDIO_VAD_AGGRESSIVENESS=2
IA_LAB_AUDIO_VAD_FRAME_MS=30

# STT
IA_LAB_AUDIO_STT_MODEL=speechbrain/asr-wav2vec2-commonvoice-14-en
IA_LAB_AUDIO_STT_LANGUAGE=pt

# TTS
IA_LAB_AUDIO_TTS_ENGINE=espeak
IA_LAB_AUDIO_TTS_VOICE=pt-br
```

---

## 📦 Dependências

### Sistema (já instalados ✅)
- `pipewire` / `pipewire-pulse` — servidor de áudio
- `ffmpeg` — codecs e conversão
- `espeak` / `espeak-ng` — TTS offline

### Python (já instalados ✅)
- `numpy` — processamento de arrays
- `scipy` — filtros e reamostragem
- `webrtcvad` — detecção de voz
- `soundfile` — leitura/escrita de áudio
- `speechbrain` — STT (modelo ASR)
- `torchaudio` — suporte a áudio do PyTorch
- `prometheus_client` — métricas

### Python (instalação opcional)
- `sounddevice` — API Python para PulseAudio (alternativa a subprocess)
- `pydub` — manipulação de áudio de alto nível
- `edge-tts` — vozes naturais TTS (requer internet)

---

## 🎯 Padrões e Convenções

| Padrão | Onde | Exemplo |
|---|---|---|
| **pydantic_settings** | `settings.py` | `class AudioSettings(BaseSettings):` com `env_prefix="IA_LAB_AUDIO_"` |
| **Singleton** | `settings.py` | `@lru_cache` + `get_audio_settings()` |
| **Lazy imports** | `api/server.py` | `from ai.audio import AudioEngine` dentro da função |
| **get_logger()** | Todos os módulos | `logger = get_logger("ai.audio")` |
| **Hierarquia de exceções** | `exceptions.py` | `AudioError` → 9 subtipos |
| **DRY** | `core.py` | `list_sources/list_sinks` → `_list_devices(device_type)` |
| **Fallbacks** | `tts.py`, `stt.py` | espeak → edge-tts; speechbrain → whisper |
| **ABC** | `agent` | `BaseAgent` com `@abstractmethod` |
| **async/await** | `api/server.py`, `agent` | Endpoints e agentes assíncronos |

---

## 💡 Exemplos de Uso

### Python (engine principal)
```python
from ai.audio import AudioEngine, SpeechToText, TextToSpeech

# Status do sistema
engine = AudioEngine()
status = await engine.get_status()

# STT
stt = SpeechToText()
texto = stt.transcribe(audio_pcm_bytes)

# TTS
tts = TextToSpeech()
audio = tts.synthesize("Olá, mundo!")

# Microfone virtual
from ai.audio.microphone import VirtualMicrophone
vmic = VirtualMicrophone()
vmic.create()
```

### API REST
```bash
# Status
curl http://localhost:8000/api/audio/status

# STT (enviar áudio em base64)
curl -X POST http://localhost:8000/api/audio/stt \
  -H "Content-Type: application/json" \
  -d '{"audio_base64":"<base64>","language":"pt"}'

# TTS
curl -X POST http://localhost:8000/api/audio/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Olá, mundo!","engine":"espeak"}'

# Microfone virtual
curl -X POST http://localhost:8000/api/audio/mic/create
curl -X GET http://localhost:8000/api/audio/mic/status
```

### Bash (scripts)
```bash
# Diagnóstico rápido
./scripts/audio/diagnose_audio.sh --apply --quick

# Criar microfone virtual
./scripts/audio/setup_microfone_virtual.sh --apply

# Backup da configuração
./scripts/audio/backup_audio_config.sh --apply
```

---

## 🧪 Testes (planejados)

Os testes automatizados para o módulo de áudio serão organizados em:

```
tests/test_audio/
├── test_core.py
├── test_vad.py
├── test_recorder.py
├── test_player.py
├── test_effects.py
├── test_stt.py
├── test_tts.py
├── test_microphone.py
├── test_formats.py
└── conftest.py
```

Ferramentas: `pytest` + `pytest-asyncio`.

---

> **Documentação gerada em:** Julho de 2026
> **Projeto:** IA-Lab Enterprise — Módulo de Áudio (Fases 1-7)
