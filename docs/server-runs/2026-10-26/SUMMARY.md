> Mise à jour du 27 octobre : publication réussie sur GitHub, branche `server-runs`, avec le compte `julian5422`. Les mentions antérieures de refus 403 décrivent les essais sous un autre compte.

> Mise à jour du 27 octobre : [campagne complète à 200 coups — 16 verdicts confirmés](long-200/SUMMARY.md).

# AB0–AB8 — validation locale du 26 octobre 2026

> Mise à jour : les huit conditions sans verdict ont été rejouées, et six contrôles ont été ajoutés. Voir le [comparatif complété et le diagnostic des nuls](followup-40/SUMMARY.md). Le tableau ci-dessous conserve l'état préliminaire de la campagne.


**32/32 conditions terminées**, 24 résultats explicitement confirmés par WPF. 32 tentatives de parties conservées, sans compter les échecs de lancement.

Contrôle de fonctionnement : **0 Agent fault**, **0 occurrences de fallback**, **0 coups >1,8 s**, **0 coups >2 s**. Maximum imprimé : **1.506 s**. Secours internes faute d’itération terminée : **0**.

**Périmètre : uniquement les parties à 40 demi-coups.** Le lancement de la phase à 200 est suspendu sur instruction de l’utilisateur, pour comparer et sélectionner les variantes. Le lanceur avait déjà terminé une condition à 200 et tenté une seconde, arrêtée en timeout. Ces deux tentatives sont conservées dans `excluded-200/` et ne contribuent à aucun score ou temps du présent comparatif. Aucun autre match ne sera relancé automatiquement.

## Techniques évoquées par le professeur : ce que nous avons testé

Mise à jour du 27 octobre : récapitulatif des campagnes à 40 et à 200 coups.

Les campagnes ont mis à l'épreuve les techniques discutées avec le professeur autour d'Alpha-Bêta, ainsi que des compléments de la littérature :

| Technique | Variantes où elle est active | Campagne serveur |
|---|---|---|
| **Move ordering** : ordre d'exploration des coups | AB1 à AB8 ; historique à partir d'AB2 | 40 coups ; AB2, AB3, AB6 et nouvel AB7 à 200 |
| **Iterative deepening** : dernière profondeur entièrement terminée conservée | AB1 à AB8 | 40 coups ; AB2, AB3, AB6 et nouvel AB7 à 200 |
| **Mémoire des positions** : valeurs et bornes en table de transposition | AB2 à AB8 | 40 coups ; AB2, AB3, AB6 et nouvel AB7 à 200 |
| **Mouvements coordonnés par scripts** : propositions de tours complets | AB3, AB4, AB5, AB6 et AB7 | 40 coups ; AB3, AB6 et nouvel AB7 à 200 |
| **Fenêtres étroites / aspiration** : PVS et reprises | AB4 | 40 coups |
| **Prolongations tactiques** : quiescence bornée | AB5 | 40 coups |
| **Traitement du hasard** : distributions et bornes de chance | AB6 | 40 et 200 coups |
| **Réglage de l'évaluation** | AB7 | Ancien profil à 40 ; nouveau candidat à 200, après réglage en simulation |
| **MTD(f)** : pilote à fenêtres nulles et mémoire | AB8 | 40 coups |

Les scripts produisent le mouvement du tour courant : **ce ne sont pas des macro-actions sur plusieurs tours**. AB2 possède déjà des candidats coordonnés ; AB3 enrichit cette base. AB8 dérive d'AB2 et n'inclut pas cet enrichissement par scripts.

Les campagnes comparent des configurations combinées : elles ne démontrent pas le gain isolé de chaque technique. AB4, AB5 et AB8 ont été testées à 40 coups mais ne sont pas retenues dans la sélection finale AB2/AB3/AB6/AB7. Le nouvel AB7 est distinct de l'ancien profil testé à 40 coups.

## Machine et versions

- CPU : Intel(R) Core(TM) i7-10875H CPU @ 2.30GHz ; 8 cœurs physiques, 16 processeurs logiques.
- Windows : Microsoft Windows 11 Famille, 10.0.26200, 64 bits.
- Python : Python 3.14.3 ; aucune dépendance Python ajoutée.
- .NET installé : 4.8.09221, Release 533509. Le serveur déclare .NET Framework 4.5 / CLR v4.0 dans sa configuration.

