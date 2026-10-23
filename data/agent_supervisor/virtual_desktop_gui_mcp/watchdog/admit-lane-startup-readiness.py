"""Admit the observed launch-fence failure without altering task history."""
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
    'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py',
    'external/ipfs_accelerate/test/api/test_agent_supervisor_lane_resume_lifecycle.py',
    'external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_watchdog.py',
    'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/resume-source-current-batch.py',
]
command = ('python3 external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/run_repo_pytest.py -q '
           'external/ipfs_accelerate/test/api/test_agent_supervisor_lane_resume_lifecycle.py '
           'external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_watchdog.py '
           '-c /dev/null --noconftest -p no:cacheprovider --tb=short')
with (w / 'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
    fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
    status = json.loads((w / 'lanes/vdg-planning/vdg_planning_status.json').read_text())
    assert status['state'] == 'stopped' and status['terminal_reason'] == 'resume_stopped'
    assert not Path('/proc/2681269').exists()
    assert json.loads((w / 'repair-dispatcher.hold').read_text())['reason'] == 'controlled VDG completion repairs'
    original = board.read_text()
    before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
    assert 'VDG-013-R16' not in before and before['VDG-039-R01']['status'] == 'pending'
    result = admit_gate_repair_task(
        original, repo_root=root, task_id='VDG-039-R01', repair_task_id='VDG-013-R16',
        command=command, validation=command, predicted_files=sources,
        depends_on=['VDG-013-R15'], resource_class='cpu-small', implementation_timeout_seconds=1800,
        acceptance='Repair the observed parent-held lifecycle flock launch race and false spawn-only success. Transfer a verified exact lifecycle fence to the owned child without an unlock window; require bounded readiness acknowledgement after the child acquires ownership and publishes its own PID and startup heartbeat. Reject wrong inherited descriptors, duplicate/live owners, exited children, and unready startups; clean only the launched failed process. Prove the delayed-parent handoff and failure paths with real process regressions and preserve all workload limits, intentional holds, source refusal budgets, five completed-family proofs and all source-bound Local checkpoints. Require actual remaining full captures, six strict GO gates, aggregate GO and closeout before completion.')
    amended = result.pop('todo_text')
    parts = re.split(r'(?=^## VDG-)', amended, flags=re.M)
    for index, block in enumerate(parts):
        if '\n- Status: pending\n' in block:
            block = re.sub(r'^- Predicted files: (.+)$', lambda m: '- Predicted files: ' + ', '.join(dict.fromkeys([v.strip() for v in m[1].split(',')] + sources)), block, flags=re.M)
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
    (w / 'completion-board-before-lane-startup-readiness.todo.snapshot').write_text(original)
    temporary = board.with_suffix('.startup-readiness.tmp')
    temporary.write_text(amended)
    temporary.replace(board)
    receipt = {'observed_at': time.time(), 'tasks_before': len(before), 'tasks_after': len(after),
               'statuses_preserved': True, 'admission': result,
               'work_complete': False, 'completion_authority': False}
    (w / 'lane-startup-readiness-admission.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
