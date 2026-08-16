#!/bin/bash
# =============================================================================
# backup_audio_config.sh - Backup da configuração de áudio do sistema
# =============================================================================
# Salva configurações do PipeWire/PulseAudio, lista dispositivos e módulos.
# Mantém os últimos N backups e limpa automagicamente os antigos.
#
# Uso:
#   ./backup_audio_config.sh                # Dry-run (mostra o que será salvo)
#   ./backup_audio_config.sh --apply        # Executa o backup real
#   ./backup_audio_config.sh --restore <id> # Restaura um backup (lista IDs)
#   ./backup_audio_config.sh --list         # Lista backups existentes
#   ./backup_audio_config.sh --clean        # Remove backups antigos (dry-run)
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
BACKUP_DIR="$HOME/.local/backups/audio"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/audio_config_${TIMESTAMP}.tar.gz"
LOG_DIR="$HOME/.local/log/audio"
LOG_FILE="$LOG_DIR/backup_audio_${TIMESTAMP}.log"
MAX_BACKUPS=10     # Mantém os últimos 10 backups
MAX_BACKUP_DAYS=30 # Remove backups com mais de 30 dias

# Flags
DRY_RUN=true
ACTION="backup"   # backup, restore, list, clean

# ── Parse de argumentos ──────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --apply)
            DRY_RUN=false
            shift
            ;;
        --restore)
            ACTION="restore"
            shift
            ;;
        --list)
            ACTION="list"
            shift
            ;;
        --clean)
            ACTION="clean"
            shift
            ;;
        --help|-h)
            echo "Uso: $0 [--apply] [--restore] [--list] [--clean]"
            echo ""
            echo "  (sem flags)  Dry-run: mostra o que será salvo"
            echo "  --apply      Executa o backup"
            echo "  --restore    Modo interativo: lista backups para restaurar"
            echo "  --list       Lista backups existentes"
            echo "  --clean      Remove backups antigos (dry-run primeiro)"
            exit 0
            ;;
    esac
done

# ── Garantir diretórios ──────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR" "$LOG_DIR"

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

# ── Listar backups ────────────────────────────────────────────────────────────

list_backups() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  BACKUPS DE ÁUDIO DISPONÍVEIS${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    local backups
    backups=$(find "$BACKUP_DIR" -name 'audio_config_*.tar.gz' 2>/dev/null | sort -r)

    if [ -z "$backups" ]; then
        echo ""
        echo -e "  ${YELLOW}Nenhum backup encontrado em:${NC}"
        echo -e "  $BACKUP_DIR"
        return 1
    fi

    local count=0
    echo ""
    printf "  ${CYAN}%-4s %-25s %-12s %s${NC}\n" "ID" "Data" "Tamanho" "Conteúdo"
    echo "  $(printf '%0.s-' {0..70})"

    echo "$backups" | while read -r file; do
        count=$((count + 1))
        local basename filename size
        basename=$(basename "$file" .tar.gz)
        filename=$(echo "$basename" | sed 's/audio_config_//' | sed 's/_/ /')
        size=$(du -h "$file" 2>/dev/null | awk '{print $1}')

        # Estimar conteúdo
        local content_info
        content_info=$(tar -tzf "$file" 2>/dev/null | head -5 | tr '\n' ' ' | cut -c1-40)

        printf "  %-4s %-25s %-12s %s\n" "$count" "$filename" "$size" "$content_info..."
    done

    echo ""
    echo -e "  ${GREEN}Total: $(echo "$backups" | wc -l) backup(s)${NC}"
    echo -e "  ${CYAN}Diretório:${NC} $BACKUP_DIR"
}

# ── Ação: Backup ─────────────────────────────────────────────────────────────

