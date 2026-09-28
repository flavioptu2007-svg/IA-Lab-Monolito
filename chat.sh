#!/usr/bin/env bash
# ============================================================================
# chat.sh — Atalho para o chat OpenRouter
#
# Uso:
#   ./chat.sh                    # modelo padrão do .env
#   ./chat.sh openai/gpt-4o      # modelo específico
#   ./chat.sh --list             # listar modelos gratuitos
#   ./chat.sh --help             # ajuda
#
# CUSTO ZERO (AGENTS.md, regra nº 1): nenhum modelo pago é aceito.
# O tratamento de cobrança/cota (HTTP 402/429) fica em chat_openrouter.py:
# ele tenta um modelo :free e, se não houver alternativa, sai com o código 3;
# aqui traduzimos esse código numa dica para o provedor local (Ollama).
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
CHAT_SCRIPT="$SCRIPT_DIR/chat_openrouter.py"
EXIT_BILLING=3

# ── Carregar .env ──────────────────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# ── Verificar dependências ─────────────────────────────────────────────────
if [ ! -f "$CHAT_SCRIPT" ]; then
    echo "❌ Script chat_openrouter.py não encontrado em $SCRIPT_DIR"
    exit 1
fi

# ── Executar ───────────────────────────────────────────────────────────────
# `set -e` está ativo, então capturamos o código sem abortar o script.
status=0
python3 "$CHAT_SCRIPT" "$@" || status=$?

# 402/429 sem alternativa gratuita → sugerir o provedor local (custo zero).
if [ "$status" -eq "$EXIT_BILLING" ]; then
    OLLAMA_URL="${IA_LAB_OLLAMA_BASE_URL:-http://localhost:11434}"
    echo "ℹ️  Cobrança/cota esgotada no provedor remoto — nada foi gasto."
    if curl -s --max-time 3 "${OLLAMA_URL%/}/api/tags" >/dev/null 2>&1; then
        echo "   Ollama local ativo em $OLLAMA_URL. Alternativa sem custo:"
        echo "     IA_LAB_PRIMARY_PROVIDER=ollama ./scripts/chat_local.sh --pergunta \"sua pergunta\""
    else
        echo "   Ollama não respondeu em $OLLAMA_URL. Alternativa sem custo (usa o .env):"
        echo "     ./scripts/chat_local.sh --pergunta \"sua pergunta\""
        echo "   Para usar o Ollama: ollama serve   # depois: ollama pull ${IA_LAB_OLLAMA_MODEL:-qwen3:latest}"
        echo "   Outras saídas sem custo: ./chat.sh --list (modelos :free)."
    fi
fi

exit "$status"
