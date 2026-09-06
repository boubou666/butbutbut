"""Les couleurs de club et le cache d'ecussons.

Le choix de couleur est une fonction pure : c'est le coeur de la carte, une
couleur illisible etant pire que pas de couleur. Le cache, lui, est teste sans
jamais toucher au reseau : `fetch_now` accepte un `fetcher` factice, exactement
comme `espn.fetch` accepte un `opener`.
"""

import tempfile
import unittest
from pathlib import Path

from butbutbut import crests, overlay

from helpers import png_bytes

BG = overlay.CARD_BG
LEAGUE = "#f2e34c"


class TestNormalize(unittest.TestCase):
    def test_espn_writes_hex_without_the_hash(self):
        self.assertEqual(crests.normalize("0000bf"), "#0000bf")
        self.assertEqual(crests.normalize("FFFFFF"), "#ffffff")
        self.assertEqual(crests.normalize("  144992 "), "#144992")

    def test_the_short_form_is_expanded(self):
        self.assertEqual(crests.normalize("fff"), "#ffffff")
        self.assertEqual(crests.normalize("#0a4"), "#00aa44")

    def test_anything_that_is_not_a_colour_is_none(self):
        for value in (None, "", "  ", "transparent", "0000b", "0000bff",
                      "#12345g", 42, [], "rgb(0,0,0)"):
            self.assertIsNone(crests.normalize(value), repr(value))