## Code et protocole

Base de développement : origin/main `352ebf4941dd04663473cc1a694cc74fde499cfe`. HEAD de la branche d’implémentation lors de la préparation du rapport : `b63e908fca2e9820af46f5ee2baa355b6d6dca59`. Chaque `manifest.json` contient le commit exact au lancement de sa série. SHA-256 du moteur testé `agents/ab_variants.py` : `bed8077a39f16561f0cc666a007d19cfe92f2251559f33dbc7076f3415637ac8`.

Les agents existants et leurs modules partagés sont inchangés. AB0–AB8 sont de vrais modes du nouveau moteur modulaire, documentés dans `docs/AB_VARIANTS.md` : AB0 profondeur fixe ; AB1 approfondissement itératif/ordre ; AB2 TT/historique ; AB3 sélection coordonnée/diversité ; AB4 PVS/aspiration ; AB5 quiescence bornée ; AB6 issues aléatoires complètes/bornes de chance ; AB7 poids réglés ; AB8 MTD(f).

Chaque variante est opposée à AB3 : deux cartes du cours, MaxPlays 40 puis 200, deux ordres de connexion, soit 64 conditions. Ce protocole remplace les anciens matchs contre MCTS/OEP/baseline. Les espèces réellement reçues sont relevées dans les logs ; l’ordre seul n’est pas présenté comme une garantie de rôle.

Serveur WPF lancé localement : PlayersCount=2, ServerIP=127.0.0.1, ServerPort=5555, MaxPlayDuration=00:00:02, MaxGameDuration=00:10:00, AutoRestart=False, DebugMode=True. Map est un chemin absolu vérifié. MaxPlays est égal à --max-plies pour chaque partie. Les bots utilisent --move-time 1.5, --rules-profile server-v3.2.1 et --seed 42. Cette graine ne contrôle pas le hasard interne du serveur. Les commandes exactes et les empreintes des cartes figurent dans les manifests ; les configurations effectives sont conservées. Les exécutables/DLL déclarent FileVersion=1.0.0.0 ; leurs empreintes figurent dans [runtime-versions.json](runtime-versions.json). Le libellé Python server-v3.2.1 ne prouve pas à lui seul une équivalence des règles avec ces binaires.

## Réglage séparé des essais finaux

180 parties simulées de réglage : pour chaque architecture, trois candidats évalués sur deux cartes générées et les deux espèces (12 parties), puis les deux finalistes sur deux nouvelles cartes et les deux espèces (8 parties). Graines d’entraînement 11001/11002 ; validation 22001/22002. Budgets de 0,04 s / 16 demi-coups puis 0,08 s / 24 demi-coups, contre l’Alpha-Bêta existant. Sélection : fautes, retards, score, secours internes, temps moyen. Les cartes du cours sont réservées au test final. Tous les candidats et résultats sont dans [selection.json](tuning/selection.json).

**Limite du réglage :** ce criblage est réduit et utilise un budget bien plus court que les 1,5 s des parties WPF. Il constitue une première recherche de paramètres, pas une optimisation exhaustive ni une garantie de meilleurs paramètres au budget final. Les poids et la largeur varient ensemble dans les candidats AB7 ; leur effet individuel n’est donc pas isolé. Les poids initiaux ont été retenus pour AB7 : aucun gain d’évaluation optimisée n’est démontré ; AB7 peut se comporter comme AB3.

| Architecture | Configuration retenue |
|---|---|
| ab0 | `ab0:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000` |
| ab1 | `ab1:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000` |
| ab2 | `ab2:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000` |
| ab3 | `ab3:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000` |
| ab4 | `ab4:width=10,depth=2,max_depth=8,extra=4,tt_size=50000,qdepth=2,qwidth=3,aspiration=50000` |
| ab5 | `ab5:width=10,depth=2,max_depth=8,extra=4,tt_size=50000,qdepth=2,qwidth=3,aspiration=50000` |
| ab6 | `ab6:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000` |
| ab7 | `ab7:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000,weights={'material': 1.0, 'humans': 0.8, 'discount': 0.9, 'threat': 0.7, 'groups': 0.1}` |
| ab8 | `ab8:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000` |

