# Justifications et portée des compléments AB2

Ce texte complète les [justifications AB2/AB3/AB6/AB7 archivées](../2026-10-26_2026-10-27/justifications/AB_CONFIGURATIONS_JUSTIFICATION.md).
Il documente les raisons des expériences, sans recommander une sélection finale.
La [synthèse des étapes et des configurations fixées par Julian](SYNTHESE_DEMARCHE_ET_CONFIGURATIONS.md)
complète ce texte : profondeur, pistes rapportées du professeur, cartes et
variantes, tournoi, correction ciblée, puis choix de travail avec TIE largeur 7.
Les deux candidats prioritaires actuels sont AB2 référence et AB2 largeur 7,
déjà testés en parties simulées complètes. TIE largeur 7 reste une expérimentation
dont les tests ciblés ne constituent pas une validation en parties complètes
ou sur le serveur WPF. Sa campagne comparative est en cours.

## Conseils rapportés et interprétations

Julian a rapporté au professeur les allers-retours observés. Les pistes rapportées
étaient de pouvoir aller chercher des ennemis éloignés, éventuellement en
« sautant des cases » dans la planification, et de vérifier cela sur une carte
où les armées sont aux extrémités. Ce n'est pas un verbatim authentifié ni une
confirmation que le professeur visait précisément une méthode de macro-actions.

Nous avons donc séparé des hypothèses : horizon plus profond, évaluation de la
progression, et anticipation des trajets. Une amélioration empirique d'une de
ces hypothèses n'établirait pas rétrospectivement le sens exact de son conseil.

## Mécanismes et hypothèses testées

| Mécanisme | Pourquoi le tester | Limite à expliquer |
|---|---|---|
| Plafond de profondeur augmenté | Exploiter le temps disponible après la profondeur 8 | Plus profond ne signifie pas meilleur ; recherche sélective et combats simplifiés |
| Largeur 7 ou 8 | Réduire le risque d'éliminer un coup utile avant la recherche | Le coût peut réduire la profondeur ; la génération reste non exhaustive |
| Quiescence bornée | Éviter certaines évaluations juste avant une capture/réponse | Deux candidats seulement, un demi-coup : pas une résolution complète des tactiques |
| Pénalité de répétition | Tester si l'évaluation peut décourager des plateaux déjà observés | Peut décourager une défense utile ; dépend de l'historique et impose de revoir les caches |
| Guidage lointain | Donner une valeur aux étapes intermédiaires sans gain immédiat | Cible heuristique, poids 2000 non optimisé ; peut privilégier une mauvaise poursuite |
| Trajet simulé aux feuilles | Estimer les conséquences de plusieurs déplacements sans développer toutes leurs branches | Réponses adverses scriptées, approximation supplémentaire ; pas un vrai minimax macro-temporel |

Ces expériences s'inscrivent dans la recherche Alpha-Bêta et dans le travail
sur la génération des actions et l'évaluation. Elles n'ajoutent pas de nouveau
modèle appris. Le guidage ne reprend pas AB7 : AB7 modifiait le facteur de
distance des humains dans une autre architecture ; ici une cible explicite
produit un bonus de progression sur base AB2.

## Place de la littérature et des anciens projets

Les sources classiques et récentes déjà vérifiées sont conservées dans le
document de justification antérieur : Alpha-Bêta, classement/mémoire,
abstractions d'actions et méthodologie d'évaluation. Les idées des anciens
projets ont servi d'inspiration pour intentions/cibles et contraintes de temps,
sans reproduction fidèle ni réexécution de leur classement.

L'article de Moraes et al. (JAIR 2022), discuté dans ce document, justifie
l'intérêt général de réduire et structurer les actions en jeu de stratégie.
Il ne valide pas notre poids 2000, notre largeur 7 ou notre simulation de huit
demi-coups, et ne prouve pas que ce rollout est une macro-action temporelle.
Ces réglages relèvent ici d'hypothèses à tester. Aucune nouvelle référence
scientifique n'est présentée comme preuve de leur optimalité.

## Ce que les résultats permettent de dire

Le premier lot apporte un signal en faveur d'un plafond supérieur à 8 contre
le témoin testé, sur quatre parties seulement. Le contrôle éloigné montre une
progression plus rapide dans une condition de guidage, mais un résultat dominé
par le rôle de départ. Le tournoi équilibré montre ensuite que ses deux cartes
ne séparent pas les scores : nuls sur contact, victoire du premier sur distant.

Le départage par répétitions sélectionne deux candidats, pas deux vainqueurs au
score. La confirmation indépendante favorise largeur 7 face au guidage sur
seize parties ; elle ne couvre pas les autres comparaisons ni le vrai serveur.
Les poids sont restés fixes. Ces éléments sont utilisables pour expliquer une
démarche expérimentale au professeur, pas pour annoncer un champion universel.
