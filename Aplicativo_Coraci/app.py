#!/usr/bin/env python3
"""
Coraci Chat — Aplicativo de Chat com IA
========================================
Conecta-se a APIs compatíveis com OpenAI (como Colibrì) para fornecer
uma interface de chat moderna e interativa com persistência SQLite.

Uso:
    python app.py              # Inicia servidor em localhost:5000
    python app.py --port 8080  # Porta personalizada
    python app.py --db :memory:  # Apenas memória (sem persistência)
"""

import argparse
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    stream_with_context,
)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
DB_PATH = str(BASE_DIR / "coraci.db")

DEFAULT_CONFIG = {
    "api_base_url": "http://localhost:8000/v1",
    "api_key": "",
    "model": "glm-5.2-colibri",
    "temperature": 0.7,
    "max_tokens": 4096,
    "theme": "dark",
}

app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "static"),
    static_url_path="/static",
)
app.secret_key = os.urandom(24)

# Cache em memória + lock para thread-safety
conversations: dict[str, dict] = {}
conv_lock = threading.Lock()
config_lock = threading.Lock()
current_config = dict(DEFAULT_CONFIG)


# ---------------------------------------------------------------------------
# Persistência SQLite
# ---------------------------------------------------------------------------


def get_db_path() -> str:
    """Retorna o caminho do banco de dados."""
    return DB_PATH


def init_db(db_path: str | None = None) -> None:
    """Inicializa o banco SQLite e cria as tabelas se não existirem."""
    path = db_path or get_db_path()
    if path == ":memory:":
        return
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


def db_save_conversation(conv: dict) -> None:
    """Salva ou atualiza uma conversa e suas mensagens no SQLite."""
    path = get_db_path()
    if path == ":memory:":
        return
    try:
        with sqlite3.connect(path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO conversations (id, title, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (conv["id"], conv["title"], conv["created_at"], datetime.now().isoformat()),
            )
            # Apaga mensagens antigas e reinsere
            conn.execute("DELETE FROM messages WHERE conv_id = ?", (conv["id"],))
            for msg in conv.get("messages", []):
                conn.execute(
                    "INSERT INTO messages (conv_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (
                        conv["id"],
                        msg["role"],
                        msg["content"],
                        msg.get("timestamp", datetime.now().isoformat()),
                    ),
                )
    except sqlite3.Error as e:
        print(f"[DB] Erro ao salvar conversa {conv.get('id', '?')}: {e}")


