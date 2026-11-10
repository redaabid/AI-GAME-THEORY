"""Isolated launcher provenance, worker registration, diagnostics and resume."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from game import Cell
from scripts.compare_mcts_v4 import checkpoint_label, comparison_plan, PROFILE_FILE, source_hashes
from simulator import Position
from tournament import ROLES

ROOT = Path(__file__).resolve().parents[1]
BOARD = Position(3, 7, {(0, 1): Cell(vampires=6), (6, 1): Cell(werewolves=6),
                         (3, 1): Cell(humans=4)})


class V4LauncherTests(unittest.TestCase):
    def test_default_comparison_has_32_balanced_games_and_pins_new_source(self):
        plan = comparison_plan(maps=[(f"map-{i}", BOARD) for i in range(4)])
        self.assertEqual(plan["agents"], ["mcts-v4:iterations=100000", "mcts-v1:iterations=100000"])
        self.assertEqual(len(plan["jobs"]), 32)
        self.assertEqual(plan["v4_source_sha256"], source_hashes())
        self.assertEqual(len(plan["v4_source_sha256"]), 5)
        for map_index in range(4):
            for round_index in range(2):
                jobs = [j for j in plan["jobs"] if j["map_name"] == f"map-{map_index}" and j["round"] == round_index]
                self.assertEqual({(j["a_species"], j["first"]) for j in jobs}, set(ROLES))
                self.assertTrue(all(j["settings"] == dict(max_plies=200, move_time=2.0, margin=0.5,
                                                         on_timeout="skip") for j in jobs))

    def test_retained_julian_spec_is_read_verbatim_and_fixed_control_is_available(self):
        retained = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        for label, profile in (("julian-width7", "ab2_width7"), ("julian-reference", "ab2_reference")):
            plan = comparison_plan("mcts-v4:adaptive=False,iterations=8", label, maps=[("fixture", BOARD)])
            self.assertEqual(plan["agents"][0], "mcts-v4:adaptive=False,iterations=8")
            self.assertEqual(plan["agents"][1], retained["profiles"][profile])
            self.assertEqual(plan["v4_opponent"]["status"], retained["validation_status"][profile])

    def test_exploration_only_keeps_the_same_jobs_and_budget_with_a_separate_checkpoint(self):
        maps = [(f"map-{i}", BOARD) for i in range(4)]
        normal = comparison_plan(maps=maps)
        exploration = comparison_plan(maps=maps, exploration_only=True)
        self.assertEqual(exploration["agents"], ["mcts-v4:tune_rollout=False,iterations=100000",
                                                 "mcts-v1:iterations=100000"])
        self.assertEqual(checkpoint_label(exploration["agents"][0]), "mcts-v4-exploration")
        self.assertNotEqual(checkpoint_label(normal["agents"][0]), checkpoint_label(exploration["agents"][0]))
        self.assertEqual(checkpoint_label("mcts-v4:adaptive=False,tune_rollout=False"), "mcts-v4-fixed")
        self.assertEqual(len(exploration["jobs"]), 32)
        for original, modified in zip(normal["jobs"], exploration["jobs"]):
            self.assertEqual({k: v for k, v in original.items() if k != "a"},
                             {k: v for k, v in modified.items() if k != "a"})
        explicit = comparison_plan("mcts-v4:tune_rollout=False,iterations=8", maps=maps, exploration_only=True)
        self.assertEqual(explicit["agents"][0], "mcts-v4:tune_rollout=False,iterations=8")

    def test_conflicting_exploration_only_options_are_rejected(self):
        for spec in ("mcts-v4:adaptive=False", "mcts-v4:tune_rollout=True"):
            with self.assertRaises(ValueError):
                comparison_plan(spec, maps=[("fixture", BOARD)], exploration_only=True)

    def test_cli_dry_run_writes_nothing(self):
        with TemporaryDirectory() as temporary:
            for mode in ([], ["--exploration-only"]):
                directory = Path(temporary) / "checkpoint"
                result = subprocess.run([sys.executable, "scripts/compare_mcts_v4.py", "--dry-run", "--maps", "maps",
                                         "--checkpoint", str(directory), *mode],
                                        cwd=ROOT, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("32 games | 4 maps | 2 rounds", result.stdout)
                self.assertIn("No games started", result.stdout)
                if mode:
                    self.assertIn("Tuning: exploration only | base rollout limit: 6 plies", result.stdout)
                self.assertFalse(directory.exists())

    def test_tiny_spawn_fixture_saves_diagnostics_and_resumes_without_rerunning(self):
        # A functional fixture, not a timed comparison or strength measurement.
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "checkpoint"
            args = [sys.executable, "scripts/compare_mcts_v4.py", "--maps", "maps/demo.xml", "--rounds", "1",
                    "--max-games", "1", "--workers", "2", "--iterations", "4", "--move-time", "0",
                    "--max-plies", "2", "--checkpoint", str(directory)]
            first = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = directory / "games/game-0001.json"
            before = saved.read_bytes()
            game = json.loads(before)["result"]
            self.assertTrue(game["v4_decisions"])
            self.assertEqual(game["v4_decisions"][0]["samples"], 4)
            self.assertEqual(game["a_stats"]["faults"], [])
            self.assertEqual(game["b_stats"]["faults"], [])
            self.assertTrue((directory / "tuning.md").exists())
            second = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Saved 2/4", second.stdout)
            self.assertEqual(saved.read_bytes(), before)
            report = json.loads((directory / "report.json").read_text())
            self.assertEqual(report["completed_games"], 2)
            incompatible = subprocess.run([*args, "--exploration-only"], cwd=ROOT,
                                           capture_output=True, text=True, timeout=15)
            self.assertNotEqual(incompatible.returncode, 0)
            self.assertIn("Use a new --checkpoint folder", incompatible.stderr)
            self.assertEqual(saved.read_bytes(), before)

    def test_exploration_only_survives_worker_spawn_and_checkpoint_resume(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "exploration"
            args = [sys.executable, "scripts/compare_mcts_v4.py", "--exploration-only", "--maps", "maps/demo.xml",
                    "--rounds", "1", "--max-games", "1", "--workers", "2", "--iterations", "4",
                    "--move-time", "0", "--max-plies", "2", "--checkpoint", str(directory)]
            first = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = directory / "games/game-0001.json"
            before = saved.read_bytes()
            game = json.loads(before)["result"]
            tuning = game["v4_decisions"][0]
            self.assertEqual(tuning["tuned_parameters"], ["exploration"])
            self.assertFalse(tuning["tune_rollout"])
            self.assertEqual({a["rollout_depth"] for a in tuning["arms"]}, {6})
            self.assertEqual(game["a_stats"]["faults"], [])
            self.assertEqual(game["b_stats"]["faults"], [])
            self.assertIn("tune_rollout=False", (directory / "tuning.md").read_text())
            second = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Saved 2/4", second.stdout)
            self.assertEqual(saved.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
