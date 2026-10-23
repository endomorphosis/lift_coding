"""Check only the declared P sources and named, sealed public predecessor pins.

No discovery, database/auth/key/raw-log reads or native imports. Two exact
previously qualified synthetic boundary-probe outputs are checksum streams;
their text is never retained or parsed. Execution requires a final source SHA.
"""
from pathlib import Path
import argparse
import hashlib
import os
import stat
import types
import json

P = Path('/home/barberb/lift_coding/maintenance/terminal-observer-stop-20261012-01')
O = P.parent / 'terminal-nomination-identity-20261012-01'
C = P.parent / 'terminal-token-reduction-20261007-01/checkout'
ORIGINAL_BASELINE_SHA = '82cfd195184c584636e844fa4ed89698fd054885d68be5106f1d35111ffc1b6e'
BASELINE_SHA = 'fdaded9fa0e30bdfa9abed06bdcc52ef3b4aa0bbcd285fc7eec343d891af8011'
GUARD_SHA = 'd12e0b3219170e2d5410650bbaa2831aa09702c8843d21c10a836ae0603913a1'
ANCHORS = {
    'source-manifest-03.json': (9469, '621d0da859f03099ffee747b6e185f28518d71954ca99f053db30f0f696435b5'),
    'preservation-check-03.json': (720991, '43010a2208c2ffc6f45bc37a0909c6d016442aa2e500459076174262a4a37c27'),
    'evidence-manifest.json': (70094, '1cb70ce8e9d67372868e8245e6d553181241d18631aa1618f557c5424ad095be'),
    'check-preservation.py': (27106, GUARD_SHA),
    'result-summary.json': (6629, '17271de6a712451df56157824162dcb862791ffacf69edf77dfb7e2548b54d3f'),
    'next-work.json': (5493, '62258f4d821370916781d8d297c48f547ff3692ab0fea18723d1dbbccd44b94b'),
}
EXISTING = frozenset({
    'benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py',
    'benchmarks/agent_supervisor/container_coding/retained_source_nomination_lifecycle.py',
    'benchmarks/agent_supervisor/container_coding/test_retained_source_nomination_lifecycle.py',
    'benchmarks/agent_supervisor/container_coding/test_terminal_native_dispatch_diagnostics.py',
})
NEW = frozenset({
    'benchmarks/agent_supervisor/container_coding/terminal_observer_stop.py',
    'benchmarks/agent_supervisor/container_coding/test_terminal_observer_stop.py',
})
TESTS = frozenset(name for name in EXISTING | NEW if Path(name).name.startswith('test_'))
PRODUCTION = (EXISTING | NEW) - TESTS
PIN_SCHEMA = 'terminal-observer-stop-final-source-pins@1'
MANIFEST_SCHEMA = 'terminal-observer-stop-source-manifest@1'
MAX_SOURCE = 2_000_000


def _load_guards():
    """Execute the exact already-sealed guard bytes, never a mutable reread."""
    path = O / 'check-preservation.py'
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            next_directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = next_directory
        handle = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            first = os.fstat(handle)
            if not stat.S_ISREG(first.st_mode) or first.st_nlink != 1 or first.st_size != 27106:
                raise ValueError('Pinned public guard must be a regular single-link file')
            body = bytearray()
            while len(body) <= 27106:
                block = os.read(handle, 27107 - len(body))
                if not block: break
                body.extend(block)
            fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                'st_size', 'st_mtime_ns', 'st_ctime_ns')
            witness = lambda info: tuple(getattr(info, name) for name in fields)
            if (witness(first) != witness(os.fstat(handle))
                    or witness(first) != witness(os.stat(path.name, dir_fd=directory, follow_symlinks=False))
                    or len(body) != 27106 or hashlib.sha256(body).hexdigest() != GUARD_SHA):
                raise ValueError('Sealed public guard changed')
        finally: os.close(handle)
    finally: os.close(directory)
    module = types.ModuleType('p_sealed_public_guards'); module.__file__ = str(path)
    exec(compile(bytes(body), str(path), 'exec'), module.__dict__)
    pin, captured = module.capture(path, maximum=27106, retain=True)
    module.require(captured == bytes(body) and module.witnesses[str(path)] == witness(first),
        'Guard changed after verified compilation')
    return module


g = _load_guards()


