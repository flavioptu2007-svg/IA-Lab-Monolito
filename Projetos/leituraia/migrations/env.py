"""Ambiente de execução das migrações do LeituraIA.

A URL vem de ``LEITURAIA_DATABASE_URL`` (ou do SQLite padrão de
desenvolvimento) — nunca fica escrita na configuração.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

RAIZ = Path(__file__).resolve().parents[2]  # ~/Projetos
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from leituraia.db import get_database_url  # noqa: E402 - sys.path ajustado acima
from leituraia.orm import Base  # noqa: E402 - sys.path ajustado acima

config = context.config
config.set_main_option("sqlalchemy.url", get_database_url().replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
