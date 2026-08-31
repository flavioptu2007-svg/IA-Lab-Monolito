#!/usr/bin/env python3
"""READ-ONLY map: estado de ATIVIDADE COMPLEMENTAR por turma no GRP vs coluna G da planilha.

NÃO escreve nada no GRP. Abre a avaliação apenas para ler a grade e sai sem salvar.

Usage:
  python scripts/readonly_map_ac.py
  python scripts/readonly_map_ac.py --turma "6º ANO ALFA"
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from grp_agent.browser import BrowserSession
from grp_agent.real_grp_audit import navigate_to_grades_page

EXCEL_PATH = "/home/flavio/Trabalho/Secretária/PROVAS 2026 2/Notas AGT e Ciclo 2 - Trimestre 2.xlsx"
TARGET_DISCIPLINA = "HISTÓRIA"
TARGET_PERIODO = "2º TRIMESTRE"
GRP_URL = "https://sistemas.paracatu.mg.gov.br/GRP/home/sge/turmas-avaliacoes/resultadoavaliacao"

# sheet_name -> turma no GRP
TURMA_MAP = {
    "6º ANO A": "6º ANO ALFA",
    "6º ANO B": "6º ANO BETA",
    "6º ANO G": "6º ANO GAMA",
    "7º ANO A": "7º ANO ALFA",
    "7º ANO B": "7º ANO BETA",
    "7º ANO G": "7º ANO GAMA",
    "8º ANO A": "8º ANO ALFA",
}


def _sel(page, label, val):
    el = page.locator(f"label:has-text('{label}')").first
    if not el.count():
        return
    c = el.locator("xpath=ancestor::div[contains(@class, 'dx-field-item')]")
    sb = c.locator("dx-select-box").first
    if not sb.count():
        return
    hi = sb.locator("input[type='hidden']").first
    if hi.count() and val.lower() in (hi.get_attribute("value") or "").lower():
        return
    btn = sb.locator("[role='button']").first
    if btn.count():
        btn.click()
    else:
        vi = sb.locator("input[role='combobox']").first
        if vi.count():
            vi.click()
        else:
            sb.click()
    time.sleep(1)
    page.wait_for_timeout(500)
    opt = page.get_by_text(val, exact=True).filter(visible=True).first
    if opt.count():
        opt.click()
        time.sleep(0.5)


def _filtrar(page):
    btn = page.locator("dx-button:has-text('Filtrar')").first
    if btn.count():
        btn.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)


def read_evaluations_list(page) -> list[str]:
    """Read evaluation names from the evaluations list grid."""
    ev_names = {"conceito", "avaliação bimestral", "atividade complementar"}
    all_hg = page.locator(".dx-datagrid-headers")
    for gi in range(all_hg.count()):
        hg = all_hg.nth(gi)
        pg = hg.locator("xpath=ancestor::dx-data-grid[1]")
        if not pg.count():
            continue
        dr = pg.locator(".dx-datagrid-rowsview .dx-data-row")
        if dr.count() == 0:
            continue
        fc = dr.first.locator("td")
        texts = [fc.nth(i).inner_text().strip() for i in range(fc.count())]
        if any(t.lower() in ev_names for t in texts if t):
            # this is the evaluations list; eval name is in the first non-empty cell
            evals = []
            for i in range(dr.count()):
                cells = dr.nth(i).locator("td")
                for ci in range(cells.count()):
                    t = cells.nth(ci).inner_text().strip()
                    if t:
                        evals.append(t)
                        break
            return evals
    return []


def read_student_grid(page) -> list[dict]:
    students: list[dict] = []
    ev_names = {"conceito", "avaliação bimestral", "atividade complementar"}
    all_hg = page.locator(".dx-datagrid-headers")
    for gi in range(all_hg.count()):
        hg = all_hg.nth(gi)
        hc = hg.locator("td[role='columnheader']")
        name_col = reg_col = grade_col = sit_col = None
        for ci in range(hc.count()):
            a = (hc.nth(ci).get_attribute("aria-label") or "").lower()
            if "aluno" in a:
                name_col = ci
            elif "matricula" in a or "matrícula" in a:
                reg_col = ci
            elif "nota" in a:
                grade_col = ci
            elif "situa" in a:
                sit_col = ci
        if name_col is None or grade_col is None:
            continue
        pg = hg.locator("xpath=ancestor::dx-data-grid[1]")
        if not pg.count():
            continue
        dr = pg.locator(".dx-datagrid-rowsview .dx-data-row")
        if dr.count() == 0:
            continue
        fc = dr.first.locator("td")
        if fc.count() > name_col and fc.nth(name_col).inner_text().strip().lower() in ev_names:
            continue
        for i in range(dr.count()):
            row = dr.nth(i)
            cells = row.locator("td")
            if cells.count() <= name_col:
                continue
            name = cells.nth(name_col).inner_text().strip()
            if not name or name.lower() in ("aluno", "nome"):
                continue
            reg = cells.nth(reg_col).inner_text().strip() if reg_col is not None and cells.count() > reg_col else None
            sit = cells.nth(sit_col).inner_text().strip() if sit_col is not None and cells.count() > sit_col else None
            inputs = cells.nth(grade_col).locator("input")
            raw = inputs.first.input_value().strip() if inputs.count() else cells.nth(grade_col).inner_text().strip()
            gv = None
            if raw:
                try:
                    gv = float(raw.replace(",", "."))
                except ValueError:
                    gv = None
            students.append({"name": name, "registration": reg, "grade": gv, "situacao": sit})
        if students:
            break
    return students


def read_date_field(page) -> str | None:
    date_label = page.locator("label:has-text('Data')").first
    if not date_label.count():
        return None
    container = date_label.locator("xpath=ancestor::div[contains(@class, 'dx-field-item')]")
    datebox = container.locator("dx-date-box, .dx-datebox").first
    if not datebox.count():
        return None
    date_input = datebox.locator("input[role='combobox'], input.dx-texteditor-input, input[type='text']").first
    if not date_input.count():
        return None
    return date_input.input_value().strip() or None


def map_turma(page, sheet_name: str, turma: str) -> dict:
    print(f"--- {turma} ---")
    page.goto(GRP_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    _sel(page, "Escola", "CORACI")
    time.sleep(1)
    _sel(page, "Turma", turma)
    time.sleep(1)
    _sel(page, "Disciplina", TARGET_DISCIPLINA)
    time.sleep(1)
    _sel(page, "Período de Avaliação", TARGET_PERIODO)
    time.sleep(1)
    _filtrar(page)

    result: dict = {"turma": turma, "sheet": sheet_name}
    evals = read_evaluations_list(page)
    result["avaliacoes"] = evals
    print(f"  avaliações na lista: {evals or 'NENHUMA'}")

    if not any(TARGET_EVAL.lower() in e.lower() for e in evals):
        result["ac_exists"] = False
        print(f"  ⚠️ '{TARGET_EVAL}' não aparece na lista")
        return result

    result["ac_exists"] = True
    ec = page.locator(f".dx-data-row td:has-text('{TARGET_EVAL}')").first
    if not ec.count():
        result["erro"] = "linha da avaliação não localizada"
        return result
    ec.dblclick()
    time.sleep(3)
    page.wait_for_load_state("networkidle")

    result["data_campo"] = read_date_field(page)
    result["alunos"] = read_student_grid(page)
    print(f"  data no campo: {result['data_campo']}")
    print(f"  alunos no GRP: {len(result['alunos'])} "
          f"(com nota: {sum(1 for a in result['alunos'] if a['grade'] is not None)})")
    # sai sem salvar
    page.goto(GRP_URL, wait_until="domcontentloaded")
    return result


def main():
    global TARGET_EVAL
    parser = argparse.ArgumentParser(description="Mapa READ-ONLY de avaliação no GRP")
    parser.add_argument("--turma", help="Mapear apenas uma turma (nome GRP)")
    parser.add_argument("--avaliacao", default="ATIVIDADE COMPLEMENTAR",
                        help="Avaliação a mapear (ex.: 'CONCEITO')")
    args = parser.parse_args()
    TARGET_EVAL = args.avaliacao

    session = BrowserSession.start(headless=False, state_dir="state/playwright")
    try:
        page = session.open_grp()
        navigate_to_grades_page(page)
        time.sleep(2)
        # sanity: precisa haver filtro Escola na tela (senão é login)
        if not page.locator("label:has-text('Escola')").count():
            print("🔑 Login necessário — conclua o login na janela do navegador (aguardando até 3 min)...")
            for _ in range(36):
                time.sleep(5)
                try:
                    if page.locator("label:has-text('Escola')").count():
                        break
                    if "resultadoavaliacao" not in page.url:
                        navigate_to_grades_page(page)
                except Exception:  # noqa: BLE001
                    navigate_to_grades_page(page)
            if not page.locator("label:has-text('Escola')").count():
                print("❌ Login não concluído a tempo. Rode de novo após logar.")
                return

        turmas = [(s, t) for s, t in TURMA_MAP.items() if args.turma is None or t == args.turma]
        mapping = {}
        for sheet, turma in turmas:
            try:
                mapping[turma] = map_turma(page, sheet, turma)
            except Exception as e:  # noqa: BLE001
                mapping[turma] = {"turma": turma, "erro": str(e)}
                print(f"  ❌ erro: {e}")

        out = Path("artifacts/audit") / f"{TARGET_EVAL.replace(' ', '_').lower()}-mapping-{datetime.now().astimezone():%Y%m%d-%H%M%S}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nMapa salvo em: {out}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
