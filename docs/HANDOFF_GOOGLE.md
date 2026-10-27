# Passation exhaustive — Vampires vs Werewolves / AI-GAME-THEORY

**État vérifié le 27 octobre 2026.** Document demandé par Julian pour qu'un assistant Google ayant accès à ce PC reprenne le travail. Lire d'abord cette passation et le fichier voisin [HANDOFF_STATE.json](HANDOFF_STATE.json). Les variables en mémoire et les outils privés de Codex ne sont pas transférés : les fichiers, le code et les preuves le sont.

## 1. État immédiat : tout le lot prévu est terminé

- **16 parties sur le vrai serveur WPF à 200 demi-coups maximum, 16 verdicts confirmés.** La fenêtre qui bloquait le 13e résultat a été restaurée et les trois dernières parties ont ensuite été terminées.
- Serveur arrêté ; aucun écouteur sur le port 5555 observé à la vérification de passation.
- **125 tests Python réussis en 9,916 s**, sous Python 3.14.7.
- Configurations conservées : **AB2, AB3, AB6 et le nouvel AB7**, préférence pour **AB2 et AB6**. AB0 reste disponible comme témoin ; aucun ancien modèle n'a été supprimé.
- Les justifications des quatre configurations et le tableau des techniques évoquées par le professeur sont rédigés.
- Aucun calcul, entraînement, partie ou verdict n'est en attente. **Ne pas relancer automatiquement une ancienne campagne.**
- La dernière demande consiste à préparer cette passation. Les éventuelles étapes suivantes dépendent de la prochaine consigne de Julian.
- Les instructions personnelles concernant CFTC / CIT / `cit_research` ne sont pas le plan de ce projet.

## 2. Projet, objectifs et préférences

Projet de groupe de Foundation(s) of AI, CentraleSupélec : développer un bot pour Vampires vs Werewolves, anticiper l'adversaire, respecter deux secondes par décision, comparer les configurations et expliquer leurs choix au professeur.

Dépôt : <https://github.com/redaabid/AI-GAME-THEORY>.

La direction retenue est une **famille Alpha-Bêta**, améliorée par ses composants : sélection des mouvements, coordination, ordre de recherche, mémoire, évaluation et traitement du hasard. MCTS, OEP, Portfolio et les autres agents des camarades restent disponibles, mais ne constituent pas la direction principale choisie.

Julian demande des justifications : publications classiques **et récentes**, expériences, sources techniques et inspiration des anciennes équipes. Il ne souhaite pas reproduire fidèlement leurs bots. Ne pas présenter une référence récente consultée après l'implémentation comme sa source initiale, ni prétendre reproduire un article lorsque nous n'en adaptons qu'un principe.

Préférences : agir concrètement, préserver le code des camarades, expliquer en français et brièvement dans le chat, conserver les détails dans les documents. Éviter les demandes de confirmation répétées pour ce qui est autorisé. Économiser les crédits : scripts locaux, petits lots ciblés, pas d'analyse de chaque coup par le modèle. Aucun montant exact de crédits n'a été mesuré ; temps CPU du bot et consommation de l'assistant sont deux choses distinctes.

## 3. Chemins et worktrees : ne pas se tromper de dépôt

L'ancien dossier ouvert dans la conversation était :

`C:\Users\sebju\AUtres\Documents\ChatGPT\Foundation of AI`

Il ne contient pas le code du jeu : seul un dossier `.git` y a été observé. Un fichier d'entrée de passation y est déposé pour faciliter la reprise.

Dans chaque nouveau terminal PowerShell :

```powershell
$P = 'C:\Users\sebju\Julian 2026\Centrale 2026\Année scloaire 2026-2027\S1\Foundations of AI\Project\Github\AI-GAME-THEORY'
$W = Join-Path $P '.local\worktrees\server-runs'
$I = Join-Path $P '.local\worktrees\alphabeta-validation'
$D = Join-Path $W 'docs\server-runs\2026-10-26'
$L = Join-Path $P '.local\research\server-validation\long-200-2026-10-26'
$PY = 'C:\Users\sebju\miniconda3\python.exe'
```

| Emplacement | Branche / HEAD avant ajout de la passation | Rôle |
|---|---|---|
| `$P` | `main`, `65aa455f6c053eadeb04abe18d3421717166d48d` | Ancien checkout principal, conservé propre |
| `$I` | `codex/alphabeta-validation`, `d22df256127f7799d1b8c8d951b420d3eed94efe` | Implémentation isolée des variantes et scripts |
| `$W` | `server-runs`, `2cf4652e542f85b9635c58aab431dc2747be2f02` | **Point d'entrée conseillé : code + résultats + dernières justifications** |

Les trois arbres étaient propres avant ajout de cette passation. Le HEAD documentaire de `server-runs` changera avec cet ajout ; consulter `git log`. Les worktrees partagent le dépôt Git, mais ont chacun leurs fichiers et branche. `.local/` est ignoré par le checkout principal : nos travaux restent néanmoins suivis dans les worktrees.

