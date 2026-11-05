# Contrôles à 40 coups — verdicts, décisions et ancien bot

**14 nouvelles parties WPF terminées et confirmées : huit cas rejoués et six contrôles.** Les 32 conditions de la famille AB sont désormais couvertes par un résultat confirmé ; quatre contrôles opposent AB3 à l’ancien alphabeta, puis deux à la baseline sur testmap2.

17 nouvelles tentatives sont conservées. Les contrôles dont la capture UI a expiré ont été rejoués ; leurs verdicts initiaux restent inconnus.

Les huit verdicts initiaux absents restent inconnus. Les nouvelles parties rejouent les mêmes conditions mais peuvent avoir une issue différente, car le hasard du serveur n’est pas contrôlé. Le tableau composé retient une tentative confirmée par condition ; aucune partie n’est comptée deux fois.

## Bilan composé contre AB3

| Profil | Parties | V / N / D | Max (s) | Moyenne (s) | Faults |
|---|---:|---|---:|---:|---:|
| ab0 | 4 | 1/2/1 | 0.007 | 0.002 | 0 |
| ab1 | 4 | 1/2/1 | 1.502 | 0.864 | 0 |
| ab2 | 4 | 1/2/1 | 1.502 | 0.778 | 0 |
| ab3 | 38 | 11/18/9 | 1.517 | 0.973 | 0 |
| ab4 | 4 | 1/2/1 | 1.503 | 1.016 | 0 |
| ab5 | 4 | 1/2/1 | 1.502 | 1.058 | 0 |
| ab6 | 4 | 2/2/0 | 1.502 | 1.432 | 0 |
| ab7 | 4 | 1/2/1 | 1.502 | 0.952 | 0 |
| ab8 | 4 | 0/2/2 | 1.501 | 0.774 | 0 |
| ancien alphabeta (AB90) | 4 | 1/2/1 | 1.550 | 0.973 | 0 |
| baseline historique (AB91) | 2 | 0/0/2 | 0.001 | 0.000 | 0 |

AB3 est le témoin commun : sa ligne regroupe tous les adversaires. AB7 désigne ici le profil historique ; le nouveau poids discount=0,97 est seulement inclus dans le contrôle de décisions, pas dans ces nouveaux matchs WPF.

## Ancien bot sur les deux cartes

AB90 est uniquement le nom ASCII attribué à l’agent existant --agent alphabeta. Son code est inchangé, ses paramètres natifs sont conservés. Les deux ordres de connexion sont joués sur chaque carte, avec le même serveur, MaxPlays=40 et --move-time 1.5.

AB91 désigne la baseline historique de strategy.py, inchangée depuis le rapport du 22 octobre. Ce témoin ne repose pas sur la recherche Alpha-Bêta. Deux contrôles supplémentaires le confrontent à AB3 sur testmap2, dans les deux ordres.

| Carte | Ordre | Vainqueur WPF | Effectifs dans cet ordre |
|---|---|---|---|
| thetrap.xml | ab90 puis ab3 | ab3 | 0 / 4 |
| testmap2.xml | ab3 puis ab90 | draw | 16 / 16 |
| testmap2.xml | ab90 puis ab3 | draw | 16 / 16 |
| thetrap.xml | ab3 puis ab90 | ab90 | 8 / 9 |
| testmap2.xml | ab3 puis ab91 | ab3 | 16 / 14 |
| testmap2.xml | ab91 puis ab3 | ab3 | 14 / 16 |

Sur testmap2, le contrôle avec l’ancien bot donne **2/2 nuls**. Le contrôle avec la baseline donne **0/2 nuls**. Ce petit lot ne permet pas une attribution causale complète. L’ancien bot partage aussi l’évaluation et des composants du simulateur avec la famille AB.

## Décisions à profondeur fixe

Douze positions identiques : huit états reconstruits des UPD du vrai serveur (avant les coups 1, 9, 17 et 29 sur les deux cartes), puis quatre cartes générées nouvelles. Tous les agents ont effectivement terminé une recherche de profondeur 2, sans deadline. AB5 conserve sa quiescence bornée ; AB6 conserve les nœuds de chance.

