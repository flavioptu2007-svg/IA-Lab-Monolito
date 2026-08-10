# 🔑 Chave Gemini — uso local (desenvolvimento)

Guia rápido de como a chave da API Gemini está configurada **localmente** e
como usá-la para desenvolver/testar o `/api/chat` na sua máquina.

---

## 📁 Onde está a chave

| Arquivo | Conteúdo | Commitável? |
|---|---|---|
| `.env` | **Chave real** (`IA_LAB_GEMINI_API_KEY=AQ.…`) | ❌ Não (no `.gitignore`) |
| `.env.example` | Modelo sem segredos | ✅ Sim |
| Render (dashboard) | Mesma chave em `IA_LAB_GEMINI_API_KEY` (produção) | — |

> ✅ O `.gitignore` já protege `.env` — verifique com:
> ```bash
> git check-ignore .env   # deve imprimir o caminho (ignorado)
> ```

## 🚀 Como usar

O `ai/settings.py` lê o `.env` automaticamente (pydantic-settings, prefixo
`IA_LAB_`). Basta rodar o servidor local:

```bash
# 1. Garantir que o .env está carregado (padrão já faz isso)
python3 -m uvicorn api.server:app --host 127.0.0.1 --port 8099

# 2. Testar o chat (usa o provider gemini do .env)
curl -s -X POST http://127.0.0.1:8099/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Quem descobriu o Brasil?"}'
```

## 🔄 Trocar de modelo (grátis)

Edite `IA_LAB_GEMINI_MODEL` no `.env`:

| Modelo | Latência típica | Uso |
|---|---|---|
| `gemini-3.5-flash` | ~3–4s | Padrão (melhor qualidade) |
| `gemini-3.1-flash-lite` | ~1,5s | Respostas rápidas |
| `gemini-flash-latest` | — | Alias que segue o melhor disponível |

## ⚠️ Segurança

- **Nunca** commitar o `.env` nem colar a chave em issues/PRs.
- A chave exposta é revogável: [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → botão de apagar.
- Em produção a chave vive **apenas** no dashboard do Render (env var secreta), nunca no repositório.

## 🧪 Teste rápido do provider (sem subir servidor)

```bash
python3 - <<'PY'
import asyncio, os
from ai.providers.providers import GeminiProvider

async def main():
    p = GeminiProvider()            # lê .env automaticamente
    print("modelo:", p.model)
    print("chave configurada:", await p.is_available())
    print("resposta:", (await p.complete("O que foi o Iluminismo? 1 frase."))[:200])

asyncio.run(main())
PY
```
