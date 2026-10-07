"""Inventário do Drive → inventory.jsonl + inventory.csv."""

from __future__ import annotations

import csv
import json
import os
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
    """Lê o jsonl deduplicando por id (mantém a primeira ocorrência).

    Inventários gerados por versões antigas do crawl podiam conter o mesmo
    arquivo duas vezes (pasta re-listada após queda); sem dedup, a análise
    tratava o arquivo como duplicata de si mesmo.
    """
    vistos: set[str] = set()
    rows: list[dict[str, Any]] = []
    with Path(jsonl_path).open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["id"] in vistos:
                continue
            vistos.add(row["id"])
            rows.append(row)
    return rows


def _salvar_estado(state_file: Path, state: dict[str, Any]) -> None:
    """Gravação atômica do estado (um processo morto não corrompe o JSON)."""
    tmp = state_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, state_file)


def crawl_incremental(
    base: Path,
    *,
    max_dirs: int,
    lsjson_fn: Callable[[str, bool], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Crawl resumível: lista até ``max_dirs`` pastas de topo por chamada.

    A raiz é listada uma vez (sem recursão) para descobrir as pastas de topo;
    cada pasta de topo é então listada **recursivamente** (``--fast-list``). O
    estado é gravado **após cada pasta** (atômico), então uma queda no meio da
    execução não perde progresso nem re-lista o que já foi listado. Entradas
    repetidas por id são descartadas na coleta (``seen`` no estado).
    """
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    jsonl = base / "inventory.jsonl"
    state_file = base / "inventory.state.json"
    state: dict[str, Any]
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
    else:
        state = {"pending": [], "done": [], "seeded": False, "seen": []}
        jsonl.write_text("", encoding="utf-8")
    state.setdefault("seen", [])
    vistos: set[str] = set(state["seen"])

    def escrever(fh: Any, row: dict[str, Any]) -> None:
        if row["id"] in vistos:
            return
        vistos.add(row["id"])
        state["seen"].append(row["id"])
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    listar = lsjson_fn or (lambda remote, recursive: rclone.lsjson(remote, recursive=recursive))
    with jsonl.open("a", encoding="utf-8") as fh:
        if not state.get("seeded"):
            for entry in listar(config.REMOTE, False):
                row = to_row(entry)
                escrever(fh, row)
                if row["is_dir"]:
                    state["pending"].append(row["path"])
            state["seeded"] = True
            fh.flush()
            _salvar_estado(state_file, state)
        for _ in range(max_dirs):
            if not state["pending"]:
                break
            path = state["pending"].pop(0)
            for entry in listar(f"{config.REMOTE}{path}", True):
                row = to_row(entry)
                row["path"] = f"{path}/{row['path']}"
                escrever(fh, row)
            state["done"].append(path)
            fh.flush()
            _salvar_estado(state_file, state)

    _salvar_estado(state_file, state)
    return state