action_backup() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  💾 IA-Lab Backup de Configuração de Áudio            ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
    log "Iniciando backup de áudio..."
    log "Modo: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICAR')"

    # Verificar dependências
    if ! command -v pactl &>/dev/null; then
        log "${RED}ERRO: pactl não encontrado. PipeWire/PulseAudio necessário.${NC}"
        return 1
    fi

    # ── Diretório temporário para os dados ─────────────────────────────────
    local temp_dir
    temp_dir=$(mktemp -d /tmp/ia_audio_backup_XXXXXX)
    local data_dir="$temp_dir/audio_config"
    mkdir -p "$data_dir"

    log "Diretório temporário: $temp_dir"

    # ── 1. Informações gerais do PulseAudio/PipeWire ───────────────────────
    echo ""
    echo -e "${CYAN}▸ 1. Coletando informações do PipeWire/PulseAudio${NC}"
    run_cmd "pactl info > \"$data_dir/01_pactl_info.txt\" 2>&1" \
        "Salvando info do servidor de áudio"

    # ── 2. Lista de módulos carregados ─────────────────────────────────────
    echo ""
    echo -e "${CYAN}▸ 2. Lista de módulos carregados${NC}"
    run_cmd "pactl list modules short > \"$data_dir/02_modulos.txt\" 2>&1" \
        "Salvando módulos carregados"
    run_cmd "pactl list modules > \"$data_dir/02_modulos_detalhado.txt\" 2>&1" \
        "Salvando detalhes dos módulos"

    # ── 3. Dispositivos de saída (sinks) ───────────────────────────────────
    echo ""
    echo -e "${CYAN}▸ 3. Dispositivos de saída${NC}"
    run_cmd "pactl list sinks short > \"$data_dir/03_sinks_resumo.txt\" 2>&1" \
        "Salvando resumo dos sinks"
    run_cmd "pactl list sinks > \"$data_dir/03_sinks_detalhado.txt\" 2>&1" \
        "Salvando detalhes dos sinks"

    # ── 4. Dispositivos de entrada (sources) ───────────────────────────────
    echo ""
    echo -e "${CYAN}▸ 4. Dispositivos de entrada${NC}"
    run_cmd "pactl list sources short > \"$data_dir/04_sources_resumo.txt\" 2>&1" \
        "Salvando resumo das fontes"
    run_cmd "pactl list sources > \"$data_dir/04_sources_detalhado.txt\" 2>&1" \
        "Salvando detalhes das fontes"

    # ── 5. Clientes conectados ─────────────────────────────────────────────
    echo ""
    echo -e "${CYAN}▸ 5. Clientes conectados${NC}"
    run_cmd "pactl list clients short > \"$data_dir/05_clientes.txt\" 2>&1" \
        "Salvando clientes de áudio"

    # ── 6. Configuração do PipeWire ────────────────────────────────────────
    echo ""
    echo -e "${CYAN}▸ 6. Configuração do PipeWire${NC}"
    if command -v pw-dump &>/dev/null; then
        run_cmd "pw-dump > \"$data_dir/06_pw_dump.json\" 2>&1" \
            "Salvando dump completo do PipeWire (JSON)"
    fi
    if command -v pw-cli &>/dev/null; then
        run_cmd "pw-cli list-objects > \"$data_dir/06_pw_objects.txt\" 2>&1" \
            "Salvando objetos do PipeWire"
    fi

    # ── 7. Volumes padrão ──────────────────────────────────────────────────
    echo ""
    echo -e "${CYAN}▸ 7. Volumes e configurações padrão${NC}"
    {
        echo "=== Sink Padrão ==="
        pactl get-default-sink 2>/dev/null || echo "N/A"
        echo ""
        echo "=== Source Padrão ==="
        pactl get-default-source 2>/dev/null || echo "N/A"
        echo ""
        echo "=== Volume do Sink Padrão ==="
        pactl get-sink-volume "$(pactl get-default-sink 2>/dev/null)" 2>/dev/null || echo "N/A"
        echo ""
        echo "=== Mute do Sink Padrão ==="
        pactl get-sink-mute "$(pactl get-default-sink 2>/dev/null)" 2>/dev/null || echo "N/A"
    } > "$data_dir/07_volumes_padrao.txt" 2>&1
    log "${GREEN}Volumes salvos${NC}"

    # ── 8. Estado geral do sistema de áudio ────────────────────────────────
    echo ""
    echo -e "${CYAN}▸ 8. Estado geral do sistema${NC}"
    {
        echo "=== Data do Backup ==="
        date
        echo ""
        echo "=== Kernel ==="
        uname -a
        echo ""
        echo "=== Módulos de Áudio do Kernel ==="
        lsmod | grep -E "^snd" 2>/dev/null || echo "N/A"
        echo ""
        echo "=== ALSA devices ==="
        aplay -l 2>/dev/null || echo "N/A"
        echo ""
        echo "=== ALSA capture devices ==="
        arecord -l 2>/dev/null || echo "N/A"
        echo ""
        echo "=== PipeWire versão ==="
        pw-cli info 2>/dev/null | head -3 || pactl info 2>/dev/null | head -3 || echo "N/A"
        echo ""
        echo "=== Variáveis de ambiente AUDIO ==="
        env | grep -iE "(PULSE|PIPEWIRE|ALSA|JACK|AUDIO)" 2>/dev/null || echo "Nenhuma"
    } > "$data_dir/08_estado_sistema.txt" 2>&1
    log "${GREEN}Estado do sistema salvo${NC}"

    # ── 9. Arquivos de configuração ─────────────────────────────────────────
    echo ""
    echo -e "${CYAN}▸ 9. Arquivos de configuração${NC}"
    local config_dir="$data_dir/config_files"
    mkdir -p "$config_dir"

    local config_files=(
        "/etc/pipewire/pipewire.conf"
        "/etc/pipewire/pipewire-pulse.conf"
        "/etc/pipewire/client.conf"
        "/etc/pipewire/client-rt.conf"
        "$HOME/.config/pipewire/pipewire.conf"
        "$HOME/.config/pipewire/pipewire-pulse.conf"
        "$HOME/.config/pulse/default.pa"
        "$HOME/.config/pulse/client.conf"
    )

    for cfg in "${config_files[@]}"; do
        if [ -f "$cfg" ]; then
            local safe_name
            safe_name=$(echo "$cfg" | tr '/' '_')
            cp "$cfg" "$config_dir/$safe_name" 2>/dev/null && \
                log "${GREEN}  Copiado: $cfg${NC}" || \
                log "${YELLOW}  Falha ao copiar: $cfg${NC}"
        fi
    done

    # ── 10. Empacotar ──────────────────────────────────────────────────────
    echo ""
    echo -e "${CYAN}▸ 10. Compactando backup${NC}"

    run_cmd "cd \"$temp_dir\" && tar -czf \"$BACKUP_FILE\" audio_config/ 2>&1" \
        "Compactando backup em: $BACKUP_FILE"

    # Verificar integridade
    if [ "$DRY_RUN" = false ] && [ -f "$BACKUP_FILE" ]; then
        run_cmd "tar -tzf \"$BACKUP_FILE\" > /dev/null 2>&1 && echo 'Backup íntegro' || echo 'BACKUP CORROMPIDO'" \
            "Verificando integridade do backup"

        local backup_size
        backup_size=$(du -h "$BACKUP_FILE" | awk '{print $1}')
        log "${GREEN}✓ Backup concluído: $BACKUP_FILE ($backup_size)${NC}"
    fi

    # ── 11. Limpeza temporários ────────────────────────────────────────────
    run_cmd "rm -rf \"$temp_dir\"" "Removendo diretório temporário"

    echo ""
    echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
    echo -e "  ${GREEN}Backup salvo em:${NC}"
    echo -e "  $BACKUP_FILE"
}

