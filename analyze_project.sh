#!/usr/bin/env bash
###############################################################################
# analyze_project.sh (v3 — TODOs cobrindo código, scripts/config e docs)
#
# Analisa a estrutura REAL de um projeto (código, testes, docker, deps, git)
# e gera um relatório em Markdown com o estado atual — sem depender de rede,
# sem enviar nada para fora da máquina.
#
# Uso:
#   ./analyze_project.sh /caminho/do/projeto
#   ./analyze_project.sh            # usa o diretório atual
#
# Saída:
#   ./relatorio_projeto_<nome>_<data>.md
###############################################################################

set -uo pipefail

PROJECT_DIR="${1:-.}"
PROJECT_DIR="$(cd "$PROJECT_DIR" 2>/dev/null && pwd)"

if [ -z "$PROJECT_DIR" ]; then
    echo "Erro: diretório inválido." >&2
    exit 1
fi

PROJECT_NAME="$(basename "$PROJECT_DIR")"
DATE_TAG="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="$(pwd)/relatorio_projeto_${PROJECT_NAME}_${DATE_TAG}.md"

EXCLUDE_DIRS=(
    "node_modules" ".git" "dist" "build" "__pycache__" ".venv" "venv"
    ".next" ".turbo" "coverage" ".pytest_cache" "target" ".mypy_cache"
    ".idea" ".vscode" "vendor"
)

build_exclude_args() {
    local args=()
    for d in "${EXCLUDE_DIRS[@]}"; do
        args+=(-not -path "*/$d/*")
    done
    printf '%s\0' "${args[@]}"
}
mapfile -d '' -t EXCLUDE_ARGS < <(build_exclude_args)

safe_count() {
    local var="$1"
    if [ -z "$var" ]; then
        echo 0
    else
        echo "$var" | grep -c .
    fi
}

echo "Analisando: $PROJECT_DIR"
echo "Relatório será salvo em: $OUT_FILE"
echo ""

{
echo "# Relatório de Análise de Projeto"
echo ""
echo "- **Projeto:** \`$PROJECT_NAME\`"
echo "- **Caminho:** \`$PROJECT_DIR\`"
echo "- **Gerado em:** $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "> Este relatório reflete o estado real do código no momento da execução,"
echo "> não a arquitetura planejada ou documentada."
echo ""
echo "---"
echo ""
} > "$OUT_FILE"

{
echo "## 1. Estrutura de Diretórios (2 níveis)"
echo ""
echo '```'
} >> "$OUT_FILE"

if command -v tree >/dev/null 2>&1; then
    IGNORE_PATTERN=$(IFS='|'; echo "${EXCLUDE_DIRS[*]}")
    tree -L 2 -I "$IGNORE_PATTERN" "$PROJECT_DIR" >> "$OUT_FILE" 2>/dev/null
else
    find "$PROJECT_DIR" -maxdepth 2 -mindepth 1 "${EXCLUDE_ARGS[@]}" 2>/dev/null \
        | sed "s|$PROJECT_DIR/||" >> "$OUT_FILE"
    echo "(instale 'tree' para uma visualização melhor: sudo apt install tree)" >> "$OUT_FILE"
fi

echo '```' >> "$OUT_FILE"
echo "" >> "$OUT_FILE"

{
echo "## 2. Arquivos por Extensão"
echo ""
echo "| Extensão | Quantidade |"
echo "|---|---|"
} >> "$OUT_FILE"

find "$PROJECT_DIR" -type f "${EXCLUDE_ARGS[@]}" 2>/dev/null \
    | sed 's/.*\.//' \
    | grep -v '/' \
    | sort | uniq -c | sort -rn | head -30 \
    | awk '{printf "| .%s | %s |\n", $2, $1}' >> "$OUT_FILE"

echo "" >> "$OUT_FILE"

{
echo "## 3. Linhas de Código (LOC)"
echo ""
} >> "$OUT_FILE"

