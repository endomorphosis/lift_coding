"""Admit observed Local Todo capture-state isolation repair."""
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
sources = ['swissknife/test/e2e/families/local-negative-mcp.spec.ts',
 'swissknife/scripts/build-family-mcp-spec.cjs',
 'swissknife/scripts/vdg-local-todo-isolation.test.mjs',
 'swissknife/test/e2e/smoke/vdg-local-todo-isolation-smoke.mjs']
command = 'node --test swissknife/scripts/vdg-local-todo-isolation.test.mjs'
with (w/'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
 fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
 status = json.loads((w/'lanes/vdg-planning/vdg_planning_status.json').read_text())
 assert status['state'] == 'stopped' and status['terminal_reason'] == 'resume_stopped'
 assert json.loads((w/'repair-dispatcher.hold').read_text())['reason'] == 'controlled VDG completion repairs'
 original = board.read_text()
 before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
 assert 'VDG-013-R13' not in before
 assert before['VDG-039-R01']['status'] == 'pending'
 for source in sources:
  assert (root/source).is_file(), source
 result = admit_gate_repair_task(original, repo_root=root, task_id='VDG-039-R01',
  repair_task_id='VDG-013-R13', command=command, validation=command,
  predicted_files=sources, depends_on=['VDG-013-R12'], resource_class='cpu-small',
  implementation_timeout_seconds=1800,
  acceptance='Isolate real Local Todo control cases by restoring the exact original values or absence of swissknife-todos and swissknife-goals only after the owning test window closes or the page resets. Preserve actual checkbox/delete actions, actual persisted changes while open, original before/after screenshots, every current census control, zero MCP calls, and unrelated storage keys. Keep the fixture executable in the Local spec and retained by regeneration; no shared capture or fingerprint changes. Require focused regressions and a separately recorded real Chrome run of all 18 current Todo controls including the original destructive sequence. Full current-source Local acquisitions and strict both-transport GO remain mandatory; all five unrelated family proofs stay unchanged.')
 text = result.pop('todo_text')
 parts = re.split(r'(?=^## VDG-)', text, flags=re.M)
 for index,block in enumerate(parts):
  if '\n- Status: pending\n' in block:
   block = re.sub(r'^- Predicted files: (.+)$',lambda m:'- Predicted files: '+', '.join(dict.fromkeys([v.strip() for v in m[1].split(',')]+sources)),block,flags=re.M)
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
 (w/'completion-board-before-local-todo-isolation.todo.snapshot').write_text(original)
 temporary = board.with_suffix('.local-todo-isolation.tmp')
 temporary.write_text(text);temporary.replace(board)
 receipt = {'observed_at':time.time(),'tasks_before':len(before),'tasks_after':len(after),
  'statuses_preserved':True,'admission':result,'work_complete':False,'completion_authority':False}
 (w/'local-todo-isolation-admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
