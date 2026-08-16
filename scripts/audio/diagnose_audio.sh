#!/bin/bash
# =============================================================================
# diagnose_audio.sh - Diagnóstico completo do pipeline de áudio
# =============================================================================
# Analisa toda a cadeia: kernel → ALSA → PipeWire/PulseAudio → apps
# Gera relatório detalhado com recomendações.
#
# Uso:
#   ./diagnose_audio.sh                    # Diagnóstico completo (dry-run)
#   ./diagnose_audio.sh --apply            # Executa diagnóstico real (salva relatório)
#   ./diagnose_audio.sh --quick            # Apenas resumo rápido
#   ./diagnose_audio.sh --latency          # Foco em latência
#   ./diagnose_audio.sh --help             # Ajuda
# =============================================================================

set -euo pipefail

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ── Configurações ────────────────────────────────────────────────────────────
LOG_DIR="$HOME/.local/log/audio"
REPORT_DIR="$HOME/testes-audio/relatorios"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
REPORT_FILE="$REPORT_DIR/diagnostico_audio_${TIMESTAMP}.md"
LOG_FILE="$LOG_DIR/diagnose_${TIMESTAMP}.log"

# Flags
DRY_RUN=true
QUICK=false
LATENCY_FOCUS=false

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
        --latency)
            LATENCY_FOCUS=true
            shift
            ;;
        --help|-h)
            echo "Uso: $0 [--apply] [--quick] [--latency]"
            echo ""
            echo "  (sem flags)    Diagnóstico completo (dry-run: mostra sem salvar)"
            echo "  --apply        Salva relatório Markdown em: $REPORT_DIR"
            echo "  --quick        Apenas resumo rápido (2s)"
            echo "  --latency      Foco em latência do pipeline"
            exit 0
            ;;
    esac
done

# ── Garantir diretórios ──────────────────────────────────────────────────────
mkdir -p "$LOG_DIR" "$REPORT_DIR"

# ── Funções ───────────────────────────────────────────────────────────────────

log() {
    local msg
    msg="$(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

report() {
    echo -e "$1" | tee -a "$REPORT_FILE"
    echo -e "$1"
}

run_cmd() {
    local cmd="$1"
    local desc="$2"

    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY-RUN]${NC} $desc"
    else
        log "${GREEN}[EXECUTANDO]${NC} $desc"
        eval "$cmd" 2>&1 | tee -a "$LOG_FILE" || true
    fi
}

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 ($(which "$1"))"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 (não encontrado)"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO 1: Kernel / Hardware
# ═══════════════════════════════════════════════════════════════════════════════

diagnose_kernel() {
    report ""
    report "## 🖥️ 1. Kernel e Hardware"
    report ""

    report "**Sistema:** $(uname -a 2>/dev/null || echo 'N/A')"
    report ""

    report "### Módulos de Áudio do Kernel"
    local snd_modules
    snd_modules=$(lsmod 2>/dev/null | grep -E "^snd" | head -20)
    if [ -n "$snd_modules" ]; then
        report "\`\`\`"
        report "$snd_modules"
        report "\`\`\`"
    else
        report "${RED}Nenhum módulo de som encontrado!${NC}"
    fi

    report ""
    report "### Dispositivos ALSA"
    report "\`\`\`"
    aplay -l 2>/dev/null | head -10 || report "  Nenhum dispositivo de reprodução"
    echo ""
    arecord -l 2>/dev/null | head -10 || report "  Nenhum dispositivo de captura"
    report "\`\`\`"
}

# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO 2: PipeWire / PulseAudio
# ═══════════════════════════════════════════════════════════════════════════════