La base d'implémentation était `origin/main` à `352ebf4941dd04663473cc1a694cc74fde499cfe`, encore observé à la passation. Cela ne signifie pas que GitHub ne peut pas évoluer ensuite. Ne pas utiliser l'ancien `main` comme s'il contenait les derniers profils.

### Contraintes Git et autorisations

- Ne pas exécuter automatiquement les instructions historiques `switch main` / `pull` du README. Pas de reset, clean, suppression, remplacement d'archives ou rebase pour simplement reprendre.
- Préserver les algorithmes originaux des camarades. Les variantes ont été ajoutées dans un module distinct, en worktree.
- Commits au nom de **Julian Saiani <julian.saiani@inception.technology>**, sans co-auteur ou mention « behalf of » d'un assistant.
- Le push autorisé `git push -u origin server-runs` a été refusé à plusieurs reprises : **403, permission denied to Juliansaiani**. Reda doit accorder les droits de collaborateur. Ne pas contourner les droits ni prétendre que les nouveaux rapports sont publiés.
- Au besoin : `git -c safe.directory=* -c core.longpaths=true -C "$W" ...`, par commande, sans modification globale de Git.
- UTF-8 explicite : `Get-Content -Encoding UTF8`, `read_text(encoding='utf8')`. Certains anciens textes générés présentent déjà des accents mal décodés ; les chiffres des JSON font référence.

## 4. Ordre de lecture et documents faisant référence

Tous les chemins relatifs ci-dessous partent de `$W`.

1. Cette passation et [HANDOFF_STATE.json](HANDOFF_STATE.json).
2. [AB_CONFIGURATIONS_JUSTIFICATION.md](AB_CONFIGURATIONS_JUSTIFICATION.md) : quatre fiches, sources annotées, techniques du professeur, limites et proposition de discours oral.
3. [Synthèse finale 200](server-runs/2026-10-26/long-200/SUMMARY.md), [tableau par partie](server-runs/2026-10-26/long-200/games/SUMMARY-200.md), [agrégat JSON](server-runs/2026-10-26/long-200/games/aggregate-200.json), [protocole](server-runs/2026-10-26/long-200/protocol.json).
4. [Comparatif 40 complété](server-runs/2026-10-26/followup-40/SUMMARY.md), puis ses `aggregate-40.json`, `SUMMARY-40.md` et `decisions/decisions.json`.
5. [Description initiale des variantes](AB_VARIANTS.md), puis le code listé en section 8.
6. Audits d'anciens projets et littérature locale, si nécessaire, section 13.

Les anciennes mentions « huit verdicts manquants », « pause avant 200 » ou « AB7 non testé sur Windows » décrivent **une étape historique**. Les rapports finaux ci-dessus et cette passation donnent l'état actuel. Ne pas réécrire les archives pour gommer leur chronologie.

## 5. Configurations et différences exactes

Le bot original `agents/alphabeta.py` est conservé. Le nouveau `agents/ab_variants.py` enregistre `ab0` à `ab8` dans un moteur modulaire :

| Profil | Ajout / comportement |
|---|---|
| AB0 | Alpha-Bêta déterministe, profondeur fixe, ordre canonique |
| AB1 | Approfondissement itératif et ordre statique |
| AB2 | AB1 + historique et table de transposition avec bornes |
| AB3 | AB2 + propositions par scripts et sélection diversifiée |
| AB4 | AB3 + PVS et aspiration, avec reprise si nécessaire |
| AB5 | AB3 + quiescence tactique bornée, sans stand-pat |
| AB6 | AB3 + distributions finies des survivants et intervalles de chance |
| AB7 | Structure d'AB3, poids d'évaluation explicites réglés hors ligne |
| AB8 | AB2 + MTD(f), mémoire et fenêtres nulles ; **sans scripts d'AB3** |

Les techniques évoquées avec le professeur ont bien été expérimentées : move ordering et iterative deepening AB1–AB8 ; mémoire AB2–AB8 ; scripts AB3–AB7 ; fenêtres étroites AB4 et pilote MTD(f) AB8 ; quiescence AB5 ; hasard AB6 ; évaluation AB7. AB4/5/8 ont été testés à 40 coups mais ne sont pas sélectionnés aujourd'hui.

### Points à expliquer correctement

