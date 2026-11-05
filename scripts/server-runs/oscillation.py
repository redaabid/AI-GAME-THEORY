"""Longest run of 2-periodic turns (move N == move N-2) per bot log: oscillation.py LOG_OR_GLOB..."""
import glob, os, re, sys
paths = [p for arg in sys.argv[1:] for p in sorted(glob.glob(arg))]
if not paths:
    sys.exit("No log matches.")
for path in paths:
    moves = [m.group(1) for m in (re.match(r"INFO: Turn \d+: (.*) \(", l) for l in open(path)) if m]
    best, start, run_start = (0, 0, 0), None, None
    for i in range(2, len(moves)):
        if moves[i] == moves[i - 2]:
            run_start = i - 2 if run_start is None else run_start
            length = i - run_start + 1
            if length > best[0]:
                best = (length, run_start + 1, i + 1)
        else:
            run_start = None
    print(f"{os.path.basename(path):60} turns={len(moves):3} longest 2-cycle: {best[0]:3} turns (turn {best[1]}-{best[2]})")