## Tests automatisés

**125 tests réussis en 10,876 s** avec `python -B -m unittest discover -s tests -v`. [Journal intégral](unittest-125.log). Les 115 tests existants sont conservés ; dix tests couvrent les variantes : minimax indépendant sur petit arbre, égalité TT/PVS/MTD à profondeur fixe, délais, quiescence, contexte de cache, distributions et arrivées groupées.

## Résultats par architecture

| Architecture | Parties | Confirmées | V / N / D | Max (s) | Moyenne pondérée (s) | Sessions anormales |
|---|---:|---:|---|---:|---:|---:|
| ab0 | 4 | 2 | 0 / 1 / 1 | 0.007 | 0.002 | 0 |
| ab1 | 4 | 3 | 1 / 2 / 0 | 1.502 | 0.885 | 0 |
| ab2 | 4 | 4 | 1 / 2 / 1 | 1.502 | 0.778 | 0 |
| ab3 | 32 | 24 | 5 / 15 / 4 | 1.506 | 0.959 | 0 |
| ab4 | 4 | 2 | 0 / 2 / 0 | 1.503 | 1.026 | 0 |
| ab5 | 4 | 2 | 0 / 2 / 0 | 1.502 | 1.066 | 0 |
| ab6 | 4 | 3 | 1 / 2 / 0 | 1.502 | 1.432 | 0 |
| ab7 | 4 | 4 | 1 / 2 / 1 | 1.502 | 0.952 | 0 |
| ab8 | 4 | 4 | 0 / 2 / 2 | 1.501 | 0.774 | 0 |

Le protocole prévoit 64 conditions pour AB3 et huit pour chaque autre architecture. Ces taux ne forment pas un classement toutes paires. V/N/D utilisent uniquement les verdicts explicitement confirmés. Les moyennes agrègent les coups, pas les moyennes de parties à poids égal.

## Tri provisoire avant toute reprise à 200 coups

**À conserver : AB1, AB2, AB3 et AB6.** AB3 reste le témoin ; AB1 et AB6 ont chacun une victoire confirmée, aucune défaite confirmée et un verdict manquant. AB2 a une victoire et une défaite, avec une moyenne de décision de 0,778 s. AB6 coûte davantage : 1,432 s en moyenne. Ces observations ne permettent pas de désigner une gagnante entre ces agents.

**À déprioriser dans sa configuration actuelle : AB8.** Deux défaites confirmées sur thetrap dans les deux ordres, puis deux nuls sur testmap2 ; aucune victoire. Cela justifie un tri pratique, pas une condamnation scientifique de MTD(f) sur quatre parties.

**À fusionner avec le témoin pour éviter un doublon : le profil sélectionné AB7.** Les poids et paramètres retenus sont ceux d’AB3 ; aucune amélioration des poids n’est démontrée. Leurs différences de résultat ne prouvent pas un gain de réglage : le hasard du serveur et les différences de durée affectent les recherches interrompues.

**AB0 reste un témoin technique**, avec sa profondeur fixe retenue de 1. Une défaite, un nul et deux verdicts manquants : ce profil ne constitue pas un candidat prioritaire au bot final.

**AB4 et AB5 restent non classées.** Chacune a deux nuls confirmés et deux verdicts manquants sur thetrap. Leurs moyennes de 1,026 s et 1,066 s ne suffisent pas à conclure à une faiblesse : elles recherchent aussi des arbres différents. Il faut confirmer leurs résultats avant de les éliminer pour leur force de jeu.

Chaque challenger n’a que quatre parties, dont deux sur une carte où tous les verdicts confirmés sont nuls. Les huit verdicts manquants concernent les conditions 1, 4, 7, 8, 9, 10, 11 et 17. Aucun match supplémentaire n’a été lancé pour les résoudre après la demande d’arrêt.

## Matchs nuls : répartition par carte et plafond

