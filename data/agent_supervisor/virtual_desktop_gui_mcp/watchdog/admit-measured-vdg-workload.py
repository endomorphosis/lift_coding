"""Admit workload budgets derived from actual complete Local capture timing."""
import fcntl
import json
import re
import time
from pathlib import Path
from ipfs_accelerate_py.agent_supervisor.rescue.gate_recovery import admit_gate_repair_task
from ipfs_accelerate_py.agent_supervisor.rescue.supervisor_watchdog import parse_todo_task_fields

root = Path('/home/barberb/lift_coding')
w = root / 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog'
board = root / 'implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md'
sources = [
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/gate_recovery.py',
 'external/ipfs_accelerate/test/api/test_agent_supervisor_lane_resume_lifecycle.py',
 'external/ipfs_accelerate/test/api/test_agent_supervisor_gate_recovery.py',
 'swissknife/scripts/run-vdg-all-families.mjs', 'swissknife/scripts/verify-vdg-family.mjs',
 'swissknife/scripts/run-vdg-all-families.test.mjs', 'swissknife/scripts/verify-vdg-family.test.mjs',
 'swissknife/test/e2e/families/local-negative-mcp.spec.ts',
 'swissknife/scripts/build-family-mcp-spec.cjs', 'swissknife/scripts/vdg-local-todo-isolation.test.mjs',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-measured-vdg-workload.py',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/bundle_lanes.json']
command = 'python3 data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-measured-vdg-workload.py'
with (w/'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
 fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
 status = json.loads((w/'lanes/vdg-planning/vdg_planning_status.json').read_text())
 assert status['state'] == 'stopped' and status['terminal_reason'] == 'resume_stopped'
 assert json.loads((w/'repair-dispatcher.hold').read_text())['reason'] == 'controlled VDG completion repairs'
 original = board.read_text()
 before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
 assert 'VDG-013-R14' not in before
 assert before['VDG-039-R01']['status'] == 'pending'
 for source in sources:
  assert (root/source).is_file(), source
 result = admit_gate_repair_task(original, repo_root=root, task_id='VDG-039-R01',
  repair_task_id='VDG-013-R14', command=command, validation=command,
  predicted_files=sources, depends_on=['VDG-013-R13'], resource_class='cpu-small',
  implementation_timeout_seconds=1800,
  acceptance='Fit the real 2178-control Local workload measured at 7.07 seconds per model-card row with explicit bounded budgets: Local test21600 seconds, worker22200 including startup/finalchecks, paired batch46800, lane and CPU-browser explicit ceiling50400. Keep default1800 and other resource ceilings unchanged. Preserve all controls, real clicks, PNG/receipt verification, serialized same-family transports, existing task/refusal history, and all five unrelated family proofs. Full twelve current-source acquisitions, all six strict GO checks, aggregate GO and closeout remain mandatory.')
 text = result.pop('todo_text')
 parts = re.split(r'(?=^## VDG-)', text, flags=re.M)
 for index,block in enumerate(parts):
  if '\n- Status: pending\n' in block:
   block = re.sub(r'^- Predicted files: (.+)$',lambda m:'- Predicted files: '+', '.join(dict.fromkeys([v.strip() for v in m[1].split(',')]+sources)),block,flags=re.M)
  parts[index] = block
 text = ''.join(parts)
 parts = re.split(r'(?=^## VDG-)', text, flags=re.M)
 for index,block in enumerate(parts):
  task = block.split(' ', 2)[1] if block.startswith('## VDG-') else ''
  if task in {'VDG-039-R01', 'VDG-036-R03'}:
   assert '\n- Status: pending\n' in block, task
   block = block.replace('--timeout-seconds 10800', '--timeout-seconds 22200')
   block = re.sub(r'^- Implementation timeout seconds: \d+$', '- Implementation timeout seconds: 46800', block, flags=re.M)
  elif task in {'VDG-036-R01', 'VDG-036-R02'}:
   assert '\n- Status: pending\n' in block, task
   block = re.sub(r'^- Implementation timeout seconds: \d+$', '- Implementation timeout seconds: 25200', block, flags=re.M)
  parts[index] = block
 text = ''.join(parts)
 after = dict(parse_todo_task_fields(text,task_header_prefix='## VDG-'))
 assert all(after[key]['status'] == value['status'] for key,value in before.items())
 seen,active = set(),set()
 def visit(task):
  assert task in after and task not in active,task
  if task in seen:return
  active.add(task)
  for dep in after[task].get('depends_on','').split(','):
   if dep.strip():visit(dep.strip())
  active.remove(task);seen.add(task)
 for task in after:visit(task)
 (w/'completion-board-before-measured-vdg-workload.todo.snapshot').write_text(original)
 temporary = board.with_suffix('.measured-vdg-workload.tmp')
 temporary.write_text(text);temporary.replace(board)
 receipt = {'observed_at':time.time(),'tasks_before':len(before),'tasks_after':len(after),
  'statuses_preserved':True,'admission':result,'work_complete':False,'completion_authority':False}
 (w/'measured-vdg-workload-admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
