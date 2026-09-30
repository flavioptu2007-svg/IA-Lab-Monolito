"""Testes do gerador de textos — modo template (offline/determinístico)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # ~/Projetos

import os

# Força modo offline ANTES de importar o gerador.
os.environ.setdefault("LEITURAIA_OFFLINE", "1")

from leituraia.generator import gerar_texto  # noqa: E402
from leituraia.models import GerarTextoRequest  # noqa: E402


@pytest.fixture
def req() -> GerarTextoRequest:
    return GerarTextoRequest(
        ano="7",
        disciplina="História",
        tema="Feudalismo",
        palavras=250,
        nivel="fundamental2",
    )


class TestGerarTexto:
    def test_retorna_texto_gerado(self, req):
        resultado = gerar_texto(req)
        assert resultado.titulo
        assert len(resultado.texto) > 100

    def test_modo_template_quando_offline(self, req):
        resultado = gerar_texto(req)
        assert resultado.origem == "template"

    def test_mencionar_tema(self, req):
        resultado = gerar_texto(req)
        assert "Feudalismo".lower() in resultado.texto.lower()

    def test_tem_perguntas(self, req):
        resultado = gerar_texto(req)
        assert len(resultado.perguntas) >= 1
        for p in resultado.perguntas:
            assert p.pergunta
            assert p.resposta

    def test_deterministico_no_modo_template(self, req):
        r1 = gerar_texto(req)
        r2 = gerar_texto(req)
        assert r1.texto == r2.texto

    def test_validacao_de_palavras(self):
        with pytest.raises(Exception):
            GerarTextoRequest(ano="7", disciplina="História", tema="X", palavras=10)
