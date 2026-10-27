"""Prepare a separate graphical match on one of our four comparison maps.

    python scripts/prepare_watch.py --map thetrap

Close the watch server before changing maps. This command prepares files only;
start the server and both bots using the printed commands. Needs the course ZIP.
"""

import argparse
from io import BytesIO
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mapgen import generate_maps, write_map
from scripts.setup_server import EXECUTABLE, prepare_server
from simulator import load_map

CHOICES = {"thetrap": "thetrap.xml", "testmap2": "testmap2.xml",
           "medium": "val-medium-1280000.xml", "large": "val-large-1290000.xml"}


def prepare_watch(archive, choice, *, port=5560):
    if choice not in CHOICES:
        raise ValueError("Choose thetrap, testmap2, medium, or large.")
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")
    maps = ROOT / ".local" / "maps" / "mcts-vs-best-ab"
    server = ROOT / ".local" / "watch-server"
    # Read and validate both course maps before writing any setup files.
    with ZipFile(archive) as outer:
        with ZipFile(BytesIO(outer.read("Map generator.zip"))) as nested:
            originals = {name: nested.read("Map generator/" + name)
                         for name in ("thetrap.xml", "testmap2.xml")}
    for data in originals.values():
        ET.fromstring(data)
    maps.mkdir(parents=True, exist_ok=True)
    for name, data in originals.items():
        target = maps / name
        if target.exists() and target.read_bytes() != data:
            raise ValueError(f"Map was edited; preserving it: {target}")
        target.write_bytes(data)
    for family, seed in (("medium", 28), ("large", 29)):
        name, position = generate_maps(1, family=family, split="val", seed=seed)[0]
        target = maps / (name + ".xml")
        if target.exists() and load_map(target) != position:
            raise ValueError(f"Map was edited; preserving it: {target}")
        write_map(position, target)
    selected = (maps / CHOICES[choice]).resolve()
    load_map(selected)
    configuration = server / (EXECUTABLE + ".config")
    if not configuration.exists():
        prepare_server(archive, server, port=port)
    for name in (EXECUTABLE, "VVSW.Controls.dll", "VVSW.Model.dll"):
        if not (server / name).is_file():
            raise FileNotFoundError(f"Incomplete watch server: {server / name}")
    tree = ET.parse(configuration)
    entries = {entry.get("key"): entry for entry in tree.findall("./appSettings/add")}
    settings = {"Map": str(selected), "ServerIP": "127.0.0.1", "ServerPort": str(port),
                "MaxPlays": "200", "MaxGameDuration": "00:10:00",
                "MaxPlayDuration": "00:00:02", "PlayersCount": "2", "AutoRestart": "False"}
    for key, value in settings.items():
        entries[key].set("value", value)
    tree.write(configuration, encoding="utf-8", xml_declaration=True)
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--map", choices=CHOICES, default="thetrap")
    parser.add_argument("--archive", type=Path, default=Path.home() / "Downloads" / "Softwares-20261008.zip")
    parser.add_argument("--port", type=int, default=5560)
    args = parser.parse_args(argv)
    try:
        prepare_watch(args.archive, args.map, port=args.port)
    except (OSError, ValueError, KeyError, BadZipFile, ET.ParseError) as error:
        parser.exit(1, f"Watch setup failed: {error}\n")
    print(f"Prepared {args.map}: 200 plies, 10-minute game cap, 2 seconds per move.")
    print("Run from the repository folder, using three terminals:")
    print('Start-Process -FilePath ".\\.local\\watch-server\\' + EXECUTABLE
          + '" -WorkingDirectory ".\\.local\\watch-server"')
    print(f"python main.py --agent mcts-memory --iterations 100000 --name Memory --max-plies 200 --move-time 1.5 127.0.0.1 {args.port}")
    print(f'python main.py --agent "ab2:width=6,depth=1,max_depth=8,extra=0,tt_size=50000,qdepth=1,qwidth=2,aspiration=25000" --name AB2 --max-plies 200 --move-time 1.5 127.0.0.1 {args.port}')
    print("For AB6, replace ab2 with ab6 and --name AB2 with --name AB6.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
