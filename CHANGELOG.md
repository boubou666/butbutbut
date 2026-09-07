# Changelog

Toutes les evolutions notables de butbutbut sont consignees ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et le projet respecte le [versionnage semantique](https://semver.org/lang/fr/).

## [Non publie]

## [1.10.2] - 2026-09-07

### Corrige

- **L'attente de la voix ne depasse plus quinze secondes, meme d'une
  picoseconde.** `--speak` retient l'heure a laquelle une phrase doit partir
  (`monotonic() + MAX_DELAY`) et le fil de la voix en retranche l'heure qu'il
  est. En arithmetique flottante, cette soustraction ne rend pas toujours ce
  qu'on y a mis : pour un `monotonic()` de 262 141,39 - une machine allumee
  depuis trois jours - (t + 15,0) - t vaut 15,000000000029. Personne n'entend
  la difference, mais la promesse "un but annonce avec plus de quinze secondes
  de retard n'est plus une nouvelle" cessait d'etre vraie au sens strict, et le
  test qui la controlait echouait au hasard des machines - une fois sur quinze
  environ, tombee sur la CI de la 1.10.1. Le calcul sort du fil et de l'horloge
  (`speech.wait_before`), ou il se verifie sur les valeurs qui font mal plutot
  que sur celles du jour.
- 1310 -> **1313 tests**.

## [1.10.1] - 2026-09-07

### Corrige

- **Une carte ne sort plus une application de son plein ecran.** Sous Windows,
  la carte etait bien marquee "ne prend jamais le focus, pas de bouton dans la
  barre des taches" (`WS_EX_NOACTIVATE`, `WS_EX_TOOLWINDOW`), mais un cran trop
  tard : les styles etaient poses **apres** `deiconify()`, alors que Windows
  tranche l'activation a l'instant precis ou une fenetre apparait. Le temps de
  ces quelques millisecondes, la carte etait une fenetre ordinaire : elle
  reclamait le premier plan et recevait un bouton de barre des taches. Quand le
  bureau refusait le vol, il faisait clignoter ce bouton a la place - et un
  bouton qui clignote fait remonter la barre des taches par-dessus un jeu en
  plein ecran. Mesure sur Windows 10 : une carte poussee devant un jeu sans
  bordure lui a pris le premier plan. Les styles se posent maintenant pendant
  que la fenetre est encore retiree, donc avant qu'elle n'existe pour le
  bureau ; verifie ensuite qu'ils tiennent jusqu'a la fin de la carte (ni le
  fondu ni les deplacements ne les effacent), les appels d'apres-coup ont donc
  disparu plutot que d'etre dedoubles.
- 1306 -> **1310 tests** : les styles poses avant le premier affichage, une
  carte de but et une carte epinglee qui ne se montrent qu'ensuite, et un seul
  passage par carte - l'ordre est ce qui compte ici, et c'est exactement ce
  qu'aucun test ne regardait.

## [1.10.0] - 2026-09-07

### Ajoute

- **Les releves sont compresses : neuf fois moins d'octets sur le fil.** La
  source sert du gzip depuis toujours, mais uniquement a qui le demande, et
  personne ne le demandait : `urllib` n'annonce aucun encodage tout seul et ne
  decode rien tout seul non plus. Une ligne dans `espn.headers()`
  (`Accept-Encoding: gzip`) et une decompression dans `espn.download()`
  suffisent. Mesure contre la vraie source : le tableau de bord de la Ligue 1
  passe de 33 832 a 4 145 octets, et un tour complet de `--leagues all` de
  1 355 ko a 148 ko. Sur une soiree de deux heures a suivre les 36
  competitions, 400 Mo deviennent 44 Mo - la difference entre un programme
  qu'on laisse tourner sur un partage de connexion et un programme qu'on
  coupe. Zero dependance : `gzip` est dans la bibliotheque standard.
- **C'est la seule economie disponible, et c'etait la question a trancher.**
  L'autre piste - ne redemander que ce qui a change - est morte : la source
  n'envoie **ni `ETag` ni `Last-Modified`**, il n'y a donc rien a poser dans un
  `If-None-Match`, et les 36 requetes par tour de `--leagues all` restent 36
  requetes. Elles pesent simplement neuf fois moins.

### Details qui ont demande un arbitrage

- **On regarde les deux premiers octets, pas l'en-tete `Content-Encoding`.**
  Un proxy d'entreprise qui decompresse en chemin ne pense pas toujours a
  retirer l'en-tete, et l'inverse existe aussi ; les octets, eux, ne mentent
  pas. Consequence heureuse : une reponse en clair traverse `uncompress()`
  sans y toucher, donc les openers des tests, ceux du rejeu et le jour ou la
  source cesserait de compresser passent tous par le meme chemin, sans cas
  particulier.
- **Une decompression qui echoue n'est pas une panne de reseau**, et elle est
  donc levee hors du `try` qui les attrape : un flux tronque relu comme du
  JSON aurait donne "reponse illisible pour fra.1", ce qui est vrai et envoie
  chercher le defaut du mauvais cote. Le message dit maintenant "reponse
  compressee illisible", avec le code de la competition.
- **Le contrat de `espn.download()` ne change pas d'un caractere** : il rendait
  des octets de JSON en clair, il en rend toujours. `replay.Recorder`, qui se
  pose entre le programme et la source, enregistre donc exactement ce qu'il
  enregistrait, et un fichier d'enregistrement d'hier se rejoue aujourd'hui.
- **Le canari prend les en-tetes du daemon** (`espn.headers()`) au lieu d'en
  recopier une version a lui. C'est un defaut qu'on n'aurait vu que trop tard :
  le canari est cense voir ce que voit le programme, et une source qui
  compresserait mal n'aurait casse que le daemon pendant que le canari
  annoncait vert.
- 1298 -> **1306 tests** : la requete qui demande la compression, une reponse
  compressee relue en clair, une reponse en clair qui traverse intacte, un
  flux tronque qui nomme la competition, une reponse vide, et le contrat des
  openers qui ne bouge pas. Ce sont les seuls tests du depot qui passent par
  `urlopen` plutot que par un opener - c'est justement le morceau qu'un opener
  remplace, donc le seul qu'aucun autre test ne regardait.

### Teste

- **`tests/test_shootout.py` dependait de la langue de la machine.** Il epingle
  le francais par `i18n.use()`, ce qui suffit tant qu'on appelle les fonctions
  directement - mais deux de ses tests passent par la ligne de commande, et
  `main()` refixe la langue a chaque appel : l'epinglage etait perdu en
  chemin. Tant que « tirs au but » n'etait traduit nulle part, la sortie
  restait francaise partout et personne ne le voyait ; la traduction faite,
  les machines anglaises de la CI ont rendu « penalty shootout » et huit cases
  sur quinze ont vire au rouge. L'epinglage passe donc aussi par la variable
  d'environnement, comme en tete de `tests/test_cli.py`, et pour la meme
  raison - qui y etait deja ecrite.

### Ajoute

- **Les catalogues de langue sont complets.** Sept commandes livrees depuis la
  1.6.0 - `--next`, `--top-scorers`, `--stats`, `--table`, `--speak`,
  `--sound-for`, `--export` - portaient toutes la meme note de livraison : « la
  prose n'est pas encore dans les catalogues, elle sort en francais dans les
  cinq langues, degradee et jamais cassee ». Sept fois de suite, et personne
  n'a compte avant la huitieme : **131 phrases sur 272** n'etaient traduites
  nulle part. Il en reste 16, toutes nommees phrase par phrase dans les deux
  README et dans `tests/test_i18n.py`, avec la raison de l'y laisser. (Les deux
  chiffres se comptent sur la meme base, celle d'avant ce chantier : apres lui
  le programme donne 277 phrases a traduire, cinq metavariables ayant rejoint
  `tr()` au passage.)
- **Les en-tetes du classement de `--table` sortaient en francais**, et ce
  n'etait pas un detail : `G`, `N`, `P` sont les initiales de gagne, nul et
  perdu, et ne veulent rien dire pour qui lit la page en anglais. Le titre
  d'une colonne devient une cle de catalogue, comme les libelles de carte, et
  l'anglais lit `W D L`, l'allemand `S U N`. La seule contrainte est qu'une
  abreviation tienne dans une colonne de six signes : un test la verifie langue
  par langue, la ou seul l'oeil l'aurait vue.
- **La ligne `epinglee` de `--status`** rendait ses deux valeurs en francais
  (`etat inconnu`, `aucun match en cours`). Celle-la n'avait pas l'excuse des
  autres - elle ne sert qu'a `--status`, jamais au journal - et elle est
  traduite.
- **Trois metavariables de `--help` sortaient en francais** au milieu d'une
  page par ailleurs entierement traduite : `--pin EQUIPE`, `--next
  EQUIPE|JOURS` et `--spoiler-free LISTE` ne passaient pas par `tr()`, la ou
  leurs voisines y passaient. `--since DATE` et `--test N` non plus. Elles y
  passent, et l'allemand dit desormais `--pin TEAM`, `--since DATUM`.
- **Les titres de sport du catalogue** (`Hockey sur glace (a demander)`,
  `Rugby a XV (a demander)`) et `tous les sports (N competitions)` n'avaient
  d'entree dans aucun catalogue : `butbutbut --list` les affichait en francais
  quelle que soit la langue. Traduits.

### Corrige

- **L'aide allemande de `--retry-fullscreen` renvoyait a un mot absent de la
  page.** La phrase disait « maximal SECONDES lang » alors que la
  metavariable, elle, etait bien traduite en `SEKUNDEN` : le lecteur cherchait
  dans la page un mot qui n'y figurait pas. Meme defaut que celui deja corrige
  pour l'anglais.
- **Deux commentaires orphelins dans `de.py`** flottaient au-dessus d'une
  entree qui n'etait pas la leur - la note sur `ausgelost` expliquait un choix
  de traduction pour une phrase absente du fichier. Ils ont retrouve leur
  entree, qui existe desormais.

### Teste

- **Le garde-fou qui manquait.** `tests/test_i18n.py` compare maintenant, pour
  chacune des quatre langues, les phrases que le code passe a `tr()` a ce que
  le catalogue porte : les trous a valeur doivent etre les memes (nom,
  conversion et gabarit, dans l'ordre - compter les accolades laissait passer
  `{:.1f}` rendu `{:.0f}`), chaque traduction doit se formater pour de bon, les
  etiquettes de `--status` doivent garder leur deux-points au meme caractere,
  les blancs de bord doivent survivre, et aucune entree ne doit recopier sa
  cle. Une phrase nouvelle passee a `tr()` fait echouer la suite tant qu'elle
  n'est ni traduite ni inscrite, avec sa raison, dans la liste des phrases
  laissees en francais. C'est ce qui aurait arrete la dette a la premiere
  livraison plutot qu'a la huitieme.

### Interne

- **Python 3.14 entre dans la matrice de CI**, sur les trois systemes comme les
  autres versions recentes. Elle etait la seule a n'y pas figurer, et c'est
  celle sur laquelle le depot s'ecrit tous les jours : la CI validait donc
  scrupuleusement quatre versions que personne n'utilise pour developper, et
  taisait la seule dont une rupture se serait vue en premier. La suite passe
  sous 3.14 sans une correction : rien dans le depot ne comparait un message
  d'exception mot pour mot, aucun module de la bibliotheque standard qu'il
  importe n'a change de comportement sous lui, et `-W error::DeprecationWarning`
  ne fait rien lever. Le chantier etait bien aussi petit qu'il en avait l'air,
  et c'est ce qui le rendait facile a repousser.
- **Le paquet annonce enfin la 3.14** : le classifier PyPI manquait, lui aussi.
  `requires-python` (`>=3.8`), les badges, les prerequis et les deux
  installeurs, eux, disaient deja la meme chose - le plancher n'avait pas
  bouge, c'est le plafond qui avait glisse sans que rien ne le dise.
