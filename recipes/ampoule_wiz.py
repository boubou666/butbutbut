#!/usr/bin/env python3
"""Faire virer une ampoule WiZ au vert le temps d'un but, puis la remettre.

    butbutbut --on-goal 'python3 /chemin/vers/recipes/ampoule_wiz.py'

A regler : BUTBUTBUT_WIZ_HOST, l'adresse IP de l'ampoule sur le reseau local
    (ta box la liste ; fixe-la en bail statique, sinon elle changera un jour).
    Rien d'autre : les ampoules WiZ - Philips, SLV et les autres du meme
    firmware - repondent en clair sur le port 38899 de ton reseau, sans compte,
    sans nuage et sans jeton. Il n'y a donc aucun secret dans cette recette.
    Facultatif : BUTBUTBUT_WIZ_COLOR ("R,V,B", vert par defaut),
    BUTBUTBUT_WIZ_SECONDS (duree de l'eclat, 8 par defaut, 25 au plus).

Systemes : tous. Python 3.8+, bibliotheque standard seule.

Ce que la recette fait, dans l'ordre : elle **demande son etat a l'ampoule**,
l'allume dans la couleur du but, attend, puis lui rend exactement l'etat lu.
Si l'ampoule ne repond pas a la premiere question, on n'y touche pas du tout :
on ne saurait pas ou la remettre, et laisser un salon en vert jusqu'au matin
est un plus gros defaut que de rater un but.

Deux choses a savoir avant de la brancher :

  - le fil du crochet reste occupe pendant toute la duree de l'eclat, et
    butbutbut n'en tient que huit a la fois. Huit secondes, c'est court devant
    un multiplex ;
  - un deuxieme but pendant l'eclat trouverait l'ampoule deja verte et
    croirait que c'est son etat normal. Un fichier verrou l'en empeche : le
    deuxieme but se contente de rallonger l'eclat, et c'est le premier qui
    remet l'ampoule comme il l'avait trouvee.
"""

import json
import os
import socket
import sys
import tempfile
import time

PORT = 38899
REPLY_TIMEOUT = 2.0         # l'ampoule est sur le reseau local, ou elle est absente
DEFAULT_SECONDS = 8.0
MAX_SECONDS = 25.0          # le crochet tue la commande a 30 secondes
STALE_LOCK = 60.0           # un verrou plus vieux que ca a ete abandonne

# Ce que `getPilot` rend et que `setPilot` reprend : tout le reste de la
# reponse (mac, rssi, module) ne se renvoie pas.
RESTORED = ("state", "dimming", "r", "g", "b", "c", "w", "temp", "sceneId",
            "speed")

CANCELLED_COLOR = (255, 40, 40)
DEFAULT_COLOR = (0, 255, 60)


def lock_path():
    """Un verrou par ampoule : deux ampoules chez soi ne s'attendent pas."""
    host = os.environ.get("BUTBUTBUT_WIZ_HOST", "").strip()
    name = "butbutbut-wiz-{}.lock".format(host.replace(":", "-") or "x")
    return os.path.join(tempfile.gettempdir(), name)


def color():
    """La couleur de l'eclat. Le rouge est reserve au but retire par la VAR."""
    if os.environ.get("BUT_TYPE", "") == "cancelled":
        return CANCELLED_COLOR
    raw = os.environ.get("BUTBUTBUT_WIZ_COLOR", "").strip()
    parts = [piece.strip() for piece in raw.split(",")] if raw else []
    if len(parts) != 3:
        return DEFAULT_COLOR
    try:
        channels = tuple(max(0, min(255, int(piece))) for piece in parts)
    except ValueError:
        return DEFAULT_COLOR
    return channels


def seconds():
    try:
        wanted = float(os.environ.get("BUTBUTBUT_WIZ_SECONDS", "") or
                       DEFAULT_SECONDS)
    except ValueError:
        wanted = DEFAULT_SECONDS
    return max(0.0, min(MAX_SECONDS, wanted))


def send(host, message, wait_for_reply=True):
    """Une trame WiZ en UDP. Rend la reponse, ou None si personne ne parle."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(REPLY_TIMEOUT)
    try:
        sock.sendto(json.dumps(message).encode("utf-8"), (host, PORT))
        if not wait_for_reply:
            return None
        data, _ = sock.recvfrom(4096)
    except (socket.timeout, OSError):
        return None
    finally:
        sock.close()
    try:
        return json.loads(data.decode("utf-8", "replace"))
    except ValueError:
        return None


def current_state(host):
    """L'etat de l'ampoule, reduit a ce qu'on saura lui rendre."""
    answer = send(host, {"method": "getPilot", "params": {}})
    result = (answer or {}).get("result")
    if not isinstance(result, dict):
        return None
    return {key: result[key] for key in RESTORED if key in result}


def take_lock(path):
    """Le verrou, ou False si un autre but l'a deja pris.

    O_EXCL fait tout le travail : le systeme de fichiers tranche, on n'a pas a
    croire un `exists()` qui aurait pu vieillir entre-temps.
    """
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        age = 0.0
    else:
        if age > STALE_LOCK:
            # Une recette tuee en plein eclat laisse son verrou derriere elle ;
            # sans ca, l'ampoule ne clignoterait plus jamais.
            try:
                os.unlink(path)
            except OSError:
                pass
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError:
        return False
    os.close(handle)
    return True


def main(sleep=time.sleep):
    # L'attente est injectable : sans ca, eprouver l'aller-retour complet
    # couterait huit secondes a chaque passage de la suite de tests.
    host = os.environ.get("BUTBUTBUT_WIZ_HOST", "").strip()
    if not host:
        print("wiz : BUTBUTBUT_WIZ_HOST absent de l'environnement du daemon")
        return 1
    red, green, blue = color()
    shine = {"method": "setPilot",
             "params": {"state": True, "r": red, "g": green, "b": blue,
                        "dimming": 100}}
    path = lock_path()
    if not take_lock(path):
        # Un but est deja en train d'eclairer la piece : on repeint, et on
        # laisse celui qui tient le verrou remettre l'ampoule d'aplomb.
        send(host, shine, wait_for_reply=False)
        return 0
    try:
        before = current_state(host)
        if before is None:
            print("wiz : l'ampoule {} ne repond pas, on n'y touche pas"
                  .format(host))
            return 1
        send(host, shine, wait_for_reply=False)
        sleep(seconds())
        send(host, {"method": "setPilot", "params": before},
             wait_for_reply=False)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
