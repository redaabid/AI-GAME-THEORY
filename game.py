"""Board updates and movement rules, independent of networking or strategy."""

from dataclasses import dataclass

from combat import DEFAULT_RULES_PROFILE, RULES_PROFILES


@dataclass(frozen=True)
class Cell:
    humans: int = 0
    vampires: int = 0
    werewolves: int = 0

    def __post_init__(self):
        counts = (self.humans, self.vampires, self.werewolves)
        if any(type(n) is not int or not 0 <= n <= 255 for n in counts):
            raise ValueError("Cell populations must be unsigned bytes.")
        if sum(n > 0 for n in counts) > 1:
            raise ValueError("A cell cannot contain multiple species.")


def distance(first, second):
    """Minimum number of eight-direction moves between two cells."""
    return max(abs(first[0] - second[0]), abs(first[1] - second[1]))


class GameState:
    def __init__(self, *, rules_profile=DEFAULT_RULES_PROFILE):
        if rules_profile not in RULES_PROFILES:
            raise ValueError("Unknown battle rules profile.")
        self.rules_profile = rules_profile
        self.rows = 0
        self.columns = 0
        self.home = None
        self.species = None
        self.houses = set()
        self.cells = {}
        self.turn = 0

    def in_bounds(self, position):
        x, y = position
        return 0 <= x < self.columns and 0 <= y < self.rows

    def neighbors(self, position):
        x, y = position
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                target = (x + dx, y + dy)
                if (dx or dy) and self.in_bounds(target):
                    yield target

    def groups(self, species=None):
        kind = species or self.species
        if kind not in ("vampires", "werewolves", "humans"):
            raise ValueError("Our species is not known yet.")
        return [(position, getattr(cell, kind)) for position, cell in self.cells.items()
                if getattr(cell, kind)]

    @property
    def enemy_species(self):
        if self.species is None:
            raise ValueError("Our species is not known yet.")
        return "werewolves" if self.species == "vampires" else "vampires"

    def apply_message(self, command, payload):
        if command == "set":
            rows, columns = payload
            if not 1 <= rows <= 255 or not 1 <= columns <= 255:
                raise ValueError("Board dimensions must be between 1 and 255.")
            self.__init__(rules_profile=self.rules_profile)
            self.rows, self.columns = rows, columns
        elif command == "hum":
            if any(not self.in_bounds(position) for position in payload):
                raise ValueError("A human house is outside the board.")
            self.houses = set(payload)
        elif command == "hme":
            if not self.in_bounds(payload):
                raise ValueError("Our starting position is outside the board.")
            self.home = tuple(payload)
        elif command in ("map", "upd"):
            if command == "upd" and self.species is None:
                raise ValueError("Received UPD before the initial board.")
            updates = {}
            for x, y, humans, vampires, werewolves in payload:
                if not self.in_bounds((x, y)):
                    raise ValueError("A board update is outside the board.")
                updates[(x, y)] = Cell(humans, vampires, werewolves)
            if command == "map":
                home = updates.get(self.home, Cell())
                if not (home.vampires or home.werewolves):
                    raise ValueError("MAP does not contain our starting group.")
                self.cells.clear()
                self.species = "vampires" if home.vampires else "werewolves"
            for position, cell in updates.items():
                if cell == Cell():
                    self.cells.pop(position, None)
                else:
                    self.cells[position] = cell
            if command == "upd":
                self.turn += 1
        else:
            raise ValueError(f"Unexpected board command: {command}")

    def validate_moves(self, moves):
        if self.species not in ("vampires", "werewolves"):
            raise ValueError("Our species is not known yet.")
        # Server v3.2.1 accepts multiple moves from a single group (splitting).
        if not 1 <= len(moves) <= 255:
            raise ValueError("Send between 1 and 255 moves.")
        sources, targets, outgoing = set(), set(), {}
        for move in moves:
            if len(move) != 5 or any(type(n) is not int or not 0 <= n <= 255 for n in move):
                raise ValueError("Each move must contain five unsigned bytes.")
            x, y, count, target_x, target_y = move
            source, target = (x, y), (target_x, target_y)
            if not self.in_bounds(source) or not self.in_bounds(target):
                raise ValueError("A move is outside the board.")
            if distance(source, target) != 1:
                raise ValueError("A move must go to an adjacent cell.")
            available = getattr(self.cells.get(source, Cell()), self.species)
            outgoing[source] = outgoing.get(source, 0) + count
            if count == 0 or outgoing[source] > available:
                raise ValueError("A move must use available creatures of our species.")
            sources.add(source)
            targets.add(target)
        if sources & targets:
            raise ValueError("A cell cannot be both source and target in one turn.")
