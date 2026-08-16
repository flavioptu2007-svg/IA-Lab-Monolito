#!/usr/bin/env bash
# =============================================================================
#  🔄 update_mcps.sh — audita e atualiza todos os MCPs do sistema
#
#  Verifica as versões de todos os componentes MCP (mcporter, CLI mcp,
#  servidores npx/uvx, marcadores mcp-remote), atualiza os desatualizados,
#  valida os configs (sintaxe + pacotes existem) e faz um smoke test
#  (handshake MCP) nos servidores ativos.
#
#  Uso:
#    bash scripts/update_mcps.sh              # audit + update + smoke test
#    bash scripts/update_mcps.sh --check      # somente auditoria (nada muda)
#    bash scripts/update_mcps.sh --no-smoke   # pula o smoke test final
#    bash scripts/update_mcps.sh --help
#
#  Requisitos: internet (npm registry + PyPI), npx, uvx, npm, python3, curl.
#
#  ⚠️ O upgrade do CLI mcp usa pip --user com --break-system-packages
#     (PEP 668 do Ubuntu) — instala só em ~/.local, não toca no sistema.
#
#  ⚠️ mcp-server-sqlite e mcp-server-git usam a API antiga do SDK mcp
#     (removida no 2.0) — por isso o pin "mcp<2" via --with. O script
#     scripts/check_mcp_pin.sh avisa quando esse pin puder ser removido.
# =============================================================================
set -u

CHECK_ONLY=0
SMOKE_TEST=1

LOG="$HOME/.local/log/mcp_update.log"
log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
mkdir -p "$(dirname "$LOG")"

# ── Componentes auditados ───────────────────────────────────────────────────
NPM_SERVERS=(
  "@modelcontextprotocol/server-filesystem"
  "@modelcontextprotocol/server-github"
)
UVX_SERVERS=(
  "mcp-server-docker|"
  "mcp-server-sqlite|mcp<2"
  "mcp-server-git|mcp<2"
)

# Configs validados (sintaxe + pacotes referenciados existem)
CONFIGS_JSON=(
  "$HOME/.cursor/mcp.json"
  "$HOME/.mcporter/mcporter.json"
  "$HOME/.claude.json"
)
CONFIGS_TOML=(
  "$HOME/.codex/config.toml"
)

# Smoke test: "nome|comando do servidor" (espelho do ~/.cursor/mcp.json)
SMOKE=(
  "filesystem|npx|-y|@modelcontextprotocol/server-filesystem|$HOME"
  "github|npx|-y|@modelcontextprotocol/server-github"
  "sqlite|uvx|--with|mcp<2|mcp-server-sqlite|--db-path|$HOME/.mcp/mcp.db"
  "docker|uvx|mcp-server-docker"
  "git|uvx|--with|mcp<2|mcp-server-git|-r|$HOME/AI/openvino"
)

# ── Argumentos ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)    CHECK_ONLY=1; shift ;;
    --no-smoke) SMOKE_TEST=0; shift ;;
    -h|--help)  sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "❌ Argumento desconhecido: $1 (use --help)" >&2; exit 1 ;;
  esac
done

# ── Helpers ─────────────────────────────────────────────────────────────────
latest_npm() {
  curl -fsSL --max-time 15 "https://registry.npmjs.org/$1/latest" 2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null \
    || echo "?"
}

latest_pypi() {
  curl -fsSL --max-time 15 "https://pypi.org/pypi/$1/json" 2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])" 2>/dev/null \
    || echo "?"
}

pkg_exists_npm()  { curl -fsS --max-time 15 -o /dev/null "https://registry.npmjs.org/$1" 2>/dev/null; }
pkg_exists_pypi() { curl -fsS --max-time 15 -o /dev/null "https://pypi.org/pypi/$1/json" 2>/dev/null; }

