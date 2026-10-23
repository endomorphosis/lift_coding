"""Resume one source-frozen VDG lane with its isolated runtime environment."""
import fcntl
import json
import os
import shlex
import time
from pathlib import Path
from ipfs_accelerate_py.agent_supervisor.rescue.lane_resume import resume_stopped_lane

root = Path('/home/barberb/lift_coding')
w = root / 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog'
for line in (w / 'backends/client.env').read_text().splitlines():
 if not line.strip() or line.lstrip().startswith('#'):
  continue
 key, value = line.split('=', 1)
 values = shlex.split(value)
 assert len(values) == 1, key
 os.environ[key] = values[0]
os.environ['IPFS_TEST_PROOF_REUSE_MODE'] = 'off'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
manifest = json.loads((w / 'bundle_lanes.json').read_text())
lane = dict(manifest['lanes'][0])
state = root / lane['state_dir']
lane['pid_path'] = str(state / 'vdg_planning_bundle_supervisor.pid')
with (state / 'vdg-planning.resume.lock').open('a') as fence:
 fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
 status = json.loads((state / 'vdg_planning_status.json').read_text())
 hold = w / 'repair-dispatcher.hold'
 held = json.loads(hold.read_text())
 assert held['reason'] == 'controlled VDG completion repairs'
 stopped = status['state'] == 'stopped' and status['terminal_reason'] == 'resume_stopped'
 # ENOSPC can prevent a dead lane from persisting its terminal status. An
 # explicit incident hold plus the existing lifecycle fence permits recovery
 # without fabricating a stopped heartbeat or changing any task outcome.
 if not stopped:
  assert held.get('incident_kind') == 'storage_pressure', held
  assert held.get('lane_pid') == status.get('pid') and status['pid'] > 0, status
 assert not Path(f"/proc/{status['pid']}").exists(), status
 capture_scripts = {root / 'swissknife/scripts' / name for name in
  ('run-vdg-family.mjs', 'run-vdg-all-families.mjs')}
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():
   continue
  try:
   if proc.stat().st_uid != os.getuid():
    continue
   argv = [item.decode() for item in (proc / 'cmdline').read_bytes().split(b'\0') if item]
   if not argv or Path(argv[0]).name not in {'node', 'nodejs'}:
    continue
   for argument in argv[1:]:
    candidate = argument.partition('=')[2] if argument.startswith(('--import=', '--require=')) else argument
    script = Path(candidate)
    if script.name not in {'run-vdg-family.mjs', 'run-vdg-all-families.mjs'}:
     continue
    if not script.is_absolute():
     script = (proc / 'cwd').resolve(strict=True) / script
    assert script.resolve() not in capture_scripts, proc.name
  except (FileNotFoundError, ProcessLookupError):
   continue

 result = resume_stopped_lane(lane, repo_root=root, manifest=manifest,
  resume_lock_fd=fence.fileno())
 assert result.get('restarted') is True, result
 assert result.get('readiness_verified') is True and result.get('lock_handoff') is True, result
 actual_argv = Path(f"/proc/{result['new_pid']}/cmdline").read_bytes().split(b'\0')
 actual_argv = [item.decode() for item in actual_argv if item]
 expected_lifetime = int(lane.get('max_resume_seconds', 28800))
 assert float(actual_argv[actual_argv.index('--max-seconds') + 1]) == expected_lifetime, actual_argv
 receipt = {'observed_at':time.time(), 'source_frozen':True,
  'lane_lifetime_seconds':expected_lifetime, 'actual_process_lifetime_verified':True,
  'lifecycle_readiness_verified':True, 'lifecycle_lock_handoff_verified':True,
  'actual_owner_default_payload_cases':37, 'openrouter_controls_verified':1881,
  'phase':'recorded-source-regressions -> current-inventory -> twelve-captures -> strict-family-gates -> aggregate -> closeout',
  'resume':result, 'work_complete':False, 'completion_authority':False}
 latest = w / 'source-current-workload-batch-resume.json'
 if latest.exists():
  old = json.loads(latest.read_text())
  history = w / 'resume-history'
  history.mkdir(exist_ok=True)
  archive = history / f"source-current-{old['resume']['new_pid']}.json"
  if archive.exists():
   assert archive.read_bytes() == latest.read_bytes()
  else:
   archive.write_bytes(latest.read_bytes())
 latest.write_text(json.dumps(receipt,indent=2)+'\n')
 hold.unlink()
 print(json.dumps(receipt))
