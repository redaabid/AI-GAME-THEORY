"""Set appSettings values in the server config: set_config.py CONFIG KEY=VALUE..."""
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
for pair in sys.argv[2:]:
    key, value = pair.split("=", 1)
    pattern = r'(<add key="%s" value=")[^"]*(")' % re.escape(key)
    text, count = re.subn(pattern, lambda m: m.group(1) + value + m.group(2), text)
    if count != 1:
        sys.exit(f"{key}: {count} matches")
open(path, "w", encoding="utf-8", newline="").write(text)
for key in ("Map", "MaxGameDuration", "MaxPlayDuration", "MaxPlays", "PlayersCount", "AutoRestart"):
    print(key, "=", re.search(r'<add key="%s" value="([^"]*)"' % key, text).group(1))
