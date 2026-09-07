#!/usr/bin/env python3
"""Tenir un compteur de buts dans un fichier JSON.

    butbutbut --on-goal 'python3 /chemin/vers/recipes/compteur.py'

A regler : rien. Facultatif : BUTBUTBUT_COMPTEUR, le chemin du fichier
    (par defaut, compteur-buts.json dans ton dossier personnel).

Systemes : tous. Python 3.8+, bibliotheque standard seule.

`butbutbut --stats` relit deja le journal et en tire bien plus que ca. Ce
compteur-ci sert a autre chose : un fichier JSON stable, a soi, qu'un autre
programme lit sans rien savoir de butbutbut - une page web perso, un widget de
barre d'etat, un script de fin de saison.

Deux choses qu'un compteur naif rate et que celui-ci tient :

  - **la VAR est comptee.** On ajoute `BUT_DELTA` et non 1 : un but retire vaut
    -1, un doublon rattrape vaut +2, et le total reste vrai ;
  - **deux buts a la meme seconde ne s'ecrasent pas.** Un multiplex en sert, et
    butbutbut lance jusqu'a huit commandes en parallele : sans verrou, le
    dernier arrive ecraserait le compte du premier. Le fichier lui-meme est
    ecrit a cote puis renomme, pour qu'un lecteur ne tombe jamais sur un JSON a
    moitie ecrit.
"""

import json
import os
import sys
import time

LOCK_SUFFIX = ".lock"
LOCK_PATIENCE = 5.0         # au-dela, on renonce : le crochet tue a 30s
LOCK_STALE = 30.0           # un verrou plus vieux que ca a ete abandonne
LOCK_STEP = 0.05


def value(name, default=""):
    """Le detail du but, tel que le crochet l'a pose dans l'environnement."""
    return os.environ.get(name, "") or default


def counter_path():
    raw = os.environ.get("BUTBUTBUT_COMPTEUR", "").strip()
    if raw:
        return os.path.expanduser(raw)
    return os.path.join(os.path.expanduser("~"), "compteur-buts.json")


def delta():
    """+1, -1, +2... Ce que le but change au compte, pas le nombre de buts."""
    try:
        return int(value("BUT_DELTA", "1"))
    except ValueError:
        return 1


def load(path):
    """Le compteur d'avant, ou un compteur neuf.

    Un fichier illisible - efface a moitie, edite a la main - ne doit pas faire
    tomber la recette : on repart de zero plutot que de refuser le but.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def bump(data, key, name, step):
    """Une case du compteur, creee au besoin et jamais negative."""
    if not name:
        return
    table = data.setdefault(key, {})
    if not isinstance(table, dict):
        table = data[key] = {}
    table[name] = max(0, int(table.get(name, 0) or 0) + step)


def updated(data, step):
    """Le compteur d'apres. Fonction pure : c'est elle que les tests lisent."""
    data["total"] = max(0, int(data.get("total", 0) or 0) + step)
    bump(data, "par_competition", value("BUT_LEAGUE"), step)
    bump(data, "par_equipe", value("BUT_TEAM"), step)
    if step > 0:
        data["dernier"] = {
            "texte": value("BUT_TEXT"),
            "quand": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    return data


def save(path, data):
    """Ecrit a cote, puis renomme : un lecteur voit l'ancien ou le nouveau."""
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def take_lock(path, patience=LOCK_PATIENCE, sleep=time.sleep):
    """Attend son tour, puis rend True. False si le verrou ne se libere pas.

    O_EXCL tranche a la place d'un `exists()` qui aurait pu vieillir entre le
    test et l'ecriture.
    """
    deadline = time.time() + patience
    while True:
        try:
            age = time.time() - os.path.getmtime(path)
        except OSError:
            pass
        else:
            if age > LOCK_STALE:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except OSError:
            if time.time() >= deadline:
                return False
            sleep(LOCK_STEP)
            continue
        os.close(handle)
        return True


def main():
    path = counter_path()
    lock = path + LOCK_SUFFIX
    if not take_lock(lock):
        print("compteur : {} reste verrouille, ce but n'est pas compte"
              .format(os.path.basename(lock)))
        return 1
    try:
        save(path, updated(load(path), delta()))
    except OSError as error:
        print("compteur : ecriture impossible ({})".format(error))
        return 1
    finally:
        try:
            os.unlink(lock)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
