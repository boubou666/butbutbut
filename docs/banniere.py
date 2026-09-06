"""Dessine l'illustration du README : un mur d'ecrans, deux ahuris qui pointent.

Genere un SVG (vectoriel, donc net partout) et un petit wrapper HTML pour la
rasterisation par Edge en mode headless.
"""

import math
import pathlib
import sys

W, H = 1200, 700

# Palette : celle des cartes de butbutbut.
WALL_TOP = "#151a24"
WALL_BOT = "#0a0d13"
BEZEL = "#05070a"
BEZEL_EDGE = "#2c3547"
CARD_BG = "#0d1017"
CARD_EDGE = "#232936"
TEXT = "#f3f5f9"
MUTED = "#8b95a7"
PITCH = "#1d7a3d"
PITCH_ALT = "#22894a"
LINES = "#bfe6cd"

L1, PL, BL, LIGA, SERIEA = "#f2e34c", "#00ff87", "#ff5c5c", "#ff6b5e", "#5ab7ff"

out = []
add = out.append


def esc(content):
    return (str(content).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def text(x, y, content, fill=TEXT, size=14, weight="700", anchor="start",
         spacing=0, opacity=1):
    add('<text x="{:.1f}" y="{:.1f}" fill="{}" font-size="{:.1f}" '
        'font-weight="{}" font-family="Segoe UI, Inter, DejaVu Sans, sans-serif" '
        'text-anchor="{}" letter-spacing="{:.2f}" opacity="{}">{}</text>'.format(
            x, y, fill, size, weight, anchor, spacing, opacity, esc(content)))


def rect(x, y, w, h, fill, rx=0, stroke=None, sw=1, opacity=1):
    add('<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" rx="{:.1f}" '
        'fill="{}"{}{} opacity="{}"/>'.format(
            x, y, w, h, rx, fill,
            ' stroke="{}"'.format(stroke) if stroke else "",
            ' stroke-width="{:.1f}"'.format(sw) if stroke else "", opacity))


def line(x1, y1, x2, y2, stroke, sw=1, opacity=1, cap="round"):
    add('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" '
        'stroke-width="{:.1f}" stroke-linecap="{}" opacity="{}"/>'.format(
            x1, y1, x2, y2, stroke, sw, cap, opacity))


def circle(cx, cy, r, fill, opacity=1):
    add('<circle cx="{:.1f}" cy="{:.1f}" r="{:.1f}" fill="{}" '
        'opacity="{}"/>'.format(cx, cy, r, fill, opacity))


def ellipse(cx, cy, rx, ry, fill, opacity=1):
    add('<ellipse cx="{:.1f}" cy="{:.1f}" rx="{:.1f}" ry="{:.1f}" fill="{}" '
        'opacity="{}"/>'.format(cx, cy, rx, ry, fill, opacity))


# ----------------------------------------------------------------- ecrans ----

def mini_card(x, y, w, accent, league, home, away, score, side, scale=1.0):
    """La carte de butbutbut, en reduction, posee dans un coin de l'ecran."""
    h = 46 * scale
    rect(x + 2, y + 3, w, h, "#000000", rx=7 * scale, opacity=0.45)
    rect(x, y, w, h, CARD_BG, rx=7 * scale, stroke=CARD_EDGE, sw=1)
    rect(x + 3 * scale, y + 7 * scale, 3.2 * scale, h - 14 * scale, accent,
         rx=1.6 * scale)

    pad = x + 12 * scale
    text(pad, y + 15 * scale, "BUT !", accent, 8.6 * scale, spacing=0.4)
    if league:
        text(pad + 30 * scale, y + 15 * scale, league, MUTED, 6.4 * scale,
             spacing=0.5)

    # La ligne de score ne doit pas sortir de la carte : sur une petite dalle,
    # on abrege les noms plutot que de les laisser deborder.
    def wide(name):
        return 0.58 * 11 * scale * len(name)

    room = (w - 40 * scale - 0.62 * 13 * scale * len(score)) / 2.0
    if wide(home) > room:
        home = home[:3].upper()
    if wide(away) > room:
        away = away[:3].upper()

    mid = x + w / 2.0
    text(mid - 16 * scale, y + 34 * scale, home,
         accent if side == "home" else TEXT, 11 * scale, anchor="end")
    text(mid, y + 34.5 * scale, score, TEXT, 13 * scale, anchor="middle")
    text(mid + 16 * scale, y + 34 * scale, away,
         accent if side == "away" else TEXT, 11 * scale)


def pitch(x, y, w, h):
    """Une pelouse vue de dessus, avec ses bandes de tonte."""
    rect(x, y, w, h, PITCH)
    bands = 7
    for i in range(bands):
        if i % 2:
            rect(x + i * w / bands, y, w / bands, h, PITCH_ALT)

    add('<g stroke="{}" stroke-width="1.6" fill="none" opacity="0.7">'.format(LINES))
    add('<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}"/>'.format(
        x + w * 0.05, y + h * 0.08, w * 0.9, h * 0.84))
    add('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}"/>'.format(
        x + w / 2, y + h * 0.08, x + w / 2, y + h * 0.92))
    add('<circle cx="{:.1f}" cy="{:.1f}" r="{:.1f}"/>'.format(
        x + w / 2, y + h / 2, h * 0.16))
    for k in (0, 1):
        bx = x + w * 0.05 if k == 0 else x + w * 0.95 - w * 0.1
        add('<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}"/>'.format(
            bx, y + h * 0.32, w * 0.1, h * 0.36))
    add('</g>')

    for px, py, col in ((0.26, 0.4, "#f4f6fa"), (0.35, 0.63, "#f4f6fa"),
                        (0.46, 0.48, "#f4f6fa"), (0.56, 0.34, "#e4453f"),
                        (0.63, 0.6, "#e4453f"), (0.74, 0.45, "#e4453f")):
        circle(x + w * px, y + h * py, max(2.0, h * 0.022), col)


def screen(x, y, w, h, accent, league, home, away, score, side, tilt=0.0,
           card=True):
    """Un ecran : cadre, pelouse, bandeau de chaine, carte de but."""
    add('<g transform="rotate({:.2f} {:.1f} {:.1f})">'.format(
        tilt, x + w / 2, y + h / 2))
    add('<ellipse cx="{:.1f}" cy="{:.1f}" rx="{:.1f}" ry="{:.1f}" '
        'fill="url(#glow)" opacity="0.6"/>'.format(
            x + w / 2, y + h / 2, w * 0.95, h * 1.05))
    rect(x - 7, y - 7, w + 14, h + 14, BEZEL, rx=10, stroke=BEZEL_EDGE, sw=2)
    pitch(x, y, w, h)

    bug_w = w * 0.34
    rect(x + 10, y + 10, bug_w, 20, "#0b0e14", rx=5, opacity=0.9)
    rect(x + 10, y + 10, 4, 20, accent, rx=2)
    text(x + 21, y + 24.5, "{}  {}  {}".format(
        home[:3].upper(), score, away[:3].upper()), TEXT, 10.5, spacing=0.4)

    if card:
        scale = w / 330.0
        cw = w * 0.64
        mini_card(x + w - cw - 12, y + h - 46 * scale - 12, cw, accent, league,
                  home, away, score, side, scale=scale)

    add('<path d="M{:.1f} {:.1f} L{:.1f} {:.1f} L{:.1f} {:.1f} Z" '
        'fill="#ffffff" opacity="0.05"/>'.format(
            x, y, x + w * 0.45, y, x, y + h * 0.7))
    rect(x - 7, y - 7, w + 14, h + 14, "none", rx=10, stroke="#ffffff", sw=1,
         opacity=0.07)
    add('</g>')


def monitor(x, y, w, h, accent, league, home, away, score, side):
    """Un ecran d'ordinateur : meme dalle, plus un pied."""
    screen(x, y, w, h, accent, league, home, away, score, side)
    rect(x + w / 2 - 10, y + h + 7, 20, 28, "#1b2130", rx=3)
    rect(x + w / 2 - 46, y + h + 33, 92, 9, "#242d40", rx=4)


def laptop(x, y, w, h, accent, league, home, away, score, side):
    """Un portable : dalle plus petite, base en perspective."""
    screen(x, y, w, h, accent, league, home, away, score, side)
    add('<path d="M{:.1f} {:.1f} L{:.1f} {:.1f} L{:.1f} {:.1f} L{:.1f} {:.1f} Z" '
        'fill="#1b2130" stroke="{}" stroke-width="1.5"/>'.format(
            x - 9, y + h + 8, x + w + 9, y + h + 8,
            x + w + 34, y + h + 30, x - 34, y + h + 30, BEZEL_EDGE))
    line(x - 26, y + h + 25, x + w + 26, y + h + 25, "#2f3a4f", 2.5, cap="butt")


# --------------------------------------------------------------- personnes ---

def person(cx, head_y, r, skin, skin_dark, hair, shirt, shirt_dark, target,
           other_hand, mirrored=False, scarf=None, tilt=0.0):
    """Un spectateur ahuri : une main qui pointe l'ecran, l'autre en l'air."""
    side = -1 if mirrored else 1
    shoulder_y = head_y + r * 1.6
    shoulder_x = cx + side * r * 0.9

    # --- buste
    add('<path d="M{:.1f} {:.1f} C{:.1f} {:.1f} {:.1f} {:.1f} {:.1f} {:.1f} '
        'C{:.1f} {:.1f} {:.1f} {:.1f} {:.1f} {:.1f} Z" fill="{}"/>'.format(
            cx - r * 2.15, H + 10,
            cx - r * 2.0, shoulder_y + r * 0.3,
            cx - r * 1.25, shoulder_y - r * 0.3,
            cx, shoulder_y - r * 0.32,
            cx + r * 1.25, shoulder_y - r * 0.3,
            cx + r * 2.0, shoulder_y + r * 0.3,
            cx + r * 2.15, H + 10, shirt))
    add('<path d="M{:.1f} {:.1f} C{:.1f} {:.1f} {:.1f} {:.1f} {:.1f} {:.1f} '
        'L{:.1f} {:.1f} Z" fill="{}" opacity="0.5"/>'.format(
            cx, shoulder_y - r * 0.32,
            cx + r * 1.25, shoulder_y - r * 0.3,
            cx + r * 2.0, shoulder_y + r * 0.3,
            cx + r * 2.15, H + 10,
            cx, H + 10, shirt_dark))

    rect(cx - r * 0.3, head_y + r * 0.5, r * 0.6, r * 0.95, skin_dark, rx=r * 0.2)

    def arm(sx, sy, ax, ay, margin, elbow_out, hand, stretch=False):
        """Bras a deux segments tendu vers (ax, ay).

        `stretch` : le bras va toucher la cible, bien au-dela d'un bras humain.
        C'est volontaire, c'est le trait du dessin - mais reserve au bras qui
        designe l'ecran. L'autre reste de taille normale, sinon il finit par
        recouvrir les ecrans qu'on est justement venu montrer.
        """
        angle = math.atan2(ay - sy, ax - sx)
        reach = math.hypot(ax - sx, ay - sy) - margin
        span = max(r * 1.7, reach if stretch else min(reach, r * 2.5))
        ex = sx + math.cos(angle - elbow_out) * span * 0.48
        ey = sy + math.sin(angle - elbow_out) * span * 0.48
        hx = sx + math.cos(angle) * span
        hy = sy + math.sin(angle) * span
        add('<g stroke-linecap="round" fill="none">')
        add('<path d="M{:.1f} {:.1f} L{:.1f} {:.1f}" stroke="{}" '
            'stroke-width="{:.1f}"/>'.format(sx, sy, ex, ey, shirt, r * 0.5))
        add('<path d="M{:.1f} {:.1f} L{:.1f} {:.1f}" stroke="{}" '
            'stroke-width="{:.1f}"/>'.format(ex, ey, hx, hy, skin, r * 0.42))
        add('</g>')
        hand(hx, hy, angle)

    def pointing_hand(hx, hy, angle):
        circle(hx, hy, r * 0.28, skin)
        tipx = hx + math.cos(angle) * r * 0.72
        tipy = hy + math.sin(angle) * r * 0.72
        line(hx, hy, tipx, tipy, skin, r * 0.19)
        line(hx, hy, hx + math.cos(angle - 1.5) * r * 0.32,
             hy + math.sin(angle - 1.5) * r * 0.32, skin_dark, r * 0.15)
        # petites etincelles au bout du doigt : le contact avec l'ecran
        add('<g stroke="#ffffff" stroke-width="{:.1f}" stroke-linecap="round" '
            'opacity="0.75">'.format(r * 0.06))
        for k in (-0.9, -0.3, 0.3, 0.9):
            add('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}"/>'.format(
                tipx + math.cos(angle + k) * r * 0.16,
                tipy + math.sin(angle + k) * r * 0.16,
                tipx + math.cos(angle + k) * r * 0.34,
                tipy + math.sin(angle + k) * r * 0.34))
        add('</g>')

    def open_hand(hx, hy, angle):
        circle(hx, hy, r * 0.26, skin)
        for k in (-0.8, -0.4, 0.0, 0.4, 0.8):
            line(hx, hy, hx + math.cos(angle + k) * r * 0.44,
                 hy + math.sin(angle + k) * r * 0.44, skin, r * 0.13)

    arm(shoulder_x, shoulder_y, target[0], target[1], r * 0.9, side * 0.34,
        pointing_hand, stretch=True)
    arm(cx - side * r * 0.9, shoulder_y, other_hand[0], other_hand[1], r * 0.2,
        -side * 0.3, open_hand)

    if scarf:
        add('<path d="M{:.1f} {:.1f} Q{:.1f} {:.1f} {:.1f} {:.1f}" stroke="{}" '
            'stroke-width="{:.1f}" fill="none" stroke-linecap="round"/>'.format(
                cx - r * 0.9, head_y + r * 1.3, cx, head_y + r * 1.8,
                cx + r * 0.9, head_y + r * 1.3, scarf, r * 0.34))

    # --- tete, legerement inclinee : ca donne du mouvement
    add('<g transform="rotate({:.2f} {:.1f} {:.1f})">'.format(tilt, cx, head_y))
    for s in (-1, 1):
        circle(cx + s * r * 0.86, head_y + r * 0.12, r * 0.16, skin_dark)
    ellipse(cx, head_y, r * 0.85, r, skin)
    add('<path d="M{:.1f} {:.1f} A{:.1f} {:.1f} 0 0 1 {:.1f} {:.1f} '
        'Q{:.1f} {:.1f} {:.1f} {:.1f} Z" fill="{}"/>'.format(
            cx - r * 0.86, head_y - r * 0.1, r * 0.85, r,
            cx + r * 0.86, head_y - r * 0.1,
            cx + r * 0.25, head_y - r * 0.62,
            cx - r * 0.86, head_y - r * 0.1, hair))

    for s in (-1, 1):
        ex = cx + s * r * 0.35
        ey = head_y - r * 0.02
        ellipse(ex, ey, r * 0.22, r * 0.27, "#ffffff")
        look = 0.07 * side
        circle(ex + r * look, ey - r * 0.03, r * 0.115, "#171b24")
        circle(ex + r * look - r * 0.045, ey - r * 0.1, r * 0.035, "#ffffff", 0.9)
        add('<path d="M{:.1f} {:.1f} Q{:.1f} {:.1f} {:.1f} {:.1f}" stroke="{}" '
            'stroke-width="{:.1f}" fill="none" stroke-linecap="round"/>'.format(
                ex - r * 0.24, ey - r * 0.48, ex, ey - r * 0.68,
                ex + r * 0.24, ey - r * 0.48, hair, r * 0.095))

    ellipse(cx, head_y + r * 0.5, r * 0.23, r * 0.3, "#40202a")
    ellipse(cx, head_y + r * 0.66, r * 0.14, r * 0.11, "#c9575f", 0.8)
    add('</g>')

    # --- traits d'ahurissement
    add('<g stroke="{}" stroke-width="{:.1f}" stroke-linecap="round" '
        'opacity="0.6">'.format(TEXT, r * 0.075))
    for a in (-2.75, -2.35, -1.95, -1.55, -1.15, -0.75):
        add('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}"/>'.format(
            cx + math.cos(a) * r * 1.32, head_y + math.sin(a) * r * 1.36,
            cx + math.cos(a) * r * 1.62, head_y + math.sin(a) * r * 1.7))
    add('</g>')


def ball(cx, cy, r):
    circle(cx, cy, r, "#f4f6fa")
    pts = []
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        pts.append("{:.1f},{:.1f}".format(cx + math.cos(a) * r * 0.44,
                                          cy + math.sin(a) * r * 0.44))
    add('<polygon points="{}" fill="#171b24"/>'.format(" ".join(pts)))
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5 + math.pi / 5
        line(cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55,
             cx + math.cos(a) * r * 0.99, cy + math.sin(a) * r * 0.99,
             "#171b24", r * 0.11)


# ------------------------------------------------------------------ scene ----

add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}" width="{}" '
    'height="{}" role="img" aria-label="Deux personnes ahuries pointent du '
    'doigt cinq ecrans qui affichent tous un but">'.format(W, H, W, H))