# ── Ação: Restaurar ───────────────────────────────────────────────────────────

action_restore() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  RESTAURAR BACKUP DE ÁUDIO${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    list_backups

    local backups
    backups=$(find "$BACKUP_DIR" -name 'audio_config_*.tar.gz' 2>/dev/null | sort -r)

    if [ -z "$backups" ]; then
        return 1
    fi

    echo ""
    echo -e "  ${YELLOW}Para restaurar, extraia manualmente:${NC}"
    echo ""
    echo -e "  mkdir -p ~/restauracao_audio"
    echo -e "  tar -xzf <backup.tar.gz> -C ~/restauracao_audio"
    echo -e "  ls ~/restauracao_audio/audio_config/"
    echo ""

    if [ "$DRY_RUN" = false ]; then
        echo -e "  ${RED}⚠ ATENÇÃO: Restaurar substituirá configurações atuais.${NC}"
        echo -e "  ${YELLOW}A restauração automática não está implementada por segurança.${NC}"
        echo -e "  ${YELLOW}Use o comando manual acima para inspecionar e restaurar.${NC}"
    fi
}

# ── Ação: Limpar ─────────────────────────────────────────────────────────────

action_clean() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  LIMPEZA DE BACKUPS ANTIGOS${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

    local all_backups
    all_backups=$(find "$BACKUP_DIR" -name 'audio_config_*.tar.gz' 2>/dev/null | sort -r)
    local total
    total=$(echo "$all_backups" | wc -l)

    echo ""
    echo -e "  ${CYAN}Total de backups:${NC} $total"
    echo -e "  ${CYAN}Manter últimos:${NC} $MAX_BACKUPS"
    echo -e "  ${CYAN}Remover com > ${NC} ${MAX_BACKUP_DAYS} dias"

    # Remover por quantidade (mantém últimos MAX_BACKUPS)
    local to_remove
    to_remove=$(echo "$all_backups" | tail -n +$((MAX_BACKUPS + 1)))

    if [ -n "$to_remove" ]; then
        echo ""
        echo -e "  ${YELLOW}Backups a remover (quantidade):${NC}"
        echo "$to_remove" | while read -r f; do
            echo -e "    ${RED}🗑${NC} $(basename "$f") ($(du -h "$f" | awk '{print $1}'))"
        done

        if [ "$DRY_RUN" = false ]; then
            echo ""
            echo -e "  ${RED}Confirma remoção destes backups? (s/N):${NC} "
            read -r confirm
            if [[ "$confirm" =~ ^[Ss]$ ]]; then
                echo "$to_remove" | while read -r f; do
                    rm -f "$f"
                    log "${GREEN}Removido: $(basename "$f")${NC}"
                done
            else
                log "${YELLOW}Limpeza por quantidade cancelada${NC}"
            fi
        fi
    else
        log "${GREEN}Nenhum backup para remover por quantidade${NC}"
    fi

    # Remover por idade
    echo ""
    echo -e "${CYAN}▸ Verificando backups por idade (> ${MAX_BACKUP_DAYS} dias)${NC}"
    local old_backups
    old_backups=$(find "$BACKUP_DIR" -name 'audio_config_*.tar.gz' -mtime +$MAX_BACKUP_DAYS 2>/dev/null)

    if [ -n "$old_backups" ]; then
        echo ""
        echo -e "  ${YELLOW}Backups antigos (> ${MAX_BACKUP_DAYS} dias):${NC}"
        echo "$old_backups" | while read -r f; do
            local age_days
            age_days=$(( ( $(date +%s) - $(stat -c %Y "$f") ) / 86400 ))
            echo -e "    ${RED}🗑${NC} $(basename "$f") (${age_days} dias, $(du -h "$f" | awk '{print $1}'))"
        done

        if [ "$DRY_RUN" = false ]; then
            echo ""
            echo -e "  ${RED}Confirma remoção destes backups antigos? (s/N):${NC} "
            read -r confirm
            if [[ "$confirm" =~ ^[Ss]$ ]]; then
                echo "$old_backups" | while read -r f; do
                    rm -f "$f"
                    log "${GREEN}Removido backup antigo: $(basename "$f")${NC}"
                done
            else
                log "${YELLOW}Limpeza por idade cancelada${NC}"
            fi
        fi
    else
        log "${GREEN}Nenhum backup antigo para remover${NC}"
    fi

    # Espaço recuperado
    local total_size
    total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | awk '{print $1}')
    echo ""
    echo -e "  ${CYAN}Espaço atual em backups:${NC} $total_size"
}

# ── Execução principal ────────────────────────────────────────────────────────

case "$ACTION" in
    backup)
        action_backup
        ;;
    list)
        list_backups
        ;;
    restore)
        action_restore
        ;;
    clean)
        action_clean
        ;;
esac

# ── Resumo ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Operação concluída!${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
echo -e "  Ação:     ${ACTION}"
echo -e "  Modo:     $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'APLICADO')"
echo -e "  Log:      $LOG_FILE"
echo -e "  Backup:   $BACKUP_DIR"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo ""
