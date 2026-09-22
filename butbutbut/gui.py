"""Interface graphique de butbutbut.

La ligne de commande reste la source de verite : l'interface construit une
commande, l'execute dans un processus separe et rend sa sortie dans une console
integree. De cette facon, chaque nouveaute du CLI garde exactement le meme
comportement dans la GUI (validation, journal, instance unique et codes de
sortie compris).
"""

from __future__ import annotations

import os
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import __version__, config


# ----------------------------------------------------------------- modele ---

@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: str = "text"
    default: object = ""
    option: Optional[str] = None
    choices: Tuple[str, ...] = ()
    hint: str = ""
    required: bool = False


@dataclass(frozen=True)
class ActionSpec:
    name: str
    label: str
    section: str
    description: str
    flag: Optional[str] = None
    fields: Tuple[FieldSpec, ...] = ()
    button: str = "Executer"
    tone: str = "accent"
    confirm: str = ""


PERIOD_FIELD = FieldSpec(
    "period", "Periode", "choice", "Tout le journal", choices=(
        "Tout le journal", "Aujourd'hui", "7 derniers jours",
        "30 derniers jours", "Depuis une date"),
    hint="La meme periode est appliquee aux filtres et aux exports.")
SINCE_FIELD = FieldSpec(
    "since_date", "Date de depart", "date", date.today().isoformat(),
    hint="Format AAAA-MM-JJ ; utilise si la periode est « Depuis une date ».")


ACTIONS: Tuple[ActionSpec, ...] = (
    ActionSpec(
        "start", "Demarrer la surveillance", "EN DIRECT",
        "Surveille les competitions choisies et affiche les buts en temps reel.",
        fields=(FieldSpec(
            "record", "Enregistrer les releves", "save_file", "",
            "--record", hint="Optionnel : cree un fichier .jsonl ou .jsonl.gz."),),
        button="Demarrer", tone="live"),
    ActionSpec(
        "status", "Etat de la surveillance", "EN DIRECT",
        "Affiche le daemon, les matchs suivis, le son, les ecrans et la connexion.",
        "--status", button="Actualiser"),
    ActionSpec(
        "sync_stream", "Je vois le coup d'envoi", "EN DIRECT",
        "Mesure le retard du streaming et recale les prochaines alertes.",
        "--sync-stream", fields=(FieldSpec(
            "query", "Equipe (optionnel)", "text", "", None,
            hint="Utile si plusieurs matchs commencent ensemble."),),
        button="Synchroniser", tone="live"),
    ActionSpec(
        "serve", "Ecran compagnon local", "EN DIRECT",
        "Affiche les matchs, alertes synchronisees et souvenirs dans un navigateur.",
        "--serve", fields=(FieldSpec(
            "bind", "Adresse", "text", "8765", None,
            hint="8765 = cette machine ; 0.0.0.0:8765 = reseau local."),),
        button="Demarrer", tone="live"),
    ActionSpec(
        "stop", "Arreter la surveillance", "EN DIRECT",
        "Demande proprement au daemon actif de s'arreter.", "--stop",
        button="Arreter", tone="danger",
        confirm="Arreter la surveillance en cours ?"),
    ActionSpec(
        "test", "Tester les cartes", "EN DIRECT",
        "Affiche des cartes de demonstration pour verifier le rendu et le son.",
        "--test", fields=(FieldSpec(
            "count", "Nombre de cartes", "number", "1", None,
            hint="Trois cartes permettent de voir leur empilement."),),
        button="Lancer le test"),

    ActionSpec(
        "scores", "Matchs du jour", "MATCHS",
        "Tous les matchs du jour pour les competitions et equipes selectionnees.",
        "--scores", button="Afficher"),
    ActionSpec(
        "next", "Prochains matchs", "MATCHS",
        "Cherche le prochain match d'une equipe ou elargit la fenetre en jours.",
        "--next", fields=(FieldSpec(
            "query", "Equipe ou nombre de jours", "text", "", None,
            hint="Exemples : om, psg, 14 ou om,psg,3. Vide = 7 jours."),),
        button="Rechercher"),
    ActionSpec(
        "calendar", "Exporter le calendrier", "MATCHS",
        "Cree un fichier .ics des prochains matchs, importable dans un agenda.",
        "--calendar", fields=(
            FieldSpec(
                "query", "Equipe ou nombre de jours", "text", "", None,
                hint="Exemples : om, 60 ou om,90. Vide = 30 jours."),
            FieldSpec(
                "calendar_output", "Fichier de destination", "save_file",
                "butbutbut.ics", "--calendar-output", required=True,
                hint="Format iCalendar compatible Apple, Google et Outlook."),
        ), button="Exporter"),
    ActionSpec(
        "table", "Classements", "MATCHS",
        "Affiche les classements suivis ou surligne une equipe dans le sien.",
        "--table", fields=(FieldSpec(
            "query", "Competition ou equipe", "text", "", None,
            hint="Exemples : l1, nhl, top14, om ou l1,om."),),
        button="Afficher"),
    ActionSpec(
        "list_teams", "Catalogue des equipes", "MATCHS",
        "Liste les equipes des competitions selectionnees et leurs alias.",
        "--list-teams", button="Charger"),
    ActionSpec(
        "list_leagues", "Catalogue des competitions", "MATCHS",
        "Liste toutes les competitions disponibles et les noms acceptes.",
        "--list", button="Charger"),

    ActionSpec(
        "today", "Buts d'aujourd'hui", "JOURNAL",
        "Recapitule les buts signales depuis le debut de la journee.",
        "--today", button="Consulter"),
    ActionSpec(
        "story", "Carte souvenir", "JOURNAL",
        "Exporte la derniere fin de match en une carte HTML autonome.",
        "--story", fields=(FieldSpec(
            "query", "Equipe (optionnel)", "text", "", None,
            hint="Vide = le dernier match termine."),), button="Creer"),
    ActionSpec(
        "night", "La Nuit des buts", "JOURNAL",
        "Raconte une soiree en HTML : matchs, chronologies et temps forts.",
        "--night", fields=(FieldSpec(
            "query", "Date (optionnelle)", "date", "", None,
            hint="Vide = la derniere soiree du journal."),), button="Raconter"),
    ActionSpec(
        "week", "Sept derniers jours", "JOURNAL",
        "Recapitule les buts signales sur les sept derniers jours.",
        "--week", button="Consulter"),
    ActionSpec(
        "month", "Trente derniers jours", "JOURNAL",
        "Recapitule les buts signales sur les trente derniers jours.",
        "--month", button="Consulter"),
    ActionSpec(
        "since", "Depuis une date", "JOURNAL",
        "Choisis le premier jour a inclure dans le recapitulatif.",
        "--since", fields=(FieldSpec(
            "date", "Date de depart", "date", date.today().isoformat(), None,
            required=True, hint="Format AAAA-MM-JJ."),), button="Consulter"),
    ActionSpec(
        "top_scorers", "Classement des buteurs", "ANALYSE",
        "Classe les buteurs observes, avec les buts annules par la VAR deduits.",
        "--top-scorers", fields=(PERIOD_FIELD, SINCE_FIELD), button="Analyser"),
    ActionSpec(
        "stats", "Statistiques du journal", "ANALYSE",
        "Revele les buts par minute, competition et soiree prolifique.",
        "--stats", fields=(PERIOD_FIELD, SINCE_FIELD), button="Analyser"),
    ActionSpec(
        "constellation", "Constellation de la saison", "ANALYSE",
        "Cree une carte HTML, un point par but confirme dans le journal.",
        "--constellation", fields=(PERIOD_FIELD, SINCE_FIELD), button="Creer"),
    ActionSpec(
        "export", "Exporter les donnees", "ANALYSE",
        "Exporte les buts du journal en JSON ou CSV, dans un fichier ou la console.",
        "--export", fields=(
            FieldSpec("format", "Format", "choice", "csv", "--export",
                      choices=("csv", "json")),
            PERIOD_FIELD, SINCE_FIELD,
            FieldSpec("output_file", "Fichier de destination", "save_file", "",
                      hint="Optionnel : sans fichier, le resultat reste dans la console."),
        ), button="Exporter"),

    ActionSpec(
        "replay", "Rejouer un match", "REPLAYS",
        "Rejoue un enregistrement hors ligne avec les memes cartes et les memes sons.",
        "--replay", fields=(
            FieldSpec("file", "Enregistrement", "file", "", None,
                      required=True, hint="Fichier .jsonl ou .jsonl.gz."),
            FieldSpec("speed", "Vitesse", "number", "1", "--speed",
                      hint="60 rejoue une heure de match en une minute."),
        ), button="Rejouer"),
    ActionSpec(
        "test_hook", "Tester l'automatisation", "REPLAYS",
        "Simule un but et execute la commande configuree dans le crochet.",
        "--test-hook", fields=(FieldSpec(
            "command", "Commande au but", "text", "", "--on-goal",
            hint="Vide = utilise la commande des reglages."),), button="Tester"),
    ActionSpec(
        "regen_sound", "Regenerer la corne", "REPLAYS",
        "Recree le son synthetise fourni par defaut.", "--regen-sound",
        button="Regenerer"),

    ActionSpec(
        "screens", "Ecrans detectes", "SYSTEME",
        "Liste les ecrans, leurs dimensions et leur index pour les reglages.",
        "--screens", button="Detecter"),
    ActionSpec(
        "paths", "Dossiers et fichiers", "SYSTEME",
        "Affiche les chemins du journal, de la configuration, du son et de l'etat.",
        "--paths", button="Afficher"),
    ActionSpec(
        "check_update", "Verifier les mises a jour", "SYSTEME",
        "Compare la version installee avec la derniere version disponible.",
        "--check-update", fields=(FieldSpec(
            "dev", "Inclure la version de developpement", "switch", False,
            "--dev"),), button="Verifier"),
    ActionSpec(
        "update", "Mettre a jour", "SYSTEME",
        "Telecharge, reinstalle puis relance butbutbut.", "--update",
        fields=(FieldSpec(
            "dev", "Installer la version de developpement", "switch", False,
            "--dev"),), button="Mettre a jour", tone="danger",
        confirm="Mettre a jour butbutbut maintenant ?"),
    ActionSpec(
        "write_config", "Creer un fichier de configuration", "SYSTEME",
        "Genere le modele commente de toutes les options disponibles.",
        "--write-config", fields=(FieldSpec(
            "file", "Nouveau fichier", "save_file", "butbutbut.conf", None,
            required=True),), button="Creer"),
    ActionSpec(
        "version", "Version installee", "SYSTEME",
        "Affiche la version de butbutbut utilisee par cette interface.",
        "--version", button="Afficher"),
    ActionSpec(
        "help", "Aide complete", "SYSTEME",
        "Affiche la reference de toutes les options de la ligne de commande.",
        "--help", button="Afficher"),
)

