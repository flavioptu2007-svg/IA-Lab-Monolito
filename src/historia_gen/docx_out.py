"""Montador ``.docx`` (python-docx) — as regras de formato, uma por uma.

* A4 retrato, corpo conforme ``template.py``, texto justificado, margens para impressão.
* Sem cabeçalho (única exceção: pedido expresso do professor); sem campos de
  identificação; sem título genérico — a folha começa pelo conteúdo pedagógico.
* Sem espaços/linhas de resposta quando o estudante responde no caderno.
* Citação da fonte no corpo da leitura e nos itens de completar; nos itens de
  marcar, nas afirmações V/F e nos pares de ligar, a referência acompanha o bloco
  "Fontes:" da seção.
* Itens de resposta por marcação (``itens_marcar``, ``itens_vf``) imprimem a opção
  com espaço de marcação ``( )`` — nada é escrito neles; o gabarito traz a opção
  certa e, na afirmação falsa, o que é correto.
* ``itens_parear`` (mesma palavra nas duas colunas, em ordens diferentes) e
  ``itens_ordenar`` (itens embaralhados para numerar, gabarito com a sequência
  correta) completam a escada de exigência sem pedir escrita.
* ``figuras`` insere a imagem local validada (até 14 cm de largura, no máximo
  17 cm de altura, centralizada) com legenda e citação da fonte; sem o arquivo, a
  entrada é recusada.
* Marca de rascunho no rodapé; versão do template em metadado (permanece após
  o ``finalizar``).
* Gabarito em arquivo separado quando ``gabarito: true``.
* Página final de uso do professor quando ``registro_mediacao: true``: como aplicar,
  grade de registro por item e observações — marcada como página que não vai para
  o estudante (o resto da folha segue sem campos de identificação).
* Metadados de proveniência apenas nos atributos fixos de ``core_properties``.
* Modo adaptado: sem grandes áreas de tinta (nada de preenchimento de célula).
* Suporte 3: **uma tarefa por página** (GAP-7) — cada bloco de leitura e cada
  item começam em página nova, repetindo instrução, banco de palavras e fonte,
  porque a página é entregue e recolhida sozinha.
"""

from __future__ import annotations

import random
import re
import unicodedata
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import TypeVar

from docx import Document
from docx.document import Document as Documento
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Cm, Mm, Pt
from docx.table import Table

from src.historia_gen import VERSAO_TEMPLATE
from src.historia_gen.formatos import (
    montar_banco_palavras,
    montar_ligar,
    montar_ordenar,
    montar_parear_iguais,
)
from src.historia_gen.modelos import (
    AtividadeEntrada,
    Figura,
    FonteRef,
    ItemCompletar,
    ItemMarcar,
    ItemOrdenar,
    ItemParearIguais,
    ItemVerdadeiroFalso,
    ParLigar,
    Planejamento,
)
from src.historia_gen.template import FONTE, MARCA_RASCUNHO, MARGEM_CM

_POR_EXTENSO = {
    "primaria": "fonte primária",
    "secundaria": "fonte secundária",
    "ilustracao": "ilustração",
}

LARGURA_FIGURA_CM = 14.0
# A área útil do A4 com margens de 2 cm é 17 cm de largura por 25,7 cm de altura.
# Uma imagem retrato de 14 cm de largura passa de 24 cm de altura: com legenda e
# citação ela não cabe, e o Word a empurra para a página seguinte cortada no pé.
ALTURA_MAXIMA_FIGURA_CM = 17.0


def _configurar_pagina(doc: Documento, tamanho: int) -> None:
    secao = doc.sections[0]
    secao.page_width = Mm(210)
    secao.page_height = Mm(297)
    for margem in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(secao, margem, Cm(MARGEM_CM))
    estilo = doc.styles["Normal"]
    estilo.font.name = FONTE
    estilo.font.size = Pt(tamanho)
    # Sem cabeçalho: o cabeçalho da seção permanece vazio por construção.
    rodape = secao.footer
    if rodape.paragraphs:
        rodape.paragraphs[0].text = ""


