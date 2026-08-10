# IA-Lab Audio Module — Changelog

> **Histórico completo de implementação do módulo de áudio**
> Total: **5.677 linhas** de código (Python + Bash)

---

## v2.1.0 — IA-Lab Unified (monolito)

**Data:** Agosto de 2026
**Bump:** `2.0.0 → 2.1.0` (minor — 6 features, sem breaking changes)

### Adicionado

- **LeituraIA Brasil** — integração do módulo de leitura adaptativa ao monolito (auth JWT + RBAC com perfis, biblioteca de textos, geração de texto com IA)
- **Chat local com IA** — `scripts/chat_local.sh` (sobe o servidor na porta 8099 e testa `/api/chat` com um clique; flags `--status`/`--parar`/`--pergunta`/`--porta`; modo `--lan` para a rede da escola) e `scripts/abrir_chat_ia.sh` (atalhos de desktop)
- **Providers gratuitos sem cartão** — Groq e Gemini (AI Studio) como providers primários no Render
- **Deploy na nuvem** — `Dockerfile.cloudrun` + `render.yaml` (Render grátis) + CI do dashboard no GitHub Pages
- **Guia de desenvolvimento local** — `ENV_LOCAL_GEMINI.md` + `.env.example` (chave Gemini local sem cartão)

### Corrigido

- **TTS edge-tts funcional** — `asyncio.run` em thread (não quebra em loop ativo), mapeamento de vozes espeak→edge (pt-BR-AntonioNeural), extração de PCM por chunks, header WAV válido no pipe do ffmpeg; + testes (508 no total)
- **Modelo Gemini** — padrão atualizado para `gemini-3.5-flash` (2.5-flash-001 descontinuado) e depois `gemini-3.1-flash-lite` (perf: 1.5s com respostas completas)
- **CORS** — origens do portal educacional liberadas (web.app, LAN, domínio) para `/api/chat` e `/api/audio/*`
- **Deploy** — região trocada para Virginia (menor latência p/ Brasil), `leituraia/` e `requirements.txt` no repo, espeak/ffmpeg e extra `education` na imagem

### Interno (sem mudança de comportamento)

- Lint 100% limpo (`ruff check` + `ruff format`) em todo o código de primeira parte (~600k → 0 erros com `extend-exclude` de terceiros)
- Documentação versionada: `ARCHITECTURE.md`, `LICENSE` (MIT), `VERSION`, `HISTORY.md`

---

## Manutenção — Limpeza de Lint (ruff)

**Data:** Agosto de 2026

### Corrigido

- **`leituraia/`** — lint 100% limpo (ruff):
  - `Profile(str, Enum)` → `Profile(StrEnum)` (UP042)
  - Imports ordenados; `timezone.utc` → `datetime.UTC`; f-string sem placeholder
  - `ruff format` aplicado no módulo
  - `pyproject.toml`: `extend-immutable-calls` para `fastapi.Depends`/`Query`/`require` — elimina falsos positivos B008 da injeção de dependências do FastAPI
- **Projeto inteiro** — lint de primeira parte zerado (~600k → 0 erros):
  - `pyproject.toml`: `extend-exclude` de pastas de terceiros (`Secretária`, `ComfyUI`, `Projetos`, `AI`, `.*`, …)
  - B904: `raise ... from e` / `from None` em `api/server.py`, `web/api/server.py` e `ai/audio/*` (`formats`, `recorder`, `stt`, `tts`)
  - ARG/B017/SIM117/UP031/F401/B019 corrigidos em `ai/`, `src/`, `tests/`, `scripts/`, `webcam-optimization/`
  - Validação: `ruff check .` → All checks passed; `ruff format --check .` → 94/94; **508 testes passando**

---

## v0.7.0 — Integração API e Métricas (Fase 6)

**Data:** Julho de 2026

### Adicionado

- **`ai/audio/metrics.py`** — 20 métricas Prometheus com prefixo `ia_lab_audio_`:
  - Captura: `audio_recording`, `capture_duration_seconds`, `capture_bytes_total`
  - Reprodução: `playback`, `playback_items_total`
  - VAD: `vad_speech_frames_total`, `vad_silence_frames_total`, `vad_segments_total`, `vad_speech_ratio`
  - STT: `stt_duration_seconds`, `stt_audio_duration_seconds`, `stt_characters_total`, `stt_requests_total`
  - TTS: `tts_duration_seconds`, `tts_audio_duration_seconds`, `tts_characters_total`, `tts_requests_total`
  - Dispositivos: `device_status`, `device_volume`, `device_muted`
  - Virtual Mic: `virtual_mic_active`, `virtual_mic_loopback`
  - Erros: `audio_errors_total`
  - Conversão: `conversion_duration_seconds`, `conversion_bytes_total`
