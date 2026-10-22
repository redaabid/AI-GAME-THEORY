"""Replay one server game from the two bot logs: replay.py MAP_XML P1_LOG P2_LOG [FINAL_P1 FINAL_P2].

P1 is the bot connected first (vampires). Moves alternate P1, P2, P1... and each
ply prints the moves, the battles with their win probability, and the board.
Random battles are resolved by trying seeds until the next logged moves are legal
(and, at the end, the final counts of the server window match): the survivors
shown are one outcome consistent with the logs, not necessarily the real one.
"""
import ast
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from combat import win_probability  # noqa: E402
from simulator import get_outcome, load_map, simulate_turn  # noqa: E402

TURN = re.compile(r"^INFO: Turn (\d+): (.*) \(([\d.]+) seconds\)$")
RULES = "server-v3.2.1"


def moves_of(path):
    return [(ast.literal_eval(m.group(2)), m.group(3)) for m in map(TURN.match, open(path, encoding="utf-8")) if m]


def legal(position, moves):
    return all(getattr(position.cells.get((x, y)), position.to_play, 0) >= n for x, y, n, *_ in moves)


def counts(position):
    cells = position.cells.values()
    return (sum(c.vampires for c in cells), sum(c.werewolves for c in cells), sum(c.humans for c in cells))


def show(position):
    rows = []
    for y in range(position.rows):
        row = []
        for x in range(position.columns):
            c = position.cells.get((x, y))
            row.append("  . " if c is None else
                       f"{'H' if c.humans else 'V' if c.vampires else 'W'}{c.humans or c.vampires or c.werewolves:<3}")
        rows.append("      " + "".join(row))
    return "\n".join(rows)


def battles(position, moves):
    enemy = "werewolves" if position.to_play == "vampires" else "vampires"
    found = set()
    for *_, tx, ty in moves:
        target = position.cells.get((tx, ty))
        if target and (target.humans or getattr(target, enemy)):
            attackers = sum(m[2] for m in moves if m[3:] == (tx, ty))
            defenders = target.humans or getattr(target, enemy)
            p = win_probability(attackers, defenders, humans=bool(target.humans), rules_profile=RULES)
            found.add(f"({tx},{ty}): {attackers} vs {defenders} {'humains' if target.humans else 'ennemis'}, P(gain)={p:.3f}")
    return sorted(found)


def main(map_xml, p1_log, p2_log, *final):
    names = [Path(log).stem.rsplit("_", 1)[-1] for log in (p1_log, p2_log)]
    logs = [moves_of(p1_log), moves_of(p2_log)]
    plies = [(i % 2, logs[i % 2][i // 2]) for i in range(len(logs[0]) + len(logs[1]))]
    position = load_map(map_xml, rules_profile=RULES)
    for index, (side, (moves, seconds)) in enumerate(plies):
        following = plies[index + 1][1][0] if index + 1 < len(plies) else None
        for seed in range(2000):
            after = simulate_turn(position, moves, random.Random(seed))
            if following is not None and (get_outcome(after) is not None or not legal(after, following)):
                continue
            if following is None and final and counts(after)[:2] != tuple(map(int, final)):
                continue
            break
        else:
            print("!! no outcome consistent with the logs")
        v, w, h = counts(after)
        print(f"ply {index + 1:3} {names[side]:9} turn {index // 2 + 1:3} {moves} ({seconds} s)  -> V={v} W={w} H={h}")
        for battle in battles(position, moves):
            print("      battle", battle)
        print(show(after))
        position = after


if __name__ == "__main__":
    main(*sys.argv[1:])
