#!/usr/bin/env python3
"""Lançamento ATIVIDADE COMPLEMENTAR (coluna G) — executa o plano revisado.

Lê artifacts/audit/ac-plan.json (gerado por scripts/plan_ac.py) e lança
apenas alunos com status LANCAR. NUNCA sobrescreve nota existente: o campo
é re-checado no momento da escrita.

Usage:
  python scripts/launch_ac.py --turma "6º ANO ALFA"                 # dry-run (sem navegador)
  python scripts/launch_ac.py --turma "6º ANO ALFA" --confirmar-lote
  python scripts/launch_ac.py --all --confirmar-lote
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
from grp_agent.calibration import capture_calibration
from grp_agent.real_grp_audit import navigate_to_grades_page

PLAN_PATH = Path("artifacts/audit/ac-plan.json")
TARGET_DISCIPLINA = "HISTÓRIA"
TARGET_PERIODO = "2º TRIMESTRE"
TARGET_EVAL = "ATIVIDADE COMPLEMENTAR"
TARGET_DATE = "31/08/2026"
CASAS = 2
TOLERANCIA = 0.011
GRP_URL = "https://sistemas.paracatu.mg.gov.br/GRP/home/sge/turmas-avaliacoes/resultadoavaliacao"


# ---------------------------------------------------------------------------
# DevExtreme helpers (mesmo padrão validado em scripts/batch_class_write_v2.py)
# ---------------------------------------------------------------------------
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


def _set_date(page, date_str: str) -> bool:
    date_label = page.locator("label:has-text('Data')").first
    if not date_label.count():
        print("    ⚠️ Campo 'Data' não encontrado")
        return False
    container = date_label.locator("xpath=ancestor::div[contains(@class, 'dx-field-item')]")
    datebox = container.locator("dx-date-box").first
    if not datebox.count():
        datebox = container.locator(".dx-datebox").first
    if not datebox.count():
        print("    ⚠️ DateBox não encontrado")
        return False
    date_input = datebox.locator("input[role='combobox'], input.dx-texteditor-input, input[type='text']").first
    if not date_input.count():
        print("    ⚠️ Input de data não encontrado")
        return False
    date_input.click()
    time.sleep(0.3)
    page.keyboard.press("Control+a")
    page.keyboard.type(date_str, delay=50)
    time.sleep(0.3)
    page.keyboard.press("Tab")
    time.sleep(0.5)
    print(f"    ✅ Data definida: {date_input.input_value()}")
    return True


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


def fmt_nota(v: float) -> str:
    return f"{v:.{CASAS}f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Fluxo por turma
# ---------------------------------------------------------------------------
def launch_turma(page, turma: str, items: list[dict], artifact_dir: Path) -> dict:
    before_dir = artifact_dir / "before"
    after_dir = artifact_dir / "after"
    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f"LANÇAMENTO AC: {turma} / {TARGET_DISCIPLINA} / {TARGET_PERIODO} / {TARGET_EVAL}")
    print("=" * 80)

    print(f"[1/7] Navegando para '{TARGET_EVAL}'...")
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
    btn = page.locator("dx-button:has-text('Filtrar')").first
    if btn.count():
        btn.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)

    ec = page.locator(f".dx-data-row td:has-text('{TARGET_EVAL}')").first
    if not ec.count():
        print(f"  ❌ Avaliação '{TARGET_EVAL}' não encontrada!")
        return {"error": "avaliação não encontrada"}
    ec.dblclick()
    time.sleep(3)
    page.wait_for_load_state("networkidle")
    print("  ✅ Avaliação aberta")

    print(f"[2/7] Verificando data (alvo {TARGET_DATE})...")
    cur = read_date_field(page)
    if cur and TARGET_DATE in cur:
        print(f"    ✅ Data já correta: {cur}")
    else:
        _set_date(page, TARGET_DATE)
    time.sleep(1)

    print("[3/7] Lendo grade atual (antes)...")
    grp_before = read_student_grid(page)
    grp_map = {s["name"]: s for s in grp_before}
    print(f"  {len(grp_before)} alunos no GRP")
    capture_calibration(page, destination=str(before_dir))

    # Elegíveis de fato: item LANCAR do plano + campo realmente vazio agora
    to_fill = []
    resultado_alunos = []
    for it in items:
        nome_grp = it["match"]
        ge = grp_map.get(nome_grp)
        rec = {
            "nome_planilha": it["nome_planilha"],
            "nome_grp": nome_grp,
            "matricula": ge["registration"] if ge else None,
            "nota_planilha": it["valor"],
            "nota_lancar": it["valor_lancar"],
            "nota_anterior": ge["grade"] if ge else None,
            "classificacao": it["classificacao"],
            "status": None,
            "erro": None,
        }
        if ge is None:
            rec["status"], rec["erro"] = "FALHA", "aluno não está na grid agora"
        elif ge["grade"] is not None:
            rec["status"], rec["erro"] = "BLOQUEADO", f"campo já tem nota {ge['grade']} (sem sobrescrita)"
        else:
            to_fill.append((it, ge, rec))
        resultado_alunos.append(rec)

    print(f"[4/7] A preencher: {len(to_fill)} | bloqueados agora: {len(resultado_alunos) - len(to_fill)}")
    if not to_fill:
        print("  ⚠️ Nada a preencher.")
        (artifact_dir / "resultado.json").write_text(
            json.dumps({"alunos": resultado_alunos}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"turma": turma, "lancados": 0}

    print("[5/7] Preenchendo aluno por aluno...")
    fill_ok = 0
    for i, (it, ge, rec) in enumerate(to_fill, 1):
        name = rec["nome_grp"]
        nota = rec["nota_lancar"]
        print(f"  [{i}/{len(to_fill)}] {name:<38} nota={fmt_nota(nota)} ...", end=" ", flush=True)

        cell = page.locator(f".dx-data-row td:has-text('{name}')").first
        if not cell.count():
            print("❌ linha não encontrada")
            rec["status"], rec["erro"] = "FALHA", "linha não encontrada"
            continue
        row = cell.locator("xpath=ancestor::tr[contains(@class, 'dx-data-row')]")
        grade_cell = row.locator("td[aria-roledescription='Editable']").last
        if not grade_cell.count():
            grade_cell = row.locator("td").last
        grade_cell.click()
        time.sleep(0.3)

        grade_input = grade_cell.locator("input[role='spinbutton'], input.dx-texteditor-input")
        if not grade_input.count():
            grade_input = grade_cell.locator("input:not([type='hidden'])")
        if grade_input.count():
            grade_input.fill(fmt_nota(nota))
        else:
            page.keyboard.type(fmt_nota(nota))
        time.sleep(0.2)
        # Tab commita o editor DevExtreme antes de passar para a próxima linha
        page.keyboard.press("Tab")
        time.sleep(0.3)
        rec["status"] = "PREENCHIDO"
        fill_ok += 1
        print("✅")

    print(f"\n  Preenchidos: {fill_ok}/{len(to_fill)}")
    if fill_ok == 0:
        return {"turma": turma, "lancados": 0, "erro": "nenhum preenchimento"}

    print("[6/7] Salvando (1 vez)...")
    save_btn = page.locator("dx-button:has-text('Salvar')").first
    if not save_btn.count():
        save_btn = page.locator("dx-button[aria-label='Salvar']").first
    if not save_btn.count():
        print("  ❌ Botão Salvar não encontrado — NADA FOI SALVO.")
        return {"turma": turma, "erro": "botão Salvar não encontrado"}
    save_btn.click()
    time.sleep(5)
    page.wait_for_load_state("networkidle")
    print("  ✅ SALVO")

    print("[7/7] Verificando (re-leitura)...")
    page.goto(GRP_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    _sel(page, "Turma", turma)
    time.sleep(1)
    _sel(page, "Disciplina", TARGET_DISCIPLINA)
    time.sleep(1)
    _sel(page, "Período de Avaliação", TARGET_PERIODO)
    time.sleep(1)
    btn = page.locator("dx-button:has-text('Filtrar')").first
    if btn.count():
        btn.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)
    ec = page.locator(f".dx-data-row td:has-text('{TARGET_EVAL}')").first
    if ec.count():
        ec.dblclick()
        time.sleep(3)
        page.wait_for_load_state("networkidle")
    capture_calibration(page, destination=str(after_dir))

    grp_after = {s["name"]: s for s in read_student_grid(page)}
    confirmados = falhas = 0
    for rec in resultado_alunos:
        if rec["status"] != "PREENCHIDO":
            continue
        ge2 = grp_after.get(rec["nome_grp"])
        if ge2 and ge2["grade"] is not None and abs(ge2["grade"] - rec["nota_lancar"]) <= TOLERANCIA:
            rec["status"] = "CONFIRMADO"
            rec["nota_posterior"] = ge2["grade"]
            confirmados += 1
        else:
            rec["status"] = "FALHA"
            rec["erro"] = f"esperado {rec['nota_lancar']}, encontrado {ge2['grade'] if ge2 else 'N/A'}"
            falhas += 1

    resumo = {
        "turma": turma,
        "avaliacao": TARGET_EVAL,
        "disciplina": TARGET_DISCIPLINA,
        "periodo": TARGET_PERIODO,
        "data": TARGET_DATE,
        "casas_decimais": CASAS,
        "total_plano": len(items),
        "preenchidos": fill_ok,
        "confirmados": confirmados,
        "falhas": falhas,
        "alunos": resultado_alunos,
    }
    (artifact_dir / "resultado.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print()
    print("=" * 80)
    print(f"RELATÓRIO: {turma} — preenchidos {fill_ok} | confirmados {confirmados} | falhas {falhas}")
    print(f"Artefatos: {artifact_dir}")
    print("=" * 80)
    return {"turma": turma, "lancados": fill_ok, "confirmados": confirmados, "falhas": falhas}


def main():
    global TARGET_EVAL, PLAN_PATH
    parser = argparse.ArgumentParser(description="Lançamento de avaliação no GRP")
    parser.add_argument("--turma", help="Nome GRP da turma (ex.: '6º ANO ALFA')")
    parser.add_argument("--all", action="store_true", help="Todas as turmas com itens LANCAR")
    parser.add_argument("--avaliacao", default="ATIVIDADE COMPLEMENTAR",
                        help="Avaliação a lançar (ex.: 'CONCEITO')")
    parser.add_argument("--plano", default="artifacts/audit/ac-plan.json",
                        help="Caminho do plano JSON")
    parser.add_argument("--confirmar-lote", action="store_true",
                        help="Sem esta flag, apenas mostra o que faria (dry-run, sem navegador)")
    args = parser.parse_args()
    TARGET_EVAL = args.avaliacao
    PLAN_PATH = Path(args.plano)

    if not PLAN_PATH.exists():
        print("Plano não encontrado; rode scripts/plan_ac.py antes.")
        return
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

    if args.all:
        turmas = [(t, p) for t, p in plan.items() if p["a_lancar"] > 0]
    elif args.turma:
        p = plan.get(args.turma)
        if p is None:
            print(f"Turma fora do plano: {args.turma}")
            return
        turmas = [(args.turma, p)]
    else:
        print("Uso: python scripts/launch_ac.py --turma '6º ANO ALFA' [--confirmar-lote]")
        return

    print(f"{'TURMA':<16} {'A LANÇAR':>9}  ALUNOS (nome GRP <- planilha)")
    print("-" * 90)
    for t, p in turmas:
        lanc = [i for i in p["itens"] if i["status"] == "LANCAR"]
        print(f"{t:<16} {len(lanc):>9}")
        for i in lanc:
            print(f"    {i['match'] or i['nome_planilha']:<40} <- {i['nome_planilha']:<38} {i['valor_lancar']:.2f}")
    print()

    if not args.confirmar_lote:
        print("DRY-RUN — nada será escrito. Use --confirmar-lote para executar.")
        return

    session = BrowserSession.start(headless=False, state_dir="state/playwright")
    try:
        page = session.open_grp()
        navigate_to_grades_page(page)
        time.sleep(2)
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
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        ev_slug = TARGET_EVAL.replace(" ", "_")
        for t, p in turmas:
            items = [i for i in p["itens"] if i["status"] == "LANCAR"]
            artifact_dir = Path("artifacts/batch_write") / f"{stamp}-{ev_slug}-{t.replace(' ', '_')}"
            launch_turma(page, t, items, artifact_dir)
            print()
    finally:
        session.close()
    print("FIM.")


if __name__ == "__main__":
    main()
