#!/usr/bin/env python3
"""Envoyer chaque but a Home Assistant, en evenement.

    butbutbut --on-goal 'python3 /chemin/vers/recipes/home_assistant.py'

A regler : BUTBUTBUT_HA_URL, l'adresse de ton instance (par exemple
    http://homeassistant.local:8123, sans barre finale), et BUTBUTBUT_HA_TOKEN,
    un jeton d'acces longue duree (ton profil, tout en bas de la page). Le
    jeton vaut mot de passe sur toute la maison : il se pose dans
    l'environnement du daemon, jamais dans la ligne de commande.

Systemes : tous. Python 3.8+, bibliotheque standard seule, pas de curl.

Un **evenement** plutot qu'un appel de service, parce que butbutbut n'a pas a
savoir si tu veux une lampe, une annonce vocale ou une scene : il depose le
but, et c'est ton automatisation qui decide. L'evenement s'appelle
`butbutbut_goal` et porte toutes les variables du crochet telles quelles.

Cote Home Assistant :

    automation:
      - alias: "But !"
        trigger:
          platform: event
          event_type: butbutbut_goal
        condition: "{{ trigger.event.data.BUT_TYPE == 'goal' }}"
        action:
          - service: light.turn_on
            target: {entity_id: light.salon}
            data: {flash: long}
          - service: notify.mobile_app_telephone
            data: {message: "{{ trigger.event.data.BUT_TEXT }}"}
"""

import json
import os
import sys
import urllib.error
import urllib.request

EVENT = "butbutbut_goal"

# Le crochet tue la commande a 30 secondes : une instance qui rame ne doit pas
# tenir un fil jusque-la.
TIMEOUT = 10.0


def goal_data():
    """Tout ce que le crochet a pose, et rien d'autre.

    On releve le prefixe au lieu de nommer les variables une a une : le jour ou
    butbutbut en publiera une de plus, l'automatisation la verra sans qu'on
    touche a cette recette.
    """
    return {key: text for key, text in os.environ.items()
            if key.startswith("BUT_")}


def post(url, token, body):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + token,
                 "User-Agent": "butbutbut-recipe/1.0"},
        method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status


def main():
    base = os.environ.get("BUTBUTBUT_HA_URL", "").strip().rstrip("/")
    token = os.environ.get("BUTBUTBUT_HA_TOKEN", "").strip()
    if not base or not token:
        print("home assistant : BUTBUTBUT_HA_URL ou BUTBUTBUT_HA_TOKEN absent"
              " de l'environnement du daemon")
        return 1
    data = goal_data()
    if not data:
        # Lance a la main, hors du crochet : mieux vaut le dire que d'envoyer
        # un evenement vide qui declencherait l'automatisation pour rien.
        print("home assistant : aucune variable BUT_, rien a envoyer")
        return 1
    url = "{}/api/events/{}".format(base, EVENT)
    try:
        post(url, token, data)
    except urllib.error.HTTPError as error:
        # 401 : jeton perime ou mal copie. C'est de loin la panne la plus
        # frequente, et le journal n'affiche que la premiere ligne.
        print("home assistant : refuse ({} {})".format(error.code, error.reason))
        return 1
    except Exception as error:
        print("home assistant : injoignable ({})".format(error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
