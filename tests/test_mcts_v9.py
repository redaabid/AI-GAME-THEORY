"""Recruitment thresholds, race clocks, reply losses and exact V6 controls."""

from dataclasses import replace
import json
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from agents import TurnContext, make_agent, safe_choose
from candidates import supported_turn
from game import Cell
from scripts.mcts_v9 import RecruitmentMCTSAgent
from scripts.mcts_v9.planning import Budget, Races, analyse, reply_damage
from search import action_key, search
from simulator import Position, load_map, simulate_turn

ROOT = Path(__file__).resolve().parents[1]
CHAIN = Position(3, 15, {(0, 1): Cell(vampires=10), (1, 1): Cell(humans=4),
                        (3, 1): Cell(humans=12), (14, 1): Cell(werewolves=10)})
CAPTURE = ((0, 1, 10, 1, 1),)


class PlanningTests(unittest.TestCase):
    def test_two_capture_sequence_unlocks_threshold_and_replays_to_26_units(self):
        scores, info = analyse(CHAIN, max_plies=200)
        self.assertEqual(info["status"], "complete")
        self.assertEqual(max(scores, key=scores.get), CAPTURE)
        best = next(row for row in info["plans"] if action_key(row["moves"]) == CAPTURE)
        self.assertEqual([row["humans"] for row in best["captures"]], [4, 12])
        self.assertEqual([row["strength_after"] for row in best["captures"]], [14, 26])
        self.assertEqual([row["own_arrival_ply"] for row in best["captures"]], [1, 5])
        p, rng = CHAIN, random.Random(0)
        for move, reply in ((CAPTURE, [(14, 1, 10, 14, 0)]),
                            ([(1, 1, 14, 2, 1)], [(14, 0, 10, 14, 1)]),
                            ([(2, 1, 14, 3, 1)], None)):
            p = simulate_turn(p, move, rng)
            if reply:
                p = simulate_turn(p, reply, rng)
        self.assertEqual(p.cells[3, 1].vampires, 26)
        self.assertEqual(p.ply, 5)

    def test_enemy_growth_is_in_arrival_times_and_ours_cannot_be_recruited_twice(self):
        races = Races(CHAIN, [((5, 1), 10)], [((4, 1), 2), ((2, 1), 12)], 8, Budget(20000))
        self.assertEqual(races.arrival((2, 1), 12, {}), 6)
        self.assertIsNone(races.arrival((2, 1), 12, {(4, 1): 1}))
        # Ours arrives on relative ply 5, before their ply 6; a further own
        # turn would arrive on ply 7 and lose that race.
        self.assertLess(2 * 3 - 1, races.arrival((2, 1), 12, {}))
        self.assertGreater(2 * 4 - 1, races.arrival((2, 1), 12, {}))

    def test_faster_enemy_can_prevent_future_recruitment_credit(self):
        board = Position(3, 9, {(0, 1): Cell(vampires=10), (4, 1): Cell(humans=4),
                                (5, 1): Cell(werewolves=10)})
        scores, info = analyse(board, max_plies=200)
        self.assertFalse(scores)
        self.assertGreater(info["rejected"].get("enemy_arrives_first", 0), 0)

    def test_certain_counterattack_makes_poisoned_capture_negative(self):
        board = Position(3, 6, {(0, 1): Cell(vampires=6), (1, 1): Cell(humans=1),
                                (2, 1): Cell(werewolves=20)})
        _, info = analyse(board)
        row = next(r for r in info["plans"] if action_key(r["moves"]) == ((0, 1, 6, 1, 1),))
        self.assertEqual(row["score"], -6)
        self.assertEqual(row["captures"][0]["reply_material_damage"], -7)
        self.assertEqual(reply_damage(7, 20, "server-v3.2.1"), -7)

    def test_possible_battle_stops_further_unchanged_strength_chain(self):
        board = Position(3, 15, {(0, 1): Cell(vampires=10), (1, 1): Cell(humans=4),
                                 (3, 1): Cell(humans=12), (2, 1): Cell(werewolves=8)})
        _, info = analyse(board)
        row = next(r for r in info["plans"] if action_key(r["moves"]) == CAPTURE)
        self.assertEqual(len(row["captures"]), 1)
        self.assertEqual(row["captures"][0]["reply_attackers"], 8)

    def test_recorded_capture_is_preferred_to_delaying_merges_in_the_planner(self):
        board = Position.from_dict(json.loads((ROOT / "examples/mcts_v5_delayed_capture.json").read_text())["state"])
        scores, info = analyse(board, max_plies=200)
        self.assertEqual(info["status"], "complete")
        preferred = [r for r in info["plans"] if r["score"] == max(scores.values())]
        self.assertTrue(all(any(tuple(c["target"]) == (4, 0) and c["own_arrival_ply"] == 1
                                for c in row["captures"]) for row in preferred))
        self.assertLess(info["work"], 20000)

    def test_clock_overflow_and_unaffordable_villages_do_not_create_growth(self):
        _, info = analyse(replace(CHAIN, ply=198), max_plies=200)
        self.assertTrue(all(len(r["captures"]) <= 1 for r in info["plans"]))
        board = Position(3, 8, {(0, 1): Cell(vampires=250), (1, 1): Cell(humans=10),
                                (7, 1): Cell(werewolves=250)})
        _, overflow = analyse(board)
        self.assertTrue(all(c["strength_after"] <= 255 for r in overflow["plans"] for c in r["captures"]))
        self.assertTrue(all(supported_turn(board.to_game_state(), row["moves"]) for row in overflow["plans"]))
        oversized = replace(CHAIN, cells={(0, 1): Cell(vampires=10), (1, 1): Cell(humans=20),
                                          (14, 1): Cell(werewolves=10)})
        self.assertFalse(analyse(oversized)[0])

    def test_budget_expiry_discards_all_preferences_and_species_swap_is_symmetric(self):
        scores, info = analyse(CHAIN, work=1)
        self.assertFalse(scores)
        self.assertEqual(info["status"], "work_limit")
        scores, info = analyse(CHAIN, deadline=time.perf_counter() - 1)
        self.assertFalse(scores)
        self.assertEqual(info["status"], "planning_deadline")
        swapped = replace(CHAIN, to_play="werewolves", cells={
            p: Cell(c.humans, c.werewolves, c.vampires) for p, c in CHAIN.cells.items()})
        self.assertEqual(analyse(CHAIN), analyse(swapped))


