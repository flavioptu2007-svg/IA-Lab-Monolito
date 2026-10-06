"""Testes das análises puras: pastas vazias e duplicatas."""

from __future__ import annotations

from src.drive_audit.analysis import choose_keep, find_empty_folders, group_duplicates


def _linha(path: str, *, is_dir: bool, size: int = 0, id_: str = "", modified: str = "") -> dict:
    return {
        "path": path,
        "name": path.rsplit("/", 1)[-1],
        "id": id_,
        "size": size,
        "mime": "",
        "modified": modified,
        "created": "",
        "is_dir": is_dir,
        "hash": "",
    }


def test_pastas_vazias_sao_transitivas() -> None:
    rows = [
        _linha("A", is_dir=True),
        _linha("A/B", is_dir=True),
        _linha("C", is_dir=True),
        _linha("D", is_dir=True),
        _linha("D/f.txt", is_dir=False, size=3),
    ]
    assert find_empty_folders(rows) == ["A", "A/B", "C"]


def test_pasta_com_arquivo_nao_e_vazia() -> None:
    rows = [_linha("D", is_dir=True), _linha("D/f.txt", is_dir=False, size=1)]
    assert find_empty_folders(rows) == []


def test_duplicatas_ignoram_pastas_e_arquivos_vazios() -> None:
    rows = [
        _linha("A", is_dir=True, id_="d"),
        _linha("A/x.bin", is_dir=False, size=0, id_="z"),
    ]
    assert group_duplicates(rows, {"d": "hash", "z": "hash2"}) == []


def test_duplicatas_mantem_path_limpo_e_mandam_backup_para_lixeira() -> None:
    rows = [
        _linha(
            "06_Backups/prova.pdf",
            is_dir=False,
            size=10,
            id_="1",
            modified="2026-08-01T00:00:00Z",
        ),
        _linha(
            "07_Projetos/2026-04-20_Avaliacao_Prova_v01.pdf",
            is_dir=False,
            size=10,
            id_="2",
            modified="2026-04-01T00:00:00Z",
        ),
    ]
    resultado = group_duplicates(rows, {"1": "abc", "2": "abc"})
    por_id = {linha["id"]: linha for linha in resultado}
    assert por_id["2"]["action"] == "keep"
    assert por_id["1"]["action"] == "trash"
    assert {linha["group_id"] for linha in resultado} == {1}


def test_choose_keep_usa_mtime_mais_recente_como_desempate() -> None:
    antigo = _linha("a/x.pdf", is_dir=False, id_="a", modified="2026-01-01T00:00:00Z")
    novo = _linha("b/x.pdf", is_dir=False, id_="b", modified="2026-09-01T00:00:00Z")
    assert choose_keep([antigo, novo])["id"] == "b"
