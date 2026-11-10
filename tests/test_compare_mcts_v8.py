"""V8 plan provenance, Windows workers, saved-game resume and diagnostic traces."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

from game import Cell
from scripts.compare_mcts_v8 import (PROFILE_FILE, checkpoint_directory, comparison_plan, source_hashes)
from simulator import Position
from tournament import ROLES

ROOT = Path(__file__).resolve().parents[1]
BOARD = Position(3, 7, {(0, 1): Cell(vampires=6), (6, 1): Cell(werewolves=6),
                         (3, 1): Cell(humans=4)})


class V8LauncherTests(unittest.TestCase):
    def test_default_plan_has_32_balanced_games_six_workers_and_all_dependencies(self):
        maps = [(f"map-{i}", BOARD) for i in range(4)]
        plan = comparison_plan(maps=maps)
        self.assertEqual(plan["agents"], ["mcts-v8:iterations=100000", "mcts-v6:iterations=100000"])
        self.assertEqual(plan["workers"], 6)
        self.assertEqual(len(plan["jobs"]), 32)
        expected = {"scripts/compare_mcts_v8.py"} | {
            f"scripts/mcts_v{v}/{f}.py" for v in (5, 6) for f in ("__init__", "agent", "value")} | {
            f"scripts/mcts_v8/{f}.py" for f in ("__init__", "agent", "interception")}
        self.assertEqual(set(source_hashes()), expected)
        self.assertEqual(plan["v8_source_sha256"], source_hashes())
        for name, _ in maps:
            for round_index in range(2):
                jobs = [j for j in plan["jobs"] if j["map_name"] == name and j["round"] == round_index]
                self.assertEqual({(j["a_species"], j["first"]) for j in jobs}, set(ROLES))
                self.assertTrue(all(j["settings"] == dict(max_plies=200, move_time=2.0,
                                                         margin=.5, on_timeout="skip") for j in jobs))

    def test_opponents_and_ablation_have_separate_folders_and_exact_profiles(self):
        retained = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        for label, profile in (("width7", "ab2_width7"), ("reference", "ab2_reference")):
            plan = comparison_plan(opponent=label, maps=[("fixture", BOARD)])
            self.assertEqual(plan["agents"][1], retained["profiles"][profile])
            self.assertEqual(plan["v8_opponent"]["published_status"], retained["validation_status"][profile])
        self.assertEqual(checkpoint_directory("mcts-v8", "v6").name, "mcts-v8-vs-v6")
        self.assertEqual(checkpoint_directory("mcts-v8:interceptions=False", "v6").name, "mcts-v8-control-vs-v6")
        for opponent in ("v1", "v5", "v6"):
            plan = comparison_plan(opponent=opponent, maps=[("fixture", BOARD)], iterations=32)
            self.assertEqual(plan["agents"][1], f"mcts-{opponent}:iterations=32")

    def test_bad_specs_and_preview_do_not_start_games(self):
        for kwargs in ({"agent": "mcts-v6"}, {"agent": "mcts-v8:interceptions=1"},
                       {"agent": "mcts-v8:intercept_depth=17"}, {"iterations": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                comparison_plan(maps=[("fixture", BOARD)], **kwargs)
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "campaign"
            result = subprocess.run([sys.executable, "scripts/compare_mcts_v8.py", "--dry-run", "--maps", "maps",
                                     "--checkpoint", str(directory)], cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("32 games | 4 maps | 2 rounds | 6 workers", result.stdout)
            self.assertFalse(directory.exists())

    def test_spawn_workers_resume_without_mixing_settings(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "campaign"
            args = [sys.executable, "scripts/compare_mcts_v8.py", "--maps", "maps/demo.xml", "--rounds", "1",
                    "--max-games", "1", "--workers", "2", "--iterations", "4", "--move-time", "0",
                    "--max-plies", "2", "--checkpoint", str(directory)]
            first = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = directory / "games/game-0001.json"
            original = saved.read_bytes()
            game = json.loads(original)["result"]
            for side in ("a", "b"):
                self.assertEqual(game[side + "_stats"]["search"]["iterations"], 4)
                self.assertEqual(game[side + "_stats"]["faults"], [])
                self.assertEqual(game[side + "_stats"]["timeouts"], 0)
            second = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Saved 2/4", second.stdout)
            self.assertEqual(saved.read_bytes(), original)
            changed = subprocess.run([*args, "--agent", "mcts-v8:interceptions=False"], cwd=ROOT,
                                      capture_output=True, text=True, timeout=15)
            self.assertNotEqual(changed.returncode, 0)
            self.assertIn("Use a new --checkpoint folder", changed.stderr)
            self.assertEqual(saved.read_bytes(), original)

    def test_trace_cli_records_replayable_boards_root_visits_and_goal_decisions(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "trace"
            args = [sys.executable, "scripts/trace_mcts_v8.py", "--map", "maps/demo.xml", "--opponent", "v6",
                    "--iterations", "4", "--move-time", "0", "--max-plies", "4", "--output", str(directory)]
            preview = subprocess.run([*args, "--dry-run"], cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse(directory.exists())
            result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((directory / "summary.json").read_text())
            self.assertEqual(summary["recorded_plies"], 4)
            self.assertEqual(summary["status"], "terminal")
            self.assertEqual(summary["faults"], [])
            self.assertEqual(summary["timeouts"], 0)
            rows = [json.loads(s) for s in (directory / "game.jsonl").read_text().splitlines()]
            for row in rows:
                root = row["mcts_root"]
                self.assertEqual(sum(root["visits"]), 4)
                if row["agent"].startswith("mcts-v8"):
                    self.assertIn("interception", row["agent_info"])
            with zipfile.ZipFile(directory / "source.zip") as archive:
                self.assertIn("scripts/mcts_v8/agent.py", archive.namelist())
                self.assertIn("scripts/trace_mcts_v8.py", archive.namelist())


if __name__ == "__main__":
    unittest.main()