add('''<defs>
  <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{}"/><stop offset="1" stop-color="{}"/>
  </linearGradient>
  <radialGradient id="glow">
    <stop offset="0" stop-color="#8fd7ff" stop-opacity="0.45"/>
    <stop offset="1" stop-color="#8fd7ff" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="vignette">
    <stop offset="0.55" stop-color="#000000" stop-opacity="0"/>
    <stop offset="1" stop-color="#000000" stop-opacity="0.5"/>
  </radialGradient>
</defs>'''.format(WALL_TOP, WALL_BOT))

rect(0, 0, W, H, "url(#wall)")
for i in range(1, 6):
    rect(i * 200, 0, 1.5, H, "#1d2432", opacity=0.5)
rect(0, 470, W, 8, "#1a212e", opacity=0.7)

# Les cinq ecrans.
screen(80, 52, 330, 190, L1, "LIGUE 1", "Marseille", "Paris FC", "2 - 1",
       "home", tilt=-0.6)
screen(452, 34, 306, 176, PL, "PREMIER LEAGUE", "Arsenal", "Chelsea", "2 - 1",
       "home", tilt=0.5)
screen(800, 50, 322, 185, BL, "BUNDESLIGA", "Frankfurt", "Augsburg", "1 - 4",
       "away", tilt=-0.4)
