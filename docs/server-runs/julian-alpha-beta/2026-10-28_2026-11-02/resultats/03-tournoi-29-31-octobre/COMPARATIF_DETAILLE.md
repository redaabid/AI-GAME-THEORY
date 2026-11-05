# Comparatif concret des cinq configurations AB2

96 parties valides : 80 de sélection, puis 16 de confirmation. Simulateur uniquement, pas serveur WPF. Parties perturbées par les veilles conservées à part et exclues des chiffres ci-dessous.

## Configurations

Tous utilisent Alpha-Bêta, approfondissement itératif, classement des coups et table de transposition. Le hasard des combats est simplifié pendant leur recherche ; les parties simulées utilisent des combats échantillonnés. Budget commun 1,5 seconde par décision, plafond 200 demi-coups par partie.

| Configuration | Largeur | Plafond profondeur | Ajout |
|---|---:|---:|---|
| AB2 de référence | 6 | 24 | Aucun ajout |
| AB2 + prolongation tactique | 6 | 24 | Captures : prolongation bornée à 1 demi-coup, 2 candidats |
| AB2 largeur 7 | 7 | 24 | Un candidat supplémentaire par position |
| AB2 + guidage lointain | 6 | 24 | Progression vers cible accessible, poids 2000 |
| AB2 + trajet simulé | 6 | 24 | Évaluation par trajet scripté, jusqu’à 8 demi-coups alternés |

## Sélection : chaque configuration contre les quatre autres

| Configuration | Parties | V | N | D | Décisions | Temps moyen / maximum (s) | Profondeur moyenne / maximum |
|---|---:|---:|---:|---:|---:|---|---|
| AB2 de référence | 32 | 8 | 16 | 8 | 3042 | 1.405 / 1.577 | 17.97 / 24 |
| AB2 + prolongation tactique | 32 | 8 | 16 | 8 | 3099 | 1.424 / 1.560 | 15.27 / 24 |
| AB2 largeur 7 | 32 | 8 | 16 | 8 | 2641 | 1.422 / 1.569 | 15.98 / 24 |
| AB2 + guidage lointain | 32 | 8 | 16 | 8 | 2907 | 1.435 / 1.565 | 15.71 / 24 |
| AB2 + trajet simulé | 32 | 8 | 16 | 8 | 3112 | 1.424 / 1.567 | 11.78 / 24 |

## Confirmation : largeur 7 contre guidage, nouvelles cartes

| Configuration | Parties | V | N | D | Décisions | Temps moyen / maximum (s) | Profondeur moyenne / maximum |
|---|---:|---:|---:|---:|---:|---|---|
| AB2 largeur 7 | 16 | 6 | 8 | 2 | 1512 | 1.444 / 1.566 | 12.84 / 24 |
| AB2 + guidage lointain | 16 | 2 | 8 | 6 | 1511 | 1.451 / 1.573 | 12.29 / 24 |

## Explication des résultats

La sélection contient 40 nuls sur contact et 40 victoires du premier joueur sur distant. Chaque modèle joue les deux espèces et les deux ordres de jeu ; chacun termine donc avec 8 victoires, 16 nuls, 8 défaites. Ces cartes ne départagent pas les configurations au score.

Largeur 7 et guidage sont des finalistes provisoires choisis par le critère secondaire annoncé : moins de répétitions dans leurs parties (4046 et 4376, contre 4822 pour le témoin et 4965 pour chaque autre variante). Ce sont des propriétés des parties, pas des répétitions attribuables exclusivement à un seul agent. Ils ne sont pas les deux meilleurs au score, tous les scores étant égaux.

La confirmation utilise deux nouvelles cartes, deux graines et quatre affectations espèce/premier joueur. Largeur 7 obtient 6 victoires, 8 nuls, 2 défaites contre guidage ; les victoires se répartissent également entre premier et second joueur (4 de chaque, tous agents confondus). Ce résultat favorise largeur 7 dans ce lot, sans prouver sa supériorité sur le témoin ou les autres configurations non testées sur ces nouvelles cartes.

## Sens des métriques

Le temps moyen porte sur toutes les décisions de chaque modèle dans la phase concernée. La profondeur est la dernière itération Alpha-Bêta entièrement terminée, pas le plafond configuré. Une moyenne peut être décimale, chaque décision ayant une profondeur entière.

Le maximum 24 signifie une itération terminée à cette profondeur nominale ; certaines branches finissent plus tôt (position terminale, limite de 200 coups, coupures ou mémoire). Ce n’est pas une exploration exhaustive de tous les coups légaux à 24 niveaux. La moyenne des profondeurs dépend aussi des positions rencontrées : elle ne mesure pas seule la force de jeu.

Les extensions tactiques et les demi-coups scriptés du trajet ne sont pas ajoutés à la colonne profondeur Alpha-Bêta. Le trajet utilise une politique adverse simplifiée, pas une recherche exhaustive sur ces réponses.

Zéro défaut d’agent sur le lot valide ; aucun temps supérieur à 1,8 seconde sur celui-ci. Les interruptions par veille ne sont pas masquées : les parties concernées restent dans les sous-dossiers interrupted-*. Aucun nouveau test lancé pour produire ce tableau.
