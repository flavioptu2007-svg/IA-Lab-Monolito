#!/bin/bash
# =============================================================================
# test_speaker.sh - Testa reprodução de áudio nos alto-falantes
# =============================================================================
# Reproduz tons de teste, varre canais e verifica configuração de saída.
#
# Uso:
#   ./test_speaker.sh                       # Testa o sink padrão (dry-run)
#   ./test_speaker.sh --apply               # Executa o teste real
#   ./test_speaker.sh --list                # Lista dispositivos de saída
#   ./test_speaker.sh --tone <freq>         # Testa com frequência específica (Hz)
#   ./test_speaker.sh --sink <nome>         # Testa sink específico
# =============================================================================

set -euo pipefail

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Configurações ────────────────────────────────────────────────────────────
LOG_DIR="$HOME/.local/log/audio"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="$LOG_DIR/test_speaker_${TIMESTAMP}.log"

TONE_FREQ=440       # Frequência padrão: Lá (440 Hz)
TONE_DURATION=2     # Duração em segundos
TEST_FILE="/tmp/ia_lab_test_tone.wav"

# Flags
SINK_SPECIFIED=""
LIST_ONLY=false
DRY_RUN=true

# ── Parse de argumentos ──────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --apply)
            DRY_RUN=false
            shift
            ;;
        --list)
            LIST_ONLY=true
            shift
            ;;
        --tone)
            TONE_FREQ="$2"
            shift 2
            ;;
        --sink)
            SINK_SPECIFIED="$2"
            shift 2
            ;;
        --help|-h)
            echo "Uso: $0 [--apply] [--list] [--tone <Hz>] [--sink <nome>]"
            echo ""
            echo "  (sem flags)        Dry-run: mostra o que seria testado"
            echo "  --apply            Executa o teste real"
            echo "  --list             Apenas lista dispositivos de saída"
            echo "  --tone <Hz>        Frequência do tom (padrão: 440)"
            echo "  --sink <nome>      Sink específico (padrão: default)"
            exit 0
            ;;
    esac
done

# ── Garantir diretórios ──────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"

# ── Funções ───────────────────────────────────────────────────────────────────

log() {
    local msg="$(date '+%Y-%m-%d %H:%M:%S') - $1"
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
    for cmd in ffmpeg ffplay speaker-test pactl; do
        if ! command -v "$cmd" &>/dev/null; then
            echo -e "${YELLOW}AVISO:${NC} $cmd não encontrado"
        fi
    done
}

frequency_name() {
    local freq=$1
    case $freq in
        55|110|220|440)     echo "Lá (A$(( freq / 55 )))" ;;
        65|130|260|523)     echo "Dó (C$(( freq / 65 )))" ;;
        73|147|294|587)     echo "Ré (D$(( freq / 73 )))" ;;
        82|165|330|659)     echo "Mi (E$(( freq / 82 )))" ;;
        87|175|349|698)     echo "Fá (F$(( freq / 87 )))" ;;
        98|196|392|784)     echo "Sol (G$(( freq / 98 )))" ;;
        103|207|415|831)    echo "Lá bemol (A♭$(( freq / 103 )))" ;;
        *)                  echo "${freq}Hz" ;;
    esac
}

# ── Listar sinks ──────────────────────────────────────────────────────────────

