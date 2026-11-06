"""Validação do ``atividade.json`` — a checagem adversária do fluxo.

Recusa a montagem antes de qualquer arquivo existir: esquema inválido,
habilidade fora do catálogo do ano, confirmação do professor ausente, fato sem
fonte completa, quantidade de questões divergente, bloco do modo adaptado sem
pergunta. Sempre devolve a lista completa de reprovações — o vazio nunca é
preenchido com valor inventado.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.historia_gen.formatos import (
    validar_itens,
    validar_marcar,
    validar_ordenar,
    validar_parear_iguais,
    validar_pares,
    validar_vf,
)
from src.historia_gen.modelos import AtividadeEntrada, Figura, HabilidadeCatalogo, Reprovacao
from src.historia_gen.verificador import verificar

SUFIXOS_IMAGEM = {".png", ".jpg", ".jpeg"}


def carregar_entrada(caminho: Path) -> tuple[AtividadeEntrada | None, list[Reprovacao]]:
    """Lê e valida o JSON contra os esquemas; erros viram reprovações."""
    try:
        dados: dict[str, Any] = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [Reprovacao(campo="arquivo", motivo=f"JSON inválido: {exc}")]
    try:
        return AtividadeEntrada.model_validate(dados), []
    except ValidationError as exc:
        return None, [
            Reprovacao(campo=".".join(str(p) for p in erro["loc"]) or "entrada", motivo=erro["msg"])
            for erro in exc.errors()
        ]


def _resolver_figuras(
    atividade: AtividadeEntrada, base_dir: Path | None
) -> tuple[list[Figura], list[Reprovacao]]:
    """Confere cada imagem no disco e devolve o caminho resolvido.

    O arquivo pode vir absoluto ou relativo à pasta da própria entrada — é a
    pasta onde o professor guarda a figura ao lado do ``.json``. Sem a imagem
    não há folha: um espaço vazio no lugar da figura é pior do que a recusa.
    """
    resolvidas: list[Figura] = []
    reprovacoes: list[Reprovacao] = []
    for i, figura in enumerate(atividade.figuras, start=1):
        candidatos = [Path(figura.caminho).expanduser()]
        if base_dir is not None:
            candidatos.append(Path(base_dir) / figura.caminho)
        achado = next((c for c in candidatos if c.is_file()), None)
        if achado is None:
            reprovacoes.append(
                Reprovacao(
                    campo="figuras",
                    motivo=(
                        f"figura {i}: arquivo não encontrado ({figura.caminho}) — "
                        "a folha não é gerada sem a imagem"
                    ),
                )
            )
            continue
        if achado.suffix.lower() not in SUFIXOS_IMAGEM:
            reprovacoes.append(
                Reprovacao(
                    campo="figuras",
                    motivo=f"figura {i}: formato {achado.suffix!r} não aceito (use PNG ou JPEG)",
                )
            )
            continue
        resolvidas.append(figura.model_copy(update={"caminho": str(achado.resolve())}))
    return resolvidas, reprovacoes


def validar_atividade(
    atividade: AtividadeEntrada, catalogo: dict[str, Any], base_dir: Path | None = None
) -> tuple[AtividadeEntrada, list[Reprovacao]]:
    """Checagens de fluxo contra o catálogo; devolve a atividade com a habilidade
    substituída pela **cópia canônica do catálogo** (o texto impresso vem sempre
    de lá) ou a lista completa de reprovações.
    """
    reprovacoes: list[Reprovacao] = []
    hab = atividade.habilidade
    canonica = verificar(catalogo, hab.codigo, hab.ano)
    if canonica is None:
        reprovacoes.append(
            Reprovacao(
                campo="habilidade",
                motivo=(
                    f"código {hab.codigo!r} não existe no catálogo para {hab.ano} — "
                    "'habilidade não encontrada'; nada é gerado"
                ),
            )
        )
    if not atividade.confirmado_pelo_professor:
        reprovacoes.append(
            Reprovacao(
                campo="confirmado_pelo_professor",
                motivo="confirmação do par tema↔habilidade ausente — nada é gerado",
            )
        )
    if atividade.nivel_suporte not in {2, 3}:
        reprovacoes.append(
            Reprovacao(
                campo="nivel_suporte",
                motivo=(
                    f"nível de suporte {atividade.nivel_suporte} não está implementado "
                    "(a v1.1 tem receita para o suporte 2 e, no modo adaptado, para o "
                    "suporte 3) — a folha não sai com o rótulo de outro nível"
                ),
            )
        )
    if atividade.nivel_suporte == 3 and atividade.modo != "adaptado":
        reprovacoes.append(
            Reprovacao(
                campo="nivel_suporte",
                motivo=(
                    "suporte 3 é um perfil de folha adaptada (uma tarefa por página); "
                    "no modo regular use nivel_suporte 2"
                ),
            )
        )
    if atividade.planejamento is not None and not atividade.registro_mediacao:
        reprovacoes.append(
            Reprovacao(
                campo="planejamento",
                motivo=(
                    "a ficha de planejamento é impressa na página do professor; "
                    "use registro_mediacao: true ou remova o planejamento"
                ),
            )
        )
    if atividade.modo == "adaptado":
        sem_pergunta = [i for i, b in enumerate(atividade.blocos, start=1) if not b.pergunta]
        if sem_pergunta:
            reprovacoes.append(
                Reprovacao(
                    campo="blocos",
                    motivo=(
                        f"modo adaptado exige uma pergunta imediatamente após cada bloco; "
                        f"blocos sem pergunta: {sem_pergunta}"
                    ),
                )
            )
    # Formatos: a mesma checagem que o montador faria, aqui para a recusa sair
    # como lista de reprovações em vez de exceção no meio da gravação.
    for campo, problemas in (
        ("itens_parear", validar_parear_iguais(atividade.itens_parear)),
        ("itens_marcar", validar_marcar(atividade.itens_marcar)),
        ("itens_vf", validar_vf(atividade.itens_vf)),
        ("itens_ordenar", validar_ordenar(atividade.itens_ordenar)),
        ("itens_completar", validar_itens(atividade.itens_completar)),
        ("pares_ligar", validar_pares(atividade.pares_ligar)),
    ):
        reprovacoes += [Reprovacao(campo=campo, motivo=problema) for problema in problemas]
    if (
        atividade.quantidade_questoes is not None
        and atividade.quantidade_questoes != atividade.total_questoes
    ):
        reprovacoes.append(
            Reprovacao(
                campo="quantidade_questoes",
                motivo=(
                    f"informado {atividade.quantidade_questoes}, preenchido {atividade.total_questoes}"
                ),
            )
        )
    figuras, problemas_figuras = _resolver_figuras(atividade, base_dir)
    reprovacoes += problemas_figuras
    if reprovacoes:
        return atividade, reprovacoes
    canonicos = [
        h for h in catalogo["habilidades"] if h["codigo"] == hab.codigo and h["ano"] == hab.ano
    ]
    substituida = atividade.model_copy(
        update={"habilidade": HabilidadeCatalogo.model_validate(canonicos[0]), "figuras": figuras}
    )
    return substituida, []
