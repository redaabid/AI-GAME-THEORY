# AB7 — réglage des poids à recherche identique à AB3
60 parties simulées d’entraînement puis 24 parties de validation séparée, à 40 demi-coups. Aucun serveur WPF lancé. Les cartes du cours et les anciens résultats restent inchangés.
Budget : 0.08 s en entraînement, 0.2 s en validation. Ces budgets courts ne garantissent pas un gain au budget serveur de 1,5 s.
| Profil évalué | V / N / D | Score | Faults | Retards |
|---|---|---:|---:|---:|
| baseline | 1 / 6 / 1 | 0.500 | 0 | 0 |
| discount-0.75 | 2 / 5 / 1 | 0.562 | 0 | 0 |
| discount-0.97 | 2 / 6 / 0 | 0.625 | 0 | 0 |

Gain observé sur ce lot : **True**. Décisions différentes à profondeur fixe : **1/12**.

Profil distinct expérimental : `ab7:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000,weights={'material': 1.0, 'humans': 0.8, 'discount': 0.97, 'threat': 0.7, 'groups': 0.1}`.

Eight validation games per profile; no WPF validation, no 200-ply test. Do not replace the historical profile or claim statistical superiority.
