"""Package the exact independently frozen six P source files, without imports.

Only Python syntax and clean patch application in new P scratch are checked.
Runtime provenance joins a root-pinned manifest; no archive payload is read.
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

P = Path('/home/barberb/lift_coding/maintenance/terminal-observer-stop-20261012-01')
spec = importlib.util.spec_from_file_location('p_public_preservation', P / 'check-preservation.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
g, C = m.g, m.C
MAX_PATCH = 2_000_000


def git(directory, arguments):
    environment = {name: value for name, value in os.environ.items() if not name.startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_OPTIONAL_LOCKS='0')
    result = subprocess.run(['/usr/bin/git', *arguments], cwd=directory, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    g.require(result.returncode == 0 and len(result.stdout) + len(result.stderr) <= 65536,
        'Bounded scratch Git operation failed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--source-pins', required=True, type=Path)
    parser.add_argument('--source-pins-sha256', required=True)
    parser.add_argument('--runtime-manifest', required=True, type=Path)
    parser.add_argument('--runtime-manifest-sha256', required=True)
    parser.add_argument('--artifact-generation', choices=('02', '03', '04'))
    args = parser.parse_args(); tag = m.suffix(args.artifact_generation)
    source_path, runtime_path = m.named_p(args.source_pins), m.named_p(args.runtime_manifest)
    before = m.baseline()
    final = g.document(source_path, g.digest(args.source_pins_sha256))
    expected = m.final_sources(final, before)
    archive = g.document(runtime_path, g.digest(args.runtime_manifest_sha256))
    g.require(type(archive['files']) is list and 1 <= len(archive['files']) <= 20000,
        'Bounded independently pinned runtime member inventory required')
    members = g.by_path(archive['files'])
    g.require(all('source/' + name not in members for name in m.TESTS), 'All three host tests excluded from runtime')
    names = {'changes': 'changes' + tag + '.patch', 'manifest': 'source-manifest' + tag + '.json',
        'qualification': 'patch-qualification' + tag + '.json'}
    scratch = P / ('patch-scratch' + tag)
    g.require(not scratch.exists() and not scratch.is_symlink(), 'Fresh scratch namespace only')
    for name in names.values():
        g.require(not (P / name).exists() and not (P / name).is_symlink(), 'New artifacts only; no replacement')
    current, original, current_pins, parts = {}, {}, {}, []
    for name in sorted(m.EXISTING | m.NEW):
        pin, body = g.capture(C / name, maximum=m.MAX_SOURCE, retain=True)
        g.require(pin['sha256'] == expected[name]['sha256'] and pin['bytes'] == expected[name]['bytes'],
            'Current source differs from independent final freeze')
        ast.parse(body.decode('utf-8'), filename=name)
        if name in m.EXISTING:
            row = before[name]; old_pin, old = g.capture(Path(row['baseline_path']), maximum=m.MAX_SOURCE, retain=True)
            g.require(old_pin['sha256'] == row['sha256'] and old_pin['bytes'] == row['bytes'], 'Original capture differs')
            original[name] = old; header = 'a/' + name
        else:
            old = b''; header = '/dev/null'
        current[name], current_pins[name] = body, pin
        parts.extend(difflib.unified_diff(old.decode('utf-8').splitlines(keepends=True), body.decode('utf-8').splitlines(keepends=True),
            fromfile=header, tofile='b/' + name))
        if name in m.PRODUCTION:
            member = members.get('source/' + name)
            g.require(member is not None and member['sha256'] == pin['sha256'] and member['bytes'] == pin['bytes'],
                'Every runtime head must match independently pinned archive metadata')
    patch = ''.join(parts).encode('utf-8')
    g.require(1 <= len(patch) <= MAX_PATCH, 'Nonempty bounded declared-source patch required')
    scratch.mkdir(mode=0o700); tree = scratch / 'checkout'; tree.mkdir(mode=0o700)
    for name, body in original.items():
        path = tree / name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(body)
    patch_copy = scratch / 'changes.patch'
    with patch_copy.open('xb') as stream: stream.write(patch)
    git(tree, ['init', '--quiet']); checked = git(tree, ['apply', '--check', str(patch_copy)])
    applied = git(tree, ['apply', str(patch_copy)])
    applied_rows = []
    for name, body in current.items():
        pin, copied = g.capture(tree / name, maximum=m.MAX_SOURCE, retain=True)
        g.require(copied == body, 'Applied scratch source differs from frozen current bytes')
        applied_rows.append({'path': name, 'sha256': pin['sha256'], 'bytes': pin['bytes'], 'bytes_exact': True})
        fresh, actual = g.capture(C / name, maximum=m.MAX_SOURCE, retain=True)
        g.require(fresh == current_pins[name] and actual == body, 'Current source changed after syntax/Git callbacks')
    m.final_witnesses()
    files = []
    for name in sorted(current):
        old = before.get(name)
        files.append({'path': name, 'absolute_path': str(C / name), 'bytes': current_pins[name]['bytes'],
            'sha256': current_pins[name]['sha256'], 'absent_before': name in m.NEW,
            'before_sha256': old['sha256'] if old else None, 'before_bytes': old['bytes'] if old else None,
            'baseline': old['baseline_path'] if old else None, 'runtime_archive_member': name in m.PRODUCTION})
    manifest = {'schema': m.MANIFEST_SCHEMA, 'checkout': str(C), 'files': files, 'baseline_sha256': m.BASELINE_SHA,
        'existing_deltas': 4, 'new_files': 2, 'runtime_source_files': 3, 'host_test_files': 3,
        'original_baseline_sha256': m.ORIGINAL_BASELINE_SHA,
        'patch_bytes': len(patch), 'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'runtime_manifest': g.observed(runtime_path), 'independent_final_source_pins': g.observed(source_path),
        'patch_applies_cleanly_to_original_captures': True, 'applied_changed_bytes_match_checkout': True,
        'all_production_source_hashes_match_runtime_manifest': True, 'host_tests_excluded_from_runtime': True,
        'original_repository_or_index_mutated': False, 'prior_o_or_n_mutation': False,
        'source_semantics_or_equivalence_proved': False, 'model_convergence_proved': False}
    qualification = {'schema': 'terminal-observer-stop-patch-qualification@1', 'qualified': True,
        'scratch': str(scratch), 'applied_sources': applied_rows, 'syntax_parsed_only': True,
        'git_apply_check_passed': checked.returncode == 0, 'git_apply_passed': applied.returncode == 0,
        'runtime_manifest': g.observed(runtime_path), 'source_pins': g.observed(source_path),
        'archive_bodies_read': False, 'target_source_executed': False, 'providers_or_tests_or_provers_run': False,
        'original_repository_or_index_mutated': False, 'prior_o_or_n_mutation': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False}
    m.exclusive(P / names['changes'], patch)
    m.exclusive(P / names['qualification'], m.canonical(qualification))
    m.exclusive(P / names['manifest'], m.canonical(manifest))
    print(json.dumps({'source_manifest': g.observed(P / names['manifest']),
        'patch': g.observed(P / names['changes']), 'qualification': g.observed(P / names['qualification'])}))


if __name__ == '__main__': main()
