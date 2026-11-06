"""Extração assistida do catálogo de História (Anos Finais do EF) do CRMG.

Roda cerca de uma vez por ano, sobre o PDF oficial versionado em
``dados/fonte_oficial/``. Reconstrói a tabela do Organizador Curricular
(seção 15 — História) a partir da grade desenhada do PDF: cada faixa de
coluna (ANO | Unidades | Objetos | Habilidades) tem suas próprias fronteiras
horizontais, e as células mescladas aparecem como ausência de borda na faixa.

A saída é um **rascunho** — o catálogo só é válido depois da revisão manual
(o rascunho sai sempre com a revisão pendente; o arquivo versionado só volta a
ficar aprovado depois da nova conferência literal — ``catalogo-conferir``).

Uso:
    python3 src/historia_gen/catalogo/extraidor.py [--saida CAMINHO]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf

DADOS = Path(__file__).parent / "dados"
PDF_PADRAO = DADOS / "fonte_oficial" / "crmg_infantil_ef.pdf"

# faixas de coluna (coordenadas x do PDF oficial, estáveis entre páginas)
STRIPS = {"ano": (57.0, 92.0), "unid": (92.2, 169.9), "obj": (170.2, 247.9), "hab": (248.3, 538.6)}
FIS_INICIO, FIS_FIM = 566, 578  # páginas físicas do organizador (começa com o fim do 5º ano)
OFFSET_IMPRESSA = -1  # impressa = física - 1 (o PDF imprime o número no topo da página)
ANOS_FINAIS = ("6º ano EF", "7º ano EF", "8º ano EF", "9º ano EF")
CODE = re.compile(r"\((EF\d{2}HI\d{2}[A-Z]*)\)")
ANO_RE = re.compile(r"^(\d)º Ano$")
HIFEN_QUEBRA = re.compile(
    r"(\w)- (?=\w)"
)  # "civil- militar" -> "civil-militar" (hifenização de quebra de linha)


def _bordas_h(page: pymupdf.Page, x0: float, x1: float) -> list[float]:
    """Ys das fronteiras horizontais que atravessam a faixa [x0, x1]."""
    ys: set[float] = set()
    for d in page.get_drawings():
        for item in d["items"]:
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if (
                    abs(p1.y - p2.y) < 0.5
                    and min(p1.x, p2.x) <= x0 + 2
                    and max(p1.x, p2.x) >= x1 - 2
                ):
                    ys.add(round(p1.y, 1))
            elif item[0] == "re":
                r = item[1]
                if r.height < 1.5 and r.x0 <= x0 + 2 and r.x1 >= x1 - 2:
                    ys.add(round(r.y0, 1))
    return sorted(ys)


def _texto_na_faixa(page: pymupdf.Page, x0: float, x1: float, y0: float, y1: float) -> str:
    ws = [
        w
        for w in page.get_text("words")
        if x0 - 1 <= w[0] and w[2] <= x1 + 1 and y0 + 0.5 <= w[1] and w[3] <= y1 + 0.5
    ]
    ws.sort(key=lambda w: (round(w[1], 1), w[0]))
    return re.sub(r"\s+", " ", " ".join(w[4] for w in ws)).strip()


def _tipo_modificacao(codigo: str) -> str:
    m = re.match(r"EF\d{2}HI\d{2}([A-Z0-9]*)", codigo)
    suf = m.group(1) if m else ""
    if not suf:
        return "original"
    if suf == "X":
        return "alterada"
    if suf == "MG":
        return "criada"
    if re.fullmatch(r"[A-Z]", suf):
        return "desmembrada"
    if re.fullmatch(r"P\d", suf):
        return "progressao"
    return "desconhecida"


def extrair(pdf_path: Path) -> tuple[list[dict], list[str]]:
    doc = pymupdf.open(pdf_path)
    habilidades, avisos = [], []
    for pno in range(FIS_INICIO - 1, FIS_FIM):
        page = doc[pno]
        faixas = {}
        for nome, (x0, x1) in STRIPS.items():
            ys = [y for y in _bordas_h(page, x0, x1) if 66 < y < 800]
            faixas[nome] = [
                (a, b, _texto_na_faixa(page, x0, x1, a, b)) for a, b in zip(ys, ys[1:]) if b - a > 4
            ]
        if not faixas["hab"]:
            avisos.append(f"física {pno + 1}: sem células de Habilidades")
            continue
        for y0, y1, txt in faixas["hab"]:
            m = CODE.search(txt)
            if not m:
                if txt and txt != "Habilidades" and not re.fullmatch(r"\dº Ano", txt):
                    avisos.append(f"física {pno + 1} y={y0}: célula sem código: {txt[:60]!r}")
                continue
            ymeio = (y0 + y1) / 2

            def cel(faixa: str) -> str:
                for a, b, t in faixas[faixa]:
                    if a - 2 <= ymeio <= b + 2:
                        return t
                return ""

            man = ANO_RE.match(cel("ano"))
            habilidades.append(
                {
                    "codigo": m.group(1),
                    "descricao": HIFEN_QUEBRA.sub(r"\1-", txt[m.end() :].strip()),
                    "ano": f"{man.group(1)}º ano EF" if man else None,
                    "unidade_tematica": HIFEN_QUEBRA.sub(r"\1-", cel("unid")),
                    "objeto_conhecimento": HIFEN_QUEBRA.sub(r"\1-", cel("obj")),
                    "pagina": pno + 1 + OFFSET_IMPRESSA,
                    "tipo_modificacao": _tipo_modificacao(m.group(1)),
                }
            )
    return habilidades, avisos


def _conferir_contagens(habilidades: list[dict]) -> bool:
    """Contraprova contra as contagens registradas no catálogo versionado.

    Divergência significa extração incompleta (ou documento oficial atualizado):
    falha para forçar a revisão manual, em vez de gerar rascunho truncado.
    """
    catalogo = DADOS / "catalogo_crmg_ef_anos_finais.json"
    if not catalogo.exists():
        return True
    esperadas = json.loads(catalogo.read_text(encoding="utf-8"))["meta"]["contagens_esperadas"]
    obtidas = Counter(h["ano"] for h in habilidades)
    ok = True
    for ano, esperado in sorted(esperadas.items()):
        obtido = obtidas.get(ano, 0)
        marca = "✓" if obtido == esperado else "DIVERGENTE"
        print(f"contagem {ano}: {obtido} (registrado {esperado}) {marca}")
        ok = ok and obtido == esperado
    return ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, default=PDF_PADRAO, help="PDF oficial versionado")
    ap.add_argument("--saida", type=Path, default=DADOS / "rascunho_extracao.json")
    args = ap.parse_args(argv)

    todas, avisos = extrair(args.pdf)
    doc = pymupdf.open(args.pdf)
    bruto = len(CODE.findall("".join(doc[p].get_text() for p in range(FIS_INICIO - 1, FIS_FIM))))
    sem_ano = [h["codigo"] for h in todas if h["ano"] is None]
    escopo = [h for h in todas if h["ano"] in ANOS_FINAIS]
    print(
        f"códigos no texto bruto: {bruto} | células extraídas: {len(todas)} | "
        f"no escopo Anos Finais: {len(escopo)}"
    )
    print("por ano (escopo):", dict(Counter(h["ano"] for h in escopo)))
    duplicados = [c for c, n in Counter(h["codigo"] for h in escopo).items() if n > 1]
    if duplicados:
        print("DUPLICADOS:", duplicados)
    if sem_ano:
        print("SEM ANO IDENTIFICADO:", sem_ano)
    if avisos:
        print("avisos:")
        for a in avisos:
            print("  -", a)
    contagens_ok = _conferir_contagens(escopo)
    args.saida.write_text(
        json.dumps(
            {"meta": {"rascunho": True}, "habilidades": escopo}, ensure_ascii=False, indent=1
        )
    )
    print(f"rascunho gravado em {args.saida} — revisão manual obrigatória antes do uso")
    return 0 if len(todas) == bruto and not duplicados and not sem_ano and contagens_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
