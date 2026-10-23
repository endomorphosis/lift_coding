"""Recheck named P witnesses and Q's exact three-source scope.

Only the actual current context-audit path may replace a P current-head pin.
Original captures, aliases and every prior logical-row occurrence stay intact.
No discovery, production imports, database/key/auth/archive/raw-log body reads.
The two prequalified synthetic probe outputs use the old checksum-only guard.
"""
from collections import Counter
from pathlib import Path
import ast
import hashlib
import json
import os
import stat
import types

Q = Path('/home/barberb/lift_coding/maintenance/terminal-token-pairing-20261012-01')
P = Q.parent / 'terminal-observer-stop-20261012-01'
C = Q.parent / 'terminal-token-reduction-20261007-01/checkout'
P_CHECKER_SHA = '7126ae6981c4e33bfa3c46201672c93d91c2296358eea6885a1174a5ab977b05'
P_SEAL_SHA = 'f7b244a10e6b17daea6c359d01d754ad8be3da45af97a65e0d431a22e1bd0a96'
P_PRESERVATION_SHA = '113e82fbda6c37294f8814f1e9b0e01d43e4e67b89a015cf89d86d363f1bd88c'
Q_BASELINE_SHA = 'cdec804b7afbf8e6f3e3143f10666f602f42a15865fec8174c93ecbd13ae485e'
Q_RUNTIME_SHA = '7a7ac15c7b72c366e04d665a4cd2f52f3b737d34f8780f6bc642cb5d4afa2a7f'
EXISTING = 'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py'
NEW_RUNTIME = 'benchmarks/agent_supervisor/container_coding/terminal_input_token_comparison.py'
NEW_TEST = 'benchmarks/agent_supervisor/container_coding/test_terminal_input_token_comparison.py'
OLD = (83378, '9172ccc9c846a035743bb3af4c874a331025e0cb2ff3d6612b9a1c22fcea906c')
FINAL = {
    EXISTING: (87508, '812ce0ac0fdc0bc91567b289a5f0932a25df7c195657bf471478d269e532958e'),
    NEW_RUNTIME: (16612, 'd4c4eb707aeedd754bbe05460a0539c8b9795f0426178da5aaf276bc185774d6'),
    NEW_TEST: (16142, 'b51ef991193c39acaec774e03293b4e9a233458b5f4383e0a8c16e7723aba912'),
}
STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
    'st_size', 'st_mtime_ns', 'st_ctime_ns')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_p_guards():
    """Compile only exact pinned bytes, under a non-main module identity."""
    path = P / 'check-preservation.py'
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        handle = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(handle)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != 15655:
                raise ValueError('Pinned P guard must be a bounded single-link regular file')
            raw = bytearray()
            while len(raw) <= 15655:
                block = os.read(handle, 15656 - len(raw))
                if not block:
                    break
                raw.extend(block)
            witness = lambda item: tuple(getattr(item, key) for key in STAT_FIELDS)
            if (len(raw) != 15655 or sha(raw) != P_CHECKER_SHA
                    or witness(before) != witness(os.fstat(handle))
                    or witness(before) != witness(os.stat(path.name, dir_fd=parent, follow_symlinks=False))):
                raise ValueError('Pinned P guard bytes or witness changed')
        finally:
            os.close(handle)
    finally:
        os.close(parent)
    module = types.ModuleType('q_read_only_p_guard_provider')
    module.__file__ = str(path)
    exec(compile(bytes(raw), str(path), 'exec'), module.__dict__)
    guard = module.g
    pin, retained = guard.capture(path, maximum=15655, retain=True)
    guard.require(retained == bytes(raw) and pin['sha256'] == P_CHECKER_SHA
        and guard.witnesses[str(path)] == witness(before), 'Pinned P guard changed after compilation')
    return module, guard


