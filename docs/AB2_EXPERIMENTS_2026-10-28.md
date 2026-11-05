# Variantes AB2 : diagnostic et comparaison du 28 octobre 2026

**Compte rendu achevé et consolidé le 2 novembre :** [expériences AB2 datées](server-runs/julian-alpha-beta/2026-10-28_2026-11-02/README.md).
Les mentions de campagne « active » et les sélections ci-dessous décrivent les
étapes préparatoires historiques ; les résultats et incidents finaux sont dans
le compte rendu consolidé. La sélection des plafonds a évolué avant les matchs.

## Campagne active : cinq configurations maximum

À la demande de Julian, la sélection active est maintenant limitée à cinq
configurations au total : control (profondeur 8), depth24, width8 (profondeur 24),
tactical1 (profondeur 24) et repeat (profondeur 24). Les autres plafonds et le
guidage lointain restent reportés, disponibles dans `deferred_profiles`.

Campagne lancée le 28 octobre : 16 parties simulées, 200 demi-coups maximum,
budget 1,5 s/décision, thetrap et testmap2, une graine et deux rôles par duel.
depth24 affronte control ; chaque ajout affronte depth24. C'est un premier
criblage exploratoire, pas un classement statistique ni une validation WPF.
Les cartes diagnostiques lointaines ne font pas partie de cette campagne.

Sortie locale : `.local/ab2-experiments/2026-10-28-five-200/`.
`progress.json` suit le calcul, chaque partie terminée est sauvegardée en JSON,
et `SUMMARY.md` et `completed.json` sont produits à la fin. Le lancement et les
erreurs sont enregistrés dans le dossier voisin `2026-10-28-five-200-launch`.
Le script travaille séquentiellement sans appel à un modèle ni suivi Codex par
coup. Les réglages restent figés pendant le lot. Aucun résultat n'est encore
annoncé dans cette section.

Le contrôle préalable des cinq configurations a réussi : 8 tests ciblés et
24 parties courtes sans défaut. Les paragraphes suivants décrivent aussi les
étapes et sélections préparatoires, remplacées par cette campagne active.

Objectif : tester les conseils du professeur sur la portée de recherche et les
répétitions, à partir du même AB2. Les résultats historiques AB0–AB8 restent
inchangés. Ces nouveaux profils sont expérimentaux, pas encore optimisés.

Le code additionnel est dans [agents/ab2_experiments.py](../agents/ab2_experiments.py).
Les paramètres exacts sont dans [le manifeste](../scripts/ab2_experiment_profiles.json).
Le témoin est `ab2:width=6,depth=1,max_depth=8,extra=0`.

| Profil | Changement par rapport au témoin |
|---|---|
| depth12 | Plafond 12 demi-coups |
| depth16 | Plafond 16 demi-coups |
| depth24 | Plafond 24 demi-coups |
| depth64 | Plafond 64 demi-coups, maximum accepté par le moteur |
| width8 | Base depth24, 8 tours candidats par nœud |
| tactical1 | Base depth24, prolongation de 1 demi-coup, 2 candidats de capture maximum |
| repeat | Base depth24, malus historique de répétition : 5 000 unités de score |

Sélection recentrée à la demande de Julian : sept variantes actives et le témoin.
Les variantes de largeur, tactique et répétition se comparent aussi à depth24
pour distinguer leur effet de celui du plafond augmenté. Le guidage lointain et
ses combinaisons sont reportés. Largeur 10, prolongation 2 et combinaisons sont
également conservées dans `deferred_profiles`, sans figurer dans la campagne
par défaut. Aucun profil n'est déclaré faible à partir des seuls contrôles courts.
Un plafond de 64 n'implique pas que la recherche atteindra 64 : le budget reste
1,5 s et seul le dernier approfondissement terminé fournit le résultat.

## Sens exact des changements

L'approfondissement itératif conserve le dernier résultat terminé. Le budget
reste 1,5 s, avec des vérifications coopératives du temps : ce n'est pas une
garantie temps réel stricte. Élargir la recherche peut diminuer la profondeur
terminée. Le générateur ne devient pas exhaustif avec une largeur de 10.

La prolongation reprend le mécanisme déjà présent dans le moteur : à la feuille,
elle explore des captures de créatures ou d'humains, sans stand-pat, avec une
limite explicite de profondeur et de largeur. Elle ne certifie pas que tous les
combats sont résolus et peut écarter une défense sans capture.

