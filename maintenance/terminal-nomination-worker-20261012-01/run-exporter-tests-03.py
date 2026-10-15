from pathlib import Path
import hashlib,json,os,subprocess,sys,time
K=Path(__file__).resolve().parent
C=Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
TEST='benchmarks/agent_supervisor/container_coding/test_source_nomination_review_preparation.py'
FILES=[TEST,'benchmarks/agent_supervisor/container_coding/source_nomination_review_preparation.py','benchmarks/agent_supervisor/container_coding/terminal_indexed_preparation.py','benchmarks/agent_supervisor/container_coding/terminal_initial_context.py','benchmarks/agent_supervisor/container_coding/terminal_public_intent_contract.py','ipfs_accelerate_py/agent_supervisor/runtime/code_source_inspection.py','ipfs_accelerate_py/agent_supervisor/runtime/intent_source_inspection.py','ipfs_accelerate_py/agent_supervisor/runtime/intent_source_nomination.py','ipfs_accelerate_py/agent_supervisor/runtime/code_retrieval_context.py','ipfs_accelerate_py/agent_supervisor/runtime/code_retrieval_frontier.py','ipfs_accelerate_py/agent_supervisor/analysis/code_symbol_vector_index.py']
def pins():
 return [{'path':n,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for n in FILES for raw in [(C/n).read_bytes()]]
def write(n,v):
 with (K/n).open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
before=pins();write('exporter-validation-03-before-pins.json',{'files':before})
env=dict(os.environ);env.update(PYTHONPATH=os.pathsep.join((str(C),'/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01/pinned-dependencies-v10/datasets','/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01/pinned-dependencies-v10/kit',str(K))),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(K/'fresh-seal-exporter-03.duckdb'))
env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
argv=[sys.executable,'-P','-m','pytest','-q',TEST,'--junitxml='+str(K/'exporter-validation-03.xml'),'--basetemp='+str(K/'tests-exporter-03'),'-o','cache_dir='+str(K/'pytest-cache-exporter-03')]
t0=time.monotonic()
with (K/'exporter-validation-03.stdout').open('x') as out,(K/'exporter-validation-03.stderr').open('x') as err:r=subprocess.run(argv,cwd=C,env=env,stdout=out,stderr=err)
after=pins();write('exporter-validation-03-after-pins.json',{'files':after})
write('exporter-validation-03-run.json',{'argv':argv,'python':sys.executable,'returncode':r.returncode,'seconds':time.monotonic()-t0,'source_pins_unchanged':before==after,'scope':'26 explicit exporter-fence tests; native public AST/index/frontier/capture/publication, admission/initial-context/owner observations stubbed. No live signed admission/deployment qualification.','provider_calls':0,'training_steps':0,'prover_invocations':0,'target_module_imports':0,'private_owner_database_reads':0})
print(json.dumps({'returncode':r.returncode,'source_pins_unchanged':before==after,'seconds':time.monotonic()-t0}))
