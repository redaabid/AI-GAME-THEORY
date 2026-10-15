"""Protocol, rule, strategy, and command-line checks using the standard library."""

from pathlib import Path
import socket
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from client import ByeException, ClientSocket, EndException
from game import Cell, GameState, distance
from strategy import choose_moves, win_probability

ROOT = Path(__file__).resolve().parents[1]


def board(records, *, rows=5, columns=7, home=(0, 0)):
    state = GameState()
    state.apply_message("set", (rows, columns))
    state.apply_message("hme", home)
    state.apply_message("map", records)
    return state


def receive_exactly(connection, length):
    data = bytearray()
    while len(data) < length:
        chunk = connection.recv(length - len(data))
        if not chunk:
            raise AssertionError("Bot disconnected before sending the expected packet.")
        data.extend(chunk)
    return bytes(data)


def packet(command, records):
    return command + bytes([len(records)]) + b"".join(bytes(record) for record in records)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        player, self.server = socket.socketpair()
        self.addCleanup(self.server.close)
        with patch("client.socket.create_connection", return_value=player):
            self.client = ClientSocket()
        self.addCleanup(self.client.close)
        self.server.settimeout(2)

    def test_fragmented_and_coalesced_packets(self):
        def send_fragments():
            for fragment in (b"S", b"ET\x03", b"\x05H", b"ME\x04\x02", b"UPD\x00"):
                self.server.sendall(fragment)

        sender = threading.Thread(target=send_fragments)
        sender.start()
        self.assertEqual(self.client.get_message(), ("set", (3, 5)))
        self.assertEqual(self.client.get_message(), ("hme", (4, 2)))
        self.assertEqual(self.client.get_message(), ("upd", []))
        sender.join(timeout=2)
        self.assertFalse(sender.is_alive())

    def test_houses_and_five_byte_updates(self):
        self.server.sendall(packet(b"HUM", [(2, 1), (4, 2)])
                            + packet(b"MAP", [(2, 1, 4, 0, 0), (0, 0, 0, 5, 0)])
                            + packet(b"UPD", [(2, 1, 0, 9, 0)]))
        self.assertEqual(self.client.get_message(), ("hum", [(2, 1), (4, 2)]))
        self.assertEqual(self.client.get_message()[1][0], (2, 1, 4, 0, 0))
        self.assertEqual(self.client.get_message(), ("upd", [(2, 1, 0, 9, 0)]))

    def test_game_and_session_endings(self):
        self.server.sendall(b"ENDBYE")
        with self.assertRaises(EndException):
            self.client.get_message()
        with self.assertRaises(ByeException):
            self.client.get_message()

    def test_eof_mid_packet_does_not_loop(self):
        self.server.sendall(b"MAP\x01\x00")
        self.server.shutdown(socket.SHUT_WR)
        with self.assertRaises(ConnectionError):
            self.client.get_message()

    def test_unknown_command(self):
        self.server.sendall(b"BAD")
        with self.assertRaises(ValueError):
            self.client.get_message()

    def test_outgoing_packets(self):
        self.client.send_nme("Team")
        self.assertEqual(receive_exactly(self.server, 8), b"NME\x04Team")
        self.client.send_mov(1, [(1, 2, 9, 2, 3)])
        self.assertEqual(receive_exactly(self.server, 9), b"MOV\x01\x01\x02\x09\x02\x03")

    def test_invalid_outgoing_values(self):
        for name in ("", "x" * 256, "\u00e9"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.client.send_nme(name)
        for count, moves in ((0, []), (2, [(0, 0, 1, 1, 0)]),
                             (1, [(0, 0, 0, 1, 0)]), (1, [(0, 0, 256, 1, 0)])):
            with self.subTest(moves=moves), self.assertRaises(ValueError):
                self.client.send_mov(count, moves)


class BoardTests(unittest.TestCase):
    def test_rectangular_board_and_species(self):
        state = board([(6, 2, 0, 0, 5)], rows=3, columns=7, home=(6, 2))
        self.assertEqual(state.species, "werewolves")
        self.assertEqual(state.enemy_species, "vampires")
        self.assertEqual(set(state.neighbors((6, 2))), {(5, 1), (5, 2), (6, 1)})
        self.assertFalse(state.in_bounds((2, 6)))
        self.assertEqual(distance((0, 0), (6, 2)), 6)

    def test_updates_replace_populations_and_clear_empty_cells(self):
        state = board([(0, 0, 0, 5, 0), (1, 1, 3, 0, 0)])
        state.apply_message("upd", [(0, 0, 0, 0, 0), (1, 1, 0, 8, 0)])
        self.assertNotIn((0, 0), state.cells)
        self.assertEqual(state.cells[(1, 1)], Cell(vampires=8))
        self.assertEqual(state.species, "vampires")

    def test_set_resets_previous_game(self):
        state = board([(0, 0, 0, 5, 0)])
        state.apply_message("set", (2, 3))
        self.assertEqual(state.cells, {})
        self.assertIsNone(state.species)
        self.assertIsNone(state.home)
        self.assertEqual(state.turn, 0)

    def test_invalid_update_is_atomic(self):
        state = board([(0, 0, 0, 5, 0)])
        before = state.cells.copy()
        with self.assertRaises(ValueError):
            state.apply_message("upd", [(0, 0, 0, 0, 0), (7, 0, 1, 0, 0)])
        self.assertEqual(state.cells, before)
        with self.assertRaises(ValueError):
            Cell(humans=2, vampires=3)

    def test_update_before_initialization(self):
        with self.assertRaises(ValueError):
            GameState().apply_message("upd", [])

    def test_legal_merge(self):
        state = board([(0, 0, 0, 5, 0), (1, 1, 0, 4, 0)])
        state.validate_moves([(0, 0, 5, 1, 1)])

    def test_illegal_movements(self):
        state = board([(0, 0, 0, 5, 0), (1, 1, 0, 4, 0), (4, 4, 0, 0, 6)])
        invalid = [[], [(0, 0, 0, 1, 0)], [(0, 0, 6, 1, 0)],
                   [(4, 4, 1, 3, 3)], [(0, 0, 5, 0, 0)], [(0, 0, 5, 2, 0)],
                   [(0, 0, 5, -1, 0)], [(0, 0, 3, 1, 0), (0, 0, 3, 0, 1)],
                   [(0, 0, 5, 1, 1), (1, 1, 4, 2, 2)]]
        for moves in invalid:
            with self.subTest(moves=moves), self.assertRaises(ValueError):
                state.validate_moves(moves)


class StrategyTests(unittest.TestCase):
    def test_battle_thresholds_and_random_probabilities(self):
        cases = [(6, 6, True, 1), (4, 8, True, 0.25),
                 (15, 10, False, 1), (10, 15, False, 0),
                 (10, 10, False, 0.5), (12, 10, False, 0.7), (10, 12, False, 10 / 24)]
        for attackers, defenders, humans, expected in cases:
            with self.subTest(attackers=attackers, defenders=defenders, humans=humans):
                self.assertAlmostEqual(win_probability(attackers, defenders, humans=humans), expected)

    def test_captures_affordable_humans(self):
        state = board([(0, 0, 0, 5, 0), (1, 1, 4, 0, 0), (6, 4, 0, 0, 4)])
        self.assertEqual(choose_moves(state), [(0, 0, 5, 1, 1)])

    def test_avoids_immediate_enemy_counterattack(self):
        # The nearest village would give us six units, exposed to ten enemies.
        state = board([(2, 2, 0, 5, 0), (3, 2, 1, 0, 0), (4, 2, 0, 0, 10)], home=(2, 2))
        move = choose_moves(state)[0]
        self.assertNotEqual(move[3:], (3, 2))
        self.assertGreater(distance(move[3:], (4, 2)), 1)

    def test_takes_guaranteed_enemy_victory(self):
        state = board([(0, 0, 0, 15, 0), (1, 0, 0, 0, 10)])
        self.assertEqual(choose_moves(state), [(0, 0, 15, 1, 0)])

    def test_both_species_have_legal_fallback_moves(self):
        for species in ("vampires", "werewolves"):
            own = (0, 0, 0, 2, 0) if species == "vampires" else (0, 0, 0, 0, 2)
            state = board([own, (1, 0, 20, 0, 0), (0, 1, 20, 0, 0), (1, 1, 20, 0, 0)],
                          rows=2, columns=2)
            moves = choose_moves(state)
            state.validate_moves(moves)
            self.assertEqual(moves[0][2], 2)


class CommandLineTests(unittest.TestCase):
    def run_session(self, serve):
        errors = []
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(5)
            port = listener.getsockname()[1]

            def server():
                try:
                    connection, _ = listener.accept()
                    with connection:
                        connection.settimeout(2)
                        self.assertEqual(receive_exactly(connection, 3), b"NME")
                        length = receive_exactly(connection, 1)[0]
                        self.assertEqual(receive_exactly(connection, length), b"SmokeTest")
                        serve(connection)
                except Exception as error:
                    errors.append(error)

            worker = threading.Thread(target=server, daemon=True)
            worker.start()
            result = subprocess.run(
                [sys.executable, "main.py", "--name", "SmokeTest", "127.0.0.1", str(port)],
                cwd=ROOT, capture_output=True, text=True, timeout=10,
            )
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive(), "Mock server did not finish.")
            if errors:
                raise errors[0]
            return result

    def receive_move(self, connection, state):
        self.assertEqual(receive_exactly(connection, 3), b"MOV")
        count = receive_exactly(connection, 1)[0]
        data = receive_exactly(connection, count * 5)
        moves = [tuple(data[i:i + 5]) for i in range(0, len(data), 5)]
        state.validate_moves(moves)
        return moves[0]

    def test_real_tcp_game_updates_reset_and_species_change(self):
        def serve(connection):
            state = board([(0, 1, 0, 0, 5), (2, 1, 3, 0, 0), (4, 1, 0, 4, 0)],
                          rows=3, columns=5, home=(0, 1))
            connection.sendall(b"SET\x03\x05" + packet(b"HUM", [(2, 1)]) + b"HME\x00\x01"
                               + packet(b"MAP", [(0, 1, 0, 0, 5), (2, 1, 3, 0, 0), (4, 1, 0, 4, 0)])
                               + packet(b"UPD", []))
            x, y, count, tx, ty = self.receive_move(connection, state)
            self.assertEqual(state.cells.get((tx, ty), Cell()), Cell())
            updates = [(x, y, 0, 0, 0), (tx, ty, 0, 0, count),
                       (4, 1, 0, 0, 0), (3, 1, 0, 4, 0)]
            state.apply_message("upd", updates)
            connection.sendall(packet(b"UPD", updates))
            self.receive_move(connection, state)

            # Another game on the same connection assigns us the opposite species.
            records = [(1, 1, 0, 6, 0), (2, 1, 2, 0, 0), (3, 2, 0, 0, 3)]
            state = board(records, rows=3, columns=4, home=(1, 1))
            connection.sendall(b"ENDSET\x03\x04" + packet(b"HUM", [(2, 1)]) + b"HME\x01\x01"
                               + packet(b"MAP", records) + packet(b"UPD", []))
            move = self.receive_move(connection, state)
            self.assertEqual(move[:3], (1, 1, 6))
            connection.sendall(b"ENDBYE")

        result = self.run_session(serve)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("playing werewolves", result.stderr)
        self.assertIn("playing vampires", result.stderr)
        self.assertIn("Server finished the session", result.stderr)

    def test_unexpected_disconnect_exits_with_clear_error(self):
        def serve(connection):
            connection.sendall(b"MA")

        result = self.run_session(serve)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Server closed the connection", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_arguments_do_not_attempt_a_connection(self):
        for arguments in (["127.0.0.1", "70000"], ["--name", "\u00e9"]):
            result = subprocess.run([sys.executable, "main.py", *arguments], cwd=ROOT,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 2, result.stderr)


if __name__ == "__main__":
    unittest.main()
