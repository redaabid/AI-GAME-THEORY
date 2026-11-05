"""Analyze server-run logs: analyze.py LOG_DIR GAMES_DIR OUT_JSON."""
import json
import re
import sys
from pathlib import Path

TURN = re.compile(r"^INFO: Turn (\d+): (.*) \(([\d.]+) seconds\)$")
ALERT = 1.8


def bot_stats(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    times, species = [], None
    for line in lines:
        match = TURN.match(line)
        if match:
            times.append(float(match.group(3)))
        found = re.search(r"playing (vampires|werewolves)", line)
        if found:
            species = found.group(1)
    lower = [line.lower() for line in lines]
    problems = [line for line in lines
                if not line.startswith("INFO: ")
                or re.search(r"error|exception|traceback|disconnect|refused|reset|timeout|timed out", line, re.I)]
    return {
        "log": path.name,
        "species": species,
        "turns": len(times),
        "max": max(times) if times else None,
        "mean": sum(times) / len(times) if times else None,
        "alerts": [(i + 1, t) for i, t in enumerate(times) if t > ALERT],
        "agent_fault": sum("agent fault" in line for line in lower),
        "fallback_lines": sum("fallback" in line for line in lower),
        "fallback_true": sum("fallback=true" in line for line in lower),
        "problems": problems,
        "game_ended": any("Game ended" in line for line in lines),
        "session_finished": any("Server finished the session" in line for line in lines),
        "last_line": lines[-1] if lines else "",
    }


def server_result(path):
    if not path.exists():
        return None
    rows = [line.split(" | ", 2)[-1] for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]]
    pairs = rows[0::2]
    if rows[0::2] != rows[1::2]:
        pairs = rows  # Unexpected layout; keep everything.
    countdown = pairs[1]
    players = pairs[2:4]
    after = pairs[pairs.index("Human(s) left: ") + 1:]
    return {"countdown": countdown, "p1": players[0], "p2": players[1], "humans": int(after[0]),
            "p1_count": int(after[1]), "p2_count": int(after[2]), "message": " ".join(after[3:])}


def main(log_dir, games_dir, out_json):
    log_dir, games_dir = Path(log_dir), Path(games_dir)
    games = []
    for run_file in sorted(games_dir.glob("*_run.json")):
        run = json.loads(run_file.read_text(encoding="utf-8-sig"))
        tag = run["tag"]
        series, map_tag, order = tag.split("_", 2)
        timeline = (games_dir / f"{tag}_timeline.txt").read_text(encoding="utf-8-sig").splitlines()
        first_turn = next((line for line in timeline if re.search(r": INFO: Turn 1: ", line)), "")
        mover = first_turn.split(" ", 1)[1].split(":", 1)[0] if first_turn else None
        bots = {name: bot_stats(log_dir / f"{tag}_{name}.txt") for name in (run["first"], run["second"])}
        result = server_result(games_dir / f"{tag}_final.txt")
        plies = sum(b["turns"] for b in bots.values())
        games.append({"tag": tag, "max_plays": run["maxPlies"], "map": map_tag + ".xml",
                      "first": run["first"], "second": run["second"], "first_mover": mover,
                      "plies": plies, "wall_seconds": run["seconds"], "run": run,
                      "bots": bots, "server": result})
    Path(out_json).write_text(json.dumps(games, indent=1), encoding="utf-8")
    for g in games:
        s = g["server"] or {}
        print(f'{g["tag"]:45} plies={g["plies"]:3} first={g["first_mover"]:9} '
              f'{s.get("p1")}={s.get("p1_count")} {s.get("p2")}={s.get("p2_count")} hum={s.get("humans")} '
              f'cd={s.get("countdown")} "{s.get("message")}" wall={g["wall_seconds"]}')
        for name, b in g["bots"].items():
            print(f'    {name:9} {b["species"]:10} turns={b["turns"]:3} max={b["max"]:.3f} mean={b["mean"]:.3f} '
                  f'alerts={len(b["alerts"])} fault={b["agent_fault"]} fb_lines={b["fallback_lines"]} '
                  f'fb_true={b["fallback_true"]} ended={b["game_ended"]} bye={b["session_finished"]} '
                  f'exit={g["run"]["firstExit"] if name == g["first"] else g["run"]["secondExit"]} '
                  f'problems={len(b["problems"])}')
            for p in b["problems"][:5]:
                print("        !", p)


if __name__ == "__main__":
    main(*sys.argv[1:])
