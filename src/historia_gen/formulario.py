"""Formulário impresso da Q5 — o professor preenche à mão durante a adaptação.

O instrumento da Q5 já tem onde guardar o número (``tempo-manual`` grava o CSV) e
como comparar; faltava o papel que o professor leva para a mesa. Este módulo
monta esse papel: uma página por medição, com as etapas do protocolo
(``docs/historia_gen/q5-linha-de-base.md``), campos para escrever os horários à
mão e, no fim, o comando que transforma o total em linha de base.

Sem cabeçalho de página e sem campo de identificação de estudante — a regra do
template vale também aqui; quem assina é o professor que cronometrou.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from docx import Document
from docx.document import Document as Documento
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt
from docx.table import Table

from src.historia_gen import VERSAO_TEMPLATE
from src.historia_gen.template import FONTE, MARGEM_CM

TAMANHO_TEXTO = 11
TAMANHO_TABELA = 10
VIAS_PADRAO = 2  # o protocolo pede 1–2 adaptações reais cronometradas
DESTINO_PADRAO = Path("docs/historia_gen/q5-formulario.docx")

# Etapas do protocolo: o relógio começa ao abrir o material de origem e para
# quando o arquivo está pronto para imprimir (a impressão não conta).
ETAPAS = (
    "Ler o material de origem e escolher o que fica na folha",
    "Reescrever o texto e os comandos (linguagem e tamanho)",
    "Preparar as questões adaptadas (formato, alternativas, apoio)",
    "Digitar e montar o arquivo (.docx)",
    "Revisar, corrigir e fechar o arquivo para impressão",
)
COLUNAS_ETAPAS = ("#", "Etapa", "Início", "Fim", "Minutos")
LARGURAS_ETAPAS = (1.0, 8.8, 2.2, 2.2, 2.6)
ALTURA_LINHA_CM = 1.0


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
    espaco_apos: float = 4.0,
    junto: bool = False,
) -> None:
    """Parágrafo sem justificação por padrão: campo de papel à mão é alinhado à esquerda."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if justificar else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(espaco_apos)
    p.paragraph_format.keep_with_next = junto
    _formatar(p.add_run(texto), tamanho, negrito=negrito)


def _titulo(doc: Documento, texto: str, tamanho: int = 12) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    _formatar(p.add_run(texto), tamanho, negrito=True)


def _campo(doc: Documento, rotulo: str, largura: int = 44) -> None:
    _paragrafo(doc, f"{rotulo}: {'_' * largura}", espaco_apos=4)


def _celula(cel, texto: str, tamanho: int = TAMANHO_TABELA, *, negrito: bool = False) -> None:  # noqa: ANN001
    cel.text = texto
    for paragrafo in cel.paragraphs:
        paragrafo.paragraph_format.space_before = Pt(0)
        paragrafo.paragraph_format.space_after = Pt(0)
        for run in paragrafo.runs:
            _formatar(run, tamanho, negrito=negrito)


def _configurar_pagina(doc: Documento) -> None:
    secao = doc.sections[0]
    secao.page_width = Mm(210)
    secao.page_height = Mm(297)
    for margem in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(secao, margem, Cm(MARGEM_CM))
    estilo = doc.styles["Normal"]
    estilo.font.name = FONTE
    estilo.font.size = Pt(TAMANHO_TEXTO)
    # Sem cabeçalho: a regra do template vale para todo documento do pacote.
    for paragrafo in secao.header.paragraphs:
        paragrafo.text = ""


def _tabela(
    doc: Documento,
    cabecalho: Sequence[str],
    linhas: Sequence[Sequence[str]],
    larguras_cm: Sequence[float],
    *,
    altura_cm: float | None = None,
) -> Table:
    """Grade com largura fixa e linha alta o bastante para escrever à mão."""
    tabela = doc.add_table(rows=1 + len(linhas), cols=len(cabecalho))
    tabela.style = "Table Grid"
    tabela.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tabela._tbl.tblPr.append(layout)  # noqa: SLF001 — API baixa do python-docx
    for coluna, largura in zip(tabela.columns, larguras_cm, strict=True):
        coluna.width = Cm(largura)
    for coluna, texto in enumerate(cabecalho):
        _celula(tabela.cell(0, coluna), texto, negrito=True)
    for indice, valores in enumerate(linhas, start=1):
        for coluna, texto in enumerate(valores):
            _celula(tabela.cell(indice, coluna), texto)
    if altura_cm:
        for linha in tabela.rows:
            linha.height = Cm(altura_cm)
            linha.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    # A tabela não quebra entre páginas: uma linha partida vira horário no lugar errado.
    for linha in tabela.rows:
        linha._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))  # noqa: SLF001
    return tabela


def _campo_pagina(paragrafo) -> None:  # noqa: ANN001 — objeto python-docx
    """Número de página como campo do Word (o rodapé acompanha as vias)."""
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
        run._r.append(elemento)  # noqa: SLF001 — API baixa do python-docx


