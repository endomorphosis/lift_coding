"""Bounded no-arg public baseline control on authored fixtures, not a score."""
from pathlib import Path
import hashlib,json,os,sys,time
ROOT=Path('/home/barberb/lift_coding');OUT=Path(__file__).resolve().parent
DATASETS=ROOT/'maintenance/terminal-ir-publication-20261004-01/datasets/checkout'
sys.dont_write_bytecode=True;sys.path.insert(0,str(DATASETS))
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,v):
 (OUT/name).open('x').write(json.dumps(v,sort_keys=True,indent=2)+'\n')
def binding(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
TASK=ROOT/'.benchmarks/terminal-bench-2/llm-inference-batching-scheduler'
sources={};pins=[]
for name in ('baseline_packer.py','cost_model.py'):
 p=TASK/'environment/task_file/scripts'/name;before=binding(p);b=p.read_bytes();assert binding(p)==before
 if name=='baseline_packer.py':assert before['sha256']=='547d230d5e6d93197803480cb81cab0ec6ac63fcfa0a24b246f549523f216c4e'
 frozen=OUT/name;frozen.open('xb').write(b);sources['task_file/scripts/'+name]=b;pins.append(before)
fixtures={}
for bucket,start in ((1,64),(2,576)):
 rows=[{'request_id':f'model-b{bucket}-r{i+1:02d}','prompt_len':start+i*64,'gen_len':1} for i in range(8)]
 fixtures[f'task_file/input_data/requests_bucket_{bucket}.jsonl']=''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows).encode()
control='''from pathlib import Path
from collections import Counter
import hashlib,json,runpy,sys
root=Path('task_file');paths=[root/'input_data'/f'requests_bucket_{i}.jsonl' for i in (1,2)]
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
sys.path.insert(0,str((root/'scripts').resolve()))
runpy.run_path(str(root/'scripts/baseline_packer.py'),run_name='__main__')
plans=[root/'output_data'/f'plan_b{i}.jsonl' for i in (1,2)]
inputs=[[json.loads(s) for s in p.read_text().splitlines()] for p in paths]
outputs=[[json.loads(s) for s in p.read_text().splitlines()] for p in plans]
shapes={tuple(r['shape'][k] for k in ('seq_align','heads_align','hidden_align')) for rows in outputs for r in rows}
checks=[]
for source,plan in zip(inputs,outputs):
 source_map={r['request_id']:r for r in source}
 checks.append({'included_exactly_once':Counter(r['request_id'] for r in source)==Counter(r['request_id'] for r in plan),'heads_hidden_aligned':all(r['shape']['heads_align']==32 and r['shape']['hidden_align']==4096 for r in plan),'seq_covers_and_aligned':all(r['shape']['seq_align']%64==0 and r['shape']['seq_align']>=((source_map[r['request_id']]['prompt_len']+63)//64)*64 for r in plan),'local_unique_shape_count':len({tuple(r['shape'][k] for k in ('seq_align','heads_align','hidden_align')) for r in plan})})
result={'schema':'public-baseline-authored-fixture-result@1','fixture_kind':'authored_two_disjoint_eight_request_buckets','baseline_entry_point':'unmodified_no_arg_build_plan','global_unique_shapes':sorted(shapes),'global_unique_shape_count':len(shapes),'required_global_cap':8,'global_cap_satisfied':len(shapes)<=8,'bucket_checks':checks,'input_bytes_unchanged':before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'actual_benchmark_request_data_used':False,'official_benchmark_score':None,'full_task_satisfaction':False,'universal_source_equivalence_proved':False}
assert result['global_unique_shape_count']==16 and not result['global_cap_satisfied']
assert result['input_bytes_unchanged'] and all(all(r[k] for k in ('included_exactly_once','heads_hidden_aligned','seq_covers_and_aligned')) and r['local_unique_shape_count']==8 for r in checks)
Path('result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\\n')
print(json.dumps({'shapes':len(shapes),'global_cap_satisfied':False,'inputs_unchanged':True}))
'''
sources.update(fixtures);sources['control.py']=control
save('input-manifest.json',{'schema':'public-baseline-control-inputs@1','public_sources':pins,'files':[{'path':name,'bytes':len(v.encode() if isinstance(v,str) else v),'sha256':sha(v.encode() if isinstance(v,str) else v)} for name,v in sorted(sources.items())],'fixture_training_calls':0,'fixture_used_for_training':False})
os.environ['IPFS_DATASETS_RESOURCE_SCHEDULER_PATH']=str(OUT/'resources.json')
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler,ResourceLane
from ipfs_datasets_py.logic.backends.process import BoundedToolRunner,ToolRunRequest,ToolRunLimits
scheduler=get_global_resource_scheduler();config=scheduler.config
assert config.proof_safety_enabled and (config.proof_memory_stall_percent,config.proof_cpu_stall_percent,config.proof_io_stall_percent,config.proof_backoff_seconds)==(2.0,50.0,10.0,2.0)
lease=None;start=time.monotonic();receipt={'schema':'public-baseline-owned-control@1','status':'started','cleanup_errors':[],'training_calls':0,'prover_calls':0,'official_score':None}
try:
 lease=scheduler.acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=2048,child_process_slots=1,timeout=30)
 receipt['root_lease']=lease.to_dict();receipt['resource_policy']=config.persisted_dict();save('started.json',receipt)
 run=BoundedToolRunner().run(ToolRunRequest(argv=(sys.executable,'control.py'),input_files=sources,output_paths=('result.json','task_file/output_data/plan_b1.jsonl','task_file/output_data/plan_b2.jsonl'),limits=ToolRunLimits(timeout_seconds=10,cpu_seconds=10,max_input_bytes=262144,max_output_bytes=65536,max_workspace_bytes=16*1024*1024)))
 receipt.update(run.to_dict());assert run.ok and not run.output_truncated and run.workspace_cleaned
 outputs=[]
 for name,raw in run.output_files.items():
  p=OUT/'output'/name;p.parent.mkdir(parents=True,exist_ok=True);p.open('xb').write(raw);outputs.append(binding(p))
 receipt['output_bindings']=outputs;receipt['status']='passed_observed_scoped_baseline_counterexample'
 for pin in pins:assert binding(Path(pin['path']))==pin
except BaseException as error:
 receipt['status']='failed_retained';receipt['primary_error_type']=type(error).__name__;raise
finally:
 if lease is not None:
  try:lease.release()
  except BaseException as error:receipt['cleanup_errors'].append(type(error).__name__)
 receipt['elapsed_seconds']=time.monotonic()-start;receipt['final_scheduler_snapshot']=scheduler.snapshot();save('closed.json',receipt)
print(json.dumps({'status':receipt['status'],'elapsed_seconds':receipt['elapsed_seconds']}))
