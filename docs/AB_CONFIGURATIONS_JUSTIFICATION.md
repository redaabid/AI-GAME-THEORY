# AB2, AB3, AB6 et AB7 : configurations retenues et justifications

Document de présentation — 27 octobre 2026. **Priorité expérimentale : AB2 et AB6.** AB3 reste la référence de génération sélective ; le nouvel AB7 reste une variante d'évaluation à comparer. Les quatre configurations sont conservées, sans proclamer de gagnant définitif.

Ce document décrit le code effectivement testé, puis distingue les fondements scientifiques, l'inspiration des anciens projets et nos observations. Les références complémentaires vérifiées le 27 octobre ne sont pas présentées comme des publications qui auraient toutes guidé l'implémentation du 26 octobre. Une justification bibliographique du principe n'est pas une validation de nos paramètres.

## 1. Ce qui change entre les quatre configurations

Nous utilisons un même moteur modulaire de recherche adversariale. AB2, AB3 et AB7 emploient Alpha-Bêta sur une approximation déterministe des combats ; AB6 est son extension avec des nœuds de chance.

| Composant réellement actif | AB2 | AB3 | AB6 | Nouvel AB7 |
|---|---|---|---|---|
| Approfondissement itératif, ordre des coups, historique et table de transposition | Oui | Oui | Oui | Oui |
| Générateur commun borné, comportant déjà des tours coordonnés et des splits | Oui | Oui | Oui | Oui |
| Propositions supplémentaires par scripts et sélection avec diversité de rôles | Non | Oui | Oui | Oui |
| Résolution des combats pendant la recherche | Une issue représentative | Une issue représentative | Distribution finie des survivants | Une issue représentative |
| Évaluation | Poids de référence | Poids de référence | Poids de référence | `discount=0.97` au lieu de `0.90` |

Sources de cette description : [options des profils](../agents/ab_variants.py), [générateur commun](../candidates.py), [propositions par scripts](../lookahead.py), [évaluation](../evaluation.py) et [approximation des combats](../combat.py).

**AB2 n'explore donc pas tous les mouvements légaux.** AB3 n'introduit pas la première coordination du projet : il enrichit et modifie une sélection déjà bornée. Les scripts produisent le mouvement du tour courant et sont réévalués ensuite ; nous n'avons pas implémenté de macro-actions temporelles exécutées sur plusieurs tours.

## 2. AB2 — référence efficace, avec mémoire et ordonnancement

### Fonctionnement implémenté

À chaque décision, la recherche termine successivement les profondeurs 1, 2, etc., jusqu'à la limite de temps ou au plafond de profondeur. Elle conserve le choix de la dernière itération **entièrement terminée**. L'historique privilégie les mouvements ayant provoqué des coupures. La table mémorise des valeurs exactes ou des bornes et un mouvement associé.

Les clés de notre table incluent notamment le plateau, le joueur au trait, le numéro de demi-coup, les règles, la profondeur restante et la limite de partie. La capacité est bornée. L'historique réordonne la liste retenue sans modifier sa composition. Notre clé incluant la profondeur, nous ne revendiquons pas une réutilisation automatique de la variante principale d'une profondeur différente.

### Pourquoi ce choix est raisonnable

La contrainte de deux secondes impose d'arrêter proprement une recherche dont le coût varie selon la position. L'approfondissement itératif fournit une décision utilisable ; l'ordre des coups favorise des coupures précoces ; la mémoire évite certaines recherches répétées. Ce sont des mécanismes complémentaires, pas trois nouvelles évaluations stratégiques.

**Fondements :** Knuth et Moore [R1] pour Alpha-Bêta ; Schaeffer [R2] pour l'historique et les interactions entre améliorations. Le support universitaire de 2024 [R4] présente toujours l'ordre dynamique et les transpositions comme des améliorations pertinentes. La formalisation de Nipkow, publiée en 2024 [R3], rappelle qu'il faut distinguer variantes de coupure et correction. Elle ne vérifie pas notre code Python.

