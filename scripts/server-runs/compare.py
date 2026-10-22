"""AlphaBeta record before and after, from two analysis.json files: compare.py BEFORE_JSON AFTER_JSON."""
import json
import sys

MAP_ORDER = {"thetrap.xml": 0, "testmap2.xml": 1}
OPP_ORDER = {"MCTS": 0, "OEP": 1, "Baseline": 2}


def results(path):
    games = {}
    for g in json.load(open(path, encoding="utf-8")):
        opponent = g["second"] if g["first"] == "AlphaBeta" else g["first"]
        message = g["server"]["message"]
        if message.startswith("No winner"):
            outcome = "N"
        elif message.split(" wins")[0] == "AlphaBeta":
            outcome = "V"
        else:
            outcome = "D"
        games[g["tag"]] = {"map": g["map"].removesuffix(".xml"), "opponent": opponent,
                           "max_plays": g["max_plays"], "first": g["first"], "outcome": outcome}
    return games


def record(games, keep=lambda g: True):
    outcomes = [g["outcome"] for g in games.values() if keep(g)]
    return f'{outcomes.count("V")} V, {outcomes.count("N")} N, {outcomes.count("D")} D'


def main(before_path, after_path):
    before, after = results(before_path), results(after_path)
    if before.keys() != after.keys():
        sys.exit(f"Different games: {sorted(before.keys() ^ after.keys())}")
    print("| | Avant | Après |\n|---|---|---|")
    print(f"| **Total** | {record(before)} | {record(after)} |")
    rows = [("Map", "map", ["thetrap", "testmap2"]),
            ("Adversaire", "opponent", ["MCTS", "OEP", "Baseline"]),
            ("MaxPlays", "max_plays", [40, 200])]
    for title, field, values in rows:
        for value in values:
            keep = lambda g: g[field] == value
            print(f"| {title} {value} | {record(before, keep)} | {record(after, keep)} |")
    print()
    print("| Map, adversaire | Avant | Après |\n|---|---|---|")
    for map_name in ("thetrap", "testmap2"):
        for opponent in OPP_ORDER:
            keep = lambda g: (g["map"], g["opponent"]) == (map_name, opponent)
            print(f"| {map_name}, {opponent} | {record(before, keep)} | {record(after, keep)} |")
    print()
    print("| Partie | Avant | Après |\n|---|---|---|")
    order = sorted(before, key=lambda t: (before[t]["max_plays"], MAP_ORDER[before[t]["map"] + ".xml"],
                                          OPP_ORDER[before[t]["opponent"]], before[t]["first"] != "AlphaBeta"))
    for tag in order:
        changed = " ←" if before[tag]["outcome"] != after[tag]["outcome"] else ""
        print(f'| `{tag}` | {before[tag]["outcome"]} | {after[tag]["outcome"]}{changed} |')


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:])
