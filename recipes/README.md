# Des recettes pour `--on-goal`

`butbutbut --on-goal 'ma commande'` lance ce qu'on veut a chaque but, avec tout
le detail du but dans des variables `BUT_*`. C'est la porte de sortie du
programme : tout ce que butbutbut ne fera jamais lui-meme passe par la.

Une porte ne sert a rien si personne ne sait ce qu'il y a derriere. Ce dossier
contient donc des commandes **qui marchent**, a copier et a tailler : un
webhook Discord, une ampoule qui vire au vert, un compteur de saison.

Toutes tiennent la meme regle que butbutbut : **zero dependance**. Rien que la
bibliotheque standard de Python 3.8+, ou le shell de la machine. Pas de `curl`
suppose present, pas de `jq`, rien a installer.

Un mot sur la langue : les libelles ecrits dans les recettes ("BUT !",
"Competition") sont en francais, alors que `BUT_TEXT` arrive, lui, dans la
langue des cartes. Butbutbut parle cinq langues, ces fichiers non - ce sont des
brouillons a soi, et c'est une ligne a changer si le salon en parle une autre.

## Les recettes

| Recette | Ce qu'elle fait | A regler |
| --- | --- | --- |
| [`discord_webhook.py`](discord_webhook.py) | poste le but en carte dans un salon Discord | `BUTBUTBUT_DISCORD_WEBHOOK` |
| [`slack_webhook.py`](slack_webhook.py) | poste le but en une ligne dans un canal Slack | `BUTBUTBUT_SLACK_WEBHOOK` |
| [`home_assistant.py`](home_assistant.py) | envoie l'evenement `butbutbut_goal` a Home Assistant, a toi d'ecrire l'automatisation | `BUTBUTBUT_HA_URL`, `BUTBUTBUT_HA_TOKEN` |
| [`ampoule_wiz.py`](ampoule_wiz.py) | fait virer une ampoule WiZ au vert le temps du but, puis la remet comme elle etait | `BUTBUTBUT_WIZ_HOST` |
| [`compteur.py`](compteur.py) | tient un compteur de buts en JSON, par competition et par equipe | rien (`BUTBUTBUT_COMPTEUR`) |
| [`notification_bureau.py`](notification_bureau.py) | double la carte par une vraie notification du systeme, qui reste dans le centre de notifications | rien |
| [`obs_texte.py`](obs_texte.py) | ecrit le dernier but dans un fichier texte pour OBS ou une barre d'etat, et l'efface apres | rien (`BUTBUTBUT_OBS_FICHIER`) |
| [`filtre.sh`](filtre.sh) | gabarit : ne lance une autre recette que pour les buts choisis (penaltys, fin de match, une equipe) | rien |

Les reglages facultatifs de chaque recette sont expliques dans son en-tete :
`BUTBUTBUT_WIZ_COLOR`, `BUTBUTBUT_WIZ_SECONDS`, `BUTBUTBUT_COMPTEUR`,
`BUTBUTBUT_OBS_FICHIER`, `BUTBUTBUT_OBS_SECONDES`.

## En brancher une

```bash
butbutbut --on-goal 'python3 ~/butbutbut/recipes/discord_webhook.py'
```

```powershell
butbutbut --on-goal "py -3 C:\butbutbut\recipes\discord_webhook.py"
```

Le chemin est absolu : le daemon ne tourne pas forcement dans le dossier d'ou
tu l'as lance. La cle `on_goal` du fichier de configuration
(`butbutbut --paths`) fait la meme chose sans retaper l'option a chaque fois.

Pour essayer sans attendre un but :

```bash
butbutbut --test-hook
```

La commande part sur un but fabrique, tout de suite, et butbutbut affiche les
variables qu'elle a recues, sa sortie et son code de retour. C'est aussi la
facon de verifier qu'un secret est bien arrive jusqu'au daemon.

## Ou poser le secret

