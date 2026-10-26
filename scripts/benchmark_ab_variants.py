"""Bounded train/validation search for every AB architecture, no test-map tuning.

Three candidates per architecture, equal game counts/budgets. This is a modest
parameter search, not a claim of global optimality or a substitute for WPF games.
"""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import platform
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import TurnContext, make_agent, safe_choose
from evaluation import WEIGHTS
from mapgen import random_map
from simulator import get_outcome, opponent, simulate_turn


def spec(name, params):
    return name + ':' + ','.join(f'{k}={v!r}' for k, v in params.items())


def configurations(name):
    result = []
    for i, width in enumerate((6, 10, 16)):
        params = dict(width=width, depth=i + 1, max_depth=8,
                      extra=(0, 4, 8)[i], tt_size=50000,
                      qdepth=(1, 2, 2)[i], qwidth=(2, 3, 4)[i],
                      aspiration=(25000, 50000, 100000)[i])
        if name == 'ab7':
            params['weights'] = [dict(WEIGHTS),
                                 WEIGHTS | dict(humans=1.1, threat=1.0),
                                 WEIGHTS | dict(humans=.5, threat=1.1, groups=.2)][i]
        result.append(spec(name, params))
    return result


def play(initial, candidate, candidate_species, *, budget, max_plies, seed):
    agents = {candidate_species: make_agent(candidate),
              opponent(candidate_species): make_agent('alphabeta:width=10,max_depth=8')}
    for species, agent in agents.items():
        agent.new_game(initial, species, seed)
    position = initial
    histories = {s: [] for s in agents}
    rng = random.Random(seed)
    timings, faults, bootstraps, late = [], [], 0, 0
    details = []
    while (outcome := get_outcome(position, max_plies=max_plies)) is None:
        species = position.to_play
        started = time.perf_counter()
        moves, fault = safe_choose(agents[species], position,
                                   TurnContext(started + budget, max_plies, histories[species]))
        elapsed = time.perf_counter() - started
        if species == candidate_species:
            timings.append(elapsed)
            if fault:
                faults.append(fault)
            late += elapsed > budget + .03
            info = agents[species].info or {}
            bootstraps += bool(info.get('bootstrap'))
            details.append(info)
        histories[species].append((position, moves))
        position = simulate_turn(position, moves, rng)
    totals = {s: sum(getattr(c, s) for c in position.cells.values()) for s in agents}
    score = .5 if outcome.winner is None else float(outcome.winner == candidate_species)
    return dict(score=score, winner=outcome.winner, reason=outcome.reason,
                plies=position.ply, candidate_species=candidate_species, seed=seed,
                final_populations=totals, seconds=timings, faults=faults,
                bootstraps=bootstraps, late=late, metrics=details)


def evaluate(candidate, seeds, budget, max_plies):
    games = []
    for seed in seeds:
        initial = random_map(random.Random(seed), 'small')
        for species in ('vampires', 'werewolves'):
            games.append(play(initial, candidate, species, budget=budget,
                              max_plies=max_plies, seed=seed * 13))
    timings = [t for g in games for t in g['seconds']]
    return dict(spec=candidate, games=games,
                score=sum(g['score'] for g in games) / len(games),
                faults=sum(len(g['faults']) for g in games),
                bootstraps=sum(g['bootstraps'] for g in games),
                late=sum(g['late'] for g in games),
                max_seconds=max(timings, default=0),
                mean_seconds=sum(timings) / max(1, len(timings)))


def ranking(record):
    return (-record['faults'], -record['late'], record['score'],
            -record['bootstraps'], -record['mean_seconds'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--train-budget', type=float, default=.04)
    p.add_argument('--validation-budget', type=float, default=.08)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / 'selection.json').exists():
        p.error('Output already contains a selection; use a fresh run directory')
    logging.basicConfig(filename=args.output / 'search-metrics.log', level=logging.INFO)
    report = dict(created=datetime.now(timezone.utc).isoformat(),
                  python=sys.version, platform=platform.platform(),
                  train_seeds=[11001, 11002], validation_seeds=[22001, 22002],
                  train_budget=args.train_budget, validation_budget=args.validation_budget,
                  train_plies=16, validation_plies=24, architectures={})
    for name in (f'ab{i}' for i in range(9)):
        print('Training', name, flush=True)
        training = [evaluate(s, report['train_seeds'], args.train_budget, 16)
                    for s in configurations(name)]
        finalists = sorted(training, key=ranking, reverse=True)[:2]
        validation = [evaluate(r['spec'], report['validation_seeds'], args.validation_budget, 24)
                      for r in finalists]
        selected = max(validation, key=ranking)
        report['architectures'][name] = dict(training=training, validation=validation,
                                             selected=selected['spec'])
        (args.output / 'selection.json').write_text(json.dumps(report, indent=2), encoding='utf8')
        print(name, 'selected', selected['spec'], 'validation score', selected['score'], flush=True)
    print('Selection saved:', args.output / 'selection.json', flush=True)


if __name__ == '__main__':
    main()
