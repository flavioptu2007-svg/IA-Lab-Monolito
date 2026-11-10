"""Persistência SQLite dos materiais educacionais, sem dependências externas."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from src.education.schemas import EducationBase

Model = TypeVar("Model", bound=EducationBase)


class MaterialConflictError(ValueError):
    """O professor tentou salvar uma versão anterior à persistida."""


def check_revision(current: EducationBase, expected: datetime | None) -> None:
    if expected is not None:
        if expected.tzinfo is not None:
            expected = expected.astimezone(UTC).replace(tzinfo=None)
        if current.updated_at != expected:
            raise MaterialConflictError(
                "O material foi alterado. Reabra a versão mais recente antes de salvar."
            )


class SQLiteEducationRepository:
    """Conexões curtas e transações para compartilhar o arquivo entre workers."""

    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS education_materials ("
                "collection TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, "
                "PRIMARY KEY (collection, id))"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def save(self, collection: str, item: EducationBase) -> None:
        """Confirma a gravação antes de retornar sucesso."""
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO education_materials (collection, id, payload) VALUES (?, ?, ?)",
                (collection, item.id, item.model_dump_json()),
            )

    def get(self, collection: str, item_id: str, model: type[Model]) -> Model | None:
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT payload FROM education_materials WHERE collection = ? AND id = ?",
                (collection, item_id),
            ).fetchone()
        return model.model_validate_json(row[0]) if row else None

    def all(self, collection: str, model: type[Model]) -> list[Model]:
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT payload FROM education_materials WHERE collection = ? ORDER BY rowid",
                (collection,),
            ).fetchall()
        return [model.model_validate_json(row[0]) for row in rows]

    def update(
        self,
        collection: str,
        item_id: str,
        model: type[Model],
        changes: dict[str, Any],
        expected_updated_at: datetime | None = None,
    ) -> Model | None:
        """Serializa leitura e atualização para preservar edições de outros workers."""
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT payload FROM education_materials WHERE collection = ? AND id = ?",
                (collection, item_id),
            ).fetchone()
            if row is None:
                return None
            current = model.model_validate_json(row[0])
            check_revision(current, expected_updated_at)
            updated = model.model_validate({**current.model_dump(), **changes})
            db.execute(
                "UPDATE education_materials SET payload = ? WHERE collection = ? AND id = ?",
                (updated.model_dump_json(), collection, item_id),
            )
            return updated

    def delete(self, collection: str, item_id: str) -> bool:
        with closing(self._connect()) as db, db:
            result = db.execute(
                "DELETE FROM education_materials WHERE collection = ? AND id = ?",
                (collection, item_id),
            )
            return result.rowcount > 0

    def counts(self) -> dict[str, int]:
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT collection, COUNT(*) FROM education_materials GROUP BY collection"
            ).fetchall()
        return dict(rows)
