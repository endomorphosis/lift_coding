"""Admit the observed Strudel behavior and source-binding repair without resetting history."""
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
sources = [
    'swissknife/web/js/apps/strudel-grandma.js',
    'swissknife/web/js/apps/strudel.js',
    'swissknife/test/scripts/vdg-strudel-grandma-controls.test.mjs',
    'swissknife/test/scripts/vdg-strudel-source-binding.test.mjs',
    'swissknife/test/e2e/smoke/vdg-strudel-grandma-controls-smoke.mjs',
    'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-strudel-controls-repair.py',
]
command = 'python3 data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-strudel-controls-repair.py'
with (w / 'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
    fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
    status = json.loads((w / 'lanes/vdg-planning/vdg_planning_status.json').read_text())
    assert status['state'] == 'stopped' and status['terminal_reason'] == 'resume_stopped'
    assert not Path(f"/proc/{status['pid']}").exists()
    assert json.loads((w / 'repair-dispatcher.hold').read_text())['reason'] == 'controlled VDG completion repairs'
    assert all((root / source).exists() for source in sources)
    original = board.read_text()
    before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
    assert 'VDG-013-R17' not in before and before['VDG-039-R01']['status'] == 'pending'
    assert before['VDG-013-R16']['status'] == 'completed'
    result = admit_gate_repair_task(
        original, repo_root=root, task_id='VDG-039-R01', repair_task_id='VDG-013-R17',
        command=command, validation=command, predicted_files=sources,
        depends_on=['VDG-013-R16'], resource_class='cpu-small', implementation_timeout_seconds=1800,
        acceptance='Repair the actual-browser Strudel creation and tutorial exceptions and active-playback close cleanup. Verify real local melody editing, validation, WebAudio playback and stop, tutorial progression, repeated mount and cleanup using the exact original controls and a source-bound real Chrome diagnostic with no provider or MCP POSTs. Bind the actual factory-imported implementation through the declared Strudel source compatibility symlink; prove implementation changes invalidate both Local transport fingerprints while unrelated family fingerprints remain unchanged. Require a real source-current inventory refresh and new affected canonical captures; never relabel the old failed checkpoint or diagnostic as GUI acceptance. Preserve completed task history, workload limits, lifecycle ownership, source refusal budgets and valid unaffected-family proofs. Completion still requires all six strict family GO gates, aggregate GO and closeout.')
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
    (w / 'completion-board-before-strudel-controls.todo.snapshot').write_text(original)
    temporary = board.with_suffix('.strudel-controls.tmp')
    temporary.write_text(amended)
    temporary.replace(board)
    receipt = {'observed_at': time.time(), 'tasks_before': len(before), 'tasks_after': len(after),
               'statuses_preserved': True, 'admission': result,
               'work_complete': False, 'completion_authority': False}
    (w / 'strudel-controls-admission.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
