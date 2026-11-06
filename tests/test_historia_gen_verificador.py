"""Testes do verificador (consulta exata) e da checagem adversária do fluxo.

Porta de aceite da Fase 2: código fora do catálogo reprova a folha; habilidade
de outro ano recusa a entrada; confirmação do professor ausente recusa a
montagem; fato sem FonteRef recusa a montagem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.historia_gen.entrada import carregar_entrada, validar_atividade
from src.historia_gen.verificador import verificar, verificar_folha
from tests.historia_gen_fixtures import atividade_fixture, catalogo_fixture, fonte_fixture


def _catalogo(tmp_path: Path) -> dict[str, Any]:
    from src.historia_gen.catalogo.carregar import carregar_catalogo

    return carregar_catalogo(catalogo_fixture(tmp_path / "cat"))


def _entrada(tmp_path: Path, **substituicoes: Any) -> tuple[Path, Any]:
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(atividade_fixture(**substituicoes), ensure_ascii=False), encoding="utf-8"
    )
    return caminho, carregar_entrada(caminho)[0]


def test_consulta_exata_encontra(tmp_path: Path) -> None:
    assert verificar(_catalogo(tmp_path), "EF06HI01X", "6º ano EF") is not None


def test_consulta_exata_reprova_codigo_inexistente(tmp_path: Path) -> None:
    assert verificar(_catalogo(tmp_path), "EF06HI99", "6º ano EF") is None


def test_consulta_exata_reprova_ano_errado(tmp_path: Path) -> None:
    # o código existe no catálogo, mas não naquele ano
    assert verificar(_catalogo(tmp_path), "EF07HI02", "6º ano EF") is None


def test_folha_com_um_codigo_invalido_e_recusada_inteira(tmp_path: Path) -> None:
    reprovacoes = verificar_folha(
        _catalogo(tmp_path), [("EF06HI01X", "6º ano EF"), ("EF09HI99", "9º ano EF")]
    )
    assert len(reprovacoes) == 1
    assert "EF09HI99" in reprovacoes[0].motivo


def test_habilidade_de_outro_ano_recusa_entrada(tmp_path: Path) -> None:
    catalogo = _catalogo(tmp_path)
    hab = {**atividade_fixture()["habilidade"], "ano": "9º ano EF"}
    caminho, _ = _entrada(tmp_path, habilidade=hab)
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is not None
    _, reprovacoes = validar_atividade(atividade, catalogo)
    assert any("não existe no catálogo" in r.motivo for r in reprovacoes)


def test_confirmacao_ausente_recusa_montagem(tmp_path: Path) -> None:
    caminho, atividade = _entrada(tmp_path, confirmado_pelo_professor=False)
    assert atividade is not None
    _, reprovacoes = validar_atividade(atividade, _catalogo(tmp_path))
    assert any(r.campo == "confirmado_pelo_professor" for r in reprovacoes)


def test_fato_sem_fonte_recusa_montagem(tmp_path: Path) -> None:
    dados = atividade_fixture()
    del dados["blocos"][0]["fonte"]
    caminho = tmp_path / "atividade.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is None
    assert any("fonte" in r.motivo.lower() or r.campo.startswith("blocos") for r in reprovacoes)


def test_fonte_web_sem_url_recusa_montagem(tmp_path: Path) -> None:
    dados = atividade_fixture()
    dados["blocos"][0]["fonte"]["url"] = None
    caminho = tmp_path / "atividade.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is None
    assert any("url" in r.motivo.lower() for r in reprovacoes)


def test_quantidade_divergente_recusa_montagem(tmp_path: Path) -> None:
    catalogo = _catalogo(tmp_path)
    caminho, _ = _entrada(tmp_path, quantidade_questoes=10)
    atividade, reprovacoes = carregar_entrada(caminho)
    if atividade is None:  # barrada no esquema (pydantic)
        assert any(
            "quantidade_questoes" in r.motivo or r.campo == "quantidade_questoes"
            for r in reprovacoes
        )
    else:  # barrada no fluxo
        _, reprovacoes = validar_atividade(atividade, catalogo)
        assert any(r.campo == "quantidade_questoes" for r in reprovacoes)


def test_modo_adaptado_bloco_sem_pergunta_recusa_montagem(tmp_path: Path) -> None:
    catalogo = _catalogo(tmp_path)
    caminho, _ = _entrada(tmp_path, modo="adaptado")
    atividade, _ = carregar_entrada(caminho)
    assert atividade is not None
    _, reprovacoes = validar_atividade(atividade, catalogo)
    assert any(r.campo == "blocos" for r in reprovacoes)


def test_vf_falso_sem_correcao_recusa(tmp_path: Path) -> None:
    dados = atividade_fixture(
        itens_vf=[
            {"afirmacao": "Angola fica na Europa.", "verdadeiro": False, "fonte": fonte_fixture()}
        ]
    )
    caminho = tmp_path / "atividade.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is None
    assert any("correcao" in r.motivo for r in reprovacoes)


def test_marcar_com_correta_fora_das_opcoes_recusa(tmp_path: Path) -> None:
    dados = atividade_fixture(
        itens_marcar=[
            {
                "enunciado": "Pinte a palavra certa.",
                "opcoes": ["África", "Ásia"],
                "correta": "Europa",
                "fonte": fonte_fixture(),
            }
        ]
    )
    caminho = tmp_path / "atividade.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is None
    assert any("não está entre as opções" in r.motivo for r in reprovacoes)


def test_marcar_repetido_recusa_folha(tmp_path: Path) -> None:
    catalogo = _catalogo(tmp_path)
    item = {
        "enunciado": "Pinte a palavra certa.",
        "opcoes": ["África", "Ásia"],
        "correta": "África",
        "fonte": fonte_fixture(),
    }
    caminho, _ = _entrada(tmp_path, itens_marcar=[item, dict(item)])
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is not None and not reprovacoes
    _, reprovacoes = validar_atividade(atividade, catalogo)
    assert any(r.campo == "itens_marcar" for r in reprovacoes)


def test_nivel_de_suporte_fora_da_receita_recusa_montagem(tmp_path: Path) -> None:
    # a v1.1 tem receita para o suporte 2 e, no modo adaptado, para o 3; o 1 fica fora
    catalogo = _catalogo(tmp_path)
    caminho, _ = _entrada(tmp_path, nivel_suporte=1)
    atividade, _ = carregar_entrada(caminho)
    assert atividade is not None
    _, reprovacoes = validar_atividade(atividade, catalogo)
    assert any(r.campo == "nivel_suporte" for r in reprovacoes)


def test_suporte_3_so_existe_no_modo_adaptado(tmp_path: Path) -> None:
    # "suporte 3" numa folha regular seria o defeito de contrato do par 2 de novo
    catalogo = _catalogo(tmp_path)
    caminho, _ = _entrada(tmp_path, nivel_suporte=3, modo="regular")
    atividade, _ = carregar_entrada(caminho)
    assert atividade is not None
    _, reprovacoes = validar_atividade(atividade, catalogo)
    assert any(r.campo == "nivel_suporte" and "adaptada" in r.motivo for r in reprovacoes)


def test_suporte_3_no_modo_adaptado_e_aceito(tmp_path: Path) -> None:
    catalogo = _catalogo(tmp_path)
    bloco = {**atividade_fixture()["blocos"][0], "pergunta": "O que mudou no trabalho?"}
    caminho, _ = _entrada(tmp_path, nivel_suporte=3, modo="adaptado", blocos=[bloco])
    atividade, _ = carregar_entrada(caminho)
    assert atividade is not None
    validada, reprovacoes = validar_atividade(atividade, catalogo)
    assert not reprovacoes, [str(r) for r in reprovacoes]
    assert validada.nivel_suporte == 3


def test_planejamento_sem_pagina_do_professor_recusa(tmp_path: Path) -> None:
    # sem registro_mediacao a ficha não teria onde ser impressa: recusa em vez de sumir
    catalogo = _catalogo(tmp_path)
    caminho, _ = _entrada(tmp_path, planejamento={"objetivo": "Comparar fontes históricas."})
    atividade, _ = carregar_entrada(caminho)
    assert atividade is not None
    _, reprovacoes = validar_atividade(atividade, catalogo)
    assert any(r.campo == "planejamento" and "registro_mediacao" in r.motivo for r in reprovacoes)


def test_planejamento_vazio_recusa(tmp_path: Path) -> None:
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(atividade_fixture(planejamento={}), ensure_ascii=False), encoding="utf-8"
    )
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is None
    assert any("nenhum campo preenchido" in r.motivo for r in reprovacoes)


def test_entrada_valida_substitui_habilidade_pela_canonica(tmp_path: Path) -> None:
    catalogo = _catalogo(tmp_path)
    hab = {**atividade_fixture()["habilidade"], "descricao": "texto divergente da sessão"}
    caminho, _ = _entrada(tmp_path, habilidade=hab)
    atividade, _ = carregar_entrada(caminho)
    assert atividade is not None
    substituida, reprovacoes = validar_atividade(atividade, catalogo)
    assert not reprovacoes
    assert substituida.habilidade.descricao.startswith("Identificar noções de tempo")


def test_atividade_sem_questoes_recusa(tmp_path: Path) -> None:
    dados = atividade_fixture(blocos=[], itens_completar=[], pares_ligar=[])
    caminho = tmp_path / "atividade.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is None
    assert any("ao menos uma pergunta" in r.motivo for r in reprovacoes)


def test_vocabulario_repetido_recusa(tmp_path: Path) -> None:
    caminho = tmp_path / "atividade.json"
    caminho.write_text(
        json.dumps(atividade_fixture(vocabulario=["PAZ", "paz"]), ensure_ascii=False),
        encoding="utf-8",
    )
    atividade, reprovacoes = carregar_entrada(caminho)
    assert atividade is None
    assert any("vocabulario com repetição" in r.motivo for r in reprovacoes)
