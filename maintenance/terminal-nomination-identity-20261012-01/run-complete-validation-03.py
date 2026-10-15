"""Run the final independently scoped identity/replay regression, retaining exact public pins."""
from pathlib import Path
import hashlib,json,os,subprocess,time,xml.etree.ElementTree as ET
O=Path(__file__).resolve().parent
C=O.parent/'terminal-token-reduction-20261007-01/checkout'
E=O.parent/'terminal-compact-retrieval-20261011-01/pinned-dependencies-v10'
tests=['test/api/test_reviewed_source_nomination_context.py','test/api/test_reviewed_source_nomination_audit.py','test/api/test_router_model_input_observation.py','benchmarks/agent_supervisor/container_coding/test_terminal_nomination_context_audit.py','benchmarks/agent_supervisor/container_coding/test_terminal_context_audit.py','benchmarks/agent_supervisor/container_coding/test_terminal_model_input_observation_audit.py','benchmarks/agent_supervisor/container_coding/test_terminal_context_audit_budget.py','test/api/test_portal_nomination_task_identity.py']
base=json.loads((O/'identity-validation.json').read_bytes())
names={r['path'] for r in base['sources']}|set(tests)|{'ipfs_accelerate_py/agent_supervisor/runtime/native_task_identity.py','test/api/test_native_task_identity.py'}
for r in json.loads((O/'native-task-identity-dependency-baseline-03.json').read_bytes())['files']:
 dependency=Path(r['path']);assert dependency.is_absolute() and dependency.is_relative_to(C)
 names.add(str(dependency.relative_to(C)))
def write(name,value):
 raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 with (O/name).open('xb') as stream:stream.write(raw)
 return {'path':str(O/name),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def observed(name):
 p=O/name;raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def pins():
 rows=[]
 for name in sorted(names):
  p=C/name;assert p.is_file() and not p.is_symlink() and p.suffix=='.py'
  raw=p.read_bytes();assert len(raw)<=4000000
  rows.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 return rows
before=pins();beforepin=write('complete-source-pins-before-03.json',{'schema':'terminal-nomination-validation-source-pins@1','files':before})
env=dict(os.environ)
for key in list(env):
 if key=='IPFS_ACCELERATE_META_INDEX_DUCKLAKE' or key.startswith('IPFS_ACCELERATE_AGENT_STATE_') or key.startswith('IPFS_ACCELERATE_QUACK_'):env.pop(key,None)
env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(map(str,(C,E/'datasets',E/'kit'))),IPFS_ACCELERATE_META_INDEX_DUCKDB=str(O/'fresh-meta-complete-03.duckdb'),IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(O/'fresh-seal-complete-03.duckdb'),IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(O/'fresh-orchestration-complete-03'))
argv=['/home/barberb/lift_coding/.venv/bin/python','-P','-m','pytest','-q',*tests,'--basetemp='+str(O/'tests-complete-03'),'-o','cache_dir='+str(O/'pytest-cache-complete-03'),'--junitxml='+str(O/'complete-focused-03.xml')]
started=time.monotonic()
with (O/'complete-focused-03.stdout').open('xb') as out,(O/'complete-focused-03.stderr').open('xb') as err:
 result=subprocess.run(argv,cwd=C,env=env,stdout=out,stderr=err)
after=pins();afterpin=write('complete-source-pins-after-03.json',{'schema':'terminal-nomination-validation-source-pins@1','files':after})
cases=ET.parse(O/'complete-focused-03.xml').findall('.//testcase')
identities=[(r.get('classname'),r.get('name')) for r in cases]
counts={'physical_cases':len(cases),'distinct_cases':len(set(identities)),'duplicate_cases':len(cases)-len(set(identities)),**{kind:sum(r.find(kind) is not None for r in cases) for kind in ('failure','error','skipped')}}
value={'schema':'terminal-nomination-identity-complete-test-validation@1','generation':3,'tests':tests,'sources':after,'source_pins_before':beforepin,'source_pins_after':afterpin,'all_source_pins_unchanged':before==after,'counts':counts,'exit_code':result.returncode,'seconds':time.monotonic()-started,'all_passed':result.returncode==0 and before==after and counts['failure']==counts['error']==counts['skipped']==counts['duplicate_cases']==0,'junit':observed('complete-focused-03.xml'),'scope':'Host authored/mock controls plus genuine main compiler/native capture and historical replay; installed qualification is independently reported.','provider_billing_or_total_session_savings_established':False,'full_task_satisfaction_established':False,'source_equivalence_proved':False,'model_convergence_proved':False}
print(json.dumps(write('complete-validation-03.json',value)),flush=True)
raise SystemExit(0 if value['all_passed'] else 1)
