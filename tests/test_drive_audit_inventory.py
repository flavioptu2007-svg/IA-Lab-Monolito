"""Testes do inventário (rclone mockado)."""

from __future__ import annotations

from pathlib import Path

from src.drive_audit import inventory


def test_to_row_normaliza_chaves_e_hash() -> None:
    entry = {
        "Path": "a/b.pdf",
        "Name": "b.pdf",
        "ID": "42",
        "Size": 10,
        "MimeType": "application/pdf",
        "ModTime": "2026-04-01T10:00:00Z",
        "IsDir": False,
        "Hashes": {"md5": "abc123"},
    }
    row = inventory.to_row(entry)
    assert row["path"] == "a/b.pdf"
    assert row["id"] == "42"
    assert row["hash"] == "abc123"
    assert row["is_dir"] is False


def test_to_row_pasta_sem_hash() -> None:
    row = inventory.to_row({"Path": "A", "Name": "A", "IsDir": True})
    assert row["is_dir"] is True
    assert row["hash"] == ""


def test_write_e_load_inventory_roundtrip(tmp_path: Path) -> None:
    rows = [inventory.to_row({"Path": "a.pdf", "Name": "a.pdf", "ID": "1", "Size": 1})]
    jsonl = tmp_path / "inventory.jsonl"
    csv_path = tmp_path / "inventory.csv"
    inventory.write_inventory(rows, jsonl, csv_path)
    assert jsonl.exists() and csv_path.exists()
    assert inventory.load_inventory(jsonl) == rows
