# Configurations, justifications et reproduction

## Où est le code ?

| Agent | Fichier / classe | Changement principal |
|---|---|---|
| `ab2exp` | `agents/ab2_experiments.py`, AB2 de référence | Références largeur 6 et 7 préservées |
| `ab2tie` | `agents/ab2_tie.py` | Départage ciblé des égalités |
| `ab2risk` | `agents/ab2_risk.py`, AB2Risk | Issues probabilistes des combats |
| `ab2risktie` | `agents/ab2_risk_tie.py` | Combinaison hasard / départage |
| `ab2goals` | `agents/ab2_goal_coverage.py`, GoalCoverageAB2 | Couverture conditionnelle des groupes capables de recruter |
| `ab2endgame` | `agents/ab2_endgame.py`, EndgameAB2 | `leaf` : limite de coups ; `plans` : poursuite en situation perdante |
| `ab2replies` | `agents/ab2_reply_coverage.py`, ReplyCoverageAB2 | `_plans` : réponse adverse élargie ; `search` : caches distincts |

Les nouveaux agents forment une chaîne cumulative : Risk → RiskTie → Goals → Endgame → Replies. Les tests `tests/test_ab2_*.py` et leurs trois fixtures vérifient les situations corrigées et les régressions. Le code MCTS de Reda et les anciens agents ne sont pas réécrits.

## Pourquoi ces techniques ?

Les [justifications initiales AB2 / AB6](../2026-10-26_2026-10-27/justifications/AB_CONFIGURATIONS_JUSTIFICATION.md) conservent les références consultées, notamment le cours TU Dresden 2024 et Ballard 1983. Les [justifications complémentaires](../2026-10-28_2026-11-02/JUSTIFICATIONS_COMPLEMENTAIRES.md) expliquent les abstractions d'actions, la quiescence et la place des travaux plus récents.

- Approfondissement itératif, classement des actions et table de transposition : chercher efficacement sous contrainte de temps, sans supposer une recherche exhaustive.
- Nœuds de chance : traiter explicitement les issues d'un combat incertain. Le principe classique ne prouve pas qu'un profil est plus fort ; ce sont les expériences qui l'évaluent.
- Diversification des propositions : hypothèse issue des positions réellement échouées et du conseil du professeur sur le recrutement. Les deux places réservées constituent un réglage empirique.
- Fin de partie : prendre en compte le résultat au plafond connu et le risque rationnel quand on est perdant. La fenêtre de 40 n'est pas présentée comme optimale.
- Réponses adverses élargies : réponse directe à des actions V6 observées hors de notre sélection. La largeur 32 est un réglage testé, pas une valeur démontrée par une publication.

On n'ajoute pas de citation récente pour attribuer artificiellement ces corrections à un article. Leur justification précise est le diagnostic, les régressions ciblées et les comparaisons archivées. Les anciens projets ont servi d'inspiration générale, sans revendication de reproduction fidèle.

## Lancer le candidat sur le serveur

Depuis la racine, Python 3.11 ou supérieur, sans dépendance externe :

```powershell
python -B scripts/run_ab2_replies.py 127.0.0.1 5555 --max-plies 200
```

Remplacer IP, port et `--max-plies` par ceux du vrai serveur. Ce lanceur sélectionne explicitement `ab2replies`, avec 1,5 s par décision par défaut. `main.py` garde son comportement antérieur. Le fichier `scripts/ab2_profiles_2026_11_18.json` donne les spécifications exactes de tous les témoins et candidats. `max_depth=24` est une limite nominale, pas une mesure de profondeur moyenne. AB2-Replies garde sept candidats sauf à la première réponse adverse, où il peut en examiner 32 ; il ne s'agit pas de sept cases voisines choisies parmi huit.

## Rejouer des simulations et reprendre après arrêt

```powershell
python -B scripts/compare_ab2_replies.py --maps maps/endgame.xml --checkpoint .local/campaigns/ab2-replies
```

Le comparatif charge explicitement le MCTS V6 de Reda. Pour reproduire une campagne archivée, reprendre ses cartes, graines, paramètres et ordre de rôles dans son `report.json` / `plan.json` ; la commande ci-dessus est seulement un exemple. Les cartes générées utilisées sont dans les sous-dossiers d'expériences.

Chaque carte produit quatre rôles équilibrés. Deux workers jouent des parties indépendantes : la recherche AB2 elle-même reste sur un seul thread. Chaque résultat est sauvegardé avec sa trace ; relancer la même commande reprend les parties manquantes. Un changement de sources / paramètres impose un nouveau checkpoint. Le programme arrête la campagne si un résultat présente faute, timeout ou temps supérieur à 1,8 s. La protection veille automatique n'empêche pas une fermeture manuelle du capot.

## Provenance

Base d'intégration : commit Reda `8888c096ff84ce4a0dceebe96647ba98e0d5b3fa`, qui contient déjà la publication Julian précédente et les dépendances MCTS. Les rapports conservent leurs empreintes originales ; la parité AST documente l'adaptation des prototypes locaux en modules portables. Les chemins absolus historiques des logs sont des traces de provenance, pas des prérequis pour les nouveaux lanceurs.
