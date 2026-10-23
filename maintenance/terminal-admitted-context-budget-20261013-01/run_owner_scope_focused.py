import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
Z=Path(__file__).resolve().parent;C=Z/'checkout';os.umask(0o077)
attempt=Z/sys.argv[1];attempt.mkdir(mode=0o700)
names=['ipfs_accelerate_py/agent_supervisor/runtime/checked_observer_budget.py','test/api/test_checked_observer_budget.py','ipfs_accelerate_py/agent_supervisor/runtime/checked_context_dispatch.py','ipfs_accelerate_py/agent_supervisor/runtime/checked_audit_context.py','ipfs_accelerate_py/agent_supervisor/entrypoints/admitted_benchmark_runtime.py','ipfs_accelerate_py/agent_supervisor/todo_daemon/supervisor_runtime.py','ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py','benchmarks/agent_supervisor/container_coding/container_worker_deployment.py','benchmarks/agent_supervisor/container_coding/terminal_checked_worker_budget.py','benchmarks/agent_supervisor/container_coding/terminal_semantic_budget_delivery.py','benchmarks/agent_supervisor/container_coding/terminal_semantic_context_budget.py','benchmarks/agent_supervisor/container_coding/terminal_revision_metadata.py']
def pins():
 return [{'path':str(p),'bytes':len(raw:=p.read_bytes()),'sha256':hashlib.sha256(raw).hexdigest()} for p in (C/name for name in names)]
before=pins();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TIKTOKEN_CACHE_DIR='/tmp/data-gym-cache',IPFS_ACCELERATE_META_INDEX_DUCKDB=str(attempt/'meta.duckdb'),IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(attempt/'seal.duckdb'),IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(attempt/'orchestration'))
env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
xml=attempt/'results.xml'
command=[sys.executable,'-B','-m','pytest','test/api/test_checked_observer_budget.py','-q','-p','no:cacheprovider','--tb=short','--junitxml='+str(xml),*sys.argv[2:]]
with (attempt/'pytest.log').open('xb') as out:r=subprocess.run(command,cwd=C,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=600,preexec_fn=lambda:os.umask(0o022))
after=pins();root=ET.parse(xml).getroot();cases=list(root.iter('testcase'));ids=[(x.get('classname'),x.get('name')) for x in cases]
counts={'tests':len(cases),'unique_tests':len(set(ids)),'failures':len(list(root.iter('failure'))),'errors':len(list(root.iter('error'))),'skips':len(list(root.iter('skipped')))}
v={'schema':'checked-observer-budget-focused@1','command':command,'exit_code':r.returncode,'counts':counts,'before':before,'after':after,'producer_bytes_unchanged':before==after,'child_umask':'022','current_delivery_proof_scope_explicitly_stubbed':True,'runtime_objects_authored_uninitialized_data':True,'actual_worker_birth_qualified':False,'provider_usage_measured':False,'full_task_satisfaction':False}
v['qualified_pure_test_run']=r.returncode==0 and before==after and counts['tests']==counts['unique_tests'] and counts['tests']>0 and not(counts['failures']or counts['errors']or counts['skips'])
report=attempt/'run.json';report.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n');report.chmod(0o600)
for path in attempt.iterdir():
 if path.is_file():path.chmod(0o600)
print(json.dumps({'report':str(report),'sha256':hashlib.sha256(report.read_bytes()).hexdigest(),'bytes':report.stat().st_size,'qualified':v['qualified_pure_test_run'],'counts':counts,'producer_bytes_unchanged':before==after}));raise SystemExit(0 if v['qualified_pure_test_run'] else 1)
