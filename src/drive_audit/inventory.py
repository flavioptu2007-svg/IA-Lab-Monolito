"""Inventário do Drive → inventory.jsonl + inventory.csv."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.drive_audit import config, rclone

CSV_FIELDS: tuple[str, ...] = (
    "path",
    "name",
    "id",
    "size",
    "mime",
    "modified",
    "created",
    "is_dir",
    "hash",
)


def to_row(entry: dict[str, Any]) -> dict[str, Any]:
    """Converte um item do lsjson na linha estável do inventário."""
    hashes = entry.get("Hashes") or {}
    # rclone emite a chave minúscula ("md5") no lsjson; aceita as duas formas.
    digest = hashes.get("MD5") or hashes.get("md5") or next(iter(hashes.values()), "")
    return {
        "path": entry.get("Path", ""),
        "name": entry.get("Name", ""),
        "id": entry.get("ID", ""),
        "size": entry.get("Size", 0),
        "mime": entry.get("MimeType", ""),
        "modified": entry.get("ModTime", ""),
        # O lsjson não expõe createdTime; fica vazio e é documentado no summary.
        "created": "",
        "is_dir": bool(entry.get("IsDir", False)),
        "hash": digest,
    }


def build_inventory() -> list[dict[str, Any]]:
    return rclone.lsjson(config.REMOTE, recursive=True)


def write_inventory(rows: list[dict[str, Any]], jsonl_path: Path, csv_path: Path) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        writer.writerows(rows)


def load_inventory(jsonl_path: Path) -> list[dict[str, Any]]:
    with Path(jsonl_path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
