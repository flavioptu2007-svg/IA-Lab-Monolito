"""Chat com SSE Streaming — migrado do Coraci (Flask) para FastAPI.

Endpoints:
- POST /api/v2/chat — Chat com SSE streaming
- GET  /api/v2/conversations — Listar conversas
- GET  /api/v2/conversations/{id} — Obter conversa
- DEL  /api/v2/conversations/{id} — Apagar conversa
- DEL  /api/v2/conversations — Limpar todas
- GET  /api/v2/config — Obter configuração
- POST /api/v2/config — Atualizar configuração
- POST /api/v2/config/test — Testar conexão com provider
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Router ────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/v2", tags=["chat"])

# ── Models Pydantic ───────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    message_count: int


class ConversationDetail(BaseModel):
    id: str
    title: str
    messages: list[dict]
    created_at: str


class ConfigUpdate(BaseModel):
    api_base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    theme: str | None = None


class TestConnectionRequest(BaseModel):
    api_base_url: str | None = None
    api_key: str | None = None


# ── Database ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = str(BASE_DIR / "coraci.db")
CONFIG_PATH = str(BASE_DIR / "Aplicativo_Coraci" / "config.json")

DEFAULT_CONFIG: dict[str, Any] = {
    "api_base_url": "http://localhost:8000/v1",
    "api_key": "",
    "model": "glm-5.2-colibri",
    "temperature": 0.7,
    "max_tokens": 4096,
    "theme": "dark",
}


def get_db_path() -> str:
    return DB_PATH


def init_db() -> None:
    """Inicializa o banco SQLite."""
    path = get_db_path()
    try:
        with sqlite3.connect(path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conv_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conv_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conv_id);
            """)
    except sqlite3.Error as e:
        print(f"[DB] Init error: {e}")


def db_save_conversation(conv: dict) -> None:
    path = get_db_path()
    try:
        with sqlite3.connect(path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO conversations (id, title, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (conv["id"], conv["title"], conv["created_at"], datetime.now(UTC).isoformat()),
            )
            conn.execute("DELETE FROM messages WHERE conv_id = ?", (conv["id"],))
            for msg in conv.get("messages", []):
                conn.execute(
                    "INSERT INTO messages (conv_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (
                        conv["id"],
                        msg["role"],
                        msg["content"],
                        msg.get("timestamp", datetime.now(UTC).isoformat()),
                    ),
                )
    except sqlite3.Error as e:
        print(f"[DB] Save error: {e}")


def db_delete_conversation(conv_id: str) -> None:
    path = get_db_path()
    try:
        with sqlite3.connect(path) as conn:
            conn.execute("DELETE FROM messages WHERE conv_id = ?", (conv_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    except sqlite3.Error as e:
        print(f"[DB] Delete error: {e}")


def db_clear_all() -> None:
    path = get_db_path()
    try:
        with sqlite3.connect(path) as conn:
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM conversations")
    except sqlite3.Error as e:
        print(f"[DB] Clear error: {e}")


def db_load_all() -> dict[str, dict]:
    path = get_db_path()
    result: dict[str, dict] = {}
    try:
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, title, created_at FROM conversations ORDER BY created_at DESC"
            ).fetchall()
            for row in rows:
                conv_id = row["id"]
                msg_rows = conn.execute(
                    "SELECT role, content, timestamp FROM messages WHERE conv_id = ? ORDER BY id ASC",
                    (conv_id,),
                ).fetchall()
                messages = [
                    {"role": m["role"], "content": m["content"], "timestamp": m["timestamp"]}
                    for m in msg_rows
                ]
                result[conv_id] = {
                    "id": conv_id,
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "messages": messages,
                }
    except sqlite3.Error as e:
        print(f"[DB] Load error: {e}")
    return result


# ── Config ────────────────────────────────────────────────────────────────


def close_db() -> None:
    """Fecha conexões com o banco SQLite.

    Chamado no shutdown da aplicação para garantir que
    todas as transações pendentes sejam commitadas e
    os arquivos .db-wal/.db-shm sejam limpos.
    """
    # Força checkpoint WAL via conexão temporária
    path = get_db_path()
    try:
        with sqlite3.connect(path) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        logger.info("Coraci DB: checkpoint WAL executado")
    except sqlite3.Error as exc:
        logger.warning("Coraci DB: erro no checkpoint WAL: %s", exc)


def load_config() -> dict:
    config_file = Path(CONFIG_PATH)
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text())
            return {**DEFAULT_CONFIG, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    config_file = Path(CONFIG_PATH)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False))


# Cache em memória
_conversations: dict[str, dict] = {}
_config = dict(DEFAULT_CONFIG)


# ── Helpers ───────────────────────────────────────────────────────────────


