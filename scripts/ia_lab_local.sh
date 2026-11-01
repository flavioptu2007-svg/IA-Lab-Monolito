#!/usr/bin/env bash
# =============================================================================
# ia_lab_local.sh — bootstrap local do IA-Lab Monolito + Coraci Chat
# =============================================================================
# Sobe os dois serviços SEM Docker (as portas 8000/6379/6333/8080 já estão
# ocupadas por outros projetos nesta máquina) e sem tocar em .env, bancos ou
# configurações existentes.
#
# Uso:
#   scripts/ia_lab_local.sh check      # valida pré-requisitos (não altera nada)
#   scripts/ia_lab_local.sh start      # sobe API (:8010) e Coraci (:5000)
#   scripts/ia_lab_local.sh status     # PID + healthcheck de cada serviço
#   scripts/ia_lab_local.sh stop       # parada controlada (SIGTERM)
#   scripts/ia_lab_local.sh restart
#   scripts/ia_lab_local.sh diagnose   # portas, containers, Ollama e logs
#   scripts/ia_lab_local.sh test       # pytest + ruff + mypy do repositório
#
# Variáveis (opcionais):
#   IA_LAB_API_PORT     porta da API FastAPI        (default 8010)
#   IA_LAB_CORACI_PORT  porta do Coraci Flask       (default 5000)
#   IA_LAB_FORCE_KILL   =1 permite SIGKILL no stop  (default 0)
#
# Arquivos de runtime (PIDs/logs) ficam fora do repositório, em
# ${XDG_RUNTIME_DIR:-/tmp}/ia-lab-local (permissão 0700).
#
# O script NUNCA imprime o conteúdo de .env nem de config.json.
# =============================================================================

set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

API_PORT="${IA_LAB_API_PORT:-8010}"
CORACI_PORT="${IA_LAB_CORACI_PORT:-5000}"
FORCE_KILL="${IA_LAB_FORCE_KILL:-0}"

# Diretório de runtime: XDG (normal) → /tmp quando XDG não é gravável
# (ex.: sessão sem permissão de escrita em /run/user/<uid>).
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}/ia-lab-local"
if ! mkdir -p "$RUNTIME_DIR" 2>/dev/null || [[ ! -w "$RUNTIME_DIR" ]]; then
    RUNTIME_DIR="${TMPDIR:-/tmp}/ia-lab-local"
    mkdir -p "$RUNTIME_DIR" 2>/dev/null || true
fi
chmod 700 "$RUNTIME_DIR" 2>/dev/null || true

API_PID="$RUNTIME_DIR/api.pid"
CORACI_PID="$RUNTIME_DIR/coraci.pid"
API_LOG="$RUNTIME_DIR/api.log"
CORACI_LOG="$RUNTIME_DIR/coraci.log"

C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_OFF=$'\033[0m'
ok()   { printf '%s[ok]%s   %s\n'   "$C_OK"   "$C_OFF" "$*"; }
warn() { printf '%s[warn]%s %s\n'   "$C_WARN" "$C_OFF" "$*"; }
fail() { printf '%s[fail]%s %s\n'   "$C_ERR"  "$C_OFF" "$*"; }

die() { fail "$*"; exit 1; }

# ── Python com as dependências do projeto ────────────────────────────────────
detect_python() {
    local candidato
    for candidato in "$REPO_ROOT/.venv/bin/python" python3; do
        if command -v "$candidato" >/dev/null 2>&1 || [[ -x "$candidato" ]]; then
            if "$candidato" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
                PY="$candidato"
                return 0
            fi
        fi
    done
    return 1
}

porta_em_uso() {
    local porta="$1"
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${porta}$"
}

health_api() {
    curl -fsS --max-time 2 "http://127.0.0.1:${API_PORT}/api/health/live" >/dev/null 2>&1
}

health_coraci() {
    curl -fsS --max-time 2 "http://127.0.0.1:${CORACI_PORT}/" >/dev/null 2>&1
}

# Lê um valor do .env sem imprimir (apenas para diagnóstico interno).
env_get() {
    local chave="$1"
    [[ -f .env ]] || return 1
    "$PY" - "$chave" <<'PY'
import sys
chave = sys.argv[1]
for linha in open(".env", encoding="utf-8"):
    linha = linha.strip()
    if linha.startswith("#") or "=" not in linha:
        continue
    k, v = linha.split("=", 1)
    if k.strip() == chave:
        print(v.strip())
        break
PY
}

pid_vivo() {
    local arquivo="$1" padrao="$2"
    [[ -f "$arquivo" ]] || return 1
    local pid
    pid="$(cat "$arquivo" 2>/dev/null || true)"
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    # Confere a linha de comando para não matar um PID reciclado.
    tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q "$padrao"
}

