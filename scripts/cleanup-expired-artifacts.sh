#!/usr/bin/env bash
# Remove somente artifacts que o GitHub já marcou como expirados.
# Uso:
#   ./scripts/cleanup-expired-artifacts.sh
# Requer GitHub CLI autenticado (gh auth login).

set -euo pipefail

REPO="${GITHUB_REPOSITORY:-}"
if [[ -z "$REPO" ]]; then
  REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner')"
fi

count=0
while IFS=$'\t' read -r artifact_id artifact_name; do
  [[ -z "$artifact_id" ]] && continue
  echo "Removendo artifact expirado: $artifact_id ($artifact_name)"
  gh api --method DELETE "repos/${REPO}/actions/artifacts/${artifact_id}" >/dev/null
  count=$((count + 1))
done < <(
  gh api --paginate "repos/${REPO}/actions/artifacts?per_page=100"     --jq '.artifacts[] | select(.expired == true) | [.id, .name] | @tsv'
)

echo "Artifacts expirados removidos: $count"
