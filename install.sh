#!/usr/bin/env bash
# Installe butbutbut pour l'utilisateur courant (Linux, y compris Arch, et macOS).
#
#   ./install.sh                          # installe + demarrage a la session
#   ./install.sh --no-autostart           # installe seulement la commande
#   ./install.sh --leagues l1,pl          # ne suit que ces championnats
#   ./install.sh --position top-right     # coin ou les cartes s'empilent
#
# Les options passees ici sont notees dans install.json, au chaud dans le
# dossier de donnees, et `butbutbut --update` les rejoue telles quelles.
# Celles qu'on ne passe pas ne sont pas posees non plus dans le service de
# demarrage : le fichier de configuration reste alors maitre de ces reglages.
#
# Aucun droit root, aucune dependance Python : tout est dans la stdlib.
set -euo pipefail

APP_NAME="butbutbut"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$DATA_HOME/$APP_NAME/app"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Vides tant qu'on ne les a pas recus. Materialiser un defaut en argument du
# service ecraserait silencieusement la meme cle du fichier de configuration,
# que la ligne de commande l'emporte toujours sur le fichier.
AUTOSTART=1
LEAGUES=""
POSITION=""
INTERVAL=""

while [ $# -gt 0 ]; do
    case "$1" in
        --no-autostart) AUTOSTART=0; shift ;;
        --leagues) LEAGUES="$2"; shift 2 ;;
        --position) POSITION="$2"; shift 2 ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
        *) echo "option inconnue : $1" >&2; exit 2 ;;
    esac
done

say()   { printf '  %s\n' "$*"; }
head_() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# Les arguments du daemon, en tableau : ils traversent proprement le plist,
# l'unite systemd et le fichier .desktop. Seul --quiet est pose sans condition,
# un daemon de session ecrivant sur une sortie qui n'existe pas ; le journal
# reste alimente de toute facon.
DAEMON_ARGS=()
if [ -n "$LEAGUES" ]; then
    DAEMON_ARGS+=(--leagues "$LEAGUES")
fi
if [ -n "$POSITION" ]; then
    DAEMON_ARGS+=(--position "$POSITION")
fi
if [ -n "$INTERVAL" ]; then
    DAEMON_ARGS+=(--interval "$INTERVAL")
fi
DAEMON_ARGS+=(--quiet)
ARGS_LINE="${DAEMON_ARGS[*]}"

head_ "butbutbut - installation"

# ------------------------------------------------------------ python ---------
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)'; then
            PYTHON="$(command -v "$candidate")"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    say "Python 3.8+ est introuvable. Installe-le puis relance :"
    say "  Arch/Manjaro  : sudo pacman -S python tk"
    say "  Debian/Ubuntu : sudo apt install python3 python3-tk"
    say "  Fedora        : sudo dnf install python3 python3-tkinter"
    say "  macOS         : brew install python-tk"
    exit 1
fi
say "python      : $PYTHON ($("$PYTHON" -c 'import platform; print(platform.python_version())'))"

# ------------------------------------------------------------ tkinter --------
if "$PYTHON" -c 'import tkinter' >/dev/null 2>&1; then
    say "tkinter     : OK"
else
    say "tkinter     : MANQUANT (les cartes de score ne s'afficheront pas)"
    if   command -v pacman  >/dev/null 2>&1; then say "  -> sudo pacman -S tk"
    elif command -v apt     >/dev/null 2>&1; then say "  -> sudo apt install python3-tk"
    elif command -v dnf     >/dev/null 2>&1; then say "  -> sudo dnf install python3-tkinter"
    elif command -v zypper  >/dev/null 2>&1; then say "  -> sudo zypper install python3-tk"
    elif command -v brew    >/dev/null 2>&1; then say "  -> brew install python-tk"
    fi
    say "  (l'installation continue, tu pourras l'ajouter apres)"
fi

# ------------------------------------------------------------- audio ---------
if [ "$(uname -s)" = "Darwin" ]; then
    say "audio       : afplay (integre a macOS)"