list_sinks() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  DISPOSITIVOS DE SAÍDA (ALTO-FALANTES)${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    local sinks
    sinks=$(pactl list sinks short 2>/dev/null)

    if [ -z "$sinks" ]; then
        echo -e "  ${RED}Nenhum sink encontrado${NC}"
        return 1
    fi

    echo ""
    printf "  ${CYAN}%-5s %-45s %s${NC}\n" "Índ." "Nome" "Estado"
    echo "  $(printf '%0.s-' {1..70})"

    echo "$sinks" | while read -r line; do
        local idx name state
        idx=$(echo "$line" | awk '{print $1}')
        name=$(echo "$line" | awk '{print $2}')
        state=$(echo "$line" | awk '{print $NF}')
        local formatted_name="${name:0:43}"
        printf "  %-5s %-45s %s\n" "$idx" "$formatted_name" "$state"
    done

    # Sink padrão
    echo ""
    local default_sink
    default_sink=$(pactl get-default-sink 2>/dev/null)
    echo -e "  ${GREEN}▶ Sink padrão:${NC} $default_sink"

    # Detalhes
    echo ""
    echo -e "  ${CYAN}Detalhes do sink padrão:${NC}"
    pactl list sinks 2>/dev/null | sed -n "/$default_sink/,/^$/p" | head -12 | \
        grep -E "(Name|Description|State|Mute|Volume|Rate|Channels|Formato)" | sed 's/^/    /'
}

# ── Gerar tom de teste ────────────────────────────────────────────────────────

