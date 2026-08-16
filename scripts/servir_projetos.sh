#!/usr/bin/env bash
# ============================================================================
#  📱 Portal de Projetos Educacionais — acesso pelo celular na rede local
#
#  Sobe/derruba o servidor HTTP que expõe o diretório ~/portal_projetos na
#  rede local (porta 8765 por padrão) — os jogos, quizzes, corretores e
#  provas ficam acessíveis pelo celular/tablet na mesma rede Wi-Fi.
#
#  Por padrão serve o portal JÁ EXISTENTE (não-destrutivo): nada é apagado,
#  os assets PWA (manifest.json, sw.js, ícones) são preservados.
#
#  Uso:
#    ./servir_projetos.sh            # sobe o servidor (porta 8765)
#    ./servir_projetos.sh --porta 9000
#    ./servir_projetos.sh --remontar # reconstrói o portal a partir dos fontes
#    ./servir_projetos.sh --parar    # derruba o servidor
#    ./servir_projetos.sh --status   # mostra o estado atual
#
#  Acesse pelo celular (mesma rede Wi-Fi):
#    http://192.168.15.17:8765
# ============================================================================
set -u

# Fonte dos HTMLs educacionais (usada apenas no modo --remontar)
FONTES="${FONTES:-$HOME/OpenManus}"
PORTAL="${PORTAL:-$HOME/portal_projetos}"
PIDFILE="$PORTAL/.servidor.pid"
LOG="$PORTAL/.servidor.log"

PORT=8765
REMOUNT=0
ACAO=""

while [ $# -gt 0 ]; do
  case "$1" in
    --porta)   PORT="${2:-8765}"; shift 2;;
    --porta=*) PORT="${1#--porta=}"; shift;;
    --remontar) REMOUNT=1; shift;;
    --parar|-p) ACAO="parar"; shift;;
    --status|-s) ACAO="status"; shift;;
    --help|-h)
      echo "Uso: $0 [--porta N] [--remontar] [--parar] [--status]"
      echo "  (sem flag)   Sobe o servidor na porta 8765 (padrão)"
      echo "  --porta N    Usa a porta N (ex.: --porta 9000)"
      echo "  --remontar   Reconstrói ~/portal_projetos a partir dos fontes (~/OpenManus)"
      echo "  --parar      Derruba o servidor"
      echo "  --status     Mostra o estado atual"
      exit 0;;
    *)
      echo "❌ Argumento desconhecido: $1"
      echo "Uso: $0 [--porta N] [--remontar] [--parar] [--status]"
      exit 1;;
  esac
done

VERDE=$'\e[0;32m'; AMARELO=$'\e[1;33m'; VERMELHO=$'\e[0;31m'; AZUL=$'\e[0;34m'; CINZA=$'\e[2m'; RESET=$'\e[0m'
ok()   { echo -e "${VERDE}  ✅ $1${RESET}"; }
info() { echo -e "${AZUL}  ℹ️  $1${RESET}"; }
warn() { echo -e "${AMARELO}  ⚠️  $1${RESET}"; }
erro() { echo -e "${VERMELHO}  ❌ $1${RESET}"; }

# ------------------------------------------------------------------ helpers
ip_local() {
  ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}' \
    || hostname -I 2>/dev/null | awk '{print $1}'
}

# PID de um processo http.server escutando na porta $1 (fallback sem PIDFILE)
pid_na_porta() {
  local p; p=$(ss -tlnp 2>/dev/null | grep ":$1 " | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)
  [ -z "$p" ] && p=$(pgrep -f "http.server $1" 2>/dev/null | head -1)
  echo "$p"
}

servidor_rodando() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null
}

parar_servidor() {
  local pid=""
  if [ -f "$PIDFILE" ]; then
    pid=$(cat "$PIDFILE" 2>/dev/null)
  else
    pid=$(pid_na_porta "$PORT")
  fi
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    sleep 0.5
    if kill -0 "$pid" 2>/dev/null; then
      warn "PID $pid não respondeu ao SIGTERM — tentando SIGKILL."
      kill -9 "$pid" 2>/dev/null
      sleep 0.3
    fi
    ok "Servidor parado (PID $pid)."
  else
    info "Nenhum servidor ativo na porta $PORT."
  fi
  rm -f "$PIDFILE"
}

