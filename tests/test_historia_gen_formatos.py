"""Testes dos formatos de baixa exigência do template 1.3.

Parear iguais (mesma palavra nas duas colunas), ordenação (itens embaralhados,
gabarito com a sequência correta) e figura de apoio (imagem local inserida, com
legenda e citação). Também cobre as recusas: imagem ausente ou em formato não
aceito, palavra/iitem repetido e parear duplicado entre itens.
"""

from __future__ import annotations

import base64
import json
import random
from pathlib import Path
from typing import Any

from docx import Document

from src.historia_gen.catalogo.carregar import carregar_catalogo
from src.historia_gen.docx_out import gerar_folhas
from src.historia_gen.entrada import carregar_entrada, validar_atividade
from src.historia_gen.formatos import montar_ordenar, montar_parear_iguais
from src.historia_gen.modelos import AtividadeEntrada
from src.historia_gen.registro import registrar_geracao
from tests.historia_gen_fixtures import atividade_fixture, catalogo_fixture, fonte_fixture

# 1×1 transparente — basta um PNG válido para o python-docx medir e inserir.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _atividade(**substituicoes: Any) -> AtividadeEntrada:
    return AtividadeEntrada.model_validate(atividade_fixture(**substituicoes))


def _texto(doc: Document) -> str:
    return "\n".join(p.text for p in doc.paragraphs)


def _parear(palavras: list[str] | None = None) -> dict[str, Any]:
    return {"palavras": palavras or ["Roma", "Tibre", "Lácio", "Senado"], "fonte": fonte_fixture()}


def _ordenar() -> dict[str, Any]:
    return {
        "enunciado": "Numere os acontecimentos na ordem em que ocorreram.",
        "itens": ["Fundação de Roma", "Fim da monarquia", "Início do Império"],
        "fonte": fonte_fixture(),
    }


def _entrada(tmp_path: Path, **substituicoes: Any) -> Any:
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(atividade_fixture(**substituicoes), ensure_ascii=False), encoding="utf-8"
    )
    return carregar_entrada(caminho)[0]


def _catalogo(tmp_path: Path) -> dict[str, Any]:
    return carregar_catalogo(catalogo_fixture(tmp_path / "cat"))


def test_parear_iguais_imprime_as_mesmas_palavras_nas_duas_colunas(tmp_path: Path) -> None:
    folha, gabarito = gerar_folhas(
        _atividade(itens_parear=[_parear()], gabarito=True), tmp_path, 11, 42
    )
    doc = Document(folha)
    assert "Ligue as palavras iguais" in _texto(doc)
    tabela = next(t for t in doc.tables if len(t.columns) == 2)
    esquerda = [tabela.cell(i, 0).text.split(") ", 1)[1] for i in range(len(tabela.rows))]
    direita = [tabela.cell(i, 1).text.split(") ", 1)[1] for i in range(len(tabela.rows))]
    esperado = ["Roma", "Tibre", "Lácio", "Senado"]
    assert sorted(esquerda) == sorted(direita) == sorted(esperado)
    # a resposta é a palavra idêntica: não há gabarito posicional para decorar
    assert gabarito is not None
    assert "Parear iguais" in _texto(Document(gabarito))


def test_ordenar_embaralha_na_folha_e_gabarito_traz_a_sequencia_correta(tmp_path: Path) -> None:
    itens = _ordenar()["itens"]
    folha, gabarito = gerar_folhas(
        _atividade(itens_ordenar=[_ordenar()], gabarito=True), tmp_path, 11, 42
    )
    texto = _texto(Document(folha))
    # com um único bloco, o enunciado do professor já é o comando: numerá-lo
    # fazia a instrução parecer o primeiro item
    assert "Numere os acontecimentos na ordem em que ocorreram." in texto
    assert "1) Numere" not in texto
    linhas = [linha for linha in texto.splitlines() if linha.startswith("(    ) ")]
    assert sorted(linha.removeprefix("(    ) ") for linha in linhas) == sorted(itens)
    assert "Ordene" not in texto  # nada de instrução de escrever a sequência
    assert gabarito is not None
    assert "Ordenar — sequência certa:" in _texto(Document(gabarito))
    assert "1) 1. Fundação de Roma; 2. Fim da monarquia" in _texto(Document(gabarito))


def test_parear_e_ordenar_deterministicos() -> None:
    palavras = ["Roma", "Tibre", "Lácio", "Senado"]
    assert montar_parear_iguais(palavras, random.Random(7)) == montar_parear_iguais(
        palavras, random.Random(7)
    )
    esquerda, direita = montar_parear_iguais(palavras, random.Random(7))
    assert sorted(palavra for _, palavra in esquerda) == sorted(palavra for _, palavra in direita)
    assert montar_ordenar(list("ABC"), random.Random(7)) == montar_ordenar(
        list("ABC"), random.Random(7)
    )


