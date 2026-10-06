"""Testes da coleta de hashes com cache."""

from __future__ import annotations

from pathlib import Path

from src.drive_audit import hashing


def _arquivo(id_: str, path: str, *, hash_: str = "", modified: str = "t1", size: int = 5) -> dict:
    return {
        "path": path,
        "name": path,
        "id": id_,
        "size": size,
        "mime": "",
        "modified": modified,
        "created": "",
        "is_dir": False,
        "hash": hash_,
    }


def test_usa_hash_do_inventario() -> None:
    rows = [_arquivo("1", "a.pdf", hash_="abc")]
    hashes, faltando = hashing.collect_hashes(rows, {})
    assert hashes == {"1": "abc"}
    assert faltando == []


def test_arquivo_sem_hash_entra_em_faltando() -> None:
    rows = [_arquivo("2", "doc", hash_="")]
    hashes, faltando = hashing.collect_hashes(rows, {})
    assert hashes == {}
    assert faltando == ["doc"]


def test_cache_evita_recalculo() -> None:
    rows = [_arquivo("1", "a.pdf", hash_="")]
    cache = {"1": {"mtime": "t1", "hash": "cached"}}
    hashes, faltando = hashing.collect_hashes(rows, cache)
    assert hashes == {"1": "cached"}
    assert faltando == []


def test_cache_invalida_se_mtime_muda() -> None:
    rows = [_arquivo("1", "a.pdf", hash_="novo", modified="t2")]
    cache = {"1": {"mtime": "t1", "hash": "antigo"}}
    hashes, _ = hashing.collect_hashes(rows, cache)
    assert hashes == {"1": "novo"}
    assert cache["1"]["hash"] == "novo"


def test_fallback_hashsum_quando_fornecido() -> None:
    rows = [_arquivo("3", "b.pdf", hash_="")]
    hashes, _ = hashing.collect_hashes(rows, {}, hashsum_fn=lambda _p: "deadbeef  b.pdf")
    assert hashes == {"3": "deadbeef"}


def test_save_e_load_cache(tmp_path: Path) -> None:
    caminho = tmp_path / "hash_cache.json"
    hashing.save_cache({"1": {"mtime": "t", "hash": "h"}}, caminho)
    assert hashing.load_cache(caminho) == {"1": {"mtime": "t", "hash": "h"}}
