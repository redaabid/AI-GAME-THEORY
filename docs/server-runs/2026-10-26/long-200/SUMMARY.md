# Comparatif Alpha-BÃªta â€” 200 coups maximum

Ã‰tat : **complete**. 16/16 conditions terminÃ©es, 16 verdicts confirmÃ©s.

Chaque challenger affronte AB3, sur thetrap et testmap2 et dans les deux ordres de connexion. Ce lot ne constitue pas un tournoi complet ni une preuve statistique de supÃ©rioritÃ©. Les combats du serveur restent alÃ©atoires.

Machine : Intel Core i7-10875H, Windows 11 10.0.26200, Python 3.14.7 (miniconda). La campagne prÃ©cÃ©dente utilisait Python 3.14.3 ; ce changement est enregistrÃ© dans machine.json.

Serveur : MaxPlays=200, MaxGameDuration=00:10:00, MaxPlayDuration=00:00:02 ; deux bots, budget interne 1,5 s. Les 200 coups sont le protocole local, pas une limite officielle du tournoi Ã©tablie.

| Profil | Parties | V / N / D | Temps max (s) | Moyenne (s) | Alertes >1,8 s | Faults | Secours internes |
|---|---:|---|---:|---:|---:|---:|---:|
| ab3 | 16 | 6 / 1 / 9 | 1.513 | 0.578 | 0 | 0 | 0 |
| ab0 | 4 | 1 / 0 / 3 | 0.005 | 0.002 | 0 | 0 | 0 |
| ab2 | 4 | 3 / 1 / 0 | 1.507 | 0.370 | 0 | 0 | 0 |
| ab6 | 4 | 3 / 0 / 1 | 1.513 | 1.473 | 0 | 0 | 0 |
| ab7 | 4 | 2 / 0 / 2 | 1.503 | 0.555 | 0 | 0 | 0 |

AB3 est la rÃ©fÃ©rence commune : sa ligne regroupe ses diffÃ©rents adversaires. AB7 dÃ©signe exclusivement le nouveau candidat discount=0,97, dont les autres poids et paramÃ¨tres sont figÃ©s dans selection.json.

Les captures textuelles Windows peuvent contenir un Ã©tat pÃ©rimÃ© ; les corrections manuelles dans ui-evidence.json proviennent de la lecture visuelle de la fenÃªtre finale. Un rÃ©sultat inconnu reste inconnu. Aucun vainqueur nâ€™est dÃ©duit du simulateur.

[Tableau dÃ©taillÃ© et temps par bot](games/SUMMARY-200.md) Â· [DonnÃ©es agrÃ©gÃ©es](games/aggregate-200.json) Â· [Configurations et protocole](protocol.json)

Aucun code de dÃ©cision du bot original ou des variantes nâ€™a Ã©tÃ© modifiÃ© pour cette campagne. Les scripts, configurations, logs bruts et traces sont conservÃ©s. Les binaires du professeur ne sont pas inclus.

Publication GitHub : le prÃ©cÃ©dent push a Ã©tÃ© refusÃ© (403, droits collaborateur manquants). Ce rapport est conservÃ© localement sur server-runs.

## Techniques évoquées par le professeur : ce que nous avons testé

Mise à jour du 27 octobre : récapitulatif des campagnes à 40 et à 200 coups.

Les campagnes ont mis à l'épreuve les techniques discutées avec le professeur autour d'Alpha-Bêta, ainsi que des compléments de la littérature :

| Technique | Variantes où elle est active | Campagne serveur |
|---|---|---|
| **Move ordering** : ordre d'exploration des coups | AB1 à AB8 ; historique à partir d'AB2 | 40 coups ; AB2, AB3, AB6 et nouvel AB7 à 200 |
| **Iterative deepening** : dernière profondeur entièrement terminée conservée | AB1 à AB8 | 40 coups ; AB2, AB3, AB6 et nouvel AB7 à 200 |
| **Mémoire des positions** : valeurs et bornes en table de transposition | AB2 à AB8 | 40 coups ; AB2, AB3, AB6 et nouvel AB7 à 200 |
| **Mouvements coordonnés par scripts** : propositions de tours complets | AB3, AB4, AB5, AB6 et AB7 | 40 coups ; AB3, AB6 et nouvel AB7 à 200 |
| **Fenêtres étroites / aspiration** : PVS et reprises | AB4 | 40 coups |
| **Prolongations tactiques** : quiescence bornée | AB5 | 40 coups |
| **Traitement du hasard** : distributions et bornes de chance | AB6 | 40 et 200 coups |
| **Réglage de l'évaluation** | AB7 | Ancien profil à 40 ; nouveau candidat à 200, après réglage en simulation |
| **MTD(f)** : pilote à fenêtres nulles et mémoire | AB8 | 40 coups |

Les scripts produisent le mouvement du tour courant : **ce ne sont pas des macro-actions sur plusieurs tours**. AB2 possède déjà des candidats coordonnés ; AB3 enrichit cette base. AB8 dérive d'AB2 et n'inclut pas cet enrichissement par scripts.

Les campagnes comparent des configurations combinées : elles ne démontrent pas le gain isolé de chaque technique. AB4, AB5 et AB8 ont été testées à 40 coups mais ne sont pas retenues dans la sélection finale AB2/AB3/AB6/AB7. Le nouvel AB7 est distinct de l'ancien profil testé à 40 coups.

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
| 29 | 200 | True | 95 |
| 30 | 200 | True | 116 |
| 31 | 200 | True | 77 |
| 32 | 200 | True | 111 |

Les répétitions nombreuses sont une limitation stratégique à examiner. Les victoires au plafond, parfois obtenues après une longue répétition, ne démontrent pas à elles seules une meilleure conduite du combat. Quatre parties par challenger restent insuffisantes pour conclure à une supériorité statistique.

Tests Python sous Python 3.14.7 : **125 réussis en 9,916 s** (unittest.log).

Problème d’observation : la fenêtre WPF a parfois été minimisée, le texte accessible périmé et un rendu graphique figé. La campagne a attendu la lecture du verdict ; les résultats ont été relevés visuellement, avec rafraîchissement de la fenêtre lorsque nécessaire. Voir ui-refresh-note.json pour les cas documentés. Aucun verdict de simulateur n’a été substitué.

Bilan exploratoire : **AB2 (3 V / 1 N / 0 D)** et **AB6 (3 V / 0 N / 1 D)** sont les candidats à examiner en priorité. AB7 obtient 2 V / 0 N / 2 D et AB0 1 V / 0 N / 3 D. Aucun duel AB2–AB6 n’a été joué dans ce lot.

**1 nul sur 16 parties**, mais **12/16 atteignent le plafond de 200 coups et ces douze parties présentent des répétitions de positions**. Le recul des nuls ne supprime donc pas le problème de progression stratégique. Six parties finissent avec une espèce à zéro (dont deux au dernier coup) ; neuf autres victoires sont au score, avec deux espèces encore présentes, et une partie est nulle. Ce lot ne suffit pas à désigner un champion ni à isoler l’effet causal d’un composant.
