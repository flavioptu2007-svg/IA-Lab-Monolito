import { useEffect, useState } from "react";
import { api, HealthResponse, MetricEntry, ProviderInfo } from "../api/client";
import { Activity, Bot, Zap, Clock, HardDrive, AlertCircle } from "lucide-react";

function MetricCard({
  icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  color: string;
}) {
  return (
    <div className="metric-card">
      <div className="metric-icon" style={{ background: `${color}22`, color }}>
        {icon}
      </div>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

function ProviderBadge({ name, available }: { name: string; available: boolean }) {
  const colors: Record<string, string> = {
    openai: "#10a37f",
    claude: "#d97706",
    gemini: "#4285f4",
    groq: "#f97316",
    glm: "#06b6d4",
    perplexity: "#a855f7",
    ollama: "#a855f7",
    bitnet: "#06b6d4",
  };
  const color = colors[name.toLowerCase()] || "var(--text-muted)";
  return (
    <span
      className="tag"
      style={{
        background: available ? `${color}22` : "var(--bg-tertiary)",
        color: available ? color : "var(--text-muted)",
        opacity: available ? 1 : 0.5,
      }}
    >
      {available ? "●" : "○"} {name}
    </span>
  );
}

function MiniSparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return <span className="metric-sub">—</span>;
  const max = Math.max(...values, 1);
  const h = 32;
  const w = 80;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - (v / max) * h;
    return `${x},${y}`;
  });
  return (
    <svg width={w} height={h} style={{ marginTop: 4 }}>
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [metrics, setMetrics] = useState<MetricEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.health(), api.providers(), api.metrics()])
      .then(([h, p, m]) => {
        setHealth(h);
        setProviders(p);
        setMetrics(m);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span style={{ marginLeft: 12 }}>Carregando dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-content">
        <div className="card" style={{ textAlign: "center", padding: 40, borderColor: "var(--error)" }}>
          <AlertCircle size={48} style={{ color: "var(--error)", marginBottom: 16 }} />
          <h3 style={{ marginBottom: 8 }}>Erro ao conectar</h3>
          <p style={{ color: "var(--text-secondary)" }}>{error}</p>
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => window.location.reload()}>
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  const uptime = health
    ? health.uptime_seconds >= 86400
      ? `${(health.uptime_seconds / 86400).toFixed(1)}d`
      : health.uptime_seconds >= 3600
        ? `${(health.uptime_seconds / 3600).toFixed(1)}h`
        : `${(health.uptime_seconds / 60).toFixed(0)}m`
    : "—";

  const onlineCount = providers.filter((p) => p.available).length;

  // Grab some sample metric values for sparkline
  const cpuValues = metrics.filter((m) => m.name.toLowerCase().includes("cpu")).map((m) => m.value);
  const memValues = metrics.filter((m) => m.name.toLowerCase().includes("mem")).map((m) => m.value);

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Visão geral do sistema IA-Lab Unified</p>
      </div>

      <div className="page-content">
        {/* Metric Cards */}
        <div className="grid grid-4" style={{ marginBottom: 24 }}>
          <MetricCard
            icon={<Zap size={20} />}
            label="Status"
            value={health?.status ?? "—"}
            sub={health?.version ? `v${health.version}` : undefined}
            color="#22c55e"
          />
          <MetricCard
            icon={<Clock size={20} />}
            label="Uptime"
            value={uptime}
            sub={health ? `${health.uptime_seconds.toLocaleString()}s` : undefined}
            color="#3b82f6"
          />
          <MetricCard
            icon={<Bot size={20} />}
            label="Providers"
            value={`${onlineCount}/${providers.length}`}
            sub={`${onlineCount} online`}
            color="#a855f7"
          />
          <MetricCard
            icon={<HardDrive size={20} />}
            label="Memória"
            value={health ? `${health.memory_mb.toFixed(0)} MB` : "—"}
            color="#f97316"
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* Providers Status */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Providers</span>
              <span className="status-badge online">
                <span className="status-dot online" />
                {onlineCount} online
              </span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {providers.map((p) => (
                <ProviderBadge key={p.name} name={p.name} available={p.available} />
              ))}
            </div>
            {providers.length > 0 && (
              <div className="table-container" style={{ marginTop: 16 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Provider</th>
                      <th>Modelo</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {providers.map((p) => (
                      <tr key={p.name}>
                        <td style={{ fontWeight: 600 }}>{p.name}</td>
                        <td style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                          {p.model}
                        </td>
                        <td>
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
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* System Info */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Sistema</span>
              <Activity size={16} style={{ color: "var(--text-muted)" }} />
            </div>
            {health && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span className="metric-label">CPU</span>
                    <span className="metric-sub">
                      {cpuValues.length > 0 ? `${cpuValues[cpuValues.length - 1].toFixed(1)}%` : "—"}
                    </span>
                  </div>
                  {cpuValues.length > 0 && <MiniSparkline values={cpuValues} color="#3b82f6" />}
                </div>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span className="metric-label">Memória</span>
                    <span className="metric-sub">{health.memory_mb.toFixed(0)} MB</span>
                  </div>
                  {memValues.length > 0 && <MiniSparkline values={memValues} color="#f97316" />}
                </div>
                <div style={{ marginTop: 8 }}>
                  <div className="metric-label">Timestamps</div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    <div>Iniciado em: {new Date(health.timestamp).toLocaleString("pt-BR")}</div>
                    <div>Última atualização: {new Date().toLocaleString("pt-BR")}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Recent Metrics */}
        {metrics.length > 0 && (
          <div className="card" style={{ marginTop: 24 }}>
            <div className="card-header">
              <span className="card-title">Métricas Recentes</span>
              <span className="metric-sub">{metrics.length} entries</span>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Valor</th>
                    <th>Unidade</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.slice(-15).reverse().map((m, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 500 }}>{m.name}</td>
                      <td>{m.value.toFixed(2)}</td>
                      <td style={{ color: "var(--text-muted)" }}>{m.unit}</td>
                      <td style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        {new Date(m.timestamp).toLocaleString("pt-BR")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
