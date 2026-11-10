"""Balanced V5 plans, exact retained AB2 specs, Windows workers and checkpoints."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from game import Cell
from scripts.compare_mcts_v5 import (PROFILE_FILE, checkpoint_directory,
                                     comparison_plan, source_hashes)
from simulator import Position
from tournament import ROLES

ROOT = Path(__file__).resolve().parents[1]
BOARD = Position(3, 7, {(0, 1): Cell(vampires=6), (6, 1): Cell(werewolves=6),
                         (3, 1): Cell(humans=4)})


class V5LauncherTests(unittest.TestCase):
    def test_default_plan_has_32_balanced_games_and_pins_all_new_sources(self):
        maps = [(f"map-{i}", BOARD) for i in range(4)]
        plan = comparison_plan(maps=maps)
        self.assertEqual(plan["agents"][0], "mcts-v5:iterations=100000")
        self.assertEqual(len(plan["jobs"]), 32)
        self.assertEqual(plan["v5_source_sha256"], source_hashes())
        self.assertEqual(set(source_hashes()), {"scripts/compare_mcts_v5.py", "scripts/mcts_v5/__init__.py",
                                               "scripts/mcts_v5/agent.py", "scripts/mcts_v5/value.py"})
        for map_name, _ in maps:
            for round_index in range(2):
                jobs = [j for j in plan["jobs"] if j["map_name"] == map_name and j["round"] == round_index]
                self.assertEqual({(j["a_species"], j["first"]) for j in jobs}, set(ROLES))
                self.assertTrue(all(j["settings"] == dict(max_plies=200, move_time=2.0,
                                                         margin=0.5, on_timeout="skip") for j in jobs))
        self.assertEqual(len({j["seed"] for j in plan["jobs"]}), 32)

    def test_julian_profiles_are_used_verbatim_with_their_validation_status(self):
        retained = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        for label, profile in (("width7", "ab2_width7"), ("reference", "ab2_reference")):
            plan = comparison_plan(opponent=label, maps=[("fixture", BOARD)])
            self.assertEqual(plan["agents"][1], retained["profiles"][profile])
            self.assertEqual(plan["v5_opponent"]["published_status"], retained["validation_status"][profile])
            self.assertEqual(len(plan["v5_opponent"]["retained_profiles_sha256"]), 64)

    def test_v1_and_disabled_feature_controls_use_separate_default_folders(self):
        plan = comparison_plan(opponent="v1", maps=[("fixture", BOARD)], iterations=64)
        self.assertEqual(plan["agents"], ["mcts-v5:iterations=64", "mcts-v1:iterations=64"])
        self.assertFalse(plan["v5_opponent"])
        control = comparison_plan("mcts-v5:feasibility=False,iterations=8", maps=[("fixture", BOARD)])
        self.assertEqual(control["agents"][0], "mcts-v5:feasibility=False,iterations=8")
        self.assertEqual(checkpoint_directory("mcts-v5", "width7").name, "mcts-v5-vs-julian-ab2-width7")
        self.assertEqual(checkpoint_directory("mcts-v5", "v1").name, "mcts-v5-vs-v1")
        self.assertNotEqual(checkpoint_directory("mcts-v5", "width7"),
                            checkpoint_directory(control["agents"][0], "width7"))

    def test_invalid_experiments_fail_before_creating_a_campaign(self):
        for kwargs in ({"agent": "mcts-v1"}, {"agent": "mcts-v5:feasibility=1"},
                       {"iterations": 0}, {"rounds": 0}, {"workers": 0},
                       {"move_time": 0.5, "margin": 0.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                comparison_plan(maps=[("fixture", BOARD)], **kwargs)

    def test_cli_preview_validates_four_maps_and_writes_nothing(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "checkpoint"
            result = subprocess.run([sys.executable, "scripts/compare_mcts_v5.py", "--dry-run", "--maps", "maps",
                                     "--checkpoint", str(directory)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("32 games | 4 maps | 2 rounds", result.stdout)
            self.assertIn("ab2exp:depth=1,max_depth=24,width=7,extra=0,tt_size=50000", result.stdout)
            self.assertIn("No games started", result.stdout)
            self.assertFalse(directory.exists())

    def test_spawn_workers_resume_without_rerunning_or_mixing_the_control(self):
        # Tiny functional fixtures; they do not measure match strength.
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "checkpoint"
            args = [sys.executable, "scripts/compare_mcts_v5.py", "--maps", "maps/demo.xml", "--rounds", "1",
                    "--max-games", "1", "--workers", "2", "--iterations", "4", "--move-time", "0",
                    "--max-plies", "2", "--checkpoint", str(directory)]
            first = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = directory / "games/game-0001.json"
            before = saved.read_bytes()
            game = json.loads(before)["result"]
            self.assertEqual(game["a_stats"]["search"]["iterations"], 4)
            for stats in (game["a_stats"], game["b_stats"]):
                self.assertEqual(stats["faults"], [])
                self.assertEqual(stats["timeouts"], 0)
            second = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Saved 2/4", second.stdout)
            self.assertEqual(saved.read_bytes(), before)
            report = json.loads((directory / "report.json").read_text())
            self.assertEqual(report["completed_games"], 2)
            incompatible = subprocess.run([*args, "--agent", "mcts-v5:feasibility=False"], cwd=ROOT,
                                           capture_output=True, text=True, timeout=15)
            self.assertNotEqual(incompatible.returncode, 0)
            self.assertIn("Use a new --checkpoint folder", incompatible.stderr)
            self.assertEqual(saved.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
