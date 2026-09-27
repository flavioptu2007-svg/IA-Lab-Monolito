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


@pytest.fixture(scope="session", autouse=True)
def _isolar_estado_local(tmp_path_factory: pytest.TempPathFactory):
    """Isola o estado local do Coraci em um diretorio temporario.

    O Coraci persiste ``config.json`` e ``coraci.db`` em disco ao salvar pelo
    endpoint. Sem isso, a suite reescreveria arquivos versionados do repositorio
    (Achado 10 da auditoria): a arvore ficava suja e um segredo de teste podia
    ser gravado no arquivo versionado.
    """
    estado = tmp_path_factory.mktemp("coraci-estado")
    overrides = {
        "IA_LAB_CORACI_CONFIG": estado / "config.json",
        "IA_LAB_CORACI_DB": estado / "coraci.db",
        "IA_LAB_CORACI_FLASK_CONFIG": estado / "flask-config.json",
        "IA_LAB_CORACI_FLASK_DB": estado / "flask-coraci.db",
    }
    anteriores = {chave: os.environ.get(chave) for chave in overrides}
    for chave, valor in overrides.items():
        os.environ[chave] = str(valor)
    try:
        yield
    finally:
        for chave, valor in anteriores.items():
            if valor is None:
                os.environ.pop(chave, None)
            else:
                os.environ[chave] = valor


@pytest.fixture(scope="session")
def event_loop() -> Any:
    """Cria um event loop para toda a sessao de teste (pytest-asyncio)."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
