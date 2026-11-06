"""Log de auditoria append-only — um ``registros.jsonl`` para muitas gerações.

Padrão do ``drive-audit``: um registro para muitos arquivos. Cada geração
acrescenta uma linha; o ``finalizar`` acrescenta a linha de aprovação.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def registrar(pasta: Path, evento: dict[str, Any]) -> Path:
    """Acrescenta uma linha JSON ao ``registros.jsonl`` da pasta."""
    pasta.mkdir(parents=True, exist_ok=True)
    log = pasta / "registros.jsonl"
    linha = json.dumps({"data_hora": _agora(), **evento}, ensure_ascii=False)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(linha + "\n")
    return log


def registrar_geracao(pasta: Path, atividade: dict[str, Any], **campos: Any) -> Path:
    """Linha padrão de uma geração (tema, habilidade, versões, semente, arquivos)."""
    return registrar(
        pasta,
        {
            "evento": "geracao",
            "tema": atividade["tema"],
            "ano": atividade["ano"],
            "modo": atividade["modo"],
            "nivel_suporte": atividade.get("nivel_suporte"),
            "registro_mediacao": atividade.get("registro_mediacao", False),
            "planejamento": atividade.get("planejamento") is not None,
            "habilidade": atividade["habilidade"]["codigo"],
            "pagina_habilidade": atividade["habilidade"]["pagina"],
            "confirmado_pelo_professor": atividade["confirmado_pelo_professor"],
            "respostas_do_professor": atividade.get("respostas_do_professor", []),
            "formatos": {
                campo: len(atividade.get(campo) or [])
                for campo in (
                    "figuras",
                    "itens_parear",
                    "itens_marcar",
                    "itens_vf",
                    "itens_ordenar",
                    "itens_completar",
                    "pares_ligar",
                )
            },
            **campos,
        },
    )


def registrar_aprovacao(pasta_do_arquivo: Path, arquivo: Path) -> Path:
    """Linha de aprovação do ``finalizar`` — a revisão humana fica registrada."""
    return registrar(pasta_do_arquivo, {"evento": "aprovado", "arquivo": arquivo.name})
