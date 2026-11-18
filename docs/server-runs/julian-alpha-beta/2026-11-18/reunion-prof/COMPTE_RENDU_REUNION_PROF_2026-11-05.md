# Réunion avec le professeur du 5 novembre 2026

Vampires vs Werewolves  •  Notes de Julian pour le groupe

À retenir : tester le programme sur les machines de H208, examiner les oscillations et les combats, comparer aux MCTS et rendre la démarche expérimentale vérifiable dans le rapport.

Ce document conserve d’abord l’échange fourni, puis résume les remarques du professeur et les actions pour nous. Il ne certifie aucune nouvelle validation serveur ou machine du campus.


# 1 Restitution de la conversation

Source : retranscription transmise dans la conversation, avec des repères de 14 h 34 à 14 h 40. Aucun enregistrement audio n’a été consulté. Les formulations et erreurs de transcription sont conservées ; seuls les paragraphes et la présentation sont aérés. Les réponses de Julian sont celles rapportées dans le fil, sans certification d’un verbatim audio. L’échange antérieur sur la largeur est ajouté et identifié comme complément.


## Échange antérieur sur la largeur  Horaire non indiqué

Professeur

Pardon. Quand tu dis largeur 6 finalement dans ton arbre, ça veut dire que tu ne considères que six des huit cases autour de toi.


## Réponse sur la largeur  Complément fourni plus haut dans le fil

Réponse préparée pour Julian

Pas exactement : on garde au maximum six actions candidates pour le tour complet, pas six cases voisines. Une action peut déplacer plusieurs groupes en même temps, les regrouper ou les diviser. On génère plusieurs possibilités, on les classe, puis Alpha-Bêta explore les six retenues, pour nous comme pour l’adversaire.


## Comportements attendus et combats aléatoires  Avant le repère 14 h 34

Passage attribué au professeur dans la retranscription fournie

Ne pas oubluier que votre alpha beta est Capable de sauter des cases, donc logiquement s'il reste encore des trucs à bouffer, elle n'est pas censée osciller. C'est-à-dire aller en avant et en arrière. Elle ne doit plus savoir quoi faire tant qu'il ne reste plus rien sur la carte, ce qui est logique par contre puisque c'est la fin de la partie. Donc de toute façon, quoi qu'il arrive, voilà. Donc soit si tu veux, alors il y a différentes cas de figure. Tant qu'il reste des humains que vous pouvez manger parce que vous êtes suffisamment nombreux, logiquement elle est censée s'approcher des humains tout en essayant de s'éloigner de l'adversaire. S'il n'y a plus d'humains, s'il n'y a plus que des ennemis, elle est censée les attaquer si elle est engagée cinq fois plus nombreuse que les ennemis.

Si elle est en dessous, elle a plutôt tendance à les fuir parce qu'elle sait qu'elle va se faire bouffer. Donc voilà. Après prendre en compte, il y avait une autre remarque que je voulais faire un peu plus tôt, c'était sur les batailles aléatoires et le fait de considérer les notions. Effectivement, les notions ça rajoute une couche, donc ça rajoute finalement une profondeur, etc. Et en fait il n'y a aucun, je pense que je vous l'avais déjà dit, mais il n'y a aucun intérêt de faire une bataille aléatoire avant la fin de la partie. Ou alors parce que c'est une stratégie pour embêter notre adversaire, l'occuper ailleurs ou un truc comme ça, pourquoi pas. Mais à la base, il n'y a aucun intérêt parce qu'il y a un risque que vous perdiez même si vous êtes plus nombreux qu'eux, mais en dessous d'un 1,5 quoi.

Donc si vous êtes 1,4 fois plus nombreux qu'eux, vous risquez de perdre. Donc il n'y a aucun intérêt de, voilà. Sauf si on est en fin de partie que vous êtes deux et qu'ils sont dix. De toute façon vous avez déjà perdu. Donc autant tenter le tout pour le tout et essayer de les attaquer. Ok. Voilà. En revanche, le truc inverse est vrai aussi, c'est-à-dire que si vous êtes en fin de partie, que vous êtes dix et que votre adversaire est deux et qu'il s'approche de vous, vous avez plutôt intérêt soit à vous approcher pour les attaquer si le nombre de cases permet à vous d'attaquer. Mais en tout cas si c'est le nombre de cases entre vous deux fait que c'est eux qui vont attaquer, vous ne devriez pas courir le risque. Ouais, ok. Et donc c'est ces comportements-là qu'il faut qu'on voit dans votre IA en fait.

Donc il faut mieux tester cette histoire d'oscillation. L'oscillation dont tu parles, elle intervient quand ? Il reste encore des humains sur la carte ?


