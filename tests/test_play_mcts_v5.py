"""V5 live entry point and a local reproduction of the opponent's ticket flow."""

from contextlib import ExitStack
from pathlib import Path
import socket
import subprocess
import sys
import threading
import unittest

from game import GameState
from scripts.play_mcts_v5 import client_arguments

ROOT = Path(__file__).resolve().parents[1]


def receive_exactly(connection, length):
    data = bytearray()
    while len(data) < length:
        chunk = connection.recv(length - len(data))
        if not chunk:
            raise AssertionError("Bot disconnected before the expected packet")
        data.extend(chunk)
    return bytes(data)


def packet(command, records):
    return command + bytes([len(records)]) + b"".join(bytes(record) for record in records)


class V5LiveTests(unittest.TestCase):
    def test_caps_and_agent_options_are_forwarded_without_consuming_connection_arguments(self):
        self.assertEqual(client_arguments(["host.example", "7000"]),
                         ["--agent", "mcts-v5:iterations=100000", "host.example", "7000"])
        self.assertEqual(client_arguments(["--iterations", "32", "--move-time", "0.2", "127.0.0.1", "5560"]),
                         ["--agent", "mcts-v5:iterations=32", "--move-time", "0.2", "127.0.0.1", "5560"])
        self.assertEqual(client_arguments(["--agent", "mcts-v5:feasibility=False,iterations=8",
                                           "--iterations", "32", "127.0.0.1", "5560"]),
                         ["--agent", "mcts-v5:feasibility=False,iterations=8", "127.0.0.1", "5560"])

    def test_invalid_parameters_fail_before_connecting(self):
        for options in (["--agent", "baseline"], ["--agent", "mcts-v5:feasibility=1"],
                        ["--iterations", "0"]):
            result = subprocess.run([sys.executable, "scripts/play_mcts_v5.py", *options],
                                    cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error:", result.stderr)
            self.assertNotIn("Connected to", result.stderr)

    def test_ticket_launcher_starts_v5_resets_species_and_exits_on_bye(self):
        # Reproduce the reviewed kit's two-port contract entirely on loopback.
        # No contact with the opponent, and no dependency on his private ZIP.
        with ExitStack() as stack:
            listener = stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(10)
            port = listener.getsockname()[1]
            tickets = stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            tickets.bind(("127.0.0.1", 0))
            tickets.listen(1)
            tickets.settimeout(10)
            ticket_port = tickets.getsockname()[1]
            errors = []
            moves_seen = []

            def serve():
                try:
                    with tickets.accept()[0] as ticket:
                        ticket.sendall(b"GO\n")
                    with listener.accept()[0] as connection:
                        connection.settimeout(5)
                        self.assertEqual(receive_exactly(connection, 3), b"NME")
                        size = receive_exactly(connection, 1)[0]
                        self.assertEqual(receive_exactly(connection, size), b"RemoteV5Test")
                        for species in ("vampires", "werewolves"):
                            records = [(0, 1, 0, 6, 0), (2, 1, 4, 0, 0), (4, 1, 0, 0, 6)]
                            if species == "werewolves":
                                records = [(x, y, h, w, v) for x, y, h, v, w in records]
                            state = GameState()
                            for command, payload in (("set", (3, 5)), ("hme", (0, 1)), ("map", records)):
                                state.apply_message(command, payload)
                            connection.sendall(b"SET\x03\x05" + packet(b"HUM", [(2, 1)])
                                               + b"HME\x00\x01" + packet(b"MAP", records)
                                               + packet(b"UPD", []))
                            self.assertEqual(receive_exactly(connection, 3), b"MOV")
                            count = receive_exactly(connection, 1)[0]
                            data = receive_exactly(connection, count * 5)
                            moves = [tuple(data[i:i+5]) for i in range(0, len(data), 5)]
                            state.validate_moves(moves)
                            self.assertTrue(moves)
                            moves_seen.append((state.species, moves))
                            connection.sendall(b"END")
                        connection.sendall(b"BYE")
                    with tickets.accept()[0] as ticket:
                        ticket.sendall(b"DONE\n")
                except Exception as error:
                    errors.append(error)

            worker = threading.Thread(target=serve, daemon=True)
            worker.start()
            # Model the kit: receive GO, append host/game-port, launch one bot;
            # wait for it to exit, then request the next ticket.
            with socket.create_connection(("127.0.0.1", ticket_port), timeout=5) as ticket:
                self.assertEqual(ticket.recv(16).strip(), b"GO")
            command = [sys.executable, "scripts/play_mcts_v5.py", "--name", "RemoteV5Test",
                       "--iterations", "16", "--move-time", "0.2", "--max-plies", "200"]
            result = subprocess.run(command + ["127.0.0.1", str(port)], cwd=ROOT,
                                    capture_output=True, text=True, timeout=10)
            with socket.create_connection(("127.0.0.1", ticket_port), timeout=5) as ticket:
                self.assertEqual(ticket.recv(16).strip(), b"DONE")
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive())
            if errors:
                raise errors[0]
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([species for species, _ in moves_seen], ["vampires", "werewolves"])
            self.assertIn("Agent: mcts-v5:iterations=16", result.stderr)
            self.assertIn("Server finished the session", result.stderr)
            self.assertNotIn("Agent fault", result.stderr)
            self.assertNotIn("new_game failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