class AgentTests(unittest.TestCase):
    def test_recorded_v6_delay_is_repaired_at_equal_main_search_iterations(self):
        p = Position.from_dict(json.loads((ROOT / "examples/mcts_v5_delayed_capture.json").read_text())["state"])
        before = p.to_dict()
        moves = []
        for version in ("v6", "v9"):
            agent = make_agent(f"mcts-{version}:iterations=256")
            agent.new_game(p, p.to_play, 0)
            chosen, fault = safe_choose(agent, p, TurnContext(None, 200))
            self.assertIsNone(fault)
            self.assertEqual(agent.info["iterations"], 256)
            moves.append(chosen)
        self.assertFalse(any(tuple(m[3:]) == (4, 0) for m in moves[0]))
        self.assertTrue(any(tuple(m[3:]) == (4, 0) for m in moves[1]))
        after = simulate_turn(p, moves[1], random.Random(0))
        self.assertFalse(after.cells[4, 0].humans)
        self.assertEqual(sum(c.vampires for c in after.cells.values()),
                         14 + sum(c.vampires for c in p.cells.values()))
        self.assertEqual(p.to_dict(), before)

    def test_disabled_feature_preserves_v6_moves_root_targets_and_rng(self):
        for path in sorted((ROOT / "maps").glob("*.xml")):
            for species in ("vampires", "werewolves"):
                p = replace(load_map(path), to_play=species)
                v6, control = make_agent("mcts-v6:iterations=24"), make_agent("mcts-v9:recruitment=False,iterations=24")
                captured = []

                def observe(*args, **kwargs):
                    result = search(*args, **kwargs)
                    captured.append(result)
                    return result

                for a in (v6, control):
                    a.new_game(p, species, 7)
                with self.subTest(map=path.name, species=species):
                    with patch("scripts.mcts_v5.agent.search", side_effect=observe):
                        self.assertEqual(v6.choose_moves(p, TurnContext(None, 200)),
                                         control.choose_moves(p, TurnContext(None, 200)))
                    self.assertEqual(captured[0].training_metadata(), captured[1].training_metadata())
                    self.assertEqual(v6.rng.getstate(), control.rng.getstate())

    def test_guidance_keeps_all_root_candidates_and_v6_leaf_value(self):
        captured = []

        def observe(*args, **kwargs):
            result = search(*args, **kwargs)
            captured.append((result, kwargs))
            return result

        v6, v9 = make_agent("mcts-v6:iterations=64"), make_agent("mcts-v9:iterations=64")
        for a in (v6, v9):
            a.new_game(CHAIN, CHAIN.to_play, 0)
        with patch("scripts.mcts_v5.agent.search", side_effect=observe):
            v6.choose_moves(CHAIN, TurnContext(None, 200))
            moves, fault = safe_choose(v9, CHAIN, TurnContext(None, 200))
        self.assertIsNone(fault)
        self.assertTrue(v9.info["recruitment"]["guided"])
        self.assertTrue(supported_turn(CHAIN.to_game_state(), moves))
        self.assertEqual(captured[0][0].candidate_actions, captured[1][0].candidate_actions)
        self.assertTrue(all(0 <= v <= .12 for v in captured[1][1]["root_penalties"].values()))
        self.assertEqual(v6.leaf_value(CHAIN, "vampires", max_plies=200),
                         v9.leaf_value(CHAIN, "vampires", max_plies=200))
        self.assertEqual(v9.recruitment_totals["guided_decisions"], 1)
        self.assertEqual(v9.recruitment_totals["two_capture_decisions"], 1)
        v9.new_game(CHAIN, CHAIN.to_play, 0)
        self.assertEqual(v9.recruitment_totals["decisions"], 0)

    def test_no_humans_defers_to_v6_and_expired_deadlines_keep_legal_fallbacks(self):
        p = Position(3, 7, {(0, 1): Cell(vampires=6), (6, 1): Cell(werewolves=6)})
        v6, v9 = make_agent("mcts-v6:iterations=16"), make_agent("mcts-v9:iterations=16")
        for a in (v6, v9):
            a.new_game(p, p.to_play, 0)
        self.assertEqual(v6.choose_moves(p, TurnContext(None, 200)), v9.choose_moves(p, TurnContext(None, 200)))
        self.assertEqual(v6.rng.getstate(), v9.rng.getstate())
        moves, fault = safe_choose(v9, CHAIN, TurnContext(time.perf_counter() - 1, 200))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(CHAIN.to_game_state(), moves))
        self.assertTrue(v9.info["fallback"])
        self.assertEqual(v9.info["iterations"], 0)

    def test_config_validation_and_whole_decision_time_limit(self):
        for config in ({"recruitment": 1}, {"recruit_work": 0}, {"recruit_horizon": 17},
                       {"recruit_goals": True}, {"recruit_weight": float("nan")}, {"recruit_time": 0}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                RecruitmentMCTSAgent(**config)
        agent = RecruitmentMCTSAgent(iterations=100000, time_limit=.05)
        began = time.perf_counter()
        with patch("scripts.mcts_v5.agent.search", wraps=search) as call:
            moves, fault = safe_choose(agent, CHAIN, TurnContext(None, 200))
        self.assertIsNone(fault)
        self.assertLessEqual(call.call_args.kwargs["deadline"], began + .06)
        self.assertTrue(supported_turn(CHAIN.to_game_state(), moves))


if __name__ == "__main__":
    unittest.main()
