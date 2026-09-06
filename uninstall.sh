#!/usr/bin/env bash
# Desinstalle butbutbut (Linux, macOS). Ne touche pas a tes sons perso sauf
# avec --purge.
#
#   ./uninstall.sh            # retire le programme et le demarrage auto
#   ./uninstall.sh --purge    # + le dossier de donnees (sons perso, journal)
set -euo pipefail

APP_NAME="butbutbut"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
BIN_DIR="$HOME/.local/bin"
DATA_DIR="$DATA_HOME/$APP_NAME"

PURGE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --purge) PURGE=1; shift ;;
        -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
        *) echo "option inconnue : $1" >&2; exit 2 ;;
    esac
done

say()   { printf '  %s\n' "$*"; }
head_() { printf '\n\033[1m%s\033[0m\n' "$*"; }

head_ "butbutbut - desinstallation"

# --- daemon en cours
if [ -x "$BIN_DIR/$APP_NAME" ]; then
    "$BIN_DIR/$APP_NAME" --stop >/dev/null 2>&1 || true
    say "daemon      : arrete"
fi

# --- demarrage automatique
if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user disable --now "$APP_NAME.service" >/dev/null 2>&1 || true
    rm -f "$CONFIG_HOME/systemd/user/$APP_NAME.service"
    systemctl --user daemon-reload >/dev/null 2>&1 || true
    say "systemd     : unite retiree"
fi

PLIST="$HOME/Library/LaunchAgents/com.butbutbut.goals.plist"
if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" >/dev/null 2>&1 || true
    rm -f "$PLIST"
    say "LaunchAgent : retire"
fi

if [ -f "$CONFIG_HOME/autostart/$APP_NAME.desktop" ]; then
    rm -f "$CONFIG_HOME/autostart/$APP_NAME.desktop"
    say "autostart   : retire"
fi

# --- commande et code
rm -f "$BIN_DIR/$APP_NAME" "$BIN_DIR/but"
rm -rf "$DATA_DIR/app"
say "commande    : retiree de $BIN_DIR"
say "code        : retire de $DATA_DIR/app"

# --- donnees
if [ "$PURGE" -eq 1 ]; then
    rm -rf "$DATA_DIR"
    say "donnees     : $DATA_DIR supprime"
else
    if [ -d "$DATA_DIR" ]; then
        say "donnees     : $DATA_DIR conserve (sons perso, journal)"
        say "  -> ./uninstall.sh --purge pour tout supprimer"
    fi
fi

head_ "Termine"
