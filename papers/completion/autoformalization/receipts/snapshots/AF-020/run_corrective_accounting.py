"""One corrective stdlib reduction, retaining original receipt artifacts and logs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile,time,datetime
HERE=Path(__file__).resolve().parent;PAPER=HERE.parents[2];ROOT=PAPER.parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
 with p.open('x')as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
original=json.loads((PAPER/'receipts/AF-020.json').read_text());history=HERE/'history/original-9057ce1';history.mkdir(parents=True)
shutil.copy2(PAPER/'receipts/AF-020.json',history/'AF-020.json')
for rel,digest in original['artifacts'].items():
 src=ROOT/rel;assert sha(src)==digest
 dst=history/'artifacts'/src.relative_to(HERE);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
raw_paths=[PAPER/'runs/planning/results.jsonl',PAPER/'runs/proof_assistance/results.jsonl',PAPER/'receipts/snapshots/AF-018/measure_assistance.py',PAPER/'receipts/snapshots/AF-018/logs/measure.meta.json']
raw_before={str(p.relative_to(ROOT)):sha(p)for p in raw_paths}
shutil.copy2(PAPER/'evaluation/aggregate_costs.py',HERE/'evaluation/aggregate_costs.py')
commands=[]
with tempfile.TemporaryDirectory(prefix='ipfs-accelerate-validation-home-af020-correction-')as home:
 env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin','HOME':home,'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8'}
 for name,script in [('corrective-aggregate',PAPER/'evaluation/aggregate_costs.py'),('corrective-check-outputs',HERE/'check_outputs.py'),('corrective-check-nested',HERE/'check_nested_costs.py')]:
  argv=['/usr/bin/python3.12','-S',str(script.relative_to(ROOT))];started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
  with(HERE/'logs'/f'{name}.stdout.log').open('xb')as out,(HERE/'logs'/f'{name}.stderr.log').open('xb')as err:
   r=subprocess.run(argv,cwd=ROOT,env=env,stdout=out,stderr=err,timeout=60)
   out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
  meta={'argv':argv,'cwd':'.','env':env,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-t,'exit_code':r.returncode,'execution_kind':'stdlib corrective historical cost reduction or checks; no training/model calls','log':str((HERE/'logs'/f'{name}.stdout.log').relative_to(ROOT)),'stderr_log':str((HERE/'logs'/f'{name}.stderr.log').relative_to(ROOT)),'script_artifact':str((HERE/'evaluation/aggregate_costs.py'if name=='corrective-aggregate'else script).relative_to(ROOT))}
  save(HERE/'logs'/f'{name}.meta.json',meta);commands.append(meta);assert r.returncode==0,(name,r.returncode)
for live,snapshot in original['outputs'].items():shutil.copy2(ROOT/live,ROOT/snapshot)
assert raw_before=={str(p.relative_to(ROOT)):sha(p)for p in raw_paths}
save(HERE/'corrective_execution.json',{'schema':'af020-corrective-accounting-execution/v1','completed':True,'original_receipt_sha256':sha(history/'AF-020.json'),'original_parent_commit':'9057ce1e7a441a0bcd581a039a2c95956364abad','original_attempt_history_rewritten':False,'raw_inputs_unchanged':raw_before,'commands':commands,'source_sha256':sha(PAPER/'evaluation/aggregate_costs.py'),'regression_sha256':sha(HERE/'check_nested_costs.py'),'native_telemetry_sha256':sha(ROOT/'external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/runtime_telemetry.py'),'provider_calls':0,'training_runs':0,'native_db_mutations':0})
print(json.dumps({'completed':True,'commands':len(commands),'all_exit_zero':True,'raw_inputs_unchanged':True}))