if command -v cloc >/dev/null 2>&1; then
    EXCLUDE_CSV=$(IFS=,; echo "${EXCLUDE_DIRS[*]}")
    echo '```' >> "$OUT_FILE"
    cloc "$PROJECT_DIR" --exclude-dir="$EXCLUDE_CSV" --quiet >> "$OUT_FILE" 2>/dev/null
    echo '```' >> "$OUT_FILE"
else
    echo "_'cloc' não instalado — usando contagem aproximada (wc -l)._" >> "$OUT_FILE"
    echo "Instale com: \`sudo apt install cloc\` para números precisos por linguagem." >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
    echo "| Extensão | Arquivos | Linhas (aprox.) |" >> "$OUT_FILE"
    echo "|---|---|---|" >> "$OUT_FILE"
    for ext in py ts tsx js jsx java go rs json yaml yml md sql html css; do
        files=$(find "$PROJECT_DIR" -type f -name "*.$ext" "${EXCLUDE_ARGS[@]}" 2>/dev/null)
        if [ -n "$files" ]; then
            count=$(echo "$files" | wc -l)
            lines=$(echo "$files" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
            echo "| .$ext | $count | $lines |" >> "$OUT_FILE"
        fi
    done
fi
echo "" >> "$OUT_FILE"

{
echo "## 4. Testes"
echo ""
} >> "$OUT_FILE"

TEST_FILES=$(find "$PROJECT_DIR" -type f \
    \( -iname "*test*.py" -o -iname "*spec*.ts" -o -iname "*spec*.js" \
       -o -iname "*test*.ts" -o -iname "*test*.js" -o -iname "*_test.go" \) \
    "${EXCLUDE_ARGS[@]}" 2>/dev/null)

TEST_COUNT=$(safe_count "$TEST_FILES")
echo "- **Arquivos de teste encontrados:** $TEST_COUNT" >> "$OUT_FILE"
echo "" >> "$OUT_FILE"

if [ "$TEST_COUNT" -gt 0 ]; then
    echo "<details><summary>Ver lista de arquivos de teste</summary>" >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
    echo "$TEST_FILES" | sed "s|$PROJECT_DIR/||" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
    echo "</details>" >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
else
    echo "_Nenhum arquivo de teste identificado pelos padrões de nome usados._" >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
fi

{
echo "### Execução de suites (se configuradas)"
echo ""
} >> "$OUT_FILE"

SUITE_NOTE_ADDED=0
if [ -f "$PROJECT_DIR/package.json" ] && grep -q '"test"' "$PROJECT_DIR/package.json" 2>/dev/null; then
    echo "- \`package.json\` define script de teste (\`npm test\`). Não executado automaticamente por este script." >> "$OUT_FILE"
    SUITE_NOTE_ADDED=1
fi
if [ -f "$PROJECT_DIR/pytest.ini" ] || [ -f "$PROJECT_DIR/setup.cfg" ] || find "$PROJECT_DIR" -maxdepth 2 -name "pyproject.toml" 2>/dev/null | grep -q .; then
    echo "- Configuração de \`pytest\` detectada. Não executado automaticamente por este script." >> "$OUT_FILE"
    SUITE_NOTE_ADDED=1
fi
if [ "$SUITE_NOTE_ADDED" -eq 0 ]; then
    echo "_Nenhuma configuração de suíte de teste (package.json/pytest) detectada._" >> "$OUT_FILE"
fi
echo "" >> "$OUT_FILE"
echo "_Este script não executa os testes automaticamente (podem ter efeitos colaterais). Rode manualmente com \`npm test\` / \`pytest\` para números reais de cobertura._" >> "$OUT_FILE"
echo "" >> "$OUT_FILE"

{
echo "## 5. Docker e Infraestrutura"
echo ""
} >> "$OUT_FILE"

DOCKERFILES=$(find "$PROJECT_DIR" -maxdepth 3 -iname "Dockerfile*" "${EXCLUDE_ARGS[@]}" 2>/dev/null)
COMPOSE_FILES=$(find "$PROJECT_DIR" -maxdepth 4 \( -iname "docker-compose*.yml" -o -iname "docker-compose*.yaml" -o -iname "compose.yml" -o -iname "compose.yaml" \) "${EXCLUDE_ARGS[@]}" 2>/dev/null)

DOCKERFILES_COUNT=$(safe_count "$DOCKERFILES")
COMPOSE_COUNT=$(safe_count "$COMPOSE_FILES")

if [ "$DOCKERFILES_COUNT" -gt 0 ]; then
    echo "**Dockerfiles encontrados:**" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
    echo "$DOCKERFILES" | sed "s|$PROJECT_DIR/||" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
else
    echo "_Nenhum Dockerfile encontrado._" >> "$OUT_FILE"
fi
echo "" >> "$OUT_FILE"

if [ "$COMPOSE_COUNT" -gt 0 ]; then
    echo "**Arquivos docker-compose encontrados:**" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
    echo "$COMPOSE_FILES" | sed "s|$PROJECT_DIR/||" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
    echo "**Serviços definidos (via grep, aproximado):**" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
    # shellcheck disable=SC2086
    grep -hE "^\s{0,2}[a-zA-Z0-9_-]+:\s*$" $COMPOSE_FILES 2>/dev/null | sed 's/^\s*//;s/:\s*$//' | sort -u >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
else
    echo "_Nenhum docker-compose encontrado._" >> "$OUT_FILE"
fi
echo "" >> "$OUT_FILE"

CI_FILES=$(find "$PROJECT_DIR/.github/workflows" -type f \( -iname "*.yml" -o -iname "*.yaml" \) 2>/dev/null)
CI_COUNT=$(safe_count "$CI_FILES")
if [ "$CI_COUNT" -gt 0 ]; then
    echo "**Pipelines CI/CD (GitHub Actions):**" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
    echo "$CI_FILES" | sed "s|$PROJECT_DIR/||" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
else
    echo "_Nenhum workflow do GitHub Actions encontrado em \`.github/workflows\`._" >> "$OUT_FILE"
fi
echo "" >> "$OUT_FILE"

{
echo "## 6. Dependências Declaradas"
echo ""
} >> "$OUT_FILE"

DEP_FOUND_ANY=0
check_dep_file() {
    local file="$1"
    local label="$2"
    local found
    found=$(find "$PROJECT_DIR" -maxdepth 4 -iname "$file" "${EXCLUDE_ARGS[@]}" 2>/dev/null)
    if [ -n "$found" ]; then
        DEP_FOUND_ANY=1
        echo "### $label" >> "$OUT_FILE"
        echo '```' >> "$OUT_FILE"
        echo "$found" | sed "s|$PROJECT_DIR/||" >> "$OUT_FILE"
        echo '```' >> "$OUT_FILE"
        echo "" >> "$OUT_FILE"
    fi
}

check_dep_file "package.json" "Node.js (package.json)"
check_dep_file "requirements.txt" "Python (requirements.txt)"
check_dep_file "pyproject.toml" "Python (pyproject.toml)"
check_dep_file "go.mod" "Go (go.mod)"
check_dep_file "Cargo.toml" "Rust (Cargo.toml)"

if [ "$DEP_FOUND_ANY" -eq 0 ]; then
    echo "_Nenhum arquivo de dependências (package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml) encontrado._" >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
fi

# ----------------------------------------------------------------------------
# 7. TODOs, FIXMEs e marcadores de dívida técnica
# ----------------------------------------------------------------------------
{
echo "## 7. Marcadores de Pendência (TODO / FIXME / HACK / XXX)"
echo ""
} >> "$OUT_FILE"

GREP_EXCLUDES=()
for d in "${EXCLUDE_DIRS[@]}"; do
    GREP_EXCLUDES+=(--exclude-dir="$d")
done

CODE_INCLUDES=(
    --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js"
    --include="*.jsx" --include="*.go" --include="*.java" --include="*.rb"
    --include="*.rs" --include="*.c" --include="*.cpp" --include="*.h"
    --include="*.php" --include="*.kt" --include="*.swift"
)

SCRIPT_CONFIG_INCLUDES=(
    --include="*.sh" --include="*.bash" --include="*.yml" --include="*.yaml"
    --include="*.json" --include="*.toml" --include="Dockerfile*"
    --include="*.env.example" --include="*.env.sample"
)

DOC_INCLUDES=(--include="*.md" --include="*.mdx" --include="*.rst")

CODE_MATCHES=$(grep -rEn "TODO|FIXME|HACK|XXX" "$PROJECT_DIR" \
    "${CODE_INCLUDES[@]}" "${GREP_EXCLUDES[@]}" 2>/dev/null)

SCRIPT_CONFIG_MATCHES=$(grep -rEn "TODO|FIXME|HACK|XXX" "$PROJECT_DIR" \
    "${SCRIPT_CONFIG_INCLUDES[@]}" "${GREP_EXCLUDES[@]}" 2>/dev/null)

DOC_MATCHES=$(grep -rEn "TODO|FIXME|HACK|XXX" "$PROJECT_DIR" \
    "${DOC_INCLUDES[@]}" "${GREP_EXCLUDES[@]}" 2>/dev/null)

CODE_COUNT=$(safe_count "$CODE_MATCHES")
SCRIPT_CONFIG_COUNT=$(safe_count "$SCRIPT_CONFIG_MATCHES")
DOC_COUNT=$(safe_count "$DOC_MATCHES")
TODO_COUNT=$((CODE_COUNT + SCRIPT_CONFIG_COUNT + DOC_COUNT))

{
echo "| Categoria | Ocorrências |"
echo "|---|---|"
echo "| Código-fonte (.py, .ts, .js, .go, etc.) | $CODE_COUNT |"
echo "| Scripts e config (.sh, .yml, .json, Dockerfile, etc.) | $SCRIPT_CONFIG_COUNT |"
echo "| Documentação (.md, .mdx, .rst) | $DOC_COUNT |"
echo "| **Total** | **$TODO_COUNT** |"
echo ""
} >> "$OUT_FILE"

show_matches_block() {
    local label="$1"
    local matches="$2"
    local count="$3"
    if [ "$count" -gt 0 ]; then
        echo "<details><summary>$label ($count) — ver até 40 ocorrências</summary>" >> "$OUT_FILE"
        echo "" >> "$OUT_FILE"
        echo '```' >> "$OUT_FILE"
        echo "$matches" | sed "s|$PROJECT_DIR/||" | head -40 >> "$OUT_FILE"
        echo '```' >> "$OUT_FILE"
        echo "" >> "$OUT_FILE"
        echo "</details>" >> "$OUT_FILE"
        echo "" >> "$OUT_FILE"
    fi
}

show_matches_block "Código-fonte" "$CODE_MATCHES" "$CODE_COUNT"
show_matches_block "Scripts e config" "$SCRIPT_CONFIG_MATCHES" "$SCRIPT_CONFIG_COUNT"
show_matches_block "Documentação" "$DOC_MATCHES" "$DOC_COUNT"

if [ "$TODO_COUNT" -eq 0 ]; then
    echo "_Nenhuma ocorrência de TODO/FIXME/HACK/XXX encontrada nas categorias analisadas._" >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
fi

{
echo "## 8. Arquivos Maiores que 400 Linhas"
echo ""
echo "_Não é necessariamente um problema, mas útil para identificar candidatos a refatoração._"
echo ""
} >> "$OUT_FILE"

LARGE_FILES=$(find "$PROJECT_DIR" -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.go" \) "${EXCLUDE_ARGS[@]}" -print0 2>/dev/null \
    | xargs -0 -I{} sh -c 'wc -l "{}" 2>/dev/null' \
    | awk '$1 > 400 {print}' \
    | sort -rn | head -20)

if [ -n "$LARGE_FILES" ]; then
    echo '```' >> "$OUT_FILE"
    echo "$LARGE_FILES" | sed "s|$PROJECT_DIR/||" >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"
else
    echo "_Nenhum arquivo acima de 400 linhas encontrado._" >> "$OUT_FILE"
fi
echo "" >> "$OUT_FILE"

{
echo "## 9. Estado do Git"
echo ""
} >> "$OUT_FILE"

if [ -d "$PROJECT_DIR/.git" ]; then
    (
    cd "$PROJECT_DIR" || exit 1
    BRANCH=$(git branch --show-current 2>/dev/null)
    COMMIT_COUNT=$(git rev-list --count HEAD 2>/dev/null)
    LAST_COMMIT=$(git log -1 --format="%h - %s (%ci)" 2>/dev/null)
    CONTRIBUTORS=$(git shortlog -sn --all 2>/dev/null | wc -l)
    UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l)

    {
    echo "- **Branch atual:** \`$BRANCH\`"
    echo "- **Total de commits:** $COMMIT_COUNT"
    echo "- **Último commit:** $LAST_COMMIT"
    echo "- **Contribuidores:** $CONTRIBUTORS"
    echo "- **Arquivos com mudanças não commitadas:** $UNCOMMITTED"
    echo ""
    echo "### Últimos 10 commits"
    echo '```'
    } >> "$OUT_FILE"

    git log -10 --format="%h  %ad  %s" --date=short 2>/dev/null >> "$OUT_FILE"
    echo '```' >> "$OUT_FILE"

    echo "$COMMIT_COUNT" > /tmp/.ap_commit_count.$$
    echo "$UNCOMMITTED" > /tmp/.ap_uncommitted.$$
    )
    COMMIT_COUNT=$(cat /tmp/.ap_commit_count.$$ 2>/dev/null || echo "N/A")
    UNCOMMITTED=$(cat /tmp/.ap_uncommitted.$$ 2>/dev/null || echo "N/A")
    rm -f /tmp/.ap_commit_count.$$ /tmp/.ap_uncommitted.$$
else
    echo "_Este diretório não é um repositório Git (ou \`.git\` não foi encontrado)._" >> "$OUT_FILE"
fi
echo "" >> "$OUT_FILE"

{
echo "## 10. Variáveis de Ambiente Declaradas"
echo ""
echo "_Somente os NOMES das variáveis são listados — valores/segredos nunca são lidos ou exibidos._"
echo ""
} >> "$OUT_FILE"

ENV_FILES=$(find "$PROJECT_DIR" -maxdepth 3 \( -iname ".env.example" -o -iname ".env.sample" \) "${EXCLUDE_ARGS[@]}" 2>/dev/null)
if [ -n "$ENV_FILES" ]; then
    echo '```' >> "$OUT_FILE"
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        echo "# $(basename "$f")" >> "$OUT_FILE"
        grep -oE "^[A-Z_][A-Z0-9_]*=" "$f" 2>/dev/null | sed 's/=$//' >> "$OUT_FILE"
        echo "" >> "$OUT_FILE"
    done <<< "$ENV_FILES"
    echo '```' >> "$OUT_FILE"
else
    echo "_Nenhum arquivo \`.env.example\` ou \`.env.sample\` encontrado._" >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
    echo "⚠️ Se o projeto usa \`.env\` diretamente sem um \`.env.example\`, considere criar um — facilita onboarding e evita segredos vazando no Git." >> "$OUT_FILE"
fi
echo "" >> "$OUT_FILE"

{
echo "---"
echo ""
echo "## Resumo Executivo"
echo ""
echo "| Métrica | Valor |"
echo "|---|---|"
echo "| Arquivos de teste | $TEST_COUNT |"
echo "| TODOs/FIXMEs (total) | $TODO_COUNT |"
echo "| Dockerfiles | $DOCKERFILES_COUNT |"
echo "| Docker-compose | $COMPOSE_COUNT |"
echo "| Workflows CI/CD | $CI_COUNT |"
if [ -d "$PROJECT_DIR/.git" ]; then
echo "| Commits totais | ${COMMIT_COUNT:-N/A} |"
echo "| Mudanças não commitadas | ${UNCOMMITTED:-N/A} |"
fi
echo ""
echo "_Relatório gerado automaticamente por \`analyze_project.sh\`. Revise manualmente antes de usar como base para decisões arquiteturais._"
} >> "$OUT_FILE"

echo ""
echo "✅ Análise concluída."
echo "📄 Relatório salvo em: $OUT_FILE"
