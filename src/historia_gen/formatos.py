"""Montador determinístico de formatos — marcar, V/F, completar e ligar.

Sem custo de API: recebe as estruturas de ``modelos.py`` e produz as estruturas
de tabela para o montador ``.docx``. A semente é parametrizada — aleatória por
geração (registrada no log), fixa nos testes. Marcar e V/F não embaralham nada:
opções e afirmativas saem na ordem em que o professor as escreveu (o que está
impresso é o que foi revisado).
"""

from __future__ import annotations

import random

from src.historia_gen.modelos import (
    ItemCompletar,
    ItemMarcar,
    ItemOrdenar,
    ItemParearIguais,
    ItemVerdadeiroFalso,
    ParLigar,
)

ROTULOS = "abcdef"


def validar_itens(itens: list[ItemCompletar]) -> list[str]:
    """Duplicata ambígua: itens com resposta e distratores indistinguíveis."""
    problemas: list[str] = []
    vistos: dict[tuple[str, ...], int] = {}
    for i, item in enumerate(itens, start=1):
        chave = tuple(sorted({item.resposta, *item.distratores}, key=str.casefold))
        vistos[chave] = vistos.get(chave, 0) + 1
        if vistos[chave] == 2:
            problemas.append(f"item {i}: banco de palavras indistinguível de outro item")
    return problemas


def validar_pares(pares: list[ParLigar]) -> list[str]:
    """Pares balanceados e sem duplicata ambígua em qualquer coluna."""
    problemas: list[str] = []
    esq = [p.esquerda.strip().casefold() for p in pares]
    dire = [p.direita.strip().casefold() for p in pares]
    for rotulo, coluna in (("esquerda", esq), ("direita", dire)):
        duplicados = {v for v in coluna if coluna.count(v) > 1}
        if duplicados:
            problemas.append(f"coluna {rotulo} com valores duplicados: {sorted(duplicados)}")
    return problemas


def validar_marcar(itens: list[ItemMarcar]) -> list[str]:
    """Itens de marcar indistinguíveis entre si (mesmo comando e mesmas opções)."""
    problemas: list[str] = []
    vistos: dict[tuple[str, tuple[str, ...]], int] = {}
    for i, item in enumerate(itens, start=1):
        chave = (
            " ".join(item.enunciado.split()).casefold(),
            tuple(opcao.casefold() for opcao in item.opcoes),
        )
        vistos[chave] = vistos.get(chave, 0) + 1
        if vistos[chave] == 2:
            problemas.append(f"item {i}: mesmo comando e mesmas opções de outro item")
    return problemas


def validar_vf(itens: list[ItemVerdadeiroFalso]) -> list[str]:
    """Afirmações repetidas — a segunda não ensina nada e confunde a contagem."""
    problemas: list[str] = []
    vistos: dict[str, int] = {}
    for i, item in enumerate(itens, start=1):
        chave = " ".join(item.afirmacao.split()).casefold()
        vistos[chave] = vistos.get(chave, 0) + 1
        if vistos[chave] == 2:
            problemas.append(f"item {i}: afirmação repetida de outro item")
    return problemas


def validar_parear_iguais(itens: list[ItemParearIguais]) -> list[str]:
    """Mesmo conjunto de palavras em dois itens — o segundo não ensina nada."""
    problemas: list[str] = []
    vistos: dict[tuple[str, ...], int] = {}
    for i, item in enumerate(itens, start=1):
        chave = tuple(sorted(palavra.casefold() for palavra in item.palavras))
        vistos[chave] = vistos.get(chave, 0) + 1
        if vistos[chave] == 2:
            problemas.append(f"item {i}: mesmas palavras de outro item de parear")
    return problemas


def validar_ordenar(itens: list[ItemOrdenar]) -> list[str]:
    """Mesmo comando com a mesma sequência repetido entre itens."""
    problemas: list[str] = []
    vistos: dict[tuple[str, tuple[str, ...]], int] = {}
    for i, item in enumerate(itens, start=1):
        chave = (
            " ".join(item.enunciado.split()).casefold(),
            tuple(valor.casefold() for valor in item.itens),
        )
        vistos[chave] = vistos.get(chave, 0) + 1
        if vistos[chave] == 2:
            problemas.append(f"item {i}: mesma sequência de outro item de ordenar")
    return problemas


def montar_parear_iguais(
    palavras: list[str], rng: random.Random
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Duas colunas com as mesmas palavras, embaralhadas de forma independente."""
    esquerda = [(ROTULOS[i], palavra) for i, palavra in enumerate(palavras)]
    direita = [(str(i + 1), palavra) for i, palavra in enumerate(palavras)]
    rng.shuffle(esquerda)
    # Coluna da direita na mesma ordem da esquerda vira linha reta para baixo:
    # o exercício sai resolvido. Embaralha até a sequência de palavras diferir.
    sequencia_esquerda = [palavra for _, palavra in esquerda]
    for _ in range(50):
        rng.shuffle(direita)
        if [palavra for _, palavra in direita] != sequencia_esquerda:
            break
    return esquerda, direita


def montar_ordenar(itens: list[str], rng: random.Random) -> list[str]:
    """Itens embaralhados; a ordem correta (gabarito) é a da lista original.

    A sequência impressa nunca é a correta: com 2–3 itens o sorteio cairia na
    ordem certa com frequência e o item sairia resolvido.
    """
    embaralhados = list(itens)
    for _ in range(50):
        rng.shuffle(embaralhados)
        if embaralhados != list(itens):
            break
    return embaralhados


def montar_banco_palavras(itens: list[ItemCompletar], rng: random.Random) -> list[str]:
    """Respostas + distratores, únicos (sem distinguir maiúsculas), embaralhados."""
    palavras: dict[str, str] = {}
    for item in itens:
        for palavra in (item.resposta, *item.distratores):
            palavras.setdefault(palavra.strip().casefold(), palavra.strip())
    banco = list(palavras.values())
    rng.shuffle(banco)
    return banco


def montar_ligar(
    pares: list[ParLigar], rng: random.Random
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str, str]]]:
    """Duas colunas embaralhadas independentemente + gabarito rotulado.

    Retorna (coluna_esquerda, coluna_direita, gabarito), com rótulos ``a, b, c…``
    na esquerda e numéricos na direita; o gabarito liga cada rótulo ao par.
    """
    problemas = validar_pares(pares)
    if problemas:
        raise ValueError("; ".join(problemas))
    esquerda = [(ROTULOS[i], p.esquerda.strip()) for i, p in enumerate(pares)]
    direita = [(str(i + 1), p.direita.strip()) for i, p in enumerate(pares)]
    rng.shuffle(esquerda)
    rng.shuffle(direita)
    gabarito = [(ROTULOS[i], str(i + 1), p.fonte.obra) for i, p in enumerate(pares)]
    return esquerda, direita, gabarito
