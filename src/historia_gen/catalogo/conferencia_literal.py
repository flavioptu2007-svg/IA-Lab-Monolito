"""Conferência literal do catálogo contra o PDF oficial — checagem independente.

O extrator lê a grade desenhada da tabela; esta conferência relê a **camada de
texto** do PDF e confronta o que o catálogo registra para cada habilidade:
código, descrição, unidade temática, objeto de conhecimento e página. É a mesma
fidelidade de transcrição que o roteiro pede ao professor, feita por caminho
diferente do extrator — linha perdida, célula mesclada vazando, página trocada ou
texto cortado aparecem como divergência.

Limites declarados (o que a checagem **não** prova):

* hífen: o PDF usa o mesmo caractere para hífen real e para quebra de linha, então
  o confronto ignora hífens e não verifica onde eles caem;
* unidade temática e objeto vêm de células mescladas, que podem atravessar a
  quebra de página — por isso são procurados na página registrada e nas vizinhas;
* não é revisão pedagógica: se o código pertence ao tema é decisão humana, feita
  na sessão de redação (``confirmado_pelo_professor`` no ``atividade.json``).
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from src.historia_gen.modelos import Reprovacao

ROTULOS = {
    "descricao": "descrição",
    "unidade_tematica": "unidade temática",
    "objeto_conhecimento": "objeto de conhecimento",
}


def _normalizar(texto: str) -> str:
    """Texto comparável: mesma pontuação, sem ruído de hifenização."""
    texto = unicodedata.normalize("NFC", texto).replace("\u00ad", "")
    # Hífen real e hifenização usam o mesmo caractere no PDF; o confronto ignora
    # os dois (a queda do hífen não é verificável por esta via).
    texto = re.sub(r"-\s*", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _paginas(pdf_path: Path) -> dict[int, str]:
    """Texto normalizado por página **física** do PDF (1 = primeira)."""
    import pymupdf  # noqa: PLC0415 — dependência de dev, import tardio

    documento = pymupdf.open(pdf_path)
    return {i + 1: _normalizar(documento[i].get_text("text")) for i in range(documento.page_count)}


def conferir(catalogo: dict[str, Any], pdf_path: Path) -> list[Reprovacao]:
    """Confronta as 97 linhas com o texto do PDF; devolve as divergências."""
    paginas = _paginas(pdf_path)
    total = len(paginas)
    divergencias: list[Reprovacao] = []
    for habilidade in catalogo["habilidades"]:
        codigo = habilidade["codigo"]
        impressa = habilidade["pagina"]
        fisica = impressa + 1  # página física = impressa + 1 (folha de rosto)
        campo = f"catalogo:{codigo}"
        if fisica not in paginas:
            divergencias.append(
                Reprovacao(
                    campo=campo,
                    motivo=(
                        f"página impressa {impressa} (física {fisica}) não existe no PDF "
                        f"({total} páginas)"
                    ),
                )
            )
            continue
        texto = paginas[fisica]
        if not re.search(rf"(?<![A-Z0-9]){re.escape(codigo)}(?![A-Z0-9])", texto):
            divergencias.append(
                Reprovacao(
                    campo=campo,
                    motivo=f"código não aparece na página impressa {impressa} do PDF",
                )
            )
        vizinhas = " ".join(paginas.get(p, "") for p in (fisica - 1, fisica + 1))
        for nome, rotulo in ROTULOS.items():
            alvo = _normalizar(habilidade[nome])
            if alvo in texto:
                continue
            # Somente as células mescladas podem atravessar a quebra de página.
            if nome != "descricao" and alvo in vizinhas:
                continue
            onde = (
                f"página impressa {impressa}"
                if nome == "descricao"
                else f"página impressa {impressa} nem nas vizinhas"
            )
            divergencias.append(
                Reprovacao(
                    campo=campo,
                    motivo=f"{rotulo} do catálogo não confere com o texto do PDF na {onde}",
                )
            )
    return divergencias


def aprovar(caminho: Path, responsavel: str, metodo: str) -> None:
    """Registra a aprovação no ``meta`` do catálogo — só depois de ``conferir``

    sem divergências. Grava só o bloco ``meta`` (o resto do arquivo é do
    extrator); o ``indent=1`` é o mesmo da extração, para o diff ficar no campo.
    """
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if "meta" not in dados:
        msg = f"{caminho} não tem bloco meta — não é um catálogo"
        raise ValueError(msg)
    dados["meta"]["revisao_aprovada"] = True
    dados["meta"]["revisado_por"] = responsavel
    dados["meta"]["revisao_metodo"] = metodo
    dados["meta"]["revisao_data"] = date.today().isoformat()
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


__all__ = ["ROTULOS", "aprovar", "conferir"]
