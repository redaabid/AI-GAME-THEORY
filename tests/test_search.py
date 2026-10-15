"""Tactical, chance, deadline, evaluation, and search-label regression checks."""

from dataclasses import replace
import json
from pathlib import Path
import random
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from candidates import generate_candidates, supported_turn
from evaluate import evaluate_maps
from game import Cell
from search import SearchConfig, evaluate, search
from simulate import ROOT, export_games, play_game
from simulator import Position, get_outcome, load_map, simulate_turn


def board(records, *, rows=5, columns=7, **kwargs):
    return Position(rows, columns, {(x, y): Cell(h, v, w) for x, y, h, v, w in records}, **kwargs)


class CandidateTests(unittest.TestCase):
    def test_joint_attack_combines_before_fighting(self):
        initial = board([(0, 0, 0, 3, 0), (0, 2, 0, 3, 0), (1, 1, 0, 0, 4)])
        joint = [(0, 0, 3, 1, 1), (0, 2, 3, 1, 1)]
        self.assertIn(joint, generate_candidates(initial))
        final = simulate_turn(initial, joint, random.Random(0))
        self.assertEqual(get_outcome(final).winner, "vampires")

    def test_split_recruits_two_human_groups_in_one_turn(self):
        initial = board([(0, 1, 0, 7, 0), (1, 0, 3, 0, 0),
                         (1, 2, 4, 0, 0), (4, 1, 0, 0, 5)], rows=3, columns=5)
        split = [(0, 1, 3, 1, 0), (0, 1, 4, 1, 2)]
        self.assertIn(split, generate_candidates(initial))
        final = simulate_turn(initial, split, random.Random(0))
        self.assertEqual(final.cells[(1, 0)].vampires, 6)
        self.assertEqual(final.cells[(1, 2)].vampires, 8)

    def test_candidates_are_bounded_unique_and_skip_overflow(self):
        initial = board([(0, 0, 0, 200, 0), (0, 2, 0, 100, 0),
                         (1, 1, 200, 0, 0), (6, 4, 0, 0, 10)])
        actions = generate_candidates(initial, limit=12)
        self.assertLessEqual(len(actions), 12)
        keys = {tuple(action) for action in actions}
        self.assertEqual(len(keys), len(actions))
        for action in actions:
            self.assertTrue(supported_turn(initial.to_game_state(), action))
            simulate_turn(initial, action, random.Random(0))

    def test_all_development_maps_produce_legal_candidates_for_both_sides(self):
        for path in (ROOT / "maps").glob("*.xml"):
            initial = load_map(path)
            for species in ("vampires", "werewolves"):
                position = replace(initial, to_play=species)
                for action in generate_candidates(position):
                    with self.subTest(map=path.name, species=species, action=action):
                        position.to_game_state().validate_moves(action)
                        simulate_turn(position, action, random.Random(9))


