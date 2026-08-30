from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .browser import BrowserSession
from .calibration import capture_calibration
from .config import ARTIFACT_DIR, STATE_DIR, ensure_dirs
from .discovery import discover_schools
from .dom_analyzer import analyze_html, latest_calibration
from .excel import inspect_workbook
from .logging import audit_event

app = typer.Typer(no_args_is_help=True, help="Agente local de automação segura do GRPWeb/SGE")
console = Console()


def _mode(apply: bool) -> str:
    return "APPLY" if apply else "DRY-RUN"


def _column_letter_to_number(col: str) -> int:
    """Convert a column letter (e.g. 'L') or name (e.g. 'NOTA 1') to a 1-based number.

    If the input is already a number string, return it directly.
    """
    col = col.strip()
    # Pure number
    if col.isdigit():
        return int(col)
    # Letter(s) like 'L', 'AA'
    if col.isalpha():
        result = 0
        for ch in col.upper():
            result = result * 26 + (ord(ch) - ord('A') + 1)
        return result
    # Named column — return 0 to signal caller should use detect_headers
    return 0


@app.command()
def discover():
    """Abrir o GRP e descobrir escolas disponíveis na sessão autenticada."""
    ensure_dirs()
    console.print("[bold]Modo: DISCOVERY[/bold]")
    console.print("Se o login aparecer, conclua-o manualmente no navegador aberto.")
    session = BrowserSession.start(headless=False, state_dir=STATE_DIR)
    try:
        page = session.open_grp()
        schools = discover_schools(page)
        table = Table("Escola")
        for school in schools:
            table.add_row(school)
        console.print(table)
        audit_event("discover_schools", schools=schools)
    finally:
        session.close()


@app.command()
def calibrate():
    """Abrir o GRP e capturar o DOM da tela autenticada para calibrar seletores."""
    ensure_dirs()
    console.print("[bold]Modo: CALIBRAÇÃO[/bold]")
    console.print("Faça o login no GRP e deixe aberta a tela que deseja automatizar.")
    session = BrowserSession.start(headless=False, state_dir=STATE_DIR)
    try:
        page = session.open_grp()
        console.print("Navegue até a tela desejada e pressione Enter aqui no terminal.")
        input()
        folder = capture_calibration(page)
        console.print(f"Captura salva em: {folder}")
        audit_event("calibration_captured", path=str(folder), url=page.url)
    finally:
        session.close()


@app.command()
def inspect_dom(
    html_file: Path = typer.Option(None, "--html", exists=False, readable=True),  # noqa: B008
):
    """Analisar uma captura HTML local e gerar inventário de controles."""
    ensure_dirs()
    target = html_file
    if target is None:
        target = latest_calibration(ARTIFACT_DIR / "calibration")
    if target is None or not target.exists():
        raise typer.BadParameter("nenhuma captura page.html encontrada; execute calibrate primeiro")
    report = analyze_html(target)
    out = ARTIFACT_DIR / "calibration" / "dom-inventory.txt"
    out.write_text(report, encoding="utf-8")
    console.print(report)
    console.print(f"Inventário salvo em: {out}")
    audit_event("dom_inspected", html=str(target), report=str(out))


@app.command()
def audit():
    """Executar uma auditoria inicial sem alterar dados."""
    ensure_dirs()
    console.print("[bold]Modo: DRY-RUN[/bold]")
    console.print("Auditoria de leitura do ambiente GRP; nenhuma alteração será salva.")
    audit_event("audit_started", mode="dry-run")
    console.print("A auditoria detalhada de cada módulo é habilitada após a descoberta da sessão autenticada.")


