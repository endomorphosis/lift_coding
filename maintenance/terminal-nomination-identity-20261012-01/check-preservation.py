"""Named-only N/O byte preservation after independently supplied final freeze.

No discovery, production imports, database/key/auth/raw-log reads, providers,
tests or Git writes. Only independently declared O existing heads may replace
prior current-head observations; their exact before-captures stay separate.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import stat

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
O = Path(__file__).resolve().parent
N = O.parent / 'terminal-native-dispatch-diagnostics-20261012-01'
EVIDENCE_SHA = '5874cdfa387ac299f5fb87a2655b28e2b8d960023c82f519dfbd73ad6fc226e3'
PRESERVATION_SHA = '2eb38355e5dbc72c64decef32d99ae903000e199a4dc33ec94e9dd868faa9828'
SOURCE_SHA = '839f655ee3cfb1e578fe4e768da4717f7d32cfbc4dcc59879e59f7d0fde23a00'
BEGINNING_SHA = 'ab3f9e8bc9f3da0afc1db862de2f153b53c41a0f58e45c4e9fff11ff56800e52'
PRIOR_PINS_SHA = '9bafdedecf8e179eccd53124c31020e7163bafae8888fb0743c71425de036568'
PRODUCTION = frozenset({
 'ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_context.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_audit.py'})
TESTS = frozenset({'test/api/test_reviewed_source_nomination_context.py',
 'test/api/test_reviewed_source_nomination_audit.py'})
AUTHORIZED = PRODUCTION | TESTS
ADDITIONAL_BASELINE_SHA = 'fc00baba8d7083ac45cff93edaab791a121d91ac39fd0783893b25e472c06f8e'
ADDITIONAL_EXISTING = frozenset({
 'ipfs_accelerate_py/agent_supervisor/runtime/router_public_instruction.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py',
 'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py'})
ADDITIONAL_NEW_PRODUCTION = frozenset({'ipfs_accelerate_py/agent_supervisor/runtime/native_task_identity.py'})
ADDITIONAL_NEW_TESTS = frozenset({'test/api/test_native_task_identity.py',
 'test/api/test_portal_nomination_task_identity.py'})
ADDITIONAL_NEW = ADDITIONAL_NEW_PRODUCTION | ADDITIONAL_NEW_TESTS
SUPPLEMENTAL_TEST_SHA = 'cd68e3f036c396adeb984c33f423c7ca41e8ce73fed5df71af8e5a081335eb20'
SUPPLEMENTAL_TEST = 'benchmarks/agent_supervisor/container_coding/test_terminal_nomination_context_audit.py'
DENY_SUFFIXES = frozenset({'.duckdb', '.ducklake', '.db', '.sqlite', '.sqlite3',
 '.pem', '.key', '.p12', '.pfx', '.jsonl', '.tar', '.tgz', '.zip'})
DENY_PARTS = frozenset({'.codex', '.git', 'credentials', 'private', 'hidden', 'oracle',
 'rollouts', 'transcripts', 'secrets', 'keys'})
DENY_NAMES = frozenset({'auth.json', 'synthetic-auth.json', '.env', 'token', 'private-key',
 'supervisor.stdout', 'supervisor.stderr'})
MAX_FILE = 256_000_000
MAX_DOCUMENT = 8_000_000
MAX_CHECKS = 4096
STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
 'st_size', 'st_mtime_ns', 'st_ctime_ns')
cache, witnesses, checks, inputs = {}, {}, [], []
opaque_public_pins = {}
BOUNDARY_PROBE_PINS = {
 str(O.parent / 'terminal-nomination-audit-20261012-01/installed-audit-qualification-02/worker-boundary/qualification/probe.log'):
    {'bytes': 1307, 'sha256': '9e8faa724e9971a9b8aaeab9b08273dc97cb74cb0e32cad2505a43b666c1c45b'},
 str(O.parent / 'terminal-nomination-worker-20261012-01/installed-worker-qualification-03/worker-boundary/qualification/probe.log'):
    {'bytes': 1307, 'sha256': '4d664e053b62175497205cd8c766ab553410141d453f65bcc84d3ac9bd0c0e28'},
}


def require(condition, message):
    if condition is not True:
        raise ValueError(message)


def digest(value):
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None, 'Exact independent SHA required')
    return value


def count(value):
    require(type(value) is int and 0 <= value <= MAX_FILE, 'Bounded non-Boolean byte count required')
    return value


def relative(value):
    require(type(value) is str and 0 < len(value.encode()) <= 8192, 'Bounded relative name required')
    path = PurePosixPath(value)
    require(path.parts and not path.is_absolute() and '..' not in path.parts and str(path) == value,
        'Canonical relative name required')
    return value


def public_path(value):
    text = str(value); path = Path(text)
    require(path.is_absolute() and '..' not in path.parts and str(PurePosixPath(text)) == text,
        'Explicit canonical absolute public path required')
    require(path.is_relative_to(C) or path.is_relative_to(O.parent), 'Path outside explicit workspace roots')
    require(path.suffix.lower() not in DENY_SUFFIXES and not text.endswith('.tar.gz')
        and path.name.lower() not in DENY_NAMES and (path.suffix != '.log' or text in opaque_public_pins)
        and not any(part.lower() in DENY_PARTS for part in path.parts), 'Private/database/raw/archive body excluded')
    return path


def witness(info):
    return tuple(getattr(info, field) for field in STAT_FIELDS)


def opened(path):
    path = public_path(path)
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = following
        handle = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(handle)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 <= info.st_size <= MAX_FILE,
                'Bounded no-follow single-link regular public file required')
        except BaseException:
            os.close(handle); raise
        return handle, parent, info
    except BaseException:
        os.close(parent); raise


def capture(path, *, maximum=MAX_FILE, retain=False):
    path = public_path(path); handle, parent, before = opened(path)
    try:
        require(str(path) not in opaque_public_pins or retain is False,
            'Published boundary-probe bytes are checksum-only, never retained or parsed')
        if str(path) in opaque_public_pins:
            maximum = min(maximum, opaque_public_pins[str(path)]['bytes'])
        require(before.st_size <= maximum, 'Named public file exceeds byte cap')
        size, hashed, chunks = 0, hashlib.sha256(), []
        while True:
            block = os.read(handle, min(1_048_576, maximum + 1 - size))
            if not block: break
            size += len(block); require(size <= maximum, 'Bounded read overflow')
            hashed.update(block)
            if retain: chunks.append(block)
        require(size == before.st_size and witness(before) == witness(os.fstat(handle))
            == witness(os.stat(path.name, dir_fd=parent, follow_symlinks=False)), 'Named witness changed during capture')
    finally:
        os.close(handle); os.close(parent)
    pin = {'path': str(path), 'bytes': size, 'sha256': hashed.hexdigest()}
    if str(path) in opaque_public_pins:
        expected = opaque_public_pins[str(path)]
        require(pin['bytes'] == expected['bytes'] and pin['sha256'] == expected['sha256'],
            'Exact published boundary-probe checksum differs')
    if str(path) in cache:
        require(cache[str(path)] == pin and witnesses[str(path)] == witness(before), 'Previously named witness changed')
    cache[str(path)], witnesses[str(path)] = pin, witness(before)
    return pin, b''.join(chunks) if retain else None


def observed(path):
    path = public_path(path)
    if str(path) not in cache: capture(path)
    return cache[str(path)]


def document(path, expected=None):
    pin, raw = capture(path, maximum=MAX_DOCUMENT, retain=True)
    if expected is not None: require(pin['sha256'] == digest(expected), 'Named input differs from independent SHA')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key refused'); result[key] = value
        return result
    def invalid(_): raise ValueError('Nonfinite JSON refused')
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    require(type(value) is dict, 'Named JSON object required'); inputs.append(pin.copy())
    return value


def rows(value, expected):
    require(type(value) is list and len(value) == expected and all(type(row) is dict for row in value),
        'Exact typed inventory census required')
    return value


def by_path(value):
    result = {}
    for row in value:
        name = relative(row['path']); require(name not in result, 'Repeated source name')
        digest(row['sha256']); count(row['bytes']); result[name] = row
    return result


def check(group, path, sha, size, disposition='unchanged', **extra):
    require(len(checks) < MAX_CHECKS, 'Logical check budget exceeded'); pin = observed(path)
    passed = pin['sha256'] == digest(sha) and pin['bytes'] == count(size)
    checks.append({**pin, 'group': group, 'expected_sha256': sha, 'expected_bytes': size,
        'disposition': disposition, 'passed': passed, **extra})
    require(passed, 'Named public preservation mismatch: ' + str(path))


def beginning_sources():
    value = document(O / 'beginning-source-pins.json', BEGINNING_SHA)
    require(value['schema'] == 'terminal-nomination-identity-beginning-sources@1' and value['checkout'] == str(C)
        and value['prior_stage'] == str(N) and value['prior_source_manifest_sha256'] == SOURCE_SHA,
        'Original capture must join exact prior N namespace')
    before = by_path(rows(value['files'], 4)); require(set(before) == AUTHORIZED, 'Only four authorized original sources')
    for name, row in before.items():
        require(row['baseline'] == str(O / 'baseline' / name), 'Exact original-capture path required')
    return before


def prior_stage_pins():
    value = document(O / 'prior-stage-pins.json', PRIOR_PINS_SHA)
    require(value['schema'] == 'terminal-nomination-identity-prior-stage-pins@1' and value['prior_stage'] == str(N),
        'Independently pinned prior namespace required')
    expected = {'evidence-manifest.json': EVIDENCE_SHA, 'source-manifest.json': SOURCE_SHA,
        'preservation-check.json': PRESERVATION_SHA}
    names = set()
    for row in rows(value['files'], 3):
        path = public_path(row['path'])
        require(path.parent == N and path.name in expected and path.name not in names
            and row['sha256'] == expected[path.name], 'Only exact prior three document pins allowed')
        names.add(path.name)
        require(observed(path)['sha256'] == row['sha256'] and observed(path)['bytes'] == row['bytes'],
            'Prior document differs from independently retained pin')
    return value


def register_published_boundary_probes(previous):
    # The caller must first verify the complete previous document against the
    # independent PRESERVATION_SHA. Only two already-published synthetic
    # boundary-probe outputs are exempted from the generic .log refusal.
    require(observed(N / 'preservation-check.json')['sha256'] == PRESERVATION_SHA,
        'Prior preservation bytes must be independently pinned before opaque checks')
    rows_by_path = {}
    qualification_rows = {row['path']: row for row in rows(previous['checks'], 1129)
        if row['path'] in {str(Path(name).with_name('qualification.json')) for name in BOUNDARY_PROBE_PINS}}
    for row in rows(previous['checks'], 1129):
        name = row['path']
        if name not in BOUNDARY_PROBE_PINS: continue
        expected = BOUNDARY_PROBE_PINS[name]
        require(row['passed'] is True and row['sha256'] == row['expected_sha256'] == expected['sha256']
            and row['bytes'] == row['expected_bytes'] == expected['bytes'],
            'Published synthetic-probe pin does not join fixed prior qualified inventory')
        rows_by_path[name] = expected
    require(set(rows_by_path) == set(BOUNDARY_PROBE_PINS), 'Both exact published probe pins must be present')
    for name in rows_by_path:
        qualification_path = str(Path(name).with_name('qualification.json'))
        row = qualification_rows.get(qualification_path)
        require(row is not None and row['passed'] is True and row['sha256'] == row['expected_sha256']
            and row['bytes'] == row['expected_bytes'], 'Corresponding public qualification pin required')
        qualification = document(Path(qualification_path), row['sha256'])
        require(observed(qualification_path)['bytes'] == row['bytes'] and qualification['qualified'] is True,
            'Published synthetic boundary qualification must be exactly qualified')
        evidence = qualification['permission_evidence']
        require(type(evidence) is dict and evidence['schema'] == 'container-worker-preflight@1'
            and type(evidence['uid']) is int and evidence['uid'] == 1001
            and evidence['workspace'] == '/opt/ipfs-supervisor/worktrees/provider-free'
            and type(evidence['prompt_bytes']) is int and evidence['prompt_bytes'] == 0
            and evidence['prompt_sha256'] == hashlib.sha256(b'').hexdigest()
            and type(evidence['provider_calls']) is int and evidence['provider_calls'] == 0
            and type(qualification['provider_calls']) is int and qualification['provider_calls'] == 0,
            'Only exact published synthetic boundary-probe identity is exempted; zero counters are descriptive')
    opaque_public_pins.update(rows_by_path)


def source_scope(additional_path=None, additional_sha=None, generation=None,
                 supplemental_path=None, supplemental_sha=None):
    before = beginning_sources()
    require((additional_path is None) == (additional_sha is None), 'Additional baseline path and SHA must be paired')
    scope = {'before': before, 'existing': AUTHORIZED, 'new': frozenset(),
        'production': PRODUCTION, 'tests': TESTS, 'additional': None, 'supplemental': None}
    require((supplemental_path is None) == (supplemental_sha is None), 'Supplemental test path/SHA must be paired')
    if additional_path is None:
        require(supplemental_path is None, 'Supplemental test requires exact additional generation03 scope')
        return scope
    path = public_path(additional_path)
    require(generation in {'03', '04'} and path == O / 'additional-identity-baseline-03.json'
        and digest(additional_sha) == ADDITIONAL_BASELINE_SHA,
        'Only explicitly pinned generation03 additive baseline allowed')
    value = document(path, ADDITIONAL_BASELINE_SHA)
    require(set(value) == {'schema', 'checkout', 'artifact_generation', 'original_beginning_sha256', 'existing_files', 'new_files'}
        and value['schema'] == 'terminal-nomination-identity-additional-baseline@1' and value['checkout'] == str(C)
        and value['artifact_generation'] == '03' and value['original_beginning_sha256'] == BEGINNING_SHA,
        'Closed additive before-capture declaration required')
    extra = by_path(rows(value['existing_files'], 3))
    require(set(extra) == ADDITIONAL_EXISTING, 'Only three declared additional existing producers allowed')
    for name, row in extra.items():
        require(set(row) == {'path', 'baseline', 'bytes', 'sha256'}
            and row['baseline'] == str(O / 'generation-03-baseline' / name),
            'Exact additional original-capture path required')
    absent = value['new_files']; rows(absent, 3)
    require({row['path'] for row in absent} == ADDITIONAL_NEW
        and all(set(row) == {'path', 'absent_before'} and row['absent_before'] is True for row in absent),
        'Only three independently recorded new-file absences allowed')
    before.update(extra)
    scope.update(existing=AUTHORIZED | ADDITIONAL_EXISTING, new=ADDITIONAL_NEW,
        production=PRODUCTION | ADDITIONAL_EXISTING | ADDITIONAL_NEW_PRODUCTION,
        tests=TESTS | ADDITIONAL_NEW_TESTS, additional=observed(path))
    if supplemental_path is not None:
        test_path = public_path(supplemental_path)
        require(generation == '03' and test_path == O / 'supplemental-test-baseline-03.json'
            and digest(supplemental_sha) == SUPPLEMENTAL_TEST_SHA, 'Only exact supplemental existing test scope allowed')
        supplement = document(test_path, SUPPLEMENTAL_TEST_SHA)
        require(set(supplement) == {'schema', 'checkout', 'artifact_generation', 'additional_baseline_sha256', 'existing_files'}
            and supplement['schema'] == 'terminal-nomination-identity-additional-test-baseline@1'
            and supplement['checkout'] == str(C) and supplement['artifact_generation'] == '03'
            and supplement['additional_baseline_sha256'] == ADDITIONAL_BASELINE_SHA,
            'Closed supplemental test before-capture declaration required')
        extra_test = by_path(rows(supplement['existing_files'], 1))
        require(set(extra_test) == {SUPPLEMENTAL_TEST} and set(extra_test[SUPPLEMENTAL_TEST]) == {'path', 'baseline', 'bytes', 'sha256'}
            and extra_test[SUPPLEMENTAL_TEST]['baseline'] == str(O / 'generation-03-baseline' / SUPPLEMENTAL_TEST),
            'Only exact captured supplemental test allowed')
        before.update(extra_test)
        scope.update(existing=scope['existing'] | {SUPPLEMENTAL_TEST}, tests=scope['tests'] | {SUPPLEMENTAL_TEST},
            supplemental=observed(test_path))
    return scope


def final_sources(final, scope):
    before, existing, new = scope['before'], scope['existing'], scope['new']
    require(final['schema'] == 'terminal-nomination-identity-source-manifest@1' and final['checkout'] == str(C)
        and final['existing_deltas'] == len(existing) and final['new_files'] == len(new)
        and final['runtime_source_files'] == len(scope['production']) and final['host_test_files'] == len(scope['tests']),
        'Exact independently declared final source scope required')
    heads = by_path(rows(final['files'], len(existing) + len(new)))
    require(set(heads) == existing | new, 'No undeclared source heads allowed')
    for name, row in heads.items():
        require(row['absolute_path'] == str(C / name), 'Exact final source path required')
        if name in existing:
            old = before[name]
            require(row['absent_before'] is False and row['baseline'] == old['baseline']
                and row['before_sha256'] == old['sha256'] and row['before_bytes'] == old['bytes'],
                'Final existing source must join exact original bytes')
        else:
            require(row['absent_before'] is True and row['baseline'] is None
                and row['before_sha256'] is None and row['before_bytes'] is None, 'New source cannot invent original bytes')
    if scope['additional'] is not None:
        require(final['additional_baseline'] == scope['additional'], 'Final declaration must join exact additive before-capture pin')
    if scope['supplemental'] is not None:
        require(final['supplemental_test_baseline'] == scope['supplemental'], 'Final declaration must join exact supplemental test pin')
    return heads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-manifest-sha256', required=True)
    parser.add_argument('--final-manifest', type=Path, default=O / 'source-manifest.json')
    parser.add_argument('--artifact-generation', choices=('02', '03', '04'))
    parser.add_argument('--additional-baseline', type=Path)
    parser.add_argument('--additional-baseline-sha256')
    parser.add_argument('--supplemental-test-baseline', type=Path)
    parser.add_argument('--supplemental-test-baseline-sha256')
    args = parser.parse_args()
    final_manifest_path = public_path(args.final_manifest)
    require(final_manifest_path.parent == O, 'Final manifest must be an explicit canonical document directly under O')
    suffix = '-' + args.artifact_generation if args.artifact_generation else ''
    require(final_manifest_path.name == 'source-manifest' + suffix + '.json',
        'Final manifest filename must match exact selected artifact generation')
    output = O / ('preservation-check' + suffix + '.json')
    require(not output.exists() and not output.is_symlink(), 'New receipt only')
    scope = source_scope(args.additional_baseline, args.additional_baseline_sha256, args.artifact_generation,
        args.supplemental_test_baseline, args.supplemental_test_baseline_sha256)
    before, existing, new = scope['before'], scope['existing'], scope['new']
    prior_stage_pins()
    evidence = document(N / 'evidence-manifest.json', EVIDENCE_SHA)
    previous = document(N / 'preservation-check.json', PRESERVATION_SHA)
    register_published_boundary_probes(previous)
    old_manifest = document(N / 'source-manifest.json', SOURCE_SHA)
    final = document(final_manifest_path, digest(args.final_manifest_sha256)); heads = final_sources(final, scope)
    def prior(group, path, sha, size):
        path = public_path(path); name = path.relative_to(C).as_posix() if path.is_relative_to(C) else None
        if name in existing:
            old, new = before[name], heads[name]
            require(sha == old['sha256'] and size == old['bytes'], 'Prior live head differs from exact O-before capture')
            check(group, old['baseline'], sha, size, 'authorized_delta_original_bytes_retained', original_path=str(path))
            check(group, path, new['sha256'], new['bytes'], 'authorized_stage_o_delta', original_sha256=sha, original_bytes=size)
        else:
            check(group, path, sha, size)
    for name, sha in [('evidence-manifest.json', EVIDENCE_SHA), ('preservation-check.json', PRESERVATION_SHA),
            ('source-manifest.json', SOURCE_SHA)]:
        check('prior_n_fixed_pins', N / name, sha, observed(N / name)['bytes'])
    old = by_path(rows(old_manifest['files'], 7))
    names, n_artifact_count, source_head_count = set(), 0, 0
    for row in rows(evidence['files'], 199):
        path = public_path(row['path']); require(str(path) not in names, 'Repeated prior N artifact'); names.add(str(path))
        if path.is_relative_to(N):
            n_artifact_count += 1; check('prior_n_199_sealed_files', path, row['sha256'], row['bytes'])
        else:
            require(path.is_relative_to(C) and path.relative_to(C).as_posix() in old,
                'Only exact N artifacts and N seven source heads are in sealed inventory')
            source_head_count += 1; prior('prior_n_199_sealed_files', path, row['sha256'], row['bytes'])
    require(n_artifact_count == 192 and source_head_count == 7, 'Exact prior N artifact/source census required')
    records = rows(previous['checks'], 1129)
    require(previous['all_checks_passed'] is True and type(previous['pin_checks']) is int
        and previous['pin_checks'] == 1129 and previous['unique_checked_paths'] == 865
        and len({row['path'] for row in records}) == 865, 'Prior qualified logical preservation census differs')
    for row in records:
        require(row['passed'] is True and row['sha256'] == row['expected_sha256'] and row['bytes'] == row['expected_bytes'],
            'Unqualified previous logical row cannot be reused')
        prior('prior_n_1129_logical_checks', row['path'], row['sha256'], row['bytes'])
    for name, row in old.items():
        prior('prior_n_seven_source_heads', C / name, row['sha256'], row['bytes'])
        if row['absent_before'] is False:
            require(row['baseline'] == str(N / 'baseline' / name), 'Exact prior N original capture path required')
            check('prior_n_existing_source_captures', row['baseline'], row['before_sha256'], row['before_bytes'])
    for name, row in before.items():
        check('all_o_original_captures' if scope['additional'] else 'all_four_o_original_captures', row['baseline'], row['sha256'], row['bytes'])
        prior('all_o_original_heads' if scope['additional'] else 'all_four_o_original_heads', C / name, row['sha256'], row['bytes'])
    for name, row in heads.items(): check('all_final_o_source_heads', C / name, row['sha256'], row['bytes'])
    check('final_o_patch', O / ('changes' + suffix + '.patch'), final['patch_sha256'], final['patch_bytes'])
    for name, recorded in witnesses.items():
        handle, parent, info = opened(Path(name))
        try:
            require(witness(info) == recorded == witness(os.stat(Path(name).name, dir_fd=parent, follow_symlinks=False)),
                'Final named-file witness changed')
        finally:
            os.close(handle); os.close(parent)
    value = {'schema': 'terminal-nomination-identity-independent-preservation@1', 'all_checks_passed': True,
        'inputs': inputs, 'checker': observed(Path(__file__).absolute()), 'checks': checks, 'pin_checks': len(checks),
        'unique_checked_paths': len({row['path'] for row in checks}), 'unique_hashed_paths': len(cache),
        'groups': {group: sum(row['group'] == group for row in checks) for group in sorted({row['group'] for row in checks})},
        'prior_n_199_sealed_files_unchanged': True, 'prior_n_1129_logical_checks_rechecked': True,
        'prior_n_865_original_unique_paths': 865, 'all_prior_n_seven_source_heads_and_captures_retained': True,
        'all_four_o_before_captures_retained': True, 'all_four_final_o_source_pins_match': True,
        'existing_authorized_deltas': sorted(existing), 'new_current_sources': sorted(new), 'unexpected_deltas': [],
        'database_bodies_read': False, 'credentials_or_raw_rollouts_read': False, 'recursive_discovery': False,
        'opaque_published_boundary_probe_checksum_streams': sorted(opaque_public_pins),
        'opaque_published_boundary_probe_bytes_streamed': sum(row['bytes'] for row in opaque_public_pins.values()),
        'raw_worker_model_or_daemon_logs_read': False, 'archive_payload_bytes_streamed': False,
        'archive_entries_extracted_or_parsed': False,
        'source_edits': False, 'prior_n_mutation': False, 'git_index_mutated': False, 'providers_invoked': 0,
        'tests_rerun': False, 'limitations': ['Only named byte/SHA observations; unlisted files and tree cleanliness are outside scope.',
            'Historical capture paths retain original bytes; only the independently declared O current heads are substituted.',
            'Two exact previously published synthetic boundary-probe outputs are streamed only for SHA/size checks; their text is not retained or parsed.',
            'No source semantics, task success, formal proof, model convergence or token saving follows from preservation.']}
    if scope['additional'] is not None:
        value.update(additional_baseline=scope['additional'], original_capture_count=len(before),
            final_source_count=len(heads), all_declared_existing_captures_retained=True,
            all_declared_final_source_pins_match=True)
    if scope['supplemental'] is not None:
        value['supplemental_test_baseline'] = scope['supplemental']
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with output.open('xb') as stream: stream.write(raw)
    print(json.dumps({'receipt': str(output), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
        'pin_checks': len(checks), 'all_checks_passed': True}))


if __name__ == '__main__':
    main()
