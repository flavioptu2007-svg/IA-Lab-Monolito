import { FormEvent, useEffect, useState } from "react";
import { api, BNCCSkill, BNCCCompetence, LessonPlan, Activity } from "../api/client";
import { FileText, ListTree, Plus, Search, Trash2 } from "lucide-react";

function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        gap: 4,
        marginBottom: 24,
        background: "var(--bg-primary)",
        borderRadius: "var(--radius-sm)",
        padding: 4,
      }}
    >
      {tabs.map((t) => (
        <button
          key={t.id}
          className={`btn ${active === t.id ? "btn-primary" : "btn-ghost"}`}
          onClick={() => onChange(t.id)}
          style={{ flex: 1, justifyContent: "center" }}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ─── BNCC Tab ─────────────────────────────────────────────────────────

function BNCCSkills() {
  const [skills, setSkills] = useState<BNCCSkill[]>([]);
  const [competences, setCompetences] = useState<BNCCCompetence[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("");

  useEffect(() => {
    Promise.all([
      api.bnccSkills(),
      api.bnccCompetences(),
    ])
      .then(([s, c]) => {
        setSkills(s);
        setCompetences(c);
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = skills.filter((s) => {
    if (yearFilter && s.year !== yearFilter) return false;
    if (filter) {
      const q = filter.toLowerCase();
      return (
        s.code.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.competence.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const years = [...new Set(skills.map((s) => s.year))].sort();

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <div style={{ flex: 1 }}>
          <input
            className="input"
            placeholder="Pesquisar habilidades..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <select
          className="input"
          style={{ width: "auto", minWidth: 120 }}
          value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}
        >
          <option value="">Todos os anos</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}º ano
            </option>
          ))}
        </select>
      </div>

      {competences.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
          {competences.map((c) => (
            <span
              key={c.code}
              className="tag"
              style={{
                background: "rgba(59,130,246,0.1)",
                color: "var(--accent)",
                cursor: "pointer",
              }}
              onClick={() => setFilter(c.code)}
            >
              {c.code} — {c.name}
            </span>
          ))}
        </div>
      )}

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Habilidade</th>
              <th>Competência</th>
              <th>Ano</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s, i) => (
              <tr key={i}>
                <td style={{ fontFamily: "monospace", fontWeight: 600 }}>{s.code}</td>
                <td style={{ maxWidth: 400 }}>{s.description}</td>
                <td>
                  <span
                    className="tag"
                    style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent)" }}
                  >
                    {s.competence}
                  </span>
                </td>
                <td>{s.year}º ano</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="empty-state">
            <Search size={32} />
            <h3>Nenhuma habilidade encontrada</h3>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Lesson Plans Tab ──────────────────────────────────────────────────

function LessonPlans() {
  const [plans, setPlans] = useState<LessonPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<LessonPlan>({
    title: "",
    subject: "História",
    year: "6",
    duration_minutes: 50,
    objectives: [""],
    skills: [""],
    content: "",
    methodology: "",
    resources: [""],
    assessment: "",
  });

  const load = () => {
    setLoading(true);
    api.lessonPlans.list().then(setPlans).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const createPlan = async (e: FormEvent) => {
    e.preventDefault();
    await api.lessonPlans.create({
      ...form,
      objectives: form.objectives.filter(Boolean),
      skills: form.skills.filter(Boolean),
      resources: form.resources.filter(Boolean),
    });
    setShowForm(false);
    setForm({
      title: "", subject: "História", year: "6", duration_minutes: 50,
      objectives: [""], skills: [""], content: "", methodology: "", resources: [""], assessment: "",
    });
    load();
  };

  if (loading) {
    return <div className="loading"><div className="spinner" /></div>;
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 16 }}>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          <Plus size={16} />
          {showForm ? "Cancelar" : "Novo Plano"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={createPlan}
          className="card"
          style={{ marginBottom: 16, display: "flex", flexDirection: "column", gap: 12 }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label className="metric-label">Título</label>
              <input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </div>
            <div>
              <label className="metric-label">Duração (min)</label>
              <input className="input" type="number" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: +e.target.value })} />
            </div>
          </div>
          <div>
            <label className="metric-label">Conteúdo</label>
            <textarea className="input" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} required />
          </div>
          <button className="btn btn-primary" type="submit" style={{ alignSelf: "flex-end" }}>
            Salvar Plano
          </button>
        </form>
      )}

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Título</th>
              <th>Disciplina</th>
              <th>Ano</th>
              <th>Duração</th>
              <th>Objetivos</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.id}>
                <td style={{ fontWeight: 600 }}>{p.title}</td>
                <td>{p.subject}</td>
                <td>{p.year}º</td>
                <td>{p.duration_minutes}min</td>
                <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {p.objectives?.slice(0, 2).join(", ")}
                  {p.objectives && p.objectives.length > 2 ? "..." : ""}
                </td>
                <td>
                  <button
                    className="btn btn-ghost"
                    style={{ color: "var(--error)" }}
                    onClick={async () => {
                      if (p.id && confirm("Excluir plano?")) {
                        await api.lessonPlans.delete(p.id);
                        load();
                      }
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {plans.length === 0 && (
          <div className="empty-state">
            <FileText size={32} />
            <h3>Nenhum plano de aula</h3>
            <p>Crie seu primeiro plano de aula</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Activities Tab ────────────────────────────────────────────────────

function ActivitiesTab() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.activities.list().then(setActivities).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) {
    return <div className="loading"><div className="spinner" /></div>;
  }

  return (
    <div>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Título</th>
              <th>Tipo</th>
              <th>Disciplina</th>
              <th>Ano</th>
              <th>Duração</th>
              <th>Skills</th>
            </tr>
          </thead>
          <tbody>
            {activities.map((a) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 600 }}>{a.title}</td>
                <td>
                  <span className="tag" style={{ background: "rgba(168,85,247,0.1)", color: "#a855f7" }}>
                    {a.type}
                  </span>
                </td>
                <td>{a.subject}</td>
                <td>{a.year}º</td>
                <td>{a.duration_minutes}min</td>
                <td style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {a.skills?.slice(0, 3).map((s, i) => (
                    <span key={i} className="tag" style={{ background: "rgba(6,182,212,0.1)", color: "#06b6d4", fontSize: "0.7rem" }}>
                      {s}
                    </span>
                  ))}
                  {a.skills && a.skills.length > 3 && <span className="metric-sub">+{a.skills.length - 3}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {activities.length === 0 && (
          <div className="empty-state">
            <ListTree size={32} />
            <h3>Nenhuma atividade</h3>
            <p>As atividades aparecerão aqui</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main ──────────────────────────────────────────────────────────────

export function EducationPage() {
  const [activeTab, setActiveTab] = useState("bncc");

  const tabs = [
    { id: "bncc", label: "BNCC Habilidades" },
    { id: "plans", label: "Planos de Aula" },
    { id: "activities", label: "Atividades" },
  ];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Educação</h2>
        <p>Módulo de História — BNCC, planos de aula e atividades</p>
      </div>

      <div className="page-content">
        <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />

        {activeTab === "bncc" && <BNCCSkills />}
        {activeTab === "plans" && <LessonPlans />}
        {activeTab === "activities" && <ActivitiesTab />}
      </div>
    </div>
  );
}
