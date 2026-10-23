"""One retained native generic-math development compile; no invented receipt."""
from pathlib import Path
import json
from constraint_lean import ROOT,MODEL,GENERIC_THEOREMS,_run_lean
from native_structural_ir import _scheduler
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
output=ROOT/'development-generic-lean-02'
output.mkdir(mode=0o700)
source=MODEL+''.join('#print axioms '+name+'\n' for name in GENERIC_THEOREMS)+'end SchedulerConstraint\n'
with _scheduler().acquire(ResourceLane.ORCHESTRATION,cpu_slots=1,memory_mb=2048,child_process_slots=1,
    timeout=30,request_id='terminal-typed-constraints:development-generic-proof') as lease:
    report=_run_lean(source=source,label='generic-proof',output=output,lease=lease,expected_success=True)
print(json.dumps({'status':report['status'],'stdout':report['stdout'],'stderr':report['stderr']}))
if not report['matches_expectation']:raise SystemExit(1)
