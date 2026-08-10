#!/bin/bash
# Script para instalar pacotes que requerem sudo
# Execute: bash ~/install-system-packages.sh

set -e

echo "=== Atualizando sistema ==="
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get dist-upgrade -y
sudo apt-get autoremove -y
sudo apt-get autoclean

echo "=== Instalando pacotes de desenvolvimento ==="
sudo apt-get install -y \
  git python3 python3-pip python3-venv curl wget \
  build-essential cmake gcc g++ clang \
  jq tree htop ripgrep fd-find fzf bat \
  unzip zip p7zip-full imagemagick ffmpeg \
  sqlite3 postgresql-client redis-tools \
  git-delta gh openjdk-21-jdk \
  linux-firmware

echo "=== Configurando bat (Ubuntu usa batcat) ==="
if [ ! -f ~/.local/bin/bat ] && command -v batcat &>/dev/null; then
  mkdir -p ~/.local/bin
  ln -sf /usr/bin/batcat ~/.local/bin/bat
fi

echo "=== Configurando fd (Ubuntu usa fdfind) ==="
if [ ! -f ~/.local/bin/fd ] && command -v fdfind &>/dev/null; then
  mkdir -p ~/.local/bin
  ln -sf /usr/bin/fdfind ~/.local/bin/fd
fi

echo "=== Snap refresh ==="
sudo snap refresh 2>/dev/null || true

echo "=== Flatpak update ==="
flatpak update -y 2>/dev/null || true

echo "=== Reparando pacotes quebrados ==="
sudo apt-get install -f -y

echo "=== Concluído! ==="
