"""Sequential real-WPF campaign. UI evidence is supplied by a separate observer.

Never substitutes simulator results for WPF results. Keeps a completed server
open until ui-evidence.json exists, then closes only its own process.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXE = 'VampiresVSWerewolvesGameServer.exe'


def available(port):
    # Inspect ownership using netstat; do NOT connect a probe socket: the course
    # server treats any accepted TCP connection as one of its two players.
    text = subprocess.check_output(['netstat', '-an'], text=True, errors='replace')
    return any(f':{port} ' in line and 'LISTENING' in line for line in text.splitlines())


def parse_bot(path):
    import re
    text = path.read_text(encoding='utf8', errors='replace')
    times = [float(x) for x in re.findall(r'Turn \d+:.*?\(([\d.]+) seconds\)', text)]
    metrics = []
    for line in text.splitlines():
        if 'AB_METRICS ' in line:
            metrics.append(json.loads(line.split('AB_METRICS ', 1)[1]))
    return dict(turns=len(times), max_seconds=max(times, default=None),
                mean_seconds=sum(times)/len(times) if times else None,
                alerts_1_8=sum(t > 1.8 for t in times), violations_2=sum(t > 2 for t in times),
                faults=text.count('Agent fault,'), new_game_failures=text.count('Agent new_game failed'),
                bootstraps=sum(bool(m['bootstrap']) for m in metrics),
                completed_depths=[m['depth'] for m in metrics],
                ended='Game ended;' in text, bye='Server finished the session.' in text,
                species=next(iter(re.findall(r'playing (vampires|werewolves)', text)), None),
                errors=[line for line in text.splitlines() if 'ERROR:' in line or 'Traceback' in line])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--move-time', type=float, default=1.5)
    p.add_argument('--ui-timeout', type=float, default=180)
    p.add_argument('--max-games', type=int, default=64)
    p.add_argument('--offset', type=int, default=0)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    selection = json.loads(args.selection.read_text(encoding='utf8'))
    specs = {name: data['selected'] for name, data in selection['architectures'].items()}
    jobs = [(n, m, plays, reverse) for plays in (40, 200)
            for m in ('thetrap.xml', 'testmap2.xml')
            for n in specs if n != 'ab3' for reverse in (False, True)]
    sha = subprocess.check_output(['git', '-c', 'safe.directory=*', 'rev-parse', 'HEAD'],
                                  cwd=ROOT, text=True).strip()
    for index, (challenger, map_name, plays, reverse) in enumerate(jobs):
        if index < args.offset or index >= args.offset + args.max_games:
            continue
        game = args.output / f'{index+1:03d}-{challenger}-{Path(map_name).stem}-{plays}-{int(reverse)}'
        if game.exists():
            raise RuntimeError(f'Refusing to overwrite {game}')
        if available(5555):
            raise RuntimeError('Port 5555 is already occupied; do not take over an unknown server')
        game.mkdir()
        config_path = args.runtime / (EXE + '.config')
        tree = ET.parse(config_path)
        values = dict(ServerIP='127.0.0.1', ServerPort='5555', PlayersCount='2', DebugMode='True',
                      Map=str((args.runtime / map_name).resolve()), MaxPlays=str(plays),
                      MaxPlayDuration='00:00:02', MaxGameDuration='00:10:00', AutoRestart='False')
        settings = {e.get('key'): e for e in tree.findall('./appSettings/add')}
        for key, value in values.items():
            settings[key].set('value', value)
        tree.write(config_path, encoding='utf8', xml_declaration=True)
        shutil.copy2(config_path, game / config_path.name)
        order = [challenger, 'ab3'] if reverse else ['ab3', challenger]
        commands = [[sys.executable, '-B', 'main.py', '--name', name.upper(), '--agent', specs[name],
                     '--move-time', str(args.move_time), '--max-plies', str(plays),
                     '--rules-profile', 'server-v3.2.1', '--seed', '42', '127.0.0.1', '5555']
                    for name in order]
        manifest = dict(id=index+1, sha=sha, map=map_name, max_plies=plays, order=order,
                        specs={n: specs[n] for n in order}, commands=commands,
                        map_sha256=hashlib.sha256((args.runtime/map_name).read_bytes()).hexdigest(),
                        started=datetime.now(timezone.utc).isoformat(), move_time=args.move_time)
        (game/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
        before = {x.name for x in args.runtime.glob('trace*')}
        server = subprocess.Popen([str((args.runtime/EXE).resolve())], cwd=args.runtime)
        bots, streams = [], []
        try:
            limit = time.monotonic() + 100
            while not available(5555):
                if server.poll() is not None or time.monotonic() > limit:
                    raise RuntimeError(f'Server failed to listen; exit={server.poll()}')
                time.sleep(.3)
            for name, command in zip(order, commands):
                stdout = (game/f'{name}.stdout.log').open('w', encoding='utf8')
                stderr = (game/f'{name}.stderr.log').open('w', encoding='utf8')
                streams.extend([stdout, stderr])
                bot = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                bots.append(bot)
                # Wait for MAP, not just successful connect, before the next bot.
                if len(bots) == 1:
                    connected_until = time.monotonic() + 25
                    while 'Board:' not in (game/f'{name}.stderr.log').read_text(encoding='utf8'):
                        if bot.poll() is not None or time.monotonic() > connected_until:
                            raise RuntimeError('First bot did not receive MAP')
                        time.sleep(.1)
            limit = time.monotonic() + 640
            while any(bot.poll() is None for bot in bots):
                if time.monotonic() > limit:
                    raise TimeoutError('No completed game within server duration plus margin')
                time.sleep(.3)
            for stream in streams:
                stream.close()
            result = dict(manifest, exit_codes=[b.returncode for b in bots],
                          bots={name: parse_bot(game/f'{name}.stderr.log') for name in order})
            (game/'result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
            # Observer reads this only after END/BYE. Keep window for final counts.
            (args.output/'awaiting-ui.json').write_text(json.dumps(dict(
                game=str(game.resolve()), server_pid=server.pid, index=index+1)), encoding='utf8')
            limit = time.monotonic() + args.ui_timeout
            while not (game/'ui-evidence.json').exists():
                if time.monotonic() > limit:
                    (game/'ui-missing.txt').write_text('UI evidence not captured; winner unconfirmed.\n')
                    break
                time.sleep(.2)
            print('FINISHED', index+1, challenger, map_name, plays,
                  json.dumps(result['bots']), flush=True)
        except Exception as error:
            (game/'run-error.txt').write_text(repr(error), encoding='utf8')
            print('FAILED', index+1, repr(error), flush=True)
            raise
        finally:
            for bot in bots:
                if bot.poll() is None:
                    bot.terminate()
                    bot.wait(timeout=10)
            # UI observer first attempts the normal Close command after capture.
            if server.poll() is None:
                try:
                    server.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    server.terminate()
                    server.wait(timeout=10)
            for stream in streams:
                if not stream.closed:
                    stream.close()
            for trace in args.runtime.glob('trace*'):
                if trace.name not in before:
                    shutil.copy2(trace, game/trace.name)
            time.sleep(.5)


if __name__ == '__main__':
    main()
