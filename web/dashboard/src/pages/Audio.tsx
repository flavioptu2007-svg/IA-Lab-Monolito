import { useEffect, useState } from "react";
import { api, AudioStatus } from "../api/client";
import { AlertCircle, Headphones, Mic, Radio, Sliders } from "lucide-react";

export function AudioPage() {
  const [status, setStatus] = useState<AudioStatus | null>(null);
  const [devices, setDevices] = useState<string[]>([]);
  const [config, setConfig] = useState<{
    enabled: boolean;
    sample_rate: number;
    channels: number;
  } | null>(null);
  const [micStatus, setMicStatus] = useState<{
    available: boolean;
    device: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.audioStatus(),
      api.audioDevices(),
      api.audioConfig(),
      api.audioMicStatus(),
    ])
      .then(([s, d, c, m]) => {
        setStatus(s);
        setDevices(d);
        setConfig(c);
        setMicStatus(m);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span style={{ marginLeft: 12 }}>Carregando status de áudio...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-content">
        <div className="card" style={{ textAlign: "center", padding: 40, borderColor: "var(--error)" }}>
          <AlertCircle size={48} style={{ color: "var(--error)", marginBottom: 16 }} />
          <h3>Erro ao carregar áudio</h3>
          <p style={{ color: "var(--text-secondary)", marginTop: 8 }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Áudio</h2>
        <p>Status do microfone, dispositivos e configurações</p>
      </div>

      <div className="page-content">
        {/* Status cards */}
        <div className="grid grid-2" style={{ marginBottom: 24 }}>
          <div className="metric-card">
            <div className="metric-icon" style={{ background: status?.enabled ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)", color: status?.enabled ? "var(--success)" : "var(--error)" }}>
              <Headphones size={20} />
            </div>
            <div className="metric-label">Áudio</div>
            <div className="metric-value" style={{ color: status?.enabled ? "var(--success)" : "var(--error)" }}>
              {status?.enabled ? "Ativado" : "Desativado"}
            </div>
            {status?.sample_rate && (
              <div className="metric-sub">{status.sample_rate} Hz</div>
            )}
          </div>

          <div className="metric-card">
            <div className="metric-icon" style={{ background: micStatus?.available ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)", color: micStatus?.available ? "var(--success)" : "var(--error)" }}>
              <Mic size={20} />
            </div>
            <div className="metric-label">Microfone</div>
            <div className="metric-value" style={{ color: micStatus?.available ? "var(--success)" : "var(--error)" }}>
              {micStatus?.available ? "Disponível" : "Indisponível"}
            </div>
            {micStatus?.device && (
              <div className="metric-sub">{micStatus.device}</div>
            )}
          </div>
        </div>

        {/* Audio Config */}
        <div className="grid grid-2" style={{ marginBottom: 24 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">
                <Sliders size={16} style={{ marginRight: 6, verticalAlign: "middle" }} />
                Configurações
              </span>
            </div>
            {config && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span className="metric-label">Sample Rate</span>
                  <span>{config.sample_rate} Hz</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span className="metric-label">Canais</span>
                  <span>{config.channels}</span>
                </div>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">
                <Radio size={16} style={{ marginRight: 6, verticalAlign: "middle" }} />
                Dispositivos
              </span>
            </div>
            {devices.length > 0 ? (
              <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                {devices.map((d, i) => (
                  <li
                    key={i}
                    style={{
                      padding: "8px 12px",
                      background: "var(--bg-primary)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "0.85rem",
                      fontFamily: "monospace",
                    }}
                  >
                    {d}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state" style={{ padding: 20 }}>
                <h3>Nenhum dispositivo</h3>
              </div>
            )}
          </div>
        </div>

        {/* Mic Status Detail */}
        {micStatus && (
          <div className="card">
            <div className="card-header">
              <span className="card-title">Status do Microfone</span>
              <span className={`status-badge ${micStatus.available ? "online" : "offline"}`}>
                <span className={`status-dot ${micStatus.available ? "online" : "offline"}`} />
                {micStatus.available ? "Disponível" : "Indisponível"}
              </span>
            </div>
            <div className="metric-label">Dispositivo atual</div>
            <div style={{ fontSize: "0.9rem", marginTop: 4 }}>
              {micStatus.device || "Nenhum dispositivo padrão"}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
