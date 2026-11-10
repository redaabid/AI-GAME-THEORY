"""Paired, fixed-iteration continuations from the recorded 16-16 stalemate.

    python scripts/probe_mcts_v7.py --dry-run
    python scripts/probe_mcts_v7.py --pairs 4 --iterations 256 --workers 6
    python scripts/probe_mcts_v7.py --analyse .local/experiments/v7-stalemate-RUN

This tests one recorded position, not overall playing strength. V7 goals on/off
face the same V6 opponent with matched seeds and real history for both sides.
"""

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import multiprocessing
from pathlib import Path
import random
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.mcts_v5.agent as observed_module
import scripts.mcts_v7  # Registration also happens in Windows spawn workers.
from agents import TurnContext, make_agent, safe_choose
from agents.mcts_memory import position_key
from campaign import atomic_json, campaign_lock, digest, ignore_interrupt, runtime_hashes
from combat import win_probability
from game import distance
from scripts.compare_mcts_v7 import source_hashes
from simulator import SPECIES, Position, get_outcome, opponent, simulate_turn

SNAPSHOT = ROOT / "examples/mcts_v7_controlled_snapshot.json"


def totals(position):
    return {s: sum(getattr(c, s) for c in position.cells.values())
            for s in (*SPECIES, "humans")}


def separation(position):
    a = [p for p, c in position.cells.items() if c.vampires]
    b = [p for p, c in position.cells.items() if c.werewolves]
    return min((distance(x, y) for x in a for y in b), default=None)


def validate_snapshot(data):
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported controlled-snapshot schema.")
    position = Position.from_dict(data["state"])
    species = data["focal_species"]
    if species != position.to_play or get_outcome(position, max_plies=data["max_plies"]) is not None:
        raise ValueError("The focal side must move first from a nonterminal snapshot.")
    if totals(position)["vampires"] != totals(position)["werewolves"]:
        raise ValueError("This experiment requires tied initial populations.")
    history = {}
    for side in SPECIES:
        history[side] = []
        previous_ply = -1
        for record in data["history"][side]:
            old = Position.from_dict(record["state"])
            if (old.to_play != side or not previous_ply < old.ply < position.ply
                    or (old.rows, old.columns, old.rules_profile) != (
                        position.rows, position.columns, position.rules_profile)):
                raise ValueError("Snapshot history contains a future, unordered or incompatible position.")
            old.to_game_state().validate_moves(record["moves"])
            history[side].append((old, record["moves"]))
            previous_ply = old.ply
    if not any(position_key(old) == position_key(position) for old, _ in history[species][-32:]):
        raise ValueError("The supplied history must exercise V7's tied-repetition trigger.")
    # When the fixture supplies the complete historical prefix and its original
    # battle seed, independently verify that those real moves reach this board.
    prefix = sorted([entry for entries in history.values() for entry in entries], key=lambda r: r[0].ply)
    historical_seed = data.get("origin", {}).get("historical_battle_seed")
    if historical_seed is not None and [p.ply for p, _ in prefix] == list(range(position.ply)):
        current, rng = prefix[0][0], random.Random(historical_seed)
        for old, moves in prefix:
            if current != old:
                raise ValueError("Historical prefix does not replay to its next position.")
            current = simulate_turn(current, moves, rng)
        if current != position:
            raise ValueError("Historical prefix does not reach the selected snapshot.")
    return position, history


