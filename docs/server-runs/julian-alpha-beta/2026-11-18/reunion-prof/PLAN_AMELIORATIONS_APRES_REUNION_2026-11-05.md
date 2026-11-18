# Suite à la réunion avec le professeur — audit et prochaines améliorations
Date : 5 novembre 2026.

## 1. « Sauter des cases » : clarifier avant de modifier
- Un déplacement envoyé au serveur reste vers une des huit cases adjacentes. Aucun saut physique de plusieurs cases n'est autorisé par notre validation.
- AB2 anticipe déjà plusieurs déplacements, avec alternance des deux camps. Ce n'est donc pas une fonctionnalité de déplacement oubliée.
- La formule du professeur semble viser la capacité à prendre en compte un objectif éloigné. Elle ne suffit pas à imposer une technique précise : évaluation à distance, abstraction de trajets et macro-actions sont des possibilités différentes.
- Nous avons déjà essayé le guidage et une simulation de trajet des deux camps. Leurs résultats n'ont pas démontré un gain suffisamment robuste pour les retenir.
- Rechercher plus profondément ne corrige pas forcément une évaluation qui donne la même note à tous les déplacements éloignés.

## 2. Ce qui a été vérifié aujourd'hui
Diagnostic local reproductible : [.local/research/prof-feedback-2026-11-05/diagnostic.py](.local/research/prof-feedback-2026-11-05/diagnostic.py).
Résultats détaillés : [diagnostic.json](.local/research/prof-feedback-2026-11-05/diagnostic.json).
Ces deux fichiers sont ignorés par Git ; les joindre explicitement à un futur dossier de résultats si nécessaire.

Six positions synthétiques : humains accessibles, recrutement dangereux, poursuite sans humains, élimination immédiate, armée forte face à une petite armée et dernière chance avant la limite.
AB2 référence et départage expérimental, largeurs 6 et 7, profondeur fixe de 3 demi-coups.
Comparaison avec un minimax sans coupures, sur les mêmes candidats et la même évaluation ; cache froid, cache réutilisé puis désactivé.

**72 vérifications : aucune différence de valeur avec ce minimax et aucune faute d'agent.**
Cela ne vérifie ni l'arbre de tous les coups légaux, ni toutes les profondeurs, ni le serveur, ni le respect du temps. Ce n'est pas une preuve d'absence de bug.

| Cas | Observation ciblée | Ce qu'on en déduit |
|---|---|---|
| Humains accessibles | Les deux versions se rapprochent des humains. | Ce cas simple fonctionne ; tester aussi la concurrence et plusieurs groupes. |
| Recrutement dangereux | Elles évitent la conversion directement exposée dans cette position. | Ne pas ajouter une prime aveugle au recrutement. |
| 18 contre 12, ennemis éloignés, sans humains | En largeur 7, référence : distance 11 inchangée ; départage : distance réduite à 10, même valeur de recherche. | Une égalité d'évaluation peut produire une stagnation. |
| Élimination garantie immédiatement accessible | Les deux versions éliminent l'ennemi dans ce test à cache froid. | Conserver les régressions avec cache réutilisé et attaques coordonnées. |
| 10 contre 2, distance initiale 2 | Référence s'éloigne ; départage maintient la distance. | Aucun des deux ne conclut dans ce simple test de premier coup. Il faut analyser la poursuite sur plusieurs tours et l'initiative. |
| 2 contre 10, juste avant la limite | Les deux versions évitent l'attaque et évaluent leur continuation perdante. | L'approximation déterministe peut masquer l'intérêt d'un dernier pari. |

Dernier cas, sous le profil local server-v3.2.1 : l'attaque directe vaut -1 000 000 dans le modèle déterministe, contre environ -881 000 en intégrant les issues du seul combat jusqu'au terme. Ce calcul isole une limite du modèle ; il ne démontre pas la force d'une nouvelle variante complète. Le profil brief traite certains combats autrement : confirmer le profil du tournoi avant de fixer une règle.

## 3. Modifications à privilégier
### A. Terminer la validation du départage existant
- Conserver AB2 référence largeur 6 et AB2 largeur 7 comme témoins inchangés.
- Le départage expérimental ne modifie pas les poids d'évaluation : il réordonne les choix à la racine selon score statique, répétitions récentes puis classement stratégique. Le meilleur score recherché reste prioritaire.
- La campagne complète est interrompue : 13 parties sur 16 enregistrées, dernier point le 2 novembre. Aucun processus Python de campagne actif lors du contrôle du 5 novembre.
- Finir les trois parties manquantes avec les sources gelées avant de modifier les agents : la reprise vérifie leurs empreintes.
- Les améliorations observées sur des cas ciblés ne suffisent pas à déclarer ce départage meilleur en général.

