#!/usr/bin/env bash
# =============================================================================
#  🤖 Chat IA local — sobe o servidor e testa o /api/chat com um clique
#
#  Inicia o monolito (api.server) na porta 8099 usando a chave do .env
#  (provider Gemini do Google AI Studio — grátis, sem cartão) e já testa
#  o /api/chat com uma pergunta, mostrando a resposta + latência.
#
#  O servidor fica RODANDO em background (desacoplado do terminal) — você
#  pode continuar usando o terminal normalmente e acessar o Swagger em:
#      http://127.0.0.1:8099/docs
#
#  Uso:
#    ./chat_local.sh                 # sobe o servidor + testa o chat
#    ./chat_local.sh --lan           # expõe na LAN (outros computadores acessam)
#    ./chat_local.sh --pergunta "..." # sobe e testa com pergunta customizada
#    ./chat_local.sh --status         # mostra se o servidor está no ar
#    ./chat_local.sh --parar          # derruba o servidor
#    ./chat_local.sh --porta 9000     # usa outra porta
#
#  Requisitos:
#    - Python 3.10+ com as deps do monolito (pip install -r requirements.txt)
#    - Arquivo .env na raiz com IA_LAB_GEMINI_API_KEY (ver .env.example)
#
#  🏫 Modo LAN (--lan): os computadores da sala acessam pelo IP da máquina,
#    ex.: http://192.168.15.17:8099/docs — só a máquina precisa de internet
#    (o chat chama a API Gemini da nuvem; os alunos não precisam de internet).
#    O CORS da API já libera qualquer IP 192.168.x.x para o portal.
# =============================================================================
set -u

# ── Config ──────────────────────────────────────────────────────────────────
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORTA="${PORTA:-8099}"
HOST="127.0.0.1"
URL="http://${HOST}:${PORTA}"
LOG="${TMPDIR:-/tmp}/chat_local_${PORTA}.log"
PID_FILE="${TMPDIR:-/tmp}/chat_local_${PORTA}.pid"
PERGUNTA="Quem descobriu o Brasil? Responda em 2 frases."
COMANDO_TESTE="sobe"

# ── Parsing de argumentos ───────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --porta)   PORTA="$2"; URL="http://${HOST}:${PORTA}"; LOG="${TMPDIR:-/tmp}/chat_local_${PORTA}.log"; PID_FILE="${TMPDIR:-/tmp}/chat_local_${PORTA}.pid"; shift 2 ;;
    --lan)     HOST="0.0.0.0"; shift ;;
    --pergunta) PERGUNTA="$2"; shift 2 ;;
    --status)  COMANDO_TESTE="status"; shift ;;
    --parar)   COMANDO_TESTE="parar"; shift ;;
    -h|--help) sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "❌ Argumento desconhecido: $1 (use --help)" >&2; exit 1 ;;
  esac
done

# ── Helpers ─────────────────────────────────────────────────────────────────
esta_no_ar() {
  curl -s --max-time 5 "${URL}/api/health" -o /dev/null -w '%{http_code}' 2>/dev/null | grep -q '^200$'
}

pid_atual() {
  # 1) PID guardado pelo próprio script
  if [[ -f "$PID_FILE" ]]; then
    local pid="$(cat "$PID_FILE" 2>/dev/null)"
    [[ -n "$pid" && -d "/proc/$pid" ]] && { echo "$pid"; return; }
  fi
  # 2) fallback: descobre o PID escutando a porta (ex.: servidor via tmux)
  local detectado
  detectado="$(ss -tlnp 2>/dev/null | grep ":${PORTA}" | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)"
  [[ -n "$detectado" ]] && { echo "$detectado"; return; }
  detectado="$(lsof -ti tcp:"${PORTA}" 2>/dev/null | head -1)"
  [[ -n "$detectado" ]] && echo "$detectado" || true
}

# ── --status ────────────────────────────────────────────────────────────────
if [[ "$COMANDO_TESTE" == "status" ]]; then
  if esta_no_ar; then
    echo "✅ Servidor NO AR em ${URL}"
    echo "   Swagger: ${URL}/docs"
    echo "   PID: $(pid_atual)"
    curl -s --max-time 5 "${URL}/api/health"
    echo
    exit 0
  fi
  echo "❌ Servidor PARADO (porta ${PORTA})"
  exit 1
