#!/usr/bin/env python3
"""Poster chaque but dans un salon Discord.

    butbutbut --on-goal 'python3 /chemin/vers/recipes/discord_webhook.py'

A regler : BUTBUTBUT_DISCORD_WEBHOOK, l'URL du webhook du salon (Parametres du
    salon > Integrations > Webhooks > Nouveau webhook > Copier l'URL). Elle
    vaut mot de passe : qui l'a peut ecrire dans le salon. Elle se pose dans
    l'environnement du daemon, jamais dans la ligne de commande - une ligne de
    commande se lit dans `ps`, et `butbutbut --status` la reafficherait.

Systemes : tous. Python 3.8+, bibliotheque standard seule, pas de curl.

Le but part en `embed` plutot qu'en simple phrase : un salon qui recoit
quarante buts un dimanche soir devient illisible en texte brut, alors qu'une
carte avec un titre et deux champs se survole. Le retrait par la VAR passe par
le meme chemin, en rouge - annoncer un but puis se taire quand il est refuse,
ce serait mentir au salon.
"""

import json
import os
import sys
import urllib.error
import urllib.request

# Le crochet tue la commande a 30 secondes : on rend la main bien avant, quitte
# a perdre un but plutot qu'a tenir un fil pour rien.
TIMEOUT = 10.0

COLOR_GOAL = 0x2ECC71
COLOR_CANCELLED = 0xE74C3C


def value(name, default=""):
    """Le detail du but, tel que le crochet l'a pose dans l'environnement."""
    return os.environ.get(name, "") or default


def scorer_line():
    """Le buteur et sa minute, ou rien : la source ne les publie pas toujours."""
    scorer = value("BUT_SCORER")
    minute = value("BUT_MINUTE")
    if not scorer and not minute:
        return ""
    line = scorer or "buteur inconnu"
    if value("BUT_PENALTY") == "1":
        line += " (penalty)"
    if value("BUT_OWN_GOAL") == "1":
        line += " (csc)"
    if minute:
        line += " - " + minute
    return line


def payload():
    """La carte envoyee a Discord."""
    cancelled = value("BUT_TYPE") == "cancelled"
    fields = [{"name": "Competition", "value": value("BUT_LEAGUE", "?"),
               "inline": True}]
    line = scorer_line()
    if line:
        fields.append({"name": "But de", "value": line, "inline": True})
    embed = {
        "title": "But refuse par la VAR" if cancelled else "BUT !",
        "description": "**{} {} {}**".format(
            value("BUT_HOME", "?"), value("BUT_SCORE", "?"),
            value("BUT_AWAY", "?")),
        "color": COLOR_CANCELLED if cancelled else COLOR_GOAL,
        "fields": fields,
    }
    # `username` est le seul reglage d'apparence qu'un webhook accepte sans
    # droits sur le serveur : de quoi ne pas se faire passer pour quelqu'un.
    return {"username": "butbutbut", "embeds": [embed]}


def post(url, body):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "User-Agent": "butbutbut-recipe/1.0"},
        method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status


def main():
    url = os.environ.get("BUTBUTBUT_DISCORD_WEBHOOK", "").strip()
    if not url:
        print("discord : BUTBUTBUT_DISCORD_WEBHOOK absent de l'environnement"
              " du daemon")
        return 1
    try:
        post(url, payload())
    except urllib.error.HTTPError as error:
        # 429 : Discord limite les webhooks. On n'insiste pas - reessayer
        # tiendrait un fil du crochet, et un but rate vaut mieux qu'un daemon
        # qui traine huit commandes derriere lui un soir de multiplex.
        print("discord : refuse ({} {})".format(error.code, error.reason))
        return 1
    except Exception as error:
        print("discord : injoignable ({})".format(error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
