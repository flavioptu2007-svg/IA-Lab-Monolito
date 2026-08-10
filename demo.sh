#!/bin/bash
# =============================================================================
# demo.sh — Demonstração mestre: Bash + Python
# =============================================================================
# Executa os dois demos do módulo de áudio em sequência:
#   1. scripts/audio/demo_audio.sh --apply  (scripts de sistema)
#   2. python3 demo_audio.py                (módulos Python)
#
# Uso:
#   bash demo.sh               # Dry-run dos scripts Bash + Python
#   bash demo.sh --apply       # Execução completa
#   bash demo.sh --quick       # Apenas Python + diagnóstico Bash
#   bash demo.sh --help        # Ajuda
# =============================================================================

set -euo pipefail

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Configurações ────────────────────────────────────────────────────────────
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_DIR="$HOME/.local/log/audio/demo"
LOG_FILE="$LOG_DIR/demo_mestre_${TIMESTAMP}.log"

# Flags
DRY_RUN=true
QUICK=false

# ── Parse de argumentos ──────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --apply)    DRY_RUN=false; shift ;;
        --quick)    QUICK=true; shift ;;
        --help|-h)
            echo "Uso: $0 [--apply] [--quick]"
            echo ""
            echo "  (sem flags)  Dry-run: mostra o que seria executado"
            echo "  --apply      Executa a demonstração completa"
            echo "  --quick      Apenas Python + diagnóstico (pula testes de HW)"
            exit 0
            ;;
    esac
done

mkdir -p "$LOG_DIR"

# ── Funções ───────────────────────────────────────────────────────────────────

log() {
    local msg="$(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

section() {
    local emoji="$1" title="$2"
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}  $emoji  $title${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    log "--- $title ---"
}

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${BOLD}🎧 IA-Lab Demo Mestre (Bash + Python)${NC}             ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  $(date '+%d/%m/%Y %H:%M')                                          ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  Modo: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICAR')${NC}                                        ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    log "Iniciando demo mestre"
}

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

print_header

# ── Parte 1: Bash ────────────────────────────────────────────────────────────
section "🖥️" "Parte 1: Scripts Bash (sistema)"

BASH_FLAGS="--apply"
if [ "$QUICK" = true ]; then
    BASH_FLAGS="$BASH_FLAGS --quick"
fi

if [ "$DRY_RUN" = true ]; then
    echo -e "  ${YELLOW}[DRY-RUN]${NC} Comando: bash scripts/audio/demo_audio.sh $BASH_FLAGS"
    log "[DRY-RUN] bash scripts/audio/demo_audio.sh $BASH_FLAGS"
else
    log "Executando: bash scripts/audio/demo_audio.sh $BASH_FLAGS"
    echo -e "  ${CYAN}▶${NC} Executando scripts Bash..."
    bash "$DIR/scripts/audio/demo_audio.sh" $BASH_FLAGS 2>&1 | tee -a "$LOG_FILE"
    BASH_EXIT=${PIPESTATUS[0]}
    echo ""
fi

# ── Parte 2: Python ──────────────────────────────────────────────────────────
section "🐍" "Parte 2: Módulos Python"

PYTHON_FLAGS=""
if [ "$QUICK" = true ]; then
    PYTHON_FLAGS="--quick"
fi

if [ "$DRY_RUN" = true ]; then
    echo -e "  ${YELLOW}[DRY-RUN]${NC} Comando: python3 demo_audio.py $PYTHON_FLAGS"
    log "[DRY-RUN] python3 demo_audio.py $PYTHON_FLAGS"
else
    log "Executando: python3 demo_audio.py $PYTHON_FLAGS"
    echo -e "  ${CYAN}▶${NC} Executando módulos Python..."
    python3 "$DIR/demo_audio.py" $PYTHON_FLAGS 2>&1 | tee -a "$LOG_FILE"
    PYTHON_EXIT=${PIPESTATUS[0]}
    echo ""
fi

# ── Resumo final ──────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  📊 RESUMO FINAL${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "  Modo DRY-RUN — nada foi executado"
    echo -e "  Execute com ${CYAN}--apply${NC} para rodar a demonstração completa"
else
    BASH_STATUS="${GREEN}OK${NC}"
    PYTHON_STATUS="${GREEN}OK${NC}"
    [ "${BASH_EXIT:-1}" -ne 0 ] && BASH_STATUS="${RED}FALHA${NC}"
    [ "${PYTHON_EXIT:-1}" -ne 0 ] && PYTHON_STATUS="${RED}FALHA${NC}"

    echo -e "  🖥️  Bash:   $BASH_STATUS"
    echo -e "  🐍 Python: $PYTHON_STATUS"
    echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
    echo -e "  Log completo: $LOG_FILE"
    echo ""
    echo -e "  ${YELLOW}💡 Dica:${NC} Para ouvir os tons, certifique-se de que os alto-falantes estão ligados!"
fi
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo ""

log "Demo mestre concluída"
