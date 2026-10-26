"""Archive completed 40-ply replays, old-agent controls and decision probes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize_ab_server import summarize

EXPECTED = {1, 4, 7, 8, 9, 10, 11, 17, 65, 66, 67, 68}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--followup', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    replay = summarize(args.followup/'real-server')
    if {r['id'] for r in replay} != EXPECTED or not all(r['ui']['confirmed'] for r in replay):
        p.error('All twelve new WPF results must be explicitly confirmed before final publication')
    if any(r['max_plies'] != 40 for r in replay):
        p.error('A 200-ply result cannot enter this report')
    if args.output.exists():
        p.error('Refusing to replace a previous report')
    args.output.mkdir(parents=True)
    (args.output/'.gitattributes').write_text('* -text\n', encoding='utf8')
    def copy_game(src, dst):
        dst.mkdir(parents=True)
        for f in src.iterdir():
            if f.is_file() and f.suffix in ('.json', '.config', '.log', '.txt'):
                shutil.copy2(f, dst/f.name)
    for r in summarize(args.original):
        if r['max_plies'] == 40:
            copy_game(args.original/r['directory'], args.output/'original'/r['directory'])
    for r in replay:
        copy_game(args.followup/'real-server'/r['directory'], args.output/'replayed'/r['directory'])
    shutil.copytree(args.followup/'decisions', args.output/'decisions')
    subprocess.run([sys.executable, '-B', str(ROOT/'scripts/summarize_ab_server.py'),
                    str(args.output), '--max-plies', '40'], check=True, stdout=subprocess.DEVNULL)
    aggregate = json.loads((args.output/'aggregate-40.json').read_text(encoding='utf8'))
    probe = json.loads((args.output/'decisions/summary.json').read_text(encoding='utf8'))
    protocol = dict(rerun_ids=sorted(EXPECTED-{65,66,67,68}), control_ids=[65,66,67,68],
                    alias_ab90='Original unchanged alphabeta agent with default parameters',
                    max_plies=40, new_games=12, original_games=32,
                    note='Replays replace missing conditions in the composed comparison, not the '
                    'unknown outcomes of the original random games. All attempts are retained. '
                    'No 200-ply game was scheduled. The launcher was stopped after job 4 '
                    'to retain the final window while the user restored it; then resumed with remaining IDs.',
                    source_sha=subprocess.check_output(['git','-c','safe.directory=*','rev-parse','HEAD'],
                                                       cwd=ROOT, text=True).strip())
    (args.output/'protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf8')
    lines = ['# Contrôles à 40 coups — verdicts, décisions et ancien bot', '',
             '**12 nouvelles parties WPF terminées et confirmées : huit cas rejoués et quatre contrôles.** '
             'Les 32 conditions de la famille AB sont désormais couvertes par un résultat confirmé ; '
             'les quatre contrôles supplémentaires opposent AB3 à l’ancien alphabeta.', '',
             'Les huit verdicts initiaux absents restent inconnus. Les nouvelles parties rejouent les mêmes '
             'conditions mais peuvent avoir une issue différente, car le hasard du serveur n’est pas contrôlé. '
             'Le tableau composé retient une tentative confirmée par condition ; aucune partie n’est comptée deux fois.', '',
             '## Bilan composé contre AB3', '',
             '| Profil | Parties | V / N / D | Max (s) | Moyenne (s) | Faults |',
             '|---|---:|---|---:|---:|---:|']
    for name, s in sorted(aggregate['architectures'].items()):
        label = 'ancien alphabeta (AB90)' if name == 'ab90' else name
        lines.append(f'| {label} | {s["games"]} | {s["wins"]}/{s["draws"]}/{s["losses"]} | '
                     f'{s["max_seconds"]:.3f} | {s["mean_seconds"]:.3f} | {s["faults"]} |')
    lines += ['', 'AB3 est le témoin commun : sa ligne regroupe tous les adversaires. AB7 désigne ici '
              'le profil historique ; le nouveau poids discount=0,97 est seulement inclus dans le contrôle '
              'de décisions, pas dans ces nouveaux matchs WPF.', '',
              '## Ancien bot sur les deux cartes', '',
              'AB90 est uniquement le nom ASCII attribué à l’agent existant --agent alphabeta. '
              'Son code est inchangé, ses paramètres natifs sont conservés. Les deux ordres de connexion '
              'sont joués sur chaque carte, avec le même serveur, MaxPlays=40 et --move-time 1.5.', '',
              '| Carte | Ordre | Vainqueur WPF | Effectifs dans cet ordre |',
              '|---|---|---|---|']
    for r in replay:
        if r['id'] < 65:
            continue
        a,b = r['order']
        pop = r['ui']['populations']
        lines.append(f'| {r["map"]} | {a} puis {b} | {r["ui"]["winner"]} | {pop.get(a)} / {pop.get(b)} |')
    legacy_big = [r for r in replay if r['id'] in (67,68)]
    draws = sum(r['ui']['winner']=='draw' for r in legacy_big)
    lines += ['', f'Sur testmap2, le contrôle avec l’ancien bot donne **{draws}/2 nuls**. '
              'Quatre parties ne permettent pas une attribution causale complète. L’ancien bot partage '
              'aussi l’évaluation et des composants du simulateur avec la famille AB.', '',
              '## Décisions à profondeur fixe', '',
              'Douze positions identiques : huit états reconstruits des UPD du vrai serveur '
              '(avant les coups 1, 9, 17 et 29 sur les deux cartes), puis quatre cartes générées nouvelles. '
              'Tous les agents ont effectivement terminé une recherche de profondeur 2, sans deadline. '
              'AB5 conserve sa quiescence bornée ; AB6 conserve les nœuds de chance.', '',
              '| Profil | Choix différents d’AB3, paramètres communs /12 | Profils réglés /12 |',
              '|---|---:|---:|']
    for name, s in probe['summary']['common'].items():
        lines.append(f'| {name} | {s["different_from_ab3"]} | '
                     f'{probe["summary"]["selected"][name]["different_from_ab3"]} |')
    lines += ['', 'Les paramètres communs normalisent la famille AB0–AB8. Le témoin legacy garde '
              'sa largeur native (10), donc son écart ne mesure pas uniquement son algorithme.', '',
              '**AB0/AB1/AB2/AB8 ont les mêmes choix et valeurs sur les douze positions à paramètres '
              'communs. AB3 et AB4 aussi.** C’est attendu pour des optimisations de recherche qui visent '
              'à calculer la même décision plus efficacement. À temps limité, elles peuvent atteindre '
              'des profondeurs différentes et donc jouer différemment.', '',
              'AB6 choisit ici les mêmes actions qu’AB3, mais sa valeur diffère sur une position '
              '(generated-44002 : +1 000 000 pour le substitut déterministe, 0 pour la moyenne stochastique). '
              'Cela montre une différence de modèle sans garantir un changement d’action dans cet échantillon. '
              'L’ancien AB7 fait doublon ; le nouveau AB7 change une décision sur douze.', '',
              '## Comparaison avec les anciens rapports', '',
              'Le [rapport du 22 octobre](../../2026-10-22-670a148/SUMMARY.md) indique déjà deux nuls '
              '16–16 contre OEP sur testmap2 à 40 coups. Contre MCTS et baseline, les quatre victoires '
              'sur cette carte à 40 coups étaient des scores 16–14 au plafond, sans élimination. '
              'Les anciennes parties différaient donc aussi par l’adversaire et sa collecte des humains. '
              'Machine, commit et archive du serveur historiques diffèrent ; ce contrôle ne prétend pas '
              'reproduire exactement ces anciens matchs.', '',
              '## Données et limites', '',
              '[Tableau de chaque condition](SUMMARY-40.md), [toutes les tentatives](aggregate-40.json), '
              '[décisions et états complets](decisions/decisions.json), [protocole](protocol.json).', '',
              'Les résultats de force portent sur quatre parties par challenger, avec combats aléatoires. '
              'Ce sont des tendances exploratoires. Les temps imprimés sont arrondis ; les recherches '
              'sans deadline du contrôle de décisions ne sont pas des mesures sous la limite de deux secondes. '
              'Le compteur de secours internes n’est pas instrumenté dans l’ancien bot ; seuls les faults '
              'et occurrences de fallback présents dans ses logs peuvent être contrôlés.', '',
              'Aucun bot existant n’a été modifié, aucun match à 200 coups n’a été lancé dans ce contrôle.']
    (args.output/'SUMMARY.md').write_text('\n'.join(lines)+'\n', encoding='utf8')
    hashes = [hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(args.output).as_posix()
              for f in sorted(args.output.rglob('*')) if f.is_file() and f.name != 'SHA256SUMS.txt']
    (args.output/'SHA256SUMS.txt').write_text('\n'.join(hashes)+'\n', encoding='utf8')
    print(json.dumps(dict(conditions=len(aggregate['games']), confirmed=sum(
        r['ui']['confirmed'] for r in aggregate['games']), attempts=len(aggregate['attempts']),
        legacy_testmap_draws=draws)))


if __name__ == '__main__':
    main()
