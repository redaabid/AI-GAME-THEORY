"""Generate fair random maps in the course XML format (MapGenerator.exe is Windows-only).

Maps are point-symmetric: the cell (x, y) mirrors (columns-1-x, rows-1-y), and
werewolves start on the mirror of the vampires. Neither side has a positional
advantage, so match scores measure the agents. Train, validation, and test maps
use disjoint seed ranges: tune on train, select on validation, report on test.
"""

import argparse
from pathlib import Path
import random
import xml.etree.ElementTree as ET

from game import Cell
from simulator import Position

FAMILIES = {
    # (rows range, columns range, human group pairs range, start range, max humans per group)
    "small": ((4, 7), (5, 10), (2, 4), (4, 10), 6),
    "medium": ((7, 12), (10, 16), (3, 7), (6, 14), 10),
    "large": ((12, 20), (16, 30), (5, 10), (8, 16), 14),
}
SPLIT_OFFSETS = {"train": 0, "val": 1_000_000, "test": 2_000_000}
POPULATION_LIMIT = 255  # Keeps every possible merge within the one-byte protocol.


def mirror(cell, rows, columns):
    return columns - 1 - cell[0], rows - 1 - cell[1]


def random_map(rng, family="medium", *, to_play="vampires"):
    (r0, r1), (c0, c1), (h0, h1), (s0, s1), max_humans = FAMILIES[family]
    rows, columns = rng.randint(r0, r1), rng.randint(c0, c1)
    start = rng.randint(s0, s1)
    # Cells strictly before their mirror image in reading order; the centre maps to itself.
    half = [(x, y) for y in range(rows) for x in range(columns)
            if (y, x) < tuple(reversed(mirror((x, y), rows, columns)))]
    rng.shuffle(half)
    home = half.pop()
    cells = {home: Cell(vampires=start), mirror(home, rows, columns): Cell(werewolves=start)}
    budget = POPULATION_LIMIT - 2 * start
    for cell in half[:rng.randint(h0, h1)]:
        humans = min(rng.randint(1, max_humans), budget // 2)
        if humans < 1:
            break
        cells[cell] = cells[mirror(cell, rows, columns)] = Cell(humans=humans)
        budget -= 2 * humans
    centre = ((columns - 1) // 2, (rows - 1) // 2)
    if rows % 2 and columns % 2 and centre not in cells and budget > 0 and rng.random() < 0.5:
        cells[centre] = Cell(humans=min(rng.randint(1, 2 * max_humans), budget))
    return Position(rows, columns, cells, to_play=to_play)


def generate_maps(count, *, family="medium", split="train", seed=0):
    """Deterministic list of (name, Position); the same arguments give the same maps."""
    maps = []
    for index in range(count):
        map_seed = SPLIT_OFFSETS[split] + seed * 10_000 + index
        maps.append((f"{split}-{family}-{map_seed}", random_map(random.Random(map_seed), family)))
    return maps


def write_map(position, path):
    root = ET.Element("Map", Rows=str(position.rows), Columns=str(position.columns))
    for (x, y), cell in sorted(position.cells.items(), key=lambda item: (item[0][1], item[0][0])):
        for tag, kind in (("Humans", "humans"), ("Vampires", "vampires"), ("Werewolves", "werewolves")):
            if getattr(cell, kind):
                ET.SubElement(root, tag, X=str(x), Y=str(y), Count=str(getattr(cell, kind)))
    ET.indent(root)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--family", choices=FAMILIES, default="medium")
    parser.add_argument("--split", choices=SPLIT_OFFSETS, default="train")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, help="Output folder (default .local/maps/<split>)")
    args = parser.parse_args(argv)
    out = args.out or Path(__file__).resolve().parent / ".local" / "maps" / args.split
    for name, position in generate_maps(args.count, family=args.family, split=args.split, seed=args.seed):
        write_map(position, out / f"{name}.xml")
    print(f"Wrote {args.count} {args.family} {args.split} maps to {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