@app.command("audit-preview")
def audit_preview(
    file: Path = typer.Option(..., "--file", exists=True, readable=True),  # noqa: B008
    grade_column: str = typer.Option(..., "--grade-column", help="Coluna com as notas na planilha (ex: F, G, NOTA 1)"),
):
    """Comparar notas do Excel com o GRP e gerar prévia sem alterar nada."""
    ensure_dirs()
    from .grade_engine import parse_grades
    from .grp_audit import generate_audit_preview, read_grp_context, read_grp_grades
    from .models import StudentRef

    console.print("[bold]Modo: AUDITORIA / PRÉVIA[/bold]")
    console.print("Nenhuma alteração será salva no GRP.")

    # Parse Excel
    if not file.exists():
        raise typer.BadParameter(f"arquivo não encontrado: {file}", param_hint="--file")

    # Resolve column letter to number
    col_num = _column_letter_to_number(grade_column)
    grades = parse_grades(file, grade_column=col_num)
    console.print(f"Planilha: {len(grades)} alunos carregados da coluna {grade_column}")

    # Connect to GRP
    session = BrowserSession.start(headless=False, state_dir=STATE_DIR)
    try:
        page = session.open_grp()
        console.print("Navegue até a tela de avaliações no GRP e pressione Enter aqui.")
        input()

        ctx = read_grp_context(page)
        grp_grades = read_grp_grades(page)
        console.print(f"GRP: {ctx.class_name} — {ctx.subject} — {ctx.period} — {len(grp_grades)} alunos")

        # Build comparison data
        excel_students = [StudentRef(name=g.name) for g in grades]
        excel_grades_dict = {
            g.name: float(g.value)
            for g in grades
            if isinstance(g.value, (int, float))
        }

        preview = generate_audit_preview(ctx, excel_students, excel_grades_dict, grp_grades)

        # Display results
        table = Table("Aluno", "Tipo", "GRP", "Excel")
        for item in preview.diff.items:
            old = str(item.old_value) if item.old_value is not None else "—"
            new = str(item.new_value) if item.new_value is not None else "—"
            table.add_row(item.student, item.change_type, old, new)
        console.print(table)

        if preview.blocked:
            console.print(f"[bold red]BLOQUEADO[/bold red] — {sum(1 for i in preview.diff.items if i.change_type == 'not_found')} aluno(s) não encontrado(s) no GRP")
        elif preview.has_changes:
            console.print(f"[bold yellow]{preview.changes_count} alteração(ões) detectada(s)[/bold yellow]")
        else:
            console.print("[bold green]Nenhuma alteração necessária[/bold green]")

        audit_event(
            "audit_preview",
            file=str(file),
            changes=preview.changes_count,
            blocked=preview.blocked,
        )
    finally:
        session.close()


@app.command()
def grades(
    file: Path = typer.Option(..., "--file", exists=False, readable=True),  # noqa: B008
    period: str = typer.Option(..., "--period"),
    evaluation: str = typer.Option("AVALIAÇÃO BIMESTRAL", "--evaluation"),
    column: str = typer.Option("L", "--column"),
    apply: bool = typer.Option(False, "--apply", help="Permite preparar execução de escrita; ainda exige confirmação."),
):
    """Ler notas do Excel e preparar lançamento no GRP."""
    ensure_dirs()
    console.print(f"[bold]{_mode(apply)}[/bold] — período: {period} — avaliação: {evaluation} — coluna: {column}")
    console.print("Sem --apply, nenhuma escrita no GRP é permitida. Com --apply, o contexto ainda precisa ser confirmado.")
    if not file.exists():
        raise typer.BadParameter(f"arquivo não encontrado: {file}", param_hint="--file")
    inspection = inspect_workbook(file, source_column=column)
    table = Table("Aba", "Alunos", "Sem valor", "Não numérico")
    for name in inspection.sheet_names:
        item = inspection.sheets[name]
        table.add_row(name, str(item.student_rows), str(item.missing_values), str(item.non_numeric_values))
    console.print(table)
    audit_event("grades_inspected", file=str(file), period=period, evaluation=evaluation, column=column, apply=apply)


@app.command()
def lessons():
    """Auditar/registrar aulas; escrita requer confirmação no módulo."""
    console.print("Registro de aulas: modo de leitura preparado; escrita requer calibração da sessão autenticada.")


@app.command()
def attendance():
    """Auditar/registrar frequência; escrita requer confirmação no módulo."""
    console.print("Frequência: modo de leitura preparado; escrita requer calibração da sessão autenticada.")


@app.command()
def reports():
    """Listar a área de artefatos destinada aos relatórios baixados."""
    ensure_dirs()
    console.print(f"Relatórios serão organizados em: {ARTIFACT_DIR}")






@app.command("inspect-workbook")
def inspect_workbook_cmd(file: Path = typer.Option(..., "--file", exists=True, readable=True)):  # noqa: B008
    """Analisar uma planilha flexível por cabeçalhos, sem escrever no GRP."""
    from .workbook_flexible import inspect_workbook

    result = inspect_workbook(file)
    console.print_json(json.dumps(result, ensure_ascii=False, indent=2))
    audit_event("workbook_inspected", file=str(file), sheets=len(result))
if __name__ == "__main__":
    app()
