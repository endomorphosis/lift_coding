"""Review final-input auditor inert source; never import or execute that auditor."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
HERE = Path(__file__).resolve().parent
TARGET = W / 'maintenance/ranker-objective-scalar-publication-input-review-20261005-01/review_inputs_01.py'
PUB = W / 'maintenance/ranker-objective-scalar-publication-source-review-20261005-01/review-receipt.json'
Q = W / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
PINS = {
    TARGET: (35412, '79cc227e1d50242a1f7f828f34a3fb648da4e37c9400eba10f19d3361207c187'),
    PUB: (13455, 'a76277c257ca0fcae4e53ea1c304398853b79b935e1afff3cdf2d95606c1e2f0'),
}
HELD = {}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path, expected=None):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical source input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and 0 <= first.st_size <= 1024**2, 'bounded independent review input')
        chunks, total = [], 0
        while block := os.read(fd, 65536):
            total += len(block)
            need(total <= 1024**2, 'running independent review bound')
            chunks.append(block)
        raw = b''.join(chunks)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda row: tuple(getattr(row, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and total == first.st_size, 'input changed')
    finally:
        os.close(fd)
    row = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None:
        need((row['bytes'], row['sha256']) == expected, 'exact reviewed source pin')
    need(str(path) not in HELD or HELD[str(path)] == row, 'previous review input changed')
    HELD[str(path)] = row
    return raw, row


def require(text, *fragments):
    for fragment in fragments:
        need(fragment in text, 'source control missing: ' + fragment)


def main():
    need(__debug__, 'optimized review refused')
    need(not (HERE / 'review-receipt.json').exists(), 'fresh source supplement required')
    source, target_pin = read(TARGET, PINS[TARGET])
    publication, publication_pin = read(PUB, PINS[PUB])
    text = source.decode()
    tree = ast.parse(source, filename=str(TARGET))
    allowed_imports = {'argparse', 'datetime', 'hashlib', 'json', 'os', 'pathlib', 'stat', 'time'}
    for node in tree.body:
        if isinstance(node, ast.Import):
            need(all(alias.name in allowed_imports for alias in node.names), 'stdlib-only target imports')
        elif isinstance(node, ast.ImportFrom):
            need(node.module in allowed_imports, 'stdlib-only target from-imports')
        elif isinstance(node, ast.If):
            need(ast.dump(node.test, include_attributes=False) == ast.dump(ast.parse("__name__ == '__main__'", mode='eval').body, include_attributes=False), 'sole main guard')
        elif isinstance(node, ast.Assign):
            need(all(isinstance(call.func, ast.Name) and call.func.id == 'Path' for call in ast.walk(node.value)
                     if isinstance(call, ast.Call)), 'module setup has only inert path constructor calls')
        elif isinstance(node, ast.Expr):
            need(isinstance(node.value, ast.Constant) and type(node.value.value) is str, 'module docstring only')
        else:
            need(isinstance(node, ast.FunctionDef), 'inert target definitions')
    need(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in
                 {'exec', 'eval', 'compile', '__import__'} for node in ast.walk(tree)), 'no dynamic target execution')
    need(not any(isinstance(node, ast.Attribute) and node.attr == 'read_bytes' for node in ast.walk(tree)), 'no unbounded body allocation')
    require(text,
        "fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)",
        "need(total <= p['bytes'], 'pinned stream grew beyond declared size')",
        "need(stat_identity(os.fstat(fd)) == before and total == p['bytes']",
        "need(total <= before['size'], 'observed stream grew beyond initial size')",
        "0 < limit <= 32 * 1024**2 and binding['bytes'] <= limit",
        "os.read(fd, min(1048576, limit + 1 - total))",
        "need(total <= limit, 'parsed input grew beyond bound')",
        "stat_identity(os.fstat(fd)) == identity(path) == before",
        "return parse(bounded_read(binding, 32 * 1024**2))",
        "reviewed == {str(path): actual_pin(path) for path in source_paths}",
        "len(reviewed) == len(source_review['reviewed_sources']) == 9",
        "len(phase_modes) == len(set(phase_modes)) == 5 and set(phase_modes) == expected_modes",
        "built['frozen_build_plan'] == metadata['frozen_build_plan']",
        "wire(current) == wire(load(metadata['metadata_inputs']))",
        "closed['plan'] == PINS['plan'] and closed['final_selection'] == PINS['selection']",
        "'reviewer': actual_pin(Path(__file__).resolve()), 'fixed_inputs': PINS",
        "len(guards['files']) == 2393", "len(request['strict_old_inputs']) == 2108",
        "len(request['protected_live_sources']) == 4", "metadata['metadata_row_count'] == 4458",
        "sum(map(len, prior.values())) == 4440", "len(current['vectors']) == 375",
        "len(current['contracts']) == 2", "pure['selected_test_count'] == 98", "len(pure_phases) == 294",
        "compile_receipt['source_AST_parse_calls'] == 2", "compile_receipt['source_function_execution_calls'] == 0",
        "with destination.open('xb') as stream", "os.fsync(stream.fileno())")
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    native_text = ast.get_source_segment(text, functions['native'])
    require(native_text, "for binding in profile['files']:", 'check_pin(binding)',
        "native_per_file_capture_bytes_unchanged'] == 65536", "root_reconstructed_external_module_aggregate_max_bytes'] == 3997696",
        'bounded_read(chunks[name], 65536)', "bounded_read(binding, 16 * 1024**2)",
        "set(x['axioms']) <= ALLOWED", "x['report_occurrences'] == 2",
        "len(actual_queries) == (5 if entry['mode'] == 'lean-objective-scalar-01' else 9)")
    public_review = json.loads(publication)
    need(public_review['status'] == 'passed_source_only' and public_review['outstanding_source_issues'] == [] and
         len(public_review['reviewed_sources']) == 9, 'exact prior nine-source publication pass')
    for binding in public_review['reviewed_sources']:
        need(read(binding['path'], (binding['bytes'], binding['sha256']))[1] == binding, 'publication reviewed source is current')
    descriptors = {}
    for name in ['evidence/compile-source-objective-01/objective-slices.json', 'evidence/compile-source-objective-01/closed.json',
                 'evidence/metadata-objective-01/metadata-readback.json', 'qualified-review-01.json', 'file-only-seal-01.json']:
        raw, binding = read(Q / name)
        descriptors[name] = binding
        body = json.loads(raw)
        if name.endswith('objective-slices.json'):
            need(body['source_function_execution_calls'] == 0 and body['host_AST_parse_calls'] == 1 and body['theorem_qualified'] is False, 'actual AST field interface')
        elif name == 'evidence/compile-source-objective-01/closed.json':
            need(body['source_AST_parse_calls'] == 2 and body['source_function_execution_calls'] == 0, 'actual compile field interface')
        elif name.endswith('metadata-readback.json'):
            need(body['schema'] == 'ranker-objective-scalar-native-metadata-readback@1' and 'frozen_build_plan' in body and
                 body['metadata_row_count'] == 4458, 'actual metadata field interface')
        elif name == 'file-only-seal-01.json':
            need(body['regular_file_count'] == 276 and body['regular_file_bytes'] == 78794802, 'actual final sealed census interface')
    own = read(Path(__file__).resolve())[1]
    need(all(read(path, (binding['bytes'], binding['sha256']))[1] == binding for path, binding in list(HELD.items())), 'final source/JSON pin recheck')
    result = {'schema': 'ranker-objective-scalar-final-input-reviewer-independent-source-review@1', 'status': 'passed_source_only',
        'producer': own, 'reviewed_source': target_pin, 'prior_nine_source_review': publication_pin,
        'AST_node_count': sum(1 for _ in ast.walk(tree)), 'actual_small_JSON_interfaces_checked': descriptors,
        'scope': 'The independent file-only input auditor hashes actual guarded/native dependency bodies, checks complete native objects and ordered chunks, and joins the frozen publication population and peer source reviews. This source supplement runs none of those target operations.',
        'finite_declared_size_O_NOFOLLOW_FD_streams': True, 'large_guard_or_native_dependency_body_memory_accumulation': False,
        'bounded_JSON_allocation_bytes': 33554432, 'bounded_provenance_and_export_allocation_bytes': 14680064,
        'bounded_native_chunk_allocation_bytes': 65536, 'bounded_joined_object_allocation_bytes': 16777216,
        'all_nine_publication_source_review_descriptors_join_actual_sources': True,
        'exact_five_distinct_owned_phase_modes_required': True, 'canonical_metadata_and_frozen_plan_join_required': True,
        'complete_2393_guard_union_and_2108plus4_request_inclusion_required': True,
        'output_fixed_inputs_keys': ['closed', 'plan', 'selection', 'guards'],
        'output_schema': 'ranker-objective-scalar-final-publication-input-review@1',
        'output_status': 'passed_file_only_final_publication_input_review', 'output_issue_field': 'outstanding_issues',
        'output_matches_pinned_invocation_producer_interface': True, 'full_selected_root_and_seal_self_census_required': True,
        'native_standard_axiom_queries_required': 14, 'pure_controls_required': 98, 'pure_phase_records_required': 294,
        'metadata_required': {'families': 32, 'payloads': 4458, 'canonical_prior_prefix_payloads': 4440, 'vectors_unchanged': 375, 'contracts_unchanged': 2},
        'outstanding_source_issues': [], 'reviewed_auditor_imported_or_executed': False,
        'target_helper_native_model_metadata_codec_classifier_git_remote_jobs_run': False,
        'full_environment_body_rehash_by_this_source_reviewer': False,
        'actual_final_input_PASS_or_publication_claimed_here': False,
        'limitations': ['The actual final-input auditor must still run against externally reviewed closed/plan/selection/guards pins and counts.',
                        'Native environment/full object body rehash is delegated to that actual auditor, not repeated by this source-only supplement.',
                        'Only narrow exact-real scalar constructor/projection claims are supported; all host/Python/Float/full objective/gradient/training/global convergence frontiers remain open.'],
        'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None,
        'atomic_whole_source_snapshot_claimed': False, 'historical_execution_origin_proved': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
    with (HERE / 'review-receipt.json').open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'review': read(HERE / 'review-receipt.json')[1]}))


if __name__ == '__main__':
    main()