def main():
    if Path(__file__).absolute() != Q / 'check-preservation.py':
        raise ValueError('Only the named Q checker is permitted')
    output = Q / 'preservation-check.json'
    if output.exists() or output.is_symlink():
        raise ValueError('Fresh Q preservation report only; no replacement')
    parent, g = load_p_guards()
    seal = g.document(P / 'evidence-manifest.json', P_SEAL_SHA)
    previous = g.document(P / 'preservation-check.json', P_PRESERVATION_SHA)
    baseline = g.document(Q / 'baseline-manifest.json', Q_BASELINE_SHA)
    runtime = g.document(Q / 'runtime-source-pins.json', Q_RUNTIME_SHA)
    g.require(seal['schema'] == 'terminal-observer-stop-explicit-public-evidence-seal@1'
        and seal['all_named_guards_passed'] is True and type(seal['file_count']) is int
        and seal['file_count'] == 77, 'Exact sealed P inventory required')
    g.require(previous['schema'] == 'terminal-observer-stop-preservation@1'
        and previous['all_checks_passed'] is True and type(previous['pin_checks']) is int
        and previous['pin_checks'] == 1667 and type(previous['unique_checked_paths']) is int
        and previous['unique_checked_paths'] == 1239, 'Exact prior preservation census required')
    g.require(set(baseline) == {'schema', 'checkout', 'files', 'sealed_prior_manifest'}
        and baseline['schema'] == 'terminal-token-pair-baseline@1' and baseline['checkout'] == str(C),
        'Closed Q baseline required')
    g.require(baseline['sealed_prior_manifest'] == {'path': str(P / 'evidence-manifest.json'),
        'bytes': 21835, 'sha256': P_SEAL_SHA}, 'Q baseline must retain exact P seal identity')
    before = {}
    for row in g.rows(baseline['files'], 3):
        name = g.relative(row['path'])
        g.require(name not in before, 'Unique Q baseline paths required')
        before[name] = row
    g.require(set(before) == set(FINAL), 'Exactly one existing and two new Q sources')
    original = before[EXISTING]
    g.require(original == {'path': EXISTING, 'exists': True, 'capture': str(Q / 'baseline' / EXISTING),
        'bytes': OLD[0], 'sha256': OLD[1]}, 'Exact Q before-source capture required')
    for name in (NEW_RUNTIME, NEW_TEST):
        g.require(before[name] == {'path': name, 'exists': False}, 'New Q source must be recorded absent before edits')
    g.require(set(runtime) == {'schema', 'checkout', 'files'}
        and runtime['schema'] == 'terminal-token-pair-runtime-pins@1' and runtime['checkout'] == str(C),
        'Closed independently frozen Q runtime pins required')
    runtime_rows = g.by_path(g.rows(runtime['files'], 2))
    g.require(set(runtime_rows) == {EXISTING, NEW_RUNTIME}
        and all(row == {'path': name, 'bytes': FINAL[name][0], 'sha256': FINAL[name][1]}
            for name, row in runtime_rows.items()), 'Both exact frozen Q runtime heads required')

    # Registration permits only the already pinned two synthetic empty-prompt
    # boundary probes. It never adds a general raw-log read exception.
    historical = g.document(g.N / 'preservation-check.json', g.PRESERVATION_SHA)
    g.register_published_boundary_probes(historical)
    g.require(sorted(g.opaque_public_pins) == previous['opaque_boundary_probe_checksum_paths']
        and sum(row['bytes'] for row in g.opaque_public_pins.values()) == 2614,
        'Exactly two previous synthetic checksum-only probes required')

    replacements = []
    logical_links = []
    target = C / EXISTING
    capture = Q / 'baseline' / EXISTING

    def prior(group, path, expected_sha, expected_bytes, *, link=None):
        path = g.public_path(path)
        initial = len(g.checks)
        if path == target:
            g.require((expected_bytes, expected_sha) == OLD,
                'Only exact P current context-audit pin may be replaced')
            g.check(group, capture, OLD[1], OLD[0], 'authorized_q_original_retained',
                original_path=str(path))
            g.check(group, target, FINAL[EXISTING][1], FINAL[EXISTING][0], 'authorized_q_current',
                original_sha256=OLD[1], original_bytes=OLD[0])
            replacements.append({'group': group, 'original_path': str(path),
                'retained_original_path': str(capture), 'prior_row_index': link})
        else:
            g.check(group, path, expected_sha, expected_bytes)
        return list(range(initial, len(g.checks)))

    sealed_rows = g.rows(seal['files'], 77)
    names = set()
    sealed_links = []
    for index, row in enumerate(sealed_rows):
        g.require(set(row) == {'path', 'bytes', 'sha256'}, 'Closed sealed P pin required')
        path = g.public_path(row['path'])
        g.require(str(path) not in names and (path.is_relative_to(P) or path.is_relative_to(C)),
            'Unique explicit P sealed artifacts/current heads required')
        names.add(str(path))
        indices = prior('prior_p_77_sealed_entries', path, row['sha256'], row['bytes'])
        sealed_links.append({'prior_row_index': index, 'prior_row_sha256': sha(canonical(row)),
            'current_check_indices': indices})
    logical_rows = g.rows(previous['checks'], 1667)
    g.require(len({row['path'] for row in logical_rows}) == 1239, 'Exact prior logical-row path census')
    for index, row in enumerate(logical_rows):
        g.require(row['passed'] is True and row['sha256'] == row['expected_sha256']
            and row['bytes'] == row['expected_bytes'], 'Only previously qualified exact logical pins reused')
        indices = prior('prior_p_1667_logical_rows', row['path'], row['sha256'], row['bytes'], link=index)
        logical_links.append({'prior_row_index': index, 'prior_row_sha256': sha(canonical(row)),
            'current_check_indices': indices})
    g.require(Counter(row['prior_row_sha256'] for row in logical_links)
        == Counter(sha(canonical(row)) for row in logical_rows)
        and [row['prior_row_index'] for row in logical_links] == list(range(1667)),
        'Every complete prior logical-row occurrence must be rechecked without deduplication')
    g.require(Counter(row['prior_row_sha256'] for row in sealed_links)
        == Counter(sha(canonical(row)) for row in sealed_rows), 'Exact P seal pin multiset required')
    g.require(len(replacements) == 12 and all(row['group'] == 'prior_p_1667_logical_rows'
        and row['original_path'] == str(target) for row in replacements), 'Only twelve actual current-head row substitutions')

    g.check('q_original_capture', capture, OLD[1], OLD[0])
    for name, (size, expected_sha) in FINAL.items():
        g.check('q_final_heads', C / name, expected_sha, size)
        pin, raw = g.capture(C / name, maximum=2_000_000, retain=True)
        ast.parse(raw)
        g.require(pin['bytes'] == size and pin['sha256'] == expected_sha, 'Final source changed before syntax check')
    checker_pin = g.observed(Path(__file__))
    for name, recorded in g.witnesses.items():
        handle, directory, info = g.opened(Path(name))
        try:
            g.require(g.witness(info) == recorded == g.witness(os.stat(Path(name).name,
                dir_fd=directory, follow_symlinks=False)), 'Named public witness changed before report publication')
        finally:
            os.close(handle)
            os.close(directory)
    value = {'schema': 'terminal-input-token-pair-preservation@1', 'all_checks_passed': True,
        'checks': g.checks, 'pin_checks': len(g.checks),
        'unique_checked_paths': len({row['path'] for row in g.checks}), 'unique_hashed_paths': len(g.cache),
        'prior_p_sealed_entries': 77, 'prior_p_logical_rows': 1667, 'prior_p_unique_logical_paths': 1239,
        'prior_p_sealed_links': sealed_links, 'prior_p_logical_links': logical_links,
        'all_prior_logical_rows_rechecked_without_deduplication': True,
        'complete_prior_logical_row_multiset_retained': True, 'substitutions': replacements,
        'substitution_rule': {'actual_path_only': str(target), 'before_bytes': OLD[0], 'before_sha256': OLD[1],
            'retained_original_path': str(capture), 'after_bytes': FINAL[EXISTING][0],
            'after_sha256': FINAL[EXISTING][1], 'capture_aliases_and_original_path_metadata_rewritten': False},
        'baseline_sha256': Q_BASELINE_SHA, 'runtime_source_pins_sha256': Q_RUNTIME_SHA,
        'baseline_source_count': 3, 'existing_source_count': 1, 'new_source_count': 2,
        'final_sources': [{'path': name, 'bytes': size, 'sha256': expected_sha}
            for name, (size, expected_sha) in FINAL.items()],
        'final_python_sources_parse': True, 'inputs': g.inputs, 'checker': checker_pin,
        'p_guard_provider_sha256': P_CHECKER_SHA, 'p_guard_main_called': False,
        'opaque_boundary_probe_checksum_paths': sorted(g.opaque_public_pins),
        'opaque_boundary_probe_bytes_streamed': 2614, 'unexpected_deltas': [],
        'recursive_discovery': False, 'raw_worker_model_or_daemon_log_text_read': False,
        'archive_bodies_read_or_extracted': False, 'database_or_key_or_auth_bodies_read': False,
        'sealed_p_or_prior_stages_mutated': False, 'original_git_index_mutated': False,
        'providers_or_tests_or_provers_run': False, 'source_equivalence_proved': False,
        'global_model_convergence_proved': False, 'full_task_satisfaction_established': False,
        'provider_total_session_token_savings_established': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
        'limitations': ['Only explicitly named file witnesses; no unlisted tree cleanliness or owner immutability claim.',
            'Each of the 1667 complete previous logical-row occurrences is linked independently; only an actual current-head path is substituted.',
            'Two exact published synthetic boundary probes are checksum streams only; their bodies are never retained or parsed.',
            'No archive payloads, private databases, keys, auth files or worker/model raw log bodies are read.',
            'Preservation and syntax checks grant no semantic equivalence, task completion, convergence or provider token-usage claim.']}
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'path': str(output), 'bytes': len(raw), 'sha256': sha(raw),
        'pin_checks': len(g.checks), 'all_checks_passed': True}))


if __name__ == '__main__':
    main()
