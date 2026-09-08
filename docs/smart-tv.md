# Butbutbut sur une smart TV

Note de faisabilite, ecrite le **8 septembre 2026**, contre la version 1.12.0.

La question est venue comme ca : "est-ce que ca s'installe sur une smart TV ?".
Reponse courte : **non, pas dans la TV** - mais la carte peut tres bien
apparaitre **sur** son ecran, et le depot a deja presque tout ce qu'il faut.

Ce fichier separe deux choses qui n'ont pas la meme valeur :

  - ce qui a ete **verifie dans le code** de ce depot, avec le fichier et la
    ligne. C'est solide ;
  - ce qui vient de la **documentation des plateformes** et n'a **pas** ete
    essaye sur du vrai materiel. C'est marque `[non teste]`, et ca le restera
    tant que personne n'aura branche une TV.

---

## 1. Ce que le programme reclame

Trois exigences, relevees dans le code :

  - **Python 3.8+ et la bibliotheque standard seule** (`pyproject.toml`,
    `dependencies = []`). C'est le point fort : rien a compiler, rien a
    telecharger. Partout ou il y a un Python, butbutbut tourne ;
  - **tkinter** pour les cartes (`butbutbut/overlay.py:192`), et derriere
    tkinter un vrai gestionnaire de fenetres : `-transparentcolor` sous
    Windows, fenetres de type `splash` sous X11, `topmost` partout. C'est
    l'en-tete d'`overlay.py` qui l'ecrit lui-meme ;
  - **un lecteur audio du systeme** (`butbutbut/sound.py:56`) : `ffplay`,
    `paplay`, `aplay`, `afplay`, ou `winsound` sous Windows.

La premiere exigence passe presque partout. Les deux autres, nulle part sur une
TV.

## 2. Le mur, avant meme le logiciel

Il y a une contrainte qui prime sur toute discussion de portage : **aucun
logiciel ne dessine par-dessus une entree HDMI ni par-dessus le tuner d'une
TV**. Ce sont des plans video geres par le materiel, en dessous de la couche ou
vivent les applications.

Autrement dit : meme en supposant le probleme resolu - un Python, un tkinter,
un compositeur, tout ce qu'on veut - la carte ne recouvrirait que l'interface
de la TV, jamais le match. Et le match, sur une TV, arrive presque toujours par
HDMI (box, console, decodeur) ou par le tuner.

C'est la vraie raison pour laquelle il ne faut pas chercher a installer
butbutbut dans la TV. Ce n'est pas une difficulte technique a contourner, c'est
un plafond.

La seule exception est une application qui passe par le systeme de
**notifications** de la TV : celui-la, la TV le compose elle-meme au-dessus de
tout. C'est exactement la porte qu'ouvre la section 4.

## 3. Plateforme par plateforme

| Plateforme | Faire tourner le code | Afficher la carte |
| --- | --- | --- |
| Tizen (Samsung) | non | non |
| webOS (LG) | non | oui, en notification |
| Roku | non | non |
| Android TV / Google TV / Fire TV | en partie | oui, en surimpression |