def baseline():
    original = g.document(P / 'baseline-manifest.json', ORIGINAL_BASELINE_SHA)
    value = g.document(P / 'baseline-manifest-02.json', BASELINE_SHA)
    g.require(set(value) == {'schema', 'checkout', 'existing_files', 'new_files', 'previous_stage_anchors'}
        and value['schema'] == 'terminal-observer-stop-baseline@1' and value['checkout'] == str(C),
        'Exact independently pinned P baseline required')
    g.require(original['existing_files'] == value['existing_files'][:3]
        and original['new_files'] == value['new_files']
        and original['previous_stage_anchors'] == value['previous_stage_anchors'],
        'Scope extension must retain the exact initial baseline population')
    before = g.by_path(g.rows(value['existing_files'], 4))
    g.require(set(before) == EXISTING, 'Only the four declared existing P sources')
    for name, row in before.items():
        g.require(set(row) == {'path', 'baseline_path', 'bytes', 'sha256'}
            and row['baseline_path'] == str(P / 'baseline' / name), 'Exact original capture path required')
    absent = g.rows(value['new_files'], 2)
    g.require({row['path'] for row in absent} == NEW
        and all(set(row) == {'path', 'absent'} and row['absent'] is True for row in absent),
        'Exact two before-absent sources required')
    seen = set()
    for row in g.rows(value['previous_stage_anchors'], 6):
        g.require(set(row) == {'path', 'bytes', 'sha256'}, 'Closed prior anchor descriptor')
        path = g.public_path(row['path'])
        g.require(path.parent == O and path.name in ANCHORS and path.name not in seen, 'Only fixed O anchor names')
        seen.add(path.name); size, sha = ANCHORS[path.name]
        g.require(row['bytes'] == size and row['sha256'] == sha, 'Prior anchor differs from selected sealed O bytes')
        pin, _ = g.capture(path)
        g.require(pin['bytes'] == size and pin['sha256'] == sha, 'Selected O anchor changed')
    return before


def final_sources(value, before, *, source_manifest=False):
    if source_manifest:
        g.require(value['schema'] == MANIFEST_SCHEMA and value['checkout'] == str(C)
            and value['baseline_sha256'] == BASELINE_SHA, 'P source manifest must bind original baseline')
    else:
        g.require(set(value) == {'schema', 'checkout', 'files'} and value['schema'] == PIN_SCHEMA
            and value['checkout'] == str(C), 'Closed independent final source freeze required')
    heads = g.by_path(g.rows(value['files'], 6))
    g.require(set(heads) == EXISTING | NEW, 'Exact final six-source scope only')
    for name, row in heads.items():
        g.require(1 <= row['bytes'] <= MAX_SOURCE, 'Nonempty bounded Python source required')
        if not source_manifest:
            g.require(set(row) == {'path', 'bytes', 'sha256'}, 'Closed final source descriptor required')
        else:
            g.require(set(row) == {'path', 'absolute_path', 'bytes', 'sha256', 'absent_before',
                'runtime_archive_member', 'before_sha256', 'before_bytes', 'baseline'},
                'Closed source-manifest descriptor required')
            g.require(row['absolute_path'] == str(C / name) and row['absent_before'] is (name in NEW)
                and row['runtime_archive_member'] is (name in PRODUCTION), 'Exact source role/absence joins')
            old = before.get(name)
            g.require(row['before_sha256'] == (old['sha256'] if old else None)
                and row['before_bytes'] == (old['bytes'] if old else None)
                and row['baseline'] == (old['baseline_path'] if old else None), 'Exact source original-capture joins')
    return heads


def suffix(generation):
    return '-' + generation if generation else ''


def named_p(path):
    path = g.public_path(path)
    g.require(path.is_relative_to(P), 'Only explicitly provided canonical P public input')
    return path


def final_witnesses():
    for name, recorded in g.witnesses.items():
        handle, parent, info = g.opened(Path(name))
        try:
            g.require(g.witness(info) == recorded == g.witness(os.stat(Path(name).name, dir_fd=parent,
                follow_symlinks=False)), 'Named file changed before publication')
        finally: os.close(handle); os.close(parent)