def _paragrafo(
    doc: Documento,
    texto: str,
    tamanho: int,
    negrito: bool = False,
    esquerda: bool = False,
    junto: bool = False,
    espaco_depois: float | None = None,
) -> None:
    p = doc.add_paragraph()
    # Instrução não pode ficar no pé de uma página com o item/tabela na seguinte.
    p.paragraph_format.keep_with_next = junto
    # Rótulo colado na grade seguinte não precisa do respiro de 8 pt do estilo.
    if espaco_depois is not None:
        p.paragraph_format.space_after = Pt(espaco_depois)
    # Linha com caminho/nome de arquivo não se justifica: a justificação estica
    # os espaços até o token longo e a linha fica aberta no papel.
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if esquerda else WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(texto)
    run.bold = negrito
    run.font.name = FONTE
    run.font.size = Pt(tamanho)


def _citacao(fonte: FonteRef) -> str:
    pedacos = [f"({_POR_EXTENSO[fonte.tipo]}: {fonte.obra}"]
    if fonte.autor:
        pedacos.append(fonte.autor)
    if fonte.ano:
        pedacos.append(fonte.ano)
    pedacos.append(f"acesso em {fonte.data_acesso})")
    return ", ".join(pedacos)


def _fontes_unicas(fontes: Sequence[FonteRef]) -> str:
    """Cada fonte citada uma única vez, na ordem em que aparece na seção.

    A repetição literal da mesma referência a cada item empurrava o bloco para
    uma segunda página quase vazia (visto na revisão de impressão).
    """
    vistas: dict[tuple, FonteRef] = {}
    for fonte in fontes:
        chave = (fonte.tipo, fonte.origem, fonte.obra, fonte.autor, fonte.ano, fonte.url)
        vistas.setdefault(chave, fonte)
    return "; ".join(_citacao(f) for f in vistas.values())


def _nao_parte(tabela: Table) -> None:
    """A grade não quebra entre páginas: nem a linha, nem o conjunto.

    ``cantSplit`` impede cortar uma linha ao meio, mas sozinho ainda deixa a
    tabela partir entre linhas: na conferência de impressão da atividade de Roma
    a grade do ligar deixou uma linha órfã numa página quase vazia. O
    ``keepNext`` em todas as linhas menos a última mantém a tabela inteira na
    mesma página — quem lê marca a linha errada quando ela continua na seguinte.
    """
    linhas = list(tabela.rows)
    for i, linha in enumerate(linhas):
        tr_pr = linha._tr.get_or_add_trPr()  # noqa: SLF001 — API baixa do python-docx
        tr_pr.append(OxmlElement("w:cantSplit"))
        if i < len(linhas) - 1:
            for celula in linha.cells:
                for paragrafo in celula.paragraphs:
                    paragrafo.paragraph_format.keep_with_next = True


def _celula(cel, texto: str, tamanho: int) -> None:  # noqa: ANN001 — objeto python-docx
    cel.text = texto
    for paragrafo in cel.paragraphs:
        # Célula não é parágrafo de corpo: o "8 pt depois" do estilo Normal abre
        # uma faixa em branco sob cada linha da grade e infla a tabela — na
        # revisão da atividade de Roma as 11 linhas do registro somavam 3 cm de
        # espaçamento e o campo de observações caía numa página quase vazia.
        paragrafo.paragraph_format.space_before = Pt(0)
        paragrafo.paragraph_format.space_after = Pt(0)
        paragrafo.paragraph_format.line_spacing = 1.0
        for run in paragrafo.runs:
            run.font.name = FONTE
            run.font.size = Pt(tamanho)


