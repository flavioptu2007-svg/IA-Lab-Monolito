"""Testes da normalização de texto usada nos nomes arquivísticos."""

from __future__ import annotations

from src.drive_audit.textutil import normalize_ascii, strip_noise, to_title_ascii


def test_normalize_ascii_remove_acentos() -> None:
    assert normalize_ascii("Educação Básica") == "Educacao Basica"


def test_strip_noise_remove_prefixo_copia() -> None:
    assert strip_noise("Cópia de Prova Bimestral.docx") == "Prova Bimestral.docx"


def test_strip_noise_remove_sufixo_numerado() -> None:
    assert strip_noise("Prova Bimestral (1).pdf") == "Prova Bimestral.pdf"


def test_strip_noise_remove_timestamp_de_export_do_drive() -> None:
    assert strip_noise("AMOSTRAS CAÇA-20250707T021524Z-1-001.zip") == "AMOSTRAS CAÇA.zip"


def test_to_title_ascii_junta_palavras() -> None:
    assert to_title_ascii("prova bimestral de história") == "ProvaBimestralDeHistoria"
