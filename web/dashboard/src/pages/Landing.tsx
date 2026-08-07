import {
  Activity,
  ArrowRight,
  BookOpen,
  Bot,
  Cpu,
  Github,
  Globe,
  Headphones,
  Layers,
  MessageSquare,
  Network,
  Server,
  Shield,
  Star,
  Zap,
} from "lucide-react";

const PROVIDERS = [
  { name: "OpenAI", color: "#10a37f" },
  { name: "Claude", color: "#d97706" },
  { name: "Gemini", color: "#4285f4" },
  { name: "Groq", color: "#f97316" },
  { name: "GLM", color: "#06b6d4" },
  { name: "Perplexity", color: "#a855f7" },
  { name: "Ollama", color: "#8b5cf6" },
  { name: "BitNet", color: "#06b6d4" },
];

const FEATURES = [
  {
    icon: <Bot size={28} />,
    title: "8 Providers de IA",
    desc: "OpenAI, Claude, Gemini, Groq, GLM, Perplexity, Ollama e BitNet — com roteamento inteligente entre eles.",
    color: "#3b82f6",
  },
  {
    icon: <Headphones size={28} />,
    title: "Pipeline de Áudio",
    desc: "STT, TTS, VAD, microfone virtual e processamento de efeitos em tempo real via PipeWire.",
    color: "#22c55e",
  },
  {
    icon: <MessageSquare size={28} />,
    title: "Chat SSE Streaming",
    desc: "Chat com histórico e streaming Server-Sent Events, migrado do Coraci (Flask para FastAPI).",
    color: "#a855f7",
  },
  {
    icon: <Network size={28} />,
    title: "RAG com Qdrant",
    desc: "Busca semântica vetorial com Qdrant para aumentar prompts com contexto relevante.",
    color: "#f59e0b",
  },
  {
    icon: <BookOpen size={28} />,
    title: "Módulo Educacional",
    desc: "Planos de aula, atividades, avaliações e calendário letivo com habilidades BNCC.",
    color: "#ec4899",
  },
  {
    icon: <Cpu size={28} />,
    title: "OpenVINO + BitNet",
    desc: "Inferência local otimizada Intel OpenVINO e LLM 1-bit ultra-eficiente em CPU.",
    color: "#06b6d4",
  },
  {
    icon: <Activity size={28} />,
    title: "487 Testes — 100%",
    desc: "Testes unitários, de integração e E2E cobrindo 57+ rotas da API.",
    color: "#22c55e",
  },
  {
    icon: <Layers size={28} />,
    title: "5 Projetos Unificados",
    desc: "IA-Lab, Coraci, BitNet, OpenVINO e HistóriaIA em um único monolito FastAPI.",
    color: "#3b82f6",
  },
];

const ARCH_STEPS = [
  {
    icon: <Server size={20} />,
    title: "FastAPI Monolito",
    desc: "Lifespan com startup/shutdown graceful. Routers centralizados em src/core/.",
  },
  {
    icon: <Bot size={20} />,
    title: "8 Providers",
    desc: "Cada provider com adapter próprio. Roteamento por TaskType.",
  },
  {
    icon: <Network size={20} />,
    title: "Qdrant + SQLite",
    desc: "Vector store para RAG e SQLite para histórico de conversas.",
  },
  {
    icon: <Globe size={20} />,
    title: "Dashboard React",
    desc: "10 páginas interativas com streaming SSE e gráficos SVG.",
  },
];

interface PageProps {
  onNavigate: (page: string) => void;
}

