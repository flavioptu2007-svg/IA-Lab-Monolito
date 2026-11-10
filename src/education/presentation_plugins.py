"""Plugins locais de exportação: HTML offline e PowerPoint editável."""

from __future__ import annotations

import html
from importlib.util import find_spec
from io import BytesIO
from typing import Any

from src.education.presentation_models import PresentationResponse


def available_plugins() -> list[dict[str, Any]]:
    return [
        {
            "id": "html_slides",
            "name": "Slides HTML offline",
            "license": "Código do projeto",
            "installed": True,
            "cost": "local",
            "format": "html",
        },
        {
            "id": "python_pptx",
            "name": "PowerPoint editável (python-pptx)",
            "license": "MIT",
            "installed": find_spec("pptx") is not None,
            "cost": "local",
            "format": "pptx",
        },
    ]


YEAR_LABELS = {
    "EF_6": "6º ano",
    "EF_7": "7º ano",
    "EF_8": "8º ano",
    "EF_9": "9º ano",
    "EM": "Ensino médio",
}


def export_html(deck: PresentationResponse) -> bytes:
    escape = html.escape
    pages = []
    for number, slide in enumerate(deck.slides, 1):
        bullets = "".join(f"<li>{escape(value)}</li>" for value in slide.bullets)
        sources = " · ".join(escape(value) for value in slide.sources)
        draft = (
            "Rascunho · revisão pendente"
            if deck.status != "aprovado"
            else "Revisado pelo professor"
        )
        pages.append(
            f'<article class="slide {slide.layout}" aria-label="Slide {number}: {escape(slide.title, quote=True)}">'
            f"<header><span>{escape(deck.subject)} / {escape(YEAR_LABELS.get(deck.academic_year, deck.academic_year))}</span><span>{draft}</span></header>"
            f'<div class="body"><p class="eyebrow">{number:02d} / {len(deck.slides):02d}</p>'
            f'<h1>{escape(slide.title)}</h1><p class="subtitle">{escape(slide.subtitle)}</p>'
            f"<ul>{bullets}</ul></div><footer><span>{sources}</span><span>{number:02d}</span></footer></article>"
            f'<details class="notes"><summary>Notas do apresentador — slide {number}</summary><p>{escape(slide.speaker_notes)}</p></details>'
        )
    paper = deck.theme == "paper"
    bg, fg, accent = (
        ("#F8FAFC", "#14213D", "#006B68") if paper else ("#111C32", "#F8FAFC", "#8DE4D4")
    )
    document = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(deck.title)}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#263247;color:{fg};font-family:Arial,Helvetica,sans-serif}}
.slide{{width:100%;aspect-ratio:16/9;background:{bg};padding:3% 6%;display:flex;flex-direction:column;break-after:page;position:relative;border-top:8px solid {accent};overflow:hidden}}
header,footer{{display:flex;justify-content:space-between;gap:20px;font-size:clamp(9px,1.2vw,17px)}}
header{{opacity:.85}}footer{{margin-top:auto;min-height:20px;align-items:end;font-size:clamp(8px,1vw,14px)}}footer span:first-child{{max-width:88%}}
.body{{padding:2% 0}}.eyebrow{{color:{accent};letter-spacing:.15em;font-size:clamp(10px,1.2vw,18px);margin:0 0 1.5%}}
h1{{font-size:clamp(22px,3.4vw,48px);line-height:1.15;margin:0 0 1.8%;max-width:96%;overflow-wrap:anywhere}}
.subtitle{{font-size:clamp(13px,1.65vw,24px);line-height:1.3;margin:0 0 2%;max-width:95%}}
ul{{padding-left:1.5em;margin:0;display:grid;gap:clamp(6px,1.4vw,20px)}}li{{font-size:clamp(12px,1.85vw,27px);line-height:1.3;padding-left:.25em;overflow-wrap:anywhere}}li::marker{{color:{accent}}}
.comparison ul{{grid-template-columns:1fr 1fr;column-gap:5%}}.title h1,.closing h1{{font-size:clamp(26px,4vw,58px);max-width:90%}}
.notes{{padding:16px;background:#fff;color:#14213D;white-space:pre-wrap}}.notes p{{max-width:1000px;line-height:1.6}}
@page{{size:13.333in 7.5in;margin:0}}@media print{{body{{background:none;print-color-adjust:exact;-webkit-print-color-adjust:exact}}.slide{{height:7.5in;width:13.333in}}.notes{{display:none}}}}
</style></head><body>{"".join(pages)}</body></html>"""
    return document.encode("utf-8")


def export_pptx(deck: PresentationResponse) -> bytes:
    """Texto, formas e notas nativos; sem depender de serviços ou imagens externas."""
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.enum.text import MSO_AUTO_SIZE
        from pptx.util import Inches, Pt
    except ImportError as exc:
        raise RuntimeError('Instale o plugin gratuito: pip install -e ".[presentations]"') from exc

    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    paper = deck.theme == "paper"
    bg, fg, accent = ("F8FAFC", "14213D", "006B68") if paper else ("111C32", "F8FAFC", "8DE4D4")

    def text(
        slide: Any,
        value: str,
        x: float,
        y: float,
        width: float,
        height: float,
        size: int,
        color: str = fg,
        bold: bool = False,
    ) -> None:
        shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height))
        frame = shape.text_frame
        frame.word_wrap = True
        frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        frame.margin_left = frame.margin_right = 0
        frame.margin_top = frame.margin_bottom = 0
        paragraph = frame.paragraphs[0]
        paragraph.text = value
        paragraph.font.name = "Aptos"
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = RGBColor.from_string(color)

    for index, item in enumerate(deck.slides, 1):
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(bg)
        rail = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, presentation.slide_width, Inches(0.08)
        )
        rail.fill.solid()
        rail.fill.fore_color.rgb = RGBColor.from_string(accent)
        rail.line.fill.background()
        text(
            slide,
            f"{deck.subject} / {YEAR_LABELS.get(deck.academic_year, deck.academic_year)}",
            0.7,
            0.35,
            7,
            0.35,
            13,
        )
        text(
            slide,
            "Revisado pelo professor"
            if deck.status == "aprovado"
            else "RASCUNHO — revisão pendente",
            8.0,
            0.35,
            4.5,
            0.35,
            12,
        )
        text(slide, f"{index:02d} / {len(deck.slides):02d}", 0.7, 0.92, 3, 0.35, 14, accent)
        text(slide, item.title, 0.7, 1.38, 11.9, 1.22, 36, bold=True)
        text(slide, " ".join(item.subtitle.split()), 0.7, 2.65, 11.9, 0.65, 20)
        for bullet_index, bullet in enumerate(item.bullets):
            if item.layout == "comparison":
                column, row = bullet_index % 2, bullet_index // 2
                x, y, width, height, size = 0.9 + column * 6.0, 3.4 + row * 1.35, 5.4, 1.25, 21
            else:
                x, y, width, height, size = 0.9, 3.3 + bullet_index * 0.82, 11.5, 0.8, 22
            text(slide, "• " + bullet, x, y, width, height, size)
        text(slide, " · ".join(item.sources), 0.7, 6.8, 11.2, 0.55, 9)
        text(slide, f"{index:02d}", 12.0, 6.8, 0.6, 0.35, 12, accent)
        slide.notes_slide.notes_text_frame.text = item.speaker_notes
    buffer = BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


EXPORTERS = {
    "html": (export_html, "text/html; charset=utf-8"),
    "pptx": (
        export_pptx,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
}
