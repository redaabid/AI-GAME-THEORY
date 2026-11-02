# Audit de validation du 2 novembre 2026

Cet audit recoupe l'historique, les sources, les protocoles et les résultats.
Il n'ajoute pas de classement ou de sélection finale de modèles.

## Vérifications faites aujourd'hui

Les 138 tests Python passent de nouveau (9,385 s). Le journal est archivé sous
`validation/07-audit-2-novembre/unittest.log`. Aucun nouvel entraînement ni
nouvelle partie n'est lancé pendant cet audit.

Les anciennes archives WPF confirment 16 conditions à 200 demi-coups avec
verdicts UI. AB2 y avait un plafond de 8 et une largeur de 6 : quatre parties
contre AB3, bilan 3 V / 1 N / 0 D, maximum 1,507 s. Cela ne valide pas les
nouveaux réglages plafond 24 / largeur 6 ou 7 sur le serveur Windows.

Les résultats plus récents sont réellement issus du simulateur, et non WPF.
Les 80 parties de sélection et 16 de confirmation retenues comportent zéro
défaut et zéro alerte au-dessus de 1,8 s. Les tentatives contaminées par la
veille sont conservées séparément, puis leurs conditions sont rejouées.

## Limites méthodologiques vérifiées

- Sélection : 40 nuls sur contact ; 40 victoires du premier joueur sur distant.
  Le bilan égal ne démontre pas une équivalence générale des configurations.
- Les finalistes sont choisis au critère secondaire des répétitions, et non à
  un meilleur score de victoire.
- Confirmation : sur fresh-20054231, largeur 7 obtient 6 V / 0 N / 2 D ; sur
  fresh-20054232, 0 V / 8 N / 0 D. Le signal de victoire vient d'une seule carte.
- Le témoin largeur 6 n'a pas joué sur les cartes de confirmation. Ce lot ne
  montre pas que largeur 7 lui est supérieure.
- 63 des 80 parties de sélection et 10 des 16 parties de confirmation atteignent
  le plafond de 200 demi-coups. Les répétitions restent un problème stratégique.
- Les modèles comparés partagent générateur, évaluation de base et simulateur.
  Un tournoi interne ne mesure pas leur force contre les bots des autres équipes.

## Portée technique et vérifications encore absentes

Le budget de recherche 1,5 s est contrôlé de manière coopérative ; ce n'est pas
un mécanisme d'interruption matérielle garantie. Le client réel mesure aussi
la mise à jour et l'envoi réseau. Le simulateur de ces expériences enregistre
les dépassements sans appliquer la sanction de tour perdu du vrai serveur.
Les coups sont validés, mais la conformité finale doit être contrôlée sur WPF.

Le plafond et le nombre de demi-coups restants interviennent dans l'évaluation.
La limite locale de 200 ne doit donc pas être transposée au jour de l'examen
sans confirmer ses paramètres. Le profil de combat utilisé est server-v3.2.1 ;
sa différence avec le profil brief est connue et couverte par les tests. La
version et les modalités du serveur du cours actuel restent à confirmer.
Le Projectv10 retrouvé dans une ancienne équipe confirme deux secondes, mais
ce document historique ne certifie pas toutes les modalités de l'examen actuel.

Les nouvelles cartes XML sont acceptées par Python, pas encore validées sur WPF.
Le lancement réel doit fournir explicitement `--agent` : le défaut de main.py
est baseline. Il faut conserver les spécifications exactes des variantes.

Les nouveaux modules et résultats sont encore locaux au moment de cet audit ;
le contrôle Git précédent trouve la branche distante à c1bb526. Un autre membre
ne les récupérera pas encore par un simple téléchargement de cette branche.

Ces éléments ne remettent pas en cause l'existence des essais. Ils limitent
ce qu'on peut affirmer sur la conformité du paquet final et sa force à l'examen.