ver_lt() { # $1 < $2 (semântico)
  [[ "$1" != "$2" ]] && [[ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)" == "$1" ]]
}

cached_npx() { # maior versão em cache do pacote @modelcontextprotocol/*
  local pkg="$1" f name ver max=""
  while IFS= read -r f; do
    name="$(sed -n 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$f" | head -1)"
    ver="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$f" | head -1)"
    if [[ "$name" == "$pkg" ]] && [[ -n "$ver" ]]; then
      if [[ -z "$max" ]] || [[ "$(printf '%s\n%s\n' "$max" "$ver" | sort -V | tail -1)" == "$ver" ]]; then
        max="$ver"
      fi
    fi
  done < <(find "$HOME/.npm/_npx" -maxdepth 6 -path "*/node_modules/@modelcontextprotocol/*/package.json" 2>/dev/null)
  echo "${max:-—}"
}

cached_uvx() { # maior versão em cache do pacote PyPI (dist-info)
  local pkg="$1" dist_pkg="${1//-/_}" d v max=""
  while IFS= read -r d; do
    v="$(basename "$d" .dist-info | sed "s/^${dist_pkg}-//")"
    if [[ "$v" != "$(basename "$d" .dist-info)" ]] && [[ -n "$v" ]]; then
      if [[ -z "$max" ]] || [[ "$(printf '%s\n%s\n' "$max" "$v" | sort -V | tail -1)" == "$v" ]]; then
        max="$v"
      fi
    fi
  done < <(find "$HOME/.cache/uv/archive-v0" -maxdepth 3 -name "${dist_pkg}-*.dist-info" 2>/dev/null)
  echo "${max:-—}"
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
                "clientInfo": {"name": "mcp-update", "version": "1.0"}}},
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

# ── Auditoria de versões (sempre roda) ──────────────────────────────────────
audit_versions() {
  local v i pkg pin
  echo "── Versões ────────────────────────────────────────────────"
  v="$(mcporter --version 2>/dev/null || echo "?")"
  echo "  mcporter (npm global):   instalado $v | latest $(latest_npm mcporter)"
  v="$(python3 -m pip show mcp 2>/dev/null | sed -n 's/^Version: //p' || true)"
  echo "  mcp CLI (python ~/.local): instalado ${v:-?} | latest $(latest_pypi mcp)"
  echo "  ── servidores npx ──"
  for pkg in "${NPM_SERVERS[@]}"; do
    echo "    $pkg: cache $(cached_npx "$pkg") | latest $(latest_npm "$pkg")"
  done
  echo "  ── servidores uvx ──"
  for i in "${UVX_SERVERS[@]}"; do
    pkg="${i%%|*}"; pin="${i#*|}"
    echo "    $pkg${pin:+ (pin $pin)}: cache $(cached_uvx "$pkg") | latest $(latest_pypi "$pkg")"
  done
}

# ── Atualizações (puladas com --check) ─────────────────────────────────────
update_mcporter() {
  local installed latest
  installed="$(mcporter --version 2>/dev/null || echo "?")"
  latest="$(latest_npm mcporter)"
  if [[ "$latest" == "?" ]]; then echo "  ⚠ sem acesso ao npm registry — pulando"; return; fi
  if [[ "$installed" == "?" ]] || ver_lt "$installed" "$latest"; then
    echo "  ⬆ mcporter $installed → $latest ..."
    if npm install -g mcporter@latest >/dev/null 2>&1; then
      echo "  ✅ mcporter agora $(mcporter --version)"
    else
      echo "  ❌ falha ao atualizar mcporter"; return 1
    fi
  else
    echo "  ✅ mcporter já atualizado ($installed)"
  fi
}

update_mcp_cli() {
  local installed latest
  installed="$(python3 -m pip show mcp 2>/dev/null | sed -n 's/^Version: //p' || true)"
  latest="$(latest_pypi mcp)"
  if [[ "$latest" == "?" ]]; then echo "  ⚠ sem acesso ao PyPI — pulando"; return; fi
  if [[ -z "$installed" ]] || ver_lt "$installed" "$latest"; then
    echo "  ⬆ mcp CLI ${installed:-?} → $latest (pip --user, --break-system-packages)..."
    if python3 -m pip install --user -U mcp --break-system-packages >/dev/null 2>&1; then
      echo "  ✅ mcp CLI atualizado"
    else
      echo "  ❌ falha ao atualizar mcp CLI"; return 1
    fi
  else
    echo "  ✅ mcp CLI já atualizado ($installed)"
  fi
}

