"""Les catalogues de traduction de la ligne de commande, un module par langue.

Deux mecanismes cohabitent dans le projet, et ce n'est pas un oubli :

  - les libelles des cartes passent par une cle qui porte le sens
    (`title_goal`, `goal_by`). Ils sont courts, reutilises a plusieurs endroits,
    et une cle nommee dit mieux qu'une chaine ce qu'on manipule. Ils vivent
    dans i18n.MESSAGES ;
  - la prose de la ligne de commande passe par **le francais lui-meme**, comme
    cle. Elle compte des centaines de phrases, chacune employee une seule fois :
    inventer un nom pour chacune serait du travail pour rien, et une cle mal
    recopiee produirait un texte muet. Avec le francais en cle, une traduction
    manquante rend le francais - degrade, jamais casse.

C'est ce second catalogue qui vit ici, un fichier par langue pour que cinq
personnes puissent traduire sans se marcher dessus.
"""

from __future__ import annotations

from . import de, en, es, it

# Le francais n'a pas de catalogue : il EST les cles.
CATALOGUES = {
    "en": en.MESSAGES,
    "es": es.MESSAGES,
    "it": it.MESSAGES,
    "de": de.MESSAGES,
}
