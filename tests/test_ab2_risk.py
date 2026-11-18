import random
import time
import unittest
from agents import TurnContext, make_agent, safe_choose
from agents.ab_variants import exact_successors
from agents.ab2_risk import uncertain_combat
from candidates import generate_candidates, supported_turn
from game import Cell
from simulator import Position, get_outcome, simulate_turn
from mapgen import random_map

def run(node, name="ab2risk", depth=2, deadline=None):
    a=make_agent(f"{name}:depth={depth},max_depth=24,width=7,extra=0")
    m,f=safe_choose(a,node,TurnContext(deadline,200))
    if f:raise AssertionError(f)
    return a,m

def exact_oracle(a,node,depth):
    if depth==0 or get_outcome(node,max_plies=200):return a.leaf(node)
    actions=generate_candidates(node,limit=7)
    return max(sum(q*-exact_oracle(a,p,depth-1) for q,p in exact_successors(node,m)) for m in actions)

class RiskTests(unittest.TestCase):
    def test_losing_endgame_prefers_real_chance_to_certain_loss(self):
        p=Position(3,3,{(0,1):Cell(vampires=2),(1,1):Cell(werewolves=10)},ply=198)
        a,m=run(p)
        self.assertEqual(m,[(0,1,2,1,1)])
        self.assertGreater(a.info["value"],-1000000)
        self.assertAlmostEqual(a.info["value"],exact_oracle(a,p,2),places=4)

    def test_exact_chance_minimax_value_with_cold_and_warm_cache(self):
        for species in ("vampires","werewolves"):
            other="werewolves" if species=="vampires" else "vampires"
            p=Position(3,3,{(0,1):Cell(**{species:4}),(1,1):Cell(**{other:4})},to_play=species,ply=198)
            a,_=run(p)
            expected=exact_oracle(a,p,2)
            self.assertAlmostEqual(a.info["value"],expected,places=4)
            a.choose_moves(p,TurnContext(None,200))
            self.assertAlmostEqual(a.info["value"],expected,places=4)

    def test_quiet_reference_parity(self):
        p=Position(5,25,{(0,0):Cell(vampires=18),(11,1):Cell(werewolves=12)},ply=58)
        a,m=run(p,depth=3);b,n=run(p,"ab2exp",depth=3)
        self.assertEqual((m,a.info["value"]),(n,b.info["value"]))
        self.assertEqual({r[1] for r in a.plans(p)},{r[1] for r in b.plans(p)})

    def test_certain_elimination(self):
        p=Position(3,3,{(0,0):Cell(vampires=18),(1,1):Cell(werewolves=12)})
        _,m=run(p)
        self.assertEqual(get_outcome(simulate_turn(p,m,None)).winner,"vampires")

    def test_joint_arrivals_are_combined(self):
        p=Position(3,3,{(0,0):Cell(vampires=3),(0,2):Cell(vampires=3),(1,1):Cell(werewolves=4)})
        self.assertFalse(uncertain_combat(p,[(0,0,3,1,1),(0,2,3,1,1)]))
        self.assertTrue(uncertain_combat(p,[(0,0,3,1,1)]))

    def test_human_battle_detection(self):
        p=Position(3,3,{(0,0):Cell(vampires=3),(1,1):Cell(humans=4),(2,2):Cell(werewolves=5)})
        self.assertTrue(uncertain_combat(p,[(0,0,3,1,1)]))

    def test_short_and_expired_deadlines(self):
        p=random_map(random.Random(88199),"medium")
        for budget in (-1,0.05):
            start=time.perf_counter();_,m=run(p,deadline=start+budget)
            self.assertTrue(supported_turn(p.to_game_state(),m))
            self.assertLess(time.perf_counter()-start,.3)
