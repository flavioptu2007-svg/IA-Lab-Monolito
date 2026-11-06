"""Conferência literal do catálogo contra o PDF e registro da aprovação.

Porta da Fase 1: a transcrição das 97 linhas confere com a camada de texto do
PDF oficial; uma descrição alterada ou uma página trocada aparecem como
divergência; e a aprovação registrada no ``meta`` libera a geração.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.historia_gen.catalogo.carregar import (
    carregar_catalogo,
    carregar_para_geracao,
    validar_catalogo_versionado,
)
from src.historia_gen.catalogo.conferencia_literal import aprovar, conferir
from tests.historia_gen_fixtures import CATALOGO_VERSIONADO, PDF_VERSIONADO


def test_conferencia_literal_passa_no_catalogo_versionado() -> None:
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    assert conferir(catalogo, PDF_VERSIONADO) == []


def test_conferencia_literal_pega_descricao_divergente() -> None:
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    alvo = catalogo["habilidades"][0]
    alvo["descricao"] = "Texto que não está no documento oficial."
    divergencias = conferir(catalogo, PDF_VERSIONADO)
    assert any(alvo["codigo"] in r.campo and "descrição" in r.motivo for r in divergencias)


def test_conferencia_literal_pega_pagina_trocada() -> None:
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    alvo = catalogo["habilidades"][0]
    alvo["pagina"] = 566  # página real do organizador, mas de outra habilidade
    divergencias = conferir(catalogo, PDF_VERSIONADO)
    assert any(alvo["codigo"] in r.campo for r in divergencias)


def test_conferencia_literal_pega_pagina_fora_do_pdf() -> None:
    catalogo = carregar_catalogo(CATALOGO_VERSIONADO)
    catalogo["habilidades"][0]["pagina"] = 9999
    divergencias = conferir(catalogo, PDF_VERSIONADO)
    assert any("não existe no PDF" in r.motivo for r in divergencias)


def test_aprovar_grava_meta_e_libera_geracao(tmp_path: Path) -> None:
    copia = tmp_path / "catalogo.json"
    copia.write_text(CATALOGO_VERSIONADO.read_text(encoding="utf-8"), encoding="utf-8")
    aprovar(copia, "Prof. Teste", "conferência literal automática")
    meta = json.loads(copia.read_text(encoding="utf-8"))["meta"]
    assert meta["revisao_aprovada"] is True
    assert meta["revisado_por"] == "Prof. Teste"
    assert meta["revisao_metodo"] == "conferência literal automática"
    assert meta["revisao_data"]
    assert carregar_para_geracao(copia, PDF_VERSIONADO)["meta"]["revisao_aprovada"] is True


def test_catalogo_versionado_esta_aprovado() -> None:
    """O gate só abre com a transcrição conferida e o registro no meta."""
    caminho = CATALOGO_VERSIONADO
    catalogo = carregar_catalogo(caminho)
    meta = catalogo["meta"]
    assert meta["revisao_aprovada"] is True
    assert meta["revisado_por"]
    assert meta["revisao_metodo"]
    assert conferir(catalogo, PDF_VERSIONADO) == []
    ok, linhas = validar_catalogo_versionado()
    assert ok
    assert any("revisão: aprovada" in linha for linha in linhas)
