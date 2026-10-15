"""Prepare the course Windows server from Softwares-20261008.zip.

Only the named server files and selected map are copied, into .local/server.
This command prepares files; start the server separately to watch the game.
"""

import argparse
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXECUTABLE = "VampiresVSWerewolvesGameServer.exe"
MAPS = ("thetrap.xml", "testmap2.xml")


def prepare_server(archive_path, destination, *, port=5555, map_name="thetrap.xml", overwrite=False):
    if not 1 <= port <= 65535:
        raise ValueError("The server port must be between 1 and 65535.")
    if map_name not in MAPS:
        raise ValueError(f"Choose one of these maps: {', '.join(MAPS)}")
    destination = Path(destination).resolve()
    with ZipFile(archive_path) as outer:
        with ZipFile(BytesIO(outer.read("Server v3.2.1.zip"))) as server:
            names = (EXECUTABLE, "VVSW.Controls.dll", "VVSW.Model.dll")
            files = {name: server.read(name) for name in names}
            # Some comments in the original config contain invalid UTF-8 bytes.
            configuration = ET.fromstring(server.read(EXECUTABLE + ".config")
                                          .decode("utf-8-sig", errors="replace"))
        with ZipFile(BytesIO(outer.read("Map generator.zip"))) as maps:
            files[map_name] = maps.read("Map generator/" + map_name)

    settings = {
        "ServerIP": "127.0.0.1",
        "ServerPort": str(port),
        "DebugMode": "False",
        "PlayersCount": "2",
        "Map": str(destination / map_name),
        "MaxGameDuration": "00:00:30",
        "MaxPlayDuration": "00:00:02",
        "MaxPlays": "40",
        "AutoRestart": "False",
    }
    entries = {entry.get("key"): entry for entry in configuration.findall("./appSettings/add")}
    missing = settings.keys() - entries.keys()
    if missing:
        raise ValueError(f"The server config is missing settings: {', '.join(sorted(missing))}")
    for key, value in settings.items():
        entries[key].set("value", value)
    files[EXECUTABLE + ".config"] = ET.tostring(configuration, encoding="utf-8", xml_declaration=True)

    if not overwrite and any((destination / name).exists() for name in files):
        raise FileExistsError("Server files already exist. Use --force to reset them to the demo settings.")
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (destination / name).write_bytes(data)
    return destination / EXECUTABLE


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Path to the course Softwares-20261008.zip archive")
    parser.add_argument("--port", type=int, default=5555, help="TCP port (default: 5555)")
    parser.add_argument("--map", dest="map_name", choices=MAPS, default="thetrap.xml")
    parser.add_argument("--force", action="store_true", help="Replace previously prepared server files")
    args = parser.parse_args(argv)
    try:
        executable = prepare_server(args.archive, ROOT / ".local" / "server", port=args.port,
                                    map_name=args.map_name, overwrite=args.force)
    except (OSError, ValueError, KeyError, BadZipFile, ET.ParseError) as error:
        parser.exit(1, f"Setup failed: {error}\n")
    print(f"Prepared: {executable}")
    print(f"Server: 127.0.0.1:{args.port}; map: {args.map_name}")
    print("Demo limits: two players, two seconds per move, 40 plies or 30 seconds per game.")
    print("Open .local/server and double-click " + EXECUTABLE)
    print("Then run these commands in two separate terminals, from the repository folder:")
    print(f"python main.py --name Bot-A 127.0.0.1 {args.port}")
    print(f"python main.py --name Bot-B 127.0.0.1 {args.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
