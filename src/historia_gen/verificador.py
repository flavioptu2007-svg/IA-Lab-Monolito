"""Verificador de códigos — módulo puro, ponto único de recusa por código.

Consulta exata por (código, ano) contra o catálogo carregado; nenhum acesso a
modelo, web ou disco além do catálogo passado como argumento. A correção
semântica da atribuição tema→habilidade não é papel dele (é decisão pedagógica
confirmada pelo professor na sessão de redação); a checagem adversária de
entrada inválida pertence a ``entrada.py`` (nível do fluxo).
"""

from __future__ import annotations

from typing import Any

from src.historia_gen.modelos import Reprovacao


def verificar(catalogo: dict[str, Any], codigo: str, ano: str) -> dict[str, Any] | None:
    """Consulta exata por (código, ano); retorna a habilidade ou ``None``."""
    for h in catalogo["habilidades"]:
        if h["codigo"] == codigo and h["ano"] == ano:
            return h
    return None


def verificar_folha(
    catalogo: dict[str, Any], pares_codigo_ano: list[tuple[str, str]]
) -> list[Reprovacao]:
    """Valida todos os códigos impressos de uma folha; reprova a folha inteira."""
    reprovacoes: list[Reprovacao] = []
    for codigo, ano in pares_codigo_ano:
        if verificar(catalogo, codigo, ano) is None:
            reprovacoes.append(
                Reprovacao(
                    campo="habilidade",
                    motivo=f"código {codigo!r} não existe no catálogo para {ano} — folha recusada",
                )
            )
    return reprovacoes
