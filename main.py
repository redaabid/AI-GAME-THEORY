"""Run a baseline or MCTS bot: python main.py [--agent mcts] [IP] [PORT]."""

import argparse
import logging
from math import isfinite
import random
import time

import config
from client import ByeException, ClientSocket, EndException
from combat import DEFAULT_RULES_PROFILE, RULES_PROFILES
from game import GameState
from search import SearchConfig, search
from simulator import Position
from strategy import choose_moves

LOGGER = logging.getLogger(__name__)


def play_game(args):
    state = GameState(rules_profile=args.rules_profile)
    rng = random.Random(args.seed)
    with ClientSocket(args.ip, args.port) as client:
        client.send_nme(args.name)
        LOGGER.info("Connected to %s:%s as %s", args.ip, args.port, args.name)
        LOGGER.info("Rules profile: %s", args.rules_profile)
        LOGGER.info("Agent: %s", args.agent)
        while True:
            try:
                command, payload = client.get_message()
            except EndException:
                LOGGER.info("Game ended; waiting for the next game.")
                state = GameState(rules_profile=args.rules_profile)
                continue
            except ByeException:
                LOGGER.info("Server finished the session.")
                return
            started = time.perf_counter()
            state.apply_message(command, payload)
            if command == "map":
                LOGGER.info("Board: %s columns x %s rows; playing %s",
                            state.columns, state.rows, state.species)
            elif command == "upd":
                if args.agent == "mcts":
                    result = search(Position.from_game_state(state),
                                    config=SearchConfig(iterations=args.iterations), rng=rng,
                                    deadline=started + args.move_time)
                    moves = result.moves
                    LOGGER.info("Search: %s iterations; fallback=%s", result.iterations, result.fallback)
                else:
                    moves = choose_moves(state)
                client.send_mov(len(moves), moves)
                LOGGER.info("Turn %s: %s (%.3f seconds)", state.turn, moves,
                            time.perf_counter() - started)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="AI-GAME-THEORY", help="ASCII name sent to the server")
    parser.add_argument("--rules-profile", choices=RULES_PROFILES, default=DEFAULT_RULES_PROFILE)
    parser.add_argument("--agent", choices=("baseline", "mcts"), default="baseline")
    parser.add_argument("--move-time", type=float, default=1.5, help="MCTS seconds per turn (maximum 1.8)")
    parser.add_argument("--iterations", type=int, default=10000, help="MCTS iteration cap per turn")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("ip", nargs="?", default=config.SERVER_IP, help="Server IP or hostname")
    parser.add_argument("port", nargs="?", default=config.SERVER_PORT, type=int, help="Server TCP port")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if not isfinite(args.move_time) or not 0 < args.move_time <= 1.8:
        parser.error("move-time must be positive and at most 1.8 seconds")
    if args.iterations < 1:
        parser.error("iterations must be positive")
    try:
        encoded_name = args.name.encode("ascii")
    except UnicodeEncodeError:
        parser.error("name must use ASCII characters")
    if not 1 <= len(encoded_name) <= 255:
        parser.error("name must contain 1-255 ASCII characters")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        play_game(args)
    except KeyboardInterrupt:
        LOGGER.info("Stopped.")
    except (OSError, ValueError) as error:
        LOGGER.error("%s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
