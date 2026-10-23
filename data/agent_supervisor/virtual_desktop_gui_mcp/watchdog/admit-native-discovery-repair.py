"""Track the observed duplicate-native discovery repair without erasing proof."""
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
tests = [
 'swissknife/scripts/live-click-discovery.test.cjs',
 'swissknife/scripts/live-click-compound-confirmation.test.cjs',
 'swissknife/scripts/rendered-control-rows.test.mjs',
 'swissknife/scripts/vdg-evidence.test.cjs',
 'swissknife/scripts/refresh-vdg-inventory.test.mjs',
 'swissknife/scripts/vdg-inventory-contract.test.cjs',
 'swissknife/scripts/vdg-cli-inventory-guard.test.mjs',
]
sources = [
 'swissknife/test/e2e/helpers/live-click-session.ts',
 'swissknife/scripts/refresh-vdg-inventory.mjs',
 'swissknife/scripts/vdg-inventory-contract.cjs',
 'swissknife/scripts/rendered-control-rows.mjs',
 'swissknife/scripts/vdg-evidence.cjs',
]
with (w/'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
 fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
 original = board.read_text()
 before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
 assert 'VDG-013-R07' not in before
 assert before['VDG-039-R01']['status'] == 'pending'
 command = 'node --test ' + ' '.join(tests)
 result = admit_gate_repair_task(original, repo_root=root, task_id='VDG-039-R01',
  repair_task_id='VDG-013-R07', command=command, validation=command,
  predicted_files=sources+tests, depends_on=['VDG-013-R06'],
  resource_class='cpu-small', implementation_timeout_seconds=1800,
  acceptance='Use actual Chrome DOM regressions to prove root-relative matrix selectors identify their original controls without duplicate unsupported extras, including repeated native binding/tool attributes. Preserve all declared controls and true unknown-control NO_GO obligations. Verify real flock/eval imports do not run the CLI twice. Full source-current captures and strict both-transport GO remain mandatory.')
 text = result.pop('todo_text')
 parts = re.split(r'(?=^## VDG-)',text,flags=re.M)
 for index,block in enumerate(parts):
  if '\n- Status: pending\n' in block:
   block = re.sub(r'^- Predicted files: (.+)$',lambda m:'- Predicted files: '+', '.join(dict.fromkeys([v.strip() for v in m[1].split(',')]+sources+tests)),block,flags=re.M)
  parts[index] = block
 text = ''.join(parts)
 after = dict(parse_todo_task_fields(text,task_header_prefix='## VDG-'))
 assert all(after[key]['status'] == value['status'] for key,value in before.items())
 (w/'completion-board-before-native-discovery.todo.snapshot').write_text(original)
 temporary = board.with_suffix('.native-discovery.tmp');temporary.write_text(text);temporary.replace(board)
 receipt = {'observed_at':time.time(),'tasks_before':len(before),'tasks_after':len(after),
  'statuses_preserved':True,'observed_failure':'declared root-relative controls duplicated as unsupported live-control extras',
  'admission':result,'work_complete':False,'completion_authority':False}
 (w/'native-discovery-admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
