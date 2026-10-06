"""Testes do crawl incremental e retomável do inventário."""

from __future__ import annotations

from pathlib import Path

from src.drive_audit import inventory


def _fake_lsjson(remote: str, recursive: bool) -> list[dict]:
    if remote == "gdrive:" and not recursive:
        return [
            {"Path": "a.txt", "Name": "a.txt", "ID": "1", "Size": 1, "IsDir": False},
            {"Path": "Sub", "Name": "Sub", "ID": "2", "Size": -1, "IsDir": True},
        ]
    if remote == "gdrive:Sub" and recursive:
        return [{"Path": "b.txt", "Name": "b.txt", "ID": "3", "Size": 2, "IsDir": False}]
    raise AssertionError(f"chamada inesperada: {remote} recursive={recursive}")


def test_crawl_incremental_pausa_e_retoma(tmp_path: Path) -> None:
    state = inventory.crawl_incremental(tmp_path, max_dirs=0, lsjson_fn=_fake_lsjson)
    assert state["pending"] == ["Sub"]
    assert state["done"] == []

    state = inventory.crawl_incremental(tmp_path, max_dirs=10, lsjson_fn=_fake_lsjson)
    assert state["pending"] == []
    assert state["done"] == ["Sub"]

    rows = inventory.load_inventory(tmp_path / "inventory.jsonl")
    assert sorted(r["path"] for r in rows) == ["Sub", "Sub/b.txt", "a.txt"]


def test_crawl_incremental_reinicia_jsonl_em_base_nova(tmp_path: Path) -> None:
    inventory.crawl_incremental(tmp_path, max_dirs=10, lsjson_fn=_fake_lsjson)
    rows = inventory.load_inventory(tmp_path / "inventory.jsonl")
    assert len(rows) == 3
