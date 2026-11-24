import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # ~/Projetos
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def banco_isolado(tmp_path, monkeypatch):
    """Cada teste roda em banco limpo.

    Padrão: arquivo SQLite novo em ``tmp_path``. Com
    ``LEITURAIA_TEST_DATABASE_URL`` definida, a suíte roda contra esse
    PostgreSQL (as tabelas são truncadas antes de cada teste).
    """
    from leituraia import db

    url_postgres = os.environ.get("LEITURAIA_TEST_DATABASE_URL", "").strip()
    if url_postgres:
        monkeypatch.setenv("LEITURAIA_DATABASE_URL", url_postgres)
        db.reset_engines()
        db.init_db()
        from sqlalchemy import text

        with db.session_scope() as sessao:
            sessao.execute(
                text("TRUNCATE TABLE leituras, textos, usuarios RESTART IDENTITY CASCADE")
            )
        caminho = None
    else:
        caminho = tmp_path / "leituraia-test.db"
        monkeypatch.setenv("LEITURAIA_DATABASE_URL", f"sqlite+pysqlite:///{caminho}")
        db.reset_engines()

    import leituraia.auth as auth_mod
    import leituraia.library as library_mod

    monkeypatch.setattr(auth_mod, "_user_store", None)
    monkeypatch.setattr(library_mod, "_library", None)

    yield caminho

    db.reset_engines()
