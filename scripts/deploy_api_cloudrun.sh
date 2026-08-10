#!/usr/bin/env bash
# =============================================================================
# deploy_api_cloudrun.sh — Deploy da API IA-Lab no Google Cloud Run
# =============================================================================
# Documenta todo o processo e permite retomar o deploy quando o billing ativar.
#
# ESTADO ATUAL (09/08/2026):
#   ✅ Imagem construída e testada localmente:  ia-lab-api:cloudrun (963MB)
#   ✅ API funciona (health OK, /api/chat responde, 30+ rotas)
#   ✅ Access token renovado (client_secret extraído do firebase-tools)
#   ⏸️ BLOQUEIO: billing DESATIVADO no projeto jogos-5f131 → Cloud Run exige billing
#   ⏸️ Pendente: chave OpenAI válida (a do ambiente está inválida - 401)
#
# USO:
#   ./scripts/deploy_api_cloudrun.sh status        # mostra estado atual
#   ./scripts/deploy_api_cloudrun.sh build         # reconstrói a imagem
#   ./scripts/deploy_api_cloudrun.sh push          # envia p/ Artifact Registry
#   ./scripts/deploy_api_cloudrun.sh deploy        # cria/atualiza serviço Cloud Run
# =============================================================================
set -euo pipefail

PROJECT="jogos-5f131"
REGION="us-central1"
SERVICE="ia-lab-api"
IMAGE_TAG="ia-lab-api:cloudrun"
GCR_IMAGE="gcr.io/${PROJECT}/ia-lab-api:latest"

CONFIGSTORE="$HOME/.config/configstore/firebase-tools.json"

# ── Utilitário: obtém access token (renova se necessário) ────────────────────
get_token() {
  python3 - "$CONFIGSTORE" <<'EOF'
import json, sys, time, urllib.request, urllib.parse
conf = json.load(open(sys.argv[1]))
tok = conf.get('tokens', {})
exp = tok.get('expires_at', 0)
now = int(time.time())
if tok.get('access_token') and exp > now + 120:
    print(tok['access_token']); raise SystemExit
rt = tok.get('refresh_token')
cid = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
csec = 'j9iVZfS8kkCEFUPaAeJV0sAi'  # client_secret público do firebase-tools
data = urllib.parse.urlencode({
    'client_id': cid, 'client_secret': csec, 'grant_type': 'refresh_token',
    'refresh_token': rt,
    'scope': 'https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/firebase openid',
}).encode()
req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data,
                             headers={'Content-Type': 'application/x-www-form-urlencoded'})
resp = json.load(urllib.request.urlopen(req, timeout=30))
at = resp['access_token']
conf['tokens']['access_token'] = at
conf['tokens']['expires_at'] = int(time.time()) + int(resp.get('expires_in', 3600))
json.dump(conf, open(sys.argv[1], 'w'))
print(at)
EOF
}

# ── 1. STATUS ────────────────────────────────────────────────────────────────
cmd_status() {
  echo "=== PROJETO: $PROJECT ==="
  echo "--- imagem local ---"
  docker images $IMAGE_TAG --format '{{.Repository}}:{{.Tag}} {{.Size}} {{.CreatedSince}}' || echo "  (não construída)"
  echo
  echo "--- billing do projeto (obrigatório p/ Cloud Run) ---"
  TOKEN=$(get_token)
  curl -s "https://cloudbilling.googleapis.com/v1/projects/$PROJECT/billingInfo" \
    -H "Authorization: Bearer $TOKEN" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print('  billingEnabled:', d.get('billingEnabled', False))"
  echo
  echo "--- APIs necessárias ---"
  for api in artifactregistry run cloudbuild; do
    echo -n "  $api: "
    curl -s "https://serviceusage.googleapis.com/v1/projects/$PROJECT/services/${api}.googleapis.com" \
      -H "Authorization: Bearer $TOKEN" | python3 -c \
      "import json,sys; d=json.load(sys.stdin); print(d.get('state', '?'))"
  done
  echo
  echo "--- serviço Cloud Run existente? ---"
  TOKEN=$(get_token)
  curl -s -o /dev/null -w '  HTTP %{http_code}\n' \
    "https://run.googleapis.com/v2/projects/$PROJECT/locations/$REGION/services/$SERVICE" \
    -H "Authorization: Bearer $TOKEN"
}

