#!/bin/bash
# =============================================================================
# test_microphone.sh - Testa captura de áudio dos microfones
# =============================================================================
# Grava uma amostra curta, reproduz e mostra nível de volume.
#
# Uso:
#   ./test_microphone.sh                    # Lista microfones e testa o padrão
#   ./test_microphone.sh --source <nome>    # Testa fonte específica
#   ./test_microphone.sh --list             # Apenas lista dispositivos
#   ./test_microphone.sh --record-only      # Apenas grava (não reproduz)
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
LOG_DIR="$HOME/.local/log/audio"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="$LOG_DIR/test_mic_${TIMESTAMP}.log"
RECORDING_DIR="$HOME/testes-audio"
RECORDING_FILE="$RECORDING_DIR/teste_mic_${TIMESTAMP}.wav"
RECORD_SECONDS=4
SAMPLE_RATE=48000

# Flags
SOURCE_SPECIFIED=""
LIST_ONLY=false
RECORD_ONLY=false
DRY_RUN=true

# ── Parse de argumentos ──────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --apply)
            DRY_RUN=false
            shift
            ;;
        --source)
            SOURCE_SPECIFIED="$2"
            shift 2
            ;;
        --list)
            LIST_ONLY=true
            shift
            ;;
        --record-only)
            RECORD_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Uso: $0 [--apply] [--source <nome>] [--list] [--record-only]"
            echo ""
            echo "  (sem flags)       Dry-run: mostra o que seria testado"
            echo "  --apply           Executa o teste real"
            echo "  --source <nome>   Testa fonte específica (padrão: default)"
            echo "  --list            Apenas lista dispositivos de entrada"
            echo "  --record-only     Apenas grava (não reproduz)"
            exit 0
            ;;
    esac
done

# ── Garantir diretórios ──────────────────────────────────────────────────────
mkdir -p "$LOG_DIR" "$RECORDING_DIR"

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
    for cmd in pactl arecord ffmpeg sox; do
        if ! command -v "$cmd" &>/dev/null; then
            echo -e "${YELLOW}AVISO:${NC} $cmd não encontrado (funcionalidade limitada)"
        fi
    done
    return 0
}

# ── Listar dispositivos de entrada ──────────────────────────────────────────

list_sources() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  DISPOSITIVOS DE ENTRADA (MICROFONES)${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    local sources
    sources=$(pactl list sources short 2>/dev/null)

    if [ -z "$sources" ]; then
        echo -e "  ${RED}Nenhuma fonte de entrada encontrada${NC}"
        return 1
    fi

    echo ""
    printf "  ${CYAN}%-5s %-40s %s${NC}\n" "Índ." "Nome" "Estado"
    echo "  $(printf '%0.s-' {1..65})"

    echo "$sources" | while read -r line; do
        local idx name state
        idx=$(echo "$line" | awk '{print $1}')
        name=$(echo "$line" | awk '{print $2}')
        state=$(echo "$line" | awk '{print $NF}')
        local formatted_name="${name:0:38}"
        printf "  %-5s %-40s %s\n" "$idx" "$formatted_name" "$state"
    done

    # Fonte padrão
    echo ""
    local default_source
    default_source=$(pactl get-default-source 2>/dev/null)
    echo -e "  ${GREEN}▶ Fonte padrão:${NC} $default_source"

    # Detalhes da fonte padrão
    echo ""
    echo -e "  ${CYAN}Detalhes da fonte padrão:${NC}"
    pactl list sources 2>/dev/null | sed -n "/$(pactl get-default-source 2>/dev/null)/,/^$/p" | head -12 | \
        grep -E "(Name|Description|State|Mute|Volume|Sample|Formato|Rate|Channels)" | sed 's/^/    /'

    return 0
}

# ── Teste de gravação ─────────────────────────────────────────────────────────