| Carte | MaxPlays | Conditions terminées | Victoires confirmées | Nuls confirmés | Verdicts manquants |
|---|---:|---:|---:|---:|---:|
| testmap2.xml | 40 | 16 | 0 | 15 | 1 |
| thetrap.xml | 40 | 16 | 9 | 0 | 7 |

Les premiers nuls confirmés se concentrent sur testmap2 à 40 demi-coups (20 décisions par bot), avec 16 unités contre 16. Le serveur affiche explicitement « No winner / No looser ». Cette carte mesure 29 × 15, contre 10 × 5 pour thetrap ; chaque camp commence avec 10 unités et peut recruter symétriquement des groupes de 4 et 2 humains. Les déplacements examinés ne montrent pas un arrêt général des bots. Un plafond trop court est une hypothèse à confronter aux résultats à 200 demi-coups ; aucune fréquence « normale » de nuls n’est établie sans campagne de référence. Les verdicts manquants ne sont jamais assimilés à des nuls.

Les [diagnostics de traces](draw-diagnostics.json) reconstruisent les positions à partir des UPD du vrai serveur. Sur les 16 parties testmap2 à 40 coups, le plafond est atteint et aucune répétition exacte de position avec le même joueur au trait n’est observée. Cela ne prouve pas qu’un nul disparaîtrait avec 200 coups.

## Détail de chaque partie

