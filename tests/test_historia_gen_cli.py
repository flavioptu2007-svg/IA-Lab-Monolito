"""Testes do CLI: --help de todos os subcomandos; catalogo-validar sobre o
catálogo versionado (passa, com a revisão registrada); catalogo-conferir e
tempo-manual; montar com catálogo aprovado de fixture (gera arquivos + log) e
com código inválido (recusa, sem arquivo); verificar; finalizar.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from docx import Document

from src.historia_gen.__main__ import main
from src.historia_gen.catalogo.carregar import carregar_catalogo
from src.historia_gen.entrada import carregar_entrada, validar_atividade
from src.historia_gen.template import MARCA_RASCUNHO
from tests.historia_gen_fixtures import (
    CATALOGO_VERSIONADO,
    atividade_fixture,
    catalogo_fixture,
)

EXEMPLO = Path(__file__).resolve().parents[1] / "src/historia_gen/exemplos/atividade-exemplo.json"


def test_help_de_todos_os_subcomandos(capsys: Any) -> None:
    import pytest

    subcomandos = (
        "montar",
        "finalizar",
        "verificar",
        "catalogo-validar",
        "catalogo-extrair",
        "conferencia-docx",
        "catalogo-conferir",
        "tempo-manual",
    )
    for comando in subcomandos:
        with pytest.raises(SystemExit) as saida:
            main([comando, "--help"])
        assert saida.value.code == 0
        texto = capsys.readouterr().out
        assert "uso" in texto.lower() or "usage" in texto.lower()


def test_catalogo_validar_passa_no_versionado_com_revisao_registrada(capsys: Any) -> None:
    assert main(["catalogo-validar"]) == 0
    saida = capsys.readouterr().out
    assert "97 habilidades" in saida
    assert "integridade: MD5 e SHA-256 conferem" in saida
    assert "revisão: aprovada" in saida
    assert "revisão manual PENDENTE" not in saida


def test_catalogo_validar_falha_com_pdf_ausente(tmp_path: Path, capsys: Any) -> None:
    assert main(["catalogo-validar", "--pdf", str(tmp_path / "nada.pdf")]) == 1
    assert "PDF-base ausente" in capsys.readouterr().out


def _gravar_entrada(tmp_path: Path, **substituicoes: Any) -> Path:
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(atividade_fixture(**substituicoes), ensure_ascii=False), encoding="utf-8"
    )
    return caminho


def _fixture_aprovada(tmp_path: Path) -> Path:
    return catalogo_fixture(tmp_path / "cat", aprovado=True)


def test_montar_gera_folha_e_gabarito_com_log(tmp_path: Path, capsys: Any) -> None:
    entrada = _gravar_entrada(tmp_path)
    saida = tmp_path / "saida"
    fixture = _fixture_aprovada(tmp_path)
    codigo = main(
        [
            "montar",
            str(entrada),
            "--saida",
            str(saida),
            "--catalogo",
            str(fixture),
            "--pdf",
            str(fixture.parent / "pdf_base.pdf"),
        ]
    )
    assert codigo == 0
    folha = saida / "roma-antiga-teste-automatizado.docx"
    gabarito = saida / "roma-antiga-teste-automatizado-gabarito.docx"
    assert folha.exists() and gabarito.exists()
    assert MARCA_RASCUNHO in Document(folha).sections[0].footer.paragraphs[0].text
    log = (saida / "registros.jsonl").read_text(encoding="utf-8").strip().splitlines()
    registro = json.loads(log[-1])
    assert registro["evento"] == "geracao"
    assert registro["habilidade"] == "EF06HI01X"
    assert registro["semente"]
    assert registro["entrada_sha256"]
    assert registro["duracao_s"] > 0  # lado automático da Q5
    assert "revisar antes de imprimir" in capsys.readouterr().out


def test_montar_recusa_codigo_fora_do_catalogo_sem_gerar_arquivo(
    tmp_path: Path, capsys: Any
) -> None:
    entrada = _gravar_entrada(
        tmp_path,
        habilidade={
            **atividade_fixture()["habilidade"],
            "codigo": "EF06HI99",
            "tipo_modificacao": "original",
        },
    )
    saida = tmp_path / "saida"
    fixture = _fixture_aprovada(tmp_path)
    codigo = main(
        [
            "montar",
            str(entrada),
            "--saida",
            str(saida),
            "--catalogo",
            str(fixture),
            "--pdf",
            str(fixture.parent / "pdf_base.pdf"),
        ]
    )
    assert codigo == 1
    assert "habilidade não encontrada" in capsys.readouterr().out
    assert not saida.exists()


def test_montar_recusa_catalogo_sem_revisao(tmp_path: Path, capsys: Any) -> None:
    entrada = _gravar_entrada(tmp_path)
    fixture = catalogo_fixture(tmp_path / "cat", aprovado=False)
    codigo = main(
        [
            "montar",
            str(entrada),
            "--saida",
            str(tmp_path / "saida"),
            "--catalogo",
            str(fixture),
            "--pdf",
            str(fixture.parent / "pdf_base.pdf"),
        ]
    )
    assert codigo == 1
    assert "revisão manual aprovada" in capsys.readouterr().out


def test_verificar_valida_sem_gerar_arquivo(tmp_path: Path, capsys: Any) -> None:
    entrada = _gravar_entrada(tmp_path)
    fixture = _fixture_aprovada(tmp_path)
    assert main(["verificar", str(entrada), "--catalogo", str(fixture)]) == 0
    assert "EF06HI01X" in capsys.readouterr().out
    assert not (tmp_path / "saida").exists()


def test_verificar_reprova_entrada_invalida(tmp_path: Path, capsys: Any) -> None:
    entrada = _gravar_entrada(tmp_path, confirmado_pelo_professor=False)
    fixture = _fixture_aprovada(tmp_path)
    assert main(["verificar", str(entrada), "--catalogo", str(fixture)]) == 1
    assert "confirmado_pelo_professor" in capsys.readouterr().out


def test_finalizar_remove_marca_e_registra(tmp_path: Path, capsys: Any) -> None:
    saida = tmp_path / "saida"
    entrada = _gravar_entrada(tmp_path)
    fixture = _fixture_aprovada(tmp_path)
    assert (
        main(
            [
                "montar",
                str(entrada),
                "--saida",
                str(saida),
                "--catalogo",
                str(fixture),
                "--pdf",
                str(fixture.parent / "pdf_base.pdf"),
            ]
        )
        == 0
    )
    folha = saida / "roma-antiga-teste-automatizado.docx"
    assert main(["finalizar", str(folha)]) == 0
    assert MARCA_RASCUNHO not in Document(folha).sections[0].footer.paragraphs[0].text
    linhas = (saida / "registros.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(linhas[-1])["evento"] == "aprovado"
    assert "aprovação registrada" in capsys.readouterr().out


def test_exemplo_versionado_e_valido_contra_o_catalogo() -> None:
    atividade, reprovacoes = carregar_entrada(EXEMPLO)
    assert atividade is not None, reprovacoes
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    _, reprovacoes = validar_atividade(atividade, catalogo)
    assert reprovacoes == []
    assert atividade.habilidade.codigo == "EF06HI11X"
    assert atividade.habilidade.pagina == 566
    assert atividade.quantidade_questoes == atividade.total_questoes
    assert atividade.gabarito is True


def test_verificar_sem_catalogo_usa_o_versionado(capsys: Any) -> None:
    assert main(["verificar", str(EXEMPLO)]) == 0
    saida = capsys.readouterr().out
    assert "EF06HI11X" in saida
    assert "catalogo_crmg_ef_anos_finais.json" in saida


def test_catalogo_extrair_repassa_a_saida_e_grava_rascunho(tmp_path: Path, capsys: Any) -> None:
    """O subcomando precisa repassar --saida: sem isso, argparse lê o nome do comando.

    É o comando do procedimento anual (`docs/historia_gen/reextracao-anual.md`).
    """
    rascunho = tmp_path / "rascunho.json"
    assert main(["catalogo-extrair", "--saida", str(rascunho)]) == 0
    dados = json.loads(rascunho.read_text(encoding="utf-8"))
    assert dados["meta"]["rascunho"] is True
    assert len(dados["habilidades"]) == 97
    assert "códigos no texto bruto: 103" in capsys.readouterr().out


def test_conferencia_docx_gera_o_roteiro(tmp_path: Path, capsys: Any) -> None:
    destino = tmp_path / "roteiro.docx"
    assert main(["conferencia-docx", "--saida", str(destino)]) == 0
    assert destino.exists()
    assert "97 habilidades" in capsys.readouterr().out
    assert len(Document(destino).sections) == 2  # retrato (roteiro) + paisagem (lista)


def test_catalogo_versionado_existe_no_repositorio() -> None:
    assert CATALOGO_VERSIONADO.exists()
    dados = json.loads(CATALOGO_VERSIONADO.read_text(encoding="utf-8"))
    # gate aberto só com a conferência literal passando e o registro no meta
    assert dados["meta"]["revisao_aprovada"] is True
    assert dados["meta"]["revisado_por"]
    assert dados["meta"]["revisao_metodo"]


def test_catalogo_conferir_passa_no_versionado(capsys: Any) -> None:
    assert main(["catalogo-conferir"]) == 0
    saida = capsys.readouterr().out
    assert "97 habilidades conferem" in saida
    assert "--aprovar" in saida


def test_catalogo_conferir_acha_divergencia_em_copia_alterada(tmp_path: Path, capsys: Any) -> None:
    copia = tmp_path / "catalogo.json"
    dados = json.loads(CATALOGO_VERSIONADO.read_text(encoding="utf-8"))
    dados["habilidades"][0]["descricao"] = "Descrição trocada de propósito."
    copia.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    pdf = Path("src/historia_gen/catalogo/dados/fonte_oficial/crmg_infantil_ef.pdf")
    assert main(["catalogo-conferir", "--catalogo", str(copia), "--pdf", str(pdf)]) == 1
    assert "divergência" in capsys.readouterr().out


def test_tempo_manual_registra_e_recusa_comparacao_sem_dados(tmp_path: Path, capsys: Any) -> None:
    csv = tmp_path / "q5.csv"
    assert (
        main(
            [
                "tempo-manual",
                "--tema",
                "Roma Antiga",
                "--ano",
                "6º ano EF",
                "--minutos",
                "65",
                "--arquivo",
                str(csv),
            ]
        )
        == 0
    )
    assert "Roma Antiga" in csv.read_text(encoding="utf-8")
    assert (
        main(
            [
                "tempo-manual",
                "--comparar",
                "--arquivo",
                str(csv),
                "--registros",
                str(tmp_path / "sem-log.jsonl"),
            ]
        )
        == 1
    )
    assert "sem comparação" in capsys.readouterr().out