refresh_npx() {
  local pkg latest cached new
  for pkg in "${NPM_SERVERS[@]}"; do
    latest="$(latest_npm "$pkg")"
    cached="$(cached_npx "$pkg")"
    if [[ "$latest" == "?" ]]; then echo "  ⚠ $pkg: sem registro — pulando"; continue; fi
    if [[ "$cached" == "—" ]] || ver_lt "$cached" "$latest"; then
      echo "  ⬆ $pkg: cache $cached → latest $latest (refresh npx)..."
      timeout 90 npx -y "$pkg@latest" --help >/dev/null 2>&1 || true
      new="$(cached_npx "$pkg")"
      echo "  ✅ $pkg: cache agora $new"
    else
      echo "  ✅ $pkg: cache $cached = latest $latest"
    fi
  done
}

refresh_uvx() {
  local i pkg pin latest cached new
  local -a cmd
  for i in "${UVX_SERVERS[@]}"; do
    pkg="${i%%|*}"; pin="${i#*|}"
    latest="$(latest_pypi "$pkg")"
    cached="$(cached_uvx "$pkg")"
    if [[ "$latest" == "?" ]]; then echo "  ⚠ $pkg: sem registro — pulando"; continue; fi
    if [[ "$cached" == "—" ]] || ver_lt "$cached" "$latest"; then
      echo "  ⬆ $pkg: cache $cached → latest $latest (refresh uvx)..."
      cmd=(uvx)
      [[ -n "$pin" ]] && cmd+=(--with "$pin")
      cmd+=("$pkg" --help)
      timeout 90 "${cmd[@]}" >/dev/null 2>&1 || true
      new="$(cached_uvx "$pkg")"
      echo "  ✅ $pkg: cache agora $new"
    else
      echo "  ✅ $pkg: cache $cached = latest $latest"
    fi
  done
}

clean_mcp_auth() {
  local dirs d v max=""
  dirs="$(ls -d "$HOME/.mcp-auth"/mcp-remote-* 2>/dev/null || true)"
  [[ -z "$dirs" ]] && { echo "  (sem marcadores mcp-remote)"; return; }
  for d in $dirs; do
    v="${d##*mcp-remote-}"
    if [[ -z "$max" ]] || [[ "$(printf '%s\n%s\n' "$max" "$v" | sort -V | tail -1)" == "$v" ]]; then
      max="$v"
    fi
  done
  for d in $dirs; do
    v="${d##*mcp-remote-}"
    if [[ "$v" == "$max" ]]; then
      echo "  ✅ mantendo mcp-remote-$v (mais recente)"
    else
      echo "  🧹 removendo marcador antigo mcp-remote-$v"
      rm -rf "$d"
    fi
  done
}

# ── Validação de configs (sempre roda) ─────────────────────────────────────
validate_configs() {
  local path refs name cmd pkg bad=0

  echo "── Configs ─────────────────────────────────────────────────"
  for path in "${CONFIGS_JSON[@]}"; do
    [[ -f "$path" ]] || continue
    echo "  ${path#$HOME/}"
    refs="$(python3 - "$path" <<'PYEOF'
import json, sys
def pkg_of(cmd, args):
    if cmd == "npx":
        for a in args:
            if a in ("-y", "--yes") or a.startswith("-"):
                continue
            return a
    if cmd == "uvx":
        skip = False
        for a in args:
            if skip:
                skip = False; continue
            if a == "--with":
                skip = True; continue
            if a.startswith("-"):
                continue
            return a
    return ""
try:
    with open(sys.argv[1]) as f: d = json.load(f)
except Exception as e:
    print(f"ERRO|{e}"); sys.exit(0)
servers = d.get("mcpServers", {})
for name, cfg in servers.items():
    if not isinstance(cfg, dict):
        continue
    cmd = cfg.get("command")
    args = cfg.get("args") or []
    if cmd in ("npx", "uvx"):
        print(f"{name}|{cmd}|{pkg_of(cmd, args)}")
PYEOF
)"
    if [[ "$refs" == ERRO\|* ]]; then
      echo "    ❌ ${refs#ERRO|}"
      bad=1
      continue
    fi
    if [[ -z "$refs" ]]; then
      echo "    (sem servidores stdio)"
      continue
    fi
    while IFS='|' read -r name cmd pkg; do
      if [[ -z "$pkg" ]]; then echo "    ⚠ $name: sem pacote identificado"; continue; fi
      if [[ "$cmd" == "npx" ]] && pkg_exists_npm "$pkg"; then
        echo "    ✓ $name → $pkg (npm)"
      elif [[ "$cmd" == "uvx" ]] && pkg_exists_pypi "$pkg"; then
        echo "    ✓ $name → $pkg (PyPI)"
      else
        echo "    ❌ $name → $pkg NÃO existe no registro (404!)"
        bad=1
      fi
    done < <(printf '%s\n' "$refs")
  done

  for path in "${CONFIGS_TOML[@]}"; do
    [[ -f "$path" ]] || continue
    echo "  ${path#$HOME/}"
    refs="$(python3 - "$path" <<'PYEOF'