class SearchTests(unittest.TestCase):
    def test_search_finds_guaranteed_joint_elimination(self):
        initial = board([(0, 0, 0, 3, 0), (0, 2, 0, 3, 0), (1, 1, 0, 0, 4)])
        result = search(initial, config=SearchConfig(iterations=100, rollout_depth=2), rng=random.Random(0))
        final = simulate_turn(initial, result.moves, random.Random(1))
        self.assertEqual(get_outcome(final).winner, "vampires")
        self.assertEqual(len(result.moves), 2)

    def test_search_avoids_recruitment_that_allows_a_forced_enemy_kill(self):
        initial = board([(0, 1, 0, 10, 0), (1, 1, 3, 0, 0), (2, 1, 0, 0, 20)],
                        rows=3, columns=3, rules_profile="brief")
        config = SearchConfig(iterations=256, tree_depth=3, rollout_depth=0)
        result = search(initial, config=config, rng=random.Random(7))
        self.assertNotIn((0, 1, 10, 1, 1), result.moves)
        # A partial recruitment can leave a reserve out of reach. Check the
        # actual tactical property: no generated enemy reply eliminates us.
        after = simulate_turn(initial, result.moves, random.Random(0))
        for reply in generate_candidates(after):
            outcome = get_outcome(simulate_turn(after, reply, random.Random(0)))
            self.assertTrue(outcome is None or outcome.winner != "werewolves")

    def test_chance_is_resampled_instead_of_freezing_one_lucky_result(self):
        # Only one legal action. Equal 1-v-1 has win/loss/draw probabilities
        # 1/4, 1/4, 1/2, including zero survivors. Expected reward is zero.
        initial = board([(0, 0, 0, 1, 0), (1, 0, 0, 0, 1)], rows=1, columns=2)
        result = search(initial, config=SearchConfig(iterations=1200, rollout_depth=0), rng=random.Random(2))
        self.assertEqual(result.visits, [1200])
        self.assertAlmostEqual(result.action_values[0], 0, delta=0.07)

    def test_seeded_fixed_budget_is_reproducible_and_preserves_input(self):
        initial = load_map(ROOT / "maps" / "demo.xml")
        before = initial.to_dict()
        config = SearchConfig(iterations=40)
        first = search(initial, config=config, rng=random.Random(18))
        second = search(initial, config=config, rng=random.Random(18))
        self.assertEqual(first.moves, second.moves)
        self.assertEqual(first.candidate_actions, second.candidate_actions)
        self.assertEqual(first.training_metadata(), second.training_metadata())
        self.assertEqual(sum(first.visits), first.iterations)
        self.assertAlmostEqual(sum(first.policy), 1)
        self.assertEqual(initial.to_dict(), before)

    def test_saved_json_and_reordered_cells_reproduce_the_same_search(self):
        initial = load_map(ROOT / "maps" / "recruitment.xml")
        reordered = replace(initial, cells=dict(reversed(list(initial.cells.items()))))
        restored = Position.from_dict(json.loads(json.dumps(initial.to_dict())))
        config = SearchConfig(iterations=64)
        results = [search(p, config=config, rng=random.Random(8)) for p in (initial, reordered, restored)]
        for result in results[1:]:
            self.assertEqual(result.training_metadata(), results[0].training_metadata())
            self.assertEqual(result.candidate_actions, results[0].candidate_actions)
            self.assertEqual(result.moves, results[0].moves)

    def test_expired_deadline_returns_a_legal_labeled_fallback(self):
        initial = load_map(ROOT / "maps" / "demo.xml")
        result = search(initial, deadline=time.perf_counter() - 1,
                        config=SearchConfig(iterations=10000), rng=random.Random(0))
        initial.to_game_state().validate_moves(result.moves)
        self.assertTrue(result.fallback)
        self.assertEqual(result.iterations, 0)
        self.assertEqual(result.policy, [1.0])

    def test_deadline_interrupts_search_with_a_large_iteration_cap(self):
        initial = load_map(ROOT / "maps" / "recruitment.xml")
        result = search(initial, config=SearchConfig(iterations=100000, time_limit=0.02), rng=random.Random(0))
        self.assertLess(result.iterations, 100000)
        self.assertLess(result.elapsed_seconds, 0.3)
        initial.to_game_state().validate_moves(result.moves)

    def test_incomplete_iteration_does_not_add_training_visits(self):
        initial = load_map(ROOT / "maps" / "demo.xml")
        with patch("search._rollout", side_effect=TimeoutError):
            result = search(initial, config=SearchConfig(iterations=8), rng=random.Random(0))
        self.assertEqual(sum(result.visits), 0)
        self.assertEqual(result.iterations, 0)
        self.assertTrue(result.fallback)
        self.assertEqual(sum(result.policy), 1)

    def test_evaluation_is_antisymmetric_and_respects_recruitment_races(self):
        initial = board([(0, 0, 0, 8, 0), (6, 4, 0, 0, 8), (1, 1, 4, 0, 0)])
        self.assertAlmostEqual(evaluate(initial, "vampires"), -evaluate(initial, "werewolves"))
        self.assertGreater(evaluate(initial, "vampires"), 0)

    def test_terminal_positions_and_invalid_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            search(board([(0, 0, 0, 3, 0)]))
        for kwargs in ({"iterations": 0}, {"time_limit": float("nan")},
                       {"max_candidates": 1}, {"rollout_depth": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SearchConfig(**kwargs)


class SearchExportTests(unittest.TestCase):
    def test_mcts_visits_align_with_candidates_and_real_games_replay(self):
        initial = load_map(ROOT / "maps" / "demo.xml")
        kwargs = dict(seed=37, max_plies=8, agent="mcts", opponent_agent="baseline",
                      search_config=SearchConfig(iterations=24))
        summary, records = play_game(initial, **kwargs)
        self.assertEqual((summary, records), play_game(initial, **kwargs))
        actual_rng, current = random.Random(37), initial
        for record in records:
            self.assertEqual(record["state"], current.to_dict())
            current = simulate_turn(current, record["action"], actual_rng)
            self.assertEqual(record["next_state"], current.to_dict())
            if record["teacher"] == "mcts":
                self.assertEqual(record["policy_target_kind"], "mcts_visits")
                visits = record["search"]["visits"]
                self.assertEqual(sum(visits), 24)
                self.assertEqual(len(visits), len(record["candidate_actions"]))
                self.assertEqual(record["policy_target"], [n / sum(visits) for n in visits])
                self.assertIn(record["action"], record["candidate_actions"])
            else:
                self.assertEqual(record["policy_target_kind"], "behavior_one_hot")
        self.assertEqual(current.to_dict(), summary["final_state"])

    def test_fallback_records_are_not_labeled_as_mcts_visits(self):
        _, records = play_game(load_map(ROOT / "maps" / "demo.xml"), seed=0, max_plies=1,
                               agent="mcts", search_config=SearchConfig(time_limit=1e-12))
        self.assertEqual(records[0]["policy_target_kind"], "fallback_one_hot")
        self.assertEqual(sum(records[0]["search"]["visits"]), 0)

    def test_export_manifest_identifies_search_and_configuration(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            manifest = export_games(ROOT / "maps" / "demo.xml", output, games=1, max_plies=2,
                                    agent="mcts", opponent_agent="baseline",
                                    search_config=SearchConfig(iterations=8))
            self.assertEqual(manifest["purpose"], "mcts_search_targets")
            self.assertEqual(manifest["search_config"]["iterations"], 8)
            self.assertEqual(manifest["candidate_set"], "per_transition")

    def test_evaluation_balances_roles_on_each_map(self):
        report = evaluate_maps([ROOT / "maps" / "endgame.xml"], games=4, max_plies=3,
                               search_config=SearchConfig(iterations=8))
        matches = report["maps"][0]["matches"]
        self.assertEqual(len({(m["agent_species"], m["first_player"]) for m in matches}), 4)
        self.assertEqual(report["macro_mean_score"], sum(m["agent_score"] for m in matches) / 4)
        with self.assertRaises(ValueError):
            evaluate_maps([ROOT / "maps" / "demo.xml"], games=3)

    def test_mcts_export_cli(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = subprocess.run([sys.executable, "simulate.py", "--agent", "mcts", "--opponent", "baseline",
                                     "--iterations", "8", "--games", "1", "--max-plies", "2",
                                     "--output", str(output)], cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("MCTS records contain root visit targets", result.stdout)
            self.assertEqual(json.loads((output / "manifest.json").read_text())["agent"], "mcts")


if __name__ == "__main__":
    unittest.main()
