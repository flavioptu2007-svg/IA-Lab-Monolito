"""Carga e validação do catálogo fechado.

Três níveis, com fallha fechada:

* ``carregar_catalogo`` — estrutura (esquemas, códigos únicos, contagens).
* ``verificar_integridade`` — recalcula os dois hashes do PDF versionado.
* ``carregar_para_geracao`` — exige ``revisao_aprovada=true``; sem isso,
  o catálogo não é fonte válida de geração.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.historia_gen.modelos import HabilidadeCatalogo, MetaCatalogo

DADOS = Path(__file__).parent / "dados"
CATALOGO_PADRAO = DADOS / "catalogo_crmg_ef_anos_finais.json"
PDF_PADRAO = DADOS / "fonte_oficial" / "crmg_infantil_ef.pdf"


def carregar_catalogo(caminho: Path) -> dict[str, Any]:
    """Carrega e valida a estrutura do catálogo (sem exigir revisão aprovada)."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    try:
        dados["meta"] = MetaCatalogo.model_validate(dados["meta"]).model_dump()
        dados["habilidades"] = [
            HabilidadeCatalogo.model_validate(h).model_dump() for h in dados["habilidades"]
        ]
    except (KeyError, ValidationError) as exc:
        msg = f"catálogo com estrutura inválida ({caminho.name}): {exc}"
        raise ValueError(msg) from exc
    codigos = [h["codigo"] for h in dados["habilidades"]]
    duplicados = {c for c in codigos if codigos.count(c) > 1}
    if duplicados:
        msg = f"catálogo com códigos duplicados: {sorted(duplicados)}"
        raise ValueError(msg)
    return dados


def _hashes(pdf_path: Path) -> tuple[str, str]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha = hashlib.sha256()
    pdf_path.read_bytes()  # falha com FileNotFoundError se ausente
    with pdf_path.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            md5.update(bloco)
            sha.update(bloco)
    return md5.hexdigest(), sha.hexdigest()


def verificar_integridade(meta: dict[str, Any], pdf_path: Path) -> list[str]:
    """Recalcula MD5/SHA-256 do PDF e compara com o registrado no catálogo."""
    problemas: list[str] = []
    if not pdf_path.exists():
        return [f"PDF-base ausente: {pdf_path}"]
    md5, sha = _hashes(pdf_path)
    if md5 != meta["pdf_md5"]:
        problemas.append(f"pdf_md5 divergente: registrado {meta['pdf_md5']}, calculado {md5}")
    if sha != meta["pdf_sha256"]:
        problemas.append(f"pdf_sha256 divergente: registrado {meta['pdf_sha256']}, calculado {sha}")
    return problemas


def buscar_habilidade(catalogo: dict[str, Any], codigo: str, ano: str) -> dict[str, Any] | None:
    """Consulta exata por (código, ano) — o único caminho de entrada de código."""
    for h in catalogo["habilidades"]:
        if h["codigo"] == codigo and h["ano"] == ano:
            return h
    return None


def carregar_para_geracao(
    caminho: Path | None = None, pdf_path: Path | None = None
) -> dict[str, Any]:
    """Catálogo válido para geração: estrutura + integridade + revisão aprovada."""
    caminho = caminho or CATALOGO_PADRAO
    pdf = pdf_path or PDF_PADRAO
    catalogo = carregar_catalogo(caminho)
    problemas = verificar_integridade(catalogo["meta"], pdf)
    if problemas:
        raise ValueError("; ".join(problemas))
    if not catalogo["meta"]["revisao_aprovada"]:
        raise ValueError(
            "catálogo sem revisão manual aprovada (revisao_aprovada=false) — "
            "não é fonte válida de geração; conferir contra o PDF e registrar a aprovação"
        )
    return catalogo


def validar_catalogo_versionado(
    caminho: Path | None = None, pdf_path: Path | None = None
) -> tuple[bool, list[str]]:
    """Checagem completa do catálogo versionado (subcomando ``catalogo-validar``).

    Retorna ``(ok, linhas)``. Divergência de estrutura/hashes/contagens falha;
    revisão pendente e ano de acesso anterior ao corrente são avisos (não falham).
    """
    caminho = caminho or CATALOGO_PADRAO
    pdf = pdf_path or PDF_PADRAO
    linhas: list[str] = []
    ok = True
    try:
        catalogo = carregar_catalogo(caminho)
    except ValueError as exc:
        return False, [str(exc)]
    meta = catalogo["meta"]
    linhas.append(
        f"catálogo: {len(catalogo['habilidades'])} habilidades · versão {meta['versao']!r} · "
        f"acesso {meta['data_acesso']}"
    )
    problemas = verificar_integridade(meta, pdf)
    if problemas:
        ok = False
        linhas += [f"FALHA: {p}" for p in problemas]
    else:
        linhas.append("integridade: MD5 e SHA-256 conferem com o PDF versionado")

    contagens: dict[str, int] = {}
    for h in catalogo["habilidades"]:
        contagens[h["ano"]] = contagens.get(h["ano"], 0) + 1
    esperadas = meta["contagens_esperadas"] or contagens
    for ano in sorted(esperadas):
        obtido, esperado = contagens.get(ano, 0), esperadas[ano]
        if obtido != esperado:
            ok = False
            linhas.append(f"FALHA: contagem de {ano}: esperado {esperado}, obtido {obtido}")
        else:
            linhas.append(f"contagem {ano}: {obtido} ✓")

    total_paginas: int | None = None
    if pdf.exists():
        try:
            import pymupdf  # noqa: PLC0415 — dependência de dev, import tardio

            total_paginas = pymupdf.open(pdf).page_count
        except ImportError:
            total_paginas = None
    paginas_ruins = [
        h["codigo"]
        for h in catalogo["habilidades"]
        if total_paginas and h["pagina"] > total_paginas
    ]
    if paginas_ruins:
        ok = False
        linhas.append(f"FALHA: páginas de origem fora do PDF: {paginas_ruins}")

    if meta["data_acesso"][:4] < str(date.today().year):
        linhas.append(
            f"AVISO: data_acesso ({meta['data_acesso']}) é de ano letivo anterior — "
            "reconfirmar a versão vigente no site da SEE-MG e atualizar o catálogo"
        )
    if not meta["revisao_aprovada"]:
        linhas.append(
            "AVISO: revisão manual PENDENTE (revisao_aprovada=false) — o catálogo não é "
            "fonte válida de geração até a conferência do professor"
        )
    else:
        quem = meta.get("revisado_por") or "responsável não informado"
        quando = f" em {meta['revisao_data']}" if meta.get("revisao_data") else ""
        metodo = f" — {meta['revisao_metodo']}" if meta.get("revisao_metodo") else ""
        linhas.append(f"revisão: aprovada por {quem}{quando}{metodo}")
    return ok, linhas
