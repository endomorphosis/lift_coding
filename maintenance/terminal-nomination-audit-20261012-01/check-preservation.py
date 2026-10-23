"""Recheck only explicit public K/L pins after the final L source freeze.

The required external final-manifest SHA is supplied by the root only after its
freeze notification. This program does not discover files recursively, import
production code, open database bodies, or read credentials/raw rollouts.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import stat

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
K = Path('/home/barberb/lift_coding/maintenance/terminal-nomination-worker-20261012-01')
L = Path('/home/barberb/lift_coding/maintenance/terminal-nomination-audit-20261012-01')
K_MANIFEST_SHA = 'ad571285402ec92f8c1042109ba2da9de36605b3a5a123bb035a279aa14dbe6c'
K_PRESERVATION_SHA = 'bd8a86fe13f6f3342c1b8cbf88f0cdc05d82c861a92fee10dd9960bc38bf6beb'
K_SOURCE_SHA = 'b161f6903af6d534b71592bef5d832603835c1a6d1b72f00a91ff63c3e60e8a0'
EXPECTED_EXISTING_DELTAS = frozenset({
    'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py',
    'benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py',
    'ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_context.py',
})
EXPECTED_NEW_FILES = frozenset({
    'ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_audit.py',
    'test/api/test_reviewed_source_nomination_audit.py',
    'benchmarks/agent_supervisor/container_coding/test_terminal_nomination_context_audit.py',
})
DENY_SUFFIXES = frozenset({'.duckdb', '.ducklake', '.db', '.sqlite', '.sqlite3', '.pem', '.key', '.p12', '.pfx', '.jsonl'})
DENY_PARTS = frozenset({'.codex', 'credentials', 'private', 'hidden', 'oracle', 'rollouts', 'transcripts'})
MAX_FILE_BYTES = 256_000_000
MAX_DOCUMENT_BYTES = 8_000_000
MAX_CHECKS = 2048
STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
cache, checks, input_pins = {}, [], []


def require(condition, message):
    if condition is not True:
        raise ValueError(message)


def digest(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('Canonical SHA256 required')
    return value


def byte_count(value):
    if type(value) is not int or not 0 <= value <= MAX_FILE_BYTES:
        raise ValueError('Exact bounded public byte count required')
    return value


def relative(name):
    if type(name) is not str or not name or len(name.encode('utf-8')) > 8192:
        raise ValueError('Bounded manifest-relative path required')
    path = PurePosixPath(name)
    if not path.parts or path.is_absolute() or str(path) != name or '..' in path.parts:
        raise ValueError('Canonical manifest-relative path required')
    return name


def public_path(path):
    path = Path(path)
    if (not path.is_absolute() or '..' in path.parts or str(path) != str(PurePosixPath(path))
            or path.suffix.lower() in DENY_SUFFIXES
            or any(part.lower() in DENY_PARTS for part in path.parts)):
        raise ValueError('Nonpublic explicit preservation path refused')
    return path


def _open_regular(path):
    """Walk only the nominated absolute path; no linked ancestor is followed."""
    path = public_path(path)
    current = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = following
        handle = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
        try:
            before = os.fstat(handle)
            if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= MAX_FILE_BYTES:
                raise ValueError('Bounded regular public preservation file required')
        except Exception:
            os.close(handle)
            raise
        return handle, current, before
    except Exception:
        os.close(current)
        raise


def _capture(path, *, maximum=MAX_FILE_BYTES, keep_bytes=False):
    path = public_path(path)
    handle, parent, before = _open_regular(path)
    try:
        require(before.st_size <= maximum, 'Public document exceeds its bound')
        size, hashed, captured = 0, hashlib.sha256(), []
        while True:
            block = os.read(handle, min(1_048_576, maximum + 1 - size))
            if not block:
                break
            size += len(block)
            require(size <= maximum, 'Public preservation file exceeded bounded read')
            hashed.update(block)
            if keep_bytes:
                captured.append(block)
        after = os.fstat(handle)
        named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        witness = lambda value: tuple(getattr(value, key) for key in STAT_FIELDS)
        require(witness(before) == witness(after) == witness(named), 'Public preservation input changed while hashing')
        require(size == before.st_size, 'Public preservation file size changed')
    finally:
        os.close(handle)
        os.close(parent)
    pin = {'path': str(path), 'bytes': size, 'sha256': hashed.hexdigest()}
    return pin, b''.join(captured) if keep_bytes else None


def observed(path, *, fresh=False):
    path = public_path(path)
    name = str(path)
    if not fresh and name in cache:
        return cache[name]
    pin, _ = _capture(path)
    cache[name] = pin
    return pin


def document(path, *, expected_sha256=None):
    pin, raw = _capture(path, maximum=MAX_DOCUMENT_BYTES, keep_bytes=True)
    if expected_sha256 is not None:
        require(pin['sha256'] == digest(expected_sha256), 'Selected public manifest digest differs')
    cache[pin['path']] = pin
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate manifest JSON key')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Nonfinite JSON constant refused')
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    require(type(value) is dict, 'Public manifest object required')
    input_pins.append(pin.copy())
    return value


def records(value, count):
    require(type(value) is list and len(value) == count, 'Explicit inventory population differs')
    require(all(type(row) is dict for row in value), 'Typed explicit inventory rows required')
    return value


def by_path(rows):
    result = {}
    for row in rows:
        name = relative(row['path'])
        require(name not in result, 'Duplicate explicit inventory path')
        digest(row['sha256'])
        byte_count(row['bytes'])
        result[name] = row
    return result


def check(group, path, sha256, size, *, disposition='unchanged', **extra):
    require(len(checks) < MAX_CHECKS, 'Logical preservation checks exceed bound')
    current = observed(path)
    sha256, size = digest(sha256), byte_count(size)
    passed = current['sha256'] == sha256 and current['bytes'] == size
    checks.append({**current, 'group': group, 'expected_sha256': sha256, 'expected_bytes': size,
        'disposition': disposition, 'passed': passed, **extra})
    require(passed, 'Explicit preservation pin mismatch: ' + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-manifest-sha256', required=True,
        help='Independent root-provided final source-manifest pin after its freeze')
    args = parser.parse_args()
    final_sha = digest(args.final_manifest_sha256)
    require(not (L / 'preservation-check.json').exists(), 'Refusing to replace a retained preservation receipt')
    prior_manifest = document(K / 'evidence-manifest.json', expected_sha256=K_MANIFEST_SHA)
    previous = document(K / 'preservation-check.json', expected_sha256=K_PRESERVATION_SHA)
    prior_sources = document(K / 'source-manifest.json', expected_sha256=K_SOURCE_SHA)
    before = document(L / 'beginning-source-pins.json')
    final = document(L / 'source-manifest.json', expected_sha256=final_sha)
    checker_pin = observed(Path(__file__).absolute())

    public_artifacts = by_path(records(prior_manifest['files'], 112))
    records(previous['checks'], 463)
    require(previous['all_checks_passed'] is True and type(previous['pin_checks']) is int
        and previous['pin_checks'] == 463, 'Prior K preservation is not the qualified 463-check receipt')
    require(type(previous['unique_checked_paths']) is int and previous['unique_checked_paths'] == 394
        and len({row['path'] for row in previous['checks']}) == 394, 'Prior K preservation unique-path census differs')
    source_before = by_path(records(prior_sources['files'], 11))
    require(set(source_before) & EXPECTED_EXISTING_DELTAS == {
        'benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py',
        'ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_context.py'},
        'Exactly two authorized L deltas must be old K source entries')
    require(prior_manifest['source_files'] == prior_sources['files'], 'Sealed K source inventory differs from its source manifest')
    baseline = by_path(records(before['files'], 9))
    require(before['checkout'] == str(C) and final['checkout'] == str(C), 'Source checkout identity differs')
    require(before['prior_manifest'] == {'path': str(K / 'evidence-manifest.json'), 'sha256': K_MANIFEST_SHA},
        'Beginning stage prior sealed manifest differs')
    source_pins = by_path(records(final['files'], 6))
    require(all(type(row.get('absent_before')) is bool for row in source_pins.values()), 'Exact source absence flags required')
    existing = {name: row for name, row in source_pins.items() if row['absent_before'] is False}
    new = {name: row for name, row in source_pins.items() if row['absent_before'] is True}
    require(set(existing) == EXPECTED_EXISTING_DELTAS, 'Only the three authorized existing L deltas are allowed')
    require(set(new) == EXPECTED_NEW_FILES, 'Only the three named new L files are allowed')
    for name, row in source_pins.items():
        require(row['absolute_path'] == str(C / name), 'Final source absolute path differs')
        if name in existing:
            digest(row['before_sha256'])
            byte_count(row['before_bytes'])
            require(name in baseline and row['before_sha256'] == baseline[name]['sha256']
                and row['before_bytes'] == baseline[name]['bytes'], 'Existing delta does not join exact L baseline')
        else:
            require(row.get('before_sha256') is None and row.get('before_bytes') is None,
                'New source must not assert an invented before pin')

    def prior_check(group, path, sha256, size, **extra):
        path = public_path(path)
        relative_name = path.relative_to(C).as_posix() if path.is_relative_to(C) else None
        if relative_name in existing:
            base, head = baseline[relative_name], existing[relative_name]
            require(sha256 == base['sha256'] and size == base['bytes'],
                'Older current-head pin does not match the exact L baseline capture')
            check(group, L / 'baseline' / relative_name, sha256, size,
                disposition='authorized_head_delta_original_bytes_retained', original_head_path=str(path), **extra)
            check(group, path, head['sha256'], head['bytes'], disposition='authorized_stage_l_delta',
                original_expected_sha256=sha256, original_expected_bytes=size, **extra)
        else:
            check(group, path, sha256, size, **extra)

    for name, expected in (('evidence-manifest.json', K_MANIFEST_SHA),
            ('preservation-check.json', K_PRESERVATION_SHA), ('source-manifest.json', K_SOURCE_SHA)):
        check('prior_k_fixed_manifest_receipt_pins', K / name, expected, observed(K / name)['bytes'])
    for name, row in public_artifacts.items():
        check('prior_k_112_public_artifacts', K / name, row['sha256'], row['bytes'])
    for row in previous['checks']:
        require(row['passed'] is True and row['sha256'] == row['expected_sha256']
            and row['bytes'] == row['expected_bytes'], 'Unqualified prior logical pin refused')
        prior_check('prior_463_logical_pin_rechecks', row['path'], row['sha256'], row['bytes'],
            historical_group=row['group'], historical_disposition=row['disposition'])
    for name, row in source_before.items():
        prior_check('prior_k_eleven_current_sources', C / name, row['sha256'], row['bytes'])
    for name, row in baseline.items():
        check('current_l_nine_baseline_captures', L / 'baseline' / name, row['sha256'], row['bytes'],
            disposition='captured_before_bytes_retained')
        prior_check('current_l_nine_current_sources', C / name, row['sha256'], row['bytes'])
    for name, row in source_pins.items():
        check('current_l_six_final_source_pins', C / name, row['sha256'], row['bytes'],
            disposition='new_stage_l_file' if row['absent_before'] else 'authorized_stage_l_delta_final_pin')
    require(final['patch_path'] == str(L / 'changes.patch'), 'Final patch path differs')
    check('current_l_final_patch', final['patch_path'], final['patch_sha256'], final['patch_bytes'], disposition='final_patch_pin')
    for pin in [*input_pins, checker_pin]:
        current = observed(pin['path'], fresh=True)
        require(current == pin, 'Selected manifest or checker changed during preservation')
        check('selected_manifest_and_checker_stability', pin['path'], pin['sha256'], pin['bytes'],
            disposition='inventory_unchanged_during_check')

    groups = {}
    for row in checks:
        group = groups.setdefault(row['group'], {'checks': 0, 'passed': 0, 'unique_paths': set()})
        group['checks'] += 1
        group['passed'] += row['passed']
        group['unique_paths'].add(row['path'])
    for group in groups.values():
        group['unique_paths'] = len(group['unique_paths'])
    prior_rows = [row for row in checks if row['group'] == 'prior_463_logical_pin_rechecks']
    authorized_heads = sorted({row['path'] for row in prior_rows if row['disposition'] == 'authorized_stage_l_delta'})
    receipt = {
        'schema': 'reviewed-source-nomination-historical-audit-preservation-check@1',
        'enumeration': 'Only explicit sealed K public inventory, prior K logical pins, L baseline and final source pins; no recursive/private discovery.',
        'inputs': input_pins, 'checker': checker_pin, 'checks': checks, 'groups': groups,
        'pin_checks': len(checks), 'unique_checked_paths': len({row['path'] for row in checks}),
        'unique_hashed_paths': len(cache), 'all_checks_passed': all(row['passed'] for row in checks),
        'prior_k_112_public_artifacts_unchanged': True,
        'prior_k_fixed_manifest_preservation_and_source_receipts_unchanged': True,
        'prior_463_logical_pins_rechecked': True, 'prior_463_original_unique_paths': 394,
        'prior_checks_unchanged_count': sum(row['disposition'] == 'unchanged' for row in prior_rows),
        'prior_authorized_head_delta_checks': sum(row['disposition'] == 'authorized_stage_l_delta' for row in prior_rows),
        'prior_authorized_head_delta_unique_paths': authorized_heads,
        'prior_expected_head_bytes_retained_for_every_authorized_delta': True,
        'prior_k_eleven_sources_nine_unchanged_two_authorized_l_deltas': True,
        'all_nine_current_baseline_captures_retained': True,
        'current_beginning_six_sources_unchanged_three_authorized_deltas': True,
        'all_six_final_source_pins_match': True,
        'authorized_current_delta_unique_paths': sorted(str(C / name) for name in existing),
        'new_current_source_paths': sorted(str(C / name) for name in new),
        'unexpected_deltas': [], 'provider_calls': 0, 'prover_invocations': 0,
        'database_bodies_read': False, 'credentials_or_raw_rollouts_read': False,
        'source_edits': False, 'tests_rerun': False,
        'limitations': [
            'Exact selected public bytes/SHA preservation only; unlisted files and whole-repository cleanliness are outside scope.',
            'Only the three explicitly authorized L current heads are replaced by final pins and independently joined to retained before bytes; no other historical pin is substituted.',
            'The old auditor head is joined directly through L baseline even though it is not a K source-manifest entry.',
            'No imported-producer equivalence, current admission/freshness, behavioral/task completion, source authentication, provider-token savings or model-convergence claim is established.'
        ]}
    output = L / 'preservation-check.json'
    with output.open('x') as stream:
        stream.write(json.dumps(receipt, sort_keys=True, separators=(',', ':')) + '\n')
    raw = output.read_bytes()
    print(json.dumps({'path': str(output), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
        'pin_checks': receipt['pin_checks'], 'unique_checked_paths': receipt['unique_checked_paths'],
        'all_checks_passed': receipt['all_checks_passed'], 'groups': groups,
        'prior_authorized_head_delta_checks': receipt['prior_authorized_head_delta_checks'],
        'prior_authorized_head_delta_unique_paths': authorized_heads}, sort_keys=True))


if __name__ == '__main__':
    main()
