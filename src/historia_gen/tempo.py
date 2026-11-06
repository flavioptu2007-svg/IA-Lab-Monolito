"""Q5 — linha de base do tempo de adaptação manual.

O que é automático aqui: guardar o registro, medir cada montagem e confrontar os
números. O que **não** é: a medição em si — cronometrar 1–2 adaptações reais
feitas sem o pipeline é trabalho humano (professor). Sem esse registro o módulo
se recusa a falar em ganho de tempo: ``comparar`` levanta ``SemLinhaDeBase`` em
vez de inventar um número.
"""

from __future__ import annotations

import csv
import json
import statistics
from dataclasses import dataclass
from datetime import date
from pathlib import Path

COLUNAS = ("data", "tema", "ano", "modo", "minutos", "quem", "observacao")
CAMINHO_PADRAO = Path("docs/historia_gen/q5-linha-de-base.csv")


class SemLinhaDeBase(ValueError):
    """Não há medição manual (ou geração medida) suficiente para comparar."""


@dataclass(frozen=True)
class MedicaoManual:
    data: str
    tema: str
    ano: str
    modo: str
    minutos: float
    quem: str
    observacao: str = ""


@dataclass(frozen=True)
class Comparacao:
    medicoes: int
    mediana_min: float
    montagens: int
    mediana_montagem_s: float

    @property
    def razao(self) -> float:
        """Quantas vezes a montagem é mais rápida que a adaptação manual."""
        montagem = self.mediana_montagem_s
        return (self.mediana_min * 60) / montagem if montagem > 0 else float("inf")


def registrar(
    caminho: Path,
    *,
    tema: str,
    ano: str,
    minutos: float,
    quem: str = "",
    modo: str = "adaptado",
    data: str | None = None,
    observacao: str = "",
) -> Path:
    """Acrescenta uma medição humana ao CSV (cria o cabeçalho se for a primeira)."""
    if minutos <= 0:
        msg = "minutos deve ser positivo — o tempo de uma adaptação real"
        raise ValueError(msg)
    if modo not in {"regular", "adaptado"}:
        msg = f"modo {modo!r} inválido (use 'regular' ou 'adaptado')"
        raise ValueError(msg)
    novo = not caminho.exists()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8", newline="") as fh:
        escritor = csv.writer(fh)
        if novo:
            escritor.writerow(COLUNAS)
        escritor.writerow(
            [
                data or date.today().isoformat(),
                tema,
                ano,
                modo,
                f"{minutos:g}",
                quem,
                observacao,
            ]
        )
    return caminho


def ler(caminho: Path) -> list[MedicaoManual]:
    """Lê o CSV de medições; arquivo ausente ou só com cabeçalho devolve vazio."""
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8") as fh:
        linhas = [linha for linha in csv.DictReader(fh) if (linha.get("tema") or "").strip()]
    return [
        MedicaoManual(
            data=linha["data"],
            tema=linha["tema"],
            ano=linha["ano"],
            modo=linha["modo"],
            minutos=float(linha["minutos"]),
            quem=linha.get("quem") or "",
            observacao=linha.get("observacao") or "",
        )
        for linha in linhas
    ]


def _duracoes(registros: Path) -> list[float]:
    """Durações de montagem registradas no ``registros.jsonl`` (só o que tem medida)."""
    if not registros.exists():
        msg = f"sem log de gerações em {registros} — montar uma folha antes de comparar"
        raise SemLinhaDeBase(msg)
    duracoes: list[float] = []
    for linha in registros.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        evento = json.loads(linha)
        if evento.get("evento") == "geracao" and "duracao_s" in evento:
            duracoes.append(float(evento["duracao_s"]))
    return duracoes


def comparar(caminho: Path, registros: Path) -> Comparacao:
    """Mediana manual × mediana da montagem; recusa comparar sem os dois lados."""
    medicoes = ler(caminho)
    if not medicoes:
        msg = (
            f"nenhuma medição manual registrada em {caminho} — cronometrar 1–2 adaptações "
            "reais (Q5) antes de comparar; sem isso não há afirmação de ganho de tempo"
        )
        raise SemLinhaDeBase(msg)
    duracoes = _duracoes(registros)
    if not duracoes:
        msg = f"nenhuma geração com duracao_s em {registros} — montar uma folha antes de comparar"
        raise SemLinhaDeBase(msg)
    return Comparacao(
        medicoes=len(medicoes),
        mediana_min=statistics.median(m.minutos for m in medicoes),
        montagens=len(duracoes),
        mediana_montagem_s=statistics.median(duracoes),
    )


__all__ = [
    "CAMINHO_PADRAO",
    "COLUNAS",
    "Comparacao",
    "MedicaoManual",
    "SemLinhaDeBase",
    "comparar",
    "ler",
    "registrar",
]
