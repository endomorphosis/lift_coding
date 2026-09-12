"""Final hardware-label correction; all prior render evidence is retained."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile,time,datetime
HERE=Path(__file__).resolve().parent;PAPER=HERE.parents[2];ROOT=PAPER.parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
 with p.open('x')as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
v2=json.loads((HERE/'corrective_execution_v2.json').read_text());old=json.loads((HERE/'history/original-9057ce1/AF-020.json').read_text())
raw=v2['raw_inputs_unchanged'];assert all(sha(ROOT/p)==h for p,h in raw.items())
shutil.copy2(PAPER/'evaluation/aggregate_costs.py',HERE/'evaluation/aggregate_costs.py')
commands=[]
with tempfile.TemporaryDirectory(prefix='ipfs-accelerate-validation-home-af020-final-')as home:
 env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin','HOME':home,'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8'}
 for name,script in [('corrective-v3-aggregate',PAPER/'evaluation/aggregate_costs.py'),('corrective-v3-check-outputs',HERE/'check_outputs.py'),('corrective-v3-check-nested',HERE/'check_nested_costs.py')]:
  argv=['/usr/bin/python3.12','-S',str(script.relative_to(ROOT))];started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
  with(HERE/'logs'/f'{name}.stdout.log').open('xb')as out,(HERE/'logs'/f'{name}.stderr.log').open('xb')as err:
   result=subprocess.run(argv,cwd=ROOT,env=env,stdout=out,stderr=err,timeout=60);out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
  meta={'argv':argv,'cwd':'.','env':env,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-t,'exit_code':result.returncode,'execution_kind':'stdlib historical cost correction/check; no model or training call','log':str((HERE/'logs'/f'{name}.stdout.log').relative_to(ROOT)),'stderr_log':str((HERE/'logs'/f'{name}.stderr.log').relative_to(ROOT)),'script_artifact':str((HERE/'evaluation/aggregate_costs.py'if name=='corrective-v3-aggregate'else script).relative_to(ROOT))}
  save(HERE/'logs'/f'{name}.meta.json',meta);commands.append(meta);assert result.returncode==0,(name,result.returncode)
for live,snapshot in old['outputs'].items():shutil.copy2(ROOT/live,ROOT/snapshot)
assert all(sha(ROOT/p)==h for p,h in raw.items())
save(HERE/'corrective_execution_v3.json',{'schema':'af020-corrective-accounting-execution/v3','completed':True,'original_receipt_sha256':sha(HERE/'history/original-9057ce1/AF-020.json'),'prior_corrective_execution_sha256':sha(HERE/'corrective_execution_v2.json'),'original_parent_commit':v2['original_parent_commit'],'original_attempt_history_rewritten':False,'raw_inputs_unchanged':raw,'commands':commands,'source_sha256':sha(PAPER/'evaluation/aggregate_costs.py'),'regression_sha256':sha(HERE/'check_nested_costs.py'),'native_telemetry_sha256':v2['native_telemetry_sha256'],'provider_calls':0,'training_runs':0,'native_db_mutations':0})
print(json.dumps({'completed':True,'commands':3,'all_exit_zero':True,'raw_inputs_unchanged':True}))
