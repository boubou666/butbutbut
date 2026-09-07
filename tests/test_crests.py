"""Les couleurs de club et le cache d'ecussons.

Le choix de couleur est une fonction pure : c'est le coeur de la carte, une
couleur illisible etant pire que pas de couleur. Le cache, lui, est teste sans
jamais toucher au reseau : `fetch_now` accepte un `fetcher` factice, exactement
comme `espn.fetch` accepte un `opener`.
"""

import hashlib
import tempfile
import unittest
from pathlib import Path

from butbutbut import crests, overlay

from helpers import FakeFont, png_bytes

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


class TestFitSize(unittest.TestCase):
    """L'echelle des tailles demandees au combineur d'ESPN."""

    def test_a_size_is_rounded_up_onto_the_ladder(self):
        # Vers le haut, toujours : un ecusson demande plus petit que la place
        # qu'il occupera serait rezoome, donc floute.
        for target, expected in ((1, 64), (30, 64), (64, 64), (65, 128),
                                 (128, 128), (200, 256), (256, 256)):
            self.assertEqual(crests.fit_size(target), expected, target)

    def test_past_the_last_rung_the_original_wins(self):
        # 500x500, c'est ce qu'ESPN annonce : le combineur ne ferait que
        # l'agrandir.
        self.assertIsNone(crests.fit_size(257))
        self.assertIsNone(crests.fit_size(4000))

    def test_nonsense_asks_for_nothing(self):
        for target in (None, 0, -12, "", "grand", [], object()):
            self.assertIsNone(crests.fit_size(target), repr(target))


class TestCombinerUrl(unittest.TestCase):
    """La seule URL du programme qui ne vienne pas de la source.

    Elle est fabriquee, donc tenue en laisse courte : ce qu'on ne sait pas
    manipuler ne produit rien, et l'appelant repart avec l'annonce.
    """

    def test_a_real_href_becomes_a_resized_one(self):
        for href, path in (
                ("https://a.espncdn.com/i/teamlogos/soccer/500/170.png",
                 "/i/teamlogos/soccer/500/170.png"),
                ("https://a.espncdn.com/i/teamlogos/nhl/500/scoreboard/bos.png",
                 "/i/teamlogos/nhl/500/scoreboard/bos.png"),
                ("https://a.espncdn.com/i/teamlogos/rugby/teams/500/25922.png",
                 "/i/teamlogos/rugby/teams/500/25922.png")):
            self.assertEqual(
                crests.combiner_url(href, 64),
                "https://a.espncdn.com/combiner/i?img={}&h=64&w=64".format(path))

    def test_the_size_goes_on_both_sides(self):
        self.assertTrue(crests.combiner_url(
            "https://a.espncdn.com/i/teamlogos/soccer/500/170.png",
            128).endswith("&h=128&w=128"))

    def test_an_unexpected_shape_falls_back_on_the_announcement(self):
        for href in ("https://exemple.org/i/teamlogos/soccer/500/170.png",
                     "https://a.espncdn.com/i/teamlogos/soccer/500/170.svg",
                     "https://a.espncdn.com/i/teamlogos/soccer/500/170.png?w=1",
                     "https://a.espncdn.com/combiner/i?img=/i/x.png&h=64&w=64",
                     "ftp://a.espncdn.com/i/teamlogos/soccer/500/170.png",
                     "https://a.espncdn.com.exemple.org/i/x.png",
                     "", None, 42):
            self.assertIsNone(crests.combiner_url(href, 64), repr(href))

    def test_without_a_size_nothing_is_fabricated(self):
        for size in (None, 0):
            self.assertIsNone(crests.combiner_url(
                "https://a.espncdn.com/i/teamlogos/soccer/500/170.png", size))