- **`api/server.py`** — 11 novos endpoints REST sob `/api/audio/*`:
  - `GET /api/audio/status` — Status completo do AudioEngine
  - `GET /api/audio/devices` — Lista fontes + sinks
  - `GET /api/audio/config` — Config do módulo (sem secrets)
  - `GET /api/audio/metrics` — Snapshot das métricas Prometheus
  - `GET /api/audio/mic/status` — Status do microfone virtual
  - `POST /api/audio/record` — Grava áudio (duração/VAD)
  - `POST /api/audio/stt` — Transcreve áudio (base64) → texto
  - `POST /api/audio/tts` — Sintetiza texto → áudio
  - `POST /api/audio/effects` — Aplica efeitos em cadeia
  - `POST /api/audio/mic/create` — Cria microfone virtual
  - `POST /api/audio/mic/remove` — Remove microfone virtual

### Corrigido

- `engine._get_recorder()` removido (código morto — `AudioEngine` não tinha o método)
- `AudioEffectsRequest.audio_base64` adicionado ao modelo (faltava o campo)
- `POST /api/audio/effects` endpoint criado (modelo existia sem endpoint)
- `audio_b64` → `request.audio_base64` (variável dangling)
- `import json` removido do endpoint effects (não usado)
- Startup duplicado corrigido (2x logger.info)

---

## v0.6.0 — AudioAgent (Fase 7)

**Data:** Julho de 2026

### Adicionado

- **`ai/agents/audio_agent.py`** — `AudioAgent(BaseAgent)`:
  - `name = "audio"`
  - `task_type = TaskType.local`
  - `default_provider = "ollama"`
  - System prompt de 487 chars especializado em áudio
- **`ai/agents/base.py`** — `AudioAgent` registrado no `AgentRegistry`

### Agentes disponíveis

```
['code', 'architect', 'writer', 'audio']  ← 4 agentes
```

---

## v0.5.0 — Módulos de IA: STT, TTS, Microfone Virtual, Formatos (Fase 5)

**Data:** Julho de 2026

### Adicionado

- **`ai/audio/stt.py`** — `SpeechToText`:
  - Engine primário: `speechbrain` (`EncoderASR`)
  - Modelo: `speechbrain/asr-wav2vec2-commonvoice-14-en`
  - Pré-processamento: normalize → resample (16kHz) → remove_silence
  - `transcribe(audio, sample_rate, language)` — PCM → texto
  - `transcribe_file(path)` — arquivo → texto
  - `load_model()` / `unload_model()` — gerenciamento de memória
  - `is_available()` — verifica se speechbrain está instalado

- **`ai/audio/tts.py`** — `TextToSpeech`:
  - Engine primário: `espeak-ng` (offline, nativo Linux)
  - Engine secundário: `edge-tts` (vozes naturais, requer internet)
  - Fallback automático entre engines
  - Cache LRU de 128 entradas para frases repetidas
  - `synthesize(text, voice, rate, volume)` — texto → PCM
  - `synthesize_to_file(text, path)` — texto → arquivo WAV
  - `list_voices()` — lista vozes disponíveis
  - `cache_hits` / `cache_misses` — estatísticas de cache

- **`ai/audio/microphone.py`** — `VirtualMicrophone`:
  - Gerencia null-sink + loopback no PipeWire
  - `create()` — cria sink + loopback
  - `remove()` — remove módulos
  - `get_status()` — status detalhado com módulos e sink info
  - Idempotente: verifica existência antes de criar

- **`ai/audio/formats.py`** — Conversão entre formatos:
  - Engine: `ffmpeg` via subprocess
  - Detecção: magic bytes + extensão + ffprobe
  - `convert(input, output_format, ...)` — conversão genérica
  - `to_wav()`, `to_mp3()`, `to_flac()`, `to_pcm()` — helpers
  - `get_audio_info(file)` — duração, sample rate, canais, codec
  - `get_duration(file)`, `get_sample_rate(file)`
  - `get_human_readable_info(file)` — resumo formatado

