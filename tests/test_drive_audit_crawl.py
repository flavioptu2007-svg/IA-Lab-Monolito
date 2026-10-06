"""Testes do crawl incremental e retomável do inventário."""

from __future__ import annotations

from pathlib import Path

from src.drive_audit import inventory


def _fake_lsjson(remote: str) -> list[dict]:
    if remote == "gdrive:":
        return [
            {"Path": "a.txt", "Name": "a.txt", "ID": "1", "Size": 1, "IsDir": False},
            {"Path": "Sub", "Name": "Sub", "ID": "2", "Size": -1, "IsDir": True},
        ]
    if remote == "gdrive:Sub":
        return [{"Path": "b.txt", "Name": "b.txt", "ID": "3", "Size": 2, "IsDir": False}]
    raise AssertionError(f"chamada inesperada: {remote}")


def test_crawl_incremental_pausa_e_retoma(tmp_path: Path) -> None:
    state = inventory.crawl_incremental(tmp_path, max_dirs=1, lsjson_fn=_fake_lsjson)
    assert state["done"] == [""]
    assert state["pending"] == ["Sub"]

    state = inventory.crawl_incremental(tmp_path, max_dirs=10, lsjson_fn=_fake_lsjson)
    assert state["pending"] == []

    rows = inventory.load_inventory(tmp_path / "inventory.jsonl")
    assert sorted(r["path"] for r in rows) == ["Sub", "Sub/b.txt", "a.txt"]


def test_crawl_incremental_reinicia_jsonl_em_base_nova(tmp_path: Path) -> None:
    inventory.crawl_incremental(tmp_path, max_dirs=10, lsjson_fn=_fake_lsjson)
    rows = inventory.load_inventory(tmp_path / "inventory.jsonl")
    assert len(rows) == 3
