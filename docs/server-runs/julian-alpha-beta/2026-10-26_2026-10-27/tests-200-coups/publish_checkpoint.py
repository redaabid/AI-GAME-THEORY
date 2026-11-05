import json,shutil,hashlib,sys
from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parent
w=r.parents[2]/'worktrees/server-runs'
d=w/'docs/server-runs/2026-10-26/long-200-checkpoint-12'
if d.exists():raise RuntimeError('Refusing to overwrite an existing publication')
d.mkdir(parents=True)
for file in r.rglob('*'):
    if not file.is_file() or 'runtime' in file.relative_to(r).parts:continue
    if file.name in ('publish_report.py','runner-pid.txt','awaiting-ui.json'):continue
    if file.suffix.lower() in ('.exe','.dll','.zip','.png','.jpg'):continue
    out=d/file.relative_to(r);out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,out)
agg=json.loads((d/'games/aggregate-200.json').read_text(encoding='utf8'))
state=json.loads((d/'campaign-state.json').read_text())
lines=['# Comparatif Alpha-BÃªta â€” 200 coups maximum','',f"Ã‰tat : **{state['status']}**. {len(agg['games'])}/16 conditions terminÃ©es, {sum(g['ui']['confirmed'] for g in agg['games'])} verdicts confirmÃ©s.",'','Chaque challenger affronte AB3, sur thetrap et testmap2 et dans les deux ordres de connexion. Ce lot ne constitue pas un tournoi complet ni une preuve statistique de supÃ©rioritÃ©. Les combats du serveur restent alÃ©atoires.','', 'Machine : Intel Core i7-10875H, Windows 11 10.0.26200, Python 3.14.7 (miniconda). La campagne prÃ©cÃ©dente utilisait Python 3.14.3 ; ce changement est enregistrÃ© dans machine.json.','', 'Serveur : MaxPlays=200, MaxGameDuration=00:10:00, MaxPlayDuration=00:00:02 ; deux bots, budget interne 1,5 s. Les 200 coups sont le protocole local, pas une limite officielle du tournoi Ã©tablie.','', '| Profil | Parties | V / N / D | Temps max (s) | Moyenne (s) | Alertes >1,8 s | Faults | Secours internes |','|---|---:|---|---:|---:|---:|---:|---:|']
for n,s in agg['architectures'].items():
    lines.append(f"| {n} | {s['games']} | {s['wins']} / {s['draws']} / {s['losses']} | {s['max_seconds']:.3f} | {s['mean_seconds']:.3f} | {s['alerts_1_8']} | {s['faults']} | {s['bootstraps']} |")
lines+=['','AB3 est la rÃ©fÃ©rence commune : sa ligne regroupe ses diffÃ©rents adversaires. AB7 dÃ©signe exclusivement le nouveau candidat discount=0,97, dont les autres poids et paramÃ¨tres sont figÃ©s dans selection.json.','', 'Les captures textuelles Windows peuvent contenir un Ã©tat pÃ©rimÃ© ; les corrections manuelles dans ui-evidence.json proviennent de la lecture visuelle de la fenÃªtre finale. Un rÃ©sultat inconnu reste inconnu. Aucun vainqueur nâ€™est dÃ©duit du simulateur.','', '[Tableau dÃ©taillÃ© et temps par bot](games/SUMMARY-200.md) Â· [DonnÃ©es agrÃ©gÃ©es](games/aggregate-200.json) Â· [Configurations et protocole](protocol.json)','', 'Aucun code de dÃ©cision du bot original ou des variantes nâ€™a Ã©tÃ© modifiÃ© pour cette campagne. Les scripts, configurations, logs bruts et traces sont conservÃ©s. Les binaires du professeur ne sont pas inclus.','', 'Publication GitHub : le prÃ©cÃ©dent push a Ã©tÃ© refusÃ© (403, droits collaborateur manquants). Ce rapport est conservÃ© localement sur server-runs.']
diag=d/'games/draw-diagnostics-200.json'
if diag.exists():
    records=json.loads(diag.read_text())['games']
    lines+=['','## Fin des parties et répétitions','','Les traces reconstruisent les états avant les mouvements ; le dernier état reconstruit ne remplace pas les effectifs finaux lus dans WPF. Une répétition inclut le joueur au trait. Le compteur ne constitue pas une règle de nul du serveur.','','| Partie | Dernier coup observé | Plafond atteint | États répétés |','|---|---:|---|---:|']
    for g in records:
        lines.append(f"| {g['id']} | {g.get('observed_server_plies','?')} | {g.get('reached_cap','?')} | {g.get('repeated_states','?')} |")
    lines+=['','Les répétitions nombreuses sont une limitation stratégique à examiner. Les victoires au plafond, parfois obtenues après une longue répétition, ne démontrent pas à elles seules une meilleure conduite du combat. Quatre parties par challenger restent insuffisantes pour conclure à une supériorité statistique.']
(d/'SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
(d/'.gitattributes').write_text('* -text\n',encoding='ascii')
files=sorted(p for p in d.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
(d/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(d).as_posix()+'\n' for p in files),encoding='utf8')
print(d)
