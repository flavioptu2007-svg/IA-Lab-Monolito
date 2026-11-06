"""O template versionado é código: constantes nomeadas com valores concretos.

Mudança de formato = diff auditável + incremento de VERSAO_TEMPLATE (em
``__init__.py``). As faixas registradas no design: regular 11–12, adaptado
12–14 (``--fonte`` amplia até o limite).
"""

from __future__ import annotations

from src.historia_gen import VERSAO_TEMPLATE
from src.historia_gen.modelos import Modo

FONTE = "Arial"
TAMANHO_REGULAR = 11  # faixa aceita: 11–12
TAMANHO_ADAPTADO = 12  # faixa aceita: 12–14 (ampliável por --fonte)
MARGEM_CM = 2.0
TAMANHO_MIN, TAMANHO_MAX = 11, 14
MARCA_RASCUNHO = "RASCUNHO — revisar antes de imprimir"


def tamanho_corpo(modo: Modo, fonte_flag: int | None = None) -> int:
    """Tamanho do corpo em pontos, com a faixa do modo como limite."""
    base = TAMANHO_REGULAR if modo == "regular" else TAMANHO_ADAPTADO
    limite = 12 if modo == "regular" else 14
    if fonte_flag is None:
        return base
    if fonte_flag < TAMANHO_MIN or fonte_flag > TAMANHO_MAX:
        raise ValueError(f"--fonte aceita {TAMANHO_MIN} a {TAMANHO_MAX}")
    return max(base, min(fonte_flag, limite))


__all__ = [
    "FONTE",
    "MARCA_RASCUNHO",
    "MARGEM_CM",
    "TAMANHO_ADAPTADO",
    "TAMANHO_MAX",
    "TAMANHO_MIN",
    "TAMANHO_REGULAR",
    "VERSAO_TEMPLATE",
    "tamanho_corpo",
]