monitor(122, 272, 262, 150, LIGA, "LA LIGA", "Real Madrid", "Barcelona",
        "3 - 3", "home")
laptop(858, 288, 236, 136, SERIEA, "SERIE A", "Inter", "Juve", "1 - 0",
       "home")

# Les deux ahuris : la main s'arrete juste au bord de l'ecran montre.
person(330, 520, 52, "#e9b489", "#d69f74", "#2f2a2c", "#3a5686", "#2f4670",
       target=(556, 216), other_hand=(196, 402), scarf="#f2e34c", tilt=-5)
person(884, 512, 54, "#a9714b", "#94603d", "#241d1c", "#7a3550", "#642b42",
       target=(906, 246), other_hand=(1064, 408), mirrored=True, tilt=6)

text(468, 552, "!", L1, 70, anchor="middle", opacity=0.9)
text(762, 524, "!", BL, 56, anchor="middle", opacity=0.85)
ball(620, 656, 29)

rect(0, 0, W, H, "url(#vignette)")
add('</svg>')

svg = "\n".join(out)
target = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "tv.svg")
target.write_text(svg, encoding="utf-8")
target.with_suffix(".html").write_text(
    "<!doctype html><meta charset='utf-8'>"
    "<style>html,body{margin:0;padding:0;background:#0a0d13}</style>" + svg,
    encoding="utf-8")
print("ecrit {} ({} octets)".format(target, len(svg)))