fi

# ── --parar ─────────────────────────────────────────────────────────────────
if [[ "$COMANDO_TESTE" == "parar" ]]; then
  PID="$(pid_atual)"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null
    rm -f "$PID_FILE"
    echo "🛑 Servidor parado (PID $PID)"
  else
    echo "ℹ️  Nenhum servidor rodando na porta ${PORTA}"
    rm -f "$PID_FILE"
  fi
  exit 0
fi

# ── Pré-checagens ───────────────────────────────────────────────────────────
cd "$RAIZ" || { echo "❌ Não consegui entrar em $RAIZ" >&2; exit 1; }

if [[ ! -f .env ]]; then
  echo "❌ Arquivo .env não encontrado na raiz." >&2
  echo "   Copie o modelo: cp .env.example .env  (e preencha IA_LAB_GEMINI_API_KEY)" >&2
  exit 1
fi

if ! grep -q '^IA_LAB_GEMINI_API_KEY=AQ' .env 2>/dev/null; then
  echo "⚠️  IA_LAB_GEMINI_API_KEY parece vazia no .env — o chat pode falhar." >&2
  echo "   Obtenha uma chave grátis em https://aistudio.google.com/apikey" >&2
fi

if esta_no_ar; then
  echo "ℹ️  Já existe um servidor NO AR em ${URL} — vou apenas testar o chat."
  COMANDO_TESTE="ja_rodando"
else
  echo "🚀 Subindo o servidor na porta ${PORTA} (log: $LOG)..."

  # Desacopla do terminal (sobrevive ao fim do shell) — aprendizado:
  # rodar direto em background faz o processo morrer junto com o shell.
  # --lan usa --host 0.0.0.0 (acessível pelos computadores da escola).
  setsid nohup python3 -m uvicorn api.server:app --host "$HOST" --port "$PORTA" \
    > "$LOG" 2>&1 < /dev/null &
  echo $! > "$PID_FILE"
  COMANDO_TESTE="subindo"

  # Espera o boot (até 45s)
  for _ in $(seq 1 15); do
    if esta_no_ar; then break; fi
    sleep 3
  done
fi

# ── Resultado ───────────────────────────────────────────────────────────────
if esta_no_ar; then
  echo "✅ Servidor NO AR — ${URL}"
  echo "   Swagger: ${URL}/docs"
  echo "   Provider: $(curl -s --max-time 5 "${URL}/api/config" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('primary_provider','?'))" 2>/dev/null || echo '?')"
  if [[ "$HOST" == "0.0.0.0" ]]; then
    # Descobre o IP da máquina na LAN para os alunos acessarem
    LAN_IP="$(ip -4 addr show 2>/dev/null | grep -oE 'inet 192\.168\.[0-9.]+' | head -1 | awk '{print $2}')"
    echo "   🏫 LAN:  http://${LAN_IP:-<IP-da-maquina>}:${PORTA}/docs  (computadores da escola)"
  fi
  echo
  echo "🧪 Testando /api/chat..."
  echo "   Pergunta: $PERGUNTA"
  echo
  curl -s --max-time 90 -X POST "${URL}/api/chat" \
    -H 'Content-Type: application/json' \
    -d "{\"prompt\": \"$PERGUNTA\"}" \
    -o /tmp/chat_local_resposta.json -w '   HTTP %{http_code} | %{time_total}s\n'
  python3 - <<'PY' 2>/dev/null || head -c 300 /tmp/chat_local_resposta.json
import json
d = json.load(open('/tmp/chat_local_resposta.json'))
print('\n   💬 Resposta:')
print('   ' + (d.get('response') or '(vazia)')[:400])
print(f"\n   ⚡ {d.get('latency_ms')} ms · provider: {d.get('provider')} · task: {d.get('task_type')}")
PY
  echo
  echo "💡 Para parar: ./scripts/chat_local.sh --parar  |  status: --status"
  exit 0
fi

echo "❌ Servidor não subiu em ${PORTA} (45s). Últimas linhas do log:" >&2
tail -15 "$LOG" 2>/dev/null >&2
exit 1
