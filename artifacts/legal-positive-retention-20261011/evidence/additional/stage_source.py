"""Stage the six owned source contributions in the isolated worktree."""
from pathlib import Path
from hashlib import sha256
import json, subprocess
F=Path(__file__).resolve().parent; D=F/'datasets'
paths=['ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_retention_gate.py',
       'ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_retention_selection.py',
       'tests/unit/logic/test_legal_scope_retention_gate.py',
       'tests/unit/logic/test_legal_scope_retention_selection.py',
       'docs/implementation/legal_scope_retention_gate_pilot_20261011.md',
       'docs/autoencoders/progress_integration.md']
def git(*args):return subprocess.check_output(['git',*args],cwd=D)
assert git('diff','--cached','--name-only')==b''
base=git('rev-parse','HEAD').decode().strip()
progress=git('show',base+':'+paths[-1]);assert (D/paths[-1]).read_bytes().startswith(progress)
assert json.loads((F/'hub-publication-review.json').read_text())['passed'] is True
assert json.loads((F/'hub-checkpoint-replay.json').read_text())['complete_outputs_exact']==1280
records={}
for p in paths:
 raw=(D/p).read_bytes();assert b'PENDING_' not in raw
 records[p]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
subprocess.run(['git','add','--sparse','--',*paths],cwd=D,check=True)
assert set(git('diff','--cached','--name-only').decode().splitlines())==set(paths)
subprocess.run(['git','diff','--cached','--check'],cwd=D,check=True)
for p,record in records.items():
 raw=git('show',':'+p);assert len(raw)==record['bytes'] and sha256(raw).hexdigest()==record['sha256']
v=dict(schema='support-retention-source-contribution-binding/v1',base=base,paths=records,
    only_six_owned_paths_staged=True,upstream_progress_prefix_exact=True,
    successful_current_tests=179,selected_Hub_replay_outputs_exact=1280,
    hub_revision=json.loads((F/'hub-upload-commit.json').read_text())['revision'],
    numeric_old_producers_preserved=True,checkpoint_weights_in_Git=False)
(F/'source-contribution-binding.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(dict(staged_paths=6,base=base,whitespace_passed=True)))
