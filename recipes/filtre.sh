#!/bin/sh
# Ne lancer une recette que pour les buts qui t'interessent.
#
#   butbutbut --on-goal '/chemin/vers/recipes/filtre.sh'
#
# A regler : les tests ci-dessous, et la derniere ligne - la recette a lancer
#     vraiment. Rien d'autre : ce fichier est un gabarit a copier et a tailler.
#
# Systemes : Linux, macOS, et tout ce qui a un /bin/sh (Git Bash et WSL sous
#     Windows). Shell POSIX, aucune commande externe.
#
# `--teams om` filtre deja par equipe, et mieux : il coupe aussi la carte et le
# son. Ce gabarit-ci sert a ce que `--teams` ne sait pas faire - ne reagir
# qu'aux penaltys, ignorer les buts encaisses, se taire avant la 80e minute -
# et a montrer comment on lit les variables du crochet dans un shell.
#
# Les guillemets autour de chaque "$BUT_..." ne sont pas decoratifs : sans eux,
# une equipe nommee "Paris FC" arriverait au test en deux mots.

set -eu

# 1. Un but retire par la VAR n'est pas un but. Enleve ces trois lignes pour
#    prevenir aussi des annulations - c'est ce que fait le crochet par defaut.
if [ "${BUT_TYPE:-}" != "goal" ]; then
    exit 0
fi

# 2. Seulement les buts de mes equipes. BUT_TEAM porte celle qui vient de
#    marquer, BUT_OPPONENT celle qui encaisse : intervertir les deux donne
#    l'alerte "on prend un but".
case "${BUT_TEAM:-}" in
    "Marseille"|"Paris FC") ;;
    *) exit 0 ;;
esac

# 3. Un penalty seulement, ou un csc seulement : decommente ce qu'il te faut.
# [ "${BUT_PENALTY:-0}" = "1" ] || exit 0
# [ "${BUT_OWN_GOAL:-0}" = "1" ] || exit 0

# 4. Rien avant la 80e minute. BUT_MINUTE vaut "83'" ou "90+3'" : on ne garde
#    que les chiffres de tete, et une minute vide (source muette) passe.
minute="${BUT_MINUTE:-}"
minute="${minute%\'}"
minute="${minute%%+*}"
case "$minute" in
    ''|*[!0-9]*) ;;
    *) [ "$minute" -ge 80 ] || exit 0 ;;
esac

# Le but a passe tous les tests : on passe la main, environnement compris.
exec python3 "$(dirname "$0")/discord_webhook.py"
