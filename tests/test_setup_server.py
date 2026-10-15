"""Verify course-archive setup without needing or executing server binaries."""

from io import BytesIO
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from scripts.setup_server import EXECUTABLE, ROOT, prepare_server

KEYS = ("ServerIP", "ServerPort", "DebugMode", "PlayersCount", "Map",
        "MaxGameDuration", "MaxPlayDuration", "MaxPlays", "AutoRestart")


def course_archive(path, *, missing_binary=False, missing_setting=False):
    server_data, map_data = BytesIO(), BytesIO()
    keys = KEYS[:-1] if missing_setting else KEYS
    entries = "".join(f'<add key="{key}" value="original"/>' for key in keys)
    configuration = ("<configuration><appSettings>" + entries
                     + "</appSettings><!-- legacy byte: ").encode() + b"\xe9 --></configuration>"
    with ZipFile(server_data, "w") as server:
        server.writestr(EXECUTABLE, b"fake executable")
        server.writestr("VVSW.Controls.dll", b"fake controls")
        if not missing_binary:
            server.writestr("VVSW.Model.dll", b"fake model")
        server.writestr(EXECUTABLE + ".config", configuration)
        server.writestr("../escape.txt", b"must not be extracted")
    with ZipFile(map_data, "w") as maps:
        for name in ("thetrap.xml", "testmap2.xml"):
            maps.writestr("Map generator/" + name, '<Map Rows="3" Columns="4"/>')
    with ZipFile(path, "w") as outer:
        outer.writestr("Server v3.2.1.zip", server_data.getvalue())
        outer.writestr("Map generator.zip", map_data.getvalue())


class ServerSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.archive = self.directory / "course.zip"
        self.output = self.directory / "local" / "server"
        course_archive(self.archive)

    def settings(self):
        tree = ET.parse(self.output / (EXECUTABLE + ".config"))
        return {entry.get("key"): entry.get("value")
                for entry in tree.findall("./appSettings/add")}

    def test_prepare_configures_playable_demo_and_only_copies_named_files(self):
        executable = prepare_server(self.archive, self.output, port=5556, map_name="testmap2.xml")
        self.assertEqual(executable.read_bytes(), b"fake executable")
        settings = self.settings()
        self.assertEqual(settings["ServerPort"], "5556")
        self.assertEqual(settings["PlayersCount"], "2")
        self.assertEqual(settings["DebugMode"], "False")
        self.assertEqual(settings["MaxPlayDuration"], "00:00:02")
        self.assertEqual(settings["MaxPlays"], "40")
        self.assertEqual(Path(settings["Map"]), self.output / "testmap2.xml")
        self.assertTrue(Path(settings["Map"]).is_file())
        self.assertEqual(len(list(self.output.iterdir())), 5)
        self.assertFalse((self.output.parent / "escape.txt").exists())

    def test_existing_configuration_is_preserved_until_force_is_requested(self):
        prepare_server(self.archive, self.output, port=5556)
        original = (self.output / (EXECUTABLE + ".config")).read_bytes()
        with self.assertRaises(FileExistsError):
            prepare_server(self.archive, self.output)
        self.assertEqual((self.output / (EXECUTABLE + ".config")).read_bytes(), original)
        (self.output / "personal-notes.txt").write_text("keep this")
        prepare_server(self.archive, self.output, port=5557, overwrite=True)
        self.assertEqual(self.settings()["ServerPort"], "5557")
        self.assertEqual((self.output / "personal-notes.txt").read_text(), "keep this")

    def test_invalid_port_and_map_leave_no_output(self):
        for arguments in ({"port": 0}, {"port": 65536}, {"map_name": "../other.xml"}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                prepare_server(self.archive, self.output, **arguments)
            self.assertFalse(self.output.exists())

    def test_missing_binary_leaves_no_partial_setup(self):
        course_archive(self.archive, missing_binary=True)
        with self.assertRaises(KeyError):
            prepare_server(self.archive, self.output)
        self.assertFalse(self.output.exists())

    def test_missing_config_setting_leaves_no_partial_setup(self):
        course_archive(self.archive, missing_setting=True)
        with self.assertRaises(ValueError):
            prepare_server(self.archive, self.output)
        self.assertFalse(self.output.exists())

    def test_cli_reports_missing_archive_without_traceback(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "setup_server.py"), str(self.directory / "absent.zip")],
            cwd=ROOT, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Setup failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