**Inspiration applicative :** Langorou [H2] utilisait déjà un budget explicite, un approfondissement itératif et une décision de secours. Nous retenons ces principes sans reprendre ses coefficients ni annoncer une reproduction de son programme.

### Pourquoi nous le conservons

Dans notre lot à 200 coups maximum, AB2 obtient **3 victoires, 1 nul et aucune défaite contre AB3**, pour une moyenne de **0,370 s par décision**. C'est notre candidat prioritaire pour une base simple et relativement peu coûteuse. Ce résultat ne mesure pas séparément l'effet de sa table ou de son historique : AB2 et AB3 diffèrent aussi par leur sélection de mouvements.

## 3. AB3 — sélection de tours coordonnés et diversité des propositions

### Fonctionnement implémenté

AB3 conserve les mécanismes d'AB2. Il ajoute aux candidats communs les propositions de `candidate_turns` : comportements de groupes, variantes où un groupe change de comportement, attaques conjointes et autres tours légaux prévus par ce module. Les doublons sont supprimés.

La sélection conserve aussi une diversité fondée sur des catégories : attaque, split, mouvement de plusieurs groupes et implication d'un groupe proche de l'ennemi. Dans le profil testé, la recherche retient **au plus six tours candidats par nœud**. Produire et classer les propositions a néanmoins un coût : largeur retenue et coût de génération sont deux mesures différentes.

### Pourquoi ce choix est raisonnable

Les déplacements et divisions de plusieurs groupes multiplient les combinaisons. Une liste limitée de propositions cohérentes peut permettre une anticipation plus profonde. Le risque est de supprimer une bonne réponse adverse ou un mouvement préparatoire.

**Recherche récente :** Moraes, Nascimento et Lelis (2022) [R5] étudient les abstractions d'actions qui restreignent les choix et répartissent l'effort de recherche de manière asymétrique entre unités. Cela motive notre attention aux groupes critiques. **Notre règle de diversité est une adaptation heuristique**, pas une reproduction de leurs algorithmes ni une abstraction garantie sans perte. Leurs expériences portent sur d'autres jeux et moteurs.

**Anciens projets :** ZCSN [H1] fournit une inspiration propre à Vampires vs Werewolves : raisonner par cibles pertinentes et limiter les possibilités de split pour maîtriser la combinatoire. Nous ne reprenons pas sa limite rigide de deux groupes et ne transférons pas sa profondeur annoncée à notre code.

### Pourquoi nous le conservons

AB3 est le **comparateur commun** des 16 parties longues : il permet d'étudier séparément l'ajout probabiliste d'AB6 et le réglage d'AB7. Ses résultats regroupés contre plusieurs adversaires ne constituent pas un taux directement comparable aux quatre parties de chaque challenger. Il reste utile comme architecture de coordination, même si le lot ne montre pas qu'il surpasse AB2.

## 4. AB6 — intégrer les issues aléatoires des combats

### Fonctionnement implémenté

AB6 reprend la génération et la sélection d'AB3. Dans la recherche, une attaque incertaine produit plusieurs états réalisables : victoire ou défaite, puis nombres possibles de survivants suivant les distributions binomiales du modèle. Les issues sans survivants sont regroupées. Les arrivées sur une même destination sont additionnées avant de déterminer le combat.

La valeur d'un mouvement tient compte de l'espérance des valeurs des états obtenus :

