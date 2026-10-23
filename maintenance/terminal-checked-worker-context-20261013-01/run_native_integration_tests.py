import os,sys,subprocess,json,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
Z=Path(__file__).resolve().parent;C=Z/'checkout';os.umask(0o077)
name=sys.argv[1]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',IPFS_ACCELERATE_META_INDEX_DUCKDB=str(Z/(name+'-meta.duckdb')),IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(Z/(name+'-seal.duckdb')),IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(Z/(name+'-orchestration')))
env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
paths=[C/x for x in ['ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py','ipfs_accelerate_py/agent_supervisor/runtime/model_input_observation_receipt.py','ipfs_accelerate_py/agent_supervisor/runtime/checked_audit_context.py','ipfs_accelerate_py/agent_supervisor/entrypoints/admitted_benchmark_runtime.py','benchmarks/agent_supervisor/container_coding/terminal_context_audit.py','benchmarks/agent_supervisor/container_coding/terminal_model_input_observation_audit.py','benchmarks/agent_supervisor/container_coding/terminal_observer_stop.py','benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py','test/api/test_router_checked_context_integration.py']]
def pins():return [{'path':str(p),'bytes':len(raw:=p.read_bytes()),'sha256':hashlib.sha256(raw).hexdigest()} for p in paths]
before=pins();xml=Z/(name+'.xml');assert not xml.exists()
command=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--junitxml='+str(xml),'test/api/test_router_checked_context_integration.py',*sys.argv[2:]]
with (Z/(name+'.log')).open('xb') as f:r=subprocess.run(command,cwd=C,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=300,preexec_fn=lambda:os.umask(0o022))
after=pins();root=ET.fromstring(xml.read_bytes());cases=list(root.iter('testcase'));ids=[(x.get('classname'),x.get('name')) for x in cases]
v={'schema':'terminal-checked-native-integration-tests@1','exit_code':r.returncode,'tests':len(cases),'unique_tests':len(set(ids)),'failures':len(list(root.iter('failure'))),'errors':len(list(root.iter('error'))),'skips':len(list(root.iter('skipped'))),'before':before,'after':after,'sources_unchanged':before==after,'provider_calls':0,'actual_worker_birth_verified':False}
with (Z/(name+'-run.json')).open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({k:v[k] for k in ('exit_code','tests','failures','errors','skips','sources_unchanged')}));raise SystemExit(r.returncode)
