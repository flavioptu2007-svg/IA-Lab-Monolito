"""Executa o contrato de rotas existente com um banco temporário real."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.test_education_module import TestEducationEndpoints as _EducationEndpoints


class TestEducationSQLiteEndpoints(_EducationEndpoints):
    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        import src.education.services as services
        from ai.settings import settings
        from src.api.v2.education import router

        monkeypatch.setattr(settings, "api_token", SecretStr(""))
        monkeypatch.setattr(services, "_store", services.EducationStore(str(tmp_path / "edu.db")))
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            yield client

    def test_router_registrado_na_app(self, client):
        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/v2/education/health" in paths
        assert "/api/v2/education/lesson-plans" in paths
        assert "/api/v2/education/activities" in paths
        assert "/api/v2/education/evaluations" in paths
        assert "/api/v2/education/calendar" in paths
        assert "/api/v2/education/bncc/skills" in paths