def _resumo(texto: str, limite: int = 46) -> str:
    """Primeiras palavras do item, para identificar a linha na grade do professor.

    O limite era 70 e a coluna do item tem 7,8 cm: as linhas de três frases
    empurravam a grade até o pé da página e o campo de observações caía sozinho
    numa quinta página quase vazia (visto na revisão da atividade de Roma).
    """
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def _itens_do_registro(atividade: AtividadeEntrada) -> list[str]:
    """Rótulos na ordem em que os itens aparecem impressos na folha."""
    rotulos = [
        f"Leitura {i}: {_resumo(bloco.pergunta)}"
        for i, bloco in enumerate((b for b in atividade.blocos if b.pergunta), start=1)
    ]
    rotulos += [
        f"Parear {i} ({len(item.palavras)} palavras)"
        for i, item in enumerate(atividade.itens_parear, start=1)
    ]
    rotulos += [
        f"Marcar {i}: {_resumo(item.enunciado)}"
        for i, item in enumerate(atividade.itens_marcar, start=1)
    ]
    rotulos += [
        f"V/F {i}: {_resumo(item.afirmacao)}" for i, item in enumerate(atividade.itens_vf, start=1)
    ]
    rotulos += [
        f"Ordenar {i}: {_resumo(item.enunciado)}"
        for i, item in enumerate(atividade.itens_ordenar, start=1)
    ]
    # "Completar" nomeia o formato como as outras linhas: o "1)" sozinho se
    # confundia com a numeração do marcar na mesma grade.
    rotulos += [
        f"Completar {i}: {_resumo(item.frase_com_lacuna)}"
        for i, item in enumerate(atividade.itens_completar, start=1)
    ]
    if atividade.pares_ligar:
        rotulos.append(f"Ligar colunas ({len(atividade.pares_ligar)} pares)")
    return rotulos


def _orientacoes(atividade: AtividadeEntrada, nome_gabarito: str | None) -> list[str]:
    """Orientações geradas da própria folha + as do professor, nesta ordem."""
    orientacoes = [
        "Leia o comando em voz alta e mostre o primeiro item como modelo.",
        "Aceite também apontar, ditar, colar a ficha da palavra ou usar comunicação alternativa.",
    ]
    if atividade.figuras:
        orientacoes.append(
            "Deixe a figura à vista durante toda a tarefa; ela é o apoio, não a resposta."
        )
    if atividade.itens_parear:
        orientacoes.append(
            "No parear, vale traçar a linha com o dedo ou apontar as duas palavras iguais."
        )
    if atividade.itens_completar:
        orientacoes.append(
            "No banco de palavras, apontar a palavra certa também vale como resposta."
        )
    if atividade.itens_ordenar:
        orientacoes.append(
            "Na ordenação, aceite a sequência ditada ou montada com fichas, não só o número escrito."
        )
    if atividade.pares_ligar:
        orientacoes.append("No ligar, peça a letra e o número — por escrito, apontando ou ditando.")
    if nome_gabarito:
        orientacoes.append("O gabarito está em arquivo separado: não imprimir junto com a folha.")
    return [*orientacoes, *atividade.orientacoes_aplicacao]


def _tabela(
    doc: Documento,
    cabecalho: Sequence[str],
    linhas: Sequence[Sequence[str]],
    larguras_cm: Sequence[float],
    tamanho: int,
) -> Table:
    """Grade do registro; a largura vem da coluna (é ela que a impressão obedece)."""
    tabela = doc.add_table(rows=1 + len(linhas), cols=len(cabecalho))
    tabela.style = "Table Grid"
    for i, largura in enumerate(larguras_cm):
        tabela.columns[i].width = Cm(largura)
    for coluna, texto in enumerate(cabecalho):
        _celula(tabela.cell(0, coluna), texto, tamanho)
    for linha, valores in enumerate(linhas, start=1):
        for coluna, texto in enumerate(valores):
            _celula(tabela.cell(linha, coluna), texto, tamanho)
    _nao_parte(tabela)
    return tabela


def _tabela_de_colunas(
    doc: Documento,
    esquerda: Sequence[tuple[str, str]],
    direita: Sequence[tuple[str, str]],
    tamanho: int,
) -> None:
    """Duas colunas lado a lado (parear iguais e ligar)."""
    tabela = doc.add_table(rows=max(len(esquerda), len(direita)), cols=2)
    tabela.style = "Table Grid"
    tabela.columns[0].width = Cm(8.4)
    tabela.columns[1].width = Cm(8.4)
    for linha, (rotulo, texto) in enumerate(esquerda):
        _celula(tabela.cell(linha, 0), f"{rotulo}) {texto}", tamanho)
    for linha, (rotulo, texto) in enumerate(direita):
        _celula(tabela.cell(linha, 1), f"{rotulo}) {texto}", tamanho)
    # Depois de preencher: ``cell.text`` recria os parágrafos e apagaria o
    # ``keepNext`` aplicado antes.
    _nao_parte(tabela)


