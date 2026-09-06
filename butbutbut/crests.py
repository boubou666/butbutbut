"""Les ecussons des clubs et leurs couleurs, sur la carte.

Deux choses qui vont ensemble, parce qu'elles viennent de la meme source :

  - **la couleur du club**. ESPN publie `team.color` et `team.alternateColor`,
    mais ces couleurs sont choisies pour un fond blanc. Le fond de la carte est
    presque noir : le bleu marine de Troyes (`0000bf`) y est illisible, et le
    noir du Paris FC (`000000`) n'existe carrement plus. On mesure donc le
    contraste, et on se rabat sur la couleur secondaire puis sur celle du
    championnat tant qu'on ne lit rien. Une couleur illisible est pire que pas
    de couleur du tout ;

  - **l'ecusson**, un PNG que tkinter 8.6 ouvre tout seul, sans Pillow. Une
    carte ne doit JAMAIS attendre le reseau : un but s'affiche dans la seconde.
    Les ecussons sont donc servis depuis un cache disque, et un ecusson encore
    inconnu part se telecharger dans un fil de fond - la carte du moment se
    passe de lui, celle du prochain but l'aura.

Rien qu'urllib, hashlib et threading : zero dependance, comme le reste.
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import urllib.request
from pathlib import Path

from . import __version__

# --------------------------------------------------------------- couleurs ----

HEX_SHAPE = re.compile(r"^#?([0-9a-f]{3}|[0-9a-f]{6})$")

# Seuil de contraste WCAG. 3.0 est le minimum pour du "grand texte" ; on prend
# un peu de marge, parce qu'un nom d'equipe reste petit sur une carte de coin.
MIN_CONTRAST = 3.5


def normalize(value):
    """Une couleur ESPN ("0000bf", "FFF") en "#rrggbb", ou None.

    Tout ce qui n'est pas une couleur - une cle absente, une chaine vide, un
    "transparent" surprise - vaut None : l'appelant se rabattra dessus.
    """
    if not value:
        return None
    text = str(value).strip().lower()
    found = HEX_SHAPE.match(text)
    if found is None:
        return None
    digits = found.group(1)
    if len(digits) == 3:
        digits = "".join(digit * 2 for digit in digits)
    return "#" + digits


def channels(color) -> tuple:
    """Les trois composantes 0-255 d'une couleur, ou (0, 0, 0)."""
    normalized = normalize(color)
    if normalized is None:
        return (0, 0, 0)
    return tuple(int(normalized[index:index + 2], 16) for index in (1, 3, 5))


