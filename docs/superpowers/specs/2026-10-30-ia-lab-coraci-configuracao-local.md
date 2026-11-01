# Configuração local IA-Lab Monolito + Coraci — 2026-10-30

Status: implementado e verificado
Escopo: subir e validar os dois serviços nesta máquina, sem Docker e sem gasto.

## Contexto

O repositório é a working copy em `/home/flavio` (branch `main`, 4 commits à
frente do `origin/main`); o clone em `~/.hermes/cache/repo/IA-Lab-Monolito` é
cache e está no commit do origin. As portas do `docker-compose.yml` (8000,
5000, 6379, 6333/6334, 8080) já são usadas por outros projetos desta máquina
(`ia-backend`, `intel-redis`, `ia-qdrant`, `intel-bitnet`), então `docker
compose up` colidiria com serviços vivos.

Decisão: rodar o monólito e o Coraci como processos locais, em portas
alternativas, com os mesmos perfis lógicos do Compose (API + chat + Ollama),
sem recriar containers nem volumes.

## Modelo de execução

| Serviço | Como sobe | Porta padrão | Dependências |
|---|---|---|---|
| API FastAPI (`api.server:app`) | `scripts/ia_lab_local.sh start` | 8010 | Ollama; Qdrant só se `IA_LAB_RAG_ENABLED=true` |
| Coraci Flask (`Aplicativo_Coraci/app.py`) | idem | 5000 | Ollama (API OpenAI-compatible em `/v1`) |
| Dashboard React (`web/dashboard`) | `npm run dev` (fora do script) | 5173 | API |
| Redis | não consumido pelo código | — | — |
| Qdrant | opcional (RAG) | 6333 | — |
| BitNet | opcional (profile `llm`) | 8080 | — |

Os dois apps são independentes: bancos, configurações e processos separados.
O monólito não inicia o Coraci e vice-versa.

## Contrato de configuração (o que o código realmente lê)

- `IA_LAB_PRIMARY_PROVIDER` (default `ollama`), `IA_LAB_OLLAMA_MODEL`
  (default `glm4:latest`), `IA_LAB_OLLAMA_BASE_URL`.
- `IA_LAB_RAG_ENABLED` (default `false` no `.env`): com `false`, a readiness
  reporta `qdrant: skipped` e não exige o serviço.
- `IA_LAB_API_TOKEN`: protege os routers `/api/v2/**` via header `X-API-Key`.
  `/api/chat` (v1) **não** é protegido — ver riscos.
- Caminhos do chat v2: `IA_LAB_CORACI_DB` e `IA_LAB_CORACI_CONFIG`
  (defaults: `coraci.db` na raiz e `Aplicativo_Coraci/config.json`).
- Caminhos do Flask: `IA_LAB_CORACI_FLASK_DB` e `IA_LAB_CORACI_FLASK_CONFIG`.
- `CORACI_API_KEY` precede o campo `api_key` do `config.json` (Flask) e não é
  persistida em disco.

Knobs definidos em `src/core/config.py` sem consumidor hoje (documentados, não
removidos): `education_db_url`, `education_redis_url`, `education_jwt_secret`
(só validado), `openvino_enabled`, `bitnet_enabled`, `coraci_max_history`.

## Correções aplicadas

1. Default local válido: `ollama_model` era `qwen3:latest` (inexistente) e o
   `primary_provider` era `openai`; agora `glm4:latest` e `ollama`.
2. Defaults do chat v2: apontavam para `localhost:8000` (outro projeto) e
   `glm-5.2-colibri` (modelo inexistente); agora `11434/v1` + `glm4:latest`.
3. `BASE_DIR` do chat v2 resolvia para `src/`: banco em `src/coraci.db` e
   `config.json` real nunca lido; corrigido para a raiz do repositório.
4. Chave Gemini saiu da query string (`?key=`) para o header `x-goog-api-key`;
   mensagens de erro passam por `redact()` antes de log/resposta.
5. Fallback não mascara erro de credencial: 401/403 (sem marcador de cota)
   viram resposta explícita; 402/429 continuam caindo para o local.
6. Provedor de nuvem sem chave não é escolhido pelo roteamento por tarefa.
7. Readiness só exige Qdrant com RAG ligado.
8. Coraci: segredo vindo do ambiente não é gravado no `config.json`; arquivos
   de configuração salvos com permissão 0600; `.env` em 0600.

## Verificação

- `pytest tests/ -q`: 638 passed, 1 skipped (antes: 628/1).
- `ruff check`, `ruff format --check`, `mypy ai api src`: limpos.
- `scripts/ia_lab_local.sh test`: check + pytest + ruff + mypy.
- Bateria ao vivo (42 verificações): health liveness/readiness, chat v1 e SSE
  v2 com Ollama real, persistência e recuperação SQLite entre reinícios,
  cancelamento de stream, autenticação 401/200, Ollama inalcançável, modelo
  inexistente, CRUD do Coraci Flask, logs sem traceback.
- Gemini (free tier): uma chamada real confirmou o header novo.

## Riscos e pendências

- `/api/chat` (v1), `/api/providers`, `/api/agents` e `/api/history` não usam
  `IA_LAB_API_TOKEN`. Protegê-las exige ajustar o dashboard (`web/ui` usa
  `fetch` sem header) — decisão pendente.
- `docker compose up` colide com containers existentes; se for usado, mapear
  outras portas e não subir Redis/Qdrant duplicados.
- `education_*` e `openvino_enabled`/`bitnet_enabled` sem consumidor: ou
  integrar, ou remover em uma limpeza futura.
- EGM não está disponível neste ambiente; esta especificação foi escrita
  manualmente.
