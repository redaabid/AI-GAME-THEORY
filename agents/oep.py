"""Online Evolutionary Planning (Justesen et al. 2016), adapted to Vampires vs Werewolves (E1).

A genome gives each of our groups one option: the orders of a playbook script,
or a direct order toward a human group, an enemy it can kill, or an ally. The
population is seeded with every script applied to all groups, then evolves by
uniform crossover and mutation. Fitness plays the genome's turn (uncertain
battles weighted by probability), lets both sides follow scripts for `horizon`
plies, and evaluates the result with the clock. With several opponent scripts,
the fitness is the worst case among them (robust to the opponent's style).
"""

from itertools import product
import random
import time

from agents import Agent, fallback_moves, register
from evaluation import WEIGHTS, evaluate
from game import distance
from lookahead import outcomes
from macro import Order, orders_to_moves
from playbook import SCRIPTS, View, playout
from simulator import opponent


def options_for(view, cell, n, targets=4):
    """Distinct order lists one group can follow this turn."""
    options, seen = [], set()

    def add(orders):
        signature = tuple(orders)
        if orders and signature not in seen:
            seen.add(signature)
            options.append(orders)

    for script in SCRIPTS.values():
        add(script(view, cell, n))
    humans = sorted((distance(cell, p), p) for p, h in view.humans if h <= n)
    for _, p in humans[:targets]:
        add([Order(cell, n, p)])
    for p, m in view.enemy:
        if 2 * n >= 3 * m:
            add([Order(cell, n, p)])
    for p, _ in view.own:
        if p != cell:
            add([Order(cell, n, p)])
    return options


@register("oep")
class OnlineEvolution(Agent):
    def __init__(self, population=16, generations=12, horizon=8, mutation=0.3, elite=4,
                 opponents=("eat", "attack"), max_risky=2, weights=None):
        if any(s not in SCRIPTS for s in opponents):
            raise ValueError(f"Opponent scripts must be among {sorted(SCRIPTS)}.")
        self.population, self.generations, self.horizon = population, generations, horizon
        self.mutation, self.elite, self.opponents = mutation, elite, tuple(opponents)
        self.max_risky = max_risky
        self.weights = WEIGHTS | (weights or {})
        self.rng = random.Random(0)

    def new_game(self, position, species, seed):
        self.rng = random.Random(seed)

    def choose_moves(self, position, context):
        deadline, max_plies = context.deadline, context.max_plies
        me, rng = position.to_play, self.rng
        view = View(position)
        cells = [cell for cell, _ in view.own]
        choices = [options_for(view, cell, n) for cell, n in view.own]
        fitness = {}

        def check():
            if deadline is not None and time.perf_counter() >= deadline:
                raise TimeoutError

        def turn(genome):
            orders = [order for options, gene in zip(choices, genome) for order in options[gene]]
            return orders_to_moves(position, orders)[0]

        def score(genome):
            if genome in fitness:
                return fitness[genome]
            moves = turn(genome)
            if not moves:
                fitness[genome] = -float("inf")
                return fitness[genome]
            value = 0.0
            for q, child in outcomes(position, moves, self.max_risky):
                if q <= 0:
                    continue
                worst = float("inf")
                for script in self.opponents:
                    check()
                    # We keep eating in the playout; the opponent follows `script`.
                    ours = {cell: "eat" for cell, c in child.cells.items() if getattr(c, me)}
                    final = playout(child, {me: ours}, horizon=self.horizon, default=script,
                                    max_plies=max_plies, deadline_check=check)
                    worst = min(worst, evaluate(final, me, self.weights, max_plies))
                value += q * worst
            fitness[genome] = value
            return value

        def mutate(genome):
            genes = list(genome)
            for index, options in enumerate(choices):
                if len(options) > 1 and rng.random() < self.mutation:
                    genes[index] = rng.randrange(len(options))
            return tuple(genes)

        # Seeds: each script applied to every group.
        seeds = {tuple(options.index(script(view, cell, n)) for options, (cell, n) in zip(choices, view.own))
                 for script in SCRIPTS.values()}
        population = sorted(seeds)
        space = 1
        for options in choices:
            space *= len(options)
        if space <= 4 * self.population:
            population = list(product(*(range(len(options)) for options in choices)))  # Small: try all.
        while len(population) < self.population:
            population.append(tuple(rng.randrange(len(options)) for options in choices))
        best, generations, stale = None, 0, 0
        try:
            population.sort(key=score, reverse=True)
            best = population[0]
            limit = self.generations if deadline is None else 10 ** 6
            # Stop early once the space is exhausted or three generations bring nothing new.
            while generations < limit and len(fitness) < space and stale < 3:
                check()
                known = len(fitness)
                parents = population[:max(2, self.elite)]
                children = population[:self.elite]
                while len(children) < self.population:
                    a, b = rng.sample(parents, 2) if len(parents) > 1 else (parents[0], parents[0])
                    child = tuple(x if rng.random() < 0.5 else y for x, y in zip(a, b))
                    children.append(mutate(child))
                population = sorted(set(children), key=score, reverse=True)
                best = population[0]
                generations += 1
                stale = stale + 1 if len(fitness) == known else 0
        except TimeoutError:
            if fitness:
                best = max(fitness, key=fitness.get)
        self.info = {"generations": generations, "evaluated": len(fitness), "groups": len(cells)}
        moves = turn(best) if best is not None else []
        return moves or fallback_moves(position)
