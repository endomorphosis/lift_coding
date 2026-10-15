"""Offline timing of frozen historical-input audit; no provider calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


EVIDENCE = Path(__file__).parent
CHECKOUT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
AUDIT = CHECKOUT / 'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py'


def pin():
    raw = AUDIT.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


report = {'schema': 'terminal-frontier-audit-offline-timing@1', 'source_before': pin(),
          'scope': 'fresh-process imports and actual twenty-hit native fixture historical audit; local machine, not installed worker timings',
          'provider_calls': 0, 'cold_imports': [], 'collections': []}
for modules in (
    ('benchmarks.agent_supervisor.container_coding.terminal_context_audit',),
    ('ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner',),
    ('ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_frontier',
     'ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index'),
):
    program = 'import importlib,json,time; s=time.monotonic(); ' + '; '.join(
        'importlib.import_module(' + repr(module) + ')' for module in modules
    ) + '; print(json.dumps({"import_seconds":time.monotonic()-s}))'
    started = time.monotonic()
    process = subprocess.run([sys.executable, '-B', '-P', '-c', program], check=True,
                             capture_output=True, text=True, timeout=30)
    report['cold_imports'].append({'modules': modules, 'process_wall_seconds': time.monotonic() - started,
                                  **json.loads(process.stdout)})

import pytest
from benchmarks.agent_supervisor.container_coding import test_terminal_context_audit as fixture
from benchmarks.agent_supervisor.container_coding import terminal_context_audit as audit

workspace = EVIDENCE / 'audit-timing-01-fixture'
workspace.mkdir(exist_ok=False)
monkeypatch = pytest.MonkeyPatch()
try:
    started = time.monotonic()
    case = fixture.actual_frontier.__wrapped__(workspace, monkeypatch)
    report['fixture_build_seconds'] = time.monotonic() - started
    report['fixture_population'] = {key: case['expected']['code_retrieval_frontier'][key] for key in
        ('complete_hit_count', 'included_hit_count', 'omitted_hit_count', 'source_bytes', 'frontier_bytes')}
    started = time.monotonic()
    direct = audit.audit_terminal_context(state=case['state'], receipts=case['receipts'],
                                          workspace_root=case['workspace_root'])
    report['direct'] = {'seconds': time.monotonic() - started, 'status': direct['status'],
                        'reason': direct['reason'], 'read_errors': direct['read_errors']}
    for budget in (3.0, 10.0):
        started = time.monotonic()
        observed = audit.collect_terminal_context_audit(state=case['state'], receipts=case['receipts'],
            workspace_root=case['workspace_root'], timeout_seconds=budget)
        report['collections'].append({'budget_seconds': budget, 'seconds': time.monotonic() - started,
            'status': observed['status'], 'reason': observed['reason'], 'read_errors': observed['read_errors']})
finally:
    monkeypatch.undo()
report['source_after'] = pin()
assert report['source_before'] == report['source_after']
(EVIDENCE / 'audit-timing-01.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
print(json.dumps(report, sort_keys=True))
