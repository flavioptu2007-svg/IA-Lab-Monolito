#!/usr/bin/env bash
# =============================================================================
# install_office2016_msi.sh
# -----------------------------------------------------------------------------
# Instala o Microsoft Office 2016 (versao MSI — NÃO Click-to-Run) no prefixo
# Wine isolado ~/.wine-office, com log completo em ~/office2016_install.log.
# Aceita como argumento o caminho de um .exe (setup.exe da midia MSI) ou de
# um .iso (extraido automaticamente com 7z, se disponivel).
#
# Uso:
#   bash install_office2016_msi.sh ~/Downloads/Office2016ProPlus.iso
#   bash install_office2016_msi.sh ~/Downloads/setup.exe
#   bash install_office2016_msi.sh --help
#
# Pre-requisitos: wine instalado; 7z apenas quando o argumento for um .iso;
#                 DISPLAY grafico para a interface do instalador.
# Prefixo:       ~/.wine-office  (override com: WINEPREFIX=/caminho bash script.sh ...)
# Log:           ~/office2016_install.log
#
# Seguranca: ativacao apenas por licenca legitima — nada de cracks/ativadores.
# =============================================================================

set -u

# -----------------------------------------------------------------------------
# Configuracao
# -----------------------------------------------------------------------------
LOG="$HOME/office2016_install.log"
WINEPREFIX_DIR="${WINEPREFIX:-$HOME/.wine-office}"
export WINEPREFIX="$WINEPREFIX_DIR"
export WINEARCH="${WINEARCH:-win64}"
# Evita dialogs do wineboot (mono/gecko) e ruido de debug
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-mscoree,mshtml=}"
export WINEDEBUG="${WINEDEBUG:--all}"

EXTRACT_DIR="$HOME/.cache/office2016_media"   # destino da extracao de .iso

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
step() { echo; echo "### >>> $*" | tee -a "$LOG"; }

die()  { echo "ERRO: $*" | tee -a "$LOG"; exit 1; }

usage() {
    sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

# -----------------------------------------------------------------------------
# Argumentos
# -----------------------------------------------------------------------------
MEDIA=""
for arg in "$@"; do
    case "$arg" in
        -h|--help) usage ;;
        *) [ -z "$MEDIA" ] && MEDIA="$arg" ;;
    esac
done

echo "### Instalacao do Microsoft Office 2016 (MSI) no Wine" | tee "$LOG"
log "Log:     $LOG"
log "Prefixo: $WINEPREFIX_DIR (WINEARCH=$WINEARCH)"

# -----------------------------------------------------------------------------
# 1. Pre-requisitos
# -----------------------------------------------------------------------------
step "Verificando pre-requisitos"
command -v wine >/dev/null 2>&1 || die "wine nao encontrado. Instale: sudo apt install -y wine winetricks"
log "wine: $(wine --version 2>/dev/null || echo '?')"

[ -n "$MEDIA" ] || die "Nenhuma midia informada. Uso: bash $(basename "$0") /caminho/setup.exe (ou .iso)"

[ -f "$MEDIA" ] || die "Midia nao encontrada: $MEDIA"

# -----------------------------------------------------------------------------
# 2. Extrair .iso (se for o caso)
# -----------------------------------------------------------------------------
SETUP="$MEDIA"
case "$MEDIA" in
    *.iso|*.ISO)
        step "Extraindo .iso com 7z para: $EXTRACT_DIR"
        command -v 7z >/dev/null 2>&1 || die "7z nao encontrado (necessario p/ .iso). Instale: sudo apt install -y p7zip-full"
        # Limpa o destino antes para nunca reaproveitar setup.exe de extracao anterior
        rm -rf "$EXTRACT_DIR"
        mkdir -p "$EXTRACT_DIR"
        if ! 7z x -y -o"$EXTRACT_DIR" "$MEDIA" >>"$LOG" 2>&1; then
            die "Falha ao extrair o .iso (ver $LOG)."
        fi
        log "Extracao concluida."

        # Localizar o setup.exe da midia (raiz da imagem)
        SETUP="$(find "$EXTRACT_DIR" -maxdepth 2 -iname 'setup.exe' 2>/dev/null | head -n 1)"
        [ -n "$SETUP" ] || die "setup.exe nao encontrado na raiz da midia extraida."
        log "setup.exe localizado: $SETUP"
        ;;
