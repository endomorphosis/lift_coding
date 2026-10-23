"""Preserve task history while recording the measured no-change decision."""
import fcntl
import json
from pathlib import Path
import re
import time

from ipfs_accelerate_py.agent_supervisor.rescue.supervisor_watchdog import parse_todo_task_fields

root = Path(__file__).resolve().parents[4]
w = Path(__file__).resolve().parent
board = root / 'implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md'
validator = 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-openrouter-case-cost-diagnostic.py'
command = 'python3 ' + validator
with (w / 'lanes/vdg-planning/vdg-planning.resume.lock').open('a') as fence:
    fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
    status = json.loads((w / 'lanes/vdg-planning/vdg_planning_status.json').read_text())
    assert status['state'] == 'stopped' and status['terminal_reason'] == 'resume_stopped'
    assert not Path('/proc/2112582').exists()
    assert json.loads((w / 'repair-dispatcher.hold').read_text())['reason'] == 'controlled VDG completion repairs'
    original = board.read_text()
    before = dict(parse_todo_task_fields(original, task_header_prefix='## VDG-'))
    assert before['VDG-013-R15']['status'] == 'pending'
    parts = re.split(r'(?=^## VDG-)', original, flags=re.M)
    for index, block in enumerate(parts):
        if block.startswith('## VDG-013-R15 '):
            block = re.sub(r'^## VDG-013-R15 .*$', '## VDG-013-R15 Validate OpenRouter cost diagnostic and preserve current proof', block, flags=re.M)
            block = re.sub(r'^- Deterministic command: .*$', '- Deterministic command: ' + command, block, flags=re.M)
            block = re.sub(r'^- Validation: .*$', '- Validation: ' + command, block, flags=re.M)
            block = re.sub(r'^- Acceptance: .*$', '- Acceptance: Validate the archived actual 48-case paired OpenRouter diagnostic, all 96 original screenshot hashes, full 468-model catalog and 1881 original selectors, genuine trusted actions, zero provider/MCP POSTs, and exact restored canonical Local source bytes with all eight Todo/regeneration regressions. Recompute the measured 6.13 percent speed gain and recapture cost; reject optional OpenRouter state isolation because losing 596 source-bound rows costs more than the measured remaining-work savings. Preserve the original Local fingerprints, Todo isolation, all five completed-family proofs, every real control, quiet/consent checks, and workload limits. This diagnostic grants no GUI acceptance: require actual full Local captures, all six strict family GO checks, aggregate GO, and closeout.', block, flags=re.M)
        if '\n- Status: pending\n' in block:
            block = re.sub(r'^- Predicted files: (.+)$', lambda m: '- Predicted files: ' + ', '.join(dict.fromkeys([v.strip() for v in m[1].split(',')] + [validator])), block, flags=re.M)
        parts[index] = block
    amended = ''.join(parts)
    after = dict(parse_todo_task_fields(amended, task_header_prefix='## VDG-'))
    assert before.keys() == after.keys()
    assert all(after[key]['status'] == value['status'] and after[key].get('depends_on') == value.get('depends_on') for key, value in before.items())
    (w / 'completion-board-before-openrouter-diagnostic-decision.todo.snapshot').write_text(original)
    temporary = board.with_suffix('.diagnostic-decision.tmp')
    temporary.write_text(amended)
    temporary.replace(board)

    prompt = w / 'supervisor-repair.prompt.txt'
    old = prompt.read_text()
    start = old.index("The same Local fixture isolates OpenRouter's favorites")
    end = old.index('For a proved runtime-only recovery', start)
    replacement = (
        'A paired 48-case OpenRouter diagnostic measured only a 6.13 percent gain\n'
        'from optional per-case favorite/settings/history isolation. Exact catalog\n'
        'selectors remain valid with accumulated favorites. The candidate was rejected\n'
        'because recapturing 596 valid source-bound rows costs more than its measured\n'
        'remaining-work savings. Canonical Local source is restored byte-for-byte.\n'
        'Preserve those checkpoints and the existing Todo-only isolation. The archived\n'
        'candidate is diagnostic-only and grants no capture or acceptance authority.\n'
        'Do not reintroduce that performance hypothesis without new evidence that\n'
        'justifies its total cost. Preserve every catalog model/control and actual\n'
        'quiet checks; complete the unchanged-source captures and strict gates.\n'
    )
    prompt.write_text(old[:start] + replacement + old[end:])
    receipt = {'observed_at': time.time(), 'tasks': len(after), 'statuses_and_dependencies_preserved': True,
               'task': 'VDG-013-R15', 'decision': 'rollback_optional_isolation', 'validator': command,
               'work_complete': False, 'completion_authority': False}
    (w / 'openrouter-diagnostic-decision-amendment.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
