"""Fábricas de fixtures para os testes do ``src.historia_gen``.

Constroem um catálogo pequeno (PDF real minúsculo + hashes reais) e um
``atividade.json`` válido — sem depender do estado de revisão do catálogo
versionado do repositório, que só se torna fonte de geração depois da revisão
manual do professor.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pymupdf

DIRETORIO_RAIZ = Path(__file__).resolve().parents[1]
CATALOGO_VERSIONADO = (
    DIRETORIO_RAIZ / "src/historia_gen/catalogo/dados/catalogo_crmg_ef_anos_finais.json"
)
PDF_VERSIONADO = (
    DIRETORIO_RAIZ / "src/historia_gen/catalogo/dados/fonte_oficial/crmg_infantil_ef.pdf"
)


def _pdf_minimo(caminho: Path) -> None:
    doc = pymupdf.open()
    pagina = doc.new_page()
    pagina.insert_text((72, 72), "fixture do catálogo")
    doc.save(caminho)


def _hashes(caminho: Path) -> tuple[str, str]:
    bruto = caminho.read_bytes()
    return (
        hashlib.md5(bruto, usedforsecurity=False).hexdigest(),
        hashlib.sha256(bruto).hexdigest(),
    )


def catalogo_fixture(pasta: Path, *, aprovado: bool = True) -> Path:
    """Catálogo pequeno com PDF-base real (miniatura) e hashes computados."""
    pasta.mkdir(parents=True, exist_ok=True)
    pdf = pasta / "pdf_base.pdf"
    _pdf_minimo(pdf)
    md5, sha = _hashes(pdf)
    habilidades = [
        {
            "codigo": "EF06HI01X",
            "descricao": "Identificar noções de tempo em registros da Roma Antiga (fixture).",
            "ano": "6º ano EF",
            "unidade_tematica": "História: tempo, espaço e formas de registros",
            "objeto_conhecimento": "A questão do tempo, sincronias e diacronias.",
            "pagina": 1,
            "tipo_modificacao": "alterada",
        },
        {
            "codigo": "EF07HI02",
            "descricao": "Identificar conexões entre Europa, América e África (fixture).",
            "ano": "7º ano EF",
            "unidade_tematica": "O mundo moderno e a conexão entre sociedades africanas, americanas e europeias",
            "objeto_conhecimento": "As rotas portuguesas na África.",
            "pagina": 1,
            "tipo_modificacao": "original",
        },
    ]
    meta = {
        "documento": "Catálogo fixture",
        "url_oficial": "https://exemplo.test/crmg",
        "url_pdf": "https://exemplo.test/crmg.pdf",
        "versao": "fixture",
        "data_acesso": "2026-11-02",
        "pdf_md5": md5,
        "pdf_sha256": sha,
        "escopo": "fixture",
        "contagens_esperadas": {"6º ano EF": 1, "7º ano EF": 1},
        "legenda_modificacoes": {"X": "Alterada"},
        "revisao_aprovada": aprovado,
        "revisado_por": "Teste automatizado" if aprovado else None,
        "extraido_em": "2026-11-02",
        "ferramenta": "fixture",
        "anomalias_do_documento": [],
    }
    caminho = pasta / "catalogo_fixture.json"
    caminho.write_text(
        json.dumps({"meta": meta, "habilidades": habilidades}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return caminho


def fonte_fixture(**substituicoes: Any) -> dict[str, Any]:
    fonte: dict[str, Any] = {
        "tipo": "primaria",
        "origem": "web",
        "obra": "Vidas dos Césares, Suetônio (fixture)",
        "autor": "Suetônio",
        "ano": "121",
        "url": "https://exemplo.test/fonte-original",
        "data_acesso": "2026-11-02",
    }
    fonte.update(substituicoes)
    return fonte


def atividade_fixture(**substituicoes: Any) -> dict[str, Any]:
    """Atividade válida: 2 itens de completar + 2 pares de ligar, gabarito ligado."""
    base: dict[str, Any] = {
        "tema": "Roma Antiga (teste automatizado)",
        "ano": "6º ano EF",
        "modo": "regular",
        "nivel_suporte": 2,
        "habilidade": {
            "codigo": "EF06HI01X",
            "descricao": "Identificar noções de tempo em registros da Roma Antiga (fixture).",
            "ano": "6º ano EF",
            "unidade_tematica": "História: tempo, espaço e formas de registros",
            "objeto_conhecimento": "A questão do tempo, sincronias e diacronias.",
            "pagina": 1,
            "tipo_modificacao": "alterada",
        },
        "confirmado_pelo_professor": True,
        "blocos": [
            {
                "texto": "Roma surgiu no Lácio e dominou o mar Mediterrâneo na Antiguidade (fixture).",
                "pergunta": "",
                "fonte": fonte_fixture(),
            }
        ],
        "itens_completar": [
            {
                "frase_com_lacuna": "A cidade de ___ foi fundada, segundo a lenda, pelos gêmeos Rômulo e Remo.",
                "resposta": "Roma",
                "distratores": ["Atenas", "Cartago"],
                "fonte": fonte_fixture(),
            },
            {
                "frase_com_lacuna": "O ___ era o espaço público central da vida política romana.",
                "resposta": "fórum",
                "distratores": ["coliseu", "aqueduto"],
                "fonte": fonte_fixture(),
            },
        ],
        "pares_ligar": [
            {
                "esquerda": "Rômulo e Remo",
                "direita": "lenda da fundação de Roma",
                "fonte": fonte_fixture(),
            },
            {
                "esquerda": "Fórum Romano",
                "direita": "centro político da cidade",
                "fonte": fonte_fixture(),
            },
        ],
        "quantidade_questoes": None,
        "gabarito": True,
        "registro_mediacao": False,
        "orientacoes_aplicacao": [],
        "observacoes_pedagogicas": "Fixture de teste automatizado.",
        "documento_apoio": "",
        "respostas_do_professor": [],
    }
    base.update(substituicoes)
    return base