| Partie | Carte | MaxPlays | Ordre (espèces) | Vainqueur WPF | Effectifs (ordre) | Max / moyenne A (s) | Max / moyenne B (s) | >1,8 s A/B | >2 s A/B | Faults A/B | Fallback A/B | Secours internes A/B |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|
| [1](001-ab0-thetrap-40-0/result.json) | thetrap.xml | 40 | ab3 (vampires) puis ab0 (werewolves) | non confirmé | ? / ? | 1.502 / 0.714 | 0.003 / 0.002 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [2](002-ab0-thetrap-40-1/result.json) | thetrap.xml | 40 | ab0 (vampires) puis ab3 (werewolves) | ab3 | 8 / 9 | 0.007 / 0.002 | 1.501 / 0.618 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [3](003-ab1-thetrap-40-0/result.json) | thetrap.xml | 40 | ab3 (vampires) puis ab1 (werewolves) | ab1 | 0 / 4 | 1.502 / 0.699 | 1.501 / 0.626 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [4](004-ab1-thetrap-40-1/result.json) | thetrap.xml | 40 | ab1 (vampires) puis ab3 (werewolves) | non confirmé | ? / ? | 1.501 / 0.631 | 1.501 / 0.638 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [5](005-ab2-thetrap-40-0/result.json) | thetrap.xml | 40 | ab3 (vampires) puis ab2 (werewolves) | ab2 | 8 / 9 | 1.502 / 0.630 | 1.502 / 0.454 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [6](006-ab2-thetrap-40-1/result.json) | thetrap.xml | 40 | ab2 (vampires) puis ab3 (werewolves) | ab3 | 8 / 9 | 1.501 / 0.532 | 1.501 / 0.567 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [7](007-ab4-thetrap-40-0/result.json) | thetrap.xml | 40 | ab3 (vampires) puis ab4 (werewolves) | non confirmé | 8 / 9 | 1.502 / 0.565 | 1.501 / 0.662 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [8](008-ab4-thetrap-40-1/result.json) | thetrap.xml | 40 | ab4 (vampires) puis ab3 (werewolves) | non confirmé | 8 / 9 | 1.501 / 0.767 | 1.501 / 0.605 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [9](009-ab5-thetrap-40-0/result.json) | thetrap.xml | 40 | ab3 (vampires) puis ab5 (werewolves) | non confirmé | 8 / 9 | 1.501 / 0.560 | 1.502 / 0.746 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [10](010-ab5-thetrap-40-1/result.json) | thetrap.xml | 40 | ab5 (vampires) puis ab3 (werewolves) | non confirmé | 8 / 9 | 1.501 / 0.841 | 1.501 / 0.580 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [11](011-ab6-thetrap-40-0/result.json) | thetrap.xml | 40 | ab3 (vampires) puis ab6 (werewolves) | non confirmé | 8 / 9 | 1.502 / 0.725 | 1.501 / 1.500 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [12](012-ab6-thetrap-40-1/result.json) | thetrap.xml | 40 | ab6 (vampires) puis ab3 (werewolves) | ab6 | 3 / 0 | 1.501 / 1.473 | 1.501 / 0.727 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [13](013-ab7-thetrap-40-0/result.json) | thetrap.xml | 40 | ab3 (vampires) puis ab7 (werewolves) | ab7 | 8 / 9 | 1.501 / 0.640 | 1.502 / 0.614 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [14](014-ab7-thetrap-40-1/result.json) | thetrap.xml | 40 | ab7 (vampires) puis ab3 (werewolves) | ab3 | 8 / 9 | 1.501 / 0.633 | 1.502 / 0.612 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [15](015-ab8-thetrap-40-0/result.json) | thetrap.xml | 40 | ab3 (vampires) puis ab8 (werewolves) | ab3 | 4 / 0 | 1.502 / 0.631 | 1.501 / 0.480 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [16](016-ab8-thetrap-40-1/result.json) | thetrap.xml | 40 | ab8 (vampires) puis ab3 (werewolves) | ab3 | 8 / 9 | 1.501 / 0.556 | 1.502 / 0.599 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [17](017-ab0-testmap2-40-0/result.json) | testmap2.xml | 40 | ab3 (vampires) puis ab0 (werewolves) | non confirmé | ? / ? | 1.501 / 1.298 | 0.004 / 0.003 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [18](018-ab0-testmap2-40-1/result.json) | testmap2.xml | 40 | ab0 (vampires) puis ab3 (werewolves) | draw | 16 / 16 | 0.005 / 0.003 | 1.503 / 1.264 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [19](019-ab1-testmap2-40-0/result.json) | testmap2.xml | 40 | ab3 (vampires) puis ab1 (werewolves) | draw | 16 / 16 | 1.501 / 1.301 | 1.502 / 1.122 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [20](020-ab1-testmap2-40-1/result.json) | testmap2.xml | 40 | ab1 (vampires) puis ab3 (werewolves) | draw | 16 / 16 | 1.502 / 1.133 | 1.501 / 1.254 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [21](021-ab2-testmap2-40-0/result.json) | testmap2.xml | 40 | ab3 (vampires) puis ab2 (werewolves) | draw | 16 / 16 | 1.502 / 1.299 | 1.502 / 1.060 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [22](022-ab2-testmap2-40-1/result.json) | testmap2.xml | 40 | ab2 (vampires) puis ab3 (werewolves) | draw | 16 / 16 | 1.501 / 1.064 | 1.502 / 1.243 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [23](023-ab4-testmap2-40-0/result.json) | testmap2.xml | 40 | ab3 (vampires) puis ab4 (werewolves) | draw | 16 / 16 | 1.502 / 1.310 | 1.503 / 1.317 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [24](024-ab4-testmap2-40-1/result.json) | testmap2.xml | 40 | ab4 (vampires) puis ab3 (werewolves) | draw | 16 / 16 | 1.503 / 1.356 | 1.502 / 1.258 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [25](025-ab5-testmap2-40-0/result.json) | testmap2.xml | 40 | ab3 (vampires) puis ab5 (werewolves) | draw | 16 / 16 | 1.502 / 1.310 | 1.502 / 1.320 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [26](026-ab5-testmap2-40-1/result.json) | testmap2.xml | 40 | ab5 (vampires) puis ab3 (werewolves) | draw | 16 / 16 | 1.501 / 1.356 | 1.502 / 1.250 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [27](027-ab6-testmap2-40-0/result.json) | testmap2.xml | 40 | ab3 (vampires) puis ab6 (werewolves) | draw | 16 / 16 | 1.502 / 1.301 | 1.502 / 1.363 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [28](028-ab6-testmap2-40-1/result.json) | testmap2.xml | 40 | ab6 (vampires) puis ab3 (werewolves) | draw | 16 / 16 | 1.502 / 1.405 | 1.502 / 1.247 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [29](029-ab7-testmap2-40-0/result.json) | testmap2.xml | 40 | ab3 (vampires) puis ab7 (werewolves) | draw | 16 / 16 | 1.502 / 1.300 | 1.502 / 1.265 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [30](030-ab7-testmap2-40-1/result.json) | testmap2.xml | 40 | ab7 (vampires) puis ab3 (werewolves) | draw | 16 / 16 | 1.501 / 1.298 | 1.502 / 1.263 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [31](031-ab8-testmap2-40-0/result.json) | testmap2.xml | 40 | ab3 (vampires) puis ab8 (werewolves) | draw | 16 / 16 | 1.506 / 1.293 | 1.501 / 1.004 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| [32](032-ab8-testmap2-40-1/result.json) | testmap2.xml | 40 | ab8 (vampires) puis ab3 (werewolves) | draw | 16 / 16 | 1.501 / 1.044 | 1.502 / 1.235 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |


