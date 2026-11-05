# Julian — avancement AB2 — publication du 4 novembre 2026

Branche : **`julian-tests-alpha-beta-2026-11-04`**. Compte GitHub : `julian5422`.
Cette branche dédiée reprend l'état publié le 2 novembre (commit `3061b57`) et
l'identifie avec une nouvelle date de publication. L'ancienne branche
`julian-tests-alpha-beta-2026-10-27` est conservée ; son historique n'est pas réécrit.

La date du 4 novembre est celle de cette publication. Les dossiers de résultats
gardent les dates réelles des expériences : ils ne sont pas renommés en laissant
croire que les matchs ont été rejoués le 4 novembre.

## Configurations de travail

| Configuration | Plafond de profondeur | Largeur | Statut publié |
|---|---:|---:|---|
| AB2 référence | 24 | 6 | Candidat prioritaire testé en parties simulées complètes |
| AB2 largeur 7 | 24 | 7 | Candidat prioritaire testé en parties simulées complètes |
| AB2 TIE largeur 7 | 24 | 7 | Expérimentation : contrôles ciblés, campagne complète non encore validée dans le dossier publié |

Les trois [spécifications exactes](scripts/ab2_retained_profiles.json) sont
sélectionnables par `main.py`. Le plafond 24 n'est pas une profondeur atteinte
systématiquement ; le budget est de 1,5 s. La validation WPF des nouveaux réglages
reste à effectuer. Les moyennes et résultats du dossier distinguent explicitement
les parties complètes, les sondes et les rejeux ciblés.

## Code général du projet

- [Base AB2 et options expérimentales](agents/ab2_experiments.py).
- [Correction TIE](agents/ab2_tie.py), [tests ciblés](tests/test_ab2_tie.py) et [positions conservées](tests/fixtures/ab2_stagnation.json).
- [Expérience de trajet](agents/ab2_routes.py), conservée pour reproduire les comparaisons, hors des trois configurations retenues.
- [Comparaisons autonomes](scripts/compare_ab2_experiments.py), [tournoi](scripts/screen_ab2_round_robin.py), [rejeux de positions](scripts/replay_ab2_tie.py).

Les agents originaux et le code des autres membres sont conservés. Aucun
algorithme n'est modifié pour créer cette nouvelle branche datée.

## Résultats et explications dans le dossier personnel

- [Synthèse étape par étape et justifications des choix](docs/server-runs/julian-alpha-beta/2026-10-28_2026-11-02/SYNTHESE_DEMARCHE_ET_CONFIGURATIONS.md).
- [Dossier des expériences du 28 octobre au 2 novembre](docs/server-runs/julian-alpha-beta/2026-10-28_2026-11-02/README.md).
- [Tableaux détaillés des 80 parties de sélection et 16 de confirmation](docs/server-runs/julian-alpha-beta/2026-10-28_2026-11-02/resultats/03-tournoi-29-31-octobre/COMPARATIF_DETAILLE.md).
- [Correction TIE : cas réels, essai négatif et vérifications](docs/server-runs/julian-alpha-beta/2026-10-28_2026-11-02/corrections-ciblees-2-novembre/README.md).
- [Point d'étape TIE capturé le 2 novembre : quatre parties, pas un bilan final](docs/server-runs/julian-alpha-beta/2026-10-28_2026-11-02/checkpoint-tie-experimental-2-novembre/README.md).
- [Archives antérieures des 26–27 octobre, dont les parties WPF](docs/server-runs/julian-alpha-beta/2026-10-26_2026-10-27/README.md).

Les résultats simulés ne sont pas présentés comme des résultats WPF. Les limites,
les égalités au premier tournoi et la sélection par répétitions sont conservées.
