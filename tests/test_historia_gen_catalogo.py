"""Testes de integridade e completeza do catálogo.

Esquema válido; códigos únicos; campos obrigatórios; hashes conferem com o PDF
versionado; contagens por ano batem com as esperadas; catálogo sem revisão
aprovada não é fonte de geração; hash divergente é detectado.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest
from docx import Document
from docx.enum.section import WD_ORIENT

from src.historia_gen import conferencia
from src.historia_gen.catalogo.carregar import (
    carregar_catalogo,
    carregar_para_geracao,
    validar_catalogo_versionado,
    verificar_integridade,
)
from tests.historia_gen_fixtures import CATALOGO_VERSIONADO, PDF_VERSIONADO, catalogo_fixture

CONTAGENS_ESPERADAS = {"6º ano EF": 19, "7º ano EF": 17, "8º ano EF": 27, "9º ano EF": 34}
CONFERENCIA_CSV = Path(__file__).resolve().parents[1] / "docs/historia_gen/conferencia_catalogo.csv"
CONFERENCIA_DOCX = (
    Path(__file__).resolve().parents[1] / "docs/historia_gen/roteiro-conferencia-catalogo.docx"
)
COLUNAS_CONFERENCIA = [
    "pagina_impressa",
    "ano",
    "codigo",
    "tipo_modificacao",
    "unidade_tematica",
    "objeto_conhecimento",
    "descricao",
    "conferido",
    "observacao",
]


def test_catalogo_versionado_tem_estrutura_valida() -> None:
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    meta = catalogo["meta"]
    assert meta["documento"].startswith("Currículo Referência de Minas Gerais")
    assert meta["url_oficial"].startswith("https://")
    assert meta["data_acesso"] >= "2026-11-01"


def test_catalogo_versionado_codigos_unicos_e_completos() -> None:
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    codigos = [h["codigo"] for h in catalogo["habilidades"]]
    assert len(codigos) == len(set(codigos))
    for h in catalogo["habilidades"]:
        assert h["descricao"]
        assert h["ano"] in CONTAGENS_ESPERADAS
        assert h["unidade_tematica"]
        assert h["objeto_conhecimento"]
        assert h["pagina"] >= 1
        assert h["tipo_modificacao"] in {
            "original",
            "alterada",
            "criada",
            "desmembrada",
            "progressao",
        }


@pytest.mark.parametrize("ano,esperado", sorted(CONTAGENS_ESPERADAS.items()))
def test_catalogo_versionado_contagem_por_ano(ano: str, esperado: int) -> None:
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    obtido = sum(1 for h in catalogo["habilidades"] if h["ano"] == ano)
    assert obtido == esperado
    assert catalogo["meta"]["contagens_esperadas"][ano] == esperado


def test_catalogo_versionado_hashes_conferem_com_pdf() -> None:
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    assert verificar_integridade(catalogo["meta"], PDF_VERSIONADO) == []


def test_validacao_do_versionado_reporta_revisao_registrada() -> None:
    ok, linhas = validar_catalogo_versionado()
    assert ok
    assert any("revisão: aprovada" in linha for linha in linhas)
    assert not any("PENDENTE" in linha for linha in linhas)


def test_carregar_para_geracao_recusa_sem_revisao(tmp_path: Path) -> None:
    caminho = catalogo_fixture(tmp_path / "cat", aprovado=False)
    with pytest.raises(ValueError, match="revisão manual aprovada"):
        carregar_para_geracao(caminho, tmp_path / "cat" / "pdf_base.pdf")


def test_carregar_para_geracao_aceita_revisado(tmp_path: Path) -> None:
    caminho = catalogo_fixture(tmp_path / "cat", aprovado=True)
    catalogo = carregar_para_geracao(caminho, tmp_path / "cat" / "pdf_base.pdf")
    assert catalogo["meta"]["revisao_aprovada"] is True


def test_hash_divergente_e_detectado(tmp_path: Path) -> None:
    caminho = catalogo_fixture(tmp_path / "cat")
    catalogo = carregar_catalogo(caminho)
    catalogo["meta"]["pdf_md5"] = "0" * 32
    problemas = verificar_integridade(catalogo["meta"], tmp_path / "cat" / "pdf_base.pdf")
    assert any("pdf_md5 divergente" in p for p in problemas)


def test_pdf_ausente_falha_fechado(tmp_path: Path) -> None:
    caminho = catalogo_fixture(tmp_path / "cat")
    catalogo = carregar_catalogo(caminho)
    problemas = verificar_integridade(catalogo["meta"], tmp_path / "cat" / "inexistente.pdf")
    assert problemas == [f"PDF-base ausente: {tmp_path / 'cat' / 'inexistente.pdf'}"]


def test_extrator_reproduz_o_catalogo_versionado() -> None:
    """Reextrair o PDF oficial deve devolver o catálogo versionado linha a linha.

    Guarda de regressão: o organizador começa na página física 566 ainda com o
    fim do 5º ano (fora do escopo), e a página registrada é a **impressa**
    (física − 1) — a que o professor confere no documento.
    """
    from src.historia_gen.catalogo import extraidor

    todas, avisos = extraidor.extrair(PDF_VERSIONADO)
    assert avisos == []
    assert {h["ano"] for h in todas} - set(extraidor.ANOS_FINAIS)  # há linhas fora do escopo
    escopo = [h for h in todas if h["ano"] in extraidor.ANOS_FINAIS]
    campos = (
        "codigo",
        "descricao",
        "ano",
        "unidade_tematica",
        "objeto_conhecimento",
        "pagina",
        "tipo_modificacao",
    )
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    assert [{k: h[k] for k in campos} for h in escopo] == [
        {k: h[k] for k in campos} for h in catalogo["habilidades"]
    ]
    # EF06HI01X está na página física 566, impressa 565
    assert [(h["pagina"]) for h in escopo if h["codigo"] == "EF06HI01X"] == [565]


def test_csv_de_conferencia_acompanha_o_catalogo() -> None:
    """A lista de conferência do professor é derivada: não pode ficar velha.

    Se o catálogo mudar (nova extração anual) sem regerar o CSV, a conferência
    seria feita contra outra lista — este teste falha antes disso acontecer.
    """
    with CONFERENCIA_CSV.open(encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh))
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    habs = sorted(catalogo["habilidades"], key=lambda h: (h["pagina"], h["codigo"]))
    assert len(linhas) == len(habs) == 97
    assert list(linhas[0]) == COLUNAS_CONFERENCIA
    for linha, hab in zip(linhas, habs, strict=True):
        assert linha["codigo"] == hab["codigo"]
        assert linha["ano"] == hab["ano"]
        assert linha["pagina_impressa"] == str(hab["pagina"])
        assert linha["tipo_modificacao"] == hab["tipo_modificacao"]
        assert linha["unidade_tematica"] == hab["unidade_tematica"]
        assert linha["objeto_conhecimento"] == hab["objeto_conhecimento"]
        assert linha["descricao"] == hab["descricao"]


def test_docx_de_conferencia_tem_roteiro_e_lista_marcavel(tmp_path: Path) -> None:
    """Um único arquivo: procedimento em retrato e lista em paisagem, com espaço para marcar."""
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    caminho = conferencia.gerar_roteiro(catalogo, tmp_path / "roteiro.docx")
    doc = Document(caminho)
    assert [secao.orientation for secao in doc.sections] == [
        WD_ORIENT.PORTRAIT,
        WD_ORIENT.LANDSCAPE,
    ]
    assert all(p.text.strip() == "" for p in doc.sections[0].header.paragraphs)
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "97 habilidades" in texto
    assert "(  )" in texto  # checklist final imprimível

    tabela = doc.tables[0]
    assert [celula.text for celula in tabela.rows[0].cells] == list(conferencia.COLUNAS)
    habs = sorted(catalogo["habilidades"], key=lambda h: (h["pagina"], h["codigo"]))
    assert len(tabela.rows) == 1 + len({h["pagina"] for h in habs}) + len(habs)
    por_codigo = {h["codigo"]: h for h in habs}
    encontradas: set[str] = set()
    for linha in tabela.rows[1:]:
        codigo = linha.cells[0].text
        if codigo not in por_codigo:  # linha de grupo de página (células mescladas)
            continue
        encontradas.add(codigo)
        assert linha.cells[2].text == por_codigo[codigo]["descricao"]
        assert linha.cells[4].text == ""  # OK, em branco para o professor marcar
        assert linha.cells[5].text == ""  # divergência, espaço para escrever
    assert encontradas == set(por_codigo)


def _texto_e_celulas(doc: Any) -> tuple[list[str], list[list[str]]]:
    paragrafos = [p.text for p in doc.paragraphs]
    celulas = [[c.text for c in linha.cells] for tabela in doc.tables for linha in tabela.rows]
    return paragrafos, celulas


def test_docx_de_conferencia_esta_atualizado(tmp_path: Path) -> None:
    """O arquivo versionado é derivado: não pode ficar velho em relação ao catálogo."""
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    novo = conferencia.gerar_roteiro(catalogo, tmp_path / "roteiro.docx")
    assert _texto_e_celulas(Document(novo)) == _texto_e_celulas(Document(CONFERENCIA_DOCX))


def test_estrutura_invalida_falha(tmp_path: Path) -> None:
    caminho = catalogo_fixture(tmp_path / "cat")
    dados = caminho.read_text(encoding="utf-8").replace('pdf_md5": "', 'pdf_md5_quebrado": "')
    caminho.write_text(dados, encoding="utf-8")
    with pytest.raises(ValueError, match="estrutura inválida"):
        carregar_catalogo(caminho)
