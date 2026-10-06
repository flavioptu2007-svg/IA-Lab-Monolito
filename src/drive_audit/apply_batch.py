"""Dry-run e apply de um lote aprovado (trash de duplicatas)."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.drive_audit import config, rclone


def load_actions(duplicates_csv: Path) -> list[dict[str, Any]]:
    with Path(duplicates_csv).open(encoding="utf-8", newline="") as fh:
        return [row for row in csv.DictReader(fh) if row["action"] == "trash"]


def apply_actions(
    actions: list[dict[str, Any]],
    *,
    dry_run: bool = True,
    log_path: Path,
    run_fn: Callable[[list[str]], str] = rclone.run_rclone,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> list[dict[str, Any]]:
    """Aplica (ou simula) cada ação; sempre anexa o resultado ao log."""
    results: list[dict[str, Any]] = []
    for row in actions:
        remote = f"{config.REMOTE}{row['path']}"
        if dry_run:
            resultado = "dry-run"
        else:
            try:
                # deletefile + flag explícita: garante a lixeira, nunca exclusão permanente.
                run_fn(["deletefile", remote, "--drive-use-trash=true"])
                resultado = "ok"
            except rclone.RcloneError as exc:  # pragma: no cover - caminho de erro real
                resultado = f"erro: {exc}"
        results.append(
            {
                "timestamp": now().isoformat(),
                "id": row["id"],
                "path": row["path"],
                "acao": "trash",
                "resultado": resultado,
            }
        )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        for entry in results:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return results
