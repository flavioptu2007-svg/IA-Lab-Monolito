"""Testes da autenticação por API key e da validação anti-SSRF (Achado 7).

Cobre:
- Autenticação desabilitada por padrão (sem ``IA_LAB_API_TOKEN``)
- 401 sem header, com token errado e liberação com token correto nos 3 routers v2
- ``validate_api_base_url``: esquema, host, metadata de cloud e flag de privados
- ``POST /api/v2/config`` e ``POST /api/v2/config/test`` bloqueando SSRF
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from ai.settings import settings
from src.api.v2.chat_coraci import router as chat_router
from src.api.v2.education import router as education_router
from src.api.v2.openvino import router as openvino_router
from src.core import security

PROTECTED_PATHS = ("/api/v2/config", "/api/v2/education/health", "/api/v2/openvino/health")


@pytest.fixture
def client() -> TestClient:
    """App FastAPI apenas com os routers v2 (sem lifespan/DB)."""
    app = FastAPI()
    app.include_router(chat_router)
    app.include_router(education_router)
    app.include_router(openvino_router)
    return TestClient(app)


@pytest.fixture
def token(monkeypatch) -> str:
    """Configura um token e devolve o valor esperado."""
    value = "token-de-teste-123"
    monkeypatch.setattr(settings, "api_token", SecretStr(value))
    return value


# ═════════════════════════════════════════════════════════════════════════════
# Autenticação
# ═════════════════════════════════════════════════════════════════════════════


class TestAuthDesabilitada:
    """Sem token configurado a autenticação fica desligada (dev/testes)."""

    def test_sem_token_nao_exige_header(self, client, monkeypatch):
        monkeypatch.setattr(settings, "api_token", SecretStr(""))
        assert security.auth_enabled() is False
        for path in PROTECTED_PATHS:
            assert client.get(path).status_code == 200, path


class TestAuthComToken:
    """Com token configurado todo router protegido exige X-API-Key."""

    def test_sem_header_retorna_401(self, client, token):
        assert security.auth_enabled() is True
        for path in PROTECTED_PATHS:
            resp = client.get(path)
            assert resp.status_code == 401, path
            assert resp.headers.get("www-authenticate") == security.API_KEY_HEADER

    def test_header_errado_retorna_401(self, client, token):
        resp = client.get("/api/v2/config", headers={security.API_KEY_HEADER: "errado"})
        assert resp.status_code == 401

    def test_token_correto_autoriza(self, client, token):
        resp = client.get("/api/v2/config", headers={security.API_KEY_HEADER: token})
        assert resp.status_code == 200
        assert "model" in resp.json()

    def test_education_e_openvino_autorizados_com_token(self, client, token):
        for path in PROTECTED_PATHS[1:]:
            resp = client.get(path, headers={security.API_KEY_HEADER: token})
            assert resp.status_code == 200, path


# ═════════════════════════════════════════════════════════════════════════════
# validate_api_base_url
# ═════════════════════════════════════════════════════════════════════════════


class TestValidateApiBaseUrl:
    """Bloqueio de esquemas inválidos, metadata e (opcionalmente) rede privada."""

    def test_url_vazia(self):
        with pytest.raises(HTTPException) as exc:
            security.validate_api_base_url("")
        assert exc.value.status_code == 400

    def test_esquema_invalido(self):
        for url in ("file:///etc/passwd", "gopher://127.0.0.1:6379", "ftp://exemplo.com"):
            with pytest.raises(HTTPException) as exc:
                security.validate_api_base_url(url)
            assert exc.value.status_code == 400

    def test_sem_host(self):
        with pytest.raises(HTTPException):
            security.validate_api_base_url("http:///v1")

    def test_metadata_por_ip(self):
        with pytest.raises(HTTPException) as exc:
            security.validate_api_base_url("http://169.254.169.254/latest/meta-data/")
        assert exc.value.status_code == 400
        assert "ssrf" in exc.value.detail.lower()

    def test_metadata_por_hostname(self):
        with pytest.raises(HTTPException):
            security.validate_api_base_url("http://metadata.google.internal/computeMetadata/v1")

    def test_localhost_permitido_por_padrao(self):
        """O projeto é local-first: Ollama na própria máquina deve funcionar."""
        assert security.validate_api_base_url("http://localhost:11434/v1")

    def test_privado_bloqueado_quando_flag_desligada(self, monkeypatch):
        monkeypatch.setattr(settings, "allow_private_api_hosts", False)
        for url in ("http://127.0.0.1:11434/v1", "http://192.168.0.10:8000/v1"):
            with pytest.raises(HTTPException) as exc:
                security.validate_api_base_url(url)
            assert exc.value.status_code == 400

    def test_publico_permitido_com_flag_desligada(self, monkeypatch):
        monkeypatch.setattr(settings, "allow_private_api_hosts", False)
        # 8.8.8.8 é literal (não exige DNS) e é público.
        assert security.validate_api_base_url("https://8.8.8.8/v1")

    def test_metadata_bloqueada_mesmo_com_privados_liberados(self, monkeypatch):
        monkeypatch.setattr(settings, "allow_private_api_hosts", True)
        with pytest.raises(HTTPException):
            security.validate_api_base_url("http://169.254.169.254/")


# ═════════════════════════════════════════════════════════════════════════════
# Endpoints de config bloqueando SSRF
# ═════════════════════════════════════════════════════════════════════════════


class TestConfigEndpointsAntiSSRF:
    """Os endpoints que aceitam api_base_url validam antes de usar."""

    def test_config_test_bloqueia_metadata(self, client):
        resp = client.post(
            "/api/v2/config/test", json={"api_base_url": "http://169.254.169.254/latest"}
        )
        assert resp.status_code == 400
        assert "ssrf" in resp.json()["detail"].lower()

    def test_update_config_bloqueia_metadata(self, client):
        resp = client.post("/api/v2/config", json={"api_base_url": "http://169.254.169.254/v1"})
        assert resp.status_code == 400

    def test_update_config_aceita_url_valida(self, client):
        resp = client.post("/api/v2/config", json={"api_base_url": "http://localhost:11434/v1"})
        assert resp.status_code == 200