### Corrigido

- `language` param removido de `_transcribe_with_speechbrain` (EncoderASR não usa)

---

## v0.4.0 — Captura e Reprodução (Fase 4)

**Data:** Julho de 2026

### Adicionado

- **`ai/audio/vad.py`** — `VoiceActivityDetector`:
  - Engine: Google WebRTC VAD (`webrtcvad`)
  - Agressividade: 0-3 (padrão: 2)
  - Frame: 10/20/30ms (padrão: 30ms)
  - `is_speech(frame)` — classifica frame individual
  - `detect_speech(buffer)` — encontra segmentos de fala com timestamps
  - `detect_speech_simple(buffer)` — True/False se há fala
  - `process_frame_streaming(frame)` — streaming com histerese
  - Estados: `speech_start`, `speech`, `speech_end`, `silence`

- **`ai/audio/recorder.py`** — `AudioRecorder`:
  - Engine: `ffmpeg` via subprocess (fallback: `arecord`)
  - Buffer circular (evita perda durante processamento)
  - VAD integrado com padding pré/pós-fala configurável
  - `start(duration, use_vad)` — inicia thread de gravação
  - `stop()` — para e retorna PCM capturado
  - `record_fixed(duration, source)` — gravação síncrona
  - `save_to_file(data, path)` — salva em WAV
  - Callbacks: `data_callback`, `vad_callback`

- **`ai/audio/player.py`** — `AudioPlayer`:
  - Engine: `ffplay` via subprocess (fallback: `aplay`)
  - Fila: `deque` de `PlaybackItem`
  - Crossfade entre faixas via `ffmpeg filter_complex`
  - `play()`, `pause()`, `resume()`, `stop()`, `skip()`
  - `enqueue(source, title, volume, crossfade)`
  - `play_once(source, title, wait)` — reprodução simples
  - `play_tone(frequency, duration)` — gera tom senoidal
  - Volume global + por item (0.0 a 1.0)
  - `PULSE_SINK` env var para redirecionar sink

- **`ai/audio/effects.py`** — Processamento de sinal (8 funções):
  - `apply_gain(data, dB)` — ganho/atenuação
  - `normalize(data, target)` — normalização de pico
  - `noise_gate(data, ...)` — noise gate com attack/release
  - `compressor(data, ...)` — compressão dinâmica
  - `resample(data, orig, target)` — reamostragem (scipy)
  - `high_pass_filter(data, cutoff)` — filtro passa-alta (Butterworth 4ª ordem)
  - `low_pass_filter(data, cutoff)` — filtro passa-baixa (Butterworth 4ª ordem)
  - `remove_silence(data, ...)` — remove silêncio início/fim
  - Todas aceitam `bytes | np.ndarray` e retornam `bytes`

### Corrigido

- `import struct` removido de `vad.py` e `effects.py` (não usado)

---

## v0.3.0 — Módulos Base (Fase 3)

**Data:** Julho de 2026

### Adicionado

- **`ai/audio/__init__.py`** — API pública com `__all__` explícito
- **`ai/audio/exceptions.py`** — Hierarquia de 9 exceções:
  - `AudioError` → `AudioDeviceError`, `AudioCaptureError`, `AudioPlaybackError`,
    `AudioFormatError`, `AudioConversionError`, `VADError`, `STTError`,
    `TTSError`, `AudioConfigError`
- **`ai/audio/settings.py`** — `AudioSettings(BaseSettings)`:
  - 35 campos configuráveis via `IA_LAB_AUDIO_*`
  - Singleton com `@lru_cache`
  - Categorias: devices, sample_rate, VAD, recording, STT, TTS, effects, logs
- **`ai/audio/core.py`** — `AudioEngine` (orquestrador):
  - `initialize()` / `shutdown()` — ciclo de vida
  - `get_default_source()` / `get_default_sink()` — dispositivos padrão
  - `list_sources()` / `list_sinks()` — via `_list_devices()` (DRY)
  - `get_status()` — snapshot completo

### Corrigido

- `$HOME` em `audio_log_dir` removido (pydantic não expande variáveis)
- `list_sources()` / `list_sinks()` refatorados → `_list_devices()` (DRY, -30 linhas)

---

## v0.2.0 — Scripts Bash (Fase 2)