def _via(doc: Documento, numero: int, total: int) -> None:
    """Uma medição por página: cabeçalho, etapas, retrabalho e como registrar."""
    rotulo = f"Formulário {numero} de {total}" if total > 1 else "Formulário"
    _paragrafo(
        doc,
        f"{rotulo} — cronometragem da adaptação manual (Q5)",
        tamanho=15,
        negrito=True,
        espaco_apos=2,
    )
    _paragrafo(
        doc,
        "História · Anos Finais · preencher à mão, durante a adaptação feita sem o pipeline",
        tamanho=TAMANHO_TEXTO - 1,
        espaco_apos=8,
    )
    _paragrafo(
        doc,
        "O relógio começa ao abrir o material de origem e para quando o arquivo está pronto "
        "para imprimir — a impressão não conta.",
        justificar=True,
        espaco_apos=6,
    )

    _titulo(doc, "1. Adaptação cronometrada")
    _campo(doc, "Professor(a)", 30)
    _campo(doc, "Data (dia/mês/ano)", 20)
    _campo(doc, "Ano/série e turma", 28)
    _paragrafo(doc, "Modo:   (  ) regular        (  ) adaptado (suporte 2)", espaco_apos=8)
    _campo(doc, "Tema ou conteúdo da aula", 40)
    _campo(doc, "Material de origem (prova, caderno, livro e página)", 32)

    _titulo(doc, "2. Tempo por etapa")
    _paragrafo(
        doc,
        "Anote o horário de início e de fim de cada etapa (hora:minuto) e os minutos "
        "gastos. Se preferir, marque o relógio do começo ao fim do trabalho e escreva "
        "só o total.",
        justificar=True,
        espaco_apos=6,
    )
    linhas = [
        (f"{numero_etapa}.", etapa, "", "", "")
        for numero_etapa, etapa in enumerate(ETAPAS, start=1)
    ]
    linhas.append(("", "Total (minutos)", "", "", ""))
    tabela = _tabela(doc, COLUNAS_ETAPAS, linhas, LARGURAS_ETAPAS, altura_cm=ALTURA_LINHA_CM)
    # O total é a resposta do formulário: mais alto e com o rótulo em negrito.
    total_linha = tabela.rows[-1]
    total_linha.height = Cm(1.4)
    _celula(total_linha.cells[1], "Total de minutos deste trabalho", negrito=True)

    _titulo(doc, "3. Retrabalho")
    _paragrafo(doc, "Depois de pronto, o arquivo precisou de retrabalho?", espaco_apos=4)
    _paragrafo(doc, "(  ) não        (  ) sim — quanto tempo a mais: ______ min", espaco_apos=6)
    _paragrafo(doc, "O que teve de ser refeito:", espaco_apos=2)
    # 72 sublinhados cabem numa linha de 17 cm em Arial 11: com 100 o traço
    # quebrava e o campo saía em dois pedaços desiguais.
    for _ in range(2):
        _paragrafo(doc, "_" * 72, espaco_apos=10)

    _titulo(doc, "4. Como este papel vira linha de base")
    _paragrafo(
        doc,
        "Só o total entra no registro; as etapas mostram onde o tempo foi gasto. Com ele em mãos:",
        justificar=True,
        espaco_apos=3,
    )
    _paragrafo(
        doc,
        'python3 -m src.historia_gen tempo-manual --tema "tema preenchido acima" '
        '--ano "ano preenchido acima" --minutos TOTAL',
        tamanho=TAMANHO_TEXTO - 2,
        espaco_apos=2,
    )
    _paragrafo(
        doc,
        "Use --modo regular se a folha era regular; --quem e --observacao são opcionais. "
        "O comando grava em docs/historia_gen/q5-linha-de-base.csv.",
        tamanho=TAMANHO_TEXTO - 1,
        justificar=True,
        espaco_apos=2,
    )


def gerar_formulario(destino: Path, *, vias: int = VIAS_PADRAO) -> Path:
    """Grava o formulário impresso (uma página por medição) e devolve o caminho."""
    if vias < 1:
        msg = "vias deve ser pelo menos 1 — cada via é uma adaptação cronometrada"
        raise ValueError(msg)
    doc = Document()
    _configurar_pagina(doc)
    for numero in range(1, vias + 1):
        if numero > 1:
            doc.add_page_break()
        _via(doc, numero, vias)

    rodape = doc.sections[0].footer.paragraphs[0]
    rodape.text = ""
    _formatar(
        rodape.add_run(f"Cronometragem da adaptação manual (Q5) · template {VERSAO_TEMPLATE} · "),
        8,
    )
    _campo_pagina(rodape)

    props = doc.core_properties
    props.title = "Cronometragem da adaptação manual — formulário Q5"
    props.category = f"template {VERSAO_TEMPLATE}"
    props.comments = "instrumento da Q5; gerado por src/historia_gen/formulario.py"

    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(destino))
    return destino


__all__ = ["DESTINO_PADRAO", "ETAPAS", "VIAS_PADRAO", "gerar_formulario"]
