"""V7 objective proposals, alternating replies, persistence and V6 ablation."""

from dataclasses import replace
import json
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

from agents import TurnContext, make_agent, safe_choose
from candidates import supported_turn
from game import Cell, distance
from scripts.mcts_v7 import GoalMCTSAgent
from scripts.mcts_v7.objectives import Objective, policy_moves, progress, propose, track
from scripts.mcts_v7.planning import PROFILES, compare_objectives, continuation, objective_value
from scripts.mcts_v6.value import endgame_evaluate
from search import search
from simulator import Position, load_map, simulate_turn

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "examples/mcts_v7_tied_objectives.json").read_text())


def recorded():
    return Position.from_dict(FIXTURE["state"])


def context(deadline=None):
    return TurnContext(deadline, 200, [(Position.from_dict(r["state"]), r["action"])
                                     for r in FIXTURE["history"]])


class ObjectiveTests(unittest.TestCase):
    def test_proposals_cover_interception_recruitment_and_regrouping_without_oversized_attack(self):
        position = Position(7, 12, {(0, 0): Cell(vampires=8), (0, 3): Cell(vampires=8),
                                   (8, 0): Cell(werewolves=12), (11, 6): Cell(werewolves=4),
                                   (2, 2): Cell(humans=3), (5, 3): Cell(humans=20)})
        goals = propose(position)
        self.assertEqual({g.kind for g in goals}, {"intercept", "recruit", "regroup"})
        self.assertTrue(all(g.target != (5, 3) for g in goals))
        late = propose(recorded())
        self.assertEqual({g.target_count for g in late}, {4, 12})
        self.assertTrue(all(g.kind == "intercept" for g in late))

    def test_reply_models_generate_supported_moves_on_four_maps_both_species(self):
        for path in sorted((ROOT / "maps").glob("*.xml")):
            for species in ("vampires", "werewolves"):
                position = replace(load_map(path), to_play=species)
                for profile in PROFILES:
                    moves = policy_moves(position, profile=profile)
                    with self.subTest(map=path.name, species=species, profile=profile):
                        self.assertTrue(supported_turn(position.to_game_state(), moves))
                        simulate_turn(position, moves, random.Random(0))

    def test_tracking_follows_a_moving_target_and_invalidates_merges(self):
        position = recorded()
        goal = propose(position)[0]
        moved = replace(position, ply=60, cells={(27, 0): Cell(vampires=16), (10, 2): Cell(werewolves=12),
                                                (0, 1): Cell(werewolves=4), (14, 7): Cell(humans=20)})
        tracked = track(moved, goal, "vampires")
        self.assertEqual(tracked.source, (27, 0))
        self.assertEqual(tracked.target, (10, 2))
        self.assertEqual(tracked.created_ply, goal.created_ply)
        merged = replace(moved, cells={(27, 0): Cell(vampires=16), (10, 2): Cell(werewolves=16),
                                       (14, 7): Cell(humans=20)})
        self.assertIsNone(track(merged, tracked, "vampires"))

    def test_progress_does_not_replace_terminal_material_or_tactical_evaluation(self):
        root = recorded()
        goal = propose(root)[0]
        closer = replace(root, ply=60, cells={**{p: c for p, c in root.cells.items() if p != (28, 0)},
                                             (27, 1): Cell(vampires=16)})
        self.assertGreater(progress(closer, root, goal, "vampires"), 0)
        self.assertGreater(objective_value(closer, root, goal, "vampires", endgame_evaluate, .12,
                                          max_plies=200), 0)
        self.assertEqual(objective_value(closer, root, goal, "werewolves", endgame_evaluate, .12,
                                         max_plies=200),
                         -objective_value(closer, root, goal, "vampires", endgame_evaluate, .12, max_plies=200))
        terminal = replace(closer, ply=200)
        self.assertEqual(objective_value(terminal, root, goal, "vampires", endgame_evaluate, .12,
                                         max_plies=200), 0)
        changed = replace(closer, cells={**closer.cells, (0, 1): Cell(werewolves=3)})
        self.assertEqual(progress(changed, root, goal, "vampires"), 0)
        self.assertEqual(objective_value(changed, root, goal, "vampires", endgame_evaluate, .12,
                                         max_plies=200), endgame_evaluate(changed, "vampires", max_plies=200))
        capped = replace(changed, ply=200)
        # A deliberately soft evaluator (e.g. clock=False) cannot soften a
        # real population-at-cap outcome inside the objective comparison.
        self.assertEqual(objective_value(capped, root, goal, "vampires", lambda *a, **k: .01, .12,
                                         max_plies=200), 1)

    def test_counterattack_is_simulated_before_scoring_a_nonterminal_capture(self):
        position = Position(3, 4, {(0, 0): Cell(vampires=9), (1, 0): Cell(humans=1),
                                  (2, 0): Cell(werewolves=19)})
        goal = Objective("recruit", (0, 0), 9, (1, 0), 1, 0, 0)
        with patch("scripts.mcts_v7.planning.policy_moves", side_effect=[[(0, 0, 9, 1, 0)],
                                                                         [(2, 0, 19, 1, 0)]]):
            with patch("scripts.mcts_v7.planning.simulate_turn", wraps=simulate_turn) as calls:
                value, plies = continuation(position, goal, "economic", random.Random(0), depth=4,
                                            evaluator=endgame_evaluate, weight=.12, max_plies=200)
        self.assertEqual(plies, 2)
        self.assertEqual(value, -1)
        self.assertEqual([c.args[0].to_play for c in calls.call_args_list], ["vampires", "werewolves"])
        self.assertTrue(all(isinstance(c.args[2], random.Random) for c in calls.call_args_list))
        # The proposal policy itself avoids this certain kill-then-die trap.
        self.assertFalse(any(tuple(m[3:]) == (1, 0) for m in policy_moves(position, objective=goal)))

    def test_ranking_uses_worst_profile_and_discards_incomplete_comparison_rounds(self):
        goals = propose(recorded())

        def score(position, goal, profile, rng, **kwargs):
            value = (-.1 if profile == "evasive" else .5) if goal == goals[0] else .1
            return value, 4

        with patch("scripts.mcts_v7.planning.continuation", side_effect=score):
            best, rows, completed = compare_objectives(recorded(), goals, rng=random.Random(0),
                depth=4, samples=2, evaluator=endgame_evaluate, weight=.12)
        self.assertEqual(best, 1)
        self.assertEqual(completed, 2)
        self.assertEqual(rows[0]["robust_value"], -.1)
        with patch("scripts.mcts_v7.planning.continuation", side_effect=[(.8, 4), TimeoutError]):
            best, rows, completed = compare_objectives(recorded(), goals, rng=random.Random(0),
                depth=4, samples=2, evaluator=endgame_evaluate, weight=.12)
        self.assertIsNone(best)
        self.assertEqual(completed, 0)
        self.assertTrue(all(r["trials"] == 0 and r["robust_value"] is None for r in rows))


