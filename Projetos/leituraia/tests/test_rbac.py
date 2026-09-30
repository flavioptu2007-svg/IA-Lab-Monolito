"""Testes da matriz RBAC do LeituraIA Brasil."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from leituraia.auth import get_current_user
from leituraia.rbac import PERMISSIONS, Profile, require, tem_permissao


class TestMatrizPermissoes:
    def test_permissoes_mapeiam_para_perfis(self):
        for permissao, perfis in PERMISSIONS.items():
            assert isinstance(permissao, str)
            assert perfis, f"permissão '{permissao}' não pode ter conjunto vazio"
            assert all(isinstance(p, Profile) for p in perfis)

    def test_admin_tem_permissoes_de_gestao(self):
        for permissao in PERMISSIONS:
            if permissao == "leitura:registrar":  # ação do aluno/professor/monitor
                continue
            assert tem_permissao(Profile.ADMIN, permissao), permissao

    def test_aluno_pode_ler_mas_nao_gerar(self):
        assert tem_permissao(Profile.ALUNO, "textos:ler")
        assert not tem_permissao(Profile.ALUNO, "textos:gerar")
        assert not tem_permissao(Profile.ALUNO, "usuarios:gerenciar")

    def test_monitor_limitado(self):
        assert tem_permissao(Profile.MONITOR, "alunos:ver")
        assert not tem_permissao(Profile.MONITOR, "textos:gerar")
        assert not tem_permissao(Profile.MONITOR, "relatorios:ver")

    def test_usuarios_gerenciar_apenas_admin_secretaria(self):
        permitidos = PERMISSIONS["usuarios:gerenciar"]
        assert permitidos == {Profile.ADMIN, Profile.SECRETARIA}

    def test_config_gerenciar_so_admin(self):
        assert PERMISSIONS["config:gerenciar"] == {Profile.ADMIN}

    def test_permissao_desconhecida_negada(self):
        assert not tem_permissao(Profile.ADMIN, "permissao:inexistente")

    def test_aceita_string_como_perfil(self):
        assert tem_permissao("admin", "config:gerenciar")
        assert not tem_permissao("aluno", "config:gerenciar")

    def test_onze_perfis_definidos(self):
        assert len(Profile) == 11

    @pytest.mark.parametrize(
        "perfil,permissao,esperado",
        [
            (Profile.RESPONSAVEL, "textos:ler", True),
            (Profile.RESPONSAVEL, "dashboard:ver", False),
            (Profile.ALUNO, "leitura:registrar", True),
            (Profile.PROFESSOR, "leitura:registrar", True),
            (Profile.SECRETARIA, "relatorios:ver", True),
            (Profile.COORDENADOR, "textos:publicar", True),
            (Profile.PROFESSOR, "textos:publicar", False),
        ],
    )
    def test_casos_da_matriz(self, perfil, permissao, esperado):
        assert tem_permissao(perfil, permissao) is esperado


class TestRequireDependency:
    def _app_com_rota(self, permissao: str) -> FastAPI:
        app = FastAPI()

        @app.get("/protegido", dependencies=[Depends(require(permissao))])
        def protegido():
            return {"ok": True}

        return app

    def test_403_sem_permissao(self):
        app = self._app_com_rota("config:gerenciar")

        class FakeUser:
            perfil = Profile.ALUNO

        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        client = TestClient(app)
        resp = client.get("/protegido")
        assert resp.status_code == 403
        assert "config:gerenciar" in resp.json()["detail"]

    def test_200_com_permissao(self):
        app = self._app_com_rota("textos:ler")

        class FakeUser:
            perfil = Profile.ALUNO

        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        client = TestClient(app)
        resp = client.get("/protegido")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
