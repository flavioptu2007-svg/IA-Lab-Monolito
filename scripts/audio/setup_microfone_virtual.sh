#!/bin/bash
# =============================================================================
# setup_microfone_virtual.sh - Cria microfone virtual no PipeWire
# =============================================================================
# Cria um sink nulo (null-sink) + loopbacks para servir como microfone virtual.
# Útil para redirecionar áudio do sistema para apps de IA (STT, voice assistants).
#
# Uso:
#   ./setup_microfone_virtual.sh              # Dry-run (mostra o que será feito)
#   ./setup_microfone_virtual.sh --apply       # Cria/recria o microfone virtual
#   ./setup_microfone_virtual.sh --remove      # Remove o microfone virtual
#   ./setup_microfone_virtual.sh --status      # Mostra status atual
# =============================================================================

set -euo pipefail

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Configurações ────────────────────────────────────────────────────────────
SCRIPT_NAME="microfone-virtual"
LOG_DIR="$HOME/.local/log/audio"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="$LOG_DIR/${SCRIPT_NAME}_${TIMESTAMP}.log"

# Nomes dos dispositivos virtuais
NULL_SINK_NAME="ia-lab-mic"
NULL_SINK_DESCRIPTION="IA-Lab Microfone Virtual"

# Flags
DRY_RUN=true
ACTION="create"  # create, remove, status

# ── Parse de argumentos ──────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --apply)
            DRY_RUN=false
            shift
            ;;
        --remove)
            ACTION="remove"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --help|-h)
            echo "Uso: $0 [--apply] [--remove] [--status]"
            echo ""
            echo "  (sem flags)  Dry-run: mostra o que seria criado"
            echo "  --apply      Cria/recria o microfone virtual"
            echo "  --remove     Remove o microfone virtual"
            echo "  --status     Mostra status atual dos dispositivos"
            exit 0
            ;;
    esac
done

# ── Garantir diretório de logs ───────────────────────────────────────────────
mkdir -p "$LOG_DIR"

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
        eval "$cmd" 2>&1 | tee -a "$LOG_FILE" || true
    fi
}

check_dependencies() {
    local missing=0
    for cmd in pactl pw-cli pw-dump; do
        if ! command -v "$cmd" &>/dev/null; then
            echo -e "${RED}ERRO:${NC} $cmd não encontrado. Instale o PipeWire primeiro."
            missing=1
        fi
    done
    return "$missing"
}

sink_exists() {
    pactl list sinks short 2>/dev/null | grep -q "$NULL_SINK_NAME"
}

source_exists() {
    pactl list sources short 2>/dev/null | grep -q "$NULL_SINK_NAME"
}

module_exists() {
    local name="$1"
    pactl list modules short 2>/dev/null | grep -qi "$name"
}

get_sink_index() {
    pactl list sinks short 2>/dev/null | grep "$NULL_SINK_NAME" | awk '{print $1}' | head -1
}

get_source_index() {
    pactl list sources short 2>/dev/null | grep "$NULL_SINK_NAME" | grep -v monitor | awk '{print $1}' | head -1
}

get_default_sink() {
    pactl get-default-sink 2>/dev/null
}

# ── Ações ─────────────────────────────────────────────────────────────────────

action_status() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  STATUS DO MICROFONE VIRTUAL${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    echo ""
    echo -e "${CYAN}▶ Null Sink (${NULL_SINK_NAME}):${NC}"
    if sink_exists; then
        local idx
        idx=$(get_sink_index)
        echo -e "  ${GREEN}✓${NC} Sink ativo (índice $idx)"
        pactl list sinks 2>/dev/null | sed -n "/$NULL_SINK_NAME/,/^$/p" | grep -E "(Name|Description|State|Mute|Volume)" | head -6 | sed 's/^/  /'
    else
        echo -e "  ${RED}✗${NC} Sink não encontrado"
    fi

    echo ""
    echo -e "${CYAN}▶ Source (virtual mic):${NC}"
    if source_exists; then
        local idx
        idx=$(get_source_index)
        echo -e "  ${GREEN}✓${NC} Source ativo (índice $idx)"
        pactl list sources 2>/dev/null | sed -n "/$NULL_SINK_NAME/,/^$/p" | grep -E "(Name|Description|State|Mute|Volume)" | grep -v monitor | head -6 | sed 's/^/  /'
    else
        echo -e "  ${RED}✗${NC} Source não encontrado"
    fi

    echo ""
    echo -e "${CYAN}▶ Sink de saída padrão:${NC}"
    echo -e "  $(get_default_sink)"

    echo ""
    echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
}

