#!/usr/bin/env bash
# =============================================================================
#  🔎 check_mcp_pin.sh — monitora quando os servidores MCP git/sqlite passam
#  a suportar o SDK mcp 2.0 (para remover o pin "mcp<2")
#
#  Contexto: o SDK mcp 2.0 removeu a API antiga (list_tools/list_resources)
#  usada pelos servidores mcp-server-sqlite e mcp-server-git. Enquanto os
#  mantenedores não publicarem versão compatível, o pin "mcp<2" é necessário
#  nos configs (Cursor/Claude/Codex). Este script roda o servidor SEM o pin
#  a cada execução e avisa quando ele passar a funcionar.
#
#  Uso:
#    bash scripts/check_mcp_pin.sh            # verifica + avisa (1x por transição)
#    bash scripts/check_mcp_pin.sh --force    # avisa mesmo sem mudança de estado
#    bash scripts/check_mcp_pin.sh --auto-fix # remove o pin dos configs quando OK
#    bash scripts/check_mcp_pin.sh --help
#
#  Agendamento sugerido (crontab):
#    17 9 * * * /home/flavio/scripts/check_mcp_pin.sh
#  (o script já loga sozinho em ~/.local/log/mcp_pin_check.log)
#
#  Estado: ~/.cache/mcp-pin-check/state.json (evita notificar toda execução)
#  Log:    ~/.local/log/mcp_pin_check.log
# =============================================================================
set -u

FORCE=0
AUTO_FIX=0

STATE_DIR="$HOME/.cache/mcp-pin-check"
STATE_FILE="$STATE_DIR/state.json"
LOG="$HOME/.local/log/mcp_pin_check.log"

# Servidores com pin no formato: "nome|comando de teste SEM o pin"
# (override para testes: MCP_PIN_SERVERS="nome|cmd|arg1|arg2;nome2|...")
SERVERS=(
  "sqlite|uvx|mcp-server-sqlite|--db-path|$HOME/.mcp/mcp.db"
  "git|uvx|mcp-server-git|-r|$HOME/AI/openvino"
)
if [[ -n "${MCP_PIN_SERVERS:-}" ]]; then
  IFS=';' read -r -a SERVERS <<< "$MCP_PIN_SERVERS"
fi

# Configs que contêm o pin (override com MCP_CONFIGS="a:b:c" para testes)
CONFIGS="${MCP_CONFIGS:-$HOME/.cursor/mcp.json:$HOME/.claude.json:$HOME/.codex/config.toml}"

# ── Argumentos ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)    FORCE=1; shift ;;
    --auto-fix) AUTO_FIX=1; shift ;;
    -h|--help)  sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "❌ Argumento desconhecido: $1 (use --help)" >&2; exit 1 ;;
  esac
done

# ── Helpers ─────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

mkdir -p "$STATE_DIR" "$(dirname "$LOG")"

notify() {
  local title="$1" body="$2"
  log "🔔 $title — $body"
  if command -v notify-send >/dev/null 2>&1; then
    export DISPLAY="${DISPLAY:-:0}"
    export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"
    notify-send --app-name="check_mcp_pin" --urgency=normal "$title" "$body" 2>/dev/null || true
  fi
}

