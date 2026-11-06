"""Testes das regras de formato do documento e dos formatos determinísticos.

Para os dois modos: ausência de cabeçalho e de campos de identificação; marca
de rascunho no rodapé; fonte e corpo conforme o template (faixas 11–12 e
12–14); texto justificado; gabarito em arquivo separado; metadados fixos
gravados; após ``finalizar``, marca ausente e aprovação no log.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from src.historia_gen.docx_out import gerar_folhas, remover_marca_rascunho
from src.historia_gen.formatos import (
    montar_banco_palavras,
    montar_ligar,
    validar_itens,
    validar_pares,
)
from src.historia_gen.modelos import AtividadeEntrada
from src.historia_gen.registro import registrar_aprovacao
from src.historia_gen.template import FONTE, MARCA_RASCUNHO, VERSAO_TEMPLATE, tamanho_corpo
from tests.historia_gen_fixtures import atividade_fixture, fonte_fixture


def _atividade(**substituicoes: Any) -> AtividadeEntrada:
    return AtividadeEntrada.model_validate(atividade_fixture(**substituicoes))


def _gerar(
    tmp_path: Path, atividade: AtividadeEntrada, tamanho: int, semente: int = 42
) -> tuple[Path, Path | None]:
    return gerar_folhas(atividade, tmp_path, tamanho, semente)


def test_sem_cabecalho_e_sem_identificacao(tmp_path: Path) -> None:
    folha, _ = _gerar(tmp_path, _atividade(), 11)
    doc = Document(folha)
    secao = doc.sections[0]
    assert all(p.text.strip() == "" for p in secao.header.paragraphs)
    cabecalho_proibido = ("escola", "professor", "turma", "aluno", "data:")
    for p in doc.paragraphs:
        for proibido in cabecalho_proibido:
            assert proibido not in p.text.lower(), f"campo de identificação no corpo: {p.text!r}"


def test_marca_de_rascunho_no_rodape_e_metadados(tmp_path: Path) -> None:
    atividade = _atividade()
    folha, _ = _gerar(tmp_path, atividade, 11)
    doc = Document(folha)
    rodape = " ".join(p.text for p in doc.sections[0].footer.paragraphs)
    assert MARCA_RASCUNHO in rodape
    assert f"template {VERSAO_TEMPLATE}" in rodape
    assert doc.core_properties.title == atividade.tema
    assert doc.core_properties.category == f"template {VERSAO_TEMPLATE}"
    assert atividade.habilidade.codigo in (doc.core_properties.comments or "")


def test_corpo_e_justificado_conforme_template(tmp_path: Path) -> None:
    folha, _ = _gerar(tmp_path, _atividade(), 11)
    doc = Document(folha)
    estilo = doc.styles["Normal"]
    assert estilo.font.name == FONTE
    conteudo = [p for p in doc.paragraphs if p.text.strip()]
    assert conteudo
    assert all(p.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY for p in conteudo)
    tamanhos = {r.font.size.pt for p in conteudo for r in p.runs if r.font.size}
    assert tamanhos <= {11}


def test_modos_usam_faixas_de_tamanho(tmp_path: Path) -> None:
    assert tamanho_corpo("regular") == 11
    assert tamanho_corpo("adaptado") == 12
    assert tamanho_corpo("adaptado", 14) == 14
    assert tamanho_corpo("regular", 12) == 12
    import pytest

    with pytest.raises(ValueError, match="11 a 14"):
        tamanho_corpo("adaptado", 10)
    folha, _ = _gerar(tmp_path / "a", _atividade(modo="adaptado", gabarito=False), 12)
    doc = Document(folha)
    tamanhos = {r.font.size.pt for p in doc.paragraphs for r in p.runs if r.font.size}
    assert tamanhos == {12}


def test_gabarito_em_arquivo_separado(tmp_path: Path) -> None:
    folha, gabarito = _gerar(tmp_path, _atividade(gabarito=True), 11)
    assert gabarito is not None and gabarito != folha
    assert gabarito.name.endswith("-gabarito.docx")
    gab = Document(gabarito)
    texto = "\n".join(p.text for p in gab.paragraphs)
    assert "Gabarito" in texto
    assert "Roma" in texto  # resposta do primeiro item de completar
    folha_doc = Document(folha)
    assert "Gabarito" not in "\n".join(p.text for p in folha_doc.paragraphs)


def test_sem_espacos_de_resposta_e_fontes_citadas(tmp_path: Path) -> None:
    folha, _ = _gerar(tmp_path, _atividade(), 11)
    doc = Document(folha)
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "_____" not in texto.replace("___", "")  # só lacunas dos itens, sem linhas de resposta
    assert "fonte primária: Vidas dos Césares" in texto  # citação no corpo
    assert "Fontes:" in texto  # referências acompanham os pares de ligar
    linha_fontes = next(linha for linha in texto.splitlines() if "Fontes:" in linha)
    assert linha_fontes.count("Vidas dos Césares") == 1  # mesma fonte citada uma única vez


def test_finalizar_remove_marca_e_registra_aprovacao(tmp_path: Path) -> None:
    folha, _ = _gerar(tmp_path, _atividade(gabarito=False), 11)
    remover_marca_rascunho(folha)
    doc = Document(folha)
    rodape = " ".join(p.text for p in doc.sections[0].footer.paragraphs)
    assert MARCA_RASCUNHO not in rodape
    assert f"template {VERSAO_TEMPLATE}" in rodape  # a versão permanece
    assert doc.core_properties.category == f"template {VERSAO_TEMPLATE}"
    log = registrar_aprovacao(folha.parent, folha)
    linhas = log.read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(linhas[-1])["evento"] == "aprovado"


def _atividade_com_pergunta(**substituicoes: Any) -> AtividadeEntrada:
    bloco = {**atividade_fixture()["blocos"][0], "pergunta": "O que mudou no trabalho?"}
    return _atividade(modo="adaptado", blocos=[bloco], **substituicoes)


def test_registro_de_mediacao_so_quando_pedido(tmp_path: Path) -> None:
    sem_registro, _ = _gerar(tmp_path / "sem", _atividade_com_pergunta(), 12)
    texto_sem = "\n".join(p.text for p in Document(sem_registro).paragraphs)
    assert "Registro da mediação" not in texto_sem
    assert "Como aplicar" not in texto_sem

    folha, gabarito = _gerar(
        tmp_path / "com",
        _atividade_com_pergunta(
            registro_mediacao=True,
            orientacoes_aplicacao=["Recortar as fichas antes da aula."],
        ),
        12,
    )
    assert gabarito is not None
    doc = Document(folha)
    textos = [p.text for p in doc.paragraphs]
    texto = "\n".join(textos)

    # a folha do estudante continua começando pelo conteúdo pedagógico
    assert textos[0] == atividade_fixture()["blocos"][0]["texto"]
    # a página do professor vem depois de uma quebra de página e se anuncia
    assert 'w:type="page"' in doc.element.xml
    assert "Registro da mediação — página de uso do professor" in texto
    assert "não vai para o estudante" in texto
    # orientações: as da folha e depois as do professor
    assert "No banco de palavras, apontar a palavra certa" in texto
    assert "No ligar, peça a letra e o número" in texto
    assert gabarito.name in texto
    assert texto.index("No banco de palavras") < texto.index("Recortar as fichas")
    # última coisa da página é o campo de observações
    assert textos[-1] == "Observações do professor:"

    registro = next(t for t in doc.tables if t.rows[0].cells[0].text == "Item")
    assert [c.text for c in registro.rows[0].cells] == [
        "Item",
        "Sozinho",
        "Apoio parcial",
        "Apoio total",
    ]
    # 1 pergunta de bloco + 2 itens de completar + 1 bloco de ligar
    assert len(registro.rows) == 1 + 1 + 2 + 1
    assert registro.rows[1].cells[0].text.startswith("Leitura 1: O que mudou no trabalho?")
    assert registro.rows[2].cells[0].text.startswith("Completar 1: A cidade de")
    assert registro.rows[4].cells[0].text == "Ligar colunas (2 pares)"
    assert all(c.text == "" for r in registro.rows[1:] for c in r.cells[1:])
    # a coluna do item é a larga: as três de marcação são estreitas (o rótulo
    # quebrava em três linhas e empurrava a página do professor para uma quinta)
    assert registro.columns[0].width > registro.columns[1].width


def test_pagina_do_professor_cabe_numa_pagina(tmp_path: Path) -> None:
    """O registro inteiro fecha numa página: o campo de observações não cai fora.

    Medido em impressão (LibreOffice + pymupdf) no template 1.6: instruções,
    grade e caixa de observações terminam a 23,0 cm de 25,7 cm úteis. O teste
    guarda as duas decisões que produziram isso — rótulo colado na caixa e
    espaço de escrita suficiente — sem depender do renderizador.
    """
    folha, _ = _gerar(
        tmp_path,
        _atividade_com_pergunta(
            registro_mediacao=True,
            itens_marcar=[
                _item_marcar(
                    enunciado="Olhe o mapa e responda: o mar que o Império Romano "
                    "contornava por inteiro era o"
                )
            ],
        ),
        11,
    )
    doc = Document(folha)
    rotulo = next(p for p in doc.paragraphs if p.text == "Observações do professor:")
    assert rotulo.paragraph_format.keep_with_next is True
    assert rotulo.paragraph_format.space_after.pt == 0
    caixa = doc.tables[-1]
    assert caixa.rows[0].height.pt >= 80  # 3,0 cm de área de escrita
    # o rótulo longo entra resumido: na coluna do item cabem duas linhas
    grade = next(t for t in doc.tables if t.rows[0].cells[0].text == "Item")
    resumo = next(r.cells[0].text for r in grade.rows if r.cells[0].text.startswith("Marcar 1"))
    assert resumo.startswith("Marcar 1: Olhe o mapa")
    assert resumo.endswith("…") and len(resumo) <= 58


def test_ficha_de_planejamento_na_pagina_do_professor(tmp_path: Path) -> None:
    """GAP-2 residual: objetivo, duração, metodologia, recursos e público/PDI."""
    folha, _ = _gerar(
        tmp_path,
        _atividade_com_pergunta(
            registro_mediacao=True,
            planejamento={
                "objetivo": "Reconhecer a passagem da monarquia para a república.",
                "duracao": "2 aulas de 50 min",
                "metodologia": "Leitura mediada e marcação.",
                "recursos": ["Folha impressa", "Lápis"],
                "publico": "Estudante com TEA, suporte 2",
            },
        ),
        12,
    )
    textos = [p.text for p in Document(folha).paragraphs]
    assert "Planejamento" in textos
    ficha = next(t for t in textos if t.startswith("Objetivo:"))
    assert "Objetivo: Reconhecer a passagem da monarquia para a república." in ficha
    assert "Duração: 2 aulas de 50 min" in ficha
    assert "Metodologia: Leitura mediada e marcação." in ficha
    assert "Recursos: Folha impressa; Lápis" in ficha
    assert "Público/PDI: Estudante com TEA, suporte 2" in ficha
    # a ficha abre a página do professor, antes das orientações de aplicação
    assert next(i for i, t in enumerate(textos) if t == "Planejamento") < textos.index(
        "Como aplicar"
    )
    # com a ficha, a caixa de observações cede espaço (3,0 → 1,6 cm)
    assert Document(folha).tables[-1].rows[0].height.pt < 50


def test_ficha_de_planejamento_imprime_so_campos_preenchidos(tmp_path: Path) -> None:
    folha, _ = _gerar(
        tmp_path,
        _atividade_com_pergunta(
            registro_mediacao=True, planejamento={"objetivo": "Comparar fontes históricas."}
        ),
        12,
    )
    textos = [p.text for p in Document(folha).paragraphs]
    ficha = next(t for t in textos if t.startswith("Objetivo:"))
    assert ficha == "Objetivo: Comparar fontes históricas."


def test_suporte_3_tem_uma_tarefa_por_pagina(tmp_path: Path) -> None:
    """GAP-7: no suporte 3 cada tarefa começa em página nova e se resolve sozinha.

    Folha da fixture: 1 bloco de leitura + 2 de marcar + 2 de completar + 1 de
    ligar = 6 tarefas, 6 páginas. Cada página repete instrução, banco de
    palavras e fontes, porque a anterior já foi recolhida.
    """
    atividade = _atividade_com_pergunta(
        nivel_suporte=3,
        itens_marcar=[_item_marcar(), _item_marcar(enunciado="Pinte a outra palavra certa.")],
    )
    folha, _ = _gerar(tmp_path, atividade, 12)
    doc = Document(folha)
    textos = [p.text for p in doc.paragraphs]
    assert doc.element.xml.count('w:type="page"') == 5
    assert textos.count("Marque com um X a opção certa — pode pintar ou circular:") == 2
    banco = next(t for t in textos if " | " in t and "___" not in t)
    assert textos.count(banco) == 2  # banco repetido em cada página de completar
    assert sum(1 for t in textos if t.startswith("Fontes:")) == 3  # 2 marcar + 1 ligar
    # a folha continua começando pelo conteúdo pedagógico — sem título
    assert textos[0].startswith("Roma surgiu no Lácio")


def test_suporte_2_segue_em_folha_corrida(tmp_path: Path) -> None:
    atividade = _atividade_com_pergunta(
        nivel_suporte=2,
        itens_marcar=[_item_marcar(), _item_marcar(enunciado="Pinte a outra palavra certa.")],
    )
    folha, _ = _gerar(tmp_path, atividade, 12)
    doc = Document(folha)
    textos = [p.text for p in doc.paragraphs]
    assert doc.element.xml.count('w:type="page"') == 0
    assert textos.count("Marque com um X a opção certa — pode pintar ou circular:") == 1


def _item_marcar(**substituicoes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "enunciado": "Pinte a palavra que completa a frase.",
        "frase": "A ___ do Sul fica no continente africano.",
        "opcoes": ["África", "Ásia", "Europa"],
        "correta": "África",
        "fonte": fonte_fixture(),
    }
    base.update(substituicoes)
    return base


def _vf(afirmacao: str, verdadeiro: bool, correcao: str = "") -> dict[str, Any]:
    return {
        "afirmacao": afirmacao,
        "verdadeiro": verdadeiro,
        "correcao": correcao,
        "fonte": fonte_fixture(),
    }


def test_itens_de_marcar_e_vf_impressos_com_espaco_de_marcacao(tmp_path: Path) -> None:
    atividade = _atividade_com_pergunta(
        itens_marcar=[_item_marcar()],
        itens_vf=[
            _vf("Angola fica na Europa.", False, "Angola fica na África."),
            _vf("Gana ficou independente em 1957.", True),
        ],
    )
    folha, gabarito = _gerar(tmp_path, atividade, 12)
    doc = Document(folha)
    textos = [p.text for p in doc.paragraphs]
    texto = "\n".join(textos)

    # marcar: comando, frase de apoio e opções com espaço de marcação
    assert "Marque com um X a opção certa" in texto
    assert "1) Pinte a palavra que completa a frase." in texto
    assert "A ___ do Sul fica no continente africano." in texto
    assert "( ) África" in texto and "( ) Ásia" in texto and "( ) Europa" in texto
    # a linha de opções é curta e alinhada à esquerda (justificar abriria a linha)
    linha_opcoes = next(p for p in doc.paragraphs if "( ) África" in p.text)
    assert linha_opcoes.alignment == WD_ALIGN_PARAGRAPH.LEFT

    # V/F: uma decisão por afirmação, sem escrever
    assert "Leia cada frase e marque Verdadeiro ou Falso:" in texto
    assert "1) Angola fica na Europa." in texto
    assert "2) Gana ficou independente em 1957." in texto
    assert texto.count("( ) Verdadeiro") == 2

    # ordem de exigência: marcar antes de completar
    assert texto.index("Marque com um X") < texto.index("Complete com as palavras do banco")

    # instrução não pode ficar órfã no pé da página, com o item/tabela na seguinte
    for inicio in (
        "Marque com um X",
        "Leia cada frase",
        "Complete com as palavras",
        "Ligue as colunas",
    ):
        instrucao = next(p for p in doc.paragraphs if p.text.startswith(inicio))
        assert instrucao.paragraph_format.keep_with_next is True

    assert gabarito is not None
    gab = Document(gabarito)
    gab_texto = "\n".join(p.text for p in gab.paragraphs)
    assert "1) África" in gab_texto
    assert "1) F — o correto é: Angola fica na África." in gab_texto
    assert "2) V" in gab_texto


def test_grades_nao_partem_entre_paginas(tmp_path: Path) -> None:
    """Todas as linhas menos a última seguem a seguinte: a grade não se parte.

    Na conferência de impressão da atividade de Roma, o ligar deixou uma linha
    órfã na página seguinte — ``cantSplit`` sozinho não impede a quebra entre
    linhas.
    """
    folha, _ = _gerar(tmp_path, _atividade(registro_mediacao=True), 11)
    doc = Document(folha)
    grades = [t for t in doc.tables if len(t.rows) > 1]
    assert grades
    for grade in grades:
        for linha in grade.rows[:-1]:
            for celula in linha.cells:
                for paragrafo in celula.paragraphs:
                    assert paragrafo.paragraph_format.keep_with_next is True


def test_quantidade_questoes_conta_marcar_e_vf() -> None:
    atividade = _atividade(
        itens_marcar=[_item_marcar()],
        itens_vf=[_vf("A.", True), _vf("B.", True)],
    )
    # 2 itens de completar + 2 pares de ligar (fixture) + 1 marcar + 2 V/F
    assert atividade.total_questoes == 2 + 2 + 1 + 2


def test_banco_de_palavras_deterministico_e_sem_duplicata(tmp_path: Path) -> None:
    itens = _atividade().itens_completar
    banco_a = montar_banco_palavras(itens, random.Random(42))
    banco_b = montar_banco_palavras(itens, random.Random(42))
    assert banco_a == banco_b  # mesma semente → mesmo layout
    caixas = [p.casefold() for p in banco_a]
    assert len(caixas) == len(set(caixas))  # sem duplicata ambígua
    assert validar_itens(itens) == []


def test_ligar_deterministico_e_validado(tmp_path: Path) -> None:
    pares = _atividade().pares_ligar
    esq_a, dir_a, gab_a = montar_ligar(pares, random.Random(42))
    esq_b, dir_b, gab_b = montar_ligar(pares, random.Random(42))
    assert (esq_a, dir_a, gab_a) == (esq_b, dir_b, gab_b)
    assert sorted(esq_a) == sorted(esq_b)
    assert validar_pares(pares) == []


def test_ligar_reprova_duplicata_ambigua(tmp_path: Path) -> None:
    dados = atividade_fixture()
    dados["pares_ligar"][1]["esquerda"] = dados["pares_ligar"][0]["esquerda"]
    pares = AtividadeEntrada.model_validate(dados).pares_ligar
    problemas = validar_pares(pares)
    assert problemas and "esquerda" in problemas[0]


def test_caixa_de_vocabulario_no_topo_da_folha(tmp_path: Path) -> None:
    atividade = _atividade(vocabulario=["ÁFRICA", "ANGOLA", "MANDELA", "PAZ"])
    folha, _ = _gerar(tmp_path, atividade, 11)
    tabelas = Document(folha).tables
    # a primeira tabela da folha é a caixa: ela abre a página do estudante
    assert tabelas[0].cell(0, 0).text == "Vocabulário: ÁFRICA · ANGOLA · MANDELA · PAZ"


def test_vocabulario_volta_em_cada_pagina_do_suporte_3(tmp_path: Path) -> None:
    # no suporte 3 a tarefa anterior já foi recolhida: a página repete a caixa
    atividade = _atividade(modo="adaptado", nivel_suporte=3, vocabulario=["ÁFRICA", "PAZ"])
    folha, _ = _gerar(tmp_path, atividade, 12)
    caixas = [t for t in Document(folha).tables if t.cell(0, 0).text.startswith("Vocabulário: ")]
    # 1 bloco de leitura + 2 itens de completar + 1 table de ligar = 4 páginas
    assert len(caixas) == 4