# ── check ────────────────────────────────────────────────────────────────────
cmd_check() {
    local erros=0

    detect_python || die "nenhum Python com fastapi+uvicorn (instale com: pip install -e '.[dev]')"
    ok "Python: $("$PY" -V 2>&1) ($PY)"

    if [[ -f .env ]]; then
        ok ".env presente ($(stat -c '%a' .env) $(stat -c '%U' .env))"
    else
        warn ".env ausente — a API usa os defaults (local/Ollama) e não autentica"
    fi

    if "$PY" -c 'import api.server' >/dev/null 2>&1; then
        ok "api.server importa sem erro"
    else
        fail "api.server não importa"; "$PY" -c 'import api.server' || true; erros=$((erros + 1))
    fi

    local porta
    for porta in "$API_PORT" "$CORACI_PORT"; do
        if porta_em_uso "$porta"; then
            if [[ "$porta" == "$API_PORT" ]] && health_api; then
                ok "porta $porta já atendida pela API do projeto"
            elif [[ "$porta" == "$CORACI_PORT" ]] && health_coraci; then
                ok "porta $porta já atendida pelo Coraci do projeto"
            elif { [[ "$porta" == "$API_PORT" ]] && pid_vivo "$API_PID" "api.server:app"; } ||
                 { [[ "$porta" == "$CORACI_PORT" ]] && pid_vivo "$CORACI_PID" "Aplicativo_Coraci/app.py"; }; then
                warn "porta $porta reservada por um serviço que ainda está subindo"
            else
                fail "porta $porta já está em uso por outro processo (use IA_LAB_API_PORT=...)"
                erros=$((erros + 1))
            fi
        else
            ok "porta $porta livre"
        fi
    done

    if curl -fsS --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
        local modelo
        modelo="$(env_get IA_LAB_OLLAMA_MODEL || true)"
        modelo="${modelo:-glm4:latest}"
        if curl -fsS --max-time 3 http://localhost:11434/api/tags |
            "$PY" -c 'import json,sys; nomes={m["name"] for m in json.load(sys.stdin)["models"]}; sys.exit(0 if sys.argv[1] in nomes else 1)' "$modelo"; then
            ok "Ollama acessível, modelo $modelo instalado"
        else
            fail "Ollama acessível, mas o modelo '$modelo' não está instalado (ollama list)"
            erros=$((erros + 1))
        fi
    else
        fail "Ollama não responde em http://localhost:11434 (fallback local indisponível)"
        erros=$((erros + 1))
    fi

    local db
    db="$(env_get IA_LAB_CORACI_DB || true)"; db="${db:-coraci.db}"
    if mkdir -p "$(dirname "$db")" 2>/dev/null && [[ -w "$(dirname "$db")" ]]; then
        ok "diretório do banco Coraci gravável: $(dirname "$db")"
    else
        fail "diretório do banco Coraci não é gravável: $(dirname "$db")"
        erros=$((erros + 1))
    fi

    [[ "$erros" -eq 0 ]] || die "$erros verificação(ões) falharam"
    ok "configuração validada"
}

# ── start ────────────────────────────────────────────────────────────────────
esperar() {
    local tentativas=40
    while (( tentativas-- > 0 )); do
        "$1" && return 0
        sleep 0.5
    done
    return 1
}

cmd_start() {
    cmd_check

    if health_api; then
        ok "API já responde em http://127.0.0.1:${API_PORT}"
    else
        : > "$API_LOG"
        nohup "$PY" -m uvicorn api.server:app \
            --host 127.0.0.1 --port "$API_PORT" --log-level info \
            >>"$API_LOG" 2>&1 &
        echo $! > "$API_PID"
        if esperar health_api; then
            ok "API iniciada em http://127.0.0.1:${API_PORT} (pid $(cat "$API_PID"))"
        else
            tail -30 "$API_LOG" >&2 || true
            die "API não respondeu em 20s — log: $API_LOG"
        fi
    fi

    if health_coraci; then
        ok "Coraci já responde em http://127.0.0.1:${CORACI_PORT}"
    else
        : > "$CORACI_LOG"
        nohup "$PY" "$REPO_ROOT/Aplicativo_Coraci/app.py" \
            --host 127.0.0.1 --port "$CORACI_PORT" \
            >>"$CORACI_LOG" 2>&1 &
        echo $! > "$CORACI_PID"
        if esperar health_coraci; then
            ok "Coraci iniciado em http://127.0.0.1:${CORACI_PORT} (pid $(cat "$CORACI_PID"))"
        else
            tail -30 "$CORACI_LOG" >&2 || true
            die "Coraci não respondeu em 20s — log: $CORACI_LOG"
        fi
    fi
}