test_recording() {
    local source_name="$1"

    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  TESTE DE GRAVAÇÃO${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    echo ""
    echo -e "  ${CYAN}Fonte:${NC} $source_name"
    echo -e "  ${CYAN}Duração:${NC} ${RECORD_SECONDS}s"
    echo -e "  ${CYAN}Taxa:${NC} ${SAMPLE_RATE}Hz"
    echo -e "  ${CYAN}Arquivo:${NC} $RECORDING_FILE"

    # Gravar usando arecord (WAV)
    echo ""
    echo -e "${CYAN}▸ 1. Gravando...${NC}"
    log "Iniciando gravação de ${RECORD_SECONDS}s..."

    # Usa arecord por ser mais leve e sempre disponível
    run_cmd "arecord -f cd -t wav -d $RECORD_SECONDS -r $SAMPLE_RATE \
        -D \"$source_name\" \"$RECORDING_FILE\" 2>&1 || \
        arecord -f cd -t wav -d $RECORD_SECONDS -r $SAMPLE_RATE \
        \"$RECORDING_FILE\" 2>&1 || \
        echo 'Falha na gravação com arecord'" \
        "Gravando amostra de ${RECORD_SECONDS}s"

    # Verificar se o arquivo foi criado
    if [ -f "$RECORDING_FILE" ] && [ "$DRY_RUN" = false ]; then
        local file_size
        file_size=$(stat -c%s "$RECORDING_FILE" 2>/dev/null || echo 0)
        if [ "$file_size" -gt 1000 ]; then
            log "${GREEN}✓ Gravação concluída: $RECORDING_FILE ($((file_size / 1024)) KB)${NC}"
        else
            log "${YELLOW}⚠ Arquivo muito pequeno (${file_size} bytes). Microfone pode estar mudo.${NC}"
        fi
    else
        log "${YELLOW}[DRY-RUN] Arquivo seria salvo em: $RECORDING_FILE${NC}"
    fi
}

# ── Medição de nível ──────────────────────────────────────────────────────────

measure_level() {
    local source_name="$1"

    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  MEDIÇÃO DE NÍVEL DE ÁUDIO${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    if [ "$DRY_RUN" = false ]; then
        echo ""
        log "Medindo nível de volume por 3 segundos..."

        # Usa sox para medir nível em tempo real
        if command -v sox &>/dev/null; then
            echo ""
            echo -e "  ${YELLOW}Fale algo ou faça som próximo ao microfone...${NC}"
            echo ""

            # Captura e mostra nível RMS
            timeout 3 sox -t pulseaudio "$source_name" -n stats 2>&1 | \
                grep -E "(RMS|Peak|Mean)" | sed 's/^/  /' | tee -a "$LOG_FILE"

            echo ""
            log "${GREEN}✓ Medição concluída${NC}"
            echo ""
            echo -e "  ${YELLOW}Dica:${NC} Nível RMS > -30 dB = bom. < -40 dB = muito baixo."
        else
            log "${YELLOW}sox não disponível para medição de nível${NC}"
        fi
    else
        log "${YELLOW}[DRY-RUN] Medição de nível seria executada${NC}"
    fi
}

# ── Reprodução ────────────────────────────────────────────────────────────────

play_recording() {
    if [ "$RECORD_ONLY" = true ]; then
        return 0
    fi

    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  REPRODUÇÃO DA GRAVAÇÃO${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    if [ -f "$RECORDING_FILE" ]; then
        echo ""
        echo -e "  ${CYAN}Reproduzindo:${NC} $RECORDING_FILE"
        run_cmd "ffplay -nodisp -autoexit -showmode 0 \"$RECORDING_FILE\" 2>/dev/null || \
            aplay \"$RECORDING_FILE\" 2>/dev/null || \
            echo 'Nenhum reprodutor disponível'" \
            "Reproduzindo gravação"
    else
        echo ""
        echo -e "  ${YELLOW}Arquivo de gravação não encontrado. Execute --apply primeiro.${NC}"
    fi
}

# ── Execução principal ───────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  🎤 IA-Lab Teste de Microfone                         ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  $(date '+%d/%m/%Y %H:%M')                                          ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"

check_dependencies

# ── Listar fontes (sempre) ────────────────────────────────────────────────────
list_sources

if [ "$LIST_ONLY" = true ]; then
    echo ""
    log "Modo --list: apenas listagem concluída"
    exit 0
fi

# ── Determinar fonte a testar ─────────────────────────────────────────────────
local_source=""
if [ -n "$SOURCE_SPECIFIED" ]; then
    local_source="$SOURCE_SPECIFIED"
    echo ""
    log "Usando fonte especificada: $local_source"
else
    # Tenta fonte padrão
    if command -v pactl &>/dev/null; then
        local_source=$(pactl get-default-source 2>/dev/null)
    fi
    if [ -z "$local_source" ]; then
        local_source="default"
    fi
    echo ""
    log "Usando fonte padrão: $local_source"
fi

# ── Testes ────────────────────────────────────────────────────────────────────
test_recording "$local_source"
measure_level "$local_source"
play_recording

# ── Resumo ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Teste concluído!${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
echo -e "  Modo:     $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICADO')"
echo -e "  Fonte:    $local_source"
echo -e "  Arquivo:  $RECORDING_FILE"
echo -e "  Log:      $LOG_FILE"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo ""
