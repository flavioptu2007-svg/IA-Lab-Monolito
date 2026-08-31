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
    sheet: str = typer.Option(None, "--sheet", help="Limitar a análise a uma aba/turma"),
    target_max: float = typer.Option(None, "--target-max", help="Escala de destino (ex: 10). Sem este parâmetro nenhuma conversão é feita."),
    final_column: str = typer.Option(None, "--final-column", help="MODO MANUAL: força a coluna da nota final (não é regra de negócio)"),
    compare_grp: bool = typer.Option(False, "--compare-grp", help="Após a análise, abrir o GRP (SOMENTE LEITURA) para comparar notas existentes"),
    save_json: bool = typer.Option(True, "--save-json / --no-save-json", help="Salvar relatório JSON em artifacts/audit"),
):
    """Simulação de lançamento a partir da planilha — NUNCA escreve no GRP.

    Modo padrão: 100% offline. Analisa cada aba por estrutura semântica
    (cabeçalhos, blocos e fórmulas), identifica turma, alunos, fontes de nota,
    regra de cálculo e escalas. Nenhuma posição de coluna é assumida.
    Regra insuficiente ou ambiguidade não resolvida => aluno/aba BLOQUEADO.
    """
    ensure_dirs()
    from .audit_preview import analyze_workbook, audit_to_dict

    console.print("[bold]Modo: SIMULAÇÃO / AUDIT-PREVIEW (somente leitura)[/bold]")
    console.print("[yellow]Nenhuma escrita no GRP é possível neste comando — nem com flags.[/yellow]")

    audit = analyze_workbook(
        file,
        target_scale=target_max,
        final_column=final_column,
    )
    sheets = [s for s in audit.sheets if sheet is None or s.sheet == sheet]

    for s in sheets:
        header = f"[bold underline]{s.sheet}[/bold underline]"
        if s.turma:
            header += f" — turma: {s.turma}"
        if s.period:
            header += f" — período declarado: {s.period}"
        console.print(f"\n{header}")
        console.print(
            f"cabeçalho na linha {s.header_row}; aluno na coluna {s.student_column}; "
            f"matrícula: {s.registration_column or '—'}"
        )

        fontes = Table("Fonte", "Coluna", "Escala", show_header=True)
        for f in s.sources:
            fontes.add_row(f.label, f.column_letter, f"{f.max_value:g}" if f.max_value else "bruta")
        console.print(fontes)

        if s.final_column:
            fc = s.final_column
            destino = f"{target_max:g}" if target_max else "não configurada"
            console.print(
                f"[green]nota final: coluna {fc.column_letter} — regra {fc.formula} "
                f"(escala de origem {fc.scale:g} → destino {destino})[/green]"
            )
        else:
            console.print("[red]nota final: NÃO DETERMINÁVEL — aba BLOQUEADA[/red]")

        alunos = Table("Aluno", "Cálculo", "Escala", "Nota", "Status", show_header=True)
        for st in s.students:
            escala = (
                f"{st.scale_from:g}→{f'{st.scale_to:g}' if st.scale_to else '?'}"
                if st.scale_from
                else "—"
            )
            alunos.add_row(
                st.name,
                st.calculation or "—",
                escala,
                f"{st.final_value:g}" if st.final_value is not None else "—",
                st.status,
            )
        console.print(alunos)

        for msg in s.pendencias:
            console.print(f"[yellow]PENDÊNCIA:[/yellow] {msg}")
        for msg in s.ambiguidades:
            console.print(f"[magenta]AMBIGUIDADE:[/magenta] {msg}")
        console.print(
            f"resumo: {s.ok_count} OK · {s.pending_count} pendentes · "
            f"{s.blocked_count} bloqueados · {len(s.students)} alunos"
        )

    for msg in audit.pendencias:
        console.print(f"[yellow]PENDÊNCIA GLOBAL:[/yellow] {msg}")
    for msg in audit.ambiguidades:
        console.print(f"[magenta]AMBIGUIDADE GLOBAL:[/magenta] {msg}")

    if save_json:
        out_dir = ARTIFACT_DIR / "audit"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = audit.generated_at.replace(":", "").replace("-", "")
        out = out_dir / f"audit-preview-{stamp}.json"
        out.write_text(
            json.dumps(audit_to_dict(audit), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        console.print(f"\nRelatório JSON salvo em: {out}")

    audit_event(
        "audit_preview_offline",
        file=str(file),
        sheets=len(sheets),
        target_scale=target_max,
        wrote_to_grp=False,
    )

    if compare_grp:
        _compare_with_grp(file, final_column, target_max)


def _compare_with_grp(file: Path, final_column: str | None, target_max: float | None) -> None:
    """Fluxo opcional SOMENTE LEITURA: compara prévia com notas já existentes no GRP."""
    from .audit_preview import analyze_workbook
    from .grp_audit import generate_audit_preview, read_grp_context, read_grp_grades
    from .models import StudentRef

    console.print("\n[bold]Modo adicional: COMPARAÇÃO GRP (somente leitura)[/bold]")
    audit = analyze_workbook(file, target_scale=target_max, final_column=final_column)

    session = BrowserSession.start(headless=False, state_dir=STATE_DIR)
    try:
        page = session.open_grp()
        console.print("Navegue até a tela de avaliações no GRP e pressione Enter aqui.")
        input()

        ctx = read_grp_context(page)
        grp_grades = read_grp_grades(page)
        console.print(f"GRP: {ctx.class_name} — {ctx.subject} — {ctx.period} — {len(grp_grades)} alunos")

        for s in audit.sheets:
            if s.final_column is None:
                continue
            excel_students = [
                StudentRef(name=st.name) for st in s.students if st.final_value is not None
            ]
            excel_grades = {
                st.name: st.final_value for st in s.students if st.final_value is not None
            }
            preview = generate_audit_preview(ctx, excel_students, excel_grades, grp_grades)
            table = Table(f"{s.sheet}: Aluno", "Tipo", "GRP", "Planilha")
            for item in preview.diff.items:
                old = str(item.old_value) if item.old_value is not None else "—"
                new = str(item.new_value) if item.new_value is not None else "—"
                table.add_row(item.student, item.change_type, old, new)
            console.print(table)
            if preview.blocked:
                console.print(
                    f"[red]{s.sheet}: BLOQUEADO[/red] — aluno(s) da planilha não encontrado(s) no GRP"
                )
        audit_event("audit_preview_compare_grp", file=str(file), wrote_to_grp=False)
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
    """[MODO LEGADO/MANUAL] Inspecionar notas do Excel por coluna fixa.

    AVISO DE SEGURANÇA: a coluna fixa (padrão 'L') NÃO é regra de negócio —
    a posição da nota varia entre planilhas. Este comando existe apenas para
    inspeção manual e compatibilidade. O fluxo padrão do agente é o motor
    flexível: use 'grp-agent audit-preview --file <arquivo>'.
    """
    ensure_dirs()
    console.print("[bold red]⚠ MODO LEGADO/MANUAL[/bold red] — coluna fixa não é regra de negócio.")
    if column.upper() == "L":
        console.print("[red]A coluna 'L' é apenas o padrão legado; a nota pode estar em qualquer coluna.[/red]")
    console.print("[dim]Fluxo padrão (motor flexível): grp-agent audit-preview --file <arquivo>[/dim]")
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
