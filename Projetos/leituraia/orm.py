"""Modelos ORM do LeituraIA Brasil (SQLAlchemy 2.0).

O schema é portável entre PostgreSQL (produção) e SQLite (desenvolvimento e
testes): listas são guardadas em colunas JSON e a unicidade por sessão usa um
índice único parcial, suportado pelos dois bancos.

As migrações versionadas ficam em ``leituraia/migrations`` (Alembic). Este
módulo é a fonte da verdade para ``Base.metadata`` — usado tanto pelas
migrações quanto pela criação idempotente em desenvolvimento/testes.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UsuarioORM(Base):
    __tablename__ = "usuarios"

    uid: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    perfil: Mapped[str] = mapped_column(String(30), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    leituras: Mapped[list[LeituraORM]] = relationship(
        back_populates="usuario", passive_deletes=True
    )


class TextoORM(Base):
    __tablename__ = "textos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    autor: Mapped[str] = mapped_column(String(200), nullable=False)
    ano: Mapped[str] = mapped_column(String(10), nullable=False)
    disciplina: Mapped[str] = mapped_column(String(60), nullable=False)
    tema: Mapped[str] = mapped_column(String(120), nullable=False)
    nivel: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    genero: Mapped[str] = mapped_column(String(60), nullable=False)
    idioma: Mapped[str] = mapped_column(String(20), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    bncc: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    crmg: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    glossario: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    perguntas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    palavras: Mapped[int] = mapped_column(Integer, nullable=False)
    tempo_leitura_min: Mapped[int] = mapped_column(Integer, nullable=False)

    leituras: Mapped[list[LeituraORM]] = relationship(
        back_populates="texto",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_textos_disciplina", "disciplina"),
        Index("ix_textos_nivel", "nivel"),
    )


class LeituraORM(Base):
    __tablename__ = "leituras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    texto_id: Mapped[str | None] = mapped_column(
        ForeignKey("textos.id", ondelete="CASCADE"), nullable=True
    )
    usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.uid", ondelete="SET NULL"), nullable=True
    )
    tempo_segundos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completou: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sessao: Mapped[str | None] = mapped_column(String(64), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    texto: Mapped[TextoORM | None] = relationship(back_populates="leituras")
    usuario: Mapped[UsuarioORM | None] = relationship(back_populates="leituras")

    __table_args__ = (
        Index("ix_leituras_texto", "texto_id"),
        # Idempotência do Leitor Digital: a mesma sessão não conta duas vezes.
        Index(
            "uq_leituras_texto_sessao",
            "texto_id",
            "sessao",
            unique=True,
            postgresql_where=text("sessao IS NOT NULL"),
            sqlite_where=text("sessao IS NOT NULL"),
        ),
    )


__all__ = ["Base", "LeituraORM", "TextoORM", "UsuarioORM"]