- **AB2 sélectionne déjà un sous-ensemble borné de mouvements**, comprenant des tours coordonnés et des splits dans `candidates.py`. AB3 enrichit cette base : il n'introduit pas la première coordination du projet.
- Les scripts produisent le **tour courant**, réévalué ensuite. Ce ne sont pas des macro-actions temporelles engagées sur plusieurs tours.
- Profils retenus testés : `width=6`, `max_depth=8`, `extra=0`, `tt_size=50000`. Produire/classer les propositions peut coûter davantage que la recherche de la liste retenue. `depth=1` ne limite pas un profil itératif chronométré à une profondeur de 1.
- Les paramètres `qdepth`, `qwidth`, `aspiration` présents dans les chaînes ne suffisent pas à activer une option : AB2/3/6/7 n'ont ni quiescence ni PVS/aspiration.
- La TT contient plateau, trait, demi-coup, règles, profondeur, régime de quiescence et plafond. L'historique réordonne sans changer la composition des candidats retenus. La clé incluant la profondeur, ne pas revendiquer une réutilisation automatique du meilleur coup d'une autre profondeur.
- Score terminal ±1 000 000 ; heuristiques strictement à l'intérieur. Secours légal acquis avant la recherche, dernière itération complète conservée. `AB_METRICS` documente profondeur, TT, nœuds, deadline, bootstrap, chances, etc.
- AB2/3/7 utilisent `simulate_turn(..., None)` : **l'issue la plus probable, avec survivants conditionnels moyens arrondis**. C'est un substitut déterministe, pas une simulation exacte des combats ni leur espérance globale.
- AB6 additionne les arrivées par destination, énumère victoire/défaite et survivants binomiaux, regroupe l'issue sans survivants et combine les combats de destinations indépendantes selon le simulateur. Les coupures bornent la contribution de la probabilité restante ; elles ne suppriment pas arbitrairement les issues rares.
- « Distribution complète » signifie complète **dans ce modèle**, pas certification indépendante de tous les comportements DLL. La sélection des candidats d'AB6 reste classée par le substitut déterministe et peut donc filtrer une action intéressante en espérance. Espérance d'heuristique, probabilité calibrée de victoire et aversion au risque sont des notions différentes.

### Ancien et nouveau AB7

L'ancien AB7 avait conservé les poids d'AB3 et faisait doublon sur les sondes étudiées. Réglage supplémentaire : **60 parties simulées d'entraînement puis 24 de validation**, cartes séparées, maximum 40 demi-coups, budgets 0,08 s / 0,2 s.

Candidat retenu : `discount=0.97` au lieu de 0,90, les autres poids restant `material=1`, `humans=0.8`, `threat=0.7`, `groups=0.1`. Ce paramètre concerne la distance aux humains dans l'évaluation, pas la probabilité de combat. Les poids affectent aussi le classement avant sélection : même structure de génération ne signifie pas exactement le même arbre retenu.

Huit parties de validation du candidat : **2 V / 6 N / 0 D**, score **0,625** contre 0,500 pour le contrôle AB3 ; un nul vaut un demi-point. Ce n'est pas un taux de victoire de 62,5 %. Le candidat change un choix sur douze positions contrôlées puis joue bien les quatre parties WPF à 200 coups.

Les fichiers historiques du candidat disent encore « no WPF / no 200 test » : vrais lors de leur création, avant le lot final. Garder cette provenance et consulter le rapport 200 pour l'état actuel. **`--agent ab7` sans poids explicites est volontairement refusé.**

## 6. Résultats et conclusions permises

### Lot final à 200 demi-coups maximum

| Profil | Adversaires / parties | V / N / D | Moyenne / maximum |
|---|---|---|---|
| **AB2** | AB3, 4 | **3 / 1 / 0** | 0,370 / 1,507 s |
| **AB6** | AB3, 4 | **3 / 0 / 1** | 1,473 / 1,513 s |
| **Nouvel AB7** | AB3, 4 | **2 / 0 / 2** | 0,555 / 1,503 s |
| AB0 témoin | AB3, 4 | 1 / 0 / 3 | 0,002 / 0,005 s |
| AB3 | Quatre adversaires, 16 | 6 / 1 / 9 | 0,578 / 1,513 s |

Deux cartes (`thetrap.xml` / `testmap2.xml`), deux ordres de connexion. **Aucun duel direct AB2–AB6.** La ligne AB3 regroupe des adversaires différents ; elle n'est pas directement comparable à une série de quatre parties.

Zéro Agent fault, erreur, occurrence de fallback, bootstrap ou alerte >1,8 s. Codes de sortie nuls et END/BYE reçus pour tous. Les temps sont arrondis dans les logs, pas mesurés indépendamment par le serveur sur toute la chaîne réseau.

**Un seul nul sur 16**, mais **12 parties atteignent le plafond et ces douze présentent des répétitions de positions**. Six fins avec une espèce à zéro, dont deux au dernier coup ; neuf victoires au score avec deux espèces présentes ; un nul. Moins de nuls ne signifie donc pas une progression stratégique satisfaisante. AB2 et AB6 sont prioritaires sur ce petit lot, pas statistiquement démontrés supérieurs.

`--seed 42` ne fixe pas le hasard du serveur. Reproduire le code et les paramètres ne garantit pas les mêmes coups ou gagnants ; le PC influence aussi les profondeurs terminées sous deadline.

### Lot 40 : comparaison composée terminée

