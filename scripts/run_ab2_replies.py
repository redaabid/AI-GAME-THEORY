"""Run Julian's AB2-Replies candidate: python scripts/run_ab2_replies.py IP PORT."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from main import main

if __name__=="__main__":
    args=sys.argv[1:]
    if not any(x=="--agent" or x.startswith("--agent=") for x in args):
        args=["--agent","ab2replies:depth=1,max_depth=24,width=7,extra=0,tt_size=50000",*args]
    if not any(x=="--name" or x.startswith("--name=") for x in args):
        args=["--name","AB2-Replies",*args]
    raise SystemExit(main(args))