else
    PLAYER=""
    for p in mpv ffplay play cvlc pw-play paplay aplay; do
        if command -v "$p" >/dev/null 2>&1; then
            PLAYER="$p"
            break
        fi
    done
    if [ -n "$PLAYER" ]; then
        say "audio       : $PLAYER"
        case "$PLAYER" in
            pw-play|paplay|aplay)
                say "  (ce lecteur ne lit que le wav : le mp3 fourni sera remplace"
                say "   par la corne synthetisee. Installe mpv ou ffmpeg pour le mp3.)" ;;
        esac
    else
        say "audio       : aucun lecteur trouve (butbutbut restera muet)"
        if command -v pacman >/dev/null 2>&1; then
            say "  -> sudo pacman -S mpv    (ou ffmpeg / alsa-utils)"
        fi
    fi
fi

# ---------------------------------------------------------- connexion -------
PROBE='import urllib.request; urllib.request.urlopen("https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard", timeout=8).read(64)'
if "$PYTHON" -c "$PROBE" >/dev/null 2>&1; then
    say "source      : ESPN joignable"
else
    say "source      : ESPN INJOIGNABLE pour l'instant (le daemon reessaiera)"
fi

# ------------------------------------------------------------ fichiers -------
head_ "Copie des fichiers"

# Un daemon deja lance continuerait sur du code efface : on l'arrete, et
# l'autostart le relance en fin d'installation. C'est aussi ce que fait
# `butbutbut --update`, qui rejoue ce script.
PID_FILE="$DATA_HOME/$APP_NAME/butbutbut.pid"
if [ -f "$PID_FILE" ]; then
    # La premiere ligne, et elle seule : le fichier porte aussi l'empreinte du
    # processus, et `kill -0 "12345 1788938197.844"` ne viserait personne.
    DAEMON_PID="$(head -n 1 "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$DAEMON_PID" ] && kill -0 "$DAEMON_PID" 2>/dev/null; then
        kill "$DAEMON_PID" 2>/dev/null || true
        rm -f "$PID_FILE"
        say "daemon      : arrete (pid $DAEMON_PID) le temps de la copie"
    fi
fi

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR" "$BIN_DIR"
cp -R "$SRC_DIR/butbutbut" "$APP_DIR/butbutbut"
say "code        : $APP_DIR/butbutbut"

cat > "$BIN_DIR/butbutbut" <<EOF
#!/usr/bin/env bash
# Lanceur genere par install.sh
export PYTHONPATH="$APP_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$PYTHON" -m butbutbut "\$@"
EOF
chmod +x "$BIN_DIR/butbutbut"
ln -sf "$BIN_DIR/butbutbut" "$BIN_DIR/but"
say "commande    : $BIN_DIR/butbutbut  (alias : but)"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) say "ATTENTION   : $BIN_DIR n'est pas dans ton PATH"
       say "  -> ajoute  export PATH=\"\$HOME/.local/bin:\$PATH\"  a ton ~/.bashrc / ~/.zshrc" ;;
esac

# Fiche d'installation, relue par `butbutbut --update` : d'ou vient le code,
# quel commit, et avec quelles options il a ete installe.
COMMIT=""
if [ -d "$SRC_DIR/.git" ] && command -v git >/dev/null 2>&1; then
    COMMIT="$(git -C "$SRC_DIR" rev-parse HEAD 2>/dev/null || true)"
fi
VERSION="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' \
    "$SRC_DIR/butbutbut/__init__.py" 2>/dev/null || true)"