\[
Q(s,a)=\sum_{s'}P(s'\mid s,a)\,V(s').
\]

Ce calcul est différent de la notation d'une unique issue représentative. En général, la valeur d'un état moyen ne remplace pas la moyenne des valeurs, notamment près de l'élimination.

Pour interrompre l'énumération sans ignorer arbitrairement les issues rares, le code exploite les scores bornés : avec une contribution déjà calculée `S` et une masse de probabilité restante `r`, la valeur se trouve entre `S-rM` et `S+rM`, avec `M=1 000 000` et une marge numérique. Une coupure est possible si tout cet intervalle est sans intérêt pour la fenêtre de recherche. Une itération interrompue par la deadline est abandonnée.

### Pourquoi ce choix est raisonnable

Le hasard intervient dans les règles du jeu : comparer uniquement des combats rendus déterministes peut masquer une probabilité de disparition ou surestimer une attaque. Ballard [R6] fournit le fondement de l'extension des coupures aux arbres à nœuds de chance. Notre implémentation emploie des bornes sur la masse restante ; elle ne reproduit pas toutes les variantes Star de l'article.

**Appui récent :** le mémoire universitaire de Baraniuk (2025) [R7] propose une expérience récente de recherche adversariale avec hasard et d'évaluation des positions. C'est un mémoire de licence sur le backgammon, pas un article démontrant notre méthode de coupure.

**Inspiration historique :** Langorou [H2] pondérait déjà des issues de combat. Notre distribution de survivants est plus détaillée que ses deux issues représentatives à survivants moyens ; son classement interne ne démontre pas la supériorité de notre choix.

### Résultats et limites

AB6 obtient **3 victoires et 1 défaite contre AB3**, moyenne **1,473 s**, maximum **1,513 s**. Il mérite donc une priorité expérimentale, avec un coût supérieur à AB2.

« Distribution complète » désigne le modèle fini implémenté : cela ne certifie pas indépendamment toutes les règles de la DLL Windows. Les combats de destinations différentes sont supposés indépendants. Le générateur reste classé par l'approximation déterministe commune ; une action intéressante en espérance peut être éliminée avant la recherche. La sélection, la profondeur et l'évaluation restent approximatives. Enfin, espérance du score heuristique et probabilité calibrée de victoire ne sont pas synonymes : AB6 n'est pas un agent explicitement averse au risque.

## 5. Nouvel AB7 — régler l'évaluation sans changer les mécanismes de recherche

### Ce qui a réellement été réglé

AB7 conserve la structure d'AB3 et ses caractéristiques d'évaluation : effectifs relatifs, humains accessibles avant l'adversaire, menaces et dispersion. Après un criblage supplémentaire de **60 parties simulées d'entraînement et 24 de validation**, le candidat retenu passe `discount` de **0,90 à 0,97**. Les autres poids restent : `material=1`, `humans=0.8`, `threat=0.7`, `groups=0.1`.

Ce paramètre réduit la pénalisation de la distance aux humains dans l'évaluation : la contribution d'une cible à dix pas est multipliée par environ **0,35** avec 0,90, contre **0,74** avec 0,97. C'est une hypothèse sur la valeur des opportunités lointaines, pas une nouvelle probabilité de combat ni un facteur appliqué à toute la recherche.

Les poids interviennent aussi dans le classement des candidats avant sélection : **les mécanismes du générateur restent identiques, mais la liste retenue peut changer**. Ce n'est donc pas une ablation où seules les feuilles d'un arbre strictement identique changeraient.

### Pourquoi ce choix est raisonnable

Buro [R8] justifie l'étude expérimentale de la combinaison de caractéristiques pour évaluer des positions. Nous n'avons pas reproduit sa régression logistique : notre réglage est un criblage limité de paramètres par parties simulées.

**Article récent :** Chen et al. (2024) [R9] rapportent une amélioration d'évaluation exploitant des bases de finales dans un autre jeu. Ce travail motive l'étude de l'évaluation comme composant distinct. Nous n'utilisons aucune de ces bases et cet article ne justifie pas la valeur 0,97. Langorou [H2] constitue également une inspiration applicative pour comparer des jeux de coefficients par tournoi.

### Pourquoi le conserver sans le déclarer meilleur

Sur les huit parties de validation du candidat, le score est de **0,625** (2 victoires, 6 nuls, 0 défaite), contre 0,500 pour le contrôle AB3 ; un nul vaut un demi-point. Il ne s'agit pas d'un taux de victoire de 62,5 %. Les cartes de validation sont distinctes des cartes d'entraînement et des cartes du cours ; les budgets simulés sont courts (0,08 s puis 0,2 s).

Sur le serveur à 200 coups maximum, le **nouvel** AB7 obtient ensuite **2 victoires et 2 défaites**, moyenne **0,555 s** : le gain simulé n'est pas confirmé comme une supériorité sur AB3. Nous le conservons pour étudier l'évaluation, avec priorité moindre qu'AB2 et AB6. L'ancien AB7 et ses résultats ne sont pas confondus avec ce candidat.

## 6. Ce que nos expériences permettent de défendre

| Configuration | Statut retenu | Résultat contre AB3 à 200 coups maximum | Temps moyen / maximum |
|---|---|---|---|
| **AB2** | Candidat prioritaire, recherche relativement économique | 3 V / 1 N / 0 D | 0,370 / 1,507 s |
| **AB6** | Candidat prioritaire, modèle de combat probabiliste | 3 V / 0 N / 1 D | 1,473 / 1,513 s |
| **AB3** | Référence de sélection et coordination | Comparateur des 16 parties | 0,578 / 1,513 s |
| **Nouvel AB7** | Variante d'évaluation à conserver | 2 V / 0 N / 2 D | 0,555 / 1,503 s |

Source : [campagne complète et logs](server-runs/2026-10-26/long-200/SUMMARY.md), commit de résultats `9324fe9`. Deux cartes, deux ordres de connexion, quatre parties par challenger ; AB0 est aussi présent comme témoin dans les données. AB2 et AB6 ne se sont pas affrontés directement.

La campagne utilise 200 demi-coups maximum, dix minutes maximum, deux secondes serveur et 1,5 seconde de calcul interne par décision. Les 200 coups sont notre protocole local, pas une limite officielle du tournoi établie. Les règles sont sélectionnées explicitement avec `server-v3.2.1`.

Les 16 verdicts ont été confirmés dans WPF. Zéro faute, secours interne, occurrence de fallback ou alerte au-dessus de 1,8 s est observé ; 125 tests Python réussissent. Cependant, **12 parties atteignent le plafond et présentent des répétitions de positions**. Un seul nul ne signifie donc pas douze stratégies de combat convaincantes. Les effectifs et verdicts sont relevés visuellement lorsque le texte accessible est périmé ; les difficultés d'affichage sont documentées dans le rapport.

Les combats sont aléatoires, l'échantillon est petit et les réglages proviennent d'une recherche limitée. Les garanties théoriques d'un article ne deviennent pas des garanties sur notre jeu tronqué. La pratique récente de Stockfish/Fishtest [R10] soutient la démarche de comparer des versions par parties et mesures de performance ; elle ne valide ni notre échantillon ni un Elo transférable.

## 7. Réglages exacts et traçabilité

Les quatre profils partagent `width=6`, `max_depth=8`, `extra=0` et `tt_size=50000`. En recherche chronométrée, les profils itératifs partent de la profondeur 1 ; le `depth=1` conservé dans la spécification ne les limite pas à un seul niveau. `qdepth`, `qwidth` et `aspiration` figurent dans les spécifications historiques mais n'activent ni quiescence ni aspiration dans ces quatre profils.

Les articles justifient les mécanismes, pas ces valeurs numériques. Les profils ont été sélectionnés par un petit criblage sur des cartes générées et à des budgets plus courts que le serveur. Le plafond de table est un choix d'ingénierie, sans étude isolée démontrant que 50 000 entrées sont optimales. Les parties à 200 coups sont une évaluation ultérieure de configurations figées, pas une nouvelle optimisation de leurs paramètres.

Les spécifications intégrales testées sont dans [protocol.json](server-runs/2026-10-26/long-200/protocol.json) ; les configurations, commandes et espèces réellement attribuées sont enregistrées pour chaque partie. Le code de lancement est identifié par le commit `d22df25`. Le [candidat AB7 explicite](server-runs/2026-10-26/long-200/ab7-candidate.json) contient ses poids. Aucun code d'une ancienne équipe n'est présenté comme notre moteur et le bot original des camarades est conservé.

Pour distinguer comportement et efficacité, nous avons aussi comparé des décisions sur douze positions identiques à profondeur fixe : voir [contrôle de décisions](server-runs/2026-10-26/followup-40/SUMMARY.md). Même choix à profondeur fixée ne veut pas dire même coût ; choix différents à temps égal ne prouvent pas qu'un composant précis les a causés.

## 8. Références à citer, avec leur portée

Les références classiques et celle de 2022 figuraient déjà dans le corpus local. Les appuis de 2024–2025 ci-dessous complètent la justification le 27 octobre. Les liens ont été vérifiés à cette date ; la date d'un téléchargement ou d'une indexation n'est pas l'année de publication.

- **[R1] Knuth, D. E. et Moore, R. W. (1975).** *An analysis of alpha-beta pruning*. Artificial Intelligence, 6(4), 293–326. [Éditeur et résumé](https://www.sciencedirect.com/science/article/pii/0004370275900193), DOI `10.1016/0004-3702(75)90019-3`. Fondement du noyau et de ses coupures. Notice/résumé vérifiés ; accès intégral éditeur bloqué dans cette vérification.
- **[R2] Schaeffer, J. (1989).** *The history heuristic and alpha-beta search enhancements in practice*. IEEE TPAMI, 11(11), 1203–1212. [DOI](https://doi.org/10.1109/34.42858). Référence classique pour l'ordre historique et les interactions avec les transpositions. Résumé et métadonnées vérifiés ; pas de relecture intégrale revendiquée ici, ni de reprise de ses pourcentages de gains.
- **[R3] Nipkow, T. (2024).** *Alpha-Beta Pruning*, Archive of Formal Proofs, 13 juin 2024. [Texte et preuves](https://isa-afp.org/entries/Alpha_Beta_Pruning.html). Contribution formalisée sur plusieurs variantes, dont fail-hard et fail-soft. Source récente de correction algorithmique ; pas un benchmark de notre moteur, ni une preuve formelle de notre implémentation.
- **[R4] Strass, H. (2024).** *Playing Games: Alpha-Beta Tree Search*, cours d'Algorithmic Game Theory, TU Dresden, 6 mai 2024. [Support universitaire](https://iccl.inf.tu-dresden.de/w/images/7/7c/AGT2024-04.pdf), notamment diapositive 25. Appui pédagogique récent pour ordre des coups, approfondissement et mémoire ; ce n'est pas un nouvel algorithme de recherche publié en revue.
- **[R5] Moraes, R. O., Nascimento, M. A. et Lelis, L. H. S. (2022).** *Asymmetric Action Abstractions for Planning in Real-Time Strategy Games*. JAIR, 75, 1103–1137. [Article intégral hébergé à l'université](https://webdocs.cs.ualberta.ca/~santanad/papers/2022/moraesNL22.pdf), DOI `10.1613/jair.1.13769`. Introduction et définition des abstractions consultées. Justification du principe d'AB3 ; transfert à notre générateur et à Alpha-Bêta à valider expérimentalement.
- **[R6] Ballard, B. W. (1983).** *The *-Minimax Search Procedure for Trees Containing Chance Nodes*. Artificial Intelligence, 21(3), 327–350. [Article intégral](https://www.cs.uleth.ca/~benkoczi/3750/data/ballard83-star_alpha_beta.pdf), DOI `10.1016/S0004-3702(83)80015-0`. Fondement des bornes aux nœuds de chance d'AB6 ; ne pas transférer ses gains chiffrés à notre jeu.
- **[R7] Baraniuk, N. (2025).** *Application of the ExpectiMiniMax procedure to the Backgammon*. Mémoire de licence, Brno University of Technology, soutenu le 16 juin 2025. [Notice universitaire](https://www.vut.cz/en/students/final-thesis/detail/162826?zp_id=162826), [mémoire intégral](https://www.vut.cz/www_base/zav_prace_soubor_verejne.php?file_id=279311). Chapitre 6 consulté : comparaison de facteurs d'évaluation, 200 parties par cas ; combinaison annoncée à 137/200 victoires. Recherche à trois demi-coups et temps moyen rapporté de 5,6 s sur un processeur à 14 cœurs : aucune preuve de faisabilité en deux secondes chez nous. Expérience récente utile pour AB6/AB7, avec niveau de preuve distinct d'un article de recherche évalué par les pairs ; ses statistiques ne sont pas une validation indépendante.
- **[R8] Buro, M. (1995).** *Statistical Feature Combination for the Evaluation of Game Positions*. JAIR, 3, 373–382. [Résumé auteur et article](https://arxiv.org/abs/cs/9512106), DOI de revue `10.1613/jair.179`. Fondement de l'étude des poids d'évaluation ; sa méthode d'estimation diffère de notre criblage AB7.
- **[R9] Chen, J.-C., Chen, J.-P., Wang, Y.-Y. et Hsu, T.-S. (2024).** *Improvements in Evaluation Functions Based on Endgame Databases of Chinese Dark Chess*. IEEE Conference on Games. [Notice institutionnelle et résumé des auteurs](https://scholar.ntpu.edu.tw/zh/publications/improvements-in-evaluation-functions-based-on-endgame-databases-o/), DOI `10.1109/CoG60054.2024.10645645`. Métadonnées et résumé consultés, texte intégral non obtenu. Appui récent pour étudier l'évaluation ; ni bases de finales ni coefficients de cet article implémentés dans AB7. Aucun gain numérique extrapolé.
- **[R10] Équipe Stockfish (2025 ; documentation consultée en 2026).** [Annonce officielle Stockfish 17.1, 30 mars 2025](https://stockfishchess.org/blog/2025/stockfish-17-1/) et [Fishtest, dépôt officiel](https://github.com/official-stockfish/fishtest). Témoignage technique et expérience de développement actuels : mesures de vitesse, tests de modifications et comparaison à une version de référence. Ce sont des sources de pratique expérimentale, pas des articles prouvant la force de nos configurations.

### Inspirations propres au projet, vérifiées dans les copies de l'audit

- **[H1] ZCSN / shawn-lab-ml, projet 2022**, version `a59f0b0af9a55a4c60d8964710ed25841f0b6558` : [rapport, notamment p. 3](https://github.com/shawn-lab-ml/VampiresVsWerewolves/blob/a59f0b0af9a55a4c60d8964710ed25841f0b6558/report/ZCSN_Report.pdf#page=3), [génération de mouvements](https://github.com/shawn-lab-ml/VampiresVsWerewolves/blob/a59f0b0af9a55a4c60d8964710ed25841f0b6558/utils.py). Inspiration : intentions, cibles et restriction de la combinatoire. Le classement annoncé par l'équipe n'a pas été reproduit et ne justifie pas nos performances.
- **[H2] Langorou, projet 2020**, version `178a59d6775ae0403ed2ee99afe7a02a0c6ff38d` : [rapport, notamment p. 3–6](https://github.com/langorou/langorou/blob/178a59d6775ae0403ed2ee99afe7a02a0c6ff38d/doc/report.pdf), [recherche](https://github.com/langorou/langorou/blob/178a59d6775ae0403ed2ee99afe7a02a0c6ff38d/pkg/client/min_max.go), [simulateur](https://github.com/langorou/langorou/blob/178a59d6775ae0403ed2ee99afe7a02a0c6ff38d/pkg/client/model/simulator.go). Inspiration : budget, issues pondérées et tournois de coefficients. Certaines approximations et dépendances à l'historique sont signalées dans l'audit ; nous ne reprenons pas aveuglément cette implémentation.

## 9. Proposition de présentation orale

> Nous avons conservé une famille Alpha-Bêta pour comparer des améliorations identifiables. AB2 organise efficacement la recherche avec approfondissement itératif, historique et mémoire. AB3 étudie une autre question : quels mouvements coordonnés proposer quand toutes les combinaisons sont trop nombreuses ? AB6 reprend cette sélection et représente explicitement les différentes issues des combats. AB7 garde la structure d'AB3 et règle la manière de noter les opportunités, notamment les humains éloignés.
>
> Les choix reposent sur des fondements classiques, des travaux et expériences récents, et des inspirations des anciennes équipes. Notre contribution est leur adaptation au jeu et leur comparaison dans un protocole commun, avec une traçabilité des réglages et des logs. Sur ce petit lot, AB2 et AB6 sont prioritaires ; nous ne prétendons ni avoir trouvé les paramètres optimaux ni avoir résolu le problème des répétitions.
