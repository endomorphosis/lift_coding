#!/usr/bin/env python3
"""Run the combined compact-policy and installer regression suite once."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
DATASETS = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-datasets-20261011')
HARBOR_SITE = Path('/home/barberb/lift_coding/.venvs/terminal-bench-harbor/lib/python3.12/site-packages')
API = ['test_tool_output_policy.py', 'test_tool_output_artifact.py',
       'test_router_implementation_runner.py', 'test_codex_telemetry_pipeline.py',
       'test_terminal_doctor_dispatch.py']
BENCH = ['test_terminal_context_audit.py', 'test_terminal_tool_output_policy.py',
         'test_terminal_semantic_metadata_policy.py', 'test_full_supervisor_harbor_agent.py',
         'test_benchmark_controls.py', 'test_terminal_live_census_provenance.py',
         'test_benchmark_comparison.py', 'test_terminal_deployment.py',
         'test_native_codex_installer.py', 'test_native_codex_bundle.py',
         'test_terminal_setup_cache_advice.py', 'test_setup_cache_comparison_controls.py',
         'test_native_codex_baseline.py', 'test_terminal_grok_deployment.py']
files = ['test/api/' + name for name in API]
files += ['benchmarks/agent_supervisor/container_coding/' + name for name in BENCH]
changed = ['benchmarks/agent_supervisor/container_coding/' + name for name in
           ('terminal_deployment.py', 'test_native_codex_installer.py', 'README.md')]


def hashes():
    return {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in changed}


before = hashes()
environment = dict(os.environ, PYTHONPATH=f'{SOURCE}:{DATASETS}:{HARBOR_SITE}',
                   PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                   IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB='/tmp/compact-installer-validation-20261012-02.duckdb',
                   OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
argv = ['/home/barberb/.local/bin/python', '-m', 'pytest', '-q', '-o', 'addopts=',
        '-o', 'log_cli=false', '--color=no', '--junitxml=' + str(ROOT / 'source-validation.xml'), *files]
started = time.monotonic()
with (ROOT / 'source-validation.log').open('x') as log:
    result = subprocess.run(argv, cwd=SOURCE, env=environment,
                            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
elapsed = time.monotonic() - started
suites = ET.parse(ROOT / 'source-validation.xml').getroot().findall('testsuite')
counts = {name: sum(int(suite.get(name, 0)) for suite in suites)
          for name in ('tests', 'errors', 'failures', 'skipped')}
counts['passed'] = counts['tests'] - counts['errors'] - counts['failures'] - counts['skipped']
report = {'schema': 'compact-installer-combined-validation@1', 'returncode': result.returncode,
          'test_counts': counts, 'elapsed_seconds': elapsed, 'files': files,
          'tested_source_sha256': before, 'source_files_stable': before == hashes(),
          'provider_calls': 0, 'subset_counts_are_not_additive': True,
          'log_sha256': hashlib.sha256((ROOT / 'source-validation.log').read_bytes()).hexdigest(),
          'xml_sha256': hashlib.sha256((ROOT / 'source-validation.xml').read_bytes()).hexdigest()}
(ROOT / 'source-validation.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps(report, sort_keys=True))
raise SystemExit(0 if result.returncode == 0 and report['source_files_stable'] else 1)
