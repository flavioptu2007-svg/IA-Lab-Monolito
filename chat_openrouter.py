#!/usr/bin/env python3
"""Chat interativo com OpenRouter — conecta a 400+ modelos de IA.

Uso:
    python3 chat_openrouter.py                         # modelo padrão (openrouter/free)
    python3 chat_openrouter.py --model openai/gpt-4o   # modelo específico
    python3 chat_openrouter.py --list                  # listar modelos gratuitos
    python3 chat_openrouter.py --help

Comandos especiais no chat:
    /model <id>     Trocar de modelo em tempo real (só modelos gratuitos)
    /list           Listar modelos gratuitos disponíveis
    /clear          Limpar histórico de conversa
    /sair           Sair do chat

Política de custo zero (AGENTS.md): modelos pagos são RECUSADOS por padrão.
Escape --allow-paid existe, mas não use sem autorização expressa.

Cobrança/cota (HTTP 402/429) nunca é resolvida gastando: o script tenta cair
para um modelo gratuito e, se não houver alternativa, encerra com o código 3
e instruções de uso do provedor local (Ollama) — o `chat.sh` traduz esse
código numa dica amigável.
"""

import argparse
import json
import os
import sys
import urllib.request

DEFAULT_MODEL = os.environ.get("OPENROUTER_DEFAULT_MODEL", "openrouter/free")

# Código de saída reservado para falha de cobrança/cota sem alternativa gratuita
EXIT_BILLING = 3
# Status HTTP que significam "dinheiro/cota", não "erro de código"
BILLING_STATUS_CODES = (402, 429)
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_URL = "https://openrouter.ai/api/v1/models"


def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        print(
            "❌ Chave não encontrada.\n"
            "   exporte OPENROUTER_API_KEY ou preencha no .env:\n"
            "     export OPENROUTER_API_KEY=sk-or-v1-...",
            file=sys.stderr,
        )
        sys.exit(2)
    if key.startswith("YOUR_"):
        print(
            "❌ A chave parece ser um placeholder.\n"
            "   Obtenha uma em https://openrouter.ai/settings/keys",
            file=sys.stderr,
        )
        sys.exit(2)
    return key


def fetch_free_models() -> list[str]:
    """Busca modelos gratuitos na API pública."""
    try:
        req = urllib.request.Request(MODELS_URL)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return [
            m["id"]
            for m in data.get("data", [])
            if m.get("pricing", {}).get("prompt", "1") == "0"
            and m.get("pricing", {}).get("completion", "1") == "0"
            and ":free" in m["id"]
        ]
    except Exception:
        return []


class BillingError(RuntimeError):
    """Falha de cobrança/cota (HTTP 402/429) sem alternativa gratuita."""

    def __init__(self, code: int, model: str, detail: str = "") -> None:
        super().__init__(f"HTTP {code} em {model}: {detail}")
        self.code = code
        self.model = model
        self.detail = detail


# ---- Política custo-zero (AGENTS.md, regra nº 1) ----
ALLOW_PAID = False
_PRICING_CACHE: dict[str, dict] | None = None


def fetch_pricing_table() -> dict[str, dict] | None:
    """Tabela {id: pricing} de todos os modelos; None se a API falhar."""
    global _PRICING_CACHE
    if _PRICING_CACHE is not None:
        return _PRICING_CACHE
    try:
        req = urllib.request.Request(MODELS_URL)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        _PRICING_CACHE = {m["id"]: m.get("pricing", {}) for m in data.get("data", [])}
        return _PRICING_CACHE
    except Exception:
        return None


def is_free_model(model: str, table: dict[str, dict] | None) -> bool:
    """True só se for comprovadamente gratuito; falha segura para desconhecidos."""
    if model == "openrouter/free" or model.endswith(":free"):
        return True  # IDs explicitamente gratuitos
    if not table:
        return False  # sem catálogo não dá para provar que é grátis
    p = table.get(model)
    if not p:
        return False  # id desconhecido → recusar
    try:
        return float(p.get("prompt", "1")) == 0.0 and float(p.get("completion", "1")) == 0.0
    except (TypeError, ValueError):
        return False


def ensure_free(model: str) -> bool:
    """Verifica a política custo-zero; imprime o motivo quando recusa."""
    if ALLOW_PAID:
        return True
    if not is_free_model(model, fetch_pricing_table()):
        print(
            f"🚫 Modelo pago ou não-verificável recusado: {model}\n"
            "   Política deste ambiente: CUSTO ZERO (veja AGENTS.md).\n"
            "   Use /list para ver modelos gratuitos.\n"
            "   (Escape --allow-paid existe, mas NÃO use sem autorização expressa.)"
        )
        return False
    return True


def billing_hint(model: str, code: int) -> None:
    """Explica um HTTP 402/429 e aponta as saídas sem custo."""
    print(
        f"\n⚠️  HTTP {code} — o provedor recusou por cobrança/cota esgotada "
        f"(modelo: {model}).\n"
        "   Política deste ambiente: CUSTO ZERO — nada foi cobrado e nenhuma\n"
        "   credencial paga será usada para contornar isso.\n"
        "   Alternativas gratuitas:\n"
        f"     • Trocar para um modelo :free → /model openrouter/free  (veja /list)\n"
        "     • Usar o provedor local (custo zero) via monolito:\n"
        '         ./scripts/chat_local.sh --pergunta "sua pergunta"\n'
        "       (com IA_LAB_PRIMARY_PROVIDER=ollama no .env, para Ollama em\n"
        "        http://localhost:11434)\n"
    )