def _sse_event(data: dict) -> str:
    """Formata um evento SSE."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_chat_openai(
    messages: list[dict],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """Faz streaming da resposta via OpenAI-compatible API (assíncrono)."""
    from openai import AsyncOpenAI

    cfg = _config
    base = cfg.get("api_base_url", DEFAULT_CONFIG["api_base_url"]).rstrip("/")
    key = cfg.get("api_key") or "no-key"

    client = AsyncOpenAI(base_url=base, api_key=key)
    try:
        response = await client.chat.completions.create(
            model=model or cfg.get("model", DEFAULT_CONFIG["model"]),
            messages=messages,
            temperature=temperature or cfg.get("temperature", DEFAULT_CONFIG["temperature"]),
            max_tokens=max_tokens or cfg.get("max_tokens", DEFAULT_CONFIG["max_tokens"]),
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield _sse_event({"type": "content", "text": delta.content})
                if getattr(delta, "reasoning_content", None):
                    yield _sse_event({"type": "reasoning", "text": delta.reasoning_content})
        yield _sse_event({"type": "done"})
    except Exception as e:
        yield _sse_event({"type": "error", "text": str(e)})


# ── Endpoints ─────────────────────────────────────────────────────────────

# Nota: O startup (init_db, load_data) foi movido para
# src/core/lifespan.py para substituir o on_event deprecado.


@router.post("/chat")
async def chat_sse(request: ChatRequest):
    """Chat com SSE streaming. Retorna eventos:
    - conv_id: ID da conversa
    - content: texto gerado
    - reasoning: pensamento do modelo (se disponível)
    - error: mensagem de erro
    - done: fim da transmissão
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    conv_id = request.conversation_id
    message = request.message.strip()

    # Cria/obtém conversa
    if not conv_id or conv_id not in _conversations:
        conv_id = str(uuid.uuid4())
        _conversations[conv_id] = {
            "id": conv_id,
            "title": message[:60] + ("…" if len(message) > 60 else ""),
            "messages": [],
            "created_at": datetime.now(UTC).isoformat(),
        }

    conv = _conversations[conv_id]
    user_msg = {"role": "user", "content": message, "timestamp": datetime.now(UTC).isoformat()}
    conv["messages"].append(user_msg)

    if len(conv["messages"]) == 1:
        conv["title"] = message[:60] + ("…" if len(message) > 60 else "")

    db_save_conversation(conv)

    api_messages = [{"role": m["role"], "content": m["content"]} for m in conv["messages"]]

    async def event_generator():
        # Envia o ID da conversa primeiro
        yield _sse_event({"type": "conv_id", "id": conv_id})

        full_response = ""
        async for event in _stream_chat_openai(
            api_messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            yield event
            data_str = event.removeprefix("data: ").strip()
            if data_str:
                try:
                    parsed = json.loads(data_str)
                    if parsed.get("type") == "content":
                        full_response += parsed.get("text", "")
                except json.JSONDecodeError:
                    pass

        # Salva resposta no histórico
        if full_response and conv_id in _conversations:
            _conversations[conv_id]["messages"].append(
                {
                    "role": "assistant",
                    "content": full_response,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            db_save_conversation(_conversations[conv_id])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/conversations")
async def list_conversations():
    """Lista todas as conversas."""
    items = []
    for conv in _conversations.values():
        items.append(
            ConversationSummary(
                id=conv["id"],
                title=conv["title"],
                created_at=conv["created_at"],
                message_count=len([m for m in conv["messages"] if m["role"] == "user"]),
            )
        )
    items.sort(key=lambda x: x.created_at, reverse=True)
    return items


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """Retorna uma conversa específica."""
    conv = _conversations.get(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return ConversationDetail(
        id=conv["id"], title=conv["title"], messages=conv["messages"], created_at=conv["created_at"]
    )


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Apaga uma conversa."""
    if conv_id in _conversations:
        del _conversations[conv_id]
    db_delete_conversation(conv_id)
    return {"status": "ok"}


@router.delete("/conversations")
async def clear_conversations():
    """Apaga todas as conversas."""
    _conversations.clear()
    db_clear_all()
    return {"status": "ok"}


@router.get("/config")
async def get_config():
    """Retorna a configuração atual (sem expor API key completa)."""
    cfg = dict(_config)
    if cfg.get("api_key"):
        key = cfg["api_key"]
        cfg["api_key"] = key[:4] + "…" if len(key) > 4 else "…"
    return cfg


@router.post("/config")
async def update_config(update: ConfigUpdate):
    """Atualiza a configuração."""
    allowed = {"api_base_url", "api_key", "model", "temperature", "max_tokens", "theme"}
    data = update.model_dump(exclude_none=True)
    for key, value in data.items():
        if key in allowed:
            _config[key] = value
    save_config(_config)
    return {"status": "ok"}


@router.post("/config/test")
async def test_connection(req: TestConnectionRequest):
    """Testa a conexão com a API listando modelos."""
    from openai import OpenAI

    base = (req.api_base_url or _config.get("api_base_url", "")).rstrip("/")
    key = req.api_key or _config.get("api_key") or "no-key"

    try:
        client = OpenAI(base_url=base, api_key=key)
        models = client.models.list()
        model_list = [m.id for m in models]
        return {"status": "ok", "models": model_list}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
