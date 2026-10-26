# AB0–AB8 — validation locale du 26 octobre 2026

**26/64 conditions terminées**, 17 résultats explicitement confirmés par WPF. 26 tentatives de parties conservées, sans compter les échecs de lancement.

Contrôle de fonctionnement : **0 Agent fault**, **0 occurrences de fallback**, **0 coups >1,8 s**, **0 coups >2 s**. Maximum imprimé : **1.503 s**. Secours internes faute d’itération terminée : **0**.

## Machine et versions

- CPU : Intel(R) Core(TM) i7-10875H CPU @ 2.30GHz ; 8 cœurs physiques, 16 processeurs logiques.
- Windows : Microsoft Windows 11 Famille, 10.0.26200, 64 bits.
- Python : Python 3.14.3 ; aucune dépendance Python ajoutée.
- .NET installé : 4.8.09221, Release 533509. Le serveur déclare .NET Framework 4.5 / CLR v4.0 dans sa configuration.

## Code et protocole

Base de développement : origin/main `352ebf4941dd04663473cc1a694cc74fde499cfe`. HEAD de la branche d’implémentation lors de la préparation du rapport : `76f7a9d7a431dce612efa8c10364aa63adce7e74`. Chaque `manifest.json` contient le commit exact au lancement de sa série. SHA-256 du moteur testé `agents/ab_variants.py` : `bed8077a39f16561f0cc666a007d19cfe92f2251559f33dbc7076f3415637ac8`.

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

| ab3 | 26 | 17 | 5 / 8 / 4 | 1.503 | 0.884 | 0 |

| ab4 | 4 | 2 | 0 / 2 / 0 | 1.503 | 1.026 | 0 |

| ab5 | 4 | 1 | 0 / 1 / 0 | 1.502 | 1.066 | 0 |

| ab6 | 2 | 1 | 1 / 0 / 0 | 1.501 | 1.486 | 0 |

| ab7 | 2 | 2 | 1 / 0 / 1 | 1.502 | 0.623 | 0 |

| ab8 | 2 | 2 | 0 / 0 / 2 | 1.501 | 0.519 | 0 |

Le protocole prévoit 64 conditions pour AB3 et huit pour chaque autre architecture. Ces taux ne forment pas un classement toutes paires. V/N/D utilisent uniquement les verdicts explicitement confirmés. Les moyennes agrègent les coups, pas les moyennes de parties à poids égal.

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

| [26](026-ab5-testmap2-40-1/result.json) | testmap2.xml | 40 | ab5 (vampires) puis ab3 (werewolves) | non confirmé | ? / ? | 1.501 / 1.356 | 1.502 / 1.250 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |


## Limites

Chaque variante est comparée à AB3, pas dans un tournoi complet. Les versions réglées peuvent avoir des largeurs différentes : cette campagne ne constitue pas une ablation isolant chaque optimisation. Le hasard du serveur n’est pas contrôlé par --seed. Les temps imprimés sont arrondis à trois décimales et ne remplacent pas une mesure de l’horloge interne du serveur.


## Problèmes rencontrés et traçabilité

Deux premières tentatives ont échoué dans le lanceur : l’alias XML `encoding="utf8"` était rejeté par .NET, puis le parseur rencontrait le chemin accentué. Le nouveau lanceur écrit `utf-8` et décode explicitement la configuration. Ces incidents précèdent les parties et ne sont pas des fautes des bots. Les fichiers sont conservés dans `startup-attempts/`.

La collecte d’interface a d’abord produit des captures vides ou incomplètes. Les essais concernés restent archivés ; les conditions rejouées ne sont comptées qu’une fois, avec préférence pour un verdict WPF explicite, puis la tentative la plus récente. Le serveur exprime un nul par « No winner / No looser » : ce cas est reconnu explicitement. Les captures textuelles finales sont dans `ui-evidence.json`. Une victoire n’est jamais inférée des effectifs ni d’une prédiction du simulateur.

Les valeurs temporelles viennent des lignes Turn et sont arrondies à trois décimales. Elles couvrent la décision côté client mais ne certifient pas l’horloge interne du serveur. Le modèle stochastique AB6 suit les sémantiques indépendantes par destination du simulateur ; les parties réussies ne prouvent pas une équivalence complète avec la DLL du professeur. Les générateurs sont bornés, y compris AB0 ; aucun moteur ne prétend explorer tous les MOV légaux.

## Publication

Le push a reçu HTTP 403 : `Permission to redaabid/AI-GAME-THEORY.git denied to Juliansaiani`. Reda doit accorder les droits de collaboration à ce compte. Le travail est conservé localement sur les branches dédiées ; ce rapport ne constitue pas une preuve de publication distante. Aucun commit n’utilise de trailer Co-authored-by. Aucun binaire, DLL ou archive du professeur n’est inclus dans les résultats. Les fichiers bruts JSON/log/config et les tests sont conservés.

Les empreintes de tous les fichiers de ce dossier sont dans `SHA256SUMS.txt`.