diagnose_pipewire() {
    report ""
    report "## 🔊 2. Servidor de Áudio (PipeWire/PulseAudio)"
    report ""

    # Status do servidor
    if pactl info &>/dev/null; then
        report "**Status:** ✅ Rodando"
        report ""
        report "\`\`\`"
        pactl info 2>/dev/null || true
        report "\`\`\`"
    else
        report "**Status:** ❌ **PARADO**"
        report ""
        report "  Tente iniciar:"
        report "  \`\`\`bash"
        report "  systemctl --user start pipewire"
        report "  systemctl --user start pipewire-pulse"
        report "  \`\`\`"
        return
    fi

    # Sinks
    report ""
    report "### Sinks (saídas)"
    report "\`\`\`"
    local sinks
    sinks=$(pactl list sinks short 2>/dev/null)
    if [ -n "$sinks" ]; then
        report "$sinks"
        report ""
        report "Sink padrão: $(pactl get-default-sink 2>/dev/null || echo 'N/A')"
    else
        report "  Nenhum sink encontrado"
    fi
    report "\`\`\`"

    # Sources
    report ""
    report "### Sources (entradas)"
    report "\`\`\`"
    local sources
    sources=$(pactl list sources short 2>/dev/null)
    if [ -n "$sources" ]; then
        report "$sources"
        report ""
        report "Source padrão: $(pactl get-default-source 2>/dev/null || echo 'N/A')"
    else
        report "  Nenhum source encontrado"
    fi
    report "\`\`\`"

    # Módulos carregados
    report ""
    report "### Módulos Carregados ($(pactl list modules short 2>/dev/null | wc -l))"
    report "\`\`\`"
    pactl list modules short 2>/dev/null | head -30 || true
    report "\`\`\`"

    # Clientes conectados
    report ""
    report "### Clientes Conectados"
    local clients
    clients=$(pactl list clients short 2>/dev/null)
    if [ -n "$clients" ]; then
        report "\`\`\`"
        report "$clients"
        report "\`\`\`"
    else
        report "  Nenhum cliente conectado"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO 3: Microfones e Volumes
# ═══════════════════════════════════════════════════════════════════════════════

diagnose_mics() {
    report ""
    report "## 🎤 3. Microfones e Volumes"
    report ""

    local default_source
    default_source=$(pactl get-default-source 2>/dev/null)

    if [ -n "$default_source" ]; then
        report "**Source padrão:** $default_source"
        report ""
        report "### Estado do microfone padrão"
        report "\`\`\`"
        pactl list sources 2>/dev/null | sed -n "/$default_source/,/^$/p" | \
            grep -E "(Name|Description|State|Mute|Volume|Balance|Base)" | head -10 || \
            report "  Não foi possível obter detalhes"
        report "\`\`\`"

        # Volume
        local mute_state
        mute_state=$(pactl get-source-mute "$default_source" 2>/dev/null || echo "Mute: N/A")
        local vol_state
        vol_state=$(pactl get-source-volume "$default_source" 2>/dev/null || echo "Volume: N/A")
        report ""
        report "**Mute:** $mute_state"
        report "**Volume:** $vol_state"
    else
        report "${RED}Nenhum source padrão encontrado${NC}"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO 4: Latência
# ═══════════════════════════════════════════════════════════════════════════════

diagnose_latency() {
    report ""
    report "## ⏱️ 4. Análise de Latência"
    report ""

    if [ "$DRY_RUN" = true ]; then
        report "  ${YELLOW}[Dry-run] Análise de latência seria executada${NC}"
        return
    fi

    # Verificar configuração de fragment size / buffer
    report "### Configuração ALSA"
    report "\`\`\`"
    cat /proc/asound/card*/pcm*/sub*/hw_params 2>/dev/null | head -20 || \
        report "  Não foi possível ler configuração ALSA diretamente"
    report "\`\`\`"

    # Verificar PipeWire quantum (latência)
    report ""
    report "### Configuração PipeWire (quantum/tamanho do buffer)"
    if command -v pw-cli &>/dev/null; then
        report "\`\`\`"
        pw-cli info 2>/dev/null | grep -E "(quantum|latency|sample|rate)" | head -10 || \
            report "  quantum: default"
        report "\`\`\`"
    else
        report "  pw-cli não disponível"
    fi

    # Recomendações com base na latência
    report ""
    report "### Recomendações de Latência"
    report ""
    report "  | Uso | Buffer | Latência | Configuração |"
    report "  |-----|--------|----------|--------------|"
    report "  | 🎵 Música/Gravação | 256 frames | ~5.3ms | quantum = 256 |"
    report "  | 🎤 STT/Voz | 512 frames | ~10.7ms | quantum = 512 |"
    report "  | 🎬 Mídia geral | 1024 frames | ~21.3ms | quantum = 1024 |"
    report "  | 🤖 IA/Batch | 2048 frames | ~42.7ms | quantum = 2048 |"
    report ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO 5: Ferramentas
# ═══════════════════════════════════════════════════════════════════════════════

diagnose_tools() {
    report ""
    report "## 🧰 5. Ferramentas de Áudio Instaladas"
    report ""

    report "### Essenciais"
    check_cmd "pactl"
    check_cmd "pw-cli"
    check_cmd "pw-dump"
    check_cmd "aplay"
    check_cmd "arecord"
    check_cmd "ffmpeg"

    report ""
    report "### Úteis"
    check_cmd "sox"
    check_cmd "speaker-test"
    check_cmd "ffplay"
    check_cmd "pacat"
    check_cmd "parec"
    check_cmd "jackd"

    report ""
    report "### Python"
    check_cmd "python3"

    # Pacotes Python de áudio
    if command -v python3 &>/dev/null; then
        report ""
        report "### Pacotes Python para Áudio"
        report "\`\`\`"
        python3 -c "
import pkg_resources
pkgs = ['pyaudio', 'sounddevice', 'soundfile', 'torchaudio', 'webrtcvad',
        'speechbrain', 'whisper', 'faster-whisper', 'pyttsx3', 'edge-tts',
        'pydub', 'librosa', 'audioread', 'numpy']
for p in pkgs:
    try:
        v = pkg_resources.get_distribution(p).version
        print(f'  [✓] {p}=={v}')
    except:
        print(f'  [ ] {p} (não instalado)')
" 2>/dev/null || echo "  Não foi possível listar pacotes Python"
        report "\`\`\`"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO 6: Microfone Virtual
# ═══════════════════════════════════════════════════════════════════════════════

diagnose_virtual_mic() {
    report ""
    report "## 🎛️ 6. Microfone Virtual"
    report ""

    if pactl list sinks short 2>/dev/null | grep -qi "ia-lab-mic\|virtual\|null"; then
        report "**Status:** ✅ Configurado"
        report ""
        report "\`\`\`"
        pactl list sinks short 2>/dev/null | grep -iE "ia-lab-mic|virtual|null" || \
            report "  Nenhum sink virtual identificado pelo nome 'ia-lab-mic'"
        report "\`\`\`"

        local mic_sink
        mic_sink=$(pactl list sinks short 2>/dev/null | grep -i "ia-lab-mic" | awk '{print $2}' | head -1)
        if [ -n "$mic_sink" ]; then
            report ""
            report "**Sink virtual:** $mic_sink"
            report "**Source monitor:** ${mic_sink}.monitor"
            report ""
            report "  Para usar em apps, selecione o microfone:"
            report "  - **PipeWire:** ${mic_sink}.monitor"
            report "  - **ALSA:** sysdefault:CARD=${mic_sink}"
        fi
    else
        report "**Status:** ❌ Não configurado"
        report ""
        report "  Execute para criar:"
        report "  \`\`\`bash"
        report "  ./scripts/audio/setup_microfone_virtual.sh --apply"
        report "  \`\`\`"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO 7: Teste Rápido de Gravação
# ═══════════════════════════════════════════════════════════════════════════════

diagnose_quick_test() {
    if [ "$DRY_RUN" = true ] || [ "$QUICK" = true ]; then
        return 0
    fi

    report ""
    report "## 🧪 7. Teste Rápido de Gravação"
    report ""

    local test_file="/tmp/ia_diag_test_${TIMESTAMP}.wav"
    local default_source
    default_source=$(pactl get-default-source 2>/dev/null || echo "default")

    if command -v sox &>/dev/null; then
        log "Gravando 2s para teste..."
        if timeout 3 sox -t pulseaudio "$default_source" -n stats 2>&1 | \
            grep -E "(RMS|Peak)" > /tmp/ia_diag_level.txt 2>/dev/null; then
            report "**Microfone responded ao teste de nível:** ✅"
            report "\`\`\`"
            cat /tmp/ia_diag_level.txt
            report "\`\`\`"
            log "${GREEN}Microfone funcionando${NC}"
        else
            report "**Microfone não respondeu ao teste:** ⚠️"
            log "${YELLOW}Microfone pode estar mudo ou desconectado${NC}"
        fi
        rm -f /tmp/ia_diag_level.txt
    else
        report "  sox não disponível para teste rápido"
    fi
    rm -f "$test_file"
}

# ═══════════════════════════════════════════════════════════════════════════════
# RESUMO E RECOMENDAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════

generate_summary() {
    report ""
    report "---"
    report ""
    report "# 📋 Resumo e Recomendações"
    report ""

    # Contagem de problemas
    local issues=0
    local warnings=0

    report "## ✅ Status"
    report ""

    # 1. PipeWire
    if pactl info &>/dev/null; then
        report "  ✅ Servidor de áudio: OK"
    else
        report "  ❌ Servidor de áudio: PARADO"
        issues=$((issues + 1))
    fi

    # 2. Microfone virtual
    if pactl list sinks short 2>/dev/null | grep -qi "ia-lab-mic"; then
        report "  ✅ Microfone virtual: configurado"
    else
        report "  ⚠️ Microfone virtual: não configurado"
        warnings=$((warnings + 1))
    fi

    # 3. Microfone físico
    local mic_count
    mic_count=$(pactl list sources short 2>/dev/null | grep -v ".monitor" | wc -l)
    if [ "$mic_count" -gt 0 ]; then
        report "  ✅ ${mic_count} microfone(s) físico(s) detectado(s)"
    else
        report "  ⚠️ Nenhum microfone físico detectado"
        warnings=$((warnings + 1))
    fi

    # 4. Ferramentas essenciais
    local missing_tools=0
    for cmd in pactl ffmpeg arecord aplay; do
        command -v "$cmd" &>/dev/null || missing_tools=$((missing_tools + 1))
    done
    if [ "$missing_tools" -eq 0 ]; then
        report "  ✅ Ferramentas essenciais: completas"
    else
        report "  ⚠️ Faltam $missing_tools ferramenta(s) essencial(is)"
        warnings=$((warnings + 1))
    fi

    # 5. sox para medição
    if command -v sox &>/dev/null; then
        report "  ✅ sox disponível para medições"
    else
        report "  ⚠️ sox não instalado (recomendado para medições de nível)"
        warnings=$((warnings + 1))
    fi

    # Score
    report ""
    report "## 📊 Score de Saúde"
    report ""

    local total_checks=5
    local score=$(( ( (total_checks - issues) * 100 / total_checks ) ))
    local score_emoji=""

    if [ "$score" -ge 80 ]; then
        score_emoji="🟢"
    elif [ "$score" -ge 50 ]; then
        score_emoji="🟡"
    else
        score_emoji="🔴"
    fi

    report "  **${score_emoji} Score: ${score}%**"
    report "  - Problemas: ${issues}"
    report "  - Avisos: ${warnings}"

    # Recomendações
    report ""
    report "## 🎯 Recomendações"
    report ""

    if ! pactl info &>/dev/null; then
        report "  1. **Iniciar PipeWire:**"
        report "     \`\`\`bash"
        report "     systemctl --user start pipewire pipewire-pulse"
        report "     \`\`\`"
    fi

    if ! pactl list sinks short 2>/dev/null | grep -qi "ia-lab-mic"; then
        report "  1. **Criar microfone virtual para apps de IA:**"
        report "     \`\`\`bash"
        report "     ./scripts/audio/setup_microfone_virtual.sh --apply"
        report "     \`\`\`"
    fi

    if ! command -v sox &>/dev/null; then
        report "  1. **Instalar sox** para medições de nível e conversões:"
        report "     \`\`\`bash"
        report "     sudo apt install -y sox"
        report "     \`\`\`"
    fi

    if [ "$LATENCY_FOCUS" = true ]; then
        report "  1. **Otimizar latência para STT/IA:**"
        report "     Crie \`~/.config/pipewire/pipewire.conf.d/latency.conf\`:"
        report "     \`\`\`conf"
        report "     context.properties = {"
        report "         default.clock.quantum      = 512"
        report "         default.clock.min-quantum   = 256"
        report "         default.clock.max-quantum   = 2048"
        report "     }"
        report "     \`\`\`"
        report "     Depois reinicie: systemctl --user restart pipewire"
    fi

    report "---"
}

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  🔬 IA-Lab Diagnóstico de Áudio                       ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  $(date '+%d/%m/%Y %H:%M')                                          ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

log "Iniciando diagnóstico de áudio"
log "Modo: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICAR')"
log "Relatório: $REPORT_FILE"

# ── Cabeçalho do relatório ───────────────────────────────────────────────────
if [ "$DRY_RUN" = false ] && [ "$QUICK" = false ]; then
    report "# 🔬 IA-Lab Diagnóstico de Áudio"
    report ""
    report "**Data:** $(date '+%d/%m/%Y %H:%M')"
    report "**Sistema:** $(uname -a 2>/dev/null | awk '{print $2, $3}')"
    report "**Modo:** $( [ "$LATENCY_FOCUS" = true ] && echo 'Foco em Latência' || echo 'Completo')"
    report ""
    report "---"
fi

# ── Executar diagnósticos ─────────────────────────────────────────────────────
diagnose_kernel
diagnose_pipewire
diagnose_mics

diagnose_tools
diagnose_virtual_mic
diagnose_quick_test

if [ "$QUICK" = false ]; then
    # diagnose_latency é executada aqui (uma única vez)
    # O parâmetro --latency define o nível de detalhe, não se deve chamar novamente
    diagnose_latency
    generate_summary
fi

# ── Resumo final ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Diagnóstico concluído!${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
echo -e "  Modo:     $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICADO')"
echo -e "  Log:      $LOG_FILE"

if [ "$DRY_RUN" = false ] && [ "$QUICK" = false ]; then
    echo -e "  ${GREEN}Relatório:${NC}"
    echo -e "  $REPORT_FILE"
fi

echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo ""
