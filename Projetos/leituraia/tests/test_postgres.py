"""Integração com PostgreSQL: migração Alembic e API ponta a ponta.

O módulo só roda quando ``LEITURAIA_TEST_DATABASE_URL`` aponta para um
PostgreSQL (o job ``leituraia-postgres`` do Projects CI sobe o serviço). Sem a
variável ele é pulado, então a suíte padrão continua em SQLite — o schema aqui
é criado **pelas migrações**, não por ``create_all``, que é o que se quer
verificar antes de um deploy.
"""

from __future__ import annotations

import os
from pathlib import Path

import leituraia
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from fastapi.testclient import TestClient
from leituraia import db
from leituraia.orm import Base
from sqlalchemy import inspect, text

URL_POSTGRES = os.environ.get("LEITURAIA_TEST_DATABASE_URL", "").strip()
PACOTE = Path(leituraia.__file__).parent
_TABELAS = {"usuarios", "textos", "leituras"}

pytestmark = pytest.mark.skipif(
    not URL_POSTGRES.startswith("postgresql"),
    reason="defina LEITURAIA_TEST_DATABASE_URL (postgresql+psycopg://...) para rodar",
)


# ── Infraestrutura ───────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def banco_isolado():
    """Sobrepõe o fixture do conftest (SQLite/TRUNCATE).

    Aqui o schema é responsabilidade de cada teste, que o recria pelo Alembic;
    truncar tabelas criadas por ``create_all`` mascararia a migração.
    """
    yield


@pytest.fixture
def pg(monkeypatch):
    """Aponta o pacote para o PostgreSQL e deixa o schema vazio."""
    monkeypatch.setenv("LEITURAIA_DATABASE_URL", URL_POSTGRES)
    db.reset_engines()
    _zerar_schema()
    import leituraia.auth as auth_mod
    import leituraia.library as library_mod

    monkeypatch.setattr(auth_mod, "_user_store", None)
    monkeypatch.setattr(library_mod, "_library", None)
    yield URL_POSTGRES
    db.reset_engines()
    _zerar_schema()


def _config() -> Config:
    return Config(str(PACOTE / "alembic.ini"))


def _zerar_schema() -> None:
    """Remove só o schema do LeituraIA (o banco de teste pode ser compartilhado)."""
    engine = db.get_engine()
    Base.metadata.drop_all(engine)
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS alembic_version"))


def _migrar(direcao: str, destino: str) -> None:
    if direcao == "up":
        command.upgrade(_config(), destino)
    else:
        command.downgrade(_config(), destino)


def _versao_aplicada() -> str | None:
    with db.session_scope() as sessao:
        return sessao.execute(text("SELECT version_num FROM alembic_version")).scalar()


def _tabelas() -> set[str]:
    return set(inspect(db.get_engine()).get_table_names())


def _texto(**overrides) -> dict:
    base = {
        "titulo": "O ciclo da água em PostgreSQL",
        "conteudo": "A água evapora, condensa e retorna ao solo. " * 5,
        "ano": "6",
        "disciplina": "Ciências",
        "tema": "Ciclo da água",
        "nivel": "fundamental2",
        "tags": ["agua", "natureza"],
        "bncc": ["EF06CI02"],
        "glossario": ["evaporação"],
        "perguntas": [
            {
                "pergunta": "O que é evaporação?",
                "tipo": "multipla_escolha",
                "resposta": "passagem do estado líquido para o gasoso",
            }
        ],
    }
    base.update(overrides)
    return base