class TestCrestSize(unittest.TestCase):
    """La taille demandee doit suivre l'affichage, donc --scale.

    Le calcul vit dans overlay - lui seul sait comment une carte est dessinee -
    mais c'est ici qu'il se verifie, parce que c'est le contrat du cache.
    """

    def measured(self, scale, ratio):
        """Ce que `_logo_size` rendrait avec une police de ce rapport."""
        points = max(10, int(16 * scale))
        return overlay._logo_size({"team": FakeFont(line=int(points * ratio))})

    def test_it_never_asks_for_less_than_the_card_will_show(self):
        # Une police de N points occupe entre 1.1 N et 1.8 N pixels de hauteur
        # de ligne selon la plateforme et la famille. On majore : trop grand ne
        # coute que des octets, trop petit se voit.
        for scale in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
            for ratio in (1.1, 1.4, 1.8):
                self.assertGreaterEqual(overlay.crest_size(scale),
                                        self.measured(scale, ratio),
                                        (scale, ratio))

    def test_a_bigger_card_asks_for_a_bigger_crest(self):
        sizes = [overlay.crest_size(scale) for scale in (1.0, 2.0, 4.0)]
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual([crests.fit_size(size) for size in sizes],
                         [64, 128, 256])

    def test_nonsense_scales_do_not_raise(self):
        for scale in (None, 0, -3):
            self.assertGreater(overlay.crest_size(scale), 0, repr(scale))


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
        # La signature suivie de rien compte aussi : c'est ce que rendrait une
        # reponse coupee en chemin, et tkinter ne doit pas la decouvrir au
        # moment d'afficher un but.
        for junk in (b"<html>404</html>", b"", "pas des octets", None, oversized,
                     crests.PNG_MAGIC, crests.PNG_MAGIC + b"coupe"):
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

    # ------------------------------------------------------- le combineur ---

    def small(self, size=64):
        """L'URL redimensionnee que le cache doit essayer en premier."""
        return crests.combiner_url(self.URL, size)

    def test_the_resized_url_is_tried_first_and_the_announcement_indexes_it(self):
        asked = []

        def fetcher(url, _timeout):
            asked.append(url)
            return png_bytes()

        cache = self.cache(size=64, fetcher=fetcher)
        path = cache.fetch_now(self.URL)
        self.assertEqual(asked, [self.small()])
        # Le cache reste indexe sur l'URL annoncee : c'est la seule que la
        # carte connait, et le repli doit ranger son image au meme endroit.
        self.assertEqual(path, cache.path_for(self.URL))
        self.assertEqual(cache.get(self.URL), path)

    def test_a_resized_url_that_answers_badly_falls_back_on_the_announcement(self):
        """Le coeur de l'affaire : l'URL fabriquee ne vaut que tant qu'elle repond."""
        for answer in (OSError("404"), b"", b"<html>404</html>",
                       crests.PNG_MAGIC + b"coupe", b"GIF89a"):
            asked = []

            def fetcher(url, _timeout, answer=answer):
                asked.append(url)
                if url == self.URL:
                    return png_bytes()
                if isinstance(answer, Exception):
                    raise answer
                return answer

            cache = self.cache(size=64, fetcher=fetcher)
            self.assertEqual(cache.fetch_now(self.URL),
                             cache.path_for(self.URL), repr(answer)[:30])
            self.assertEqual(asked, [self.small(), self.URL], repr(answer)[:30])
            self.assertEqual(cache.path_for(self.URL).read_bytes(), png_bytes())

    def test_an_href_we_cannot_handle_goes_out_as_it_is(self):
        asked = []
        other = "https://exemple.org/ecusson.png"

        def fetcher(url, _timeout):
            asked.append(url)
            return png_bytes()

        cache = self.cache(size=64, fetcher=fetcher)
        self.assertEqual(cache.fetch_now(other), cache.path_for(other))
        self.assertEqual(asked, [other])

    def test_two_sizes_do_not_tread_on_each_other(self):
        # Le meme ecusson en 64 et en 256 sont deux fichiers : sinon un
        # --scale change d'un jour a l'autre servirait l'image de l'autre
        # taille, sans jamais la remplacer.
        small = self.cache(size=64, fetcher=lambda _u, _t: png_bytes(8, 8))
        big = self.cache(size=200, fetcher=lambda _u, _t: png_bytes(16, 16))
        self.assertEqual((small.size, big.size), (64, 256))
        self.assertNotEqual(small.path_for(self.URL), big.path_for(self.URL))
        self.assertIsNotNone(small.fetch_now(self.URL))
        self.assertIsNotNone(big.fetch_now(self.URL))
        self.assertEqual(small.get(self.URL).read_bytes(), png_bytes(8, 8))
        self.assertEqual(big.get(self.URL).read_bytes(), png_bytes(16, 16))
        self.assertEqual(len(small.cached()), 2)

    def test_without_a_size_the_old_file_name_is_kept(self):
        # Les ecussons deja sur le disque sont ranges sous l'URL seule. Un
        # cache sans taille les retrouve : c'est ce qui garde le comportement
        # d'avant quand personne ne dit a quelle taille afficher.
        cache = self.cache()
        self.assertIsNone(cache.size)
        self.assertEqual(cache.candidates(self.URL), (self.URL,))
        digest = hashlib.sha1(self.URL.encode("utf-8")).hexdigest()[:20]
        self.assertEqual(cache.path_for(self.URL).name, digest + ".png")

    def test_the_card_of_the_moment_still_does_not_wait(self):
        cache = self.cache(size=64, fetcher=lambda _u, _t: png_bytes())
        self.assertIsNone(cache.get(self.URL))      # le but ne l'attend pas
        cache.join(5.0)
        self.assertEqual(cache.get(self.URL), cache.path_for(self.URL))

    def test_a_crest_that_exists_nowhere_stays_without_consequence(self):
        """Ni redimensionne ni annonce : la carte s'affiche sans image, et c'est tout."""
        asked = []

        def missing(url, _timeout):
            asked.append(url)
            raise OSError("404")

        cache = self.cache(size=64, fetcher=missing)
        self.assertIsNone(cache.get(self.URL))
        cache.join(5.0)
        self.assertEqual(asked, [self.small(), self.URL])
        self.assertEqual(cache.cached(), [])
        for _ in range(3):
            self.assertIsNone(cache.get(self.URL))
        cache.join(5.0)
        # Deux URL perdues, ce n'est pas une raison pour les redemander a
        # chaque but.
        self.assertEqual(len(asked), 2)


if __name__ == "__main__":
    unittest.main()
