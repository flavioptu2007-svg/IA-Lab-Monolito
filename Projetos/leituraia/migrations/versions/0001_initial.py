"""schema inicial do LeituraIA (usuarios, textos, leituras)

Revision ID: 0001
Revises:
Create Date: 2026-11-13

Portável entre PostgreSQL e SQLite: listas em colunas JSON e unicidade por
sessão via índice único parcial, suportado pelos dois bancos.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("perfil", sa.String(length=30), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(op.f("ix_usuarios_email"), "usuarios", ["email"], unique=True)

    op.create_table(
        "textos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("autor", sa.String(length=200), nullable=False),
        sa.Column("ano", sa.String(length=10), nullable=False),
        sa.Column("disciplina", sa.String(length=60), nullable=False),
        sa.Column("tema", sa.String(length=120), nullable=False),
        sa.Column("nivel", sa.String(length=20), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("genero", sa.String(length=60), nullable=False),
        sa.Column("idioma", sa.String(length=20), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("bncc", sa.JSON(), nullable=False),
        sa.Column("crmg", sa.JSON(), nullable=False),
        sa.Column("glossario", sa.JSON(), nullable=False),
        sa.Column("perguntas", sa.JSON(), nullable=False),
        sa.Column("palavras", sa.Integer(), nullable=False),
        sa.Column("tempo_leitura_min", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_textos_disciplina", "textos", ["disciplina"])
    op.create_index("ix_textos_nivel", "textos", ["nivel"])

    op.create_table(
        "leituras",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("texto_id", sa.String(length=36), nullable=True),
        sa.Column("usuario_id", sa.String(length=36), nullable=True),
        sa.Column("tempo_segundos", sa.Integer(), nullable=False),
        sa.Column("completou", sa.Boolean(), nullable=False),
        sa.Column("sessao", sa.String(length=64), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["texto_id"], ["textos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leituras_texto", "leituras", ["texto_id"])
    op.create_index(
        "uq_leituras_texto_sessao",
        "leituras",
        ["texto_id", "sessao"],
        unique=True,
        postgresql_where=sa.text("sessao IS NOT NULL"),
        sqlite_where=sa.text("sessao IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_leituras_texto_sessao", table_name="leituras")
    op.drop_index("ix_leituras_texto", table_name="leituras")
    op.drop_table("leituras")
    op.drop_index("ix_textos_nivel", table_name="textos")
    op.drop_index("ix_textos_disciplina", table_name="textos")
    op.drop_table("textos")
    op.drop_index(op.f("ix_usuarios_email"), table_name="usuarios")
    op.drop_table("usuarios")
