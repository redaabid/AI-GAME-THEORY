"""Rule, branch-isolation, stochastic, and portable data-contract checks."""

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import random
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from combat import sample_battle, win_probability
from game import Cell
from game import GameState
from simulate import ROOT, export_games, play_game
from simulator import Outcome, Position, full_group_actions, get_outcome, load_map, simulate_turn


class FixedRandom:
    def __init__(self, values=()):
        self.values = iter(values)

    def random(self):
        return next(self.values)


def position(records, **kwargs):
    return Position(5, 7, {(x, y): Cell(h, v, w) for x, y, h, v, w in records}, **kwargs)


class CombatTests(unittest.TestCase):
    def test_deterministic_battles_do_not_consume_randomness(self):
        self.assertEqual(sample_battle(6, 6, FixedRandom(), humans=True).survivors, 12)
        self.assertEqual(sample_battle(15, 10, FixedRandom()).survivors, 15)
        loss = sample_battle(10, 15, FixedRandom(), rules_profile="brief")
        self.assertFalse(loss.attacker_won)
        self.assertEqual(loss.survivors, 15)

    def test_human_win_samples_survivors_from_both_populations(self):
        result = sample_battle(4, 8, FixedRandom([0.1] + [0.1] * 3 + [0.9] * 9), humans=True)
        self.assertTrue(result.attacker_won)
        self.assertEqual(result.survivors, 3)
        self.assertEqual(result.probability, 0.25)

    def test_defenders_survive_with_one_minus_win_probability(self):
        result = sample_battle(4, 8, FixedRandom([0.9] + [0.1] * 2 + [0.9] * 6), humans=True)
        self.assertFalse(result.attacker_won)
        self.assertEqual(result.survivors, 2)

    def test_stronger_defender_differs_between_brief_and_supplied_server(self):
        self.assertEqual(win_probability(10, 15, rules_profile="brief"), 0)
        self.assertAlmostEqual(win_probability(10, 15, rules_profile="server-v3.2.1"), 1 / 3)
        result = sample_battle(10, 15, FixedRandom([0.1] * 11), rules_profile="server-v3.2.1")
        self.assertTrue(result.attacker_won)
        self.assertEqual(result.survivors, 10)

    def test_zero_survivors_is_possible(self):
        result = sample_battle(1, 1, FixedRandom([0.1, 0.9]))
        self.assertTrue(result.attacker_won)
        self.assertEqual(result.survivors, 0)

    def test_invalid_battle_inputs(self):
        for attackers, defenders in ((0, 3), (3, -1), (1.5, 3), (True, 2)):
            with self.subTest(attackers=attackers), self.assertRaises(ValueError):
                sample_battle(attackers, defenders, random.Random(0))
        for value in (float("nan"), float("inf"), 0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                win_probability(value, 3)
        with self.assertRaises(ValueError):
            win_probability(3, 3, rules_profile="unknown")

    def test_seeded_survivor_statistics_match_the_rules(self):
        # Independent analytic expectations include the battle-winning draw:
        # E[attackers alive] = P * (A [+ H]) * P, not just N * P.
        cases = ((12, 10, False, 0.7, "brief"), (4, 8, True, 0.25, "brief"),
                 (1, 1, False, 0.5, "brief"), (10, 15, False, 1 / 3, "server-v3.2.1"))
        for attackers, defenders, humans, probability, profile in cases:
            rng = random.Random(2026)
            attacker_total = defender_total = attacker_present = 0
            samples = 20000
            for _ in range(samples):
                battle = sample_battle(attackers, defenders, rng, humans=humans, rules_profile=profile)
                if battle.attacker_won:
                    attacker_total += battle.survivors
                    attacker_present += battle.survivors > 0
                else:
                    defender_total += battle.survivors
            population = attackers + (defenders if humans else 0)
            with self.subTest(attackers=attackers, humans=humans):
                self.assertAlmostEqual(attacker_total / samples, population * probability ** 2, delta=0.15)
                self.assertAlmostEqual(defender_total / samples, defenders * (1-probability) ** 2, delta=0.15)
                self.assertAlmostEqual(attacker_present / samples,
                                       probability * (1-(1-probability) ** population), delta=0.02)


class PositionTests(unittest.TestCase):
    def test_rule_profile_survives_network_reset_and_simulator_adapter(self):
        state = GameState(rules_profile="brief")
        state.apply_message("set", (5, 7))
        state.species = "vampires"
        state.cells = {(0, 0): Cell(vampires=3), (6, 4): Cell(werewolves=2)}
        self.assertEqual(state.rules_profile, "brief")
        self.assertEqual(Position.from_game_state(state).rules_profile, "brief")
        state.apply_message("set", (3, 4))
        self.assertEqual(state.rules_profile, "brief")
        self.assertEqual(state.cells, {})

    def test_snapshot_is_immutable_and_isolated_from_adapters(self):
        original = {(0, 0): Cell(vampires=5), (6, 4): Cell(werewolves=2)}
        snapshot = Position(5, 7, original)
        original.clear()
        self.assertEqual(len(snapshot.cells), 2)
        with self.assertRaises(TypeError):
            snapshot.cells[(0, 0)] = Cell()
        with self.assertRaises(FrozenInstanceError):
            snapshot.cells[(0, 0)].vampires = 1
        view = snapshot.to_game_state()
        self.assertEqual(view.rules_profile, snapshot.rules_profile)
        view.cells.clear()
        self.assertEqual(len(snapshot.cells), 2)
        self.assertEqual(Position.from_game_state(snapshot.to_game_state()), snapshot)

    def test_json_round_trip_and_schema_validation(self):
        snapshot = position([(0, 0, 0, 5, 0), (6, 4, 0, 0, 2)], ply=3, rules_profile="brief")
        data = json.loads(json.dumps(snapshot.to_dict()))
        self.assertEqual(Position.from_dict(data), snapshot)
        data["schema_version"] = 99
        with self.assertRaises(ValueError):
            Position.from_dict(data)
        data["schema_version"] = 1
        data["cells"].append(data["cells"][0])
        with self.assertRaises(ValueError):
            Position.from_dict(data)

    def test_invalid_positions(self):
        invalid = [dict(rows=0, columns=2, cells={}), dict(rows=2, columns=2, cells={(2, 0): Cell()}),
                   dict(rows=2, columns=2, cells={}, to_play="humans"),
                   dict(rows=2, columns=2, cells={}, ply=-1),
                   dict(rows=2, columns=2, cells={}, rules_profile="unknown")]
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                Position(**arguments)

    def test_xml_loader_and_invalid_map(self):
        snapshot = load_map(ROOT / "maps" / "demo.xml")
        self.assertEqual((snapshot.rows, snapshot.columns), (5, 7))
        self.assertEqual(snapshot.cells[(0, 0)], Cell(vampires=8))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.xml"
            path.write_text('<Map Rows="2" Columns="2"><Humans X="2" Y="0" Count="3"/></Map>')
            with self.assertRaises(ValueError):
                load_map(path)
            path.write_text('<Map Rows="2" Columns="2"><Vampires X="0" Y="0" Count="3"/>'
                            '<Humans X="0" Y="0" Count="3"/></Map>')
            with self.assertRaises(ValueError):
                load_map(path)


class TransitionTests(unittest.TestCase):
    def test_reference_turns_for_both_species(self):
        fixtures = json.loads((ROOT / "tests" / "fixtures" / "server_turns.json").read_text())
        for fixture in fixtures:
            for actor in ("vampires", "werewolves"):
                def swap(records):
                    return [[x, y, h, w, v] if actor == "werewolves" else [x, y, h, v, w]
                            for x, y, h, v, w in records]

                initial = position(swap(fixture["cells"]), to_play=actor)
                before = initial.to_dict()
                rng = random.Random(7)
                rng_state = rng.getstate()
                with self.subTest(case=fixture["name"], actor=actor):
                    if fixture.get("rejected"):
                        with self.assertRaises(ValueError):
                            simulate_turn(initial, fixture["moves"], rng)
                    else:
                        updated = simulate_turn(initial, fixture["moves"], rng)
                        self.assertEqual(updated.to_dict()["cells"], swap(fixture["expected"]))
                        self.assertNotEqual(updated.to_play, actor)
                        self.assertEqual(updated.ply, 1)
                        self.assertEqual(updated.rules_profile, initial.rules_profile)
                    self.assertEqual(initial.to_dict(), before)
                    self.assertEqual(rng.getstate(), rng_state)

    def test_combined_attack_crosses_enemy_victory_threshold(self):
        initial = position([(0, 0, 0, 3, 0), (0, 2, 0, 3, 0), (1, 1, 0, 0, 4)])
        updated = simulate_turn(initial, [(0, 0, 3, 1, 1), (0, 2, 3, 1, 1)], FixedRandom())
        self.assertEqual(updated.cells[(1, 1)], Cell(vampires=6))
        self.assertEqual(get_outcome(updated).winner, "vampires")

    def test_human_defenders_and_empty_battle_cells(self):
        initial = position([(0, 0, 0, 4, 0), (1, 1, 8, 0, 0), (6, 4, 0, 0, 2)])
        updated = simulate_turn(initial, [(0, 0, 4, 1, 1)], FixedRandom([0.9] + [0.1] * 2 + [0.9] * 6))
        self.assertEqual(updated.cells[(1, 1)], Cell(humans=2))
        initial = position([(0, 0, 0, 1, 0), (1, 1, 0, 0, 1)])
        updated = simulate_turn(initial, [(0, 0, 1, 1, 1)], FixedRandom([0.1, 0.9]))
        self.assertEqual(dict(updated.cells), {})
        self.assertEqual(get_outcome(updated), Outcome(None, "elimination"))

    def test_move_order_does_not_change_seeded_outcomes(self):
        initial = position([(0, 0, 0, 4, 0), (3, 0, 0, 4, 0),
                            (1, 1, 8, 0, 0), (2, 1, 8, 0, 0), (6, 4, 0, 0, 2)])
        moves = [(0, 0, 4, 1, 1), (3, 0, 4, 2, 1)]
        first_rng, second_rng = random.Random(42), random.Random(42)
        self.assertEqual(simulate_turn(initial, moves, first_rng),
                         simulate_turn(initial, list(reversed(moves)), second_rng))
        self.assertEqual(first_rng.getstate(), second_rng.getstate())

    def test_byte_overflow_is_explicit_and_does_not_consume_rng(self):
        initial = position([(0, 0, 0, 100, 0), (1, 1, 200, 0, 0), (6, 4, 0, 0, 1)])
        rng = random.Random(1)
        before = rng.getstate()
        with self.assertRaisesRegex(ValueError, "255"):
            simulate_turn(initial, [(0, 0, 100, 1, 1)], rng)
        self.assertEqual(rng.getstate(), before)
        self.assertEqual(initial.cells[(0, 0)].vampires, 100)

    def test_termination_and_scoring(self):
        ongoing = position([(0, 0, 0, 5, 0), (6, 4, 0, 0, 2)])
        self.assertIsNone(get_outcome(ongoing, max_plies=3))
        result = get_outcome(replace(ongoing, ply=3), max_plies=3)
        self.assertEqual(result, Outcome("vampires", "ply_limit"))
        self.assertEqual((result.value_for("vampires"), result.value_for("werewolves")), (1, -1))
        tied = position([(0, 0, 0, 2, 0), (6, 4, 0, 0, 2)], ply=3)
        self.assertEqual(get_outcome(tied, max_plies=3), Outcome(None, "ply_limit"))
        finished = position([(0, 0, 0, 5, 0)])
        self.assertEqual(full_group_actions(finished), [])
        with self.assertRaises(ValueError):
            simulate_turn(finished, [(0, 0, 5, 1, 1)], random.Random(0))

    def test_candidate_moves_and_random_trajectory_invariants(self):
        initial = load_map(ROOT / "maps" / "demo.xml")
        total = sum(c.humans + c.vampires + c.werewolves for c in initial.cells.values())
        for seed in range(30):
            rng = random.Random(seed)
            current = initial
            previous_total = total
            for _ in range(30):
                if get_outcome(current) is not None:
                    break
                actions = full_group_actions(current)
                for moves in actions:
                    current.to_game_state().validate_moves(moves)
                current = simulate_turn(current, rng.choice(actions), rng)
                population = sum(c.humans + c.vampires + c.werewolves for c in current.cells.values())
                self.assertLessEqual(population, previous_total)
                self.assertGreaterEqual(population, 0)
                previous_total = population


class ExportTests(unittest.TestCase):
    def test_games_are_reproducible_and_replayable(self):
        initial = load_map(ROOT / "maps" / "demo.xml")
        summary, records = play_game(initial, seed=19, max_plies=40)
        self.assertEqual((summary, records), play_game(initial, seed=19, max_plies=40))
        rng = random.Random(19)
        state = initial
        for record in records:
            self.assertEqual(Position.from_dict(record["state"]), state)
            state = simulate_turn(state, record["action"], rng)
            self.assertEqual(Position.from_dict(record["next_state"]), state)
            self.assertEqual(sum(record["policy_target"]), 1)
            chosen = record["policy_target"].index(1)
            self.assertEqual(record["candidate_actions"][chosen], record["action"])
            self.assertIn(record["value_target"], (-1, 0, 1))
        self.assertEqual(state.to_dict(), summary["final_state"])

    def test_export_balances_roles_and_keeps_existing_runs(self):
        with TemporaryDirectory() as directory:
            first, second = Path(directory) / "first", Path(directory) / "second"
            map_path = ROOT / "maps" / "demo.xml"
            manifest = export_games(map_path, first, games=4, seed=11, max_plies=20)
            export_games(map_path, second, games=4, seed=11, max_plies=20)
            for name in ("manifest.json", "games.jsonl", "transitions.jsonl"):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            games = [json.loads(line) for line in (first / "games.jsonl").read_text().splitlines()]
            self.assertEqual(len({(g["baseline_species"], g["first_player"]) for g in games}), 4)
            transitions = [json.loads(line) for line in (first / "transitions.jsonl").read_text().splitlines()]
            self.assertEqual(len(transitions), manifest["transitions"])
            self.assertEqual(manifest["rules_profile"], "server-v3.2.1")
            with self.assertRaises(FileExistsError):
                export_games(map_path, first, games=1)

    def test_cli_runs_without_server_or_gpu(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = subprocess.run(
                [sys.executable, "simulate.py", "--games", "4", "--seed", "7", "--max-plies", "12",
                 "--rules-profile", "brief", "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Completed 4 CPU games", result.stdout)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["rules_profile"], "brief")
            self.assertEqual(manifest["purpose"], "baseline_pipeline_example")

    def test_invalid_export_does_not_create_a_run(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            with self.assertRaises(ValueError):
                export_games(ROOT / "maps" / "demo.xml", output, games=0)
            self.assertFalse(output.exists())

    def test_manifest_reconstructs_the_initial_map_without_a_source_path(self):
        with TemporaryDirectory() as directory:
            manifest = export_games(ROOT / "maps" / "demo.xml", Path(directory) / "run",
                                    games=1, max_plies=5, rules_profile="brief")
            self.assertEqual(Position.from_dict(manifest["initial_state"]),
                             load_map(ROOT / "maps" / "demo.xml", rules_profile="brief"))
            self.assertEqual(manifest["rules_profile"], "brief")
            self.assertEqual(len(manifest["code_sha256"]), 64)
            self.assertIn("python_version", manifest)


if __name__ == "__main__":
    unittest.main()
