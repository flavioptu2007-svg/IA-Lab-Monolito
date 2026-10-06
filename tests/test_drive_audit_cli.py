"""Testes do relatório e da CLI (sem tocar no Drive real)."""

from __future__ import annotations

from pathlib import Path

from src.drive_audit import cli, report


def _linha(path: str, *, is_dir: bool, size: int = 0, id_: str = "", name: str = "") -> dict:
    return {
        "path": path,
        "name": name or path.rsplit("/", 1)[-1],
        "id": id_,
        "size": size,
        "mime": "",
        "modified": "2026-04-20T00:00:00Z",
        "created": "",
        "is_dir": is_dir,
        "hash": "",
    }


def test_summary_conta_itens_e_espaco_recuperavel() -> None:
    rows = [_linha("a.pdf", is_dir=False, size=1048576, id_="1")]
    empty = ["P"]
    dup = [
        {
            "group_id": 1,
            "hash": "h",
            "action": "keep",
            "path": "a.pdf",
            "id": "1",
            "size": 1048576,
            "motivo": "",
        },
        {
            "group_id": 1,
            "hash": "h",
            "action": "trash",
            "path": "b.pdf",
            "id": "2",
            "size": 1048576,
            "motivo": "",
        },
    ]
    texto = report.build_summary(
        rows, empty, dup, ["doc-native"], generated_at="2026-10-06T00:00:00Z"
    )
    assert "Itens inventariados: 1" in texto
    assert "Pastas vazias: 1" in texto
    assert "Cópias marcadas para lixeira: 1" in texto
    assert "1.00 MiB" in texto
    assert "Nenhuma alteração foi feita no Drive" in texto


def test_cli_analyze_escreve_artefatos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DRIVE_AUDIT_DIR", str(tmp_path))
    rows = [
        _linha("06_Backups/prova.pdf", is_dir=False, size=10, id_="1"),
        _linha("07_Projetos/prova.pdf", is_dir=False, size=10, id_="2"),
    ]
    for row in rows:
        row["hash"] = "abc"
    # inventário já pronto para o analyze não chamar o rclone
    from src.drive_audit import inventory

    inventory.write_inventory(rows, tmp_path / "inventory.jsonl", tmp_path / "inventory.csv")
    assert cli.main(["analyze"]) == 0
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "duplicates.csv").exists()
    assert (tmp_path / "empty_folders.csv").exists()
    assert (tmp_path / "rename_plan.csv").exists()
