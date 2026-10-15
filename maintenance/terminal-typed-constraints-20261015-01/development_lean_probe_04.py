"""Retained actual compile of accepted finite authored mathematical fixtures."""
import hashlib
import json
from constraint_lean import ROOT,build_lean_theory,_run_lean
from constraint_io import inputs
from scheduler_constraints import build_scheduler_contract,authored_cases
from native_structural_ir import _scheduler
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
_,bodies,instructions,_=inputs()
head=json.loads((ROOT.parent/'terminal-intent-coverage-20261015-01'/'experiment-02'/'structural-report.json').read_bytes())['head']
contract=build_scheduler_contract(instruction=instructions['llm-inference-batching-scheduler'],head=head,
    source_records=[{'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'source_text':raw.decode()} for name,raw in sorted(bodies.items())])
theory=build_lean_theory(contract=contract,cases=authored_cases())
output=ROOT/'development-fixture-lean-04';output.mkdir(mode=0o700)
with _scheduler().acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=2048,child_process_slots=1,
    timeout=30,request_id='terminal-typed-constraints:development-fixture-proof') as lease:
    report=_run_lean(source=theory['sources'][0]['source'],label='authored-fixtures',output=output,lease=lease,expected_success=True)
print(json.dumps({'status':report['status'],'stdout':report['stdout'],'stderr':report['stderr']}))
if not report['matches_expectation']:raise SystemExit(1)