La répétition compare le plateau complet et le joueur au trait, en ignorant le
numéro absolu du demi-coup. Elle utilise les plateaux réellement observés avant
nos décisions, fournis par TurnContext.history. Elle ne pénalise pas une simple
case revisitée et n'invente aucune règle de nul. Le malus est appliqué aux feuilles
correspondantes, à partir de la deuxième occurrence, avec un plafond de trois
malus. Il n'ajoute pas une détection de tous les cycles internes à l'arbre.
Les caches de valeurs et d'historique de classement sont vidés à chaque décision
pour les profils dépendant de l'historique ou de la cible : une ancienne valeur
ne doit pas être réutilisée avec une autre fonction d'évaluation. Ce choix prudent
a aussi un coût en calcul à mesurer.

Le guidage choisit au début de chaque décision une cible humaine convertible ou
une armée ennemie attaquable avec au moins 1,5 fois ses effectifs par un groupe.
Le choix privilégie le rapport effectifs de la cible / (1 + distance). La fonction
récompense la réduction de distance d'un groupe encore assez fort. La cible peut
changer au tour suivant ; ce n'est pas un plan persistant sur plusieurs tours.
L'évaluation d'origine considère déjà la course aux humains : ce terme ajoute
un gradient spatial, notamment pour la poursuite d'un ennemi éloigné. Aucun terme
ne peut remplacer le verdict d'une position terminale. Les poids restent des
hypothèses à régler, pas des valeurs optimales établies.

Les profils gardent le simulateur déterministe d'AB2 pour la recherche. Il n'y a
ni téléportation ni saut des réponses adverses : chaque transition représente
un tour légal. Une abstraction temporelle des trajets serait une expérience
supplémentaire, non implémentée ici.

## Protocole disponible

[compare_ab2_experiments.py](../scripts/compare_ab2_experiments.py) confronte chaque
variante au témoin, séquentiellement afin de limiter la concurrence CPU. Il utilise
trois cartes : recrutement à longue distance (25 colonnes), poursuite à longue
distance avec avantage matériel, et contact tactique. Les fichiers XML exportés
dans chaque sortie pourront aussi servir au vrai serveur Windows. Des cartes
supplémentaires peuvent être ajoutées avec `--map chemin.xml`.

Le protocole complet par défaut utilise 200 demi-coups, 1,5 s par décision,
deux graines de combat et les deux rôles, soit 48 parties simulées pour les quatre
variantes actives et les trois cartes. La campagne active ci-dessus restreint
explicitement ce défaut aux deux cartes du cours et à une graine (16 parties).
Les fichiers JSON sont écrits après chaque partie,
avec les traces, temps, profondeurs, répétitions, premier contact adjacent,
effectifs finaux, défauts et configurations. Le répertoire de sortie doit être neuf.
Il s'agit d'un comparatif en simulateur ; les finalistes devront jouer sous WPF.

Depuis la racine de ce checkout :

```powershell
python -B scripts/compare_ab2_experiments.py --smoke --output .local/ab2-experiments/nouveau-controle
python -B scripts/compare_ab2_experiments.py --output .local/ab2-experiments/nouvelle-campagne
```

`--smoke` réduit le budget à 0,02 s et la limite à 12 demi-coups : il vérifie le
fonctionnement, pas la force de jeu. La grande campagne n'est pas lancée par
les tests unitaires. `--profiles depth12 width8` permet une sélection limitée.

Avant de présenter une combinaison comme meilleure : comparer les changements
isolés, régler les poids sur d'autres cartes/graines, figer les paramètres, puis
utiliser un lot final indépendant et le serveur réel. Mesurer aussi les cycles
et la progression : une victoire au plafond ne prouve pas une capacité à conclure.

## Vérifications effectuées

- 133 tests unitaires réussis, dont 8 nouveaux tests : équivalence avec AB2 quand
  les options sont désactivées, historique/caches, verdicts terminaux, captures,
  guidage à distance, légalité et interruption temporelle.
- Contrôle court de la sélection initiale (avant ce recentrage) : 60 parties simulées, zéro défaut, zéro bootstrap, zéro alerte
  supérieure à 1,8 s ; budget de 0,02 s, donc aucun classement de force déduit.
- Données locales : `.local/ab2-experiments/2026-10-28-smoke/`.
- Sondes supplémentaires à 1,5 s :
  `.local/ab2-experiments/2026-10-28-probes-1_5s/probes.json`.
  Les 33 décisions de la sélection initiale (témoin et dix variantes, trois positions) sont légales,
  sans défaut et sous 1,8 s. Sur la poursuite simple, depth12 termine à 12
  contre 8 pour le témoin. Sur le contact tactique, width10 termine à 6
  contre 7 pour le témoin : ce sont des observations ponctuelles, pas un classement.

Aucune nouvelle partie WPF, publication GitHub ou campagne complète à 200
demi-coups n'est déclarée terminée par ce document.
