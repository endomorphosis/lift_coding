"""Qualify published child against the newer preserved datasets pin; no Git writes."""
from __future__ import annotations
import collections
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

PARENT=Path(__file__).resolve().parents[2]
PHASE=Path(__file__).resolve().parent
CHILD=Path('/home/barberb/lift_coding/.worktrees/router-signed-scope-closing-20261014')
DATASETS=Path('/home/barberb/lift_coding/.worktrees/router-signed-scope-closing-datasets-20261014')
KIT=Path('/home/barberb/lift_coding/.worktrees/repository-proof-context-kit-20261014')
CHILD_REVISION='cb104896f55a28352feb8cd35c4b9991144c933a'
DATASETS_REVISION='eb18ab0d24557de46d9bd804e8da69d41049874f'
KIT_REVISION='40c98c71b95be750509ffdb21e7e5494d91b4e79'
INPUTS=CHILD/'docs/agent_supervisor/evidence/router-signed-scope-closing-20261014'

def git(root,*args): return subprocess.check_output(['git','--no-optional-locks',*args],cwd=root)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,data): path.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
def state(root): return dict(head=git(root,'rev-parse','HEAD').decode().strip(),index_sha256=sha(git(root,'ls-files','--stage','-z')),refs_sha256=sha(git(root,'for-each-ref','--format=%(refname) %(objectname)')))
def bindings():
 rows=[]
 for row in json.loads((INPUTS/'source-inventory.json').read_text()):
  owner=CHILD if row['repository']=='accelerator' else DATASETS
  raw=(owner/row['path']).read_bytes()
  revision=CHILD_REVISION if owner==CHILD else DATASETS_REVISION
  assert raw==git(owner,'show',revision+':'+row['path']),row['path']
  rows.append(dict(row,bytes=len(raw),sha256=sha(raw),source_checkout=str(owner),matches_immutable_git_object=True))
 return rows