**32 conditions de famille avec un verdict confirmé**, puis **6 contrôles**, soit **38 conditions sélectionnées et 49 tentatives brutes**. Huit verdicts initiaux étaient manquants : leurs conditions ont été rejouées, pas leurs anciens résultats retrouvés. Trois contrôles ont aussi été rejoués après une expiration de capture UI. Garder les inconnus historiques et ne pas compter deux fois une condition.

Contre AB3, quatre conditions par challenger : AB0/1/2/4/5 et **ancien AB7** ont chacun 1 V / 2 N / 1 D ; AB6 2 V / 2 N / 0 D ; AB8 0 V / 2 N / 2 D. Sur les 49 tentatives : aucune faute, erreur ou alerte >1,8 s ; maximum 1,550 s en incluant les contrôles.

Ancien `alphabeta` inchangé nommé **AB90 uniquement pour l'UI** : 1 V / 2 N / 1 D ; ses deux parties `testmap2` font 16–16. Baseline historique nommée AB91 : deux défaites 14–16 contre AB3 sur cette carte. Le protocole ne forçait pas les nuls ; recrutement symétrique et arrêt précoce rendaient le test peu discriminant. Les anciens rapports du 22 octobre montraient déjà des nuls contre OEP et des victoires 16–14 contre d'autres bots, souvent au plafond sans élimination.

Aucune répétition exacte n'avait été observée avant le plafond court sur les cas étudiés ; les répétitions nombreuses apparaissent dans les traces longues. Les états reconstruits **avant MOV** ne donnent pas automatiquement les effectifs après le dernier combat.

### Décisions sur positions identiques : déjà fait

12 positions (8 états reconstruits du serveur, 4 cartes nouvelles), profondeur 2 sans deadline, deux régimes de paramètres, 11 profils : **264 décisions légales terminées**, aucune faute.

À paramètres communs, mêmes choix/valeurs pour AB0/1/2/8 et pour AB3/4 : attendu pour des optimisations de calcul équivalentes à arbre fixé. AB2 diffère d'AB3 sur 3/12 positions. AB6 choisit les mêmes actions qu'AB3 sur cet échantillon mais une valeur passe du substitut déterministe +1 000 000 à 0 probabiliste. Nouveau AB7 : un choix différent sur douze ; ancien AB7 : aucun. Le témoin ancien garde sa largeur native 10, donc son écart n'isole pas seulement le moteur.

## 7. Serveur Windows, fichiers et paramètres réels

Application WPF `VampiresVSWerewolvesGameServer.exe`. Six fichiers présents dans les deux emplacements :

```text
VampiresVSWerewolvesGameServer.exe
VampiresVSWerewolvesGameServer.exe.config
VVSW.Model.dll
VVSW.Controls.dll
thetrap.xml
testmap2.xml
```

- **Installation originale** : `$P\.local\server` ; au snapshot : carte `thetrap.xml`, `MaxPlays=200`, **MaxGameDuration=00:05:00**.
- **Runtime de la campagne finale** : `$L\runtime` ; au snapshot : carte `testmap2.xml`, `MaxPlays=200`, **MaxGameDuration=00:10:00**. Les essais ont modifié une copie dédiée, pas l'installation originale.

Cible déclarée : .NET Framework 4.5 / CLR4. .NET Framework 4.8.09221, Release 533509, installé lors des contrôles et serveur réellement exécuté. Ce n'est pas une application à lancer par `dotnet` sous Linux. Les propriétés des EXE/DLL affichent 1.0.0.0 ; le nom d'archive était `Server v3.2.1.zip` à l'intérieur de `Softwares-20261008.zip`. Un chemin actuel du ZIP n'est pas garanti ; les fichiers extraits suffisent pour fonctionner.

Profil de règles des bots : **`server-v3.2.1`**, distinct de `brief` dans `combat.py`. Ne pas changer silencieusement de profil ni déduire une équivalence complète de la seule version de fichier.

| Clé XML réelle `appSettings/add` | Valeur du lot final |
|---|---|
| `ServerIP` / `ServerPort` | `127.0.0.1` / `5555` |
| `PlayersCount` | `2` |
| `Map` | Chemin absolu de la carte du runtime |
| `MaxPlayDuration` | `00:00:02` |
| `MaxGameDuration` | `00:10:00` |
| `MaxPlays` | `200`, égal au `--max-plies` des deux bots |
| `DebugMode` / `AutoRestart` | `True` / `False` |

Les deux secondes sont une exigence du sujet. **200 demi-coups et dix minutes sont notre protocole local, pas des conditions officielles de tournoi établies.** Chaque bot dispose au plus d'environ 100 décisions ; une élimination peut arrêter avant.

Le serveur écoute automatiquement au lancement : aucun bouton Start n'a été nécessaire. **Ne pas ouvrir une connexion TCP de sonde** avec `Test-NetConnection`, un socket, etc. : elle peut être comptée comme un joueur. Observer le port avec `netstat -an`, puis connecter exactement les deux bots.