# handshake MCP (initialize + tools/list) — retorna 0 se o servidor responder.
# Subprocess com deadline: sai assim que recebe as 2 respostas (mata o servidor),
# tolerante a servidores que não fecham o stdio (ex.: demora no tools/list).
handshake_ok() {
  python3 - "$@" <<'PYEOF'
import json, os, select, subprocess, sys, time
payload = "\n".join(json.dumps(m) for m in [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "mcp-pin-check", "version": "1.0"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
]) + "\n"
try:
    proc = subprocess.Popen(sys.argv[1:], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
except Exception:
    sys.exit(1)
try:
    proc.stdin.write(payload.encode())
    proc.stdin.flush()
    # Não fechar o stdin: alguns servidores (ex.: mcp-server-docker) encerram
    # o loop de leitura ao ver EOF antes de processar o tools/list pendente.
except Exception:
    pass
ids = {}
buf = b""
deadline = time.time() + 90
while time.time() < deadline:
    r, _, _ = select.select([proc.stdout], [], [], 1.0)
    if not r:
        continue
    chunk = os.read(proc.stdout.fileno(), 4096)
    if not chunk:
        break
    buf += chunk
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        try:
            m = json.loads(line)
        except Exception:
            continue
        if isinstance(m, dict) and "id" in m:
            ids[m["id"]] = m
    if 1 in ids and 2 in ids:
        break
try:
    proc.kill()
except Exception:
    pass
ok = 1 in ids and "result" in ids[1] and 2 in ids and "result" in ids[2]
sys.exit(0 if ok else 1)
PYEOF
}

read_state() {
  python3 - "$STATE_FILE" <<'PYEOF'
import json, sys
try:
    with open(sys.argv[1]) as f: d = json.load(f)
except Exception:
    d = {}
for s in ("sqlite", "git"):
    d.setdefault(s, "pendente")
print(json.dumps(d))
PYEOF
}

set_state() {
  python3 - "$STATE_FILE" "$1" "$2" <<'PYEOF'
import json, os, sys
path, name, val = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path) as f: d = json.load(f)
except Exception:
    d = {}
d[name] = val
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f: json.dump(d, f, indent=2)
PYEOF
}

# remove o pin "--with mcp<2" do servidor nos configs (JSON e TOML)
auto_fix() {
  local server="$1"
  log "🛠  --auto-fix: removendo pin mcp<2 do servidor '$server' nos configs..."
  IFS=':' read -r -a cfgs <<< "$CONFIGS"
  python3 - "$server" "${cfgs[@]}" <<'PYEOF'
import json, re, sys
server = sys.argv[1]
paths = sys.argv[2:]
for path in paths:
    try:
        with open(path) as f: text = f.read()
    except OSError as e:
        print(f"  ⚠ {path}: {e}"); continue
    if path.endswith(".toml"):
        # remove só na linha args do pacote deste servidor
        new = re.sub(r'args\s*=\s*\["--with",\s*"mcp<2",\s*("mcp-server-' + server + r'")',
                     r'args = [\1', text)
    else:
        # JSON: remove "--with"/"mcp<2" apenas dentro do objeto do servidor
        new = re.sub(r'("' + server + r'"\s*:\s*\{[^}]*?"args"\s*:\s*\[\s*)"--with",\s*"mcp<2",\s*',
                     r'\1', text)
    if new != text:
        with open(path, "w") as f: f.write(new)
        print(f"  ✓ pin removido: {path}")
    else:
        print(f"  – sem pin para remover: {path}")
PYEOF
}

# ── Execução ────────────────────────────────────────────────────────────────
log "═══ check_mcp_pin.sh (auto-fix=$AUTO_FIX, force=$FORCE) ═══"
STATE="$(read_state)"
changed=0

for entry in "${SERVERS[@]}"; do
  IFS='|' read -r -a parts <<< "$entry"
  name="${parts[0]}"
  cmd=("${parts[@]:1}")

  prev="$(printf '%s' "$STATE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('$name','pendente'))")"

  if handshake_ok "${cmd[@]}"; then
    echo "  ✅ $name: funciona SEM o pin mcp<2 — pode remover!"
    log "✅ $name: compatível com SDK mcp 2.0 (sem pin)"
    if [[ "$FORCE" == 1 || "$prev" != "pronto" ]]; then
      notify "MCP '$name': pin mcp<2 pode ser removido!" \
        "O servidor $name já funciona com o SDK mcp 2.0. Remova o pin nos configs (Cursor/Claude/Codex) ou rode: bash scripts/check_mcp_pin.sh --auto-fix"
    fi
    if [[ "$AUTO_FIX" == 1 ]]; then
      auto_fix "$name"
    fi
    set_state "$name" "pronto"
    changed=1
  else
    echo "  ⏳ $name: ainda precisa do pin (SDK mcp 2.0 incompatível)"
    log "⏳ $name: ainda incompatível com SDK mcp 2.0 (mantendo pin)"
    set_state "$name" "pendente"
  fi
done

if [[ "$changed" == 0 ]]; then
  echo "  (nenhuma mudança — pin continua necessário)"
fi
echo "  estado: $(cat "$STATE_FILE" 2>/dev/null | tr -d '\n')"
log "═══ fim (estado: $(cat "$STATE_FILE" 2>/dev/null | tr -d '\n')) ═══"