# ── stop ─────────────────────────────────────────────────────────────────────
parar() {
    local nome="$1" arquivo="$2" padrao="$3" checagem="$4"
    if ! pid_vivo "$arquivo" "$padrao"; then
        rm -f "$arquivo"
        ok "$nome não está rodando"
        return 0
    fi
    local pid
    pid="$(cat "$arquivo")"
    kill -TERM "$pid" 2>/dev/null || true
    for _ in {1..20}; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.5
    done
    if kill -0 "$pid" 2>/dev/null; then
        if [[ "$FORCE_KILL" == "1" ]]; then
            warn "$nome não encerrou com SIGTERM — enviando SIGKILL ($pid)"
            kill -KILL "$pid" 2>/dev/null || true
        else
            fail "$nome (pid $pid) ainda vivo após 10s; use IA_LAB_FORCE_KILL=1"
            return 1
        fi
    fi
    rm -f "$arquivo"
    if "$checagem"; then
        warn "$nome encerrou, mas a porta ainda responde"
        return 1
    fi
    ok "$nome parado"
}

cmd_stop() {
    detect_python || PY=python3
    local falhas=0
    parar "Coraci" "$CORACI_PID" "Aplicativo_Coraci/app.py" health_coraci || falhas=$((falhas + 1))
    parar "API" "$API_PID" "uvicorn api.server:app" health_api || falhas=$((falhas + 1))
    [[ "$falhas" -eq 0 ]] || die "parada incompleta"
}

# ── status ───────────────────────────────────────────────────────────────────
cmd_status() {
    local rc=0
    if health_api; then ok "API     : http://127.0.0.1:${API_PORT} (pid $(cat "$API_PID" 2>/dev/null || echo '?'))"
    else fail "API     : sem resposta em :${API_PORT}"; rc=1; fi

    if health_coraci; then ok "Coraci  : http://127.0.0.1:${CORACI_PORT} (pid $(cat "$CORACI_PID" 2>/dev/null || echo '?'))"
    else fail "Coraci  : sem resposta em :${CORACI_PORT}"; rc=1; fi

    if health_api; then
        local ready
        ready="$(curl -s --max-time 3 "http://127.0.0.1:${API_PORT}/api/health/ready" || true)"
        printf '         readiness: %s\n' "${ready:-sem resposta}"
    fi
    return "$rc"
}

# ── diagnose ─────────────────────────────────────────────────────────────────
cmd_diagnose() {
    detect_python || PY=python3
    echo "== repositório =="
    echo "  $REPO_ROOT"
    git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null | sed 's/^/  branch: /' || true
    git -C "$REPO_ROOT" log -1 --format='  commit: %h %s' 2>/dev/null || true

    echo "== python =="
    echo "  $("$PY" -V 2>&1) — $PY"

    echo "== portas =="
    ss -ltnp 2>/dev/null | grep -E ":(8000|8010|5000|5173|6379|6333|8080|11434)\b" | sed 's/^/  /' || echo "  (nenhuma)"

    echo "== containers (projetos vizinhos) =="
    docker ps --format '  {{.Names}}  {{.Status}}  {{.Ports}}' 2>/dev/null | head -20 || echo "  docker indisponível"

    echo "== ollama =="
    curl -fsS --max-time 3 http://localhost:11434/api/tags 2>/dev/null |
        "$PY" -c 'import json,sys; [print("  ", m["name"]) for m in json.load(sys.stdin)["models"]]' ||
        echo "  (sem resposta)"

    echo "== logs recentes =="
    tail -5 "$API_LOG" 2>/dev/null | sed 's/^/  api| /' || echo "  (sem log da API)"
    tail -5 "$CORACI_LOG" 2>/dev/null | sed 's/^/  coraci| /' || echo "  (sem log do Coraci)"
}

# ── test ─────────────────────────────────────────────────────────────────────
cmd_test() {
    cmd_check
    echo "== pytest =="
    "$PY" -m pytest tests/ -q --no-header -p no:cacheprovider
    echo "== ruff =="
    ruff check ai api src tests
    ruff format --check ai api src tests
    echo "== mypy =="
    mypy ai api src
    ok "suíte, lint e tipos aprovados"
}

usage() {
    sed -n '3,26p' "$0" | sed 's/^# \{0,1\}//'
}

case "${1:-help}" in
    check)    cmd_check ;;
    start)    cmd_start ;;
    stop)     cmd_stop ;;
    restart)  cmd_stop && cmd_start ;;
    status)   cmd_status ;;
    diagnose) cmd_diagnose ;;
    test)     cmd_test ;;
    help|-h|--help) usage ;;
    *) die "comando desconhecido: $1 (use: check|start|stop|restart|status|diagnose|test)" ;;
esac
