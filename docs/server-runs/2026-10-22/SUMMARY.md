# Parties sur le vrai serveur du cours — 22 octobre 2026

Premier passage des moteurs sur le serveur Windows du cours (Server v3.2.1).
Code des bots testé : `main` au commit `10f337e`, sans aucune modification.

**Verdict : 24 parties sur 24 jouées jusqu'au bout, sans plantage ni déconnexion.**
Les deux bots ont reçu `Game ended` puis `Server finished the session` et sont
sortis avec le code 0 dans toutes les parties. Sur 1 322 coups, aucun ne dépasse
1.8 s (maximum 1.581 s), et il n'y a aucun `Agent fault` ni aucun `fallback=True`.

## Machine

| | |
|---|---|
| CPU | Intel Core i5-14400F (10 cœurs, 16 threads) |
| RAM | 15,8 Go |
| OS | Windows 10 Professionnel 22H2 (10.0.19045) |
| Python | 3.12.7 (Anaconda, 64 bits), aucune dépendance externe |
| Serveur | Server v3.2.1 extrait par `scripts/setup_server.py`, sur 127.0.0.1:5555 |

## Configuration

`python scripts/setup_server.py <archive> [--map testmap2.xml] --force`, puis
dans `.local/server/VampiresVSWerewolvesGameServer.exe.config` :

| Clé | Valeur |
|---|---|
| `MaxGameDuration` | `00:10:00` (au lieu des `00:00:30` du setup) |
| `MaxPlayDuration` | `00:00:02` (inchangé) |
| `MaxPlays` | `40` (série démo) puis `200` (conditions réelles) |
| `PlayersCount` / `AutoRestart` | `2` / `False` |

Maps : `thetrap.xml` et `testmap2.xml`. Le serveur a été relancé pour chaque partie
(`Start-Process`). Il n'y a aucun bouton à cliquer : il écoute dès l'ouverture et la
partie démarre environ 5 s après la connexion du second bot. Commandes des bots,
lancés en arrière-plan avec stdout et stderr redirigés vers le log, le second
environ 1 s après la connexion du premier :

```
python main.py --name AlphaBeta --agent alphabeta --max-plies <MaxPlays> 127.0.0.1 5555 > <log> 2>&1
python main.py --name MCTS      --agent mcts      --max-plies <MaxPlays> 127.0.0.1 5555 > <log> 2>&1
python main.py --name OEP       --agent oep       --max-plies <MaxPlays> 127.0.0.1 5555 > <log> 2>&1
python main.py --name Baseline  --agent baseline  --max-plies <MaxPlays> 127.0.0.1 5555 > <log> 2>&1
```

Les options restent par défaut : `--move-time 1.5`, `--seed 42`, `--rules-profile server-v3.2.1`,
et pour MCTS `iterations=10000`.

**Rôles.** Le bot connecté en premier devient Player 1, joue les Vampires et joue
en premier. Vérifié dans les 24 parties. `MaxPlays` compte les demi-coups des deux
joueurs : avec 40, chaque bot joue 20 coups.

## Résultats

Le vainqueur et les effectifs finaux (Player 1 – Player 2, humains restants) sont
ceux affichés par la fenêtre du serveur en fin de partie. Les temps sont ceux des
lignes `Turn N: ... (X seconds)` des logs. « Faults » compte les lignes `Agent fault`
et `fallback=True`.

