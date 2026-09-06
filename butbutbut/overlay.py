"""Les cartes de score : elles s'empilent dans un coin de l'ecran, puis s'effacent.

Trois lignes par carte, toujours les memes :

    BUT !   LIGUE 1                                            35'
    Angers        1 - 2        Stade Rennais
    But de C. Arcus

L'equipe qui vient de marquer et son chiffre sont ecrits dans la couleur du
championnat, le nom du buteur ressort en clair. On sait donc d'un coup d'oeil
qui a marque, ou en est le match et dans quel championnat il se joue.

Deux buts coup sur coup ne se marchent pas dessus : chaque carte est une
fenetre a elle, et `Stack` les empile depuis le coin (la derniere arrivee est
collee au coin, les precedentes remontent). Quand l'une s'efface, les autres
reprennent sa place.

Multiplateforme, comme doot :
  - Windows : fond reellement transparent (-transparentcolor), fenetres
    "click-through" qui ne volent jamais le focus (styles etendus Win32) ;
  - macOS   : fenetres sans bordure, absentes du Dock ;
  - Linux   : fenetres de type "splash", posees au-dessus, sans decoration.
"""

from __future__ import annotations

import sys

from . import screens, sound

TRANSPARENT_KEY = "#ff00fe"
CARD_BG = "#0d1017"
CARD_EDGE = "#232936"
TEXT = "#f3f5f9"
MUTED = "#8b95a7"
CANCEL_ACCENT = "#ffa63d"

PAD_X = 22
PAD_Y = 16
BAR_WIDTH = 7
RADIUS = 14
GAP = 26                 # espace entre un nom d'equipe et le score
LINE_GAP = 12
STACK_GAP = 10           # espace entre deux cartes empilees

MIN_WIDTH = 420          # largeur de confort : les cartes empilees s'alignent
MAX_WIDTH = 720

FADE_IN = 0.22
FADE_OUT = 0.40
FADE_STEPS = 12
PUMP_MS = 120            # cadence des petites taches de la boucle tkinter

MAX_VISIBLE = 5          # au-dela, la plus ancienne carte cede sa place

FONT_CANDIDATES = {
    "win32": ("Segoe UI", "Tahoma", "Arial"),
    "darwin": ("SF Pro Text", "Helvetica Neue", "Helvetica"),
}
LINUX_FONTS = ("Inter", "Cantarell", "DejaVu Sans", "Liberation Sans", "Noto Sans")


class TkinterMissing(RuntimeError):
    """tkinter absent : paquet systeme a installer."""


def _import_tk():
    try:
        import tkinter as tk
        import tkinter.font as tkfont
    except Exception as exc:  # pragma: no cover - depend de l'install systeme
        raise TkinterMissing(
            "tkinter est introuvable. Installe-le :\n"
            "  Arch/Manjaro   : sudo pacman -S tk\n"
            "  Debian/Ubuntu  : sudo apt install python3-tk\n"
            "  Fedora         : sudo dnf install python3-tkinter\n"
            "  macOS (brew)   : brew install python-tk\n"
            "  Windows        : reinstalle Python en cochant 'tcl/tk'"
        ) from exc
    return tk, tkfont


# ----------------------------------------------------------------- carte -----

