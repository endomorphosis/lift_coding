"""Bounded ordinary host materialization of the complete original prefix.

The ranker remains data. Only exact tested emitter/decoder/compiler definitions
and reviewed standard-library file helpers execute. Genuine closed native
imports are joined as immutable evidence, never rerun in this host phase.
"""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess

W = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
READER = W / 'qualification/codebase_ir/ranker-objective-prefix-projections-candidate-20261006-02/prefix_file_helpers_01.py'
READER_PIN = (22214, '40ed16e8f7bb3d7c7db1a7b6c2de9660d50db073c9ce318614d61e3be84451e0')
CONTROL_PLAN = {'path': str(W / 'maintenance/ranker-objective-container-emitter-controls-20261006-01/control-plan-02.json'),
    'bytes': 3938, 'sha256': '15167672f23666f121bc64335991cf80ad0f1dfc53b4b6c4427abfa5be2cc9fb'}
CONTROL_RESULT = {'path': str(W / 'maintenance/ranker-objective-container-emitter-controls-20261006-01/run-01/closed.json'),
    'bytes': 3904, 'sha256': '8d57cc87ffb9105481022a97b5d52f71432bc48067a571131e1d49b45f0681e9'}
EMITTER_PIN = (14989, 'f6a97381502153a336c076093a59504945b8797283ddaa2830826c6d04000a32')
OUTPUT = W / 'qualification/codebase_ir/ranker-objective-container-prefix-host-result-20261006-01'
AUTHORITY = {k: False for k in ('proof_authority', 'execution_authority', 'planner_activation', 'completion_authority')}
MODULE_ORDER = ('ObjectiveContainerSource', 'ObjectiveContainerTyped', 'ObjectiveContainerSemantics',
                'ObjectiveContainerCompiler', 'ObjectiveContainerPreservation')
BUFFER_ROLES = ('draft', 'original_source', 'bindings', 'materialization_receipt',
                'qualified_host_compiler', 'qualified_host_decoder')
EXPECTED_COUNTS = {'letBind': 5, 'var': 31, 'scalarLiteral': 7, 'scalarOp': 26, 'mapRows': 1,
    'mapVector': 2, 'zipMap': 2, 'zipRowsMap': 1, 'rangeMap': 1, 'indexVector': 2,
    'length': 2, 'natToScalar': 2, 'fsumExact': 4, 'prefixRecord': 1}
PREFIX_NAMES = ('margins', 'data', 'regularizer', 'factors', 'gradient')


