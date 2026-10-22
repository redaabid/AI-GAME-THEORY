# Séries de parties sur le serveur du cours

Ces scripts rejouent la série de `docs/server-runs/` : AlphaBeta contre MCTS, OEP et
Baseline, sur `thetrap.xml` et `testmap2.xml`, avec `MaxPlays` à 40 puis à 200, et
chaque match dans les deux ordres de connexion. Cela fait 24 parties, environ 30 minutes.

Il faut Windows, Python 3.10 ou plus récent, l'archive du cours (`Softwares-AAAAMMJJ.zip`,
sur Moodle) et une session de bureau ouverte : le serveur ouvre une fenêtre, et le résultat
est lu dans cette fenêtre. Le port 5555 doit être libre, et aucun autre serveur ne doit tourner.

## Lancer la série

Les bots joués sont ceux du dossier de travail : il faut donc être sur la branche du code
à tester, en général `main`. Ces scripts ne sont que sur `server-runs`. On les copie sans
les commiter, depuis la racine du dépôt :

```powershell
git switch main; git pull --ff-only
git restore --source origin/server-runs -- scripts/server-runs
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\server-runs\run_series.ps1 `
    -Archive C:\chemin\vers\Softwares-20261022.zip -LogDir docs\server-runs\2026-10-22
```

Pour publier ensuite les logs sur `server-runs`, supprimez d'abord la copie des scripts
(`Remove-Item -Recurse scripts\server-runs`), sinon `git switch server-runs` refuse
d'écraser ces fichiers non suivis. Le dossier de logs, nouveau, suit le changement de branche.

Pour chaque valeur de `MaxPlays` puis chaque map, le script prépare le serveur avec
`scripts/setup_server.py`, règle `MaxGameDuration=00:10:00` et `MaxPlays` dans la config
(`set_config.py`), puis joue les 6 parties avec `run_game.ps1`. Options :

| Option | Défaut | Rôle |
|---|---|---|
| `-Maps` | `thetrap.xml, testmap2.xml` | Maps à jouer |
| `-MaxPlays` | `40, 200` | Valeurs de `MaxPlays` |
| `-LogDir` | `docs\server-runs\<date du jour>` | Logs des bots, relatif au dépôt, sans espace |
| `-WorkDir` | `.local\server-runs\<nom de LogDir>` | Relevés de chaque partie (voir plus bas) |

Une partie déjà jouée (son `_run.json` existe dans `WorkDir`) est sautée. Si la série
s'arrête, relancer la même commande la fait reprendre là où elle s'est arrêtée.

`run_game.ps1` joue une partie : il démarre le serveur, connecte le premier bot, puis le
second environ 1 s après la connexion du premier. Le premier connecté joue les Vampires
et joue en premier. Les commandes sont :

```
python main.py --name <Nom> --agent <agent> --max-plies <MaxPlays> 127.0.0.1 5555 > <log> 2>&1
```

## Fichiers produits

Dans `LogDir`, un log par bot et par partie, nommé
`p<MaxPlays>_<map>_<1er connecté>-then-<2e connecté>_<bot>.txt`. L'extension `.txt` permet
de les commiter, car `.gitignore` ignore `*.log`.

Dans `WorkDir`, pour chaque partie, des fichiers qu'on ne commite pas :

- `<tag>_run.json` : commandes, codes de sortie, durée, dépassement du délai de 900 s ;
- `<tag>_timeline.txt` : les lignes des deux logs, horodatées pendant la partie (les logs des
  bots n'ont pas d'horodatage) ; sert à savoir qui a joué en premier ;
- `<tag>_final.png` et `<tag>_final.txt` : capture et textes de la fenêtre du serveur en fin
  de partie, d'où viennent le vainqueur et les effectifs finaux.

## Analyser

```powershell
$run = 'docs\server-runs\2026-10-22'; $work = '.local\server-runs\2026-10-22'
python -I scripts\server-runs\analyze.py $run $work $work\analysis.json
python -I scripts\server-runs\make_table.py $work\analysis.json
python -I scripts\server-runs\compare.py <analysis.json de la série d'avant> $work\analysis.json
python -I scripts\server-runs\oscillation.py "$run\*.txt"
```

- `analyze.py` affiche, pour chaque partie, le vainqueur, les effectifs, et par bot le temps
  max et moyen par coup, les coups au-dessus de 1.8 s, les `Agent fault`, les `fallback=True`
  et les lignes suspectes (erreur, exception, déconnexion…). Il écrit tout dans `analysis.json`.
- `make_table.py` donne, au format de `SUMMARY.md`, le tableau des résultats, le bilan
  d'AlphaBeta par configuration et le tableau des temps et faults par bot.
- `compare.py` compare le bilan d'AlphaBeta entre deux séries : total, par map, par
  adversaire, par `MaxPlays`, puis partie par partie.
- `oscillation.py` donne, pour chaque log, la plus longue suite de coups qui alternent
  entre deux positions (coup N = coup N−2).
- `replay.py` rejoue une partie à partir des deux logs, demi-coup par demi-coup. Il affiche
  le plateau, les combats et leur probabilité de gain. On lui passe la map (copiée dans
  `.local\server\` par `setup_server.py`), le log du premier connecté, celui du second, et
  éventuellement les effectifs finaux affichés par le serveur. Exemple :

  ```powershell
  python -I scripts\server-runs\replay.py .local\server\thetrap.xml `
      "$run\p200_thetrap_OEP-then-AlphaBeta_OEP.txt" "$run\p200_thetrap_OEP-then-AlphaBeta_AlphaBeta.txt" 8 0
  ```

  Les logs ne donnent pas l'issue des combats aléatoires. Le script choisit donc une issue
  compatible avec les coups suivants, qui n'est pas forcément celle qui a eu lieu.

Une ligne `fallback=False` n'est pas un fallback : MCTS l'écrit à chaque coup. Seuls
`Agent fault` et `fallback=True` comptent.
