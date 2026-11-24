import { Material, PresentationSlide } from "../api/educationStudio";

export function PresentationEditor({
  material,
  onChange,
}: {
  material: Material;
  onChange: (value: Partial<Material>) => void;
}) {
  const slides = material.slides || [];
  function update(index: number, values: Partial<PresentationSlide>) {
    onChange({
      slides: slides.map((slide, position) =>
        position === index ? { ...slide, ...values } : slide,
      ),
    });
  }
  function move(index: number, delta: number) {
    const next = [...slides];
    [next[index], next[index + delta]] = [next[index + delta], next[index]];
    onChange({ slides: next });
  }
  return (
    <section aria-label="Revisão dos slides">
      <label>
        Tema visual
        <select
          className="input"
          value={material.theme || "navy"}
          onChange={(event) =>
            onChange({ theme: event.target.value as "navy" | "paper" })
          }
        >
          <option value="navy">Azul profundo</option>
          <option value="paper">Papel claro</option>
        </select>
      </label>
      {slides.map((slide, index) => (
        <section key={index} className="studio-item" style={{ marginTop: 16 }}>
          <h4>Slide {index + 1}</h4>
          <div
            className={`slide-preview ${material.theme === "paper" ? "slide-preview-paper" : ""}`}
            aria-label={`Prévia do slide ${index + 1}`}
          >
            <small>
              {index + 1} / {slides.length}
            </small>
            <h3>{slide.title}</h3>
            <p>{slide.subtitle}</p>
            <ul>
              {slide.bullets.map((bullet, number) => (
                <li key={number}>{bullet}</li>
              ))}
            </ul>
          </div>
          <label>
            Layout
            <select
              className="input"
              aria-label={`Layout do slide ${index + 1}`}
              value={slide.layout}
              onChange={(event) =>
                update(index, {
                  layout: event.target.value as PresentationSlide["layout"],
                })
              }
            >
              <option value="title">Abertura</option>
              <option value="content">Conteúdo</option>
              <option value="comparison">Comparação</option>
              <option value="closing">Fechamento</option>
            </select>
          </label>
          <label>
            Título do slide {index + 1}
            <input
              className="input"
              value={slide.title}
              maxLength={80}
              onChange={(event) => update(index, { title: event.target.value })}
            />
          </label>
          <label>
            Subtítulo do slide {index + 1}
            <textarea
              className="input"
              value={slide.subtitle}
              maxLength={180}
              onChange={(event) =>
                update(index, { subtitle: event.target.value })
              }
            />
          </label>
          <label>
            Tópicos do slide {index + 1} (até 4; um por linha)
            <textarea
              className="input"
              rows={4}
              value={slide.bullets.join("\n")}
              onChange={(event) =>
                update(index, { bullets: event.target.value.split("\n") })
              }
            />
          </label>
          <label>
            Notas do apresentador — slide {index + 1}
            <textarea
              className="input"
              rows={4}
              value={slide.speaker_notes}
              maxLength={3000}
              onChange={(event) =>
                update(index, { speaker_notes: event.target.value })
              }
            />
          </label>
          <label>
            Fontes do slide {index + 1} (até 3; uma por linha)
            <textarea
              className="input"
              value={slide.sources.join("\n")}
              onChange={(event) =>
                update(index, { sources: event.target.value.split("\n") })
              }
            />
          </label>
          <div className="studio-actions">
            <button
              type="button"
              className="btn btn-ghost"
              disabled={index === 0}
              onClick={() => move(index, -1)}
            >
              Mover para cima
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={index === slides.length - 1}
              onClick={() => move(index, 1)}
            >
              Mover para baixo
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={slides.length <= 3}
              onClick={() =>
                onChange({
                  slides: slides.filter((_, number) => number !== index),
                })
              }
            >
              Remover slide
            </button>
          </div>
        </section>
      ))}
      <button
        type="button"
        className="btn btn-ghost"
        disabled={slides.length >= 20}
        onClick={() =>
          onChange({
            slides: [
              ...slides,
              {
                layout: "content",
                title: "Novo slide",
                subtitle: "",
                bullets: [],
                speaker_notes: "",
                sources: [],
              },
            ],
          })
        }
      >
        Adicionar slide
      </button>
      <p className="metric-sub">
        Uma ideia por slide. Use até 110 caracteres por tópico e leve os
        detalhes para as notas.
      </p>
    </section>
  );
}
