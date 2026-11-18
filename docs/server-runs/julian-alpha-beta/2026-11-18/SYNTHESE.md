# Synthèse des travaux depuis le dernier push

## Point de départ et demandes du professeur

On conserve les AB2 de référence, largeur 6 et largeur 7. Les anciennes campagnes de profondeur, largeur, guidage et trajet simulé ne sont pas recomptées ici. Elles restent dans les archives précédentes.

Après la réunion du 5 novembre : vérifier les oscillations, recruter les humains accessibles sans exposer inutilement l'armée, gérer les combats aléatoires et le camp qui attaque, comparer aux MCTS de Reda, puis vérifier le temps sur les machines H208. Le rapport doit relier chaque choix à une expérience et au code.

« Sauter des cases » reste une formulation ambiguë. Les règles écrites imposent des déplacements adjacents : aucune téléportation n'a été ajoutée. L'anticipation sur plusieurs tours est distincte du déplacement légal.

## Ce qu'on a trouvé et changé

| Étape | Constat / test | Modification | Ce qu'on retient |
|---|---|---|---|
| Audit de recherche | Six positions synthétiques, caches froid/chaud et désactivé, comparaison à une recherche de référence sur les mêmes candidats | Pas de changement arbitraire du cache | 72 contrôles cohérents ; cela n'exclut pas tous les bugs ni les actions manquantes |
| Combats | La transition déterministe simplifiait des combats pourtant incertains | AB2-Risk développe leurs issues probabilisées ; les combats garantis conservent le chemin rapide | Réduit cette approximation ; davantage de calculs, pas une interdiction de prendre un risque |
| Départage des égalités | Plusieurs choix ont le même score, y compris quand certains stagnent | AB2-RiskTie combine le traitement du hasard et le départage existant : score statique, répétition récente, classement stratégique | 8 victoires sur 8 sur thetrap, mais résultats moins favorables ailleurs |
| Groupes et humains | Un petit groupe pouvait attirer les propositions alors qu'un autre pouvait recruter utilement | AB2-Goals réserve au plus deux des sept places à des propositions de groupes capables, seulement dans cette situation mixte | La version trop générale a été abandonnée après un contre-exemple ; la version conditionnelle reste |
| Fin de partie | Une armée perdante pouvait patienter jusqu'à perdre à la limite de coups | AB2-Endgame rapproche l'évaluation du résultat au plafond dans les 40 derniers demi-coups sans humains ; départage orienté vers une cible quand on est derrière | Victoire WPF confirmée, mais encore des défaites en simulation ; paramètres expérimentaux |
| Réponses adverses absentes | Des coups réellement joués par V6 se classaient entre les rangs 9 et 31, hors des sept coups examinés | AB2-Replies examine jusqu'à 32 candidats à la première réponse adverse, sept ailleurs ; caches séparés pour les deux régimes | Piste actuelle ; amélioration sur une carte diagnostiquée, confirmation indépendante partagée |

Un meilleur score de recherche reste prioritaire dans les départages. La correction n'est pas un simple malus global contre toute répétition. On conserve les anciennes variantes pour les comparaisons.

## Parties complètes en simulation

**52 nouvelles parties contre MCTS V6**, avec inversion des camps et du premier joueur. Budget de réflexion 1,5 s, limite locale 200 demi-coups. Zéro faute, timeout ou décision mesurée au-dessus de 1,8 s dans ces rapports, pour les deux agents. Temps ci-dessous : décisions AB2, moyenne pondérée par le nombre de coups.

