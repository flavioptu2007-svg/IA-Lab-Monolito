import { useEffect, useState } from "react";
import { api, ProviderInfo } from "../api/client";
import { AlertCircle, Bot, CheckCircle, Globe } from "lucide-react";

const PROVIDER_META: Record<string, { color: string; label: string }> = {
  openai: { color: "#10a37f", label: "OpenAI" },
  claude: { color: "#d97706", label: "Anthropic Claude" },
  gemini: { color: "#4285f4", label: "Google Gemini" },
  groq: { color: "#f97316", label: "Groq" },
  glm: { color: "#06b6d4", label: "GLM" },
  perplexity: { color: "#a855f7", label: "Perplexity" },
  ollama: { color: "#8b5cf6", label: "Ollama" },
  bitnet: { color: "#06b6d4", label: "BitNet" },
};

export function ProvidersPage() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .providers()
      .then(setProviders)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span style={{ marginLeft: 12 }}>Carregando providers...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-content">
        <div
          className="card"
          style={{ textAlign: "center", padding: 40, borderColor: "var(--error)" }}
        >
          <AlertCircle size={48} style={{ color: "var(--error)", marginBottom: 16 }} />
          <h3 style={{ marginBottom: 8 }}>Erro ao carregar providers</h3>
          <p style={{ color: "var(--text-secondary)" }}>{error}</p>
        </div>
      </div>
    );
  }

  const onlineCount = providers.filter((p) => p.available).length;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Providers</h2>
        <p>
          {onlineCount}/{providers.length} providers online
        </p>
      </div>

      <div className="page-content">
        <div className="grid grid-2" style={{ marginBottom: 24 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Total de Providers</span>
              <Globe size={20} style={{ color: "var(--accent)" }} />
            </div>
            <div className="card-value">{providers.length}</div>
          </div>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Online</span>
              <CheckCircle size={20} style={{ color: "var(--success)" }} />
            </div>
            <div className="card-value" style={{ color: "var(--success)" }}>
              {onlineCount}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {providers.map((p) => {
            const meta = PROVIDER_META[p.name.toLowerCase()] || {
              color: "var(--text-muted)",
              label: p.name,
            };
            return (
              <div
                key={p.name}
                className="card"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  padding: "16px 20px",
                  borderLeft: `4px solid ${meta.color}`,
                }}
              >
                <Bot size={24} style={{ color: meta.color, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, marginBottom: 2 }}>{meta.label}</div>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    {p.model || "—"}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  {p.available ? (
                    <span className="status-badge online">
                      <span className="status-dot online" />
                      Online
                    </span>
                  ) : (
                    <span className="status-badge offline">
                      <span className="status-dot offline" />
                      Offline
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
