"""Gera o summary.md do lote de auditoria."""

from __future__ import annotations

from typing import Any


def build_summary(
    rows: list[dict[str, Any]],
    empty: list[str],
    duplicate_rows: list[dict[str, Any]],
    hash_missing: list[str],
    *,
    generated_at: str,
) -> str:
    files = [row for row in rows if not row["is_dir"]]
    dirs = [row for row in rows if row["is_dir"]]
    trash = [row for row in duplicate_rows if row["action"] == "trash"]
    freed = sum(int(row["size"]) for row in trash)
    groups = len({row["group_id"] for row in duplicate_rows})
    return "\n".join(
        [
            "# Auditoria do Google Drive — Resumo",
            "",
            f"Gerado em: {generated_at}",
            "",
            "## Contagens",
            "",
            f"- Itens inventariados: {len(rows)}",
            f"- Arquivos: {len(files)}",
            f"- Pastas: {len(dirs)}",
            f"- Pastas vazias: {len(empty)}",
            f"- Grupos de duplicatas: {groups}",
            f"- Cópias marcadas para lixeira: {len(trash)}",
            f"- Espaço recuperável estimado: {freed / (1024 * 1024):.2f} MiB",
            f"- Arquivos sem hash (revisar manualmente): {len(hash_missing)}",
            "",
            "## Segurança",
            "",
            "Nenhuma alteração foi feita no Drive. O apply só roda após aprovação por lote.",
            "",
        ]
    )