ACTION_BY_NAME = {action.name: action for action in ACTIONS}


@dataclass(frozen=True)
class SettingSpec:
    name: str
    label: str
    section: str
    kind: str = "text"
    default: object = ""
    choices: Tuple[str, ...] = ()
    hint: str = ""


SETTINGS: Tuple[SettingSpec, ...] = (
    SettingSpec("leagues", "Competitions suivies", "CE QUE TU SUIS", "text", "",
                hint="Vide = les 5 grands. Ex. l1,pl,ucl ; all-sports pour tout."),
    SettingSpec("exclude", "Competitions exclues", "CE QUE TU SUIS", "text", "",
                hint="Meme syntaxe, par exemple liga,seriea."),
    SettingSpec("teams", "Equipes suivies", "CE QUE TU SUIS", "text", "",
                hint="Vide = toutes. Ex. om,psg ou ligue2:sochaux."),
    SettingSpec("exclude_teams", "Equipes exclues", "CE QUE TU SUIS", "text", ""),
    SettingSpec("pin", "Carte epinglee", "CE QUE TU SUIS", "text", "",
                hint="Une seule equipe dont le score reste a l'ecran."),
    SettingSpec("spoiler_free", "Mode sans spoiler", "CE QUE TU SUIS", "text", "",
                hint="Equipes dont les cartes et sons doivent rester caches."),

    SettingSpec("position", "Position des cartes", "AFFICHAGE", "choice",
                "bottom-right", ("bottom-right", "bottom-left", "top-right",
                                 "top-left", "center")),
    SettingSpec("screen", "Ecran", "AFFICHAGE", "text", "primary",
                hint="primary ou un index obtenu avec « Ecrans detectes »."),
    SettingSpec("duration", "Duree d'affichage (s)", "AFFICHAGE", "number", "",
                hint="Vide = duree du son, avec un minimum de 6 secondes."),
    SettingSpec("scale", "Taille des cartes", "AFFICHAGE", "number", "1.0"),
    SettingSpec("opacity", "Opacite", "AFFICHAGE", "number", "1.0",
                hint="Entre 0.0 et 1.0."),
    SettingSpec("no_overlay", "Desactiver les cartes", "AFFICHAGE", "switch", False),
    SettingSpec("terminal", "Cartes dans le terminal", "AFFICHAGE", "switch", False),
    SettingSpec("no_phase_cards", "Masquer les cartes de phase", "AFFICHAGE", "switch", False),
    SettingSpec("no_logos", "Masquer les ecussons", "AFFICHAGE", "switch", False),
    SettingSpec("red_cards", "Signaler les cartons rouges", "AFFICHAGE", "switch", False),
    SettingSpec("before_kickoff", "Annonce avant match (min)", "AFFICHAGE", "number", "0"),
    SettingSpec("retry_fullscreen", "Retenter apres plein ecran (s)", "AFFICHAGE", "number", "0"),

    SettingSpec("volume", "Volume", "SON ET VOIX", "number", "100",
                hint="De 0 a 100."),
    SettingSpec("no_sound", "Mode muet", "SON ET VOIX", "switch", False),
    SettingSpec("speak", "Lire les buts a voix haute", "SON ET VOIX", "switch", False),
    SettingSpec("sound_for", "Sons personnalises", "SON ET VOIX", "text", "",
                hint="Ex. om=C:/sons/om.wav,ucl=C:/sons/ucl.mp3"),
    SettingSpec("lang", "Langue des cartes", "SON ET VOIX", "choice", "",
                ("", "fr", "en", "es", "it", "de"),
                "Vide = langue du systeme."),

    SettingSpec("interval", "Releve en match (s)", "RYTHME ET DISCRETION", "number", "25"),
    SettingSpec("idle_interval", "Releve au repos (s)", "RYTHME ET DISCRETION", "number", "300"),
    SettingSpec("quiet_hours", "Heures silencieuses", "RYTHME ET DISCRETION", "text", "",
                hint="Ex. 23:00-08:00."),
    SettingSpec("quiet_while_presenting", "Silence pendant une presentation",
                "RYTHME ET DISCRETION", "switch", False),
    SettingSpec("catch_up", "Resume au retour de veille", "RYTHME ET DISCRETION", "switch", False),
    SettingSpec("stream_delay", "Retard du streaming (s)",
                "RYTHME ET DISCRETION", "number", "0",
                hint="0 = direct ; ou clique « Je vois le coup d'envoi »."),
    SettingSpec("quiet", "Journal seulement dans le fichier", "RYTHME ET DISCRETION", "switch", False),
    SettingSpec("on_goal", "Commande a chaque but", "AUTOMATISATION", "text", "",
                hint="Les variables BUT_* sont fournies a la commande."),
)

