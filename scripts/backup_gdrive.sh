#!/usr/bin/env bash
# ============================================================================
#  ☁️  backup_gdrive.sh — Backup dos projetos-fonte para o Google Drive
#
#  Sincroniza os projetos-fonte (OpenManus, portal_projetos, leituraia,
#  next-app, Projetos) para o remote rclone `gdrive:IA-Lab-Projetos`,
#  excluindo caches, venvs, node_modules, .git e repositórios de terceiros
#  (ai-skills-repos) que não são código-fonte próprio.
#
#  Uso:
#    ./backup_gdrive.sh            # Dry-run (mostra o que seria enviado)
#    ./backup_gdrive.sh --apply    # Executa o backup de verdade
#    ./backup_gdrive.sh --status   # Mostra tamanhos no Drive
#
#  Agendamento sugerido (semanal):
#    0 3 * * 0 /home/flavio/scripts/backup_gdrive.sh --apply >> /home/flavio/.local/log/backup_gdrive/cron.log 2>&1
# ============================================================================
set -uo pipefail

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
info() { echo -e "${BLUE}  ℹ️  $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
erro() { echo -e "${RED}  ❌ $1${NC}"; }

# ── Configurações ────────────────────────────────────────────────────────────
REMOTE="gdrive:IA-Lab-Projetos"
HOME_DIR="${HOME:-/home/flavio}"

# Projetos a sincronizar (nome_local -> nome_remoto)
PROJETOS=(
  "OpenManus"
  "portal_projetos"
  "leituraia"
  "next-app"
  "Projetos"
)

LOG_DIR="$HOME_DIR/.local/log/backup_gdrive"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="$LOG_DIR/backup_${TIMESTAMP}.log"
EXCL_FILE="/tmp/rclone-backup-excludes.txt"

# ── Flags ────────────────────────────────────────────────────────────────────
APPLY=false
STATUS=false

for arg in "$@"; do
  case "$arg" in
    --apply)  APPLY=true ;;
    --status) STATUS=true ;;
    --help|-h)
      echo "Uso: $0 [--apply] [--status]"
      echo "  --apply    Executa o backup (padrão: dry-run)"
      echo "  --status   Mostra os tamanhos atuais no Google Drive"
      exit 0 ;;
    *) erro "Argumento desconhecido: $arg"; exit 1 ;;
  esac
done

mkdir -p "$LOG_DIR"

# ── Arquivo de exclusões (criado localmente, com caches) ─────────────────────
cat > "$EXCL_FILE" <<'EOF'
node_modules/**
.venv/**
.git/**
__pycache__/**
.pytest_cache/**
.next/**
.servidor.log
.servidor.pid
ai-skills-repos/**
**/.tmp/**
EOF

# ── Modo status ──────────────────────────────────────────────────────────────
if [ "$STATUS" = true ]; then
  echo "══════════════════════════════════════════════════"
  echo "   ☁️  STATUS DO BACKUP NO GOOGLE DRIVE"
  echo "══════════════════════════════════════════════════"
  for p in "${PROJETOS[@]}"; do
    if rclone lsd "$REMOTE/$p" >/dev/null 2>&1; then
      sz=$(timeout 90 rclone size "$REMOTE/$p" 2>/dev/null | grep 'Total size' | sed 's/.*: //')
      [ -z "$sz" ] && sz="0"
      info "$p → ${sz}"
    else
      warn "$p → (ainda não existe no Drive)"
    fi
  done
  timeout 30 rclone about "$REMOTE" 2>/dev/null | grep -E 'Total|Used|Free' | head -3
  exit 0
fi

# ── Verificação de pré-requisitos ────────────────────────────────────────────
if ! command -v rclone >/dev/null 2>&1; then
  erro "rclone não encontrado. Instale com: sudo apt install rclone"
  exit 1
fi
if ! rclone listremotes 2>/dev/null | grep -q '^gdrive:'; then
  erro "Remote 'gdrive:' não configurado. Rode: rclone config"
  exit 1
fi

echo "══════════════════════════════════════════════════"
echo "   ☁️  BACKUP PROJETOS-FONTE → GOOGLE DRIVE"
echo "   $(date '+%d/%m/%Y %H:%M:%S')"
echo "   Destino: $REMOTE"
echo "   Modo:    $([ "$APPLY" = true ] && echo 'EXECUTAR' || echo 'DRY-RUN')"
echo "══════════════════════════════════════════════════"

if [ "$APPLY" = false ]; then
  echo
  info "Dry-run — apenas mostrando o que seria enviado:"
  echo
fi

# ── Execução ─────────────────────────────────────────────────────────────────
failed=0
for p in "${PROJETOS[@]}"; do
  local_dir="$HOME_DIR/$p"
  remote_dir="$REMOTE/$p"

  if [ ! -d "$local_dir" ]; then
    warn "Pasta local não encontrada: $local_dir — pulando."
    continue
  fi

  echo
  echo "  ── $p ──────────────────────────────────────────"

  if [ "$APPLY" = false ]; then
    timeout 120 rclone copy "$local_dir" "$remote_dir" \
      --exclude-from "$EXCL_FILE" --dry-run --stats 10s 2>&1 | tail -4
    continue
  fi

  # Executa em background com setsid (sobrevive ao fechamento do terminal)
  setsid nohup rclone copy "$local_dir" "$remote_dir" \
    --exclude-from "$EXCL_FILE" \
    --stats 60s --stats-one-line --log-level ERROR \
    > "$LOG_FILE" 2>&1 < /dev/null &
  bg_pid=$!

  # Aguarda o rclone deste projeto terminar
  while kill -0 "$bg_pid" 2>/dev/null; do
    sleep 10
  done

  if grep -qiE 'ERROR|Fatal error' "$LOG_FILE" 2>/dev/null; then
    erro "Falha em $p — veja $LOG_FILE"
    failed=$((failed + 1))
  else
    transferred=$(grep -E 'Transferred:' "$LOG_FILE" 2>/dev/null | tail -1)
    ok "$p concluído. $transferred"
  fi
done

echo
echo "══════════════════════════════════════════════════"
if [ "$APPLY" = false ]; then
  info "Dry-run concluído. Rode com --apply para executar."
else
  if [ "$failed" -eq 0 ]; then
    ok "BACKUP CONCLUÍDO COM SUCESSO — log: $LOG_FILE"
  else
    erro "BACKUP CONCLUÍDO COM $failed FALHA(S) — log: $LOG_FILE"
    exit 1
  fi
fi
echo "══════════════════════════════════════════════════"
