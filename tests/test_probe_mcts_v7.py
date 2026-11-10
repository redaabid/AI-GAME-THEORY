"""Controlled snapshot history, treatment activation, deterministic pairs and resume."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

from scripts.probe_mcts_v7 import (SNAPSHOT, continue_game, experiment_plan, read_results,
                                   validate_snapshot, verify_rows, write_report)

ROOT = Path(__file__).resolve().parents[1]


def snapshot():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def tiny_plan(**kwargs):
    return experiment_plan(snapshot(), pairs=1, iterations=8, workers=1, stop_after_plies=2, **kwargs)


class ControlledV7Tests(unittest.TestCase):
    def test_snapshot_preserves_and_replays_both_real_histories(self):
        data = snapshot()
        position, history = validate_snapshot(data)
        self.assertEqual(position.ply, 58)
        self.assertEqual(data["max_plies"], 200)
        self.assertEqual({k: len(v) for k, v in history.items()}, {"vampires": 29, "werewolves": 29})
        for side in history:
            self.assertTrue(all(p.to_play == side and p.ply < 58 for p, _ in history[side]))
        bad = deepcopy(data)
        bad["history"]["vampires"][-1]["state"]["ply"] = 58
        with self.assertRaises(ValueError):
            validate_snapshot(bad)
        bad = deepcopy(data)
        bad["origin"]["historical_battle_seed"] = 7
        # All previous battles here were guaranteed, so changing the historical
        # RNG seed is immaterial; changing a recorded move must still fail.
        bad["history"]["vampires"][0]["moves"][0][3:] = [0, 0]
        with self.assertRaises(ValueError):
            validate_snapshot(bad)

    def test_plan_pairs_seeds_and_changes_only_the_focal_goal_flag(self):
        plan = experiment_plan(snapshot())
        self.assertEqual(plan["iterations"], 256)
        self.assertEqual(plan["workers"], 6)
        self.assertEqual(plan["stop_after_plies"], 142)
        self.assertEqual(len(plan["jobs"]), 8)
        self.assertEqual(plan["specs"]["on"], "mcts-v7:goals=True,iterations=256")
        self.assertEqual(plan["specs"]["off"], "mcts-v7:goals=False,iterations=256")
        self.assertEqual(plan["specs"]["opponent"], "mcts-v6:iterations=256")
        for i in range(4):
            jobs = [j for j in plan["jobs"] if j["pair"] == i]
            self.assertEqual({j["arm"] for j in jobs}, {"on", "off"})
            self.assertEqual(len({j["seed"] for j in jobs}), 1)
        for kwargs in ({"pairs": 0}, {"iterations": True}, {"workers": 0},
                       {"seed": -1}, {"stop_after_plies": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                experiment_plan(snapshot(), **kwargs)

    def test_initial_activation_and_fixed_iteration_budgets_are_observed_in_both_arms(self):
        plan = tiny_plan()
        for job in plan["jobs"]:
            result, rows = continue_game(plan, job)
            with self.subTest(arm=job["arm"]):
                self.assertEqual(result["status"], "truncated")
                self.assertIsNone(result["score"])
                self.assertEqual(rows[0]["before"], plan["snapshot"]["state"])
                self.assertEqual(bool(rows[0]["info"].get("objective")), job["arm"] == "on")
                self.assertTrue(all(r["root"]["iterations"] == 8 for r in rows))
                self.assertEqual(verify_rows(rows, plan, job).ply, 60)
                self.assertEqual(result["faults"], [])

    def test_fixed_iteration_moves_and_search_targets_reproduce_without_wall_time(self):
        plan = tiny_plan()
        job = plan["jobs"][0]
        a, rows_a = continue_game(plan, job)
        b, rows_b = continue_game(plan, job)
        for first, second in zip(rows_a, rows_b):
            for key in ("before", "after", "moves", "root", "contacts", "goal_before"):
                self.assertEqual(first[key], second[key])
            for key in ("objective", "goal_status", "goal_comparisons"):
                self.assertEqual(first["info"].get(key), second["info"].get(key))
        self.assertEqual(a["final_state"], b["final_state"])

    def test_absolute_cap_is_not_restarted_at_the_snapshot(self):
        data = snapshot()
        data["state"]["ply"] = 199
        data["origin"] = {"note": "synthetic cap boundary test"}
        plan = experiment_plan(data, pairs=1, iterations=4, workers=1)
        self.assertEqual(plan["stop_after_plies"], 1)
        result, rows = continue_game(plan, plan["jobs"][1])
        self.assertEqual(result["status"], "terminal")
        self.assertEqual(result["score"], .5)
        self.assertEqual(result["outcome"]["reason"], "ply_limit")
        self.assertEqual(len(rows), 1)
        self.assertEqual(result["final_state"]["ply"], 200)

    def test_tampered_transition_budget_and_activation_are_rejected(self):
        plan = tiny_plan()
        job = plan["jobs"][0]
        _, rows = continue_game(plan, job)
        for edit in ("state", "budget", "activation"):
            bad = deepcopy(rows)
            if edit == "state":
                bad[0]["after"]["ply"] += 1
            elif edit == "budget":
                bad[0]["root"]["iterations"] = 9
            else:
                bad[0]["info"]["objective"] = None
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                verify_rows(bad, plan, job)

    def test_cli_dry_run_spawn_resume_and_incompatible_settings(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "experiment"
            args = [sys.executable, "scripts/probe_mcts_v7.py", "--pairs", "1", "--iterations", "8",
                    "--workers", "2", "--stop-after-plies", "2", "--max-continuations", "1",
                    "--output", str(directory)]
            preview = subprocess.run([*args, "--dry-run"], cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertFalse(directory.exists())
            first = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = directory / "pair-0001-on/result.json"
            before = saved.read_bytes()
            second = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(saved.read_bytes(), before)
            manifest = json.loads((directory / "manifest.json").read_text())
            results = read_results(directory, manifest["plan"])
            self.assertEqual(len(results), 2)
            report = json.loads((directory / "analysis.json").read_text())
            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["arms"]["on"]["terminal"], 0)
            self.assertEqual(report["arms"]["on"]["draws"], 0)
            self.assertIsNone(report["arms"]["on"]["mean_score"])
            self.assertIsNone(report["pairs"][0]["score_delta"])
            changed = subprocess.run([*args, "--iterations", "9"], cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(changed.returncode, 0)
            self.assertIn("new --output", changed.stderr)
            self.assertEqual(saved.read_bytes(), before)
            with zipfile.ZipFile(directory / "source.zip") as archive:
                self.assertIn("scripts/probe_mcts_v7.py", archive.namelist())
                self.assertIn("snapshot.json", archive.namelist())
            summary = json.loads(before)
            trace = directory / summary["trace_file"]
            trace.write_text(trace.read_text() + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_results(directory, manifest["plan"])


if __name__ == "__main__":
    unittest.main()