def _largura_figura(caminho: str) -> float:
    """Largura em cm: 14 cm, reduzida quando a proporção estoura a altura útil."""
    from docx.image.image import Image as ImagemDocx  # noqa: PLC0415 — API de imagem

    imagem = ImagemDocx.from_file(caminho)
    largura_px, altura_px = float(imagem.px_width), float(imagem.px_height)
    if largura_px <= 0 or altura_px <= 0:
        return LARGURA_FIGURA_CM
    return min(LARGURA_FIGURA_CM, ALTURA_MAXIMA_FIGURA_CM * largura_px / altura_px)


def _figura(doc: Documento, figura: Figura, tamanho: int) -> None:
    """Figura de apoio centralizada, com legenda e fonte, dentro da área útil."""
    doc.add_picture(figura.caminho, width=Cm(_largura_figura(figura.caminho)))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if figura.legenda:
        _paragrafo(doc, figura.legenda, tamanho)
    _paragrafo(doc, _citacao(figura.fonte), tamanho)


def _ficha_de_planejamento(doc: Documento, planejamento: Planejamento, tamanho: int) -> None:
    """Ficha do caderno do professor: só os campos preenchidos são impressos.

    Um parágrafo só, e não cinco: com uma linha por campo a ficha empurrava o
    campo de observações para uma página quase vazia na folha de 13 itens
    (medido em impressão).
    """
    campos = (
        ("Objetivo", planejamento.objetivo.strip()),
        ("Duração", planejamento.duracao.strip()),
        ("Metodologia", planejamento.metodologia.strip()),
        ("Recursos", "; ".join(planejamento.recursos)),
        ("Público/PDI", planejamento.publico.strip()),
    )
    partes = [f"{rotulo}: {valor}" for rotulo, valor in campos if valor]
    _paragrafo(doc, "Planejamento", tamanho, negrito=True, junto=True)
    _paragrafo(doc, " · ".join(partes), tamanho, espaco_depois=4)


def _caixa_de_vocabulario(doc: Documento, palavras: Sequence[str], tamanho: int) -> None:
    """Caixa de vocabulário no topo da folha (GAP-6 da Fase 4).

    O caderno de referência adaptado à mão abre com as palavras-chave que
    percorrem as tarefas; a v1.1 só tinha banco de palavras nos itens de
    completar. A caixa é uma frase só, com o rótulo em negrito — uma palavra por
    linha ocuparia meia página no suporte 3, que repete o topo em cada tarefa.
    """
    tabela = doc.add_table(rows=1, cols=1)
    tabela.style = "Table Grid"
    tabela.columns[0].width = Cm(16.8)
    paragrafo = tabela.cell(0, 0).paragraphs[0]
    paragrafo.paragraph_format.space_before = Pt(0)
    paragrafo.paragraph_format.space_after = Pt(0)
    paragrafo.paragraph_format.line_spacing = 1.0
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
    rotulo = paragrafo.add_run("Vocabulário: ")
    rotulo.bold = True
    palavras_run = paragrafo.add_run(" · ".join(palavras))
    for run in (rotulo, palavras_run):
        run.font.name = FONTE
        run.font.size = Pt(tamanho)


