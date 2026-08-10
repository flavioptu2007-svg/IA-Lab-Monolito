#!/usr/bin/env bash
# =============================================================================
#  ☁️ Deploy do Portal de Projetos Educacionais para o Firebase Hosting
#
#  Publica ~/portal_projetos na internet com HTTPS automático:
#    https://<projeto>.web.app
#
#  Requisitos (uma vez):
#    npm install -g firebase-tools
#    firebase login            # autentica com a conta Google (abre o navegador)
#
#  Uso:
#    ./deploy_portal_firebase.sh                # faz o deploy
#    ./deploy_portal_firebase.sh --login        # autentica (se ainda não fez)
#    ./deploy_portal_firebase.sh --projeto NOME # usa projeto específico
#    ./deploy_portal_firebase.sh --status       # mostra o projeto ativo
#    ./deploy_portal_firebase.sh --abrir        # abre o site publicado
# =============================================================================
set -euo pipefail

PORTAL="$(cd "$(dirname "$0")/.." && pwd)/portal_projetos"
PROJETO_PADRAO="jogos-5f131"  # EducacionAI

cd "$PORTAL"

# Sem .firebaserc? Cria apontando para o projeto padrão (criado automaticamente)
if [[ ! -f .firebaserc ]]; then
  echo "{\"projects\":{\"default\":\"$PROJETO_PADRAO\"}}" > .firebaserc
  echo "ℹ️  .firebaserc criado apontando para o projeto '$PROJETO_PADRAO'"
fi

case "${1:-deploy}" in
  --login)
    firebase login --reauth
    ;;
  --status)
    echo "=== Login ativo ==="
    firebase login:list 2>/dev/null || true
    echo
    echo "=== Projeto ativo ==="
    firebase use 2>/dev/null || cat .firebaserc
    ;;
  --abrir)
    URL="https://$(firebase use 2>/dev/null | grep -oE '[a-z0-9-]+' | head -1 || echo "$PROJETO_PADRAO").web.app"
    echo "Abrindo $URL ..."
    xdg-open "$URL" 2>/dev/null || echo "Abra manualmente: $URL"
    ;;
  deploy)
    echo "=== Deploy do portal ($(find . -maxdepth 1 -name '*.html' | wc -l) páginas) para Firebase Hosting ==="
    echo "Destino: https://$(cat .firebaserc | grep -oE '"[a-z0-9-]+"' | head -1 | tr -d '"').web.app"
    echo
    firebase deploy --only hosting
    ;;
  *)
    echo "Uso: $0 [--login|--status|--abrir|deploy]"
    exit 1
    ;;
esac
