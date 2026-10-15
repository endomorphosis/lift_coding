"""Unexecuted file-only freezer for the one four-query container native batch.

Preserves the previous declared dependency closure. It copies new reviewed
source/tooling inputs only, validates actual qualified import objects/chunks,
and creates a new manifest/specification without imports or prover execution.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
COMMON = (17601, '815bec62dd2c8de4073b389dbdf62827c4a639d4f6a3e08e5e79ef83ccffff3a')
CHECKER = {'path': str(ROOT.with_name('ranker-real-curvature-20261005-01') / 'preparation/lean-original-descent-01-producer/bounded_analytic_checker.py'),
           'bytes': 29086, 'sha256': '04015267ed110533a7406c0b39c38b88a974a1d80259fd5755a99ef908a8a8b4'}
RETENTION = {'path': str(ROOT.with_name('ranker-real-curvature-20261005-01') / 'preparation/lean-original-descent-01-producer/RetainLeanProof.py'),
             'bytes': 5828, 'sha256': 'ccdf7df547844ac5d39cc077c8a14194fd06f7bb51838d80ffa9d7f349999e66'}


def helpers():
    path = ROOT / 'container_core_file_helpers_01.py'
    if path.resolve(strict=True) != path or path.is_symlink():
        raise ValueError('canonical reviewed helper source required')
    with path.open('rb') as stream:
        raw = stream.read(COMMON[0] + 1)
    if len(raw) != COMMON[0] or hashlib.sha256(raw).hexdigest() != COMMON[1]:
        raise ValueError('reviewed file-only helper source differs')
    namespace = {'__file__': str(path), '__name__': 'held_container_profile_file_helpers'}
    exec(compile(raw, str(path), 'exec'), namespace)
    namespace['exact']({'path': str(path), 'bytes': COMMON[0], 'sha256': COMMON[1]})
    return namespace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=['lean-objective-container-core-02'])
    parser.add_argument('--expected-producer-sha256', required=True)
    args = parser.parse_args()
    if not __debug__ or re.fullmatch('[0-9a-f]{64}', args.expected_producer_sha256) is None:
        raise ValueError('unoptimized reviewed freezer source pin required')
    h = helpers()
    need, pin = h['need'], h['pin']
    own = pin(Path(__file__).resolve())
    need(own['sha256'] == args.expected_producer_sha256, 'reviewed profile producer differs')
    h['core_source_gate']()
    request = h['document'](pin(ROOT / 'preparation/request-v3.json'))
    need(request['exact_native_mode'] == h['MODE'] and request['exact_theorem_names'] == list(h['QUERIES'])
         and request['independent_core_source_review'] == h['SOURCE_GATE'], 'fresh v2 request source gate required')
    h['validate_guard_union'](request)
    source_raw, source_pin = h['fixed'](ROOT / 'math/ObjectiveContainerCore.lean', h['CORE_PINS']['math/ObjectiveContainerCore.lean'], True)
    need(re.findall(rb'^import ([A-Za-z0-9_.]+)\s*$', source_raw, re.M) == [b'ObjectiveScalarIR'], 'one exact direct import required')
    base = h['document'](h['BASE_PROFILE'])
    need(base['native_per_file_capture_bytes_unchanged'] == 65536
         and base['root_reconstructed_external_module_aggregate_max_bytes'] == 3997696,
         'unchanged native retention bounds required')
    old_files = {row['path']: row for row in base['files']}
    need(len(old_files) == len(base['files']) == base['external_file_count'] == 20114
         and sum(row['bytes'] for row in old_files.values()) == base['external_file_bytes'], 'unique complete previous closure required')
    imports = [h['qualified_module'](name, base) for name in ('ObjectiveScalarIR', 'RealStableFactor', 'TypedNumericSlice')]
    executable = pin(Path(sys.executable).resolve(strict=True))
    need(executable['bytes'] == 7845032 and executable['sha256'] == '1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f',
         'exact existing Python executable required')
    for row in (CHECKER, RETENTION):
        h['exact'](row)
    preparation = ROOT / 'preparation'
    need(preparation.is_dir(), 'prepare guarded request first')
    destination = preparation / (args.mode + '-producer')
    need(not destination.exists(), 'fresh numbered native producer directory required')
    destination.mkdir()
    files = dict(old_files)
    sources = []
    for original in (source_pin, CHECKER, RETENTION, own,
                     {'path': str(ROOT / 'container_core_file_helpers_01.py'), 'bytes': COMMON[0], 'sha256': COMMON[1]}):
        raw = h['exact'](original, True)
        captured = destination / Path(original['path']).name
        with captured.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            import os
            os.fsync(stream.fileno())
        captured.chmod(0o444)
        held = pin(captured)
        need((held['bytes'], held['sha256']) == (original['bytes'], original['sha256']), 'held copy differs')
        sources.append({'original': original, 'captured': held})
        need(held['path'] not in files, 'new capture aliases previous dependency')
        files[held['path']] = held
    need(executable['path'] not in files or files[executable['path']] == executable, 'existing executable descriptor differs')
    files[executable['path']] = executable
    need(len(files) == 20119, 'complete previous 20114 entries plus exactly five new captures required')
    profile = dict(base)
    profile.update(selected_proof_sources=[sources[0]['captured']], profile_parent=h['BASE_PROFILE'],
                   per_check_sources=sources, files=[files[path] for path in sorted(files)],
                   external_file_count=len(files), external_file_bytes=sum(row['bytes'] for row in files.values()))
    need(all(files[path] == row for path, row in old_files.items()), 'old environment closure may not change')
    need(profile['source_import_modules'] == base['source_import_modules'] and profile['local_checked_modules'] == base['local_checked_modules']
         and profile['lean_path'] == base['lean_path'] and profile['requested_imports'] == base['requested_imports'], 'all previous import/loader registry fields must remain exact')
    h['verify_held']()
    profile_pin = h['write'](destination / 'environment-manifest.json', profile)
    Path(profile_pin['path']).chmod(0o444)
    specification = {
        'schema': 'ranker-objective-container-core-native-check-specification@1', 'mode': h['MODE'],
        'source': sources[0]['captured'], 'environment_manifest': profile_pin,
        'expected_success': True, 'theorem_names': list(h['QUERIES']),
        'freeze_producer': sources[3]['captured'], 'checker_wrapper': sources[1]['captured'],
        'retention_helper': sources[2]['captured'], 'file_helpers': sources[4]['captured'],
        'python_executable': executable, 'independent_core_source_review': h['SOURCE_GATE'],
        'qualified_imports': imports, 'profile_parent': h['BASE_PROFILE'],
        'source_capture_scope': 'individual held-byte copies; no whole-live atomic or loader-open claim',
    }
    spec_pin = h['write'](preparation / (args.mode + '-check-specification.json'), specification)
    Path(spec_pin['path']).chmod(0o444)
    h['verify_held']()
    print(json.dumps({'status': 'prepared_file_only_native_execution_pending', 'specification': spec_pin,
                     'source': sources[0]['captured'], 'profile': profile_pin, 'wrapper': sources[1]['captured'],
                     'native_jobs': 0, 'target_imports': 0, 'new_dependency_files': 0}))


if __name__ == '__main__':
    main()
