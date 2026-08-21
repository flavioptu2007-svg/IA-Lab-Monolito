#!/bin/bash
# auto_inbox.sh - Monitora a pasta Downloads/Transferências e move arquivos
# maduros (>5 min sem modificação) para a Inbox do sistema Escola.
# Uso no crontab: */15 * * * * /home/flavio/scripts/auto_inbox.sh

WATCH_DIR="/home/flavio/Transferências"
INBOX_DIR="/home/flavio/Documentos/Escola/00-Inbox"
TODAY=$(date +%Y-%m-%d)
LOG="/home/flavio/.local/log/inbox_$TODAY.log"

# Extensões ignoradas — arquivos com estas extensões NÃO são movidos para a
# Inbox (ficam em Transferências). Adicione/remova conforme necessário.
# Ex.: instaladores que você ainda vai executar (.deb, .AppImage, .exe, .msi, .run).
IGNORE_EXTS="deb appimage exe msi run"

mkdir -p "$INBOX_DIR" "$(dirname "$LOG")"

moved=0

for f in "$WATCH_DIR"/*; do
    [ -f "$f" ] || continue
    filename=$(basename "$f")

    # Pula ocultos
    case "$filename" in
        .*) continue ;;
    esac

    # Pula extensões ignoradas (case-insensitive)
    ext="${filename##*.}"
    if [ -n "$ext" ] && [[ " $IGNORE_EXTS " == *" ${ext,,} "* ]]; then
        continue
    fi

    # Pula arquivos com menos de 5 minutos (ainda baixando)
    if [ "$(find "$f" -mmin +5 2>/dev/null | wc -l)" -eq 0 ]; then
        continue
    fi

    dest="$INBOX_DIR/$filename"

    # Evita sobrescrever — adiciona sufixo de duplicata
    if [ -f "$dest" ]; then
        base="${filename%.*}"
        ext="${filename##*.}"
        # Se não tem extensão
        if [ "$base" = "$filename" ]; then
            ext=""
        fi
        counter=1
        while true; do
            if [ -n "$ext" ]; then
                dest="$INBOX_DIR/${base}_dup${counter}.${ext}"
            else
                dest="$INBOX_DIR/${base}_dup${counter}"
            fi
            [ -f "$dest" ] || break
            counter=$((counter + 1))
        done
    fi

    mv "$f" "$dest"
    echo "[$(date +%H:%M)] Movido: $filename" >> "$LOG"
    moved=$((moved + 1))
done

if [ "$moved" -gt 0 ]; then
    echo "[$(date +%H:%M)] $moved arquivo(s) movido(s) para Inbox" >> "$LOG"
fi
