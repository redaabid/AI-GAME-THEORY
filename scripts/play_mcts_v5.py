"""Run V5 through the course TCP protocol, including remote benchmark launchers.

    python scripts/play_mcts_v5.py --move-time 1.5 HOST_IP 7000

The final IP and port arguments and all ordinary client options go to main.py.
V5 defaults to 100,000 iterations, bounded by the client's thinking deadline.
This separate entry point preserves existing CPU-campaign source fingerprints.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.mcts_v5  # Explicit registration; ordinary main.py stays intact.
from agents import make_agent, parse_spec
from main import main as client_main


def client_arguments(argv):
    """Select V5 and honor both --iterations and an explicit agent-spec cap."""
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--agent", default="mcts-v5")
    parser.add_argument("--iterations", type=int, default=100000)
    options, remaining = parser.parse_known_args(argv)
    if options.iterations < 1:
        parser.error("iterations must be positive")
    name, params = parse_spec(options.agent)
    if name != "mcts-v5":
        parser.error("This entry point runs mcts-v5; use main.py for other agents.")
    spec = options.agent
    if "iterations" not in params:
        spec += f"{',' if ':' in spec else ':'}iterations={options.iterations}"
    try:
        make_agent(spec)
    except ValueError as error:
        parser.error(str(error))
    return ["--agent", spec, *remaining]


def main(argv=None):
    return client_main(client_arguments(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
