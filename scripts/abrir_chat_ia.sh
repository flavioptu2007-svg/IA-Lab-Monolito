#!/usr/bin/env bash
# Atalho de desktop: abre o chat_local.sh em uma janela e mantem aberto.
# Uso: abrir_chat_ia.sh [modo]  onde modo = lan | status | (vazio = normal)
set -u

MODO="${1:-}"

echo '=== Chat IA local (monolito) ==='
echo

case "$MODO" in
  lan)    ~/scripts/chat_local.sh --lan ;;
  status) ~/scripts/chat_local.sh --status ;;
  *)      ~/scripts/chat_local.sh ;;
esac

STATUS=$?
echo
echo '----------------------------'
echo "Fim (codigo $STATUS). Pressione ENTER para fechar."
read -r _
