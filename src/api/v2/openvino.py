"""Endpoints OpenVINO — API REST para pipelines de inferência, áudio e RAG.

Todas as rotas são prefixadas com ``/api/v2/openvino`` e
lidam graciosamente com a ausência do OpenVINO (retornam 503
com ``detail="openvino_not_available"``).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

router = APIRouter(prefix="/api/v2/openvino", tags=["openvino"])


# ═══════════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════════


@router.get("/health")
async def openvino_health():
    """Verifica se OpenVINO está disponível no ambiente."""
    from src.openvino.pipelines import is_available

    available = await is_available()
    return {
        "status": "ok" if available else "unavailable",
        "openvino_available": available,
        "message": "OpenVINO está disponível" if available else "OpenVINO não está instalado",
    }


# ═══════════════════════════════════════════════════════════════
# Geração de texto
# ═══════════════════════════════════════════════════════════════


@router.post("/generate")
async def openvino_generate(
    prompt: str,
    system_prompt: str | None = None,
    model_path: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    device: str = "CPU",
    max_new_tokens: int = 256,
    temperature: float = 0.3,
):
    """Gera texto usando pipeline OpenVINO.

    Args:
        prompt: Texto de entrada.
        system_prompt: Instrução de sistema opcional.
        model_path: Modelo (path local ou HF ID).
        device: Dispositivo (CPU, GPU, AUTO).
        max_new_tokens: Máximo de tokens.
        temperature: Temperatura de amostragem.
    """
    from src.openvino.pipelines import OpenVINOPipeline, is_available

    if not await is_available():
        raise HTTPException(status_code=503, detail="openvino_not_available")

    pipe = OpenVINOPipeline(
        model_path=model_path, device=device, max_new_tokens=max_new_tokens, temperature=temperature
    )

    try:
        result = await pipe.generate(prompt=prompt, system_prompt=system_prompt)
        return {"status": "ok", "model": model_path, "device": device, "output": result}
    finally:
        await pipe.close()


# ═══════════════════════════════════════════════════════════════
# Transcrição de áudio
# ═══════════════════════════════════════════════════════════════


@router.post("/transcribe")
async def openvino_transcribe(audio: UploadFile, whisper_model: str = "openai/whisper-tiny.en"):
    """Transcreve um arquivo de áudio com Whisper.

    Args:
        audio: Arquivo de áudio (wav, mp3, etc).
        whisper_model: Modelo Whisper a usar.
    """
    from src.openvino.pipelines import AudioRagPipeline, is_available

    if not await is_available():
        raise HTTPException(status_code=503, detail="openvino_not_available")

    # Salva upload em arquivo temporário
    suffix = Path(audio.filename or "audio.wav").suffix if audio.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    pipe = AudioRagPipeline(whisper_model=whisper_model)

    try:
        result = await pipe.transcribe(tmp_path)
        return {"status": "ok", **result}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        await pipe.close()


# ═══════════════════════════════════════════════════════════════
# RAG — Pergunta sobre base de conhecimento
# ═══════════════════════════════════════════════════════════════


@router.post("/rag/query")
async def openvino_rag_query(question: str, docs_dir: str | None = None, k: int = 4):
    """Faz uma pergunta à base de conhecimento via RAG.

    Args:
        question: Pergunta do usuário.
        docs_dir: Diretório de documentos (opcional).
        k: Número de documentos relevantes.
    """
    from src.openvino.pipelines import AudioRagPipeline, is_available

    if not await is_available():
        raise HTTPException(status_code=503, detail="openvino_not_available")

    pipe = AudioRagPipeline(docs_dir=docs_dir, k=k)

    try:
        result = await pipe.query_rag(question)
        return {"status": "ok", **result}
    finally:
        await pipe.close()


# ═══════════════════════════════════════════════════════════════
# Listar modelos locais
# ═══════════════════════════════════════════════════════════════


@router.get("/models")
async def openvino_models():
    """Lista modelos OpenVINO disponíveis localmente."""
    from src.openvino.pipelines import INTEL_AI_LAB_DIR

    models_dir = INTEL_AI_LAB_DIR / "models" / "openvino"
    models = []

    if models_dir.exists():
        for child in sorted(models_dir.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                models.append(
                    {
                        "name": child.name,
                        "path": str(child),
                        "config_exists": (child / "config.json").exists(),
                    }
                )

    return {
        "status": "ok",
        "models_dir": str(models_dir),
        "models": models,
        "default": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    }