Lire le XML avec `utf-8-sig` si nécessaire, écrire avec la déclaration **`encoding="utf-8"`**. La variante `utf8` avait été refusée par .NET. Après copie, mettre `Map` au chemin absolu du nouveau runtime. Préserver les autres réglages.

Ne pas lancer `setup_server.py --force` pour réparer une fenêtre ou « vérifier » l'installation : il réinitialise la démo à **40 coups / 30 secondes**, et ne remplace pas un observateur UI. Ce script sert à une nouvelle extraction intentionnelle, sans écraser les installations actuelles.

## 8. Interpréteurs, code et tests

Deux Python sont présents et la résolution de `python` a varié selon le terminal :

- Campagne 40 : **3.14.3**, `C:\Users\sebju\AppData\Local\Programs\Python\Python314\python.exe`.
- Campagne finale 200 et ses 125 tests : **3.14.7**, `C:\Users\sebju\miniconda3\python.exe`.
- À la passation, `python --version` indiquait de nouveau 3.14.3 ; l'exécutable Miniconda explicite restait à 3.14.7. Pour l'environnement final, utiliser `$PY`.

Aucune dépendance externe ni GPU nécessaire pour ces bots et scripts. Ne pas installer Torch à cause d'un ancien projet externe.

Code dans `$W` ou `$I` :

| Fichiers | Fonction |
|---|---|
| `main.py` | CLI, boucle MAP/UPD, deadline, appel sûr, MOV et logs ; sans `--agent` explicite, baseline |
| `client.py`, `game.py`, `config.py` | Protocole, état, validation et valeurs par défaut |
| `agents/ab_variants.py` | Nos profils AB0–AB8 |
| `agents/alphabeta.py` et autres agents | Contributions originales conservées |
| `candidates.py`, `lookahead.py`, `playbook.py`, `macro.py` | Candidats, scripts, coordination et intentions |
| `evaluation.py` | Effectifs, humains, menaces, dispersion, poids et score |
| `combat.py`, `simulator.py` | Règles de combat, transitions, état et fins |
| `tests/test_ab_variants.py` | Dix tests ajoutés : petit oracle Minimax indépendant, variantes, deadline, caches et distributions |

Suite complète : 115 tests préexistants + 10 nouveaux = 125. Cela n'est pas une certification exhaustive du serveur.

Commandes si nécessaires, sans lancer de partie :

```powershell
& $PY --version
git -c safe.directory=* -c core.longpaths=true -C $W status --short --branch
git -c safe.directory=* -C $W log -6 --oneline
Get-Content -Encoding UTF8 (Join-Path $D 'long-200\protocol.json')
Push-Location -LiteralPath $W
& $PY -B -m unittest discover -s tests -v
Pop-Location
```

Spécifications exactes : `$D\long-200\protocol.json`, champ `profiles`, et `$L\selection.json`. Charger ces chaînes au lieu d'inventer les valeurs par défaut. SHA-256 Git/LF du moteur : `bed8077a39f16561f0cc666a007d19cfe92f2251559f33dbc7076f3415637ac8`. Sur disque dans `$W`, CRLF donne `9e6e133d806dca69b9266b3e056a8bcc7dbae5600ac6afa89cb7be97aecf45da` ; normaliser CRLF vers LF retrouve le premier. Le code de `$I` et `$W` est donc identique, pas deux variantes différentes.

## 9. Lancer une nouvelle partie : procédure, pas instruction de démarrer

Créer un **nouveau** dossier daté sous `$P\.local\research\server-validation` et un runtime neuf ; copier les six fichiers, régler le XML et son chemin de carte, archiver les commandes et paramètres. Les binaires du professeur restent hors de GitHub.

Une fois `$R` défini comme ce nouveau runtime configuré :

```powershell
$serverHandle = Start-Process -FilePath (Join-Path $R 'VampiresVSWerewolvesGameServer.exe') -WorkingDirectory $R -PassThru
netstat -an | Select-String ':5555 .*LISTENING'
```

La fenêtre doit être observable. Chaque bot est un processus distinct. Dans **chaque terminal**, redéfinir les variables de section 3 puis :

```powershell
$specs = (Get-Content -Raw -Encoding UTF8 (Join-Path $D 'long-200\protocol.json') | ConvertFrom-Json).profiles
Set-Location -LiteralPath $W
# Terminal A : exemple AB2
& $PY -B main.py --name AB2 --agent $specs.ab2 --move-time 1.5 --max-plies 200 --rules-profile server-v3.2.1 --seed 42 127.0.0.1 5555
# Terminal B, après la ligne Board: du premier bot :
& $PY -B main.py --name AB6 --agent $specs.ab6 --move-time 1.5 --max-plies 200 --rules-profile server-v3.2.1 --seed 42 127.0.0.1 5555
```

