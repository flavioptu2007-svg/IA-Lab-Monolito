import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import { Cpu, Info, Loader2 } from "lucide-react";

export function BitNetPage() {
  const [prompt, setPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<{ status: string; model: string; available: boolean } | null>(null);

  useEffect(() => {
    api
      .providers()
      .then((providers) => {
        const bitnet = providers.find((p) => p.name.toLowerCase() === "bitnet");
        setHealth({
          status: bitnet?.available ? "available" : "unavailable",
          model: bitnet?.model || "—",
          available: bitnet?.available ?? false,
        });
      })
      .catch(() => setHealth({ status: "error", model: "—", available: false }));
  }, []);

  const handleGenerate = async (e: FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setOutput("");
    try {
      // Use the chat endpoint to test BitNet
      const res = await api.chat({ message: prompt.trim(), provider: "bitnet" });
      setOutput(res.response);
    } catch (err: unknown) {
      setOutput(`Erro: ${err instanceof Error ? err.message : "Falha na geração"}`);
    } finally {
      setLoading(false);
    }
  };

  const available = health?.available ?? false;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>BitNet</h2>
        <p>Inferência eficiente com modelos binarizados</p>
      </div>

      <div className="page-content">
        {/* Status */}
        <div
          className="card"
          style={{
            marginBottom: 24,
            display: "flex",
            alignItems: "center",
            gap: 16,
            borderLeft: `4px solid ${available ? "var(--success)" : "var(--error)"}`,
          }}
        >
          <Cpu size={32} style={{ color: available ? "var(--success)" : "var(--error)" }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              BitNet {available ? "Disponível" : "Indisponível"}
            </div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              {available
                ? `Modelo: ${health?.model || "—"}`
                : "BitNet não está configurado. Configure BITNET_API_KEY e BITNET_BASE_URL no .env"}
            </div>
          </div>
          <span className={`status-badge ${available ? "online" : "offline"}`}>
            <span className={`status-dot ${available ? "online" : "offline"}`} />
            {available ? "Online" : "Offline"}
          </span>
        </div>

        {/* Info card */}
        <div
          className="card"
          style={{
            marginBottom: 24,
            background: "rgba(6,182,212,0.05)",
            borderColor: "rgba(6,182,212,0.2)",
            display: "flex",
            gap: 12,
            alignItems: "flex-start",
          }}
        >
          <Info size={20} style={{ color: "#06b6d4", flexShrink: 0, marginTop: 2 }} />
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            <strong style={{ color: "var(--text-primary)" }}>BitNet</strong> é um provider de IA que usa modelos binários
            para inferência extremamente eficiente. Como 8º provider do sistema, ele oferece suporte
            via API compatível com OpenAI.
          </div>
        </div>

        {available && (
          <div className="card">
            <div className="card-header">
              <span className="card-title">Gerar Texto</span>
            </div>
            <form onSubmit={handleGenerate} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <textarea
                className="input"
                placeholder="Digite o prompt..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={3}
              />
              <div>
                <button className="btn btn-primary" type="submit" disabled={loading || !prompt.trim()}>
                  {loading ? <Loader2 size={16} className="spinner" /> : <Cpu size={16} />}
                  Gerar
                </button>
              </div>
            </form>
            {output && (
              <div
                style={{
                  marginTop: 12,
                  padding: 12,
                  background: "var(--bg-primary)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.9rem",
                  whiteSpace: "pre-wrap",
                }}
              >
                {output}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