class Card:
    """Le contenu a afficher, independamment de tkinter."""

    __slots__ = ("title", "league", "minute", "home", "away", "home_score",
                 "away_score", "side", "parts", "accent", "muted_title")

    def __init__(self, title, league, minute, home, away, home_score, away_score,
                 side, detail, accent, muted_title=False):
        self.title = title              # "BUT !", "BUT ANNULE"...
        self.league = league            # "LIGUE 1"
        self.minute = minute            # "35'"
        self.home = home
        self.away = away
        self.home_score = home_score
        self.away_score = away_score
        self.side = side                # "home", "away" ou None
        self.parts = tuple(detail)      # [(texte, mis_en_valeur)] : le buteur
        self.accent = accent            # couleur du championnat
        self.muted_title = muted_title  # vrai pour un but annule

    @property
    def detail(self) -> str:
        """La troisieme ligne d'un bloc, sans mise en forme."""
        return "".join(text for text, _ in self.parts)

    @classmethod
    def from_event(cls, event):
        """Construit la carte a partir d'un evenement du watcher."""
        cancelled = not event.goal
        return cls(
            title=event.title,
            league=event.league.label,
            minute=event.minute,
            home=event.match.home,
            away=event.match.away,
            home_score=event.home_score,
            away_score=event.away_score,
            side=event.side,
            detail=event.detail_parts(),
            accent=CANCEL_ACCENT if cancelled else event.league.accent,
            muted_title=cancelled,
        )

    @classmethod
    def demo(cls, league=None):
        """Une carte d'exemple, pour `butbutbut --test`."""
        from .leagues import LEAGUES

        league = league or LEAGUES[0]
        samples = {
            "fra.1": ("Marseille", "Paris FC", 2, 1, "home", "M. Greenwood", "67'"),
            "eng.1": ("Arsenal", "Chelsea", 1, 2, "away", "C. Palmer", "74'"),
            "esp.1": ("Real Madrid", "Barcelona", 3, 3, "home", "K. Mbappe", "88'"),
            "ita.1": ("Inter Milan", "Juventus", 1, 0, "home", "M. Thuram", "23'"),
            "ger.1": ("Bayern Munich", "Dortmund", 4, 2, "home", "H. Kane", "56'"),
        }
        home, away, hs, as_, side, scorer, minute = samples.get(
            league.slug, samples["fra.1"])
        return cls(
            title="BUT !",
            league=league.label,
            minute=minute,
            home=home,
            away=away,
            home_score=hs,
            away_score=as_,
            side=side,
            detail=[("But de ", False), (scorer, True)],
            accent=league.accent,
        )

    def text_line(self) -> str:
        return "{} {} - {} {}".format(self.home, self.home_score,
                                      self.away_score, self.away)


# ----------------------------------------------------------------- dessin ----

def _pick_font(tkfont, families_wanted, size, weight="normal"):
    families = set(tkfont.families())
    for name in families_wanted:
        if name in families:
            return tkfont.Font(family=name, size=size, weight=weight)
    return tkfont.Font(size=size, weight=weight)


def _fonts(tkfont, scale: float):
    wanted = FONT_CANDIDATES.get(sys.platform, LINUX_FONTS)
    return {
        "label": _pick_font(tkfont, wanted, max(7, int(9 * scale)), "bold"),
        "title": _pick_font(tkfont, wanted, max(8, int(11 * scale)), "bold"),
        "team": _pick_font(tkfont, wanted, max(10, int(16 * scale)), "bold"),
        "score": _pick_font(tkfont, wanted, max(12, int(22 * scale)), "bold"),
        "detail": _pick_font(tkfont, wanted, max(8, int(11 * scale)), "normal"),
        "scorer": _pick_font(tkfont, wanted, max(8, int(12 * scale)), "bold"),
    }


def _detail_font(fonts, strong):
    return fonts["scorer"] if strong else fonts["detail"]