def _pagina_do_professor(
    doc: Documento, atividade: AtividadeEntrada, tamanho: int, nome_gabarito: str | None
) -> None:
    """Página final de uso do professor — nunca junto do que o estudante recebe."""
    doc.add_page_break()
    _paragrafo(doc, "Registro da mediação — página de uso do professor", tamanho, negrito=True)
    _paragrafo(
        doc,
        "Esta página não vai para o estudante: destaque antes de entregar a folha.",
        tamanho,
    )
    if atividade.planejamento is not None:
        _ficha_de_planejamento(doc, atividade.planejamento, tamanho)
    _paragrafo(doc, "Como aplicar", tamanho, negrito=True)
    for i, orientacao in enumerate(_orientacoes(atividade, nome_gabarito), start=1):
        # Lista numerada, não prosa: o respiro cheio do estilo em dez itens custava
        # 1,4 cm e deixava a página do professor com 2 mm de folga no pé.
        _paragrafo(doc, f"{i}. {orientacao}", tamanho, espaco_depois=4)
    if nome_gabarito:
        _paragrafo(doc, f"Arquivo do gabarito: {nome_gabarito}", tamanho, esquerda=True)
    _paragrafo(doc, "Marque uma coluna por item:", tamanho, junto=True)
    linhas = [(rotulo, "", "", "") for rotulo in _itens_do_registro(atividade)]
    # A coluna do item ganha o espaço que sobra das três colunas de marcação: com
    # 7,8 cm os rótulos quebravam em três linhas e empurravam o campo de
    # observações para a página seguinte.
    _tabela(
        doc,
        ("Item", "Sozinho", "Apoio parcial", "Apoio total"),
        linhas,
        (8.6, 2.7, 2.8, 2.7),
        tamanho,
    )
    # Sem linhas em branco entre as grades: com elas o campo de observações caía
    # sozinho numa quinta página, 90% vazia.
    data_tempo = _tabela(
        doc, ("Data da aplicação", "", "Tempo", ""), [], (4.8, 4.4, 2.4, 5.2), tamanho
    )
    # Uma linha só não dá para escrever a data à mão: a altura mínima deixa o
    # campo utilizável sem empurrar o resto para a página seguinte.
    data_tempo.rows[0].height = Cm(1.0)
    data_tempo.rows[0].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    _paragrafo(doc, "Observações do professor:", tamanho, junto=True, espaco_depois=0)
    observacoes = _tabela(doc, ("",), [], (16.8,), tamanho)
    # A ficha de planejamento ocupa o topo da página: a caixa de observações cede
    # 1,4 cm (ainda são três linhas de escrita à mão) para a página seguir
    # fechando em uma folha na grade de 13 itens.
    observacoes.rows[0].height = Cm(1.6 if atividade.planejamento is not None else 3.0)
    observacoes.rows[0].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST


_T = TypeVar("_T")


class _Folha:
    """Estado da paginação: no suporte 3 cada tarefa começa em página nova.

    O perfil de suporte 3 pede **uma tarefa por página** — a folha é entregue e
    recolhida tarefa a tarefa (GAP-7 da Fase 4). O suporte 2 continua em folha
    corrida: a quebra só entra quando o nível é 3.
    """

    def __init__(
        self,
        doc: Documento,
        tamanho: int,
        uma_por_pagina: bool,
        vocabulario: Sequence[str] = (),
    ) -> None:
        self.doc = doc
        self.tamanho = tamanho
        self.uma_por_pagina = uma_por_pagina
        self.vocabulario = vocabulario
        self.tem_conteudo = False

    def comecar(self) -> None:
        """Abre uma tarefa: quebra a página quando a anterior já tem conteúdo.

        No suporte 3 a caixa de vocabulário volta no topo de cada página: a
        tarefa anterior já foi recolhida e a página precisa se resolver sozinha,
        como o banco de palavras.
        """
        if self.uma_por_pagina and self.tem_conteudo:
            self.doc.add_page_break()
            if self.vocabulario:
                _caixa_de_vocabulario(self.doc, self.vocabulario, self.tamanho)
        self.tem_conteudo = True