## Limites

Chaque variante est comparée à AB3, pas dans un tournoi complet. Les versions réglées peuvent avoir des largeurs différentes : cette campagne ne constitue pas une ablation isolant chaque optimisation. Le hasard du serveur n’est pas contrôlé par --seed. Les temps imprimés sont arrondis à trois décimales et ne remplacent pas une mesure de l’horloge interne du serveur.


## Problèmes rencontrés et traçabilité

Deux premières tentatives ont échoué dans le lanceur : l’alias XML `encoding="utf8"` était rejeté par .NET, puis le parseur rencontrait le chemin accentué. Le nouveau lanceur écrit `utf-8` et décode explicitement la configuration. Ces incidents précèdent les parties et ne sont pas des fautes des bots. Les fichiers sont conservés dans `startup-attempts/`.

La collecte d’interface a d’abord produit des captures vides ou incomplètes. Les essais concernés restent archivés ; les conditions rejouées ne sont comptées qu’une fois, avec préférence pour un verdict WPF explicite, puis la tentative la plus récente. Le serveur exprime un nul par « No winner / No looser » : ce cas est reconnu explicitement. Les captures textuelles finales sont dans `ui-evidence.json`. Une victoire n’est jamais inférée des effectifs ni d’une prédiction du simulateur.

Les valeurs temporelles viennent des lignes Turn et sont arrondies à trois décimales. Elles couvrent la décision côté client mais ne certifient pas l’horloge interne du serveur. Le modèle stochastique AB6 suit les sémantiques indépendantes par destination du simulateur ; les parties réussies ne prouvent pas une équivalence complète avec la DLL du professeur. Les générateurs sont bornés, y compris AB0 ; aucun moteur ne prétend explorer tous les MOV légaux.

## Publication

Le push a reçu HTTP 403 : `Permission to redaabid/AI-GAME-THEORY.git denied to Juliansaiani`. Reda doit accorder les droits de collaboration à ce compte. Le travail est conservé localement sur les branches dédiées ; ce rapport ne constitue pas une preuve de publication distante. Aucun commit n’utilise de trailer Co-authored-by. Aucun binaire, DLL ou archive du professeur n’est inclus dans les résultats. Les fichiers bruts JSON/log/config et les tests sont conservés.

Les empreintes de tous les fichiers de ce dossier sont dans `SHA256SUMS.txt`.

## Nouveau réglage AB7 après le comparatif à 40 coups

Le profil AB7 du comparatif ci-dessus utilisait les mêmes poids que AB3. Une recherche ultérieure a testé dix réglages de poids avec la recherche AB3 figée : 60 parties simulées d'entraînement, puis 24 de validation sur d'autres cartes générées. Le candidat discount=0,97 (au lieu de 0,90) obtient 2 victoires, 6 nuls et 0 défaite sur ses huit parties de validation ; le témoin AB3 obtient 1 victoire, 6 nuls et 1 défaite. Un contrôle à profondeur fixe trouve une décision différente sur 12 positions supplémentaires. Ce candidat justifie de conserver AB7 pour une future validation : les anciens résultats WPF ne lui sont pas attribués. Le gain reste exploratoire, avec un budget de 0,2 seconde et un petit échantillon.

[Résumé du réglage](ab7-weights/SUMMARY.md) — [profil exact](ab7-weights/ab7-candidate.json) — [données](ab7-weights/results.json). Aucun serveur WPF ni essai à 200 coups n'a été relancé.
