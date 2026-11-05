# Parties sur le vrai serveur du cours — 22 octobre 2026, après le correctif d'AlphaBeta

Deuxième passage des moteurs sur le serveur Windows du cours (Server v3.2.1), pour
mesurer l'effet du correctif d'Adam. Code des bots testé : `main` au commit `670a148`
(« Fix alpha-beta losses seen on the course server »), sans aucune modification.
Cette série rejoue exactement celle de [`../2026-10-22/`](../2026-10-22/SUMMARY.md),
jouée le même jour sur `10f337e`. La machine, l'archive du serveur, la configuration et
les commandes sont identiques.

**Verdict : 24 parties sur 24 jouées jusqu'au bout, sans plantage ni déconnexion.**
Les deux bots ont reçu `Game ended` puis `Server finished the session` et sont
sortis avec le code 0 dans toutes les parties. Sur 1 811 coups, aucun ne dépasse
1.8 s (maximum 1.563 s, pour MCTS ; 1.502 s pour AlphaBeta), et il n'y a aucun
`Agent fault` ni aucun `fallback=True`.

**Bilan d'AlphaBeta : 14 V, 3 N, 7 D, contre 10 V, 3 N, 11 D avant le correctif.
Sur thetrap : 6 V, 6 D, contre 2 V, 10 D.** AlphaBeta perd encore contre OEP sur
thetrap (4 D sur 4) et contre MCTS sur thetrap à 200 (2 D). Le détail est dans
[Défaites d'AlphaBeta](#défaites-dalphabeta).

## Machine

| | |
|---|---|
| CPU | Intel Core i5-14400F (10 cœurs, 16 threads) |
| RAM | 15,8 Go |
| OS | Windows 10 Professionnel 22H2 (10.0.19045) |
| Python | 3.12.7 (Anaconda, 64 bits), aucune dépendance externe |
| Serveur | Server v3.2.1 extrait par `scripts/setup_server.py`, sur 127.0.0.1:5555 |

## Configuration

Même archive que la première série, `Softwares-20261022.zip` (SHA-256
`aa6ecdd4ac9639160031f94c23480a60b80e537556211fdd1dff0cc7a1aec103`).
`python scripts/setup_server.py <archive> [--map testmap2.xml] --force`, puis dans
`.local/server/VampiresVSWerewolvesGameServer.exe.config` :

| Clé | Valeur |
|---|---|
| `MaxGameDuration` | `00:10:00` (au lieu des `00:00:30` du setup) |
| `MaxPlayDuration` | `00:00:02` (inchangé) |
| `MaxPlays` | `40` (série démo) puis `200` (conditions réelles) |
| `PlayersCount` / `AutoRestart` | `2` / `False` |

Maps : `thetrap.xml` et `testmap2.xml`. Les 24 parties ont été jouées de 15:27 à 15:55
par les scripts de [`scripts/server-runs/`](../../../scripts/server-runs/README.md), avec
cette commande :

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\server-runs\run_series.ps1 `
    -Archive <...>\Softwares-20261022.zip -LogDir docs\server-runs\2026-10-22-670a148
```

Le serveur a été relancé pour chaque partie. Il n'y a aucun bouton à cliquer : il
écoute dès l'ouverture et la partie démarre environ 5 s après la connexion du second
bot. Commandes des bots, lancés en arrière-plan avec stdout et stderr redirigés vers le
log, le second environ 1 s après la connexion du premier :

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
| 1 | AlphaBeta vs MCTS | thetrap.xml | 40 | AlphaBeta → MCTS | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 9 – MCTS 8 (humains 0) | MaxPlays | 40 | 1.500 / 0.551 | 1.505 / 1.420 | 0 / 0 |
| 2 | AlphaBeta vs MCTS | thetrap.xml | 40 | MCTS → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | MCTS 0 – AlphaBeta 4 (humains 0) | élimination | 38 | 1.501 / 0.647 | 1.503 / 1.498 | 0 / 0 |
| 3 | AlphaBeta vs OEP | thetrap.xml | 40 | AlphaBeta → OEP | Vampires (P1, joue en 1er) | **OEP** | AlphaBeta 0 – OEP 3 (humains 0) | élimination | 17 | 1.500 / 1.170 | 0.010 / 0.007 | 0 / 0 |
| 4 | AlphaBeta vs OEP | thetrap.xml | 40 | OEP → AlphaBeta | Loups-garous (P2, joue en 2e) | **OEP** | OEP 6 – AlphaBeta 0 (humains 0) | élimination | 17 | 1.500 / 1.266 | 0.010 / 0.006 | 0 / 0 |
| 5 | AlphaBeta vs Baseline | thetrap.xml | 40 | AlphaBeta → Baseline | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 9 – Baseline 8 (humains 0) | MaxPlays | 40 | 1.501 / 0.588 | 0.000 / 0.000 | 0 / 0 |
| 6 | AlphaBeta vs Baseline | thetrap.xml | 40 | Baseline → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | Baseline 8 – AlphaBeta 9 (humains 0) | MaxPlays | 40 | 1.500 / 0.785 | 0.000 / 0.000 | 0 / 0 |
| 7 | AlphaBeta vs MCTS | testmap2.xml | 40 | AlphaBeta → MCTS | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 16 – MCTS 14 (humains 22) | MaxPlays | 40 | 1.501 / 1.196 | 1.503 / 1.474 | 0 / 0 |
| 8 | AlphaBeta vs MCTS | testmap2.xml | 40 | MCTS → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | MCTS 14 – AlphaBeta 16 (humains 22) | MaxPlays | 40 | 1.501 / 1.142 | 1.505 / 1.502 | 0 / 0 |
| 9 | AlphaBeta vs OEP | testmap2.xml | 40 | AlphaBeta → OEP | Vampires (P1, joue en 1er) | Égalité | AlphaBeta 16 – OEP 16 (humains 20) | MaxPlays | 40 | 1.501 / 1.175 | 0.052 / 0.017 | 0 / 0 |
| 10 | AlphaBeta vs OEP | testmap2.xml | 40 | OEP → AlphaBeta | Loups-garous (P2, joue en 2e) | Égalité | OEP 16 – AlphaBeta 16 (humains 20) | MaxPlays | 40 | 1.502 / 1.119 | 0.057 / 0.018 | 0 / 0 |
| 11 | AlphaBeta vs Baseline | testmap2.xml | 40 | AlphaBeta → Baseline | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 16 – Baseline 14 (humains 22) | MaxPlays | 40 | 1.501 / 0.781 | 0.000 / 0.000 | 0 / 0 |
| 12 | AlphaBeta vs Baseline | testmap2.xml | 40 | Baseline → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | Baseline 14 – AlphaBeta 16 (humains 22) | MaxPlays | 40 | 1.501 / 0.908 | 0.000 / 0.000 | 0 / 0 |
| 13 | AlphaBeta vs MCTS | thetrap.xml | 200 | AlphaBeta → MCTS | Vampires (P1, joue en 1er) | **MCTS** | AlphaBeta 0 – MCTS 3 (humains 0) | élimination | 19 | 1.500 / 1.111 | 1.504 / 1.503 | 0 / 0 |
| 14 | AlphaBeta vs MCTS | thetrap.xml | 200 | MCTS → AlphaBeta | Loups-garous (P2, joue en 2e) | **MCTS** | MCTS 2 – AlphaBeta 0 (humains 0) | élimination | 28 | 1.500 / 0.727 | 1.503 / 1.502 | 0 / 0 |
| 15 | AlphaBeta vs OEP | thetrap.xml | 200 | AlphaBeta → OEP | Vampires (P1, joue en 1er) | **OEP** | AlphaBeta 0 – OEP 3 (humains 0) | élimination | 17 | 1.500 / 1.094 | 0.008 / 0.006 | 0 / 0 |
| 16 | AlphaBeta vs OEP | thetrap.xml | 200 | OEP → AlphaBeta | Loups-garous (P2, joue en 2e) | **OEP** | OEP 8 – AlphaBeta 0 (humains 0) | élimination | 17 | 1.501 / 1.176 | 0.008 / 0.005 | 0 / 0 |
| 17 | AlphaBeta vs Baseline | thetrap.xml | 200 | AlphaBeta → Baseline | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 9 – Baseline 8 (humains 0) | MaxPlays | 200 | 1.500 / 0.154 | 0.001 / 0.000 | 0 / 0 |
| 18 | AlphaBeta vs Baseline | thetrap.xml | 200 | Baseline → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | Baseline 8 – AlphaBeta 9 (humains 0) | MaxPlays | 200 | 1.500 / 0.145 | 0.000 / 0.000 | 0 / 0 |
| 19 | AlphaBeta vs MCTS | testmap2.xml | 200 | AlphaBeta → MCTS | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 11 – MCTS 0 (humains 20) | élimination | 198 | 1.501 / 0.522 | 1.507 / 1.502 | 0 / 0 |
| 20 | AlphaBeta vs MCTS | testmap2.xml | 200 | MCTS → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | MCTS 14 – AlphaBeta 16 (humains 22) | MaxPlays | 200 | 1.501 / 0.311 | 1.563 / 1.502 | 0 / 0 |
| 21 | AlphaBeta vs OEP | testmap2.xml | 200 | AlphaBeta → OEP | Vampires (P1, joue en 1er) | **AlphaBeta** | AlphaBeta 4 – OEP 0 (humains 16) | élimination | 70 | 1.501 / 0.685 | 0.020 / 0.007 | 0 / 0 |
| 22 | AlphaBeta vs OEP | testmap2.xml | 200 | OEP → AlphaBeta | Loups-garous (P2, joue en 2e) | **AlphaBeta** | OEP 0 – AlphaBeta 16 (humains 12) | élimination | 117 | 1.501 / 0.365 | 0.020 / 0.005 | 0 / 0 |
| 23 | AlphaBeta vs Baseline | testmap2.xml | 200 | AlphaBeta → Baseline | Vampires (P1, joue en 1er) | Égalité | AlphaBeta 16 – Baseline 16 (humains 20) | MaxPlays | 200 | 1.501 / 0.784 | 0.001 / 0.000 | 0 / 0 |
| 24 | AlphaBeta vs Baseline | testmap2.xml | 200 | Baseline → AlphaBeta | Loups-garous (P2, joue en 2e) | **Baseline** | Baseline 5 – AlphaBeta 0 (humains 20) | élimination | 113 | 1.501 / 0.489 | 0.000 / 0.000 | 0 / 0 |

Bilan d'AlphaBeta (V = victoire, N = nul, D = défaite) : **14 V, 3 N, 7 D**.

| | contre MCTS | contre OEP | contre Baseline |
|---|---|---|---|
| thetrap, 40 | 2 V, 0 N, 0 D | 0 V, 0 N, 2 D | 2 V, 0 N, 0 D |
| thetrap, 200 | 0 V, 0 N, 2 D | 0 V, 0 N, 2 D | 2 V, 0 N, 0 D |
| testmap2, 40 | 2 V, 0 N, 0 D | 0 V, 2 N, 0 D | 2 V, 0 N, 0 D |
| testmap2, 200 | 2 V, 0 N, 0 D | 2 V, 0 N, 0 D | 0 V, 1 N, 1 D |

Une seule partie par configuration et des combats aléatoires : ces scores donnent
une tendance, pas une mesure. MCTS s'arrête au délai, donc ses coups varient d'une
série à l'autre. OEP, Baseline et AlphaBeta rejouent souvent les mêmes coups sur ces
petites positions. Les parties 3 et 15 suivent exactement la même séquence à 40 et
à 200. Les parties 4 et 16 aussi, jusqu'au dernier coup d'OEP.

## Avant / après

Même série, mêmes conditions. Seul le code d'AlphaBeta a changé entre les deux
(`10f337e` → `670a148`). Le commit touche `agents/alphabeta.py`, `evaluation.py` (nouvelle
fonction `win_value`) et `lookahead.candidate_turns`, que seul AlphaBeta utilise. OEP
n'importe de `lookahead` que `outcomes`, qui n'a pas changé. MCTS et Baseline ne sont pas
touchés. « Avant » reprend la série du 22/10 sur `10f337e`.

| | Avant | Après |
|---|---|---|
| **Total** | 10 V, 3 N, 11 D | 14 V, 3 N, 7 D |
| Map thetrap | 2 V, 0 N, 10 D | 6 V, 0 N, 6 D |
| Map testmap2 | 8 V, 3 N, 1 D | 8 V, 3 N, 1 D |
| Adversaire MCTS | 4 V, 0 N, 4 D | 6 V, 0 N, 2 D |
| Adversaire OEP | 3 V, 2 N, 3 D | 2 V, 2 N, 4 D |
| Adversaire Baseline | 3 V, 1 N, 4 D | 6 V, 1 N, 1 D |
| MaxPlays 40 | 4 V, 2 N, 6 D | 8 V, 2 N, 2 D |
| MaxPlays 200 | 6 V, 1 N, 5 D | 6 V, 1 N, 5 D |

| Map, adversaire | Avant | Après |
|---|---|---|
| thetrap, MCTS | 1 V, 0 N, 3 D | 2 V, 0 N, 2 D |
| thetrap, OEP | 1 V, 0 N, 3 D | 0 V, 0 N, 4 D |
| thetrap, Baseline | 0 V, 0 N, 4 D | 4 V, 0 N, 0 D |
| testmap2, MCTS | 3 V, 0 N, 1 D | 4 V, 0 N, 0 D |
| testmap2, OEP | 2 V, 2 N, 0 D | 2 V, 2 N, 0 D |
| testmap2, Baseline | 3 V, 1 N, 0 D | 2 V, 1 N, 1 D |

Partie par partie (résultat d'AlphaBeta, effectifs AlphaBeta–adversaire, longueur ;
← quand le résultat change) :

| # | Map | MaxPlays | Connexion | Avant (`10f337e`) | Après (`670a148`) |
|---|---|---|---|---|---|
| 1 | thetrap | 40 | AlphaBeta → MCTS | D, 0–10, 20 demi-coups | V, 9–8, 40 demi-coups ← |
| 2 | thetrap | 40 | MCTS → AlphaBeta | D, 4–10, 40 demi-coups | V, 4–0, 38 demi-coups ← |
| 3 | thetrap | 40 | AlphaBeta → OEP | D, 0–11, 28 demi-coups | D, 0–3, 17 demi-coups |
| 4 | thetrap | 40 | OEP → AlphaBeta | D, 0–11, 27 demi-coups | D, 0–6, 17 demi-coups |
| 5 | thetrap | 40 | AlphaBeta → Baseline | D, 0–4, 26 demi-coups | V, 9–8, 40 demi-coups ← |
| 6 | thetrap | 40 | Baseline → AlphaBeta | D, 0–4, 21 demi-coups | V, 9–8, 40 demi-coups ← |
| 7 | testmap2 | 40 | AlphaBeta → MCTS | V, 16–14, 40 demi-coups | V, 16–14, 40 demi-coups |
| 8 | testmap2 | 40 | MCTS → AlphaBeta | V, 16–14, 40 demi-coups | V, 16–14, 40 demi-coups |
| 9 | testmap2 | 40 | AlphaBeta → OEP | N, 16–16, 40 demi-coups | N, 16–16, 40 demi-coups |
| 10 | testmap2 | 40 | OEP → AlphaBeta | N, 16–16, 40 demi-coups | N, 16–16, 40 demi-coups |
| 11 | testmap2 | 40 | AlphaBeta → Baseline | V, 16–14, 40 demi-coups | V, 16–14, 40 demi-coups |
| 12 | testmap2 | 40 | Baseline → AlphaBeta | V, 16–14, 40 demi-coups | V, 16–14, 40 demi-coups |
| 13 | thetrap | 200 | AlphaBeta → MCTS | D, 0–7, 20 demi-coups | D, 0–3, 19 demi-coups |
| 14 | thetrap | 200 | MCTS → AlphaBeta | V, 3–0, 15 demi-coups | D, 0–2, 28 demi-coups ← |
| 15 | thetrap | 200 | AlphaBeta → OEP | V, 3–0, 22 demi-coups | D, 0–3, 17 demi-coups ← |
| 16 | thetrap | 200 | OEP → AlphaBeta | D, 0–11, 27 demi-coups | D, 0–8, 17 demi-coups |
| 17 | thetrap | 200 | AlphaBeta → Baseline | D, 0–3, 26 demi-coups | V, 9–8, 200 demi-coups ← |
| 18 | thetrap | 200 | Baseline → AlphaBeta | D, 0–4, 21 demi-coups | V, 9–8, 200 demi-coups ← |
| 19 | testmap2 | 200 | AlphaBeta → MCTS | D, 0–5, 110 demi-coups | V, 11–0, 198 demi-coups ← |
| 20 | testmap2 | 200 | MCTS → AlphaBeta | V, 16–14, 200 demi-coups | V, 16–14, 200 demi-coups |
| 21 | testmap2 | 200 | AlphaBeta → OEP | V, 4–0, 63 demi-coups | V, 4–0, 70 demi-coups |
| 22 | testmap2 | 200 | OEP → AlphaBeta | V, 16–0, 152 demi-coups | V, 16–0, 117 demi-coups |
| 23 | testmap2 | 200 | AlphaBeta → Baseline | V, 5–0, 64 demi-coups | N, 16–16, 200 demi-coups ← |
| 24 | testmap2 | 200 | Baseline → AlphaBeta | N, 16–16, 200 demi-coups | D, 0–5, 113 demi-coups ← |

Ce qui change :

- **thetrap : 2 V, 10 D → 6 V, 6 D.** AlphaBeta joue un autre coup que le 22/10 dès
  son premier coup, dans les 12 parties. Les deux schémas de défaite du 22/10 ont
  disparu. Il ne fuit plus avec son dernier groupe le long du bord, et ne s'arrête plus
  au contact de l'armée de Baseline. Dans les 12 parties, il mange les 5 humains de
  droite pendant que l'adversaire mange les 4 de gauche. Il mène alors **9 à 8**, sans
  humains restants. Contre Baseline, il n'y a ensuite plus aucun combat, et AlphaBeta
  gagne 9–8 à `MaxPlays` (4 V sur 4, y compris sur 200 demi-coups). Les 6 défaites restantes se
  jouent toutes à partir de ce 9 contre 8 : voir [Défaites d'AlphaBeta](#défaites-dalphabeta).
- **testmap2 : bilan identique (8 V, 3 N, 1 D), mais pas les mêmes parties.** À 40, les
  6 résultats et les effectifs sont identiques au 22/10. Les parties 10, 11 et 12 sont
  même identiques coup pour coup. À 200, la partie 19 passe de D à V : MCTS tente deux
  attaques risquées et les perd. La partie 23 passe de V à N, et la 24 de N à D (défaite
  détaillée plus bas).
- **MaxPlays 40 : 4 V, 2 N, 6 D → 8 V, 2 N, 2 D.** Tout le gain vient de thetrap.
- **MaxPlays 200 : 6 V, 1 N, 5 D dans les deux séries, mais 7 parties sur 12 changent de
  résultat.** Trois passent de D à V : thetrap contre Baseline (parties 17 et 18) et
  testmap2 contre MCTS (partie 19). Deux passent de V à D, sur thetrap contre MCTS
  (partie 14) et contre OEP (partie 15). Enfin, la partie 23 passe de V à N et la
  partie 24 de N à D.

## Temps et faults par bot

| Bot | Parties | Coups | Max (s) | Moyenne (s) | Coups > 1.8 s | `Agent fault` | `fallback=True` | Lignes contenant « fallback » | Erreurs, exceptions, déconnexions |
|---|---|---|---|---|---|---|---|---|---|
| AlphaBeta | 24 | 905 | 1.502 | 0.555 | 0 | 0 | 0 | 0 | 0 |
| MCTS | 8 | 301 | 1.563 | 1.495 | 0 | 0 | 0 | 301 (toutes `fallback=False`) | 0 |
| OEP | 8 | 168 | 0.057 | 0.009 | 0 | 0 | 0 | 0 | 0 |
| Baseline | 8 | 437 | 0.001 | < 0.001 | 0 | 0 | 0 | 0 | 0 |

Tous les logs ne contiennent que des lignes `INFO:`. Il n'y a aucune ligne `WARNING`,
`ERROR` ni `Traceback`, et aucun bot ne s'est déconnecté avant le `BYE` du serveur.
Le 22/10, AlphaBeta jouait en 0.475 s en moyenne (maximum 1.581 s).

## Défaites d'AlphaBeta

Un coup s'écrit `(x, y, n, x', y')` : `n` créatures vont de `(x, y)` à `(x', y')`. Sur
thetrap, AlphaBeta joue les Vampires quand il est connecté en premier, les Loups-garous
sinon. Les probabilités de gain viennent de `combat.win_probability` (profil
`server-v3.2.1`). Les plateaux ont été reconstitués avec `scripts/server-runs/replay.py`.

Les coups de fin de partie d'AlphaBeta prennent 0.04 à 0.5 s. Avec deux ou trois groupes
sur le plateau, la recherche atteint sa profondeur maximale (12) avant le délai : ce n'est
ni un timeout ni un fallback. J'ai reconstitué depuis les logs les positions où AlphaBeta
joue les coups cités ci-dessous, puis je les ai rejouées hors serveur avec le code de
`670a148` (agent `alphabeta` par défaut, 1.5 s, table de transposition vide). Elles
redonnent chaque fois le coup joué sur le serveur, avec `depth = 12`.

### thetrap : 9 contre 8, AlphaBeta attaque à 62,5 % (parties 3, 13, 14, 15)

Une fois au contact, AlphaBeta attaque les 8 avec ses 9 (P = 0.625). Il l'a fait 5 fois
dans la série : il gagne la partie 2 (4 survivants, à 2 demi-coups de la fin) et perd
les parties 3, 13, 14 et 15. Avec P = 0.625, gagner au plus 1 combat sur 5 arrive
environ 7 % du temps. La malchance compte donc pour une part. Mais chaque fois, AlphaBeta
mène 9–8 et finit son tour précédent à 2 cases des 8, ce qui leur permet de venir au contact.

- *Parties 3 et 15 (AlphaBeta → OEP), mêmes coups à 40 et à 200.* AlphaBeta finit de
  manger avec deux groupes séparés (4 et 5) et les laisse séparés. OEP vient au contact
  des deux à la fois : chacun peut alors être mangé à coup sûr par 8 (8 ≥ 1,5 × 5), et
  il ne reste que l'attaque à 9 contre 8. Au tour 8, réunir les 9 en (9,1) faisait
  partie des candidats d'AlphaBeta (8 ne bat pas 9 à coup sûr). Hors serveur, il rejoue
  pourtant le même coup. Partie 3 (`p40_thetrap_AlphaBeta-then-OEP_*.txt`) :
  ```
  AlphaBeta INFO: Turn 7: [(9, 1, 2, 9, 0), (9, 3, 4, 9, 2)] (1.229 seconds)   -> mange 2 + 1 humains : 4 en (9,0), 5 en (9,2) ; 9 contre 8
  OEP       INFO: Turn 7: [(6, 3, 8, 7, 2)] (0.003 seconds)                     -> 8 en (7,2), à 2 cases des deux groupes
  AlphaBeta INFO: Turn 8: [(9, 0, 4, 8, 0), (9, 2, 5, 9, 1)] (0.217 seconds)   -> 4 en (8,0), 5 en (9,1), toujours séparés
  OEP       INFO: Turn 8: [(7, 2, 8, 8, 1)] (0.003 seconds)                     -> 8 en (8,1), au contact des deux groupes
  AlphaBeta INFO: Turn 9: [(8, 0, 4, 8, 1), (9, 1, 5, 8, 1)] (0.087 seconds)   -> 9 attaquent 8 (P = 0.625) : OEP gagne (3 survivants)
  ```
- *Partie 13 (AlphaBeta → MCTS, 200).* AlphaBeta réunit bien ses 9, puis avance à 2 cases
  des 8 de MCTS. MCTS vient au contact, AlphaBeta attaque.
  ```
  AlphaBeta INFO: Turn 8: [(9, 0, 4, 9, 1), (9, 2, 5, 9, 1)] (0.518 seconds)   -> 9 réunis en (9,1)
  MCTS      INFO: Turn 8: [(7, 1, 8, 6, 2)] (1.504 seconds)                     -> 8 en (6,2)
  AlphaBeta INFO: Turn 9: [(9, 1, 9, 8, 2)] (0.047 seconds)                     -> 9 en (8,2), à 2 cases
  MCTS      INFO: Turn 9: [(6, 2, 8, 7, 1)] (1.502 seconds)                     -> 8 en (7,1), au contact
  AlphaBeta INFO: Turn 10: [(8, 2, 9, 7, 1)] (0.043 seconds)                    -> 9 attaquent 8 (P = 0.625) : MCTS gagne (3 survivants)
  ```
- *Partie 14 (MCTS → AlphaBeta, 200).* Du tour 9 au tour 13, AlphaBeta garde ses 9 à 2 ou
  3 cases des 8 de MCTS. Au tour 14, MCTS vient au contact.
  ```
  MCTS      INFO: Turn 13: [(8, 3, 8, 8, 4)] (1.502 seconds)                    -> 8 en (8,4)
  AlphaBeta INFO: Turn 13: [(8, 1, 9, 8, 2)] (0.143 seconds)                    -> 9 en (8,2), à 2 cases
  MCTS      INFO: Turn 14: [(8, 4, 8, 8, 3)] (1.502 seconds)                    -> 8 en (8,3), au contact
  AlphaBeta INFO: Turn 14: [(8, 2, 9, 8, 3)] (0.041 seconds)                    -> 9 attaquent 8 (P = 0.625) : MCTS gagne (2 survivants)
  ```

### thetrap : l'attaque groupée manque aux candidats (parties 4 et 16, OEP → AlphaBeta)

Même fin de partie à 40 et à 200 : les 4 et 5 Loups-garous d'AlphaBeta sont tous deux au
contact des 8 Vampires d'OEP. AlphaBeta envoie les 4 seuls contre les 8 (P = 0.25) et
pose les 5 à côté. Les 4 perdent, puis OEP mange les 5. Attaquer avec les 9 ensemble
(P = 0.625) était possible, mais ce coup n'est pas dans `lookahead.candidate_turns` pour
cette position. Les « gambles » ajoutés par `670a148` n'envoient qu'un groupe à la fois.
Position à reprendre en test : W4 en (9,1), W5 en (9,2), V8 en (8,2), Loups-garous à
jouer, demi-coup 15. Hors serveur, AlphaBeta rejoue
`[(9, 1, 4, 8, 2), (9, 2, 5, 8, 1)]` à chaque essai. Partie 16
(`p200_thetrap_OEP-then-AlphaBeta_*.txt`) :
```
OEP       INFO: Turn 7: [(6, 2, 8, 7, 1)] (0.004 seconds)                       -> 8 en (7,1)
AlphaBeta INFO: Turn 7: [(8, 3, 4, 9, 2), (9, 0, 4, 9, 1)] (1.012 seconds)     -> mange 1 humain : 5 en (9,2), 4 en (9,1) ; 9 contre 8
OEP       INFO: Turn 8: [(7, 1, 8, 8, 2)] (0.002 seconds)                       -> 8 en (8,2), au contact des deux groupes
AlphaBeta INFO: Turn 8: [(9, 1, 4, 8, 2), (9, 2, 5, 8, 1)] (0.083 seconds)     -> 4 attaquent 8 (P = 0.25) et perdent ; 5 en (8,1)
OEP       INFO: Turn 9: [(8, 2, 8, 8, 1)] (0.000 seconds)                       -> 8 attaquent 5 (sûr) : OEP 8, AlphaBeta 0
```
Partie 4 : mêmes coups jusqu'au tour 8 d'AlphaBeta (0.110 s). OEP attaque ensuite les 5
avec 7 (`(8, 2, 7, 8, 1)`, P = 0.9) et finit avec 6.

### testmap2 : contact à effectifs égaux (partie 24, Baseline → AlphaBeta, 200)

Il reste 20 humains au centre, qu'aucune armée de 16 ne peut prendre à coup sûr. Les deux
armées de 16 se tournent autour. AlphaBeta répète les deux mêmes coups du tour 22 au
tour 50. Au tour 56, il vient au contact des 16 de Baseline, qui attaque à 50 % et
gagne. Dans cette position, AlphaBeta n'a que deux candidats : s'approcher en (1,10) ou
s'éloigner en (1,12). Hors serveur, il choisit encore (1,10). C'est le schéma
« se met au contact d'une armée de taille proche » du 22/10, qui reste ici à
effectifs égaux.
```
Baseline  INFO: Turn 56: [(1, 8, 16, 0, 9)] (0.000 seconds)                    -> 16 en (0,9), à 2 cases
AlphaBeta INFO: Turn 56: [(0, 11, 16, 1, 10)] (0.086 seconds)                  -> 16 en (1,10), au contact
Baseline  INFO: Turn 57: [(0, 9, 16, 1, 10)] (0.000 seconds)                   -> 16 attaquent 16 (P = 0.5) : Baseline gagne (5 survivants)
```

## Problèmes rencontrés et observations

1. **Nom du dossier.** La première série date aussi du 22 octobre, et son dossier
   `2026-10-22/` existe déjà. Pour ne pas écraser ses logs, qui portent les mêmes noms,
   celle-ci est dans `2026-10-22-670a148/`, du nom du commit testé.

2. **Encodage des relevés de partie.** Lancé par `powershell -File`, `Tee-Object` écrivait
   le résumé `_run.json` en UTF-16, que `analyze.py` ne lit pas. `run_game.ps1` l'écrit
   maintenant en UTF-8 avec `Out-File`. J'ai corrigé le script pendant la série, donc à
   partir de la partie 4. Les 3 fichiers déjà écrits ont été convertis. Les parties et
   les logs des bots ne sont pas concernés.

3. **« fallback » dans les logs de MCTS.** Comme le 22/10, MCTS écrit à chaque coup
   `INFO: Search: ... iterations; fallback=False` (301 lignes), sans aucun vrai fallback.
   La même limite reste valable : AlphaBeta et OEP repassent sur `fallback_moves` en
   silence quand leur recherche ne rend rien, et ce cas ne peut pas être compté dans les logs.

4. **Léger dépassement du budget de 1.5 s.** Un seul coup dépasse 1.507 s : MCTS au
   tour 58 de la partie 20 (`(1.563 seconds)`). Il reste 0.24 s de marge avant l'alerte de
   1.8 s et 0.44 s avant la limite serveur de 2 s. AlphaBeta ne dépasse jamais 1.502 s.

5. **Parties bloquées sur testmap2 : personne ne prend les 20 humains du centre.** Le
   problème du 22/10 est toujours là. Les parties qui vont jusqu'à `MaxPlays` finissent à
   16–14 ou 16–16, avec 20 à 22 humains restants. Les bots répètent les deux mêmes coups
   pendant des dizaines de tours :
   - partie 20 (200, MCTS → AlphaBeta) : AlphaBeta du tour 29 au tour 97, MCTS du tour 21 au tour 96 ;
   - partie 23 (200, AlphaBeta → Baseline) : les deux bots du tour 50 au tour 100 ;
   - partie 19 : AlphaBeta du tour 54 au tour 97, avant que les 2 derniers Loups-garous
     de MCTS attaquent ses 11 (P = 0.09) au demi-coup 198 ;
   - parties 22 et 24 : AlphaBeta du tour 22 au tour 45, et du tour 22 au tour 50.

6. **OEP joue en 9 ms en moyenne (57 ms au maximum).** Rien de nouveau : c'est sa
   configuration par défaut (12 générations de 16 individus).

7. **Les logs des bots n'ont pas d'horodatage.** Comme le 22/10, j'ai horodaté les lignes
   de l'extérieur pendant la partie, et le résultat final a été lu dans la fenêtre du
   serveur. Ces relevés ne sont pas commités. `scripts/server-runs/README.md` explique comment
   les refaire.

8. **Logs commités.** `CONTRIBUTING.md` demande de garder les logs générés hors des commits.
   Ceux-ci sont ajoutés à la demande, sur la branche `server-runs` seulement, avec
   l'extension `.txt` (`.gitignore` ignore `*.log`). C'est à trancher avant un éventuel
   merge dans `main`. La branche `server-runs` part de `10f337e` et ne contient pas `670a148` :
   pour rejouer la série sur `main`, il faut prendre les scripts sur `server-runs` (voir
   le README des scripts).

## Fichiers

Un log par bot et par partie, nommé `p<MaxPlays>_<map>_<1er connecté>-then-<2e connecté>_<bot>.txt`.
Par exemple, `p200_testmap2_Baseline-then-AlphaBeta_AlphaBeta.txt` est le log
d'AlphaBeta dans la partie 24. Il y a 48 fichiers. Les scripts qui ont joué et analysé la
série sont dans [`scripts/server-runs/`](../../../scripts/server-runs/).