def _secao(
    folha: _Folha,
    instrucao: str,
    preambulo: Sequence[str],
    itens: Sequence[_T],
    desenhar: Callable[[_T], None],
    fontes: str,
    *,
    respiro: bool = False,
) -> None:
    """Um formato da folha: instrução (com pré-âmbulo), itens e fontes.

    No suporte 2 a página é contínua: instrução e fontes saem uma vez. No
    suporte 3 cada item ganha a própria página e repete instrução, pré-âmbulo
    (banco de palavras) e fontes — a página anterior já foi recolhida.
    """
    if not itens:
        return
    por_pagina = folha.uma_por_pagina
    if not por_pagina:
        if instrucao:
            _paragrafo(folha.doc, instrucao, folha.tamanho, junto=True)
        for linha in preambulo:
            _paragrafo(folha.doc, linha, folha.tamanho, junto=True)
    for item in itens:
        if por_pagina:
            folha.comecar()
            if instrucao:
                _paragrafo(folha.doc, instrucao, folha.tamanho, junto=True)
            for linha in preambulo:
                _paragrafo(folha.doc, linha, folha.tamanho, junto=True)
        desenhar(item)
        if por_pagina:
            # O respiro entre a grade e o bloco de fontes vale também na página
            # única: sem ele a linha "Fontes:" encosta na borda da tabela.
            if respiro:
                _paragrafo(folha.doc, "", folha.tamanho)
            if fontes:
                _paragrafo(folha.doc, fontes, folha.tamanho)
    if not por_pagina:
        if respiro:
            _paragrafo(folha.doc, "", folha.tamanho)
        if fontes:
            _paragrafo(folha.doc, fontes, folha.tamanho)
    folha.tem_conteudo = True


def _item_parear(
    doc: Documento,
    numero: int,
    conjunto: ItemParearIguais,
    total: int,
    tamanho: int,
    rng: random.Random,
) -> None:
    """Um conjunto de palavras iguais; o número só aparece com mais de um."""
    if total > 1:
        _paragrafo(doc, f"{numero})", tamanho, junto=True)
    esquerda, direita = montar_parear_iguais(conjunto.palavras, rng)
    _tabela_de_colunas(doc, esquerda, direita, tamanho)


def _item_marcar(doc: Documento, numero: int, marcar: ItemMarcar, tamanho: int) -> None:
    _paragrafo(doc, f"{numero}) {marcar.enunciado}", tamanho)
    if marcar.frase:
        _paragrafo(doc, marcar.frase, tamanho)
    _paragrafo(
        doc,
        "        ".join(f"( ) {opcao}" for opcao in marcar.opcoes),
        tamanho,
        esquerda=True,
    )


def _item_vf(doc: Documento, numero: int, vf: ItemVerdadeiroFalso, tamanho: int) -> None:
    _paragrafo(doc, f"{numero}) {vf.afirmacao}", tamanho)
    _paragrafo(doc, "( ) Verdadeiro        ( ) Falso", tamanho, esquerda=True)


def _item_ordenar(
    doc: Documento, rotulo: str, ordenacao: ItemOrdenar, tamanho: int, rng: random.Random
) -> None:
    _paragrafo(doc, f"{rotulo}{ordenacao.enunciado}", tamanho, junto=True)
    for embaralhado in montar_ordenar(ordenacao.itens, rng):
        _paragrafo(doc, f"(    ) {embaralhado}", tamanho, esquerda=True)


def _item_completar(doc: Documento, numero: int, completar: ItemCompletar, tamanho: int) -> None:
    _paragrafo(
        doc,
        f"{numero}) {completar.frase_com_lacuna} {_citacao(completar.fonte)}",
        tamanho,
    )


def _tabela_ligar(doc: Documento, pares: list[ParLigar], tamanho: int, rng: random.Random) -> None:
    esquerda, direita, _gab = montar_ligar(pares, rng)
    _tabela_de_colunas(doc, esquerda, direita, tamanho)