def experiment_plan(snapshot, *, pairs=4, iterations=256, workers=6, seed=20261108,
                    stop_after_plies=None):
    position, _ = validate_snapshot(snapshot)
    for name, value in (("pairs", pairs), ("iterations", iterations), ("workers", workers)):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer.")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer.")
    remaining = snapshot["max_plies"] - position.ply
    stop = remaining if stop_after_plies is None else stop_after_plies
    if type(stop) is not int or stop < 1:
        raise ValueError("stop-after-plies must be a positive integer.")
    specs = {arm: f"mcts-v7:goals={enabled},iterations={iterations}"
             for arm, enabled in (("on", True), ("off", False))}
    specs["opponent"] = f"mcts-v6:iterations={iterations}"
    for spec in specs.values():
        make_agent(spec)
    jobs = [dict(pair=i, seed=seed + i, arm=arm, id=f"pair-{i + 1:04d}-{arm}")
            for i in range(pairs) for arm in ("on", "off")]
    return dict(purpose="single_snapshot_fixed_iteration_ablation_not_strength_tournament",
                schema_version=1, snapshot=snapshot, snapshot_sha256=digest(snapshot),
                iterations=iterations, workers=workers, stop_after_plies=min(stop, remaining),
                specs=specs, jobs=jobs, core_source_sha256=runtime_hashes(), v7_source_sha256=source_hashes(),
                experiment_source_sha256={"scripts/probe_mcts_v7.py": sha256(
                    Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()})


@contextmanager
def capture_root():
    original, captured = observed_module.search, {}

    def observe(*args, **kwargs):
        result = original(*args, **kwargs)
        captured["result"] = result
        return result

    observed_module.search = observe
    try:
        yield captured
    finally:
        observed_module.search = original


def battle_contacts(position, moves):
    arrivals = Counter()
    for _, _, n, x, y in moves:
        arrivals[x, y] += n
    contacts = []
    for target, n in sorted(arrivals.items()):
        cell = position.cells.get(target)
        if cell is None:
            continue
        defenders = cell.humans or getattr(cell, opponent(position.to_play))
        if defenders:
            contacts.append(dict(target=list(target), kind="humans" if cell.humans else "monsters",
                                 attackers=n, defenders=defenders,
                                 probability=win_probability(n, defenders, humans=bool(cell.humans),
                                                             rules_profile=position.rules_profile)))
    return contacts


def summarize(rows, plan, job, final):
    focal = plan["snapshot"]["focal_species"]
    own = [r for r in rows if r["actor"] == focal]
    outcome = get_outcome(final, max_plies=plan["snapshot"]["max_plies"])
    populations = totals(final)
    distances = [r["enemy_distance"] for r in rows if r["enemy_distance"] is not None]
    return dict(job=job, job_sha256=digest(job), status="terminal" if outcome else "truncated",
                score=None if outcome is None else (outcome.value_for(focal) + 1) / 2,
                outcome=None if outcome is None else dict(winner=outcome.winner, reason=outcome.reason),
                initial_ply=plan["snapshot"]["state"]["ply"], final_state=final.to_dict(),
                recorded_plies=len(rows), final_populations=populations,
                margin=populations[focal] - populations[opponent(focal)],
                objective_decisions=sum(r["info"].get("objective") is not None for r in own),
                goal_statuses=dict(Counter(r["info"].get("goal_status") for r in own)),
                first_objective=next((dict(ply=r["ply"], objective=r["info"]["objective"])
                                      for r in own if r["info"].get("objective") is not None), None),
                minimum_enemy_distance=min(distances, default=None),
                first_contact_ply=next((r["ply"] for r in rows if r["enemy_distance"] == 1), None),
                repeated_focal_positions=sum(r["repeated"] for r in own),
                focal_cpu_seconds=sum(r["cpu_seconds"] for r in own),
                focal_wall_seconds=sum(r["wall_seconds"] for r in own),
                planning_seconds=sum(r["info"].get("goal_planning_seconds", 0) for r in own),
                population_events=[dict(after_ply=r["ply"] + 1, actor=r["actor"],
                                        populations=r["populations_after"], contacts=r["contacts"])
                                   for r in rows if r["populations_before"] != r["populations_after"]],
                faults=[])


def continue_game(plan, job, *, on_record=None):
    position, history = validate_snapshot(plan["snapshot"])
    focal = position.to_play
    specs = {focal: plan["specs"][job["arm"]], opponent(focal): plan["specs"]["opponent"]}
    agents = {s: make_agent(specs[s]) for s in SPECIES}
    for index, side in enumerate(SPECIES):
        agents[side].new_game(position, side, 2 * job["seed"] + index)
    seen = {s: Counter(position_key(p) for p, _ in history[s]) for s in SPECIES}
    rng, rows = random.Random(job["seed"]), []
    with capture_root() as captured:
        while (get_outcome(position, max_plies=plan["snapshot"]["max_plies"]) is None
               and len(rows) < plan["stop_after_plies"]):
            actor, before = position.to_play, position
            old_goal = getattr(agents[actor], "_goal", None)
            captured.clear()
            started, cpu = time.perf_counter(), time.process_time()
            moves, fault = safe_choose(agents[actor], position,
                                       TurnContext(None, plan["snapshot"]["max_plies"], history[actor]))
            elapsed, used_cpu = time.perf_counter() - started, time.process_time() - cpu
            result, info = captured.get("result"), agents[actor].info
            if fault or result is None or result.iterations != plan["iterations"]:
                raise ValueError(f"Invalid fixed-iteration decision at ply {before.ply}: {fault or 'missing budget/root'}")
            if not rows and (bool(info.get("objective")) != (job["arm"] == "on")):
                raise ValueError("Initial objective activation did not match the planned ablation.")
            position = simulate_turn(before, moves, rng)
            key = position_key(before)
            row = dict(ply=before.ply, actor=actor, agent=specs[actor], before=before.to_dict(),
                       after=position.to_dict(), moves=moves, info=info,
                       goal_before=None if old_goal is None else old_goal.to_dict(),
                       root=result.training_metadata() | {"candidate_actions": result.candidate_actions},
                       repeated=seen[actor][key] > 0, enemy_distance=separation(before),
                       contacts=battle_contacts(before, moves), populations_before=totals(before),
                       populations_after=totals(position), wall_seconds=elapsed, cpu_seconds=used_cpu)
            row = json.loads(json.dumps(row, allow_nan=False))
            rows.append(row)
            seen[actor][key] += 1
            history[actor].append((before, moves))
            if on_record:
                on_record(row)
    return summarize(rows, plan, job, position), rows


def verify_rows(rows, plan, job):
    current, _ = validate_snapshot(plan["snapshot"])
    rng = random.Random(job["seed"])
    for row in rows:
        if current.to_dict() != row["before"] or row["actor"] != current.to_play or row["ply"] != current.ply:
            raise ValueError("Discontinuous controlled trace.")
        if get_outcome(current, max_plies=plan["snapshot"]["max_plies"]) is not None:
            raise ValueError("Trace continued after the game ended.")
        if row["root"]["iterations"] != plan["iterations"] or sum(row["root"]["visits"]) != plan["iterations"]:
            raise ValueError("Trace has a different MCTS iteration budget.")
        current = simulate_turn(current, row["moves"], rng)
        if current.to_dict() != row["after"]:
            raise ValueError("Moves and battle seed do not reproduce the controlled trace.")
    if not rows or bool(rows[0]["info"].get("objective")) != (job["arm"] == "on"):
        raise ValueError("Missing initial activation evidence.")
    if job["arm"] == "off" and any(r["info"].get("objective") for r in rows):
        raise ValueError("Disabled arm unexpectedly activated an objective.")
    return current


def execute_job(args):
    plan, job, base = args
    if (runtime_hashes() != plan["core_source_sha256"] or source_hashes() != plan["v7_source_sha256"]):
        raise ValueError("Source changed before a controlled continuation started.")
    folder = Path(base) / job["id"]
    folder.mkdir(exist_ok=True)
    attempt = folder / f"attempt-{len(list(folder.glob('attempt-*'))) + 1:04d}"
    attempt.mkdir()
    trace = attempt / "trace.jsonl"
    with trace.open("x", encoding="utf-8") as stream:
        def save(row):
            stream.write(json.dumps(row, allow_nan=False) + "\n")
            stream.flush()
        summary, rows = continue_game(plan, job, on_record=save)
    verified = verify_rows(rows, plan, job)
    if verified.to_dict() != summary["final_state"]:
        raise ValueError("Verified continuation ends at another board.")
    summary.update(trace_file=trace.relative_to(Path(base)).as_posix(),
                   trace_sha256=sha256(trace.read_bytes()).hexdigest())
    atomic_json(folder / "result.json", summary)
    return job["id"]


def read_results(directory, plan):
    results = {}
    for job in plan["jobs"]:
        path = directory / job["id"] / "result.json"
        if not path.exists():
            continue
        summary = json.loads(path.read_text(encoding="utf-8"))
        if summary["job"] != job or summary["job_sha256"] != digest(job):
            raise ValueError("Saved result belongs to a different continuation.")
        trace = (directory / summary["trace_file"]).resolve()
        if not trace.is_relative_to(directory.resolve()):
            raise ValueError("Trace path escapes the experiment directory.")
        if sha256(trace.read_bytes()).hexdigest() != summary["trace_sha256"]:
            raise ValueError("Controlled trace fingerprint changed.")
        rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        final = verify_rows(rows, plan, job)
        expected = summarize(rows, plan, job, final)
        if any(summary.get(k) != v for k, v in expected.items()):
            raise ValueError("Saved summary does not match its controlled trace.")
        results[job["id"]] = summary
    return results


def write_report(directory, plan, results):
    arms = {}
    for arm in ("on", "off"):
        rows = [r for r in results.values() if r["job"]["arm"] == arm]
        scores = [r["score"] for r in rows if r["score"] is not None]
        arms[arm] = dict(completed=len(rows), terminal=len(scores), wins=scores.count(1), draws=scores.count(.5),
                         losses=scores.count(0), mean_score=sum(scores) / len(scores) if scores else None,
                         objective_decisions=sum(r["objective_decisions"] for r in rows))
    pairs = []
    for i in sorted({j["pair"] for j in plan["jobs"]}):
        pair = {j["arm"]: results[j["id"]] for j in plan["jobs"] if j["pair"] == i and j["id"] in results}
        if len(pair) != 2:
            continue
        on, off = pair["on"], pair["off"]
        pairs.append(dict(pair=i, seed=on["job"]["seed"], on_score=on["score"], off_score=off["score"],
                          score_delta=on["score"] - off["score"] if on["score"] is not None and off["score"] is not None else None,
                          on_margin=on["margin"], off_margin=off["margin"],
                          on_objective_decisions=on["objective_decisions"], off_objective_decisions=off["objective_decisions"],
                          on_minimum_distance=on["minimum_enemy_distance"], off_minimum_distance=off["minimum_enemy_distance"]))
    deltas = [p["score_delta"] for p in pairs if p["score_delta"] is not None]
    report = dict(purpose=plan["purpose"], status="complete" if len(results) == len(plan["jobs"]) else "partial",
                  completed_continuations=len(results), planned_continuations=len(plan["jobs"]), arms=arms, pairs=pairs,
                  pairs_improved=sum(d > 0 for d in deltas), pairs_worsened=sum(d < 0 for d in deltas),
                  pairs_unchanged=sum(d == 0 for d in deltas))
    atomic_json(directory / "analysis.json", report)
    text = ["# Controlled V7 stalemate ablation", "", f"{report['status']}: {len(results)}/{len(plan['jobs'])} continuations.",
            "", "One historical board, fixed MCTS iterations, no deadlines. V7 does additional planning work.",
            "Truncated continuations have no match score. This is not a general strength tournament.", "",
            "| Goals | Terminal | Wins | Draws | Losses | Score | Objective decisions |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for arm, row in arms.items():
        score = "n/a" if row["mean_score"] is None else f"{row['mean_score']:.4f}"
        text.append(f"| {arm} | {row['terminal']} | {row['wins']} | {row['draws']} | {row['losses']} | {score} | {row['objective_decisions']} |")
    text += ["", "| Seed | On score | Off score | On / off margin | On / off minimum enemy distance |",
             "|---|---:|---:|---|---|"]
    for row in pairs:
        text.append(f"| {row['seed']} | {row['on_score']} | {row['off_score']} | {row['on_margin']} / {row['off_margin']} | {row['on_minimum_distance']} / {row['off_minimum_distance']} |")
    text += ["", f"Paired outcomes: improved {report['pairs_improved']}, worsened {report['pairs_worsened']}, unchanged {report['pairs_unchanged']}.",
             "", "Same future battle seeds do not imply identical battles after the policies diverge."]
    (directory / "analysis.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return report


def run(plan, directory, *, max_continuations=None):
    directory = Path(directory)
    with campaign_lock(directory):
        manifest = directory / "manifest.json"
        if manifest.exists():
            if json.loads(manifest.read_text(encoding="utf-8"))["plan"] != plan:
                raise ValueError("Settings or sources changed. Use a new --output directory.")
        else:
            if list(directory.glob("pair-*")):
                raise ValueError("Results exist without their manifest; preserving them.")
            atomic_json(manifest, dict(created_utc=datetime.now(timezone.utc).isoformat(), plan=plan))
            sources = plan["core_source_sha256"] | plan["v7_source_sha256"] | plan["experiment_source_sha256"]
            with zipfile.ZipFile(directory / "source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
                for relative, expected in sources.items():
                    data = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
                    if sha256(data).hexdigest() != expected:
                        raise ValueError(f"Source changed: {relative}")
                    archive.writestr(relative, data)
                archive.writestr("snapshot.json", json.dumps(plan["snapshot"], indent=2))
        saved = read_results(directory, plan)
        pending = [j for j in plan["jobs"] if j["id"] not in saved]
        if max_continuations is not None:
            pending = pending[:max_continuations]
        write_report(directory, plan, saved)
        args = [(plan, job, str(directory)) for job in pending]

        def completed(identifier):
            saved.update(read_results(directory, plan))
            report = write_report(directory, plan, saved)
            row = saved[identifier]
            print(f"Saved {len(saved)}/{len(plan['jobs'])} | seed {row['job']['seed']} | goals {row['job']['arm']}"
                  f" | score {row['score']} | objectives {row['objective_decisions']}", flush=True)
            return report

        if args and plan["workers"] > 1:
            with multiprocessing.get_context("spawn").Pool(min(plan["workers"], len(args)), initializer=ignore_interrupt) as pool:
                iterator = pool.imap_unordered(execute_job, args)
                left = len(args)
                while left:
                    try:
                        completed(iterator.next(timeout=15))
                        left -= 1
                    except multiprocessing.TimeoutError:
                        print(f"Saved {len(saved)}/{len(plan['jobs'])}; fixed-iteration workers running...", flush=True)
        else:
            for argument in args:
                completed(execute_job(argument))
        return write_report(directory, plan, saved)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--pairs", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=256)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--stop-after-plies", type=int)
    parser.add_argument("--max-continuations", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--analyse", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.max_continuations is not None and args.max_continuations < 1:
        parser.error("max-continuations must be positive")
    try:
        if args.analyse:
            plan = json.loads((args.analyse / "manifest.json").read_text(encoding="utf-8"))["plan"]
            if runtime_hashes() != plan["core_source_sha256"]:
                raise ValueError("Simulator differs from the recorded source; use the archived version.")
            report = write_report(args.analyse, plan, read_results(args.analyse, plan))
            print(json.dumps(report, indent=2))
            return 0
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        plan = experiment_plan(snapshot, pairs=args.pairs, iterations=args.iterations, workers=args.workers,
                               seed=args.seed, stop_after_plies=args.stop_after_plies)
        directory = args.output or ROOT / ".local/experiments" / (
            "v7-stalemate-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        print(f"Output: {directory.resolve()}", flush=True)
        print(f"Paired seeds: {args.pairs} | continuations: {len(plan['jobs'])} | MCTS iterations/decision: {args.iterations}"
              f" | workers: {args.workers} | start/cap: {snapshot['state']['ply']}/{snapshot['max_plies']}", flush=True)
        if args.dry_run:
            print("Validated. No continuations started or files written.")
            return 0
        report = run(plan, directory, max_continuations=args.max_continuations)
        print(f"{report['status'].upper()}: {report['completed_continuations']}/{report['planned_continuations']}", flush=True)
        print(f"Analysis: {directory.resolve() / 'analysis.md'}", flush=True)
        return 0
    except KeyboardInterrupt:
        print("Stopped. Finished continuations are saved; rerun with the same --output to resume.", flush=True)
        return 130
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Controlled experiment failed: {error}\nExisting results are preserved.\n")


if __name__ == "__main__":
    raise SystemExit(main())