def _registrar(client: TestClient, email: str, perfil: str = "aluno") -> dict:
    resp = client.post(
        "/api/leituraia/auth/registro",
        json={"nome": f"Pessoa {perfil}", "email": email, "senha": "senha123", "perfil": perfil},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    from leituraia.routes import leitor_pages, router

    app = FastAPI()
    app.include_router(router)
    app.include_router(leitor_pages)
    with TestClient(app) as c:
        yield c


# ── Migração ─────────────────────────────────────────────────────────
class TestMigracao:
    def test_upgrade_head_cria_schema_e_versao(self, pg):
        _migrar("up", "head")

        tabelas = _tabelas()
        assert {"usuarios", "textos", "leituras", "alembic_version"} <= tabelas
        assert _versao_aplicada() == ScriptDirectory.from_config(_config()).get_current_head()

        inspetor = inspect(db.get_engine())
        email = {i["name"]: i for i in inspetor.get_indexes("usuarios")}["ix_usuarios_email"]
        assert email["unique"]
        assert {c["name"] for c in inspetor.get_columns("textos")} >= {
            "titulo",
            "conteudo",
            "tags",
            "bncc",
            "perguntas",
        }

    def test_indice_unico_parcial_por_sessao(self, pg):
        _migrar("up", "head")

        indices = {i["name"]: i for i in inspect(db.get_engine()).get_indexes("leituras")}
        sessao = indices["uq_leituras_texto_sessao"]
        assert sessao["unique"]
        assert sessao["column_names"] == ["texto_id", "sessao"]
        assert sessao["dialect_options"]["postgresql_where"] is not None

    def test_upgrade_repetido_nao_duplica_versao(self, pg):
        _migrar("up", "head")
        _migrar("up", "head")

        with db.session_scope() as sessao:
            total = sessao.execute(text("SELECT count(*) FROM alembic_version")).scalar()
        assert total == 1

    def test_downgrade_base_remove_tabelas(self, pg):
        _migrar("up", "head")
        _migrar("down", "base")

        assert not {"usuarios", "textos", "leituras"} & _tabelas()

    def test_migracao_e_modelos_orm_concordam(self, pg):
        """Se o ORM e a migração divergirem, o deploy fica com schema errado."""
        _migrar("up", "head")

        # O banco de teste pode ter outras tabelas (ex.: pgvector); comparar
        # apenas as do LeituraIA evita ruído de objetos alheios ao projeto.
        def apenas_nossas(name: str, type_: str, parent_names: dict) -> bool:
            return type_ != "table" or name in _TABELAS

        with db.get_engine().connect() as conexao:
            contexto = MigrationContext.configure(
                conexao, opts={"compare_type": True, "include_name": apenas_nossas}
            )
            diferencas = compare_metadata(contexto, Base.metadata)
        assert diferencas == []


# ── API sobre o schema migrado ───────────────────────────────────────
class TestApiSobrePostgres:
    def test_registro_login_e_me(self, pg, client):
        criado = _registrar(client, "prof@escola.edu.br", "professor")

        login = client.post(
            "/api/leituraia/auth/login",
            json={"email": "prof@escola.edu.br", "senha": "senha123"},
        )
        assert login.status_code == 200, login.text
        eu = client.get("/api/leituraia/auth/me", headers=_auth(login.json()["access_token"]))
        assert eu.status_code == 200
        assert eu.json()["id"] == criado["usuario"]["id"]
        assert eu.json()["perfil"] == "professor"

    def test_professor_publica_e_aluno_le(self, pg, client):
        prof = _registrar(client, "prof@escola.edu.br", "professor")
        headers = _auth(prof["access_token"])

        criado = client.post("/api/leituraia/biblioteca", json=_texto(), headers=headers)
        assert criado.status_code == 201, criado.text
        texto_id = criado.json()["id"]

        aluno = _registrar(client, "aluno@escola.edu.br", "aluno")
        aluno_headers = _auth(aluno["access_token"])

        listagem = client.get(
            "/api/leituraia/biblioteca", params={"disciplina": "Ciências"}, headers=aluno_headers
        )
        assert listagem.status_code == 200
        assert texto_id in [t["id"] for t in listagem.json()]

        leitura = client.post(
            f"/api/leituraia/biblioteca/{texto_id}/leitura/registro",
            json={"texto_id": texto_id, "tempo_segundos": 90, "completou": True},
            headers=aluno_headers,
        )
        assert leitura.status_code == 201, leitura.text
        assert leitura.json()["total_leituras"] >= 1

        dashboard = client.get("/api/leituraia/dashboard", headers=headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["textos_biblioteca"] >= 1

    def test_leitura_publica_do_leitor_e_idempotente_por_sessao(self, pg, client):
        prof = _registrar(client, "prof@escola.edu.br", "professor")
        texto_id = client.post(
            "/api/leituraia/biblioteca",
            json=_texto(),
            headers=_auth(prof["access_token"]),
        ).json()["id"]

        primeira = client.post(
            f"/leituraia/leitor/{texto_id}/leitura",
            json={"tempo_segundos": 30, "sessao": "visita-1"},
        )
        repetida = client.post(
            f"/leituraia/leitor/{texto_id}/leitura",
            json={"tempo_segundos": 45, "sessao": "visita-1"},
        )
        outra = client.post(
            f"/leituraia/leitor/{texto_id}/leitura",
            json={"tempo_segundos": 10, "sessao": "visita-2"},
        )

        assert primeira.status_code == 201
        assert repetida.json()["total_leituras"] == primeira.json()["total_leituras"]
        assert outra.json()["total_leituras"] == primeira.json()["total_leituras"] + 1

    def test_pagina_do_leitor_nao_expoe_o_gabarito(self, pg, client):
        prof = _registrar(client, "prof@escola.edu.br", "professor")
        texto_id = client.post(
            "/api/leituraia/biblioteca",
            json=_texto(),
            headers=_auth(prof["access_token"]),
        ).json()["id"]

        pagina = client.get(f"/leituraia/leitor/{texto_id}")
        assert pagina.status_code == 200
        assert "O ciclo da água em PostgreSQL" in pagina.text
        assert "evaporação" in pagina.text  # glossário
        assert "O que é evaporação?" in pagina.text
        assert "passagem do estado líquido para o gasoso" not in pagina.text

    def test_dados_persistem_para_uma_nova_conexao(self, pg, client, monkeypatch):
        prof = _registrar(client, "prof@escola.edu.br", "professor")
        client.post(
            "/api/leituraia/biblioteca",
            json=_texto(titulo="Texto persistido no PostgreSQL"),
            headers=_auth(prof["access_token"]),
        )

        # Simula outro processo: descarta engines e singletons em memória.
        db.reset_engines()
        import leituraia.auth as auth_mod
        import leituraia.library as library_mod

        monkeypatch.setattr(auth_mod, "_user_store", None)
        monkeypatch.setattr(library_mod, "_library", None)

        assert any(
            t.titulo == "Texto persistido no PostgreSQL" for t in leituraia.get_library().listar()
        )
        assert auth_mod.UserStore().autenticar("prof@escola.edu.br", "senha123") is not None
