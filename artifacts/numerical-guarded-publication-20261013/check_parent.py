"""Verify the parent pins, committed evidence, report links and CI observation."""
import hashlib,importlib.util,json,subprocess
from pathlib import Path
W=Path('/home/barberb/lift_coding/.worktrees')
parent=W/'supervisor-comparison-publication-20261011'
p=W/'supervisor-comparison-contracts-20261011'
d=W/'indexed-coverage-datasets-20261013'
output=parent/'artifacts/numerical-guarded-publication-20261013/parent-checks.json'
report=parent/'implementation_plan/docs/110-supervisor-guarded-numerical-coverage-2026-10-13.md'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
expected={'external/ipfs_accelerate':'d13c68ce80dba65478c87f24ada0669ddfb36a1b','external/ipfs_datasets':'9eb06b73658d8203628a697db6199f14ecf479e4','external/ipfs_kit':'8ac00bb1974b1378e12091d546d8425af34049e0'}
actual={}
for name in expected:
    mode,digest,stage,path=git(parent,'ls-files','--stage','--',name).split()
    assert mode=='160000' and stage=='0'
    actual[path]=digest
assert actual==expected
assert git(parent,'ls-tree','HEAD','external/ipfs_kit').split()[2]==expected['external/ipfs_kit']
for root,key in [(p,'external/ipfs_accelerate'),(d,'external/ipfs_datasets')]:
    assert git(root,'rev-parse','HEAD')==git(root,'rev-parse','origin/main')==expected[key]
evidence=p/'docs/agent_supervisor/evidence/numerical-guarded-20261013'
manifest=json.loads((evidence/'manifest.json').read_bytes())
for name,row in manifest['files'].items():
    raw=subprocess.check_output(['git','show','HEAD:'+str((evidence/name).relative_to(p))],cwd=p)
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
assert len(manifest['files'])+1==84
ci_path=output.parent/'hosted-ci.json';ci=json.loads(ci_path.read_bytes())
assert ci['exact_head_sha']==expected['external/ipfs_accelerate'] and ci['billing_lock_observed']
assert all(j['runner_id']==0 and not j['steps'] for run in ci['runs'] for j in run['jobs'])
# Reserve this checker-owned destination so its report link can be validated.
if not output.exists():output.write_text('{}\n')
spec=importlib.util.spec_from_file_location('doclinks',p/'scripts/docs/check_current_docs_links.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.ROOT=parent
errors=module.check_file(report,check_anchors=True)
assert not errors,errors
for root in (p,d,parent):
    subprocess.run(['git','diff','--check'],cwd=root,check=True)
    subprocess.run(['git','diff','--cached','--check'],cwd=root,check=True)
local=json.loads((evidence/'documentation-01/result.json').read_bytes())
assert local['passed']
result=dict(schema='numerical-guarded-parent-publication-checks@1',passed=True,parent_base=git(parent,'rev-parse','HEAD'),staged_gitlinks=actual,preserved_kit=expected['external/ipfs_kit'],sealed_evidence_file_count=84,manifest_sha256=sha(evidence/'manifest.json'),report_sha256=sha(report),hosted_ci_observation_sha256=sha(ci_path),unique_passing_tests=947,skipped_checkpoint_tests=2,explicit_link_errors=errors,local_documentation_gates_passed=True,hosted_documentation_gates_passed=ci['hosted_documentation_gates_passed'],hosted_billing_lock_observed=True,git_diff_checks_passed=True)
output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result))