SETTING_BY_NAME = {setting.name: setting for setting in SETTINGS}


def action_arguments(action: ActionSpec, values: Dict[str, object]) -> List[str]:
    """Construit les arguments d'une action, sans le programme ni la config."""
    arguments: List[str] = []
    if action.flag:
        arguments.append(action.flag)

    # --export porte sa valeur sur le drapeau principal, pas sur un second
    # argument ajoute plus tard par la boucle generique.
    export_format = values.get("format") if action.name == "export" else None
    if export_format:
        arguments.append(str(export_format))

    for spec in action.fields:
        value = values.get(spec.name, spec.default)
        if spec.name in ("period", "since_date", "output_file", "format"):
            continue
        if action.name == "write_config" and spec.name == "file":
            # Ce chemin est passe a --config par execute(), puisque c'est la
            # destination de --write-config et non un argument positionnel.
            continue
        if spec.kind == "switch":
            if bool(value) and spec.option:
                arguments.append(spec.option)
            continue
        text = str(value).strip() if value is not None else ""
        if not text:
            continue
        if spec.option:
            arguments.extend((spec.option, text))
        else:
            arguments.append(text)

    period = str(values.get("period", ""))
    if period == "Aujourd'hui":
        arguments.append("--today")
    elif period == "7 derniers jours":
        arguments.append("--week")
    elif period == "30 derniers jours":
        arguments.append("--month")
    elif period == "Depuis une date":
        arguments.extend(("--since", str(values.get("since_date", "")).strip()))
    return arguments


def shell_command(arguments: Sequence[str]) -> str:
    """Une commande copiable, adaptee au shell qui accueille la GUI."""
    visible = ["butbutbut"] + list(arguments)
    if os.name == "nt":
        return subprocess.list2cmdline(visible)
    return shlex.join(visible)


def wheel_units(delta=0, button=None) -> int:
    """Normalise une molette Windows/macOS ou les boutons 4/5 de X11.

    Certaines souris rendent 120 par cran, les pavés tactiles de petits
    deltas et X11 deux pseudo-boutons. Aucun de ces cas ne doit finir a zero,
    sinon le scroll parait fonctionner avec une souris mais pas avec une autre.
    """
    if button == 4:
        return -3
    if button == 5:
        return 3
    if not delta:
        return 0
    if abs(delta) >= 120:
        return int(-delta / 120) * 3
    return -1 if delta > 0 else 1


def setting_defaults(path: Path) -> Dict[str, object]:
    values = {item.name: item.default for item in SETTINGS}
    outcome = config.read(path)
    values.update({key: value for key, value in outcome.values.items()
                   if key in values})
    return values


def serialize_settings(values: Dict[str, object]) -> str:
    """Ecrit une configuration complete et lisible par config.read()."""
    lines = [
        "# Configuration enregistree depuis l'interface graphique.",
        "# Les reglages peuvent aussi etre modifies a la main.",
        "",
        "[butbutbut]",
    ]
    current_section = ""
    for spec in SETTINGS:
        if spec.section != current_section:
            current_section = spec.section
            lines.extend(("", "# {}".format(current_section.lower())))
        value = values.get(spec.name, spec.default)
        if spec.kind == "switch":
            rendered = "oui" if bool(value) else "non"
        else:
            rendered = str(value).strip()
        # Une valeur vide est volontairement acceptee par le lecteur : elle
        # revient au defaut du programme.
        lines.append("{} = {}".format(spec.name, rendered))
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------- interface ---

def _load_tk():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    return tk, ttk, filedialog, messagebox


