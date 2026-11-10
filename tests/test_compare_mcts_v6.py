"""Balanced V6 comparisons, pinned dependencies and Windows checkpoint resume."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from game import Cell
from scripts.compare_mcts_v6 import (PROFILE_FILE, checkpoint_directory,
                                     comparison_plan, source_hashes)
from simulator import Position
from tournament import ROLES

ROOT = Path(__file__).resolve().parents[1]
BOARD = Position(3, 7, {(0, 1): Cell(vampires=6), (6, 1): Cell(werewolves=6),
                         (3, 1): Cell(humans=4)})


class V6LauncherTests(unittest.TestCase):
    def test_default_plan_is_32_balanced_games_against_v5_with_both_versions_pinned(self):
        maps = [(f"map-{i}", BOARD) for i in range(4)]
        plan = comparison_plan(maps=maps)
        self.assertEqual(plan["agents"], ["mcts-v6:iterations=100000", "mcts-v5:iterations=100000"])
        self.assertEqual(len(plan["jobs"]), 32)
        self.assertEqual(plan["v6_source_sha256"], source_hashes())
        expected = {"scripts/compare_mcts_v6.py"} | {
            f"scripts/mcts_v{version}/{file}.py" for version in (5, 6)
            for file in ("__init__", "agent", "value")}
        self.assertEqual(set(source_hashes()), expected)
        for map_name, _ in maps:
            for round_index in range(2):
                jobs = [j for j in plan["jobs"] if j["map_name"] == map_name and j["round"] == round_index]
                self.assertEqual({(j["a_species"], j["first"]) for j in jobs}, set(ROLES))
                self.assertTrue(all(j["settings"] == dict(max_plies=200, move_time=2.0,
                                                         margin=.5, on_timeout="skip") for j in jobs))
        self.assertEqual(len({j["seed"] for j in plan["jobs"]}), 32)

    def test_julian_profiles_are_unchanged_and_keep_their_published_status(self):
        retained = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        for label, profile in (("width7", "ab2_width7"), ("reference", "ab2_reference")):
            plan = comparison_plan(opponent=label, maps=[("fixture", BOARD)])
            self.assertEqual(plan["agents"][1], retained["profiles"][profile])
            self.assertEqual(plan["v6_opponent"]["published_status"], retained["validation_status"][profile])
            self.assertEqual(len(plan["v6_opponent"]["retained_profiles_sha256"]), 64)

    def test_controls_and_opponents_have_separate_default_folders(self):
        plan = comparison_plan(opponent="v1", maps=[("fixture", BOARD)], iterations=64)
        self.assertEqual(plan["agents"], ["mcts-v6:iterations=64", "mcts-v1:iterations=64"])
        self.assertFalse(plan["v6_opponent"])
        control = comparison_plan("mcts-v6:endgame=False,iterations=8", maps=[("fixture", BOARD)])
        self.assertEqual(control["agents"][0], "mcts-v6:endgame=False,iterations=8")
        self.assertEqual(checkpoint_directory("mcts-v6", "v5").name, "mcts-v6-vs-v5")
        self.assertEqual(checkpoint_directory("mcts-v6", "width7").name, "mcts-v6-vs-julian-ab2-width7")
        self.assertNotEqual(checkpoint_directory("mcts-v6", "v5"),
                            checkpoint_directory(control["agents"][0], "v5"))

    def test_invalid_experiments_fail_before_creating_a_campaign(self):
        for kwargs in ({"agent": "mcts-v5"}, {"agent": "mcts-v6:endgame=1"},
                       {"agent": "mcts-v6:endgame_window=0"}, {"iterations": 0},
                       {"rounds": 0}, {"workers": 0}, {"move_time": .5, "margin": .5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                comparison_plan(maps=[("fixture", BOARD)], **kwargs)

    def test_cli_preview_validates_four_maps_and_writes_nothing(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "checkpoint"
            result = subprocess.run([sys.executable, "scripts/compare_mcts_v6.py", "--dry-run", "--maps", "maps",
                                     "--checkpoint", str(directory)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("32 games | 4 maps | 2 rounds", result.stdout)
            self.assertIn("mcts-v5:iterations=100000", result.stdout)
            self.assertIn("window 40 plies", result.stdout)
            self.assertIn("No games started", result.stdout)
            self.assertFalse(directory.exists())

    def test_spawn_workers_resume_without_rerunning_or_mixing_the_control(self):
        # Tiny integration games; not evidence of playing strength.
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "checkpoint"
            args = [sys.executable, "scripts/compare_mcts_v6.py", "--maps", "maps/demo.xml", "--rounds", "1",
                    "--max-games", "1", "--workers", "2", "--iterations", "4", "--move-time", "0",
                    "--max-plies", "2", "--checkpoint", str(directory)]
            first = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = directory / "games/game-0001.json"
            before = saved.read_bytes()
            game = json.loads(before)["result"]
            for stats in (game["a_stats"], game["b_stats"]):
                self.assertEqual(stats["search"]["iterations"], 4)
                self.assertEqual(stats["faults"], [])
                self.assertEqual(stats["timeouts"], 0)
            second = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Saved 2/4", second.stdout)
            self.assertEqual(saved.read_bytes(), before)
            report = json.loads((directory / "report.json").read_text())
            self.assertEqual(report["completed_games"], 2)
            incompatible = subprocess.run([*args, "--agent", "mcts-v6:endgame=False"], cwd=ROOT,
                                           capture_output=True, text=True, timeout=15)
            self.assertNotEqual(incompatible.returncode, 0)
            self.assertIn("Use a new --checkpoint folder", incompatible.stderr)
            self.assertEqual(saved.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
