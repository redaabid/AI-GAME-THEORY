"""Checkpointed AB2 versus V6; raw turn traces, balanced roles, no core changes."""
from pathlib import Path
from hashlib import sha256
import argparse,ctypes,json,os,sys,time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import scripts.mcts_v6
import campaign
import tournament
from agents import make_agent
from campaign import atomic_json,make_plan,run_campaign
from simulator import load_map

PROFILES=ROOT/"scripts/ab2_profiles_2026_11_18.json"

def recorded_job(job):
    original=tournament.safe_choose
    turns=[]
    def choose(agent,position,context):
        started=time.perf_counter();cpu=time.process_time()
        moves,fault=original(agent,position,context)
        turns.append(dict(position=position.to_dict(),moves=moves,fault=fault,info=agent.info,
                          wall_seconds=time.perf_counter()-started,cpu_seconds=time.process_time()-cpu))
        return moves,fault
    tournament.safe_choose=choose
    try:
        result=tournament._run_job(job)
    finally:
        tournament.safe_choose=original
    target=Path(job["trace_directory"])/(str(time.time_ns())+"-"+str(job["seed"])+".json")
    result["trace_file"]=str(target)
    atomic_json(target,dict(job=job,result=result,turns=turns))
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",default="ab2_replies")
    parser.add_argument("--agent",help="Explicit spec overrides the named profile")
    parser.add_argument("--opponent",default="mcts-v6:iterations=100000")
    parser.add_argument("--maps",nargs="+",type=Path,required=True)
    parser.add_argument("--checkpoint",type=Path,default=ROOT/".local/campaigns/julian-ab2-replies")
    parser.add_argument("--seed",type=int,default=2026211304)
    parser.add_argument("--rounds",type=int,default=1)
    parser.add_argument("--workers",type=int,default=2)
    parser.add_argument("--max-plies",type=int,default=200)
    parser.add_argument("--move-time",type=float,default=2.0,help="Total allowance, not thinking budget")
    parser.add_argument("--margin",type=float,default=.5)
    parser.add_argument("--max-games",type=int,help="Maximum additional games in this invocation")
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(argv)
    try:
        profiles=json.loads(PROFILES.read_text(encoding="utf-8"))["profiles"]
        agent=args.agent or profiles[args.profile]
        for spec in (agent,args.opponent):make_agent(spec)
        files=[f for p in args.maps for f in (sorted(p.glob("*.xml")) if p.is_dir() else [p])]
        maps=[(p.stem,load_map(p)) for p in files]
        plan=make_plan([agent,args.opponent],maps,seed=args.seed,workers=args.workers,
                      rounds=args.rounds,max_plies=args.max_plies,move_time=args.move_time,margin=args.margin)
        plan["ab2_launcher_sha256"]={str(p.relative_to(ROOT)):sha256(p.read_bytes().replace(b"\r\n",b"\n")).hexdigest()
                                    for p in (Path(__file__),PROFILES)}
        for job in plan["jobs"]:job["trace_directory"]=str((args.checkpoint/"traces").resolve())
        print(f"Agents: {agent} vs {args.opponent}",flush=True)
        print(f"{len(plan['jobs'])} planned | {len(maps)} maps | {args.workers} workers | cap {args.max_plies}",flush=True)
        if args.dry_run:
            print("Validated; no games or checkpoint files written.")
            return 0
        def progress(done,total,result):
            if result:
                print(f"Saved {done}/{total}: {result['map_name']} score {result['a_score']}",flush=True)
                invalid=any(result[k]["faults"] or result[k]["timeouts"] or any(v>1.8 for v in result[k]["seconds"])
                            for k in ("a_stats","b_stats"))
                if invalid:
                    atomic_json(args.checkpoint/"INVALID_RUN.json",dict(map=result["map_name"],seed=result["seed"]))
                    raise ValueError("Invalid timing/fault: raw game saved; use a fresh directory for a rerun")
        old=campaign._run_job
        campaign._run_job=recorded_job
        if os.name=="nt":ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        try:
            report,interrupted=run_campaign(plan,args.checkpoint,max_games=args.max_games,progress=progress)
        finally:
            campaign._run_job=old
            if os.name=="nt":ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        print(f"{report['status']}: {report['completed_games']}/{report['total_games']} saved",flush=True)
        return 130 if interrupted else 0
    except (OSError,ValueError,KeyError) as error:
        parser.exit(1,f"Setup/run failed: {error}\nExisting results are preserved.\n")

if __name__=="__main__":raise SystemExit(main())
