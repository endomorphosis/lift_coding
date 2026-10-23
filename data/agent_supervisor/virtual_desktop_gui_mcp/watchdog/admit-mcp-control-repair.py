"""Admit the actual MCP Control load, dialog and false-GO repair without resetting history."""
import fcntl
import json
from pathlib import Path
import re
import time

from ipfs_accelerate_py.agent_supervisor.rescue.gate_recovery import admit_gate_repair_task
from ipfs_accelerate_py.agent_supervisor.rescue.supervisor_watchdog import parse_todo_task_fields

root = Path(__file__).resolve().parents[4]
w = Path(__file__).resolve().parent
board = root / 'implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md'
sources = ['swissknife/web/js/apps/mcp-control.js',
 'swissknife/test/scripts/vdg-mcp-control-mounted.test.mjs',
 'swissknife/test/e2e/smoke/vdg-mcp-control-mounted-smoke.mjs',
 'swissknife/test/e2e/families/control-plane-mcp-invoke.spec.ts',
 'swissknife/scripts/build-family-mcp-spec.cjs',
 'swissknife/scripts/vdg-control-primary-mount.test.mjs',
 'swissknife/scripts/vdg-local-todo-isolation.test.mjs',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-openrouter-case-cost-diagnostic.py',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-mcp-control-repair.py']
command = 'python3 data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-mcp-control-repair.py'
with (w / 'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
    fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
    status = json.loads((w / 'lanes/vdg-planning/vdg_planning_status.json').read_text())
    assert status['state'] == 'stopped' and status['terminal_reason'] == 'resume_stopped'
    assert not Path(f"/proc/{status['pid']}").exists()
    assert json.loads((w / 'repair-dispatcher.hold').read_text())['reason'] == 'controlled VDG completion repairs'
    assert all((root / source).exists() for source in sources)
    original = board.read_text()
    before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
    assert 'VDG-013-R18' not in before and before['VDG-039-R01']['status'] == 'pending'
    assert before['VDG-013-R17']['status'] == 'pending'
    result = admit_gate_repair_task(
        original, repo_root=root, task_id='VDG-039-R01', repair_task_id='VDG-013-R18',
        command=command, validation=command, predicted_files=sources,
        depends_on=['VDG-013-R17'], resource_class='cpu-small', implementation_timeout_seconds=1800,
        acceptance='Repair the actual MCP Control module syntax failure, owned dialogs intercepting titlebar Close, and literal unmeasured metric claims. Prove the real registered desktop factory mounts the primary MCP Control UI without the app-error fallback, all affected native dialog actions support trusted close and reopen, displayed metrics remain truthful, and both requested profiles pass actual source-bound Chrome diagnostics with no unexpected POSTs or page errors. Add the Control-only per-launch primary-app guard so working generic gateway controls cannot hide a failed main app and exact launch timeout text cannot bypass it. Preserve exact Local and all other family spec bytes; require generated-spec parity. Retain the immutable prior OpenRouter experiment archive while honestly allowing this Control-only generator change in its validator. Require a real fresh source-bound inventory exposing the previously missing primary controls, fresh Control and Local canonical captures, all six strict GO gates, aggregate GO and closeout. Preserve task history, actual source identities, owner proof requirements, workload bounds, lifecycle fences and unaffected-family evidence.')
    amended = result.pop('todo_text')
    parts = re.split(r'(?=^## VDG-)', amended, flags=re.M)
    for index, block in enumerate(parts):
        if '\n- Status: pending\n' in block:
            block = re.sub(r'^- Predicted files: (.+)$', lambda match: '- Predicted files: ' + ', '.join(dict.fromkeys([value.strip() for value in match[1].split(',')] + sources)), block, flags=re.M)
        parts[index] = block
    amended = ''.join(parts)
    after = dict(parse_todo_task_fields(amended, task_header_prefix='## VDG-'))
    assert all(after[key]['status'] == value['status'] for key, value in before.items())
    seen, active = set(), set()
    def visit(task):
        assert task in after and task not in active, task
        if task in seen:
            return
        active.add(task)
        for dependency in after[task].get('depends_on', '').split(','):
            if dependency.strip():
                visit(dependency.strip())
        active.remove(task)
        seen.add(task)
    for task in after:
        visit(task)
    (w / 'completion-board-before-mcp-control.todo.snapshot').write_text(original)
    temporary = board.with_suffix('.mcp-control.tmp')
    temporary.write_text(amended)
    temporary.replace(board)
    receipt = {'observed_at': time.time(), 'tasks_before': len(before), 'tasks_after': len(after),
               'statuses_preserved': True, 'admission': result,
               'work_complete': False, 'completion_authority': False}
    (w / 'mcp-control-admission.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
