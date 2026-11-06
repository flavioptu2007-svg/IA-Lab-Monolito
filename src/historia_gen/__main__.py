"""CLI do agente: ``python3 -m src.historia_gen <subcomando>``.

* ``montar``    — valida o ``atividade.json`` contra o catálogo e gera o ``.docx``.
* ``finalizar`` — remove a marca de rascunho e registra a aprovação no log.
* ``verificar`` — roda só as checagens, sem gerar arquivo.
* ``catalogo-validar`` — integridade + contagens + avisos do catálogo versionado.
* ``catalogo-extrair`` — extração assistida anual (dependência de dev, import tardio).
* ``conferencia-docx`` — gera o roteiro imprimível de conferência do catálogo.
* ``catalogo-conferir`` — confere a transcrição literal das 97 linhas contra o PDF
  e, com ``--aprovar``, registra a aprovação no ``meta`` do catálogo.
* ``tempo-manual`` — registra a medição humana da Q5 (minutos de uma adaptação
  feita à mão) e confronta com a duração medida de cada montagem.
* ``tempo-formulario`` — gera o formulário impresso que o professor preenche
  durante a adaptação manual (uma página por medição).

O pipeline nunca pergunta no meio da execução: entrada faltante ou inválida é
recusa imediata com a lista do que falta. A única interação humana planejada é
a confirmação do par tema↔habilidade, que acontece na sessão de redação e chega
pronta no JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

from src.historia_gen import VERSAO_TEMPLATE, conferencia, formulario, tempo
from src.historia_gen.catalogo import conferencia_literal
from src.historia_gen.catalogo.carregar import (
    CATALOGO_PADRAO,
    PDF_PADRAO,
    carregar_catalogo,
    carregar_para_geracao,
    validar_catalogo_versionado,
)
from src.historia_gen.docx_out import gerar_folhas, remover_marca_rascunho
from src.historia_gen.entrada import carregar_entrada, validar_atividade
from src.historia_gen.registro import registrar_aprovacao, registrar_geracao
from src.historia_gen.template import tamanho_corpo

SAIDA_PADRAO = Path("~/Documentos/Escola/Atividades").expanduser()
ROTEIRO_PADRAO = Path("docs/historia_gen/roteiro-conferencia-catalogo.docx")


def _ler_entrada(caminho: Path) -> tuple[bytes, dict]:
    bruto = caminho.read_bytes()
    return bruto, json.loads(bruto)


def cmd_montar(args: argparse.Namespace) -> int:
    try:
        catalogo = carregar_para_geracao(args.catalogo, args.pdf)
    except ValueError as exc:
        print(f"montagem recusada: {exc}")
        return 1
    atividade, reprovacoes = carregar_entrada(args.atividade)
    inicio = time.perf_counter()
    if atividade is None:
        print(f"entrada recusada ({args.atividade}):")
        for r in reprovacoes:
            print(f"  - {r}")
        return 1
    atividade, reprovacoes = validar_atividade(atividade, catalogo, args.atividade.parent)
    if reprovacoes:
        print("folha recusada — nada foi gerado:")
        for r in reprovacoes:
            print(f"  - {r}")
        return 1
    tamanho = tamanho_corpo(atividade.modo, args.fonte)
    semente = random.SystemRandom().randrange(1, 2**31)
    bruto, _ = _ler_entrada(args.atividade)
    caminho, gabarito = gerar_folhas(atividade, args.saida, tamanho, semente)
    registrar_geracao(
        args.saida,
        atividade.model_dump(),
        entrada_sha256=hashlib.sha256(bruto).hexdigest(),
        catalogo_versao=catalogo["meta"]["versao"],
        catalogo_data_acesso=catalogo["meta"]["data_acesso"],
        template=VERSAO_TEMPLATE,
        semente=semente,
        arquivo=caminho.name,
        gabarito=gabarito.name if gabarito else None,
        # Duração de validação + gravação (sem a redação): é o lado automático da Q5.
        duracao_s=round(time.perf_counter() - inicio, 3),
    )
    print(f"folha gerada: {caminho}")
    if gabarito:
        print(f"gabarito separado: {gabarito}")
    print(f"rascunho registrado em {args.saida / 'registros.jsonl'} — revisar antes de imprimir")
    return 0


def cmd_finalizar(args: argparse.Namespace) -> int:
    if not args.arquivo.exists():
        print(f"arquivo não encontrado: {args.arquivo}")
        return 1
    remover_marca_rascunho(args.arquivo)
    log = registrar_aprovacao(args.arquivo.parent, args.arquivo)
    print(f"marca de rascunho removida; aprovação registrada em {log}")
    return 0


def cmd_verificar(args: argparse.Namespace) -> int:
    caminho = args.catalogo or CATALOGO_PADRAO
    try:
        catalogo = carregar_catalogo(caminho)
    except ValueError as exc:
        print(f"verificação recusada: {exc}")
        return 1
    atividade, reprovacoes = carregar_entrada(args.atividade)
    if atividade is not None:
        atividade, reprovacoes = validar_atividade(atividade, catalogo, args.atividade.parent)
    if atividade is None or reprovacoes:
        print("entrada com reprovações:")
        for r in reprovacoes:
            print(f"  - {r}")
        return 1
    print(f"entrada válida contra o catálogo ({caminho.name}): {atividade.habilidade.codigo}")
    return 0


def cmd_catalogo_validar(args: argparse.Namespace) -> int:
    try:
        ok, linhas = validar_catalogo_versionado(args.catalogo, args.pdf)
    except (ValueError, OSError) as exc:
        print(f"validação recusada: {exc}")
        return 1
    for linha in linhas:
        print(linha)
    return 0 if ok else 1


def cmd_conferencia_docx(args: argparse.Namespace) -> int:
    caminho = args.catalogo or CATALOGO_PADRAO
    try:
        catalogo = carregar_catalogo(caminho)
    except ValueError as exc:
        print(f"roteiro recusado: {exc}")
        return 1
    destino = conferencia.gerar_roteiro(catalogo, args.saida)
    total = len(catalogo["habilidades"])
    print(f"roteiro de conferência gerado: {destino}")
    print(f"{total} habilidades em {len({h['pagina'] for h in catalogo['habilidades']})} páginas")
    return 0


def cmd_catalogo_extrair(args: argparse.Namespace) -> int:
    import pymupdf  # noqa: F401, PLC0415 — dependência de dev, import tardio

    from src.historia_gen.catalogo import extraidor  # noqa: PLC0415

    repassados: list[str] = []
    if args.pdf is not None:
        repassados += ["--pdf", str(args.pdf)]
    if args.saida is not None:
        repassados += ["--saida", str(args.saida)]
    return extraidor.main(repassados)


def cmd_catalogo_conferir(args: argparse.Namespace) -> int:
    caminho = args.catalogo or CATALOGO_PADRAO
    pdf = args.pdf or PDF_PADRAO
    try:
        catalogo = carregar_catalogo(caminho)
        divergencias = conferencia_literal.conferir(catalogo, pdf)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"conferência recusada: {exc}")
        return 1
    if divergencias:
        print(f"conferência literal: {len(divergencias)} divergência(s) contra {pdf.name}:")
        for r in divergencias:
            print(f"  - {r}")
        return 1
    total = len(catalogo["habilidades"])
    print(
        f"conferência literal: {total} habilidades conferem com {pdf.name} "
        "(código, descrição, unidade, objeto e página)"
    )
    if not args.aprovar:
        print('para registrar a aprovação: --aprovar --responsavel "<nome de quem conferiu>"')
        return 0
    if not args.responsavel:
        print("--aprovar exige --responsavel (o nome fica no meta.revisado_por do catálogo)")
        return 1
    metodo = f"conferência literal automática da camada de texto do PDF ({pdf.name})"
    conferencia_literal.aprovar(caminho, args.responsavel, metodo)
    print(f"aprovação registrada em {caminho.name}: revisado_por={args.responsavel!r}")
    return 0


def cmd_tempo_formulario(args: argparse.Namespace) -> int:
    try:
        destino = formulario.gerar_formulario(args.saida, vias=args.vias)
    except ValueError as exc:
        print(f"formulário recusado: {exc}")
        return 1
    print(
        f"formulário da Q5 gerado: {destino} "
        f"({args.vias} {'via' if args.vias == 1 else 'vias'}, uma por adaptação cronometrada)"
    )
    print(f"total de cada via vai para {tempo.CAMINHO_PADRAO} pelo tempo-manual")
    return 0


def cmd_tempo_manual(args: argparse.Namespace) -> int:
    if args.comparar:
        try:
            dados = tempo.comparar(args.arquivo, args.registros)
        except tempo.SemLinhaDeBase as exc:
            print(f"sem comparação: {exc}")
            return 1
        print(
            f"linha de base manual: {dados.medicoes} medição(ões), "
            f"mediana {dados.mediana_min:.0f} min"
        )
        print(
            f"montagem pelo pipeline: {dados.montagens} geração(ões), "
            f"mediana {dados.mediana_montagem_s:.2f} s"
        )
        print(
            f"razão: ~{dados.razao:.0f}× menos tempo na montagem — "
            "a redação do atividade.json não entra na conta"
        )
        return 0
    faltando = [f"--{nome}" for nome in ("tema", "ano", "minutos") if getattr(args, nome) is None]
    if faltando:
        print(f"--registrar exige: {', '.join(faltando)}")
        return 1
    try:
        caminho = tempo.registrar(
            args.arquivo,
            tema=args.tema,
            ano=args.ano,
            minutos=args.minutos,
            quem=args.quem,
            modo=args.modo,
            data=args.data,
            observacao=args.observacao,
        )
    except ValueError as exc:
        print(f"registro recusado: {exc}")
        return 1
    print(f"medição manual registrada em {caminho}: {args.tema} ({args.ano}), {args.minutos:g} min")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="src.historia_gen", description=__doc__)
    sub = ap.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("montar", help="gera o .docx a partir do atividade.json")
    p.add_argument("atividade", type=Path, help="caminho do atividade.json")
    p.add_argument(
        "--saida", type=Path, default=SAIDA_PADRAO, help="pasta de saída (criada se não existir)"
    )
    p.add_argument(
        "--fonte",
        type=int,
        default=None,
        help="tamanho do corpo (11–14; ampliação do modo adaptado)",
    )
    p.add_argument(
        "--catalogo", type=Path, default=None, help="catálogo alternativo (padrão: o versionado)"
    )
    p.add_argument("--pdf", type=Path, default=None, help="PDF-base para checagem de integridade")
    p.set_defaults(func=cmd_montar)

    p = sub.add_parser("finalizar", help="remove a marca de rascunho e registra a aprovação")
    p.add_argument("arquivo", type=Path, help="folha .docx revisada")
    p.set_defaults(func=cmd_finalizar)

    p = sub.add_parser("verificar", help="roda só as checagens, sem gerar arquivo")
    p.add_argument("atividade", type=Path, help="caminho do atividade.json")
    p.add_argument(
        "--catalogo", type=Path, default=None, help="catálogo alternativo (padrão: o versionado)"
    )
    p.set_defaults(func=cmd_verificar)

    p = sub.add_parser("catalogo-validar", help="integridade + contagens + avisos do catálogo")
    p.add_argument(
        "--catalogo", type=Path, default=None, help="catálogo alternativo (padrão: o versionado)"
    )
    p.add_argument("--pdf", type=Path, default=None, help="PDF-base para checagem de integridade")
    p.set_defaults(func=cmd_catalogo_validar)

    p = sub.add_parser("catalogo-extrair", help="extração assistida anual (requer extra dev)")
    p.add_argument("--pdf", type=Path, default=None, help="PDF-base (padrão: o versionado)")
    p.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="rascunho .json de saída (padrão: catalogo/dados/rascunho_extracao.json)",
    )
    p.set_defaults(func=cmd_catalogo_extrair)

    p = sub.add_parser(
        "conferencia-docx", help="gera o roteiro imprimível de conferência do catálogo"
    )
    p.add_argument(
        "--saida",
        type=Path,
        default=ROTEIRO_PADRAO,
        help="arquivo .docx de saída (padrão: docs/historia_gen/roteiro-conferencia-catalogo.docx)",
    )
    p.add_argument(
        "--catalogo", type=Path, default=None, help="catálogo alternativo (padrão: o versionado)"
    )
    p.set_defaults(func=cmd_conferencia_docx)

    p = sub.add_parser(
        "catalogo-conferir",
        help="confere a transcrição literal contra o PDF e registra a aprovação",
    )
    p.add_argument(
        "--catalogo", type=Path, default=None, help="catálogo alternativo (padrão: o versionado)"
    )
    p.add_argument("--pdf", type=Path, default=None, help="PDF-base (padrão: o versionado)")
    p.add_argument(
        "--aprovar", action="store_true", help="grava a aprovação no meta (só sem divergências)"
    )
    p.add_argument(
        "--responsavel", default="", help="nome de quem conferiu (vai para meta.revisado_por)"
    )
    p.set_defaults(func=cmd_catalogo_conferir)

    p = sub.add_parser(
        "tempo-formulario",
        help="gera o formulário impresso de cronometragem da adaptação manual (Q5)",
    )
    p.add_argument(
        "--saida",
        type=Path,
        default=formulario.DESTINO_PADRAO,
        help="arquivo .docx de saída (padrão: docs/historia_gen/q5-formulario.docx)",
    )
    p.add_argument(
        "--vias",
        type=int,
        default=formulario.VIAS_PADRAO,
        help="quantas páginas/formulários (padrão: 2 — o protocolo pede 1–2 medições)",
    )
    p.set_defaults(func=cmd_tempo_formulario)

    p = sub.add_parser("tempo-manual", help="registra a medição da Q5 e compara com a montagem")
    p.add_argument("--tema", default=None, help="tema da adaptação cronometrada")
    p.add_argument("--ano", default=None, help="ano/série da adaptação")
    p.add_argument("--minutos", type=float, default=None, help="tempo cronometrado, em minutos")
    p.add_argument("--quem", default="", help="quem cronometrou")
    p.add_argument("--modo", default="adaptado", choices=("regular", "adaptado"))
    p.add_argument("--data", default=None, help="AAAA-MM-DD (padrão: hoje)")
    p.add_argument("--observacao", default="")
    p.add_argument(
        "--arquivo", type=Path, default=tempo.CAMINHO_PADRAO, help="CSV das medições manuais"
    )
    p.add_argument("--comparar", action="store_true", help="compara com o registros.jsonl")
    p.add_argument(
        "--registros", type=Path, default=Path("saida/registros.jsonl"), help="log das gerações"
    )
    p.set_defaults(func=cmd_tempo_manual)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
