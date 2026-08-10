"""Backend FastAPI para o painel web do IA-Lab Unified.

Fornece endpoints REST para:
- Chat com IA (roteamento inteligente) + SSE streaming (Coraci)
- Agentes especializados
- Histórico de conversas
- Métricas Prometheus
- Áudio (STT, TTS, efeitos, microfone virtual)
- OpenVINO (opcional) — inferência Intel
- Education (HistóriaIA) — planos, atividades, avaliações, BNCC
"""

from __future__ import annotations

import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Módulos auxiliares ───────────────────────────────────────────
from src.core.lifespan import lifespan
from src.core.routers import register_routers

app = FastAPI(
    title="IA-Lab Unified API",
    version="2.0.0",
    description="Monolito FastAPI unificado — IA, Áudio, RAG, OpenVINO e Educação",
    lifespan=lifespan,
)

# CORS: painel dev (React localhost:5173) + portal educacional
# (Firebase Hosting, LAN escolar e futuro domínio próprio)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
        "https://jogos-5f131.web.app",
        "http://192.168.15.17:8765",
        "https://educacionai.com.br",
    ],
    allow_origin_regex=r"https?://192\.168\.\d{1,3}\.\d{1,3}:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Monta rotas dos módulos unificados ────────────────────────────
register_routers(app)

# ---- Dependências internas (lazy import para evitar circular no startup) ----


def get_service():
    from ai.service import AIService

    return AIService()


def get_agent_registry():
    from ai.agents.base import get_agent_registry

    return get_agent_registry()


def get_settings():
    from ai.settings import settings

    return settings


# ---- Modelos Pydantic ----


class ChatRequest(BaseModel):
    prompt: str
    provider: str | None = None
    task_type: str | None = None
    use_rag: bool = True
    agent: str | None = None


class ChatResponse(BaseModel):
    response: str
    provider: str
    task_type: str
    latency_ms: int


class AgentInfo(BaseModel):
    name: str
    task_type: str
    default_provider: str


class HistoryEntry(BaseModel):
    id: str
    prompt: str
    response: str
    provider: str
    task_type: str
    timestamp: float
    agent: str | None = None


# ---- Armazenamento em memória (histórico, substituir por banco futuro) ----


class HistoryStore:
    def __init__(self):
        self._entries: list[HistoryEntry] = []
        self._counter = 0

    def add(self, entry: HistoryEntry) -> None:
        self._entries.append(entry)
        self._counter += 1

    def list(self, limit: int = 50) -> list[HistoryEntry]:
        return list(reversed(self._entries))[:limit]

    def clear(self) -> None:
        self._entries.clear()
        self._counter = 0


history_store = HistoryStore()

# ---- Rotas da API ----


@app.get("/api/health")
async def health():
    """Health check completo do sistema."""
    from ai.memory.store import VectorStore
    from ai.telemetry import health_status as hs

    checks: dict[str, str] = {}

    # Qdrant
    try:
        store = VectorStore()
        qdrant_ok = store.is_available()
        checks["qdrant"] = "ok" if qdrant_ok else "error"
        hs.labels(component="qdrant").set(1 if qdrant_ok else 0)
    except Exception:
        checks["qdrant"] = "error"
        hs.labels(component="qdrant").set(0)

    # Ollama (via health check do settings)
    import httpx

    try:
        cfg = get_settings()
        resp = httpx.get(f"{cfg.ollama_base_url}/api/tags", timeout=cfg.health_check_timeout)
        ollama_ok = resp.status_code == 200
        checks["ollama"] = "ok" if ollama_ok else "error"
        hs.labels(component="ollama").set(1 if ollama_ok else 0)
    except Exception:
        checks["ollama"] = "error"
        hs.labels(component="ollama").set(0)

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks, "version": "2.0.0"}


@app.get("/api/providers")
async def list_providers():
    """Lista providers disponíveis com seus status."""
    cfg = get_settings()
    providers = [
        {
            "name": "glm",
            "model": cfg.glm_model,
            "configured": bool(cfg.glm_api_key),
            "task": "code",
        },
        {"name": "ollama", "model": cfg.ollama_model, "configured": True, "task": "local"},
        {"name": "bitnet", "model": cfg.bitnet_model, "configured": True, "task": "local"},
        {
            "name": "openai",
            "model": cfg.openai_model,
            "configured": bool(cfg.openai_api_key),
            "task": "general",
        },
        {
            "name": "claude",
            "model": cfg.claude_model,
            "configured": bool(cfg.claude_api_key),
            "task": "general",
        },
        {
            "name": "gemini",
            "model": cfg.gemini_model,
            "configured": bool(cfg.gemini_api_key),
            "task": "architecture",
        },
        {
            "name": "groq",
            "model": cfg.groq_model,
            "configured": bool(cfg.groq_api_key),
            "task": "general",
        },
        {
            "name": "perplexity",
            "model": cfg.perplexity_model,
            "configured": bool(cfg.perplexity_api_key),
            "task": "general",
        },
    ]
    return {"providers": providers}


