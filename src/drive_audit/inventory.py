"""Inventário do Drive → inventory.jsonl + inventory.csv."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
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


def crawl_incremental(
    base: Path,
    *,
    max_dirs: int,
    lsjson_fn: Callable[[str], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Crawl resumível: lista até ``max_dirs`` diretórios por chamada.

    Cada diretório é listado **sem recursão** (1 chamada de API por pasta) e as
    entradas são anexadas a ``inventory.jsonl``; o progresso (pendentes /
    concluídos) vai para ``inventory.state.json``. Permite retomar de onde
    parou, sem segurar o Drive inteiro em memória nem num único ``lsjson -R``.
    """
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    jsonl = base / "inventory.jsonl"
    state_file = base / "inventory.state.json"
    state: dict[str, Any]
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
    else:
        state = {"pending": [""], "done": []}
        jsonl.write_text("", encoding="utf-8")

    listar = lsjson_fn or (lambda remote: rclone.lsjson(remote, recursive=False))
    with jsonl.open("a", encoding="utf-8") as fh:
        for _ in range(max_dirs):
            if not state["pending"]:
                break
            path = state["pending"].pop(0)
            remote = f"{config.REMOTE}{path}" if path else config.REMOTE
            child_dirs: list[str] = []
            for entry in listar(remote):
                row = to_row(entry)
                if path:
                    row["path"] = f"{path}/{row['path']}"
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                if row["is_dir"]:
                    child_dirs.append(row["path"])
            state["done"].append(path)
            state["pending"].extend(child_dirs)

    state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    return state
