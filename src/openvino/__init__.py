"""Módulo OpenVINO — Integração opcional com Intel AI Lab.

Fornece pipelines de inferência, áudio e RAG sobre OpenVINO,
expondo funcionalidades do ``AI/openvino/Intel-AI-Lab`` como
um módulo opcional do monolito FastAPI.

Uso:
    from src.openvino.pipelines import OpenVINOPipeline, is_available

    if await is_available():
        pipe = OpenVINOPipeline()
        result = await pipe.generate("explique IA")
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["__version__"]
