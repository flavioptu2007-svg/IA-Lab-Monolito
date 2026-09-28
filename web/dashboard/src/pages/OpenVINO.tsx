import { FormEvent, useEffect, useState } from "react";
import { api, OpenVINOHealth } from "../api/client";
import { Cpu, Headphones, Loader2, MessageSquare, Microscope } from "lucide-react";

export function OpenVINOPage() {
  const [health, setHealth] = useState<OpenVINOHealth | null>(null);
  const [loading, setLoading] = useState(true);

  // Generate
  const [prompt, setPrompt] = useState("");
  const [genOutput, setGenOutput] = useState("");
  const [genLoading, setGenLoading] = useState(false);

  // Transcribe
  const [audioPath, setAudioPath] = useState("");
  const [transcript, setTranscript] = useState("");
  const [transcribeLoading, setTranscribeLoading] = useState(false);

  // RAG
  const [ragQuestion, setRagQuestion] = useState("");
  const [ragAnswer, setRagAnswer] = useState("");
  const [ragLoading, setRagLoading] = useState(false);

  useEffect(() => {
    api.openvino.health()
      .then(setHealth)
      .catch(() => {
        // OpenVINO not available is expected
        setHealth({ available: false });
      })
      .finally(() => setLoading(false));
  }, []);

  const available = health?.available ?? false;

  const handleGenerate = async (e: FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || genLoading) return;
    setGenLoading(true);
    setGenOutput("");
    try {
      const res = await api.openvino.generate(prompt.trim());
      setGenOutput(res.output);
    } catch (err: unknown) {
      setGenOutput(`Erro: ${err instanceof Error ? err.message : "Erro desconhecido"}`);
    } finally {
      setGenLoading(false);
    }
  };

  const handleTranscribe = async (e: FormEvent) => {
    e.preventDefault();
    if (!audioPath.trim() || transcribeLoading) return;
    setTranscribeLoading(true);
    setTranscript("");
    try {
      const res = await api.openvino.transcribe(audioPath.trim());
      setTranscript(res.text);
    } catch (err: unknown) {
      setTranscript(`Erro: ${err instanceof Error ? err.message : "Erro desconhecido"}`);
    } finally {
      setTranscribeLoading(false);
    }
  };

  const handleRag = async (e: FormEvent) => {
    e.preventDefault();
    if (!ragQuestion.trim() || ragLoading) return;
    setRagLoading(true);
    setRagAnswer("");
    try {
      const res = await api.openvino.ragQuery(ragQuestion.trim());
      setRagAnswer(`${res.answer}\n\nFontes: ${res.sources.map((s) => s.title).join(", ")}`);
    } catch (err: unknown) {
      setRagAnswer(`Erro: ${err instanceof Error ? err.message : "Erro desconhecido"}`);
    } finally {
      setRagLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span style={{ marginLeft: 12 }}>Verificando disponibilidade do OpenVINO...</span>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>OpenVINO</h2>
        <p>Inferência otimizada com Intel OpenVINO</p>
      </div>

      <div className="page-content">
        {/* Status Banner */}
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
              {available ? "OpenVINO Disponível" : "OpenVINO Não Disponível"}
            </div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              {available
                ? `Versão: ${health?.version || "—"} • Dispositivos: ${health?.devices?.join(", ") || "—"}`
                : "Instale o OpenVINO para ativar. Consulte a documentação em AI/openvino/"}
            </div>
          </div>
          {available && (
            <span className="status-badge online">
              <span className="status-dot online" />
              {health?.devices?.length || 0} devices
            </span>
          )}
        </div>

        {available && (
          <>
            {/* Generate */}
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-header">
                <span className="card-title">
                  <Microscope size={16} style={{ marginRight: 6, verticalAlign: "middle" }} />
                  Geração de Texto
                </span>
              </div>
              <form onSubmit={handleGenerate} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <textarea
                  className="input"
                  placeholder="Digite o prompt para geração..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={3}
                />
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <button className="btn btn-primary" type="submit" disabled={genLoading || !prompt.trim()}>
                    {genLoading ? <Loader2 size={16} className="spinner" /> : <Microscope size={16} />}
                    Gerar
                  </button>
                </div>
              </form>
              {genOutput && (
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
                  {genOutput}
                </div>
              )}
            </div>

            {/* Transcribe */}
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-header">
                <span className="card-title">
                  <Headphones size={16} style={{ marginRight: 6, verticalAlign: "middle" }} />
                  Transcrição de Áudio
                </span>
              </div>
              <form onSubmit={handleTranscribe} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <input
                  className="input"
                  placeholder="Caminho do arquivo de áudio (ex: /path/to/audio.wav)"
                  value={audioPath}
                  onChange={(e) => setAudioPath(e.target.value)}
                />
                <div>
                  <button className="btn btn-primary" type="submit" disabled={transcribeLoading || !audioPath.trim()}>
                    {transcribeLoading ? <Loader2 size={16} className="spinner" /> : <Headphones size={16} />}
                    Transcrever
                  </button>
                </div>
              </form>
              {transcript && (
                <div
                  style={{
                    marginTop: 12,
                    padding: 12,
                    background: "var(--bg-primary)",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "0.9rem",
                  }}
                >
                  {transcript}
                </div>
              )}
            </div>

            {/* RAG Query */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <MessageSquare size={16} style={{ marginRight: 6, verticalAlign: "middle" }} />
                  RAG Query
                </span>
              </div>
              <form onSubmit={handleRag} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <input
                  className="input"
                  placeholder="Faça uma pergunta sobre os documentos..."
                  value={ragQuestion}
                  onChange={(e) => setRagQuestion(e.target.value)}
                />
                <div>
                  <button className="btn btn-primary" type="submit" disabled={ragLoading || !ragQuestion.trim()}>
                    {ragLoading ? <Loader2 size={16} className="spinner" /> : <MessageSquare size={16} />}
                    Perguntar
                  </button>
                </div>
              </form>
              {ragAnswer && (
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
                  {ragAnswer}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