Les deux commandes tournent simultanément, pas successivement dans un terminal bloqué. Remplacer le profil par `$specs.ab3` / `$specs.ab7` selon le duel demandé. Ne pas oublier que ces exemples **ne signifient pas qu'un duel AB2–AB6 a été joué ou doit être lancé maintenant**. Faire correspondre `--max-plies` au serveur.

Ces commandes manuelles expliquent le fonctionnement, mais ne produisent pas à elles seules toute l'archive. Pour les lots, le lanceur sauvegarde stdout/stderr, manifeste, XML, commandes, traces et résultats.

### Lanceur existant : contraintes importantes

`scripts/run_ab_server.py` accepte `--runtime`, `--selection`, `--output`, `--ids`, `--allow-200`, `--move-time`, `--stop-on-bot-error`, `--ui-timeout`. Il refuse une sortie existante et un port occupé ; il gère seulement ses propres processus.

**La référence AB3 est codée dans ce lanceur.** Il ne sait pas planifier un duel arbitraire AB2–AB6 en supprimant AB3 de la sélection. Adapter un lanceur serait un travail nouveau, à faire seulement pour une expérience demandée.

Les IDs dépendent du nombre et de l'ordre des profils, du plafond, de la carte et de l'ordre de connexion :
- Sélection finale ordonnée **AB0, AB2, AB3, AB6, AB7** : 1–16 à 40 coups, **17–32 à 200**.
- Sélection initiale AB0–AB8 : 32 conditions par plafond, donc autre découpage.

Ne pas copier des IDs sans vérifier la sélection. Pas d'option `--dry-run` dans le script. `--allow-200` est toujours un garde-fou intentionnel, même si le premier lot est maintenant fini.

Commande historique, **à ne pas réexécuter sur les sorties existantes** :

```text
python -B scripts/run_ab_server.py --runtime <L>/runtime --selection <L>/selection.json --output <L>/games --ids 17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32 --allow-200 --stop-on-bot-error --move-time 1.5 --ui-timeout 3600
```

`$L\campaign.py` est un wrapper ancien à chemins fixes qui réécrit état et logs avant lancement : **ne pas le relancer**. `live_summary.py` est terminé. Les PID enregistrés sont historiques et peuvent être réattribués : ils n'autorisent pas à tuer un processus actuel. Ne jamais fermer globalement tous les Python ou serveurs du PC.

## 10. Lecture des verdicts WPF : automatisation partielle

Les logs Python actuels reçoivent END/BYE sans fournir directement le vainqueur et les effectifs finaux. Le serveur affiche le résultat dans **« Vampires versus Werewolves »**. Ne jamais le déduire d'un simulateur ou transformer une capture manquante en nul.

Le lanceur écrit `<output>/awaiting-ui.json` après la fin des bots : dossier de partie, PID possédé et index. Il attend `<partie>/ui-evidence.json` avant de passer au match suivant. Une expiration de capture fait arrêter le lot avant la suite.

### Observation robuste avec les outils propres à Google

1. Lire la nouvelle demande et son `manifest.json` ; ignorer une demande déjà traitée. Ne pas appliquer l'ancienne demande à une nouvelle fenêtre.
2. Identifier la fenêtre du runtime de cette campagne ; vérifier noms et ordre des bots.
3. Relever le **verdict explicite** et les effectifs. Le texte d'accessibilité peut être périmé, même avec les bons noms ; le bitmap a aussi parfois été figé.
4. Restaurer la fenêtre si elle est minimisée ; activer puis agrandir/restaurer si nécessaire pour forcer un rafraîchissement. Relire après l'animation de fin.
5. Si les outils restent bloqués ou signalent une interaction persistante, demander à Julian une restauration, conserver les données et attendre. Ne pas rejouer ni tuer le serveur pour « réparer » une observation.
6. Écrire la preuve vérifiée, puis fermer normalement **ce serveur uniquement**. Le lanceur attend brièvement avant son mécanisme de terminaison de secours.

Format portable d'une preuve, exemple de structure et non résultat à fabriquer :

```json
{
  "captured": "date UTC ISO réelle",
  "request": {"game": "chemin exact du dossier", "server_pid": 12345, "index": 29},
  "captures": [{"tree": "texte réellement disponible", "document_text": "texte disponible"}],
  "manual": {
    "winner": "ab6",
    "populations": {"ab3": 4, "ab6": 12},
    "observed_order": ["ab3", "ab6"],
    "reason": "Verdict et effectifs lus visuellement après rafraîchissement"
  }
}
```

Le gagnant appartient au manifeste ou vaut `draw`. Populations entières, noms et ordre vérifiés sur l'écran. Pour un nul, l'interface a affiché **« No winner / No looser »**. Si le résultat n'est pas vérifiable, le laisser inconnu. Conserver la provenance des corrections.

Piège réel : la 14e partie semblait montrer 16–16 sans verdict ; après agrandissement, **AB6 gagnait explicitement 16–12**. Seul ce dernier résultat a été retenu ; voir `ui-refresh-note.json`.

