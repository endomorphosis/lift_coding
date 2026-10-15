"""Named-only N/O byte preservation after independently supplied final freeze.

No discovery, production imports, database/key/auth/raw-log reads, providers,
tests or Git writes. Only the four root-authorized O heads may replace prior
current-head observations, with exact O-before captures retained separately.
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
        and path.name.lower() not in DENY_NAMES and path.suffix != '.log'
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


def final_sources(final, before):
    require(final['schema'] == 'terminal-nomination-identity-source-manifest@1' and final['checkout'] == str(C)
        and final['existing_deltas'] == 4 and final['new_files'] == 0 and final['runtime_source_files'] == 2
        and final['host_test_files'] == 2, 'Exact four-existing-file final scope required')
    heads = by_path(rows(final['files'], 4)); require(set(heads) == AUTHORIZED, 'No new or extra authorized heads')
    for name, row in heads.items():
        old = before[name]
        require(row['absolute_path'] == str(C / name) and row['absent_before'] is False
            and row['baseline'] == old['baseline'] and row['before_sha256'] == old['sha256']
            and row['before_bytes'] == old['bytes'], 'Final source must join exact original bytes')
    return heads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-manifest-sha256', required=True); args = parser.parse_args()
    output = O / 'preservation-check.json'; require(not output.exists() and not output.is_symlink(), 'New receipt only')
    before = beginning_sources()
    prior_stage_pins()
    evidence = document(N / 'evidence-manifest.json', EVIDENCE_SHA)
    previous = document(N / 'preservation-check.json', PRESERVATION_SHA)
    old_manifest = document(N / 'source-manifest.json', SOURCE_SHA)
    final = document(O / 'source-manifest.json', digest(args.final_manifest_sha256)); heads = final_sources(final, before)
    def prior(group, path, sha, size):
        path = public_path(path); name = path.relative_to(C).as_posix() if path.is_relative_to(C) else None
        if name in AUTHORIZED:
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
        check('all_four_o_original_captures', row['baseline'], row['sha256'], row['bytes'])
        prior('all_four_o_original_heads', C / name, row['sha256'], row['bytes'])
    for name, row in heads.items(): check('all_final_o_source_heads', C / name, row['sha256'], row['bytes'])
    check('final_o_patch', O / 'changes.patch', final['patch_sha256'], final['patch_bytes'])
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
        'existing_authorized_deltas': sorted(AUTHORIZED), 'new_current_sources': [], 'unexpected_deltas': [],
        'database_bodies_read': False, 'credentials_or_raw_rollouts_read': False, 'recursive_discovery': False,
        'source_edits': False, 'prior_n_mutation': False, 'git_index_mutated': False, 'providers_invoked': 0,
        'tests_rerun': False, 'limitations': ['Only named byte/SHA observations; unlisted files and tree cleanliness are outside scope.',
            'Historical capture paths retain original bytes; only the four exact O current heads are substituted.',
            'No source semantics, task success, formal proof, model convergence or token saving follows from preservation.']}
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with output.open('xb') as stream: stream.write(raw)
    print(json.dumps({'receipt': str(output), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
        'pin_checks': len(checks), 'all_checks_passed': True}))


if __name__ == '__main__':
    main()