**Tizen et webOS.** Pas de shell, pas de Python, pas d'installation de paquet.
Les applications sont des applications web signees, poussees en mode
developpeur, et ce mode se re-arme regulierement (de l'ordre du mois). Faire
vivre un daemon la-dedans n'a pas de sens. `[non teste]`

**Roku.** BrightScript, canal prive, aucune execution arbitraire. Ferme. La
question ne se pose pas. `[non teste]`

**Android TV, Google TV, Fire TV.** C'est la seule famille ou le code pourrait
tourner : Termux sideloade donne un Python. Mais :

  - **pas de tkinter utilisable** : il faudrait un serveur X (termux-x11) et un
    gestionnaire de fenetres, absents d'une TV ;
  - il resterait donc `--no-overlay` (`butbutbut/cli.py:3060`), c'est-a-dire un
    daemon **sans carte**, ce qui vide le programme de son objet ;
  - et sur Android, une surimpression par-dessus les autres applications passe
    par une permission systeme reservee a une vraie application Android. Un
    processus Python dans Termux ne l'obtiendra pas.

Reste donc un Termux a entretenir sur un boitier qui se met a jour tout seul,
sans demarrage automatique, pour un programme qui n'afficherait rien. Ce n'est
pas une voie. `[non teste]`

## 4. La voie qui marche : le crochet

Le daemon reste sur une machine du reseau - PC, Raspberry Pi, NAS - la ou il
tourne deja bien, et c'est **`--on-goal` qui pousse le but vers la TV**.

C'est precisement ce pour quoi `butbutbut/hook.py` a ete ecrit, et son en-tete
le dit mieux que cette note : ne pas ecrire dans butbutbut les dix integrations
que dix personnes voudraient, mais leur donner de quoi les ecrire elles-memes.
Une TV est la onzieme.

Le contrat est deja la : les variables `BUT_*` (`butbutbut/hook.py:90`), la
phrase toute faite dans `BUT_TEXT`, le depart en fil separe, et `--test-hook`
pour regler tout ca sans attendre un vrai but.

### 4.1 Android TV et Fire TV, sans rien d'autre

**TvOverlay** (https://github.com/gugutab/TvOverlay) expose un simple
`POST /notify` avec un objet JSON. La documentation annonce `corner`
(`bottom_end`), `seconds`, et un champ `image` qui accepte une URL.
`[non teste]`

C'est la meilleure piste, et de loin : la correspondance avec la carte est
presque terme a terme.

    carte butbutbut          TvOverlay
    --position bottom-right  corner: "bottom_end"
    --duration               seconds
    --opacity                transparence reglable
    ecusson                  image: <url>

Une recette `urllib` d'une trentaine de lignes suffit, zero dependance, dans la
lignee exacte de `recipes/discord_webhook.py`. Elle n'existe pas encore : c'est
le travail a faire (section 6).

### 4.2 Avec Home Assistant

`recipes/home_assistant.py` marche deja et depose l'evenement
`butbutbut_goal`. Il ne reste qu'a ecrire l'automatisation, du cote de la
maison :

  - **Android TV / Fire TV** : l'integration `nfandroidtv`
    (https://www.home-assistant.io/integrations/nfandroidtv/). Sa documentation
    donne la position, la duree, la transparence, la couleur, et surtout dit
    que la notification s'affiche quelle que soit l'application en cours.
    `[non teste]`
  - **LG webOS** : l'integration `webostv`
    (https://www.home-assistant.io/integrations/webostv/). Un toast avec icone.
    Plus pauvre : de l'ordre de cinq secondes, pas de coin au choix, et la
    communaute rapporte que sur certains firmwares, passer une icone empeche la
    notification de s'afficher. `[non teste]`

### 4.3 Samsung

Rien de fiable trouve. Un boitier Android a quarante euros branche en HDMI
reste la reponse honnete - et ramene au cas 4.1, qui est le meilleur des deux.

## 5. Ce qui manque cote code

Une seule chose, et elle est petite.

Les integrations de TV veulent une **URL d'image** pour l'ecusson. Or le
contrat du crochet (`butbutbut/hook.py:90`) n'en porte pas, alors que
`butbutbut/crests.py:156` en fabrique deja de parfaites sur `espncdn.com`, avec
la taille voulue.

Deux variables a ajouter :

    BUT_HOME_CREST      l'ecusson de l'equipe qui recoit
    BUT_AWAY_CREST      celui de l'equipe qui se deplace

Et la carte du salon porte les memes couleurs que celle du bureau. **Ajouter ne
casse rien** : l'en-tete de `hook.py` promet que les noms existants ne
bougeront plus, pas qu'il n'y en aura jamais de nouveaux. Les tests epinglent
deja les cles d'`environment()` contre celles de `demo()`, il faudra donc
toucher les deux - c'est le garde-fou qui fait son travail.

## 6. Ce qu'il resterait a faire

  1. ajouter `BUT_HOME_CREST` et `BUT_AWAY_CREST` a `environment()` et a
     `demo()`, dans `butbutbut/hook.py` ;
  2. ecrire `recipes/tvoverlay.py`, sur le modele de
     `recipes/discord_webhook.py` : `urllib`, zero dependance, hote dans
     `BUTBUTBUT_TVOVERLAY_HOST` ;
  3. l'inscrire dans le tableau de `recipes/README.md` ;
  4. **essayer sur du vrai materiel**, et venir effacer les `[non teste]` de ce
     fichier.

Tant que le point 4 n'est pas fait, cette note reste un plan, pas un mode
d'emploi.
