"""Independent file-only gate for the actual four-query prepared inputs."""
import datetime
import argparse
import re
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent
CORE = WORKSPACE / 'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02'



def main():
    if not __debug__:
        raise ValueError('unoptimized prepared-input reviewer required')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--expected-source-sha256', required=True)
    args = parser.parse_args()
    if any(re.fullmatch('[0-9a-f]{64}', x) is None for x in (args.plan_sha256, args.expected_source_sha256)):
        raise ValueError('exact external source and plan pins required')
    helper_path = CORE / 'container_core_file_helpers_01.py'
    with helper_path.open('rb') as stream:
        raw = stream.read(17602)
    if len(raw) != 17601 or hashlib.sha256(raw).hexdigest() != '815bec62dd2c8de4073b389dbdf62827c4a639d4f6a3e08e5e79ef83ccffff3a':
        raise ValueError('independently source-reviewed stdlib reader differs')
    h = {'__file__': str(helper_path), '__name__': 'held_independent_prepared_input_file_readers'}
    exec(compile(raw, str(helper_path), 'exec'), h)
    need, exact, document = h['need'], h['exact'], h['document']
    h['core_source_gate']()
    own = h['pin'](Path(__file__).resolve())
    need(own['sha256'] == args.expected_source_sha256, 'reviewer source differs')
    plan_pin = h['pin'](args.plan)
    need(plan_pin['sha256'] == args.plan_sha256, 'prepared input review plan differs')
    plan = document(plan_pin)
    need(set(plan) == {'schema', 'prepared_input_pins'} and plan['schema'] == 'ranker-objective-container-core-prepared-input-review-plan@2', 'closed prepared review plan required')
    pins = plan['prepared_input_pins']
    need(set(pins) == {'request', 'specification', 'profile', 'driver'}, 'exact prepared input roles required')
    for role, suffix in {'request':'preparation/request-v3.json', 'specification':'preparation/lean-objective-container-core-02-check-specification.json', 'profile':'preparation/lean-objective-container-core-02-producer/environment-manifest.json', 'driver':'run_container_core_controls_01.py'}.items():
        need(pins[role]['path'] == str(CORE / suffix), 'exact input path differs: ' + role)
    request, spec, profile = [document(pins[key]) for key in ('request', 'specification', 'profile')]
    exact(pins['driver'])
    tooling_pin = {'path': str(WORKSPACE / 'maintenance/ranker-objective-container-core-tooling-source-review-20261005-02/review-receipt.json'), 'bytes': 9173, 'sha256': 'bb1f7df2dd76f37349480094cdf3181d93e53b5886a263bca4fc3bc3b0f57b4e'}
    tooling = document(tooling_pin)
    need(tooling['status'] == 'passed_source_only' and tooling['findings'] == [] and tooling['tooling_source_pins']['run_container_core_controls_01.py'] == pins['driver'], 'exact independent tooling source review required')
    for pin in tooling['tooling_source_pins'].values():
        exact(pin)
    need(request['schema'] == 'terminal-ranker-objective-container-core-request@1' and request['exact_native_mode'] == h['MODE'] and request['exact_theorem_names'] == list(h['QUERIES']), 'exact request mode and query names differ')
    need(request['proof_limits'] == h['NATIVE_LIMITS'] and request['root_request'] == h['ROOT_LEASE'] and request['proof_pressure_limits'] == h['PRESSURE'] and request['outer_timeout_seconds'] == 120, 'native/admission/outer bounds changed')
    need(request['independent_core_source_review'] == spec['independent_core_source_review'] == h['SOURCE_GATE'] and request['candidate_compiled'] is False and request['candidate_native_qualified'] is False, 'uncompiled source gate differs')
    h['validate_guard_union'](request)
    inherited, failed_seal, failed_review = h['failed_v1_inputs'](request['prior_failed_container_seal'])
    union = {row['path']: row for row in inherited['strict_old_inputs']}
    need(len(union) == 2391, 'exact previous strict guard denominator required')
    for row in [*failed_seal['files'], request['prior_failed_container_seal']]:
        need(row['path'] not in union or union[row['path']] == row, 'historical guard overlap differs')
        union[row['path']] = row
    for name, pair in h['CORE_PINS'].items():
        row = {'path': str(CORE / name), 'bytes': pair[0], 'sha256': pair[1]}
        need(row['path'] not in union or union[row['path']] == row, 'new candidate overlap differs')
        union[row['path']] = row
    need(len(union) == 2421 and request['strict_old_inputs'] == [union[path] for path in sorted(union)]
         and request['protected_live_sources'] == inherited['protected_live_sources']
         and len({row['path'] for row in request['protected_live_sources']}) == 4,
         'independently reconstructed complete strict/live guard cohorts differ')
    need(all(row['path'] not in union or row == union[row['path']] for row in request['protected_live_sources']), 'shared strict/live descriptor differs')
    for row in [*union.values(), *request['protected_live_sources']]:
        exact(row)
    need(all(request[key] is False for key in h['AUTHORITY']), 'prepared request grants authority')
    need(spec['schema'] == 'ranker-objective-container-core-native-check-specification@1' and spec['mode'] == h['MODE'] and spec['expected_success'] is True and spec['theorem_names'] == list(h['QUERIES']) and spec['environment_manifest'] == pins['profile'] and spec['profile_parent'] == h['BASE_PROFILE'], 'exact prepared native specification differs')
    base = document(h['BASE_PROFILE'])
    old_files = {row['path']: row for row in base['files']}
    files = {row['path']: row for row in profile['files']}
    need(len(old_files) == 20114 and len(files) == len(profile['files']) == profile['external_file_count'] == 20119 and sum(row['bytes'] for row in files.values()) == profile['external_file_bytes'], 'exact physical environment census differs')
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
    receipt = {'schema': 'ranker-objective-container-core-independent-prepared-input-review@2', 'status': 'passed_file_only', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': own, 'review_plan': plan_pin, 'prior_failed_v1_seal': request['prior_failed_container_seal'], 'prior_failed_v1_qualified_queries': 0, 'prepared_input_pins': pins, 'tooling_source_review': tooling_pin, 'core_source_review': h['SOURCE_GATE'], 'findings': [], 'physical_environment_files_verified_before_after': len(files), 'physical_environment_bytes_verified_before_after': profile['external_file_bytes'], 'historical_closure_files_preserved': len(old_files), 'only_five_new_captures': True, 'strict_guards_verified_before_after': 2421, 'live_guards_verified_before_after': 4, 'import_objects_and_ordered_chunks_verified': True, 'native_queries': 0, 'native_or_model_or_test_or_metadata_jobs': 0, 'project_imports': 0, 'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None, **h['AUTHORITY']}
    descriptor = h['write'](ROOT / 'review-receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'receipt': descriptor, 'physical_files': len(files), 'native_jobs': 0}))


if __name__ == '__main__':
    main()
