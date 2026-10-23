"""Admit the actual storage-pressure supervisor repair without resetting task history."""
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
sources = ['external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/storage_pressure.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/supervisor_watchdog.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/watchdog_guardian.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/repair_dispatcher.py',
 'external/ipfs_accelerate/test/api/test_agent_supervisor_storage_pressure.py',
 'external/ipfs_accelerate/test/api/test_agent_supervisor_lane_resume_lifecycle.py',
 'external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_watchdog.py',
 'external/ipfs_accelerate/test/api/test_agent_supervisor_watchdog_guardian.py',
 'external/ipfs_accelerate/test/api/test_agent_supervisor_repair_dispatcher.py',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/resume-source-current-batch.py',
 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/bundle_lanes.json']
command = 'python3 external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/run_repo_pytest.py -q external/ipfs_accelerate/test/api/test_agent_supervisor_storage_pressure.py external/ipfs_accelerate/test/api/test_agent_supervisor_lane_resume_lifecycle.py external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_watchdog.py external/ipfs_accelerate/test/api/test_agent_supervisor_watchdog_guardian.py external/ipfs_accelerate/test/api/test_agent_supervisor_repair_dispatcher.py -c /dev/null --noconftest -p no:cacheprovider --tb=short'
with (w / 'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
    fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
    status = json.loads((w / 'lanes/vdg-planning/vdg_planning_status.json').read_text())
    hold = json.loads((w / 'repair-dispatcher.hold').read_text())
    assert hold.get('incident_kind') == 'storage_pressure' and hold.get('lane_pid') == status.get('pid')
    assert not Path(f"/proc/{status['pid']}").exists()
    assert json.loads((w / 'repair-dispatcher.hold').read_text())['reason'] == 'controlled VDG completion repairs'
    assert all((root / source).exists() for source in sources)
    original = board.read_text()
    before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
    assert 'VDG-013-R19' not in before and before['VDG-039-R01']['status'] == 'pending'
    assert before['VDG-013-R18']['status'] == 'completed'
    result = admit_gate_repair_task(
        original, repo_root=root, task_id='VDG-039-R01', repair_task_id='VDG-013-R19',
        command=command, validation=command, predicted_files=sources,
        depends_on=['VDG-013-R18'], resource_class='cpu-small', implementation_timeout_seconds=1800,
        acceptance='Repair the observed ENOSPC supervisor failure that killed the owned capture tree during heartbeat persistence, and the dispatcher/guardian storage-write crash loops. Classify only actual ENOSPC/EDQUOT; retain owned running work and stop/deadline bounds, publish explicit degraded emergency telemetry fenced to the independently expected owner role, UID, PID, start time, exact canonical path and freshness. Defer new work under actual capacity pressure without consuming repair/producer attempts; require successful durable filesystem probes and canonical writes before clearing degradation or accepting completion. Retry failed durable task and receipt commits in place without rerunning a successful producer. Preserve existing lock ownership through lock-header ENOSPC and all permission, process identity, lifetime and non-storage failures. Prove running-child survival, bounded cleanup, both storage errnos, spoof/stale marker refusal, durable recovery and ordinary control-plane regressions with fresh tests. Probe declared actual output roots including the storage-backed capture path. Resume only the verified dead incident owner under the existing lifecycle fence and explicit repair hold, without fabricating its stopped heartbeat. Preserve all task history, failure budgets, capture bytes and source fingerprints, then require the remaining real captures, six strict family GO gates, aggregate GO and closeout.')
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
    (w / 'completion-board-before-storage-pressure.todo.snapshot').write_text(original)
    temporary = board.with_suffix('.storage-pressure.tmp')
    temporary.write_text(amended)
    temporary.replace(board)
    receipt = {'observed_at': time.time(), 'tasks_before': len(before), 'tasks_after': len(after),
               'statuses_preserved': True, 'admission': result,
               'work_complete': False, 'completion_authority': False}
    (w / 'storage-pressure-admission.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
