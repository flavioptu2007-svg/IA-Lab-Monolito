#!/usr/bin/env bash
# =============================================================================
# test_all.sh — matriz completa de testes do monorepo
# =============================================================================
# Roda num comando só a mesma matriz que os três workflows do CI cobrem
# (ci.yml, projects-ci.yml e a suíte do odysseus) e imprime um resumo por
# projeto.
#
# O script NÃO instala nada e NÃO altera nada: só executa verificações e grava
# a saída de cada uma num diretório temporário (0700), apagado no fim, a menos
# que --keep-logs seja usado. Dependências de terceiros (node_modules) não
# presentes viram SKIP, não falha — quem chama decide se roda `npm ci` antes.
#
# Uso:
#   scripts/test_all.sh                      # matriz completa
#   scripts/test_all.sh --fast               # sem builds npm e sem odysseus
#   scripts/test_all.sh --only monolito,next-app
#   scripts/test_all.sh --skip odysseus --verbose
#
# Saída: uma linha por verificação, uma tabela por projeto e um detalhamento
# das falhas. Código de saída 0 quando nada falhou, 1 quando algo falhou.
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Projetos conhecidos, na ordem em que rodam. A lista alimenta --only/--skip e
# a mensagem de erro de nome inválido.
PROJETOS_CONHECIDOS=(
    monolito
    next-app
    dashboard-raiz
    dashboard-projetos
    leituraia
    web-api
    odysseus
)

ONLY=""
SKIP=""
VERBOSE=0
KEEP_LOGS=0
FAIL_FAST=0
FAST=0

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/test_all.XXXXXX")"
chmod 700 "$LOG_DIR"

declare -A PROJ_OK=() PROJ_FAIL=() PROJ_SKIP=() PROJ_TIME=()
declare -a ORDEM=()
declare -a FALHAS=()
TOTAL_OK=0
TOTAL_FAIL=0
TOTAL_SKIP=0

# -----------------------------------------------------------------------------
# Ajuda
# -----------------------------------------------------------------------------
# Imprime o bloco de comentário do topo (título, uso e opções), cortando as
# linhas de separador.
uso() {
    awk 'NR > 2 { if ($0 ~ /^#/) { sub(/^# ?/, ""); print } else { exit } }' \
        "${BASH_SOURCE[0]}" | sed '/^=\{10,\}$/d'
}

# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------
erro() {
    printf 'erro: %s\n' "$*" >&2
    exit 2
}

tem() {
    command -v "$1" >/dev/null 2>&1
}

# selecionado <projeto> — aplica --only/--skip
selecionado() {
    local projeto=$1
    if [[ -n "$ONLY" && ",$ONLY," != *",$projeto,"* ]]; then
        return 1
    fi
    if [[ -n "$SKIP" && ",$SKIP," == *",$projeto,"* ]]; then
        return 1
    fi
    return 0
}

# valida os nomes passados em --only/--skip
valida_lista() {
    local opcao=$1 lista=$2 nome
    local -a itens
    IFS=',' read -r -a itens <<<"$lista"
    for nome in "${itens[@]}"; do
        [[ -z "$nome" ]] && continue
        if [[ " ${PROJETOS_CONHECIDOS[*]} " != *" $nome "* ]]; then
            erro "$opcao aceita apenas: ${PROJETOS_CONHECIDOS[*]} (recebido: '$nome')"
        fi
    done
}

# garante que o projeto aparece uma vez só na ordem do resumo
registra_projeto() {
    local projeto=$1 existente
    for existente in "${ORDEM[@]:-}"; do
        [[ "$existente" == "$projeto" ]] && return 0
    done
    ORDEM+=("$projeto")
    PROJ_OK["$projeto"]=0
    PROJ_FAIL["$projeto"]=0
    PROJ_SKIP["$projeto"]=0
    PROJ_TIME["$projeto"]=0
}

# -----------------------------------------------------------------------------
# Execução de uma verificação
# -----------------------------------------------------------------------------
# executa <projeto> <verificação> <diretório> <comando...>
executa() {
    local projeto=$1 nome=$2 dir=$3
    shift 3

    registra_projeto "$projeto"

    if [[ ! -d "$dir" ]]; then
        anota_skip "$projeto" "$nome" "diretório ausente: ${dir#"$REPO_ROOT"/}"
        return 0
    fi

    local log="$LOG_DIR/${projeto}__${nome//[^A-Za-z0-9]/_}.log"
    local inicio=$SECONDS
    local status=0

    printf '  %-26s ' "$nome"

    (
        cd "$dir" || exit 90
        "$@"
    ) >"$log" 2>&1 || status=$?

    local duracao=$((SECONDS - inicio))
    PROJ_TIME["$projeto"]=$((PROJ_TIME["$projeto"] + duracao))

    if [[ $status -eq 0 ]]; then
        PROJ_OK["$projeto"]=$((PROJ_OK["$projeto"] + 1))
        TOTAL_OK=$((TOTAL_OK + 1))
        printf 'ok      %3ds\n' "$duracao"
    else
        PROJ_FAIL["$projeto"]=$((PROJ_FAIL["$projeto"] + 1))
        TOTAL_FAIL=$((TOTAL_FAIL + 1))
        printf 'FALHOU  %3ds\n' "$duracao"
        FALHAS+=("$projeto :: $nome :: saída $status :: $log")
        if [[ $VERBOSE -eq 1 ]]; then
            sed 's/^/      │ /' "$log"
        else
            tail -n 12 "$log" | sed 's/^/      │ /'
            printf '      │ (log completo: %s)\n' "$log"
        fi
        if [[ $FAIL_FAST -eq 1 ]]; then
            printf '\n--fail-fast: interrompendo na primeira falha\n'
            resume
            exit 1
        fi
    fi
    return 0
}

