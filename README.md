# IA-Lab Unified

[![🇧🇷 Português](README.md)](README.md) [![🇺🇸 English](README.en.md)](README.en.md) [![🇨🇳 中文](README_zh.md)](README_zh.md) [![🇯🇵 日本語](README_ja.md)](README_ja.md) [![🇰🇷 한국어](README_ko.md)](README_ko.md)
[![CI](https://github.com/flavioptu2007-svg/IA-Lab-Monolito/actions/workflows/ci.yml/badge.svg)](https://github.com/flavioptu2007-svg/IA-Lab-Monolito/actions/workflows/ci.yml)

**Monolito FastAPI** que unifica 5 projetos em um único ecossistema de IA, áudio, RAG, educação e inferência local.

```
📦 ia-lab-unified v2.1.1
├── 🧠 8 providers de IA (OpenAI, Claude, Gemini, Groq, GLM, Perplexity, Ollama, BitNet)
├── 🎙️ Pipeline de áudio completo (STT, TTS, VAD, efeitos, microfone virtual)
├── 📚 RAG com Qdrant (busca semântica + contexto aumentado)
├── 💬 Chat SSE com histórico (migrado do Coraci)
├── 🏫 Módulo educacional (planos de aula, BNCC, avaliações, calendário)
├── 🔧 OpenVINO opcional (inferência local Intel)
├── 🔢 BitNet (LLM 1-bit ultra-eficiente em CPU)
├── 🧪 487 testes — suíte completa
├── 📡 53+ endpoints REST
└── 🐳 13 serviços Docker orquestrados
```

---

## 🚀 Guia Rápido de 5 Minutos

```bash
# 1. Clone e instale
pip install -e ".[dev]"

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas API keys (pelo menos uma)

# 3. Inicie o servidor
uvicorn api.server:app --reload --port 8000

# 4. Teste se está funcionando
curl http://localhost:8000/api/health

# 5. Abra o dashboard
cd web/dashboard && npm install && npm run dev
# Acesse http://localhost:5173
```

### Comandos essenciais

| O que fazer | Comando |
|-------------|---------|
| Rodar testes | `python3 -m pytest tests/ -v` |
| Testar chat | `curl -X POST http://localhost:8000/api/chat -H 'Content-Type: application/json' -d '{"prompt":"Olá"}'` |
| Ver providers | `curl http://localhost:8000/api/providers` |
| Ver docs da API | Abrir `http://localhost:8000/docs` |
| Rodar só educação | `pip install -e ".[education]"` |
| Rodar com Docker | `docker compose up -d` |

---

## Índice

- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Desenvolvimento Local com IA (grátis)](#desenvolvimento-local-com-ia-grátis)
- [Execução](#execução)
- [Docker Compose](#docker-compose)
- [API Endpoints](#api-endpoints)
- [Testes](#testes)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Ferramentas do Ambiente](#ferramentas-do-ambiente)
- [Troubleshooting](#troubleshooting)
- [Contribuição](#contribuição)

---

## Arquitetura

### Ciclo de Vida da Aplicação

O FastAPI moderno usa o padrão **lifespan** (substituindo `@app.on_event` que é deprecado):

```
FastAPI(lifespan=lifespan)
    │
    ├── Startup ──────────────────────────────────────┐
    │   • init_db()         — SQLite Coraci           │
    │   • db_load_all()     — Carrega conversas       │
    │   • load_config()     — Carrega configurações   │
    │   └─ logger.info()    — Log de inicialização    │
    │                                                 │
    ├── Aplicação rodando (yield)                     │
    │   • 58+ endpoints REST                          │
    │   • 8 providers de IA                           │
    │   • SSE streaming, áudio, RAG, educação         │
    │                                                 │
    └── Shutdown ─────────────────────────────────────┘
        • VectorStore.close()     — Qdrant socket
        • close_db()              — SQLite WAL checkpoint
        • AudioEngine.close()     — PipeWire/PulseAudio
        • AIService.close()       — Providers (futuro)
        └─ logger.info()          — Log de encerramento
```

### Diagrama do Sistema

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Monolito (lifespan)                      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 register_routers(app)                            │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │    │
│  │  │ API v1   │ │ API v2   │ │ API v2   │ │ API v2             │  │    │
│  │  │ Chat/IA  │ │ Chat SSE │ │ OpenVINO │ │ Education (BNCC)   │  │    │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────────┬──────────┘  │    │
│  └───────┼────────────┼────────────┼──────────────────┼──────────────┘    │
│          │            │            │                  │                    │
│  ┌───────▼────────────▼────────────▼──────────────────▼──────────────┐    │
│  │                     Core Services                                 │    │
│  │  AIService · TaskClassifier · AudioEngine · VectorStore · Cache    │    │
│  └────────────────────────────────┬──────────────────────────────────┘    │
│                                   │                                       │
│  ┌────────────────────────────────▼──────────────────────────────────┐    │
│  │                     Providers (8)                                 │    │
│  │  OpenAI · Claude · Gemini · Groq · GLM · Perplexity · Ollama · B. │    │
│  └───────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐
│  Qdrant  │ │ SQLite   │ │ PipeWire /   │ │ PostgreSQL   │ │ OpenVINO │
│  (RAG)   │ │ (Coraci) │ │ PulseAudio   │ │ (Educação)   │ │(Opcional)│
└──────────┘ └──────────┘ └──────────────┘ └──────────────┘ └──────────┘
```

### Módulos Core (`src/core/`)

| Módulo | Responsabilidade |
|--------|-----------------|
| **`src/core/lifespan.py`** | Context manager de startup/shutdown — init DB, carrega dados, fecha conexões |
| **`src/core/routers.py`** | `register_routers(app)` — centraliza todos os `include_router` |
| **`src/core/config.py`** | `UnifiedSettings` — configuração unificada de todos os módulos |

### Routers Centralizados

Todos os routers são registrados em um único lugar — `src/core/routers.py`:

```python
def register_routers(app: FastAPI) -> None:
    app.include_router(chat_v2_router)
    app.include_router(openvino_router)
    app.include_router(education_router)
    # Adicione novos routers aqui
```

### Shutdown Graceful

No encerramento da API, o lifespan libera automaticamente:

| Recurso | O que fecha |
|---------|-------------|
| **Qdrant** (`VectorStore`) | Socket gRPC/REST do cliente persistente |
| **SQLite** (`close_db()`) | Checkpoint WAL → `.db-wal`/`.db-shm` limpos |
| **AudioEngine** | Dispositivos PipeWire/PulseAudio (se inicializado) |
| **AIService** | Providers/cache de classes (preparado para futuro) |

### Projetos Unificados

| Projeto Original | Módulo no Monolito | Status |
|-----------------|-------------------|--------|
| **IA-Lab Enterprise** (raiz) | Core: API, providers, áudio, RAG | ✅ Nativo |
| **Coraci** (Flask) | `src/api/v2/chat_coraci.py` | ✅ Migrado para FastAPI SSE |
| **BitNet** (LLM 1-bit) | `ai/providers/bitnet.py` | ✅ 8º provider |
| **OpenVINO** (Intel AI Lab) | `src/openvino/` (opcional) | ✅ Módulo opcional |
| **HistóriaIA** (Educação) | `src/education/` | ✅ Módulo integrado |

---

## Instalação

### Pré-requisitos

- Python ≥ 3.11
- Redis (opcional, para cache)
- Qdrant (opcional, para RAG)

### Instalação básica (core)

```bash
pip install -e .
```

### Com grupos opcionais

```bash
# Core + ferramentas de desenvolvimento
pip install -e ".[dev]"

# Core + STT (SpeechBrain + PyTorch)
pip install -e ".[stt]"

# Core + TTS avançado (Edge-TTS)
pip install -e ".[tts]"

# Core + OpenVINO (inferência Intel)
pip install -e ".[openvino]"

# Core + LangChain + RAG avançado
pip install -e ".[langchain]"

# Core + BitNet (LLM 1-bit)
pip install -e ".[bitnet]"

# Core + HistóriaIA (PostgreSQL + auth)
pip install -e ".[education]"

# Tudo (exceto OpenVINO que é pesado)
pip install -e ".[all]"
```

### Desenvolvimento completo

```bash
pip install -e ".[dev,stt,tts,langchain,bitnet,education]"
```

---

## Configuração

Copie o arquivo de exemplo e configure as variáveis de ambiente:

```bash
cp .env.example .env
```

> 📄 O arquivo completo com **todas as variáveis** está em [`.env.example`](.env.example) (47 variáveis).

### Variáveis principais

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `IA_LAB_PRIMARY_PROVIDER` | `openai` | Provedor padrão |
| `IA_LAB_OPENAI_API_KEY` | — | API key OpenAI |
| `IA_LAB_CLAUDE_API_KEY` | — | API key Anthropic Claude |
| `IA_LAB_GEMINI_API_KEY` | — | API key Google Gemini |
| `IA_LAB_GROQ_API_KEY` | — | API key Groq |
| `IA_LAB_GLM_API_KEY` | — | API key GLM (Zhipu) |
| `IA_LAB_PERPLEXITY_API_KEY` | — | API key Perplexity |
| `IA_LAB_OLLAMA_BASE_URL` | `http://localhost:11434` | URL do Ollama |
| `IA_LAB_BITNET_BASE_URL` | `http://localhost:8080/v1` | URL do BitNet |
| `IA_LAB_QDRANT_HOST` | `localhost` | Host do Qdrant |
| `IA_LAB_LOG_LEVEL` | `INFO` | Nível de log |

> 💡 **Dica:** Você só precisa de **uma** API key para começar. Defina `IA_LAB_OPENAI_API_KEY` ou use o Ollama local (zero configuração).

---

## Desenvolvimento Local com IA (grátis)

A forma mais simples de rodar o chat com IA **sem gastar nada**: o provider **Gemini** do Google AI Studio (conta gratuita, **sem cartão de crédito**). Guia completo: **[`ENV_LOCAL_GEMINI.md`](ENV_LOCAL_GEMINI.md)**.

### Passo a passo

```bash
# 1. Configure o .env (modelo sem segredos):
cp .env.example .env
# 2. Edite .env e cole sua chave gratuita em IA_LAB_GEMINI_API_KEY
#    (obtenha em https://aistudio.google.com/apikey — sem cartão)

# 3. Sobe o servidor local (porta 8099) e testa o chat com 1 comando:
./scripts/chat_local.sh
```

### Tudo com um clique

O script [`scripts/chat_local.sh`](scripts/chat_local.sh) sobe o servidor **e já testa o `/api/chat`**, mostrando resposta + latência:

| Comando | O que faz |
|---------|-----------|
| `./scripts/chat_local.sh` | Sobe o servidor (porta 8099) + testa o chat |
| `./scripts/chat_local.sh --pergunta "..."` | Testa com pergunta customizada |
| `./scripts/chat_local.sh --status` | Mostra se está no ar + PID |
| `./scripts/chat_local.sh --parar` | Derruba o servidor |
| `./scripts/chat_local.sh --porta 9000` | Usa outra porta |

Swagger local: `http://127.0.0.1:8099/docs`

### Configuração recomendada (já no `.env.example`)

| Variável | Valor recomendado | Motivo |
|----------|------------------|--------|
| `IA_LAB_PRIMARY_PROVIDER` | `gemini` | Grátis, sem cartão |
| `IA_LAB_GEMINI_API_KEY` | `AQ...` (sua chave) | Google AI Studio |
| `IA_LAB_GEMINI_MODEL` | `gemini-3.1-flash-lite` | ~1,5s, respostas completas |
| `IA_LAB_RAG_ENABLED` | `false` | RAG exige Qdrant local |

> ⚠️ **Segurança:** o `.env` está no `.gitignore` — a chave **nunca** deve ser commitada. Em produção ela vive apenas nas env vars do Render/dashboard. Veja detalhes em [`ENV_LOCAL_GEMINI.md`](ENV_LOCAL_GEMINI.md).

---

## Execução

### Servidor API

```bash
# Desenvolvimento (com reload)
uvicorn api.server:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000`.

- Documentação interativa: `http://localhost:8000/docs`
- Documentação ReDoc: `http://localhost:8000/redoc`

### Dashboard Web

```bash
cd web/dashboard
npm install
npm run dev
# Acesse http://localhost:5173
```

O Vite faz proxy de `/api/*` para `localhost:8000` automaticamente.

### Demonstração de áudio

```bash
python3 demo_audio.py           # Demonstração completa
python3 demo_audio.py --quick   # Apenas processamento de sinal
```

---

## Docker Compose

O ecossistema completo pode ser executado via Docker Compose com profiles seletivos:

### Apenas core (sempre ativo)

```bash
docker compose up -d
# Sobe: api, coraci, redis, qdrant
```

### Core + BitNet (LLM 1-bit)

```bash
docker compose --profile llm up -d
```

### Core + OpenVINO

```bash
docker compose --profile openvino up -d
```

### Core + HistóriaIA

```bash
docker compose --profile historiaia up -d
```

### Tudo

```bash
docker compose --profile all up -d
```

### Serviços

| Serviço | Porta | Profile | Descrição |
|---------|:-----:|:-------:|-----------|
| **api** | `8000` | sempre | Monolito FastAPI |
| **coraci** | `5000` | sempre | Chat Flask (legado) |
| **redis** | `6379` | sempre | Cache + sessões |
| **qdrant** | `6333` | sempre | Vector database (RAG) |
| **bitnet** | `8080` | `llm, all` | LLM 1-bit |
| **openvino-dashboard** | `8501` | `openvino, all` | Streamlit dashboard |
| **openvino-flask** | `5001` | `openvino, all` | Flask dashboard |
| **vad** | — | `audio, all` | Escuta contínua |
| **batch** | — | `batch, all` | Processamento em lote |
| **docs** | `8002` | `dev, all` | MkDocs |
| **historiaia-db** | `5432` | `historiaia, all` | PostgreSQL |
| **historiaia-app** | `8001` | `historiaia, all` | FastAPI HistóriaIA |
| **test** | — | `test` | Suite de testes |

---

## API Endpoints

### v1 — Chat, Áudio e Sistema

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/health` | Health check (Qdrant, Ollama) |
| `GET` | `/api/providers` | Listar providers configurados |
| `GET` | `/api/agents` | Listar agentes especializados |
| `POST` | `/api/chat` | Chat com IA (roteamento inteligente) |
| `GET` | `/api/history` | Histórico de conversas |
| `DELETE` | `/api/history` | Limpar histórico |
| `GET` | `/api/metrics` | Métricas Prometheus |
| `GET` | `/api/config` | Configuração do sistema |
| `GET` | `/api/audio/status` | Status do módulo de áudio |
| `GET` | `/api/audio/devices` | Dispositivos de áudio |
| `POST` | `/api/audio/record` | Gravar áudio |
| `POST` | `/api/audio/stt` | Speech-to-text |
| `POST` | `/api/audio/tts` | Text-to-speech |
| `POST` | `/api/audio/effects` | Processar áudio |
| `POST` | `/api/audio/mic/create` | Criar microfone virtual |
| `POST` | `/api/audio/mic/remove` | Remover microfone virtual |
| `GET` | `/api/audio/mic/status` | Status do microfone virtual |
| `GET` | `/api/audio/metrics` | Métricas Prometheus de áudio |
| `GET` | `/api/audio/config` | Configuração do módulo de áudio |

### v2 — Chat SSE (Coraci)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/v2/chat` | Chat SSE streaming |
| `GET` | `/api/v2/conversations` | Listar conversas |
| `GET` | `/api/v2/conversations/{id}` | Obter conversa |
| `DELETE` | `/api/v2/conversations/{id}` | Apagar conversa |
| `DELETE` | `/api/v2/conversations` | Limpar todas |
| `GET` | `/api/v2/config` | Obter configuração |
| `POST` | `/api/v2/config` | Atualizar configuração |
| `POST` | `/api/v2/config/test` | Testar conexão |

### v2 — OpenVINO (opcional)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v2/openvino/health` | Health check |
| `POST` | `/api/v2/openvino/generate` | Geração de texto |
| `POST` | `/api/v2/openvino/transcribe` | Transcrição Whisper |
| `POST` | `/api/v2/openvino/rag/query` | Pergunta RAG |
| `GET` | `/api/v2/openvino/models` | Listar modelos |

> **Nota:** Todos os endpoints OpenVINO retornam `503` com `detail="openvino_not_available"` quando o OpenVINO não está instalado.

### v2 — Education (HistóriaIA)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v2/education/health` | Health check |
| `GET` | `/api/v2/education/bncc/skills` | Listar habilidades BNCC |
| `GET` | `/api/v2/education/bncc/competences` | Listar competências |
| `POST` | `/api/v2/education/lesson-plans` | Criar plano de aula |
| `GET` | `/api/v2/education/lesson-plans` | Listar planos de aula |
| `GET` | `/api/v2/education/lesson-plans/{id}` | Obter plano de aula |
| `PATCH` | `/api/v2/education/lesson-plans/{id}` | Atualizar plano de aula |
| `DELETE` | `/api/v2/education/lesson-plans/{id}` | Remover plano de aula |
| `POST` | `/api/v2/education/activities` | Criar atividade |
| `GET` | `/api/v2/education/activities` | Listar atividades |
| `GET` | `/api/v2/education/activities/{id}` | Obter atividade |
| `PATCH` | `/api/v2/education/activities/{id}` | Atualizar atividade |
| `DELETE` | `/api/v2/education/activities/{id}` | Remover atividade |
| `POST` | `/api/v2/education/evaluations` | Criar avaliação |
| `GET` | `/api/v2/education/evaluations` | Listar avaliações |
| `GET` | `/api/v2/education/evaluations/{id}` | Obter avaliação |
| `PATCH` | `/api/v2/education/evaluations/{id}` | Atualizar avaliação |
| `DELETE` | `/api/v2/education/evaluations/{id}` | Remover avaliação |
| `POST` | `/api/v2/education/calendar` | Criar evento |
| `GET` | `/api/v2/education/calendar` | Listar eventos |
| `DELETE` | `/api/v2/education/calendar/{id}` | Remover evento |

---

## Testes

```bash
# Executar todos os testes
python3 -m pytest tests/ -v

# Testes específicos
python3 -m pytest tests/test_openvino_module.py -v
python3 -m pytest tests/test_education_module.py -v
python3 -m pytest tests/test_bitnet_provider.py -v
python3 -m pytest tests/test_api_v2_chat.py -v
python3 -m pytest tests/test_e2e_monolito.py -v  # Testes E2E cobrindo 57+ rotas

# Com cobertura
python3 -m pytest tests/ --cov=ai,api,src --cov-report=term-missing

# Testes via Docker
docker compose --profile test up
```

### Cobertura atual: **487 testes**

> 💡 **Nota:** se o plugin `pytest-flask` estiver instalado no ambiente, ele conflita com as fixtures do FastAPI e gera erros (`AttributeError: response_class`). Remova com `pip uninstall pytest-flask`.

| Módulo | Testes | Status |
|--------|:------:|:------:|
| Core (IA, Providers, Settings) | 353+ | ✅ |
| Coraci SSE Chat (v2) | 15 | ✅ |
| BitNet Provider | 12 | ✅ |
| OpenVINO Module | 25 (19 + 6 success-path) | ✅ |
| Education Module | 47 | ✅ |
| E2E Monolito | 35 (57+ rotas) | ✅ |

---

## Estrutura do Projeto

```
/home/flavio/
├── src/                          # Módulos do monolito unificado
│   ├── __init__.py               # Package marker v2.1.1
│   ├── core/
│   │   ├── __init__.py
│   │   ├── lifespan.py           # 🔄 Startup/shutdown (init DB → fecha conexões)
│   │   ├── routers.py            # 🔗 register_routers(app) — centraliza includes
│   │   └── config.py             # UnifiedSettings
│   ├── api/
│   │   └── v2/
│   │       ├── chat_coraci.py    # Chat SSE (Coraci) — streaming + histórico
│   │       ├── openvino.py       # Endpoints OpenVINO (opcional, 503 guard)
│   │       └── education.py      # Endpoints Education (BNCC, planos, atividades)
│   ├── education/                # Módulo HistóriaIA
│   │   ├── __init__.py
│   │   ├── enums.py              # Enums acadêmicos + BNCC (30+ habilidades)
│   │   ├── schemas.py            # 15 schemas Pydantic
│   │   └── services.py           # EducationStore (CRUD) + BNCC skills
│   └── openvino/                 # Módulo OpenVINO (opcional)
│       ├── __init__.py
│       └── pipelines.py          # OpenVINOPipeline, AudioRagPipeline
├── ai/                           # Core IA (legado, em uso ativo)
│   ├── providers/
│   │   ├── base.py               # BaseProvider + TaskType
│   │   ├── providers.py          # OpenAI, Claude, Gemini, Groq, GLM, Perplexity
│   │   ├── ollama.py             # OllamaProvider
│   │   └── bitnet.py             # BitNetProvider (8º, LLM 1-bit)
│   ├── service.py                # AIService — orquestrador de providers
│   ├── settings.py               # Settings (SecretStr, ProviderName Literal)
│   ├── classifier.py             # TaskClassifier
│   ├── memory/store.py           # VectorStore (Qdrant — singleton + close())
│   ├── agents/                   # Agentes especializados (architect, code, audio, writer)
│   ├── audio/                    # Engine, STT, TTS, VAD, efeitos, microfone virtual
│   └── telemetry.py              # Prometheus metrics
├── api/
│   └── server.py                 # FastAPI app (lifespan + register_routers)
├── web/
│   └── dashboard/                # 🆕 Dashboard React + Vite + TypeScript
│       ├── src/
│       │   ├── api/client.ts     # API client tipado (57+ endpoints)
│       │   ├── pages/            # 10 páginas (Dashboard, Chat, Providers, etc.)
│       │   ├── components/       # Sidebar com navegação
│       │   └── styles/           # Tema escuro completo
│       ├── vite.config.ts        # Proxy /api → localhost:8000
│       └── package.json          # React 19, lucide-react, recharts
├── tests/                        # 487 testes
│   ├── test_service.py
│   ├── test_classifier.py
│   ├── test_bitnet_provider.py
│   ├── test_api_v2_chat.py
│   ├── test_openvino_module.py
│   ├── test_education_module.py
│   ├── test_e2e_monolito.py      # 🆕 35 testes E2E (57 rotas)
│   └── test_audio/               # STT, TTS, VAD, efeitos, recorder, player…
├── Aplicativo_Coraci/            # Flask app (mantido para compatibilidade)
├── AI/                           # Projetos fonte originais
│   ├── BitNet/
│   ├── openvino/
│   └── historiaia/
├── docker-compose.yml            # 13 serviços com profiles
├── pyproject.toml                # Dependências consolidadas (8 grupos)
└── .env.example                  # 47 variáveis documentadas
```

---

## Ferramentas do Ambiente

Ferramentas complementares instaladas neste ambiente, fora do monolito.

### Multi-Agent-CAD (`mac`)

Geração de modelos 3D a partir de texto (**text-to-CAD**) com 4 agentes orquestrados por LangGraph e kernel build123d. Repo local: `Projetos/Multi-Agent-CAD/` (venv Python 3.11, `multi-agent-cad 1.0.0`).

**Provider configurado (Z.AI / GLM):**

| Item | Valor |
|------|-------|
| `DS_BASE_URL` | `https://api.z.ai/api/coding/paas/v4` (OpenAI-compatible, Z.AI Coding Plan) |
| Modelos (4 etapas) | `glm-4.7` (Spec Planner, Architect, Coder, Repair) |
| Aider | `AIDER_MODEL = openai/glm-4.7` · `AIDER_CHECK_UPDATE=false` (pin aider 0.82.3) |
| Chave | env `ZAI_API_KEY` (**nunca** em arquivo) — prioridade: `ZAI_API_KEY` → `OPENAI_API_KEY` → `DASHSCOPE_API_KEY` → `DS_API_KEY` |
| Web UI | `http://localhost:8001` (sessão tmux `macweb`) |

**Comandos:**

| Comando | O que faz |
|---------|-----------|
| `mac graph` | Pipeline padrão (determinístico + fallback Aider) na pasta atual |
| `mac peça "descrição"` | Gera em **subpasta datada** `peca_AAAAMMDD-HHMMSS[_desc]` e abre o STL (f3d/FreeCAD/xdg-open) |
| `mac aider` | Fluxo Aider-first (modifica `temp_design*.py` existente) |
| `mac web [porta]` | Sobe a Web UI (porta livre em 8001+, padrão `8001`) |
| `oc-mac` | Função do `~/.bashrc` — roda `mac graph` em `~/Projetos/peças/` (peças organizadas) |
| `mac config` / `mac reset` | Ver configuração (sem chaves) / restaurar defaults |

> Detalhes: `multi_agent_cad/config.py` e seção "Z.AI / GLM" do README do projeto (`Projetos/Multi-Agent-CAD/README.md`).

---

### Busca na Web — Brave Search API

Busca na web em tempo real para os agentes de IA (grounding com informação atualizada), usando o índice independente da Brave.

**Recursos:**

| Recurso | Detalhe |
|---|---|
| Plano gratuito | ~US$ 5/mês em créditos (≈ 1.000 buscas) · 50 req/s |
| Chave | env `BRAVE_API_KEY` **ou** arquivo `~/.brave_api_key` (obtenha em [brave.com/search/api](https://brave.com/search/api/)) — o fallback de arquivo é necessário porque o cliente MCP sanitiza o env do subprocesso |
| Servidor MCP | `OpenManus/brave_search_mcp.py` (tools `brave_web_search`, `brave_news_search`, `brave_image_search`, `brave_video_search`, `brave_autosuggest`) |
| Registro | `OpenManus/config/mcp.json` — o agente Manus conecta via stdio (tools `mcp_brave_*`). O `command` precisa apontar para um interpretador com o pacote `mcp` instalado |
| Agente local | `buscar_web()` no `OpenManus/agente_ollama.py` (function calling com Ollama) |

**Teste rápido:**

```bash
export BRAVE_API_KEY=BSA-...
python3 OpenManus/brave_search_mcp.py   # servidor MCP (stdio)
python3 OpenManus/agente_ollama.py "pesquise sobre o 7 de setembro de 1822"
```

> 🔑 Sem a chave configurada, as ferramentas retornam mensagem de erro amigável orientando a criação em https://brave.com/search/api/. Para o MCP, o jeito mais simples é `echo 'BSA-sua-chave' > ~/.brave_api_key` (chmod 600).

---

### Microsoft Office no Linux (Wine)

Executar o Office (Word/Excel/PowerPoint) no Linux via Wine num **prefixo isolado**, sem afetar os demais ambientes do sistema (Docker, Python, Node, Ollama, ComfyUI…).

| Ferramenta | O que faz |
|------------|-----------|
| [`scripts/diagnose_office_linux.sh`](scripts/diagnose_office_linux.sh) | Diagnóstico **somente leitura** (SO, kernel, CPU, RAM, disco, Wine, Winetricks, CUPS, locale, prefixos e instaladores do Office) — nada é instalado ou alterado |
| [`docs/microsoft-office-linux-wine.md`](docs/microsoft-office-linux-wine.md) | Guia completo em 8 etapas: diagnóstico → recomendação → autorização → instalação → configuração → testes → correções → relatório |

> ⚠️ Execute **a partir da raiz do repositório** ou por **caminho absoluto**:
>
> ```bash
> cd /home/flavio   # raiz deste repositório
> ./scripts/diagnose_office_linux.sh
> ```
>
> O script **não depende do diretório** — `bash /caminho/absoluto/scripts/diagnose_office_linux.sh` funciona de qualquer pasta. O erro `Ficheiro ou pasta inexistente` ocorre quando se roda `./scripts/...` fora da raiz do projeto.

---

## Troubleshooting

### `ImportError: openvino not found`

O OpenVINO é um módulo **opcional**. O monolito funciona sem ele — os endpoints retornam `503` com `detail="openvino_not_available"`.

```bash
# Se precisar do OpenVINO:
pip install -e ".[openvino]"
```

### `Qdrant connection refused`

O Qdrant é necessário para RAG. Para desenvolvimento, use SQLite:

```bash
# Desabilita RAG via env var:
export IA_LAB_RAG_ENABLED=false
```

Ou inicie o Qdrant via Docker:

```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### `Redis connection refused`

Redis é opcional. Se não estiver disponível, o cache simplesmente não será usado:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### `ModuleNotFoundError` ao importar módulos do monolito

Certifique-se de que o projeto está instalado em modo editável:

```bash
pip install -e ".[dev]"
```

### Porta 8000 já em uso

```bash
uvicorn api.server:app --reload --port 8001
```

### Testes falhando

```bash
# Verifique se as dependências de desenvolvimento estão instaladas:
pip install -e ".[dev]"

# Execute apenas um módulo específico para isolar o problema:
python3 -m pytest tests/test_education_module.py -v
```

### Erro de permissão no Vite

```bash
# O dashboard React requer Node.js ≥ 18
node --version

# Se não tiver, instale via nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
nvm install 22
```

---

## Contribuição

1. Faça um fork do projeto
2. Instale as dependências de desenvolvimento:
   ```bash
   pip install -e ".[dev]"
   ```
3. Crie uma branch para sua feature:
   ```bash
   git checkout -b feat/minha-feature
   ```
4. Execute os testes para garantir que tudo está funcionando:
   ```bash
   python3 -m pytest tests/ -v
   ```
5. Faça o commit e abra um Pull Request

### Convenções de código

- **Python:** seguir PEP 8 com line-length 100
- **Formatação:** Ruff format + Ruff lint (automático via `ruff format . && ruff check --fix`)
- **Imports:** Ruff (regra I, padrão do projeto)
- **Tipos:** type hints em todas as funções públicas
- **Testes:** pytest com `asyncio_mode = auto`
- **Documentação:** docstrings em português (projeto brasileiro)
- **Frontend:** TypeScript strict + React 19 + Vite

---

## Licença

MIT License — veja o arquivo [LICENSE](LICENSE) para detalhes.