class V7AgentTests(unittest.TestCase):
    def test_validation_and_defaults(self):
        self.assertEqual(make_agent("mcts-v6").config, make_agent("mcts-v7").config)
        for kwargs in ({"goals": 1}, {"goal_depth": 3}, {"goal_depth": 0}, {"goal_samples": False},
                       {"goal_candidates": 0}, {"goal_weight": 1}, {"goal_fraction": .8},
                       {"goal_time": float("inf")}, {"goal_ttl": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                GoalMCTSAgent(**kwargs)

    def test_disabled_goals_exactly_reproduce_v6_on_four_maps_species_and_clocks(self):
        for path in sorted((ROOT / "maps").glob("*.xml")):
            for species in ("vampires", "werewolves"):
                for clock in (True, False):
                    position = replace(load_map(path), to_play=species)
                    agents = [make_agent(f"mcts-v6:iterations=16,clock={clock}"),
                              make_agent(f"mcts-v7:iterations=16,clock={clock},goals=False")]
                    results, chosen = [], []

                    def observe(*args, **kwargs):
                        result = search(*args, **kwargs)
                        results.append(result)
                        return result

                    for agent in agents:
                        agent.new_game(position, species, 5)
                        with patch("scripts.mcts_v5.agent.search", side_effect=observe):
                            chosen.append(agent.choose_moves(position, TurnContext(None, 40)))
                    with self.subTest(map=path.name, species=species, clock=clock):
                        self.assertEqual(chosen[0], chosen[1])
                        self.assertEqual(results[0].candidate_actions, results[1].candidate_actions)
                        self.assertEqual(results[0].training_metadata(), results[1].training_metadata())
                        self.assertEqual(agents[0].rng.getstate(), agents[1].rng.getstate())

    def test_no_repetition_and_tactical_contact_defer_to_v6(self):
        position = recorded()
        agent = GoalMCTSAgent(iterations=16)
        agent.new_game(position, position.to_play, 0)
        agent.choose_moves(position, TurnContext(None, 200))
        self.assertEqual(agent.info["goal_status"], "no_tied_repetition")
        tactical = Position(3, 4, {(0, 0): Cell(vampires=16), (1, 0): Cell(werewolves=12),
                                  (3, 2): Cell(werewolves=4)})
        agent.choose_moves(tactical, TurnContext(None, 200, [(replace(tactical, ply=0), [])]))
        self.assertEqual(agent.info["goal_status"], "tactical_contact")
        self.assertIsNone(agent.info["objective"])

    def test_recorded_stalemate_moves_inward_for_four_seeds(self):
        position = recorded()
        before = position.to_dict()
        for seed in range(4):
            agent = GoalMCTSAgent(iterations=512)
            agent.new_game(position, position.to_play, seed)
            moves, fault = safe_choose(agent, position, context())
            with self.subTest(seed=seed):
                self.assertIsNone(fault)
                self.assertTrue(supported_turn(position.to_game_state(), moves))
                goal = agent.info["objective"]
                self.assertIsNotNone(goal)
                self.assertEqual(goal["kind"], "intercept")
                self.assertLess(distance(tuple(moves[0][3:]), tuple(goal["target"])),
                                distance(tuple(moves[0][:2]), tuple(goal["target"])))
                self.assertEqual(agent.info["goal_samples_completed"], 3)
        self.assertEqual(position.to_dict(), before)

    def test_persistent_objective_tracks_the_next_real_reply_and_reset_clears_it(self):
        position = recorded()
        agent = GoalMCTSAgent(iterations=32, goal_samples=1, goal_depth=8)
        agent.new_game(position, position.to_play, 0)
        moves = agent.choose_moves(position, context())
        original = agent.info["objective"]
        after_own = simulate_turn(position, moves, random.Random(0))
        next_turn = simulate_turn(after_own, policy_moves(after_own), random.Random(0))
        ctx = TurnContext(None, 200, context().history + [(position, moves)])
        agent.choose_moves(next_turn, ctx)
        self.assertEqual(agent.info["goal_status"], "retained")
        self.assertEqual(agent.info["objective"]["created_ply"], original["created_ply"])
        agent.new_game(position, position.to_play, 0)
        self.assertIsNone(agent._goal)
        self.assertIsNone(agent.info)

    def test_expired_deadline_returns_legal_fallback_without_fault(self):
        agent = GoalMCTSAgent(iterations=100000)
        moves, fault = safe_choose(agent, recorded(), context(time.perf_counter() - 1))
        self.assertIsNone(fault)
        self.assertTrue(supported_turn(recorded().to_game_state(), moves))
        self.assertTrue(agent.info["fallback"])
        self.assertEqual(agent.info["goal_status"], "planning_deadline")

    def test_planning_reserve_is_part_of_the_whole_turn_budget(self):
        agent = GoalMCTSAgent(iterations=8, time_limit=.5)
        original_plan = agent._plan
        observed = []

        def observe(position, ctx, deadline):
            observed.append((time.perf_counter(), ctx.deadline, deadline))
            return original_plan(position, ctx, deadline)

        with patch.object(agent, "_plan", side_effect=observe):
            _, fault = safe_choose(agent, recorded(), context(time.perf_counter() + 1.5))
        self.assertIsNone(fault)
        now, total_deadline, plan_deadline = observed[0]
        self.assertLessEqual(total_deadline - now, .5)
        self.assertLessEqual(plan_deadline - now, .5 * .15)
        self.assertLess(plan_deadline, total_deadline)


if __name__ == "__main__":
    unittest.main()
