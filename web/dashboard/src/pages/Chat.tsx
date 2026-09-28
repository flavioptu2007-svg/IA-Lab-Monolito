import { FormEvent, useRef, useState } from "react";
import { api, ChatResponse } from "../api/client";
import { Bot, Send, User, Trash2, Loader2 } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  id: string;
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Olá! Sou o assistente IA-Lab. Como posso ajudar você hoje?",
      id: "welcome",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = { role: "user", content: trimmed, id: crypto.randomUUID() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);
    setStreamingContent("");

    try {
      const res = await api.chatStream({ message: trimmed });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("Stream não disponível");

      const decoder = new TextDecoder();
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (!data || data === "[DONE]") continue;
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                fullText += parsed.content;
                setStreamingContent(fullText);
              } else if (parsed.response) {
                fullText += parsed.response;
                setStreamingContent(fullText);
              }
            } catch {
              fullText += data;
              setStreamingContent(fullText);
            }
          }
        }
      }

      const assistantMsg: Message = {
        role: "assistant",
        content: fullText || "Resposta recebida.",
        id: crypto.randomUUID(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setStreamingContent("");
    } catch (err) {
      const fallback: ChatResponse = await api.chat({ message: trimmed }).catch(() => ({
        response: "Desculpe, ocorreu um erro ao processar sua mensagem.",
        provider: "error",
        model: "",
        elapsed_ms: 0,
      }));
      const assistantMsg: Message = {
        role: "assistant",
        content: fallback.response,
        id: crypto.randomUUID(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } finally {
      setLoading(false);
      setStreamingContent("");
      setTimeout(scrollToBottom, 50);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        role: "assistant",
        content: "Chat limpo. Como posso ajudar?",
        id: "cleared",
      },
    ]);
  };

  return (
    <div className="fade-in">
      <div className="page-header" style={{ paddingBottom: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2>Chat</h2>
            <p>Converse com os providers de IA</p>
          </div>
          <button className="btn btn-ghost" onClick={clearChat} title="Limpar chat">
            <Trash2 size={16} />
            Limpar
          </button>
        </div>
      </div>

      <div className="page-content">
        <div className="card chat-container">
          <div className="chat-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`chat-message ${msg.role}`}>
                <div className={`chat-avatar ${msg.role}`}>
                  {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className="chat-bubble">{msg.content}</div>
              </div>
            ))}
            {streamingContent && (
              <div className="chat-message assistant">
                <div className="chat-avatar assistant">
                  <Bot size={16} />
                </div>
                <div className="chat-bubble">
                  {streamingContent}
                  <span className="spinner" style={{ display: "inline-block", width: 12, height: 12, marginLeft: 8, verticalAlign: "middle" }} />
                </div>
              </div>
            )}
            {loading && !streamingContent && (
              <div className="chat-message assistant">
                <div className="chat-avatar assistant">
                  <Bot size={16} />
                </div>
                <div className="chat-bubble">
                  <div style={{ display: "flex", gap: 6 }}>
                    <div className="spinner" style={{ width: 16, height: 16 }} />
                    <span>Pensando...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {error && (
            <div
              style={{
                padding: "8px 12px",
                marginBottom: 8,
                background: "rgba(239,68,68,0.1)",
                border: "1px solid rgba(239,68,68,0.2)",
                borderRadius: "var(--radius-sm)",
                color: "var(--error)",
                fontSize: "0.85rem",
              }}
            >
              {error}
            </div>
          )}

          <form className="chat-input-area" onSubmit={sendMessage}>
            <input
              className="input"
              placeholder="Digite sua mensagem..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button className="btn btn-primary" type="submit" disabled={loading || !input.trim()}>
              {loading ? <Loader2 size={16} className="spinner" /> : <Send size={16} />}
              Enviar
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