def main():
 if len(sys.argv)!=2 or re.fullmatch(r'dependency-qualification-[0-9]{2}',sys.argv[1]) is None: raise SystemExit('Exact attempt directory required')
 attempt=PHASE/sys.argv[1]; attempt.mkdir(exist_ok=False)
 roots=(PARENT,CHILD,DATASETS,KIT); guards={str(root):state(root) for root in roots}
 assert guards[str(CHILD)]['head']==CHILD_REVISION and guards[str(DATASETS)]['head']==DATASETS_REVISION and guards[str(KIT)]['head']==KIT_REVISION
 assert all(not git(root,'status','--porcelain') for root in roots[1:])
 before=bindings(); targets=json.loads((INPUTS/'targets.json').read_text()); assert len(before)==268 and len(targets)==8
 script=Path(__file__).read_bytes(); (attempt/'runner.snapshot.txt').write_bytes(script)
 snapshots=[]
 original=json.loads((INPUTS/'qualification-02/commands.json').read_text())
 for row in before:
  old=next(old for old in original['before'] if (old['repository'],old['path'])==(row['repository'],row['path']))
  if row['sha256']!=old['sha256']:
   assert row['repository']=='datasets_execution_checkout'
   target=attempt/'source-snapshot'/(row['path']+'.snapshot.txt'); target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes((DATASETS/row['path']).read_bytes()); snapshots.append(dict(row,snapshot=str(target.relative_to(PARENT))))
 assert len(snapshots)==6
 private=Path(tempfile.mkdtemp(prefix='router-new-datasets-'+sys.argv[1]+'-'))
 updates=dict(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',PYTHONHASHSEED='0',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',IPFS_DATASETS_PY_LAZY_INSTALL_ERGOAI='0',IPFS_KIT_DISABLE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONPATH=os.pathsep.join(map(str,(CHILD,DATASETS,KIT))),IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(private/'orchestration'),IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(private/'seal.duckdb'))
 removed=('IPFS_ACCELERATE_AGENT_STATE_OWNER_SOCKET','IPFS_ACCELERATE_AGENT_QUACK_TOKEN','IPFS_ACCELERATE_META_INDEX_DUCKDB','IPFS_ACCELERATE_META_INDEX_DUCKLAKE','PYTEST_ADDOPTS','PYTEST_PLUGINS','IPFS_TEST_PROOF_REUSE_MODE')
 env=os.environ.copy()
 for key in removed: env.pop(key,None)
 env.update(updates)
 argv=[sys.executable,'-B','-m','pytest','-c','pytest.ini',*targets,'--color=no','--basetemp='+str(private/'pytest-temp'),'-o','log_cli=false','-o','cache_dir='+str(private/'pytest-cache'),'--tb=short','--maxfail=1','--junitxml='+str(attempt/'junit.xml')]
 report=dict(schema='router-signed-scope-closing-new-datasets-qualification@1',status='running',started_at_utc=utc(),child_revision=CHILD_REVISION,datasets_execution_revision=DATASETS_REVISION,kit_execution_revision=KIT_REVISION,parent_merge=guards[str(PARENT)]['head'],targets=targets,argv=argv,cwd=str(CHILD),interpreter=sys.executable,interpreter_version=sys.version,platform=platform.platform(),distribution_versions={name:importlib.metadata.version(name) for name in ('pytest','duckdb','cryptography','numpy')},before=before,git_state_before=guards,changed_dataset_snapshots=snapshots,runner_snapshot=dict(path=str((attempt/'runner.snapshot.txt').relative_to(PARENT)),bytes=len(script),sha256=sha(script)),environment_updates=updates,inherited_environment_names_removed=list(removed),private_runtime_directory=str(private),source_binding_scope='listed_dependencies_not_complete_import_closure',previous_counts_added=False,external_provider_calls=0,model_calls=0,training_steps=0,native_solver_or_kernel_executions=0,authored_provider_stubs_exercised=True,actual_inert_socket_client_probes=True,worker_uid_qualified=False,production_coding_child_adoption=False,official_task_result=None,proof_authority=False,execution_authority=False,completion_authority=False,total_session_token_savings_established=False)
 write(attempt/'commands.json',report); print('Starting eight complete suites against six updated dataset modules.',flush=True)
 started=time.monotonic()
 with (attempt/'tests.stdout.log').open('wb') as out,(attempt/'tests.stderr.log').open('wb') as err: result=subprocess.run(argv,cwd=CHILD,env=env,stdout=out,stderr=err)
 report.update(completed_at_utc=utc(),elapsed_seconds=round(time.monotonic()-started,3),pytest_exit_code=result.returncode,after=bindings(),git_state_after={str(root):state(root) for root in roots})
 for name in ('junit.xml','tests.stdout.log','tests.stderr.log'):
  raw=(attempt/name).read_bytes(); report[name]=dict(bytes=len(raw),sha256=sha(raw))
 xml=ET.parse(attempt/'junit.xml').getroot(); cases=[(c.get('classname'),c.get('name')) for c in xml.iter('testcase')]
 counts=re.findall(r'^(?:collecting \.\.\. )?collected ([0-9]+) items?\s*$',(attempt/'tests.stdout.log').read_text(errors='replace'),re.M)
 outcome=dict(tests=len(cases),failures=sum(1 for _ in xml.iter('failure')),errors=sum(1 for _ in xml.iter('error')),skipped=sum(1 for _ in xml.iter('skipped')))
 report.update(junit=outcome,collected_tests=int(counts[0]) if len(counts)==1 else None,distinct_junit_cases=len(set(cases)),new_cases=sum(suite=='benchmarks.agent_supervisor.container_coding.test_terminal_signed_working_set_closing' for suite,_ in cases),suites=dict(collections.Counter(suite for suite,_ in cases)),source_before_after_equal=report['before']==report['after'],git_state_unchanged=report['git_state_before']==report['git_state_after'])
 passed=(result.returncode==0 and outcome==dict(tests=145,failures=0,errors=0,skipped=0) and report['collected_tests']==len(set(cases))==145 and report['new_cases']==18 and report['source_before_after_equal'] and report['git_state_unchanged'])
 report['status']='pass' if passed else 'fail'; write(attempt/'commands.json',report)
 print(json.dumps({key:report[key] for key in ('status','junit','new_cases','elapsed_seconds')}),flush=True)
 return 0 if passed else 1

if __name__=='__main__': raise SystemExit(main())
