"""Declare the measured full VDG capture workload under explicit bounds."""
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
]
command = ('python3 external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/run_repo_pytest.py '
           '-c /dev/null --noconftest -p no:cacheprovider -q ' + ' '.join(sources[2:]))
with (w / 'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
 fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
 original = board.read_text()
 before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
 assert 'VDG-013-R06' not in before
 result = admit_gate_repair_task(original, repo_root=root, task_id='VDG-039-R01',
  repair_task_id='VDG-013-R06', command=command, validation=command, predicted_files=sources,
  depends_on=['VDG-013-R05'], resource_class='cpu-small', implementation_timeout_seconds=1800,
  acceptance='Verify an explicit cpu-browser workload bound of 25200 seconds survives board parsing and reaches the producer. Keep browser defaults and all other resource class limits unchanged; reject admission above the explicit eight-hour maximum. This source regression does not grant capture completion or any GO.')
 text = result.pop('todo_text')
 parts = re.split(r'(?=^## VDG-)', text, flags=re.M)
 for index, block in enumerate(parts):
  if '\n- Status: pending\n' not in block:
   continue
  if block.startswith('## VDG-039-R01 '):
   block = re.sub(r'^- Deterministic command: .+$',
    '- Deterministic command: node swissknife/scripts/run-vdg-all-families.mjs --timeout-seconds 10800', block, flags=re.M)
   block = re.sub(r'^- Implementation timeout seconds: .+$', '- Implementation timeout seconds: 25200', block, flags=re.M)
   block += '\n- Workload basis: Live DOM inventory has 2178 local controls per transport, including 1881 OpenRouter controls. Real warm clicks measured about 3.94 seconds each. Allow 10800 seconds per transport and 25200 seconds for both transports plus the other families; useful progress remains subject to watchdog evidence checks.\n'
  elif re.match(r'## VDG-03[1-6]-R0[34] ', block):
   block = re.sub(r'^- Deterministic command: (node swissknife/scripts/verify-vdg-family.mjs vdg-\w+)(?: .*)?$',
    r'- Deterministic command: \1 --timeout-seconds 10800', block, flags=re.M)
   block = re.sub(r'^- Implementation timeout seconds: .+$', '- Implementation timeout seconds: 25200', block, flags=re.M)
  elif re.match(r'## VDG-03[1-6]-R0[12] ', block):
   block = re.sub(r'^- Implementation timeout seconds: .+$', '- Implementation timeout seconds: 14400', block, flags=re.M)
  if not block.startswith('## VDG-013-R06 '):
   block = re.sub(r'^- Predicted files: (.+)$',lambda m:'- Predicted files: '+', '.join(dict.fromkeys([v.strip() for v in m[1].split(',')]+sources)),block,flags=re.M)
  parts[index] = block
 text = ''.join(parts)
 after = dict(parse_todo_task_fields(text, task_header_prefix='## VDG-'))
 assert all(after[key]['status'] == value['status'] for key,value in before.items())
 seen, active = set(),set()
 def visit(task):
  assert task in after and task not in active,task
  if task in seen:return
  active.add(task)
  for dep in after[task].get('depends_on','').split(','):
   if dep.strip():visit(dep.strip())
  active.remove(task);seen.add(task)
 for task in after:visit(task)
 (w/'completion-board-before-workload-bounds.todo.snapshot').write_text(original)
 temp = board.with_suffix('.workload.tmp');temp.write_text(text);temp.replace(board)
 receipt={'observed_at':time.time(),'tasks_before':len(before),'tasks_after':len(after),
  'statuses_preserved':True,'admission':result,'transport_timeout_seconds':10800,
  'batch_timeout_seconds':25200,'work_complete':False,'completion_authority':False}
 (w/'capture-workload-bounds-admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
