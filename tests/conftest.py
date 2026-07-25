"""Fixtures globais de teste para o IA-Lab Enterprise."""

from __future__ import annotations

import os
from typing import Any

import pytest

# Apenas vars que NAO conflitam com os defaults do AudioSettings
os.environ.setdefault("IA_LAB_AUDIO_SAMPLE_RATE", "16000")  # = default
os.environ.setdefault("IA_LAB_AUDIO_VAD_AGGRESSIVENESS", "2")  # = default
os.environ.setdefault("IA_LAB_AUDIO_VAD_FRAME_MS", "30")  # = default
os.environ.setdefault("IA_LAB_AUDIO_TTS_ENGINE", "espeak")  # = default
os.environ.setdefault("IA_LAB_AUDIO_STT_DEVICE", "cpu")  # = default
# NOTA: Nao setar vars que mudam defaults (input_device, output_device,
# stt_model, record_temp_dir, etc.) para nao poluir testes de defaults.


@pytest.fixture(scope="session")
def event_loop() -> Any:
    """Cria um event loop para toda a sessao de teste (pytest-asyncio)."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
