"""Análises puras sobre o inventário: pastas vazias e duplicatas por hash."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any

BACKUP_MARKERS = ("backup", "backups", "backuplinux", "backupdocumentos", "avastcleanup", "bkp")
_STANDARD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[A-Za-z]+_[A-Za-z0-9]+_v\d{2}(\.[A-Za-z0-9]+)?$")
_NOISE_RE = re.compile(r"(c[oó]pia de|copy of|\(\d+\)|-20\d{6}t\d{6}z)", re.IGNORECASE)


def _parent(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def find_empty_folders(rows: list[dict[str, Any]]) -> list[str]:
    """Pastas sem arquivos e sem subpastas com conteúdo (vazio transitivo)."""
    dirs = {row["path"] for row in rows if row["is_dir"]}
    children: dict[str, list[str]] = {d: [] for d in dirs}
    file_count: dict[str, int] = defaultdict(int)
    for d in dirs:
        parent = _parent(d)
        if parent in children:
            children[parent].append(d)
    for row in rows:
        if not row["is_dir"]:
            file_count[_parent(row["path"])] += 1
    empty: set[str] = set()
    for d in sorted(dirs, key=lambda p: p.count("/"), reverse=True):
        if file_count.get(d, 0) == 0 and all(c in empty for c in children.get(d, [])):
            empty.add(d)
    return sorted(empty)


def _is_backup_path(path: str) -> bool:
    return any(
        any(marker in part.lower() for marker in BACKUP_MARKERS) for part in path.split("/")[:-1]
    )


def _mtime_key(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def choose_keep(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Escolhe a cópia a manter (menor chave = melhor), na ordem da spec."""

    def key(row: dict[str, Any]) -> tuple[bool, bool, bool, int, float]:
        name = row["name"]
        return (
            _is_backup_path(row["path"]),
            not bool(_STANDARD_RE.match(name)),
            bool(_NOISE_RE.search(name)),
            len(row["path"]),
            -_mtime_key(row["modified"]),
        )

    return min(items, key=key)


def group_duplicates(rows: list[dict[str, Any]], hashes: dict[str, str]) -> list[dict[str, Any]]:
    """Agrupa por hash e decide keep/trash. Só arquivos hasháveis e size>0."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["is_dir"] or int(row.get("size", 0)) <= 0:
            continue
        digest = hashes.get(row["id"])
        if digest:
            groups[digest].append(row)
    out: list[dict[str, Any]] = []
    group_id = 0
    for digest in sorted(groups):
        items = groups[digest]
        if len(items) < 2:
            continue
        group_id += 1
        keep = choose_keep(items)
        for row in sorted(items, key=lambda r: r["path"]):
            e_keep = row is keep
            out.append(
                {
                    "group_id": group_id,
                    "hash": digest,
                    "action": "keep" if e_keep else "trash",
                    "path": row["path"],
                    "id": row["id"],
                    "size": row["size"],
                    "motivo": (
                        "melhor cópia: path fora de backup, nome limpo e mais curto"
                        if e_keep
                        else "duplicata de conteúdo; enviar à lixeira"
                    ),
                }
            )
    return out
