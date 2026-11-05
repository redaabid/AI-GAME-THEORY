# Analyse de positions et correction ciblée du 2 novembre

**Statut : expérimental.** Les résultats ciblés ci-dessous sont positifs, mais
ne constituent pas une validation générale. La campagne complète de TIE largeur 7
contre AB2 référence et AB2 largeur 7 est encore en cours au moment de cette mise
à jour. Ces deux derniers restent les candidats prioritaires déjà testés en
parties simulées complètes ; leur validation WPF reste également à faire.

Les deux AB2 historiques plafond 24 / largeurs 6 et 7 sont conservés inchangés.
Une seule correction paramétrable est ajoutée dans
[agents/ab2_tie.py](../../../../../agents/ab2_tie.py), sélectionnable par `ab2tie`.
Ce n'est pas un nouveau tournoi ou une preuve de supériorité générale.

## Problèmes observés, pas supposés

Les traces du tournoi existant ont fourni quatre positions répétées réelles :
trois du témoin et une de largeur 7. Sans humains, une armée de 18 domine une
armée de 12. Des coups de progression et des coups qui stagnent ou reculent
reçoivent la même évaluation. L'ordre lexicographique, l'historique de recherche
ou une action principale en cache peuvent alors départager les égalités.
Les [positions et leur provenance](audit/cases.json) sont aussi figées dans
[les fixtures de tests](../../../../../tests/fixtures/ab2_stagnation.json).

Un audit ciblé de 5683 décisions du témoin et de largeur 7 identifie 83 occasions
d'élimination immédiate garantie de l'unique groupe adverse par des attaquants
adjacents. Dans 78 décisions, toutes de largeur 7, cette élimination n'est pas
choisie. Ces occurrences représentent six plateaux distincts. Les six scores
originaux sont déjà gagnants (+1000000) : ce n'est pas la preuve d'une erreur
de valeur minimax. Un coup peut être noté gagnant sans terminer immédiatement.
L'objectif de la correction est de mieux conclure et départager, pas de réparer
une illégalité. Voir [audit de combat](audit/combat-audit.json) et
[revérification des six positions](audit/combat-rechecks.json).

## Correction et première tentative écartée

La première tentative conservait simplement l'ordre stratégique du générateur
à la racine après le score statique. Le premier déplacement progressait dans
trois cas sur quatre, au même score Alpha-Bêta à profondeur fixe. Mais sur deux
rejeux de 40 demi-coups, les répétitions augmentaient (12 à 27 et 8 à 25).
Cette tentative est conservée dans [essai-1](essai-1/) et n'est pas présentée
comme une amélioration validée.

La correction révisée ordonne les actions racines par :
1. le score statique habituel ;
2. le nombre de retours récents au plateau exact après notre déplacement ;
3. le rang stratégique déjà fourni par le générateur.

Cette priorité remplace à la racine l'ordre TT/historique ; celui des nœuds
internes ne change pas. Un meilleur score recherché reste toujours prioritaire
dans Alpha-Bêta. Aucun poids d'évaluation ni malus de feuille n'est ajouté.
Les candidats, règles et modèle de combat restent ceux d'AB2.

L'historique utilisé est limité aux huit dernières décisions du bot. Seuls les
déplacements historiques sans combat sont reconstruits, car leur état après
déplacement est déterministe. Les combats passés ne sont pas réinventés avec
une issue moyenne. Le plateau complet et le joueur au trait sont comparés,
en ignorant le numéro absolu de demi-coup ; ce n'est pas un malus sur une case.

Les entrées de cache de la racine sont réévaluées pour appliquer ce départage :
une action principale calculée auparavant comme nœud interne ne doit pas le
contourner. Les valeurs internes restent indépendantes de cet historique.
Le choix de huit décisions est heuristique et n'a pas été optimisé.

## Vérification finale

Rejeu de chaque état avec agents fraîchement initialisés, même adversaire AB2,
même graine de combat, profondeur fixe 4 sans chronomètre, horizon d'observation
40 demi-coups et limite de partie conservée à 200. Ce sont des diagnostics
bornés, pas huit matchs officiels ni une reproduction bit à bit des caches du
match original. Les deux cas sans fin à 40 ne sont pas déclarés nuls ou perdus.

| Situation | AB2 inchangé | AB2 corrigé |
|---|---|---|
| 0, largeur 6, distance initiale 3 | Élimination adverse en 9 demi-coups | Identique |
| 1, largeur 6, distance initiale 11 | Encore en cours à 40 ; 12 états répétés | Élimination adverse en 33 ; zéro répétition |
| 2, largeur 6, distance initiale 3 | Élimination adverse en 7 demi-coups | Identique |
| 3, largeur 7, distance initiale 13 | Encore en cours à 40 ; 8 états répétés | Élimination adverse en 37 ; zéro répétition |

Sur les six positions distinctes d'élimination immédiate manquée dans les logs,
la correction choisit l'élimination dans les six revérifications à profondeur 3.
Des tests indépendants gardent aussi l'élimination par deux groupes et l'évitement
d'un recrutement exposant à une destruction immédiate.

Les 147 tests passent (9,687 s), dont neuf nouveaux tests ciblés. Les scores à
profondeur fixe sont inchangés sur les quatre cas et douze contrôles issus de
six cartes fraîches, pour les deux largeurs. Ce contrôle n'est pas une preuve
d'équivalence à toutes les profondeurs ni de force égale sous contrainte de temps.

Huit sondes avec budget 1,5 s sur les états initiaux : zéro défaut ; maximum
1,502 s. Tous les résultats sont dans [verification-finale](verification-finale/).
Les étapes et sources figées sont conservées pour ne pas masquer l'essai négatif.

## Reproduction et portée

Commandes depuis la racine du checkout :

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/replay_ab2_tie.py --output .local/ab2-experiments/nouveau-rejeu
```

Spécifications du correctif : `ab2tie:depth=1,max_depth=24,width=6,extra=0` et
`ab2tie:depth=1,max_depth=24,width=7,extra=0`. Le plafond 24 ne s'applique qu'en
recherche chronométrée ; les diagnostics sans chronomètre utilisent depth=4.

Les résultats locaux montrent une amélioration sur les cas ciblés, sans conclure
que les cycles sont résolus ou que le taux de victoire général augmente. Il reste
à valider les deux largeurs corrigées sur WPF et sur un lot indépendant. Les
sources des camarades et les anciens modèles ne sont pas modifiés. Aucun commit
ou push n'est réalisé pendant cette correction.
