import { FormEvent, useEffect, useState } from "react";
import { api, OpenVINORagQuery } from "../api/client";
import { Database, Loader2, MessageSquare, Network, Search } from "lucide-react";

export function RAGPage() {
  const [qdrantStatus, setQdrantStatus] = useState<string>("checking");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<OpenVINORagQuery | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Check if Qdrant is reachable via health endpoint
    api
      .health()
      .then(() => setQdrantStatus("connected"))
      .catch(() => setQdrantStatus("disconnected"));
  }, []);

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!question.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await api.openvino.ragQuery(question.trim());
      setResult(res);
    } catch (err: unknown) {
      setResult({
        answer: `Erro: ${err instanceof Error ? err.message : "Falha na consulta"}`,
        sources: [],
        elapsed_ms: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>RAG — Busca Semântica</h2>
        <p>Recuperação aumentada por geração com Qdrant</p>
      </div>

      <div className="page-content">
        {/* Status cards */}
        <div className="grid grid-2" style={{ marginBottom: 24 }}>
          <div className="metric-card">
            <div className="metric-icon" style={{ background: qdrantStatus === "connected" ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)", color: qdrantStatus === "connected" ? "var(--success)" : "var(--error)" }}>
              <Database size={20} />
            </div>
            <div className="metric-label">Qdrant</div>
            <div className="metric-value" style={{ color: qdrantStatus === "connected" ? "var(--success)" : "var(--error)", fontSize: "1rem" }}>
              {qdrantStatus === "checking"
                ? "Verificando..."
                : qdrantStatus === "connected"
                  ? "Conectado"
                  : "Desconectado"}
            </div>
            {qdrantStatus === "connected" && (
              <div className="metric-sub">Vector store pronto</div>
            )}
          </div>

          <div className="metric-card">
            <div className="metric-icon" style={{ background: "rgba(168,85,247,0.1)", color: "#a855f7" }}>
              <Network size={20} />
            </div>
            <div className="metric-label">Vector Store</div>
            <div className="metric-value" style={{ fontSize: "1rem" }}>Qdrant</div>
            <div className="metric-sub">Embeddings + busca por similaridade</div>
          </div>
        </div>

        {/* Info card */}
        <div
          className="card"
          style={{
            marginBottom: 24,
            background: "rgba(59,130,246,0.05)",
            borderColor: "rgba(59,130,246,0.2)",
          }}
        >
          <div className="card-header">
            <span className="card-title">
              <Search size={16} style={{ marginRight: 6, verticalAlign: "middle" }} />
              Consulta RAG
            </span>
          </div>
          <form onSubmit={handleSearch} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <input
              className="input"
              placeholder="Faça uma pergunta sobre os documentos indexados..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="btn btn-primary"
                type="submit"
                disabled={loading || !question.trim()}
              >
                {loading ? <Loader2 size={16} className="spinner" /> : <MessageSquare size={16} />}
                Consultar
              </button>
            </div>
          </form>
        </div>

        {/* Result */}
        {result && (
          <div className="card">
            <div className="card-header">
              <span className="card-title">Resposta</span>
              {result.elapsed_ms > 0 && (
                <span className="metric-sub">{result.elapsed_ms}ms</span>
              )}
            </div>
            <div
              style={{
                padding: 12,
                background: "var(--bg-primary)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.9rem",
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                marginBottom: result.sources.length > 0 ? 16 : 0,
              }}
            >
              {result.answer}
            </div>
            {result.sources.length > 0 && (
              <div>
                <div className="metric-label" style={{ marginBottom: 8 }}>Fontes</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {result.sources.map((s, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "8px 12px",
                        background: "var(--bg-primary)",
                        borderRadius: "var(--radius-sm)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span style={{ fontSize: "0.85rem" }}>{s.title}</span>
                      <span className="metric-sub">{(s.score * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
