"""Acesso ao banco do LeituraIA Brasil: engine, sessões e inicialização.

O backend é PostgreSQL em produção (``LEITURAIA_DATABASE_URL``) e SQLite por
padrão no desenvolvimento/testes (mesmo schema ORM, sem configuração). A URL
legada ``LEITURAIA_DB_PATH`` continua aceita e vira um SQLite.

Migrações versionadas ficam em ``leituraia/migrations`` (Alembic); em
desenvolvimento/testes ``init_db()`` cria o schema a partir do ORM.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from leituraia.orm import Base

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "leituraia.db"
DEFAULT_DATABASE_URL = f"sqlite+pysqlite:///{DEFAULT_DB_PATH}"

_engines: dict[str, Engine] = {}
_inicializados: set[str] = set()


def _sqlite_url(caminho: Path) -> str:
    return f"sqlite+pysqlite:///{caminho}"


def get_database_url() -> str:
    """URL efetiva do banco: ``LEITURAIA_DATABASE_URL``, ``LEITURAIA_DB_PATH`` ou SQLite local."""
    url = os.environ.get("LEITURAIA_DATABASE_URL", "").strip()
    if url:
        return url
    caminho = os.environ.get("LEITURAIA_DB_PATH", "").strip()
    if caminho:
        return _sqlite_url(Path(caminho).expanduser().resolve())
    return DEFAULT_DATABASE_URL


def get_db_path() -> Path | None:
    """Arquivo SQLite em uso, ou ``None`` quando o banco não é SQLite."""
    url = get_database_url()
    if not url.startswith("sqlite"):
        return None
    return Path(url.split("///", 1)[-1]).expanduser()


def _eh_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _preparar_sqlite(url: str) -> None:
    if not _eh_sqlite(url):
        return
    caminho = url.split("///", 1)[-1]
    if caminho and caminho != ":memory:":
        Path(caminho).expanduser().parent.mkdir(parents=True, exist_ok=True)


def get_engine(url: str | None = None) -> Engine:
    """Engine por URL (cacheada) — uma para cada banco configurado."""
    url = url or get_database_url()
    engine = _engines.get(url)
    if engine is not None:
        return engine

    _preparar_sqlite(url)
    if _eh_sqlite(url):
        engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _ativar_fks(conexao_dbapi, _registro):  # pragma: no cover - hook do driver
            cursor = conexao_dbapi.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        engine = create_engine(url, pool_pre_ping=True)

    _engines[url] = engine
    return engine


@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    """Uma sessão por operação: commit no sucesso, rollback na exceção."""
    sessao = Session(get_engine(url), expire_on_commit=False)
    try:
        yield sessao
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()


def init_db(url: str | None = None) -> None:
    """Cria o schema a partir do ORM (idempotente por URL).

    Em produção o schema é responsabilidade do Alembic; este caminho serve
    para desenvolvimento e testes, onde ``create_all`` é suficiente.
    """
    url = url or get_database_url()
    if url in _inicializados:
        return
    Base.metadata.create_all(get_engine(url))
    _inicializados.add(url)


def reset_engines() -> None:
    """Descarta engines e o cache de inicialização (usado pelos testes)."""
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()
    _inicializados.clear()


__all__ = [
    "DEFAULT_DATABASE_URL",
    "DEFAULT_DB_PATH",
    "get_database_url",
    "get_db_path",
    "get_engine",
    "init_db",
    "reset_engines",
    "session_scope",
]
