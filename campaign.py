"""Run the four-map MCTS comparison with one checkpoint per finished game.

    python campaign.py --opponent ab2 --max-games 4
    python campaign.py --opponent ab2
    python campaign.py --opponent mcts-v1
    python campaign.py --opponent mcts-v1 --agent mcts-v3

The same command resumes the same campaign automatically. Completed games are
never rerun; interrupted games restart. Existing tournament.py runs are separate.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
import multiprocessing
import os
from pathlib import Path
import platform
import signal
from tempfile import NamedTemporaryFile

from agents import make_agent, parse_spec
from simulator import get_outcome, load_map
from tournament import ROLES, _run_job, markdown_tables, summarize

ROOT = Path(__file__).resolve().parent
PARAMS = "width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000"
MAP_NAMES = ("testmap2", "thetrap", "val-large-1290000", "val-medium-1280000")
RESULT_KEYS = ("i", "j", "map_name", "round", "a_species", "first", "seed")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()


def runtime_hashes():
    paths = sorted([*ROOT.glob("*.py"), *(ROOT / "agents").glob("*.py")])
    return {p.relative_to(ROOT).as_posix(): sha256(
        p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in paths}


def make_plan(names, maps, *, seed=20261028, workers=2, max_plies=200,
              move_time=2.0, margin=0.5, rounds=1):
    if len(names) != 2 or len(set(names)) != 2:
        raise ValueError("A campaign needs two different agent specs.")
    if not maps or len({name for name, _ in maps}) != len(maps):
        raise ValueError("Maps must be nonempty and have unique names.")
    if any(type(value) is not int or value < 1 for value in (workers, max_plies, rounds)):
        raise ValueError("workers, max_plies and rounds must be positive integers.")
    if (not isfinite(move_time) or move_time < 0 or not isfinite(margin) or margin < 0
            or (move_time and margin >= move_time)):
        raise ValueError("Timing must be finite and nonnegative; margin must be smaller than move-time.")
    jobs = []
    settings = dict(max_plies=max_plies, move_time=move_time, margin=margin, on_timeout="skip")
    for index, (map_name, position) in enumerate(maps):
        if get_outcome(position) is not None:
            raise ValueError(f"Map {map_name} is already terminal.")
        for round_index in range(rounds):
            for role, (species, first) in enumerate(ROLES):
                jobs.append(dict(i=0, j=1, a=names[0], b=names[1], map_name=map_name,
                                 map=position.to_dict(), round=round_index, a_species=species, first=first,
                                 seed=seed + 100_003 * index + 4 * round_index + role, settings=settings))
    return dict(schema_version=1, agents=list(names), workers=workers,
                python_version=platform.python_version(), source_sha256=runtime_hashes(), jobs=jobs)


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=1, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def campaign_lock(directory):
    """OS releases the lock on exit/crash; no stale PID lock after a reboot."""
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "run.lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError("This checkpoint is already open by another campaign.") from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def result_key(result):
    return tuple(result[key] for key in RESULT_KEYS)


def read_games(directory, plan):
    results = {}
    for path in sorted((directory / "games").glob("game-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        index = record["game_index"]
        if type(index) is not int or not 0 <= index < len(plan["jobs"]) or index in results:
            raise ValueError(f"Invalid or duplicate game index in {path}")
        job, result = plan["jobs"][index], record["result"]
        if (record["job_sha256"] != digest(job) or record["result_sha256"] != digest(result)
                or result_key(result) != result_key(job)):
            raise ValueError(f"Checkpoint content does not match the planned game: {path}")
        results[index] = result
    return results


def save_report(directory, plan, results):
    games = [results[index] for index in sorted(results)]
    matrix, ranking = summarize(plan["agents"], games) if games else ({}, [])
    complete = len(games) == len(plan["jobs"])
    per_map = {}
    for name in sorted({game["map_name"] for game in games}):
        scores = [game["a_score"] for game in games if game["map_name"] == name]
        per_map[name] = dict(games=len(scores), wins=scores.count(1), draws=scores.count(0.5),
                             losses=scores.count(0), mean_score=sum(scores) / len(scores))
    report = dict(schema_version=1, status="complete" if complete else "partial",
                  updated_utc=utc_now(), completed_games=len(games), total_games=len(plan["jobs"]),
                  plan=plan, matrix=matrix, ranking=ranking, per_map=per_map, games=games)
    atomic_json(directory / "report.json", report)
    # report.json is authoritative; this Markdown is a regenerable convenience.
    if games:
        text = (f"{report['status'].upper()}: {len(games)}/{len(plan['jobs'])} games.\n\n"
                + markdown_tables(plan["agents"], matrix, ranking) + "\n")
        text += (f"\nResults for {plan['agents'][0]}:\n\n"
                 "| Map | Games | Wins | Draws | Losses | Score |\n|---|---|---|---|---|---|\n")
        for name, row in per_map.items():
            text += (f"| {name} | {row['games']} | {row['wins']} | {row['draws']} "
                     f"| {row['losses']} | {row['mean_score']:.3f} |\n")
        (directory / "report.md").write_text(text, encoding="utf-8")
    return report


def ignore_interrupt():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def pending_results(jobs, workers, heartbeat):
    if workers == 1:
        for job in jobs:
            yield _run_job(job)
    else:
        with multiprocessing.get_context("spawn").Pool(workers, initializer=ignore_interrupt) as pool:
            iterator = pool.imap_unordered(_run_job, jobs)
            remaining = len(jobs)
            while remaining:
                try:
                    result = iterator.next(timeout=15)
                except multiprocessing.TimeoutError:
                    heartbeat()
                    continue
                remaining -= 1
                yield result


def run_campaign(plan, directory, *, max_games=None, progress=None):
    """Save before announcing completion; only schedule games still missing."""
    if max_games is not None and (type(max_games) is not int or max_games < 1):
        raise ValueError("max_games must be a positive integer.")
    directory = Path(directory)
    interrupted = False
    with campaign_lock(directory):
        manifest = directory / "manifest.json"
        if manifest.exists():
            stored = json.loads(manifest.read_text(encoding="utf-8"))
            if stored["plan"] != plan:
                raise ValueError("Code, Python, maps or settings changed. Use a new --checkpoint folder.")
        else:
            if list((directory / "games").glob("game-*.json")):
                raise ValueError("Game checkpoints exist without their manifest; preserving them.")
            atomic_json(manifest, dict(created_utc=utc_now(), plan=plan))
        results = read_games(directory, plan)
        pending = [job for index, job in enumerate(plan["jobs"]) if index not in results]
        if max_games is not None:
            pending = pending[:max_games]
        lookup = {result_key(job): index for index, job in enumerate(plan["jobs"])}

        def announce(result=None):
            if progress:
                progress(len(results), len(plan["jobs"]), result)

        announce()
        try:
            for result in pending_results(pending, plan["workers"], announce) if pending else ():
                index = lookup[result_key(result)]
                if index in results:
                    raise ValueError("Duplicate completed game; preserving the existing checkpoint.")
                record = dict(game_index=index, job_sha256=digest(plan["jobs"][index]),
                              result_sha256=digest(result), saved_utc=utc_now(), result=result)
                atomic_json(directory / "games" / f"game-{index + 1:04d}.json", record)
                results[index] = result
                save_report(directory, plan, results)
                announce(result)
        except KeyboardInterrupt:
            interrupted = True
            results = read_games(directory, plan)
        finally:
            report = save_report(directory, plan, results)
    return report, interrupted


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--opponent", choices=("ab2", "ab6", "mcts-v1"), required=True)
    parser.add_argument("--agent", help="Challenger spec, e.g. mcts-v3; MCTS defaults to --iterations")
    parser.add_argument("--max-games", type=int, help="Finish at most N additional games, then stop")
    parser.add_argument("--checkpoint", type=Path, help="Default: .local/campaigns/mcts-vs-OPPONENT")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--rounds", type=int, help="4 role-balanced games per map per round; default 2 vs v1, 1 vs AB")
    parser.add_argument("--iterations", type=int, default=100000, help="Iteration cap per MCTS decision")
    parser.add_argument("--maps", nargs="+", type=Path, help="XML files or folders; default the four prepared maps")
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--move-time", type=float, default=2.0, help="Hard allowance; 0 for fixed-iteration screening")
    parser.add_argument("--margin", type=float, default=0.5, help="Reserve from allowance; default thinking time 1.5 s")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the plan without starting games or writing checkpoints")
    args = parser.parse_args(argv)
    if (min(args.workers, args.iterations, args.max_plies) < 1
            or (args.rounds is not None and args.rounds < 1)
            or (args.max_games is not None and args.max_games < 1)):
        parser.error("workers, iterations, max-plies, rounds and max-games must be positive")
    against_v1 = args.opponent == "mcts-v1"
    default_agent = "mcts-v2" if against_v1 else "mcts-memory"
    label = args.agent.partition(":")[0].strip() if args.agent else default_agent
    checkpoint_name = (f"{label}-vs-v1" if against_v1 else
                       f"{label if args.agent else 'mcts'}-vs-{args.opponent}")
    directory = args.checkpoint or ROOT / ".local" / "campaigns" / checkpoint_name

    def progress(done, total, result):
        if result is None:
            print(f"Saved {done}/{total} games. Workers running if games remain...", flush=True)
        else:
            score = {0: "loss", 0.5: "draw", 1: "win"}[result["a_score"]]
            print(f"Saved {done}/{total} | {result['map_name']} | {label} {score} | {result['plies']} plies", flush=True)

    try:
        challenger = args.agent or default_agent
        name, params = parse_spec(challenger)
        if name in ("mcts", "mcts-memory", "mcts-v1", "mcts-v2", "mcts-v3") and "iterations" not in params:
            challenger += f"{',' if ':' in challenger else ':'}iterations={args.iterations}"
        names = [challenger,
                 f"mcts-v1:iterations={args.iterations}" if against_v1 else f"{args.opponent}:{PARAMS}"]
        label = names[0].partition(":")[0]
        for name in names:
            make_agent(name)
        paths = ([file for path in args.maps for file in
                  (sorted(path.glob("*.xml")) if path.is_dir() else [path])] if args.maps else
                 [ROOT / ".local" / "maps" / "mcts-vs-best-ab" / (name + ".xml") for name in MAP_NAMES])
        maps = [(path.stem, load_map(path)) for path in paths]
        rounds = args.rounds if args.rounds is not None else (2 if against_v1 else 1)
        plan = make_plan(names, maps, workers=args.workers, rounds=rounds, seed=args.seed,
                         max_plies=args.max_plies, move_time=args.move_time, margin=args.margin)
        print(f"Checkpoint: {directory.resolve()}", flush=True)
        print(f"Agents: {names[0]} vs {names[1]}", flush=True)
        print(f"Planned: {len(plan['jobs'])} games | {len(maps)} maps | {rounds} rounds | {args.workers} workers", flush=True)
        print(f"Thinking time: {args.move_time - args.margin if args.move_time else 0:g} s per move "
              f"(0 = untimed), allowance {args.move_time:g} s | cap {args.max_plies} plies", flush=True)
        if args.dry_run:
            print("Plan validated. No games started and no checkpoint files written.")
            return 0
        report, interrupted = run_campaign(plan, directory, max_games=args.max_games, progress=progress)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Campaign failed: {error}\nAlready-saved game files are preserved.\n")
    print(f"{report['completed_games']}/{report['total_games']} saved. Report: {directory / 'report.json'}")
    if report["status"] != "complete":
        print("Run the same opponent command later to continue. Unfinished games restart.")
    return 130 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