def exclusive(path, body):
    g.require(path.parent == P and not path.exists() and not path.is_symlink(), 'Fresh direct P artifact only')
    with path.open('xb') as stream: stream.write(body)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--final-manifest-sha256', required=True)
    parser.add_argument('--final-manifest', type=Path)
    parser.add_argument('--artifact-generation', choices=('02', '03', '04'))
    args = parser.parse_args(); tag = suffix(args.artifact_generation)
    manifest_path = named_p(args.final_manifest or P / ('source-manifest' + tag + '.json'))
    g.require(manifest_path == P / ('source-manifest' + tag + '.json'), 'Manifest filename must match generation')
    output = P / ('preservation-check' + tag + '.json')
    g.require(not output.exists() and not output.is_symlink(), 'No preservation receipt replacement')
    before = baseline()
    final = g.document(manifest_path, g.digest(args.final_manifest_sha256))
    heads = final_sources(final, before, source_manifest=True)
    sealed = g.document(O / 'evidence-manifest.json', ANCHORS['evidence-manifest.json'][1])
    previous = g.document(O / 'preservation-check-03.json', ANCHORS['preservation-check-03.json'][1])
    old_manifest = g.document(O / 'source-manifest-03.json', ANCHORS['source-manifest-03.json'][1])
    g.require(sealed['schema'] == 'terminal-nomination-identity-explicit-public-evidence-seal@1'
        and sealed['all_named_guards_passed'] is True and type(sealed['file_count']) is int
        and sealed['file_count'] == 186, 'Exact prior O seal required')
    g.require(previous['all_checks_passed'] is True and type(previous['pin_checks']) is int
        and previous['pin_checks'] == 1413 and type(previous['unique_checked_paths']) is int
        and previous['unique_checked_paths'] == 1065, 'Exact prior O preservation census required')
    # This trusted guard registers only the original exact two opaque probes
    # after joining their fixed N public preservation/qualification metadata.
    historical = g.document(g.N / 'preservation-check.json', g.PRESERVATION_SHA)
    g.register_published_boundary_probes(historical)
    def prior(group, path, sha, size):
        path = g.public_path(path)
        name = path.relative_to(C).as_posix() if path.is_relative_to(C) else None
        if name in EXISTING:
            old, new = before[name], heads[name]
            g.require(sha == old['sha256'] and size == old['bytes'], 'Prior actual C head differs from P-before capture')
            g.check(group, old['baseline_path'], sha, size, 'authorized_p_original_retained', original_path=str(path))
            g.check(group, path, new['sha256'], new['bytes'], 'authorized_p_current', original_sha256=sha, original_bytes=size)
        else:
            g.check(group, path, sha, size)
    for name, (size, sha) in ANCHORS.items(): g.check('fixed_o_anchors', O / name, sha, size)
    old_heads = g.by_path(g.rows(old_manifest['files'], 11))
    paths, source_rows = set(), 0
    for row in g.rows(sealed['files'], 186):
        path = g.public_path(row['path'])
        g.require(str(path) not in paths and (path.is_relative_to(O)
            or (path.is_relative_to(C) and path.relative_to(C).as_posix() in old_heads)),
            'Only unique sealed O artifacts/eleven declared source heads')
        paths.add(str(path)); source_rows += path.is_relative_to(C)
        prior('prior_o_186_sealed_entries', path, row['sha256'], row['bytes'])
    g.require(source_rows == 11, 'Exact eleven predecessor current source rows')
    logical = g.rows(previous['checks'], 1413)
    g.require(len({row['path'] for row in logical}) == 1065, 'Exact prior logical multiset/path census')
    for row in logical:
        g.require(row['passed'] is True and row['sha256'] == row['expected_sha256']
            and row['bytes'] == row['expected_bytes'], 'Only qualified historical logical checks reused')
        prior('prior_o_1413_logical_rows', row['path'], row['sha256'], row['bytes'])
    for name, row in old_heads.items():
        prior('prior_o_eleven_source_heads', C / name, row['sha256'], row['bytes'])
        if row['absent_before'] is False:
            g.check('prior_o_original_captures', row['baseline'], row['before_sha256'], row['before_bytes'])
    for name, row in before.items():
        g.check('p_original_captures', row['baseline_path'], row['sha256'], row['bytes'])
        prior('p_original_heads', C / name, row['sha256'], row['bytes'])
    for name, row in heads.items(): g.check('p_final_heads', C / name, row['sha256'], row['bytes'])
    g.check('p_patch', P / ('changes' + tag + '.patch'), final['patch_sha256'], final['patch_bytes'])
    final_witnesses()
    value = {'schema': 'terminal-observer-stop-preservation@1', 'all_checks_passed': True,
        'checks': g.checks, 'pin_checks': len(g.checks), 'unique_checked_paths': len({x['path'] for x in g.checks}),
        'unique_hashed_paths': len(g.cache), 'prior_o_sealed_entries': 186, 'prior_o_logical_rows': 1413,
        'prior_o_unique_logical_paths': 1065, 'all_prior_logical_rows_rechecked_without_deduplication': True,
        'existing_authorized_deltas': sorted(EXISTING), 'new_sources': sorted(NEW), 'final_source_count': 6,
        'original_capture_count': 4, 'unexpected_deltas': [], 'baseline_sha256': BASELINE_SHA,
        'original_baseline_sha256': ORIGINAL_BASELINE_SHA,
        'final_manifest_sha256': args.final_manifest_sha256, 'inputs': g.inputs, 'checker': g.observed(Path(__file__)),
        'opaque_boundary_probe_checksum_paths': sorted(g.opaque_public_pins),
        'opaque_boundary_probe_bytes_streamed': sum(row['bytes'] for row in g.opaque_public_pins.values()),
        'raw_worker_model_or_daemon_log_text_read': False, 'archive_bodies_read_or_extracted': False,
        'database_or_key_or_auth_bodies_read': False, 'recursive_discovery': False,
        'source_edits_or_prior_stage_mutation': False, 'original_git_index_mutated': False,
        'providers_or_tests_or_provers_run': False, 'proof_authority': False, 'completion_authority': False,
        'execution_authority': False, 'source_equivalence_proved': False, 'model_convergence_proved': False,
        'limitations': ['Only explicit named byte/SHA witnesses, not unlisted tree cleanliness or owner immutability.',
            'Actual C paths alone are substituted; historical captures and original_path aliases are never rewritten.',
            'Two exact published synthetic probe outputs are checksum streams only; no generic log exception.',
            'Preservation grants no task completion, source semantics, provider billing or total-token claim.']}
    raw = canonical(value); exclusive(output, raw)
    print(json.dumps({'path': str(output), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
        'pin_checks': len(g.checks), 'all_checks_passed': True}))


if __name__ == '__main__': main()