def db_delete_conversation(conv_id: str) -> None:
    """Remove uma conversa e suas mensagens do SQLite."""
    path = get_db_path()
    if path == ":memory:":
        return
    try:
        with sqlite3.connect(path) as conn:
            conn.execute("DELETE FROM messages WHERE conv_id = ?", (conv_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    except sqlite3.Error as e:
        print(f"[DB] Erro ao apagar conversa {conv_id}: {e}")


def db_clear_all() -> None:
    """Remove todas as conversas e mensagens do SQLite."""
    path = get_db_path()
    if path == ":memory:":
        return
    try:
        with sqlite3.connect(path) as conn:
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM conversations")
    except sqlite3.Error as e:
        print(f"[DB] Erro ao limpar banco: {e}")


def db_load_all() -> dict[str, dict]:
    """Carrega todas as conversas do SQLite para a memória."""
    path = get_db_path()
    if path == ":memory:":
        return {}
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
        print(f"[DB] Erro ao carregar conversas: {e}")
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_config() -> dict:
    """Carrega configuração do arquivo JSON ou retorna defaults."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return {**DEFAULT_CONFIG, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Persiste configuração no arquivo JSON."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False))


def load_openai_client():
    """Cria um cliente da API OpenAI compatível com a configuração atual."""
    from openai import OpenAI

    base = current_config.get("api_base_url", DEFAULT_CONFIG["api_base_url"]).rstrip("/")
    key = current_config.get("api_key") or "no-key"
    return OpenAI(base_url=base, api_key=key)


def stream_chat(messages, model=None, temperature=None, max_tokens=None):
    """Faz o streaming da resposta da API e renderiza os eventos SSE."""
    import openai

    client = load_openai_client()
    try:
        response = client.chat.completions.create(
            model=model or current_config.get("model", DEFAULT_CONFIG["model"]),
            messages=messages,
            temperature=temperature
            or current_config.get("temperature", DEFAULT_CONFIG["temperature"]),
            max_tokens=max_tokens or current_config.get("max_tokens", DEFAULT_CONFIG["max_tokens"]),
            stream=True,
        )
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield f"data: {json.dumps({'type': 'content', 'text': delta.content})}\n\n"
                # Se o modelo enviar reasoning/thinking
                if getattr(delta, "reasoning_content", None):
                    yield f"data: {json.dumps({'type': 'reasoning', 'text': delta.reasoning_content})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except openai.APIConnectionError as e:
        yield f"data: {json.dumps({'type': 'error', 'text': f'❌ Erro de conexão: {e}'})}\n\n"
    except openai.RateLimitError as e:
        yield f"data: {json.dumps({'type': 'error', 'text': f'⏳ Limite de taxa: {e}'})}\n\n"
    except openai.APIStatusError as e:
        yield f"data: {json.dumps({'type': 'error', 'text': f'⚠️ Erro da API ({e.status_code}): {e}'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'text': f'🚫 Erro inesperado: {e}'})}\n\n"


# ---------------------------------------------------------------------------
# Rotas — Páginas
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Rotas — API de Chat
# ---------------------------------------------------------------------------


@app.route("/api/chat", methods=["POST"])
def chat():
    """Envia mensagem e recebe resposta em streaming (SSE)."""
    data = request.get_json(force=True)
    conv_id = data.get("conversation_id")
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Mensagem vazia"}), 400

    with conv_lock:
        # Cria nova conversa se necessário
        if not conv_id or conv_id not in conversations:
            conv_id = str(uuid.uuid4())
            conversations[conv_id] = {
                "id": conv_id,
                "title": message[:60] + ("…" if len(message) > 60 else ""),
                "messages": [],
                "created_at": datetime.now().isoformat(),
            }

        conv = conversations[conv_id]

        # Adiciona mensagem do usuário
        user_msg = {"role": "user", "content": message, "timestamp": datetime.now().isoformat()}
        conv["messages"].append(user_msg)

        # Abrevia o título se for a primeira mensagem
        if len(conv["messages"]) == 1:
            conv["title"] = message[:60] + ("…" if len(message) > 60 else "")

        # Salva imediatamente no SQLite
        db_save_conversation(conv)

    # Prepara histórico para a API (pode limitar para caber no contexto)
    api_messages = [{"role": m["role"], "content": m["content"]} for m in conv["messages"]]

    def generate():
        # Envia o ID da conversa primeiro
        yield f"data: {json.dumps({'type': 'conv_id', 'id': conv_id})}\n\n"

        full_response = ""
        for event in stream_chat(api_messages):
            yield event
            # Acumula para salvar no histórico
            data_str = event.removeprefix("data: ").strip()
            if data_str:
                try:
                    parsed = json.loads(data_str)
                    if parsed.get("type") == "content":
                        full_response += parsed.get("text", "")
                except json.JSONDecodeError:
                    pass

        # Salva resposta do assistente no histórico
        if full_response:
            with conv_lock:
                if conv_id in conversations:
                    conversations[conv_id]["messages"].append(
                        {
                            "role": "assistant",
                            "content": full_response,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    # Persiste no SQLite
                    db_save_conversation(conversations[conv_id])

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    """Lista todas as conversas."""
    with conv_lock:
        items = []
        for conv in conversations.values():
            items.append(
                {
                    "id": conv["id"],
                    "title": conv["title"],
                    "created_at": conv["created_at"],
                    "message_count": len([m for m in conv["messages"] if m["role"] == "user"]),
                }
            )
        items.sort(key=lambda x: x["created_at"], reverse=True)
    return jsonify(items)


@app.route("/api/conversations/<conv_id>", methods=["GET"])
def get_conversation(conv_id):
    """Retorna uma conversa específica."""
    with conv_lock:
        conv = conversations.get(conv_id)
        if not conv:
            return jsonify({"error": "Conversa não encontrada"}), 404
        return jsonify(
            {
                "id": conv["id"],
                "title": conv["title"],
                "messages": conv["messages"],
                "created_at": conv["created_at"],
            }
        )


@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    """Apaga uma conversa."""
    with conv_lock:
        if conv_id in conversations:
            del conversations[conv_id]
        db_delete_conversation(conv_id)
    return jsonify({"status": "ok"})


@app.route("/api/conversations", methods=["DELETE"])
def clear_conversations():
    """Apaga todas as conversas."""
    with conv_lock:
        conversations.clear()
        db_clear_all()
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Rotas — Configuração
# ---------------------------------------------------------------------------


@app.route("/api/config", methods=["GET"])
def get_config():
    """Retorna a configuração atual (sem expor a API key completa)."""
    with config_lock:
        cfg = dict(current_config)
        if cfg.get("api_key"):
            cfg["api_key"] = cfg["api_key"][:4] + "…" if len(cfg["api_key"]) > 4 else "…"
    return jsonify(cfg)


@app.route("/api/config", methods=["POST"])
def update_config():
    """Atualiza a configuração."""
    data = request.get_json(force=True)
    allowed_keys = {"api_base_url", "api_key", "model", "temperature", "max_tokens", "theme"}
    with config_lock:
        for key, value in data.items():
            if key in allowed_keys:
                current_config[key] = value
        save_config(current_config)
    return jsonify({"status": "ok"})


@app.route("/api/config/test", methods=["POST"])
def test_connection():
    """Testa a conexão com a API listando os modelos disponíveis."""
    import openai

    data = request.get_json(force=True)
    base = data.get("api_base_url", current_config["api_base_url"]).rstrip("/")
    key = data.get("api_key") or current_config.get("api_key") or "no-key"
    try:
        client = openai.OpenAI(base_url=base, api_key=key)
        models = client.models.list()
        model_list = [m.id for m in models]
        return jsonify({"status": "ok", "models": model_list})
    except openai.APIConnectionError:
        return jsonify(
            {"status": "error", "message": "❌ Não foi possível conectar ao servidor"}
        ), 400
    except openai.AuthenticationError:
        return jsonify({"status": "error", "message": "❌ Chave de API inválida"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"❌ {e}"}), 400


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Coraci Chat — App de Chat com IA")
    parser.add_argument("--port", type=int, default=5000, help="Porta do servidor (default: 5000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--debug", action="store_true", help="Modo debug")
    parser.add_argument(
        "--db", type=str, default=None, help="Caminho do banco SQLite (default: coraci.db)"
    )
    args = parser.parse_args()

    global DB_PATH, conversations

    if args.db:
        DB_PATH = args.db

    # Inicializa o banco de dados
    init_db()
    print(f"[DB] Banco de dados: {DB_PATH}")

    # Carrega conversas salvas do SQLite
    saved = db_load_all()
    if saved:
        conversations = saved
        print(f"[DB] {len(saved)} conversas carregadas do banco")
    else:
        conversations = {}
        print("[DB] Nenhuma conversa salva encontrada")

    # Carrega configuração salva
    global current_config
    current_config = load_config()

    print(f"""
╔══════════════════════════════════════════════╗
║           🤖 Coraci Chat                     ║
║                                              ║
║  🌐 http://{args.host}:{args.port}                    ║
║  ⚙️  API: {current_config.get("api_base_url", "?")}  ║
║  📦 Modelo: {current_config.get("model", "?")}       ║
║  💾 DB: {DB_PATH}  ║
║                                              ║
╚══════════════════════════════════════════════╝
    """)

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
