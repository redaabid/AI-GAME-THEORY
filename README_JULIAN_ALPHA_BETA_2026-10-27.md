# Julian — tests d’optimisation Alpha-Bêta — 27 octobre 2026

**Archive de la publication précédente.** L'avancement AB2 dispose maintenant
d'une [entrée datée du 4 novembre](README_JULIAN_ALPHA_BETA_2026-11-04.md), sur la
branche `julian-tests-alpha-beta-2026-11-04`. Les mentions de l'ancienne branche
ci-dessous décrivent les publications antérieures.

**Mise à jour documentaire du 2 novembre :** [compléments AB2, cartes et tournoi](docs/server-runs/julian-alpha-beta/2026-10-28_2026-11-02/README.md).
[Synthèse chronologique et trois configurations de travail, TIE largeur 7 inclus](docs/server-runs/julian-alpha-beta/2026-10-28_2026-11-02/SYNTHESE_DEMARCHE_ET_CONFIGURATIONS.md).
**AB2 référence et AB2 largeur 7 sont les candidats prioritaires testés en
simulateur ; TIE largeur 7 reste expérimental, sa campagne complète étant en cours.**
La [correction ciblée du départage des coups AB2](docs/server-runs/julian-alpha-beta/2026-10-28_2026-11-02/corrections-ciblees-2-novembre/README.md)
est isolée dans `agents/ab2_tie.py` ; les AB2 précédents restent disponibles.
Ce nouveau dossier documente les conseils rapportés du professeur, les essais
du 28 au 31 octobre et la correction TIE expérimentale du 2 novembre.
Il complète la livraison sur la même branche personnelle ; la campagne TIE
en cours est présentée uniquement sous forme d'un point d'étape incomplet.
L'[index personnel daté](docs/server-runs/julian-alpha-beta/README.md) distingue
les deux périodes. Les résultats ci-dessous des 26–27 octobre restent historiques.

Branche de travail : **`julian-tests-alpha-beta-2026-10-27`**. Ce fichier identifie explicitement les ajouts de Julian sans déplacer les modules Python ni casser leurs imports. `main` est conservée ; l’ancienne branche `server-runs` n’est pas supprimée.

## Code exact et architecture

| Élément | Fichier |
|---|---|
| Moteur modulaire et profils AB0 à AB8 | [agents/ab_variants.py](agents/ab_variants.py) |
| Registre commun des agents | [agents/__init__.py](agents/__init__.py) |
| Génération commune des candidats | [candidates.py](candidates.py) |
| Propositions coordonnées et scripts | [lookahead.py](lookahead.py), [playbook.py](playbook.py), [macro.py](macro.py) |
| Évaluation et poids | [evaluation.py](evaluation.py) |
| Règles et simulation | [combat.py](combat.py), [simulator.py](simulator.py) |
| Client et point de lancement | [main.py](main.py), [client.py](client.py) |
| Tests des variantes | [tests/test_ab_variants.py](tests/test_ab_variants.py) |
| Description des options | [docs/AB_VARIANTS.md](docs/AB_VARIANTS.md) |

Les modules communs et les agents originaux sont les contributions du projet, pas tous des fichiers créés par Julian. Nos profils ajoutés sont isolés dans `agents/ab_variants.py`. Le rangement ne modifie aucun de ces fichiers de code.

## Scripts expérimentaux

- [Campagnes sur serveur WPF](scripts/run_ab_server.py) : référence AB3, preuve UI requise, arrêt sur problème.
- [Synthèse des résultats](scripts/summarize_ab_server.py) et [diagnostic des répétitions](scripts/diagnose_ab_draws.py).
- [Comparaison de décisions](scripts/compare_ab_decisions.py).
- [Criblage des profils](scripts/benchmark_ab_variants.py) et [réglage d’AB7](scripts/tune_ab7_weights.py).
- [Assemblage des contrôles à 40 coups](scripts/report_ab_followup.py).

## Dossier personnel daté

[Ouvrir les résultats et documents de Julian](docs/server-runs/julian-alpha-beta/2026-10-26_2026-10-27/README.md).

- [Configurations exactes testées, poids inclus](docs/server-runs/julian-alpha-beta/2026-10-26_2026-10-27/tests-200-coups/protocol.json).
- [Résultats des 16 parties longues](docs/server-runs/julian-alpha-beta/2026-10-26_2026-10-27/tests-200-coups/SUMMARY.md).
- [Justifications pour le professeur](docs/server-runs/julian-alpha-beta/2026-10-26_2026-10-27/justifications/AB_CONFIGURATIONS_JUSTIFICATION.md).
- [Passation](docs/server-runs/julian-alpha-beta/2026-10-26_2026-10-27/passation/HANDOFF_GOOGLE.md).

AB2 et AB6 sont prioritaires ; AB3 et le nouvel AB7 restent conservés. Les 125 tests réussis et les résultats sont ceux de la campagne archivée. Aucun nouveau test de jeu n’est lancé pour ce changement de rangement. Le script WPF ne connaît pas de référence arbitraire : ne pas supposer qu’il lance automatiquement AB2 contre AB6.
