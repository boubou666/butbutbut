"""Compacte les motifs de club sans changer leur taille ni leur transparence.

Les sorties ImageGen reencodees en RGBA sont inutilement lourdes pour une
palette bleu nuit et or. Un PNG indexe de 256 couleurs garde le grain et les
bords antialiases, tout en divisant fortement la taille du paquet.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CLUBS = ROOT / "butbutbut" / "assets" / "clubs"


def optimize(path: Path) -> tuple[int, int]:
    before = path.stat().st_size
    temporary = path.with_suffix(".optimized.png")
    try:
        with Image.open(path) as source:
            rgba = source.convert("RGBA")
            if rgba.size != (512, 512):
                raise ValueError("{}: taille {}".format(path.name, rgba.size))
            indexed = rgba.quantize(
                colors=256,
                method=Image.Quantize.FASTOCTREE,
                dither=Image.Dither.NONE,
            )
            indexed.save(temporary, optimize=True, compress_level=9)

        with Image.open(temporary) as check:
            checked = check.convert("RGBA")
            if checked.size != (512, 512) or checked.getpixel((0, 0))[3] != 0:
                raise ValueError("{}: sortie invalide".format(path.name))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return before, path.stat().st_size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", type=Path, default=CLUBS)
    args = parser.parse_args()
    paths = sorted(args.directory.glob("*.png"))
    before = after = 0
    for path in paths:
        old, new = optimize(path)
        before += old
        after += new
    print("{} PNG : {:.1f} Mio -> {:.1f} Mio".format(
        len(paths), before / 1024 / 1024, after / 1024 / 1024))


if __name__ == "__main__":
    main()
