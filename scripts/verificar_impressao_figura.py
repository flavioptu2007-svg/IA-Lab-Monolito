#!/usr/bin/env python3
"""Verificação de impressão da figura de apoio (template 1.4).

Os testes de unidade usam um PNG 1×1: provam que a imagem entra no `.docx`, não
que ela cabe na página. Este script faz a verificação que faltava, com figuras
**reais** (larga, quadrada e retrato), o catálogo versionado, conversão para PDF
no LibreOffice e medição do retângulo da imagem na página.

Confere, por figura: largura ≤ 14 cm, altura ≤ 17 cm, imagem inteira dentro das
margens de 2 cm, centralizada, legenda e citação abaixo dela e na mesma página.

Uso: python3 scripts/verificar_impressao_figura.py [--manter]
Sai 1 quando alguma medida sai da faixa.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
EXEMPLO = RAIZ / "src/historia_gen/exemplos/atividade-exemplo.json"
PT_CM = 72 / 2.54
MARGEM_PT = 2.0 * PT_CM
LARGURA_MAX_CM = 14.0
ALTURA_MAX_CM = 17.0
TOLERANCIA_CM = 0.1
FONTE_CITACAO = "fonte primária:"


def _fonte(tamanho: int):  # noqa: ANN202 — objeto PIL
    from PIL import ImageFont

    for nome in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


def _desenhar(caminho: Path, largura: int, altura: int, titulo: str) -> Path:
    """Figura de verdade: moldura, título e barras de legenda (não é 1×1)."""
    from PIL import Image, ImageDraw

    imagem = Image.new("RGB", (largura, altura), "white")
    desenho = ImageDraw.Draw(imagem)
    margem = max(6, largura // 40)
    desenho.rectangle(
        [margem, margem, largura - margem, altura - margem],
        outline="black",
        width=max(2, largura // 200),
    )
    grande, pequena = _fonte(max(18, largura // 22)), _fonte(max(14, largura // 34))
    desenho.text((margem * 3, margem * 3), titulo, fill="black", font=grande)
    linhas = ("Rio Tibre", "Colina do Palatino", "Muralha de Sérvio", "Via Ápia")
    passo = (altura - margem * 8) // (len(linhas) + 1)
    for i, texto in enumerate(linhas):
        y = margem * 5 + i * passo
        desenho.rectangle(
            [margem * 3, y, largura - margem * 3, y + max(3, altura // 90)], fill="black"
        )
        desenho.text((margem * 3, y + max(6, altura // 70)), texto, fill="black", font=pequena)
    imagem.save(caminho)
    return caminho


def _montar(entrada: Path, saida: Path) -> int:
    sys.path.insert(0, str(RAIZ))
    from src.historia_gen.__main__ import main

    return main(["montar", str(entrada), "--saida", str(saida)])


def _imagem_no_pdf(pdf: Path) -> tuple[Any, Any]:
    import pymupdf

    documento = pymupdf.open(pdf)
    for indice in range(documento.page_count):
        pagina = documento[indice]
        imagens = pagina.get_images(full=True)
        if imagens:
            return pagina, pagina.get_image_bbox(imagens[0])
    raise AssertionError("nenhuma imagem no PDF gerado")


def _medir(nome: str, pdf: Path, legenda: str) -> list[str]:
    """Mede a figura impressa e devolve a lista de problemas (vazia = tudo certo)."""
    pagina, bbox = _imagem_no_pdf(pdf)
    largura_cm = (bbox.x1 - bbox.x0) / PT_CM
    altura_cm = (bbox.y1 - bbox.y0) / PT_CM
    centro_pagina = pagina.rect.width / 2
    centro_imagem = (bbox.x0 + bbox.x1) / 2
    texto = pagina.get_text("text")
    problemas: list[str] = []

    def faixa(rotulo: str, valor: float, maximo: float) -> None:
        if valor > maximo + TOLERANCIA_CM:
            problemas.append(f"{rotulo} {valor:.2f} cm > {maximo} cm")
        print(f"    {rotulo}: {valor:.2f} cm (máx. {maximo} cm)")

    print(f"  {nome}: página {pagina.number + 1}")
    faixa("largura", largura_cm, LARGURA_MAX_CM)
    faixa("altura", altura_cm, ALTURA_MAX_CM)
    if abs(centro_imagem - centro_pagina) / PT_CM > TOLERANCIA_CM:
        problemas.append(
            f"não centralizada: centro {centro_imagem / PT_CM:.2f} cm × "
            f"página {centro_pagina / PT_CM:.2f} cm"
        )
    print(f"    centro: {centro_imagem / PT_CM:.2f} cm (página {centro_pagina / PT_CM:.2f} cm)")
    if bbox.x0 < MARGEM_PT - 1 or bbox.x1 > pagina.rect.width - MARGEM_PT + 1:
        problemas.append("imagem invade a margem horizontal")
    if bbox.y0 < MARGEM_PT - 1 or bbox.y1 > pagina.rect.height - MARGEM_PT + 1:
        problemas.append("imagem invade a margem vertical (pé ou topo da página)")
    print(
        f"    posição: x {bbox.x0 / PT_CM:.2f}–{bbox.x1 / PT_CM:.2f} cm · "
        f"y {bbox.y0 / PT_CM:.2f}–{bbox.y1 / PT_CM:.2f} cm"
    )

    if legenda not in texto:
        problemas.append("legenda ausente na página da figura")
    else:
        achados = pagina.search_for(legenda)
        if not achados:
            problemas.append("legenda não localizada na página")
        elif achados[0].y0 < bbox.y1 - 2:
            problemas.append("legenda acima da figura")
    if FONTE_CITACAO not in texto:
        problemas.append("citação da fonte ausente na página da figura")
    print(f"    legenda e citação: {'ok' if not problemas else 'ver abaixo'}")
    return problemas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manter", action="store_true", help="mantém a pasta temporária")
    args = ap.parse_args(argv)
    if shutil.which("soffice") is None:
        print("soffice (LibreOffice) ausente — sem ele não há medição de impressão")
        return 1

    base = Path(tempfile.mkdtemp(prefix="figura-"))
    casos = {
        "larga (1600×900)": (1600, 900),
        "quadrada (1000×1000)": (1000, 1000),
        "retrato (700×1400)": (700, 1400),
    }
    falhas: list[str] = []
    original = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    for nome, (largura, altura) in casos.items():
        caso = base / nome.split(" ")[0]
        caso.mkdir(parents=True, exist_ok=True)
        imagem = _desenhar(caso / "figura.png", largura, altura, "Mapa de Roma antiga")
        legenda = f"Figura — {nome}."
        dados = dict(original)
        dados["figuras"] = [
            {
                "caminho": str(imagem),
                "legenda": legenda,
                "fonte": original["blocos"][0]["fonte"],
            }
        ]
        entrada = caso / "atividade.json"
        entrada.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        codigo = _montar(entrada, caso)
        if codigo != 0:
            falhas.append(f"{nome}: montagem recusada")
            continue
        # A pasta tem folha e gabarito: a medição é na folha, nunca no gabarito.
        docx = next(p for p in caso.glob("*.docx") if not p.stem.endswith("-gabarito"))
        conversao = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(caso), str(docx)],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        pdf = docx.with_suffix(".pdf")
        if not pdf.exists():
            falhas.append(f"{nome}: conversão para PDF falhou ({conversao.stderr.strip()[:120]})")
            continue
        problemas = _medir(nome, pdf, legenda)
        falhas += [f"{nome}: {p}" for p in problemas]

    if args.manter:
        print(f"\npasta preservada: {base}")
    if falhas:
        print("\nFALHOU:")
        for falha in falhas:
            print(f"  - {falha}")
        return 1
    print("\nfigura de apoio: 3 proporções medidas, todas dentro da faixa de impressão")
    return 0


if __name__ == "__main__":
    sys.exit(main())
