"""Exercise save/resume, interrupted runs, corruption, and parallel completion."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import campaign
from game import Cell
from simulator import Position
from tournament import run_tournament

ROOT = Path(__file__).resolve().parents[1]
BOARD = Position(3, 5, {(0, 1): Cell(vampires=6), (4, 1): Cell(werewolves=6),
                         (2, 1): Cell(humans=4)})


def without_times(results):
    clean = deepcopy(results)
    for result in clean:
        for key in ("a_stats", "b_stats"):
            result[key].pop("seconds", None)
    return sorted(clean, key=campaign.result_key)


class CampaignTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name) / "checkpoint"
        self.plan = campaign.make_plan(["baseline", "random"], [("duel", BOARD)], seed=77,
                                       workers=1, max_plies=4, move_time=0, margin=0)

    def test_resume_skips_saved_games_and_matches_uninterrupted_results(self):
        expected = run_tournament(["baseline", "random"], [("duel", BOARD)], seed=77,
                                  max_plies=4, move_time=0, margin=0)
        with patch("campaign._run_job", wraps=campaign._run_job) as runner:
            first, interrupted = campaign.run_campaign(self.plan, self.folder, max_games=1)
            self.assertFalse(interrupted)
            self.assertEqual(first["completed_games"], 1)
            self.assertEqual(first["status"], "partial")
            saved_file = self.folder / "games/game-0001.json"
            saved_bytes = saved_file.read_bytes()
            second, _ = campaign.run_campaign(self.plan, self.folder, max_games=1)
            self.assertEqual(second["completed_games"], 2)  # N additional games.
            final, _ = campaign.run_campaign(self.plan, self.folder)
            self.assertEqual(runner.call_count, 4)
        self.assertEqual(saved_file.read_bytes(), saved_bytes)
        self.assertEqual(final["status"], "complete")
        self.assertEqual(without_times(final["games"]), without_times(expected))
        with patch("campaign._run_job", side_effect=AssertionError("Must not replay")):
            repeated, _ = campaign.run_campaign(self.plan, self.folder)
        self.assertEqual(repeated["games"], final["games"])
        self.assertEqual(len(list((self.folder / "games").glob("game-*.json"))), 4)

    def test_ctrl_c_preserves_finished_game_and_restarts_missing_games(self):
        real = campaign._run_job
        calls = 0

        def interrupt(job):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt
            return real(job)

        with patch("campaign._run_job", side_effect=interrupt):
            partial, interrupted = campaign.run_campaign(self.plan, self.folder)
        self.assertTrue(interrupted)
        self.assertEqual(partial["completed_games"], 1)
        with patch("campaign._run_job", wraps=real) as runner:
            final, interrupted = campaign.run_campaign(self.plan, self.folder)
        self.assertEqual(runner.call_count, 3)
        self.assertFalse(interrupted)
        self.assertEqual(final["completed_games"], 4)

    def test_unexpected_failure_also_keeps_previously_saved_game(self):
        first_job = campaign._run_job(self.plan["jobs"][0])
        with patch("campaign._run_job", side_effect=[first_job, RuntimeError("worker failed")]):
            with self.assertRaisesRegex(RuntimeError, "worker failed"):
                campaign.run_campaign(self.plan, self.folder)
        self.assertEqual(len(campaign.read_games(self.folder, self.plan)), 1)
        self.assertEqual(json.loads((self.folder / "report.json").read_text())["status"], "partial")

    def test_interrupt_after_game_file_commit_recovers_it_before_reporting(self):
        real = campaign.atomic_json

        def commit_then_interrupt(path, data):
            real(path, data)
            if Path(path).name == "game-0001.json":
                raise KeyboardInterrupt

        with patch("campaign.atomic_json", side_effect=commit_then_interrupt):
            report, interrupted = campaign.run_campaign(self.plan, self.folder)
        self.assertTrue(interrupted)
        self.assertEqual(report["completed_games"], 1)
        self.assertEqual(len(campaign.read_games(self.folder, self.plan)), 1)

    def test_code_settings_and_map_changes_are_rejected_without_overwriting(self):
        campaign.run_campaign(self.plan, self.folder, max_games=1)
        manifest = (self.folder / "manifest.json").read_bytes()
        for change in ("source", "settings", "map"):
            modified = deepcopy(self.plan)
            if change == "source":
                modified["source_sha256"]["agents/mcts_memory.py"] = "changed"
            elif change == "settings":
                modified["jobs"][0]["settings"]["max_plies"] += 2
            else:
                modified["jobs"][0]["map"]["columns"] += 1
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "changed"):
                campaign.run_campaign(modified, self.folder)
        self.assertEqual((self.folder / "manifest.json").read_bytes(), manifest)
        self.assertEqual(len(campaign.read_games(self.folder, self.plan)), 1)

    def test_corrupt_game_is_detected_instead_of_counted_or_overwritten(self):
        campaign.run_campaign(self.plan, self.folder, max_games=1)
        path = self.folder / "games/game-0001.json"
        record = json.loads(path.read_text())
        record["result"]["a_score"] = 123
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not match"):
            campaign.run_campaign(self.plan, self.folder)
        self.assertEqual(json.loads(path.read_text())["result"]["a_score"], 123)

    def test_missing_manifest_does_not_overwrite_or_adopt_existing_games(self):
        games = self.folder / "games"
        games.mkdir(parents=True)
        orphan = games / "game-0001.json"
        orphan.write_text("{}")
        with self.assertRaisesRegex(ValueError, "without their manifest"):
            campaign.run_campaign(self.plan, self.folder)
        self.assertFalse((self.folder / "manifest.json").exists())
        self.assertEqual(orphan.read_text(), "{}")

    def test_failed_atomic_replace_preserves_old_checkpoint(self):
        path = self.folder / "saved.json"
        campaign.atomic_json(path, {"saved": 1})
        with patch("campaign.os.replace", side_effect=OSError("interrupted write")):
            with self.assertRaises(OSError):
                campaign.atomic_json(path, {"saved": 2})
        self.assertEqual(json.loads(path.read_text()), {"saved": 1})
        self.assertEqual(list(self.folder.glob("*.tmp")), [])

    def test_exclusive_lock_releases_for_a_later_session(self):
        with campaign.campaign_lock(self.folder):
            with self.assertRaisesRegex(ValueError, "already open"):
                with campaign.campaign_lock(self.folder):
                    self.fail("A second writer acquired the same checkpoint")
        with campaign.campaign_lock(self.folder):
            pass

    def test_parallel_partial_run_resumes_and_saves_each_game_once(self):
        plan = deepcopy(self.plan)
        plan["workers"] = 2
        first, _ = campaign.run_campaign(plan, self.folder, max_games=1)
        self.assertEqual(first["completed_games"], 1)
        final, _ = campaign.run_campaign(plan, self.folder)
        self.assertEqual(final["completed_games"], 4)
        self.assertEqual(len(campaign.read_games(self.folder, plan)), 4)
        self.assertTrue((self.folder / "report.md").exists())

    def test_manifest_covers_both_policies_and_checkpoint_runner(self):
        self.assertTrue({"campaign.py", "agents/ab_variants.py", "agents/mcts_memory.py"}
                        <= self.plan["source_sha256"].keys())
        self.assertEqual(len(self.plan["jobs"]), 4)
        self.assertEqual({(job["a_species"], job["first"]) for job in self.plan["jobs"]}, set(campaign.ROLES))

    def test_invalid_cli_limit_stops_before_scheduling_games(self):
        result = subprocess.run([sys.executable, "campaign.py", "--opponent", "ab2", "--max-games", "0"],
                                cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be positive", result.stderr)

    def test_two_round_plan_covers_all_roles_on_all_four_maps_with_distinct_seeds(self):
        maps = [(name, BOARD) for name in campaign.MAP_NAMES]
        plan = campaign.make_plan(["mcts-v2:iterations=8", "mcts-v1:iterations=8"], maps, rounds=2)
        self.assertEqual(len(plan["jobs"]), 32)
        self.assertEqual(len({job["seed"] for job in plan["jobs"]}), 32)
        for name, _ in maps:
            for round_index in range(2):
                self.assertEqual({(j["a_species"], j["first"]) for j in plan["jobs"]
                                  if j["map_name"] == name and j["round"] == round_index}, set(campaign.ROLES))
        self.assertIn("rollouts.py", plan["source_sha256"])
        self.assertIn("agents/mcts_v2.py", plan["source_sha256"])

    def test_v2_cli_dry_run_validates_32_games_and_does_not_create_checkpoints(self):
        result = subprocess.run([sys.executable, "campaign.py", "--opponent", "mcts-v1",
                                 "--maps", "maps", "--checkpoint", str(self.folder), "--dry-run"],
                                cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("32 games | 4 maps | 2 rounds", result.stdout)
        self.assertIn("mcts-v2:iterations=100000 vs mcts-v1:iterations=100000", result.stdout)
        self.assertIn("Thinking time: 1.5 s", result.stdout)
        self.assertFalse(self.folder.exists())

    def test_v3_dry_run_uses_a_separate_checkpoint_and_equal_iteration_caps(self):
        result = subprocess.run([sys.executable, "campaign.py", "--opponent", "mcts-v1",
                                 "--agent", "mcts-v3", "--maps", "maps", "--dry-run"],
                                cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("32 games | 4 maps | 2 rounds", result.stdout)
        self.assertIn("mcts-v3:iterations=100000 vs mcts-v1:iterations=100000", result.stdout)
        self.assertIn(str(ROOT / ".local/campaigns/mcts-v3-vs-v1"), result.stdout)
        self.assertIn("Thinking time: 1.5 s", result.stdout)
        self.assertIn("No games started", result.stdout)

    def test_v3_dry_run_respects_explicit_caps_and_checkpoint_directory(self):
        result = subprocess.run([sys.executable, "campaign.py", "--opponent", "mcts-v1",
                                 "--agent", "mcts-v3:iterations=8", "--iterations", "16",
                                 "--maps", "maps", "--checkpoint", str(self.folder), "--dry-run"],
                                cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mcts-v3:iterations=8 vs mcts-v1:iterations=16", result.stdout)
        self.assertIn(str(self.folder.resolve()), result.stdout)
        self.assertFalse(self.folder.exists())

    def test_invalid_timing_is_rejected_before_creating_a_checkpoint(self):
        for value in ("nan", "-1", "0.1"):
            result = subprocess.run([sys.executable, "campaign.py", "--opponent", "mcts-v1",
                                     "--maps", "maps", "--checkpoint", str(self.folder),
                                     "--move-time", value, "--dry-run"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.folder.exists())

    def test_report_includes_per_map_wins_draws_losses(self):
        game = campaign._run_job(self.plan["jobs"][0])
        report = campaign.save_report(self.folder, self.plan, {0: game})
        row = report["per_map"]["duel"]
        self.assertEqual(row["games"], 1)
        self.assertEqual(row["wins"] + row["draws"] + row["losses"], 1)
        self.assertEqual(row["mean_score"], game["a_score"])
        self.assertIn("| Map | Games | Wins | Draws | Losses | Score |",
                      (self.folder / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
