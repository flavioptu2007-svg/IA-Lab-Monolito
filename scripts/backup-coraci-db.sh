#!/usr/bin/env bash
# Backup dos bancos SQLite do Coraci, sem adicionar arquivos ao repositório.
# Uso: ./scripts/backup-coraci-db.sh [destino]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-${HOME}/backups/ia-lab-coraci}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "${DEST}"

found=0
for db in "${ROOT_DIR}/src/coraci.db" "${ROOT_DIR}/Aplicativo_Coraci/coraci.db"; do
  [[ -f "${db}" ]] || continue
  found=1
  name="$(basename "${db}" .db)"
  out="${DEST}/${name}-${STAMP}.db"
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "${db}" ".backup '${out}'"
    sqlite3 "${out}" "PRAGMA integrity_check;" >/dev/null
  else
    cp -- "${db}" "${out}"
  fi
  echo "Backup: ${out}"
done

if [[ "${found}" -eq 0 ]]; then
  echo "Nenhum banco Coraci encontrado; nada para copiar."
fi

find "${DEST}" -maxdepth 1 -type f -name 'coraci-*.db' -mtime +10 -delete 2>/dev/null || true
find "${DEST}" -maxdepth 1 -type f -name 'coraci.db-*.db' -mtime +10 -delete 2>/dev/null || true
