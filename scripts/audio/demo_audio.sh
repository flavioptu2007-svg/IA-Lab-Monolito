#!/bin/bash
# =============================================================================
# demo_audio.sh - Demonstração completa dos scripts Bash de áudio
# =============================================================================
# Executa todos os scripts do módulo de áudio em sequência lógica:
#   1. Diagnóstico completo do sistema
#   2. Criação do microfone virtual
#   3. Teste de captura (microfone)
#   4. Teste de reprodução (alto-falantes)
#   5. Backup da configuração atual
#
# Uso:
#   ./scripts/audio/demo_audio.sh             # Dry-run (mostra o que será feito)
#   ./scripts/audio/demo_audio.sh --apply     # Executa a demonstração completa
#   ./scripts/audio/demo_audio.sh --quick     # Apenas diagnóstico + backup
#   ./scripts/audio/demo_audio.sh --help      # Ajuda
# =============================================================================

set -euo pipefail

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# ── Configurações ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIO_DIR="$SCRIPT_DIR"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$HOME/.local/log/audio/demo"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="$LOG_DIR/demo_${TIMESTAMP}.log"
RESULTS_FILE="/tmp/ia_demo_results_${TIMESTAMP}.txt"

# Flags
DRY_RUN=true
QUICK=false

# ── Parse de argumentos ──────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --apply)
            DRY_RUN=false
            shift
            ;;
        --quick)
            QUICK=true
            shift
            ;;
        --help|-h)
            echo "Uso: $0 [--apply] [--quick]"
            echo ""
            echo "  (sem flags)  Dry-run: mostra o que seria executado"
            echo "  --apply      Executa a demonstração completa"
            echo "  --quick      Apenas diagnóstico + backup (pula testes de HW)"
            exit 0
            ;;
    esac
done

# ── Garantir diretório de logs ───────────────────────────────────────────────
mkdir -p "$LOG_DIR"

# Limpeza em caso de interrupção
trap 'rm -f "$RESULTS_FILE" 2>/dev/null' EXIT

# ── Funções ───────────────────────────────────────────────────────────────────

log() {
    local msg
    msg="$(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

run_cmd() {
    local cmd="$1"
    local desc="$2"

    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY-RUN]${NC} $desc"
        log "  Comando: $cmd"
    else
        log "${GREEN}[EXECUTANDO]${NC} $desc"
        echo -e "  ${CYAN}▶${NC} $desc"
        if eval "$cmd" 2>&1 | tee -a "$LOG_FILE"; then
            echo -e "  ${GREEN}✓ Concluído${NC}"
            echo "OK:$desc" >> "$RESULTS_FILE"
        else
            echo -e "  ${RED}✗ Falhou${NC}"
            echo "FAIL:$desc" >> "$RESULTS_FILE"
        fi
        true  # Garante retorno 0 mesmo com pipefail + tee
    fi
}

step() {
    local num="$1"
    local title="$2"
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${MAGENTA}  Etapa ${num}: ${title}${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    log "--- Etapa $num: $title ---"
}

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${BOLD}🎧 IA-Lab Demo de Áudio${NC}                           ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  $(date '+%d/%m/%Y %H:%M')                                          ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  Modo: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICAR')${NC}                                        ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""

    log "Iniciando demonstração de áudio"
    log "Modo: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICAR')"
    log "Projeto: $PROJECT_DIR"
}

print_footer() {
    local errors=0
    local success=0

    if [ -f "$RESULTS_FILE" ]; then
        errors=$(grep -c "^FAIL:" "$RESULTS_FILE" 2>/dev/null || echo 0)
        success=$(grep -c "^OK:" "$RESULTS_FILE" 2>/dev/null || echo 0)
    fi

    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}  📊 RESUMO DA DEMONSTRAÇÃO${NC}"
    echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
    echo -e "  Etapas concluídas: $((success + errors))"
    echo -e "  ${GREEN}Sucesso: ${success}${NC}"
    if [ "$errors" -gt 0 ]; then
        echo -e "  ${RED}Falhas:  ${errors}${NC}"
    else
        echo -e "  Falhas:  ${errors}"
    fi
    echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
    echo -e "  Modo:   $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICADO')"
    echo -e "  Log:    $LOG_FILE"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo ""

    log "Demonstração concluída: ${success} sucessos, ${errors} falhas"
    rm -f "$RESULTS_FILE"
}

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

print_header

# ── Etapa 1: Diagnóstico completo do sistema ─────────────────────────────────
step "1/5" "Diagnóstico do Sistema de Áudio"

run_cmd "bash \"$AUDIO_DIR/diagnose_audio.sh\" --apply --quick 2>&1 | tail -20" \
    "Diagnóstico rápido do sistema (kernel, PipeWire, dispositivos)"

if [ "$DRY_RUN" = false ]; then
    echo -e "  ${GREEN}Relatório salvo em:${NC} ~/testes-audio/relatorios/"
fi

# ── Etapa 2: Criar microfone virtual ─────────────────────────────────────────
step "2/5" "Criação do Microfone Virtual"

run_cmd "bash \"$AUDIO_DIR/setup_microfone_virtual.sh\" --apply 2>&1 | tail -15" \
    "Criação do microfone virtual (null-sink + loopback)"

# ── Etapa 3: Teste de microfone ──────────────────────────────────────────────
if [ "$QUICK" = false ]; then
    step "3/5" "Teste de Captura (Microfone)"

    run_cmd "bash \"$AUDIO_DIR/test_microphone.sh\" --apply --record-only 2>&1 | tail -15" \
        "Gravação de amostra de áudio (4s)"

    echo ""
    echo -e "  ${YELLOW}ℹ Arquivo salvo em: ~/testes-audio/teste_mic_*.wav${NC}"
else
    log "Modo --quick: pulando teste de microfone"
fi

# ── Etapa 4: Teste de alto-falantes ──────────────────────────────────────────
if [ "$QUICK" = false ]; then
    step "4/5" "Teste de Reprodução (Alto-Falantes)"

    run_cmd "bash \"$AUDIO_DIR/test_speaker.sh\" --apply --tone 440 2>&1 | tail -10" \
        "Reprodução de tom 440Hz (Lá) por 2 segundos"

    echo ""
    echo -e "  ${YELLOW}▶ Você deve ouvir um tom Lá (440Hz) por 2 segundos${NC}"
else
    log "Modo --quick: pulando teste de alto-falantes"
fi

# ── Etapa 5: Backup da configuração ──────────────────────────────────────────
step "5/5" "Backup da Configuração de Áudio"

run_cmd "bash \"$AUDIO_DIR/backup_audio_config.sh\" --apply 2>&1 | tail -10" \
    "Backup da configuração atual do PipeWire"

if [ "$DRY_RUN" = false ]; then
    echo -e "  ${GREEN}Backup salvo em:${NC} ~/.local/backups/audio/"
fi

# ── Resumo ───────────────────────────────────────────────────────────────────
print_footer

# ── Dicas finais ─────────────────────────────────────────────────────────────
echo -e "${BOLD}  💡 PRÓXIMOS PASSOS${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
echo -e "  • Execute a demo Python:  ${CYAN}python3 demo_audio.py${NC}"
echo -e "  • Inicie o servidor API:  ${CYAN}python3 -m api.server${NC}"
echo -e "  • Execute os testes:      ${CYAN}python3 -m pytest tests/test_audio/ -v${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
echo ""