def stream_chat(api_key: str, model: str, messages: list[dict], *, _retried: bool = False) -> str:
    """Envia mensagem com streaming e exibe resposta em tempo real.

    Em HTTP 402/429 tenta uma única vez um modelo gratuito (``openrouter/free``)
    e, se ainda falhar, levanta :class:`BillingError`.
    """
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": True,
        }
    ).encode()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/openrouter-chat",
        "X-Title": "OpenRouter Chat",
    }

    req = urllib.request.Request(API_URL, data=payload, headers=headers, method="POST")

    full_response = ""
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            buffer = ""
            while True:
                chunk = resp.read(1)
                if not chunk:
                    break
                buffer += chunk.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        try:
                            obj = json.loads(line[6:])
                            delta = obj["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                print(content, end="", flush=True)
                                full_response += content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.readable() else ""
        try:
            error_data = json.loads(error_body)
            msg = error_data.get("error", {}).get("message", error_body)
        except (json.JSONDecodeError, AttributeError):
            msg = error_body or str(e)

        if e.code in BILLING_STATUS_CODES:
            billing_hint(model, e.code)
            if not _retried and model != DEFAULT_MODEL:
                print(f"\n🔁 Tentando o modelo gratuito {DEFAULT_MODEL}...\n")
                return stream_chat(api_key, DEFAULT_MODEL, messages, _retried=True)
            print(f"   Detalhe do provedor: {msg}")
            raise BillingError(e.code, model, str(msg)) from e

        print(f"\n❌ Erro HTTP {e.code}: {msg}")
    except Exception as e:
        print(f"\n❌ Erro: {type(e).__name__}: {e}")

    print()  # linha final
    return full_response


def print_banner(model: str) -> None:
    print("╔══════════════════════════════════════════════════╗")
    print("║        🤖 OpenRouter Chat Interativo            ║")
    print("╠══════════════════════════════════════════════════╣")
    print(f"║  Modelo: {model:<38}║")
    print("║                                                  ║")
    print("║  Comandos:                                       ║")
    print("║    /model <id>  Trocar modelo                   ║")
    print("║    /list        Modelos gratuitos                ║")
    print("║    /clear       Limpar conversa                  ║")
    print("║    /sair        Sair                             ║")
    print("╚══════════════════════════════════════════════════╝")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--model", "-m", default=DEFAULT_MODEL, help="Modelo ID (default: %(default)s)"
    )
    parser.add_argument("--list", "-l", action="store_true", help="Listar modelos gratuitos e sair")
    parser.add_argument(
        "--allow-paid",
        action="store_true",
        help="Permitir modelos pagos (NÃO USE sem autorização expressa — política custo zero)",
    )
    args = parser.parse_args()

    global ALLOW_PAID
    ALLOW_PAID = args.allow_paid
    model = args.model

    # Listar modelos gratuitos (não precisa de chave)
    if args.list:
        print("🆓 Modelos gratuitos disponíveis:\n")
        free = fetch_free_models()
        if free:
            for m in sorted(free):
                print(f"   {m}")
            print(f"\nTotal: {len(free)} modelos")
        else:
            print("   Nenhum modelo gratuito encontrado (ou erro de conexão).")
        sys.exit(0)

    api_key = get_api_key()

    # Política custo-zero: validar o modelo antes de qualquer chamada
    if not ensure_free(model):
        sys.exit(2)

    print_banner(model)
    messages: list[dict] = []

    while True:
        try:
            user_input = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Até logo!")
            break

        if not user_input:
            continue

        # Comandos especiais
        if user_input.startswith("/"):
            cmd_parts = user_input.split(maxsplit=1)
            cmd = cmd_parts[0].lower()

            if cmd in ("/sair", "/exit", "/quit", "/q"):
                print("👋 Até logo!")
                break

            elif cmd == "/clear":
                messages.clear()
                print("🧹 Conversa limpa.\n")
                continue

            elif cmd == "/list":
                free = fetch_free_models()
                if free:
                    print("\n🆓 Modelos gratuitos:\n")
                    for m in sorted(free):
                        marker = " →" if m == model else "  "
                        print(f"{marker} {m}")
                    print(f"\nTotal: {len(free)}\n")
                else:
                    print("⚠️  Não foi possível listar modelos.\n")
                continue

            elif cmd == "/model":
                new_model = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""
                if new_model:
                    if ensure_free(new_model):
                        model = new_model
                        print(f"🔄 Modelo alterado para: {model}\n")
                    else:
                        print(f"📌 Mantendo modelo atual: {model}\n")
                else:
                    print(f"📌 Modelo atual: {model}")
                    print("   Uso: /model <id-gratuito>\n")
                continue

            elif cmd == "/help":
                print("Comandos: /model <id> · /list · /clear · /sair\n")
                continue

            else:
                print(f"❓ Comando desconhecido: {cmd}\n")
                continue

        # Adicionar mensagem do usuário
        messages.append({"role": "user", "content": user_input})

        # Resposta
        print(f"\n🤖 {model.split('/')[-1]}: ", end="", flush=True)
        try:
            reply = stream_chat(api_key, model, messages)
        except BillingError as e:
            print(
                "\n🛑 Sem alternativa gratuita neste momento. Nada foi cobrado.\n"
                "   Próximos passos:\n"
                "     • Confirme o provedor local: curl -s http://localhost:11434/api/tags\n"
                "     • Recarregue créditos gratuitos depois ou use outro modelo :free (/list)\n"
                f"   (detalhe: HTTP {e.code} em {e.model})\n"
            )
            sys.exit(EXIT_BILLING)
        except urllib.error.URLError as e:
            print(f"\n❌ Falha de rede: {e.reason}")
            reply = ""

        # Salvar resposta no histórico
        if reply:
            messages.append({"role": "assistant", "content": reply})

        print()


if __name__ == "__main__":
    main()
