"""Instrumento da Q5: registro do tempo manual e comparação fail-closed.

Sem medição humana o módulo não compara nem afirma ganho; com as duas pontas
registradas, compara medianas — a montagem medida no log contra os minutos
cronometrados à mão.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from docx import Document

from src.historia_gen import formulario, tempo

FORMULARIO_DOCX = Path(__file__).resolve().parents[1] / "docs/historia_gen/q5-formulario.docx"


def _log(tmp_path: Path, duracoes: list[float]) -> Path:
    caminho = tmp_path / "registros.jsonl"
    linhas = [
        json.dumps({"evento": "geracao", "tema": "Roma", "duracao_s": duracao}, ensure_ascii=False)
        for duracao in duracoes
    ]
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def test_registrar_cria_csv_com_cabecalho_e_le(tmp_path: Path) -> None:
    caminho = tmp_path / "q5.csv"
    tempo.registrar(
        caminho,
        tema="Roma Antiga",
        ano="6º ano EF",
        minutos=65,
        quem="Prof. X",
        data="2026-11-03",
    )
    tempo.registrar(caminho, tema="Revolução Industrial", ano="8º ano EF", minutos=80)
    medicoes = tempo.ler(caminho)
    assert [(m.tema, m.minutos) for m in medicoes] == [
        ("Roma Antiga", 65.0),
        ("Revolução Industrial", 80.0),
    ]
    assert caminho.read_text(encoding="utf-8").splitlines()[0] == ",".join(tempo.COLUNAS)


def test_minutos_invalidos_recusa(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="minutos"):
        tempo.registrar(tmp_path / "q5.csv", tema="Roma", ano="6º ano EF", minutos=0)


def test_csv_ausente_nao_vira_linha_de_base(tmp_path: Path) -> None:
    assert tempo.ler(tmp_path / "nao-existe.csv") == []
    with pytest.raises(tempo.SemLinhaDeBase, match="nenhuma medição manual"):
        tempo.comparar(tmp_path / "nao-existe.csv", _log(tmp_path, [0.2]))


def test_sem_geracao_medida_recusa(tmp_path: Path) -> None:
    csv = tmp_path / "q5.csv"
    tempo.registrar(csv, tema="Roma", ano="6º ano EF", minutos=60)
    registros = tmp_path / "registros.jsonl"
    registros.write_text(json.dumps({"evento": "aprovado"}) + "\n", encoding="utf-8")
    with pytest.raises(tempo.SemLinhaDeBase, match="duracao_s"):
        tempo.comparar(csv, registros)


def test_formulario_tem_uma_pagina_por_via(tmp_path: Path) -> None:
    """Duas medições = duas folhas: a via não pode transbordar para a página seguinte."""
    destino = formulario.gerar_formulario(tmp_path / "q5-formulario.docx", vias=2)
    doc = Document(destino)
    assert doc.element.xml.count('w:type="page"') == 1
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "Formulário 1 de 2" in texto
    assert "Formulário 2 de 2" in texto
    # a regra do template vale aqui também: nada no cabeçalho
    assert all(p.text.strip() == "" for p in doc.sections[0].header.paragraphs)


def test_formulario_tem_os_campos_e_as_etapas_do_protocolo(tmp_path: Path) -> None:
    destino = formulario.gerar_formulario(tmp_path / "q5-formulario.docx", vias=1)
    doc = Document(destino)
    texto = "\n".join(p.text for p in doc.paragraphs)
    for campo in ("Professor(a)", "Data (dia/mês/ano)", "Ano/série e turma", "Modo:", "Tema ou"):
        assert campo in texto
    # o total é o único número que vira linha de base
    tabela = doc.tables[0]
    etapas = [linha.cells[1].text for linha in tabela.rows[1:]]
    assert etapas[:-1] == list(formulario.ETAPAS)
    assert "Total" in etapas[-1]
    assert "tempo-manual" in texto  # como o papel vira medição no CSV
    assert "retrabalho" in texto.lower()


def _texto_e_celulas(doc: Any) -> tuple[list[str], list[list[str]]]:
    paragrafos = [p.text for p in doc.paragraphs]
    celulas = [[c.text for c in linha.cells] for tabela in doc.tables for linha in tabela.rows]
    return paragrafos, celulas


def test_formulario_versionado_esta_atualizado(tmp_path: Path) -> None:
    """O .docx versionado é derivado: se o gerador muda, o arquivo muda junto."""
    novo = formulario.gerar_formulario(tmp_path / "q5.docx", vias=formulario.VIAS_PADRAO)
    assert _texto_e_celulas(Document(novo)) == _texto_e_celulas(Document(FORMULARIO_DOCX))


def test_formulario_recusa_zero_vias(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="vias"):
        formulario.gerar_formulario(tmp_path / "q5.docx", vias=0)


def test_comparar_usa_medianas_dos_dois_lados(tmp_path: Path) -> None:
    csv = tmp_path / "q5.csv"
    tempo.registrar(csv, tema="Roma", ano="6º ano EF", minutos=60)
    tempo.registrar(csv, tema="Revolução Industrial", ano="8º ano EF", minutos=80)
    dados = tempo.comparar(csv, _log(tmp_path, [0.18, 0.22, 0.20]))
    assert dados.medicoes == 2
    assert dados.mediana_min == 70
    assert dados.montagens == 3
    assert dados.mediana_montagem_s == pytest.approx(0.2)
    assert dados.razao == pytest.approx(70 * 60 / 0.2)
