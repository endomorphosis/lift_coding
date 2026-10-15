"""Package independently frozen O base files plus the exact additive scope.

Read exact captured originals, parse syntax without imports, apply the patch in
a fresh scratch Git checkout and compare bytes. No target execution, original
index mutation, prior-stage writes, provider calls or archive-body reads.
"""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
import subprocess

O = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('stage_o_named_public_guards', O / 'check-preservation.py')
guards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guards)
C = guards.C
PIN_SCHEMA = 'terminal-nomination-identity-final-source-pins@1'
MAX_SOURCE = 4_000_000
MAX_PATCH = 8_000_000


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def exclusive(path, raw):
    path = guards.public_path(path)
    guards.require(path.is_relative_to(O) and not path.exists() and not path.is_symlink(), 'New O artifact only')
    with path.open('xb') as stream: stream.write(raw)


def git(scratch, argv):
    return subprocess.run(['/usr/bin/git', *argv], cwd=scratch, capture_output=True, check=True, timeout=30,
        env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-pins', type=Path, required=True)
    parser.add_argument('--source-pins-sha256', required=True)
    parser.add_argument('--runtime-manifest', type=Path, required=True)
    parser.add_argument('--runtime-manifest-sha256', required=True)
    parser.add_argument('--artifact-generation', choices=('02', '03', '04'))
    parser.add_argument('--additional-baseline', type=Path)
    parser.add_argument('--additional-baseline-sha256')
    parser.add_argument('--supplemental-test-baseline', type=Path)
    parser.add_argument('--supplemental-test-baseline-sha256')
    args = parser.parse_args()
    guards.require(args.source_pins.is_relative_to(O) and args.runtime_manifest.is_relative_to(O),
        'Only root-named O public input documents')
    scope = guards.source_scope(args.additional_baseline, args.additional_baseline_sha256, args.artifact_generation,
        args.supplemental_test_baseline, args.supplemental_test_baseline_sha256)
    before, existing, new = scope['before'], scope['existing'], scope['new']
    names, production, tests = existing | new, scope['production'], scope['tests']
    guards.prior_stage_pins()
    frozen = guards.document(args.source_pins, args.source_pins_sha256)
    guards.require(set(frozen) == {'schema', 'checkout', 'files'} and frozen['schema'] == PIN_SCHEMA
        and frozen['checkout'] == str(C), 'Closed independent four-source freeze required')
    expected = guards.by_path(guards.rows(frozen['files'], len(names)))
    guards.require(set(expected) == names, 'Exact independently declared existing/new source scope only')
    archive = guards.document(args.runtime_manifest, args.runtime_manifest_sha256)
    guards.require(type(archive.get('files')) is list and 1 <= len(archive['files']) <= 20000,
        'Bounded root-pinned archive inventory required')
    members = guards.by_path(archive['files'])
    guards.require(all('source/' + name not in members for name in tests), 'All declared host tests stay outside archive')
    suffix = '-' + args.artifact_generation if args.artifact_generation else ''
    patch_name = 'changes' + suffix + '.patch'
    manifest_name = 'source-manifest' + suffix + '.json'
    qualification_name = 'patch-qualification' + suffix + '.json'
    scratch = O / ('scratch-' + args.artifact_generation if args.artifact_generation else 'patch-qualification-01')
    guards.require(not scratch.exists() and not scratch.is_symlink(), 'Fresh isolated scratch namespace required')
    for name in (patch_name, manifest_name, qualification_name):
        guards.require(not (O / name).exists() and not (O / name).is_symlink(), 'No existing artifact replacement')
    current, originals, source_pins, patches = {}, {}, {}, []
    for name in sorted(names):
        got, body = guards.capture(C / name, maximum=MAX_SOURCE, retain=True)
        guards.require(got['sha256'] == expected[name]['sha256'] and got['bytes'] == expected[name]['bytes'],
            'Current source differs from independent final freeze')
        ast.parse(body.decode('utf-8'), filename=name)
        if name in existing:
            row = before[name]
            old, original = guards.capture(Path(row['baseline']), maximum=MAX_SOURCE, retain=True)
            guards.require(old['sha256'] == row['sha256'] and old['bytes'] == row['bytes'], 'Original captured source differs')
            originals[name] = original
            old_header = 'a/' + name
        else:
            original, old_header = b'', '/dev/null'
        current[name], source_pins[name] = body, got
        patches.extend(difflib.unified_diff(original.decode().splitlines(keepends=True), body.decode().splitlines(keepends=True),
            fromfile=old_header, tofile='b/' + name))
        if name in production:
            member = members.get('source/' + name)
            guards.require(member is not None and member['sha256'] == got['sha256'] and member['bytes'] == got['bytes'],
                'Both production files must join independently pinned installed-runtime manifest')
    patch = ''.join(patches).encode()
    guards.require(0 < len(patch) <= MAX_PATCH, 'Nonempty bounded four-source patch required')
    scratch.mkdir(mode=0o700); tree = scratch / 'checkout'; tree.mkdir(mode=0o700)
    for name, body in originals.items():
        path = tree / name; path.parent.mkdir(parents=True, exist_ok=True); exclusive(path, body)
    patch_copy = scratch / 'changes.patch'; exclusive(patch_copy, patch)
    git(tree, ['init', '--quiet']); checked = git(tree, ['apply', '--check', str(patch_copy)])
    applied = git(tree, ['apply', str(patch_copy)])
    applied_rows = []
    for name, body in current.items():
        observed, copied = guards.capture(tree / name, maximum=MAX_SOURCE, retain=True)
        guards.require(copied == body, 'Applied scratch bytes differ from frozen checkout source')
        applied_rows.append({'path': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'bytes_exact': True})
    for name, body in current.items():
        observed, reread = guards.capture(C / name, maximum=MAX_SOURCE, retain=True)
        guards.require(observed == source_pins[name] and reread == body, 'Source changed after syntax/diff/Git callbacks')
    files = [{'path': name, 'absolute_path': str(C / name), 'bytes': source_pins[name]['bytes'],
        'sha256': source_pins[name]['sha256'], 'absent_before': name in new,
        'before_sha256': before[name]['sha256'] if name in existing else None,
        'before_bytes': before[name]['bytes'] if name in existing else None,
        'baseline': before[name]['baseline'] if name in existing else None,
        'runtime_archive_member': name in production} for name in sorted(names)]
    manifest = {'schema': 'terminal-nomination-identity-source-manifest@1', 'checkout': str(C), 'files': files,
        'existing_deltas': len(existing), 'new_files': len(new), 'runtime_source_files': len(production), 'host_test_files': len(tests),
        'patch_bytes': len(patch), 'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'runtime_manifest_sha256': args.runtime_manifest_sha256,
        'independent_final_source_pins': guards.observed(args.source_pins),
        'original_beginning_pins_sha256': guards.BEGINNING_SHA, 'prior_stage_pins_sha256': guards.PRIOR_PINS_SHA,
        'patch_applies_cleanly_to_captured_baselines': True, 'applied_changed_bytes_match_checkout': True,
        'all_production_source_hashes_match_runtime_manifest': True, 'host_test_sources_excluded_from_runtime': True,
        'original_dirty_checkout_or_git_index_mutated': False, 'prior_n_mutation': False,
        'source_semantics_or_equivalence_proved': False, 'model_convergence_proved': False}
    if scope['additional'] is not None:
        manifest['additional_baseline'] = scope['additional']
    if scope['supplemental'] is not None:
        manifest['supplemental_test_baseline'] = scope['supplemental']
    qualification = {'schema': 'terminal-nomination-identity-patch-qualification@1', 'qualified': True,
        'scratch': str(scratch), 'applied_sources': applied_rows, 'syntax_parsed_only': True,
        'git_apply_check_passed': checked.returncode == 0, 'git_apply_passed': applied.returncode == 0,
        'installed_archive_manifest_join_only': True, 'archive_bodies_reopened': False,
        'runtime_manifest': guards.observed(args.runtime_manifest), 'source_pins': guards.observed(args.source_pins),
        'target_source_executed': False, 'provider_or_test_or_prover_jobs_run': False,
        'original_repository_or_index_mutated': False, 'prior_n_mutation': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False}
    exclusive(O / patch_name, patch); exclusive(O / qualification_name, canonical(qualification))
    exclusive(O / manifest_name, canonical(manifest))
    print(json.dumps({'source_manifest': guards.observed(O / manifest_name),
        'patch': guards.observed(O / patch_name), 'qualification': guards.observed(O / qualification_name)}))


if __name__ == '__main__':
    main()