def _montar_folha(
    atividade: AtividadeEntrada, tamanho: int, rng: random.Random, nome_gabarito: str | None = None
) -> Documento:
    """A folha do estudante: começa diretamente pelo conteúdo pedagógico."""
    doc = Document()
    _configurar_pagina(doc, tamanho)
    folha = _Folha(
        doc,
        tamanho,
        uma_por_pagina=atividade.nivel_suporte == 3,
        vocabulario=atividade.vocabulario,
    )
    if atividade.vocabulario:
        _caixa_de_vocabulario(doc, atividade.vocabulario, tamanho)

    for bloco in atividade.blocos:
        # No suporte 3 cada bloco de leitura é uma tarefa: o texto e a pergunta
        # que o acompanham ficam na mesma página.
        folha.comecar()
        _paragrafo(doc, bloco.texto, tamanho)
        _paragrafo(doc, _citacao(bloco.fonte), tamanho)
        if bloco.pergunta:
            _paragrafo(doc, bloco.pergunta, tamanho)

    for figura in atividade.figuras:
        _figura(doc, figura, tamanho)

    _secao(
        folha,
        "Ligue as palavras iguais — escreva a letra e o número no caderno:",
        (),
        list(enumerate(atividade.itens_parear, start=1)),
        lambda par: _item_parear(doc, par[0], par[1], len(atividade.itens_parear), tamanho, rng),
        f"Fontes: {_fontes_unicas([item.fonte for item in atividade.itens_parear])}",
        respiro=True,
    )

    _secao(
        folha,
        "Marque com um X a opção certa — pode pintar ou circular:",
        (),
        list(enumerate(atividade.itens_marcar, start=1)),
        lambda par: _item_marcar(doc, par[0], par[1], tamanho),
        f"Fontes: {_fontes_unicas([item.fonte for item in atividade.itens_marcar])}",
    )

    _secao(
        folha,
        "Leia cada frase e marque Verdadeiro ou Falso:",
        (),
        list(enumerate(atividade.itens_vf, start=1)),
        lambda par: _item_vf(doc, par[0], par[1], tamanho),
        f"Fontes: {_fontes_unicas([item.fonte for item in atividade.itens_vf])}",
    )

    # Com um único bloco o enunciado do professor já é o comando. Repetir a
    # instrução genérica e numerá-la ("1) Numere os acontecimentos…") fazia a
    # instrução parecer o primeiro item da ordenação — visto na impressão.
    varios = len(atividade.itens_ordenar) > 1
    _secao(
        folha,
        "Numere os itens na ordem certa, começando por 1:" if varios else "",
        (),
        list(enumerate(atividade.itens_ordenar, start=1)),
        lambda par: _item_ordenar(doc, f"{par[0]}) " if varios else "", par[1], tamanho, rng),
        f"Fontes: {_fontes_unicas([item.fonte for item in atividade.itens_ordenar])}",
    )

    if atividade.itens_completar:
        banco = montar_banco_palavras(atividade.itens_completar, rng)
        # Cada item de completar já carrega a citação no próprio texto: não há
        # linha "Fontes:" deste formato.
        _secao(
            folha,
            "Complete com as palavras do banco:",
            (" | ".join(banco),),
            list(enumerate(atividade.itens_completar, start=1)),
            lambda par: _item_completar(doc, par[0], par[1], tamanho),
            "",
        )

    # Uma tabela de ligar é uma tarefa só: a seção tem um item (o conjunto de
    # pares) e o respiro mantém o bloco de fontes fora da borda da grade.
    _secao(
        folha,
        "Ligue as colunas — escreva a letra e o número no caderno:",
        (),
        [atividade.pares_ligar] if atividade.pares_ligar else [],
        lambda _pares: _tabela_ligar(doc, atividade.pares_ligar, tamanho, rng),
        f"Fontes: {_fontes_unicas([par.fonte for par in atividade.pares_ligar])}",
        respiro=True,
    )

    if atividade.registro_mediacao:
        _pagina_do_professor(doc, atividade, tamanho, nome_gabarito)

    rodape = doc.sections[0].footer.paragraphs[0]
    rodape.text = f"{MARCA_RASCUNHO} · template {VERSAO_TEMPLATE}"
    return doc


