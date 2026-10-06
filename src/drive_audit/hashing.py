"""Coleta de hashes MD5 (do inventário) com cache local em disco."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.drive_audit import config


def load_cache(path: Path) -> dict[str, dict[str, Any]]:
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, dict[str, Any]], path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_hashes(
    rows: list[dict[str, Any]],
    cache: dict[str, dict[str, Any]],
    *,
    hashsum_fn: Callable[[str], str] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Devolve (id → md5, paths sem hash).

    Usa o hash já presente no inventário; ``hashsum_fn`` é o fallback lento
    (desligado por padrão) para arquivos sem MD5 nos metadados.
    """
    result: dict[str, str] = {}
    missing: list[str] = []
    for row in rows:
        if row["is_dir"] or int(row.get("size", 0)) <= 0:
            continue
        cached = cache.get(row["id"])
        if cached and cached.get("mtime") == row["modified"]:
            digest = str(cached.get("hash") or "")
        else:
            digest = str(row.get("hash") or "")
            if not digest and hashsum_fn is not None:
                parts = hashsum_fn(f"{config.REMOTE}{row['path']}").split()
                digest = parts[0] if parts and parts[0] != "UNSUPPORTED" else ""
            cache[row["id"]] = {"mtime": row["modified"], "hash": digest}
        if digest:
            result[row["id"]] = digest
        else:
            missing.append(row["path"])
    return result, missing
