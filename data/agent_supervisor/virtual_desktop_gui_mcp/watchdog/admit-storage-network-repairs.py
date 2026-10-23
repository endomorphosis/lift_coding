"""Record independently reproduced keyboard and native-status repairs."""
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
repairs = [
 ('VDG-013-R09', 'swissknife/test/scripts/vdg-storage-native-apps.test.mjs', [
  'swissknife/web/js/apps/image-viewer.js', 'swissknife/web/js/apps/media-player.js',
  'swissknife/test/scripts/vdg-storage-native-apps.test.mjs',
  'swissknife/test/e2e/smoke/vdg-storage-native-smoke.mjs'],
  'Verify CID Enter is consumed by the CID submission and cannot also activate the newly focused owner-consent Cancel button. Preserve zero requests before separate trusted confirmation, exact declared tool/transport bindings and truthful content reads. Real six-case browser proof is retained separately; full Storage acquisition and strict GO remain mandatory.'),
 ('VDG-013-R10', 'swissknife/test/scripts/vdg-network-native-apps.test.mjs', [
  'swissknife/web/js/apps/p2p-chat-unified.js',
  'swissknife/test/scripts/vdg-network-native-apps.test.mjs',
  'swissknife/test/e2e/smoke/vdg-unified-p2p-native-smoke.mjs'],
  'Verify Unified P2P Chat preserves the actual native tool/correlation/outcome/receipt status across root rerenders and clears prior proof before each action, including cancellation and owner failure. Retain actual archive state and truthful nonpersistent previews. Real HTTP/libp2p Chrome proof is retained separately; full Network acquisition and strict GO remain mandatory.'),
]
with (w/'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
 fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
 original = board.read_text()
 before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
 text, admissions = original, []
 for task, test, sources, acceptance in repairs:
  assert task not in before
  for source in sources:
   assert (root/source).is_file(), source
  command = 'node --test ' + test
  result = admit_gate_repair_task(text, repo_root=root, task_id='VDG-039-R01',
   repair_task_id=task, command=command, validation=command, predicted_files=sources,
   depends_on=['VDG-013-R08'], resource_class='cpu-small', implementation_timeout_seconds=1800,
   acceptance=acceptance)
  text = result.pop('todo_text');admissions.append(result)
 all_sources = list(dict.fromkeys(source for _,_,sources,_ in repairs for source in sources))
 parts = re.split(r'(?=^## VDG-)',text,flags=re.M)
 for index,block in enumerate(parts):
  if '\n- Status: pending\n' in block and not any(block.startswith('## '+task+' ') for task,_,_,_ in repairs):
   block = re.sub(r'^- Predicted files: (.+)$',lambda m:'- Predicted files: '+', '.join(dict.fromkeys([v.strip() for v in m[1].split(',')]+all_sources)),block,flags=re.M)
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
 (w/'completion-board-before-storage-network.todo.snapshot').write_text(original)
 temporary=board.with_suffix('.storage-network.tmp');temporary.write_text(text);temporary.replace(board)
 receipt={'observed_at':time.time(),'tasks_before':len(before),'tasks_after':len(after),
  'statuses_preserved':True,'admissions':admissions,'work_complete':False,'completion_authority':False}
 (w/'storage-network-admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
