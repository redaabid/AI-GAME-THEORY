"""Small saved-position regression experiment; not a replacement tournament.

Replays four observed states for 40 plies, fresh agents, depth 4 untimed,
same baseline opponent and battle seed; then probes initial choices at 1.5 s.
Old agents and archived campaigns remain untouched.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agents import make_agent, safe_choose, TurnContext
from agents.ab2_experiments import repetition_key
from game import distance
from simulator import Position, simulate_turn, get_outcome, opponent


def gap(node, species):
    own=[p for p,c in node.cells.items() if getattr(c,species)]
    enemy=[p for p,c in node.cells.items() if getattr(c,opponent(species))]
    return min((distance(a,b) for a in own for b in enemy),default=None)


def replay(case,name):
    node=Position.from_dict(case['position'])
    actor=node.to_play
    width=7 if case['profile']=='width7' else 6
    agents={actor:make_agent(f'{name}:depth=4,max_depth=24,width={width},extra=0'),
            opponent(actor):make_agent('ab2exp:depth=4,max_depth=24,width=6,extra=0')}
    for species,agent in agents.items():agent.new_game(node,species,5422009)
    histories={s:[] for s in agents}
    seen=Counter();rows=[];rng=random.Random(5422009)
    repeated=0;started=time.perf_counter()
    for _ in range(40):
        if get_outcome(node,max_plies=200) is not None:break
        key=repetition_key(node);repeated+=seen[key]>0;seen[key]+=1
        mover=node.to_play
        moves,fault=safe_choose(agents[mover],node,TurnContext(None,200,histories[mover]))
        if fault:raise RuntimeError(fault)
        rows.append(dict(position=node.to_dict(),moves=moves,metrics=agents[mover].info))
        histories[mover].append((node,moves))
        node=simulate_turn(node,moves,rng)
    outcome=get_outcome(node,max_plies=200)
    return dict(agent=name,width=width,plies=len(rows),repetitions=repeated,
                start_gap=case['distance'],end_gap=gap(node,actor),
                outcome=outcome.__dict__ if outcome else None,
                window_limit=outcome is None,seconds=time.perf_counter()-started,
                trace=rows,final_position=node.to_dict())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    fixture=ROOT/'tests/fixtures/ab2_stagnation.json'
    cases=json.loads(fixture.read_text())
    protocol=dict(created=datetime.now(timezone.utc).isoformat(),cases=cases,
                  fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
                  python=sys.version,window_plies=40,fixed_depth=4,seed=5422009,
                  timeout_probe_budget=1.5,max_plies=200,
                  files={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()
                         for folder in (ROOT,ROOT/'agents') for f in folder.glob('*.py')})
    (args.output/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    records=[];probes=[]
    for index,case in enumerate(cases):
        for name in ('ab2exp','ab2tie'):
            r=replay(case,name);r['case']=index
            (args.output/f'{index}-{name}.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
            records.append({k:v for k,v in r.items() if k not in ('trace','final_position')})
            node=Position.from_dict(case['position']);width=r['width']
            agent=make_agent(f'{name}:depth=1,max_depth=24,width={width},extra=0')
            start=time.perf_counter()
            moves,fault=safe_choose(agent,node,TurnContext(start+1.5,200))
            elapsed=time.perf_counter()-start
            probes.append(dict(case=index,agent=name,width=width,moves=moves,fault=fault,
                               seconds=elapsed,metrics=agent.info,
                               after_gap=gap(simulate_turn(node,moves,None),node.to_play)))
            (args.output/'probes.json').write_text(json.dumps(probes,indent=2),encoding='utf-8')
    (args.output/'summary.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps(dict(replays=records,probes=[{k:v for k,v in p.items() if k!='metrics'} for p in probes]),indent=2))
    return int(any(p['fault'] or p['seconds']>1.8 for p in probes))


if __name__=='__main__':
    raise SystemExit(main())
