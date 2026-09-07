#!/usr/bin/env python3
"""Poster chaque but dans un canal Slack.

    butbutbut --on-goal 'python3 /chemin/vers/recipes/slack_webhook.py'

A regler : BUTBUTBUT_SLACK_WEBHOOK, l'URL d'un webhook entrant
    (api.slack.com/apps > ton app > Incoming Webhooks > Add New Webhook).
    Elle vaut mot de passe : qui l'a peut ecrire dans le canal. Elle se pose
    dans l'environnement du daemon, jamais dans la ligne de commande.

Systemes : tous. Python 3.8+, bibliotheque standard seule, pas de curl.

Slack, contrairement a Discord, affiche tres bien une seule ligne dense : on
lui envoie donc la phrase toute faite du crochet, mise en gras, plutot qu'une
carte a champs. `BUT_TEXT` est deja redigee dans la langue des cartes, il n'y a
rien a rassembler ici.
"""

import json
import os
import sys
import urllib.error
import urllib.request

# Le crochet tue la commande a 30 secondes : on rend la main bien avant.
TIMEOUT = 10.0


def value(name, default=""):
    """Le detail du but, tel que le crochet l'a pose dans l'environnement."""
    return os.environ.get(name, "") or default


def escape(text):
    """Les trois signes que Slack lit comme du balisage.

    Un club nomme `Foot & Co` s'afficherait `Foot &amp; Co` sans ca.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def payload():
    """La ligne envoyee a Slack, et son emoji d'humeur."""
    cancelled = value("BUT_TYPE") == "cancelled"
    icon = ":no_entry_sign:" if cancelled else ":soccer:"
    text = value("BUT_TEXT") or "{} {} {} {}".format(
        value("BUT_LEAGUE", "?"), value("BUT_HOME", "?"),
        value("BUT_SCORE", "?"), value("BUT_AWAY", "?"))
    return {"text": "{} *{}*".format(icon, escape(text)),
            "username": "butbutbut"}


def post(url, body):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "User-Agent": "butbutbut-recipe/1.0"},
        method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace").strip()


def main():
    url = os.environ.get("BUTBUTBUT_SLACK_WEBHOOK", "").strip()
    if not url:
        print("slack : BUTBUTBUT_SLACK_WEBHOOK absent de l'environnement"
              " du daemon")
        return 1
    try:
        # Slack repond "ok" en texte brut, jamais en JSON : un corps different
        # veut dire que le message n'est pas parti, meme avec un code 200.
        answer = post(url, payload())
    except urllib.error.HTTPError as error:
        print("slack : refuse ({} {})".format(error.code, error.reason))
        return 1
    except Exception as error:
        print("slack : injoignable ({})".format(error))
        return 1
    if answer != "ok":
        print("slack : reponse inattendue ({})".format(answer[:60]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
