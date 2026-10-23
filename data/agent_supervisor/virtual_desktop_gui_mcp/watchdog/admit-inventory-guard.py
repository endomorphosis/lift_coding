"""Admit executable freshness/native regressions without rewriting history."""
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
    'swissknife/scripts/vdg-inventory-contract.test.cjs',
    'swissknife/scripts/refresh-vdg-inventory.test.mjs',
    'swissknife/scripts/vdg-cli-inventory-guard.test.mjs',
    'swissknife/scripts/vdg-capture-fingerprint.test.cjs',
    'swissknife/scripts/run-vdg-family.test.mjs',
    'swissknife/scripts/run-vdg-all-families.test.mjs',
    'swissknife/scripts/verify-vdg-family.test.mjs',
    'swissknife/scripts/check-vdg-capture.test.cjs',
    'swissknife/scripts/check-vdg-family-evidence.test.cjs',
    'swissknife/scripts/vdg-capture-checkpoint.test.cjs',
    'swissknife/test/scripts/vdg-dataset-native-apps.test.mjs',
    'swissknife/test/scripts/vdg-openrouter-catalog.test.mjs',
    'swissknife/test/scripts/vdg-dataset-default-payloads.test.mjs',
]
sources = [
    'swissknife/scripts/vdg-inventory-contract.cjs',
    'swissknife/scripts/vdg-capture-fingerprint.cjs',
    'swissknife/scripts/refresh-vdg-inventory.mjs',
    'swissknife/scripts/run-rendered-census.mjs',
    'swissknife/scripts/prepare-vdg-rendered-inputs.cjs',
    'swissknife/scripts/run-vdg-family.mjs',
    'swissknife/scripts/run-vdg-all-families.mjs',
    'swissknife/scripts/verify-vdg-family.mjs',
    'swissknife/scripts/check-vdg-family-evidence.cjs',
    'swissknife/web/js/apps/ai-chat.js',
    'swissknife/web/js/apps/openrouter.js',
    'swissknife/web/js/apps/huggingface.js',
]

with (w / 'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
    fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
    original = board.read_text()
    before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
    assert 'VDG-013-R05' not in before
    assert before['VDG-039-R01']['status'] == 'pending'
    for item in tests + sources:
        assert (root / item).is_file(), item
    result = admit_gate_repair_task(
        original, repo_root=root, task_id='VDG-039-R01', repair_task_id='VDG-013-R05',
        command='node --test ' + ' '.join(tests), validation='node --test ' + ' '.join(tests),
        predicted_files=sources + tests, depends_on=['VDG-013-R04'],
        acceptance='Verify source-bound census freshness, one locked automatic refresh after a genuine source repair, read-only checks, per-family checkpoint preservation, exact independent report integrity, and actual AI Chat prompt/context behavior. This implementation task grants no family GO or completion authority.',
        resource_class='cpu-small', implementation_timeout_seconds=1800,
    )
    text = result.pop('todo_text')
    active = None
    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith('## '):
            active = line[3:].split(' ', 1)[0].strip()
        if active in before and before[active]['status'] == 'pending' and line.startswith('- Predicted files:'):
            existing = [part.strip() for part in line.split(':', 1)[1].strip().split(',') if part.strip()]
            line = '- Predicted files: ' + ', '.join(dict.fromkeys(existing + sources + tests)) + '\n'
        lines.append(line)
    text = ''.join(lines)
    after = dict(parse_todo_task_fields(text, task_header_prefix='## VDG-'))
    assert all(after[key]['status'] == value['status'] for key, value in before.items())
    seen, stack = set(), set()
    def visit(task):
        assert task in after, task
        assert task not in stack, task
        if task in seen:
            return
        stack.add(task)
        for dep in after[task].get('depends_on', '').split(','):
            if dep.strip():
                visit(dep.strip())
        stack.remove(task)
        seen.add(task)
    for task in after:
        visit(task)
    (w / 'completion-board-before-inventory-guard.todo.snapshot').write_text(original)
    temporary = board.with_suffix('.inventory-guard.tmp')
    temporary.write_text(text)
    temporary.replace(board)
    receipt = {'observed_at':time.time(), 'tasks_before':len(before), 'tasks_after':len(after),
               'statuses_preserved':True, 'admission':result, 'work_complete':False, 'completion_authority':False}
    (w / 'inventory-guard-admission.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