| # | Match | Map | MaxPlays | Connexion (1er → 2e) | Rôle d'AlphaBeta | Vainqueur | Effectifs finaux | Fin | Demi-coups | AlphaBeta max / moy (s) | Adversaire max / moy (s) | Faults AB / adv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | AlphaBeta vs MCTS | thetrap.xml | 40 | AlphaBeta → MCTS | Vampires (P1, joue en 1er) | **MCTS** | AlphaBeta 0 – MCTS 10 (humains 1) | élimination | 20 | 1.500 / 0.654 | 1.503 / 1.502 | 0 / 0 |
| 2 | AlphaBeta vs MCTS | thetrap.xml | 40 | MCTS → AlphaBeta | Loups-garous (P2, joue en 2e) | **MCTS** | MCTS 10 – AlphaBeta 4 (humains 0) | MaxPlays | 40 | 0.844 / 0.208 | 1.507 / 1.469 | 0 / 0 |
| 3 | AlphaBeta vs OEP | thetrap.xml | 40 | AlphaBeta → OEP | Vampires (P1, joue en 1er) | **OEP** | AlphaBeta 0 – OEP 11 (humains 0) | élimination | 28 | 0.914 / 0.264 | 0.006 / 0.004 | 0 / 0 |
| 4 | AlphaBeta vs OEP | thetrap.xml | 40 | OEP → AlphaBeta | Loups-garous (P2, joue en 2e) | **OEP** | OEP 11 – AlphaBeta 0 (humains 0) | élimination | 27 | 0.846 / 0.256 | 0.007 / 0.004 | 0 / 0 |
| 5 | AlphaBeta vs Baseline | thetrap.xml | 40 | AlphaBeta → Baseline | Vampires (P1, joue en 1er) | **Baseline** | AlphaBeta 0 – Baseline 4 (humains 0) | élimination | 26 | 0.836 / 0.297 | 0.000 / 0.000 | 0 / 0 |
| 6 | AlphaBeta vs Baseline | thetrap.xml | 40 | Baseline → AlphaBeta | Loups-garous (P2, joue en 2e) | **Baseline** | Baseline 4 – AlphaBeta 0 (humains 0) | élimination | 21 | 0.856 / 0.278 | 0.000 / 0.000 | 0 / 0 |
| 7 | AlphaBeta vs MCTS | testmap2.xml | 40 | AlphaBeta → MCTS | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 16 – MCTS 14 (humains 22) | MaxPlays | 40 | 1.581 / 1.201 | 1.576 / 1.488 | 0 / 0 |
| 8 | AlphaBeta vs MCTS | testmap2.xml | 40 | MCTS → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | MCTS 14 – AlphaBeta 16 (humains 22) | MaxPlays | 40 | 1.501 / 0.810 | 1.503 / 1.502 | 0 / 0 |
| 9 | AlphaBeta vs OEP | testmap2.xml | 40 | AlphaBeta → OEP | Vampires (P1, joue en 1er) | Égalité | AlphaBeta 16 – OEP 16 (humains 20) | MaxPlays | 40 | 1.501 / 1.206 | 0.062 / 0.018 | 0 / 0 |
| 10 | AlphaBeta vs OEP | testmap2.xml | 40 | OEP → AlphaBeta | Loups-garous (P2, joue en 2e) | Égalité | OEP 16 – AlphaBeta 16 (humains 20) | MaxPlays | 40 | 1.501 / 1.136 | 0.061 / 0.020 | 0 / 0 |
| 11 | AlphaBeta vs Baseline | testmap2.xml | 40 | AlphaBeta → Baseline | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 16 – Baseline 14 (humains 22) | MaxPlays | 40 | 1.501 / 0.789 | 0.000 / 0.000 | 0 / 0 |
| 12 | AlphaBeta vs Baseline | testmap2.xml | 40 | Baseline → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | Baseline 14 – AlphaBeta 16 (humains 22) | MaxPlays | 40 | 1.501 / 0.916 | 0.000 / 0.000 | 0 / 0 |
| 13 | AlphaBeta vs MCTS | thetrap.xml | 200 | AlphaBeta → MCTS | Vampires (P1, joue en 1er) | **MCTS** | AlphaBeta 0 – MCTS 7 (humains 1) | élimination | 20 | 1.500 / 0.807 | 1.503 / 1.502 | 0 / 0 |
| 14 | AlphaBeta vs MCTS | thetrap.xml | 200 | MCTS → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | MCTS 0 – AlphaBeta 3 (humains 2) | élimination | 15 | 1.344 / 0.661 | 1.502 / 1.502 | 0 / 0 |
| 15 | AlphaBeta vs OEP | thetrap.xml | 200 | AlphaBeta → OEP | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 3 – OEP 0 (humains 0) | élimination | 22 | 1.500 / 0.442 | 0.009 / 0.005 | 0 / 0 |
| 16 | AlphaBeta vs OEP | thetrap.xml | 200 | OEP → AlphaBeta | Loups-garous (P2, joue en 2e) | **OEP** | OEP 11 – AlphaBeta 0 (humains 0) | élimination | 27 | 1.283 / 0.292 | 0.009 / 0.005 | 0 / 0 |
| 17 | AlphaBeta vs Baseline | thetrap.xml | 200 | AlphaBeta → Baseline | Vampires (P1, joue en 1er) | **Baseline** | AlphaBeta 0 – Baseline 3 (humains 0) | élimination | 26 | 1.020 / 0.445 | 0.000 / 0.000 | 0 / 0 |
| 18 | AlphaBeta vs Baseline | thetrap.xml | 200 | Baseline → AlphaBeta | Loups-garous (P2, joue en 2e) | **Baseline** | Baseline 4 – AlphaBeta 0 (humains 0) | élimination | 21 | 0.877 / 0.317 | 0.000 / 0.000 | 0 / 0 |
| 19 | AlphaBeta vs MCTS | testmap2.xml | 200 | AlphaBeta → MCTS | Vampires (P1, joue en 1er) | **MCTS** | AlphaBeta 0 – MCTS 5 (humains 20) | élimination | 110 | 1.501 / 0.568 | 1.502 / 1.502 | 0 / 0 |
| 20 | AlphaBeta vs MCTS | testmap2.xml | 200 | MCTS → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | MCTS 14 – AlphaBeta 16 (humains 22) | MaxPlays | 200 | 1.502 / 0.291 | 1.503 / 1.502 | 0 / 0 |
| 21 | AlphaBeta vs OEP | testmap2.xml | 200 | AlphaBeta → OEP | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 4 – OEP 0 (humains 20) | élimination | 63 | 1.501 / 0.532 | 0.012 / 0.004 | 0 / 0 |
| 22 | AlphaBeta vs OEP | testmap2.xml | 200 | OEP → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | OEP 0 – AlphaBeta 16 (humains 0) | élimination | 152 | 1.501 / 0.218 | 0.013 / 0.003 | 0 / 0 |
| 23 | AlphaBeta vs Baseline | testmap2.xml | 200 | AlphaBeta → Baseline | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 5 – Baseline 0 (humains 20) | élimination | 64 | 1.501 / 0.602 | 0.000 / 0.000 | 0 / 0 |
| 24 | AlphaBeta vs Baseline | testmap2.xml | 200 | Baseline → AlphaBeta | Loups-garous (P2, joue en 2e) | Égalité | Baseline 16 – AlphaBeta 16 (humains 20) | MaxPlays | 200 | 1.501 / 0.238 | 0.000 / 0.000 | 0 / 0 |

