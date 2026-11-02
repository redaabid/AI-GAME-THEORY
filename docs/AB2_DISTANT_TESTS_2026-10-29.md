# AB2 : cinq configurations sur les cartes éloignées

**Résultats achevés et compte rendu du 2 novembre :** [expériences AB2 datées](server-runs/julian-alpha-beta/2026-10-28_2026-11-02/README.md).
Ce document décrit la préparation ; le compte rendu consolidé inclut les trois
campagnes, les résultats bruts, le tournoi et ses limites.

Demande de Julian du 29 octobre : conserver AB2 profondeur maximale 24 et sa
prolongation tactique, ajouter largeur 7 et tester les deux pistes de progression
lointaine. Aucun ancien algorithme AB0–AB8 n'est modifié.

Paramètres exacts : [ab2_distant_profiles.json](../scripts/ab2_distant_profiles.json).
Les cinq configurations sont le témoin profondeur 24 / largeur 6, ce témoin avec
prolongation tactique de 1 demi-coup, largeur 7, guidage pondéré vers une cible,
et anticipation de trajet par simulation scriptée. Tous ont le même plafond
24 et le même budget de 1,5 seconde par décision. Un plafond n'est pas une
profondeur atteinte : les traces enregistrent la profondeur réellement terminée.

Le guidage reprend l'expérience disponible dans `agents/ab2_experiments.py` avec
poids 2000 : il valorise le rapprochement d'une cible humaine convertible ou
ennemie attaquable avec une force suffisante. Ce poids est exploratoire.

L'anticipation dans [ab2_routes.py](../agents/ab2_routes.py) prolonge l'évaluation
des feuilles calmes par au maximum huit demi-coups scriptés, en alternant les
deux camps. Tous les déplacements simulés sont légaux. Elle s'arrête avant un
contact ennemi à deux cases ou moins. Le classement initial des candidats reste
celui d'AB2. Il s'agit d'une approximation de l'évaluation par trajectoire, pas
d'une recherche minimax exhaustive sur les réponses intermédiaires, ni de
véritables transitions macro-actions. Les huit demi-coups scriptés sont
comptabilisés séparément de la profondeur Alpha-Bêta. Aucun trajet complet n'est
envoyé au serveur : seule l'action racine est jouée, puis le bot replanifie.

Protocole : deux cartes de 25 colonnes (`distant-recruitment`, symétrique avec
humains, et `distant-pursuit`, avantage initial 12 contre 8), deux rôles, une
graine de combat, quatre challengers contre le témoin : 16 parties simulées,
200 demi-coups maximum. Inverser les rôles sur la carte asymétrique est
indispensable. Les résultats sont exploratoires : une graine ne suffit pas à
classer statistiquement les variantes. Pas de validation WPF dans ce lot.

Les parties sont séquentielles et autonomes, sans appel de modèle. Le script
enregistre chaque partie terminée et un suivi de progression. Windows reçoit
une demande temporaire de maintien éveillé, libérée à la fin du processus ;
cela ne bloque pas une veille manuelle ou la fermeture du capot. Les délais
restent coopératifs et les dépassements mesurés sont conservés.

Sortie : `.local/ab2-experiments/2026-10-29-distant-five-200/`.
Lancement et reprise : dossier voisin `2026-10-29-distant-five-200-launch/`.
Une reprise avec `--resume` vérifie les paramètres, cartes et empreintes des
sources, conserve les parties terminées et recommence une partie interrompue.
Le résumé automatique contient résultats, temps, profondeur et répétitions ;
les traces complètes permettent aussi d'analyser le recrutement et le premier
contact adjacent. Les anciennes campagnes restent conservées.