@app.get("/api/agents")
async def list_agents():
    """Lista agentes especializados disponíveis."""
    registry = get_agent_registry()
    agents = []
    for name in registry.list_names():
        agent = registry.create(name)
        agents.append(
            {
                "name": agent.name,
                "task_type": agent.task_type.value,
                "default_provider": agent.default_provider,
                "description": (
                    f"Agente especializado em {agent.task_type.value}. "
                    f"Provider padrão: {agent.default_provider}"
                ),
            }
        )
    return {"agents": agents}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Envia uma mensagem para a IA com roteamento inteligente."""
    from ai.providers.base import TaskType

    service = get_service()
    start = time.monotonic()

    try:
        # Se um agente foi especificado, usa ele em vez do chat direto
        if request.agent:
            registry = get_agent_registry()
            try:
                agent = registry.create(request.agent)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc))

            response_text = await agent.run(
                request.prompt, provider=request.provider, use_rag=request.use_rag
            )
            task_type = agent.task_type.value
            provider = request.provider or agent.default_provider or "auto"
        else:
            # TaskType a partir da string
            task_type_enum = None
            if request.task_type:
                try:
                    task_type_enum = TaskType(request.task_type)
                except ValueError:
                    task_type_enum = request.task_type

            response_text = await service.complete(
                prompt=request.prompt,
                provider=request.provider,
                task_type=task_type_enum,
                use_rag=request.use_rag,
            )

            # Extrai o provider real usado e task_type da service
            final_task = task_type_enum
            if final_task is None:
                from ai.classifier import TaskClassifier

                final_task = TaskClassifier.classify(request.prompt)
            task_type = getattr(final_task, "value", str(final_task))
            provider = request.provider or service.choose_provider(request.provider)

        latency = int((time.monotonic() - start) * 1000)

        # Histórico
        entry = HistoryEntry(
            id=str(time.time_ns()),
            prompt=request.prompt,
            response=response_text,
            provider=provider,
            task_type=task_type,
            timestamp=time.time(),
            agent=request.agent,
        )
        history_store.add(entry)

        return ChatResponse(
            response=response_text, provider=provider, task_type=task_type, latency_ms=latency
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/history")
async def get_history(limit: int = 50):
    """Retorna o histórico de conversas."""
    entries = history_store.list(limit=limit)
    return {"history": [e.model_dump() for e in entries]}


@app.delete("/api/history")
async def clear_history():
    """Limpa o histórico de conversas."""
    history_store.clear()
    return {"status": "ok"}


@app.get("/api/metrics")
async def get_metrics():
    """Retorna um snapshot das métricas Prometheus."""
    from prometheus_client.registry import REGISTRY

    # Coleta amostras das métricas mais importantes
    samples = {}
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            key = sample.name
            labels = dict(sample.labels)
            if key not in samples:
                samples[key] = []
            samples[key].append({"labels": labels, "value": sample.value})

    return {"metrics": samples}


@app.get("/api/config")
async def get_config():
    """Retorna a configuração atual do sistema (sem secrets)."""
    cfg = get_settings()
    return {
        "primary_provider": cfg.primary_provider,
        "local_provider": cfg.local_provider,
        "providers": {
            "glm": {"model": cfg.glm_model, "configured": bool(cfg.glm_api_key)},
            "ollama": {"model": cfg.ollama_model, "configured": True},
            "openai": {"model": cfg.openai_model, "configured": bool(cfg.openai_api_key)},
            "claude": {"model": cfg.claude_model, "configured": bool(cfg.claude_api_key)},
            "gemini": {"model": cfg.gemini_model, "configured": bool(cfg.gemini_api_key)},
            "groq": {"model": cfg.groq_model, "configured": bool(cfg.groq_api_key)},
            "perplexity": {
                "model": cfg.perplexity_model,
                "configured": bool(cfg.perplexity_api_key),
            },
        },
        "rag_enabled": cfg.rag_enabled,
        "qdrant_host": cfg.qdrant_host,
        "qdrant_port": cfg.qdrant_port,
        "log_level": cfg.log_level,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Audio API — /api/audio/*
# ═══════════════════════════════════════════════════════════════════════════


def get_audio_engine():
    from ai.audio import AudioEngine

    return AudioEngine()


# ── Modelos de áudio ──────────────────────────────────────────────────────


class AudioRecordRequest(BaseModel):
    duration: float | None = None
    source: str | None = None
    use_vad: bool = False
    save_format: str = "wav"  # wav, mp3, flac, pcm


class AudioTTSRequest(BaseModel):
    text: str
    voice: str | None = None
    engine: str | None = None
    rate: int | None = None
    save_format: str = "wav"


class AudioSTTRequest(BaseModel):
    audio_base64: str = ""
    audio_format: str = "pcm"  # pcm, wav, mp3
    language: str | None = None
    sample_rate: int | None = None


class AudioEffectsRequest(BaseModel):
    audio_base64: str = ""  # PCM 16-bit mono em base64
    apply_gain: float | None = None  # dB
    normalize: bool = False
    noise_gate: bool = False
    compressor: bool = False
    high_pass: float | None = None  # Hz
    low_pass: float | None = None  # Hz
    remove_silence: bool = False


class AudioMicRequest(BaseModel):
    sink_name: str | None = None
    description: str | None = None


# ── Rotas de áudio ────────────────────────────────────────────────────────


@app.get("/api/audio/status")
async def audio_status():
    """Status completo do módulo de áudio."""
    from ai.audio import metrics as am

    engine = get_audio_engine()
    status = await engine.get_status()

    # Atualiza métricas de dispositivos
    for src in engine.list_sources():
        am.device_status.labels(device_name=src["name"], device_type="source").set(
            1 if src["state"] == "RUNNING" else 0
        )

    for snk in engine.list_sinks():
        am.device_status.labels(device_name=snk["name"], device_type="sink").set(
            1 if snk["state"] == "RUNNING" else 0
        )

    return status


@app.get("/api/audio/devices")
async def audio_devices():
    """Lista todos os dispositivos de áudio (entrada e saída)."""
    engine = get_audio_engine()

    return {
        "default_source": engine.get_default_source(),
        "default_sink": engine.get_default_sink(),
        "sources": engine.list_sources(),
        "sinks": engine.list_sinks(),
        "sample_rate": engine.sample_rate,
    }


@app.post("/api/audio/record")
async def audio_record(request: AudioRecordRequest):
    """Grava áudio do microfone.

    Args no body:
        duration: Duração em segundos (None = contínuo / VAD).
        source: Nome do dispositivo PulseAudio.
        use_vad: Se True, para automaticamente quando não detectar fala.
        save_format: Formato de saída (wav, mp3, flac, pcm).

    Returns:
        Dados de áudio no formato solicitado, ou erro.
    """
    from ai.audio import metrics as am
    import base64

    engine = get_audio_engine()
    from ai.audio.recorder import AudioRecorder

    recorder = AudioRecorder(source=request.source)

    try:
        am.audio_recording.labels(source=request.source or "default").set(1)

        audio_data = recorder.record_fixed(duration=request.duration or 5.0, source=request.source)

        # Converte para formato solicitado
        if request.save_format != "pcm":
            from ai.audio import formats as fm

            audio_data = fm.convert(
                audio_data, f".{request.save_format}", sample_rate=engine.sample_rate
            )

        # Métricas
        am.audio_capture_duration.labels(source=request.source or "default").observe(
            request.duration or 5.0
        )
        am.audio_capture_bytes.labels(
            source=request.source or "default", format=request.save_format
        ).inc(len(audio_data))

        return {
            "status": "ok",
            "format": request.save_format,
            "duration_sec": request.duration or 5.0,
            "size_bytes": len(audio_data),
            "audio_base64": base64.b64encode(audio_data).decode(),
        }

    except Exception as e:
        am.audio_errors.labels(error_type="capture").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        am.audio_recording.labels(source=request.source or "default").set(0)


@app.post("/api/audio/effects")
async def audio_effects(request: AudioEffectsRequest):
    """Aplica efeitos de processamento a um áudio enviado como base64.

    O áudio PCM 16-bit deve ser enviado como campo "audio_base64" no body.
    """
    from ai.audio import effects as ef
    from ai.audio import metrics as am
    import base64

    if not request.audio_base64:
        raise HTTPException(
            status_code=400, detail="Campo 'audio_base64' com PCM 16-bit é obrigatório"
        )

    try:
        audio_data = base64.b64decode(request.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="audio_base64 inválido")

    try:
        # Aplica efeitos em cadeia
        processed = audio_data

        if request.high_pass:
            processed = ef.high_pass_filter(processed, cutoff_hz=request.high_pass)

        if request.low_pass:
            processed = ef.low_pass_filter(processed, cutoff_hz=request.low_pass)

        if request.noise_gate:
            processed = ef.noise_gate(processed)

        if request.compressor:
            processed = ef.compressor(processed)

        if request.apply_gain:
            processed = ef.apply_gain(processed, request.apply_gain)

        if request.normalize:
            processed = ef.normalize(processed)

        if request.remove_silence:
            processed = ef.remove_silence(processed)

        return {
            "status": "ok",
            "original_size": len(audio_data),
            "processed_size": len(processed),
            "effects_applied": [
                k
                for k, v in {
                    "high_pass": request.high_pass,
                    "low_pass": request.low_pass,
                    "noise_gate": request.noise_gate,
                    "compressor": request.compressor,
                    "apply_gain": request.apply_gain,
                    "normalize": request.normalize,
                    "remove_silence": request.remove_silence,
                }.items()
                if v
            ],
            "audio_base64": base64.b64encode(processed).decode(),
        }

    except Exception as e:
        am.audio_errors.labels(error_type="config").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/stt")
async def audio_stt(request: AudioSTTRequest):
    """Transcreve áudio (enviado como base64 no body) para texto.

    O áudio deve ser enviado como campo "audio_base64" no body JSON.
    """
    from ai.audio import metrics as am
    import base64

    if not request.audio_base64:
        raise HTTPException(status_code=400, detail="Campo 'audio_base64' é obrigatório no body")

    try:
        audio_data = base64.b64decode(request.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="audio_base64 inválido")

    from ai.audio.stt import SpeechToText

    stt = SpeechToText(language=request.language)

    try:
        am.stt_requests.labels(model=stt.model_name, status="started").inc()

        import time

        start = time.monotonic()

        text = stt.transcribe(
            audio_data, sample_rate=request.sample_rate, language=request.language
        )

        elapsed = time.monotonic() - start

        # Métricas
        audio_duration = len(audio_data) / (request.sample_rate or 16000) / 2  # estimativa
        am.stt_duration.labels(model=stt.model_name).observe(elapsed)
        am.stt_audio_duration.labels(model=stt.model_name).observe(audio_duration)
        am.stt_characters.labels(model=stt.model_name, language=request.language or "pt").inc(
            len(text)
        )
        am.stt_requests.labels(model=stt.model_name, status="success").inc()

        return {
            "status": "ok",
            "text": text,
            "characters": len(text),
            "latency_ms": int(elapsed * 1000),
            "audio_duration_sec": round(audio_duration, 2),
        }

    except Exception as e:
        am.stt_requests.labels(model=stt.model_name, status="error").inc()
        am.audio_errors.labels(error_type="stt").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/tts")
async def audio_tts(request: AudioTTSRequest):
    """Sintetiza texto em áudio (Text-to-Speech).

    Args no body:
        text: Texto a ser sintetizado.
        voice: Voz/idioma (ex: 'pt-br', 'en-us').
        engine: Engine ('espeak' ou 'edge-tts', padrão: settings).
        rate: Velocidade de fala.
        save_format: Formato de saída (wav, mp3, flac, pcm).

    Returns:
        Áudio em base64 no formato solicitado.
    """
    from ai.audio import metrics as am
    import base64
    import time

    from ai.audio.tts import TextToSpeech

    tts = TextToSpeech(engine=request.engine, voice=request.voice, rate=request.rate)

    try:
        am.tts_requests.labels(engine=tts.engine, status="started").inc()

        start = time.monotonic()

        audio_data = tts.synthesize(request.text, voice=request.voice, rate=request.rate)

        elapsed = time.monotonic() - start

        # Engine real (pode ser fallback — ex.: edge-tts quando espeak ausente)
        real_engine = tts.last_engine or tts.engine

        if not audio_data:
            raise HTTPException(status_code=500, detail="Falha na síntese de áudio — retorno vazio")

        # Converte para formato solicitado
        if request.save_format != "pcm":
            try:
                from ai.audio import formats as fm

                audio_data = fm.convert(audio_data, f".{request.save_format}")
            except Exception:
                # Fallback: retorna PCM mesmo se conversão falhar
                pass

        # Métricas
        audio_duration = len(audio_data) / 16000 / 2  # estimativa PCM 16kHz
        am.tts_duration.labels(engine=real_engine, voice=request.voice or tts.voice).observe(elapsed)
        am.tts_audio_duration.labels(engine=real_engine).observe(audio_duration)
        am.tts_characters.labels(engine=real_engine, voice=request.voice or tts.voice).inc(
            len(request.text)
        )
        am.tts_requests.labels(engine=real_engine, status="success").inc()

        return {
            "status": "ok",
            "format": request.save_format,
            "text_length": len(request.text),
            "audio_duration_sec": round(audio_duration, 2),
            "latency_ms": int(elapsed * 1000),
            "engine": real_engine,
            "voice": request.voice or tts.voice,
            "audio_base64": base64.b64encode(audio_data).decode(),
        }

    except HTTPException:
        raise
    except Exception as e:
        am.tts_requests.labels(engine=tts.engine, status="error").inc()
        am.audio_errors.labels(error_type="tts").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audio/mic/status")
async def audio_mic_status():
    """Status do microfone virtual."""
    from ai.audio.microphone import VirtualMicrophone
    from ai.audio import metrics as am

    vmic = VirtualMicrophone()
    status = vmic.get_status()

    # Atualiza métricas
    am.virtual_mic_active.set(1 if status["active"] else 0)
    am.virtual_mic_loopback.set(1 if len(status.get("modules", [])) > 1 else 0)
    am.device_status.labels(device_name=vmic.sink_name, device_type="virtual_mic").set(
        1 if status["sink_exists"] else 0
    )

    return status


@app.post("/api/audio/mic/create")
async def audio_mic_create(request: AudioMicRequest):
    """Cria o microfone virtual no PipeWire."""
    from ai.audio.microphone import VirtualMicrophone
    from ai.audio import metrics as am

    vmic = VirtualMicrophone(sink_name=request.sink_name, description=request.description)

    try:
        result = vmic.create()
        if result:
            am.virtual_mic_active.set(1)
            am.device_status.labels(device_name=vmic.sink_name, device_type="virtual_mic").set(1)
            return {"status": "ok", "sink_name": vmic.sink_name, "source_name": vmic.source_name}
        else:
            raise HTTPException(status_code=500, detail="Falha ao criar microfone virtual")
    except Exception as e:
        am.audio_errors.labels(error_type="device").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/mic/remove")
async def audio_mic_remove(request: AudioMicRequest):
    """Remove o microfone virtual do PipeWire."""
    from ai.audio.microphone import VirtualMicrophone
    from ai.audio import metrics as am

    vmic = VirtualMicrophone(sink_name=request.sink_name, description=request.description)

    try:
        result = vmic.remove()
        am.virtual_mic_active.set(0)
        am.virtual_mic_loopback.set(0)
        am.device_status.labels(device_name=vmic.sink_name, device_type="virtual_mic").set(0)
        return {"status": "ok", "removed": result}
    except Exception as e:
        am.audio_errors.labels(error_type="device").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audio/metrics")
async def audio_metrics():
    """Retorna um snapshot das métricas Prometheus específicas de áudio."""
    from prometheus_client.registry import REGISTRY

    samples = {}
    for metric in REGISTRY.collect():
        # Filtra apenas métricas de áudio
        if not metric.name.startswith("ia_lab_audio"):
            continue
        for sample in metric.samples:
            key = sample.name
            labels = dict(sample.labels)
            if key not in samples:
                samples[key] = []
            samples[key].append({"labels": labels, "value": sample.value})

    return {"audio_metrics": samples}


@app.get("/api/audio/config")
async def audio_config():
    """Retorna a configuração do módulo de áudio (sem secrets)."""
    from ai.audio.settings import audio_settings as acfg

    return {
        "input_device": acfg.input_device,
        "output_device": acfg.output_device,
        "sample_rate": acfg.sample_rate,
        "vad_aggressiveness": acfg.vad_aggressiveness,
        "vad_frame_ms": acfg.vad_frame_ms,
        "stt_model": acfg.stt_model,
        "stt_device": acfg.stt_device,
        "stt_language": acfg.stt_language,
        "tts_engine": acfg.tts_engine,
        "tts_voice": acfg.tts_voice,
        "tts_rate": acfg.tts_rate,
        "virtual_mic_name": acfg.virtual_mic_name,
        "record_buffer_seconds": acfg.record_buffer_seconds,
        "record_max_duration": acfg.record_max_duration,
        "noise_gate_threshold": acfg.noise_gate_threshold,
        "compressor_threshold": acfg.compressor_threshold,
        "compressor_ratio": acfg.compressor_ratio,
    }


# ---- Ponto de entrada ----


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api.server:app", host="0.0.0.0", port=port, reload=True)
