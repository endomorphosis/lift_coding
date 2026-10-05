"""Independent file-only joins of existing results; no native jobs or uploads."""
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import types

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = WORKSPACE / 'qualification/codebase_ir/ranker-trace-authentication-20261005-01'
PUBLISHER = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface/publish_successor_evidence_02.py'
PUBLISHER_SHA = '670e064a8222ce1b0c962e202985974741a9a4476630b0541c7ec880b32009f2'
EXPECTED = {
    'file-only-review-01.json': 'd1809dca6471ba8640f03805d6ed1ef557a7879887664de9ec712abac90c0e8f',
    'file-only-seal-01.json': '8ea31286ffda2a5f08b4820bcc6ccf9ee05f133b96018132378f8c96ec16f438',
}


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def main():
    raw = PUBLISHER.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == PUBLISHER_SHA, 'reviewed stable reader source changed')
    reader = types.ModuleType('frozen_publication_reader')
    reader.__file__ = str(PUBLISHER)
    exec(compile(raw, str(PUBLISHER), 'exec'), reader.__dict__)

    def load(path, expected=None):
        binding, data = reader.stable_read(Path(path), retain_plan_bytes=True)
        if expected is not None:
            need(binding == expected if isinstance(expected, dict) else binding['sha256'] == expected,
                 'exact document binding changed: ' + str(path))
        return json.loads(data), binding

    review, review_pin = load(ROOT / 'file-only-review-01.json', EXPECTED['file-only-review-01.json'])
    seal, seal_pin = load(ROOT / 'file-only-seal-01.json', EXPECTED['file-only-seal-01.json'])
    need(seal['review'] == review_pin and seal['file_count'] == len(seal['files']) == 203,
         'sealed qualification population differs')
    need(hashlib.sha256(wire(seal['files'])).hexdigest() == seal['file_inventory_sha256'],
         'sealed inventory digest differs')
    for row in seal['files']:
        need(reader.pin(Path(row['path'])) == row, 'sealed file changed')

    request, request_pin = load(review['request']['path'], review['request'])
    need(len(request['strict_old_inputs']) == 348, 'old population differs')
    for row in request['strict_old_inputs']:
        observed = reader.pin(Path(row['path']))
        need(observed['sha256'] == row['sha256'] and ('bytes' not in row or observed['bytes'] == row['bytes']),
             'old strict input changed')
    need(len(request['protected_live_sources']) == 4, 'protected source population differs')
    for row in request['protected_live_sources']:
        need(reader.pin(Path(row['path'])) == row, 'protected live source changed')

    auth, auth_pin = load(review['authentication']['path'], review['authentication'])
    need(hashlib.sha256(wire({k: v for k, v in auth.items() if k != 'authentication_sha256'})).hexdigest()
         == auth['authentication_sha256'] == review['authentication_sha256'], 'authentication self binding differs')
    need(len(auth['authenticated_states']) == 129 and [r['epoch'] for r in auth['authenticated_states']] == list(range(129)),
         'authenticated state population/order differs')
    need(hashlib.sha256(wire(auth['authenticated_states'])).hexdigest() == auth['authenticated_states_sha256'],
         'authenticated state digest differs')
    need(auth['checked_trace_rows'] == 129 and auth['optimizer_replay_updates'] == 128
         and auth['gradient_evaluations'] == 131 and auth['replay_gradient_evaluations'] == 129
         and auth['endpoint_validation_gradient_evaluations'] == 2 and auth['native_preparation_calls'] == 2,
         'bounded native operation counts differ')
    for flag in ('all_recorded_epoch_observations_match_native_replay', 'all_recorded_weight_digests_match_native_replay',
                 'final_checkpoint_matches_native_replay', 'finite_native_update_sequence_authenticated'):
        need(auth[flag] is True, 'finite authentication check failed')

    mapping, mapping_pin = load(review['finite_objective_mapping']['path'], review['finite_objective_mapping'])
    for key in ('authentication_sha256', 'authenticated_states_sha256', 'corpus_sha256', 'checkpoint_sha256',
                'training_receipt_sha256', 'ranker_result_sha256', 'recorded_trace_sha256', 'native_update_profile_sha256'):
        need(mapping[key] == auth[key], 'mapping-to-authentication join differs')
    original = WORKSPACE / 'artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01/evidence/actual-02/ranker-result.json'
    result, result_pin = load(original)
    need(result_pin['sha256'] == '6a6b7eaa20bf1a82a958ff6c9a6ab6f64c613fb880569a76b625de156284d60a'
         and hashlib.sha256(wire(result)).hexdigest() == auth['ranker_result_sha256'], 'original raw/canonical result binding differs')
    trace = result['training_receipt']['trace']
    need(hashlib.sha256(wire(trace)).hexdigest() == auth['recorded_trace_sha256'], 'original trace binding differs')
    denominator = int(mapping['common_denominator'])
    need(denominator == 2**56 and mapping['observations'] == 129 and mapping['strict_adjacent_declines'] == 128,
         'finite observation mapping profile differs')
    units = [int(value) for value in mapping['loss_units']]
    need(len(units) == len(trace) == 129 and all(a > b for a, b in zip(units, units[1:])),
         'observed order differs')
    need(all(Fraction.from_float(row['objective']) == Fraction(unit, denominator) for row, unit in zip(trace, units)),
         'exact observed binary64-to-integer mapping differs')

    checks, checks_pin = load(review['final_lean_checks']['path'], review['final_lean_checks'])
    need(len(checks) == 2 and checks[0]['status'] == 'passed' and checks[0]['returncode'] == 0
         and checks[1]['status'] == 'rejected' and checks[1]['returncode'] == 1
         and 'is false' in checks[1]['stdout'], 'qualified positive/false control outcomes differ')
    for check in checks:
        for flag in ('output_truncated', 'timed_out', 'resource_exhausted', 'workspace_limit_exceeded'):
            need(check[flag] is False, 'inconclusive final Lean check')
        need(check['backend_executed'] is True and check['matches_expectation'] is True
             and check['authentication_sha256'] == auth['authentication_sha256'], 'actual Lean/authentication join differs')
        need(reader.pin(Path(check['artifact']['path'])) == check['artifact'], 'Lean source changed')
        for artifact in check['compiled_artifacts']:
            need(reader.pin(Path(artifact['path'])) == artifact, 'Lean compiled artifact changed')
    need(checks[0]['compiled_artifacts'][0]['bytes'] == 58952, 'complete compiled payload differs')
    retained, retained_pin = load(review['retained_inconclusive_checker']['path'], review['retained_inconclusive_checker'])
    need(retained['status'] == 'inconclusive' and retained['output_truncated'] is True
         and retained['returncode'] == 0 and review['native_lean_invocations_total'] == 3,
         'prior inconclusive history missing')

    metadata, metadata_pin = load(review['native_metadata_readback']['path'], review['native_metadata_readback'])
    need(metadata['row_count'] == sum(metadata['family_counts'].values()) == 4348 and len(metadata['family_counts']) == 29,
         'metadata population differs')
    for family, count in {'ranker_trace_authentication': 1, 'ranker_trace_states': 129, 'ranker_trace_lean_checks': 2}.items():
        need(metadata['family_counts'][family] == count, 'new metadata family differs')
    restart = metadata['fresh_process_readback']
    need(restart['verified'] is True and restart['row_count'] == metadata['row_count'], 'fresh metadata restart not verified')
    for field in ('lake_snapshot_digest', 'manifest_sha256', 'row_root_sha256'):
        need(restart[field] == metadata[field], 'fresh restart receipt join differs')
    need(review['prior_payload_rows_preserved_exactly'] == 4216 and review['selected_unit_tests'] == 64
         and review['tests_skipped'] == 0 and review['all_phase_cleanup_errors'] == []
         and review['all_phase_scheduler_drains_zero_active_zero_waiting'] is True, 'closed qualification facts differ')
    need(review['all32_governing_RPI_exits'] == 'OPEN' and review['full_task_satisfaction'] == 'unknown'
         and review['official_benchmark_score'] is None and review['planning_handoff'] == 'abstained', 'scope elevated')
    for flag in ('whole_source_runtime_equivalence_proved', 'asymptotic_optimizer_convergence_proved',
                 'global_optimizer_convergence_proved', 'autoencoder_convergence_proved', 'exact_real_logistic_descent_proved',
                 'binary64_error_bound_proved', 'proof_authority', 'execution_authority', 'completion_authority'):
        need(review[flag] is False, 'unqualified authority or global claim')
    for row in seal['files']:
        need(reader.pin(Path(row['path'])) == row, 'sealed file changed during independent review')
    need(reader.pin(PUBLISHER)['sha256'] == PUBLISHER_SHA, 'frozen reader changed')
    output = Path(__file__).resolve().parent / 'independent-qualified-join-01.json'
    reader.save(output, {'schema': 'terminal-ranker-trace-independent-closed-file-join@1', 'status': 'passed',
                        'review': review_pin, 'seal': seal_pin, 'request': request_pin, 'authentication': auth_pin,
                        'mapping': mapping_pin, 'final_lean_checks': checks_pin, 'retained_inconclusive_check': retained_pin,
                        'metadata_readback': metadata_pin, 'original_result': result_pin,
                        'sealed_files_rehashed_twice': 203, 'strict_old_inputs_verified': 348, 'protected_live_sources_verified': 4,
                        'new_native_jobs': 0, 'external_mutations': 0, 'historical_execution_origin_authenticated': False,
                        'whole_source_runtime_equivalence_proved': False, 'asymptotic_optimizer_convergence_proved': False,
                        'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
                        'source': reader.pin(Path(__file__).resolve()), 'reader_source': reader.pin(PUBLISHER)})
    print(json.dumps(reader.pin(output), sort_keys=True))


if __name__ == '__main__':
    main()