Bilan d'AlphaBeta (V = victoire, N = nul, D = défaite) : **10 V, 3 N, 11 D**.

| | contre MCTS | contre OEP | contre Baseline |
|---|---|---|---|
| thetrap, 40 | 0 V, 0 N, 2 D | 0 V, 0 N, 2 D | 0 V, 0 N, 2 D |
| thetrap, 200 | 1 V, 0 N, 1 D | 1 V, 0 N, 1 D | 0 V, 0 N, 2 D |
| testmap2, 40 | 2 V, 0 N, 0 D | 0 V, 2 N, 0 D | 2 V, 0 N, 0 D |
| testmap2, 200 | 1 V, 0 N, 1 D | 2 V, 0 N, 0 D | 1 V, 1 N, 0 D |

Une seule partie par configuration et des combats aléatoires : ces scores donnent
une tendance, pas une mesure. Les bilans des deux séries ne se comparent pas
directement. Par exemple, la partie 5 (40) et la partie 17 (200) ont suivi la même
séquence de coups jusqu'au dernier combat, qui laisse 4 puis 3 survivants à Baseline.

## Temps et faults par bot

| Bot | Parties | Coups | Max (s) | Moyenne (s) | Coups > 1.8 s | `Agent fault` | `fallback=True` | Lignes contenant « fallback » | Erreurs, exceptions, déconnexions |
|---|---|---|---|---|---|---|---|---|---|
| AlphaBeta | 24 | 659 | 1.581 | 0.475 | 0 | 0 | 0 | 0 | 0 |
| MCTS | 8 | 243 | 1.576 | 1.498 | 0 | 0 | 0 | 243 (toutes `fallback=False`) | 0 |
| OEP | 8 | 200 | 0.062 | 0.007 | 0 | 0 | 0 | 0 | 0 |
| Baseline | 8 | 220 | < 0.001 | < 0.001 | 0 | 0 | 0 | 0 | 0 |

