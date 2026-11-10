import { FormEvent, useEffect, useState } from "react";
import {
  educationStudioApi,
  GenerateRequest,
  Material,
  MaterialType,
  SavedMaterial,
} from "../api/educationStudio";

const NAMES: Record<MaterialType, string> = {
  lesson_plan: "Plano de aula",
  activity: "Atividade",
  evaluation: "Avaliação",
};
const YEARS: Record<string, string> = {
  EF_6: "6º ano",
  EF_7: "7º ano",
  EF_8: "8º ano",
  EF_9: "9º ano",
  EM: "Ensino médio",
};
const lines = (value: string) =>
  value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
const message = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Não foi possível concluir. Tente novamente.";

export function EducationStudio() {
  const [token, setToken] = useState("");
  const [form, setForm] = useState<GenerateRequest>({
    material_type: "lesson_plan",
    topic: "",
    academic_year: "EF_8",
    duration_minutes: 50,
    learning_objectives: [],
    bncc_skills: [],
    instructions: "",
  });
  const [objectives, setObjectives] = useState("");
  const [skills, setSkills] = useState("");
  const [items, setItems] = useState<SavedMaterial[]>([]);
  const [offset, setOffset] = useState(0);
  const [saved, setSaved] = useState<SavedMaterial | null>(null);
  const [editing, setEditing] = useState<Material | null>(null);
  const [dirty, setDirty] = useState(false);
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [notice, setNotice] = useState("");
  const api = educationStudioApi(token);

  async function load(page = offset) {
    setLoading(true);
    setListError("");
    try {
      const result = await api.list(page);
      setItems(result.materials);
      setOffset(page);
    } catch (error) {
      setListError(message(error));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load(0);
  }, []);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function open(item: SavedMaterial) {
    if (
      dirty &&
      !confirm(
        "Há alterações não salvas. Deseja descartá-las e abrir outro material?",
      )
    )
      return;
    setSaved(item);
    setEditing(structuredClone(item.material));
    setDirty(false);
    setApproved(false);
    setError("");
    setNotice("");
  }
  function edit(values: Partial<Material>) {
    setEditing((current) => (current ? { ...current, ...values } : current));
    setDirty(true);
    setApproved(false);
    setNotice("");
  }
  async function generate(event: FormEvent) {
    event.preventDefault();
    if (
      dirty &&
      !confirm("Há alterações não salvas. Deseja gerar um novo rascunho?")
    )
      return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const item = await api.generate({
        ...form,
        learning_objectives: lines(objectives),
        bncc_skills: skills.split(/[,\s]+/).filter(Boolean),
      });
      setSaved(item);
      setEditing(structuredClone(item.material));
      setDirty(false);
      setApproved(false);
      setNotice("Rascunho gerado e salvo. Revise o conteúdo antes de aprovar.");
      await load(0);
    } catch (error) {
      setError(message(error));
    } finally {
      setBusy(false);
    }
  }
  async function save(approve: boolean) {
    if (!saved || !editing || (approve && !approved)) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const item = await api.review(saved, editing, approve);
      setSaved(item);
      setEditing(structuredClone(item.material));
      setDirty(false);
      setApproved(false);
      setNotice(
        approve
          ? "Material revisado, aprovado e salvo."
          : "Revisão salva como rascunho.",
      );
      await load(0);
    } catch (error) {
      setError(message(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="education-studio"
      aria-label="Criação e revisão de materiais"
    >
      <div className="card">
        <h3>Da ideia ao material revisado</h3>
        <p>
          Gere com a IA local, revise as informações e aprove a versão que
          deseja utilizar.
        </p>
        <label>
          Chave de acesso da escola (se exigida)
          <input
            className="input"
            type="password"
            autoComplete="off"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            disabled={busy || loading}
          />
        </label>
        <form onSubmit={generate}>
          <fieldset disabled={busy}>
            <div className="grid-2">
              <label>
                Material
                <select
                  className="input"
                  aria-label="Material"
                  value={form.material_type}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      material_type: event.target.value as MaterialType,
                    })
                  }
                >
                  {Object.entries(NAMES).map(([value, name]) => (
                    <option key={value} value={value}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Ano escolar
                <select
                  className="input"
                  aria-label="Ano escolar"
                  value={form.academic_year}
                  onChange={(event) =>
                    setForm({ ...form, academic_year: event.target.value })
                  }
                >
                  {Object.entries(YEARS).map(([value, name]) => (
                    <option key={value} value={value}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label>
              Tema
              <input
                className="input"
                value={form.topic}
                onChange={(event) =>
                  setForm({ ...form, topic: event.target.value })
                }
                required
                minLength={3}
                maxLength={500}
                placeholder="Ex.: fontes históricas e memória da comunidade"
              />
            </label>
            <label>
              Duração em minutos
              <input
                className="input"
                type="number"
                min={1}
                max={240}
                value={form.duration_minutes}
                onChange={(event) =>
                  setForm({
                    ...form,
                    duration_minutes: Number(event.target.value),
                  })
                }
                required
              />
            </label>
            <label>
              Objetivos de aprendizagem (um por linha)
              <textarea
                className="input"
                value={objectives}
                onChange={(event) => setObjectives(event.target.value)}
                rows={3}
              />
            </label>
            <label>
              Habilidades BNCC (opcional)
              <input
                className="input"
                value={skills}
                onChange={(event) => setSkills(event.target.value)}
                placeholder="Ex.: EF06HI02 para o 6º ano"
              />
            </label>
            <label>
              Orientações para a criação
              <textarea
                className="input"
                value={form.instructions}
                onChange={(event) =>
                  setForm({ ...form, instructions: event.target.value })
                }
                maxLength={3000}
                rows={3}
              />
            </label>
            <button className="btn btn-primary" type="submit">
              {busy ? "Processando…" : "Gerar e salvar rascunho"}
            </button>
          </fieldset>
        </form>
        <p className="metric-sub">
          A geração precisa do Ollama ativo e de um modelo instalado no
          servidor. Confira fatos, gabaritos e adequação à turma.
        </p>
      </div>
      {error && (
        <p role="alert" className="studio-error">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="studio-notice">
          {notice}
        </p>
      )}
      {editing && saved && (
        <section className="card" aria-label="Revisão do material">
          <h3>Revisão do professor</h3>
          <p>
            {NAMES[saved.material_type]} ·{" "}
            {YEARS[editing.academic_year] || editing.academic_year} ·{" "}
            {saved.material.status === "aprovado" ? "Aprovado" : "Rascunho"}
            {dirty ? " · Alterações não salvas" : ""}
          </p>
          <fieldset disabled={busy}>
            <label>
              Título
              <input
                className="input"
                value={editing.title}
                onChange={(event) => edit({ title: event.target.value })}
                maxLength={200}
              />
            </label>
            <label>
              Duração em minutos
              <input
                className="input"
                type="number"
                min={1}
                value={editing.duration_minutes}
                onChange={(event) =>
                  edit({ duration_minutes: Number(event.target.value) })
                }
              />
            </label>
            {saved.material_type === "lesson_plan" && (
              <>
                <label>
                  Objetivos
                  <textarea
                    className="input"
                    rows={3}
                    value={(editing.learning_objectives || []).join("\n")}
                    onChange={(event) =>
                      edit({
                        learning_objectives: event.target.value.split("\n"),
                      })
                    }
                  />
                </label>
                {(editing.moments || []).map((moment, index) => (
                  <div key={index} className="studio-item">
                    <label>
                      Momento {index + 1} — título
                      <input
                        className="input"
                        value={moment.title}
                        onChange={(event) =>
                          edit({
                            moments: editing.moments!.map((item, i) =>
                              i === index
                                ? { ...item, title: event.target.value }
                                : item,
                            ),
                          })
                        }
                      />
                    </label>
                    <label>
                      Conteúdo e condução
                      <textarea
                        className="input"
                        rows={5}
                        value={moment.description}
                        onChange={(event) =>
                          edit({
                            moments: editing.moments!.map((item, i) =>
                              i === index
                                ? { ...item, description: event.target.value }
                                : item,
                            ),
                          })
                        }
                      />
                    </label>
                    <label>
                      Duração do momento (minutos)
                      <input
                        className="input"
                        type="number"
                        min={1}
                        value={moment.duration_minutes}
                        onChange={(event) =>
                          edit({
                            moments: editing.moments!.map((item, i) =>
                              i === index
                                ? {
                                    ...item,
                                    duration_minutes: Number(
                                      event.target.value,
                                    ),
                                  }
                                : item,
                            ),
                          })
                        }
                      />
                    </label>
                    <label>
                      Metodologia
                      <textarea
                        className="input"
                        rows={2}
                        value={moment.methodology}
                        onChange={(event) =>
                          edit({
                            moments: editing.moments!.map((item, i) =>
                              i === index
                                ? { ...item, methodology: event.target.value }
                                : item,
                            ),
                          })
                        }
                      />
                    </label>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() =>
                        edit({
                          moments: editing.moments!.filter(
                            (_, i) => i !== index,
                          ),
                        })
                      }
                    >
                      Remover momento
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() =>
                    edit({
                      moments: [
                        ...(editing.moments || []),
                        {
                          moment: "DESENVOLVIMENTO",
                          title: "",
                          description: "",
                          duration_minutes: 15,
                          methodology: "",
                          resources: [],
                          order: editing.moments?.length || 0,
                        },
                      ],
                    })
                  }
                >
                  Adicionar momento pedagógico
                </button>
                <label>
                  Recursos (um por linha)
                  <textarea
                    className="input"
                    value={(editing.resources || []).join("\n")}
                    onChange={(event) =>
                      edit({ resources: event.target.value.split("\n") })
                    }
                  />
                </label>
                <label>
                  Avaliação da aprendizagem
                  <textarea
                    className="input"
                    value={editing.assessment_type || ""}
                    onChange={(event) =>
                      edit({ assessment_type: event.target.value })
                    }
                  />
                </label>
              </>
            )}
            {saved.material_type === "activity" && (
              <>
                <label>
                  Descrição
                  <textarea
                    className="input"
                    value={editing.description || ""}
                    onChange={(event) =>
                      edit({ description: event.target.value })
                    }
                  />
                </label>
                <label>
                  Atividade para a turma
                  <textarea
                    className="input"
                    rows={10}
                    value={String(editing.content?.text || "")}
                    onChange={(event) =>
                      edit({
                        content: {
                          ...editing.content,
                          text: event.target.value,
                        },
                      })
                    }
                  />
                </label>
              </>
            )}
            {saved.material_type !== "lesson_plan" && (
              <label>
                Instruções
                <textarea
                  className="input"
                  rows={3}
                  value={editing.instructions || ""}
                  onChange={(event) =>
                    edit({ instructions: event.target.value })
                  }
                />
              </label>
            )}
            {saved.material_type === "evaluation" && (
              <>
                <div className="grid-2">
                  <label>
                    Pontuação total
                    <input
                      className="input"
                      type="number"
                      min={0}
                      step="any"
                      value={editing.total_score}
                      onChange={(event) =>
                        edit({ total_score: Number(event.target.value) })
                      }
                    />
                  </label>
                  <label>
                    Nota para aprovação
                    <input
                      className="input"
                      type="number"
                      min={0}
                      step="any"
                      value={editing.passing_score}
                      onChange={(event) =>
                        edit({ passing_score: Number(event.target.value) })
                      }
                    />
                  </label>
                </div>
                {(editing.questions || []).map((question, index) => (
                  <div key={index} className="studio-item">
                    <label>
                      Questão {index + 1}
                      <textarea
                        className="input"
                        rows={3}
                        value={question.command}
                        onChange={(event) =>
                          edit({
                            questions: editing.questions!.map((item, i) =>
                              i === index
                                ? { ...item, command: event.target.value }
                                : item,
                            ),
                          })
                        }
                      />
                    </label>
                    <label>
                      Alternativas (uma por linha)
                      <textarea
                        className="input"
                        rows={3}
                        value={question.options.join("\n")}
                        onChange={(event) =>
                          edit({
                            questions: editing.questions!.map((item, i) =>
                              i === index
                                ? {
                                    ...item,
                                    options: event.target.value.split("\n"),
                                  }
                                : item,
                            ),
                          })
                        }
                      />
                    </label>
                    <label>
                      Gabarito
                      <input
                        className="input"
                        value={question.correct_answer}
                        onChange={(event) =>
                          edit({
                            questions: editing.questions!.map((item, i) =>
                              i === index
                                ? {
                                    ...item,
                                    correct_answer: event.target.value,
                                  }
                                : item,
                            ),
                          })
                        }
                      />
                    </label>
                    <label>
                      Comentário do gabarito
                      <textarea
                        className="input"
                        rows={2}
                        value={question.feedback}
                        onChange={(event) =>
                          edit({
                            questions: editing.questions!.map((item, i) =>
                              i === index
                                ? { ...item, feedback: event.target.value }
                                : item,
                            ),
                          })
                        }
                      />
                    </label>
                    <label>
                      Pontos
                      <input
                        className="input"
                        type="number"
                        min={0}
                        step="any"
                        value={question.score}
                        onChange={(event) =>
                          edit({
                            questions: editing.questions!.map((item, i) =>
                              i === index
                                ? { ...item, score: Number(event.target.value) }
                                : item,
                            ),
                          })
                        }
                      />
                    </label>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() =>
                        edit({
                          questions: editing.questions!.filter(
                            (_, i) => i !== index,
                          ),
                        })
                      }
                    >
                      Remover questão
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() =>
                    edit({
                      questions: [
                        ...(editing.questions || []),
                        {
                          number: (editing.questions?.length || 0) + 1,
                          type: "DISCURSIVA",
                          command: "",
                          options: [],
                          correct_answer: "",
                          score: 1,
                          skill_code: "",
                          feedback: "",
                        },
                      ],
                    })
                  }
                >
                  Adicionar questão
                </button>
              </>
            )}
            <label className="studio-approval">
              <input
                type="checkbox"
                checked={approved}
                onChange={(event) => setApproved(event.target.checked)}
              />{" "}
              Revisei o conteúdo, o gabarito quando aplicável e a adequação à
              turma.
            </label>
            <div className="studio-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => void save(false)}
              >
                Salvar revisão como rascunho
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={!approved}
                onClick={() => void save(true)}
              >
                Aprovar e salvar
              </button>
            </div>
          </fieldset>
        </section>
      )}
      <section className="card" aria-label="Materiais salvos">
        <div className="studio-actions">
          <h3>Materiais salvos</h3>
          <button
            className="btn btn-ghost"
            disabled={busy || loading}
            onClick={() => void load(0)}
          >
            {loading ? "Carregando…" : "Atualizar acervo"}
          </button>
        </div>
        {listError && (
          <p role="alert" className="studio-error">
            {listError}
          </p>
        )}
        {!loading && !listError && items.length === 0 && (
          <p>Nenhum material salvo nesta página.</p>
        )}
        {items.map((item) => (
          <div
            key={`${item.material_type}-${item.material.id}`}
            className="studio-saved"
          >
            <div>
              <strong>{item.material.title}</strong>
              <p>
                {NAMES[item.material_type]} ·{" "}
                {YEARS[item.material.academic_year] ||
                  item.material.academic_year}{" "}
                ·{" "}
                {item.material.status === "aprovado" ? "Aprovado" : "Rascunho"}
              </p>
            </div>
            <button
              className="btn btn-ghost"
              disabled={busy}
              onClick={() => open(item)}
            >
              Abrir para revisão
            </button>
          </div>
        ))}
        <div className="studio-actions">
          <button
            className="btn btn-ghost"
            disabled={busy || loading || offset === 0}
            onClick={() => void load(Math.max(0, offset - 20))}
          >
            Anterior
          </button>
          <button
            className="btn btn-ghost"
            disabled={busy || loading || items.length < 20}
            onClick={() => void load(offset + 20)}
          >
            Próxima
          </button>
        </div>
      </section>
    </section>
  );
}
