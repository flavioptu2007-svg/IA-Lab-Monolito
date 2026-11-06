"""Roteiro de conferência do catálogo em um único ``.docx`` imprimível.

Duas partes no mesmo arquivo, porque a conferência acontece com o papel na mão:

* **procedimento** (retrato) — o que conferir, como navegar no PDF, as anomalias
  conhecidas, o que fazer em divergência e como registrar a aprovação;
* **lista de conferência** (paisagem) — as 97 habilidades do organizador, uma
  linha por habilidade, com coluna ``OK`` para marcar e espaço para escrever a
  divergência.

Derivado do catálogo versionado: se a extração mudar, regerar o arquivo (o teste
``test_docx_de_conferencia_acompanha_o_catalogo`` falha quando um muda sem o
outro). Sem dependência de rede e sem custo de API.
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

from docx import Document
from docx.document import Document as Documento
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt

from src.historia_gen.template import FONTE

TAMANHO_TEXTO = 11
TAMANHO_TABELA = 8
MARGEM_PAISAGEM_CM = 1.5
COLUNAS = (
    "Código",
    "Ano",
    "Descrição literal",
    "Unidade temática / objeto",
    "OK",
    "Divergência",
)
LARGURAS_CM = (2.7, 1.9, 8.9, 6.0, 1.2, 4.8)
CINZA_CABECALHO = "D9D9D9"
CINZA_GRUPO = "F2F2F2"


def _formatar(run, tamanho: int, *, negrito: bool = False) -> None:  # noqa: ANN001 — objeto python-docx
    run.font.name = FONTE
    run.font.size = Pt(tamanho)
    run.font.bold = negrito


def _paragrafo(
    doc: Documento,
    texto: str = "",
    *,
    tamanho: int = TAMANHO_TEXTO,
    negrito: bool = False,
    justificar: bool = False,
    recuo_cm: float = 0.0,
    espaco_apos: float = 4.0,
) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if justificar else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(espaco_apos)
    if recuo_cm:
        p.paragraph_format.left_indent = Cm(recuo_cm)
    _formatar(p.add_run(texto), tamanho, negrito=negrito)


def _titulo(doc: Documento, texto: str, tamanho: int = 15) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(6)
    _formatar(p.add_run(texto), tamanho, negrito=True)


def _comando(doc: Documento, linha: str) -> None:
    """Comando em bloco: recuado e um ponto menor, sem depender de fonte mono."""
    _paragrafo(doc, linha, tamanho=TAMANHO_TEXTO - 2, recuo_cm=0.6, espaco_apos=2)


def _campo(doc: Documento, rotulo: str, largura: int = 46) -> None:
    _paragrafo(doc, f"{rotulo}: {'_' * largura}", espaco_apos=6)


def _campo_pagina(paragrafo) -> None:  # noqa: ANN001 — objeto python-docx
    """Número de página como campo do Word (o rodapé vale nas duas seções)."""
    run = paragrafo.add_run()
    _formatar(run, 8)
    inicio = OxmlElement("w:fldChar")
    inicio.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separador = OxmlElement("w:fldChar")
    separador.set(qn("w:fldCharType"), "separate")
    resultado = OxmlElement("w:t")
    resultado.text = "1"
    fim = OxmlElement("w:fldChar")
    fim.set(qn("w:fldCharType"), "end")
    for elemento in (inicio, instr, separador, resultado, fim):
        run._r.append(elemento)


def _configurar_secao(secao, *, paisagem: bool) -> None:  # noqa: ANN001 — objeto python-docx
    if paisagem:
        secao.orientation = WD_ORIENT.LANDSCAPE
        secao.page_width = Mm(297)
        secao.page_height = Mm(210)
        margem = Cm(MARGEM_PAISAGEM_CM)
    else:
        secao.orientation = WD_ORIENT.PORTRAIT
        secao.page_width = Mm(210)
        secao.page_height = Mm(297)
        margem = Cm(2.0)
    for atributo in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(secao, atributo, margem)
    # Sem cabeçalho (regra do template: a folha nunca tem cabeçalho).
    for paragrafo in secao.header.paragraphs:
        paragrafo.text = ""


def _celula_texto(celula, texto: str, tamanho: int, *, negrito: bool = False) -> None:  # noqa: ANN001
    celula.text = texto
    for paragrafo in celula.paragraphs:
        paragrafo.paragraph_format.space_after = Pt(0)
        for run in paragrafo.runs:
            _formatar(run, tamanho, negrito=negrito)


def _sombra(celula, cor: str) -> None:  # noqa: ANN001 — objeto python-docx
    tc_pr = celula._tc.get_or_add_tcPr()
    sombra = OxmlElement("w:shd")
    sombra.set(qn("w:val"), "clear")
    sombra.set(qn("w:color"), "auto")
    sombra.set(qn("w:fill"), cor)
    tc_pr.append(sombra)


def _repetir_cabecalho(linha) -> None:  # noqa: ANN001 — objeto python-docx
    tr_pr = linha._tr.get_or_add_trPr()
    marca = OxmlElement("w:tblHeader")
    marca.set(qn("w:val"), "true")
    tr_pr.append(marca)


def _largura_fixa(tabela) -> None:  # noqa: ANN001 — objeto python-docx
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tabela._tbl.tblPr.append(layout)


def _nao_quebrar(linha) -> None:  # noqa: ANN001 — objeto python-docx
    """Uma habilidade ocupa uma linha inteira: nada de linha partida entre páginas."""
    linha._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))


def _procedimento(doc: Documento, catalogo: dict[str, Any], total: int) -> None:
    meta = catalogo["meta"]
    titulo = doc.add_paragraph()
    titulo.paragraph_format.space_after = Pt(2)
    _formatar(
        titulo.add_run("Conferência do catálogo CRMG — aprovação das habilidades"), 16, negrito=True
    )
    _paragrafo(
        doc,
        f"História · Anos Finais · {total} habilidades · documento oficial de {meta['data_acesso']}",
        tamanho=10,
        espaco_apos=10,
    )
    if meta["revisao_aprovada"]:
        situacao = (
            "O catálogo está aprovado "
            f"({meta.get('revisao_data') or 'data não registrada'} — "
            f"{meta.get('revisado_por') or 'responsável não informado'}), e o comando "
            "montar já o aceita como fonte de geração. Esta conferência é a auditoria: "
            "refaça-a quando o documento oficial for reextraído."
        )
    else:
        situacao = (
            "Com o catálogo em revisão pendente, o comando montar recusa qualquer folha: "
            "esta conferência é o único caminho para abrir esse gate."
        )
    _paragrafo(
        doc,
        "Duas partes: o procedimento (páginas em retrato) e a lista de conferência "
        "(páginas em paisagem, uma linha por habilidade, com coluna para marcar e "
        f"espaço para a divergência). {situacao}",
        justificar=True,
    )
    _paragrafo(
        doc,
        "Quem faz: professor(a) de História dos Anos Finais. O que se confere: "
        "fidelidade da transcrição ao documento oficial — não é revisão pedagógica "
        "das habilidades. Tempo estimado: 40 a 60 minutos.",
        justificar=True,
        espaco_apos=2,
    )

    _titulo(doc, "1. Antes de começar", 12)
    _paragrafo(
        doc,
        "Tenha em mãos o PDF oficial versionado, aberto na página física 567 (impressa "
        "566), e a lista de conferência a partir da página seguinte deste documento. "
        "Confirme antes a integridade da fonte:",
        justificar=True,
        espaco_apos=2,
    )
    _paragrafo(
        doc,
        "src/historia_gen/catalogo/dados/fonte_oficial/crmg_infantil_ef.pdf",
        tamanho=TAMANHO_TEXTO - 2,
        recuo_cm=0.6,
        espaco_apos=4,
    )
    _comando(doc, "python3 -m src.historia_gen catalogo-validar")
    _paragrafo(
        doc,
        "Esperado: MD5 e SHA-256 conferindo com o PDF versionado, as quatro contagens "
        "(6º 19 · 7º 17 · 8º 27 · 9º 34) e o aviso de revisão manual pendente. Se a "
        "integridade falhar, pare: o PDF aberto não é o da extração.",
        justificar=True,
    )

    _titulo(doc, "2. Como navegar no PDF", 12)
    _paragrafo(doc, "• O organizador de História começa na página impressa 558; as habilidades dos")
    _paragrafo(doc, "   Anos Finais ocupam as impressas 565 a 577 (13 páginas).")
    _paragrafo(doc, "• A página física do PDF é a impressa + 1; o número impresso aparece no topo.")
    _paragrafo(
        doc, "• A tabela tem 4 colunas: Ano | Unidades Temáticas | Objetos de Conhecimento |"
    )
    _paragrafo(doc, "   Habilidades. As células mescladas valem para todas as linhas do bloco.")

    _titulo(doc, "3. O que conferir em cada linha", 12)
    itens = (
        "Código — idêntico ao impresso, incluindo o sufixo (X, MG, A/B/C, P1/P2). "
        "Sufixo perdido muda o significado.",
        "Descrição — palavra por palavra, sem cortes nem melhorias. Erros de "
        "digitação do próprio CRMG também são transcritos como estão.",
        "Ano — a linha em que a habilidade aparece (6º a 9º ano EF).",
        "Unidade temática e objeto de conhecimento — os do bloco da linha, mesmo "
        "quando repetidos em várias habilidades.",
        "Página — o número impresso no topo da página de onde a linha foi tirada.",
    )
    for numero, item in enumerate(itens, start=1):
        _paragrafo(doc, f"{numero}) {item}", justificar=True)

    _titulo(doc, "4. Anomalias já conhecidas — decisão esperada", 12)
    _paragrafo(
        doc,
        "As duas linhas abaixo parecem erro, mas são transcrição fiel: não corrija o "
        "texto, confirme que o catálogo reproduz o que o documento imprime.",
        justificar=True,
    )
    _paragrafo(
        doc,
        "1) 7º ano — unidade quebrada (p. 568): EF07HI01 e EF07HI03X registram o "
        "fragmento “moderno e a conexão entre sociedades africanas, americanas e "
        "europeias”, porque a unidade aparece partida entre duas linhas. Decisão "
        "esperada: manter o literal.",
        justificar=True,
    )
    _paragrafo(
        doc,
        "2) 9º ano — ano variável no nome da unidade (pp. 575 a 577): a unidade "
        "“Modernização, ditadura civil-militar e redemocratização: o Brasil após …” "
        "varia o ano a cada linha. Decisão esperada: manter o que cada linha imprime.",
        justificar=True,
    )

    _titulo(doc, "5. Se encontrar divergência", 12)
    _paragrafo(
        doc,
        "Não edite o JSON do catálogo à mão: ele é gerado pelo extrator, e corrigir só "
        "o arquivo faria a próxima extração desfazer a correção sem aviso.",
        justificar=True,
    )
    _paragrafo(doc, "1) Registre no espaço da linha: o que o PDF imprime e o que o catálogo tem.")
    _paragrafo(doc, "2) A correção é no extrator: src/historia_gen/catalogo/extraidor.py.")
    _paragrafo(doc, "3) Regenere, revalide e rode os testes do catálogo:")
    _comando(doc, "python3 src/historia_gen/catalogo/extraidor.py")
    _comando(doc, "python3 -m src.historia_gen catalogo-validar")
    _comando(doc, "python3 -m pytest -q tests/test_historia_gen_catalogo.py")
    _paragrafo(
        doc,
        "4) Repita a conferência apenas das linhas afetadas.",
        espaco_apos=6,
    )

    _titulo(doc, "6. Aprovando o catálogo", 12)
    _paragrafo(
        doc,
        "Com todas as linhas marcadas OK, nesta ordem:",
        justificar=True,
        espaco_apos=3,
    )
    passos = (
        "rodar a conferência literal contra o PDF: python3 -m src.historia_gen catalogo-conferir;",
        "registrar a aprovação com o nome de quem conferiu: python3 -m src.historia_gen "
        'catalogo-conferir --aprovar --responsavel "Prof. <nome>" (o comando se '
        "recusa a aprovar se houver divergência);",
        "rodar catalogo-validar, os testes do pacote e a montagem de teste com o "
        "catálogo versionado;",
        "registrar data, conferente e divergências em docs/historia_gen/validacoes.md.",
    )
    for letra, passo in zip("abcd", passos, strict=True):
        _paragrafo(doc, f"({letra}) {passo}")

    _titulo(doc, "7. Critério de conclusão", 12)
    for item in (
        "catalogo-validar passou antes da conferência (integridade e contagens);",
        f"as {total} linhas da lista marcadas OK;",
        "as duas anomalias conhecidas decididas e registradas;",
        "meta.revisao_aprovada: true, com revisado_por e revisao_metodo preenchidos;",
        "teste do gate e validacoes.md atualizados;",
        "pytest verde e montar gerando folha + gabarito com o catálogo versionado;",
        "validacoes.md atualizado.",
    ):
        _paragrafo(doc, f"(  )  {item}", espaco_apos=3)
    _campo(doc, "Conferente")
    _campo(doc, "Data da conferência")


def _agrupar_por_pagina(
    habilidades: list[dict[str, Any]],
) -> list[tuple[int, list[dict[str, Any]]]]:
    """Ordena por página impressa (e código) e agrupa — a conferência anda página a página."""
    ordenadas = sorted(habilidades, key=lambda h: (h["pagina"], h["codigo"]))
    return [
        (pagina, list(itens))
        for pagina, itens in itertools.groupby(ordenadas, key=lambda h: h["pagina"])
    ]


def _lista_conferencia(doc: Documento, grupos: list[tuple[int, list[dict[str, Any]]]]) -> None:
    total = sum(len(itens) for _, itens in grupos)
    _paragrafo(doc, "Lista de conferência — uma linha por habilidade", tamanho=14, negrito=True)
    _paragrafo(
        doc,
        f"{total} habilidades em {len(grupos)} páginas do organizador. Marque OK quando os "
        "cinco itens do passo 3 conferirem; quando não conferirem, deixe OK em branco e "
        "escreva na última coluna o que o PDF imprime e o que o catálogo tem.",
        tamanho=9,
        justificar=True,
        espaco_apos=8,
    )

    linhas = 1 + len(grupos) + total
    tabela = doc.add_table(rows=linhas, cols=len(COLUNAS))
    tabela.style = "Table Grid"
    tabela.autofit = False
    _largura_fixa(tabela)
    # Larguras vão na grade da tabela: com layout fixo é ela que manda na impressão.
    for coluna, largura in zip(tabela.columns, LARGURAS_CM, strict=True):
        coluna.width = Cm(largura)

    cabecalho = tabela.rows[0]
    _repetir_cabecalho(cabecalho)
    for celula, rotulo in zip(cabecalho.cells, COLUNAS, strict=True):
        _celula_texto(celula, rotulo, TAMANHO_TABELA, negrito=True)
        celula.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _sombra(celula, CINZA_CABECALHO)

    indice = 1
    for pagina, habilidades in grupos:
        grupo = tabela.rows[indice]
        celula_grupo = grupo.cells[0].merge(grupo.cells[-1])
        plural = "habilidade" if len(habilidades) == 1 else "habilidades"
        _celula_texto(
            celula_grupo,
            f"Página impressa {pagina} (física {pagina + 1}) — {len(habilidades)} {plural}",
            TAMANHO_TABELA,
            negrito=True,
        )
        _sombra(celula_grupo, CINZA_GRUPO)
        indice += 1
        for habilidade in habilidades:
            linha = tabela.rows[indice]
            valores = (
                habilidade["codigo"],
                habilidade["ano"],
                habilidade["descricao"],
                "Unidade: "
                + habilidade["unidade_tematica"]
                + "\nObjeto: "
                + habilidade["objeto_conhecimento"],
                "",
                "",
            )
            for celula, valor in zip(linha.cells, valores, strict=True):
                _celula_texto(celula, valor, TAMANHO_TABELA)
                celula.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            indice += 1

    for linha in tabela.rows:
        _nao_quebrar(linha)


def _resultado(doc: Documento, total: int) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    _paragrafo(doc, "Resultado da conferência", tamanho=14, negrito=True, espaco_apos=10)
    _campo(doc, "Conferente")
    _campo(doc, "Data")
    _campo(doc, f"Linhas com OK (de {total})", 14)
    _campo(doc, "Divergências encontradas", 14)
    _paragrafo(
        doc, "Decisão:   (  ) aprovar o catálogo      (  ) devolver para correção", espaco_apos=10
    )
    _paragrafo(doc, "Anomalias conhecidas (7º ano, p. 568 · 9º ano, pp. 575-577):")
    _paragrafo(
        doc, "(  ) mantidas como transcrição literal (esperado)", recuo_cm=0.6, espaco_apos=3
    )
    _paragrafo(
        doc,
        "(  ) alterar a regra do extrator — registrar abaixo o porquê",
        recuo_cm=0.6,
        espaco_apos=10,
    )
    _paragrafo(doc, "Observações:", espaco_apos=2)
    for _ in range(4):
        _paragrafo(doc, "_" * 110, espaco_apos=12)


def gerar_roteiro(catalogo: dict[str, Any], destino: Path) -> Path:
    """Grava o roteiro imprimível e devolve o caminho do ``.docx``."""
    habilidades = catalogo["habilidades"]
    grupos = _agrupar_por_pagina(habilidades)
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = FONTE
    estilo.font.size = Pt(TAMANHO_TEXTO)
    _configurar_secao(doc.sections[0], paisagem=False)
    _procedimento(doc, catalogo, len(habilidades))

    secao_lista = doc.add_section(WD_SECTION.NEW_PAGE)
    _configurar_secao(secao_lista, paisagem=True)
    _lista_conferencia(doc, grupos)
    _resultado(doc, len(habilidades))

    rodape = doc.sections[0].footer.paragraphs[0]
    rodape.text = ""
    _formatar(
        rodape.add_run(
            f"Conferência do catálogo CRMG · acesso {catalogo['meta']['data_acesso']} · página "
        ),
        8,
    )
    _campo_pagina(rodape)

    props = doc.core_properties
    props.title = "Conferência do catálogo CRMG — aprovação das habilidades"
    props.comments = (
        f"derivado de {catalogo['meta']['versao']}; {len(habilidades)} habilidades; "
        "gerado por src/historia_gen/conferencia.py"
    )

    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(destino))
    return destino


__all__ = ["COLUNAS", "gerar_roteiro"]
