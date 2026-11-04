# Julian — compléments AB2 du 28 octobre au 2 novembre 2026

**Publication dédiée du 4 novembre :** branche `julian-tests-alpha-beta-2026-11-04`,
[nouvelle entrée de lecture](../../../../README_JULIAN_ALPHA_BETA_2026-11-04.md).
Les dates de ce dossier restent celles des expériences et de leur compte rendu.

**Statut des configurations :** AB2 référence (plafond 24, largeur 6) et AB2
largeur 7 sont nos candidats prioritaires actuels, déjà testés en parties
complètes dans le simulateur. **AB2 TIE largeur 7 reste une expérimentation** :
ses tests ciblés sont positifs, mais sa campagne comparative complète est encore
en cours. Aucun de ces nouveaux réglages n'est encore validé sur le serveur WPF.
Le statut prioritaire n'établit pas une supériorité statistique de largeur 7 sur 6.
Un [point d'étape de la campagne TIE](checkpoint-tie-experimental-2-novembre/README.md)
archive le protocole et quatre parties terminées au moment de la préparation
de cette livraison ; il est explicitement marqué incomplet et non validé.

**Lecture de synthèse :** [démarche étape par étape et trois configurations de travail](SYNTHESE_DEMARCHE_ET_CONFIGURATIONS.md).
Julian fixe AB2 TIE en largeur 7 le 2 novembre ; les configurations exactes sont
dans [ab2_retained_profiles.json](../../../../scripts/ab2_retained_profiles.json).

**Ajout du 2 novembre :** [analyse des erreurs observées et correction ciblée](corrections-ciblees-2-novembre/README.md),
avec cas réels, essai initial négatif conservé, rejeux et 147 tests réussis.

Ce dossier complète les [expériences des 26–27 octobre](../2026-10-26_2026-10-27/README.md).
Un [audit de validation du 2 novembre](AUDIT_VALIDATION_2026-11-02.md) distingue
les preuves serveur, les essais en simulateur et les vérifications encore absentes.
Les matchs ont été joués du 28 au 31 octobre ; ce compte rendu a été établi le
2 novembre. L'historique reste conservé ; la synthèse distingue la sélection de
travail récente des résultats qui ne démontrent pas encore une supériorité générale.

## Origine de l'expérience

Selon les conseils du professeur rapportés par Julian, il fallait examiner les
allers-retours et la capacité du bot à aller chercher des humains ou adversaires
éloignés. L'expression rapportée « sauter des cases » était ambiguë : nous ne
disposons pas d'une confirmation de son sens exact. Nous avons distingué :
augmenter l'horizon Alpha-Bêta, valoriser la progression vers une cible, et
anticiper des déplacements intermédiaires par une politique scriptée.

Le professeur n'a pas prescrit nos valeurs de profondeur, largeurs, poids ou
longueurs de simulation. Ces réglages sont nos hypothèses expérimentales.
Les variantes de largeur, quiescence et pénalité de répétition ont été étudiées
en complément. Les coefficients nouveaux restent exploratoires, pas optimisés.

## Ce qui a été implémenté

Le moteur AB0–AB8 et les agents précédents restent inchangés. Les ajouts sont
dans les dossiers généraux, pas cachés dans le dossier personnel de résultats :

| Élément | Code / configuration |
|---|---|
| Profondeur, largeur, quiescence, répétition et guidage sur base AB2 | [agents/ab2_experiments.py](../../../../agents/ab2_experiments.py) |
| Anticipation de trajet par simulation scriptée | [agents/ab2_routes.py](../../../../agents/ab2_routes.py) |
| Profils paramétriques du premier lot, dont options reportées | [ab2_experiment_profiles.json](../../../../scripts/ab2_experiment_profiles.json) |
| Cinq configurations du lot éloigné et du tournoi | [ab2_distant_profiles.json](../../../../scripts/ab2_distant_profiles.json) |
| Comparaisons à une référence et cartes diagnostiques | [compare_ab2_experiments.py](../../../../scripts/compare_ab2_experiments.py) |
| Tournoi toutes paires, confirmation et reprise | [screen_ab2_round_robin.py](../../../../scripts/screen_ab2_round_robin.py) |
| Tests supplémentaires | [test_ab2_experiments.py](../../../../tests/test_ab2_experiments.py), [test_ab2_routes.py](../../../../tests/test_ab2_routes.py) |

Tous partagent Alpha-Bêta, approfondissement itératif, classement des coups,
mémoire des positions et le simulateur déterministe d'AB2 pendant la recherche.
Les parties utilisent, elles, les issues de combat échantillonnées du simulateur.
Ce lot n'introduit pas les distributions complètes d'AB6.

### Caractéristiques des cinq configurations du tournoi

| Nom dans les logs | Plafond | Largeur | Ajout |
|---|---:|---:|---|
| control | 24 | 6 | AB2 sans mécanisme supplémentaire |
| tactical1 | 24 | 6 | Quiescence : un demi-coup de capture, deux candidats maximum, sans stand-pat |
| width7 | 24 | 7 | Un candidat supplémentaire par position |
| guidance | 24 | 6 | Bonus de progression vers une cible accessible, poids 2000 |
| travel | 24 | 6 | Évaluation par simulation scriptée jusqu'à huit demi-coups alternés |

Le guidage choisit une cible humaine convertible ou un ennemi attaquable avec
une force suffisante ; sa cible est réévaluée à chaque décision. Les caches
dépendant de cette évaluation ou de l'historique sont réinitialisés entre décisions.

Le trajet simule chaque déplacement légal des deux camps à tour de rôle, puis
évalue la position obtenue. Il s'arrête lorsque les armées sont proches. Les
réponses adverses y suivent un script : ce n'est ni une exploration exhaustive
ni un vrai moteur de macro-actions temporelles. L'action envoyée reste un seul
tour légal, pas un trajet exécuté sans réévaluation. Les pas scriptés ne sont
pas ajoutés à la profondeur Alpha-Bêta rapportée.

La pénalité de répétition du premier lot concernait des plateaux complets avec
le même joueur au trait, pas une simple case revisitée. Elle n'invente pas de
règle de nul et ne détecte pas tous les cycles internes à l'arbre.

## Cartes et paramètres communs

Les cartes diagnostiques sont écrites par Python au format XML du projet,
via `mapgen.write_map`. Map Generator du professeur n'a pas été utilisé.
Le chargeur et le simulateur Python acceptent ces fichiers ; ces nouvelles
cartes n'ont pas été vérifiées sur le serveur WPF.

- `thetrap.xml` et `testmap2.xml` : cartes existantes utilisées dans le premier lot.
- `distant-recruitment` : 5 × 25, armées de 8 aux extrémités, humains disposés
  symétriquement, dont un groupe central ; premier contrôle recrutement/progression.
- `distant-pursuit` : 5 × 25, vampires 12 contre loups-garous 8, sans humains ;
  carte volontairement asymétrique, évaluée dans les deux rôles.
- `contact` : 5 × 7, deux armées de 8 et deux groupes humains de 3, utilisée au tournoi.
- Confirmation : deux nouvelles cartes `medium`, générées symétriquement avec
  les graines de carte 20054231 et 20054232. Elles ne sont pas utilisées pour
  sélectionner les finalistes. Aucun coefficient n'est réglé sur ces cartes.

Chaque carte exacte est archivée dans le sous-dossier `maps` de sa campagne.
Budget : 1,5 s/décision ; plafond : 200 demi-coups par partie. La limite du cours
rapportée est 2 s/décision ; 200 demi-coups est notre protocole local, pas une
confirmation indépendante des modalités du tournoi du cours.

Une graine de carte fixe une disposition. Une graine de combat initialise le
générateur des issues aléatoires ; elle ne garantit pas des combats identiques
si les agents choisissent des actions différentes.

## Les trois campagnes, dans l'ordre

### 1. Paramètres sur les cartes existantes — 16 parties

[Résultats bruts et protocole](resultats/01-parametres-28-octobre/),
[résumé automatique](resultats/01-parametres-28-octobre/SUMMARY.md).

| Challenger | Référence | V / N / D |
|---|---|---|
| Profondeur 24, largeur 6 | AB2 plafond 8, largeur 6 | 2 / 2 / 0 |
| Profondeur 24, largeur 8 | Profondeur 24, largeur 6 | 0 / 2 / 2 |
| Profondeur 24 + quiescence | Profondeur 24, largeur 6 | 1 / 2 / 1 |
| Profondeur 24 + pénalité de répétition | Profondeur 24, largeur 6 | 0 / 2 / 2 |

Deux cartes, deux rôles, une graine. Une partie de largeur 8 contient trois
temps anormaux : le lot ne compte donc pas seize parties temporellement
validées. Les [journaux Windows et l'audit](resultats/01-parametres-28-octobre/TIMING_AUDIT.md)
étayent fortement une suspension du PC. Aucun résultat ni temps brut n'a été
effacé. Cette condition n'a pas été rejouée dans ce lot ; ne pas conclure que
largeur 8 est trop lente ni certifier ses résultats sous la contrainte serveur.

Les plafonds 12, 16 et 64 ont aussi été préparés et vérifiés fonctionnellement,
mais n'ont pas tous fait l'objet de campagnes longues. Le plafond 64 est la
limite acceptée par le moteur, pas une profondeur atteinte revendiquée.

### 2. Cinq configurations sur les cartes éloignées — 16 parties

[Résultats et protocole](resultats/02-cartes-eloignees-29-octobre/).
Chaque ajout affronte `control`, plafond 24 et largeur 6, sur les deux cartes
éloignées avec les deux rôles. Tous obtiennent 2 V / 0 N / 2 D.
Les vampires gagnent les seize parties : ce test ne départage pas les variantes.

Un signal ponctuel motive la suite : en poursuite, le guidage côté fort obtient
un premier contact adjacent au demi-coup 23, contre environ 186–192 dans les
autres parties où un contact est observé. Le contact plus rapide ne démontre
pas une meilleure force de jeu ; des répétitions subsistent ensuite.

### 3. Tournoi toutes paires — 80 parties, puis confirmation — 16 parties

[Comparatif chiffré complet](resultats/03-tournoi-29-31-octobre/COMPARATIF_DETAILLE.md),
[statistiques recalculées](resultats/03-tournoi-29-31-octobre/DETAILED_STATS.json),
[protocole figé](resultats/03-tournoi-29-31-octobre/protocol.json).

Sélection : dix paires de configurations × deux cartes × quatre affectations
espèce/premier joueur × une graine de combat (5422901) = 80 parties.
Chaque configuration joue 32 parties contre les quatre autres.

| Configuration | V / N / D | Temps moyen / max (s) | Profondeur moyenne / max nominale |
|---|---|---|---|
| AB2 de référence | 8 / 16 / 8 | 1,405 / 1,577 | 17,97 / 24 |
| Quiescence | 8 / 16 / 8 | 1,424 / 1,560 | 15,27 / 24 |
| Largeur 7 | 8 / 16 / 8 | 1,422 / 1,569 | 15,98 / 24 |
| Guidage | 8 / 16 / 8 | 1,435 / 1,565 | 15,71 / 24 |
| Trajet scripté | 8 / 16 / 8 | 1,424 / 1,567 | 11,78 / 24 |

L'égalité s'explique précisément : les quarante parties `contact` sont nulles ;
dans les quarante parties `distant`, le premier joueur gagne toujours. Inverser
les rôles équilibre cet avantage, mais ne rend pas les cartes discriminantes.

Largeur 7 et guidage sont sélectionnés au critère secondaire prédéfini du nombre
de répétitions dans leurs parties : 4046 et 4376, contre 4822 pour le témoin et
4965 pour les autres. Ces nombres décrivent les parties, pas la responsabilité
exclusive d'un agent. Ce choix ne prouve pas qu'ils sont les deux meilleurs.

Confirmation : deux nouvelles cartes × deux graines de combat (5422911 et
5422912) × quatre affectations de rôles = 16 parties entre ces deux finalistes.

| Configuration | V / N / D | Temps moyen / max (s) | Profondeur moyenne / max nominale |
|---|---|---|---|
| Largeur 7 | 6 / 8 / 2 | 1,444 / 1,566 | 12,84 / 24 |
| Guidage | 2 / 8 / 6 | 1,451 / 1,573 | 12,29 / 24 |

Ce lot favorise largeur 7 contre guidage, sans démontrer une supériorité sur
AB2 largeur 6, quiescence ou trajet, absents de la confirmation. Le petit nombre
de cartes et de graines limite toute généralisation.

## Profondeur, temps et incidents : précautions de lecture

La profondeur est celle de la dernière itération terminée, en demi-coups.
Le plafond 24 n'est pas atteint systématiquement. Une itération nominale 24 peut
comporter des branches arrêtées avant (fin de partie, limite à 200, coupures ou
mémoire). Avec six ou sept candidats conservés par position et des combats
simplifiés, ce n'est pas une recherche exhaustive de tous les coups légaux.
Les chiffres ne prouvent pas une supériorité sur les anciens projets limités à 6.

Les moyennes temporelles sont pondérées par les décisions, non par les parties.
Les 96 parties valides du tournoi/confirmation comportent zéro défaut et zéro
temps supérieur à 1,8 s ; maximum 1,577 s. Cela valide ce lot en simulateur, pas
une garantie temps réel ni une validation réseau/serveur.

Windows est passé plusieurs fois en veille malgré la demande temporaire de
maintien éveillé. Le script s'est arrêté sur les parties aux temps contaminés.
Les trois tentatives concernées du tournoi sont conservées dans les sous-dossiers
`interrupted-*`, puis les mêmes conditions ont été rejouées sans modifier les
paramètres. Les parties terminées sont conservées et la reprise les ignore.
Les logs de lancement/erreurs restent disponibles dans [lancements/](lancements/).

Les cartes, protocoles, empreintes de code, traces et tentatives exclues sont
conservés. Les fichiers copiés sont identiques octet par octet aux originaux
locaux ; [PROVENANCE_COPIES.json](PROVENANCE_COPIES.json) décrit les copies et
`SHA256SUMS.txt` permet de les contrôler. Aucun ancien fichier brut n'est réécrit.

## Validation et justification

[Complément de justification et limites](JUSTIFICATIONS_COMPLEMENTAIRES.md).
Les 138 tests unitaires passent lors de l'ajout du trajet, dont 13 tests ciblant
ces expériences. Les contrôles courts sont archivés dans [validation/](validation/) ;
ils vérifient le fonctionnement, pas la force de jeu. Il n'y a pas eu de réglage
exhaustif ni d'optimisation validée des poids nouveaux.

Les parties tournent en Python local sans appel à un modèle. Les appels Codex
ont servi à préparer, lancer, vérifier l'avancement et interpréter les sorties.
Aucune nouvelle partie n'a été lancée pour rédiger cette mise à jour.

## État Git au moment de la rédaction

Branche de livraison actuelle : `julian-tests-alpha-beta-2026-11-04`, compte
GitHub `julian5422`. Première publication de ce dossier : le 2 novembre sur
`julian-tests-alpha-beta-2026-10-27`, commit `3061b57`. Avant cette première
publication, la branche distante était à
`c1bb52662bccb9a8dfdd670a5db64cc84207a965`, avec les archives des 26–27 octobre.
Cette mise à jour ajoute les nouveaux modules, scripts, tests et le dossier
documentaire du 28 octobre au 2 novembre. Les fichiers de code restent dans les
dossiers généraux et les données dans le dossier personnel daté. Les originaux
dans `.local/ab2-experiments/` sont préservés. `main` reste inchangée.
Le point d'étape TIE ne doit pas être lu comme un résultat final de sa campagne.
La nouvelle branche du 4 novembre reprend cet avancement avec une entrée datée
distincte ; les données des anciens tests sont conservées dans leurs archives.