action_create() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  CONFIGURAÇÃO DO MICROFONE VIRTUAL${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    log "Modo: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICAR')"

    # Verificar dependências
    if ! check_dependencies; then
        log "${RED}Dependências ausentes. Abortando.${NC}"
        exit 1
    fi

    # ── Passo 1: Verificar se PipeWire está rodando
    echo ""
    echo -e "${CYAN}▸ 1. Verificando PipeWire${NC}"
    if pactl info &>/dev/null; then
        log "${GREEN}PipeWire/PulseAudio está operacional${NC}"
    else
        log "${RED}PipeWire não está rodando. Execute: systemctl --user start pipewire${NC}"
        return 1
    fi

    # ── Passo 2: Remover configuração anterior se existir
    echo ""
    echo -e "${CYAN}▸ 2. Limpando configuração anterior${NC}"
    if sink_exists; then
        local sink_idx
        sink_idx=$(get_sink_index)
        if [ -n "$sink_idx" ]; then
            run_cmd "pactl unload-module $(pactl list modules short 2>/dev/null | grep -i "$NULL_SINK_NAME" | awk '{print $1}' | head -1 2>/dev/null) 2>/dev/null || true" \
                "Removendo sink virtual anterior (índice $sink_idx)"
        fi
    else
        log "${GREEN}Nenhum sink virtual anterior encontrado${NC}"
    fi

    # ── Passo 3: Criar null-sink (microfone virtual)
    echo ""
    echo -e "${CYAN}▸ 3. Criando null-sink (${NULL_SINK_NAME})${NC}"
    run_cmd "pactl load-module module-null-sink \
        sink_name=$NULL_SINK_NAME \
        sink_properties=\"device.description=$NULL_SINK_DESCRIPTION\"" \
        "Criando sink nulo como base do microfone virtual"

    # ── Passo 4: Aguardar estabilização
    if [ "$DRY_RUN" = false ]; then
        sleep 0.5
    fi

    # ── Passo 5: Loopback do sink padrão para o null-sink
    echo ""
    echo -e "${CYAN}▸ 4. Conectando loopback do sistema → microfone virtual${NC}"
    local default_sink
    default_sink=$(get_default_sink)
    if [ -n "$default_sink" ] && [ "$default_sink" != "null" ]; then
        run_cmd "pactl load-module module-loopback \
            source=${default_sink}.monitor \
            sink=$NULL_SINK_NAME \
            latency_msec=25 \
            source_dont_move=true \
            sink_dont_move=true" \
            "Criando loopback: $default_sink → $NULL_SINK_NAME"
    else
        log "${YELLOW}AVISO: Nenhum sink padrão encontrado para loopback${NC}"
    fi

    # ── Passo 6: Verificar resultado
    echo ""
    echo -e "${CYAN}▸ 5. Verificando resultado${NC}"
    if [ "$DRY_RUN" = false ]; then
        sleep 0.5
        if source_exists; then
            log "${GREEN}✓ Microfone virtual criado com sucesso!${NC}"
            echo ""
            echo -e "  ${GREEN}Nome do source (microfone virtual):${NC} $NULL_SINK_NAME.monitor"
            echo -e "  ${GREEN}Descrição:${NC} $NULL_SINK_DESCRIPTION"
            echo ""
            echo -e "  ${YELLOW}Para usar em apps:${NC} selecione o microfone chamado \"$NULL_SINK_DESCRIPTION\""
            echo -e "  ${YELLOW}Ou use o nome PulseAudio:${NC} $NULL_SINK_NAME.monitor"
            echo ""
        else
            log "${RED}✗ Falha ao criar microfone virtual${NC}"
        fi
    fi

    echo ""
    echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
}

action_remove() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  REMOVENDO MICROFONE VIRTUAL${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    log "Modo: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICAR')"

    # Listar módulos relacionados
    local modules
    modules=$(pactl list modules short 2>/dev/null | grep -iE "($NULL_SINK_NAME|ia-lab-)" | awk '{print $1}')

    if [ -z "$modules" ]; then
        log "${YELLOW}Nenhum módulo do microfone virtual encontrado. Nada a remover.${NC}"
        return 0
    fi

    echo ""
    echo -e "${CYAN}▸ Módulos encontrados para remoção:${NC}"
    pactl list modules short 2>/dev/null | grep -iE "($NULL_SINK_NAME|ia-lab-)" | while read -r line; do
        echo -e "  $line"
    done

    # Remover cada módulo
    echo ""
    for mod_id in $modules; do
        local mod_desc
        mod_desc=$(pactl list modules short 2>/dev/null | grep "^$mod_id" | awk '{$1=""; print $0}' | xargs)
        run_cmd "pactl unload-module $mod_id" "Removendo módulo $mod_id: $mod_desc"
    done

    # Verificar resultado
    local remaining
    remaining=$(pactl list modules short 2>/dev/null | grep -c -iE "($NULL_SINK_NAME|ia-lab-)" || true)
    if [ "$remaining" -eq 0 ]; then
        log "${GREEN}✓ Microfone virtual removido com sucesso${NC}"
    else
        log "${YELLOW}Ainda restam $remaining módulo(s) relacionados${NC}"
    fi

    echo ""
    echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
}

# ── Execução principal ───────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  🎤 IA-Lab Microfone Virtual                         ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  $(date '+%d/%m/%Y %H:%M')                                          ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"

case "$ACTION" in
    status)
        action_status
        ;;
    create)
        action_create
        ;;
    remove)
        action_remove
        ;;
esac

# ── Resumo ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
log "Comando: $ACTION"
log "Modo: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICADO')"
echo -e "${GREEN}Log salvo em:${NC}"
echo -e "  $LOG_FILE"
echo ""
