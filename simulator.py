"""CPU-only, functional game transitions for search and offline data generation."""

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
import xml.etree.ElementTree as ET

from combat import DEFAULT_RULES_PROFILE, RULES_PROFILES, sample_battle
from game import Cell, GameState

SPECIES = ("vampires", "werewolves")
SCHEMA_VERSION = 1


def opponent(species):
    if species not in SPECIES:
        raise ValueError("The player must be vampires or werewolves.")
    return SPECIES[1] if species == SPECIES[0] else SPECIES[0]


@dataclass(frozen=True)
class Position:
    """Immutable board snapshot. Coordinates are (x, y); cells are frozen Cells."""

    rows: int
    columns: int
    cells: Mapping[tuple[int, int], Cell]
    to_play: str = "vampires"
    ply: int = 0
    rules_profile: str = DEFAULT_RULES_PROFILE

    def __post_init__(self):
        if any(type(n) is not int or not 1 <= n <= 255 for n in (self.rows, self.columns)):
            raise ValueError("Board dimensions must be integers between 1 and 255.")
        opponent(self.to_play)
        if self.rules_profile not in RULES_PROFILES:
            raise ValueError("Unknown battle rules profile.")
        if type(self.ply) is not int or self.ply < 0:
            raise ValueError("The ply count must be a nonnegative integer.")
        snapshot = {}
        for coordinate, cell in self.cells.items():
            if (not isinstance(coordinate, tuple) or len(coordinate) != 2
                    or any(type(n) is not int for n in coordinate)):
                raise ValueError("Coordinates must be integer (x, y) tuples.")
            x, y = coordinate
            if not (0 <= x < self.columns and 0 <= y < self.rows):
                raise ValueError("A cell is outside the board.")
            if not isinstance(cell, Cell):
                raise ValueError("Board values must be Cells.")
            if cell != Cell():
                snapshot[coordinate] = cell
        object.__setattr__(self, "cells", MappingProxyType(snapshot))

    @classmethod
    def from_game_state(cls, state, *, to_play=None, ply=0, rules_profile=None):
        # Network state.turn counts our UPDs, not both players' plies.
        profile = state.rules_profile if rules_profile is None else rules_profile
        return cls(state.rows, state.columns, state.cells, to_play or state.species, ply, profile)

    def to_game_state(self):
        """Return an independent, mutable view for the current benchmark agent."""
        state = GameState(rules_profile=self.rules_profile)
        state.rows, state.columns = self.rows, self.columns
        state.species = self.to_play
        state.cells = dict(self.cells)
        state.houses = {p for p, cell in self.cells.items() if cell.humans}
        state.turn = self.ply
        return state

    def to_dict(self):
        """Portable JSON-compatible state, shared with the offline trainer."""
        return {
            "schema_version": SCHEMA_VERSION,
            "rows": self.rows, "columns": self.columns,
            "to_play": self.to_play, "ply": self.ply,
            "rules_profile": self.rules_profile,
            "cells": [[x, y, cell.humans, cell.vampires, cell.werewolves]
                      for (x, y), cell in sorted(self.cells.items())],
        }

    @classmethod
    def from_dict(cls, data):
        if type(data.get("schema_version")) is not int or data["schema_version"] != SCHEMA_VERSION:
            raise ValueError("Unsupported position schema version.")
        cells = {}
        for x, y, humans, vampires, werewolves in data["cells"]:
            if (x, y) in cells:
                raise ValueError("A serialized position has duplicate coordinates.")
            cells[(x, y)] = Cell(humans, vampires, werewolves)
        return cls(data["rows"], data["columns"], cells, data["to_play"], data["ply"], data["rules_profile"])


@dataclass(frozen=True)
class Outcome:
    winner: str | None
    reason: str

    def value_for(self, species):
        opponent(species)
        return 0 if self.winner is None else (1 if self.winner == species else -1)


