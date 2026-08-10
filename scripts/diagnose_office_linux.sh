#!/usr/bin/env bash
#
# diagnose_office_linux.sh — Diagnóstico do Microsoft Office no Linux (ETAPA 1)
#
# Coleta informações do sistema em MODO SOMENTE LEITURA:
#   • não instala nada
#   • não remove nada
#   • não altera configurações, prefixos Wine, repositórios, drivers ou arquivos
#   • não cria arquivos (a saída é impressa no terminal)
#
# Pode ser executado de qualquer pasta (não depende do diretório do repositório):
#   ./scripts/diagnose_office_linux.sh
#   bash scripts/diagnose_office_linux.sh
#   bash /caminho/absoluto/scripts/diagnose_office_linux.sh
#
# Após o diagnóstico, envie a saída completa + a versão do Office (com licença
# legítima) que você possui. Fluxo completo: docs/microsoft-office-linux-wine.md

set -u   # variável não definida → erro (sem set -e: continuar após falhas)
         # nenhum comando abaixo altera o sistema; todos são de leitura

# ── Helpers ─────────────────────────────────────────────────────────────────

# run_check <título> <comando...> — executa um comando direto e reporta falha
run_check() {
    local title="$1"
    shift
    echo
    echo "### ${title}"
    echo "\$ $*"
    "$@" 2>&1 || echo "[indisponível ou falhou: código $?]"
}

# run_shell_check <título> <comando> — executa via bash -lc com timeout de 10s
run_shell_check() {
    local title="$1"
    local cmd="$2"
    echo
    echo "### ${title}"
    echo "\$ ${cmd}"
    timeout 10s bash -lc "${cmd}" 2>&1 || echo "[indisponível, falhou ou excedeu 10s]"
}

# ── Cabeçalho ───────────────────────────────────────────────────────────────

echo "# Diagnóstico Microsoft Office no Linux"
echo "Gerado em: $(date -Is 2>/dev/null || date)"
echo "Modo: somente leitura — nenhuma instalação ou alteração é feita."
echo "Usuário: $(id -un 2>/dev/null || echo '?') (uid $(id -u 2>/dev/null || echo '?'))"

# ── 1. Sistema operacional ──────────────────────────────────────────────────

run_check "Sistema operacional" cat /etc/os-release
run_shell_check "LSB release" "lsb_release -a 2>/dev/null"
run_check "Kernel" uname -a
run_check "Arquitetura" uname -m

# ── 2. Hardware ─────────────────────────────────────────────────────────────

run_shell_check "CPU" "lscpu 2>/dev/null | grep -E 'Model name|Architecture|CPU\\(s\\)|Thread|Core|Socket' | head -10"
run_check "Memória RAM" free -h
run_check "Espaço em disco" df -h

# ── 3. Gerenciadores de pacotes ─────────────────────────────────────────────

run_shell_check "Gerenciadores de pacotes detectados" \
    "for c in apt dnf pacman zypper flatpak snap; do command -v \$c >/dev/null && echo \$c; done; true"

# ── 4. Wine / Winetricks / PlayOnLinux / Bottles ────────────────────────────

run_shell_check "Wine no PATH" "command -v wine || true"
run_shell_check "Versão do Wine" "wine --version 2>/dev/null"
run_shell_check "Winetricks no PATH" "command -v winetricks || true"
run_shell_check "Versão do Winetricks" "winetricks --version 2>/dev/null"
run_shell_check "PlayOnLinux no PATH" "command -v playonlinux || true"
run_shell_check "Bottles no PATH" "command -v bottles || flatpak list --app 2>/dev/null | grep -i bottles || true"

# ── 5. Arquiteturas dpkg (i386 é necessário p/ Office 32-bit) ────────────────

run_shell_check "Arquiteturas dpkg" "dpkg --print-architecture; dpkg --print-foreign-architectures 2>/dev/null"

# ── 6. Dependências relevantes ──────────────────────────────────────────────

run_shell_check "Dependências relevantes no PATH" \
    "for c in cabextract curl wget unzip 7z winbind cups lpstat fc-match; do printf '%-12s ' \$c; command -v \$c || echo ausente; done"

# ── 7. Impressão (CUPS) ─────────────────────────────────────────────────────

run_shell_check "Serviço CUPS" "systemctl is-active cups 2>/dev/null || service cups status 2>/dev/null | head -20 || true"
run_shell_check "Impressora padrão" "lpstat -d 2>/dev/null || true"

# ── 8. Idioma / Região / Teclado ────────────────────────────────────────────

run_shell_check "Locale atual" "locale 2>/dev/null | sed -n '1,20p'"
run_shell_check "Layout de teclado" "localectl status 2>/dev/null | grep -E 'Layout|Keymap' || setxkbmap -query 2>/dev/null || true"

# ── 9. Prefixos Wine existentes ─────────────────────────────────────────────

run_shell_check "Prefixos Wine comuns" \
    "for d in \"\$HOME/.wine\" \"\$HOME/.wine-office\" \"\$HOME/.local/share/bottles/bottles\" \"\$HOME/.PlayOnLinux/wineprefix\" \"\$HOME/wineprefixes\"; do [ -e \"\$d\" ] && echo \"existe: \$d\"; done; true"

# ── 10. Instalações anteriores do Office ────────────────────────────────────

run_shell_check "Instalações Office em prefixos Wine" \
    "find \"\$HOME/.wine\" \"\$HOME/.local/share/bottles\" \"\$HOME/.PlayOnLinux\" -maxdepth 10 -type f 2>/dev/null | grep -iE 'WINWORD\\.EXE|EXCEL\\.EXE|POWERPNT\\.EXE|OUTLOOK\\.EXE' | sort | head -20"

# ── 11. Instaladores do Office ──────────────────────────────────────────────

run_shell_check "Instaladores do Office em locais comuns" \
    "find \"\$HOME/Downloads\" \"\$HOME/Transferências\" \"\$HOME/Documentos\" \"\$HOME/Área de Trabalho\" \"\$HOME/Desktop\" -maxdepth 3 -type f 2>/dev/null | grep -iE '\\.(exe|iso|msi|cab|img)$' | sort | head -20"

# ── 12. Candidatos apt (versões que seriam instaladas) ──────────────────────

run_shell_check "Candidatos apt (wine/winetricks/cabextract)" \
    "apt-cache policy wine winetricks cabextract 2>/dev/null | grep -E '^wine|^winetricks|^cabextract|Candidato|Candidate'"

# ── Conclusão ───────────────────────────────────────────────────────────────

echo
echo "# Próximo passo"
echo "1) Envie a saída completa deste diagnóstico."
echo "2) Informe a versão do Microsoft Office que você possui com licença legítima"
echo "   (ex.: Office 2016, 2019, 2021 ou Microsoft 365) e o instalador disponível."
echo "3) A recomendação técnica virá ANTES de qualquer instalação."
echo "Guia completo: docs/microsoft-office-linux-wine.md"
