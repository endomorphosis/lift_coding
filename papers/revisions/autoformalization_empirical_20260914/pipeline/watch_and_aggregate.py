from pathlib import Path
import json,subprocess,sys,time
P=Path(__file__).resolve().parent
start=time.monotonic()
while time.monotonic()-start<7200:
 ready=True
 for arm in ['B','C','T5']:
  p=P/f'final_{arm}.log'
  lines=p.read_text().splitlines() if p.exists() else []
  try:last=json.loads(lines[-1])
  except (ValueError,IndexError):ready=False;continue
  if last.get('done')!=1913:ready=False
 if ready:
  r=subprocess.run([sys.executable,'-B',str(P/'aggregate_pipeline.py')],capture_output=True,text=True)
  (P/'aggregate.log').write_text(r.stdout+r.stderr)
  if r.returncode:raise SystemExit(r.returncode)
  s=json.loads((P/'summary.json').read_text());print(json.dumps({'pipeline_complete':True,'C':s['C'],'T5':s['T5'],'B':s['B'],'repair':s['repair']},indent=2),flush=True)
  break
 time.sleep(20)
else:raise SystemExit('Pipeline aggregation wait deadline reached')
