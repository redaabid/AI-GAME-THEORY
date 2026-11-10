"""Create an offline board replay and population timeline for V5 diagnostics.

    python scripts/render_mcts_trace.py .local/diagnostics/V5-RUN

The generated HTML embeds the recorded boards and requires no server or CDN.
Raw traces and summaries are read only; source fingerprints are checked first.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path


PAGE = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V5 recorded game replay</title>
<style>
body{font:16px system-ui,sans-serif;margin:24px auto;padding:0 20px;max-width:1250px;background:#101720;color:#e7edf5}
h1{font-size:24px}h2{font-size:18px}select,button{font:inherit;background:#263347;color:inherit;border:1px solid #506078;border-radius:5px;padding:7px 12px}
button{cursor:pointer}input{width:min(540px,60vw)}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:16px 0}
.muted{color:#adbbcd}.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:20px}
.panel{background:#182332;border:1px solid #344255;border-radius:8px;padding:14px;overflow:auto}
svg{display:block;width:100%;height:auto}.v{color:#fb7185}.w{color:#60a5fa}.h{color:#facc15}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:7px;border-bottom:1px solid #344255;text-align:left}
pre{font:13px ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere}.chosen{background:#29413e}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style>
<h1>V5: recorded decisions against AB</h1>
<p class="muted">New diagnostic games, not replays of the earlier campaign. Step through actual recorded moves; values are search estimates, not win probabilities.</p>
<div class="row"><label>Game <select id="game"></select></label><span id="result"></span></div>
<div class="row"><button id="previous">Previous</button><button id="play">Play</button><button id="next">Next</button>
<input id="turn" type="range" min="0" value="0"><strong id="counter"></strong></div>
<div class="grid"><div>
<div class="panel"><svg id="board" role="img" aria-label="Recorded board"></svg></div>
<div class="row"><span class="v">Vampires</span><span class="w">Werewolves</span><span class="h">Humans</span><span class="muted">Numbers = group population; arrows = last turn.</span></div>
<div class="panel"><h2>Population timeline — click to select a turn</h2><svg id="timeline" role="img" aria-label="V5 and AB populations over time"></svg>
<p><span class="v">V5</span> / <span class="w">AB</span></p></div>
</div><div class="panel"><h2 id="decision">Initial position</h2><pre id="details"></pre>
<h2>V5 root candidates</h2><p class="muted">Chosen move is highlighted. Visits show where search spent its simulations.</p>
<table><thead><tr><th>Move plan</th><th>Visits</th><th>Value</th></tr></thead><tbody id="candidates"></tbody></table>
</div></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const games=JSON.parse(document.getElementById('data').textContent), ns='http://www.w3.org/2000/svg';
const el=id=>document.getElementById(id); let chosen=0,frame=0,timer=null;
function svgNode(tag,attrs={},text=null){const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text!==null)n.textContent=text;return n;}
function add(svg,tag,attrs,text){const n=svgNode(tag,attrs,text);svg.appendChild(n);return n;}
function board(g,state,record){
 const svg=el('board');svg.replaceChildren();const size=32,pad=25,W=state.columns*size,H=state.rows*size;
 svg.setAttribute('viewBox',`0 0 ${W+2*pad} ${H+2*pad}`);
 const defs=add(svg,'defs');const marker=add(defs,'marker',{id:'arrow',markerWidth:6,markerHeight:6,refX:5,refY:3,orient:'auto'});
 add(marker,'path',{d:'M0,0 L6,3 L0,6 z',fill:'#a7f3d0'});
 for(let y=0;y<=state.rows;y++)add(svg,'line',{x1:pad,y1:pad+y*size,x2:pad+W,y2:pad+y*size,stroke:'#344255'});
 for(let x=0;x<=state.columns;x++)add(svg,'line',{x1:pad+x*size,y1:pad,x2:pad+x*size,y2:pad+H,stroke:'#344255'});
 for(let x=0;x<state.columns;x++)add(svg,'text',{x:pad+(x+.5)*size,y:16,'text-anchor':'middle',fill:'#adbbcd','font-size':11},x);
 for(let y=0;y<state.rows;y++)add(svg,'text',{x:12,y:pad+(y+.64)*size,'text-anchor':'middle',fill:'#adbbcd','font-size':11},y);
 for(const [x,y,h,v,w] of state.cells){const color=h?'#facc15':v?'#fb7185':'#60a5fa';
  add(svg,'rect',{x:pad+x*size+2,y:pad+y*size+2,width:size-4,height:size-4,rx:5,fill:color});
  add(svg,'text',{x:pad+(x+.5)*size,y:pad+(y+.65)*size,'text-anchor':'middle',fill:'#101720','font-size':13,'font-weight':700},h||v||w);
 }
 if(record)for(const [x,y,n,tx,ty] of record.executed_moves){
  add(svg,'line',{x1:pad+(x+.5)*size,y1:pad+(y+.5)*size,x2:pad+(tx+.5)*size,y2:pad+(ty+.5)*size,stroke:'#a7f3d0','stroke-width':2,'marker-end':'url(#arrow)'});
 }
}
function totals(state,species){const column=species==='vampires'?3:4;return state.cells.reduce((n,c)=>n+c[column],0);}
function timeline(g){const svg=el('timeline');svg.replaceChildren();svg.setAttribute('viewBox','0 0 760 190');
 const all=[g.initial,...g.records.map(r=>r.after)], max=Math.max(1,...all.flatMap(s=>[totals(s,g.v5_species),totals(s,g.ab_species)]));
 const X=i=>40+700*i/Math.max(1,all.length-1),Y=n=>155-130*n/max;
 add(svg,'line',{x1:40,y1:155,x2:740,y2:155,stroke:'#adbbcd'});
 for(const [s,color] of [[g.v5_species,'#fb7185'],[g.ab_species,'#60a5fa']])add(svg,'polyline',{points:all.map((state,i)=>`${X(i)},${Y(totals(state,s))}`).join(' '),fill:'none',stroke:color,'stroke-width':2});
 add(svg,'line',{x1:X(frame),y1:20,x2:X(frame),y2:155,stroke:'#fff','stroke-dasharray':'4 4'});
 add(svg,'text',{x:5,y:25,fill:'#adbbcd','font-size':12},max);
 add(svg,'text',{x:30,y:178,fill:'#adbbcd','font-size':12},'0');
 add(svg,'text',{x:680,y:178,fill:'#adbbcd','font-size':12},`${all.length-1} plies`);
 svg.onclick=e=>{const rect=svg.getBoundingClientRect();frame=Math.round(Math.max(0,Math.min(1,((e.clientX-rect.left)/rect.width*760-40)/700))*(all.length-1));draw();};
}
function draw(){const g=games[chosen],r=frame?g.records[frame-1]:null,state=r?r.after:g.initial;
 el('turn').max=g.records.length;el('turn').value=frame;el('counter').textContent=`After ply ${state.ply}`;
 el('result').textContent=`${g.summary.status}: ${g.summary.outcome?JSON.stringify(g.summary.outcome):'unfinished'}; V5 plays ${g.v5_species}`;
 board(g,state,r);timeline(g);el('decision').textContent=r?`${r.actor===g.v5_species?'V5':'AB'} decision at ply ${r.ply}`:'Initial position';
 const lines=[`V5 ${totals(state,g.v5_species)} / AB ${totals(state,g.ab_species)}`];
 if(r){const info=r.agent_info||{};lines.push(`Moves: ${JSON.stringify(r.executed_moves)}`,`Decision time: ${r.wall_seconds.toFixed(3)} s`,`Timeout: ${r.timeout}; fault: ${r.fault||'none'}`);
  if(r.actor===g.v5_species){lines.push(`Iterations: ${info.iterations}`,`Memory: ${info.penalized_actions||0} penalized actions`);if(r.static_root_evaluation)lines.push(`Static values BEFORE this move: ${JSON.stringify(r.static_root_evaluation)}`);}
  else lines.push(`AB actual completed depth: ${info.depth}`);
  const repeat=g.summary.repetitions.find(q=>q.ply===r.ply);if(repeat)lines.push(`Repeated board: last seen at ply ${repeat.previous_ply}; actor population margin ${repeat.margin}`);
 }
 el('details').textContent=lines.join('\n');const body=el('candidates');body.replaceChildren();
 if(r&&r.mcts_root){const root=r.mcts_root;const indices=root.visits.map((_,i)=>i).sort((a,b)=>root.visits[b]-root.visits[a]);
  for(const i of indices){const tr=document.createElement('tr');if(JSON.stringify(root.candidate_actions[i])===JSON.stringify(root.chosen_moves))tr.className='chosen';
   for(const text of [JSON.stringify(root.candidate_actions[i]),root.visits[i],root.action_values[i]===null?'—':root.action_values[i].toFixed(3)]){const td=document.createElement('td');td.textContent=text;tr.appendChild(td);}body.appendChild(tr);}
 }
}
function stop(){clearInterval(timer);timer=null;el('play').textContent='Play';}
games.forEach((g,i)=>{const option=document.createElement('option');option.value=i;option.textContent=g.summary.map_name;el('game').appendChild(option);});
el('game').onchange=()=>{stop();chosen=Number(el('game').value);frame=0;draw();};
el('turn').oninput=()=>{frame=Number(el('turn').value);draw();};
el('previous').onclick=()=>{frame=Math.max(0,frame-1);draw();};el('next').onclick=()=>{frame=Math.min(games[chosen].records.length,frame+1);draw();};
el('play').onclick=()=>{if(timer){stop();return;}if(frame===games[chosen].records.length)frame=0;el('play').textContent='Pause';timer=setInterval(()=>{if(frame>=games[chosen].records.length){stop();return;}frame++;draw();},350);};
draw();
</script></html>'''


def render(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    games = []
    for index, job in enumerate(manifest['plan']['jobs']):
        summary = json.loads((directory / f'game-{index+1:02d}.summary.json').read_text(encoding='utf-8'))
        path = directory / summary['trace_file']
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != summary['trace_sha256']:
            raise ValueError('Trace fingerprint mismatch. Verify the recording before rendering.')
        records = [json.loads(line) for line in raw.decode('utf-8').splitlines()]
        initial = job['map'] | {'to_play': job['first']}
        games.append({'initial': initial, 'v5_species': job['a_species'],
                      'ab_species': 'werewolves' if job['a_species'] == 'vampires' else 'vampires',
                      'records': records, 'summary': summary})
    if not games:
        raise ValueError('No completed recordings to render.')
    data = json.dumps(games, allow_nan=False).replace('<', '\\u003c')
    target = directory / 'replay.html'
    target.write_text(PAGE.replace('__DATA__', data), encoding='utf-8')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(render(args.directory).resolve())
