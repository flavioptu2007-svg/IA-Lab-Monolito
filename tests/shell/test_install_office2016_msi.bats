#!/usr/bin/env bats
# =============================================================================
# Testes unitários do fluxo de scripts/install_office2016_msi.sh
# -----------------------------------------------------------------------------
# Executa o script real com `wine`/`wineboot`/`7z` MOCKADOS (fake binários) e
# um $HOME temporário isolado — nenhum prefixo Wine real é tocado.
#
# Roda com:  bats tests/shell/test_install_office2016_msi.bats
# =============================================================================

SCRIPT="$BATS_TEST_DIRNAME/../../scripts/install_office2016_msi.sh"

setup() {
    export HOME="$BATS_TEST_TMPDIR/home"
    export WINEPREFIX="$HOME/.wine-office"
    export WINEDEBUG=-all
    mkdir -p "$HOME" "$BATS_TEST_TMPDIR/fakebin"

    # ── wine fake ──────────────────────────────────────────────────────────
    # Responde ao --version e simula o instalador:
    #   FAKE_WINE_RC=0 (padrão)  → cria os binários do Office se FAKE_WINE_INSTALL=1
    #   FAKE_WINE_RC=N           → instalador "falha" com código N
    cat > "$BATS_TEST_TMPDIR/fakebin/wine" <<'FAKEWINE'
#!/usr/bin/env bash
if [ "${1:-}" = "--version" ]; then
    echo "wine-10.0 (fake)"
    exit 0
fi
rc="${FAKE_WINE_RC:-0}"
if [ "$rc" -eq 0 ] && [ "${FAKE_WINE_INSTALL:-0}" = "1" ]; then
    office="$WINEPREFIX/drive_c/Program Files (x86)/Microsoft Office/Office16"
    mkdir -p "$office"
    touch "$office/WINWORD.EXE" "$office/EXCEL.EXE" "$office/POWERPNT.EXE"
    chmod +x "$office"/*.EXE
fi
exit "$rc"
FAKEWINE
    chmod +x "$BATS_TEST_TMPDIR/fakebin/wine"

    # ── wineboot fake: cria um prefixo "utilizável" ────────────────────────
    cat > "$BATS_TEST_TMPDIR/fakebin/wineboot" <<'FAKEBOOT'
#!/usr/bin/env bash
mkdir -p "$WINEPREFIX"
touch "$WINEPREFIX/system.reg"
exit 0
FAKEBOOT
    chmod +x "$BATS_TEST_TMPDIR/fakebin/wineboot"

    # ── 7z fake: extrai um .iso criando setup.exe na raiz ──────────────────
    # FAKE_7Z_NO_SETUP=1 → não cria setup.exe (testa o erro de mídia)
    # FAKE_7Z_FAIL=1     → 7z "falha" (testa o erro de extração)
    cat > "$BATS_TEST_TMPDIR/fakebin/7z" <<'FAKE7Z'
#!/usr/bin/env bash
# sintaxe: 7z x -y -o<destino> <arquivo.iso>
if [ "${FAKE_7Z_FAIL:-0}" = "1" ]; then
    echo "fake 7z: erro de extração" >&2
    exit 1
fi
dest=""
for a in "$@"; do
    case "$a" in
        -o*) dest="${a#-o}" ;;
    esac
done
mkdir -p "$dest"
if [ "${FAKE_7Z_NO_SETUP:-0}" != "1" ]; then
    touch "$dest/setup.exe"
fi
exit 0
FAKE7Z
    chmod +x "$BATS_TEST_TMPDIR/fakebin/7z"

    # PATH com os fakes primeiro (mas preservando coreutils do sistema)
    export PATH="$BATS_TEST_TMPDIR/fakebin:$PATH"
}

# ─────────────────────────────────────────────────────────────────────────────
# Ajuda e argumentos
# ─────────────────────────────────────────────────────────────────────────────

@test "--help mostra o uso e sai com 0" {
    run bash "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Uso:"* ]]
    [[ "$output" == *"install_office2016_msi.sh"* ]]
}

@test "sem midia informada → erro (código 1)" {
    run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Nenhuma midia informada"* ]]
}

@test "midia inexistente → erro (código 1)" {
    run bash "$SCRIPT" "$BATS_TEST_TMPDIR/nao-existe.iso"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Midia nao encontrada"* ]]
}

# ─────────────────────────────────────────────────────────────────────────────
# Pré-requisitos
# ─────────────────────────────────────────────────────────────────────────────

@test "wine ausente → erro (código 1)" {
    # PATH restrito a coreutils (sem o wine fake e sem /usr/bin com wine real)
    core="$BATS_TEST_TMPDIR/core"
    mkdir -p "$core"
    for c in date tee sed head find ls dirname basename mkdir rm echo; do
        ln -s "$(command -v "$c")" "$core/$c"
    done
    touch "$BATS_TEST_TMPDIR/setup.exe"
    run env PATH="$core" "$BASH" "$SCRIPT" "$BATS_TEST_TMPDIR/setup.exe"
    [ "$status" -eq 1 ]
    [[ "$output" == *"wine nao encontrado"* ]]
}

# ─────────────────────────────────────────────────────────────────────────────
# Fluxo principal — setup.exe direto (mídia MSI)
# ─────────────────────────────────────────────────────────────────────────────

@test "setup.exe MSI: cria prefixo, roda instalador e confirma binários" {
    touch "$BATS_TEST_TMPDIR/setup.exe"
    run env FAKE_WINE_INSTALL=1 bash "$SCRIPT" "$BATS_TEST_TMPDIR/setup.exe"
    [ "$status" -eq 0 ]
    [[ "$output" == *"criando (wineboot -u)"* ]]
    [[ "$output" == *"Midia parece ser MSI"* ]]
    [[ "$output" == *"Office 2016 instalado"* ]]
    [[ "$output" == *"WINWORD.EXE e EXCEL.EXE encontrados"* ]]
    # log foi gerado no HOME isolado
    [ -f "$HOME/office2016_install.log" ]
    grep -q "Office 2016 instalado" "$HOME/office2016_install.log"
}

@test "setup.exe MSI: prefixo existente é reutilizado (sem wineboot)" {
    mkdir -p "$WINEPREFIX"
    touch "$WINEPREFIX/system.reg"
    touch "$BATS_TEST_TMPDIR/setup.exe"
    run env FAKE_WINE_INSTALL=1 bash "$SCRIPT" "$BATS_TEST_TMPDIR/setup.exe"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Prefixo ja existe"* ]]
    [[ "$output" != *"criando (wineboot"* ]]
    [[ "$output" == *"Office 2016 instalado"* ]]
}

@test "setup.exe MSI: instalador falha (código 1) → aviso, mas sem binários" {
    touch "$BATS_TEST_TMPDIR/setup.exe"
    run env FAKE_WINE_RC=1 bash "$SCRIPT" "$BATS_TEST_TMPDIR/setup.exe"
    [ "$status" -eq 0 ]  # o script reporta e segue, sem sair com erro
    [[ "$output" == *"Instalador encerrou com erro (codigo 1)"* ]]
    [[ "$output" == *"Instalacao nao confirmada"* ]]
    [[ "$output" != *"Office 2016 instalado"* ]]
}

# ─────────────────────────────────────────────────────────────────────────────
# Fluxo com .iso
# ─────────────────────────────────────────────────────────────────────────────

@test ".iso: extrai com 7z, localiza setup.exe e executa" {
    touch "$BATS_TEST_TMPDIR/office2016.iso"
    run env FAKE_WINE_INSTALL=1 bash "$SCRIPT" "$BATS_TEST_TMPDIR/office2016.iso"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Extraindo .iso"* ]]
    [[ "$output" == *"setup.exe localizado"* ]]
    [[ "$output" == *"Office 2016 instalado"* ]]
}

@test ".ISO maiúsculo também é aceito (extrai e instala)" {
    touch "$BATS_TEST_TMPDIR/office2016.ISO"
    run env FAKE_WINE_INSTALL=1 bash "$SCRIPT" "$BATS_TEST_TMPDIR/office2016.ISO"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Extraindo .iso"* ]]
    [[ "$output" == *"setup.exe localizado"* ]]
    [[ "$output" == *"Office 2016 instalado"* ]]
}

@test ".iso com falha de extração do 7z → erro (código 1)" {
    touch "$BATS_TEST_TMPDIR/office2016.iso"
    run env FAKE_7Z_FAIL=1 bash "$SCRIPT" "$BATS_TEST_TMPDIR/office2016.iso"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Falha ao extrair o .iso"* ]]
}

@test ".iso sem setup.exe na raiz → erro (código 1)" {
    touch "$BATS_TEST_TMPDIR/office2016.iso"
    run env FAKE_7Z_NO_SETUP=1 bash "$SCRIPT" "$BATS_TEST_TMPDIR/office2016.iso"
    [ "$status" -eq 1 ]
    [[ "$output" == *"setup.exe nao encontrado"* ]]
}

@test ".iso sem 7z disponível → erro (código 1)" {
    touch "$BATS_TEST_TMPDIR/office2016.iso"
    # PATH restrito: só o wine fake + coreutils — NUNCA o 7z (real ou fake)
    no7z="$BATS_TEST_TMPDIR/no7z"
    mkdir -p "$no7z"
    cp "$BATS_TEST_TMPDIR/fakebin/wine" "$no7z/wine"
    for c in date tee sed head find ls dirname basename mkdir rm echo; do
        ln -s "$(command -v "$c")" "$no7z/$c"
    done
    run env PATH="$no7z" "$BASH" "$SCRIPT" "$BATS_TEST_TMPDIR/office2016.iso"
    [ "$status" -eq 1 ]
    [[ "$output" == *"7z nao encontrado"* ]]
}

# ─────────────────────────────────────────────────────────────────────────────
# Sanidade da mídia (Click-to-Run)
# ─────────────────────────────────────────────────────────────────────────────

@test "mídia Click-to-Run (configuration.xml) → aviso, não bloqueia" {
    mkdir -p "$BATS_TEST_TMPDIR/c2r"
    touch "$BATS_TEST_TMPDIR/c2r/setup.exe" "$BATS_TEST_TMPDIR/c2r/configuration.xml"
    run env FAKE_WINE_RC=0 bash "$SCRIPT" "$BATS_TEST_TMPDIR/c2r/setup.exe"
    [ "$status" -eq 0 ]
    [[ "$output" == *"AVISO: a midia contem arquivos tipicos do Click-to-Run"* ]]
    # segue o fluxo normalmente (instalador fake roda sem criar binários)
    [[ "$output" == *"Instalacao nao confirmada"* ]]
}