## Réponse sur les oscillations  Repère fourni 14 h 34

Julian  Réponse rapportée

Dans les positions qu’on a analysées précisément, il ne restait plus d’humains. On avait notamment notre groupe de 18 contre un groupe de 12, donc assez pour une attaque garantie. Pourtant, le bot faisait encore des allers-retours. On a même trouvé des positions où il pouvait éliminer l’adversaire immédiatement et choisissait autre chose, également noté gagnant. C’est ce départage qu’on a corrigé. Par contre, on n’a pas encore vérifié systématiquement les oscillations lorsqu’il reste des humains accessibles.


## Question sur un bug possible et sur l’heuristique  Avant le repère 14 h 36

Professeur

À la limite c'est un peu moins surprenant s'il n'y a plus d'humains et qu'il reste que des ennemis. Parce que du coup si l'ennemi s'approche, enfin non c'est un peu bizarre parce que normalement comme vous avez la même IA, il y en a une qui doit essayer de s'approcher et si l'autre s'approche, l'autre devrait s'éloigner. Et là ça donne, ouais, il y a un truc bizarre, ça a peut-être un bug quand même dans votre alpha bêta, donc faites gaffe. Juste tu peux m'appeler s'il te plaît lheuristique


## Réponse sur l’heuristique  Repère fourni 14 h 36

Julian  Réponse rapportée

Notre heuristique combine la différence d’effectifs, les humains que chaque camp peut atteindre et convertir, les menaces d’élimination immédiate et une petite pénalité si nos troupes sont dispersées. Pour les humains, on tient compte de la distance.

Par contre, dans l’AB2 de référence, quand il n’y a plus d’humains et pas de menace immédiate, on ne valorise pas explicitement le rapprochement vers l’ennemi. Plusieurs déplacements peuvent donc avoir la même note. Ça peut expliquer une partie du comportement, mais on doit aussi vérifier la recherche et le cache pour exclure un bug.


## Question transcrite sur la parallélisation  Avant le repère 14 h 37

Professeur  Formulation ambiguë

Ouais puis vous êtes pour la ménage, ouais et vous avez utilisé quoi de la paralysation, des choses comme ça ?


## Réponse sur la parallélisation  Repère fourni 14 h 37

Julian  Réponse rapportée

Pour nos AB2, non, la recherche est sur un seul thread. On a surtout gagné du temps avec les coupures Alpha-Bêta, le classement des coups et la table de transposition pour réutiliser des résultats. Et on limite à six ou sept actions candidates par position. On n’a pas encore testé la parallélisation.


## Question sur le tri des actions  Repère fourni 14 h 38

Professeur

La dernière chose comment sur quoi vous vous basez pour trier les actions ?


## Réponse sur le tri des actions  Repère fourni 14 h 39

Julian  Réponse rapportée

On a deux étapes. D’abord, le générateur classe les actions selon le recrutement possible, le rapprochement vers les humains, les gains estimés dans les combats et l’exposition à une attaque adverse. Ça sert à sélectionner les six ou sept candidats.

Ensuite, pour les explorer, on simule chaque action et on applique notre heuristique au plateau obtenu. On privilégie aussi le coup mémorisé dans la table et les coups qui ont déjà provoqué des coupures. Donc la sélection initiale et l’ordre d’exploration sont deux choses distinctes.


## Machines du campus comparaisons rapport et fin de réunion  Repère fourni 14 h 40

Échange final entre le professeur et Julian  Prises de parole non segmentées dans la source

Alli en H deux cent huit vérifier s'il y a votre IA a fait 1,34 secondes là-bas aussi. Ok oui, oui parce qu'on l'a testé que sur le mien pour le moment donc. Ben c'est ça et je me souviens pas de ce que t'as comme ordinateur mais s'il est un peu puissant, tu vois si t'as un joua ou un truc comme ça, il est possible quand même que ça soit pas du tout la même configuration. Après je vous avais donné la configuration des machines. Elles sont pas non plus obsolètes tu vois donc mais bon ça ça fait éviter de découvrir le jour du tournoi qu'en fait elle met trois secondes quoi. Donc c'est un peu dommage avec tout le mal que vous vous donnez, voilà. Donc ouais je essayais de voir et essayer de passer en H208. Donc des fois on est sur le campus. Et puis au moins vous regardez si ça tourne quoi. Je pense que c'est ça la prochaine étape là.

