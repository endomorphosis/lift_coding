"""Track the observed Neural Photoshop layout/native-control repair."""
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
sources = ['swissknife/web/js/apps/neural-photoshop.js',
 'swissknife/test/scripts/vdg-neural-photoshop-truth.test.mjs',
 'swissknife/test/e2e/smoke/vdg-neural-photoshop-native-smoke.mjs']
command = 'node --test swissknife/test/scripts/vdg-neural-photoshop-truth.test.mjs'
with (w/'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
 fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
 original = board.read_text()
 before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
 assert 'VDG-013-R08' not in before
 assert before['VDG-039-R01']['status'] == 'pending'
 result = admit_gate_repair_task(original, repo_root=root, task_id='VDG-039-R01',
  repair_task_id='VDG-013-R08', command=command, validation=command,
  predicted_files=sources, depends_on=['VDG-013-R07'], resource_class='cpu-small',
  implementation_timeout_seconds=1800,
  acceptance='Verify the actual Neural Photoshop factory retains exact native bindings, truthful owner previews, real confirmation, bounded inputs and idempotent mounted handlers after its layout/panel repair. The isolated real Chrome default-window and HTTP/libp2p native smoke is a separate recorded prerequisite; full source-current Accelerate acquisition and strict both-transport GO remain mandatory. Preserve completed unrelated family proof and resumable checkpoints.')
 text = result.pop('todo_text')
 parts = re.split(r'(?=^## VDG-)',text,flags=re.M)
 for index,block in enumerate(parts):
  if '\n- Status: pending\n' in block:
   block = re.sub(r'^- Predicted files: (.+)$',lambda m:'- Predicted files: '+', '.join(dict.fromkeys([v.strip() for v in m[1].split(',')]+sources)),block,flags=re.M)
  parts[index] = block
 text = ''.join(parts)
 after = dict(parse_todo_task_fields(text,task_header_prefix='## VDG-'))
 assert all(after[key]['status'] == value['status'] for key,value in before.items())
 (w/'completion-board-before-neural-photoshop.todo.snapshot').write_text(original)
 temporary = board.with_suffix('.neural-photoshop.tmp');temporary.write_text(text);temporary.replace(board)
 receipt = {'observed_at':time.time(),'tasks_before':len(before),'tasks_after':len(after),
  'statuses_preserved':True,'observed_failure':'Neural Photoshop canvas obscured panels and native actions in the default window',
  'admission':result,'work_complete':False,'completion_authority':False}
 (w/'neural-photoshop-admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
