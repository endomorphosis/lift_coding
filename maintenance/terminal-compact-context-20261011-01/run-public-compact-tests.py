"""Retain fresh-seal real-public-fixture checks and exact producer snapshots."""
import contextlib
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time

import pytest

attempt = Path(sys.argv[1]).absolute()
attempt.mkdir(mode=0o700, exist_ok=False)
test_path = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout/benchmarks/agent_supervisor/container_coding/test_terminal_compact_intent_experiment.py')
names = (
    'ipfs_accelerate_py.agent_supervisor.runtime.compact_intent_requirements',
    'ipfs_accelerate_py.agent_supervisor.runtime.router_public_instruction',
    'ipfs_accelerate_py.agent_supervisor.runtime.intent_requirement_context',
    'ipfs_accelerate_py.agent_supervisor.runtime.local_planning_admission',
    'ipfs_accelerate_py.agent_supervisor.planning.intent_symbolic_planning',
    'ipfs_accelerate_py.agent_supervisor.prompt.intent_plan_coverage',
    'benchmarks.agent_supervisor.container_coding.terminal_public_intent_contract',
    'benchmarks.agent_supervisor.container_coding.terminal_indexed_preparation',
)
modules = {name: importlib.import_module(name) for name in names}

def pin(path):
    raw = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def write(path, raw):
    with path.open('xb') as handle:
        handle.write(raw)

before = {name: pin(module.__file__) for name, module in modules.items()}
before['test_source'] = pin(test_path)
os.environ['IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB'] = str(attempt / 'fresh-pytest-seal.duckdb')
os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(attempt / 'fresh-meta-index.duckdb')
argv = ['-c', '/dev/null', '--noconftest', '-p', 'no:cacheprovider',
        '-p', 'ipfs_accelerate_py.testing.pytest_ast_seal', '-q', str(test_path),
        '--junitxml=' + str(attempt / 'tests.xml')]
command = {'schema': 'terminal-public-compact-intent-test-command@1', 'argv': sys.argv,
    'pytest_argv': argv, 'cwd': os.getcwd(), 'source_pins_before': before,
    'environment': {key: os.environ.get(key) for key in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB', 'IPFS_ACCELERATE_META_INDEX_DUCKDB')},
    'scope': 'Real public instruction and authored tiny Git fixture; actual scanner/symbolic planner/coverage/signatures/context/codec/loader; no provider, hidden verifier, original indexes, training or external proving.'}
write(attempt / 'command.json', (json.dumps(command, indent=2, sort_keys=True) + '\n').encode())
write(attempt / 'test-source.py', test_path.read_bytes())
write(attempt / 'test-driver.py', Path(__file__).read_bytes())
for name, module in modules.items():
    write(attempt / (name + '.py'), Path(module.__file__).read_bytes())
start = time.monotonic()
with (attempt / 'stdout.txt').open('x') as stdout, (attempt / 'stderr.txt').open('x') as stderr:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = int(pytest.main(argv))
after = {name: pin(module.__file__) for name, module in modules.items()}
after['test_source'] = pin(test_path)
result = {'schema': 'terminal-public-compact-intent-test-result@1', 'pytest_exit_code': code,
          'elapsed_seconds': time.monotonic() - start, 'sources_unchanged': before == after,
          'source_pins_before': before, 'source_pins_after': after}
write(attempt / 'result.json', (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
print(json.dumps(result, sort_keys=True))
sys.exit(code if before == after else 98)