class TestLuminanceAndContrast(unittest.TestCase):
    def test_black_and_white_are_the_two_ends(self):
        self.assertAlmostEqual(crests.luminance("#000000"), 0.0)
        self.assertAlmostEqual(crests.luminance("#ffffff"), 1.0)

    def test_contrast_is_symmetric_and_bounded(self):
        self.assertAlmostEqual(crests.contrast("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(crests.contrast("#ffffff", "#000000"), 21.0)
        self.assertAlmostEqual(crests.contrast(BG, BG), 1.0)

    def test_the_card_background_is_nearly_black(self):
        # Toute la mecanique repose la-dessus : sur ce fond, une couleur sombre
        # ne se voit pas.
        self.assertLess(crests.luminance(BG), 0.01)


class TestPickAccent(unittest.TestCase):
    """Les cas reels releves dans le tableau de bord, un par etage du repli."""

    def test_a_readable_club_colour_is_kept(self):
        # Bayern (dc052d) et Arsenal (e20520) : du rouge vif, lisible.
        self.assertEqual(crests.pick_accent("dc052d", "1a1a1a", LEAGUE, BG),
                         "#dc052d")
        self.assertEqual(crests.pick_accent("e20520", "003399", LEAGUE, BG),
                         "#e20520")

    def test_a_dark_club_colour_falls_back_on_the_alternate(self):
        # Troyes (0000bf), Chelsea (144992), Inter (00239c) : du bleu marine,
        # invisible sur le fond de la carte.
        for color, alternate, expected in (("0000bf", "fafafc", "#fafafc"),
                                           ("144992", "FFFFFF", "#ffffff"),
                                           ("00239c", "ffffff", "#ffffff"),
                                           ("990000", "FCE38A", "#fce38a")):
            self.assertEqual(
                crests.pick_accent(color, alternate, LEAGUE, BG), expected,
                color)

    def test_two_unreadable_colours_fall_back_on_the_league(self):
        # Paris FC : 000000 des deux cotes. Il n'y a rien a sauver.
        self.assertEqual(crests.pick_accent("000000", "000000", LEAGUE, BG),
                         LEAGUE)

    def test_missing_colours_fall_back_on_the_league(self):
        for color, alternate in (("", ""), (None, None), ("bidon", "")):
            self.assertEqual(crests.pick_accent(color, alternate, LEAGUE, BG),
                             LEAGUE)

    def test_whatever_it_returns_is_readable_or_the_fallback(self):
        """L'invariant de la fonction, celui qui compte vraiment."""
        samples = ("0000bf", "000000", "1a1a1a", "ffffff", "dc052d", "144992",
                   "00239c", "990000", "ffee00", "011f68", "", "n'importe quoi")
        for color in samples:
            for alternate in samples:
                chosen = crests.pick_accent(color, alternate, LEAGUE, BG)
                self.assertTrue(chosen == LEAGUE or crests.readable(chosen, BG),
                                "{} / {} -> {}".format(color, alternate, chosen))


class TestScaleFactors(unittest.TestCase):
    """tkinter ne redimensionne qu'en rapports entiers : zoom / subsample."""

    def check(self, width, height, target):
        zoom, subsample = crests.scale_factors(width, height, target)
        self.assertGreaterEqual(zoom, 1)
        self.assertGreaterEqual(subsample, 1)
        return max(width, height) * zoom // subsample

    def test_an_espn_logo_lands_just_under_the_target(self):
        # Les ecussons d'ESPN font 500x500.
        for target in range(12, 80):
            size = self.check(500, 500, target)
            self.assertLessEqual(size, target, target)
            # "Juste en dessous" : on ne veut pas d'un ecusson minuscule.
            self.assertGreaterEqual(size, target - 4, target)

    def test_a_small_logo_is_enlarged(self):
        self.assertGreater(self.check(16, 16, 40), 16)

    def test_it_never_goes_past_the_target(self):
        for width, height in ((500, 500), (300, 100), (64, 512), (7, 7),
                              (1, 1000), (9000, 9000)):
            self.assertLessEqual(self.check(width, height, 30), 30,
                                 (width, height))

    def test_nonsense_sizes_do_not_raise(self):
        self.assertEqual(crests.scale_factors(0, 0, 30), (1, 1))
        self.assertEqual(crests.scale_factors(-5, 10, 30), (1, 1))
        self.assertEqual(crests.scale_factors(500, 500, 0), (1, 1))


class TestCache(unittest.TestCase):
    URL = "https://a.espncdn.com/i/teamlogos/soccer/500/170.png"
    OTHER = "https://a.espncdn.com/i/teamlogos/soccer/500/180.png"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / "logos"

    def cache(self, **kwargs):
        return crests.Cache(self.directory, **kwargs)

    def test_the_file_name_is_stable_and_unique(self):
        cache = self.cache()
        self.assertEqual(cache.path_for(self.URL), cache.path_for(self.URL))
        self.assertNotEqual(cache.path_for(self.URL), cache.path_for(self.OTHER))
        self.assertEqual(cache.path_for(self.URL).suffix, ".png")
        self.assertEqual(cache.path_for(self.URL).parent, self.directory)

    def test_an_empty_cache_gives_nothing(self):
        self.assertIsNone(self.cache(enabled=False).get(self.URL))

    def test_a_stored_logo_comes_back(self):
        cache = self.cache(enabled=False)      # aucun fil de fond en jeu
        path = cache.store(self.URL, png_bytes())
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())
        self.assertIsNone(cache.get(self.URL))          # --no-logos : rien
        self.assertEqual(self.cache().get(self.URL), path)

    def test_what_is_not_a_png_is_refused(self):
        cache = self.cache(enabled=False)
        oversized = crests.PNG_MAGIC + b"x" * crests.MAX_BYTES
        for junk in (b"<html>404</html>", b"", "pas des octets", None, oversized):
            self.assertIsNone(cache.store(self.URL, junk), repr(junk)[:20])
        self.assertFalse(cache.path_for(self.URL).is_file())

    def test_nothing_is_asked_when_logos_are_off(self):
        asked = []

        def fetcher(url, _timeout):
            asked.append(url)
            return png_bytes()

        cache = self.cache(enabled=False, fetcher=fetcher)
        self.assertIsNone(cache.get(self.URL))
        self.assertFalse(cache.prefetch(self.URL))
        self.assertEqual(asked, [])

    def test_an_empty_url_is_simply_ignored(self):
        cache = self.cache()
        for url in ("", None):
            self.assertIsNone(cache.get(url))
            self.assertFalse(cache.prefetch(url))

    def test_fetch_now_goes_through_the_fetcher(self):
        cache = self.cache(fetcher=lambda _url, _timeout: png_bytes())
        path = cache.fetch_now(self.URL)
        self.assertEqual(path, cache.path_for(self.URL))
        self.assertEqual(cache.get(self.URL), path)

    def test_a_broken_download_leaves_no_trace(self):
        def broken(_url, _timeout):
            raise OSError("pas de reseau")

        cache = self.cache(fetcher=broken)
        self.assertIsNone(cache.fetch_now(self.URL))
        self.assertFalse(cache.path_for(self.URL).is_file())
        self.assertEqual(cache.cached(), [])

    def test_a_missing_logo_is_downloaded_for_the_next_time(self):
        """La regle : la carte du moment se passe de l'ecusson, pas la suivante."""
        cache = self.cache(fetcher=lambda _url, _timeout: png_bytes())
        self.assertIsNone(cache.get(self.URL))     # le but ne l'attend pas
        cache.join(5.0)
        self.assertEqual(cache.get(self.URL), cache.path_for(self.URL))

    def test_a_url_that_failed_is_not_asked_again(self):
        asked = []

        def broken(url, _timeout):
            asked.append(url)
            raise OSError("404")

        cache = self.cache(fetcher=broken)
        cache.get(self.URL)
        cache.join(5.0)
        for _ in range(5):
            cache.get(self.URL)
        cache.join(5.0)
        self.assertEqual(asked, [self.URL])

    def test_an_unwritable_directory_does_not_raise(self):
        # Un fichier la ou le cache attend un dossier : mkdir echouera.
        blocked = Path(self.temporary.name) / "bloque"
        blocked.write_text("pas un dossier")
        cache = crests.Cache(blocked)
        self.assertIsNone(cache.store(self.URL, png_bytes()))
        self.assertIsNone(cache.get(self.URL))
        self.assertEqual(cache.cached(), [])

    def test_failures_are_reported_without_stopping_anything(self):
        said = []
        cache = self.cache(fetcher=lambda *_: b"<html>", on_log=said.append)
        self.assertIsNone(cache.fetch_now(self.URL))
        cache = self.cache(fetcher=lambda *_: 1 / 0, on_log=said.append)
        self.assertIsNone(cache.fetch_now(self.URL))
        self.assertTrue(said)


if __name__ == "__main__":
    unittest.main()
