# Démarche expérimentale et trois configurations AB2 retenues

État du 2 novembre 2026. Ce document expose les étapes dans leur ordre logique
d'expérimentation, avec la question posée, la modification et le résultat.
Les dates exactes des échanges oraux avec le professeur ne sont pas établies.
Les conseils sont ceux rapportés par Julian ; nos paramètres et interprétations
ne doivent pas être attribués au professeur.

## 1. Point de départ : un AB2 fonctionnel mais plafonné à 8

AB2 disposait déjà d'Alpha-Bêta, d'approfondissement itératif, de classement des
coups, d'historique de recherche et d'une table de transposition. Le générateur
réduit l'arbre à un nombre borné de tours candidats : il n'énumère pas tous les
coups légaux. La recherche simplifie les issues aléatoires des combats.

Sur le vrai serveur Windows, AB2 plafond 8 / largeur 6 avait joué quatre parties
contre AB3 : 3 victoires, 1 nul, aucun défaut ; temps moyen 0,370 s, maximum
1,507 s. Les logs indiquaient une itération 8 terminée sur 289 décisions sur 317.

**Question :** le plafond 8 empêche-t-il d'exploiter du temps disponible ? La
moyenne basse ne prouvait pas que toutes les positions étaient faciles :
certaines décisions consommaient déjà le budget interne de 1,5 s.

## 2. Première amélioration étudiée : augmenter la profondeur autorisée

Nous avons préparé plusieurs plafonds (12, 16, 24, 64) et conservé une limite
temporelle de 1,5 s. L'approfondissement itératif garde la dernière recherche
entièrement terminée. Tous ces plafonds n'ont pas été comparés en parties
longues ; le lot principal a retenu 24 pour limiter le nombre de configurations.

Le premier lot simulé utilise thetrap et testmap2, deux rôles, une graine.
Plafond 24 / largeur 6 contre plafond 8 / largeur 6 : **2 V / 2 N / 0 D**.
C'est un signal exploratoire sur quatre parties, pas la preuve d'une optimalité
du plafond 24 ni une certification serveur de cette nouvelle configuration.

Une profondeur 24 signifie une itération nominale à 24 demi-coups, pas une
exploration exhaustive de toutes les branches jusqu'à ce niveau. Les branches
peuvent finir plus tôt. La profondeur réellement terminée varie selon les
positions, la largeur, le temps et les fins de partie.

## 3. Conseils rapportés du professeur : progression et adversaires éloignés

Le problème présenté au professeur était notamment les allers-retours. Les
pistes rapportées étaient de mieux atteindre des ennemis lointains, éventuellement
de « sauter des cases » dans la planification, et d'essayer une carte avec les
armées aux deux bouts. Le sens technique exact de cette expression n'a pas été
confirmé ; nous n'avons ni modifié la légalité des déplacements ni téléporté les groupes.

**Pour étudier ce conseil**, nous avons séparé deux hypothèses :
- donner une valeur à la progression vers une cible accessible ;
- anticiper un trajet par une simulation bornée de déplacements des deux camps.

Les autres leviers (largeur, prolongation tactique, répétition) sont nos
expériences complémentaires, pas des réglages expressément imposés par lui.

## 4. Variantes complémentaires et cartes de diagnostic

| Modification | Pourquoi l'essayer | Observation / limite |
|---|---|---|
| Largeur 8 puis 7 | Conserver davantage de coups candidats | Plus de choix mais profondeur potentiellement réduite ; une partie largeur 8 est perturbée par la veille |
| Quiescence bornée | Éviter certaines évaluations juste avant une capture | Pas de gain clair contre la référence dans le premier lot |
| Malus de répétition aux feuilles | Décourager les retours sur un plateau déjà observé | Le réglage testé fait 0 V / 2 N / 2 D contre la référence ; pas un succès démontré |
| Guidage vers une cible | Donner un intérêt aux déplacements intermédiaires | Premier contact plus rapide dans un cas de poursuite ; pas de gain global établi |
| Trajet simulé | Anticiper plusieurs déplacements à faible branchement | Adversaire scripté, approximation d'évaluation, pas de vraies macro-actions temporelles |

Nous avons écrit les cartes XML avec Python, sans Map Generator : une carte
symétrique de recrutement lointain, une carte de poursuite asymétrique 12 contre 8,
puis une carte de contact. Cela permet de contrôler la situation testée. Leur
compatibilité avec Python est vérifiée ; pas encore leur fonctionnement sur WPF.

Le lot éloigné comporte 16 parties entre quatre variantes et AB2 plafond 24 /
largeur 6. Chaque variante obtient 2 V / 0 N / 2 D ; les vampires gagnent toujours.
**Pourquoi poursuivre les tests ?** Ce lot est dominé par le rôle et la position
initiale : il ne permet pas de désigner la meilleure variante.

## 5. Comparer les cinq configurations entre elles, puis confirmer

Pour limiter la consommation de tokens, les matchs sont exécutés par un script
local autonome, sans appel de modèle par tour. Les résultats sont sauvegardés
après chaque partie, avec reprise possible. Les veilles du PC ont contaminé
quelques tentatives, qui sont archivées à part puis rejouées.

