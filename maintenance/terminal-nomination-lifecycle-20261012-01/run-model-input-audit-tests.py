"""Retain observer-audit unit/regression runs with pinned local dependencies."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, time
p=argparse.ArgumentParser();p.add_argument('--attempt',required=True);p.add_argument('--regressions',action='store_true');args=p.parse_args()
m=Path(__file__).resolve().parent;c=m.parent/'terminal-token-reduction-20261007-01/checkout';prior=m.parent/'terminal-compact-retrieval-20261011-01/pinned-dependencies-v10'
a=m/('model-input-audit-attempt-'+args.attempt);a.mkdir()
new='benchmarks/agent_supervisor/container_coding/test_terminal_model_input_observation_audit.py'
tests=[new]
if args.regressions:tests+=['benchmarks/agent_supervisor/container_coding/test_terminal_context_audit.py','benchmarks/agent_supervisor/container_coding/test_terminal_nomination_context_audit.py']
sources=[new,'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py','benchmarks/agent_supervisor/container_coding/terminal_model_input_observation_audit.py','benchmarks/agent_supervisor/container_coding/test_terminal_context_audit.py','benchmarks/agent_supervisor/container_coding/test_terminal_nomination_context_audit.py','ipfs_accelerate_py/agent_supervisor/runtime/model_input_observation_receipt.py','ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_audit.py','ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_context.py','ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py','ipfs_accelerate_py/agent_supervisor/runtime/supervisor_meta_index.py','ipfs_accelerate_py/agent_supervisor/runtime/compact_code_retrieval.py','ipfs_accelerate_py/agent_supervisor/runtime/verified_code_retrieval_projection.py','ipfs_accelerate_py/agent_supervisor/runtime/router_public_instruction.py','ipfs_accelerate_py/agent_supervisor/runtime/semantic_router_translation.py','ipfs_accelerate_py/agent_supervisor/context/context_compiler.py']
def pins():return {s:{'bytes':len((c/s).read_bytes()),'sha256':hashlib.sha256((c/s).read_bytes()).hexdigest()} for s in sources}
before=pins();(a/'source-pins-before.json').write_text(json.dumps(before,sort_keys=True,indent=2))
for s in sources:
 q=a/'sources'/s;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((c/s).read_bytes())
roots=[c,prior/'datasets',prior/'kit'];env={**os.environ,'PYTHONPATH':':'.join(map(str,roots)),'PYTHONDONTWRITEBYTECODE':'1','IPFS_ACCELERATE_META_INDEX_DUCKDB':str(a/'fresh-meta.duckdb'),'IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR':str(a/'fresh-orchestration'),'IPFS_TEST_PROOF_REUSE_MODE':'off','IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB':str(a/'fresh-seals.duckdb')};env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
argv=['/home/barberb/lift_coding/.venv/bin/python','-B','-P','-m','pytest',*tests,'-q','--color=no','-o','addopts=','-o','log_cli=false','-p','ipfs_accelerate_py.testing.pytest_ast_seal','--junitxml='+str(a/'tests.xml'),'--basetemp='+str(a/'tmp')]
(a/'argv.json').write_text(json.dumps(argv,indent=2));(a/'environment.json').write_text(json.dumps({'interpreter':argv[0],'trusted_import_roots':list(map(str,roots)),'fresh_metadata':env['IPFS_ACCELERATE_META_INDEX_DUCKDB'],'fresh_seal':env['IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB'],'proof_reuse':'off','no_provider_calls':True},sort_keys=True,indent=2))
started=time.monotonic()
with (a/'stdout.txt').open('w') as out,(a/'stderr.txt').open('w') as err:r=subprocess.run(argv,cwd=c,env=env,stdout=out,stderr=err)
after=pins();(a/'source-pins-after.json').write_text(json.dumps(after,sort_keys=True,indent=2));(a/'exit.json').write_text(json.dumps({'returncode':r.returncode,'seconds':time.monotonic()-started,'pins_unchanged':before==after},sort_keys=True,indent=2));print(json.dumps({'returncode':r.returncode,'pins_unchanged':before==after,'attempt':str(a)}))
