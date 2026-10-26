import json,time,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent
w=r.parents[2]/'worktrees/alphabeta-validation'
seen=-1
while True:
    count=len(list((r/'games').glob('*/ui-evidence.json')))
    status=json.loads((r/'campaign-state.json').read_text())
    if count!=seen:
        subprocess.run([sys.executable,'-B',str(w/'scripts/summarize_ab_server.py'),str(r/'games'),'--max-plies','200'],cwd=w,stdout=subprocess.DEVNULL,check=True)
        (r/'progress.json').write_text(json.dumps(dict(confirmed=count,total=16,status=status['status'])),encoding='utf8')
        seen=count
    if status['status']!='running':break
    time.sleep(3)