- **Un test confronte les seize endroits qui parlent de versions de Python.**
  C'est la vraie lecon du chantier : la matrice n'avait pas menti d'un coup,
  elle avait vieilli, et rien ne pouvait le signaler puisque chacun de ces
  fichiers est seul chez lui. Le test verifie que le plancher est le meme
  partout (`requires-python`, les deux badges, les deux listes de prerequis,
  la comparaison et le message de chaque installeur, et les en-tetes de
  `recipes/` - ceux-la decouverts et non listes, pour que la recette ecrite
  demain soit tenue elle aussi), que la CI l'essaye
  vraiment, et que la version la plus haute des classifiers est bien celle que
  la matrice va jusqu'a essayer. L'inverse n'est volontairement pas exige : le
  paquet annonce 3.10 et 3.11 sans les essayer, un pari assume - ce qui casse
  d'une version a l'autre casse rarement au milieu seul.
- 1222 -> **1227 tests**.

### Corrige

- **Un tir au but comptait pour un but sur les cartes.** La source publie
  chaque tir reussi dans le meme tableau que les buts, avec le meme drapeau
  `scoringPlay` et un `scoreValue` de 1 ; seul `shootout` l'en distingue, et ce
  drapeau etait lu par `espn.py` puis jamais regarde par personne. La finale de
  la FA Cup 2022, terminee 0-0, sortait donc une carte `FIN DU MATCH` annoncant
  `Chelsea 0 - 0 Liverpool` suivie de **onze buteurs**, et `--scores` alignait
  onze "Penalty de ..." sous un score nul. Les tirs sont maintenant mis de cote
  des la lecture (`Match.shootout`), et rien de ce qui habille les cartes ne
  les voit plus.
- **La detection, elle, n'avait pas de bug** - et c'est le resultat le plus
  utile de ce chantier, parce que personne ne le savait. Verifie contre la
  source sur quatre seances reelles (FA Cup 2022, Coupe de France 2025, Coupe du
  monde 2022, Ligue des champions 2025) : **le score publie ne bouge pas
  pendant une seance de tirs au but**, il reste celui de la fin du temps
  reglementaire et la seance est publiee a cote. Une finale ne declenchait donc
  pas dix cornes, et n'en declenche toujours pas. Le detail de ce qui a ete
  observe est dans le README, section "Les tirs au but".

### Ajoute

- **La carte de fin de match dit qui se qualifie.** `FIN DU MATCH / Angers
  1 - 1 Stade de Reims` est exact et rate l'essentiel. La troisieme ligne porte
  desormais `Tirs au but 3 - 5 : Stade de Reims`, le vainqueur mis en valeur
  comme un buteur l'est ailleurs. Le total vient de `shootoutScore` quand la
  source le donne, du decompte des tirs reussis sinon - il manque environ une
  fois sur dix - et le nom du vainqueur du drapeau `winner`, sans lequel la
  carte se contente de dire `Tirs au but` plutot que d'inventer un qualifie.
  La carte reste muette : un verdict s'ecrit, il ne se corne pas.
- `--scores` ajoute une ligne `tirs au but` sous un match de coupe decide ainsi,
  pour la meme raison : une soiree de Coupe de France s'affichait en matchs nuls.
- **Le hockey y est traite a part, parce que son reglement l'est.** Sa
  fusillade donne un but au vainqueur, dans le score du match (Vegas 4-3
  Chicago, `Final/SO`) : le score bouge donc pour de vrai, une fois, et la
  corne sonne au bon moment - rien a corriger la. La carte de fin de match
  ajoute seulement `Vainqueur aux tirs au but : ...`, parce qu'un 4-3 qui n'a
  pas eu lieu dans le temps reglementaire merite d'etre explique. Le marqueur
  vit dans `sports.py` (`Sport.shootout`) : le football le pose dans le nom
  d'etat, le hockey dans le detail, et le rugby n'en a aucun.
- **Le canari compte les tirs a part** et verifie qu'un match decide aux tirs
  au but porte bien son drapeau `winner`. Sans ce comptage il aurait rougi a
  chaque soiree de coupe, pour un comportement voulu.
- 1222 -> **1257 tests** : les charges utiles de la FA Cup 2022, de la Coupe de
  France 2025 et d'une fusillade de NHL sont figees dans `tests/test_shootout.py`
  telles que la source les sert, drapeaux compris. Huit tirs qui tombent un par
  un ne doivent produire aucune carte ; la neuvieme, celle de la fin du match,
  doit nommer le qualifie.

### Reste ouvert

- Tout ceci est etabli sur des seances **terminees**. Ce que la source publie
  pendant les quelques minutes que dure la seance n'a pas pu etre observe : il
  aurait fallu etre devant un match a elimination directe au bon moment. Le
  score final etant celui du temps reglementaire dans les quatre competitions
  relevees, il n'y a pas de raison de croire qu'il bouge entre-temps - mais
  c'est une deduction, pas une observation, et elle est ecrite dans le README
  pour que le jour ou quelqu'un verra une carte de trop, il sache ou regarder.

### Ajoute

- **Le football feminin entre au catalogue : 14 competitions.** La source les
  publiait depuis toujours, par le meme endpoint et avec les memes cles - un
  but de Liga F se lit exactement comme un but de LaLiga, buteur, minute, csc
  et penalty compris. Il n'y avait donc rien a ecrire du cote de la lecture :
  leur absence n'etait pas un arbitrage, c'etait un angle mort. Cinq
  championnats (Women's Super League, Liga F, Premiere Ligue, Eredivisie,
  NWSL), deux coupes d'Europe (Ligue des champions et Coupe Europa), trois
  competitions de selections (Coupe du monde, Ligue des nations, qualifications
  UEFA), trois coupes nationales (FA Cup, League Cup, Copa de la Reina) et la
  W Champions Cup de la Concacaf. Chacune a ete interrogee une par une contre
  la source, avec son nom, ses matchs et son classement.
- **La regle d'entree est le miroir** : entre au catalogue la competition
  feminine dont l'homologue masculin y est deja. Ce seul principe fait tout le
  tri, et il explique les absences sans avoir a les justifier une par une - il
  n'y a pas d'Euro feminin parce qu'il n'y a pas d'Euro tout court, et la W
  Gold Cup attendra la Gold Cup. Toutes ont ete verifiees et restent ouvertes
  par l'echappatoire (`--leagues uefa.weuro`, `fifa.w.olympics`, `aus.w.1`,
  `can.w.nsl`, `usa.w.usl.1`...).
- **Les alias : le mot masculin, plus un `f`.** `l1f`, `plf`, `ligaf`, `uclf`,
  `cdmf`, `facupf`. C'etait le seul vrai arbitrage du chantier : un mot qui
  change de sens selon la competition suivie ne se rattrape jamais, et
  personne ne relit son fichier de configuration six mois plus tard. Aucun mot
  deja pris ne bouge donc - `l1` reste la Ligue 1, `liga` LaLiga, `ucl` la C1
  masculine -, et le mot feminin se devine sans lire le README. Le `f` est le
  marqueur que tout le monde ecrit deja, des grilles de programmes
  (« France F ») au nom officiel de la premiere division espagnole, Liga F.
  Une competition qui porte un nom a elle repond en plus a ce nom-la : `wsl`,
  `nwsl`, `uwcl`, `reina`.
- **`--leagues all` ne les prend pas**, et c'est le second arbitrage. Meme
  raison que pour le hockey, mot pour mot : une mise a jour ne change pas ce
  qu'on suit, et quelqu'un qui tapait `all` hier ne doit pas recevoir demain
  des cartes de matchs qu'il n'a pas demandes. Elles se demandent d'un mot -
  `feminines`, `footf`, `women` - et `all-sports` les emporte comme il emporte
  tout le reste. `all` reste 36 endpoints ; `all-sports` en fait 60.
- L'etiquette de la carte suit la meme regle que les alias, et pour la meme
  raison : « Premiere Ligue » affiche tel quel se lit « Premier League » a deux
  heures du matin, la carte annonce donc **PREMIERE LIGUE F**. Cinq libelles
  qui se traduisent (Ligue des champions, Coupe Europa, Ligue des nations,
  Coupe du monde et ses qualifications) ont leurs cles dans les cinq langues.
- `--scores`, `--next` et `--table` marchent dessus sans une ligne de plus.
  Le classement a une notion de colonnes par sport : une competition feminine
  est du football, elle compte donc les matchs nuls comme la Ligue 1 - verifie
  contre la source plutot que suppose, en direct comme en test.
- 1222 -> **1251 tests** : la resolution de chaque alias, le fait que les mots
  masculins n'ont pas bouge, un controle deux a deux de **tout** ce qui
  designe une competition dans le catalogue entier (codes, noms, etiquettes,
  alias) plutot qu'une liste ecrite a la main, la convention `+ f` verifiee sur
  les paires que la source elle-meme relie, l'unicite des couleurs, ce que
  `all` emporte et n'emporte pas, une charge utile de WSL figee, et le
  classement de la WSL avec les colonnes du football.

### Note

