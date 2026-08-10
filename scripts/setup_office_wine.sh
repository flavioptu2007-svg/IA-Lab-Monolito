#!/usr/bin/env bash
# =============================================================================
# setup_office_wine.sh
# -----------------------------------------------------------------------------
# Prepara o Wine (na VM ou computador com Wine) para instalar o Microsoft 365
# (ou Office 2016/2019/2021) em um prefixo ISOLADO. Nada fora do prefixo e do
# Wine e alterado. Roda com o usuario comum (pede sudo apenas na etapa opcional
# de upgrade do Wine para o repo oficial WineHQ).
# -----------------------------------------------------------------------------
# Uso (na VM):
#   bash setup_office_wine.sh                            # prepara tudo, para antes do instalador
#   bash setup_office_wine.sh ~/Downloads/OfficeSetup.exe  # prepara e executa o instalador
#   bash setup_office_wine.sh --skip-wine-upgrade        # usa o wine do repositorio da distro
#
# Log completo:  ~/office_setup.log
# Prefixo:       ~/wineprefixes/M365  (WINEARCH=win64)
# =============================================================================

set -u

LOG="$HOME/office_setup.log"
WINEPREFIX_DIR="$HOME/wineprefixes/M365"
export WINEPREFIX="$WINEPREFIX_DIR"
export WINEARCH="win64"
# Evita dialogs do wineboot (mono/gecko) que travam em execucao automatica
export WINEDLLOVERRIDES="mscoree,mshtml="
export WINEDEBUG="-all"

SKIP_WINE_UPGRADE=0
INSTALLER=""

for arg in "$@"; do
  case "$arg" in
    --skip-wine-upgrade) SKIP_WINE_UPGRADE=1 ;;
    -h|--help) sed -n '1,25p' "$0"; exit 0 ;;
    *) INSTALLER="$arg" ;;
  esac
done

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
step() { echo; echo "### >>> $*" | tee -a "$LOG"; }

echo "### Configuracao do Wine para Microsoft 365 (Office no Linux)" | tee "$LOG"
log "Log: $LOG"
log "Prefixo: $WINEPREFIX_DIR (WINEARCH=$WINEARCH)"

# --- 0. Pre-requisitos -------------------------------------------------------
step "Verificando wine / winetricks"
if ! command -v wine >/dev/null 2>&1; then
  echo "ERRO: wine nao encontrado. Instale primeiro (na VM):" | tee -a "$LOG"
  echo "  sudo apt update && sudo apt install -y wine winetricks cabextract" | tee -a "$LOG"
  exit 1
fi
log "wine: $(wine --version 2>/dev/null || echo '?')"
log "winetricks: $(winetricks --version 2>/dev/null || echo '?')"

# --- 1. WineHQ Staging (opcional, repo oficial WineHQ) -----------------------
if [ "$SKIP_WINE_UPGRADE" -eq 0 ]; then
  step "Upgrade para WineHQ Staging (repo oficial WineHQ)"
  CODENAME="$(lsb_release -sc 2>/dev/null || echo unknown)"
  if [ -z "$CODENAME" ] || [ "$CODENAME" = "unknown" ]; then
    log "AVISO: codename do Ubuntu nao detectado — pulando upgrade."
    log "       (rode com --skip-wine-upgrade para nao tentar de novo)"
  else
    log "Codename detectado: $CODENAME"
    sudo dpkg --add-architecture i386
    sudo mkdir -pm755 /etc/apt/keyrings
    sudo wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key
    sudo wget -NP /etc/apt/sources.list.d/ "https://dl.winehq.org/wine-builds/ubuntu/dists/${CODENAME}/winehq-${CODENAME}.sources"
    sudo apt update
    sudo apt install --install-recommends -y winehq-staging
    log "wine apos upgrade: $(wine --version 2>/dev/null)"
  fi
else
  log "Upgrade do Wine pulado (--skip-wine-upgrade)"
fi

# --- 2. Prefixo isolado 64-bit -----------------------------------------------
step "Criando prefixo isolado: $WINEPREFIX_DIR"
if [ -f "$WINEPREFIX_DIR/system.reg" ]; then
  log "Prefixo ja existe — reutilizando."
else
  wineboot -u
  log "Prefixo inicializado (wineboot -u)."
fi
# Windows 10 como versao padrao (evita ter que mexer na GUI do winecfg)
if winecfg -v win10 >/dev/null 2>&1; then
  log "Windows versao: win10"
else
  log "aviso: winecfg -v win10 falhou (defina 'Windows 10' na GUI se necessario)"
fi

# --- 3. Dependencias winetricks (minimas para M365/Office) -------------------
step "Instalando dependencias winetricks (pode demorar — baixa da Microsoft)"
DEPS="dotnet48 corefonts msxml6 vcrun2019 d3dcompiler_47 riched20"
for dep in $DEPS; do
  if winetricks -q "$dep" >>"$LOG" 2>&1; then
    log "OK: $dep"
  else
    log "Falha em $dep — tentando com --force"
    if winetricks -q --force "$dep" >>"$LOG" 2>&1; then
      log "OK (com --force): $dep"
    else
      log "AVISO: $dep falhou (pode nao ser necessario para a sua versao)"
    fi
  fi
done

# --- 4. Instalador ------------------------------------------------------------
if [ -n "$INSTALLER" ]; then
  if [ ! -f "$INSTALLER" ]; then
    echo "ERRO: instalador nao encontrado: $INSTALLER" | tee -a "$LOG"
    exit 1
  fi
  step "Executando instalador oficial: $INSTALLER"
  if [ -z "${DISPLAY:-}" ]; then
    log "AVISO: sem DISPLAY (headless) — a tela do instalador NAO vai aparecer."
    log "       Rode de um terminal com interface grafica (ou com xvfb + VNC)."
  fi
  log "Se a tela abrir, faca o login com sua conta Microsoft (licenca legitima)."
  wine "$INSTALLER" 2>&1 | tee -a "$LOG"
else
  step "Instalador nao informado — ambiente pronto para receber o OfficeSetup.exe"
  echo
  echo "1) Baixe o instalador oficial em:  https://www.office.com  (Instalar Office)"
  echo "2) Copie para ~/Downloads na VM"
  echo "3) Execute:"
  echo "     export WINEPREFIX=\"$WINEPREFIX_DIR\""
  echo "     wine ~/Downloads/OfficeSetup.exe"
  echo
fi

# --- 5. Resumo ---------------------------------------------------------------
step "Resumo final"
log "Prefixo:  $WINEPREFIX_DIR"
log "Wine:     $(wine --version 2>/dev/null)"
log "Log:      $LOG"
echo
echo "Para abrir o Word depois da instalacao:" | tee -a "$LOG"
echo "  export WINEPREFIX=\"$WINEPREFIX_DIR\"" | tee -a "$LOG"
echo "  wine \"\$WINEPREFIX/drive_c/Program Files/Microsoft Office/root/Office16/WINWORD.EXE\"" | tee -a "$LOG"
echo
echo "Regras de seguranca: nada de cracks/ativadores; ativacao somente por licenca legitima."