def test_embaralhamento_nunca_entrega_o_exercicio_resolvido() -> None:
    # com 2–3 itens, o sorteio cairia na ordem certa com frequência
    for semente in range(50):
        assert montar_ordenar(["Fundação", "República", "Império"], random.Random(semente)) != [
            "Fundação",
            "República",
            "Império",
        ]
    for semente in range(50):
        esquerda, direita = montar_parear_iguais(["Roma", "Tibre", "Lácio"], random.Random(semente))
        assert [p for _, p in esquerda] != [p for _, p in direita]


def test_figura_inserida_com_legenda_e_citacao(tmp_path: Path) -> None:
    imagem = tmp_path / "mapa.png"
    imagem.write_bytes(PNG_1X1)
    atividade = _atividade(
        figuras=[
            {"caminho": str(imagem), "legenda": "Mapa do Mediterrâneo.", "fonte": fonte_fixture()}
        ]
    )
    folha, _ = gerar_folhas(atividade, tmp_path, 11, 42)
    doc = Document(folha)
    assert len(doc.inline_shapes) == 1
    texto = _texto(doc)
    assert "Mapa do Mediterrâneo." in texto
    assert "fonte primária: Vidas dos Césares" in texto


def test_figura_ausente_recusa_a_folha(tmp_path: Path) -> None:
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(
            atividade_fixture(figuras=[{"caminho": "nao-existe.png", "fonte": fonte_fixture()}]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    atividade, _ = carregar_entrada(caminho)
    _, reprovacoes = validar_atividade(atividade, _catalogo(tmp_path), tmp_path)
    assert any(r.campo == "figuras" and "não encontrado" in r.motivo for r in reprovacoes)


def test_figura_com_extensao_nao_aceita_recusa(tmp_path: Path) -> None:
    (tmp_path / "figura.gif").write_bytes(PNG_1X1)
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(
            atividade_fixture(figuras=[{"caminho": "figura.gif", "fonte": fonte_fixture()}]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    atividade, _ = carregar_entrada(caminho)
    _, reprovacoes = validar_atividade(atividade, _catalogo(tmp_path), tmp_path)
    assert any(r.campo == "figuras" and "não aceito" in r.motivo for r in reprovacoes)


def test_figura_relativa_a_entrada_e_resolvida(tmp_path: Path) -> None:
    (tmp_path / "figura.png").write_bytes(PNG_1X1)
    atividade = _entrada(
        tmp_path, figuras=[{"caminho": "figura.png", "legenda": "Mapa.", "fonte": fonte_fixture()}]
    )
    substituida, reprovacoes = validar_atividade(atividade, _catalogo(tmp_path), tmp_path)
    assert reprovacoes == []
    assert Path(substituida.figuras[0].caminho).is_absolute()
    assert Path(substituida.figuras[0].caminho).is_file()


def test_parear_com_palavra_repetida_recusa_entrada(tmp_path: Path) -> None:
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(
            atividade_fixture(itens_parear=[_parear(["Roma", "Tibre", "roma"])]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is None
    assert any("repetição" in r.motivo for r in reprovacoes)


def test_ordenar_com_item_repetido_recusa_entrada(tmp_path: Path) -> None:
    item = {**_ordenar(), "itens": ["Fundação de Roma", "Fundação de Roma"]}
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(atividade_fixture(itens_ordenar=[item]), ensure_ascii=False), encoding="utf-8"
    )
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is None
    assert any("repetição" in r.motivo for r in reprovacoes)


def test_parear_duplicado_entre_itens_recusa_folha(tmp_path: Path) -> None:
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(
            atividade_fixture(
                itens_parear=[_parear(), _parear(["Senado", "Roma", "Lácio", "Tibre"])]
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    atividade, _ = carregar_entrada(caminho)
    _, reprovacoes = validar_atividade(atividade, _catalogo(tmp_path), tmp_path)
    assert any(r.campo == "itens_parear" for r in reprovacoes)


def test_registro_conta_os_formatos_usados(tmp_path: Path) -> None:
    atividade = _atividade(itens_parear=[_parear()], itens_ordenar=[_ordenar()])
    log = registrar_geracao(tmp_path, atividade.model_dump())
    registro = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert registro["formatos"]["itens_parear"] == 1
    assert registro["formatos"]["itens_ordenar"] == 1
    assert registro["formatos"]["itens_completar"] == 2
    assert registro["formatos"]["pares_ligar"] == 2
    assert registro["formatos"]["figuras"] == 0