| Campagne / configuration | Carte | V/N/D | Temps moyen (s) | Temps max (s) |
|---|---|---|---|---|
| ab2exp-thetrap-1.5-2026111201 | thetrap | 2/0/2 | 1.391 | 1.505 |
| ab2risktie-thetrap-1.5-2026111201 | thetrap | 4/0/0 | 1.416 | 1.509 |
| ab2risktie-thetrap-1.5-2026111202 | thetrap | 4/0/0 | 1.483 | 1.522 |
| ab2tie-thetrap-1.5-2026111201 | thetrap | 2/0/2 | 1.494 | 1.500 |
| endgame-policy-2026-11-17/matches | holdout-medium-20261113 | 2/0/2 | 1.500 | 1.500 |
| endgame-policy-2026-11-17/matches | unseen-medium-20261117 | 0/2/2 | 1.439 | 1.514 |
| goal-coverage-2026-11-13/matches | holdout-medium-20261113 | 2/1/1 | 1.448 | 1.517 |
| goal-coverage-2026-11-13/matches | testmap2 | 0/4/0 | 1.430 | 1.514 |
| reply-coverage-2026-11-17/holdout | holdout-medium-20261119 | 2/0/2 | 1.470 | 1.529 |
| reply-coverage-2026-11-17/matches | holdout-medium-20261113 | 1/1/2 | 1.456 | 1.502 |
| reply-coverage-2026-11-17/matches | unseen-medium-20261117 | 4/0/0 | 1.468 | 1.522 |
| validation-other-maps-2026-11-13 | holdout-medium-20261113 | 1/1/2 | 1.441 | 1.502 |
| validation-other-maps-2026-11-13 | testmap2 | 0/4/0 | 1.431 | 1.501 |

Les rapports JSON contiennent les paramètres, graines, rôles, effectifs finaux et temps par décision. Les traces permettent de retrouver les positions et actions. Les graines voisines des deux campagnes thetrap ne représentent pas huit tirages entièrement indépendants.

Pour AB2-Replies : 5 V / 1 N / 2 D sur les cartes de développement, puis **2 V / 0 N / 2 D sur une nouvelle carte de confirmation**. La carte sur laquelle on obtient 4/4 avait servi au diagnostic : ce n'est pas un test aveugle. La graine `20261119` est un identifiant ; cette confirmation a eu lieu le 17 novembre.

## Serveur Windows réel

| Session | État vérifié | Temps AB2 moyen / max | Verdict |
|---|---|---|---|
| AB2-Endgame / V6, thetrap | Partie terminée, aucun fault/fallback/Traceback | 1,502 / 1,502 s | Victoire AB2, effectifs 3–0, relevée dans WPF |
| AB2-Replies, premier essai | Session perturbée par une mise en veille Windows ; temps MCTS de 734,45 s | Hors lot valide | Exclue des conclusions de performance, conservée dans l'archive |
| AB2-Replies, nouvel essai protégé | 200 demi-coups, 100 décisions chacun, codes de sortie 0/0, aucune faute | 1,407 / 1,515 s | Verdict graphique non relevé ; aucune victoire annoncée |

Les logs correspondants sont dans les sous-dossiers `wpf-run-2026-11-17` et `wpf-safe-run-2026-11-17` des expériences Endgame / Reply. Le serveur et les bibliothèques du cours restent locaux. Un chemin Windows trop long empêchait le démarrage : une copie locale à chemin court a permis le test.

## Autres vérifications conservées

- 16 continuations synthétiques très courtes de fin de partie : comparaison initiale Risk / référence, distincte des 52 parties complètes.
- Rejeux ciblés, version Goals rejetée, traces d'actions adverses manquantes, contrôles de transitions et essais de réglage conservés dans les expériences.
- Ancien checkpoint TIE du 2 novembre ajouté pour mémoire : 13/16 parties, campagne incomplète, distincte des nouveaux résultats.
- Intégration du 18 novembre : **396 tests unitaires passent**. Les cinq classes intégrées ont le même AST algorithmique que les prototypes testés ; seuls les imports et emplacements ont été adaptés.
- Le nouveau lanceur comparatif a été vérifié sur deux mini-parties de quatre demi-coups avec reprise du checkpoint. C'est un contrôle de fonctionnement, pas un résultat de force de jeu.

## Ce qui reste à vérifier

H208 n'a pas été testé : les temps observés sur ce PC ne garantissent pas ceux du tournoi. Il faut encore comparer sur davantage de cartes indépendantes et contre les autres versions MCTS, relever le dernier verdict WPF et confirmer les règles / limites finales. AB2-Replies est un candidat expérimental, pas un champion établi. Une largeur 7 supérieure à 6 n'est toujours pas démontrée globalement.

Le plafond paramétré de recherche est 24, mais ce n'est ni une profondeur moyenne ni une profondeur atteinte à chaque décision. Les nouvelles tables ci-dessus ne donnent pas de moyenne de profondeur non mesurée de manière homogène. Les traces conservent les informations de recherche disponibles ; la sélection de candidats et les branches de chance rendent les comparaisons de profondeur délicates.