def _linear(value: float) -> float:
    if value <= 0.03928:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def luminance(color) -> float:
    """Luminance relative WCAG, de 0.0 (noir) a 1.0 (blanc)."""
    red, green, blue = (_linear(part / 255.0) for part in channels(color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first, second) -> float:
    """Rapport de contraste WCAG entre deux couleurs, de 1.0 a 21.0."""
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def readable(color, background, minimum: float = MIN_CONTRAST) -> bool:
    """Vrai si `color` se detache assez de `background` pour etre lue."""
    if normalize(color) is None:
        return False
    return contrast(color, background) >= minimum


def pick_accent(color, alternate, fallback, background,
                minimum: float = MIN_CONTRAST) -> str:
    """La couleur a donner au club qui vient de marquer.

    Dans l'ordre : sa couleur, sa couleur secondaire, celle du championnat.
    On s'arrete a la premiere qui se lit sur le fond de la carte. Fonction
    pure : c'est le coeur de l'affaire, et c'est ce que les tests verifient.
    """
    for candidate in (color, alternate):
        normalized = normalize(candidate)
        if normalized is not None and readable(normalized, background, minimum):
            return normalized
    return fallback


# ------------------------------------------------------------ cache disque ---

USER_AGENT = "butbutbut/{} (+https://github.com/boubou666/butbutbut)".format(__version__)
DEFAULT_TIMEOUT = 6.0
MAX_BYTES = 1 << 20            # un ecusson d'ESPN pese ~30 ko : 1 Mio suffit
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _download(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "image/png,image/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(MAX_BYTES + 1)


class Cache:
    """Les ecussons deja telecharges, ranges sur le disque.

    `get()` ne bloque jamais et ne leve jamais : soit le fichier est la, soit il
    ne l'est pas et le telechargement part en tache de fond pour la prochaine
    fois. Un disque en lecture seule, un PNG corrompu, un 404 : rien de tout ca
    ne doit empecher une carte de s'afficher, ni faire tomber le daemon.
    """

    __slots__ = ("directory", "enabled", "timeout", "fetcher", "on_log",
                 "_lock", "_running", "_failed")

    def __init__(self, directory, enabled: bool = True,
                 timeout: float = DEFAULT_TIMEOUT, fetcher=None, on_log=None):
        self.directory = Path(directory)
        self.enabled = bool(enabled)
        self.timeout = float(timeout)
        # `fetcher` sert aux tests : n'importe quel callable(url, timeout) -> bytes.
        self.fetcher = fetcher
        self.on_log = on_log or (lambda message: None)
        self._lock = threading.Lock()
        self._running = {}          # url -> Thread en cours
        self._failed = set()        # urls a ne pas redemander dans cette session

    # ---------------------------------------------------------- lecture ----

    def path_for(self, url: str) -> Path:
        """Ou vit l'ecusson de cette URL.

        Le nom est un condense de l'URL : deux competitions peuvent servir le
        meme numero d'equipe, et une URL n'est pas toujours un nom de fichier
        valable sur toutes les plateformes.
        """
        digest = hashlib.sha1(str(url).encode("utf-8")).hexdigest()[:20]
        return self.directory / (digest + ".png")

    def get(self, url):
        """Le chemin de l'ecusson s'il est deja en cache, sinon None.

        Ne touche pas au reseau : c'est tout l'interet. Un ecusson manquant est
        seulement mis en file pour un telechargement de fond.
        """
        if not self.enabled or not url:
            return None
        path = self.path_for(url)
        try:
            if path.is_file() and path.stat().st_size > 0:
                return path
        except OSError:
            return None
        self.prefetch(url)
        return None

    def cached(self) -> list:
        """Les ecussons presents sur le disque. Sert a `--status`."""
        try:
            return sorted(p for p in self.directory.iterdir()
                          if p.is_file() and p.suffix == ".png")
        except OSError:
            return []

    # ------------------------------------------------------ telechargement --

    def prefetch(self, url) -> bool:
        """Lance le telechargement en tache de fond. Vrai s'il a demarre.

        Un meme ecusson n'est demande qu'une fois a la fois, et une URL qui a
        echoue n'est plus retentee : sinon chaque but d'un club dont l'ecusson
        n'existe pas relancerait la meme requete perdue.
        """
        if not self.enabled or not url:
            return False
        with self._lock:
            if url in self._failed or url in self._running:
                return False
            thread = threading.Thread(target=self._work, args=(url,),
                                      name="butbutbut-crest", daemon=True)
            self._running[url] = thread
        thread.start()
        return True

    def fetch_now(self, url):
        """Telecharge et range l'ecusson tout de suite. Rend son chemin ou None.

        C'est le corps de la tache de fond, isole pour etre testable sans fil
        ni reseau : il suffit de passer un `fetcher`.
        """
        if not url:
            return None
        try:
            fetcher = self.fetcher or _download
            data = fetcher(url, self.timeout)
        except Exception as exc:
            self.on_log("ecusson injoignable ({}) : {}".format(url, exc))
            return None
        return self.store(url, data)

    def store(self, url, data):
        """Range des octets deja recuperes. Rend le chemin ecrit, ou None.

        Un fichier n'apparait dans le cache que complet et reconnu comme PNG :
        une reponse tronquee ou une page d'erreur HTML n'a rien a y faire, et
        tkinter n'a pas a decouvrir ca au moment d'afficher un but.
        """
        if not isinstance(data, (bytes, bytearray)):
            return None
        data = bytes(data)
        if not data.startswith(PNG_MAGIC) or len(data) > MAX_BYTES:
            return None

        path = self.path_for(url)
        temporary = path.with_suffix(".part")
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with temporary.open("wb") as handle:
                handle.write(data)
            os.replace(str(temporary), str(path))
        except Exception as exc:
            try:
                temporary.unlink()
            except OSError:
                pass
            self.on_log("ecusson non ecrit ({}) : {}".format(path, exc))
            return None
        return path

    def join(self, timeout: float = 5.0) -> None:
        """Attend les telechargements en cours (arret du daemon, tests)."""
        with self._lock:
            threads = list(self._running.values())
        for thread in threads:
            thread.join(timeout)

    def _work(self, url) -> None:
        found = None
        try:
            found = self.fetch_now(url)
        finally:
            with self._lock:
                self._running.pop(url, None)
                if not found:
                    self._failed.add(url)


# ---------------------------------------------------------------- image ------

MAX_ZOOM = 4               # tkinter ne sait qu'agrandir en nombres entiers
MAX_SUBSAMPLE = 64


def scale_factors(width: int, height: int, target: int) -> tuple:
    """Le couple (zoom, subsample) qui approche le mieux `target`.

    tkinter ne redimensionne qu'en rapports entiers : `zoom()` multiplie,
    `subsample()` divise. On cherche donc le plus grand resultat qui ne DEPASSE
    pas la taille visee - une image plus grande deborderait de la place que
    `_layout` lui a reservee, et c'est exactement ce qu'on ne veut pas.
    """
    if width <= 0 or height <= 0 or target <= 0:
        return (1, 1)

    longest = max(width, height)
    best = None
    best_size = 0
    for zoom in range(1, MAX_ZOOM + 1):
        for subsample in range(1, MAX_SUBSAMPLE + 1):
            size = longest * zoom // subsample
            if size < 1 or size > target or size <= best_size:
                continue
            best, best_size = (zoom, subsample), size

    if best is None:
        # Une image demesuree : on divise autant qu'il faut, quitte a sortir
        # des bornes ci-dessus. Mieux vaut trop petit que par-dessus bord.
        return (1, -(-longest // target))
    return best


def photo(tk, path, target: int, master=None):
    """Un PhotoImage a la taille voulue, ou None si l'image est inexploitable.

    Un PNG tronque, un format que tkinter refuse, un fichier efface entre-temps :
    la carte s'affiche alors sans ecusson, et c'est tout.
    """
    try:
        image = tk.PhotoImage(file=str(path), master=master)
        zoom, subsample = scale_factors(image.width(), image.height(), target)
        if zoom > 1:
            image = image.zoom(zoom, zoom)
        if subsample > 1:
            image = image.subsample(subsample, subsample)
        return image
    except Exception:
        return None
