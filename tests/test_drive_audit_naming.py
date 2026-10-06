"""Testes das regras de nomenclatura arquivística."""

from __future__ import annotations

from src.drive_audit.naming import (
    build_assunto,
    extract_date,
    infer_tipo,
    is_already_standard,
    suggest_name,
)


def test_extrai_data_de_nome_iso() -> None:
    assert extract_date("2026-03-15 prova.pdf") == ("2026-03-15", "nome")


def test_extrai_data_de_nome_compacto() -> None:
    assert extract_date("20260420_plano.docx") == ("2026-04-20", "nome")


def test_extrai_data_de_dd_mm_aaaa() -> None:
    assert extract_date("15-03-2026 prova.pdf") == ("2026-03-15", "nome")


def test_extrai_data_fallback_modtime() -> None:
    data, origem = extract_date("prova.pdf", "2026-09-30T12:00:00Z", "2026-01-01T00:00:00Z")
    assert (data, origem) == ("2026-09-30", "modifiedTime")


def test_infer_tipo_por_palavra_chave() -> None:
    assert infer_tipo("Plano de Aula março.docx", "x/Plano de Aula março.docx") == "Plano"


def test_infer_tipo_backup_vence_pelo_path() -> None:
    assert infer_tipo("aula.docx", "06_Backups/aula.docx") == "Backup"


def test_infer_tipo_desconhecido_vira_outro() -> None:
    assert infer_tipo("zzz.bin", "zzz.bin") == "Outro"


def test_build_assunto_normaliza_e_remove_ruido() -> None:
    assert build_assunto("Cópia de Prova Bimestral (1).pdf") == "ProvaBimestral"


def test_is_already_standard() -> None:
    assert is_already_standard("2026-04-20_Plano_Abril2026_v01.pdf") is True
    assert is_already_standard("Prova Bimestral.pdf") is False


def test_suggest_name_formato_completo() -> None:
    sugestao = suggest_name(
        "2026-04-20_Prova Bimestral (1).pdf",
        "07_Projetos/2026-04-20_Prova Bimestral (1).pdf",
        False,
        "2026-04-21T00:00:00Z",
    )
    assert sugestao is not None
    assert sugestao.suggested == "2026-04-20_Avaliacao_ProvaBimestral_v02.pdf"
    assert sugestao.confianca == "alta"


def test_suggest_name_ja_no_padrao_retorna_none() -> None:
    assert suggest_name("2026-04-20_Plano_Abril2026_v01.pdf", "x", False) is None


def test_suggest_name_pasta_nao_tem_extensao() -> None:
    # "2026" no nome É um padrão de data para a spec, então vence o modifiedTime
    # (vira 2026-01-01 com origem "nome-ano" e confiança média).
    sugestao = suggest_name("Abril de 2026", "Abril de 2026", True, "2026-04-05T00:00:00Z")
    assert sugestao is not None
    assert sugestao.suggested == "2026-01-01_Outro_AbrilDe2026_v01"
    assert sugestao.confianca == "media"