import sys, tomllib
def pkg_of(cmd, args):
    if cmd == "npx":
        for a in args:
            if a in ("-y", "--yes") or str(a).startswith("-"):
                continue
            return a
    if cmd == "uvx":
        skip = False
        for a in args:
            if skip:
                skip = False; continue
            if a == "--with":
                skip = True; continue
            if str(a).startswith("-"):
                continue
            return a
    return ""
try:
    with open(sys.argv[1], "rb") as f: d = tomllib.load(f)
except Exception as e:
    print(f"ERRO|{e}"); sys.exit(0)
for name, cfg in d.get("mcp_servers", {}).items():
    if not isinstance(cfg, dict):
        continue
    cmd = cfg.get("command")
    args = cfg.get("args") or []
    if cmd in ("npx", "uvx"):
        print(f"{name}|{cmd}|{pkg_of(cmd, args)}")
PYEOF
)"
    if [[ "$refs" == ERRO\|* ]]; then
      echo "    ❌ ${refs#ERRO|}"
      bad=1
      continue
    fi
    if [[ -z "$refs" ]]; then echo "    (sem servidores stdio)"; continue; fi
    while IFS='|' read -r name cmd pkg; do
      if [[ -z "$pkg" ]]; then echo "    ⚠ $name: sem pacote identificado"; continue; fi
      if [[ "$cmd" == "npx" ]] && pkg_exists_npm "$pkg"; then
        echo "    ✓ $name → $pkg (npm)"
      elif [[ "$cmd" == "uvx" ]] && pkg_exists_pypi "$pkg"; then
        echo "    ✓ $name → $pkg (PyPI)"
      else
        echo "    ❌ $name → $pkg NÃO existe no registro (404!)"
        bad=1
      fi
    done < <(printf '%s\n' "$refs")
  done
  return "$bad"
}

# ── Smoke test ─────────────────────────────────────────────────────────────
smoke_test() {
  local entry name
  local -a cmd
  echo "── Smoke test (handshake MCP) ─────────────────────────────"
  for entry in "${SMOKE[@]}"; do
    IFS='|' read -r -a parts <<< "$entry"
    name="${parts[0]}"
    cmd=("${parts[@]:1}")
    if handshake_ok "${cmd[@]}"; then
      echo "    ✓ $name"
    else
      echo "    ❌ $name (initialize/tools-list sem resposta)"
    fi
  done
}

# ── Execução ───────────────────────────────────────────────────────────────
log "═══ update_mcps.sh (check=$CHECK_ONLY, smoke=$SMOKE_TEST) ═══"
audit_versions

STATUS=0
if [[ "$CHECK_ONLY" == 1 ]]; then
  echo
  echo "── Modo --check: somente auditoria (nada foi alterado) ──"
else
  echo
  echo "── Atualizações ───────────────────────────────────────────"
  update_mcporter  || STATUS=1
  update_mcp_cli   || STATUS=1
  echo "  ── refresh caches npx ──"
  refresh_npx
  echo "  ── refresh caches uvx ──"
  refresh_uvx
  echo "  ── limpeza .mcp-auth ──"
  clean_mcp_auth
fi

echo
validate_configs || STATUS=1

if [[ "$SMOKE_TEST" == 1 ]]; then
  echo
  smoke_test
fi

log "═══ fim (status=$STATUS) ═══"
exit "$STATUS"