Tous les logs ne contiennent que des lignes `INFO:`. Il n'y a aucune ligne `WARNING`,
`ERROR` ni `Traceback`, et aucun bot ne s'est déconnecté avant le `BYE` du serveur.

## Problèmes rencontrés et observations

1. **Nom de l'archive.** Le fichier disponible était `Softwares-20261022.zip`, téléchargé
   le jour même sur le Moodle du cours. Moodle date le nom au jour du téléchargement,
   d'où la différence avec `Softwares-20261008.zip`. Le contenu est celui qu'attend
   `setup_server.py` : `Server v3.2.1.zip`, dont les fichiers datent du 21/11/2019, et
   `Map generator.zip`. SHA-256 : `aa6ecdd4ac9639160031f94c23480a60b80e537556211fdd1dff0cc7a1aec103`.

2. **« fallback » dans les logs de MCTS.** MCTS écrit à chaque coup
   `INFO: Search: 1320 iterations; fallback=False`. Un `grep fallback` compte donc
   243 lignes, mais aucune n'est un vrai fallback. Le chiffre qui compte, `Agent fault`
   plus `fallback=True`, vaut 0. Limite : AlphaBeta et OEP repassent sur
   `fallback_moves` en silence quand leur recherche ne rend rien
   (`agents/alphabeta.py:113`, `agents/oep.py:145`). Ce cas n'apparaît pas dans les
   logs et ne peut pas être compté.

3. **Léger dépassement du budget de 1.5 s.** Deux coups seulement, tous deux dans la
   partie 7 : AlphaBeta au tour 12 (`(1.581 seconds)`) et MCTS au tour 14
   (`(1.576 seconds)`). Il reste 0.22 s de marge avant l'alerte de 1.8 s et 0.42 s
   avant la limite serveur de 2 s. Tous les autres coups sont à 1.507 s ou moins.

4. **AlphaBeta perd presque tout sur thetrap (2 V, 10 D), dont 4 défaites sur 4 contre Baseline.**
   Deux schémas reviennent :
   - *Contre Baseline* : AlphaBeta place son armée à côté de celle de Baseline, à
     effectifs proches, au lieu d'attaquer. Baseline attaque et gagne le combat
     aléatoire. Partie 5 (`p40_thetrap_AlphaBeta-then-Baseline_*.txt`) :
     ```
     AlphaBeta INFO: Turn 12: [(8, 1, 6, 8, 2), (9, 2, 3, 8, 2)] (0.016 seconds)   -> 9 en (8,2)
     Baseline  INFO: Turn 12: [(6, 0, 8, 6, 1)] (0.000 seconds)                     -> 8 en (6,1)
     AlphaBeta INFO: Turn 13: [(8, 2, 9, 7, 1)] (0.015 seconds)                     -> 9 en (7,1), au contact
     Baseline  INFO: Turn 13: [(6, 1, 8, 7, 1)] (0.000 seconds)                     -> 8 attaquent 9 : Baseline gagne (4 survivants)
     ```
     Partie 17 : exactement la même séquence (Baseline gagne avec 3 survivants).
     Avant ce combat, aux tours 8 à 11, le groupe de 3 d'AlphaBeta fait un
     aller-retour (9,2) → (8,3) → (7,2) → (8,3) → (9,2).
   - *Contre OEP* : le dernier groupe de 4 d'AlphaBeta fuit le long du bord haut,
     poursuivi par les groupes de 7 et de 4 d'OEP, et se fait rattraper. Il joue
     ces coups en 1 à 17 ms. Les parties 3, 4 et 16 finissent par les mêmes coups
     (extrait de la partie 3) :
     ```
     AlphaBeta INFO: Turn 12: [(8, 0, 4, 7, 1)] (0.010 seconds)
     OEP       INFO: Turn 12: [(8, 3, 7, 7, 2), (9, 4, 4, 8, 4)] (0.001 seconds)
     AlphaBeta INFO: Turn 13: [(7, 1, 4, 6, 0)] (0.001 seconds)
     OEP       INFO: Turn 13: [(7, 2, 7, 6, 1), (8, 4, 4, 7, 3)] (0.002 seconds)
     AlphaBeta INFO: Turn 14: [(6, 0, 4, 5, 0)] (0.001 seconds)
     OEP       INFO: Turn 14: [(6, 1, 7, 5, 0), (7, 3, 4, 6, 2)] (0.001 seconds)   -> AlphaBeta 0, OEP 11
     ```

