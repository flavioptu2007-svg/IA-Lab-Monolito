"""Testes do apply por lote: dry-run não toca no Drive, apply usa deletefile."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.drive_audit import apply_batch, cli


def _escrever_duplicates(tmp_path: Path, nome: str = "duplicates.csv") -> Path:
    caminho = tmp_path / nome
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


def _cmd_apply_com_fakes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    capturado: dict[str, object] = {}

    def fake_load(caminho: Path) -> list[dict[str, str]]:
        capturado["caminho"] = Path(caminho)
        return [{"id": "2", "path": "ruim.pdf"}]

    def fake_apply(
        actions: list[dict[str, str]], *, dry_run: bool, log_path: Path
    ) -> list[dict[str, object]]:
        capturado["dry_run"] = dry_run
        return [{"resultado": "dry-run"}]

    monkeypatch.setattr(cli.config, "ensure_workdir", lambda: tmp_path)
    monkeypatch.setattr(cli.apply_batch, "load_actions", fake_load)
    monkeypatch.setattr(cli.apply_batch, "apply_actions", fake_apply)
    return capturado


def test_cmd_apply_usa_o_csv_do_lote_indicado(tmp_path: Path, monkeypatch) -> None:
    lote = _escrever_duplicates(tmp_path, nome="lote1_backups.csv")
    capturado = _cmd_apply_com_fakes(tmp_path, monkeypatch)

    rc = cli.cmd_apply(argparse.Namespace(confirm=False, lote=str(lote)))

    assert rc == 0
    assert capturado["caminho"] == lote
    assert capturado["dry_run"] is True


def test_cmd_apply_sem_lote_cai_no_duplicates_do_workdir(tmp_path: Path, monkeypatch) -> None:
    capturado = _cmd_apply_com_fakes(tmp_path, monkeypatch)

    rc = cli.cmd_apply(argparse.Namespace(confirm=False, lote=None))

    assert rc == 0
    assert capturado["caminho"] == tmp_path / "duplicates.csv"


def test_apply_grava_o_log_incrementalmente(tmp_path: Path) -> None:
    log = tmp_path / "apply.jsonl"
    linhas_vistas: list[int] = []

    def run_fn(args: list[str]) -> str:
        if log.exists():
            linhas_vistas.append(len(log.read_text(encoding="utf-8").strip().splitlines()))
        else:
            linhas_vistas.append(0)
        return ""

    apply_batch.apply_actions(
        [{"id": "1", "path": "a.pdf"}, {"id": "2", "path": "b.pdf"}],
        dry_run=False,
        log_path=log,
        run_fn=run_fn,
    )

    # Ao processar a 2ª ação, a 1ª já deve estar gravada (progresso visível
    # e retomável mesmo se o processo morrer no meio).
    assert linhas_vistas == [0, 1]
