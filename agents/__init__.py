"""Shared agent interface, registry, and safety net for every model we compare.

An agent receives an immutable simulator Position (its own species is
position.to_play) and returns one legal turn: a list of (x, y, count, tx, ty)
moves. The same object plays live on the server (main.py), in CPU matches, and
in the round-robin tournament (tournament.py), so results are comparable.

Add a model by creating agents/<name>.py with a decorated subclass:

    from agents import Agent, register

    @register("alphabeta")
    class AlphaBeta(Agent):
        def __init__(self, depth=4):
            self.depth = depth

        def choose_moves(self, position, context):
            ...

Modules in this package are discovered automatically. Variants are selected
with a spec string, for example "alphabeta:depth=6" or "mcts:iterations=256".
"""

from ast import literal_eval
from dataclasses import dataclass, field
import importlib
import pkgutil
import time

from candidates import first_supported_move, supported_turn
from strategy import choose_moves as greedy_moves

_REGISTRY = {}
_DISCOVERED = False


@dataclass
class TurnContext:
    """What an agent knows besides the board.

    deadline is a time.perf_counter() value already including the safety margin,
    or None for untimed, reproducible matches. history lists this agent's own
    previous turns as (position, moves), oldest first; moves is [] for a turn
    lost to a timeout. Opponent moves are not sent by the server: infer them by
    comparing a position with the next one. Ply counts both players' turns.
    """

    deadline: float | None
    max_plies: int | None
    history: list = field(default_factory=list)

    def time_left(self):
        return float("inf") if self.deadline is None else self.deadline - time.perf_counter()


class Agent:
    """Base class. Override choose_moves; override new_game to keep game memory."""

    name = "agent"
    info = None  # Optional per-turn dict for logs, e.g. {"iterations": 812}.

    def new_game(self, position, species, seed):
        """Called before each game, with the initial board and our species."""

    def choose_moves(self, position, context):
        raise NotImplementedError


def register(name):
    def decorator(cls):
        if name in _REGISTRY and _REGISTRY[name] is not cls:
            raise ValueError(f"Agent name already registered: {name}")
        cls.name = name
        _REGISTRY[name] = cls
        return cls
    return decorator


def _discover():
    global _DISCOVERED
    if not _DISCOVERED:
        _DISCOVERED = True
        for module in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
            importlib.import_module(f"{__name__}.{module.name}")


def available_agents():
    _discover()
    return sorted(_REGISTRY)


def parse_spec(spec):
    """'mcts:iterations=256,exploration=1.0' -> ('mcts', {...}). Values are Python literals."""
    name, _, raw = spec.partition(":")
    params = {}
    for item in filter(None, (part.strip() for part in raw.split(","))):
        key, sep, value = item.partition("=")
        if not sep or not key.strip().isidentifier():
            raise ValueError(f"Bad agent parameter {item!r} in {spec!r}; use key=value.")
        try:
            params[key.strip()] = literal_eval(value.strip())
        except (ValueError, SyntaxError):
            params[key.strip()] = value.strip()
    return name.strip(), params


def make_agent(spec):
    _discover()
    name, params = parse_spec(spec)
    if name not in _REGISTRY:
        raise ValueError(f"Unknown agent {name!r}. Available: {', '.join(available_agents())}")
    try:
        return _REGISTRY[name](**params)
    except TypeError as error:
        raise ValueError(f"Bad parameters for agent {name!r}: {error}") from None


def fallback_moves(position):
    """Greedy whole-group move, or the first supported move if that fails."""
    view = position.to_game_state()
    try:
        moves = greedy_moves(view)
        if supported_turn(view, moves):
            return moves
    except (ValueError, TimeoutError):
        pass
    return first_supported_move(view)


def safe_choose(agent, position, context):
    """Never let a model crash or send an illegal turn (brief: failure caps the grade).

    Returns (moves, fault); fault is None, or a short reason when the fallback was used.
    """
    try:
        moves = agent.choose_moves(position, context)
        moves = [tuple(int(n) for n in move) for move in moves]
        if supported_turn(position.to_game_state(), moves):
            return moves, None
        fault = f"illegal turn {moves}"
    except Exception as error:  # Any model bug must still produce a move.
        fault = f"{type(error).__name__}: {error}"
    return fallback_moves(position), fault
