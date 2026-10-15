"""Seal explicitly named public stage-M evidence after independent final review.

No discovery, runtime archive bodies, credential/database/raw worker log reads,
production imports, provider calls or Git changes. Qualification failures are
retained observations, not a reason to omit evidence. Do not run before the root
supplies and approves the final-review path and independently pinned SHA.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import stat

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
L = Path('/home/barberb/lift_coding/maintenance/terminal-nomination-audit-20261012-01')
M = Path(__file__).resolve().parent
L_EVIDENCE_SHA = 'fa7045dc58f52ac14cd4f2b851c5a6a93c8cc14961cefc765d279ab7eee09c3b'
L_PRESERVATION_SHA = '940154ae6e678ba4d6f343609e151d6e34c4810d9025fe77f49ee98e6e4c084f'
L_SOURCE_SHA = 'd1b5a8ba27eeb5e337a60b67051aba0970e0c2068305c2f0fa54d2fad53ea33a'
EXISTING = frozenset({
    'benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py',
    'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py',
    'benchmarks/agent_supervisor/container_coding/container_worker_deployment.py',
    'benchmarks/agent_supervisor/container_coding/test_terminal_nomination_entrypoint.py',
    'ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py',
})
NEW = frozenset({
    'benchmarks/agent_supervisor/container_coding/' + name + '.py'
    for name in ('terminal_source_nomination_budget', 'test_terminal_source_nomination_budget',
        'retained_source_nomination_lifecycle', 'test_retained_source_nomination_lifecycle',
        'terminal_model_input_observation_audit', 'test_terminal_model_input_observation_audit')
}) | frozenset({
    'ipfs_accelerate_py/agent_supervisor/runtime/model_input_observation_receipt.py',
    'test/api/test_router_model_input_observation.py',
    'test/api/test_model_input_observation_receipt.py',
})
DENY_SUFFIXES = frozenset({'.duckdb', '.ducklake', '.db', '.sqlite', '.sqlite3',
    '.pem', '.key', '.p12', '.pfx', '.jsonl'})
DENY_PARTS = frozenset({'.codex', '.git', 'credentials', 'private', 'hidden', 'oracle',
    'rollouts', 'transcripts', 'secrets', 'keys'})
DENY_NAMES = frozenset({'auth.json', '.env', 'token', 'private-key', 'supervisor.stdout', 'supervisor.stderr', 'synthetic-auth.json'})
MAX_FILE = 32_000_000
MAX_DOCUMENT = 8_000_000
MAX_CHECKS = 4096
STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
    'st_size', 'st_mtime_ns', 'st_ctime_ns')
cache, witnesses, checks, inputs = {}, {}, [], []


def require(condition, message):
    if condition is not True:
        raise ValueError(message)


def digest(value):
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None,
        'Independent canonical SHA256 required')
    return value


def count(value):
    require(type(value) is int and 0 <= value <= MAX_FILE, 'Bounded non-Boolean byte count required')
    return value


def relative(value):
    require(type(value) is str and 0 < len(value.encode()) <= 8192, 'Bounded named relative path required')
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.parts and '..' not in path.parts and str(path) == value,
        'Canonical relative path required')
    return value


def public_path(value):
    text = str(value)
    path = Path(text)
    require(path.is_absolute() and '..' not in path.parts and str(PurePosixPath(text)) == text,
        'Canonical explicitly named absolute path required')
    require(path.suffix.lower() not in DENY_SUFFIXES and path.name.lower() not in DENY_NAMES
        and not any(part.lower() in DENY_PARTS for part in path.parts), 'Private/body path denied')
    require(path.is_relative_to(C) or path.is_relative_to(M.parent), 'Path outside nominated workspace roots')
    return path


def witness(info):
    return tuple(getattr(info, key) for key in STAT_FIELDS)


def opened(path):
    path = public_path(path)
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = following
        handle = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(handle)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and 0 <= info.st_size <= MAX_FILE, 'Bounded single-link regular public file required')
        except BaseException:
            os.close(handle)
            raise
        return handle, parent, info
    except BaseException:
        os.close(parent)
        raise


def capture(path, *, maximum=MAX_FILE, retain=False):
    path = public_path(path)
    handle, parent, before = opened(path)
    try:
        require(before.st_size <= maximum, 'Named public document exceeds byte bound')
        size, hashed, chunks = 0, hashlib.sha256(), []
        while True:
            block = os.read(handle, min(1_048_576, maximum + 1 - size))
            if not block:
                break
            size += len(block)
            require(size <= maximum, 'Public file exceeded bounded read')
            hashed.update(block)
            if retain:
                chunks.append(block)
        require(size == before.st_size and witness(before) == witness(os.fstat(handle))
            == witness(os.stat(path.name, dir_fd=parent, follow_symlinks=False)), 'Public witness changed during read')
    finally:
        os.close(handle)
        os.close(parent)
    pin = {'path': str(path), 'bytes': size, 'sha256': hashed.hexdigest()}
    if str(path) in cache:
        require(cache[str(path)] == pin and witnesses[str(path)] == witness(before),
            'Previously captured public input changed')
    cache[str(path)], witnesses[str(path)] = pin, witness(before)
    return pin, b''.join(chunks) if retain else None


def observed(path):
    path = public_path(path)
    if str(path) not in cache:
        capture(path)
    return cache[str(path)]


def document(path, expected=None):
    pin, raw = capture(path, maximum=MAX_DOCUMENT, retain=True)
    if expected is not None:
        require(pin['sha256'] == digest(expected), 'Named input SHA does not match independent pin')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON input key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('Nonfinite JSON input refused')
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    require(type(value) is dict, 'Explicit named JSON object required')
    inputs.append(pin.copy())
    return value


def rows(value, expected):
    require(type(value) is list and len(value) == expected
        and all(type(row) is dict for row in value), 'Exact typed inventory census required')
    return value


def by_path(values):
    result = {}
    for row in values:
        name = relative(row['path'])
        require(name not in result, 'Repeated source inventory entry refused')
        digest(row['sha256']); count(row['bytes'])
        result[name] = row
    return result


def check(group, path, sha, size, disposition='unchanged', **extra):
    require(len(checks) < MAX_CHECKS, 'Logical check budget exceeded')
    got = observed(path)
    passed = got['sha256'] == digest(sha) and got['bytes'] == count(size)
    checks.append({**got, 'group': group, 'expected_sha256': sha, 'expected_bytes': size,
        'disposition': disposition, 'passed': passed, **extra})
    require(passed, 'Explicit public preservation mismatch: ' + str(path))



FINAL_SOURCE_SHA = '657895d3a12ae52e142cfc0546f0acf6640e89c42d3a2e102fc35438382bc122'
PRESERVATION_SHA = '8d1b3d5a85d70c81d6bed7be29fc9a65aada639815139a1626bc84b65064df10'
MAX_FILES = 1024
MAX_AGGREGATE = 128_000_000
ROOT_NAMES = (
    'source-manifest.json', 'changes.patch', 'preservation-check.json',
    'selected-validation-reports.json', 'final-focused-validation.json',
    'result-summary.json', 'next-work.json', 'native-dispatch-gap-analysis.json',
    'beginning-source-pins.json', 'observation-source-before-pins.json',
    'worker-observation-before-pins.json', 'observation-final-test-before-pins.json',
    'observation-owned-baseline.json', 'model-input-audit-owned-baseline.json',
    'budget-refresh-source-pins-04.json', 'budget-final-source-pins-06.json',
    'budget-final-source-pins-07.json', 'model-input-audit-validation.json',
    'controller-validation.json', 'observation-validation.json',
    'budget-validation-01.json', 'budget-validation-02.json',
    'budget-validation-03.json', 'budget-validation-04.json',
    'root-qualifier-review.json', 'actual-harbor-lifecycle-independent-review.json',
    'actual-harbor-02-additional-diagnostics.json',
    'public-task-metadata.json', 'public-task-image.json',
    'runtime-archive/manifest.json', 'runtime-archive-final-02/manifest.json',
    'runtime-archive-verification.json', 'runtime-archive-final-02-verification.json',
    'public-task-inputs/instruction.md', 'public-task-inputs/task.toml',
    'public-task-inputs/environment/Dockerfile',
    'public-task-inputs/reviewed-intent-contract.json',
    'build-pinned-runtime.py', 'build-pinned-runtime-attempt-01.py',
    'package-stage.py', 'package-stage-attempt-01.py', 'packaging-attempt-01.json',
    'build-stage-results.py', 'capture-fresh-driver-diagnostics.py',
    'run-model-input-audit-tests.py', 'check-preservation.py', 'seal-evidence.py',
    'qualify-retained-harbor.py', 'qualify-retained-harbor-attempt-01.py',
    'qualify-retained-harbor-attempt-02.py',
    'runtime-build.stdout', 'runtime-build.stderr',
    'runtime-final-build.stdout', 'runtime-final-build.stderr',
    'additional-diagnostics.stdout', 'additional-diagnostics.stderr',
    'receipt-validator-tests-03.stdout', 'receipt-validator-tests-03.stderr',
    'observation-regression-01.xml', 'worker-observation-tests-01.xml',
    'worker-observation-golden-01.xml',
)
VALIDATION_NAMES = ('budget-validation-04.json', 'controller-validation.json',
    'observation-validation.json', 'model-input-audit-validation.json')
LIFECYCLE_NAMES = (
    'controller-result.json', 'prepare_only-public-report.json', 'resume-public-report.json',
    'prepare_only-attempt.json', 'resume-attempt.json',
    'prepare_only-execution.json', 'resume-execution.json',
    'baseline.json', 'template.json', 'authored-review.json',
)
ARTIFACT_CATEGORIES = {}
PIN_JOINS = []


def nominate(path, category):
    path = public_path(path)
    require(path.is_relative_to(M) or (path.is_relative_to(C) and path.suffix == '.py'),
        'Artifact must be explicitly nominated stage evidence or Python source')
    ARTIFACT_CATEGORIES.setdefault(str(path), set()).add(category)
    require(len(ARTIFACT_CATEGORIES) <= MAX_FILES, 'Explicit file census exceeds budget')
    return path


def add(path, category, expected=None, expected_bytes=None):
    path = nominate(path, category)
    pin = observed(path)
    require(sum(row['bytes'] for row in cache.values()) <= MAX_AGGREGATE,
        'Aggregate explicitly named evidence exceeds budget')
    if expected is not None:
        require(pin['sha256'] == digest(expected), 'Named evidence digest mismatch: ' + str(path))
    if expected_bytes is not None:
        require(pin['bytes'] == count(expected_bytes), 'Named evidence byte count mismatch: ' + str(path))
    if expected is not None or expected_bytes is not None:
        PIN_JOINS.append({'path': str(path), 'category': category,
            'expected_sha256': expected, 'expected_bytes': expected_bytes, 'matched': True})
    return pin


def read_doc(name, category, expected=None):
    path = nominate(M / relative(name), category)
    value = document(path, expected)
    add(path, category)
    return value


def list_rows(value, maximum=1024):
    require(type(value) is list and len(value) <= maximum
        and all(type(row) is dict for row in value), 'Bounded typed named inventory required')
    return value


def source_name(value):
    name = relative(value)
    require(name.endswith('.py') and name.startswith(('benchmarks/', 'ipfs_accelerate_py/', 'test/')),
        'Only explicit public Python source paths may be nominated')
    public_path(C / name)
    return name


def pin_rows(value, *, maximum=1024):
    """Inspect only bounded metadata, never follow arbitrary path references."""
    found, nodes = [], 0
    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        require(nodes <= 100_000 and depth <= 32, 'Receipt metadata traversal exceeds budget')
        if type(item) is dict:
            if type(item.get('path')) is str and 'sha256' in item and 'bytes' in item:
                found.append(item)
                require(len(found) <= maximum, 'Named receipt pin census exceeds budget')
            for child in item.values():
                if type(child) in (dict, list):
                    visit(child, depth + 1)
        elif type(item) is list:
            for child in item:
                if type(child) in (dict, list):
                    visit(child, depth + 1)
    visit(value, 0)
    return found


def named_ref(value, allowed):
    text = value.get('path')
    require(type(text) is str and len(text.encode('utf-8')) <= 8192,
        'Bounded named receipt reference required')
    path = Path(text) if text.startswith('/') else M / relative(text)
    # Root source references are historical assertions unless explicitly nominated
    # as final sources. No arbitrary outside/owner/private reference is opened.
    return path if str(path) in allowed else None


def snapshot_rows(name, value):
    if type(value) is dict and 'before' in value:
        before, after = list_rows(value['before']), list_rows(value['after'])
        require(before == after, 'Retained controller snapshot changed across test execution')
        return before
    require(type(value) is dict and 0 < len(value) <= 32
        and all(type(row) is dict for row in value.values()),
        'Bounded typed audit snapshot source mapping required')
    return [{'path': key, **row} for key, row in value.items()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-review', default='final-stage-independent-review.json',
        choices=('final-stage-independent-review.json',),
        help='Fixed root-nominated final public review JSON leaf under stage M')
    parser.add_argument('--final-review-sha256', required=True)
    args = parser.parse_args()
    review_name = relative(args.final_review)
    require('/' not in review_name and review_name.endswith('.json') and 'review' in review_name,
        'Final public review must be an explicitly named JSON leaf')
    review_sha = digest(args.final_review_sha256)
    output = M / 'evidence-manifest.json'
    require(not output.exists() and not output.is_symlink(), 'Evidence seal already exists')

    review = read_doc(review_name, 'independently-approved-final-review', review_sha)
    # False qualification is valid evidence. The only approval authority here is
    # the independently supplied expected digest, never review success booleans.
    source = read_doc('source-manifest.json', 'final-source-package', FINAL_SOURCE_SHA)
    preservation = read_doc('preservation-check.json', 'prior-stage-preservation', PRESERVATION_SHA)
    require(preservation.get('all_checks_passed') is True,
        'Prior-stage byte preservation receipt is not qualified')
    require(type(source.get('files')) is list and len(source['files']) == 14,
        'Final package source census changed')
    current_sources = []
    for row in source['files']:
        require(type(row) is dict, 'Final source row malformed')
        name = source_name(row['path'])
        pin = add(C / name, 'final-source', row['sha256'], row['bytes'])
        current_sources.append({'path': name, 'bytes': pin['bytes'], 'sha256': pin['sha256']})
    require(len({r['path'] for r in current_sources}) == 14, 'Final source inventory repeats paths')
    add(M / 'changes.patch', 'clean-reviewed-patch', source['patch_sha256'], source['patch_bytes'])

    literal_names = set(ROOT_NAMES)
    literal_names.update(f'budget-tests-{i:02d}.xml' for i in range(1, 8))
    literal_names.update(f'controller-tests-{i:02d}.xml' for i in range(1, 6))
    literal_names.update(f'observation-tests-{i:02d}.xml' for i in range(1, 6))
    literal_names.update(f'receipt-validator-tests-{i:02d}.xml' for i in range(1, 4))
    literal_names.add(review_name)
    for attempt in range(1, 4):
        base = f'actual-harbor-lifecycle-{attempt:02d}'
        literal_names.update(base + '/lifecycle/' + n for n in LIFECYCLE_NAMES)
        literal_names.update(base + '/' + n for n in (
            'qualification.json', 'original-head.txt',
            'installed-import-provenance.stdout', 'installed-import-provenance.stderr',
            'named-owner-public-metadata.stdout', 'named-owner-public-metadata.stderr',
            'deployment/deployment.json', 'worker-boundary/deployment.json',
            'worker-boundary/installation/installation.json',
            'worker-boundary/qualification/qualification.json'))
        literal_names.update(f'actual-harbor-{attempt:02d}.{suffix}' for suffix in ('stdout', 'stderr'))
        a = f'model-input-audit-attempt-{attempt:02d}'
        literal_names.update(a + '/' + n for n in (
            'argv.json', 'exit.json', 'source-pins-before.json', 'source-pins-after.json',
            'tests.xml', 'stdout.txt', 'stderr.txt'))
        if attempt >= 2:
            literal_names.add(a + '/environment.json')
        if attempt == 3:
            literal_names.add(a + '/additional-driver-witness.json')
    for attempt in range(2, 6):
        base = f'controller-validation-attempt-{attempt:02d}'
        literal_names.update(base + '/' + n for n in ('pins.json', 'stdout.txt', 'stderr.txt'))
    for name in sorted(literal_names):
        add(M / name, 'explicit-public-stage-artifact')

    # Sixteen exact before-captures are derived only from the three explicit
    # baseline metadata documents. This does not enumerate the baseline tree.
    baseline_count, baseline_sources = 0, set()
    for name, prefix in (
        ('beginning-source-pins.json', 'baseline'),
        ('observation-source-before-pins.json', 'baseline'),
        ('worker-observation-before-pins.json', 'baseline/worker-observation')):
        value = read_doc(name, 'baseline-pin-document')
        for row in list_rows(value['files'], 16):
            rel = source_name(row['path'])
            require(rel not in baseline_sources, 'Repeated original source capture')
            baseline_sources.add(rel)
            path = M / prefix / rel
            if 'baseline' in row:
                require(row['baseline'] == str(path), 'Baseline path differs from controlled capture')
            add(path, 'exact-original-source-capture', row['sha256'], row['bytes'])
            baseline_count += 1
    require(baseline_count == 16, 'Before-capture census differs from final package baseline')

    # Historical snapshots are joined to their retained copies. They are not
    # reinterpreted as current head hashes when a later test changed the source.
    snapshot_count = 0
    for attempt in range(2, 6):
        base = f'controller-validation-attempt-{attempt:02d}'
        value = read_doc(base + '/pins.json', 'controller-before-after-pins')
        for row in snapshot_rows(base, value):
            add(M / base / 'sources' / source_name(row['path']),
                'retained-controller-test-source', row['sha256'], row['bytes'])
            snapshot_count += 1
    for attempt in range(1, 4):
        base = f'model-input-audit-attempt-{attempt:02d}'
        before = read_doc(base + '/source-pins-before.json', 'audit-before-pins')
        after = read_doc(base + '/source-pins-after.json', 'audit-after-pins')
        require(before == after, 'Retained audit sources changed during selected attempt')
        for row in snapshot_rows(base, before):
            add(M / base / 'sources' / source_name(row['path']),
                'retained-audit-test-source', row['sha256'], row['bytes'])
            snapshot_count += 1

    # Safe references are checked only if they name a file already nominated by
    # the closed literal inventory or the controlled source/capture tables.
    allowed = set(ARTIFACT_CATEGORIES)
    out_of_scope_ref_count = 0
    joined_receipts = []
    for name in (*VALIDATION_NAMES, 'final-focused-validation.json', review_name,
            'result-summary.json'):
        value = read_doc(name, 'final-validation-or-review')
        for row in pin_rows(value):
            path = named_ref(row, allowed)
            if path is None:
                out_of_scope_ref_count += 1
                continue
            add(path, 'joined-named-receipt-reference', row['sha256'], row['bytes'])
        joined_receipts.append(name)

    # Check captured task copies against public metadata without opening the
    # original .benchmarks task, verifier, solution or repository oracle.
    metadata = read_doc('public-task-metadata.json', 'public-task-capture-metadata')
    task_names = ('instruction.md', 'task.toml', 'environment/Dockerfile')
    for row, name in zip(list_rows(metadata['files'], 3), task_names, strict=True):
        require(row['path'].endswith('/' + name), 'Public task capture metadata order changed')
        add(M / 'public-task-inputs' / name, 'public-recipe-capture', row['sha256'], row['bytes'])

    # Final checks occur after every metadata/reference read and before output.
    for text, previous in tuple(witnesses.items()):
        handle, parent, info = opened(Path(text))
        try:
            require(witness(info) == previous
                == witness(os.stat(Path(text).name, dir_fd=parent, follow_symlinks=False)),
                'Captured public input was substituted before evidence seal')
        finally:
            os.close(handle)
            os.close(parent)
    files = [{**cache[text], 'categories': sorted(categories)}
        for text, categories in sorted(ARTIFACT_CATEGORIES.items())]
    result = {
        'schema': 'terminal-source-nomination-lifecycle-evidence-manifest@1',
        'stage': str(M), 'checkout': str(C),
        'final_review': {**cache[str(M / review_name)], 'independently_expected_sha256': review_sha},
        'source_manifest_sha256': FINAL_SOURCE_SHA,
        'preservation_receipt_sha256': PRESERVATION_SHA,
        'files': files, 'file_count': len(files), 'sources': current_sources,
        'source_count': len(current_sources), 'exact_before_capture_count': baseline_count,
        'retained_snapshot_source_count': snapshot_count,
        'pin_joins': PIN_JOINS, 'pin_join_count': len(PIN_JOINS),
        'joined_validation_and_review_documents': joined_receipts,
        'out_of_scope_reference_count_not_followed': out_of_scope_ref_count,
        'aggregate_public_bytes_hashed': sum(row['bytes'] for row in cache.values()),
        'all_named_file_and_reference_guards_passed': True,
        'qualification_success_required_to_seal': False,
        'negative_actual_qualification_evidence_retained': True,
        'actual_lifecycle_or_task_success_inferred_by_seal': False,
        'provider_population_or_billing_or_token_savings_certified_by_seal': False,
        'private_auth_including_empty_synthetic_auth_selected': False,
        'database_or_key_or_raw_worker_model_log_body_selected': False,
        'runtime_archive_bodies_reopened': False,
        'recursive_filesystem_discovery': False,
        'tests_or_providers_executed_here': False,
        'prior_stage_or_source_or_git_mutation': False,
    }
    raw = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    require(len(raw) <= MAX_DOCUMENT, 'Closed evidence manifest exceeds receipt budget')
    with output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'receipt': str(output), 'bytes': len(raw),
        'sha256': hashlib.sha256(raw).hexdigest(), 'file_count': len(files),
        'source_count': len(current_sources), 'all_named_file_and_reference_guards_passed': True}))


if __name__ == '__main__':
    main()
