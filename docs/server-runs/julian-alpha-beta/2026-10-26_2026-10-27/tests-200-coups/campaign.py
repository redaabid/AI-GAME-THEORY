import json,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parent
w=r.parents[2]/'worktrees/alphabeta-validation'
# r is .local/research/server-validation/long-200-DATE
w=r.parents[2]/'worktrees/alphabeta-validation'
cmd=[sys.executable,'-B',str(w/'scripts/run_ab_server.py'),'--runtime',str(r/'runtime'),'--selection',str(r/'selection.json'),'--output',str(r/'games'),'--ids',','.join(map(str,range(17,33))),'--allow-200','--stop-on-bot-error','--ui-timeout','3600']
(r/'command.json').write_text(json.dumps(cmd,indent=2),encoding='utf8')
(r/'campaign-state.json').write_text(json.dumps(dict(status='running',started=datetime.now(timezone.utc).isoformat())),encoding='utf8')
with (r/'launcher.log').open('w',encoding='utf8') as log:
    proc=subprocess.Popen(cmd,cwd=w,stdout=log,stderr=subprocess.STDOUT)
    (r/'runner-pid.txt').write_text(str(proc.pid))
    code=proc.wait()
with (r/'summary-generation.log').open('w',encoding='utf8') as log:
    summary=subprocess.run([sys.executable,'-B',str(w/'scripts/summarize_ab_server.py'),str(r/'games'),'--max-plies','200'],cwd=w,stdout=log,stderr=subprocess.STDOUT)
(r/'campaign-state.json').write_text(json.dumps(dict(status='complete' if code==0 else 'stopped_on_error',exit_code=code,summary_exit_code=summary.returncode,finished=datetime.now(timezone.utc).isoformat())),encoding='utf8')
print('Campaign ended:',code,flush=True)