RECORD_DIR="$DATA_HOME/$APP_NAME"
mkdir -p "$RECORD_DIR"
cat > "$RECORD_DIR/install.json" <<EOF
{
  "source": "$SRC_DIR",
  "commit": "$COMMIT",
  "version": "$VERSION",
  "leagues": "$LEAGUES",
  "position": "$POSITION",
  "interval": ${INTERVAL:-null},
  "autostart": $([ "$AUTOSTART" -eq 1 ] && echo true || echo false),
  "app_dir": "$APP_DIR",
  "bin_dir": "$BIN_DIR",
  "python": "$PYTHON",
  "platform": "$(uname -s)",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
say "fiche       : $RECORD_DIR/install.json"

# --------------------------------------------------------- demarrage ---------
if [ "$AUTOSTART" -eq 1 ]; then
    head_ "Demarrage automatique"
    if [ "$(uname -s)" = "Darwin" ]; then
        PLIST="$HOME/Library/LaunchAgents/com.butbutbut.goals.plist"
        mkdir -p "$(dirname "$PLIST")"
        {
            printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>'
            printf '%s\n' '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
            printf '%s\n' '<plist version="1.0">'
            printf '%s\n' '<dict>'
            printf '%s\n' '    <key>Label</key><string>com.butbutbut.goals</string>'
            printf '%s\n' '    <key>ProgramArguments</key>'
            printf '%s\n' '    <array>'
            printf '        <string>%s</string>\n' "$BIN_DIR/butbutbut"
            for arg in "${DAEMON_ARGS[@]}"; do
                printf '        <string>%s</string>\n' "$arg"
            done
            printf '%s\n' '    </array>'
            printf '%s\n' '    <key>RunAtLoad</key><true/>'
            printf '%s\n' '    <key>KeepAlive</key><true/>'
            printf '%s\n' '    <key>ProcessType</key><string>Interactive</string>'
            printf '%s\n' '</dict>'
            printf '%s\n' '</plist>'
        } > "$PLIST"
        launchctl unload "$PLIST" >/dev/null 2>&1 || true
        launchctl load "$PLIST"
        say "LaunchAgent : $PLIST (charge)"
    elif command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
        UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
        mkdir -p "$UNIT_DIR"

        # default.target demarre avec le gestionnaire utilisateur, avant que la
        # session ne publie DISPLAY et WAYLAND_DISPLAY : butbutbut n'avait alors
        # aucun ecran ou dessiner. Plasma publie ces variables en meme temps que
        # plasma-workspace.target, sans les ordonner face a
        # graphical-session.target, d'ou l'accroche specifique quand elle existe.
        CIBLE="graphical-session.target"
        if systemctl --user list-unit-files plasma-workspace.target >/dev/null 2>&1; then
            CIBLE="plasma-workspace.target"
        fi

        cat > "$UNIT_DIR/butbutbut.service" <<EOF
[Unit]
Description=butbutbut - alerte de buts des 5 grands championnats
After=$CIBLE
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=$BIN_DIR/butbutbut $ARGS_LINE
Restart=on-failure
RestartSec=30

[Install]
WantedBy=$CIBLE
EOF
        systemctl --user daemon-reload
        # reenable et pas enable : sur une mise a jour depuis une version
        # accrochee a default.target, enable ajouterait le nouveau lien sans
        # retirer l'ancien, et l'unite continuerait de demarrer trop tot.
        systemctl --user reenable butbutbut.service >/dev/null 2>&1 || true
        # restart et pas `enable --now` : sur une reinstallation l'unite peut
        # deja tourner, et --now ne relancerait pas le code fraichement copie.
        systemctl --user restart butbutbut.service
        say "systemd     : butbutbut.service actif, accroche a $CIBLE"
    else
        DESKTOP_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
        mkdir -p "$DESKTOP_DIR"
        cat > "$DESKTOP_DIR/butbutbut.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=butbutbut
Comment=Alerte de buts des 5 grands championnats
Exec=$BIN_DIR/butbutbut $ARGS_LINE
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
        say "autostart   : $DESKTOP_DIR/butbutbut.desktop"
    fi
else
    say "demarrage automatique ignore (--no-autostart)"
fi

head_ "Termine"
say "Voir l'empilement   : butbutbut --test 3"
say "Les matchs du jour  : butbutbut --scores"
say "Etat                : butbutbut --status"
say "Mettre a jour       : butbutbut --update"
say "Desinstaller        : ./uninstall.sh"
printf '\n'
"$BIN_DIR/butbutbut" --status || true
