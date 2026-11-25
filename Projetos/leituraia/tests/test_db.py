"""Testes da camada de banco: URL/engine, persistência ORM e migrações."""

from pathlib import Path

import leituraia
from alembic import command
from alembic.config import Config
from leituraia import db
from leituraia.auth import UserStore
from leituraia.library import LibraryStore
from leituraia.models import TextoCreate
from leituraia.rbac import Profile
from sqlalchemy import inspect

PACOTE = Path(leituraia.__file__).parent


def _texto(**overrides) -> TextoCreate:
    base = {
        "titulo": "Texto persistido",
        "conteudo": "Conteúdo de teste com palavras suficientes para o schema. " * 3,
        "ano": "7",
        "disciplina": "História",
        "tema": "Feudalismo",
        "nivel": "fundamental2",
    }
    base.update(overrides)
    return TextoCreate(**base)


class TestConfiguracao:
    def test_url_sqlite_vem_do_ambiente(self, tmp_path, monkeypatch):
        # Explicita o caminho: com LEITURAIA_TEST_DATABASE_URL a suíte roda
        # contra PostgreSQL e a URL ambiente seria outra.
        caminho = tmp_path / "config.db"
        monkeypatch.delenv("LEITURAIA_DATABASE_URL", raising=False)
        monkeypatch.setenv("LEITURAIA_DB_PATH", str(caminho))
        db.reset_engines()

        assert db.get_database_url().startswith("sqlite+pysqlite:///")
        assert db.get_db_path() == caminho.resolve()

    def test_url_postgres_nao_tem_arquivo(self, monkeypatch):
        monkeypatch.setenv("LEITURAIA_DATABASE_URL", "postgresql+psycopg:///leituraia")
        assert db.get_db_path() is None

    def test_arquivo_sqlite_e_criado(self, tmp_path, monkeypatch):
        caminho = tmp_path / "novo" / "config.db"
        monkeypatch.delenv("LEITURAIA_DATABASE_URL", raising=False)
        monkeypatch.setenv("LEITURAIA_DB_PATH", str(caminho))
        db.reset_engines()

        UserStore()
        assert caminho.exists()


class TestMigracoes:
    def test_upgrade_cria_e_downgrade_remove_o_schema(self, tmp_path, monkeypatch):
        caminho = tmp_path / "migracoes.db"
        monkeypatch.setenv("LEITURAIA_DATABASE_URL", f"sqlite+pysqlite:///{caminho}")
        db.reset_engines()
        config = Config(str(PACOTE / "alembic.ini"))

        command.upgrade(config, "head")

        inspetor = inspect(db.get_engine())
        assert {"usuarios", "textos", "leituras"} <= set(inspetor.get_table_names())
        indices = {i["name"] for i in inspetor.get_indexes("leituras")}
        assert "uq_leituras_texto_sessao" in indices
        assert "ix_usuarios_email" in {i["name"] for i in inspetor.get_indexes("usuarios")}

        command.downgrade(config, "base")

        db.reset_engines()
        tabelas = set(inspect(db.get_engine()).get_table_names())
        assert not {"usuarios", "textos", "leituras"} & tabelas


class TestPersistenciaDeUsuarios:
    def test_usuario_sobrevive_a_nova_instancia(self):
        u = UserStore().criar("Maria", "maria@escola.edu.br", "senha123", Profile.PROFESSOR)

        outro = UserStore()
        autenticado = outro.autenticar("maria@escola.edu.br", "senha123")
        assert autenticado is not None
        assert autenticado.uid == u.uid
        assert autenticado.perfil == Profile.PROFESSOR
        assert outro.por_id(u.uid).nome == "Maria"

    def test_email_unico_no_banco(self):
        primeira = UserStore()
        primeira.criar("A", "a@x.com", "123456", Profile.ALUNO)

        segunda = UserStore()
        try:
            segunda.criar("B", "a@x.com", "abcdef", Profile.ALUNO)
        except ValueError as exc:
            assert "email" in str(exc)
        else:  # pragma: no cover - falha explícita se não levantar
            raise AssertionError("email duplicado deveria ser rejeitado")
        assert segunda.total == 1

    def test_listar_e_total(self):
        store = UserStore()
        store.criar("Zeca", "z@x.com", "123456", Profile.ALUNO)
        store.criar("Ana", "a@x.com", "123456", Profile.ALUNO)

        assert [u.nome for u in UserStore().listar()] == ["Ana", "Zeca"]
        assert UserStore().total == 2


class TestPersistenciaDaBiblioteca:
    def test_sementes_nao_duplicam_ao_reabrir(self):
        primeira = LibraryStore()
        total = primeira.total_textos
        assert total >= 3

        segunda = LibraryStore()
        assert segunda.total_textos == total

    def test_texto_criado_e_lido_por_outra_instancia(self):
        criado = LibraryStore().criar(_texto(tags=["bncc"], bncc=["EF07HI04"]))

        obtido = LibraryStore().obter(criado.id)
        assert obtido is not None
        assert obtido.titulo == "Texto persistido"
        assert obtido.tags == ["bncc"]
        assert obtido.bncc == ["EF07HI04"]

    def test_filtros_no_banco(self):
        lib = LibraryStore()
        assert lib.listar(disciplina="história")
        assert lib.listar(nivel="inexistente") == []
        assert lib.listar(tema="FEUDALISMO")

    def test_deletar_remove_do_banco(self):
        lib = LibraryStore()
        criado = lib.criar(_texto())
        assert lib.deletar(criado.id) is True
        assert LibraryStore().obter(criado.id) is None

    def test_habilidades_vem_do_banco(self):
        lib = LibraryStore()
        lib.criar(_texto(bncc=["EF07HI04", "EF07HI05"]))
        assert {"EF07HI04", "EF07HI05"} <= set(lib.habilidades())


class TestPersistenciaDeLeituras:
    def test_leituras_acumulam_no_banco(self):
        lib = LibraryStore()
        texto = lib.criar(_texto())
        usuario = UserStore().criar("Ana", "ana@x.com", "123456", Profile.ALUNO)

        antes = lib.total_leituras
        total = lib.registrar_leitura(
            texto_id=texto.id,
            usuario_id=usuario.uid,
            tempo_segundos=120,
            completou=True,
        )
        assert total == antes + 1
        assert LibraryStore().total_leituras == antes + 1
        assert lib.registrar_leitura() == antes + 2  # registro sem detalhes

    def test_sessao_do_leitor_e_idempotente(self):
        lib = LibraryStore()
        texto = lib.criar(_texto())
        antes = lib.total_leituras

        assert (
            lib.registrar_leitura(texto_id=texto.id, tempo_segundos=30, sessao="visita-1")
            == antes + 1
        )
        # Recarregar a página/reenviar a mesma visita não infla o contador.
        assert (
            lib.registrar_leitura(texto_id=texto.id, tempo_segundos=45, sessao="visita-1")
            == antes + 1
        )
        # Uma visita nova conta.
        assert (
            lib.registrar_leitura(texto_id=texto.id, tempo_segundos=10, sessao="visita-2")
            == antes + 2
        )
        # Leituras autenticadas (sem sessão) sempre contam.
        assert lib.registrar_leitura(texto_id=texto.id, tempo_segundos=10) == antes + 3

    def test_deletar_texto_remove_leituras_em_cascata(self):
        lib = LibraryStore()
        texto = lib.criar(_texto())
        antes = lib.total_leituras
        lib.registrar_leitura(texto_id=texto.id, tempo_segundos=30)

        lib.deletar(texto.id)
        assert lib.total_leituras == antes