Vous avez quelque chose de bien. Après le problème qu'on a évoqué. Voilà, il y a quelques petits problèmes. Il faut comparer avec MCTS. MCTS peut être aussi l'IA contre laquelle vous allez jouer. Bah enfin ça c'est vu que c'est Reda qui, Reda il doit tester justement parce que Reda MCTS de son côté. Et vu qu'on vient, enfin on vient de finir la B2 entre guillemets optimisée. Reda il devait, l'ancienne version il faisait nul et du coup Reda doit tester du coup la nouvelle version, enfin nos deux nouvelles versions pour voir. Par contre dans le rapport, ce que j'attends de vous là, parce que là vous m'avez dit plein d'informations, c'est génial.

Et je pense que dans le rapport, j'aimerais vraiment que vous montriez que vous avez par exemple testé avec une largeur de 6, de 7, de 8, que bah le nombre de victoires c'était mieux pour 7 et c'est pour ça que vous avez choisi 7. J'aimerais qu'il y ait quand même un petit peu de, comment dire, de matière, de discipline aussi dans la manière dont vous avez effectué et réglé vos paramètres. Vous l'avez fait hein, donc ce que je veux dire par là c'est que ça c'est vraiment débile de pas les faire. C'est juste que pour, vu qu'on est plein de modèles, enfin au début on s'est laissé un champ de possible hyper large pour recentrer à la fin. Je pense que du coup la narration ça sera un peu la même aussi pour, enfin pendant la soutenance s'il y en a une.

Mais bah expliquez pourquoi, enfin d'où on est parti et comment on a resserré jusqu'à la fin à B6, à B2 et MCTS quoi. Ok. Bah voilà, bah c'est exactement ça. Donc mais en tout cas voilà, il faut que je ce qu'il va me faire donner envie de mettre des points en plus, c'est d'avoir eu une démarche très scientifique donc avec des tests, des sélections parce que les tests, voilà. Comme vous l'avez fait, là vous l'avez dit, vous pouvez imaginer que je vais m'en souvenir dans trois semaines ou quatre. Non. Donc ne comptez pas là-dessus. Écrivez-le parce qu'au moins après oui quand je vais le lire je vais dire ah oui il m'avait dit ça un jour à l'oral. Mais sans ça je risque de pas m'en souvenir le jour J. Donc si tu veux, voilà, moi vraiment la note ça va être ok ils ont été rigoureux, ils ont fait du boulot.

Ils ont pas utilisé une IA générative pour générer tout le code. Donc des trucs comme ça. Ok. Ok ça marche. Voilà et n'oubliez pas donc de bien faire le lien aussi dans le rapport avec on a implémenté par exemple le choix de la sélection des N meilleurs coups possibles. Bah c'est telle fonction ou telle classe ou tel fichier ou un truc comme ça. Ok. Dernière petite chose, on est bien d'accord que votre IA, elle, enfin votre IA, pas votre IA, votre script, on peut paramétrer très facilement l'adresse IP et le port. Oui oui on l'a fait exprès pour que ça soit. Voilà parce que ça je connais pas à l'avance donc on le saura le jour J. Ok. Non non ça y a pas de souci. Ok bon ça me paraît très bien. Bah voilà. Ok bah c'était pour, on voulait faire un point avec vous pour . Bah très bien, j'apprécie. J'étais dispo.

Désolé j'ai pas pu, j'étais avec un truc avant donc j'ai pas pu répondre. C'est comme ça au moins on peut avancer déjà pour la semaine prochaine un peu. Ouais essayez quand même donc de bien avancer sur, profitez de l'après-midi parce que c'est rare qu'on ait finalement trois heures comme ça consacrées au projet. Et que voilà il reste très peu de temps finalement donc voilà essayez quand même d'aller jusqu'au bout quoi. Ok ça va. Ça va bah merci monsieur. Merci à vous, bon courage. Merci, bonne après-midi. Au revoir, à bientôt, au revoir


# 2 Résumé des remarques du professeur

- **Comportement avec des humains** : Tant qu’il reste des humains que notre groupe peut convertir, le bot doit progresser vers eux en tenant compte de la menace adverse. Des allers-retours sans progrès dans cette situation sont à investiguer.

- **Comportement face aux ennemis** : Sans humains, un groupe dominant doit pouvoir poursuivre et attaquer ; un groupe trop faible doit plutôt éviter une destruction prévisible. La distance et le joueur qui aura l’initiative du combat comptent.

- **Risque des combats** : Le professeur déconseille les combats aléatoires inutiles, y compris avec un petit avantage numérique insuffisant pour garantir la victoire. Il évoque des exceptions : diversion ou tentative de dernière chance lorsqu’on est déjà largement perdant.