Le tournoi réunit référence, largeur 7, quiescence, guidage et trajet : dix paires,
deux cartes et quatre affectations espèce/premier joueur = **80 parties**.
Chaque configuration obtient **8 V / 16 N / 8 D**. L'explication précise est
quarante nuls sur contact et quarante victoires du premier joueur sur distant.
Les cartes, même symétriques, ne départagent donc pas les scores des modèles.

Largeur 7 et guidage passent au lot suivant au critère secondaire des répétitions,
pas parce qu'ils ont gagné davantage. Deux nouvelles cartes, deux graines de
combat et quatre affectations de rôles donnent **16 parties de confirmation**.
Largeur 7 obtient **6 V / 8 N / 2 D** contre guidage : 6–2 sur une carte, huit
nuls sur l'autre. Il n'a pas démontré sa supériorité sur la référence largeur 6.

Les statistiques détaillées, profondeurs et temps sont dans le
[comparatif complet](resultats/03-tournoi-29-31-octobre/COMPARATIF_DETAILLE.md).
Les 96 parties retenues ont zéro défaut et un maximum mesuré de 1,577 s.

## 6. Corriger un problème identifié dans les positions enregistrées

Au lieu d'ajouter encore des configurations générales, nous avons examiné les
logs des deux AB2. Quatre positions répétées montrent des coups de progression
et de stagnation notés à égalité. Le choix peut alors dépendre de l'ordre des
coordonnées, de l'historique ou d'une action principale mémorisée.

Une première correction ne faisait que rétablir le classement stratégique du
générateur à la racine. Elle améliore le premier coup, mais augmente les cycles
dans deux rejeux. Cet essai négatif est conservé et n'est pas présenté comme un succès.

La correction révisée **AB2 TIE** classe les coups racines par score statique,
puis préfère les plateaux exacts moins récemment répétés, puis le classement
du générateur. Un meilleur score recherché reste prioritaire. Les coups en
cache à la racine sont réexaminés pour ne pas contourner ce départage.
Les poids d'évaluation, règles et candidats ne changent pas. Seuls les anciens
déplacements sans combat sont reconstruits ; les résultats de dés passés ne
sont pas inventés. Ce n'est pas le malus aux feuilles testé et écarté auparavant.

Sur les rejeux bornés à 40 demi-coups et à profondeur fixe 4 : deux situations
qui bouclaient encore sont conclues par élimination en **33 et 37 demi-coups** ;
les deux autres restent conclues en 9 et 7. Six positions distinctes où une
élimination immédiate n'était pas choisie sont revérifiées avec succès.
Les **147 tests passent**. Les sondes à 1,5 s restent sous 1,502 s, mais ne
remplacent pas des parties complètes avec TIE ni une validation sur le serveur.

Voir [l'analyse et les preuves de cette correction](corrections-ciblees-2-novembre/README.md).

## 7. Deux candidats prioritaires et une expérimentation

Le 2 novembre, Julian fixe TIE en **largeur 7**. Les trois spécifications sont
centralisées dans [ab2_retained_profiles.json](../../../../scripts/ab2_retained_profiles.json).
AB2 référence et AB2 largeur 7 sont nos candidats prioritaires actuels : ils
disposent de résultats en parties simulées complètes. Cela ne démontre pas une
supériorité statistique de largeur 7 sur 6 ni leur force contre toutes les équipes.
**TIE largeur 7 est conservé comme expérimentation, pas comme modèle validé.**
Ses tests ciblés sont positifs, mais la campagne complète contre les deux
candidats prioritaires est encore en cours. Aucun résultat définitif n'est annoncé.

| Configuration | Plafond chronométré | Largeur | Rôle dans la comparaison |
|---|---:|---:|---|
| AB2 référence | 24 | 6 | Candidat prioritaire, testé en parties simulées complètes |
| AB2 largeur 7 | 24 | 7 | Candidat prioritaire, testé en parties simulées complètes |
| AB2 TIE largeur 7 | 24 | 7 | Expérimentation : tests ciblés positifs, campagne complète en cours |

Les modèles originaux et essais précédents restent disponibles. Cette sélection
n'active ni quiescence, ni guidage, ni trajet. Ces fichiers font partie de la
livraison documentaire du 2 novembre sur la branche personnelle de Julian.
Un [instantané TIE incomplet](checkpoint-tie-experimental-2-novembre/README.md)
conserve les quatre parties déjà terminées lors de la préparation du push.
La validation WPF des trois configurations,
les moyennes en parties complètes de TIE largeur 7 et la confirmation des
paramètres exacts de l'examen restent à effectuer.

## Justification pour la présentation au professeur

La démarche apporte une traçabilité expérimentale : question, modification
isolable, protocole, résultat et limite à chaque étape. Les fondements et sources
déjà vérifiées sont conservés dans les justifications antérieures ; ces tests ne
créent pas de nouvelles preuves bibliographiques d'optimalité. La contribution
documentée est l'adaptation et l'évaluation progressive du même Alpha-Bêta.