- **L'Italie et l'Allemagne n'ont pas d'equivalent feminin chez la source.**
  `ita.w.1` et `ger.w.1` repondent 400, alors que la Serie A et la Bundesliga
  sont au catalogue depuis le premier jour. Ce n'est pas un oubli et on ne
  peut rien en faire : on ne suit pas ce qui n'est pas publie. Un test garde le
  catalogue de leur inscription a l'aveugle, mais **rien ne surveille la
  source** : la suite ne fait pas de reseau, et c'est `butbutbut --scores
  --leagues ita.w.1` qui repondra le jour venu.
- **Une equipe feminine porte le nom de son club** : la source ecrit « Paris
  Saint-Germain » dans `fra.w.1` comme dans `fra.1`. Le rapprochement des noms
  travaillant sur les libelles, `--teams psg` attrape les deux equipes du club
  des qu'on suit les deux competitions. C'est la bonne reponse plutot qu'un
  defaut a corriger, et rien dans le nom ne permettrait de trancher : ce qui
  separe les deux cartes, c'est la competition, et l'en-tete l'annonce.
- Un fichier son peut porter le nom d'une competition feminine (`wsl.mp3`,
  `--sound-for uclf=corne.wav`) : `leagues.designates` interroge desormais
  tout le football et non le seul catalogue masculin. Ce que `all` emporte est
  une question de surveillance, pas de nom de fichier.

### Ajoute

- **L'API d'ESPN est enfin documentee** : `docs/api-espn.md`, et sa traduction
  `docs/api-espn.en.md`. Le projet entier repose sur une source publique mais
  **non documentee** - personne n'en publie la forme, personne ne previendra le
  jour ou un champ changera de nom. Le code la lit defensivement, le canari la
  surveille tous les jours ; il manquait le troisieme etage, celui qui explique
  ce qu'on a compris de la source et pourquoi le code est ecrit comme il l'est.
  Chaque chiffre du document a ete releve contre la vraie source, en
  production, le 7 septembre 2026 : les cinq endpoints, leurs parametres, la
  forme exacte des reponses, les en-tetes, les codes d'erreur, les motifs
  d'URL des ecussons, les 243 competitions des trois sports, et douze pieges
  qui ont deja coute quelque chose. Ce qui n'a pas pu etre observe - les etats
  en cours de jeu, aucun match ne se jouant au moment du releve - est marque
  comme tel plutot que devine, et l'annexe D donne les commandes pour tout
  refaire.
- **Quatre questions ouvertes y trouvent leur reponse**, releve a l'appui :
  - **les requetes conditionnelles sont impossibles.** La source n'envoie ni
    `ETag` ni `Last-Modified` : il n'y a rien a poser dans un `If-None-Match`.
    En revanche elle honore `Accept-Encoding: gzip`, et le tableau de bord de
    la Ligue 1 tombe de 33 832 a 4 145 octets - huit fois moins pour trois
    lignes de stdlib. C'est la seule economie de trafic reellement disponible,
    et elle est partie dans la foulee (voir l'entree ci-dessus) ;
  - **les buteurs du hockey existent**, mais pas dans le tableau de bord :
    dans `/summary?event=<id>`, sous `plays[].participants[].type ==
    "scorer"`, passeurs compris. Le probleme n'est pas la donnee, c'est son
    poids - 450 ko par match - donc son moment : apres un but detecte, pour ce
    match-la seulement ;
  - **les noms traduits, c'est non.** `lang=es` et `lang=pt` traduisent
    vraiment les noms de competition et les libelles d'etat, mais `lang=fr` ne
    fait rien, et **les noms d'equipes ne bougent dans aucune langue** - ce qui
    otait l'interet principal, puisque c'est sur eux que travaille `teams.py` ;
  - **le `User-Agent` peut faire refuser la requete.** Un Akamai filtre devant
    l'API, et le refus est un 403 **en HTML**, pas un JSON d'erreur. Se faire
    passer pour un navigateur (`Mozilla/5.0`, une chaine Chrome complete) est
    justement ce qui fait refuser ; l'en-tete du projet, qui se nomme et donne
    l'URL du depot, passe. C'est une ligne a ne pas raccourcir en croyant
    faire propre.
- Deux precisions au passage, verifiees contre la source : le tableau de bord
  **tronque a 100 matchs** sans le dire (`?dates=2026` sur une saison de
  Premier League en rend 100 sur 380, et rien ne signale la coupure), et les
  ecussons de hockey **repondent bien sous le numero d'equipe** -
  `nhl/500/1.png` est Boston - la ou un commentaire du depot en doutait.

## [1.9.0] - 2026-09-07

### Corrige

- **La boucle a cartes rendait la main pendant que son fil ecrivait encore.**
  Le fil de surveillance est le seul a appeler `reporter.update()`, donc le
  seul a ecrire le fichier d'etat ; il etait lance et jamais attendu. Ce qui
  suit le retour de la boucle - l'effacement de cet etat, la fin du processus -
  passait donc par-dessus une ecriture en cours, et le fait qu'il s'agisse d'un
  fil demon n'arrangeait rien : un demon est tue net, au milieu de sa phrase.
  La boucle leve maintenant `stopping` et attend le fil (`WATCH_JOIN`, cinq
  secondes) avant de rendre la main. S'il tient un releve reseau qui ne repond
  pas, on ne retient pas l'arret pour lui - mais on le note au journal, parce
  qu'un etat a moitie ecrit se lira ailleurs.
- **C'est ce qui rendait `TestBothWatchLoopsFeedTheState` instable**, une fois
  sur deux et seulement sous Windows, sur des commits qui ne la touchaient pas.
  Deux visages du meme defaut : un fichier d'etat relu vide
  (`'NoneType' object is not subscriptable`) et un dossier temporaire qu'on ne
  pouvait plus effacer parce qu'il restait ouvert (`WinError 145`). Le nouveau
  test etire l'ecriture pour que la course soit certaine a chaque passage
  plutot qu'une fois sur deux : sans l'attente il echoue, avec elle il passe.
- **Un but dans les arrets de jeu ne comptait nulle part.** La source ecrit la
  minute `90'+9'` - apostrophe des les deux cotes du plus - la ou le lecteur du
  journal n'acceptait que `90+3'`, la forme qu'on ecrit a la main et que les
  captures de test portaient depuis toujours. Les deux se ressemblent assez
  pour que personne ne les confronte, et le resultat est le pire genre de
  panne : rien ne casse, `--stats` compte simplement ces buts parmi les minutes
  illisibles. Sur une vraie journee de Premier League, seize formes de temps
  additionnel sur soixante et un matchs partaient ainsi a la poubelle, et le
  compteur des arrets de jeu affichait zero depuis le premier jour. Les deux
  formes sont desormais lues.
- **Le canari surveille maintenant la FORME de l'horloge**, et pas seulement la
  presence de sa cle. C'est ce qui manquait pour attraper le defaut ci-dessus :
  il relit les minutes qu'il vient de telecharger avec le lecteur du journal
  (`journal.minute_of`, rendue publique pour lui), et une horloge que plus
  personne ne sait lire vaut une ligne rouge. Le football seul y est tenu :
  `12:34`, l'horloge d'un match de hockey, n'est pas une minute de jeu.
- 1029 -> **1033 tests** : les deux formes de temps additionnel, une apostrophe
  de trop qui doit rester illisible, l'horloge qui change de forme vue par le
  canari, et celle du hockey qui ne doit pas le faire crier au loup.
- **Un nom polonais ne termine plus la commande sur une trace d'appels.**
  Sous Windows, une sortie redirigee - `butbutbut --scores > matchs.txt`, un
  pipe, le journal d'un service - n'herite pas de l'UTF-8 de la console mais de
  la page de code ANSI, qui ne connait qu'une fraction des caracteres. Un
  buteur nomme Zielinski, avec le vrai `n` polonais, suffisait a faire tomber
  la commande sur une `UnicodeEncodeError` au lieu du score, alors que le meme
  nom s'affichait sans probleme dans le terminal. La sortie standard et la
  sortie d'erreur passent maintenant en UTF-8 des qu'elles ne sont pas un
  terminal (`cli.utf8_output`), comme tous les fichiers ecrits par le projet.
  Une console, elle, garde sa page de code - c'est elle qui sait ce qu'elle
  peut dessiner - et herite seulement du remplacement : un accent approximatif
  vaut mieux qu'une trace d'appels a la place des resultats.

### Ajoute

- **Un dossier `recipes/` pour `--on-goal`.** Le crochet donne tout le detail
  du but dans des variables `BUT_*` depuis la 1.7.0, et n'avait qu'un exemple :
  une ligne `notify-send`. Personne n'ecrit son webhook Discord a partir de ca.
  Huit recettes completes s'y trouvent desormais, a copier et a tailler :
  webhook Discord (`discord_webhook.py`), webhook Slack (`slack_webhook.py`),
  evenement Home Assistant a qui l'automatisation de la maison repond
  (`home_assistant.py`), ampoule WiZ qui vire au vert le temps du but
  (`ampoule_wiz.py`), compteur de buts en JSON (`compteur.py`), notification du
  systeme sur les trois plateformes (`notification_bureau.py`), bandeau texte
  pour OBS ou une barre d'etat (`obs_texte.py`), et un gabarit shell pour ne
  reagir qu'a certains buts (`filtre.sh`).
- **Zero dependance jusque dans les recettes** : bibliotheque standard de
  Python 3.8+, ou shell POSIX. Aucune ne suppose `curl` present, aucune ne
  demande `jq`. Les webhooks passent par `urllib`, l'ampoule par une trame UDP,
  la notification Windows par le PowerShell deja installe.
- **Un secret ne va ni dans le depot ni dans la ligne de commande** : chaque
  recette qui en demande un le lit dans une variable d'environnement
  (`BUTBUTBUT_DISCORD_WEBHOOK`, `BUTBUTBUT_HA_TOKEN`...). Une ligne de commande
  se lit dans `ps` et `butbutbut --status` la reaffiche. `recipes/README.md`
  dit ou poser la variable pour que le service de demarrage la voie, sur les
  trois systemes.