### Les outils Codex ne sont pas automatiquement disponibles ailleurs

L'ancien assistant utilisait `node_repl` et `@oai/sky`. `$L\observer.js` dépend de `sky`, `nodeRepl`, `abFS`, `abRoot` et `abCandidate`. **Ce fichier n'est pas autonome et ne se lance pas avec `node observer.js`.** Les globals de la conversation ne sont pas transférés.

Google doit réaliser la procédure avec ses propres outils d'accès au PC. Ne pas inventer des API Codex chez lui. Les skills et restrictions de cet ancien outil ne sont pas une installation portable du serveur.

## 11. Scripts et analyses disponibles

| Script dans `$W/scripts` | Rôle |
|---|---|
| `run_ab_server.py` | Campagnes WPF, référence AB3 et preuve UI requise |
| `summarize_ab_server.py` | Agrégat et résumé, filtre `--max-plies` |
| `diagnose_ab_draws.py` | États UPD avant MOV, répétitions et plafond |
| `compare_ab_decisions.py` | Décisions à profondeur fixe hors deadline |
| `benchmark_ab_variants.py` | Criblage initial de paramètres ; ne pas relancer sans demande |
| `tune_ab7_weights.py` | Réglage des poids ; ne pas relancer sans demande |
| `report_ab_followup.py` | Assemble la reprise 40 de cette étude précise |
| `setup_server.py` | Extraction du serveur et réglages de démo |

`scripts/server-runs/` contient aussi des outils historiques d'anciens moteurs. Ce ne sont pas nécessairement ceux du dernier lot AB.

Pour recalculer des rapports, employer **une copie de travail des données** :

```powershell
& $PY -B (Join-Path $W 'scripts\summarize_ab_server.py') <racine-des-parties> --max-plies 200
& $PY -B (Join-Path $W 'scripts\diagnose_ab_draws.py') <racine-des-parties> <runtime-contenant-les-cartes> --max-plies 200
```

Ces commandes écrivent des sorties : ne pas les lancer sur une archive immuable pour simplement la lire. Le résumeur déduplique par ID dans une campagne. **Ne pas lui passer tout le dossier global**, des checkpoints et plusieurs sélections incompatibles : un même ID peut désigner une autre condition. Le suivi 40 a volontairement assemblé des reprises des mêmes conditions, pas des expériences arbitraires.

Les `.gitattributes` des archives conservent les octets bruts (`* -text`). Si un document dérivé couvert est intentionnellement modifié, actualiser les `SHA256SUMS.txt` enfants puis parent. Ne pas modifier les logs pour les faire correspondre à une conclusion.

## 12. Cartographie des archives : où trouver chaque preuve

### `$W/docs/server-runs/2026-10-26`

- `long-200/` : **archive finale**, 16 parties, preuves, logs, traces, sélection, protocole, tests, diagnostics et SHA.
- `long-200-checkpoint-12/` : ancien instantané de 13 parties terminées / 12 verdicts confirmés, conservé ; ce n'est plus l'état courant.
- `followup-40/` : comparaison composée, 38 conditions / 49 tentatives ; `original/`, `replayed/`, contrôles et décisions.
- `ab7-weights/` : provenance du nouveau poids, statuts rédigés avant sa validation WPF.
- `SUMMARY.md` : rapport initial et liens vers les reprises ; garde des tableaux préliminaires.
- `excluded-200/` dans l'archive initiale, lorsqu'il est présent : vieux essais hors comparatif 40 (une partie 200 terminée, une tentative timeout avant pause), **pas** le nouveau lot de 16.

Anciens rapports du 22 octobre : `$W/docs/server-runs/2026-10-22/` et `2026-10-22-670a148/`. Machine, commit, règles et adversaires peuvent différer.

### `$P/.local/research/server-validation`

- `implementation-2026-10-26/` : tests initiaux ; `tuning/selection.json`, 180 parties simulées de criblage initial ; `server-inspection/` ; essais `live`/`live-v2`/`live-v3` ; erreurs XML, garde-fou et arrêt initial.
- `followup-40-2026-10-26/` : `decisions/`, `real-server/` et `real-server/controls-pass2/`.
- `ab7-weights-2026-10-26/` : entraînement/validation, cartes nouvelles, métriques et candidat.
- `long-200-2026-10-26/` (`$L`) : runtime et campagne finale de la nuit du 26 au 27, fichiers d'état, tests et scripts locaux. **Terminé, à ne pas relancer.**
- `RUN_PROMPT_ALPHA_BETA.md` et `preflight-2026-10-26/` : contexte historique, pas une file de tâches actuelle.

Les binaires du professeur restent locaux. Les publications locales sur la branche de résultats excluent EXE/DLL/ZIP/images ; elles contiennent logs, traces et preuves textuelles ou relevés visuels transcrits.

## 13. Recherche et inspiration historique : ne pas surpromettre