# ------------------------------------------------------------------ remontar (opcional)
backup_pwa_assets() {
  # Preserva os assets PWA do portal atual (manifest, SW, ícones) para restaurar
  # após a reconstrução — eles não existem nos fontes do OpenManus.
  local tmp; tmp=$(mktemp -d)
  for f in manifest.json sw.js favicon.ico favicon.png apple-touch-icon.png \
           icon-192.png icon-512.png icon-maskable-512.png; do
    [ -e "$PORTAL/$f" ] && cp -a "$PORTAL/$f" "$tmp/"
  done
  [ -e "$PORTAL/i18n" ] && cp -a "$PORTAL/i18n" "$tmp/" 2>/dev/null
  echo "$tmp"
}

montar_portal() {
  if [ ! -d "$FONTES" ] || ! ls "$FONTES"/*.html >/dev/null 2>&1; then
    erro "Fontes não encontrados em $FONTES — não é possível remontar."
    info "Use sem --remontar para servir o portal existente."
    exit 1
  fi

  local pwa; pwa=$(backup_pwa_assets)
  rm -rf "$PORTAL"
  mkdir -p "$PORTAL"
  cd "$FONTES" || exit 1

  # 1) HTMLs educacionais — todos
  for f in *.html; do
    [ -f "$f" ] && ln -s "$FONTES/$f" "$PORTAL/$f"
  done

  # 2) Recursos compartilhados usados pelos HTMLs
  for r in i18n-loader.js sw_omredu.js i18n.js; do
    [ -e "$FONTES/$r" ] && ln -s "$FONTES/$r" "$PORTAL/$r"
  done

  # 3) Restaura os assets PWA preservados
  for f in "$pwa"/*; do
    [ -e "$f" ] && cp -a "$f" "$PORTAL/"
  done
  rm -rf "$pwa"

  # 4) index.html gerado com links para todos os projetos
  gerar_index

  local total; total=$(ls "$PORTAL"/*.html | wc -l)
  info "Portal remontado em $PORTAL ($total arquivos HTML + recursos)."
}

gerar_index() {
  local ip; ip=$(ip_local)
  local f nome emoji
  cat > "$PORTAL/index.html" <<EOF
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/x-icon" href="favicon.ico">
<link rel="icon" type="image/png" sizes="64x64" href="favicon.png">
<link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#312e81">
<title>📱 Projetos Educacionais</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:linear-gradient(160deg,#1e1b4b,#312e81 60%,#4f46e5);min-height:100vh;color:#fff;padding:24px 16px 60px}
  h1{font-size:1.5rem;margin-bottom:4px}
  p.sub{color:#a5b4fc;font-size:.85rem;margin-bottom:20px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
  a.card{display:block;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);border-radius:16px;padding:16px;color:#fff;text-decoration:none;transition:all .15s}
  a.card:hover{background:rgba(255,255,255,.16);transform:translateY(-3px);border-color:#a5b4fc}
  .emoji{font-size:2rem;display:block;margin-bottom:8px}
  .nome{font-weight:800;font-size:.95rem}
  .dica{margin-top:22px;background:rgba(255,255,255,.07);border-radius:12px;padding:12px 14px;font-size:.8rem;color:#c7d2fe}
  code{background:rgba(0,0,0,.3);padding:2px 8px;border-radius:6px;font-size:.85rem}
</style>
</head>
<body>
  <h1>📱 Projetos Educacionais</h1>
  <p class="sub">Servidos pelo seu computador na rede local — abra no celular ou tablet.</p>
  <div class="grid">
EOF
  for f in "$PORTAL"/*.html; do
    b=$(basename "$f")
    [ "$b" = "index.html" ] && continue
    nome=$(echo "$b" | sed 's/_/ /g; s/\.html//' | sed -E 's/\b(.)/\U\1/g')
    case "$b" in
      *bingo*)      emoji="🎱";;
      *memoria*)    emoji="🧠";;
      *quiz*)       emoji="❓";;
      *jogo*)       emoji="🎮";;
      *domino*)     emoji="🁫";;
      *uno*)        emoji="🃏";;
      *prova*)      emoji="📝";;
      *escola*|*gestao*|*diario*) emoji="🏫";;
      *corretor*)   emoji="✅";;
      *adapt*)      emoji="🧩";;
      *debate*)     emoji="🗣️";;
      *labirinto*)  emoji="🌀";;
      *historia*|*historico*) emoji="📜";;
      *)            emoji="📄";;
    esac
    echo "    <a class=\"card\" href=\"./$b\"><span class=\"emoji\">$emoji</span><span class=\"nome\">$nome</span></a>" >> "$PORTAL/index.html"
  done
  cat >> "$PORTAL/index.html" <<EOF
  </div>
  <div class="dica">💡 No celular: acesse <code>http://$ip:$PORT</code> — o computador e o celular devem estar na <b>mesma rede Wi-Fi</b>. Para encerrar: <code>./scripts/servir_projetos.sh --parar</code></div>
</body>
</html>
EOF
}

# ------------------------------------------------------------------ main
case "$ACAO" in
  parar)  parar_servidor; exit 0;;
  status)
    if servidor_rodando; then
      ok "Servidor ATIVO (PID $(cat "$PIDFILE"))."
      info "Acesse: http://$(ip_local):$PORT"
    else
      alvo=$(pid_na_porta "$PORT")
      if [ -n "$alvo" ]; then
        warn "Servidor detectado na porta $PORT (PID $alvo) mas sem PIDFILE ($PIDFILE)."
      else
        info "Servidor parado."
      fi
    fi
    exit 0;;
esac

if [ ! -d "$PORTAL" ] || ! ls "$PORTAL"/*.html >/dev/null 2>&1; then
  if [ "$REMOUNT" = "1" ]; then
    # --remontar cria o portal — prossegue
    :
  else
    erro "Portal não encontrado em $PORTAL."
    info "Rode com --remontar para criá-lo a partir de $FONTES, ou aponte PORTAL."
    exit 1
  fi
fi

# Porta já ocupada (com ou sem PIDFILE)?
alvo=$(pid_na_porta "$PORT")
if [ -n "$alvo" ]; then
  warn "Porta $PORT já está em uso (PID $alvo). Use --parar primeiro ou --porta N."
  exit 1
fi

echo "============================================================"
echo "   📱 PORTAL DE PROJETOS EDUCACIONAIS"
echo "============================================================"

# Modo --remontar: reconstrói o portal a partir dos fontes
if [ "$REMOUNT" = "1" ]; then
  montar_portal
fi

IP=$(ip_local)
if [ -z "$IP" ]; then
  erro "Não foi possível detectar o IP da rede local."
  exit 1
fi

cd "$PORTAL" || exit 1
# setsid: desacopla o processo em nova sessão — sobrevive ao fechamento do
# terminal (nohup sozinho pode morrer junto com o shell em alguns ambientes).
setsid python3 -m http.server "$PORT" --bind 0.0.0.0 > "$LOG" 2>&1 < /dev/null &
disown
sleep 1
# o PID do setsid pode ser o de um processo intermediário — captura o PID real
# que está escutando na porta (via ss) ou o python http.server (via pgrep).
REAL_PID=$(pid_na_porta "$PORT")
[ -n "$REAL_PID" ] && echo "$REAL_PID" > "$PIDFILE"

if servidor_rodando; then
  echo
  ok "Servidor rodando em http://0.0.0.0:$PORT (PID $(cat "$PIDFILE"))"
  echo
  echo -e "${AZUL}  📲 No CELULAR (mesma rede Wi-Fi) acesse:${RESET}"
  echo -e "${VERDE}     http://$IP:$PORT${RESET}"
  echo
  echo -e "${CINZA}  Portal: $PORTAL${RESET}"
  echo -e "${CINZA}  Derrubar: ./scripts/servir_projetos.sh --parar${RESET}"
  echo -e "${CINZA}  Status:  ./scripts/servir_projetos.sh --status${RESET}"
  echo
  # verificação local (com retry — o servidor pode levar ~1-2s para aceitar conexões)
  ok_verif=false
  for _tent in 1 2 3 4 5; do
    if curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/index.html" | grep -q 200; then
      ok_verif=true; break
    fi
    sleep 1
  done
  if [ "$ok_verif" = true ]; then
    ok "Verificação local: portal respondeu HTTP 200."
  else
    warn "O portal não respondeu localmente — confira o log: $LOG"
  fi
else
  erro "Falha ao iniciar o servidor. Log: $LOG"
  cat "$LOG" 2>/dev/null | tail -5
  exit 1
fi