Une URL de webhook ou un jeton vaut mot de passe. Il ne va donc **ni dans le
depot, ni dans la ligne de commande** - une ligne de commande se lit dans `ps`,
dans le gestionnaire des taches, et `butbutbut --status` la reaffiche. Chaque
recette lit le sien dans une variable d'environnement, et le daemon transmet
son environnement entier a la commande.

Reste a poser la variable la ou le daemon la verra :

```bash
# Linux, macOS, dans un terminal : pour l'essai du jour
export BUTBUTBUT_DISCORD_WEBHOOK='https://discord.com/api/webhooks/...'
butbutbut --test-hook
```

```bash
# Linux, pour le service de demarrage : un fragment qui survit a --update
systemctl --user edit butbutbut
# [Service]
# Environment="BUTBUTBUT_DISCORD_WEBHOOK=https://discord.com/api/webhooks/..."
systemctl --user restart butbutbut
```

```bash
# macOS, pour le service de demarrage
launchctl setenv BUTBUTBUT_DISCORD_WEBHOOK 'https://discord.com/api/webhooks/...'
launchctl kickstart -k gui/$(id -u)/com.butbutbut.goals
```

```powershell
# Windows, une fois pour toutes : la variable est relue a la session suivante
setx BUTBUTBUT_DISCORD_WEBHOOK "https://discord.com/api/webhooks/..."
```

Deux pieges : sur macOS, `launchctl setenv` s'oublie a la deconnexion (une
ligne dans un `~/Library/LaunchAgents` a soi, ou dans le plist regenere par
`--update`, tient plus longtemps) ; sur Linux, un service systemd ne lit pas
`~/.profile`, d'ou le fragment ci-dessus.

## Ce qu'une recette doit tenir

Le crochet est deja ecrit pour ne jamais faire tomber le daemon : commande
introuvable, code de sortie non nul, script qui ne rend pas la main, tout finit
en une ligne de journal. Une recette n'a donc pas a se proteger de butbutbut,
mais elle a trois choses a respecter pour bien vivre a l'interieur :

- **se taire quand tout va bien.** Un crochet qui part a chaque but n'a pas a
  remplir le journal : une recette qui reussit n'ecrit rien et sort avec 0.
  Quand ca rate, elle imprime **une** ligne courte et sort avec 1 - le journal
  ne garde que la premiere ligne, et seulement 120 signes ;
- **rendre la main vite.** Butbutbut tue la commande au bout de 30 secondes et
  ne tient que 8 commandes a la fois : au-dela, les buts suivants ne lancent
  plus rien. Les recettes qui attendent (`ampoule_wiz.py`, `obs_texte.py`) sont
  bornees a 25 secondes ;
- **ne jamais recoller une valeur du reseau dans du code.** Les noms d'equipes
  et de buteurs viennent d'ailleurs. Ils se lisent dans l'environnement, ils se
  passent en argument, ils ne se collent pas dans une ligne de shell ni dans un
  script genere.

Les variables `BUT_*` disponibles sont listees dans le README principal,
section [Lancer une commande a chaque
but](../README.md#lancer-une-commande-a-chaque-but). Ce sont les seules : un
test du depot compare ce que ces recettes lisent a ce que `butbutbut/hook.py`
publie vraiment, pour qu'aucune recette ne pourrisse en inventant un nom.

## Ou les trouver une fois butbutbut installe

Ce dossier voyage avec le code source - le depot, et l'archive `.tar.gz` des
[releases](https://github.com/boubou666/butbutbut/releases). Il **n'est pas**
dans le paquet installe par `pipx install butbutbut` : butbutbut ne lance
jamais ces fichiers lui-meme, c'est toi qui les lances, et un paquet n'a pas a
embarquer du code que le programme n'execute pas. Installe par pipx, on copie
la recette voulue depuis GitHub, on la range ou on veut, et on donne son chemin
a `--on-goal`.
