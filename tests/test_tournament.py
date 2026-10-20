"""Agent registry, safety net, generated maps, and round-robin tournament checks."""

from pathlib import Path
import random
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from agents import Agent, TurnContext, make_agent, parse_spec, register, safe_choose
from candidates import supported_turn
from game import Cell
from mapgen import FAMILIES, generate_maps, mirror, random_map, write_map
from simulator import Position, get_outcome, load_map
from tournament import ROLES, bradley_terry_elo, play_match, run_tournament, summarize

ROOT = Path(__file__).resolve().parents[1]


@register("test-crash")
class CrashAgent(Agent):
    def choose_moves(self, position, context):
        raise RuntimeError("model bug")


@register("test-illegal")
class IllegalAgent(Agent):
    def choose_moves(self, position, context):
        (x, y), count = position.to_game_state().groups()[0]
        return [(x, y, count + 1, x, y)]


@register("test-slow")
class SlowAgent(Agent):
    def __init__(self, sleep=0.05):
        self.sleep = sleep

    def choose_moves(self, position, context):
        time.sleep(self.sleep)
        return make_agent("baseline").choose_moves(position, context)


def board(records, *, rows=5, columns=7, **kwargs):
    return Position(rows, columns, {(x, y): Cell(h, v, w) for x, y, h, v, w in records}, **kwargs)


DUEL = board([(0, 0, 0, 6, 0), (6, 4, 0, 0, 6), (3, 2, 4, 0, 0)])


class RegistryTests(unittest.TestCase):
    def test_spec_parsing_and_variants(self):
        self.assertEqual(parse_spec("mcts:iterations=64, exploration=1.0"),
                         ("mcts", {"iterations": 64, "exploration": 1.0}))
        self.assertEqual(parse_spec("baseline"), ("baseline", {}))
        self.assertEqual(make_agent("mcts:iterations=16").config.iterations, 16)
        self.assertEqual(make_agent("test-slow:sleep=0.5").sleep, 0.5)

    def test_bad_specs(self):
        for spec in ("nope", "mcts:iterations", "mcts:depth=3", "baseline:x=1"):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                make_agent(spec)

    def test_builtin_agents_return_legal_turns(self):
        for spec in ("random", "baseline", "mcts:iterations=8"):
            agent = make_agent(spec)
            agent.new_game(DUEL, "vampires", 0)
            moves, fault = safe_choose(agent, DUEL, TurnContext(None, 50))
            with self.subTest(spec=spec):
                self.assertIsNone(fault)
                self.assertTrue(supported_turn(DUEL.to_game_state(), moves))


class SafetyTests(unittest.TestCase):
    def test_crash_and_illegal_turns_fall_back_to_a_legal_move(self):
        for spec, reason in (("test-crash", "RuntimeError"), ("test-illegal", "illegal")):
            moves, fault = safe_choose(make_agent(spec), DUEL, TurnContext(None, 50))
            with self.subTest(spec=spec):
                self.assertIn(reason, fault)
                self.assertTrue(supported_turn(DUEL.to_game_state(), moves))

    def test_faulty_agent_finishes_games_and_faults_are_counted(self):
        result = play_match(DUEL, {"vampires": "test-crash", "werewolves": "baseline"},
                            seed=1, max_plies=20, move_time=0)
        self.assertGreater(len(result["stats"]["vampires"]["faults"]), 0)
        self.assertEqual(result["stats"]["werewolves"]["faults"], [])

    def test_slow_turns_are_skipped_like_the_server(self):
        result = play_match(DUEL, {"vampires": "test-slow:sleep=0.03", "werewolves": "baseline"},
                            seed=1, max_plies=6, move_time=0.02, margin=0.01)
        self.assertEqual(result["stats"]["vampires"]["timeouts"], 3)
        self.assertEqual(result["plies"], 6)
        self.assertEqual(result["final_populations"]["vampires"], 6)  # Never moved.


class MapTests(unittest.TestCase):
    def test_generated_maps_are_symmetric_fair_and_deterministic(self):
        for family in FAMILIES:
            for seed in range(20):
                position = random_map(random.Random(seed), family)
                with self.subTest(family=family, seed=seed):
                    self.assertIsNone(get_outcome(position))
                    for cell, content in position.cells.items():
                        other = position.cells[mirror(cell, position.rows, position.columns)]
                        self.assertEqual((content.humans, content.vampires), (other.humans, other.werewolves))
                    self.assertLessEqual(sum(c.humans + c.vampires + c.werewolves
                                             for c in position.cells.values()), 255)
        self.assertEqual(generate_maps(3, split="val"), generate_maps(3, split="val"))
        self.assertNotEqual(generate_maps(3, split="val"), generate_maps(3, split="test"))

    def test_xml_round_trip(self):
        name, position = generate_maps(1, family="small")[0]
        with TemporaryDirectory() as folder:
            path = Path(folder) / f"{name}.xml"
            write_map(position, path)
            self.assertEqual(load_map(path), position)


class TournamentTests(unittest.TestCase):
    def test_round_robin_balances_roles_and_shares_seeds(self):
        names = ["baseline", "random", "test-crash"]
        results = run_tournament(names, [("duel", DUEL)], rounds=1, max_plies=30, move_time=0)
        self.assertEqual(len(results), 3 * len(ROLES))
        for i, j in ((0, 1), (0, 2), (1, 2)):
            roles = {(r["a_species"], r["first"]) for r in results if (r["i"], r["j"]) == (i, j)}
            self.assertEqual(roles, set(ROLES))
        by_role = {}
        for r in results:
            by_role.setdefault((r["a_species"], r["first"]), set()).add(r["seed"])
        self.assertTrue(all(len(seeds) == 1 for seeds in by_role.values()))

        matrix, ranking = summarize(names, results)
        self.assertAlmostEqual(matrix["baseline vs random"]["mean_score"]
                               + matrix["random vs baseline"]["mean_score"], 1)
        self.assertEqual(ranking[0]["agent"], "baseline")
        self.assertGreater(next(r for r in ranking if r["agent"] == "test-crash")["faults"], 0)

    def test_elo_orders_agents_by_score(self):
        score = [[0, 9, 10], [1, 0, 8], [0, 2, 0]]
        games = [[0, 10, 10], [10, 0, 10], [10, 10, 0]]
        elo = bradley_terry_elo(["a", "b", "c"], score, games, anchor="b")
        self.assertEqual(elo[1], 0)
        self.assertGreater(elo[0], elo[1])
        self.assertGreater(elo[1], elo[2])

    def test_command_line_with_parallel_workers(self):
        with TemporaryDirectory() as folder:
            output = Path(folder) / "report.json"
            result = subprocess.run(
                [sys.executable, "tournament.py", "--agents", "baseline", "random", "--random-maps", "1",
                 "--family", "small", "--max-plies", "20", "--move-time", "0", "--workers", "2",
                 "--output", str(output)], cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("| 1 | baseline |", result.stdout)
            self.assertTrue(output.exists() and output.with_suffix(".md").exists())


if __name__ == "__main__":
    unittest.main()
