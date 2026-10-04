from pathlib import Path
import hashlib,json,os,sys,time
ROOT=Path('/home/barberb/lift_coding');OUT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'maintenance/terminal-ir-publication-20261004-01/datasets/checkout'))
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,v):(OUT/name).open('x').write(json.dumps(v,sort_keys=True,indent=2)+'\n')
def pin(p):b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
files={};pins=[]
for name,relative in (('source/reference.py','benchmarks/agent_supervisor/container_coding/terminal_codebase_batching_contract_reference.py'),('source/test_reference.py','test/api/test_terminal_codebase_batching_contract_reference.py')):
 path=ROOT/'external/ipfs_accelerate'/relative;before=pin(path);raw=path.read_bytes();assert pin(path)==before
 target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True);target.open('xb').write(raw);files[name]=raw;pins.append(before)
files['pytest.ini']='[pytest]\n'
files['control.py']='''from pathlib import Path
import importlib.util,json,sys,types
import pytest
for name in ('benchmarks','benchmarks.agent_supervisor','benchmarks.agent_supervisor.container_coding'):
 p=types.ModuleType(name);p.__path__=[];sys.modules[name]=p
name='benchmarks.agent_supervisor.container_coding.terminal_codebase_batching_contract_reference'
spec=importlib.util.spec_from_file_location(name,'source/reference.py');module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
phases=[]
class Reports:
 def pytest_runtest_logreport(self,report): phases.append({'nodeid':report.nodeid,'phase':report.when,'outcome':report.outcome,'seconds':report.duration})
code=int(pytest.main(['-q','-c','pytest.ini','--noconftest','-p','no:cacheprovider','-o','addopts=','--junitxml','result.xml','source/test_reference.py'],plugins=[Reports()]))
Path('phases.json').write_text(json.dumps(phases,indent=2)+'\\n')
assert code==0 and len(phases)==54 and all(p['outcome']=='passed' for p in phases)
print(json.dumps({'returncode':code,'cases':18,'phases':54,'performance_thresholds_checked':False}))
'''
os.environ['IPFS_DATASETS_RESOURCE_SCHEDULER_PATH']=str(OUT/'resources.json');os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler,ResourceLane
from ipfs_datasets_py.logic.backends.process import BoundedToolRunner,ToolRunRequest,ToolRunLimits
s=get_global_resource_scheduler();c=s.config;assert c.proof_safety_enabled and (c.proof_memory_stall_percent,c.proof_cpu_stall_percent,c.proof_io_stall_percent,c.proof_backoff_seconds)==(2.,50.,10.,2.)
lease=None;start=time.monotonic();receipt={'schema':'global-shape-reference-owned-test-control@1','status':'started','cleanup_errors':[],'source_pins':pins,'training_calls':0,'prover_calls':0,'full_task_satisfaction':'unknown'}
try:
 lease=s.acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=2048,child_process_slots=1,timeout=30);receipt['root_lease']=lease.to_dict();receipt['resource_policy']=c.persisted_dict();save('started.json',receipt)
 result=BoundedToolRunner().run(ToolRunRequest(argv=(sys.executable,'control.py'),input_files=files,output_paths=('phases.json','result.xml'),limits=ToolRunLimits(timeout_seconds=20,cpu_seconds=20,max_input_bytes=262144,max_output_bytes=65536,max_workspace_bytes=16*1024*1024)))
 receipt.update(result.to_dict());assert result.ok and not result.output_truncated and result.workspace_cleaned
 for name,raw in result.output_files.items():(OUT/name).open('xb').write(raw)
 for p in pins:assert pin(Path(p['path']))==p
 receipt['status']='passed18_cases54_phases_structural_contracts_only'
except BaseException as error:receipt['status']='failed_retained';receipt['primary_error_type']=type(error).__name__;raise
finally:
 if lease is not None:
  try:lease.release()
  except BaseException as error:receipt['cleanup_errors'].append(type(error).__name__)
 receipt['elapsed_seconds']=time.monotonic()-start;receipt['final_scheduler_snapshot']=s.snapshot();save('closed.json',receipt)
print(json.dumps({'status':receipt['status'],'elapsed_seconds':receipt['elapsed_seconds']}))