class ScrollFrame:
    """Cadre vertical defilable qui garde la largeur de son parent."""

    def __init__(self, tk, parent, background, always=False):
        from tkinter import ttk

        self.tk = tk
        self.always = always
        self.canvas = tk.Canvas(parent, highlightthickness=0,
                                background=background, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(parent, orient="vertical",
                                       command=self.canvas.yview,
                                       style="Modern.Vertical.TScrollbar")
        self.frame = tk.Frame(self.canvas, background=background)
        # App._route_scroll remonte depuis n'importe quel enfant (champ,
        # bouton, label...) jusqu'a ce marqueur. La molette ne depend donc
        # plus du fait que le pointeur soit exactement sur le canvas.
        self.canvas._butbutbut_scroll_target = self.canvas
        self.frame._butbutbut_scroll_target = self.canvas
        self.scrollbar._butbutbut_scroll_target = self.canvas
        self.window = self.canvas.create_window((0, 0), window=self.frame,
                                                anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.frame.bind("<Configure>", self._region)
        self.canvas.bind("<Configure>", self._width)

    def _region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        needed = self.always or self.frame.winfo_reqheight() > self.canvas.winfo_height()
        if needed and not self.scrollbar.winfo_ismapped():
            self.scrollbar.pack(side="right", fill="y")
        elif not needed and self.scrollbar.winfo_ismapped():
            self.scrollbar.pack_forget()

    def _width(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)
        self.canvas.after_idle(self._region)

    def pack(self, **kwargs):
        self.canvas.pack(side="left", fill="both", expand=True, **kwargs)
        self.canvas.after_idle(self._region)


class App:
    BG = "#07111f"
    SIDEBAR = "#091625"
    PANEL = "#0d1b2a"
    CARD = "#13243a"
    CARD_HOVER = "#192d46"
    FIELD = "#0a1727"
    LINE = "#223650"
    TEXT = "#f7f9fc"
    MUTED = "#8fa3bb"
    ACCENT = "#ff625f"
    ACCENT_HOVER = "#ff7774"
    LIVE = "#42d392"
    DANGER = "#ef476f"
    BLUE = "#64a8ff"

    def __init__(self, root, config_path: Path):
        self.tk, self.ttk, self.filedialog, self.messagebox = _load_tk()
        self.root = root
        self.config_path = Path(config_path)
        self.events = queue.Queue()
        self.processes: Dict[int, subprocess.Popen] = {}
        self.process_meta: Dict[int, dict] = {}
        self.action_vars: Dict[str, Dict[str, object]] = {}
        self.setting_vars: Dict[str, object] = {}
        self.nav_buttons: Dict[str, object] = {}
        self.active_action = "start"
        self.task_number = 0

        root.title("butbutbut — Centre de controle")
        root.geometry("1380x840")
        root.minsize(1120, 700)
        root.configure(background=self.BG)
        try:
            root.iconname("butbutbut")
        except Exception:
            pass
        root.protocol("WM_DELETE_WINDOW", self.close)

        self._styles()
        self._load_images()
        self._layout()
        self._install_scroll_routing()
        self._load_settings()
        self.select_action("start")
        self._poll_events()
        self._poll_daemon()

    # ---------------------------------------------------------- construction

    def _styles(self):
        style = self.ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Modern.TEntry", fieldbackground=self.FIELD,
                        foreground=self.TEXT, insertcolor=self.TEXT,
                        bordercolor=self.LINE, lightcolor=self.LINE,
                        darkcolor=self.LINE, padding=(12, 10))
        style.map("Modern.TEntry", bordercolor=[("focus", self.ACCENT)])
        style.configure("Modern.TCombobox", fieldbackground=self.FIELD,
                        background=self.FIELD, foreground=self.TEXT,
                        arrowcolor=self.MUTED, bordercolor=self.LINE,
                        lightcolor=self.LINE, darkcolor=self.LINE,
                        padding=(12, 9))
        style.map("Modern.TCombobox",
                  fieldbackground=[("readonly", self.FIELD)],
                  foreground=[("readonly", self.TEXT)],
                  selectbackground=[("readonly", self.FIELD)],
                  selectforeground=[("readonly", self.TEXT)],
                  bordercolor=[("focus", self.ACCENT)])
        style.configure("Modern.Vertical.TScrollbar", background=self.CARD,
                        troughcolor=self.PANEL, bordercolor=self.PANEL,
                        arrowcolor=self.MUTED)

    def _load_images(self):
        """Charge les illustrations embarquees, avec un repli silencieux."""
        assets = Path(__file__).with_name("assets")
        try:
            self.hero_image = self.tk.PhotoImage(
                file=str(assets / "gui_stadium.png"))
        except Exception:
            self.hero_image = None
        try:
            self.console_image = self.tk.PhotoImage(
                file=str(assets / "gui_live.png"))
        except Exception:
            self.console_image = None

    def _install_scroll_routing(self):
        """Fait suivre la molette a la zone scrollable sous le pointeur."""
        self.root.bind_all("<MouseWheel>", self._route_scroll, add="+")
        self.root.bind_all("<Button-4>", self._route_scroll, add="+")
        self.root.bind_all("<Button-5>", self._route_scroll, add="+")

    def _route_scroll(self, event):
        widget = event.widget
        target = None
        while widget is not None:
            target = getattr(widget, "_butbutbut_scroll_target", None)
            if target is not None:
                break
            widget = getattr(widget, "master", None)
        if target is None:
            return None
        units = wheel_units(getattr(event, "delta", 0),
                            getattr(event, "num", None))
        if units:
            target.yview_scroll(units, "units")
            return "break"
        return None

    def _bind_scroll_widget(self, widget):
        """Intercepte avant le binding de classe (notamment Combobox/Text)."""
        widget.bind("<MouseWheel>", self._route_scroll, add="+")
        widget.bind("<Button-4>", self._route_scroll, add="+")
        widget.bind("<Button-5>", self._route_scroll, add="+")

    def _layout(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=6)
        self.root.grid_columnconfigure(2, weight=5)

        self.sidebar = self.tk.Frame(self.root, bg=self.SIDEBAR, width=246,
                                     highlightbackground=self.LINE,
                                     highlightthickness=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.center = self.tk.Frame(self.root, bg=self.PANEL,
                                    highlightbackground=self.LINE,
                                    highlightthickness=1)
        self.center.grid(row=0, column=1, sticky="nsew")
        self.center.grid_rowconfigure(1, weight=1)
        self.center.grid_columnconfigure(0, weight=1)

        self.console_panel = self.tk.Frame(self.root, bg=self.BG)
        self.console_panel.grid(row=0, column=2, sticky="nsew")
        self.console_panel.grid_rowconfigure(3, weight=1)
        self.console_panel.grid_columnconfigure(0, weight=1)

        self._sidebar()
        self._center_header()
        self._console()

    def _sidebar(self):
        brand = self.tk.Frame(self.sidebar, bg=self.SIDEBAR, height=92)
        brand.pack(fill="x")
        brand.pack_propagate(False)
        mark = self.tk.Label(brand, text="B!", bg=self.ACCENT, fg="#ffffff",
                             font=("Segoe UI", 16, "bold"), width=3, height=1)
        mark.pack(side="left", padx=(20, 12), pady=23)
        title_box = self.tk.Frame(brand, bg=self.SIDEBAR)
        title_box.pack(side="left", pady=19)
        self.tk.Label(title_box, text="BUT BUT BUT", bg=self.SIDEBAR,
                      fg=self.TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.tk.Label(title_box, text="CENTRE DE CONTROLE", bg=self.SIDEBAR,
                      fg=self.MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w")

        search_box = self.tk.Frame(self.sidebar, bg=self.SIDEBAR)
        search_box.pack(fill="x", padx=16, pady=(0, 10))
        self.search_var = self.tk.StringVar()
        search = self.ttk.Entry(search_box, textvariable=self.search_var,
                                style="Modern.TEntry")
        search.pack(fill="x")
        search.insert(0, "Rechercher une commande")
        search.configure(foreground=self.MUTED)

        def focus_in(_event):
            if self.search_var.get() == "Rechercher une commande":
                self.search_var.set("")
                search.configure(foreground=self.TEXT)

        def focus_out(_event):
            if not self.search_var.get():
                self.search_var.set("Rechercher une commande")
                search.configure(foreground=self.MUTED)

        search.bind("<FocusIn>", focus_in)
        search.bind("<FocusOut>", focus_out)
        self.search_var.trace_add("write", lambda *_: self._rebuild_nav())

        nav_host = self.tk.Frame(self.sidebar, bg=self.SIDEBAR)
        nav_host.pack(fill="both", expand=True)
        # La liste contient volontairement toutes les commandes. Sa barre
        # reste visible pour rendre les sections situees plus bas evidentes.
        self.nav_scroll = ScrollFrame(self.tk, nav_host, self.SIDEBAR, always=True)
        self.nav_scroll.pack()
        search._butbutbut_scroll_target = self.nav_scroll.canvas
        self._rebuild_nav()

        bottom = self.tk.Frame(self.sidebar, bg=self.SIDEBAR)
        bottom.pack(fill="x", padx=14, pady=14)
        self.settings_button = self._button(
            bottom, "⚙  Reglages", self.show_settings, bg=self.CARD,
            hover=self.CARD_HOVER, anchor="w")
        self.settings_button.pack(fill="x", ipady=3)

        status = self.tk.Frame(bottom, bg=self.SIDEBAR)
        status.pack(fill="x", pady=(13, 2))
        self.daemon_dot = self.tk.Label(status, text="●", bg=self.SIDEBAR,
                                        fg=self.MUTED, font=("Segoe UI", 9))
        self.daemon_dot.pack(side="left")
        self.daemon_label = self.tk.Label(
            status, text="Verification...", bg=self.SIDEBAR, fg=self.MUTED,
            font=("Segoe UI", 8))
        self.daemon_label.pack(side="left", padx=6)

    def _rebuild_nav(self):
        if not hasattr(self, "nav_scroll"):
            return
        for child in self.nav_scroll.frame.winfo_children():
            child.destroy()
        self.nav_buttons = {}
        query = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        if query == "rechercher une commande":
            query = ""
        section = None
        for action in ACTIONS:
            haystack = "{} {} {}".format(action.label, action.section,
                                          action.description).lower()
            if query and query not in haystack:
                continue
            if not query and action.section != section:
                section = action.section
                label = self.tk.Label(
                    self.nav_scroll.frame, text=section, bg=self.SIDEBAR,
                    fg="#617792", font=("Segoe UI", 7, "bold"), anchor="w")
                label.pack(fill="x", padx=20, pady=(13, 5))
            button = self._nav_button(action)
            button.pack(fill="x", padx=10, pady=1)
            self.nav_buttons[action.name] = button
        if query and not self.nav_buttons:
            self.tk.Label(self.nav_scroll.frame, text="Aucune commande",
                          bg=self.SIDEBAR, fg=self.MUTED,
                          font=("Segoe UI", 9)).pack(pady=24)

    def _nav_button(self, action):
        button = self.tk.Button(
            self.nav_scroll.frame, text="  {}".format(action.label),
            command=lambda: self.select_action(action.name),
            bg=self.SIDEBAR, fg=self.MUTED, activebackground=self.CARD,
            activeforeground=self.TEXT, relief="flat", bd=0,
            font=("Segoe UI", 9), anchor="w", padx=10, pady=8,
            cursor="hand2")
        button.bind("<Enter>", lambda _e, b=button: b.configure(
            bg=self.CARD if action.name != self.active_action else self.CARD_HOVER))
        button.bind("<Leave>", lambda _e, b=button: b.configure(
            bg=self.CARD_HOVER if action.name == self.active_action else self.SIDEBAR))
        return button

    def _center_header(self):
        header = self.tk.Frame(self.center, bg=self.PANEL, height=78)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        self.tk.Label(header, text="COMMANDES", bg=self.PANEL, fg=self.MUTED,
                      font=("Segoe UI", 8, "bold")).pack(side="left", padx=28)
        version = self.tk.Label(
            header, text="v{}".format(__version__), bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI", 8, "bold"), padx=10, pady=5)
        version.pack(side="right", padx=26)
        self.content_host = self.tk.Frame(self.center, bg=self.PANEL)
        self.content_host.grid(row=1, column=0, sticky="nsew")

    def _console(self):
        top = self.tk.Frame(self.console_panel, bg=self.BG, height=78)
        top.grid(row=0, column=0, sticky="ew", padx=26)
        top.grid_propagate(False)
        self.tk.Label(top, text="CONSOLE", bg=self.BG, fg=self.MUTED,
                      font=("Segoe UI", 8, "bold")).pack(side="left", pady=28)
        copy_button = self._button(top, "Copier", self.copy_console,
                                   bg=self.CARD, hover=self.CARD_HOVER)
        copy_button.pack(side="right", pady=20)
        clear_button = self._button(top, "Effacer", self.clear_console,
                                    bg=self.BG, hover=self.CARD)
        clear_button.pack(side="right", pady=20, padx=4)

        preview = self.tk.Frame(self.console_panel, bg=self.CARD)
        preview.grid(row=1, column=0, sticky="ew", padx=26, pady=(0, 14))
        self.tk.Label(preview, text="APERÇU DE LA COMMANDE", bg=self.CARD,
                      fg=self.MUTED, font=("Segoe UI", 7, "bold")).pack(
                          anchor="w", padx=15, pady=(12, 5))
        self.preview_var = self.tk.StringVar(value="butbutbut")
        self.preview_label = self.tk.Label(
            preview, textvariable=self.preview_var, bg=self.CARD, fg=self.BLUE,
            font=("Cascadia Mono", 8), anchor="w", justify="left",
            wraplength=390)
        self.preview_label.pack(fill="x", padx=15, pady=(0, 13))

        divider = self.tk.Frame(self.console_panel, bg=self.LINE, height=1)
        divider.grid(row=2, column=0, sticky="ew", padx=26)

        text_host = self.tk.Frame(self.console_panel, bg=self.BG)
        text_host.grid(row=3, column=0, sticky="nsew", padx=(26, 14), pady=14)
        text_host.grid_rowconfigure(0, weight=1)
        text_host.grid_columnconfigure(0, weight=1)
        self.output = self.tk.Text(
            text_host, bg=self.BG, fg="#c8d5e5", insertbackground=self.TEXT,
            selectbackground="#29476b", selectforeground=self.TEXT,
            relief="flat", bd=0, highlightthickness=0, wrap="word",
            font=("Cascadia Mono", 9), padx=2, pady=4, spacing1=2,
            state="disabled", width=1)
        scroll = self.ttk.Scrollbar(
            text_host, orient="vertical", command=self.output.yview,
            style="Modern.Vertical.TScrollbar")
        def sync_scroll(first, last):
            scroll.set(first, last)
            if float(first) <= 0.0 and float(last) >= 1.0:
                scroll.grid_remove()
            else:
                scroll.grid()

        self.output.configure(yscrollcommand=sync_scroll)
        self.output._butbutbut_scroll_target = self.output
        self._bind_scroll_widget(self.output)
        text_host._butbutbut_scroll_target = self.output
        preview._butbutbut_scroll_target = self.output
        self.output.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.output.tag_configure("command", foreground=self.ACCENT,
                                  font=("Cascadia Mono", 9, "bold"))
        self.output.tag_configure("success", foreground=self.LIVE)
        self.output.tag_configure("error", foreground="#ff8095")
        self.output.tag_configure("muted", foreground=self.MUTED)
        self.output.tag_configure("center", justify="center")
        self.console_pristine = True
        self._console_welcome()

        footer = self.tk.Frame(self.console_panel, bg=self.BG, height=62)
        footer.grid(row=4, column=0, sticky="ew", padx=26)
        footer.grid_propagate(False)
        self.running_var = self.tk.StringVar(value="Aucune commande en cours")
        self.tk.Label(footer, textvariable=self.running_var, bg=self.BG,
                      fg=self.MUTED, font=("Segoe UI", 8)).pack(
                          side="left", pady=18)
        self.cancel_button = self._button(
            footer, "Interrompre", self.cancel_last, bg=self.CARD,
            hover=self.DANGER)
        self.cancel_button.pack(side="right", pady=11)
        self.cancel_button.configure(state="disabled")

    # --------------------------------------------------------------- contenu

    def select_action(self, name: str):
        self.active_action = name
        for action_name, button in self.nav_buttons.items():
            selected = action_name == name
            button.configure(
                bg=self.CARD_HOVER if selected else self.SIDEBAR,
                fg=self.TEXT if selected else self.MUTED)
        self.settings_button.configure(bg=self.CARD)
        self._clear_content()
        action = ACTION_BY_NAME[name]
        self.content_scroll = ScrollFrame(self.tk, self.content_host, self.PANEL)
        self.content_scroll.pack(padx=0)
        body = self.content_scroll.frame
        body.configure(padx=30, pady=12)

        self.tk.Label(body, text=action.section, bg=self.PANEL,
                      fg=self.ACCENT, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.tk.Label(body, text=action.label, bg=self.PANEL, fg=self.TEXT,
                      font=("Segoe UI", 23, "bold"), anchor="w").pack(
                          fill="x", pady=(6, 8))
        self.tk.Label(body, text=action.description, bg=self.PANEL, fg=self.MUTED,
                      font=("Segoe UI", 10), anchor="w", justify="left",
                      wraplength=480).pack(fill="x", pady=(0, 24))

        if self.hero_image is not None:
            visual = self.tk.Frame(body, bg=self.CARD,
                                   highlightbackground=self.LINE,
                                   highlightthickness=1)
            visual.pack(fill="x", pady=(0, 20))
            self.tk.Label(visual, image=self.hero_image, bg=self.CARD,
                          bd=0).pack(fill="x")

        values = self.action_vars.setdefault(name, {})
        if action.fields:
            card = self.tk.Frame(body, bg=self.CARD, padx=18, pady=16)
            card.pack(fill="x", pady=(0, 20))
            self.tk.Label(card, text="PARAMETRES", bg=self.CARD, fg=self.MUTED,
                          font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(0, 10))
            for spec in action.fields:
                if spec.name not in values:
                    values[spec.name] = self._variable(spec.kind, spec.default)
                self._field(card, spec, values[spec.name], self.CARD)
        else:
            card = self.tk.Frame(body, bg=self.CARD, padx=18, pady=17)
            card.pack(fill="x", pady=(0, 20))
            self.tk.Label(card, text="AUCUN PARAMETRE NECESSAIRE", bg=self.CARD,
                          fg=self.MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
            self.tk.Label(card, text="Les reglages globaux seront appliques automatiquement.",
                          bg=self.CARD, fg=self.MUTED, font=("Segoe UI", 9),
                          wraplength=430, justify="left").pack(anchor="w", pady=(5, 0))

        note = self.tk.Frame(body, bg=self.FIELD, padx=16, pady=14)
        note.pack(fill="x", pady=(0, 22))
        self.tk.Label(note, text="i", bg=self.BLUE, fg="#06111f",
                      font=("Segoe UI", 9, "bold"), width=2).pack(side="left")
        self.tk.Label(
            note, text="Les options de l'onglet Reglages s'ajoutent a cette commande.",
            bg=self.FIELD, fg=self.MUTED, font=("Segoe UI", 8),
            wraplength=400, justify="left").pack(side="left", padx=10)

        run = self._button(
            body, "{}   →".format(action.button),
            lambda: self.execute(action),
            bg=self.DANGER if action.tone == "danger" else (
                self.LIVE if action.tone == "live" else self.ACCENT),
            hover="#f25f7e" if action.tone == "danger" else (
                "#57dfa3" if action.tone == "live" else self.ACCENT_HOVER),
            fg="#07111f" if action.tone == "live" else "#ffffff",
            font=("Segoe UI", 10, "bold"))
        run.pack(fill="x", ipady=6, pady=(0, 26))

        self._watch_action_values(name)
        self._update_preview()

    def show_settings(self):
        self.active_action = ""
        for button in self.nav_buttons.values():
            button.configure(bg=self.SIDEBAR, fg=self.MUTED)
        self.settings_button.configure(bg=self.CARD_HOVER)
        self._clear_content()
        self.content_scroll = ScrollFrame(self.tk, self.content_host, self.PANEL)
        self.content_scroll.pack(padx=0)
        body = self.content_scroll.frame
        body.configure(padx=30, pady=12)

        self.tk.Label(body, text="PREFERENCES", bg=self.PANEL,
                      fg=self.ACCENT, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.tk.Label(body, text="Reglages", bg=self.PANEL, fg=self.TEXT,
                      font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(6, 8))
        self.tk.Label(
            body, text="Ces choix s'appliquent a toutes les commandes lancees depuis l'interface.",
            bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10),
            anchor="w", justify="left", wraplength=480).pack(fill="x", pady=(0, 20))

        if self.hero_image is not None:
            self.tk.Label(body, image=self.hero_image, bg=self.CARD,
                          bd=0).pack(fill="x", pady=(0, 18))

        path_card = self.tk.Frame(body, bg=self.FIELD, padx=16, pady=13)
        path_card.pack(fill="x", pady=(0, 18))
        self.tk.Label(path_card, text="FICHIER ACTIF", bg=self.FIELD,
                      fg=self.MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.config_label = self.tk.Label(
            path_card, text=str(self.config_path), bg=self.FIELD, fg=self.BLUE,
            font=("Cascadia Mono", 8), anchor="w", justify="left",
            wraplength=450)
        self.config_label.pack(fill="x", pady=(5, 0))

        section = None
        card = None
        for spec in SETTINGS:
            if spec.section != section:
                section = spec.section
                card = self.tk.Frame(body, bg=self.CARD, padx=18, pady=16)
                card.pack(fill="x", pady=(0, 14))
                self.tk.Label(card, text=section, bg=self.CARD, fg=self.MUTED,
                              font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(0, 10))
            self._field(card, spec, self.setting_vars[spec.name], self.CARD)

        buttons = self.tk.Frame(body, bg=self.PANEL)
        buttons.pack(fill="x", pady=(4, 30))
        save = self._button(buttons, "Enregistrer la configuration", self.save_settings,
                            bg=self.ACCENT, hover=self.ACCENT_HOVER,
                            font=("Segoe UI", 9, "bold"))
        save.pack(side="left", fill="x", expand=True, ipady=5)
        reset = self._button(buttons, "Recharger", self.reload_settings,
                             bg=self.CARD, hover=self.CARD_HOVER)
        reset.pack(side="left", padx=(8, 0), ipady=5)
        self.preview_var.set("Les reglages sont injectes dans chaque commande.")

    def _clear_content(self):
        for child in self.content_host.winfo_children():
            child.destroy()

    def _variable(self, kind, value):
        if kind == "switch":
            return self.tk.BooleanVar(value=bool(value))
        if value is None:
            value = ""
        return self.tk.StringVar(value=str(value))

    def _field(self, parent, spec, variable, background):
        row = self.tk.Frame(parent, bg=background)
        row.pack(fill="x", pady=(0, 13))
        if spec.kind == "switch":
            checkbox = self.tk.Checkbutton(
                row, text=spec.label, variable=variable, bg=background,
                fg=self.TEXT, activebackground=background,
                activeforeground=self.TEXT, selectcolor=self.FIELD,
                highlightthickness=0, bd=0, font=("Segoe UI", 9),
                anchor="w", cursor="hand2")
            checkbox.pack(fill="x")
        else:
            self.tk.Label(row, text=spec.label, bg=background, fg=self.TEXT,
                          font=("Segoe UI", 9, "bold"), anchor="w").pack(
                              fill="x", pady=(0, 6))
            input_row = self.tk.Frame(row, bg=background)
            input_row.pack(fill="x")
            if spec.kind == "choice":
                widget = self.ttk.Combobox(
                    input_row, textvariable=variable, values=spec.choices,
                    state="readonly", style="Modern.TCombobox")
            else:
                widget = self.ttk.Entry(input_row, textvariable=variable,
                                        style="Modern.TEntry")
            widget.pack(side="left", fill="x", expand=True)
            self._bind_scroll_widget(widget)
            if spec.kind in ("file", "save_file"):
                choose = self._button(
                    input_row, "Choisir", lambda s=spec, v=variable: self._choose_file(s, v),
                    bg=self.FIELD, hover=self.CARD_HOVER)
                choose.pack(side="left", padx=(7, 0), ipady=3)
        if spec.hint:
            self.tk.Label(row, text=spec.hint, bg=background, fg=self.MUTED,
                          font=("Segoe UI", 8), anchor="w", justify="left",
                          wraplength=430).pack(fill="x", pady=(5, 0))

    def _choose_file(self, spec, variable):
        if spec.kind == "file":
            path = self.filedialog.askopenfilename(title=spec.label)
        else:
            initial = str(variable.get()).strip()
            path = self.filedialog.asksaveasfilename(
                title=spec.label,
                initialfile=Path(initial).name if initial else "")
        if path:
            variable.set(path)

    def _button(self, parent, text, command, bg, hover, fg=None,
                font=None, anchor="center"):
        fg = fg or self.TEXT
        font = font or ("Segoe UI", 8, "bold")
        button = self.tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground=hover, activeforeground=fg, relief="flat", bd=0,
            highlightthickness=0, padx=13, pady=7, font=font,
            cursor="hand2", anchor=anchor)
        button.bind("<Enter>", lambda _e: button.configure(bg=hover)
                    if str(button["state"]) != "disabled" else None)
        button.bind("<Leave>", lambda _e: button.configure(bg=bg)
                    if str(button["state"]) != "disabled" else None)
        return button

    # -------------------------------------------------------------- reglages

    def _load_settings(self):
        values = setting_defaults(self.config_path)
        for spec in SETTINGS:
            self.setting_vars[spec.name] = self._variable(
                spec.kind, values.get(spec.name, spec.default))

    def setting_values(self) -> Dict[str, object]:
        return {name: variable.get() for name, variable in self.setting_vars.items()}

    def reload_settings(self):
        values = setting_defaults(self.config_path)
        for spec in SETTINGS:
            self.setting_vars[spec.name].set(values.get(spec.name, spec.default))
        self._console_write("\nReglages recharges depuis {}.\n".format(
            self.config_path), "success")

    def save_settings(self):
        if self.config_path.exists():
            answer = self.messagebox.askyesno(
                "Enregistrer les reglages",
                "Remplacer la configuration existante ?\n\nUne copie .bak sera conservee.")
            if not answer:
                return
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            if self.config_path.exists():
                shutil.copy2(str(self.config_path), str(self.config_path) + ".bak")
            temporary = self.config_path.with_suffix(self.config_path.suffix + ".tmp")
            temporary.write_text(serialize_settings(self.setting_values()), encoding="utf-8")
            os.replace(str(temporary), str(self.config_path))
        except OSError as exc:
            self.messagebox.showerror("Configuration", str(exc))
            return
        self._console_write("\nConfiguration enregistree : {}\n".format(
            self.config_path), "success")
        self.messagebox.showinfo("Configuration", "Les reglages ont ete enregistres.")

    def _session_config(self) -> str:
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".conf",
            prefix="butbutbut-gui-", delete=False)
        try:
            handle.write(serialize_settings(self.setting_values()))
            return handle.name
        finally:
            handle.close()

    # -------------------------------------------------------------- commande

    def _watch_action_values(self, name):
        for variable in self.action_vars.get(name, {}).values():
            try:
                variable.trace_add("write", lambda *_: self._update_preview())
            except Exception:
                pass

    def _action_values(self, action):
        variables = self.action_vars.get(action.name, {})
        return {name: variable.get() for name, variable in variables.items()}

    def _update_preview(self):
        if not self.active_action:
            return
        action = ACTION_BY_NAME[self.active_action]
        values = self._action_values(action)
        self.preview_var.set(shell_command(action_arguments(action, values)))

    def _validate(self, action, values):
        for spec in action.fields:
            value = str(values.get(spec.name, "")).strip()
            if spec.required and not value:
                return "Le champ « {} » est obligatoire.".format(spec.label)
            if spec.kind == "date" and value:
                try:
                    date.fromisoformat(value)
                except ValueError:
                    return "« {} » doit etre au format AAAA-MM-JJ.".format(spec.label)
        if values.get("period") == "Depuis une date":
            try:
                date.fromisoformat(str(values.get("since_date", "")))
            except ValueError:
                return "La date de depart doit etre au format AAAA-MM-JJ."
        return ""

    def execute(self, action):
        values = self._action_values(action)
        error = self._validate(action, values)
        if error:
            self.messagebox.showwarning("Parametre manquant", error)
            return
        if action.confirm and not self.messagebox.askyesno(
                action.label, action.confirm):
            return

        arguments = action_arguments(action, values)
        output_file = str(values.get("output_file", "")).strip()
        temporary_config = ""
        if action.name == "write_config":
            # --write-config ecrit a l'emplacement designe par --config.
            config_path = str(values["file"]).strip()
        elif action.name in ("version", "help"):
            config_path = ""
        else:
            temporary_config = self._session_config()
            config_path = temporary_config

        command = [sys.executable, "-m", "butbutbut"]
        if config_path:
            command.extend(("--config", config_path))
        command.extend(arguments)
        self.preview_var.set(shell_command(arguments))
        self._start_process(command, action, temporary_config, output_file)

    def _start_process(self, command, action, temporary_config, output_file):
        self.task_number += 1
        task_id = self.task_number
        if self.console_pristine:
            self._clear_console_raw()
            self.console_pristine = False
        self._console_write("\n▶ {}\n".format(shell_command(command[3:])), "command")
        self._console_write("  Lancement...\n", "muted")
        self.running_var.set("1 commande en cours")
        self.cancel_button.configure(state="normal")
        thread = threading.Thread(
            target=self._run_process,
            args=(task_id, command, action, temporary_config, output_file),
            daemon=True)
        thread.start()

    def _run_process(self, task_id, command, action, temporary_config, output_file):
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["PYTHONUNBUFFERED"] = "1"
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                errors="replace", bufsize=1, creationflags=flags,
                env=environment)
            self.events.put(("started", task_id, process, action, temporary_config))
            collected = []
            if process.stdout is not None:
                for line in process.stdout:
                    collected.append(line)
                    self.events.put(("line", task_id, line))
            code = process.wait()
            self.events.put(("done", task_id, code, action,
                             "".join(collected), output_file, temporary_config))
        except Exception as exc:
            self.events.put(("failed", task_id, action, str(exc), temporary_config))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "started":
                    _, task_id, process, action, temporary = event
                    self.processes[task_id] = process
                    self.process_meta[task_id] = {
                        "action": action, "temporary": temporary}
                elif kind == "line":
                    self._console_write(event[2])
                elif kind == "done":
                    _, task_id, code, action, collected, output_file, temporary = event
                    self.processes.pop(task_id, None)
                    self.process_meta.pop(task_id, None)
                    if output_file and code == 0:
                        try:
                            Path(output_file).write_text(collected, encoding="utf-8")
                            self._console_write(
                                "  Export enregistre : {}\n".format(output_file),
                                "success")
                        except OSError as exc:
                            self._console_write("  Export impossible : {}\n".format(exc),
                                                "error")
                    tag = "success" if code == 0 else "error"
                    self._console_write("  Termine (code {}).\n".format(code), tag)
                    self._forget_temp(temporary)
                    self._running_state()
                elif kind == "failed":
                    _, task_id, action, message, temporary = event
                    self.processes.pop(task_id, None)
                    self.process_meta.pop(task_id, None)
                    self._console_write("  Impossible de lancer : {}\n".format(message),
                                        "error")
                    self._forget_temp(temporary)
                    self._running_state()
        except queue.Empty:
            pass
        self.root.after(80, self._poll_events)

    def _running_state(self):
        count = len(self.processes)
        if count:
            self.running_var.set("{} commande{} en cours".format(
                count, "s" if count > 1 else ""))
            self.cancel_button.configure(state="normal")
        else:
            self.running_var.set("Aucune commande en cours")
            self.cancel_button.configure(state="disabled")

    def cancel_last(self):
        if not self.processes:
            return
        task_id = max(self.processes)
        process = self.processes[task_id]
        try:
            process.terminate()
            self._console_write("\n  Interruption demandee.\n", "error")
        except OSError as exc:
            self._console_write("\n  Interruption impossible : {}\n".format(exc),
                                "error")

    def _forget_temp(self, path):
        if not path:
            return
        try:
            Path(path).unlink()
        except OSError:
            pass

    # --------------------------------------------------------------- console

    def _clear_console_raw(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _console_welcome(self):
        """Affiche une illustration tant qu'aucune commande n'a parle."""
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        if self.console_image is not None:
            start = self.output.index("end-1c")
            self.output.insert("end", "\n")
            self.output.image_create("end", image=self.console_image, pady=8)
            self.output.insert("end", "\n\n")
            self.output.tag_add("center", start, "end")
        self.output.insert(
            "end",
            "Centre de controle pret.\nChoisis une commande : son resultat apparaitra ici.\n",
            "muted")
        self.output.configure(state="disabled")
        self.output.yview_moveto(0.0)

    def _console_write(self, text, tag=None):
        self.output.configure(state="normal")
        self.output.insert("end", text, tag or ())
        self.output.see("end")
        self.output.configure(state="disabled")

    def clear_console(self):
        self.console_pristine = True
        self._console_welcome()

    def copy_console(self):
        text = self.output.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    # --------------------------------------------------------------- daemon

    def _poll_daemon(self):
        try:
            from .cli import running_pid
            pid = running_pid()
        except Exception:
            pid = None
        if pid:
            self.daemon_dot.configure(fg=self.LIVE)
            self.daemon_label.configure(text="Surveillance active · {}".format(pid),
                                        fg=self.LIVE)
        else:
            self.daemon_dot.configure(fg="#53677f")
            self.daemon_label.configure(text="Surveillance arretee", fg=self.MUTED)
        self.root.after(4000, self._poll_daemon)

    def close(self):
        if self.processes:
            if not self.messagebox.askyesno(
                    "Quitter",
                    "Des commandes sont encore en cours. Les interrompre et quitter ?"):
                return
            for process in list(self.processes.values()):
                try:
                    process.terminate()
                except OSError:
                    pass
            for meta in self.process_meta.values():
                self._forget_temp(meta.get("temporary", ""))
        self.root.destroy()


def main(config_path=None) -> int:
    """Ouvre la GUI ; importe tkinter seulement quand elle est demandee."""
    tk, _ttk, _filedialog, _messagebox = _load_tk()
    if config_path is None:
        # Import local pour ne pas creer de cycle quand cli.main appelle gui.
        from .cli import paths
        config_path = paths()["config"]
    try:
        root = tk.Tk()
    except Exception as exc:
        print("butbutbut : interface graphique indisponible : {}".format(exc),
              file=sys.stderr)
        return 4
    App(root, Path(config_path))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
