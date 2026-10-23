"""Run real bounded workload regressions; this driver grants no GUI acceptance."""
import os
import json
import subprocess
import sys
from pathlib import Path

root = Path('/home/barberb/lift_coding')
profile = json.loads((root/'config/virtual_desktop_gui_mcp_supervisor.json').read_text())
assert profile['bounds']['masterDurationSeconds'] == 50400
assert profile['bounds']['browserTaskTimeoutSeconds'] == 46800
assert profile['bounds']['defaultTaskTimeoutSeconds'] == 1800
manifest = json.loads((root/'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/bundle_lanes.json').read_text())
lane = next(item for item in manifest['lanes'] if item['bundle_key'] == 'vdg-planning')
assert lane['max_resume_seconds'] == 50400
env = dict(os.environ, IPFS_TEST_PROOF_REUSE_MODE='off', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
commands = [
 [sys.executable, str(root/'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/run_repo_pytest.py'),
  '-q', str(root/'external/ipfs_accelerate/test/api/test_agent_supervisor_lane_resume_lifecycle.py'),
  str(root/'external/ipfs_accelerate/test/api/test_agent_supervisor_gate_recovery.py'),
  '-c', '/dev/null', '--noconftest', '-p', 'no:cacheprovider', '--tb=short'],
 ['node', '--test', str(root/'swissknife/scripts/run-vdg-all-families.test.mjs'),
  str(root/'swissknife/scripts/verify-vdg-family.test.mjs'),
  str(root/'swissknife/scripts/vdg-cli-inventory-guard.test.mjs'),
  str(root/'swissknife/scripts/vdg-local-todo-isolation.test.mjs')],
]
for command in commands:
 result = subprocess.run(command, cwd=root, env=env, timeout=1700)
 if result.returncode:
  raise SystemExit(result.returncode if result.returncode > 0 else 1)
