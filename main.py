"""Run any registered agent: python main.py [--agent SPEC] [IP] [PORT].

SPEC is an agent name with optional parameters, e.g. mcts or mcts:iterations=256.
"""

import argparse
import logging
from math import isfinite
import time

import config
from client import ByeException, ClientSocket, EndException
from combat import DEFAULT_RULES_PROFILE, RULES_PROFILES
from game import GameState
from agents import TurnContext, available_agents, make_agent, parse_spec, safe_choose
from simulator import Position

LOGGER = logging.getLogger(__name__)


def play_game(args):
    state = GameState(rules_profile=args.rules_profile)
    agent = make_agent(args.agent)
    game_seed = args.seed
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
                game_seed += 1
                continue
            except ByeException:
                LOGGER.info("Server finished the session.")
                return
            started = time.perf_counter()
            state.apply_message(command, payload)
            if command == "map":
                LOGGER.info("Board: %s columns x %s rows; playing %s",
                            state.columns, state.rows, state.species)
                history, we_play_first = [], None
                try:
                    agent.new_game(Position.from_game_state(state), state.species, game_seed)
                except Exception as error:  # A model bug must not stop the client.
                    LOGGER.warning("Agent new_game failed: %s", error)
            elif command == "upd":
                if we_play_first is None:
                    # The first player receives an empty UPD right after MAP.
                    we_play_first = not payload
                ply = 2 * len(history) + (0 if we_play_first else 1)
                position = Position.from_game_state(state, ply=ply)
                context = TurnContext(started + args.move_time, args.max_plies, history)
                moves, fault = safe_choose(agent, position, context)
                history.append((position, moves))
                if fault:
                    LOGGER.warning("Agent fault, fallback move sent: %s", fault)
                if agent.info and "iterations" in agent.info:
                    LOGGER.info("Search: %s iterations; fallback=%s", agent.info["iterations"],
                                agent.info.get("fallback"))
                client.send_mov(len(moves), moves)
                LOGGER.info("Turn %s: %s (%.3f seconds)", state.turn, moves,
                            time.perf_counter() - started)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="AI-GAME-THEORY", help="ASCII name sent to the server")
    parser.add_argument("--rules-profile", choices=RULES_PROFILES, default=DEFAULT_RULES_PROFILE)
    parser.add_argument("--agent", default="baseline",
                        help=f"Agent spec, e.g. mcts:iterations=256. Available: {', '.join(available_agents())}")
    parser.add_argument("--move-time", type=float, default=1.5, help="Agent seconds per turn (maximum 1.8)")
    parser.add_argument("--iterations", type=int, default=10000,
                        help="MCTS iteration cap per turn, unless the spec sets iterations")
    parser.add_argument("--max-plies", type=int, default=200, help="Server MaxPlays, told to the agent")
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
        name, params = parse_spec(args.agent)
        if name in ("mcts", "mcts-memory") and "iterations" not in params:
            args.agent = f"{args.agent}{',' if ':' in args.agent else ':'}iterations={args.iterations}"
        make_agent(args.agent)
    except ValueError as error:
        parser.error(str(error))
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