generate_tone() {
    local freq=$1
    local duration=$2
    local output=$3

    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  GERANDO TOM DE TESTE${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    local freq_name
    freq_name=$(frequency_name "$freq")
    echo ""
    echo -e "  ${CYAN}Frequência:${NC} ${freq}Hz ($freq_name)"
    echo -e "  ${CYAN}Duração:${NC}   ${duration}s"
    echo -e "  ${CYAN}Formato:${NC}   WAV 44100Hz 16bit mono"
    echo -e "  ${CYAN}Arquivo:${NC}   $output"

    # Gerar senoide com ffmpeg
    if command -v ffmpeg &>/dev/null; then
        run_cmd "ffmpeg -y -f lavfi -i \"sine=frequency=$freq:duration=$duration\" \
            -ac 1 -ar 44100 -sample_fmt s16 \
            -metadata title=\"Tom de Teste ${freq}Hz\" \
            -metadata comment=\"IA-Lab Audio Test\" \
            \"$output\" 2>&1 | tail -5" \
            "Gerando tom senoidal de ${freq}Hz por ${duration}s"

        if [ -f "$output" ] && [ "$DRY_RUN" = false ]; then
            log "${GREEN}✓ Tom gerado: $output${NC}"
        fi
    else
        # Fallback: sox
        if command -v sox &>/dev/null; then
            run_cmd "sox -n -r 44100 -c 1 \"$output\" synth $duration sine $freq" \
                "Gerando tom com sox (${freq}Hz)"
        else
            log "${RED}ERRO: nem ffmpeg nem sox estão disponíveis para gerar tom${NC}"
            return 1
        fi
    fi
}

# ── Reproduzir tom ────────────────────────────────────────────────────────────

play_tone() {
    local sink="$1"

    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  REPRODUZINDO TOM DE TESTE${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${YELLOW}▶ Você deve ouvir um tom de $(frequency_name "$TONE_FREQ") (${TONE_FREQ}Hz) por ${TONE_DURATION}s${NC}"

    if [ -n "$sink" ]; then
        echo -e "  ${CYAN}Sink:${NC} $sink"
    fi

    echo ""

    if [ -f "$TEST_FILE" ] && [ "$DRY_RUN" = false ]; then
        # Tenta ffplay primeiro
        if command -v ffplay &>/dev/null; then
            if [ -n "$sink" ]; then
                # Usa PULSE_SINK para redirecionar a saída para o sink específico
                run_cmd "PULSE_SINK=\"$sink\" ffplay -nodisp -autoexit -volume 75 \
                    \"$TEST_FILE\" 2>/dev/null || \
                    ffplay -nodisp -autoexit -volume 75 \"$TEST_FILE\" 2>/dev/null || \
                    speaker-test -t sine -f $TONE_FREQ -l 1 2>/dev/null" \
                    "Reproduzindo tom no sink $sink"
            else
                run_cmd "ffplay -nodisp -autoexit -volume 75 \"$TEST_FILE\" 2>/dev/null || \
                    speaker-test -t sine -f $TONE_FREQ -l 1 2>/dev/null" \
                    "Reproduzindo tom no sink padrão"
            fi
        elif command -v aplay &>/dev/null; then
            run_cmd "aplay \"$TEST_FILE\" 2>/dev/null" \
                "Reproduzindo com aplay"
        elif command -v speaker-test &>/dev/null; then
            run_cmd "speaker-test -t sine -f $TONE_FREQ -l 1 2>/dev/null" \
                "Reproduzindo com speaker-test"
        else
            log "${RED}Nenhum reprodutor de áudio disponível${NC}"
        fi

        log "${GREEN}✓ Reprodução concluída${NC}"
    elif [ "$DRY_RUN" = false ]; then
        # Fallback direto para speaker-test se não temos arquivo
        if command -v speaker-test &>/dev/null; then
            run_cmd "speaker-test -t sine -f $TONE_FREQ -l 1 2>/dev/null" \
                "Reproduzindo tom com speaker-test"
        else
            log "${YELLOW}Arquivo de teste não encontrado e speaker-test não disponível${NC}"
        fi
    else
        log "${YELLOW}[DRY-RUN] Tom seria reproduzido por ${TONE_DURATION}s${NC}"
    fi
}

# ── Teste de canais ───────────────────────────────────────────────────────────

test_channels() {
    if [ "$DRY_RUN" = true ] || [ "$LIST_ONLY" = true ]; then
        return 0
    fi

    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  TESTE DE CANAIS${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${YELLOW}▶ Testando canais (esquerdo/direito)...${NC}"
    echo ""

    if command -v speaker-test &>/dev/null; then
        run_cmd "speaker-test -c 2 -l 1 -t sine -f $TONE_FREQ 2>&1 | head -10" \
            "Testando canais estéreo"
    else
        log "${YELLOW}speaker-test não disponível para teste de canais${NC}"
    fi
}

# ── Execução principal ────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  🔊 IA-Lab Teste de Alto-Falantes                      ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  $(date '+%d/%m/%Y %H:%M')                                          ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"

check_dependencies

# ── Verificar PipeWire ────────────────────────────────────────────────────────
if ! pactl info &>/dev/null; then
    log "${RED}ERRO: PipeWire/PulseAudio não está rodando${NC}"
    exit 1
fi
log "${GREEN}PipeWire operacional${NC}"

# ── Listar sinks ──────────────────────────────────────────────────────────────
list_sinks

if [ "$LIST_ONLY" = true ]; then
    log "Modo --list: apenas listagem"
    exit 0
fi

# ── Determinar sink ──────────────────────────────────────────────────────────
local_sink=""
if [ -n "$SINK_SPECIFIED" ]; then
    local_sink="$SINK_SPECIFIED"
    log "Usando sink especificado: $local_sink"
else
    local_sink=$(pactl get-default-sink 2>/dev/null || echo "")
    log "Usando sink padrão: ${local_sink:-default}"
fi

# ── Executar testes ───────────────────────────────────────────────────────────
generate_tone "$TONE_FREQ" "$TONE_DURATION" "$TEST_FILE"
play_tone "$local_sink"
test_channels

# ── Limpeza ───────────────────────────────────────────────────────────────────
if [ "$DRY_RUN" = false ] && [ -f "$TEST_FILE" ]; then
    rm -f "$TEST_FILE"
    log "Arquivo temporário removido: $TEST_FILE"
fi

# ── Resumo ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Teste concluído!${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
echo -e "  Modo:       $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICADO')"
echo -e "  Sink:       ${local_sink:-padrão}"
echo -e "  Tom:        ${TONE_FREQ}Hz ($(frequency_name "$TONE_FREQ"))"
echo -e "  Duração:    ${TONE_DURATION}s"
echo -e "  Log:        $LOG_FILE"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo ""
