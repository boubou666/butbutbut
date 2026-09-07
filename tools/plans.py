#!/usr/bin/env python3
"""Regenerer les plans de carte de `tests/plans/`.

    python tools/plans.py

Les plans figent la geometrie des cartes de `butbutbut/overlay.py` en ASCII :
un tableau de boites au pixel pres, et un dessin qui montre ou est le score, ou
est le nom, ou sont les ecussons et les cartons. `tests/test_plans.py` compare
ce que le code dessine aujourd'hui a ce qui est range dans le depot, et
`tests/blueprint.py` explique le mecanisme.

Un decalage de deux pixels fait donc echouer un test. C'est le but : quand le
decalage est voulu, on relance cette commande, et le diff de la PR montre le
deplacement en clair au lieu d'un nombre qui change. Sans cette commande d'un
seul mot, la premiere evolution legitime de mise en page rendrait ces tests
insupportables et quelqu'un les supprimerait.

Pourquoi un script de `tools/` et non une option du programme : ces plans ne
servent qu'au depot. Une option durable devrait entrer dans `config.py`, une
commande ponctuelle dans la liste `ACTIONS` de `tests/test_config.py`, et
`butbutbut --help` porterait a vie une ligne qui ne parle qu'aux tests. Le
canari est ici pour la meme raison.

Codes de sortie : 0 dans tous les cas ou l'ecriture a reussi ; la liste des
plans qui ont bouge est imprimee, c'est elle qu'on relit avant de commiter.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Les plans sont fabriques par le meme module que celui des tests, et non par
# une copie : deux fabriques finiraient par ne plus rendre le meme plan, et la
# reference cesserait de vouloir dire quelque chose.
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)

import blueprint                                       # noqa: E402


def main():
    changed = blueprint.write_all()
    print("{} plans ecrits dans {}".format(len(blueprint.SCENARIOS),
                                           blueprint.PLANS))
    if not changed:
        print("aucun changement")
        return 0
    for name in changed:
        print("  change : " + name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