export function LandingPage({ onNavigate }: PageProps) {
  return (
    <div className="fade-in" style={{ overflowX: "hidden" }}>
      {/* ─── Hero Section ─────────────────────────────────────────── */}
      <section
        style={{
          minHeight: "90vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background gradient */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(ellipse at 50% 0%, rgba(59,130,246,0.15) 0%, transparent 60%), radial-gradient(ellipse at 80% 50%, rgba(168,85,247,0.1) 0%, transparent 50%)",
            pointerEvents: "none",
          }}
        />

        <div style={{ textAlign: "center", maxWidth: 720, position: "relative", zIndex: 1 }}>
          {/* Logo + Badge */}
          <div style={{ marginBottom: 24 }}>
            <span
              className="status-badge online"
              style={{ fontSize: "0.85rem", padding: "6px 16px" }}
            >
              <span className="status-dot online" />
              v2.0.0 — 487 testes
            </span>
          </div>

          <h1
            style={{
              fontSize: "clamp(2.5rem, 6vw, 4rem)",
              fontWeight: 800,
              lineHeight: 1.1,
              marginBottom: 20,
              letterSpacing: "-0.03em",
            }}
          >
            IA-Lab{" "}
            <span style={{ background: "linear-gradient(135deg, #3b82f6, #a855f7)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Unified
            </span>
          </h1>

          <p
            style={{
              fontSize: "1.2rem",
              color: "var(--text-secondary)",
              lineHeight: 1.6,
              marginBottom: 32,
              maxWidth: 600,
              margin: "0 auto 32px",
            }}
          >
            Monolito FastAPI que unifica 5 projetos em um único ecossistema.
            <br />
            8 providers de IA, áudio, RAG, educação e inferência local.
          </p>

          {/* CTA Buttons */}
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <button
              className="btn btn-primary"
              style={{ padding: "12px 28px", fontSize: "1rem" }}
              onClick={() => onNavigate("dashboard")}
            >
              <Zap size={18} />
              Acessar Dashboard
              <ArrowRight size={18} />
            </button>
            <button
              className="btn btn-secondary"
              style={{ padding: "12px 28px", fontSize: "1rem" }}
              onClick={() => onNavigate("chat")}
            >
              <MessageSquare size={18} />
              Testar Chat
            </button>
            <a
              href="https://github.com/flavioptu2007-svg/IA-Lab-Monolito"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-ghost"
              style={{ padding: "12px 28px", fontSize: "1rem", textDecoration: "none" }}
            >
              <Github size={18} />
              GitHub
            </a>
          </div>

          {/* Provider badges */}
          <div
            style={{
              display: "flex",
              gap: 8,
              justifyContent: "center",
              flexWrap: "wrap",
              marginTop: 40,
            }}
          >
            {PROVIDERS.map((p) => (
              <span
                key={p.name}
                className="tag"
                style={{
                  background: `${p.color}15`,
                  color: p.color,
                  padding: "4px 14px",
                  fontSize: "0.8rem",
                }}
              >
                {p.name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Features Grid ────────────────────────────────────────── */}
      <section style={{ padding: "80px 40px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <h2 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>
              Tudo em um só lugar
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "1.05rem" }}>
              5 projetos unificados em um monolito com 58+ endpoints REST
            </p>
          </div>

          <div className="grid grid-3" style={{ gap: 20 }}>
            {FEATURES.map((f, i) => (
              <div
                key={i}
                className="card"
                style={{
                  padding: 24,
                  borderTop: `3px solid ${f.color}`,
                  transition: "all 0.3s ease",
                  cursor: "default",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-4px)";
                  e.currentTarget.style.boxShadow = "0 8px 24px rgba(0,0,0,0.3)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "";
                  e.currentTarget.style.boxShadow = "";
                }}
              >
                <div
                  className="metric-icon"
                  style={{
                    background: `${f.color}15`,
                    color: f.color,
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    marginBottom: 16,
                  }}
                >
                  {f.icon}
                </div>
                <h3 style={{ fontSize: "1.05rem", fontWeight: 600, marginBottom: 8 }}>{f.title}</h3>
                <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Architecture ─────────────────────────────────────────── */}
      <section
        style={{
          padding: "80px 40px",
          background: "var(--bg-secondary)",
          borderTop: "1px solid var(--border)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <h2 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: 12 }}>Arquitetura</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "1.05rem" }}>
              FastAPI moderno com lifespan, routers centralizados e shutdown graceful
            </p>
          </div>

          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            {ARCH_STEPS.map((s, i) => (
              <div
                key={i}
                className="card"
                style={{
                  flex: "1 1 180px",
                  minWidth: 160,
                  maxWidth: 220,
                  textAlign: "center",
                  padding: 20,
                }}
              >
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: "50%",
                    background: "var(--bg-tertiary)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 12px",
                    color: "var(--accent)",
                  }}
                >
                  {s.icon}
                </div>
                <h4 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: 6 }}>{s.title}</h4>
                <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                  {s.desc}
                </p>
              </div>
            ))}
          </div>

          {/* Architecture diagram */}
          <div
            className="card"
            style={{
              marginTop: 32,
              padding: 24,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "0.8rem",
              lineHeight: 1.7,
              whiteSpace: "pre",
              overflowX: "auto",
              background: "#0d1117",
            }}
          >
{`┌──────────────────────────────────────────────────────────┐
│              FastAPI Monolito (lifespan)                  │
│                                                          │
│  ┌──────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Chat │ │ OpenVINO │ │Education │ │   Audio/STT    │  │
│  │ v1+v2│ │ (opcional)│ │  (BNCC)  │ │   TTS/VAD     │  │
│  └──┬───┘ └────┬─────┘ └────┬─────┘ └───────┬────────┘  │
│     │          │            │                │           │
│  ┌──▼──────────▼────────────▼────────────────▼────────┐  │
│  │              Core Services                         │  │
│  │   AIService · Classifier · VectorStore · AudioEng. │  │
│  └────────────────────┬───────────────────────────────┘  │
│                       │                                  │
│  ┌────────────────────▼───────────────────────────────┐  │
│  │          8 Providers · Qdrant · SQLite              │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘`}
          </div>
        </div>
      </section>

      {/* ─── Stats ──────────────────────────────────────────────── */}
      <section style={{ padding: "80px 40px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <div className="grid grid-4" style={{ gap: 16, textAlign: "center" }}>
            {[
              { value: "58+", label: "Endpoints REST", icon: <Server size={24} />, color: "#3b82f6" },
              { value: "487", label: "Testes — 100%", icon: <Shield size={24} />, color: "#22c55e" },
              { value: "8", label: "Providers IA", icon: <Bot size={24} />, color: "#a855f7" },
              { value: "5", label: "Projetos", icon: <Star size={24} />, color: "#f59e0b" },
            ].map((s, i) => (
              <div key={i} className="metric-card" style={{ padding: 28 }}>
                <div className="metric-icon" style={{ background: `${s.color}15`, color: s.color, margin: "0 auto 12px" }}>
                  {s.icon}
                </div>
                <div className="metric-value" style={{ color: s.color }}>{s.value}</div>
                <div className="metric-label">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA Final ──────────────────────────────────────────── */}
      <section
        style={{
          padding: "80px 40px",
          textAlign: "center",
          background: "linear-gradient(135deg, rgba(59,130,246,0.1), rgba(168,85,247,0.1))",
          borderTop: "1px solid var(--border)",
        }}
      >
        <div style={{ maxWidth: 600, margin: "0 auto" }}>
          <h2 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: 16 }}>
            Pronto para usar?
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "1.05rem", marginBottom: 32 }}>
            Tudo rodando localmente. Configure suas API keys e comece a explorar.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <button
              className="btn btn-primary"
              style={{ padding: "12px 28px", fontSize: "1rem" }}
              onClick={() => onNavigate("dashboard")}
            >
              <Zap size={18} />
              Dashboard
              <ArrowRight size={18} />
            </button>
            <button
              className="btn btn-secondary"
              style={{ padding: "12px 28px", fontSize: "1rem" }}
              onClick={() => onNavigate("providers")}
            >
              <Globe size={18} />
              Ver Providers
            </button>
          </div>
        </div>
      </section>

      {/* ─── Footer ─────────────────────────────────────────────── */}
      <footer
        style={{
          padding: "32px 40px",
          borderTop: "1px solid var(--border)",
          textAlign: "center",
          color: "var(--text-muted)",
          fontSize: "0.85rem",
        }}
      >
        <p>IA-Lab Unified v2.0.0 — MIT License</p>
        <p style={{ marginTop: 4 }}>
          Feito com{" "}
          <span style={{ color: "var(--error)" }}>❤</span> para consolidar 5 projetos em um ecossistema
        </p>
      </footer>
    </div>
  );
}
