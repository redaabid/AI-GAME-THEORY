"""TCP client for the protocol in Projectv10.pdf, pages 5-8."""

import socket

import config


class EndException(Exception):
    """The game ended; another game may follow on this connection."""


class ByeException(Exception):
    """The server has finished using this connection."""


class ClientSocket:
    def __init__(self, ip=config.SERVER_IP, port=config.SERVER_PORT):
        self._socket = socket.create_connection((ip, port), timeout=10)
        # Waiting for the other player or the next turn is not our move timer.
        self._socket.settimeout(None)

    def _receive_exactly(self, length):
        data = bytearray()
        while len(data) < length:
            chunk = self._socket.recv(length - len(data))
            if not chunk:
                raise ConnectionError("Server closed the connection.")
            data.extend(chunk)
        return bytes(data)

    def get_message(self):
        command = self._receive_exactly(3)
        if command == b"END":
            raise EndException()
        if command == b"BYE":
            raise ByeException()
        if command in (b"SET", b"HME"):
            return command.decode().lower(), tuple(self._receive_exactly(2))
        if command in (b"HUM", b"MAP", b"UPD"):
            count = self._receive_exactly(1)[0]
            width = 2 if command == b"HUM" else 5
            data = self._receive_exactly(count * width)
            records = [tuple(data[i:i + width]) for i in range(0, len(data), width)]
            return command.decode().lower(), records
        raise ValueError(f"Unknown server command: {command!r}")

    def send_nme(self, name):
        encoded = name.encode("ascii")
        if not 1 <= len(encoded) <= 255:
            raise ValueError("The bot name must contain 1-255 ASCII characters.")
        self._socket.sendall(b"NME" + bytes([len(encoded)]) + encoded)

    def send_mov(self, nb_moves, moves):
        if nb_moves != len(moves) or not 1 <= nb_moves <= 255:
            raise ValueError("MOV needs a matching, nonzero move count (at most 255).")
        for move in moves:
            if len(move) != 5 or any(type(value) is not int or not 0 <= value <= 255
                                     for value in move):
                raise ValueError("Each move must contain five unsigned bytes.")
            if move[2] == 0:
                raise ValueError("A move must contain at least one creature.")
        self._socket.sendall(b"MOV" + bytes([nb_moves]) + b"".join(bytes(m) for m in moves))

    def close(self):
        self._socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