| Profil | Choix différents d’AB3, paramètres communs /12 | Profils réglés /12 |
|---|---:|---:|
| ab0 | 3 | 3 |
| ab1 | 3 | 3 |
| ab2 | 3 | 3 |
| ab3 | 0 | 0 |
| ab4 | 0 | 1 |
| ab5 | 1 | 2 |
| ab6 | 0 | 0 |
| ab7 | 0 | 0 |
| ab8 | 3 | 3 |
| ab7_new | 1 | 1 |
| legacy | 7 | 7 |

Les paramètres communs normalisent la famille AB0–AB8. Le témoin legacy garde sa largeur native (10), donc son écart ne mesure pas uniquement son algorithme.

**AB0/AB1/AB2/AB8 ont les mêmes choix et valeurs sur les douze positions à paramètres communs. AB3 et AB4 aussi.** C’est attendu pour des optimisations de recherche qui visent à calculer la même décision plus efficacement. À temps limité, elles peuvent atteindre des profondeurs différentes et donc jouer différemment.

AB6 choisit ici les mêmes actions qu’AB3, mais sa valeur diffère sur une position (generated-44002 : +1 000 000 pour le substitut déterministe, 0 pour la moyenne stochastique). Cela montre une différence de modèle sans garantir un changement d’action dans cet échantillon. L’ancien AB7 fait doublon ; le nouveau AB7 change une décision sur douze.

## Comparaison avec les anciens rapports

Le [rapport du 22 octobre](../../../2026-10-22-670a148/SUMMARY.md) indique déjà deux nuls 16–16 contre OEP sur testmap2 à 40 coups. Contre MCTS et baseline, les quatre victoires sur cette carte à 40 coups étaient des scores 16–14 au plafond, sans élimination. Les anciennes parties différaient donc aussi par l’adversaire et sa collecte des humains. Machine, commit et archive du serveur historiques diffèrent ; ce contrôle ne prétend pas reproduire exactement ces anciens matchs.

## Données et limites

[Tableau de chaque condition](SUMMARY-40.md), [toutes les tentatives](aggregate-40.json), [décisions et états complets](decisions/decisions.json), [protocole](protocol.json).

Les résultats de force portent sur quatre parties par challenger, avec combats aléatoires. Ce sont des tendances exploratoires. Les temps imprimés sont arrondis ; les recherches sans deadline du contrôle de décisions ne sont pas des mesures sous la limite de deux secondes. Le compteur de secours internes n’est pas instrumenté dans l’ancien bot ; seuls les faults et occurrences de fallback présents dans ses logs peuvent être contrôlés.

Aucun bot existant n’a été modifié, aucun match à 200 coups n’a été lancé dans ce contrôle.

## Conclusion pratique

Le protocole ne force pas les nuls : AB3 bat la baseline 16–14 dans les deux ordres. L'ancien alphabeta fait deux nuls 16–16 contre AB3 sur testmap2. À 40 demi-coups sur cette grande carte, le comparatif mesure surtout le recrutement : les bots à 16 unités sont à égalité au plafond, alors que la baseline ne recrute que quatre humains et termine à 14.

Les variantes ne constituent pas neuf comportements indépendants. À profondeur identique, les optimisations d'ordre, mémoire, PVS et MTD(f) conservent souvent la même décision : c'est attendu. Les différences utiles à examiner sont le générateur AB3, la quiescence AB5, le modèle de hasard AB6 et les poids du nouveau AB7. Les recherches plus rapides se comparent aussi à temps égal, où elles peuvent terminer des profondeurs différentes.

Dans ce lot composé, AB6 obtient 2 victoires et 2 nuls contre AB3 ; AB0, AB1, AB2, AB4, AB5 et le profil AB7 historique ont chacun 1 victoire, 2 nuls et 1 défaite. AB8 a 2 nuls et 2 défaites. AB0 reste un témoin à conserver ; AB4/AB5 ne sont pas éliminées par ces résultats. Ce faible nombre de parties ne prouve pas une supériorité statistique. Le nouveau AB7 n'a pas encore joué ces parties WPF.

Tous les contrôles de cette reprise sont à 40 coups. La campagne est terminée et aucun essai à 200 coups n'est relancé.
