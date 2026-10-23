"""Materialize tested host JSON IR; no original ranker or native proof runs."""
import argparse
import hashlib
import json
from pathlib import Path
import resource

W = Path('/home/barberb/lift_coding')
AUTHORITY = {k: False for k in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')}


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--expected-source-sha256', required=True)
    args = p.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    helper = W / 'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02/container_core_file_helpers_01.py'
    raw = helper.read_bytes()
    need(len(raw) == 17601 and hashlib.sha256(raw).hexdigest() ==
         '815bec62dd2c8de4073b389dbdf62827c4a639d4f6a3e08e5e79ef83ccffff3a', 'reviewed file readers required')
    h = {'__file__': str(helper), '__name__': 'held_prefix_materialization_file_readers'}
    exec(compile(raw, str(helper), 'exec'), h)
    own = h['pin'](Path(__file__).resolve())
    need(own['sha256'] == args.expected_source_sha256, 'externally pinned materializer source required')
    old = W / 'maintenance/ranker-objective-prefix-controls-20261005-01'
    control_pin = {'path': str(old / 'run-01/closed.json'), 'bytes': 3787,
        'sha256': '69445c990bcf7bcf6bc614cbbc68320249bc022c743f9e306da1b1dfdcf38505'}
    controls = h['document'](control_pin)
    need(controls['status'] == 'passed' and controls['test_groups_passed'] == 20
         and controls['pytest_returncode'] == 0 and controls['cleanup_errors'] == [], 'actual twenty passed host controls required')
    plan = h['document'](controls['plan'])
    request = h['document'](plan['native_guard_request'])
    h['validate_guard_union'](request)
    seal = h['document'](plan['proof_seal'])
    for row in [*request['strict_old_inputs'], *request['protected_live_sources'], *seal['files'],
                *plan['candidate_pins'], plan['candidate_source_review'], plan['runner_source_review']]:
        h['exact'](row)
    by_name = {Path(row['path']).name: row for row in plan['candidate_pins']}
    compiler_pin = by_name['objective_prefix_compiler.py']
    need(compiler_pin['bytes'] == 48095 and compiler_pin['sha256'] ==
         'd4aec9ef8f239314c48ca2d2e0a70495be6d2df4c79329e338d9a96c26ee196c', 'exact tested compiler required')
    source = h['exact'](plan['original_source'], True)
    bindings = h['exact'](plan['bindings'], True)
    module = {'__file__': compiler_pin['path'], '__name__': 'held_tested_prefix_materializer'}
    exec(compile(h['exact'](compiler_pin, True), compiler_pin['path'], 'exec'), module)
    old_parse = module['ast'].parse
    parses = []
    def counted_parse(text, *args, **keywords):
        parses.append(text)
        return old_parse(text, *args, **keywords)
    module['ast'].parse = counted_parse
    try:
        result = module['compile_objective_numeric_prefix'](source, bindings)
        rendered = module['render_generated_objective_prefix'](result, source, bindings)
    finally:
        module['ast'].parse = old_parse
    raw = rendered['text'].encode('utf-8')
    need(len(parses) == 2 and parses[0] == parses[1] == source.decode('utf-8')
         and len(raw) == rendered['text_utf8_bytes'] and hashlib.sha256(raw).hexdigest() == rendered['text_sha256']
         and json.loads(raw) == result and result['accepted_numeric_statements'] == 5
         and result['checked_context_statements'] == 7 and len(result['checked_bindings']) == 17
         and result['kernel_checked'] is result['typed_Lean_SourcePrefix_exists'] is False
         and all(result[k] is False for k in AUTHORITY), 'source-bound unqualified JSON renderer result differs')
    h['verify_held']()
    root = W / 'qualification/codebase_ir/ranker-objective-prefix-host-result-20261005-01'
    root.mkdir()
    output = root / 'objective-prefix-draft.json'
    with output.open('xb') as stream:
        stream.write(raw)
    output_pin = h['pin'](output)
    receipt = {'schema': 'ranker-objective-prefix-host-materialization@1', 'status': 'passed_host_JSON_materialization_only',
        'producer': own, 'host_controls': control_pin, 'control_plan': controls['plan'], 'compiler': compiler_pin,
        'original_source': plan['original_source'], 'bindings': plan['bindings'], 'output': output_pin,
        'source_AST_parse_calls_observed': 2, 'same_source_buffer_reextracted': True,
        'accepted_numeric_statements': 5, 'checked_context_statements': 7, 'checked_bindings': 17,
        'kernel_checked': False, 'typed_Lean_SourcePrefix_exists': False, 'native_queries': 0,
        'new_tests': 0, 'model_training_calls': 0, 'original_ranker_import_or_execution_calls': 0,
        'metadata_hydration_calls': 0, 'cache_admission': False, 'source_semantic_equivalence_proved': False,
        'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN', **AUTHORITY}
    h['verify_held']()
    receipt_pin = h['write'](root / 'materialization-receipt.json', receipt)
    h['verify_held']()
    print(json.dumps({'status': receipt['status'], 'output': output_pin, 'receipt': receipt_pin, 'new_native_queries': 0}))


if __name__ == '__main__':
    main()
