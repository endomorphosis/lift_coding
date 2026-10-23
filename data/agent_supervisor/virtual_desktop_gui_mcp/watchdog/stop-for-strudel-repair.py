"""Stop only the verified owned lane at the observed Strudel source failure."""
import json
import os
from pathlib import Path
import signal
import time

ROOT = Path(__file__).resolve().parents[4]
W = Path(__file__).resolve().parent
PID = 2722742
START = '700773409'
MODULE = 'ipfs_accelerate_py.agent_supervisor.rescue.lane_resume'
STATUS = W / 'lanes/vdg-planning/vdg_planning_status.json'


def identity():
    proc = Path(f'/proc/{PID}')
    tail = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    argv = [v.decode() for v in (proc / 'cmdline').read_bytes().split(b'\0') if v]
    assert tail[0] != 'Z' and tail[19] == START
    assert argv[1:3] == ['-m', MODULE]
    assert argv[argv.index('--repo-root') + 1] == str(ROOT)
    assert argv[argv.index('--bundle-key') + 1] == 'vdg-planning'
    assert argv[argv.index('--task-header-prefix') + 1] == '## VDG-'
    assert Path(argv[argv.index('--status-path') + 1]) == STATUS
    todo = Path(argv[argv.index('--todo-path') + 1])
    assert (todo if todo.is_absolute() else ROOT / todo) == ROOT / 'implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md'


def capture_processes():
    found = []
    scripts = {ROOT / 'swissknife/scripts' / name for name in ('run-vdg-family.mjs', 'run-vdg-all-families.mjs')}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            argv = [v.decode() for v in (proc / 'cmdline').read_bytes().split(b'\0') if v]
            if len(argv) > 1 and Path(argv[0]).name == 'node' and Path(argv[1]) in scripts:
                found.append(int(proc.name))
        except (OSError, UnicodeDecodeError):
            pass
    return found


identity()
hold = W / 'repair-dispatcher.hold'
held = {'reason': 'controlled VDG completion repairs', 'repair': 'Strudel actual missing showCreationInterface handler',
        'lane_pid': PID, 'start_ticks': START, 'observed_at': time.time()}
with hold.open('x') as handle:
    handle.write(json.dumps(held, indent=2) + '\n')
descriptor = os.pidfd_open(PID)
try:
    identity()
    signal.pidfd_send_signal(descriptor, signal.SIGTERM)
finally:
    os.close(descriptor)
deadline = time.monotonic() + 55
while time.monotonic() < deadline:
    status = json.loads(STATUS.read_text())
    captures = capture_processes()
    if (not Path(f'/proc/{PID}').exists() and status['state'] == 'stopped'
            and status['terminal_reason'] == 'resume_stopped' and not captures):
        receipt = {'observed_at': time.time(), 'old_lane_pid': PID, 'old_start_ticks': START,
                   'signal': 'single_pidfd_SIGTERM', 'old_process_absent': True,
                   'owned_capture_processes': captures, 'status': status, 'hold_preserved': True,
                   'source_boundary_verified': True, 'work_complete': False, 'completion_authority': False}
        (W / 'strudel-repair-stop.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt))
        break
    time.sleep(1)
else:
    raise SystemExit('Stop grace expired; hold retained, no escalation or source mutation authorized.')
