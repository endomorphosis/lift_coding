"""Capture isolated native frontier qualification and loaded producer pins."""
from pathlib import Path
import contextlib
import hashlib
import importlib
import json
import os
import sys
import time

import pytest

ROOT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
TEST = ROOT / 'test/api/semantic_state/test_code_retrieval_frontier.py'
NAMES = (
    'ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_frontier',
    'ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_context',
    'ipfs_accelerate_py.agent_supervisor.context.database_context',
    'ipfs_accelerate_py.agent_supervisor.analysis.program_ast_adapters',
    'ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index',
    'ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index',
)


def pin(path):
    raw = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, raw):
    with path.open('xb') as handle:
        handle.write(raw)


attempt = Path(sys.argv[1]).absolute()
attempt.mkdir(mode=0o700, parents=True, exist_ok=False)
os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(attempt / 'fresh-meta.duckdb')
os.environ['IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB'] = str(attempt / 'fresh-seal.duckdb')
modules = {name: importlib.import_module(name) for name in NAMES}
before = {name: pin(module.__file__) for name, module in modules.items()}
before['test'] = pin(TEST)
arguments = ['-c', '/dev/null', '--noconftest', '-p', 'no:cacheprovider',
             '-p', 'ipfs_accelerate_py.testing.pytest_ast_seal', '-q', str(TEST),
             '--junitxml=' + str(attempt / 'tests.xml')]
if len(sys.argv) > 2:
    arguments.extend(['-k', sys.argv[2]])
write(attempt / 'command.json', (json.dumps({'schema': 'terminal-code-frontier-test-command@1',
    'argv': sys.argv, 'pytest_argv': arguments, 'cwd': os.getcwd(), 'source_pins_before': before,
    'scope': 'Fresh local Git/source/AST/vector/query/DuckDB fixtures; no provider calls, owner keys, external proving, training, original DB or hidden verifier.'}, indent=2, sort_keys=True) + '\n').encode())
write(attempt / 'test-source.py', TEST.read_bytes())
write(attempt / 'driver-source.py', Path(__file__).read_bytes())
for name, module in modules.items():
    write(attempt / (name + '.py'), Path(module.__file__).read_bytes())
started = time.monotonic()
with (attempt / 'stdout.txt').open('x') as stdout, (attempt / 'stderr.txt').open('x') as stderr:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = int(pytest.main(arguments))
after = {name: pin(module.__file__) for name, module in modules.items()}
after['test'] = pin(TEST)
result = {'schema': 'terminal-code-frontier-test-result@1', 'pytest_exit_code': code,
          'elapsed_seconds': time.monotonic() - started, 'sources_unchanged': before == after,
          'source_pins_before': before, 'source_pins_after': after}
write(attempt / 'result.json', (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
print(json.dumps(result, sort_keys=True))
sys.exit(code if before == after else 98)
