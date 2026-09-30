import { useEffect, useState } from "react";
import { api, MetricEntry } from "../api/client";
import { AlertCircle, BarChart3, Clock } from "lucide-react";

function MetricChart({ name, color, data }: { name: string; color: string; data: MetricEntry[] }) {
  if (data.length < 2) {
    return <div className="metric-sub">Dados insuficientes para gráfico</div>;
  }

  const values = data.map((d) => d.value);
  const max = Math.max(...values, 1);
  const w = 600;
  const h = 150;
  const padding = { top: 10, right: 10, bottom: 20, left: 50 };

  const chartW = w - padding.left - padding.right;
  const chartH = h - padding.top - padding.bottom;

  const points = values.map((v, i) => {
    const x = padding.left + (i / (values.length - 1)) * chartW;
    const y = padding.top + chartH - (v / max) * chartH;
    return `${x},${y}`;
  });

  const areaPoints = [...points, `${padding.left + chartW},${padding.top + chartH}`, `${padding.left},${padding.top + chartH}`];

  // Y-axis labels
  const yLabels = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
    value: (max * f).toFixed(1),
    y: padding.top + chartH - f * chartH,
  }));

  return (
    <div>
      <div className="metric-label" style={{ marginBottom: 8 }}>{name}</div>
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{ maxWidth: w }}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((f, i) => (
          <line
            key={i}
            x1={padding.left}
            y1={padding.top + chartH - f * chartH}
            x2={padding.left + chartW}
            y2={padding.top + chartH - f * chartH}
            stroke="var(--border)"
            strokeWidth="1"
          />
        ))}
        {/* Y-axis labels */}
        {yLabels.map((l, i) => (
          <text key={i} x={padding.left - 8} y={l.y + 4} textAnchor="end" fill="var(--text-muted)" fontSize="10">
            {l.value}
          </text>
        ))}
        {/* Area fill */}
        <polygon points={areaPoints.join(" ")} fill={`${color}15`} />
        {/* Line */}
        <polyline points={points.join(" ")} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {/* Dots */}
        {values.map((_, i) => {
          const [x, y] = points[i].split(",").map(Number);
          return <circle key={i} cx={x} cy={y} r="3" fill={color} />;
        })}
      </svg>
    </div>
  );
}

export function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .metrics()
      .then(setMetrics)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span style={{ marginLeft: 12 }}>Carregando métricas...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-content">
        <div className="card" style={{ textAlign: "center", padding: 40, borderColor: "var(--error)" }}>
          <AlertCircle size={48} style={{ color: "var(--error)", marginBottom: 16 }} />
          <h3 style={{ marginBottom: 8 }}>Erro ao carregar métricas</h3>
          <p style={{ color: "var(--text-secondary)" }}>{error}</p>
        </div>
      </div>
    );
  }

  // Group metrics by name
  const groups = new Map<string, MetricEntry[]>();
  for (const m of metrics) {
    if (!groups.has(m.name)) groups.set(m.name, []);
    groups.get(m.name)!.push(m);
  }

  // Simple stats
  const totalEntries = metrics.length;
  const uniqueNames = groups.size;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Métricas</h2>
        <p>Telemetria e monitoramento do sistema</p>
      </div>

      <div className="page-content">
        {/* Summary cards */}
        <div className="grid grid-2" style={{ marginBottom: 24 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Total de Entradas</span>
              <BarChart3 size={20} style={{ color: "var(--accent)" }} />
            </div>
            <div className="card-value">{totalEntries}</div>
            <div className="metric-sub">métricas coletadas</div>
          </div>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Métricas Únicas</span>
              <Clock size={20} style={{ color: "var(--success)" }} />
            </div>
            <div className="card-value">{uniqueNames}</div>
            <div className="metric-sub">nomes distintos</div>
          </div>
        </div>

        {/* Charts */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {Array.from(groups.entries()).map(([name, data], i) => {
            const colors = ["#3b82f6", "#22c55e", "#a855f7", "#f59e0b", "#ec4899", "#06b6d4"];
            return (
              <div key={name} className="card">
                <MetricChart name={name} color={colors[i % colors.length]} data={data} />
              </div>
            );
          })}
        </div>

        {metrics.length > 0 && (
          <div className="card" style={{ marginTop: 24 }}>
            <div className="card-header">
              <span className="card-title">Dados Brutos</span>
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
                  {metrics.slice(-20).reverse().map((m, i) => (
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
