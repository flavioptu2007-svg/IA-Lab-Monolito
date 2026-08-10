# IA-Lab Unified

**FastAPI Monolith** that unifies 5 projects into a single ecosystem of AI, audio, RAG, education, and local inference.

```
📦 ia-lab-unified v2.0.0
├── 🧠 8 AI providers (OpenAI, Claude, Gemini, Groq, GLM, Perplexity, Ollama, BitNet)
├── 🎙️ Complete audio pipeline (STT, TTS, VAD, effects, virtual microphone)
├── 📚 RAG with Qdrant (semantic search + augmented context)
├── 💬 SSE Chat with history (migrated from Coraci)
├── 🏫 Education module (lesson plans, BNCC, assessments, calendar)
├── 🔧 Optional OpenVINO (Intel local inference)
├── 🔢 BitNet (ultra-efficient 1-bit LLM on CPU)
├── 🧪 487 tests — 100% passing
├── 📡 58+ REST endpoints
└── 🐳 14 orchestrated Docker services
```

---

## 🚀 5-Minute Quick Start

```bash
# 1. Clone and install
pip install -e ".[dev]"

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your API keys (at least one)

# 3. Start the server
uvicorn api.server:app --reload --port 8000

# 4. Test that it's working
curl http://localhost:8000/api/health

# 5. Open the dashboard
cd web/dashboard && npm install && npm run dev
# Visit http://localhost:5173
```

### Essential Commands

| What to do | Command |
|-------------|---------|
| Run tests | `python3 -m pytest tests/ -v` |
| Test chat | `curl -X POST http://localhost:8000/api/chat -H 'Content-Type: application/json' -d '{"prompt":"Hello"}'` |
| View providers | `curl http://localhost:8000/api/providers` |
| View API docs | Open `http://localhost:8000/docs` |
| Education only | `pip install -e ".[education]"` |
| Run with Docker | `docker compose up -d` |

---

## Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running](#running)
- [Docker Compose](#docker-compose)
- [API Endpoints](#api-endpoints)
- [Tests](#tests)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Architecture

### Application Lifecycle

Modern FastAPI uses the **lifespan** pattern (replacing the deprecated `@app.on_event`):

```
FastAPI(lifespan=lifespan)
    │
    ├── Startup ──────────────────────────────────────┐
    │   • init_db()         — SQLite Coraci           │
    │   • db_load_all()     — Load conversations      │
    │   • load_config()     — Load configurations     │
    │   └─ logger.info()    — Initialization log      │
    │                                                 │
    ├── Application running (yield)                   │
    │   • 58+ REST endpoints                          │
    │   • 8 AI providers                              │
    │   • SSE streaming, audio, RAG, education        │
    │                                                 │
    └── Shutdown ─────────────────────────────────────┘
        • VectorStore.close()     — Qdrant socket
        • close_db()              — SQLite WAL checkpoint
        • AudioEngine.close()     — PipeWire/PulseAudio
        • AIService.close()       — Providers (future)
        └─ logger.info()          — Shutdown log
```

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Monolith (lifespan)                      │
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
│  (RAG)   │ │ (Coraci) │ │ PulseAudio   │ │ (Education)  │ │(Optional)│
└──────────┘ └──────────┘ └──────────────┘ └──────────────┘ └──────────┘
```

### Core Modules (`src/core/`)

| Module | Responsibility |
|--------|----------------|
| **`src/core/lifespan.py`** | Startup/shutdown context manager — init DB, load data, close connections |
| **`src/core/routers.py`** | `register_routers(app)` — centralizes all `include_router` calls |
| **`src/core/config.py`** | `UnifiedSettings` — unified configuration for all modules |

### Centralized Routers

All routers are registered in a single place — `src/core/routers.py`:

```python
def register_routers(app: FastAPI) -> None:
    app.include_router(chat_v2_router)
    app.include_router(openvino_router)
    app.include_router(education_router)
    # Add new routers here
```

### Graceful Shutdown

On API shutdown, the lifespan automatically releases:

| Resource | What it closes |
|----------|----------------|
| **Qdrant** (`VectorStore`) | Persistent client gRPC/REST socket |
| **SQLite** (`close_db()`) | WAL checkpoint → `.db-wal`/`.db-shm` cleaned up |
| **AudioEngine** | PipeWire/PulseAudio devices (if initialized) |
| **AIService** | Provider class cache (ready for future) |

### Unified Projects

| Original Project | Monolith Module | Status |
|-----------------|----------------|--------|
| **IA-Lab Enterprise** (root) | Core: API, providers, audio, RAG | ✅ Native |
| **Coraci** (Flask) | `src/api/v2/chat_coraci.py` | ✅ Migrated to FastAPI SSE |
| **BitNet** (1-bit LLM) | `ai/providers/bitnet.py` | ✅ 8th provider |
| **OpenVINO** (Intel AI Lab) | `src/openvino/` (optional) | ✅ Optional module |
| **HistóriaIA** (Education) | `src/education/` | ✅ Integrated module |

---

## Installation

### Prerequisites

- Python ≥ 3.11
- Redis (optional, for caching)
- Qdrant (optional, for RAG)

### Basic installation (core)

```bash
pip install -e .
```

### With optional groups

```bash
# Core + development tools
pip install -e ".[dev]"

# Core + STT (SpeechBrain + PyTorch)
pip install -e ".[stt]"

# Core + Advanced TTS (Edge-TTS)
pip install -e ".[tts]"

# Core + OpenVINO (Intel inference)
pip install -e ".[openvino]"

# Core + LangChain + Advanced RAG
pip install -e ".[langchain]"

# Core + BitNet (1-bit LLM)
pip install -e ".[bitnet]"

# Core + HistóriaIA (PostgreSQL + auth)
pip install -e ".[education]"

# Everything (except OpenVINO which is heavy)
pip install -e ".[all]"
```

### Full development

```bash
pip install -e ".[dev,stt,tts,langchain,bitnet,education]"
```

---

## Configuration

Copy the example file and configure environment variables:

```bash
cp .env.example .env
```

> 📄 The complete file with **all variables** is at [`.env.example`](.env.example).

### Main Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IA_LAB_PRIMARY_PROVIDER` | `openai` | Default provider |
| `IA_LAB_OPENAI_API_KEY` | — | OpenAI API key |
| `IA_LAB_CLAUDE_API_KEY` | — | Anthropic Claude API key |
| `IA_LAB_GEMINI_API_KEY` | — | Google Gemini API key |
| `IA_LAB_GROQ_API_KEY` | — | Groq API key |
| `IA_LAB_GLM_API_KEY` | — | GLM (Zhipu) API key |
| `IA_LAB_PERPLEXITY_API_KEY` | — | Perplexity API key |
| `IA_LAB_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama URL |
| `IA_LAB_BITNET_BASE_URL` | `http://localhost:8080/v1` | BitNet URL |
| `IA_LAB_QDRANT_HOST` | `localhost` | Qdrant host |
| `IA_LAB_LOG_LEVEL` | `INFO` | Log level |

> 💡 **Tip:** You only need **one** API key to get started. Set `IA_LAB_OPENAI_API_KEY` or use local Ollama (zero configuration).

---

## Running

### API Server

```bash
# Development (with reload)
uvicorn api.server:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

- Interactive documentation: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

### Web Dashboard

```bash
cd web/dashboard
npm install
npm run dev
# Visit http://localhost:5173
```

Vite automatically proxies `/api/*` to `localhost:8000`.

### Audio Demo

```bash
python3 demo_audio.py           # Full demo
python3 demo_audio.py --quick   # Signal processing only
```

---

## Docker Compose

The complete ecosystem can run via Docker Compose with selective profiles:

### Core only (always active)

```bash
docker compose up -d
# Starts: api, coraci, redis, qdrant
```

### Core + BitNet (1-bit LLM)

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

### Everything

```bash
docker compose --profile all up -d
```

### Services

| Service | Port | Profile | Description |
|---------|:----:|:-------:|-------------|
| **api** | `8000` | always | FastAPI Monolith |
| **coraci** | `5000` | always | Flask Chat (legacy) |
| **redis** | `6379` | always | Cache + sessions |
| **qdrant** | `6333` | always | Vector database (RAG) |
| **bitnet** | `8080` | `llm, all` | 1-bit LLM |
| **openvino-dashboard** | `8501` | `openvino, all` | Streamlit dashboard |
| **openvino-flask** | `5001` | `openvino, all` | Flask dashboard |
| **vad** | — | `audio, all` | Continuous listening |
| **batch** | — | `batch, all` | Batch processing |
| **docs** | `8002` | `dev, all` | MkDocs |
| **historiaia-db** | `5432` | `historiaia, all` | PostgreSQL |
| **historiaia-app** | `8001` | `historiaia, all` | FastAPI HistóriaIA |
| **test** | — | `test` | Test suite |

---

## API Endpoints

### v1 — Chat, Audio & System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check (Qdrant, Ollama) |
| `GET` | `/api/providers` | List configured providers |
| `GET` | `/api/agents` | List specialized agents |
| `POST` | `/api/chat` | AI Chat (intelligent routing) |
| `GET` | `/api/history` | Conversation history |
| `DELETE` | `/api/history` | Clear history |
| `GET` | `/api/metrics` | Prometheus metrics |
| `GET` | `/api/config` | System configuration |
| `GET` | `/api/audio/status` | Audio module status |
| `GET` | `/api/audio/devices` | Audio devices |
| `POST` | `/api/audio/record` | Record audio |
| `POST` | `/api/audio/stt` | Speech-to-text |
| `POST` | `/api/audio/tts` | Text-to-speech |
| `POST` | `/api/audio/effects` | Process audio |
| `POST` | `/api/audio/mic/create` | Create virtual microphone |
| `POST` | `/api/audio/mic/remove` | Remove virtual microphone |

### v2 — SSE Chat (Coraci)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v2/chat` | SSE streaming chat |
| `GET` | `/api/v2/conversations` | List conversations |
| `GET` | `/api/v2/conversations/{id}` | Get conversation |
| `DELETE` | `/api/v2/conversations/{id}` | Delete conversation |
| `DELETE` | `/api/v2/conversations` | Clear all conversations |
| `GET` | `/api/v2/config` | Get configuration |
| `POST` | `/api/v2/config` | Update configuration |
| `POST` | `/api/v2/config/test` | Test connection |

### v2 — OpenVINO (optional)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v2/openvino/health` | Health check |
| `POST` | `/api/v2/openvino/generate` | Text generation |
| `POST` | `/api/v2/openvino/transcribe` | Whisper transcription |
| `POST` | `/api/v2/openvino/rag/query` | RAG query |
| `GET` | `/api/v2/openvino/models` | List models |

> **Note:** All OpenVINO endpoints return `503` with `detail="openvino_not_available"` when OpenVINO is not installed.

### v2 — Education (HistóriaIA)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v2/education/health` | Health check |
| `GET` | `/api/v2/education/bncc/skills` | List BNCC skills |
| `GET` | `/api/v2/education/bncc/competences` | List competences |
| `POST` | `/api/v2/education/lesson-plans` | Create lesson plan |
| `GET` | `/api/v2/education/lesson-plans` | List lesson plans |
| `GET` | `/api/v2/education/lesson-plans/{id}` | Get lesson plan |
| `PATCH` | `/api/v2/education/lesson-plans/{id}` | Update lesson plan |
| `DELETE` | `/api/v2/education/lesson-plans/{id}` | Delete lesson plan |
| `POST` | `/api/v2/education/activities` | Create activity |
| `GET` | `/api/v2/education/activities` | List activities |
| `GET` | `/api/v2/education/activities/{id}` | Get activity |
| `PATCH` | `/api/v2/education/activities/{id}` | Update activity |
| `DELETE` | `/api/v2/education/activities/{id}` | Delete activity |
| `POST` | `/api/v2/education/evaluations` | Create evaluation |
| `GET` | `/api/v2/education/evaluations` | List evaluations |
| `GET` | `/api/v2/education/evaluations/{id}` | Get evaluation |
| `PATCH` | `/api/v2/education/evaluations/{id}` | Update evaluation |
| `DELETE` | `/api/v2/education/evaluations/{id}` | Delete evaluation |
| `POST` | `/api/v2/education/calendar` | Create event |
| `GET` | `/api/v2/education/calendar` | List events |
| `DELETE` | `/api/v2/education/calendar/{id}` | Delete event |

---

## Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Specific tests
python3 -m pytest tests/test_openvino_module.py -v
python3 -m pytest tests/test_education_module.py -v
python3 -m pytest tests/test_bitnet_provider.py -v
python3 -m pytest tests/test_api_v2_chat.py -v
python3 -m pytest tests/test_e2e_monolito.py -v  # E2E tests covering 57+ routes

# With coverage
python3 -m pytest tests/ --cov=ai,api,src --cov-report=term-missing

# Docker tests
docker compose --profile test up
```

### Current coverage: **487 tests — 100% passing**

| Module | Tests | Status |
|--------|:-----:|:------:|
| Core (IA, Providers, Settings) | 353+ | ✅ |
| Coraci SSE Chat (v2) | 15 | ✅ |
| BitNet Provider | 12 | ✅ |
| OpenVINO Module | 25 (19 + 6 success-path) | ✅ |
| Education Module | 47 | ✅ |
| E2E Monolith | 35 (57+ routes) | ✅ |

---

## Project Structure

```
/home/flavio/
├── src/                          # Monolith unified modules
│   ├── __init__.py               # Package marker v2.0.0
│   ├── core/
│   │   ├── __init__.py
│   │   ├── lifespan.py           # 🔄 Startup/shutdown (init DB → close connections)
│   │   ├── routers.py            # 🔗 register_routers(app) — centralized includes
│   │   └── config.py             # UnifiedSettings
│   ├── api/
│   │   └── v2/
│   │       ├── chat_coraci.py    # SSE Chat (Coraci) — streaming + history
│   │       ├── openvino.py       # OpenVINO endpoints (optional, 503 guard)
│   │       └── education.py      # Education endpoints (BNCC, plans, activities)
│   ├── education/                # HistóriaIA module
│   │   ├── __init__.py
│   │   ├── enums.py              # Academic enums + BNCC (30+ skills)
│   │   ├── schemas.py            # 15 Pydantic schemas
│   │   └── services.py           # EducationStore (CRUD) + BNCC skills
│   └── openvino/                 # OpenVINO module (optional)
│       ├── __init__.py
│       └── pipelines.py          # OpenVINOPipeline, AudioRagPipeline
├── ai/                           # Core AI (legacy, actively used)
│   ├── providers/
│   │   ├── base.py               # BaseProvider + TaskType
│   │   ├── providers.py          # OpenAI, Claude, Gemini, Groq, GLM, Perplexity
│   │   ├── ollama.py             # OllamaProvider
│   │   └── bitnet.py             # BitNetProvider (8th, 1-bit LLM)
│   ├── service.py                # AIService — provider orchestrator
│   ├── settings.py               # Settings (SecretStr, ProviderName Literal)
│   ├── classifier.py             # TaskClassifier
│   ├── memory/store.py           # VectorStore (Qdrant — singleton + close())
│   ├── audio/                    # Engine, STT, TTS, VAD, effects
│   └── telemetry.py              # Prometheus metrics
├── api/
│   └── server.py                 # FastAPI app (lifespan + register_routers)
├── web/
│   └── dashboard/                # 🆕 React + Vite + TypeScript Dashboard
│       ├── src/
│       │   ├── api/client.ts     # Typed API client (57+ endpoints)
│       │   ├── pages/            # 11 pages (Landing, Dashboard, Chat, Providers, etc.)
│       │   ├── components/       # Sidebar navigation
│       │   └── styles/           # Complete dark theme
│       ├── vite.config.ts        # Proxy /api → localhost:8000
│       └── package.json          # React 19, lucide-react, recharts
├── tests/                        # 487 tests
│   ├── test_service.py
│   ├── test_bitnet_provider.py
│   ├── test_api_v2_chat.py
│   ├── test_openvino_module.py
│   ├── test_education_module.py
│   └── test_e2e_monolito.py      # 🆕 35 E2E tests (57 routes)
├── Aplicativo_Coraci/            # Flask app (kept for compatibility)
├── AI/                           # Original source projects
│   ├── BitNet/
│   ├── openvino/
│   └── historiaia/
├── docker-compose.yml            # 14 services with profiles
├── pyproject.toml                # Consolidated dependencies (8 groups)
└── .env.example                  # 50+ documented variables
```

---

## Troubleshooting

### `ImportError: openvino not found`

OpenVINO is an **optional** module. The monolith works without it — endpoints return `503` with `detail="openvino_not_available"`.

```bash
# If you need OpenVINO:
pip install -e ".[openvino]"
```

### `Qdrant connection refused`

Qdrant is required for RAG. For development, use SQLite:

```bash
# Disable RAG via env var:
export IA_LAB_RAG_ENABLED=false
```

Or start Qdrant via Docker:

```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### `Redis connection refused`

Redis is optional. If unavailable, caching simply won't be used:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### `ModuleNotFoundError` when importing monolith modules

Make sure the project is installed in editable mode:

```bash
pip install -e ".[dev]"
```

### Port 8000 already in use

```bash
uvicorn api.server:app --reload --port 8001
```

### Tests failing

```bash
# Verify development dependencies are installed:
pip install -e ".[dev]"

# Run only a specific module to isolate the issue:
python3 -m pytest tests/test_education_module.py -v
```

### Vite permission error

```bash
# The React dashboard requires Node.js ≥ 18
node --version

# If missing, install via nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
nvm install 22
```

---

## Contributing

1. Fork the project
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Create a branch for your feature:
   ```bash
   git checkout -b feat/my-feature
   ```
4. Run tests to make sure everything is working:
   ```bash
   python3 -m pytest tests/ -v
   ```
5. Commit and open a Pull Request

### Code Conventions

- **Python:** Follow PEP 8 with line-length 100
- **Formatting:** Ruff format + Ruff lint (automatic via `ruff format . && ruff check --fix`)
- **Imports:** Ruff (rule I, project default)
- **Types:** Type hints on all public functions
- **Tests:** pytest with `asyncio_mode = auto`
- **Documentation:** Docstrings in English for this version
- **Frontend:** TypeScript strict + React 19 + Vite

### Grok Skills

This project uses Grok CLI skills for auxiliary tasks:

```bash
# List available skills for the project
grok -p "list available skills"

# Use Grok for project analysis
grok -p "analyze the project structure and suggest improvements"
```

---

## License

MIT License — see the [LICENSE](LICENSE) file for details.
