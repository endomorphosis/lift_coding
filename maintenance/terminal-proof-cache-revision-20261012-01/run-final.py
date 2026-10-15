from pathlib import Path
import hashlib,json,os,subprocess,time
R=Path(__file__).resolve().parent
C=R.parent/'terminal-token-reduction-20261007-01/checkout'
def pins():
 rows=json.loads((R/'final-source-pins.json').read_bytes())['files']
 for row in rows:
  b=Path(row['path']).read_bytes()
  assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
 return rows
env=dict(os.environ)
env.update(PYTHONDONTWRITEBYTECODE='1',TIKTOKEN_CACHE_DIR='/tmp/data-gym-cache',
 IPFS_ACCELERATE_META_INDEX_DUCKDB=str(R/'final-meta.duckdb'),
 IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(R/'final-seal.duckdb'),
 IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(R/'final-orchestration'))
env['PYTHONPATH']=':'.join([str(R/'pinned-host-duckdb'),str(R.parent/'terminal-token-pairing-20261012-01/pinned-host-tokenizer'),str(C),str(R.parent/'terminal-compact-retrieval-20261011-01/pinned-dependencies-v10/datasets'),str(R.parent/'terminal-compact-retrieval-20261011-01/pinned-dependencies-v10/kit'),'/home/barberb/lift_coding/.venvs/terminal-bench-harbor/lib/python3.12/site-packages'])
before=pins()
xml=R/'final-tests-01.xml'
args=['/home/barberb/lift_coding/.venv/bin/python','-B','-m','pytest','-q','-ra','-o','addopts=','-o','log_cli=false','--junitxml='+str(xml),
 'test/api/test_terminal_revision_metadata.py','test/api/test_terminal_revision_proof_cache.py',
 'test/api/test_agent_supervisor_cross_domain_proof_scope.py',
 'test/api/test_agent_supervisor_proof_scope_index.py',
 'test/api/test_codebase_ir_metadata_restart_paths.py']
started=time.monotonic()
with (R/'final-tests-01.stdout').open('x') as out,(R/'final-tests-01.stderr').open('x') as err:
 result=subprocess.run(args,cwd=C,env=env,stdout=out,stderr=err,check=False)
after=pins()
report={'argv':args,'returncode':result.returncode,'elapsed_seconds':time.monotonic()-started,
 'before_source_pins':before,'after_source_pins':after,'source_pins_unchanged_at_endpoints':before==after,
 'continuous_loaded_code_attestation':False,'junit':str(xml)}
with (R/'final-tests-01-run.json').open('x') as f:json.dump(report,f,sort_keys=True,indent=2)
print(json.dumps({k:report[k] for k in ['returncode','elapsed_seconds','junit']}),flush=True)
if result.returncode:raise SystemExit(result.returncode)
env.update(IPFS_ACCELERATE_META_INDEX_DUCKDB=str(R/'actual-meta.duckdb'),
 IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(R/'actual-seal.duckdb'),
 IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(R/'actual-orchestration'))
with (R/'actual-public-revision-01.stdout').open('x') as out,(R/'actual-public-revision-01.stderr').open('x') as err:
 result=subprocess.run(['/home/barberb/lift_coding/.venv/bin/python','-B',str(R/'qualify-public-revision-cache.py')],cwd=C,env=env,stdout=out,stderr=err,check=False)
pins()
print(json.dumps({'actual_returncode':result.returncode}),flush=True)
raise SystemExit(result.returncode)
