"""Run the benchmark bot: python main.py [--name NAME] [IP] [PORT]."""

import argparse
import logging
import time

import config
from client import ByeException, ClientSocket, EndException
from game import GameState
from strategy import choose_moves

LOGGER = logging.getLogger(__name__)


def play_game(args):
    state = GameState()
    with ClientSocket(args.ip, args.port) as client:
        client.send_nme(args.name)
        LOGGER.info("Connected to %s:%s as %s", args.ip, args.port, args.name)
        while True:
            try:
                command, payload = client.get_message()
            except EndException:
                LOGGER.info("Game ended; waiting for the next game.")
                state = GameState()
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
                moves = choose_moves(state)
                client.send_mov(len(moves), moves)
                LOGGER.info("Turn %s: %s (%.3f seconds)", state.turn, moves,
                            time.perf_counter() - started)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="AI-GAME-THEORY", help="ASCII name sent to the server")
    parser.add_argument("ip", nargs="?", default=config.SERVER_IP, help="Server IP or hostname")
    parser.add_argument("port", nargs="?", default=config.SERVER_PORT, type=int, help="Server TCP port")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
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
