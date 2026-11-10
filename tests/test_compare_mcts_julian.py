"""Pin the external opponent and fairness/provenance without running a campaign."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from game import Cell
from scripts.compare_mcts_julian import OPPONENTS, PROFILE_FILE, comparison_plan
from simulator import Position
from tournament import ROLES

ROOT = Path(__file__).resolve().parents[1]
BOARD = Position(3, 7, {(0, 1): Cell(vampires=6), (6, 1): Cell(werewolves=6),
                         (3, 1): Cell(humans=4)})


class ComparisonPlanTests(unittest.TestCase):
    def test_each_opponent_matches_the_published_spec_without_changing_any_setting(self):
        retained = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        for label, profile in OPPONENTS.items():
            with self.subTest(label=label):
                plan = comparison_plan("mcts-v3", label, maps=[("fixture", BOARD)])
                self.assertEqual(plan["agents"][1], retained["profiles"][profile])
                self.assertEqual(plan["comparison"]["published_status"], retained["validation_status"][profile])

    def test_four_maps_two_rounds_give_32_balanced_games_at_the_existing_budget(self):
        maps = [(f"map-{i}", BOARD) for i in range(4)]
        plan = comparison_plan("mcts-v3", "width7", maps=maps)
        self.assertEqual(plan["agents"][0], "mcts-v3:iterations=100000")
        self.assertEqual(len(plan["jobs"]), 32)
        for map_name, _ in maps:
            for round_index in range(2):
                jobs = [j for j in plan["jobs"] if j["map_name"] == map_name and j["round"] == round_index]
                self.assertEqual({(j["a_species"], j["first"]) for j in jobs}, set(ROLES))
                self.assertTrue(all(j["settings"] == dict(max_plies=200, move_time=2.0,
                                                         margin=0.5, on_timeout="skip") for j in jobs))
        self.assertEqual(len(plan["comparison"]["launcher_sha256"]), 64)
        self.assertEqual(len(plan["comparison"]["retained_profiles_sha256"]), 64)

    def test_v1_is_available_as_a_control_and_explicit_caps_are_respected(self):
        plan = comparison_plan("mcts-v1:iterations=64", "reference", maps=[("fixture", BOARD)])
        self.assertEqual(plan["agents"][0], "mcts-v1:iterations=64")

    def test_cli_preview_does_not_start_games_or_create_checkpoint_files(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "checkpoint"
            result = subprocess.run([sys.executable, "scripts/compare_mcts_julian.py", "--agent", "mcts-v3",
                                     "--opponent", "width7", "--maps", "maps", "--dry-run",
                                     "--checkpoint", str(directory)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("32 games | 4 maps | 2 rounds", result.stdout)
            self.assertIn("ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000", result.stdout)
            self.assertIn("No games started", result.stdout)
            self.assertFalse(directory.exists())


if __name__ == "__main__":
    unittest.main()