esac

# -----------------------------------------------------------------------------
# 3. Sanidade da midia (aviso, nao bloqueia)
# -----------------------------------------------------------------------------
step "Analisando a midia"
MEDIA_DIR="$(dirname "$SETUP")"
if [ -f "$MEDIA_DIR/configuration.xml" ] || ls "$MEDIA_DIR"/stream.*.dat >/dev/null 2>&1; then
    log "AVISO: a midia contem arquivos tipicos do Click-to-Run/ODT (configuration.xml ou stream.*.dat)."
    log "       O Office 2016 MSI exige a midia MSI (pasta ProPlus.WW + setup.exe), nao o ODT."
    log "       A instalacao pode falhar — se isso acontecer, use a ISO oficial MSI."
else
    log "Midia parece ser MSI (sem marcadores de Click-to-Run na raiz)."
fi
ls "$MEDIA_DIR" | head -n 20 | sed 's/^/  media: /' >>"$LOG"

# -----------------------------------------------------------------------------
# 4. Prefixo Wine
# -----------------------------------------------------------------------------
step "Verificando prefixo Wine"
if [ -f "$WINEPREFIX_DIR/system.reg" ]; then
    log "Prefixo ja existe — reutilizando ($WINEPREFIX_DIR)."
else
    log "Prefixo nao existe — criando (wineboot -u)..."
    wineboot -u || die "Falha ao inicializar o prefixo."
fi

# -----------------------------------------------------------------------------
# 5. Instalacao
# -----------------------------------------------------------------------------
step "Executando o instalador MSI"
if [ -z "${DISPLAY:-}" ]; then
    log "AVISO: sem DISPLAY (headless) — a interface do instalador NAO vai aparecer."
    log "       Rode de um terminal com interface grafica (ou com xvfb + VNC)."
fi

log "Comando: wine \"$SETUP\""
wine "$SETUP" 2>&1 | tee -a "$LOG"
RC="${PIPESTATUS[0]}"
if [ "$RC" -eq 0 ]; then
    log "Instalador encerrou com sucesso (codigo $RC)."
else
    log "Instalador encerrou com erro (codigo $RC) — veja os detalhes no log."
fi

# -----------------------------------------------------------------------------
# 6. Verificacao pos-instalacao
# -----------------------------------------------------------------------------
step "Verificando instalacao"
OFFICE16="$WINEPREFIX_DIR/drive_c/Program Files (x86)/Microsoft Office/Office16"
if [ -x "$OFFICE16/WINWORD.EXE" ] && [ -x "$OFFICE16/EXCEL.EXE" ]; then
    log "OK: WINWORD.EXE e EXCEL.EXE encontrados em:"
    log "    $OFFICE16"
    INSTALLED=1
else
    log "AVISO: binarios do Office ainda nao detectados em:"
    log "    $OFFICE16"
    log "Se a instalacao falhou, confira o final do log: tail -n 40 $LOG"
    INSTALLED=0
fi

# -----------------------------------------------------------------------------
# 7. Resumo
# -----------------------------------------------------------------------------
step "Resumo final"
log "Prefixo: $WINEPREFIX_DIR"
log "Log:     $LOG"
echo
if [ "$INSTALLED" -eq 1 ]; then
    echo "Office 2016 instalado. Para abrir os aplicativos:" | tee -a "$LOG"
    echo "  export WINEPREFIX=\"$WINEPREFIX_DIR\"" | tee -a "$LOG"
    echo "  wine \"\$WINEPREFIX/drive_c/Program Files (x86)/Microsoft Office/Office16/WINWORD.EXE\"" | tee -a "$LOG"
    echo "  wine \"\$WINEPREFIX/drive_c/Program Files (x86)/Microsoft Office/Office16/EXCEL.EXE\"" | tee -a "$LOG"
    echo "  wine \"\$WINEPREFIX/drive_c/Program Files (x86)/Microsoft Office/Office16/POWERPNT.EXE\"" | tee -a "$LOG"
else
    echo "Instalacao nao confirmada. Analise o log:" | tee -a "$LOG"
    echo "  tail -n 60 $LOG" | tee -a "$LOG"
fi
echo | tee -a "$LOG"
echo "Seguranca: ativacao apenas por licenca legitima (nada de cracks/ativadores)." | tee -a "$LOG"
