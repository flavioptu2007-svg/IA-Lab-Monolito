"""Agente gerador de atividades de História (regular e adaptada TEA suporte 2).

O modo adaptado aceita ``nivel_suporte: 3`` (GAP-7): a folha sai com uma
tarefa por página. A receita de redação do suporte 3 segue pendente (Q1).
A caixa de vocabulário opcional (GAP-6) abre a folha e, no suporte 3, volta no
topo de cada tarefa.

Dois passos com naturezas diferentes:

1. **Redação** — sessão de assistente de IA com acesso à web (fora deste
   pacote), guiada pelos arquivos em ``prompts/``, que grava um
   ``atividade.json`` estruturado com fontes de cada fato.
2. **Montagem** — este pacote: pipeline determinístico que valida a entrada
   contra o catálogo fechado do CRMG, recusa folha com problema e produz o
   ``.docx`` pelo template versionado. Nenhum modelo de linguagem roda aqui.

Design: ``docs/designs/agente-atividades-historia-design.md`` (aprovado em
2026-11-01). O catálogo só é fonte válida de geração com a revisão registrada
(``revisao_aprovada`` no JSON do catálogo) depois da conferência literal contra
o PDF (``catalogo-conferir``).
"""

from __future__ import annotations

VERSAO_TEMPLATE = "1.9"
__all__ = ["VERSAO_TEMPLATE"]
