"""Package exactly root-pinned stage N sources; never execute target code.

Run only after explicit final freeze. Existing original bytes come from five
independently pinned captures. Syntax parsing and git apply use a fresh local scratch
checkout. No original Git index, provider, database, key or hidden fixture reads.
"""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
import os
import subprocess

N = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('stage_n_named_public_guards', N / 'check-preservation.py')
guards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guards)
C = guards.C
PIN_SCHEMA = 'native-dispatch-diagnostics-final-source-pins@1'
RUNTIME_PRODUCTION = guards.MANDATORY_EXISTING | {'ipfs_accelerate_py/agent_supervisor/runtime/native_dispatch_diagnostics.py'}
MAX_SOURCE = 4_000_000
MAX_PATCH = 8_000_000


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def exclusive(path, raw):
    guards.require(path.is_relative_to(N) and not path.exists() and not path.is_symlink(), 'New stage artifact only')
    with path.open('xb') as stream:
        stream.write(raw)


def git(scratch, argv):
    return subprocess.run(['/usr/bin/git', *argv], cwd=scratch, capture_output=True, check=True,
        timeout=30, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-pins', type=Path, required=True)
    parser.add_argument('--source-pins-sha256', required=True)
    parser.add_argument('--runtime-manifest', type=Path, required=True)
    parser.add_argument('--runtime-manifest-sha256', required=True)
    parser.add_argument('--include-bridge-delta', action='store_true')
    args = parser.parse_args()
    guards.require(args.source_pins.is_relative_to(N) and args.runtime_manifest.is_relative_to(N),
        'Only explicitly named public inputs under new stage')
    before = guards.beginning_sources()
    existing = guards.MANDATORY_EXISTING | ({guards.BRIDGE} if args.include_bridge_delta else set())
    names = existing | guards.NEW
    freeze = guards.document(args.source_pins, args.source_pins_sha256)
    guards.require(set(freeze) == {'schema', 'checkout', 'files'} and freeze['schema'] == PIN_SCHEMA
        and freeze['checkout'] == str(C), 'Closed independently pinned final source declaration required')
    expected = guards.by_path(guards.rows(freeze['files'], len(names)))
    guards.require(set(expected) == names, 'Final source declaration differs from explicit authorized set')
    archive = guards.document(args.runtime_manifest, args.runtime_manifest_sha256)
    guards.require(type(archive.get('files')) is list and 1 <= len(archive['files']) <= 20000,
        'Bounded explicit runtime archive inventory required')
    members = guards.by_path(archive['files'])
    production = RUNTIME_PRODUCTION | ({guards.BRIDGE} if args.include_bridge_delta else set())
    tests = guards.NEW - RUNTIME_PRODUCTION
    guards.require(len(tests) == 2 and all('source/' + name not in members for name in tests),
        'The two host tests must be excluded from installed archive')
    scratch = N / 'patch-qualification-01'
    guards.require(not scratch.exists() and not scratch.is_symlink(), 'Fresh patch qualification namespace required')
    for name in ('changes.patch', 'source-manifest.json', 'patch-qualification.json'):
        guards.require(not (N / name).exists() and not (N / name).is_symlink(), 'Existing artifacts remain immutable')
    current, originals, source_pins, patches = {}, {}, {}, []
    for name in sorted(names):
        got, body = guards.capture(C / name, maximum=MAX_SOURCE, retain=True)
        guards.require(got['sha256'] == expected[name]['sha256'] and got['bytes'] == expected[name]['bytes'],
            'Current source differs from independent final freeze')
        ast.parse(body.decode('utf-8'), filename=name)
        current[name], source_pins[name] = body, got
        if name in existing:
            row = before[name]
            observed, original = guards.capture(Path(row['baseline']), maximum=MAX_SOURCE, retain=True)
            guards.require(observed['sha256'] == row['sha256'] and observed['bytes'] == row['bytes'],
                'Existing source does not join exact original capture')
            originals[name] = original
            old_header = 'a/' + name
        else:
            original, old_header = b'', '/dev/null'
        patches.extend(difflib.unified_diff(original.decode().splitlines(keepends=True), body.decode().splitlines(keepends=True),
            fromfile=old_header, tofile='b/' + name))
        if name in production:
            row = members.get('source/' + name)
            guards.require(row is not None and row['sha256'] == got['sha256'] and row['bytes'] == got['bytes'],
                'Production source does not join pinned final runtime inventory')
    # The unchanged bridge producer remains explicitly checked even when it is
    # not an authorized delta. No discovery or implicit scope promotion.
    for name, row in before.items():
        observed, _ = guards.capture(Path(row['baseline']), maximum=MAX_SOURCE)
        guards.require(observed['sha256'] == row['sha256'] and observed['bytes'] == row['bytes'],
            'Original producer capture changed')
        if name not in existing:
            observed, _ = guards.capture(C / name, maximum=MAX_SOURCE)
            guards.require(observed['sha256'] == row['sha256'] and observed['bytes'] == row['bytes'],
                'Unchanged bridge differs; explicit new authorization required')
    patch = ''.join(patches).encode('utf-8')
    guards.require(0 < len(patch) <= MAX_PATCH, 'Bounded nonempty exact source patch required')
    scratch.mkdir(mode=0o700)
    tree = scratch / 'checkout'; tree.mkdir(mode=0o700)
    for name, body in originals.items():
        path = tree / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(body)
    patch_copy = scratch / 'changes.patch'; exclusive(patch_copy, patch)
    init = git(tree, ['init', '--quiet'])
    checked = git(tree, ['apply', '--check', str(patch_copy)])
    applied = git(tree, ['apply', str(patch_copy)])
    applied_rows = []
    for name, body in current.items():
        got, copied = guards.capture(tree / name, maximum=MAX_SOURCE, retain=True)
        guards.require(copied == body, 'Applied scratch source bytes differ')
        applied_rows.append({'path': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'bytes_exact': True})
    # Reread only already-named current producers after parse/diff/scratch Git.
    for name, expected_body in current.items():
        got, body = guards.capture(C / name, maximum=MAX_SOURCE, retain=True)
        guards.require(body == expected_body and got == source_pins[name], 'Source changed during packaging')
    files = []
    for name in sorted(names):
        old = before.get(name) if name in existing else None
        files.append({'path': name, 'absolute_path': str(C / name), 'bytes': source_pins[name]['bytes'],
            'sha256': source_pins[name]['sha256'], 'absent_before': old is None,
            'before_sha256': old['sha256'] if old else None, 'before_bytes': old['bytes'] if old else None,
            'baseline': old['baseline'] if old else None, 'runtime_archive_member': name in production})
    manifest = {'schema': 'native-dispatch-diagnostics-source-manifest@1', 'checkout': str(C), 'files': files,
        'existing_deltas': len(existing), 'new_files': 3, 'runtime_source_files': len(production), 'host_test_files': 2,
        'bridge_delta_explicitly_authorized': args.include_bridge_delta,
        'patch_bytes': len(patch), 'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'runtime_manifest_sha256': args.runtime_manifest_sha256,
        'independent_final_source_pins': guards.observed(args.source_pins),
        'patch_applies_cleanly_to_captured_baselines': True, 'applied_changed_bytes_match_checkout': True,
        'all_production_source_hashes_match_runtime_manifest': True, 'host_test_sources_excluded_from_runtime': True,
        'original_dirty_checkout_or_git_index_mutated': False, 'remote_publication_performed': False,
        'source_semantics_or_equivalence_proved': False, 'model_convergence_proved': False}
    qualification = {'schema': 'native-dispatch-diagnostics-patch-qualification@1', 'qualified': True,
        'scratch': str(scratch), 'applied_sources': applied_rows, 'syntax_parsed_only': True,
        'git_apply_check_passed': checked.returncode == 0, 'git_apply_passed': applied.returncode == 0,
        'installed_archive_manifest_join_only': True, 'archive_bodies_reopened': False,
        'runtime_manifest': guards.observed(args.runtime_manifest), 'source_pins': guards.observed(args.source_pins),
        'target_source_executed': False, 'provider_or_test_or_prover_jobs_run': False,
        'original_repository_or_index_mutated': False, 'proof_authority': False,
        'execution_authority': False, 'completion_authority': False}
    exclusive(N / 'changes.patch', patch)
    exclusive(N / 'patch-qualification.json', canonical(qualification))
    exclusive(N / 'source-manifest.json', canonical(manifest))
    print(json.dumps({'source_manifest': guards.observed(N / 'source-manifest.json'),
        'patch': guards.observed(N / 'changes.patch'), 'qualification': guards.observed(N / 'patch-qualification.json')}))


if __name__ == '__main__':
    main()