- Les deux recettes qui attendent (l'ampoule, le bandeau) sont bornees a 25
  secondes, sous le delai de 30 du crochet, et un test le verifie contre
  `hook.DEFAULT_TIMEOUT` : une recette qui deborderait serait tuee en plein
  travail, l'ampoule restant verte jusqu'au matin.
- 66 tests de plus, dont celui qui empechera ce dossier de pourrir : **chaque
  nom `BUT_` ecrit dans `recipes/` est compare a ce que `hook.py` publie
  vraiment**. Les autres verifient qu'une recette compile et se charge sans
  configuration, qu'elle est listee dans `recipes/README.md`, que chaque
  reglage `BUTBUTBUT_*` y est documente, qu'un echec tient en une ligne courte
  (le journal n'en garde qu'une, tronquee a 120 signes), qu'une reussite se
  tait, et que l'ampoule retrouve exactement l'etat qu'elle avait. Rien ne
  parle au reseau : les recettes sont chargees comme des modules et leurs
  fonctions pures sont eprouvees a part.
- `MANIFEST.in` emporte `recipes/` dans l'archive des sources, et le paquet
  installe ne l'emporte pas : butbutbut ne lance jamais ces fichiers lui-meme.
  Un test du depot tient les deux moities de cette phrase.

### Note

- `recipes/README.md` n'existe qu'en francais, comme les commentaires du
  depot ; les deux README principaux y renvoient depuis leur section
  `--on-goal`.
- `ampoule_wiz.py` est la seule recette qu'on ne peut pas eprouver de bout en
  bout sans le materiel : les tests couvrent le dialogue (ce qui part, ce qui
  revient, le verrou entre deux buts), pas une vraie ampoule au bout du fil.

### Ajoute

- **`butbutbut --speak` : le but dit a voix haute.** Tout le reste du programme
  suppose qu'on regarde l'ecran ; le son dit qu'il s'est passe quelque chose,
  la carte dit quoi - mais elle ne dit rien a qui travaille dans une autre
  fenetre, sur un autre bureau, ou ne voit pas l'ecran du tout. La phrase part
  apres la corne, ou a sa place avec `--no-sound`. C'est du confort, et
  accessoirement de l'accessibilite.
- La phrase n'est pas une nouvelle : c'est **celle du crochet**, la variable
  `BUT_TEXT` de `--on-goal`, mot pour mot (`hook.phrase`). Deux formulations
  auraient fini par ne plus dire la meme chose. Elle suit la **langue des
  cartes** et non celle du journal : on parle a qui regarde l'ecran, pas a qui
  relira `--today` demain matin.
- Trois systemes, zero dependance, rien a installer sous Windows ni macOS :
  PowerShell et `System.Speech` d'un cote, `say` de l'autre. Sous Linux,
  `spd-say` (speech-dispatcher), puis `espeak-ng`, puis `espeak` - le premier
  qui existe. `butbutbut --status` gagne une ligne `voix` qui dit lequel
  parlerait ici, avant meme qu'on ait pose l'option.
- Sous Windows, le texte passe par une **variable d'environnement** et n'est
  jamais recolle dans le script : meme regle qu'au crochet, le jour ou la
  source annoncera un club nomme `'; rm -rf ~`, ce sera un nom d'equipe et rien
  d'autre. Ailleurs il part en argument, jamais dans une ligne de shell.
- La voix choisit une **voix installee de la langue des cartes** quand la
  machine en a une, et garde la sienne sinon : une machine anglaise lit du
  francais avec un accent anglais plutot que de se taire.
- `butbutbut --test --speak` fait dire la carte de demonstration. Sans lui,
  regler l'option voudrait dire attendre un vrai but pour savoir si la machine
  parle - la meme demi-journee de mise au point que `--test-hook` avait
  supprimee pour le crochet.
- Nouvelle cle `speak` dans le fichier de configuration, comme toute option
  durable.

### Details qui ont demande un arbitrage

- **Deux buts coup sur coup font la queue**, ils ne se parlent pas dessus et
  aucun n'est jete tant que la file tient. Deux buts du meme releve, c'est le
  plus souvent deux matchs differents : en jeter un laisserait croire a un
  score qui n'existe plus. La file est bornee a quatre phrases, et au-dela
  c'est la plus **ancienne en attente** qui saute - un soir de folie, on veut
  savoir ou on en est, pas ecouter le quart d'heure precedent.
- **La voix attend la fin de la corne** (2,5 s) avant de parler : dire le but
  pendant le jingle rendrait les deux inaudibles. En mode muet elle part tout
  de suite, puisqu'elle est alors la seule alerte.
- **Le silence de la 1.8.0 vaut pour la voix.** `--quiet-hours` et
  `--quiet-while-presenting` la taisent comme ils taisent le haut-parleur :
  c'en est un. `--spoiler-free` aussi - ce qui n'est pas montre ne se dit pas
  non plus, sinon l'option ne protegerait plus rien. Le journal, lui, garde
  tout dans les deux cas. Le crochet `--on-goal` reste la seule alerte que la
  nuit laisse partir, pour la raison deja ecrite en 1.8.0.
- **`--speak` ne parle pas en rejeu.** Une soiree rejouee a `--speed 60` reduit
  une mi-temps a trente secondes : la voix parlerait encore du premier but que
  le match serait fini. Le crochet se tait deja en rejeu pour une raison
  voisine.
- **Aucune panne de voix ne remonte.** Programme absent, voix non installee,
  commande qui rend un code non nul, commande qui ne rend jamais la main (tuee
  au bout de 30 s) : une ligne au journal, **une seule** - un samedi entier
  ecrirait sinon autant de lignes que de buts pour une panne qui ne changera
  plus - et le match continue. La parole vit dans un fil a elle et part du fil
  de surveillance, jamais de celui qui dessine les cartes : ni la carte, ni le
  releve suivant ne l'attendent.

### Ajoute

- **`--sound-for om=~/sons/om.wav` : un son a soi pour un club ou une
  competition.** Un but de son equipe et un but dans un match qu'on suit de
  loin sonnaient pareil - or on ne se leve pas pour les deux. Les sons par
  contexte de la 1.7.0 repondaient deja a la question, mais seulement en
  renommant un fichier depose dans le dossier `sound`, donc en laissant
  butbutbut deviner ce que `om` veut dire. La paire se dit maintenant
  directement, et le fichier reste ou il est.
- Plusieurs paires d'un coup (`om=...,ucl=...`), les memes mots que `--teams`
  et `--leagues`, et `contre` pour un but encaisse par une equipe suivie.
- **L'equipe l'emporte sur sa competition** quand un but coche les deux : ce
  sont les **memes quatre etages** que les noms de fichiers - equipe, `contre`,
  competition, fond sonore - et non un second mecanisme pose a cote. A etage
  egal, ce qui est nomme couvre ce qui est devine dans un nom de fichier :
  celui qui ecrit la paire vient de dire lequel il voulait. `--sound-for` n'a
  en revanche pas d'etage general - un son nomme vise quelqu'un, il ne devient
  jamais le bruit de fond des autres buts.
- **Un chemin fautif est refuse au demarrage**, comme un nom d'equipe mal
  orthographie (`check_teams`) : le fichier doit exister, etre lisible et
  porter une extension jouable, et une equipe nommee a `--sound-for` est
  confrontee au meme catalogue que `--teams`. Toutes les paires fautives sont
  dites d'un coup.
- Un fichier qui **disparait en cours de route** ne fait rien tomber : le but
  retombe sur le son d'en dessous et le journal garde une ligne. Le disque
  n'est consulte que pour les paires que le but arme, donc jamais pour une
  equipe qui ne joue pas ce soir-la.
- Cle durable `sound_for` dans le fichier de configuration : toutes les paires
  dans une seule cle, separees par des virgules ou une par ligne. Une virgule
  ne coupe que devant une nouvelle paire, pour qu'un chemin qui en contient une
  reste ecrivable. `--status` dit ce que chaque paire arme, et ce qui cloche -
  c'est la seule commande que le refus au demarrage epargne, sans quoi la seule
  capable de repondre sortirait en erreur avant d'avoir rien affiche.
- `--volume` et `--no-sound` gardent leur portee : le mode muet coupe aussi les
  sons nommes.

### Ajoute

- **`butbutbut --export json|csv` : le journal en donnees.** `--on-goal`
  couvrait l'amont, au moment du but ; rien ne couvrait l'aval. Des mois de
  buts dormaient dans le journal, et tout ce qui les en sortait etait mis en
  page pour un oeil humain - colonnes alignees, barres, rangs partages. Un
  tableur, un carnet de notes, un graphe veulent des donnees : `--export` les
  ecrit sur la **sortie standard**, pour que ca se redirige et que ca se pipe.
- `--export` prend les memes fenetres et les memes filtres que `--stats` et
  `--top-scorers` : `--week`, `--month`, `--since`, `--teams`,
  `--exclude-teams`. Sans fenetre, tout le journal. Et c'est la meme et unique
  lecture (`journal.goals_between`) : un second analyseur finirait par ne plus
  compter comme le premier.
- **Seize champs, tous tires de ce que le journal porte vraiment** : le moment
  (`timestamp`, en ISO 8601), la soiree, la competition, les deux equipes, le
  score, l'equipe qui marque, le buteur, la minute de jeu en nombre et son
  temps additionnel, la minute telle qu'ecrite, et la phrase du journal. Rien
  n'est complete aupres de la source au moment de l'export, et aucun champ que
  le journal ne sait pas remplir n'a ete invente. Les noms de colonnes sont en
  anglais et **ne se traduisent pas** : un en-tete n'est pas une phrase, c'est
  un contrat, et une colonne qui change de nom avec la langue casse tous les
  scripts en voyage.
- **La VAR sort en deux temps.** Toutes les lignes du journal sortent, buts
  **et** annulations - taire une annulation rendrait un journal que personne
  n'a vecu - et chacune porte en plus `standing`, qui dit si le but tient
  encore. Garder les lignes ou il vaut `true` rend exactement ce que comptent
  `--stats` et `--top-scorers` : le rattachement positionnel de
  `journal.settle` est repris tel quel, pas recrit a cote.
- Le CSV a un en-tete, une seule forme de ligne et la **virgule** pour
  separateur (le point-virgule ne plairait qu'a la locale du lecteur, que le
  fichier ne peut pas connaitre). Il survit a une virgule, a un guillemet et a
  un accent dans un nom d'equipe : la protection des cases est celle du module
  `csv`, rien n'est echappe a la main. Le JSON, lui, est **un seul grand
  tableau** et non du JSON par lignes comme `--record` : l'export est une
  reponse finie, pas un flux, et un fichier coupe doit refuser de s'ouvrir
  plutot que de mentir de trois lignes en silence.
- **La sortie standard ne recoit que des donnees.** La fenetre, les totaux, les
  avertissements, le chemin du journal, la confirmation des noms passes a
  `--teams` et jusqu'a la ligne de `--regen-sound` partent tous sur la sortie
  d'erreur : `--export csv > buts.csv` doit rendre un fichier, pas un fichier
  plus un commentaire. `--regen-sound` merite sa mention parce qu'elle se
  declenche AVANT l'export et que sa ligne ne se serait meme pas collee au bon
  endroit : l'export ecrit sous la couche texte de `sys.stdout`, dont le tampon
  n'est vide qu'a la fin du programme, donc elle serait ressortie derriere les
  donnees.
- Un journal absent, vide, ou une fenetre sans le moindre but restent des
  **reponses valides** - un tableau JSON vide, un CSV reduit a son en-tete - et
  l'explication va a cote. Un consommateur n'a jamais a distinguer "rien" de
  "casse". Un tuyau referme en cours de route (`--export csv | head`) ne remonte
  pas non plus : ni comme trace, ni comme les deux lignes que Python imprime en
  s'arretant quand il ne peut plus vider une sortie standard qu'on lui a fermee
  au nez. L'export n'habille donc pas le flux d'octets d'un `TextIOWrapper` -
  celui-ci ferme ce qu'il habille en se detruisant, et son `detach()` commence
  par un `flush()` qui echoue justement sur un tuyau casse.
- La sortie est ecrite en **UTF-8 quoi qu'annonce la console** : une console
  Windows revendique volontiers du cp1252, et l'export mourrait sur le premier
  accent s'il la croyait.

## [1.8.0] - 2026-09-07

### Ajoute

- **`butbutbut --stats` : ce que le journal savait deja et ne disait pas.**
  `--today`, `--week`, `--month`, `--since` et `--top-scorers` relisent tous le
  journal, mais tous les cinq rendent une liste - un but, une ligne. `--stats`
  regarde les memes lignes en tas : un histogramme ASCII des buts par minute de
  match (la bosse de fin de match se voit a l'oeil nu), la repartition par
  competition, les soirees les plus prolifiques, le nombre de matchs, la
  moyenne de buts par match et la part des penaltys et des csc. Tout tient dans
  80 colonnes, sans couleur, et rien ne demande le reseau : c'etait deja dans
  le fichier.
- `--stats` prend les memes fenetres et les memes filtres que `--top-scorers` :
  `--week`, `--month`, `--since`, `--teams`, `--exclude-teams`. Sans fenetre,
  c'est tout le journal - une forme se voit sur la duree. Une seule lecture du
  journal (`journal.goals_between`), comme toutes les autres relectures.
- Le rattachement positionnel des buts annules par la VAR est **repris tel
  quel** (`journal.settle`, arrive en 1.7.0) : un but efface ne compte ni dans
  l'histogramme, ni dans sa competition, ni dans sa soiree, et les annulations
  dont le but est tombe avant l'ouverture de la fenetre sont annoncees a part
  plutot que deduites de quelqu'un au hasard.
- **Une soiree n'est plus un jour de calendrier.** Le journal change de jour a
  minuit, une soiree de football non : le but de 23h50 et celui de 00h12 sont
  de la meme soiree, et compter par date en faisait deux demi-soirees dont
  aucune n'a existe. Six heures du matin coupe la nuit (`journal.evening_of`).
- L'analyseur du journal retient desormais **l'en-tete** de chaque ligne
  (`Entry.key`) : c'est la seule chose qui dise la nature d'un but, et c'est de
  la que sort la part des penaltys, des csc, des essais et des drops. Il sait
  aussi lire une minute de jeu et son temps additionnel (`Entry.clock`) - un
  but a `90+3'` reste un but de la 90e.
- 44 tests de plus : les tranches de l'histogramme, un match a cheval sur
  minuit, une minute qu'aucune version ne sait lire, une fenetre vide, une
  fenetre ou la VAR a tout repris, une egalite dans le classement des soirees,
  et une garantie que rien ne deborde des 80 colonnes.

### Note

- `--stats` ne compte que ce que le journal permet honnetement de compter. Un
  0-0 n'y laisse aucune ligne : la moyenne annoncee est celle des matchs **ou
  un but est tombe**, plus haute qu'une moyenne de saison, et le pied de sortie
  le dit. La part des penaltys est un plancher, pas un total : quand la source
  publie l'action trop tard, le but est ecrit `BUT` et compte comme tel.
- La prose de `--stats` n'est pas encore dans les catalogues de traduction :
  elle sort en francais dans les cinq langues, comme `--next` et
  `--top-scorers`. Degradee, jamais cassee.

### Ajoute

- **`--quiet-hours 23:00-08:00` : ne pas deranger la nuit.** Pendant la plage,
  aucune carte et aucun son - pas meme la carte epinglee, qui s'efface et
  revient toute seule apres. Le but, lui, tombe dans le journal comme
  n'importe quel autre soir, et `butbutbut --today` le retrouve au reveil :
  on ne coupe que l'alerte, jamais la trace. L'heure est celle de la machine,
  la plage peut enjamber minuit (le cas courant), le debut est inclus et la
  fin exclue. `23:00-08:00`, `23h00-08h00`, `23h-8h` et `23-8` disent la meme
  chose ; une plage illisible est refusee en nommant le format attendu, et une
  plage qui commence ou elle finit aussi - elle veut dire « tout le temps » ou
  « jamais » selon la personne a qui on demande.
- **`--quiet-while-presenting` : se taire quand quelqu'un d'autre regarde
  l'ecran.** Une carte « BUT » au milieu d'une visio partagee est le bug qu'on
  ne decouvre qu'une fois, et devant temoins. La question est posee au systeme
  plutot que devinee : sous Windows, `SHQueryUserNotificationState` est l'API
  par laquelle Windows repond lui-meme a « est-ce le moment d'afficher une
  notification ? ». Sont detectes le mode presentation, l'ecran duplique vers
  un projecteur (Windows y allume l'assistant de concentration tout seul) et
  le « ne pas deranger » active a la main.
- **Ce qui n'est PAS detecte, et c'est ecrit dans le README** : un partage de
  fenetre ou d'ecran depuis Teams, Zoom ou Meet. Windows n'expose rien qui le
  signale, et la seule facon d'y arriver serait de guetter le nom de classe de
  la barre flottante de chaque application de visio - une heuristique qui
  tombe a la premiere mise a jour et se declenche de travers entre-temps.
  Hors de Windows, rien du tout : l'option y est refusee avec un
  avertissement, comme `--retry-fullscreen`.
- **`butbutbut --status` dit quand butbutbut se tait, et pourquoi** : une ligne
  `silence`, toujours affichee, qui annonce « en veille jusqu'a 08:00 » plutot
  que de laisser croire a une panne. Le journal note les changements d'etat, et
  eux seuls : un daemon qui repeterait « en veille » a chaque releve noierait
  ses buts.
- Les deux reglages ont leur cle de configuration (`quiet_hours`,
  `quiet_while_presenting`), et 43 tests hors reseau et hors ecran
  (`tests/test_silence.py`, plus les boucles de surveillance dans
  `tests/test_cli.py`) : plage normale, plage qui enjambe minuit, bornes
  exactes, formes acceptees, plage refusee, le but qui va bien au journal
  pendant le silence, et la degradation quand la detection ne repond pas.

### Modifie

- Les trois « est-ce le moment ? » - l'heure, le regard des autres, le plein
  ecran - passent desormais par un seul point de decision
  (`butbutbut/silence.py`) au lieu d'etre eparpillees. Elles ne rendent pas le
  meme verdict, et c'est voulu : le plein ecran laisse partir la carte quitte a
  la repasser plus tard, alors que la nuit et la presentation la retiennent.
- Le crochet `--on-goal` continue de partir pendant le silence, contrairement a
  `--spoiler-free` qui le coupe : le silence protege cet ecran et ce
  haut-parleur, pas une guirlande ni un telephone a l'autre bout de la maison.

### Ajoute

- **`--table` : le classement du championnat.** `--scores` disait ce qui se
  joue, `--next` ce qui arrive, `--top-scorers` ce qu'on a vu passer. Restait la
  seule question qu'un supporter pose sans regarder de match : ils sont ou, au
  classement ? C'etait le dernier trou visible dans la famille des commandes
  ponctuelles.
- `--table l1` cible une competition (les memes noms que `--leagues`),
  `--table om` surligne la ligne d'une equipe et affiche le classement de sa
  competition (les memes noms que `--teams`), et les deux se combinent :
  `--table l1,om`. Le mot est lu comme une competition si le catalogue le
  reconnait, comme une equipe sinon.
- Le classement a son propre endpoint chez ESPN
  (`apis/v2/sports/<sport>/<slug>/standings`, et non `apis/site/v2` comme le
  tableau de bord), lu par le meme client, avec les memes en-tetes, les memes
  delais et la meme politesse : `espn.standings()` et `espn.parse_standings()`.
- **Les trois sports sont couverts, chacun avec ses vraies colonnes**
  (`sports.py`) : `J G N P Diff Pts` au football, `J G P DP Diff Pts` au hockey
  - qui n'a pas de match nul mais compte les defaites en prolongation -, et
  `J G N P Bon Diff Pts` au rugby, points de bonus compris.
- 41 tests hors reseau (`tests/test_table.py`) : charges utiles completes,
  amputees et vides, la selection par competition et par equipe, le surlignage,
  la largeur des lignes et une competition injoignable parmi d'autres.

### Notes

- **Rien n'est fabrique.** Chaque colonne vient d'une statistique que la source
  publie ; une statistique absente donne un tiret, jamais un zero. Une colonne
  de matchs nuls au hockey inventerait une statistique qui n'existe pas.
- **Le rang n'est jamais calcule** : le depart entre deux equipes a egalite suit
  des regles propres a chaque competition, et les refaire finirait par mentir un
  jour. On affiche celui qu'ESPN publie (`rank` au football et au rugby,
  `playoffSeed` au hockey). Le tri, lui, est necessaire : un championnat arrive
  trie, mais un groupe de Coupe du monde arrive dans le desordre et la
  conference Ouest de la NHL commence a sa 4e tete de serie.
- Un classement absent (une coupe, une intersaison) rend une phrase et non un
  tableau vide, en nommant l'endroit exact ou on est alle voir. Les competitions
  sont interrogees les unes apres les autres, espacees comme pour `--next`, et
  **une competition injoignable n'emporte pas les autres**.
- `--exclude-teams` est sans effet sur `--table` : on ne retire pas une equipe
  d'un classement, les rangs qui resteraient ne voudraient plus rien dire.
- Le tableau tient dans 80 colonnes, ecussons exclus - on est en terminal.

## [1.7.0] - 2026-09-07

### Ajoute

- **Un canari qui previent quand la source change** (`python tools/canari.py`).
  Tout butbutbut repose sur une API publique mais non documentee : le jour ou
  ESPN renommera `penaltyKick` ou deplacera `athletesInvolved`, rien ne
  casserait - le daemon cesserait simplement d'annoncer les penaltys, en
  silence. Le canari interroge la source pour de vrai et verifie que chaque
  cle lue par `butbutbut/espn.py` est encore la et du bon type, puis repasse
  la reponse a `espn.parse()` pour s'assurer qu'elle produit toujours des
  matchs, des buts et un buteur. Une cle disparue vaut une sortie non nulle.
- Le canari distingue **une cle qui manque** d'**une cle qu'on n'a pas pu
  regarder** : un mardi de juillet sans un match au programme, il le dit et
  sort vert plutot que de crier au loup. Il redemande alors les quatre
  derniers mois d'un coup (`?dates=AAAAMMJJ-AAAAMMJJ`), de quoi retomber sur
  des buts a inspecter en toute saison.
- Un rendez-vous quotidien dans `.github/workflows/canari.yml`
  (`schedule` + `workflow_dispatch`), qui ouvre une issue avec le rapport
  quand le canari vire au rouge. **Jamais sur push ni pull request** : la CI
  ordinaire reste hors reseau et deterministe, sans quoi une panne d'ESPN
  repeindrait en rouge des changements qui n'y sont pour rien.
- 21 tests hors reseau pour le canari lui-meme (`tests/test_canari.py`) : une
  charge utile complete, les memes amputees d'une cle ou porteuses d'une
  valeur du mauvais type, et une sans le moindre match.

### Ajoute

- **`--next` : les prochains matchs.** `--scores` disait ce qui se joue
  aujourd'hui, `--next` repond a la question d'apres - c'est quand, le prochain
  match ? Groupe par jour puis par competition, a l'heure locale de la machine,
  avec le temps qui reste avant chaque coup d'envoi.
- `--next om` cible une equipe (les memes noms que `--teams` : `om`, `barca`,
  `manu`, les noms sans accents, un debut de mot), `--next 14` allonge la
  fenetre, et les deux se disent d'un coup : `--next om,psg,3`.
- Le tableau de bord d'ESPN sait servir un intervalle de dates
  (`?dates=20260908-20260915`) : `espn.fetch()` et `espn.scoreboard()`
  l'acceptent, et une semaine entiere tient donc dans **une** requete par
  competition au lieu de sept.

### Notes

- Fenetre par defaut : **sept jours**, la maille du calendrier. Un club joue
  une fois par semaine, deux quand il a une coupe : sept jours contiennent
  toujours le prochain match de qui que ce soit, sans deverser un mois
  d'affiches. Elle se compte en jours entiers et non en tranches de 24 h, sans
  quoi elle couperait une soiree en deux.
- Les competitions sont interrogees les unes apres les autres, espacees comme
  au demarrage du daemon : avec `--leagues all` ce sont 36 requetes. **Une
  competition injoignable n'emporte pas les autres** - le calendrier sort quand
  meme, avec ce qui manque dit en toutes lettres, et seule une source
  entierement muette rend un code d'erreur.
- Rien au programme donne une phrase qui redit ce qui a ete cherche, ou, et sur
  combien de temps, plutot qu'un tableau vide - c'est aussi la que se voit une
  faute de frappe dans le nom d'equipe.

### Ajoute

- **Le journal se relit plus loin que le jour meme** : `butbutbut --week` (les
  7 derniers jours), `--month` (les 30 derniers), et `--since 2026-09-01`
  depuis une date. Meme lecture, meme analyseur que `--today` : seule la
  fenetre de dates change. `--since` l'emporte sur `--week` et `--month`, et
  une date illisible est refusee avec le format attendu.
- **`butbutbut --top-scorers`, le classement des buteurs vus passer.** Sur tout
  le journal par defaut - un classement n'a d'interet qu'accumule - ou sur la
  fenetre de `--week`, `--month` et `--since`. Les rangs sont partages a
  egalite, et les vingt premiers suffisent a tenir sur un ecran.
- **Un but retire par la VAR ne reste a personne.** Le journal ne dit pas quel
  but une annulation efface : la ligne `BUT ANNULE` ne porte que le score revenu
  en arriere. Le rattachement est donc positionnel, comme le fait l'arbitre
  video - une annulation retire le dernier but encore debout de la meme equipe
  dans le meme match. Une annulation dont le but est tombe avant la fenetre
  n'est deduite de personne, et la sortie le dit.
- Le filtre par equipe (`--teams`, `--exclude-teams`) vaut maintenant pour tous
  les recapitulatifs, `--today` compris : `butbutbut --top-scorers --teams om`
  ne classe que ce qui s'est passe dans les matchs de l'OM.

### Change

- Au-dela d'un jour, le recapitulatif change de forme : le jour devient le seul
  titre, la competition passe en colonne et la minute du match remplace l'heure
  de detection. Grouper par jour **et** par competition posait un en-tete toutes
  les deux lignes. Et parce que trente jours de Ligue 1 font trois cents buts,
  la densite se decide sur ce qu'il y a a montrer plutot que sur la fenetre
  demandee : tant que la liste tient sur un ecran elle est donnee, au-dela
  chaque journee se resume a sa ligne. `--today` ne bouge pas d'un caractere.
- Un journal absent ou vide le dit maintenant en toutes lettres, au lieu de se
  confondre avec une journee sans but.

### Interne

- Une seule lecture du journal, `journal.goals_between()`, parametree par une
  fenetre de dates ; `journal.goals()` n'en est plus qu'un cas a un jour. Les
  jours restent des chaines AAAA-MM-JJ d'un bout a l'autre : c'est la forme du
  journal, le tri alphabetique d'une date ISO est son tri chronologique, et le
  filtre tombe donc avant l'analyseur, ligne par ligne.
- La prose des nouvelles commandes passe par `i18n.tr()` comme le reste de la
  ligne de commande, mais n'est pas encore dans les catalogues : elle sort donc
  en francais dans les cinq langues, degradee et jamais cassee.
- 503 -> **540 tests** : fenetres, bascule de mois, VAR (annulation rattachee au
  bon but, au bon buteur, et annulation orpheline), journal vide ou absent,
  lignes qu'aucune version ne sait lire, classement, largeur des lignes.

### Ajoute

- **Un crochet a chaque but** : `--on-goal "commande"` lance la commande de son
  choix quand un but tombe, avec tout le detail du but dans des variables
  d'environnement `BUT_*` (`BUT_TEXT` porte la phrase toute faite). Plutot que
  d'ecrire dans butbutbut les dix integrations que dix personnes voudraient -
  guirlande connectee, webhook Discord, domotique, compteur perso - il donne de
  quoi les ecrire soi-meme.
- `--test-hook` lance la commande sur un but fabrique et montre ce qu'elle
  recoit, ce qu'elle rend et son code de sortie. Regler un crochet en guettant
  un vrai but aurait ete une mise au point d'une demi-journee, avec un daemon
  qui se tait justement quand tout va bien.
- La cle `on_goal` du fichier de configuration, et une ligne `crochet` dans
  `--status`.

### Interne

- **Les donnees du but passent par l'environnement, jamais par la commande.**
  Un nom d'equipe n'est donc jamais recolle dans une ligne de shell : le jour
  ou la source annoncera un club nomme `; rm -rf ~`, il ne se passera rien.
  C'est aussi ce qui rend `shell=True` acceptable, et donc ce qui permet
  d'ecrire sa commande avec les tubes et les guillemets dont on a l'habitude.
- La commande part dans un fil a part et personne ne guette sa fin : un script
  lent ne retarde ni la carte, ni le releve suivant. Elle est tuee au bout de
  30 s, et huit au plus tournent en meme temps. Un echec est une ligne de
  journal ; une reussite ne dit rien, un crochet qui part a chaque but n'ayant
  pas a remplir le journal.
- Le crochet part **depuis le fil de surveillance**, a cote du journal, et non
  depuis la boucle d'affichage : il decrit un but, pas une carte, et doit donc
  partir aussi en `--no-overlay` et quand l'affichage echoue.
- Il part aussi sur un but **retire par la VAR**, `BUT_TYPE` valant alors
  `cancelled` : annoncer un but puis se taire quand il est refuse, ce serait
  mentir a ce qu'on alimente. Les temps forts, les expulsions et les annonces
  d'avant match, eux, ne declenchent rien.
- 502 -> **523 tests**.

### Ajoute

- **Des sons par contexte, decides par le nom du fichier.** Le dossier `sound`
  ne se contente plus d'un tirage au hasard : `om.mp3` ne sort que quand l'OM
  marque, `fra.1.mp3` (ou `l1.mp3`) que pour un but de Ligue 1, et surtout
  `contre.mp3` quand une equipe suivie avec `--teams` **encaisse**. Suivre un
  club, c'est enfin entendre la difference entre "on a marque" et "on a pris".
- Les noms acceptes sont ceux qu'on tape deja ailleurs : les surnoms et
  abreviations de `--teams` (`om`, `barca`, `manu`, `olm`...) et les codes ou
  alias de `--list` (`fra.1`, `l1`, `ligue1`, `ucl`). Le mot pour "encaisse"
  s'ecrit aussi `encaisse`, `against` ou `conceded`.
- Plusieurs fichiers pour la meme chose se distinguent par un suffixe apres
  `-`, `_`, un espace ou un point (`om-1.mp3`, `om-2.mp3`) : le tirage au
  hasard reste, mais entre eux seulement.
- `butbutbut --status` deroule le dossier et dit, fichier par fichier, ce que
  butbutbut a compris de son nom - y compris qu'un `contre.mp3` ne servira
  jamais sans `--teams`, ou qu'un son vise une competition non suivie.

### Change

- La priorite va du plus etroit au plus large - equipe, `contre`, competition,
  fond sonore - pour qu'une intention precise ne soit jamais recouverte par une
  plus large, et un etage vide passe la main au suivant. Un dossier sans nom
  reconnaissable se comporte donc exactement comme avant.
- Le son est desormais choisi **par but** et non par releve : deux buts du meme
  tour peuvent venir de deux equipes, donc de deux fichiers.

### Ajoute

- **Le mode sans spoiler** : `--spoiler-free EQUIPES` (et la cle
  `spoiler_free`). Pour les matchs de ces equipes, plus rien n'arrive a l'ecran
  ni au haut-parleur - ni but, ni but annule, ni temps fort, ni carton rouge, ni
  annonce d'avant match. Un « COUP D'ENVOI » dit que le direct est parti, un
  « FIN DU MATCH » que tout est joue : ca spoile autant qu'un but, donc tous les
  evenements se taisent. C'est le reglage du match regarde en differe, ou la
  carte annoncait le but avant qu'on ne le voie.
- Le journal, lui, garde tout : c'est le coeur du reglage. On ne coupe que
  l'ecran et le son, et `butbutbut --today` raconte le match une fois qu'on l'a
  vu. D'ou un evenement *marque* (`Event.spoiler_free`) et non filtre, la ou
  `--exclude-teams` fait disparaitre le match jusque dans le journal.
- Les noms se tapent avec la meme souplesse que `--teams` (`om`, `barca`,
  `manu`, les noms sans accents, les debuts de mots) et un mot qui ne designe
  aucune equipe est refuse au demarrage. La faute de frappe est plus sournoise
  ici qu'ailleurs : elle ne rend pas le daemon muet, elle le laisse spoiler le
  match qu'on voulait proteger.
- `--status` rappelle le reglage, et `--list-teams` marque d'un `?` les equipes
  concernees.

### Change

- `--scores` montre les matchs sans spoiler, mais avec leur score masque :
  `Marseille ? - ? Paris FC   sans spoiler`. Les faire disparaitre aurait ete
  pire que de tout montrer - on ne saurait plus si le match a lieu, ni a quelle
  heure, et c'est justement le jour ou on le regarde qu'on ouvre `--scores`.
  Rien de ce qui permettrait de reconstituer le score ne s'affiche : ni les
  buteurs, ni l'etat du match, pour qu'un match termine ressemble a un match en
  cours. `--status` masque de la meme facon le score des matchs en cours.
- L'ordre de decision des trois filtres par equipe est fixe et teste :
  `--exclude-teams` fait disparaitre le match, puis `--teams`, puis
  `--spoiler-free` qui le laisse vivre en silence. Suivre l'OM **et** le mettre
  en sans-spoiler est donc un usage normal : je veux le journal, pas l'alerte.

### Interne

- 701 -> **743 tests**.

### Ajoute

- **`--catch-up` : rattraper ce qui s'est passe pendant la veille.** Au reveil,
  au lieu de se taire, butbutbut affiche UNE carte de resume - les matchs qui
  ont bouge, leur score avant et apres, et les buteurs. La photo d'avant le
  trou n'est plus jetee : elle est confrontee a celle du reveil, et comme la
  source publie le tableau des actions avec des cles stables, on sait
  exactement quels buts on n'a jamais vus.
- La cle `catch_up` du fichier de configuration, et une ligne « rattrapage »
  dans `--status` qui rappelle lequel des deux comportements est arme.

### Change

- Rien par defaut : l'option est **eteinte**, le silence au reveil reste le
  comportement livre. C'est celui qui ne raconte jamais rien de faux, et
  changer d'avis pour tout le monde en montant de version serait une surprise.

### Interne

- Les arbitrages de la carte de resume, tous pris contre le reflexe de tout
  dire : **une seule** carte et non une par but (rejouer trois cartes avec des
  minutes perimees est exactement ce que le silence evitait) ; **aucun son**
  (on n'annonce pas au klaxon un but vieux d'une heure) ; **pas de carte du
  tout** quand personne n'a marque, le journal notant quand meme le rattrapage
  pour que « aucune carte » et « le rattrapage n'a pas tourne » restent
  distinguables ; le filtre `--teams` respecte ; et un match commence et fini
  pendant la veille laisse de cote, meme regle que pour la carte de fin de
  match - on n'en a rien suivi.
- La troncature de la carte n'est pas reecrite : la liste des matchs passe par
  `extra_parts()` et se fait couper en hauteur et en largeur par le mecanisme
  qui coupe deja la liste des buteurs de la fin de match.
- Le resume attend que **toutes** les competitions suivies aient ete
  rephotographiees. Sous Linux `time.monotonic()` gele pendant la veille : les
  echeances ne retombent pas au meme releve, et un resume a trous vaudrait
  moins que rien.
- Deux sommeils d'affilee avant que le resume ait pu sortir gardent la photo la
  plus ancienne, pas la plus recente : c'est elle qui dit tout ce qu'on a
  manque.

### Ajoute

- **La carte epinglee** : `butbutbut --pin om`. Tant qu'un match de l'equipe
  demandee est en cours, une carte **reste a l'ecran** et se met a jour a
  chaque releve (le score et la minute), au lieu de n'apparaitre qu'aux buts.
  butbutbut passe ainsi de l'alerte au tableau de bord : la carte vit sur le
  second ecran pendant qu'on travaille.
- La cle `pin` du fichier de configuration, et une ligne `epinglee` dans
  `butbutbut --status` qui dit ce que le daemon suit vraiment.
  `butbutbut --test --pin om` en montre une, sans quoi personne ne pourrait la
  regler.

### Details qui ont demande un arbitrage

- **Ou elle vit** : ancree au coin choisi, la pile des cartes fugaces demarrant
  apres elle. Cinq buts d'affilee ne peuvent donc pas la pousser dehors (le
  plafond de cinq ne compte que les fugaces), et aucune carte de but ne peut se
  poser dessus (toutes les places sont calculees ensemble). Elle perd le coin,
  qui est la meilleure place : c'est le prix d'etre la en permanence.
- **Son cycle de vie** : elle apparait au coup d'envoi, ou tout de suite si le
  match est deja en cours au demarrage - lancer le daemon a la mi-temps doit
  donner la carte. Elle disparait cinq minutes apres la fin du match : elle ne
  passe pas la nuit a l'ecran. Un match qui disparait du tableau de bord est
  traite comme un match fini, avec le meme delai : mieux vaut une carte qui
  s'attarde qu'une carte qui clignote.
- **Un mot pour plusieurs clubs** (`--pin real` en attrape trois) est accepte,
  le nommage etant celui de `--teams` ; mais il n'y a **jamais qu'une carte**.
  Elle suit le match commence en premier et n'en change pas tant qu'il dure -
  une carte qui sauterait d'un match a l'autre serait illisible - puis passe au
  suivant. `--pin om,psg`, en revanche, est refuse au demarrage : accepter la
  liste reviendrait a n'en suivre silencieusement qu'une des deux.
- **Elle ne fait aucun bruit**, et aucune equipe n'y passe en couleur de club :
  le son reste la marque du but, et la couleur veut dire « elle vient de
  marquer », jamais « elle mene ».

### Ajoute

- **Enregistrer un vrai match, et le rejouer.** `butbutbut --record
  match.jsonl --leagues l1` surveille normalement et met en plus chaque reponse
  brute de la source sur le disque ; `butbutbut --replay match.jsonl` la
  ressort, cartes et sons compris, sans reseau, en respectant les ecarts de
  temps entre releves. `--speed 60` fait passer une heure de match en une
  minute. De quoi mettre au point l'affichage sans attendre un samedi soir,
  reproduire un bug ("chez moi la carte deborde sur ce match-la") et fabriquer
  les captures du README - `--test` ne montrait que des cartes figees.
- Le format du fichier est du **JSON Lines** documente : un en-tete portant un
  numero de format, puis une ligne par releve avec son horodatage et le code de
  la competition. Une ligne illisible - la derniere d'une session tuee en plein
  match - est comptee et ignoree, le reste se rejoue. Un fichier ecrit par une
  version future dit clairement pourquoi il ne passe pas, au lieu de partir de
  travers.
- Un nom de fichier en `.gz` est compresse a l'ecriture et decompresse a la
  lecture, des deux cotes : du JSON d'API se comprime autour de vingt fois, et
  une soiree de Ligue 1 pese sinon des dizaines de mega-octets.

### Change

- Le rejeu ne court-circuite pas la surveillance : il remplace la **source**
  (l'`opener` injectable de `espn.fetch`) et laisse le watcher, la detection des
  buts, les cartes, le son et le journal faire exactement ce qu'ils font un
  samedi soir. Un rejeu qui prendrait un raccourci ne testerait que lui-meme.
  C'est ce que verifie le test central : un match joue en direct contre une
  source simulee, enregistre, puis rejoue, doit rendre la meme suite
  d'evenements, a la ligne de journal pres.
- Le journal, le fichier d'etat et le fichier pid d'un rejeu sont detournes d'un
  bloc vers un sous-dossier `replay/` du dossier de donnees. Un match d'il y a
  trois semaines rejoue ce matin n'a rien a faire dans `--today`, et un rejeu ne
  reclame pas le fichier pid de l'instance unique : on peut donc rejouer un
  match pendant que le vrai daemon tourne. Le detournement se prend a la racine,
  dans `paths()`, pour qu'aucun appelant ne puisse l'oublier.
- Une reponse identique a la precedente n'est plus reecrite : la ligne se resume
  a son horodatage et a un marqueur `repeat`. L'heure du releve est gardee -
  c'est elle qui porte la cadence, et la perdre changerait le rythme du rejeu.

### Corrige

- La derniere carte pouvait ne jamais s'afficher : un but depose dans la file
  juste apres que la boucle d'affichage l'a trouvee vide, et juste avant que le
  fil de surveillance s'arrete, partait avec la fenetre. Invisible au quotidien
  (le daemon s'arrete quand on le lui demande, pas au dernier but), mais un
  rejeu s'arrete de lui-meme sur le dernier releve : le "FIN DU MATCH" manquait
  une fois sur cinq.

### Interne

- `espn.download()` sort du corps de `espn.fetch()` : il n'y a plus qu'un seul
  endroit ou le reseau est touche, et c'est ce que l'enregistrement enrobe.
- Le `Watcher` accepte une horloge monotone injectable, a cote de l'horloge
  murale qu'il avait deja. C'est ce qui permet a un rejeu d'accelerer le temps
  sans qu'une seule ligne des deux boucles de surveillance ne change : elles
  continuent d'appeler `tick()` et `plan_wait()`, et l'attente qu'on leur passe
  avance l'horloge de l'enregistrement.
- 573 -> **627 tests**.

### Ajoute

- **Le hockey sur glace et le rugby a XV**, a la demande. Le tableau de bord
  d'ESPN a la meme forme pour tous les sports, seul le premier segment de
  l'URL change : `soccer/fra.1`, `hockey/nhl`, `rugby/180659`. Dix
  competitions de plus, verifiees une par une contre la source - la NHL, et
  neuf competitions de rugby (Tournoi des Six Nations, Top 14, Premiership,
  URC, Champions Cup, Rugby Championship, Super Rugby, Coupe du monde, matchs
  internationaux).
- Trois nouvelles facons de choisir : `--leagues hockey` ou `--leagues rugby`
  prend un sport entier, `--leagues foot` le football seul, et
  `--leagues all-sports` (ou `tous-sports`) prend vraiment tout.
- **Le vocabulaire des cartes suit le sport, dans les cinq langues.** Un essai
  s'annonce `ESSAI !` et vaut cinq points, une transformation `TRANSFORMATION`,
  une penalite `PENALITE`, un drop `DROP` ; le hockey garde `BUT !` - un but de
  hockey est un but - mais commence par une `MISE AU JEU` et souffle a la
  `FIN DU TIERS-TEMPS`, n'ayant pas de mi-temps mais deux pauses entre trois
  tiers-temps. Une carte de rugby dont l'action n'est pas encore publiee
  annonce `POINTS !` et dit de combien : `+5 points`.
- L'echappatoire vise maintenant un autre sport : `--leagues hockey:nhl`,
  `--leagues rugby:270565`, `--leagues hockey/mens-college-hockey`. Sans
  prefixe, c'est toujours du football.
- `butbutbut --list` affiche les autres sports dans leurs propres groupes, et
  `--status` ajoute une ligne `sports` quand on en suit plusieurs.
- Un sport ecarte expres explique pourquoi plutot que de repondre "inconnu" :
  `--leagues basketball:nba` renvoie qu'un panier toutes les trente secondes
  ferait de butbutbut une alarme et non une notification.

### Change

- **`--leagues all` reste tout le catalogue de football**, et n'interroge donc
  pas la NHL. Quelqu'un qui tapait `all` pour suivre les coupes nationales ne
  doit pas se retrouver, apres une simple mise a jour, avec des cartes de
  hockey a deux heures du matin : une mise a jour ne change pas ce qu'on suit.
  C'est `all-sports` qui prend tout.
- Une action porte desormais elle-meme sa cle de vocabulaire et sa valeur en
  points : le reste du programme n'a plus jamais a se demander de quel sport
  vient la carte qu'il ecrit.
- Quand plusieurs actions tombent entre deux releves, c'est la plus chere qui
  est annoncee et non la derniere : un essai transforme (sept points d'un coup)
  affiche `ESSAI !`, pas `TRANSFORMATION`.

### Corrige

- `--today` relit maintenant les buts contre son camp et les buts sur penalty,
  que leur en-tete de journal (`BUT CONTRE SON CAMP`, `BUT SUR PENALTY`)
  faisait passer a travers le filet depuis toujours.

### Interne

- **Le numero de version s'ecrit a trois endroits, et ils avaient diverge** :
  le programme annoncait 1.6.0, le paquet se serait construit en 1.5.0, et le
  PKGBUILD d'Arch aussi. Rien ne le signalait. Trois tests les confrontent
  desormais a `butbutbut/__init__.py`, qui fait foi, et un quatrieme refuse une
  version sans son entree de CHANGELOG.

## [1.6.0] - 2026-09-07

*Jamais taguee : ses changements sont partis avec la 1.7.0.*

### Ajoute

- **La ligne de commande parle elle aussi les cinq langues.** `--help`,
  `--status`, `--scores`, `--screens`, `--list` et `--today` suivent la langue
  retenue, cartes comprises. Les *valeurs* aussi, pas seulement les etiquettes
  devant : `last poll : il y a 12 s` ne se lit plus a moitie en francais.
- La description du parseur, les metavariables (`CHEMIN`, `LISTE`, `COIN`...)
  et les noms de langue affiches par `--status` sont traduits.

### Change

- **La langue est desormais reglee avant la construction du parseur.** Les
  textes d'aide d'argparse sont traduits au moment ou on les lui donne : les
  fixer apres l'analyse laissait `--help` en francais quoi qu'on demande, et
  seule la variable `BUTBUTBUT_LANG` fonctionnait. `--lang de --help` sort
  maintenant en allemand.
- L'aide de `--lang` ne promet plus que "cette aide reste en francais" :
  c'est precisement ce qui a change. Le journal, lui, reste francais.

### Corrige

- Les tests de `--status` epinglent la langue par l'environnement. Ils
  lancaient la ligne de commande sans `--lang` tout en affirmant des libelles
  francais : ils passaient sur une machine francaise et auraient echoue sur
  l'integration continue, dont les machines sont anglaises.

## [1.5.0] - 2026-09-07

### Ajoute

- **Les cartes parlent la langue de la machine** : francais, anglais, espagnol,
  italien, allemand - les cinq langues des cinq grands championnats - et le
  francais quand ce n'est aucune des cinq. Un but en Bundesliga s'affiche
  `TOR!` / `Tor von F. Rieder` sur une machine allemande.
- Le nom des competitions suit quand il se traduit : la Ligue des champions
  devient CHAMPIONS LEAGUE, la Coupe du monde WELTMEISTERSCHAFT. Celles dont
  le nom est un nom propre sont laissees tranquilles - Bundesliga, Serie A,
  Coupe de France s'ecrivent pareil partout.
- `--lang de`, la cle `lang` du fichier de configuration, ou la variable
  d'environnement `BUTBUTBUT_LANG`. `--status` affiche la langue retenue, et une
  langue inconnue est refusee au demarrage avec la liste de celles qu'on parle.
- **Le README existe en anglais** ([README.en.md](README.en.md)), avec un
  renvoi croise en tete des deux versions.

### Change

- **Le journal reste en francais, quelle que soit la langue des cartes.** Il
  voisine la ligne de commande, qui n'est pas traduite, et surtout `--today` le
  relit : un fichier ecrit avant un changement de langue resterait sinon a
  moitie illisible pour le relecteur. Une carte peut donc afficher `TOR!`
  pendant que le journal note `BUT`.
- Le compte a rebours d'avant match est fige en secondes et non en texte : fige
  en francais, il n'aurait pu etre rendu ni dans la langue de la carte ni dans
  celle du journal, qui n'en veulent pas la meme.
- Sous Windows, l'API systeme passe avant les variables `LANG` : un shell comme
  Git Bash pose `LANG=en_US` quoi qu'il arrive, ce qui rendait la detection
  aveugle a la langue reelle de la machine.

### Corrige

- Le paragraphe du journal apparaissait deux fois dans le README, chaque moitie
  venant d'une PR differente fusionnee le meme jour. Repere par la relecture
  pour la traduction anglaise.

### Interne

- La langue par defaut dependant de la machine, les trois modules de tests qui
  affirment une formulation epinglent la leur. Sans ca la suite passait sur une
  machine francaise et echouait sur la CI, dont les machines sont anglaises :
  elle tourne desormais a l'identique en fr, en, es, it et de.
- 459 -> **498 tests**.

## [1.4.0] - 2026-09-06

Premiere contribution exterieure au projet, par
[@Arzaroth](https://github.com/Arzaroth) : la mise a jour sans reinstaller.

### Ajoute

- **Mise a jour automatique**, sur le modele de
  [doot](https://github.com/boubou666/doot) : `butbutbut --update` recupere la
  derniere version, rejoue l'installeur et relance le daemon ;
  `butbutbut --check-update` se contente de dire si une version plus recente
  existe.
- L'installeur depose une fiche `install.json` dans le dossier de donnees :
  d'ou vient le code, quel commit, et **avec quelles options**. `--update` la
  relit, donc une mise a jour rejoue les memes competitions, le meme coin et la
  meme cadence - qui suivait `l1,pl,ucl` ne se retrouve pas ramene aux cinq
  grands championnats, ni le daemon relance sans sa selection.
- C'est la **derniere release** qui est installee, depliee depuis son archive.
  Le depot clone n'est pas touche dans ce mode : l'amener sur l'etiquette
  demanderait de le laisser en HEAD detachee, et il appartient a son
  proprietaire. `--dev` vise la pointe de la branche principale, et la le clone
  sert s'il est encore la (`git pull --ff-only`), l'archive de `main` prenant
  le relais sinon. Cette seconde voie ne demande ni git ni le clone d'origine :
  une installation dont le dossier a ete efface se met a jour quand meme.
- `--check-update` et `--update` visent enfin la meme chose : des versions par
  defaut, des commits avec `--dev`. La premiere mouture annoncait une release
  et installait la pointe de `main`.
- `--update` refuse d'ecraser une installation qui ne vient pas des scripts et
  renvoie vers l'outil qui la gere : `pipx upgrade butbutbut`,
  `pip install --upgrade butbutbut`, ou le gestionnaire de paquets de la
  distribution.

### Corrige

- **La publication PyPI ne pouvait pas se declencher.** Elle vivait dans un
  workflow separe ecoutant `release: published`, or Actions refuse qu'un
  evenement produit par le `GITHUB_TOKEN` declenche un autre workflow : une
  release creee par `github-actions[bot]` ne reveille personne. Constate en
  poussant `v1.3.0`, ou le workflow `pypi` n'a meme pas eu de run. La
  publication est desormais le second job de `release.yml`, declenche par le
  push du tag - un evenement humain, qui declenche bien. Les deux jobs vivent
  dans `pypi.yml`, et `release.yml` disparait : un publisher de confiance PyPI
  autorise UN nom de fichier de workflow, et c'est celui-la qui est declare
  cote pypi.org. Le declenchement manuel du meme workflow sert de rattrapage.
  Le README ne promet plus un automatisme qui n'existait pas.
- L'installeur arrete le daemon avant de remplacer le code. Il continuait
  jusque-la sur des fichiers effaces, et ne reprenait le nouveau code qu'a la
  session suivante.
- Une mise a jour interrompue rend le daemon. Le redemarrage vit desormais
  dans un `finally` : un telechargement coupe ou un installeur en echec
  laissait sinon la surveillance eteinte jusqu'a la session suivante, sans que
  personne s'en apercoive.
- `--update` explique ce qui a echoue au lieu d'imprimer une pile d'appels.
- **L'installeur n'ecrase plus le fichier de configuration.** Il posait ses
  valeurs par defaut en arguments du service de demarrage (`--position`,
  `--interval`), et la ligne de commande l'emportant toujours sur le fichier,
  ces deux reglages de `butbutbut.conf` etaient ignores en silence. Il ne pose
  desormais que les options qu'on lui passe, `--quiet` excepte. Le bug touchait
  deja `./install.sh` rejoue a la main, avant meme l'arrivee de `--update`.

## [1.3.0] - 2026-09-06

Sept chantiers menes en parallele, chacun dans sa branche, fusionnes ensemble.

### Ajoute

- **Ecussons et couleurs des clubs sur la carte** : l'equipe qui marque prend
  la couleur de son club, le filet vertical garde celle de la competition. La
  couleur n'est retenue que si elle se lit sur le fond sombre (luminance WCAG,
  seuil 3.5) ; sinon on descend sur la couleur secondaire, puis sur celle du
  championnat - le noir sur noir du Paris FC finit ainsi en jaune Ligue 1. Les
  ecussons viennent d'un cache disque et ne sont **jamais** attendus : une
  carte sans ecusson s'affiche tout de suite et le telechargement se fait en
  fond pour la prochaine fois. `--no-logos`.
- **Fichier de configuration** (`butbutbut --write-config`) : plus besoin de
  relancer l'installeur pour changer de championnat. La ligne de commande garde
  toujours la priorite, y compris quand elle retape une valeur par defaut.
- **Cartons rouges** (`--red-cards`), **annonce d'avant-match**
  (`--before-kickoff N`, une seule fois par match) et **carte de fin de match
  avec les buteurs**. Aucune des trois ne fait de bruit : seul un but declenche
  le son.
- **Fichier d'etat et `--today`** : `--status` dit maintenant quand a eu lieu
  le dernier releve, quels matchs sont en cours et combien de buts sont tombes
  aujourd'hui, avec un avertissement quand le releve est trop vieux pour la
  cadence annoncee. `--today` recapitule la journee en relisant le journal, la
  seule trace qui survive a un redemarrage.
- **Publication PyPI** en Trusted Publishing, dans un workflow separe et inerte
  tant que le proprietaire du depot ne l'a pas arme (voir README).

### Corrige

- **Plus de fausses cartes en sortant de veille.** Apres une suspension, la
  source avait des heures d'avance sur notre derniere photo : le daemon criait
  un but avec un ecart de trois et une minute perimee. Un trou d'horloge remet
  desormais les competitions a l'etat "jamais photographie", ce qui reutilise le
  chemin silencieux du premier releve. La detection compare le temps reellement
  ecoule a l'attente annoncee, et non `time.monotonic()` a `time.time()` : la
  semantique de monotonic vis-a-vis de la veille differe entre Windows et Linux,
  ce detecteur-la aurait ete faux d'un cote.
- **Une carte masquee par une application en plein ecran est signalee.** Une
  fenetre `topmost` passe derriere un jeu ou un lecteur en plein ecran
  exclusif : le but etait rate en silence. Detecte sous Windows, note au
  journal, et `--retry-fullscreen` repasse la carte des que l'ecran se libere.
- Les liens relatifs du README auraient tous ete morts sur la fiche PyPI, et le
  sdist embarquait les tests sans `tests/helpers.py` : ils ne demarraient meme
  pas.
- Le fichier de configuration ignorait quatre options ajoutees en parallele par
  d'autres branches. Un test verifie desormais que toute option durable du
  parseur a sa cle.

### Interne

- 179 -> **403 tests**, toujours sans reseau ni ecran.


## [1.2.0] - 2026-09-06

### Ajoute

- **Filtre par equipe** : `--teams om,psg` ne signale que les matchs de ces
  clubs, `--exclude-teams psg` ne signale que les autres. Un match compte des
  qu'une des deux equipes y est, buts et cartes de deroulement comprises, et
  `--scores` s'y plie aussi.
- La reconnaissance des noms encaisse le nom complet, le nom court,
  l'abreviation de la source, les accents (`malaga` trouve Malaga), un debut de
  mot a partir de quatre lettres, et une table de surnoms usuels (`om`, `ol`,
  `asse`, `losc`, `manu`, `barca`, `juve`, `bvb`...). Un mot ne mord qu'au
  debut d'un mot du nom : `real` designe Madrid, Sociedad et Betis, mais pas
  Villarreal.
- Un mot qui ne designe aucune equipe est refuse au demarrage, avec la liste
  des competitions ou il a ete cherche - plutot qu'un daemon muet pour
  toujours.
- `--list-teams` liste les equipes des competitions suivies et marque celles
  que le filtre attrape (`*` suivie, `-` exclue).
- Une banniere en tete du README : deux supporters ahuris qui pointent cinq
  ecrans affichant tous un but. Dessinee en vectoriel
  ([docs/banniere.svg](docs/banniere.svg), genere par
  [docs/banniere.py](docs/banniere.py)), aux couleurs des cartes, et
  rasterisee en PNG pour l'affichage sur GitHub.

## [1.1.1] - 2026-09-06

### Corrige

- **`--status`, `--scores` et `--test` plantaient en 1.1.0** avec un
  `NameError`. En retirant la fonction devenue inutile qui deduisait les coups
  d'envoi, le decoupage a emporte les quatre fonctions voisines, dont
  `do_status`. La surveillance et les cartes, elles, n'etaient pas touchees :
  seuls ces trois commandes l'etaient. **Passer directement de 1.0.x a 1.1.1.**
- Un test verifie desormais que chaque commande appelee par `main()` existe
  bel et bien, et chaque commande est executee au moins une fois avec la source
  simulee. La suite passait sur la 1.1.0 cassee parce qu'aucun test n'entrait
  dans ces commandes : c'est cette lacune qui est comblee.

## [1.1.0] - 2026-09-06

### Ajoute

- Cartes de deroulement du match : **coup d'envoi**, **mi-temps**, **reprise**
  et **fin du match**. Volontairement plus sobres qu'un but (titre gris, pas de
  troisieme ligne, aucune equipe mise en avant) et surtout **sans aucun son** :
  seul un but declenche la corne. La phase est lue dans `status.type.name` de
  la source (`STATUS_HALFTIME`, `STATUS_SECOND_HALF`, `STATUS_FULL_TIME`...),
  et la mi-temps des prolongations compte comme une mi-temps.
- `--no-phase-cards` pour n'avoir que les buts a l'ecran. Le journal continue
  d'enregistrer ces moments.
- Un match jamais vu en cours ne declenche pas de carte de fin, et un match
  reporte ou abandonne reste muet.
- Badges CI, release, Python et licence dans le README, plus une capture de
  trois cartes empilees.

### Corrige

- **Le nom de l'equipe pouvait sortir de la carte par la gauche.** Le score est
  centre dans la carte, mais la largeur reservee aux noms suivait la somme des
  deux : des que l'un etait bien plus long que l'autre, il debordait
  (`Eintracht Frankfurt 1 - 4 FC Augsburg`). La place reservee est desormais la
  meme de chaque cote, ce qui rend le debordement impossible par construction ;
  des noms a rallonge sont raccourcis avec des points de suspension plutot que
  de sortir du cadre.
- Un but annule ne declenchait plus de son que dans la documentation : le
  daemon le jouait quand meme. Seul un vrai but fait du bruit.

### Change

- Les lignes de journal « coup d'envoi » et « fin du match », qui etaient
  deduites d'une comparaison de listes dans la boucle, viennent maintenant des
  memes evenements que les cartes. Un seul chemin, une seule verite.

## [1.0.1] - 2026-09-06

### Corrige

- `install.ps1` : la verification de connexion a la source echouait sur
  Windows. PowerShell mange les guillemets doubles internes en passant a un
  exe natif, et `2>$null` sur une commande native emballe la sortie d'erreur
  dans un `ErrorRecord` qui, avec `ErrorActionPreference = Stop`, faisait
  echouer l'installation entiere. L'URL passe desormais par `argv` et les
  appels a python passent par un helper qui neutralise les deux pieges.
- `install.sh` et `uninstall.sh` : `[ test ] && variable=1` sous `set -e`
  faisait sortir le script quand le test etait faux (aucune option passee).
  Remplace par des `if`.
- `uninstall.sh --help` desinstallait au lieu d'afficher l'aide : les
  arguments sont maintenant analyses.
- Le test `play_async` sur un fichier absent verifiait la mauvaise chose : le
  contrat est de ne jamais lever, pas de rendre `None`. Il echouait sur macOS,
  ou `afplay` est bien lance et echoue de son cote.

## [1.0.0] - 2026-09-06

Premiere version.

### Ajoute

- Surveillance en fond des cinq grands championnats europeens : Ligue 1,
  Premier League, LaLiga, Serie A, Bundesliga.
- Carte de score a l'ecran a chaque but : championnat, minute,
  `Equipe A score - score Equipe B`, et le buteur. L'equipe qui vient de
  marquer et son chiffre prennent la couleur du championnat, le nom du buteur
  ressort en clair.
- Les cartes s'empilent depuis le coin choisi (`bottom-right` par defaut) : la
  derniere arrivee est collee au coin, les precedentes remontent, et quand
  l'une s'efface les autres reprennent sa place. Cinq cartes visibles au plus.
- Son a chaque but : le mp3 fourni, un fichier perso depose dans le dossier
  `sound`, ou une corne de stade synthetisee en dernier recours. Un seul coup
  de corne quand plusieurs buts remontent dans le meme releve.
- Catalogue de 36 competitions, toutes verifiees contre la source : coupes
  d'Europe (`ucl`, `uel`, `uecl`, supercoupe), selections (Coupe du monde,
  Ligue des nations, qualifications), deuxiemes divisions (Ligue 2,
  Championship, Serie B, 2. Bundesliga, LaLiga 2), autres championnats
  europeens (Portugal, Eredivisie, Belgique, Super Lig, Ecosse), coupes
  nationales (Coupe de France, FA Cup, Carabao, Copa del Rey, Coppa Italia,
  DFB-Pokal) et hors d'Europe (MLS, Liga MX, Bresil, Argentine, Saudi,
  J.League, Libertadores, Concacaf).
- `--leagues` pour choisir, `--exclude` pour retirer, `--list` pour voir le
  catalogue et ses alias. Les mots-cles `all` et `big5` sont acceptes.
- N'importe quel code ESPN passe a la volee (`--leagues gre.1`) : la
  competition prend le nom que la source annonce au premier releve.
- Detection : un score qui monte est un but. Les actions de la source ne
  servent qu'a habiller la carte (buteur, minute, csc, penalty), jamais a
  detecter, car elles arrivent parfois quelques secondes plus tard.
- Le premier releve est silencieux : lancer le daemon en pleine journee de
  championnat ne rejoue pas les buts deja marques.
- Un score qui descend (but refuse par la VAR) affiche une carte orange
  `BUT ANNULE`, sans son.
- Cadence adaptative et independante par competition : 25 s quand un match est
  en cours, 60 s a l'approche d'un coup d'envoi, 5 min au repos. Les releves
  sont decales les uns des autres pour ne pas tirer trente-six requetes en
  rafale.
- Attente doublee a chaque echec reseau (plafond 5 min), reprise notee dans le
  journal.
- `--scores` pour les matchs du jour dans le terminal, `--status` pour l'etat
  complet (daemon, son, ecrans, connexion), `--test N` pour voir des cartes
  s'empiler, `--stop`, `--paths`, `--screens`.
- Multi-ecrans : les ecrans sont enumeres via l'API systeme
  (`EnumDisplayMonitors`, `xrandr --listmonitors`, CoreGraphics), pas via
  tkinter, pour qu'une carte ne se retrouve jamais a cheval sur deux dalles.
- Fenetres sans bordure, toujours au-dessus, qui ne volent jamais le focus ;
  fond transparent et clics traversants sous Windows.
- Instance unique via fichier pid, journal horodate, `--quiet` pour n'ecrire
  que dans le journal.
- Installation par plateforme : `install.sh` (systemd utilisateur, LaunchAgent
  macOS, autostart `.desktop`), `install.ps1` (raccourci de demarrage, PATH
  utilisateur, sans droits admin), PKGBUILD Arch.
- 113 tests, sans reseau ni ecran : la source est simulee, la geometrie de
  l'empilement est testee sans tkinter.

[Non publie]: https://github.com/boubou666/butbutbut/compare/v1.10.2...HEAD
[1.10.2]: https://github.com/boubou666/butbutbut/compare/v1.10.1...v1.10.2
[1.10.1]: https://github.com/boubou666/butbutbut/compare/v1.10.0...v1.10.1
[1.10.0]: https://github.com/boubou666/butbutbut/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/boubou666/butbutbut/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/boubou666/butbutbut/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/boubou666/butbutbut/compare/v1.5.0...v1.7.0
[1.5.0]: https://github.com/boubou666/butbutbut/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/boubou666/butbutbut/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/boubou666/butbutbut/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/boubou666/butbutbut/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/boubou666/butbutbut/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/boubou666/butbutbut/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/boubou666/butbutbut/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/boubou666/butbutbut/releases/tag/v1.0.0