- **Protéger une position gagnante** : En fin de partie, un groupe très supérieur ne doit pas offrir inutilement à l’adversaire l’occasion d’initier un combat risqué. Il faut regarder qui peut attaquer en premier, pas seulement compter les créatures.

- **Oscillations et bug possible** : Le professeur demande de mieux tester les allers-retours. Il n’exclut pas un bug d’Alpha-Bêta. La correction du départage présentée par Julian n’est donc pas considérée comme une validation générale de la recherche, de l’heuristique ou du cache.

- **Explications techniques données** : Julian décrit une heuristique combinant effectifs, course aux humains, menaces immédiates et dispersion. Il précise que les AB2 sont monothread et distingue sélection des candidats puis ordre d’exploration. La largeur 6 ou 7 concerne des actions de tour complet, pas six ou sept cases voisines.

- **Essais en salle H208** : C’est la prochaine étape explicitement recommandée : tester sur les machines du campus prévues pour le tournoi. Un temps observé sur le PC personnel ne suffit pas à garantir le même comportement ailleurs. Il faut mesurer le temps réel jusqu’à l’envoi du coup.

- **Comparaison avec MCTS** : Comparer les nouveaux AB2 au MCTS de Réda, qui constitue aussi un adversaire plausible au tournoi. La discussion mentionne d’anciens nuls, mais ne donne pas de résultat validé pour les nouvelles versions.

- **Rapport expérimental** : Écrire la démarche complète : point de départ, paramètres essayés, protocoles, résultats, décisions de conserver ou d’écarter. Montrer comment l’exploration initialement large a été resserrée vers les familles AB2, AB6 et MCTS. Le professeur ne se basera pas sur son souvenir de la réunion.

- **Justifier le choix des paramètres** : L’exemple oral de largeurs 6, 7 et 8 illustre la preuve attendue : un choix doit être soutenu par des résultats comparables. Ce n’est pas l’annonce que largeur 7 a déjà démontré sa supériorité dans nos données.

- **Relier explications et code** : Pour chaque mécanisme présenté dans le rapport, citer le fichier, la classe ou la fonction concernés, par exemple la sélection des N meilleurs coups. Montrer la compréhension et le travail réellement accomplis ; ne pas se contenter d’un résultat ou d’un récit oral.

- **Lancement automatique** : Le professeur confirme que l’IP et le port seront connus le jour du tournoi. Ils doivent être facilement configurables par la commande de lancement, sans modification manuelle du code ni intervention pendant les parties.

- **Avancer vers un programme prêt** : Le professeur juge le travail intéressant et encourage à profiter des séances restantes pour terminer les vérifications. Aucune nouvelle fonctionnalité, parallélisation ou profondeur précise n’est imposée dans cet échange.


## Passages à interpréter avec prudence

- « Engagée cinq fois plus nombreuse » est laissé tel quel dans la transcription. Le même passage cite ensuite explicitement le seuil 1,5. Ne pas transformer cette formulation incertaine en règle de 5 fois : contrôler la règle écrite et le comportement du serveur.
- « Sauter des cases » est une expression rapportée. Elle ne prouve pas que notre AB2 actuel implémente des transitions macro-actions ni qu’un déplacement non adjacent est autorisé.
- « Notions » semble renvoyer aux nœuds de chance ; « paralysation » à la parallélisation ; « m’appeler l’heuristique » à une demande de rappeler l’heuristique. Ce sont des interprétations, pas des corrections authentifiées.
- Le chiffre « 1,34 seconde » dans la discussion est un exemple oral à vérifier sur les machines du campus ; ce n’est pas une mesure effectuée en H208.
- Le dernier grand bloc mêle les interventions du professeur et de Julian. La source ne permet pas d’attribuer chaque phrase avec certitude. La transcription complète ci-dessus conserve cette limite.
Ces notes ne modifient pas les règles du jeu. Les règles écrites et le comportement effectif du serveur doivent être distingués des conseils stratégiques et des formulations incertaines de la transcription.


# 3 Ce qu’on doit retenir pour notre groupe

La priorité est de sécuriser et mesurer le programme final, puis d’étayer les choix. La correction du départage reste expérimentale ; elle ne dispense pas de rechercher un bug ni de contrôler les cas avec humains.


## 1 Tester le paquet réel en H208

Qui est concerné : Groupe.

Commande de lancement, machine et version Python consignées ; temps moyen et maximum jusqu’à MOV ; vérification des deux espèces et d’une partie complète. Ne pas annoncer ce test comme déjà fait.


## 2 Vérifier les oscillations

Qui est concerné : Travail AB2.

