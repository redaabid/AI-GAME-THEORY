# Comparatif Alpha-BÃªta â€” 200 coups maximum

Ã‰tat : **running**. 13/16 conditions terminÃ©es, 12 verdicts confirmÃ©s.

Chaque challenger affronte AB3, sur thetrap et testmap2 et dans les deux ordres de connexion. Ce lot ne constitue pas un tournoi complet ni une preuve statistique de supÃ©rioritÃ©. Les combats du serveur restent alÃ©atoires.

Machine : Intel Core i7-10875H, Windows 11 10.0.26200, Python 3.14.7 (miniconda). La campagne prÃ©cÃ©dente utilisait Python 3.14.3 ; ce changement est enregistrÃ© dans machine.json.

Serveur : MaxPlays=200, MaxGameDuration=00:10:00, MaxPlayDuration=00:00:02 ; deux bots, budget interne 1,5 s. Les 200 coups sont le protocole local, pas une limite officielle du tournoi Ã©tablie.

| Profil | Parties | V / N / D | Temps max (s) | Moyenne (s) | Alertes >1,8 s | Faults | Secours internes |
|---|---:|---|---:|---:|---:|---:|---:|
| ab3 | 13 | 5 / 1 / 6 | 1.513 | 0.514 | 0 | 0 | 0 |
| ab0 | 4 | 1 / 0 / 3 | 0.005 | 0.002 | 0 | 0 | 0 |
| ab2 | 4 | 3 / 1 / 0 | 1.507 | 0.370 | 0 | 0 | 0 |
| ab6 | 3 | 1 / 0 / 1 | 1.513 | 1.467 | 0 | 0 | 0 |
| ab7 | 2 | 1 / 0 / 1 | 1.502 | 0.337 | 0 | 0 | 0 |

AB3 est la rÃ©fÃ©rence commune : sa ligne regroupe ses diffÃ©rents adversaires. AB7 dÃ©signe exclusivement le nouveau candidat discount=0,97, dont les autres poids et paramÃ¨tres sont figÃ©s dans selection.json.

Les captures textuelles Windows peuvent contenir un Ã©tat pÃ©rimÃ© ; les corrections manuelles dans ui-evidence.json proviennent de la lecture visuelle de la fenÃªtre finale. Un rÃ©sultat inconnu reste inconnu. Aucun vainqueur nâ€™est dÃ©duit du simulateur.

[Tableau dÃ©taillÃ© et temps par bot](games/SUMMARY-200.md) Â· [DonnÃ©es agrÃ©gÃ©es](games/aggregate-200.json) Â· [Configurations et protocole](protocol.json)

Aucun code de dÃ©cision du bot original ou des variantes nâ€™a Ã©tÃ© modifiÃ© pour cette campagne. Les scripts, configurations, logs bruts et traces sont conservÃ©s. Les binaires du professeur ne sont pas inclus.

Publication GitHub : le prÃ©cÃ©dent push a Ã©tÃ© refusÃ© (403, droits collaborateur manquants). Ce rapport est conservÃ© localement sur server-runs.

## Fin des parties et répétitions

Les traces reconstruisent les états avant les mouvements ; le dernier état reconstruit ne remplace pas les effectifs finaux lus dans WPF. Une répétition inclut le joueur au trait. Le compteur ne constitue pas une règle de nul du serveur.

| Partie | Dernier coup observé | Plafond atteint | États répétés |
|---|---:|---|---:|
| 17 | 36 | False | 0 |
| 18 | 200 | True | 162 |
| 19 | 200 | True | 162 |
| 20 | 34 | False | 0 |
| 21 | 200 | True | 172 |
| 22 | 35 | False | 0 |
| 23 | 200 | True | 162 |
| 24 | 200 | True | 162 |
| 25 | 200 | True | 107 |
| 26 | 92 | False | 0 |
| 27 | 200 | True | 105 |
| 28 | 200 | True | 97 |
| 29 | ? | ? | ? |

Les répétitions nombreuses sont une limitation stratégique à examiner. Les victoires au plafond, parfois obtenues après une longue répétition, ne démontrent pas à elles seules une meilleure conduite du combat. Quatre parties par challenger restent insuffisantes pour conclure à une supériorité statistique.

Tests Python sous Python 3.14.7 : **125 réussis en 9,916 s**.
