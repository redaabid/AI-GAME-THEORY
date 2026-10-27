"""Check experiment controls and repetition accounting independently of MCTS."""

from pathlib import Path
import unittest

from agents import Agent, register
from benchmark_mcts import run_benchmark
from game import Cell
from simulator import Position, load_map
from tournament import ROLES, play_match

ROOT = Path(__file__).resolve().parents[1]


@register("test-shuttle")
class Shuttle(Agent):
    def choose_moves(self, position, context):
        (x, y), count = position.to_game_state().groups()[0]
        tx = {0: 1, 1: 0, 3: 4, 4: 3}[x]
        return [(x, y, count, tx, y)]


class BenchmarkTests(unittest.TestCase):
    def test_repetitions_count_complete_boards_and_losing_turns(self):
        initial = Position(1, 5, {(0, 0): Cell(vampires=6), (4, 0): Cell(werewolves=8)})
        result = play_match(initial, {s: "test-shuttle" for s in ("vampires", "werewolves")},
                            seed=0, max_plies=10, move_time=0)
        self.assertEqual(result["termination"], "ply_limit")
        self.assertEqual(result["winner"], "werewolves")
        for species in ("vampires", "werewolves"):
            stats = result["stats"][species]
            self.assertEqual(stats["repeated_positions"], 3)
            self.assertEqual(stats["repeated_while_behind"], 3 if species == "vampires" else 0)
            self.assertEqual(stats["behind_moves"], 5 if species == "vampires" else 0)

    def test_four_variants_get_identical_maps_roles_and_battle_seeds(self):
        initial = load_map(ROOT / "maps" / "endgame.xml")
        report = run_benchmark([("endgame", initial)], iterations=4, max_plies=4, opponent="baseline")
        self.assertEqual(len(report["summaries"]), 4)
        self.assertIn("agents/mcts_memory.py", report["source_sha256"])
        role_seeds = []
        for label, games in report["games"].items():
            with self.subTest(variant=label):
                self.assertEqual(len(games), 4)
                self.assertEqual({(g["a_species"], g["first"]) for g in games}, set(ROLES))
                role_seeds.append([(g["a_species"], g["first"], g["seed"]) for g in games])
                row = report["summaries"][label]
                self.assertEqual(row["wins"] + row["draws"] + row["losses"], 4)
                self.assertEqual(row["faults"], 0)
                self.assertLessEqual(row["repeated_positions"], row["moves"])
        self.assertTrue(all(seeds == role_seeds[0] for seeds in role_seeds))


if __name__ == "__main__":
    unittest.main()