def _make_click_through(window) -> None:
    """Windows : la fenetre ignore la souris et ne prend jamais le focus."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
        )
    except Exception:
        pass


def _setup_transparency(window) -> str:
    """Rend les coins arrondis possibles ; renvoie la couleur de fond a utiliser."""
    if sys.platform == "win32":
        try:
            window.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
            return TRANSPARENT_KEY
        except Exception:
            return CARD_BG

    if sys.platform == "darwin":
        try:
            window.wm_attributes("-transparent", True)
            window.config(bg="systemTransparent")
            return "systemTransparent"
        except Exception:
            return CARD_BG

    # X11 / Wayland : pas d'alpha par pixel garanti, on reste sur un fond plein.
    try:
        window.wm_attributes("-type", "splash")
    except Exception:
        pass
    return CARD_BG


def stack_positions(monitor, sizes, position="bottom-right", gap=STACK_GAP):
    """Ou poser chaque carte d'une pile, de la plus recente a la plus ancienne.

    `sizes` : [(largeur, hauteur)] dans l'ordre d'affichage, la premiere collee
    au coin. Depuis un coin du bas la pile monte, depuis le haut elle descend.
    """
    position = (position or "bottom-right").strip().lower()
    downwards = position.startswith("top") or position == "center"

    places = []
    offset = 0
    for width, height in sizes:
        x, y = monitor.place(width, height, position)
        y = y + offset if downwards else y - offset
        y = max(monitor.y, min(y, monitor.y + monitor.height - height))
        places.append((x, y))
        offset += height + gap
    return places


def _rounded(canvas, x0, y0, x1, y1, radius, **options):
    """Rectangle a coins arrondis, avec les seuls outils du Canvas."""
    radius = max(0, min(radius, int((x1 - x0) / 2), int((y1 - y0) / 2)))
    points = [
        x0 + radius, y0, x1 - radius, y0, x1, y0, x1, y0 + radius,
        x1, y1 - radius, x1, y1, x1 - radius, y1, x0 + radius, y1,
        x0, y1, x0, y1 - radius, x0, y0 + radius, x0, y0,
    ]
    return canvas.create_polygon(points, smooth=True, **options)


def _layout(card: Card, fonts):
    """Mesure la carte : largeur, hauteur et abscisses de chaque morceau."""
    # Le score est decoupe en trois pour pouvoir colorer le seul chiffre qui
    # vient de bouger.
    score_parts = (str(card.home_score), " - ", str(card.away_score))
    score_widths = [fonts["score"].measure(part) for part in score_parts]
    score_w = sum(score_widths)

    home_w = fonts["team"].measure(card.home)
    away_w = fonts["team"].measure(card.away)

    middle_w = home_w + GAP + score_w + GAP + away_w
    header_w = (fonts["title"].measure(card.title) + 18
                + fonts["label"].measure(card.league) + 18
                + fonts["label"].measure(card.minute))
    detail_w = sum(_detail_font(fonts, strong).measure(text)
                   for text, strong in card.parts)

    content_w = max(middle_w, header_w, detail_w)
    width = int(min(MAX_WIDTH, max(MIN_WIDTH, content_w + 2 * PAD_X + BAR_WIDTH)))

    header_h = max(fonts["title"].metrics("linespace"), fonts["label"].metrics("linespace"))
    score_h = max(fonts["team"].metrics("linespace"), fonts["score"].metrics("linespace"))
    detail_h = max(fonts["detail"].metrics("linespace"),
                   fonts["scorer"].metrics("linespace")) if card.parts else 0

    height = int(2 * PAD_Y + header_h + LINE_GAP + score_h
                 + ((LINE_GAP - 2 + detail_h) if card.parts else 0))

    return {
        "width": width,
        "height": height,
        "left": BAR_WIDTH + PAD_X,
        "right": width - PAD_X,
        "center": BAR_WIDTH + (width - BAR_WIDTH) / 2.0,
        "score_parts": score_parts,
        "score_widths": score_widths,
        "score_w": score_w,
        "header_y": PAD_Y + header_h / 2.0,
        "score_y": PAD_Y + header_h + LINE_GAP + score_h / 2.0,
        "detail_y": PAD_Y + header_h + LINE_GAP + score_h + (LINE_GAP - 2) + detail_h / 2.0,
    }


def _draw(canvas, card: Card, fonts, box, background):
    width, height = box["width"], box["height"]

    canvas.create_rectangle(0, 0, width, height, fill=background, outline=background)
    _rounded(canvas, 0, 0, width - 1, height - 1, RADIUS, fill=CARD_BG, outline=CARD_EDGE)
    # Filet vertical aux couleurs du championnat, cale dans l'arrondi.
    canvas.create_rectangle(3, RADIUS // 2, 3 + BAR_WIDTH, height - RADIUS // 2,
                            fill=card.accent, outline=card.accent)

    # --- ligne 1 : BUT ! / championnat / minute
    title = canvas.create_text(box["left"], box["header_y"], text=card.title,
                               fill=card.accent, font=fonts["title"], anchor="w")
    title_end = canvas.bbox(title)[2]
    canvas.create_text(title_end + 14, box["header_y"], text=card.league,
                       fill=MUTED, font=fonts["label"], anchor="w")
    if card.minute:
        canvas.create_text(box["right"], box["header_y"], text=card.minute,
                           fill=MUTED, font=fonts["label"], anchor="e")

    # --- ligne 2 : Equipe A  score - score  Equipe B
    # L'equipe qui vient de marquer et son chiffre passent en couleur.
    home_color = card.accent if card.side == "home" else TEXT
    away_color = card.accent if card.side == "away" else TEXT

    score_left = box["center"] - box["score_w"] / 2.0
    score_right = box["center"] + box["score_w"] / 2.0

    canvas.create_text(score_left - GAP, box["score_y"], text=card.home,
                       fill=home_color, font=fonts["team"], anchor="e")

    x = score_left
    for part, part_width, color in zip(box["score_parts"], box["score_widths"],
                                       (home_color, MUTED, away_color)):
        canvas.create_text(x, box["score_y"], text=part, fill=color,
                           font=fonts["score"], anchor="w")
        x += part_width

    canvas.create_text(score_right + GAP, box["score_y"], text=card.away,
                       fill=away_color, font=fonts["team"], anchor="w")

    # --- ligne 3 : le buteur, seul morceau en clair
    x = box["left"]
    for text, strong in card.parts:
        font = _detail_font(fonts, strong)
        canvas.create_text(x, box["detail_y"], text=text,
                           fill=TEXT if strong else MUTED, font=font, anchor="w")
        x += font.measure(text)


# ------------------------------------------------------------------ pile -----

class _Toast:
    """Une carte a l'ecran : sa fenetre, sa place dans la pile, sa duree."""

    def __init__(self, stack, card: Card, duration: float):
        tk = stack.tk
        self.stack = stack
        self.card = card
        self.duration = max(1.0, float(duration))
        self.closing = False

        self.window = tk.Toplevel(stack.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        for attribute, value in (("-topmost", True), ("-alpha", 0.0)):
            try:
                self.window.wm_attributes(attribute, value)
            except Exception:
                pass

        background = _setup_transparency(self.window)
        self.box = _layout(card, stack.fonts)
        self.width = self.box["width"]
        self.height = self.box["height"]

        canvas = tk.Canvas(self.window, width=self.width, height=self.height,
                           bg=background, highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)
        _draw(canvas, card, stack.fonts, self.box, background)

    def move(self, x: int, y: int) -> None:
        try:
            self.window.geometry("{}x{}+{}+{}".format(self.width, self.height, x, y))
        except Exception:
            pass

    def start(self) -> None:
        try:
            self.window.deiconify()
        except Exception:
            return
        _make_click_through(self.window)

        hold_ms = max(200, int((self.duration - FADE_IN - FADE_OUT) * 1000))
        self._fade(self.stack.opacity, FADE_STEPS,
                   max(10, int(FADE_IN * 1000 / FADE_STEPS)),
                   lambda: self._after(hold_ms, self.close))
        # Filet de securite : si le gestionnaire de fenetres avale les
        # animations, la carte disparait quand meme.
        self._after(int(self.duration * 1000) + 3000, self.destroy)

    def close(self) -> None:
        if self.closing:
            return
        self.closing = True
        self._fade(0.0, FADE_STEPS, max(10, int(FADE_OUT * 1000 / FADE_STEPS)),
                   self.destroy)

    def destroy(self) -> None:
        self.stack._remove(self)

    # -- interne

    def _after(self, ms, callback):
        try:
            self.window.after(ms, callback)
        except Exception:
            pass

    def _fade(self, target, remaining, step, done):
        if not self.window.winfo_exists():
            return
        try:
            current = float(self.window.wm_attributes("-alpha"))
        except Exception:
            current = target
            remaining = 0
        if remaining <= 0:
            try:
                self.window.wm_attributes("-alpha", target)
            except Exception:
                pass
            done()
            return
        try:
            self.window.wm_attributes("-alpha", current + (target - current) / remaining)
        except Exception:
            pass
        self._after(step, lambda: self._fade(target, remaining - 1, step, done))


class Stack:
    """La pile de cartes : une racine tkinter, N fenetres empilees dans un coin.

    La derniere carte arrivee est collee au coin, les precedentes remontent
    (ou descendent, si le coin choisi est en haut). Quand une carte s'efface,
    les autres reprennent sa place.
    """

    def __init__(self, screen=None, position="bottom-right", opacity=1.0,
                 scale=1.0, max_visible=MAX_VISIBLE):
        self.screen = screen
        self.position = (position or "bottom-right").strip().lower()
        self.opacity = max(0.05, min(1.0, float(opacity)))
        self.scale = float(scale)
        self.max_visible = max(1, int(max_visible))

        self.tk = None
        self.root = None
        self.fonts = None
        self._toasts = []      # du plus recent (au coin) au plus ancien
        self._pending = 0      # cartes programmees mais pas encore affichees
        self._monitor = None

    # ------------------------------------------------------------- cycle ----

    def open(self) -> "Stack":
        """Cree la racine tkinter. Leve TkinterMissing si tkinter manque."""
        if self.root is not None:
            return self
        tk, tkfont = _import_tk()
        self.tk = tk
        self.root = tk.Tk()
        self.root.withdraw()
        self.fonts = _fonts(tkfont, self.scale)
        self.refresh_monitor()
        return self

    def refresh_monitor(self):
        """(Re)lit la configuration des ecrans : elle peut changer en cours de route."""
        self._monitor = screens.pick(screens.monitors(), self.screen)
        return self._monitor

    def close(self) -> None:
        for toast in list(self._toasts):
            try:
                toast.window.destroy()
            except Exception:
                pass
        self._toasts = []
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None

    def stop(self) -> None:
        """Fait rendre la main a run()."""
        if self.root is not None:
            try:
                self.root.quit()
            except Exception:
                pass

    def run(self) -> None:
        """Boucle tkinter. Rend la main sur stop()."""
        self.open()
        self.root.mainloop()

    def run_until_idle(self, check_ms: int = PUMP_MS) -> None:
        """Boucle jusqu'a ce que la pile soit vide (utilise par --test)."""
        self.open()

        def check():
            if not self._toasts and self._pending == 0:
                self.stop()
                return
            self.root.after(check_ms, check)

        self.root.after(check_ms, check)
        self.root.mainloop()

    def every(self, ms: int, callback) -> None:
        """Rappelle `callback` toutes les `ms` millisecondes dans la boucle tkinter.

        C'est par la que la boucle de surveillance, qui vit dans un autre fil,
        fait remonter ses buts : tkinter n'aime pas etre touche ailleurs que
        dans son propre fil.
        """
        self.open()

        def tick():
            try:
                callback()
            finally:
                if self.root is not None:
                    try:
                        self.root.after(ms, tick)
                    except Exception:
                        pass

        self.root.after(ms, tick)

    # ------------------------------------------------------------ cartes ----

    def push(self, card: Card, duration: float = 6.0) -> None:
        """Ajoute une carte au coin, en decalant celles deja affichees."""
        self.open()

        # Trop de cartes : la plus ancienne s'en va tout de suite.
        while len(self._toasts) >= self.max_visible:
            self._toasts[-1].destroy()

        toast = _Toast(self, card, duration)
        self._toasts.insert(0, toast)
        self._reposition()
        toast.start()

    def push_later(self, delay_ms: int, card: Card, duration: float = 6.0) -> None:
        """Programme une carte : sert a montrer l'empilement (`--test 3`)."""
        self.open()
        self._pending += 1

        def fire():
            self._pending -= 1
            self.push(card, duration)

        self.root.after(max(0, int(delay_ms)), fire)

    def _remove(self, toast) -> None:
        try:
            toast.window.destroy()
        except Exception:
            pass
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._reposition()

    def _reposition(self) -> None:
        """Recalcule la place de chaque carte depuis le coin choisi."""
        monitor = self._monitor or self.refresh_monitor()
        sizes = [(toast.width, toast.height) for toast in self._toasts]
        for toast, (x, y) in zip(self._toasts,
                                 stack_positions(monitor, sizes, self.position)):
            toast.move(x, y)

    def __len__(self):
        return len(self._toasts)


# -------------------------------------------------------------- raccourcis ---

def show(cards, duration: float = 6.0, sound_path=None, screen=None,
         position="bottom-right", opacity: float = 1.0, scale: float = 1.0,
         stagger: float = 0.9) -> None:
    """Affiche une ou plusieurs cartes, et rend la main quand tout est efface.

    Bloquant : pratique pour `--test`. Le daemon, lui, garde une Stack ouverte
    et pousse ses cartes au fil des buts.
    """
    if isinstance(cards, Card):
        cards = [cards]

    stack = Stack(screen=screen, position=position, opacity=opacity, scale=scale)
    stack.open()
    try:
        for index, card in enumerate(cards):
            stack.push_later(int(index * stagger * 1000), card, duration)
        handle = sound.play_async(sound_path) if sound_path else None
        try:
            stack.run_until_idle()
        finally:
            sound.release(handle)
    finally:
        stack.close()
