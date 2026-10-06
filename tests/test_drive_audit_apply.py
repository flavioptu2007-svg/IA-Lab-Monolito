"""Testes do apply por lote: dry-run não toca no Drive, apply usa deletefile."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from src.drive_audit import apply_batch


def _escrever_duplicates(tmp_path: Path) -> Path:
    caminho = tmp_path / "duplicates.csv"
    with caminho.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["group_id", "hash", "action", "path", "id", "size", "motivo"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "group_id": 1,
                "hash": "h",
                "action": "keep",
                "path": "bom.pdf",
                "id": "1",
                "size": 1,
                "motivo": "",
            }
        )
        writer.writerow(
            {
                "group_id": 1,
                "hash": "h",
                "action": "trash",
                "path": "ruim.pdf",
                "id": "2",
                "size": 1,
                "motivo": "",
            }
        )
    return caminho


def test_load_actions_so_trash(tmp_path: Path) -> None:
    actions = apply_batch.load_actions(_escrever_duplicates(tmp_path))
    assert [a["id"] for a in actions] == ["2"]


def test_dry_run_nao_chama_rclone(tmp_path: Path) -> None:
    chamadas: list[list[str]] = []
    results = apply_batch.apply_actions(
        [{"id": "2", "path": "ruim.pdf"}],
        dry_run=True,
        log_path=tmp_path / "logs" / "apply.jsonl",
        run_fn=lambda args: chamadas.append(args) or "",
    )
    assert chamadas == []
    assert results[0]["resultado"] == "dry-run"
    assert (tmp_path / "logs" / "apply.jsonl").exists()


def test_apply_real_envia_para_lixeira(tmp_path: Path) -> None:
    chamadas: list[list[str]] = []
    results = apply_batch.apply_actions(
        [{"id": "2", "path": "ruim.pdf"}],
        dry_run=False,
        log_path=tmp_path / "apply.jsonl",
        run_fn=lambda args: chamadas.append(args) or "",
        now=lambda: datetime(2026, 10, 6, tzinfo=timezone.utc),
    )
    assert chamadas == [["deletefile", "gdrive:ruim.pdf", "--drive-use-trash=true"]]
    assert results[0]["resultado"] == "ok"
    assert results[0]["timestamp"] == "2026-10-06T00:00:00+00:00"
