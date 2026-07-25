import { useCallback, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { LandingPage } from "./pages/Landing";
import { DashboardPage } from "./pages/Dashboard";
import { ChatPage } from "./pages/Chat";
import { ProvidersPage } from "./pages/Providers";
import { EducationPage } from "./pages/Education";
import { OpenVINOPage } from "./pages/OpenVINO";
import { MetricsPage } from "./pages/Metrics";
import { AudioPage } from "./pages/Audio";
import { BitNetPage } from "./pages/BitNet";
import { LogsPage } from "./pages/Logs";
import { RAGPage } from "./pages/RAG";

const PAGES = [
  "home",
  "dashboard",
  "chat",
  "providers",
  "education",
  "openvino",
  "bitnet",
  "metrics",
  "audio",
  "logs",
  "rag",
] as const;

type Page = (typeof PAGES)[number];

export default function App() {
  const [page, setPage] = useState<Page>("home");

  const handleNavigate = useCallback((p: string) => {
    if (PAGES.includes(p as Page)) {
      setPage(p as Page);
    }
  }, []);

  const renderPage = useCallback(() => {
    switch (page) {
      case "home":
        return <LandingPage onNavigate={handleNavigate} />;
      case "dashboard":
        return <DashboardPage />;
      case "chat":
        return <ChatPage />;
      case "providers":
        return <ProvidersPage />;
      case "education":
        return <EducationPage />;
      case "openvino":
        return <OpenVINOPage />;
      case "bitnet":
        return <BitNetPage />;
      case "metrics":
        return <MetricsPage />;
      case "audio":
        return <AudioPage />;
      case "logs":
        return <LogsPage />;
      case "rag":
        return <RAGPage />;
      default:
        return <LandingPage onNavigate={handleNavigate} />;
    }
  }, [page, handleNavigate]);

  return (
    <div className="app-layout">
      <Sidebar active={page} onNavigate={handleNavigate} />
      <main className="main-content">{renderPage()}</main>
    </div>
  );
}