La justification actuelle détaille les sources, liens, nature et limites d'accès. Appuis principaux :

- Knuth/Moore 1975 et Schaeffer 1989 : Alpha-Bêta, historique, mémoire et interactions.
- Nipkow 2024 : formalisation de variantes ; pas preuve de notre code.
- Strass 2024 : support universitaire actuel sur les améliorations classiques.
- Moraes/Nascimento/Lelis 2022 : abstractions asymétriques d'actions ; adaptation AB3, pas reproduction de leurs moteurs.
- Ballard 1983 : bornes avec nœuds de chance ; inspiration AB6.
- Baraniuk 2025 : mémoire de licence, Expectiminimax/backgammon et expériences d'évaluation ; temps moyen 5,6 s, donc pas preuve de faisabilité dans notre budget.
- Buro 1995 : combinaison de caractéristiques ; nous n'avons pas reproduit sa régression.
- Chen et al. 2024 : évaluation par bases de finales dans un autre jeu ; résumé institutionnel vérifié, texte intégral non obtenu. Ni bases ni paramètres implémentés ici.
- Stockfish/Fishtest 2025 et documentation actuelle : mesure et validation de modifications, pas Elo transférable.

Les appuis récents ajoutés le 27 octobre ne doivent pas devenir une provenance initiale inventée. `0.97` vient de nos essais ; largeur 6 et table 50 000 ne sont pas prouvées optimales. « Réglé » signifie criblage limité, pas optimisation globale.

### Anciens projets

`$P/.local/research/previous-projects/` : lire `01_REPOSITORIES.md`, `02_PROJECT_ANALYSES.md`, `08_SOURCES.md` et `manifest.json`. Sources/rapports dans `sources/`, textes dans `extracted/`. Versions figées par commit ; anciens bots non exécutés pour reproduire leurs classements.

ZCSN/shawn-lab-ml (2022) inspire cibles et restriction combinatoire. Langorou (2020) inspire budget, issues pondérées et tournois de coefficients. Les classements annoncés restent ceux des auteurs, non reproduits. Certaines copies sont des doublons, certains simulateurs sont défectueux : ne pas importer leurs conclusions aveuglément. Aucun de nos AB0–AB8 n'est une reproduction fidèle, ce qui n'est plus demandé.

`$P/.local/research/scientific-literature/` : documents `01` à `14` et `references.bib`. **`11_RECOMMENDED_ARCHITECTURES.md` est une proposition historique**, antérieure aux implémentations et expériences. Les dernières justifications et sélections sont dans `$W/docs`.

## 14. Commits utiles et statut de publication

| Commit | Contenu |
|---|---|
| `d22df25` | Dernier code du lanceur utilisé, arrêt sur défaut de santé |
| `44a9390` | Comparatif 40 complété et diagnostic des nuls |
| `888b73f` | Checkpoint 200 à 12 verdicts |
| `9324fe9` | Lot final 16 parties, diagnostics et archives |
| `5f19d26` | Justifications des quatre configurations |
| `2cf4652` | Techniques du professeur, variantes et campagnes concernées |

Cette passation ajoute un commit documentaire. Les archives ont été contrôlées depuis `git archive` : 1 288 vérifications de hashes parent/enfant après le lot final, manifests actualisés lors du tableau des techniques.

Dernier push : refus 403. Les documents ultérieurs sont également **locaux**. Un assistant sur ce PC peut les lire sans être collaborateur GitHub ; ne pas donner un faux lien distant vers des fichiers non poussés.

## 15. Questions ouvertes, sans roadmap à exécuter automatiquement

- Présenter/défendre les quatre variantes avec des affirmations proportionnées aux preuves.
- Comparer directement AB2 et AB6 si Julian le demande, avec répétitions et rôles équilibrés.
- Étudier les cycles. **Un malus dépendant de l'historique peut invalider une TT qui ignore cet historique** : revoir clés, score et tests avant un tel changement.
- Étudier une optimisation récente précise, isolément puis en combinaison, si elle est choisie. Réseau appris et macro-actions temporelles ne sont pas implémentés dans nos variantes.
- Vérifier les règles officielles du tournoi si nécessaires ; le plafond 200 n'est pas confirmé comme règle officielle.
- Publier quand les droits seront accordés, avec l'identité de Julian et sans toucher main par défaut.

## 16. Comportement attendu au démarrage de Google

Lire les fichiers prioritaires, vérifier **en lecture seule** chemins, branches, interpréteur et processus. Confirmer brièvement : quatre variantes conservées, AB2/AB6 prioritaires, 16 parties finies, justifications disponibles et push bloqué. Signaler les différences réelles depuis ce snapshot, puis répondre à la prochaine consigne de Julian.

**Ne pas recommencer l'installation, les tests longs, l'entraînement ou une modification de bots simplement pour prendre connaissance du projet.** Ce dossier remplace le besoin de refaire toute la conversation, sans prétendre transférer la mémoire privée de l'ancien assistant.