Rejouer les cas existants et ajouter des humains accessibles. Comparer le score, les candidats conservés, les réponses adverses et les accès au cache ; ne pas supposer que le seul départage explique tous les cas.


## 3 Vérifier les décisions de combat

Qui est concerné : Travail AB2 et AB6.

Cas avec supériorité garantie, infériorité, combat risqué, initiative adverse et tentative de dernière chance. Garder des positions et des traces montrant les comportements.


## 4 Comparer aux adversaires MCTS

Qui est concerné : Réda et groupe.

Spécifications exactes des bots, mêmes cartes, rôles inversés, graines consignées et tableau des résultats. Les nouveaux résultats ne sont pas encore fournis dans cet échange.


## 5 Construire les preuves pour le rapport

Qui est concerné : Groupe.

Tableau paramètres → protocole → résultats → décision. Distinguer résultats serveur, simulation, sondes et corrections ciblées ; signaler les essais non concluants.


## 6 Préparer le lancement final

Qui est concerné : Groupe.

Tester la commande avec une IP et un port fournis de l’extérieur ; sélectionner le bon agent. Le main.py actuel choisit baseline si aucune option --agent n’est donnée.


## 7 Relier la narration au code

Qui est concerné : Groupe.

Référencer fonctions et fichiers, expliquer les choix et les contributions réelles. La présentation orale doit raconter la même démarche que le rapport.


## Situations concrètes à vérifier

| Situation | Comportement à contrôler |
|---|---|
| Humains accessibles | Progresser vers la conversion sans s’exposer inutilement à l’ennemi. |
| Humains présents mais groupe trop petit | Ne pas confondre cible proche et conversion garantie ; rechercher une décision adaptée aux effectifs et au risque. |
| Plus d’humains et groupe dominant | Poursuivre et conclure si c’est sûr ; vérifier l’élimination immédiate disponible. |
| Plus d’humains et groupe inférieur | Éviter une attaque certaine de l’adversaire ; examiner les possibilités de fuite. |
| Fin de partie très défavorable | Une prise de risque peut avoir du sens plutôt qu’une défaite déjà pratiquement assurée. |
| Fin de partie favorable | Préserver l’avantage ; regarder si notre mouvement permet à l’ennemi d’initier un combat aléatoire. |
| Deux coups de même note | Contrôler le départage et le cache ; un meilleur score recherché doit rester prioritaire. |


## Correspondance avec le code pour le rapport

Repères pour retrouver les mécanismes dans le checkout actuel. Les noms doivent être revérifiés si le code évolue avant la remise.

| Mécanisme | Fichier | Fonctions ou classe |
|---|---|---|
| Sélection des candidats | candidates.py | generate_candidates ; turn_score |
| Classement et recherche | agents/ab_variants.py | Variant._plans ; Variant.plans ; Variant.search |
| Évaluation du plateau | evaluation.py | evaluate ; win_value ; race_owners |
| Départage expérimental | agents/ab2_tie.py | AB2Tie.choose_moves ; AB2Tie.plans ; AB2Tie.search |
| Règles et simulation | combat.py ; simulator.py | win_probability ; simulate_turn ; get_outcome |
| Commande et communication | main.py ; client.py | main ; play_game ; ClientSocket |


## Précautions pour raconter les résultats

- Ne pas écrire que largeur 7 est meilleure que largeur 6 sur la seule base de l’exemple donné par le professeur. Notre tournoi initial était à égalité ; la confirmation suivante opposait largeur 7 au guidage, pas au témoin largeur 6.
- Présenter les profondeurs moyennes réellement terminées avec les temps moyens et maximums, la machine, les cartes et les adversaires. Un plafond configuré n’est pas une profondeur atteinte à chaque décision.
- Indiquer pour chaque modification si elle a été gardée, écartée ou laissée expérimentale, avec les données correspondantes. Conserver aussi les essais négatifs.
- Distinguer les parties WPF, les simulations, les sondes chronométrées et les rejeux de positions. Une validation locale n’est pas une validation H208.
- Décrire honnêtement les contributions, les outils utilisés et la compréhension des algorithmes. Le propos du professeur sur l’IA générative est conservé dans la transcription ; ce compte rendu n’affirme pas qu’aucune assistance n’a été utilisée.

## Mémoire de l’échange

Décisions déjà rapportées : comparaison MCTS envisagée avec Réda et IP/port paramétrables dans le programme. Actions encore à démontrer : essai H208, validation du paquet exact remis, analyse complète des oscillations et des combats, comparaisons contrôlées et rapport relié au code. Aucun de ces travaux n’a été exécuté simplement en rédigeant ces notes.
