from pathlib import Path
import hashlib,json,subprocess,os,time
q=Path(__file__).resolve().parent;c=q.parent/'terminal-token-reduction-20261007-01/checkout'
files=['benchmarks/agent_supervisor/container_coding/terminal_context_audit.py','benchmarks/agent_supervisor/container_coding/terminal_input_token_comparison.py']
def pins():
 return [{'path':r,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for r in files for b in [(c/r).read_bytes()]]
expected=json.loads((q/'runtime-source-pins.json').read_bytes())['files']
before=pins();assert before==expected
out=q/'root-final-02.stdout';err=q/'root-final-02.stderr';xml=q/'root-final-02.xml'
assert not out.exists() and not err.exists() and not xml.exists()
(q/'root-final-02-before.json').write_text(json.dumps({'files':before},sort_keys=True,indent=2)+'\n')
env=dict(os.environ)
env.update(IPFS_ACCELERATE_META_INDEX_DUCKDB=str(q/'root-final-02-meta.duckdb'),IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(q/'root-final-02-seal.duckdb'))
env['PYTHONPATH']=':'.join([str(q/'pinned-host-tokenizer'),str(c),str(q.parent/'terminal-compact-retrieval-20261011-01/pinned-dependencies-v10/datasets'),str(q.parent/'terminal-compact-retrieval-20261011-01/pinned-dependencies-v10/kit'),'/home/barberb/lift_coding/.venvs/terminal-bench-harbor/lib/python3.12/site-packages'])
argv=['/home/barberb/lift_coding/.venv/bin/python','-B','-m','pytest','-q','-ra','-o','addopts=','-o','log_cli=false','--junitxml='+str(xml),'benchmarks/agent_supervisor/container_coding/test_terminal_nomination_context_audit.py','benchmarks/agent_supervisor/container_coding/test_terminal_context_audit_budget.py']
started=time.monotonic()
with out.open('x') as o,err.open('x') as e:
 result=subprocess.run(argv,cwd=c,env=env,stdout=o,stderr=e,check=False)
after=pins();assert after==expected
value={'schema':'terminal-token-pair-focused-run@1','argv':argv,'returncode':result.returncode,'elapsed_seconds':time.monotonic()-started,'before_source_pins':before,'after_source_pins':after,'pins_unchanged_at_endpoints':True,'all_runtime_source_immutability_during_run_proved':False,'fresh_meta_database':env['IPFS_ACCELERATE_META_INDEX_DUCKDB'],'fresh_seal_database':env['IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB'],'junit':str(xml),'stdout':str(out),'stderr':str(err)}
(q/'root-final-02-run.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
print(json.dumps({'returncode':result.returncode,'elapsed_seconds':value['elapsed_seconds'],'junit':str(xml)}),flush=True)
raise SystemExit(result.returncode)
