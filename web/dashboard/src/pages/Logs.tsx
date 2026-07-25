import { useEffect, useState } from "react";
import { api } from "../api/client";
import { AlertCircle, Search } from "lucide-react";

export function LogsPage() {
  const [logs, setLogs] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api
      .logs()
      .then(setLogs)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const lines = logs.split("\n").filter(Boolean);
  const filtered = filter
    ? lines.filter((l) => l.toLowerCase().includes(filter.toLowerCase()))
    : lines;

  const lastLines = filtered.slice(-200);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span style={{ marginLeft: 12 }}>Carregando logs...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-content">
        <div className="card" style={{ textAlign: "center", padding: 40, borderColor: "var(--error)" }}>
          <AlertCircle size={48} style={{ color: "var(--error)", marginBottom: 16 }} />
          <h3>Erro ao carregar logs</h3>
          <p style={{ color: "var(--text-secondary)", marginTop: 8 }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2>Logs do Sistema</h2>
            <p>
              {lines.length} linhas no total &middot; exibindo {lastLines.length}
              {filtered.length !== lines.length ? ` de ${filtered.length} filtradas` : ""}
            </p>
          </div>
        </div>
      </div>

      <div className="page-content">
        <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
          <div style={{ flex: 1, position: "relative" }}>
            <Search
              size={16}
              style={{
                position: "absolute",
                left: 12,
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-muted)",
              }}
            />
            <input
              className="input"
              style={{ paddingLeft: 36 }}
              placeholder="Filtrar logs..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
        </div>

        <div
          className="card"
          style={{
            padding: 0,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "12px 16px",
              background: "#0d1117",
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: "0.8rem",
              lineHeight: 1.6,
              maxHeight: "calc(100vh - 300px)",
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {lastLines.length > 0 ? (
              lastLines.map((line, i) => (
                <div
                  key={i}
                  style={{
                    padding: "1px 0",
                    color: line.toLowerCase().includes("error")
                      ? "var(--error)"
                      : line.toLowerCase().includes("warn")
                        ? "var(--warning)"
                        : line.toLowerCase().includes("info")
                          ? "var(--accent)"
                          : "var(--text-secondary)",
                  }}
                >
                  {line}
                </div>
              ))
            ) : (
              <div style={{ color: "var(--text-muted)", textAlign: "center", padding: 20 }}>
                Nenhum log encontrado
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
