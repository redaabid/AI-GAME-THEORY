"""SUMMARY.md tables (results, AlphaBeta record, times per bot) from analysis.json: make_table.py ANALYSIS_JSON."""
import json
import sys

SPECIES = {"vampires": "Vampires", "werewolves": "Loups-garous"}
MAP_ORDER = {"thetrap.xml": 0, "testmap2.xml": 1}
OPP_ORDER = {"MCTS": 0, "OEP": 1, "Baseline": 2}


def fmt(t):
    return f"{t:.3f}"


def main(path):
    games = json.load(open(path, encoding="utf-8"))
    for g in games:
        g["opponent"] = g["second"] if g["first"] == "AlphaBeta" else g["first"]
    games.sort(key=lambda g: (g["max_plays"], MAP_ORDER[g["map"]], OPP_ORDER[g["opponent"]], g["first"] != "AlphaBeta"))
    print("| # | Match | Map | MaxPlays | Connexion (1er → 2e) | Rôle d'AlphaBeta | Vainqueur | Effectifs finaux | Fin | Demi-coups | AlphaBeta max / moy (s) | Adversaire max / moy (s) | Faults AB / adv |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for index, g in enumerate(games, 1):
        s, ab, op = g["server"], g["bots"]["AlphaBeta"], g["bots"][g["opponent"]]
        player = "P1, joue en 1er" if g["first_mover"] == "AlphaBeta" else "P2, joue en 2e"
        if " wins" in s["message"]:
            winner = f'**{s["message"].split(" wins")[0]}**'
        elif s["message"].startswith("No winner"):
            winner = "Égalité"
        else:
            winner = s["message"]
        counts = f'{s["p1"]} {s["p1_count"]} – {s["p2"]} {s["p2_count"]} (humains {s["humans"]})'
        if 0 in (s["p1_count"], s["p2_count"]):
            end = "élimination"
        elif g["plies"] >= g["max_plays"]:
            end = "MaxPlays"
        elif s["countdown"] == "00:00:00":
            end = "durée max"
        else:
            end = "?"
        faults = f'{ab["agent_fault"] + ab["fallback_true"]} / {op["agent_fault"] + op["fallback_true"]}'
        print(f'| {index} | AlphaBeta vs {g["opponent"]} | {g["map"]} | {g["max_plays"]} | {g["first"]} → {g["second"]} '
              f'| {SPECIES[ab["species"]]} ({player}) | {winner} | {counts} | {end} | {g["plies"]} '
              f'| {fmt(ab["max"])} / {fmt(ab["mean"])} | {fmt(op["max"])} / {fmt(op["mean"])} | {faults} |')
        g["outcome"] = ("N" if winner == "Égalité" else "V" if winner == "**AlphaBeta**" else "D")

    def record(keep):
        outcomes = [g["outcome"] for g in games if keep(g)]
        return f'{outcomes.count("V")} V, {outcomes.count("N")} N, {outcomes.count("D")} D'

    print(f"\nBilan d'AlphaBeta (V = victoire, N = nul, D = défaite) : **{record(lambda g: True)}**.\n")
    print("| | contre MCTS | contre OEP | contre Baseline |\n|---|---|---|---|")
    for map_name in MAP_ORDER:
        for plays in sorted({g["max_plays"] for g in games}):
            cells = [record(lambda g: (g["map"], g["max_plays"], g["opponent"]) == (map_name, plays, opponent))
                     for opponent in OPP_ORDER]
            print(f'| {map_name.removesuffix(".xml")}, {plays} | {" | ".join(cells)} |')

    print("\n| Bot | Parties | Coups | Max (s) | Moyenne (s) | Coups > 1.8 s | `Agent fault` | `fallback=True` "
          "| Lignes contenant « fallback » | Erreurs, exceptions, déconnexions |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name in ("AlphaBeta", *OPP_ORDER):
        bots = [g["bots"][name] for g in games if name in g["bots"]]
        turns = sum(b["turns"] for b in bots)
        top, mean = max(b["max"] for b in bots), sum(b["mean"] * b["turns"] for b in bots) / turns
        times = " | ".join("< 0.001" if t < 0.0005 else fmt(t) for t in (top, mean))
        lines = sum(b["fallback_lines"] for b in bots)
        if lines and not sum(b["fallback_true"] for b in bots):
            lines = f"{lines} (toutes `fallback=False`)"
        print(f'| {name} | {len(bots)} | {turns} | {times} | {sum(len(b["alerts"]) for b in bots)} '
              f'| {sum(b["agent_fault"] for b in bots)} | {sum(b["fallback_true"] for b in bots)} | {lines} '
              f'| {sum(len(b["problems"]) for b in bots)} |')


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