### B. Corriger la progression seulement à partir des échecs
- Rejouer les situations de stagnation sur plusieurs tours avec historique et cache réellement réutilisés.
- Sans humains, une armée suffisamment forte doit pouvoir poursuivre ; une armée faible ne doit pas être forcée à se suicider.
- Si le départage ne suffit pas, essayer une préférence de progression conditionnelle : rapprochement vers une cible attaquable, prise en compte de la réponse adverse et de la possibilité de regrouper nos troupes.
- Ne pas remettre un malus global à toutes les répétitions : l'ancien essai n'a pas amélioré les résultats et peut pénaliser une bonne défense.
- Comparer correction seule et référence ; ne pas modifier simultanément largeur, profondeur et évaluation.

### C. Mieux traiter les combats décisifs
- Distinguer victoire garantie, combat risqué évitable et pari de dernière chance.
- Examiner qui peut attaquer en premier après notre déplacement : être majoritaire n'annule pas tout risque si l'ennemi engage le combat.
- Essayer un traitement probabiliste ciblé des combats critiques en réutilisant les outils de distributions déjà présents pour AB6.
- Ce serait une expérimentation à mesurer, pas une amélioration déjà démontrée. Comparer d'abord sur de petites positions avec calcul exact.
- Éviter une interdiction absolue des attaques aléatoires : le professeur a explicitement décrit des exceptions en fin de partie.

## 4. Tests à refaire, dans l'ordre
1. **Recherche** : minimax indépendant à petite profondeur ; cache froid/réutilisé/désactivé ; deux camps ; variantes 6 et 7 ; plateaux historiques et situations générées.
2. **Comportements** : humains accessibles ou trop nombreux ; humains sous menace ; plusieurs groupes ; forte armée qui poursuit ; faible armée qui fuit ; attaque garantie immédiate ; dernier pari ; risque lié au premier attaquant.
3. **Rejeux longs ciblés** : mesurer élimination, recrutement, premier contact, répétitions et résultat. Une absence de répétitions ne suffit pas si le bot perd davantage.
4. **Parties comparables** : mêmes cartes, mêmes graines, inversion du camp et du premier joueur ; distinguer cartes de réglage et cartes nouvelles. D'abord terminer le lot expérimental existant.
5. **Adversaire différent** : comparer aux versions exactes de MCTS préparées par Reda, et conserver un témoin AB2. Ne pas déduire la force générale des seules parties entre AB2.
6. **Vrai serveur** : lancer les candidats retenus sur WPF, relever le verdict réel et le temps complet depuis UPD jusqu'à MOV ; zéro faute et aucun dépassement de 2 secondes.
7. **H208** : même protocole sur les machines de l'école, avec marge sous les 2 secondes. Les temps de notre PC ne valident pas ces machines.
8. **Lancement final** : tester l'IP et le port variables, le modèle effectivement lancé, END/BYE et remise à zéro entre parties. Sans option explicite, main.py lance encore baseline.

## 5. Ce que le professeur attend du rapport
- Expliquer le cheminement : variantes initiales, AB2/AB6, profondeur, cartes éloignées, largeur, prolongation tactique, répétitions puis correction du départage.
- Pour chaque essai : changement précis, témoin, protocole, résultat, limite et décision de garder ou abandonner.
- Donner la profondeur réellement terminée moyenne et le temps moyen/maximal, pas seulement le plafond configuré.
- Ne pas écrire que largeur 7 bat largeur 6 : ce n'est pas démontré par les comparaisons disponibles.
- Séparer simulations, tests unitaires, rejeux ciblés et parties du vrai serveur ; identifier les essais invalidés par la veille du PC.
- Relier les explications au code et aux sources scientifiques ; décrire honnêtement les contributions et l'aide reçue.

| Fonctionnement | Fichier / point d'entrée |
|---|---|
| Déplacements adjacents autorisés | game.py : GameState.validate_moves |
| Sélection initiale des candidats | candidates.py : generate_candidates |
| Simulation et sélection des plans | agents/ab_variants.py : Variant._plans |
| Ordre d'exploration | agents/ab_variants.py : Variant.plans |
| Alpha-Bêta et cache | agents/ab_variants.py : Variant.search |
| Approfondissement et échéance | agents/ab_variants.py : Variant.choose_moves |
| Départage expérimental | agents/ab2_tie.py : AB2Tie.plans / search |
| Évaluation des humains et menaces | evaluation.py : evaluate / race_owners |
| Combats approximatifs | combat.py : expected_battle |
| Issues probabilistes | agents/ab_variants.py : battle_distribution / exact_successors |
| IP, port, agent, temps | main.py : main |

## État de cette intervention
Audit du code et diagnostic ciblé effectués. Aucun code des bots modifié, aucune nouvelle grande campagne lancée, aucun commit ni push. Ce document propose l'ordre des améliorations ; il ne présente pas celles-ci comme déjà implémentées ou validées.

