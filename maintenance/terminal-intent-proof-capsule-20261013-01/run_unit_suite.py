"""Combined final U unit suite under fresh namespaces and pinned dependencies."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

U = Path(__file__).resolve().parent
C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
os.umask(0o077)
baseline = json.loads((U / 'baseline-manifest.json').read_bytes())
paths = [Path(value['path']) for value in baseline['new_sources']]
def pins():
    return [{'path':str(path),'bytes':len(raw:=path.read_bytes()),'sha256':hashlib.sha256(raw).hexdigest()} for path in paths]
before = pins()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
    IPFS_ACCELERATE_META_INDEX_DUCKDB=str(U/'test-final-meta.duckdb'),
    IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB=str(U/'test-final-seal.duckdb'),
    IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR=str(U/'test-final-orchestration'))
env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE', None)
args = [sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
    '--basetemp='+str(U/'test-final-tmp'), '--junitxml='+str(U/'test-final.xml'),
    'test/api/test_terminal_call_intent_profile.py', 'test/api/test_terminal_call_proof_capsule.py',
    'test/api/test_terminal_call_intent_planning.py']
started = time.monotonic()
with (U/'test-final.stdout').open('xb') as stdout, (U/'test-final.stderr').open('xb') as stderr:
    completed = subprocess.run(args, cwd=C, env=env, stdout=stdout, stderr=stderr, timeout=180)
elapsed = int((time.monotonic()-started)*1000)
(U/'test-final.xml').chmod(0o600)
root = ET.fromstring((U/'test-final.xml').read_bytes())
cases = list(root.iter('testcase'))
identities = [(case.get('classname'),case.get('name')) for case in cases]
assert len(identities)==len(set(identities))
after=pins()
report={'schema':'terminal-call-intent-final-tests@1','command':args,'exit_code':completed.returncode,
    'elapsed_milliseconds':elapsed,'tests':len(cases),
    'failures':len(list(root.iter('failure'))),'errors':len(list(root.iter('error'))),
    'skipped':len(list(root.iter('skipped'))),'unique_identities':len(set(identities)),
    'sources_before':before,'sources_after':after,'all_sources_unchanged':before==after,
    'provider_calls':0,'training_steps':0,'checker_invocations':0,'source_body_executed':False}
path=U/'test-final-run.json';path.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');path.chmod(0o600)
print(json.dumps({key:report[key] for key in ('exit_code','tests','failures','errors','skipped','all_sources_unchanged')}))
assert completed.returncode==0 and before==after and len(cases)==223
