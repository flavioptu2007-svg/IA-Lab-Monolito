#!/usr/bin/env bats
# =============================================================================
# Smoke tests dos scripts shell versionados do repositório
# -----------------------------------------------------------------------------
# Substitui o antigo test_install_office2016_msi.bats: o fluxo do Office 2016
# MSI foi removido do repo em 247f9624 junto com os scripts que ele testava,
# então estes testes cobrem o que realmente existe hoje em scripts/.
#
# Nenhum teste tem efeito colateral: só sintaxe, shebang e `--help`.
#
# Roda com:  bats tests/shell/
# =============================================================================

REPO_ROOT="$BATS_TEST_DIRNAME/../.."

# Scripts que implementam `--help` (o parsing de argumentos sai com 0 antes de
# qualquer efeito colateral). Mantenha em sincronia com:
#   grep -rn -- '--help|-h' scripts/
HELP_SCRIPTS=(
    "scripts/check_mcp_pin.sh"
    "scripts/chat_local.sh"
    "scripts/servir_projetos.sh"
    "scripts/update_mcps.sh"
    "scripts/audio/backup_audio_config.sh"
    "scripts/audio/demo_audio.sh"
    "scripts/audio/diagnose_audio.sh"
    "scripts/audio/setup_microfone_virtual.sh"
    "scripts/audio/test_microphone.sh"
    "scripts/audio/test_speaker.sh"
)

tracked_scripts() {
    (cd "$REPO_ROOT" && git ls-files 'scripts/*.sh')
}

@test "existe pelo menos um script versionado para testar" {
    run tracked_scripts
    [ "$status" -eq 0 ]
    [ -n "$output" ]
}

@test "todos os scripts versionados passam em bash -n (sintaxe)" {
    local falhas=0 script
    while IFS= read -r script; do
        if ! bash -n "$REPO_ROOT/$script"; then
            echo "sintaxe inválida: $script" >&2
            falhas=$((falhas + 1))
        fi
    done < <(tracked_scripts)
    [ "$falhas" -eq 0 ]
}

@test "todos os scripts versionados têm shebang de bash" {
    local falhas=0 script primeira_linha
    while IFS= read -r script; do
        primeira_linha="$(head -n 1 "$REPO_ROOT/$script")"
        case "$primeira_linha" in
        '#!'*bash*) ;;
        *)
            echo "shebang inesperada em $script: $primeira_linha" >&2
            falhas=$((falhas + 1))
            ;;
        esac
    done < <(tracked_scripts)
    [ "$falhas" -eq 0 ]
}

@test "scripts que implementam --help saem com 0" {
    local script
    for script in "${HELP_SCRIPTS[@]}"; do
        [ -f "$REPO_ROOT/$script" ] || {
            echo "script esperado não existe: $script" >&2
            return 1
        }
        run timeout 15 bash "$REPO_ROOT/$script" --help
        [ "$status" -eq 0 ] || {
            echo "$script --help saiu com $status" >&2
            return 1
        }
    done
}

@test "todos os arquivos de tests/shell são .bats" {
    local falhas=0 arquivo
    while IFS= read -r arquivo; do
        case "$arquivo" in
        *.bats) ;;
        *)
            echo "arquivo não-bats em tests/shell: $arquivo" >&2
            falhas=$((falhas + 1))
            ;;
        esac
    done < <(cd "$REPO_ROOT" && git ls-files 'tests/shell/*')
    [ "$falhas" -eq 0 ]
}
