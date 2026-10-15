"""Independent file-only gate for the actual four-query prepared inputs."""
import datetime
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent
CORE = WORKSPACE / 'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-01'
EXPECTED = {
    'request': (CORE / 'preparation/request-v3.json', 628543, 'b1aba00577a79bb2e2818ddb426c3422d8247124b9fc274ae3a7620a4ff4e90d'),
    'specification': (CORE / 'preparation/lean-objective-container-core-01-check-specification.json', 18883, '36098ccd6c52833fef43f675aa990d3e9d2f96ff6d296169a0dfd6881f20cca7'),
    'profile': (CORE / 'preparation/lean-objective-container-core-01-producer/environment-manifest.json', 9976569, 'ccd64014d7b3c9df828d25b28a6d27fb0a68fd4adac60c660b9a294bdd6f3d79'),
    'driver': (CORE / 'run_container_core_controls_01.py', 25951, 'd4118c13d4a6a61575914d39f91b19df09e8b90bf09e414bcd8b5048ea6e79d6'),
}


def main():
    if not __debug__:
        raise ValueError('unoptimized prepared-input reviewer required')
    helper_path = CORE / 'container_core_file_helpers_01.py'
    with helper_path.open('rb') as stream:
        raw = stream.read(10419)
    if len(raw) != 10418 or hashlib.sha256(raw).hexdigest() != '3e10a1311636adbb14106437d499a9202a1a026950a43d766d955e6880083478':
        raise ValueError('independently source-reviewed stdlib reader differs')
    h = {'__file__': str(helper_path), '__name__': 'held_independent_prepared_input_file_readers'}
    exec(compile(raw, str(helper_path), 'exec'), h)
    need, exact, document = h['need'], h['exact'], h['document']
    h['core_source_gate']()
    pins = {role: {'path': str(path), 'bytes': size, 'sha256': digest} for role, (path, size, digest) in EXPECTED.items()}
    request, spec, profile = [document(pins[key]) for key in ('request', 'specification', 'profile')]
    exact(pins['driver'])
    tooling_pin = {'path': str(WORKSPACE / 'maintenance/ranker-objective-container-core-tooling-source-review-20261005-01/review-receipt.json'), 'bytes': 4990, 'sha256': '61710d25146c64c82fa2a4a00de806acc4d31c7be110f247e841ab676d080adb'}
    tooling = document(tooling_pin)
    need(tooling['status'] == 'passed_source_only' and tooling['findings'] == [] and tooling['tooling_source_pins']['run_container_core_controls_01.py'] == pins['driver'], 'exact independent tooling source review required')
    for pin in tooling['tooling_source_pins'].values():
        exact(pin)
    need(request['schema'] == 'terminal-ranker-objective-container-core-request@1' and request['exact_native_mode'] == h['MODE'] and request['exact_theorem_names'] == list(h['QUERIES']), 'exact request mode and query names differ')
    need(request['proof_limits'] == h['NATIVE_LIMITS'] and request['root_request'] == h['ROOT_LEASE'] and request['proof_pressure_limits'] == h['PRESSURE'] and request['outer_timeout_seconds'] == 120, 'native/admission/outer bounds changed')
    need(request['independent_core_source_review'] == spec['independent_core_source_review'] == h['SOURCE_GATE'] and request['candidate_compiled'] is False and request['candidate_native_qualified'] is False, 'uncompiled source gate differs')
    old = document(request['prior_objective_scalar_request'])
    seal = document(request['prior_objective_scalar_seal'])
    union = {row['path']: row for row in old['strict_old_inputs']}
    need(len(union) == 2108 and len(seal['files']) == 276, 'prior full guard populations differ')
    for row in [*seal['files'], request['prior_objective_scalar_seal']]:
        need(row['path'] not in union or union[row['path']] == row, 'guard overlap differs')
        union[row['path']] = row
    for directory, mapping in ((h['P7'], h['P7_PINS']), (CORE, h['CORE_PINS'])):
        for name, pair in mapping.items():
            pin = {'path': str(directory / name), 'bytes': pair[0], 'sha256': pair[1]}
            union[pin['path']] = pin
    need(len(union) == 2391 and request['strict_old_inputs'] == [union[path] for path in sorted(union)] and request['protected_live_sources'] == old['protected_live_sources'] and len(request['protected_live_sources']) == 4, 'exact strict/live guard union differs')
    for row in [*union.values(), *request['protected_live_sources']]:
        exact(row)
    need(spec['schema'] == 'ranker-objective-container-core-native-check-specification@1' and spec['mode'] == h['MODE'] and spec['expected_success'] is True and spec['theorem_names'] == list(h['QUERIES']) and spec['environment_manifest'] == pins['profile'] and spec['profile_parent'] == h['BASE_PROFILE'], 'exact prepared native specification differs')
    base = document(h['BASE_PROFILE'])
    old_files = {row['path']: row for row in base['files']}
    files = {row['path']: row for row in profile['files']}
    need(len(files) == len(profile['files']) == profile['external_file_count'] and sum(row['bytes'] for row in files.values()) == profile['external_file_bytes'], 'exact physical environment census differs')
    need(all(files.get(path) == row for path, row in old_files.items()), 'historical physical environment changed')
    for key in ('source_import_modules', 'local_checked_modules', 'lean_path', 'requested_imports'):
        need(profile[key] == base[key], 'historical module/loader field changed: ' + key)
    captures = profile['per_check_sources']
    need(len(captures) == 5 and profile['selected_proof_sources'] == [spec['source']] and captures[0]['captured'] == spec['source'], 'exact five new capture roles required')
    additions = {row['captured']['path']: row['captured'] for row in captures}
    need(set(files) - set(old_files) == set(additions) and all(files[path] == row for path, row in additions.items()), 'only declared new capture files may extend profile')
    for row in captures:
        exact(row['original']); exact(row['captured'])
        need((row['original']['bytes'], row['original']['sha256']) == (row['captured']['bytes'], row['captured']['sha256']), 'same-buffer capture body differs')
    need(spec['qualified_imports'] == [h['qualified_module'](name, base) for name in ('ObjectiveScalarIR', 'RealStableFactor', 'TypedNumericSlice')], 'genuine qualified import/chunk joins differ')
    for row in profile['files']:
        exact(row)
    module_names = set()
    for row in profile['source_import_modules']:
        need(row['module'] not in module_names, 'duplicate module registry')
        module_names.add(row['module'])
        relative = Path(*row['module'].split('.')).with_suffix('.olean')
        candidates = [Path(library) / relative for library in profile['lean_path'] if (Path(library) / relative).is_file()]
        need(candidates and any(pin['path'] == str(candidates[0]) for pin in row['compiled']), 'import shadowed outside qualified object registry')
    need({'Init', 'ObjectiveScalarIR', 'TypedNumericSlice', 'RealStableFactor'} <= module_names and 'ObjectiveContainerCore' not in module_names, 'direct import registry/candidate freshness differs')
    need(profile['native_per_file_capture_bytes_unchanged'] == 65536 and profile['root_reconstructed_external_module_aggregate_max_bytes'] == 3997696, 'retention bounds changed')
    h['verify_held']()
    receipt = {'schema': 'ranker-objective-container-core-independent-prepared-input-review@1', 'status': 'passed_file_only', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': h['pin'](Path(__file__).resolve()), 'prepared_input_pins': pins, 'tooling_source_review': tooling_pin, 'core_source_review': h['SOURCE_GATE'], 'findings': [], 'physical_environment_files_verified_before_after': len(files), 'physical_environment_bytes_verified_before_after': profile['external_file_bytes'], 'historical_closure_files_preserved': len(old_files), 'only_five_new_captures': True, 'strict_guards_verified_before_after': 2391, 'live_guards_verified_before_after': 4, 'import_objects_and_ordered_chunks_verified': True, 'native_queries': 0, 'native_or_model_or_test_or_metadata_jobs': 0, 'project_imports': 0, 'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None, **h['AUTHORITY']}
    descriptor = h['write'](ROOT / 'review-receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'receipt': descriptor, 'physical_files': len(files), 'native_jobs': 0}))


if __name__ == '__main__':
    main()
