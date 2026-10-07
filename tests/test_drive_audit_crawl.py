"""Testes do crawl incremental e retomável do inventário."""

from __future__ import annotations

import json
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


def test_crawl_salva_progresso_antes_de_cada_pasta(tmp_path: Path) -> None:
    def lsjson_morre_na_segunda(remote: str, recursive: bool) -> list[dict]:
        if remote == "gdrive:":
            return [
                {"Path": "P1", "Name": "P1", "ID": "p1", "Size": -1, "IsDir": True},
                {"Path": "P2", "Name": "P2", "ID": "p2", "Size": -1, "IsDir": True},
            ]
        if remote == "gdrive:P1":
            return [{"Path": "f1.txt", "Name": "f1.txt", "ID": "f1", "Size": 1, "IsDir": False}]
        raise RuntimeError("processo morreu listando P2")

    try:
        inventory.crawl_incremental(tmp_path, max_dirs=10, lsjson_fn=lsjson_morre_na_segunda)
    except RuntimeError:
        pass

    # O progresso de P1 precisa estar EM DISCO (estado + linhas), mesmo com o
    # processo morto no meio — foi a ausência disso que duplicou o inventário real.
    state = json.loads((tmp_path / "inventory.state.json").read_text(encoding="utf-8"))
    assert state["done"] == ["P1"]
    assert state["pending"] == ["P2"]
    linhas = (tmp_path / "inventory.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert any('"id": "f1"' in linha or '"id":"f1"' in linha for linha in linhas)

    # Retomada: P1 NÃO pode ser listada de novo (era isso que duplicava o jsonl).
    def lsjson_so_p2(remote: str, recursive: bool) -> list[dict]:
        if remote == "gdrive:P2":
            return [{"Path": "f2.txt", "Name": "f2.txt", "ID": "f2", "Size": 2, "IsDir": False}]
        raise AssertionError(f"re-listagem indevida: {remote}")

    state = inventory.crawl_incremental(tmp_path, max_dirs=10, lsjson_fn=lsjson_so_p2)
    assert state["done"] == ["P1", "P2"]
    assert state["pending"] == []


def test_crawl_nao_repete_arquivo_com_mesmo_id(tmp_path: Path) -> None:
    def lsjson_duplicado(remote: str, recursive: bool) -> list[dict]:
        if remote == "gdrive:":
            return [
                {"Path": "P1", "Name": "P1", "ID": "p1", "Size": -1, "IsDir": True},
                {"Path": "P2", "Name": "P2", "ID": "p2", "Size": -1, "IsDir": True},
            ]
        if remote == "gdrive:P1":
            return [{"Path": "x.pdf", "Name": "x.pdf", "ID": "x1", "Size": 5, "IsDir": False}]
        if remote == "gdrive:P2":  # mesmo arquivo re-listado (bug do crawl antigo)
            return [{"Path": "x.pdf", "Name": "x.pdf", "ID": "x1", "Size": 5, "IsDir": False}]
        raise AssertionError(remote)

    inventory.crawl_incremental(tmp_path, max_dirs=10, lsjson_fn=lsjson_duplicado)
    rows = inventory.load_inventory(tmp_path / "inventory.jsonl")
    assert [r["id"] for r in rows].count("x1") == 1


def test_load_inventory_deduplica_por_id(tmp_path: Path) -> None:
    jsonl = tmp_path / "inventory.jsonl"
    jsonl.write_text(
        json.dumps({"path": "a.pdf", "id": "x"})
        + "\n"
        + json.dumps({"path": "a.pdf", "id": "x"})
        + "\n"
        + json.dumps({"path": "b.pdf", "id": "y"})
        + "\n",
        encoding="utf-8",
    )
    rows = inventory.load_inventory(jsonl)
    assert [r["id"] for r in rows] == ["x", "y"]
