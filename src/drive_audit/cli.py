"""CLI da auditoria do Google Drive: python -m src.drive_audit <comando>."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.drive_audit import (
    analysis,
    apply_batch,
    config,
    hashing,
    inventory,
    naming,
    report,
)


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def cmd_inventory(_args: argparse.Namespace) -> int:
    base = config.ensure_workdir()
    rows = [inventory.to_row(entry) for entry in inventory.build_inventory()]
    inventory.write_inventory(rows, base / "inventory.jsonl", base / "inventory.csv")
    print(f"Inventário: {len(rows)} itens → {base / 'inventory.csv'}")
    return 0


def _parent(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _with_dup_suffix(name: str, n: int) -> str:
    stem, dot, ext = name.rpartition(".")
    return f"{stem}_dup{n}.{ext}" if dot else f"{name}_dup{n}"


def _rename_rows(rows: list[dict[str, Any]], trash_paths: set[str]) -> list[dict[str, Any]]:
    """Sugere renomeações; pula duplicatas em trash e resolve colisões (_dupN)."""
    usados = {(_parent(r["path"]), r["name"].lower()) for r in rows}
    out: list[dict[str, Any]] = []
    for row in rows:
        # A spec proíbe renomear cópias que já vão para a lixeira.
        if row["path"] in trash_paths:
            continue
        sugestao = naming.suggest_name(
            row["name"], row["path"], row["is_dir"], row["modified"], row["created"]
        )
        if sugestao is None:
            continue
        parent = _parent(row["path"])
        final = sugestao.suggested
        n = 1
        while (parent, final.lower()) in usados:
            n += 1
            final = _with_dup_suffix(sugestao.suggested, n)
        usados.add((parent, final.lower()))
        out.append(
            {
                "path_atual": row["path"],
                "nome_atual": row["name"],
                "nome_sugerido": final,
                "motivo": sugestao.motivo,
                "confianca": sugestao.confianca,
            }
        )
    return out


def cmd_analyze(_args: argparse.Namespace) -> int:
    base = config.ensure_workdir()
    rows = inventory.load_inventory(base / "inventory.jsonl")

    empty = analysis.find_empty_folders(rows)
    _write_csv(base / "empty_folders.csv", ("path",), [{"path": p} for p in empty])

    cache = hashing.load_cache(base / "hash_cache.json")
    hashes, missing = hashing.collect_hashes(rows, cache)
    hashing.save_cache(cache, base / "hash_cache.json")

    duplicates = analysis.group_duplicates(rows, hashes)
    _write_csv(
        base / "duplicates.csv",
        ("group_id", "hash", "action", "path", "id", "size", "motivo"),
        duplicates,
    )

    trash_paths = {row["path"] for row in duplicates if row["action"] == "trash"}
    rename_rows = _rename_rows(rows, trash_paths)
    _write_csv(
        base / "rename_plan.csv",
        ("path_atual", "nome_atual", "nome_sugerido", "motivo", "confianca"),
        rename_rows,
    )

    summary = report.build_summary(
        rows, empty, duplicates, missing, generated_at=datetime.now(timezone.utc).isoformat()
    )
    (base / "summary.md").write_text(summary, encoding="utf-8")
    print(
        f"Análise: {len(empty)} pastas vazias, "
        f"{len(duplicates)} linhas de duplicatas, "
        f"{len(rename_rows)} renomeações → {base / 'summary.md'}"
    )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    base = config.ensure_workdir()
    actions = apply_batch.load_actions(base / "duplicates.csv")
    results = apply_batch.apply_actions(
        actions, dry_run=not args.confirm, log_path=base / "logs" / "apply.jsonl"
    )
    modo = "APPLY" if args.confirm else "dry-run"
    print(f"{modo}: {len(results)} ações")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drive_audit", description="Auditoria do Google Drive (rclone)."
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("inventory", help="Lista o Drive e grava inventory.jsonl/csv")
    sub.add_parser("analyze", help="Pastas vazias, duplicatas, renomeações e summary.md")
    apply_parser = sub.add_parser("apply", help="Aplica o lote aprovado (padrão: dry-run)")
    apply_parser.add_argument(
        "--confirm", action="store_true", help="Apply real: envia duplicatas à lixeira"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"inventory": cmd_inventory, "analyze": cmd_analyze, "apply": cmd_apply}
    return handlers[args.comando](args)
