"""Reproduce the content-free qualification summary from retained receipts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/repository-worker-tools-20261012')
BASE = '1aa0b832f1974799c785258172e8527f4add9b9c'
DATASETS = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-datasets-20261011')


def git(*args, cwd=SOURCE):
    return subprocess.run(['git', *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


test_files = ['route-baseline.xml', 'route-regression.xml', 'route-final.xml',
              'core-tests.xml', 'bench-route-tests.xml', 'final-tests.xml']
latest = {}
runs = []
for name in test_files:
    cases = list(ET.parse(ROOT / name).getroot().iter('testcase'))
    counts = dict(passed=0, failed=0, errors=0, skipped=0)
    for case in cases:
        outcome = ('failed' if case.find('failure') is not None else
                   'errors' if case.find('error') is not None else
                   'skipped' if case.find('skipped') is not None else 'passed')
        counts[outcome] += 1
        classname = case.attrib['classname']
        # pytest selects a different rootdir for API-only versus mixed runs.
        # Normalize the resulting JUnit prefix before removing repeated cases.
        if classname.startswith('api.'):
            classname = 'test.' + classname
        latest[(classname, case.attrib['name'])] = outcome
    runs.append(dict(file=name, tests=len(cases), **counts))
counts = {status: sum(value == status for value in latest.values())
          for status in ('passed', 'failed', 'errors', 'skipped')}
assert not any(counts[key] for key in ('failed', 'errors', 'skipped'))

qualification = json.loads((ROOT / 'public-final/qualification.json').read_text())
assert qualification['qualified'] and qualification['original_dataset_unchanged']
rows = []
for task in qualification['tasks']:
    original, compact = (task['arms'][key] for key in ('original', 'compact'))
    original_total = original['protocol']['total']['local_tokenizer_proxy_tokens']
    compact_total = compact['protocol']['total']['local_tokenizer_proxy_tokens']
    rows.append(dict(task=task['task_name'], qualified=task['qualified'],
        files=task['file_count'], original_total_proxy_tokens=original_total,
        compact_total_proxy_tokens=compact_total,
        proxy_tokens_saved=original_total - compact_total,
        proxy_reduction_percent=100 * (original_total - compact_total) / original_total,
        setup_included=True, paired_canonical_sources_identical=task['paired_final_canonical_sources_identical'],
        compact_arm_audit=compact['audit']))

files = git('diff', '--name-only', BASE, 'HEAD').splitlines()
review = json.loads((ROOT / 'integration-review.json').read_text())
summary = dict(schema='repository-worker-tools-campaign-summary@1',
    at=datetime.now(timezone.utc).isoformat(),
    source=dict(path=str(SOURCE), branch=git('branch', '--show-current'), commit=git('rev-parse', 'HEAD'),
        base_commit=BASE, clean=not git('status', '--porcelain'), publication='local commit only',
        changed_file_sha256={name: sha(SOURCE / name) for name in files}),
    datasets_source=dict(path=str(DATASETS), commit=git('rev-parse', 'HEAD', cwd=DATASETS)),
    tests=dict(unique_cases=len(latest), **counts,
        accounting='Latest result per normalized classname/name; API-only api.* names normalized to test.api.*. Intermediate failures retained and superseded by passing reruns.', runs=runs),
    independent_review=review,
    public_tasks=rows, local_tokenizer=qualification['local_tokenizer'],
    resource_bounds=dict(repository_entries=512, original_bytes=16 * 1024 * 1024,
        file_bytes=256 * 1024, captures=8, protocol_messages=512,
        duckdb_threads=1, duckdb_memory='128MB', duckdb_spill='128MB', native_reservation_max_mb=2048,
        hard_parser_rss_cap=False, native_pressure_refusal_and_recovery_tested=True),
    original_dataset_unchanged=True, provider_calls=0, containers_started=0,
    official_reward=None, live_model_adoption_qualified=False, live_token_savings_established=False,
    existing_runtime_defaults_changed=False, github_push_performed=False,
    limitations=[
        'Public tests are scripted actual stdio tool cycles, not live model solving or official Terminal Bench rewards.',
        'Local token proxies include JSON-RPC setup and workflow, but exclude model reasoning, provider framing, planning and retries.',
        'Independent private identities and CIDs contribute small run-to-run token-count variation.',
        'Native exclusions, including __pycache__, .pytest_cache, .venv, build, dist and vendor, currently cause refresh refusal.',
        'Native AST shards are reused; semantic reconstruction remains fresh, with no new proof authority.',
        'Only supported single-symbol edits mutate the canonical checkout; multi-file revisions remain immutable proposals.',
        'Process cleanup covers the owned CLI process group; deliberately detached children require the outer worker/container owner.',
        'Native admission and SQL limits do not guarantee a hard Python parser RSS ceiling.',
    ],
    next_phase=[
        'Define explicit coverage for generated caches so task tests can run before refresh without silent source omission.',
        'Propagate repository policies and pinned runtime/datasets dependencies through the container benchmark launcher.',
        'Qualify actual native worker adoption with matched live trials, full provider usage, backoff, and task success.',
        'Measure indexed source selection and semantic capsule/proof retrieval separately from compact rendering.',
    ])
summary['evidence_sha256'] = {name: sha(ROOT / name) for name in [
    *test_files, 'native-config.json', 'integration-review.json',
    'public-final/qualification.json', 'summarize-campaign.py']}
(ROOT / 'summary.json').write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n')
print(json.dumps(dict(commit=summary['source']['commit'], tests=counts, public_tasks=rows), indent=2))