# ── 2. BUILD ─────────────────────────────────────────────────────────────────
cmd_build() {
  echo "=== BUILD da imagem ($IMAGE_TAG) ==="
  echo "Preparando build context limpo em /tmp/ia-lab-build ..."
  rm -rf /tmp/ia-lab-build && mkdir -p /tmp/ia-lab-build
  cp pyproject.toml requirements.txt Dockerfile.cloudrun /tmp/ia-lab-build/
  for d in ai api web src leituraia Aplicativo_Coraci; do cp -r "$d" /tmp/ia-lab-build/; done
  find /tmp/ia-lab-build \( -name '__pycache__' -o -name '*.pyc' -o -name 'node_modules' -o -name '.venv' \) -exec rm -rf {} + 2>/dev/null || true
  echo "Contexto: $(du -sh /tmp/ia-lab-build 2>/dev/null | awk '{print $1}')"
  echo "Build em andamento (pode levar ~5-10 min)..."
  DOCKER_BUILDKIT=0 docker build -f /tmp/ia-lab-build/Dockerfile.cloudrun -t $IMAGE_TAG /tmp/ia-lab-build
  echo "✅ Imagem $IMAGE_TAG criada."
}

# ── 3. PUSH (requer billing ativo) ───────────────────────────────────────────
cmd_push() {
  echo "=== PUSH para Artifact Registry ==="
  TOKEN=$(get_token)
  echo "$TOKEN" | docker login -u oauth2accesstoken --password-stdin https://gcr.io
  docker tag $IMAGE_TAG $GCR_IMAGE
  docker push $GCR_IMAGE
  echo "✅ Imagem publicada: $GCR_IMAGE"
}

# ── 4. DEPLOY (requer billing ativo) ─────────────────────────────────────────
cmd_deploy() {
  echo "=== DEPLOY no Cloud Run ==="
  TOKEN=$(get_token)
  echo "Habilitando APIs (artifactregistry, run, cloudbuild)..."
  for api in artifactregistry.googleapis.com run.googleapis.com cloudbuild.googleapis.com; do
    curl -s -X POST "https://serviceusage.googleapis.com/v1/projects/$PROJECT/services/$api:enable" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
  done
  echo "Aguardando ativação das APIs (30s)..."
  sleep 30
  cmd_push
  echo
  echo "Criando/atualizando serviço $SERVICE em $REGION ..."
  # NOTE: ajustar env vars conforme necessário:
  #   IA_LAB_OPENAI_API_KEY=<chave válida>  (obrigatório para o chat funcionar)
  #   IA_LAB_RAG_ENABLED=false             (RAG desabilitado na nuvem)
  curl -s -X PATCH \
    "https://run.googleapis.com/v2/projects/$PROJECT/locations/$REGION/services/$SERVICE" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d "{
      \"template\": {
        \"containers\": [{
          \"image\": \"$GCR_IMAGE\",
          \"env\": [
            {\"name\": \"IA_LAB_RAG_ENABLED\", \"value\": \"false\"},
            {\"name\": \"IA_LAB_OPENAI_API_KEY\", \"value\": \"<SUA_CHAVE_AQUI>\"}
          ],
          \"resources\": {\"limits\": {\"cpu\": \"1\", \"memory\": \"1Gi\"}}
        }],
        \"maxInstanceRequestConcurrency\": 80
      },
      \"ingress\": \"INGRESS_TRAFFIC_ALL\"
    }" | head -c 400
  echo
  echo "✅ Deploy submetido. URL final: https://$SERVICE-$PROJECT-$REGION.run.app"
}

# ── Main ─────────────────────────────────────────────────────────────────────
case "${1:-status}" in
  status) cmd_status ;;
  build)  cmd_build ;;
  push)   cmd_push ;;
  deploy) cmd_deploy ;;
  *) echo "Uso: $0 {status|build|push|deploy}"; exit 1 ;;
esac
