"""Independent named-only L/M byte preservation after the supplied M freeze.

No discovery, production imports, database reads, provider calls or Git changes.
The mandatory manifest SHA must be supplied independently by the root.
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
DENY_NAMES = frozenset({'auth.json', '.env', 'token', 'private-key', 'supervisor.stdout', 'supervisor.stderr'})
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-manifest-sha256', required=True)
    args = parser.parse_args()
    final_sha = digest(args.final_manifest_sha256)
    output = M / 'preservation-check.json'
    require(not output.exists() and not output.is_symlink(), 'Existing preservation receipt must remain immutable')
    evidence = document(L / 'evidence-manifest.json', L_EVIDENCE_SHA)
    previous = document(L / 'preservation-check.json', L_PRESERVATION_SHA)
    old_sources = document(L / 'source-manifest.json', L_SOURCE_SHA)
    before_docs = [document(M / name) for name in ('beginning-source-pins.json',
        'observation-source-before-pins.json', 'worker-observation-before-pins.json')]
    final = document(M / 'source-manifest.json', final_sha)
    require(final['checkout'] == str(C), 'Final isolated checkout identity differs')
    heads = by_path(rows(final['files'], 14))
    require(set(heads) == EXISTING | NEW and final['existing_deltas'] == 5 and final['new_files'] == 9,
        'Exactly five authorized existing and nine new sources required')
    before = {}
    for doc, expected in zip(before_docs, (11, 4, 1)):
        for name, row in by_path(rows(doc['files'], expected)).items():
            require(name not in before, 'Baseline captured more than once')
            baseline = Path(row.get('baseline') or M / 'baseline' / name)
            require(baseline.is_relative_to(M / 'baseline'), 'Capture outside current named baseline namespace')
            before[name] = {**row, 'baseline': str(baseline)}
    require(len(before) == 16 and set(heads) & set(before) == EXISTING, 'Sixteen captures do not join five authorized deltas')
    require(before_docs[0]['checkout'] == str(C) and before_docs[0]['prior_manifest']['sha256'] == L_EVIDENCE_SHA,
        'Current captures do not join prior immutable L inventory')
    for name, head in heads.items():
        require(head['absolute_path'] == str(C / name) and type(head['absent_before']) is bool,
            'Final source declaration must have exact path/absence type')
        if name in EXISTING:
            require(head['absent_before'] is False and head['before_sha256'] == before[name]['sha256']
                and head['before_bytes'] == before[name]['bytes'] and head['baseline'] == before[name]['baseline'],
                'Authorized delta must join exact independently captured original bytes')
        else:
            require(head['absent_before'] is True and head['before_sha256'] is None
                and head['before_bytes'] is None and head['baseline'] is None, 'New source cannot invent original bytes')
    def prior(group, path, sha, size, **extra):
        path = public_path(path)
        name = path.relative_to(C).as_posix() if path.is_relative_to(C) else None
        if name in EXISTING:
            old, new = before[name], heads[name]
            require(sha == old['sha256'] and size == old['bytes'], 'Prior source pin does not join exact M-before capture')
            check(group, old['baseline'], sha, size, 'authorized_delta_original_bytes_retained', original_path=str(path), **extra)
            check(group, path, new['sha256'], new['bytes'], 'authorized_stage_m_delta', original_sha256=sha, original_bytes=size, **extra)
        else:
            check(group, path, sha, size, **extra)
    for name, sha in [('evidence-manifest.json', L_EVIDENCE_SHA), ('preservation-check.json', L_PRESERVATION_SHA),
            ('source-manifest.json', L_SOURCE_SHA)]:
        check('prior_l_fixed_pins', L / name, sha, observed(L / name)['bytes'])
    artifacts = by_path(rows(evidence['files'], 97))
    for name, row in artifacts.items():
        check('prior_l_97_public_artifacts', L / name, row['sha256'], row['bytes'])
    records = rows(previous['checks'], 630)
    require(previous['all_checks_passed'] is True and type(previous['pin_checks']) is int and previous['pin_checks'] == 630
        and previous['unique_checked_paths'] == 507 and len({r['path'] for r in records}) == 507,
        'Prior 630 logical /507 unique-path qualification census differs')
    for row in records:
        require(row['passed'] is True and row['sha256'] == row['expected_sha256'] and row['bytes'] == row['expected_bytes'],
            'Prior logical preservation row was not qualified')
        prior('prior_l_630_logical_checks', row['path'], row['sha256'], row['bytes'])
    old = by_path(rows(old_sources['files'], 6))
    require(evidence['source_files'] == old_sources['files'] and set(old) & EXISTING == {
        'benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py',
        'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py'}, 'Exactly two prior L source deltas required')
    for name, row in old.items():
        prior('prior_l_six_sources', C / name, row['sha256'], row['bytes'])
    for name, row in before.items():
        check('all_sixteen_baseline_captures', row['baseline'], row['sha256'], row['bytes'])
        prior('all_sixteen_beginning_source_heads', C / name, row['sha256'], row['bytes'])
    for name, row in heads.items():
        check('all_fourteen_final_source_heads', C / name, row['sha256'], row['bytes'])
    # Reopen each already named file after all work, without discovery or body
    # re-reading, so cached logical checks cannot conceal a later substitution.
    for name, recorded in witnesses.items():
        handle, parent, info = opened(Path(name))
        try:
            require(witness(info) == recorded == witness(os.stat(Path(name).name, dir_fd=parent, follow_symlinks=False)),
                'Final named-file witness changed')
        finally:
            os.close(handle); os.close(parent)
    value = {'schema': 'nomination-lifecycle-independent-preservation@1', 'all_checks_passed': True,
        'inputs': inputs, 'checker': observed(Path(__file__).absolute()), 'checks': checks,
        'pin_checks': len(checks), 'unique_checked_paths': len({r['path'] for r in checks}),
        'unique_hashed_paths': len(cache), 'groups': {g: sum(r['group'] == g for r in checks) for g in sorted({r['group'] for r in checks})},
        'prior_l_97_public_artifacts_unchanged': True, 'prior_l_630_logical_checks_rechecked': True,
        'prior_l_507_original_unique_paths': 507, 'all_sixteen_baseline_captures_retained': True,
        'all_fourteen_final_source_pins_match': True, 'existing_authorized_deltas': sorted(EXISTING),
        'new_current_sources': sorted(NEW), 'unexpected_deltas': [],
        'database_bodies_read': False, 'credentials_or_raw_rollouts_read': False, 'recursive_discovery': False,
        'source_edits': False, 'git_index_mutated': False, 'providers_invoked': 0, 'tests_rerun': False,
        'limitations': ['Only explicitly nominated public byte/SHA pins; unlisted files and repository cleanliness are outside scope.',
            'Authorized source changes preserve exact original captures while separately checking root-pinned final heads.',
            'No actual SDK/task/model/proof/token-savings qualification is inferred from preservation.']}
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'receipt': str(output), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
        'pin_checks': len(checks), 'all_checks_passed': True}))


if __name__ == '__main__':
    main()
