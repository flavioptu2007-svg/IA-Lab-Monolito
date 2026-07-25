import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  Cpu,
  Globe,
  Headphones,
  Home,
  LayoutDashboard,
  MessageSquare,
  Microscope,
  Network,
} from "lucide-react";

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
}

function NavItem({ icon, label, active, onClick }: NavItemProps) {
  return (
    <button
      className={`nav-item ${active ? "active" : ""}`}
      onClick={onClick}
      title={label}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

interface SidebarProps {
  active: string;
  onNavigate: (page: string) => void;
}

export function Sidebar({ active, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>
          <Bot size={24} style={{ color: "var(--accent)" }} />
          IA-Lab
          <span className="version">v2.0.0</span>
        </h1>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          <div className="nav-section-title">Geral</div>
          <NavItem
            icon={<Home />}
            label="Início"
            active={active === "home"}
            onClick={() => onNavigate("home")}
          />
          <NavItem
            icon={<LayoutDashboard />}
            label="Dashboard"
            active={active === "dashboard"}
            onClick={() => onNavigate("dashboard")}
          />
          <NavItem
            icon={<MessageSquare />}
            label="Chat"
            active={active === "chat"}
            onClick={() => onNavigate("chat")}
          />
          <NavItem
            icon={<Globe />}
            label="Providers"
            active={active === "providers"}
            onClick={() => onNavigate("providers")}
          />
          <NavItem
            icon={<BarChart3 />}
            label="Métricas"
            active={active === "metrics"}
            onClick={() => onNavigate("metrics")}
          />
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Módulos</div>
          <NavItem
            icon={<BookOpen />}
            label="Educação"
            active={active === "education"}
            onClick={() => onNavigate("education")}
          />
          <NavItem
            icon={<Cpu />}
            label="OpenVINO"
            active={active === "openvino"}
            onClick={() => onNavigate("openvino")}
          />
          <NavItem
            icon={<Microscope />}
            label="BitNet"
            active={active === "bitnet"}
            onClick={() => onNavigate("bitnet")}
          />
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Sistema</div>
          <NavItem
            icon={<Headphones />}
            label="Áudio"
            active={active === "audio"}
            onClick={() => onNavigate("audio")}
          />
          <NavItem
            icon={<Activity />}
            label="Logs"
            active={active === "logs"}
            onClick={() => onNavigate("logs")}
          />
          <NavItem
            icon={<Network />}
            label="RAG"
            active={active === "rag"}
            onClick={() => onNavigate("rag")}
          />
        </div>
      </nav>
    </aside>
  );
}
