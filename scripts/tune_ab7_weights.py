"""Weight-only AB7 screening against frozen AB3; no WPF or 200-ply games.

Keeps the historical selection intact. Exports an experimental distinct profile
even if no improvement is established, but never promotes a tied/weaker result.
"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import random
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents import TurnContext, make_agent, parse_spec
from benchmark_ab_variants import play, spec
from evaluation import WEIGHTS
from mapgen import random_map, write_map


TRAIN = [(41001, 'small'), (41002, 'small'), (41003, 'small')]
VALIDATION = [(42001, 'small'), (42002, 'small'), (42003, 'medium'), (42004, 'medium')]


def candidates(params):
    variants = [('baseline', {})]
    for key, values in dict(humans=(.2, 1.6), discount=(.75, .97),
                            threat=(0., 1.5), groups=(0., .6)).items():
        variants.extend((f'{key}-{value}', {key: value}) for value in values)
    variants.append(('joint', dict(humans=1.3, threat=1.2, groups=.3)))
    return [dict(id=name, weights=WEIGHTS | change,
                 spec=spec('ab3', params) if name == 'baseline' else
                 spec('ab7', params | dict(weights=WEIGHTS | change)))
            for name, change in variants]


def evaluate(candidate, maps, budget, reference, output, stage):
    games = []
    for seed, family in maps:
        position = random_map(random.Random(seed), family)
        write_map(position, output/'maps'/f'{stage}-{seed}-{family}.xml')
        for species in ('vampires', 'werewolves'):
            game = play(position, candidate['spec'], species, budget=budget,
                        max_plies=40, seed=seed * 17, reference=reference)
            game.update(map_seed=seed, family=family)
            games.append(game)
    times = [t for g in games for t in g['seconds']]
    return candidate | dict(games=games, score=sum(g['score'] for g in games)/len(games),
                            wins=sum(g['score'] == 1 for g in games),
                            draws=sum(g['score'] == .5 for g in games),
                            losses=sum(g['score'] == 0 for g in games),
                            faults=sum(len(g['faults']) + len(g['reference_faults']) for g in games),
                            late=sum(g['late'] for g in games),
                            bootstraps=sum(g['bootstraps'] for g in games),
                            max_seconds=max(times, default=0),
                            mean_seconds=sum(times)/max(1, len(times)))


def rank(record):
    return (-record['faults'], -record['late'], record['score'],
            -record['bootstraps'], -record['mean_seconds'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--train-budget', type=float, default=.08)
    p.add_argument('--validation-budget', type=float, default=.2)
    args = p.parse_args()
    if any(not 0 < b <= 1.5 for b in (args.train_budget, args.validation_budget)):
        p.error('budgets must be positive and at most 1.5 s')
    if args.output.exists():
        p.error('Use a new output directory; previous results will not be replaced')
    previous = json.loads(args.selection.read_text(encoding='utf8'))
    reference = previous['architectures']['ab3']['selected']
    name, params = parse_spec(reference)
    if name != 'ab3' or 'weights' in params:
        p.error('Expected the frozen AB3 profile with common default weights')
    pool = candidates(params)
    for candidate in pool:
        make_agent(candidate['spec'])
    args.output.mkdir(parents=True)
    logging.basicConfig(filename=args.output/'metrics.log', level=logging.INFO)
    report = dict(created=datetime.now(timezone.utc).isoformat(), reference=reference,
                  source_sha=subprocess.check_output(['git', '-c', 'safe.directory=*',
                      'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  engine_sha256=hashlib.sha256((ROOT/'agents/ab_variants.py').read_bytes()).hexdigest(),
                  max_plies=40, train_maps=TRAIN, validation_maps=VALIDATION,
                  train_budget=args.train_budget, validation_budget=args.validation_budget,
                  training=[], validation=[])
    def save():
        (args.output/'results.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    for candidate in pool:
        result = evaluate(candidate, TRAIN, args.train_budget, reference, args.output, 'train')
        report['training'].append(result)
        save()
        print('TRAIN', candidate['id'], 'score', result['score'], flush=True)
    finalists = sorted(report['training'][1:], key=rank, reverse=True)[:2]
    for candidate in [pool[0], *finalists]:
        result = evaluate(candidate, VALIDATION, args.validation_budget,
                          reference, args.output, 'validation')
        report['validation'].append(result)
        save()
        print('VALIDATION', candidate['id'], 'score', result['score'], flush=True)
    baseline = report['validation'][0]
    distinct = max(report['validation'][1:], key=rank)
    improved = (not distinct['faults'] and not distinct['late'] and not distinct['bootstraps']
                and not baseline['faults'] and not baseline['late'] and not baseline['bootstraps']
                and distinct['score'] > baseline['score'])
    report['distinct_candidate'] = distinct['id']
    report['improvement_observed'] = improved
    # An untimed fixed-depth probe isolates actual choice differences from
    # wall-clock fluctuations. Its maps are not used for tuning or promotion.
    differences = []
    for seed in range(43001, 43013):
        position = random_map(random.Random(seed), 'small')
        moves = []
        for agent_spec in (reference, distinct['spec']):
            _, probe_params = parse_spec(agent_spec)
            probe_spec = spec(agent_spec.split(':', 1)[0], probe_params | dict(depth=2))
            agent = make_agent(probe_spec)
            agent.new_game(position, position.to_play, seed)
            moves.append(agent.choose_moves(position, TurnContext(None, 40, [])))
        differences.append(dict(seed=seed, ab3=moves[0], ab7=moves[1], different=moves[0] != moves[1]))
    report['fixed_depth_behavior_probe'] = differences
    save()
    profile = dict(spec=distinct['spec'], weights=distinct['weights'], reference=reference,
                   status='promising_simulator_candidate' if improved else 'experimental_no_gain_established',
                   validation_score=distinct['score'], baseline_score=baseline['score'],
                   warning='Eight validation games per profile; no WPF validation, no 200-ply test. '
                   'Do not replace the historical profile or claim statistical superiority.')
    (args.output/'ab7-candidate.json').write_text(json.dumps(profile, indent=2), encoding='utf8')
    text = ['# AB7 — réglage des poids à recherche identique à AB3',
            '60 parties simulées d’entraînement puis 24 parties de validation séparée, à 40 demi-coups. '
            'Aucun serveur WPF lancé. Les cartes du cours et les anciens résultats restent inchangés.',
            f'Budget : {args.train_budget} s en entraînement, {args.validation_budget} s en validation. '
            'Ces budgets courts ne garantissent pas un gain au budget serveur de 1,5 s.',
            '| Profil validé | V / N / D | Score | Faults | Retards |',
            '|---|---|---:|---:|---:|']
    text += [f'| {r["id"]} | {r["wins"]} / {r["draws"]} / {r["losses"]} | {r["score"]:.3f} | '
             f'{r["faults"]} | {r["late"]} |' for r in report['validation']]
    text += ['', f'Gain observé sur ce lot : **{improved}**. '
             f'Décisions différentes à profondeur fixe : **{sum(x["different"] for x in differences)}/12**.',
             '', f'Profil distinct expérimental : `{distinct["spec"]}`.', '', profile['warning']]
    (args.output/'SUMMARY.md').write_text('\n'.join(text)+'\n', encoding='utf8')
    print(json.dumps(profile), flush=True)


if __name__ == '__main__':
    main()