**Data:** Julho de 2026

### Adicionado

- **`scripts/audio/setup_microfone_virtual.sh`** (325 linhas):
  - Cria null-sink + loopback no PipeWire
  - `--apply`: cria/recria o microfone virtual
  - `--remove`: remove módulos
  - `--status`: status detalhado
  - Idempotente: limpa configuração anterior antes de criar

- **`scripts/audio/test_microphone.sh`** (304 linhas):
  - Lista fontes de entrada
  - Grava amostra de 4s com `arecord`
  - Mede nível RMS (requer `sox`)
  - Reproduz gravação
  - `--source <nome>`: testa fonte específica
  - `--record-only`: apenas grava, não reproduz

- **`scripts/audio/test_speaker.sh`** (339 linhas):
  - Gera tom senoidal via `ffmpeg` (fallback: `sox`)
  - Reproduz em sink específico (`PULSE_SINK`)
  - Testa canais estéreo via `speaker-test`
  - `--tone <Hz>`: frequência personalizada
  - `--sink <nome>`: sink específico

- **`scripts/audio/backup_audio_config.sh`** (451 linhas):
  - Coleta: pactl info, módulos, sinks, sources, pw-dump JSON, volumes, config files
  - Compacta em `~/.local/backups/audio/`
  - Verifica integridade do backup
  - `--list`: lista backups existentes
  - `--clean`: remove backups antigos (por quantidade e idade)

- **`scripts/audio/diagnose_audio.sh`** (603 linhas):
  - 7 seções: Kernel, PipeWire, Microfones, Latência, Ferramentas, Virtual Mic, Teste Rápido
  - Gera relatório Markdown em `~/testes-audio/relatorios/`
  - Score de saúde com problemas/avisos
  - Recomendações automáticas
  - `--quick`: apenas resumo
  - `--latency`: foco em latência

### Corrigido

- `$BACKUP_SIZE_FILE` → `$BACKUP_FILE` (typo)
- `ffplay -f pulse -i "$sink"` → `PULSE_SINK="$sink" ffplay` (sintaxe ffplay)
- `diagnose_latency` chamada duplicada quando `--latency` ativo

---

## v0.1.0 — Planejamento e Análise (Fase 1)

**Data:** Julho de 2026

### Análise do Ambiente

- **Sistema de áudio:** PipeWire 1.6.2 (compatível PulseAudio 15.0.0)
- **Microfones:** 2 físicos detectados (Mic1 padrão, Mic2)
- **Ferramentas disponíveis:** `pactl`, `pw-cli`, `pw-dump`, `ffmpeg` 8.0.1, `aplay`, `arecord`
- **Python áudio:** `numpy` 2.4.4, `scipy` 1.18.0, `soundfile` 0.14.0, `speechbrain` 1.1.0,
  `torchaudio` 2.11.0, `webrtcvad` 2.0.10
- **Ferramentas ausentes:** `sox`, `sounddevice`, `pydub`, `edge-tts`, `whisper`

### Estrutura Planejada

```
ai/audio/           ← 13 módulos Python (3.579 linhas)
scripts/audio/      ← 5 scripts Bash (2.022 linhas)
tests/test_audio/   ← (planejado)
ARCHITECTURE.md     ← Documentação da arquitetura
```

---

## Resumo Estatístico

| Fase | Descrição | Arquivos | Linhas |
|---|---|---|---|
| 1 | Planejamento | — | — |
| 2 | Scripts Bash | 5 | 2.022 |
| 3 | Módulos Base (Python) | 4 | 492 |
| 4 | Captura/Reprodução (Python) | 4 | 1.454 |
| 5 | IA Áudio (Python) | 4 | 1.522 |
| 6 | Métricas + API | 2 | ~250 |
| 7 | AudioAgent | 2 | 52 |
| **Total** | | **21** | **~5.677** |

---

## Convenções de Versionamento

- **v0.1.x** — Planejamento e análise
- **v0.2.x** — Scripts Bash
- **v0.3.x** — Módulos base Python
- **v0.4.x** — Captura, reprodução e processamento
- **v0.5.x** — STT, TTS, microfone virtual, formatos
- **v0.6.x** — AudioAgent
- **v0.7.x** — Métricas Prometheus e API REST
- **v1.0.0** — Primeira versão estável (com testes automatizados)