def need(value, message):
    if value is not True:
        raise ValueError(message)


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def save_bytes(h, path, raw):
    need(type(raw) is bytes and len(raw) <= 262144, 'bounded generated source required')
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return h['pin'](path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    need(__debug__ and all(re.fullmatch('[0-9a-f]{64}', value) is not None
        for value in (args.plan_sha256, args.source_sha256)), 'external exact source/plan hashes required')
    limits()
    need(READER.resolve(strict=True) == READER and not READER.is_symlink(), 'canonical immutable reader required')
    raw = READER.read_bytes()
    need((len(raw), hashlib.sha256(raw).hexdigest()) == READER_PIN, 'immutable stdlib reader differs')
    h = {'__file__': str(READER), '__name__': 'held_whole_prefix_materialization_file_readers'}
    exec(compile(raw, str(READER), 'exec'), h)
    h['exact']({'path': str(READER), 'bytes': READER_PIN[0], 'sha256': READER_PIN[1]})
    own = h['pin'](Path(__file__).resolve())
    need(own['sha256'] == args.source_sha256, 'reviewed materializer differs')
    pp = h['pin'](args.plan)
    need(pp['sha256'] == args.plan_sha256, 'materialization plan differs')
    plan = h['document'](pp)
    need(set(plan) == {'schema', 'producer_review', 'proof_suffix', 'host_control_plan', 'host_control_receipt',
        'emitter_source_review', 'language_helper', 'language_tooling_source_review', 'language_source_review',
        'language_guard_request', 'base_environment_manifest', 'staged_imports', 'output_root'}
        and plan['schema'] == 'ranker-objective-container-prefix-materialization-plan@1', 'closed materialization plan required')
    gate = h['document'](plan['producer_review'])
    need(gate['status'] == 'passed_source_only' and gate['findings'] == [] and gate['reviewed_source'] == own
        and gate['reviewed_proof_suffix'] == plan['proof_suffix'] and all(gate[k] is False for k in AUTHORITY),
        'exact producer and generated suffix source gate required')
    need(plan['proof_suffix']['path'] == str(ROOT / 'proof-suffix-01.lean.txt'), 'fixed local suffix role required')
    suffix = h['exact'](plan['proof_suffix'], True)
    need(type(suffix) is bytes and len(suffix) <= 16384, 'bounded reviewed proof suffix required')
    need(plan['host_control_plan'] == CONTROL_PLAN and plan['host_control_receipt'] == CONTROL_RESULT,
        'fixed actual20 emitter controls required')
    control = h['document'](CONTROL_RESULT)
    inputs = h['document'](CONTROL_PLAN)
    source_gate = h['document'](plan['emitter_source_review'])
    need(plan['emitter_source_review'] == inputs['candidate_source_review'] == control['candidate_source_review']
        and source_gate['status'] == 'passed_source_only' and source_gate['findings'] == []
        and sorted(source_gate['candidate_pins'].values(), key=lambda r: r['path']) ==
            sorted(inputs['candidate_pins'], key=lambda r: r['path'])
        and control['status'] == 'passed' and control['test_groups_passed'] == 20
        and control['pytest_returncode'] == 0 and control['cleanup_errors'] == []
        and control['plan'] == CONTROL_PLAN and control['primary_error'] is None
        and control['strict_guards_verified_before_after'] == 2641
        and control['all_historical_and_candidate_inputs_unchanged'] is True
        and control['native_jobs'] == control['model_fit_calls'] == control['metadata_hydration_calls'] == 0
        and control['original_ranker_import_or_execution_calls'] == 0
        and all(control[k] is source_gate[k] is False for k in AUTHORITY), 'actual host control/source joins required')
    for row in (control['producer'], control['runner_source_review'], control['stdout'], control['junit']):
        h['exact'](row)
    for copy in control['captured_test_sources']:
        h['exact'](copy['original']); h['exact'](copy['captured'])
    old_request = h['document'](inputs['native_guard_request'])
    h['validate_guard_union'](old_request)
    candidate = {Path(row['path']).name: row for row in inputs['candidate_pins']}
    need(set(candidate) == {'objective_container_emitter.py', 'test_objective_container_emitter.py',
        'candidate-interface.json', 'source-model-obligations-01.json'}, 'exact four source roles required')
    emitter = candidate['objective_container_emitter.py']
    need((emitter['bytes'], emitter['sha256']) == EMITTER_PIN, 'exact tested emitter required')

    tooling = h['document'](plan['language_tooling_source_review'])
    language_gate = h['document'](plan['language_source_review'])
    need(tooling['status'] == language_gate['status'] == 'passed_source_only'
        and tooling['findings'] == language_gate['findings'] == []
        and tooling['reviewed_candidate_source_gate'] == plan['language_source_review']
        and plan['language_helper'] in tooling['reviewed_sources']
        and all(tooling[k] is language_gate[k] is False for k in AUTHORITY),
        'root-selected immutable language helper needs independent exact source gates')
    helper_path = Path(plan['language_helper']['path'])
    need(helper_path.name == 'language_file_helpers_01.py'
        and helper_path.is_relative_to(W / 'qualification/codebase_ir'), 'confined language helper role required')
    language_raw = h['exact'](plan['language_helper'], True)
    language = {'__file__': str(helper_path), '__name__': 'held_qualified_container_language_file_readers'}
    exec(compile(language_raw, str(helper_path), 'exec'), language)
    need(language['MODULES'] == tooling['reviewed_modules'] == language_gate['reviewed_modules']
        and language['SOURCE_GATE'] == plan['language_source_review'], 'selected helper module/source gate differs')
    request = language['document'](plan['language_guard_request'])
    language['validate_guard_union'](request)
    need(len(request['strict_old_inputs']) == language['STRICT_GUARD_COUNT']
        and language['STRICT_GUARD_COUNT'] >= 2682
        and len(request['protected_live_sources']) == 4
        and request['original_checkout_guards'] == old_request['original_checkout_guards']
        and all(request[k] is False for k in AUTHORITY), 'exact reviewed additive source context required')
    staged = plan['staged_imports']
    need(type(staged) is list and len(staged) == 5
        and tuple(language['module'](row['mode'])['module'] for row in staged) == MODULE_ORDER,
        'five actual accepted dependency stages in source order required')
    need(plan['base_environment_manifest'] == language['BASE_PROFILE'],
        'exact selected helper inherited environment required')
    base = language['document'](plan['base_environment_manifest'])
    extended, joined = language['import_extension'](base, staged)
    need(tuple(row['module'] for row in joined) == MODULE_ORDER, 'complete actual staged qualified imports required')
    staged_inputs = []
    for row in staged:
        selected = language['module'](row['mode'])
        check = language['document'](row['check_result'])
        need(check['status'] == 'passed' and check['native_lean_returncode'] == 0
            and (check['source']['bytes'], check['source']['sha256']) ==
                (selected['source']['bytes'], selected['source']['sha256']), 'accepted stage exact source required')
        staged_inputs.extend([row['check_result'], check['source'], check['augmented_source'], check['environment_manifest']])
    # File descriptors accumulated by the language helper's independent reader
    # are verified separately from the historical reader below.
    def verify():
        h['validate_guard_union'](old_request)
        language['validate_guard_union'](request)
        for row in [*old_request['strict_old_inputs'], *old_request['protected_live_sources'],
            *request['strict_old_inputs'], *request['protected_live_sources'], *inputs['candidate_pins'],
            *staged_inputs, *[inputs[role] for role in BUFFER_ROLES]]:
            h['exact'](row)
        for role, cwd in (('root', W), ('child', W / 'external/ipfs_accelerate')):
            expected = request['original_checkout_guards'][role]
            head = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(cwd),
                'rev-parse', 'HEAD'], text=True, timeout=10).strip()
            need(head == expected['head'] and h['pin'](expected['index']['path']) == expected['index'],
                'original checkout changed')
        language['verify_held'](); h['verify_held']()
    verify()
    buffers = [h['exact'](inputs[role], True) for role in BUFFER_ROLES]
    namespace = {'__name__': 'held_exact_tested_whole_prefix_emitter'}
    exec(compile(h['exact'](emitter, True), emitter['path'], 'exec'), namespace)
    observed, original_parse = [], ast.parse
    def counted_parse(*arguments, **keywords):
        observed.append(1)
        return original_parse(*arguments, **keywords)
    ast.parse = counted_parse
    try:
        emitted = namespace['emit_source_bound_prefix'](*buffers)
    finally:
        ast.parse = original_parse
        verify()
    need(len(observed) == 3 and emitted['whole_five_assignment_prefix_emitted'] is True
        and emitted['original_source_rejoined'] is emitted['same_buffer_compiler_receipt_rejoined'] is True
        and emitted['numeric_assignments_decoded'] == 5 and emitted['source_context_statements_rejoined'] == 7
        and emitted['source_binding_records_rejoined'] == 17 and emitted['operation_counts'] == EXPECTED_COUNTS
        and tuple(row['name'] for row in emitted['source_bound_assignments']) == PREFIX_NAMES
        and emitted['actual_numeric_coordinates_supplied'] == emitted['original_ranker_execution_calls'] == 0
        and emitted['source_suffix_compiled'] is False
        and emitted['source_L2_exact_ratio'] == ('5764607523034235', '576460752303423488')
        and all(emitted[k] is False for k in AUTHORITY), 'actual complete original prefix host join required')
    for key in ('kernel_checked', 'theorem_qualified', 'strict_cache_admission',
        'Lean_SourcePrefix_literal_typechecked', 'typed_Lean_SourcePrefix_exists', 'source_semantic_equivalence_proved',
        'whole_objective_semantics_proved', 'computed_gradient_semantics_proved',
        'source_error_order_equivalence_proved', 'host_decoder_formal_preservation_proved',
        'Python_Float_semantics_proved', 'CPython_math_fsum_semantics_proved', 'Python_libm_semantics_proved',
        'optimizer_source_convergence_proved', 'global_autoencoder_convergence_proved'):
        need(emitted[key] is False, 'host receipt falsely grants broader semantics: ' + key)
    need(emitted['emitted_namespace'] == 'GeneratedOriginalObjectiveContainerPrefix', 'fixed generated namespace required')
    lean = emitted['text'].encode('utf-8')
    need((len(lean), hashlib.sha256(lean).hexdigest()) ==
        (emitted['text_utf8_bytes'], emitted['text_sha256']), 'entire emitted source join required')
    end = '\nend\nend «GeneratedOriginalObjectiveContainerPrefix»\n'.encode('utf-8')
    need(lean.endswith(end) and b'\n#print axioms ' not in lean, 'exact whole module terminator required')
    generated = lean[:-len(end)] + suffix + end
    need(plan['output_root'] == str(OUTPUT) and OUTPUT.resolve(strict=False) == OUTPUT,
        'fixed canonical fresh output scope required')
    OUTPUT.mkdir()
    lean_pin = save_bytes(h, OUTPUT / 'ObjectiveOriginalPrefix.lean', lean)
    emission_pin = h['write'](OUTPUT / 'emission-receipt.json', emitted)
    generated_pin = save_bytes(h, OUTPUT / 'ObjectiveContainerPrefixGenerated.lean', generated)
    verify()
    receipt = {'schema': 'ranker-objective-container-prefix-host-materialization@1', 'status': 'passed_host_only',
        'producer': own, 'plan': pp, 'producer_source_review': plan['producer_review'],
        'emitter': emitter, 'host_controls': CONTROL_RESULT, 'host_control_plan': CONTROL_PLAN,
        'emitter_source_review': plan['emitter_source_review'],
        'inputs': {role: inputs[role] for role in BUFFER_ROLES},
        'language_source_review': plan['language_source_review'],
        'language_tooling_source_review': plan['language_tooling_source_review'],
        'language_helper': plan['language_helper'], 'language_guard_request': plan['language_guard_request'],
        'staged_qualified_imports': staged, 'staged_qualified_module_names': list(MODULE_ORDER),
        'base_environment_manifest': plan['base_environment_manifest'],
        'extended_environment_descriptor_count_read': extended['external_file_count'],
        'complete_environment_dependency_body_rehash_performed': False,
        'original_whole_emitted_source': lean_pin, 'whole_emission_receipt': emission_pin,
        'generated_proof_candidate_source': generated_pin, 'reviewed_proof_suffix': plan['proof_suffix'],
        'generated_query_names': ['GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_compiles',
                                 'GeneratedOriginalObjectiveContainerPrefix.emitted_prefix_preserves'],
        'source_AST_parse_calls_observed': len(observed), 'source_binding_records_rejoined': 17,
        'source_context_statements_rejoined': 7, 'numeric_assignments_decoded': 5,
        'whole_five_assignment_prefix_emitted': True, 'source_suffix_compiled': False,
        'operation_counts': EXPECTED_COUNTS, 'actual_numeric_coordinates_supplied': 0,
        'original_ranker_execution_calls': 0, 'historical_strict_guard_count': 2641,
        'language_source_guard_count': len(request['strict_old_inputs']),
        'language_origin_guard_count': 2682, 'protected_live_sources': 4,
        'guards_same': True, 'ordinary_host_materialization_job': True,
        'supervisor_lease_claimed': False, 'new_native_jobs': 0, 'new_test_jobs': 0,
        'new_model_jobs': 0, 'new_metadata_jobs': 0, 'kernel_checked': False,
        'generated_prefix_compiles_proved': False, 'generated_prefix_preservation_proved': False,
        'strict_cache_admission': False, 'whole_objective_and_computed_gradient_equivalence_proved': False,
        'JSONdecoder_formal_preservation_proved': False, 'original_preparation_equivalence_proved': False,
        'Python_Float_libm_fsum_refinement_proved': False, 'optimizer_source_convergence_proved': False,
        'global_autoencoder_convergence_proved': False, 'full_task_satisfaction': 'unknown',
        'all32_governing_RPI_exits': 'OPEN', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **AUTHORITY}
    out = h['write'](OUTPUT / 'materialization-receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'receipt': out, 'whole_source': lean_pin,
        'generated_candidate': generated_pin, 'AST_parse_calls': len(observed), 'native_jobs': 0}))


if __name__ == '__main__':
    main()
