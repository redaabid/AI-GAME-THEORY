"""Regressions for observed stagnation and independent tactical properties."""
import json
from dataclasses import replace
from pathlib import Path
import random
import time
import unittest

from agents import make_agent, safe_choose, TurnContext
from agents.ab_variants import position_key
from candidates import supported_turn, generate_candidates
from game import Cell, distance
from mapgen import random_map
from simulator import Position, simulate_turn, get_outcome


def choose(name, node, width=6, depth=4, context=None):
    agent=make_agent(f'{name}:depth={depth},max_depth=24,width={width},extra=0')
    moves,fault=safe_choose(agent,node,context or TurnContext(None,200))
    if fault:
        raise AssertionError(fault)
    return agent,moves


class TieTests(unittest.TestCase):
    def test_logged_cases_keep_value_and_reduce_distance_without_changing_actions(self):
        cases=json.loads((Path(__file__).parent/'fixtures/ab2_stagnation.json').read_text())
        improved=0
        for row in cases:
            node=Position.from_dict(row['position'])
            width=7 if row['profile']=='width7' else 6
            a,old=choose('ab2exp',node,width)
            b,new=choose('ab2tie',node,width)
            with self.subTest(row=row['file']):
                self.assertEqual(a.info['value'],b.info['value'])
                self.assertEqual({r[1] for r in a.plans(node)}, {r[1] for r in b.plans(node)})
                self.assertTrue(supported_turn(node.to_game_state(),new))
                def gap(moves):
                    p=simulate_turn(node,moves,None)
                    own=[q for q,c in p.cells.items() if getattr(c,node.to_play)]
                    other='werewolves' if node.to_play=='vampires' else 'vampires'
                    enemies=[q for q,c in p.cells.items() if getattr(c,other)]
                    return min(distance(x,y) for x in own for y in enemies)
                self.assertLessEqual(gap(new),gap(old))
                improved+=gap(new)<gap(old)
        self.assertEqual(improved,3)

    def test_fixed_depth_values_match_on_fresh_positions(self):
        for seed in range(88100,88106):
            node=random_map(random.Random(seed),'small')
            for width in (6,7):
                a,_=choose('ab2exp',node,width,2)
                b,_=choose('ab2tie',node,width,2)
                self.assertEqual(a.info['value'],b.info['value'])

    def test_joint_guaranteed_elimination_still_has_priority(self):
        node=Position(3,3,{(0,0):Cell(vampires=3),(0,2):Cell(vampires=3),(1,1):Cell(werewolves=4)})
        for width in (6,7):
            _,moves=choose('ab2tie',node,width,3)
            self.assertEqual(len(moves),2)
            self.assertEqual(get_outcome(simulate_turn(node,moves,None)).winner,'vampires')

    def test_does_not_recruit_into_an_immediate_forced_loss(self):
        node=Position(3,3,{(0,1):Cell(vampires=10),(1,1):Cell(humans=3),
                           (2,1):Cell(werewolves=20)},rules_profile='brief')
        for width in (6,7):
            _,moves=choose('ab2tie',node,width,3)
            after=simulate_turn(node,moves,None)
            # Exhaust all full-group enemy steps, independently of candidate ranking.
            state=after.to_game_state()
            for (x,y),n in state.groups():
                for tx,ty in state.neighbors((x,y)):
                    end=get_outcome(simulate_turn(after,[(x,y,n,tx,ty)],None))
                    self.assertTrue(end is None or end.winner!='werewolves')

    def test_internal_cached_principal_does_not_bypass_root_policy(self):
        node=Position(5,25,{(0,0):Cell(vampires=18),(11,1):Cell(werewolves=12)},ply=58)
        agent,_=choose('ab2tie',node,6,4)
        key=(position_key(node),4,0,200)
        agent.table[key]=(582783,582783,582783,((0,0,18,0,1),))
        moves,fault=safe_choose(agent,node,TurnContext(None,200))
        self.assertIsNone(fault)
        self.assertEqual(moves,[(0,0,18,1,0)])

    def test_immediate_win_precedes_a_cached_delayed_winning_move(self):
        node=Position(5,25,{(1,3):Cell(vampires=18),(0,3):Cell(werewolves=12)},ply=54)
        agent,_=choose('ab2tie',node,7,3)
        # Exact winning score with a different principal can be legitimate:
        # it predicts eventual victory, not necessarily immediate elimination.
        for depth in (1,2,3):
            agent.table[(position_key(node),depth,0,200)]=(1000000,1000000,1000000,((1,3,18,2,3),))
        agent.history[((1,3,18,2,3),)]=1000000
        moves,fault=safe_choose(agent,node,TurnContext(None,200))
        self.assertIsNone(fault)
        self.assertEqual(get_outcome(simulate_turn(node,moves,None)).winner,'vampires')

    def test_expired_and_short_deadlines_remain_legal(self):
        node=random_map(random.Random(88199),'medium')
        for budget in (-1,.03):
            start=time.perf_counter()
            agent,moves=choose('ab2tie',node,7,context=TurnContext(start+budget,200))
            self.assertTrue(supported_turn(node.to_game_state(),moves))
            self.assertLess(time.perf_counter()-start,.3)
            if budget<0:self.assertTrue(agent.info['bootstrap'])

    def test_recent_exact_after_board_breaks_only_the_equal_score_choice(self):
        node=Position(5,25,{(0,0):Cell(vampires=18),(11,1):Cell(werewolves=12)},ply=58)
        previous=replace(node,ply=54)
        context=TurnContext(None,200,[(previous,[(0,0,18,1,0)])])
        agent,moves=choose('ab2tie',node,6,4,context)
        baseline,_=choose('ab2exp',node,6,4)
        self.assertNotEqual(moves,[(0,0,18,1,0)])
        self.assertEqual(agent.info['value'],baseline.info['value'])
        self.assertEqual(agent.info['recent_after_boards'],1)

    def test_past_random_combat_is_not_reconstructed_as_an_observation(self):
        previous=Position(3,3,{(0,0):Cell(vampires=4),(1,1):Cell(werewolves=4)})
        node=Position(5,25,{(0,0):Cell(vampires=18),(11,1):Cell(werewolves=12)},ply=58)
        context=TurnContext(None,200,[(previous,[(0,0,4,1,1)])])
        agent,_=choose('ab2tie',node,6,4,context)
        self.assertEqual(agent.info['recent_after_boards'],0)


if __name__=='__main__':
    unittest.main()