5. **Parties bloquées sur testmap2 : personne ne prend les 20 humains du centre.** Les
   parties qui vont jusqu'à `MaxPlays` finissent toutes à 16–14 ou 16–16, avec 20 à 22
   humains restants. Les bots répètent les deux mêmes coups pendant des dizaines de tours :
   - partie 20 (200, MCTS → AlphaBeta) : AlphaBeta du tour 29 au tour 95, MCTS du tour 21 au tour 95 ;
   - partie 24 (200, Baseline → AlphaBeta) : AlphaBeta du tour 22 au tour 95, Baseline du tour 52 au tour 100 ;
   - partie 22 : AlphaBeta du tour 22 au tour 45, avant de gagner.

   Extrait de la partie 20 (`p200_testmap2_MCTS-then-AlphaBeta_*.txt`) :
   ```
   AlphaBeta INFO: Turn 40: [(2, 0, 4, 3, 1), (3, 0, 12, 2, 1)] (0.154 seconds)
   AlphaBeta INFO: Turn 41: [(2, 1, 12, 3, 0), (3, 1, 4, 2, 0)] (0.145 seconds)
   AlphaBeta INFO: Turn 42: [(2, 0, 4, 3, 1), (3, 0, 12, 2, 1)] (0.153 seconds)
   MCTS      INFO: Turn 40: [(10, 10, 14, 11, 10)] (1.502 seconds)
   MCTS      INFO: Turn 41: [(11, 10, 14, 10, 10)] (1.501 seconds)
   MCTS      INFO: Turn 42: [(10, 10, 14, 11, 10)] (1.502 seconds)
   ```

6. **OEP joue en 7 ms en moyenne (62 ms au maximum).** C'est voulu par sa configuration par défaut :
   12 générations de 16 individus, le deadline ne sert que de plafond. OEP n'utilise
   donc pas le budget de 1.5 s.

7. **Les logs des bots n'ont pas d'horodatage.** Pour savoir qui jouait en premier,
   j'ai horodaté les lignes de l'extérieur, en lisant les fichiers de log pendant la
   partie, sans changer les commandes. Ces relevés ne sont pas commités. Le résultat
   final a été lu dans la fenêtre du serveur, qui affiche par exemple
   « MCTS wins / AlphaBeta loses » ou « No winner / No looser » en cas d'égalité.

8. **Logs commités.** `CONTRIBUTING.md` demande de garder les logs générés hors des
   commits. Ceux-ci ont été ajoutés à la demande, sur la branche `server-runs` seulement.
   Comme `.gitignore` ignore `*.log`, ils portent l'extension `.txt`. À trancher avant
   un éventuel merge dans `main`.

## Fichiers

Un log par bot et par partie, nommé `p<MaxPlays>_<map>_<1er connecté>-then-<2e connecté>_<bot>.txt`.
Par exemple, `p200_testmap2_MCTS-then-AlphaBeta_AlphaBeta.txt` est le log
d'AlphaBeta dans la partie 20. Il y a 48 fichiers.