def get_outcome(position, *, max_plies=None):
    """Return None for ongoing play, or an Outcome (winner=None means a draw)."""
    if max_plies is not None and (type(max_plies) is not int or max_plies < 1):
        raise ValueError("max_plies must be a positive integer.")
    vampires = sum(cell.vampires for cell in position.cells.values())
    werewolves = sum(cell.werewolves for cell in position.cells.values())
    if vampires == 0 or werewolves == 0:
        winner = None if vampires == werewolves else ("vampires" if vampires else "werewolves")
        return Outcome(winner, "elimination")
    if max_plies is not None and position.ply >= max_plies:
        winner = None if vampires == werewolves else ("vampires" if vampires > werewolves else "werewolves")
        return Outcome(winner, "ply_limit")
    return None


def simulate_turn(position, moves, rng):
    """Apply an entire legal turn without changing the input Position.

    Debit all sources, combine arrivals at each destination, then resolve each
    destination once. Sorted destinations make seeded results independent of
    move-list order. Populations beyond the one-byte protocol are rejected.
    """
    if get_outcome(position) is not None:
        raise ValueError("Cannot move after the game has ended.")
    view = position.to_game_state()
    view.validate_moves(moves)
    outgoing, incoming = {}, {}
    for x, y, count, target_x, target_y in moves:
        outgoing[(x, y)] = outgoing.get((x, y), 0) + count
        incoming[(target_x, target_y)] = incoming.get((target_x, target_y), 0) + count

    actor = position.to_play
    for target, count in incoming.items():
        cell = position.cells.get(target, Cell())
        possible_stack = count + getattr(cell, actor) + cell.humans
        if possible_stack > 255:
            raise ValueError("A possible resulting stack exceeds the 255-creature protocol limit.")

    cells = dict(position.cells)
    for source, count in outgoing.items():
        remaining = getattr(cells[source], actor) - count
        if remaining:
            cells[source] = Cell(**{actor: remaining})
        else:
            del cells[source]

    for target, count in sorted(incoming.items()):
        cell = cells.get(target, Cell())
        if cell == Cell() or getattr(cell, actor):
            replacement = Cell(**{actor: count + getattr(cell, actor)})
        else:
            humans = bool(cell.humans)
            defending_species = "humans" if humans else opponent(actor)
            battle = sample_battle(count, getattr(cell, defending_species), rng, humans=humans,
                                   rules_profile=position.rules_profile)
            winner = actor if battle.attacker_won else defending_species
            replacement = Cell(**{winner: battle.survivors})
        if replacement == Cell():
            cells.pop(target, None)
        else:
            cells[target] = replacement
    return Position(position.rows, position.columns, cells, opponent(actor), position.ply + 1,
                    position.rules_profile)


def full_group_actions(position):
    """Small baseline action set: one whole group moves one step per turn.

    This candidate set is not an enumeration of all partial/split/joint turns.
    simulate_turn and the shared validator support those larger turn plans.
    """
    if get_outcome(position) is not None:
        return []
    view = position.to_game_state()
    return [[(source[0], source[1], count, target[0], target[1])]
            for source, count in sorted(view.groups()) for target in view.neighbors(source)]


def load_map(path, *, to_play="vampires", rules_profile=DEFAULT_RULES_PROFILE):
    """Load the course XML map format without a server or Windows dependency."""
    root = ET.parse(Path(path)).getroot()
    if root.tag != "Map":
        raise ValueError("Expected an XML Map element.")
    kinds = {"Humans": "humans", "Vampires": "vampires", "Werewolves": "werewolves"}
    cells = {}
    for entry in root:
        if entry.tag not in kinds:
            raise ValueError(f"Unknown map element: {entry.tag}")
        coordinate = (int(entry.attrib["X"]), int(entry.attrib["Y"]))
        if coordinate in cells:
            raise ValueError("A map has duplicate coordinates.")
        cells[coordinate] = Cell(**{kinds[entry.tag]: int(entry.attrib["Count"])})
    return Position(int(root.attrib["Rows"]), int(root.attrib["Columns"]), cells,
                    to_play=to_play, rules_profile=rules_profile)