def _montar_gabarito(atividade: AtividadeEntrada, tamanho: int) -> Documento:
    """Arquivo separado — o gabarito nunca junto à folha do estudante.

    Cada formato abre com o próprio título: sem ele, imprimir o gabarito dava uma
    sequência de "1)" sem referência a qual item da folha respondem.
    """
    doc = Document()
    _configurar_pagina(doc, tamanho)
    _paragrafo(doc, f"Gabarito — tema: {atividade.tema} ({atividade.ano})", tamanho)
    if atividade.itens_parear:
        _paragrafo(
            doc, "Parear iguais — cada palavra liga à palavra idêntica:", tamanho, negrito=True
        )
        for i, parear in enumerate(atividade.itens_parear, start=1):
            _paragrafo(doc, f"{i}) {', '.join(parear.palavras)}", tamanho)
    if atividade.itens_marcar:
        _paragrafo(doc, "Marcar — opção certa:", tamanho, negrito=True)
        for i, marcar in enumerate(atividade.itens_marcar, start=1):
            _paragrafo(doc, f"{i}) {marcar.correta}", tamanho)
    if atividade.itens_vf:
        _paragrafo(doc, "Verdadeiro ou falso:", tamanho, negrito=True)
        for i, vf in enumerate(atividade.itens_vf, start=1):
            resposta = "V" if vf.verdadeiro else "F"
            correcao = "" if vf.verdadeiro else f" — o correto é: {vf.correcao}"
            _paragrafo(doc, f"{i}) {resposta}{correcao}", tamanho)
    if atividade.itens_ordenar:
        _paragrafo(doc, "Ordenar — sequência certa:", tamanho, negrito=True)
        for i, ordenar in enumerate(atividade.itens_ordenar, start=1):
            sequencia = "; ".join(f"{n}. {valor}" for n, valor in enumerate(ordenar.itens, start=1))
            _paragrafo(doc, f"{i}) {sequencia}", tamanho)
    if atividade.itens_completar:
        _paragrafo(doc, "Completar — palavra de cada lacuna:", tamanho, negrito=True)
        for i, completar in enumerate(atividade.itens_completar, start=1):
            _paragrafo(doc, f"{i}) {completar.resposta}", tamanho)
    if atividade.pares_ligar:
        _paragrafo(doc, "Ligar colunas:", tamanho, negrito=True)
        for i, par in enumerate(atividade.pares_ligar, start=1):
            letra = "abcdef"[i - 1]
            _paragrafo(
                doc, f"{letra} → {i} ({par.esquerda.strip()} = {par.direita.strip()})", tamanho
            )
    return doc


def _metadados(doc: Documento, atividade: AtividadeEntrada) -> None:
    props = doc.core_properties
    props.title = atividade.tema
    props.category = f"template {VERSAO_TEMPLATE}"
    props.comments = (
        f"catálogo CRMG ({atividade.habilidade.codigo}, p. {atividade.habilidade.pagina}); "
        f"gerado em {date.today().isoformat()}"
    )


def _slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    alfanumerico = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-").lower()
    return (alfanumerico or "atividade")[:60]


def gerar_folhas(
    atividade: AtividadeEntrada, saida_dir: Path, tamanho: int, semente: int
) -> tuple[Path, Path | None]:
    """Grava a folha e, se pedido, o gabarito separado; devolve os caminhos.

    A mesma ``semente`` produz o mesmo layout (determinismo reproduzível; a
    semente usada fica registrada no ``registros.jsonl``).
    """
    saida_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(semente)
    slug = _slug(atividade.tema)
    nome_gabarito = f"{slug}-gabarito.docx" if atividade.gabarito else None
    doc = _montar_folha(atividade, tamanho, rng, nome_gabarito)
    _metadados(doc, atividade)
    caminho = saida_dir / f"{slug}.docx"
    doc.save(str(caminho))
    gabarito: Path | None = None
    if nome_gabarito:
        gab = _montar_gabarito(atividade, tamanho)
        _metadados(gab, atividade)
        gabarito = saida_dir / nome_gabarito
        gab.save(str(gabarito))
    return caminho, gabarito


def remover_marca_rascunho(arquivo: Path) -> None:
    """``finalizar``: remove a marca do rodapé; a versão do template permanece."""
    doc = Document(str(arquivo))
    for secao in doc.sections:
        for paragrafo in secao.footer.paragraphs:
            if MARCA_RASCUNHO in paragrafo.text:
                paragrafo.text = f"template {VERSAO_TEMPLATE}"
    doc.save(str(arquivo))


__all__ = ["gerar_folhas", "remover_marca_rascunho"]
