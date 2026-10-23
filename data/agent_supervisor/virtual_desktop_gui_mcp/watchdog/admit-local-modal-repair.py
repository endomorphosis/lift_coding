"""Record reproduced Local app overlays blocking subsequent real controls."""
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
sources = ['swissknife/web/js/apps/openrouter.js', 'swissknife/web/js/apps/cron.js',
 'swissknife/test/scripts/vdg-local-modal-ownership.test.mjs',
 'swissknife/test/e2e/smoke/vdg-local-modal-ownership-smoke.mjs']
command = ('node --test swissknife/test/scripts/vdg-local-modal-ownership.test.mjs '
 'swissknife/test/scripts/vdg-openrouter-catalog.test.mjs')
with (w/'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
 fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
 status = json.loads((w/'lanes/vdg-planning/vdg_planning_status.json').read_text())
 assert status['state'] == 'stopped' and status['terminal_reason'] == 'resume_stopped'
 assert json.loads((w/'repair-dispatcher.hold').read_text())['reason'] == 'controlled VDG completion repairs'
 original = board.read_text()
 before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
 assert 'VDG-013-R12' not in before and before['VDG-039-R01']['status'] == 'pending'
 for source in sources:
  assert (root/source).is_file(), source
 result = admit_gate_repair_task(original, repo_root=root, task_id='VDG-039-R01',
  repair_task_id='VDG-013-R12', command=command, validation=command,
  predicted_files=sources, depends_on=['VDG-013-R11'], resource_class='cpu-small',
  implementation_timeout_seconds=1800,
  acceptance='Repair actual OpenRouter Connect and Cron Settings overlays that block the trusted app Close button and survive window detachment to intercept Calculator controls. Scope modal surfaces to the owning app, settle and remove handlers when dismissed or detached, retain every existing model/control and stable semantic selector, and preserve truthful external-provider outcomes with zero MCP/provider write calls. Require focused regressions and separately recorded real Chrome before/after close-reopen-next-app proof; full current-source Local acquisition and strict both-transport GO remain mandatory.')
 text = result.pop('todo_text')
 parts = re.split(r'(?=^## VDG-)',text,flags=re.M)
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
 (w/'completion-board-before-local-modal.todo.snapshot').write_text(original)
 temporary=board.with_suffix('.local-modal.tmp');temporary.write_text(text);temporary.replace(board)
 receipt={'observed_at':time.time(),'tasks_before':len(before),'tasks_after':len(after),
  'statuses_preserved':True,'admission':result,'work_complete':False,'completion_authority':False}
 (w/'local-modal-admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
