"""Regressão do Achado 10 — a suíte não pode reescrever estado versionado.

O Coraci (Flask legado e FastAPI v2) persiste ``config.json`` em disco. Sem
isolamento, rodar ``pytest`` deixava ``git status`` sujo com
``Aplicativo_Coraci/config.json`` e ``src/Aplicativo_Coraci/config.json``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
APP_CORACI = RAIZ / "Aplicativo_Coraci"
CONFIG_FLASK = APP_CORACI / "config.json"
CONFIG_FASTAPI = RAIZ / "src" / "Aplicativo_Coraci" / "config.json"


def _ler(caminho: Path) -> bytes | None:
    return caminho.read_bytes() if caminho.exists() else None


@pytest.fixture(scope="module")
def flask_coraci():
    """Carrega Aplicativo_Coraci/app.py como módulo independente."""
    spec = importlib.util.spec_from_file_location("coraci_app_isolado", APP_CORACI / "app.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["coraci_app_isolado"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestCaminhosIsolados:
    """Os caminhos resolvidos devem ficar fora do repositório durante os testes."""

    def test_fastapi_aponta_para_fora_do_repositorio(self):
        from src.api.v2 import chat_coraci

        for bruto in (chat_coraci.get_config_path(), chat_coraci.get_db_path()):
            assert RAIZ not in Path(bruto).resolve().parents, bruto

    def test_flask_aponta_para_fora_do_repositorio(self, flask_coraci):
        for caminho in (flask_coraci.get_config_file(), Path(flask_coraci.get_db_path())):
            assert RAIZ not in caminho.resolve().parents, caminho


class TestSaveConfigNaoTocaNoRepositorio:
    """save_config deve gravar no caminho do override, nunca no arquivo versionado."""

    def test_fastapi(self, tmp_path, monkeypatch):
        from src.api.v2 import chat_coraci

        alvo = tmp_path / "config.json"
        monkeypatch.setenv("IA_LAB_CORACI_CONFIG", str(alvo))
        antes = _ler(CONFIG_FASTAPI)

        chat_coraci.save_config({"model": "modelo-de-teste"})

        assert alvo.exists()
        assert "modelo-de-teste" in alvo.read_text()
        assert _ler(CONFIG_FASTAPI) == antes

    def test_flask(self, flask_coraci, tmp_path, monkeypatch):
        alvo = tmp_path / "flask-config.json"
        monkeypatch.setenv("IA_LAB_CORACI_FLASK_CONFIG", str(alvo))
        antes = _ler(CONFIG_FLASK)

        flask_coraci.save_config({"model": "modelo-de-teste"})

        assert alvo.exists()
        assert "modelo-de-teste" in alvo.read_text()
        assert _ler(CONFIG_FLASK) == antes


class TestEndpointsDoFastAPI:
    """POST /api/v2/config não deve escrever no config.json do repositório."""

    def test_update_config_persiste_fora_do_repo(self, monkeypatch):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.api.v2.chat_coraci import router

        antes = _ler(CONFIG_FASTAPI)
        app = FastAPI()
        app.include_router(router)

        resp = TestClient(app).post("/api/v2/config", json={"model": "via-endpoint"})

        assert resp.status_code == 200
        assert _ler(CONFIG_FASTAPI) == antes