# anota_skip <projeto> <verificação> <motivo>
anota_skip() {
    local projeto=$1 nome=$2 motivo=$3
    registra_projeto "$projeto"
    PROJ_SKIP["$projeto"]=$((PROJ_SKIP["$projeto"] + 1))
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
    printf '  %-26s pulado  (%s)\n' "$nome" "$motivo"
}

# node_modules presente? senão o build/typecheck/lint não tem o que rodar.
exige_node_modules() {
    local projeto=$1 dir=$2 nome=$3
    if [[ ! -d "$dir/node_modules" ]]; then
        anota_skip "$projeto" "$nome" "sem node_modules — rode 'npm ci' em ${dir#"$REPO_ROOT"/}"
        return 1
    fi
    return 0
}

# -----------------------------------------------------------------------------
# Matriz por projeto
# -----------------------------------------------------------------------------
# O monolito é barato o bastante para rodar inteiro mesmo em --fast: a suíte
# leva poucos segundos e ruff/mypy pegam a maior parte dos regressos.
roda_monolito() {
    selecionado monolito || return 0

    executa monolito "pytest" "$REPO_ROOT" \
        env IA_LAB_RAG_ENABLED=false IA_LAB_LOG_LEVEL=WARNING \
        python3 -m pytest tests/ -q --tb=short

    if tem ruff; then
        executa monolito "ruff check" "$REPO_ROOT" ruff check ai scripts api src tests
        executa monolito "ruff format" "$REPO_ROOT" ruff format --check ai api src tests
    else
        anota_skip monolito "ruff check" "ruff não instalado"
        anota_skip monolito "ruff format" "ruff não instalado"
    fi

    if tem python3 && python3 -c 'import mypy' >/dev/null 2>&1; then
        executa monolito "mypy" "$REPO_ROOT" \
            python3 -m mypy ai src api --ignore-missing-imports
    else
        anota_skip monolito "mypy" "mypy não instalado"
    fi

    if tem shellcheck; then
        local -a scripts
        mapfile -t scripts < <(cd "$REPO_ROOT" && git ls-files 'scripts/*.sh')
        if [[ ${#scripts[@]} -gt 0 ]]; then
            executa monolito "shellcheck" "$REPO_ROOT" shellcheck -S warning "${scripts[@]}"
        else
            anota_skip monolito "shellcheck" "nenhum script versionado"
        fi
    else
        anota_skip monolito "shellcheck" "shellcheck não instalado"
    fi

    if tem bats && [[ -d "$REPO_ROOT/tests/shell" ]]; then
        executa monolito "bats" "$REPO_ROOT" bats tests/shell/
    else
        anota_skip monolito "bats" "bats não instalado"
    fi
}

roda_next_app() {
    selecionado next-app || return 0
    local dir="$REPO_ROOT/Projetos/next-app"
    exige_node_modules next-app "$dir" "typecheck" || return 0

    executa next-app "typecheck" "$dir" npm run typecheck
    executa next-app "lint" "$dir" npm run lint
    if [[ $FAST -eq 1 ]]; then
        anota_skip next-app "build" "--fast"
    else
        executa next-app "build" "$dir" npm run build
    fi
}

roda_dashboard_raiz() {
    selecionado dashboard-raiz || return 0
    local dir="$REPO_ROOT/web/dashboard"
    exige_node_modules dashboard-raiz "$dir" "tsc" || return 0

    executa dashboard-raiz "tsc -b" "$dir" npx tsc -b --noEmit
    if [[ $FAST -eq 1 ]]; then
        anota_skip dashboard-raiz "build" "--fast"
    else
        executa dashboard-raiz "build" "$dir" npm run build
    fi
}

roda_dashboard_projetos() {
    selecionado dashboard-projetos || return 0
    local dir="$REPO_ROOT/Projetos/web/dashboard"
    exige_node_modules dashboard-projetos "$dir" "lint" || return 0

    executa dashboard-projetos "lint" "$dir" npm run lint
    if [[ $FAST -eq 1 ]]; then
        anota_skip dashboard-projetos "build" "--fast"
    else
        executa dashboard-projetos "build" "$dir" npm run build
    fi
}

roda_leituraia() {
    selecionado leituraia || return 0
    # O projects-ci.yml roda a partir de Projetos/ (imports `leituraia.*`).
    executa leituraia "pytest" "$REPO_ROOT/Projetos" \
        python3 -m pytest leituraia/tests -q
}

roda_web_api() {
    selecionado web-api || return 0
    executa web-api "pytest" "$REPO_ROOT/Projetos/web" \
        python3 -m pytest api/tests -q
}

roda_odysseus() {
    selecionado odysseus || return 0
    local dir="$REPO_ROOT/odysseus"

    if [[ $FAST -eq 1 ]]; then
        anota_skip odysseus "pytest" "--fast"
        return 0
    fi
    if [[ ! -d "$dir/tests" ]]; then
        anota_skip odysseus "pytest" "clone do odysseus ausente"
        return 0
    fi

    # -n auto/--timeout só quando os plugins existem (a suíte leva ~2 min em
    # paralelo e ~20 min em série).
    local -a extra=()
    python3 -c 'import xdist' >/dev/null 2>&1 && extra+=(-n auto)
    python3 -c 'import pytest_timeout' >/dev/null 2>&1 && extra+=(--timeout=180)

    executa odysseus "pytest" "$dir" python3 -m pytest tests/ -q "${extra[@]}"
}

# -----------------------------------------------------------------------------
# Resumo
# -----------------------------------------------------------------------------
resume() {
    local projeto ok falha pulado tempo total_checks
    local largura=0 nome

    for nome in "${ORDEM[@]:-}"; do
        ((${#nome} > largura)) && largura=${#nome}
    done
    ((largura < 8)) && largura=8

    printf '\n%s\n' "─────────────────────────────────────────────────────────────"
    printf '%-*s  %5s %6s %6s %7s\n' "$largura" "PROJETO" "OK" "FALHA" "PULADO" "TEMPO"
    for projeto in "${ORDEM[@]:-}"; do
        ok=${PROJ_OK["$projeto"]}
        falha=${PROJ_FAIL["$projeto"]}
        pulado=${PROJ_SKIP["$projeto"]}
        tempo=${PROJ_TIME["$projeto"]}
        printf '%-*s  %5d %6d %6d %6ds\n' "$largura" "$projeto" "$ok" "$falha" "$pulado" "$tempo"
    done

    total_checks=$((TOTAL_OK + TOTAL_FAIL + TOTAL_SKIP))
    local substantivo="verificações"
    [[ $total_checks -eq 1 ]] && substantivo="verificação"
    printf '%s\n' "─────────────────────────────────────────────────────────────"
    printf '%d %s: %d ok, %d falha(s), %d pulada(s)\n' \
        "$total_checks" "$substantivo" "$TOTAL_OK" "$TOTAL_FAIL" "$TOTAL_SKIP"

    if [[ ${#FALHAS[@]} -gt 0 ]]; then
        printf '\nFalhas:\n'
        local linha
        for linha in "${FALHAS[@]}"; do
            printf '  - %s\n' "$linha"
        done
    fi
}

limpa() {
    if [[ $KEEP_LOGS -eq 0 ]]; then
        rm -rf "$LOG_DIR"
    else
        printf 'Logs preservados em %s\n' "$LOG_DIR"
    fi
}

# -----------------------------------------------------------------------------
# Argumentos
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
    -h | --help)
        uso
        exit 0
        ;;
    -f | --fast) FAST=1 ;;
    -v | --verbose) VERBOSE=1 ;;
    -k | --keep-logs) KEEP_LOGS=1 ;;
    --fail-fast) FAIL_FAST=1 ;;
    -o | --only)
        [[ $# -ge 2 ]] || erro "--only exige uma lista de projetos"
        ONLY="${2// /}"
        valida_lista --only "$ONLY"
        shift
        ;;
    -s | --skip)
        [[ $# -ge 2 ]] || erro "--skip exige uma lista de projetos"
        SKIP="${2// /}"
        valida_lista --skip "$SKIP"
        shift
        ;;
    *)
        erro "opção desconhecida: $1 (use --help)"
        ;;
    esac
    shift
done

if ! tem python3; then
    erro "python3 não encontrado"
fi

trap limpa EXIT

printf 'Matriz de testes — %s\n' "$REPO_ROOT"
[[ $FAST -eq 1 ]] && printf 'Modo --fast: sem builds npm e sem odysseus\n'
[[ $VERBOSE -eq 1 ]] && printf 'Modo --verbose: saída completa das verificações\n'
printf '\n'

roda_monolito
printf '\n'
roda_next_app
roda_dashboard_raiz
roda_dashboard_projetos
printf '\n'
roda_leituraia
roda_web_api
printf '\n'
roda_odysseus

resume

[[ $TOTAL_FAIL -eq 0 ]]
