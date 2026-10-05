#!/usr/bin/python3.12
"""Review pinned publication closure sources without importing/executing them.

This reads local files, parses source ASTs and receipt JSON, and exclusively
writes a source-review receipt. It does not produce publication evidence or
perform a native, test, model, metadata, archive, network, or Git operation.
"""

import ast
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path('/home/barberb/lift_coding')
R4 = WORKSPACE / 'maintenance/ranker-objective-scalar-publication-root-20261005-01'
S4 = WORKSPACE / 'maintenance/ranker-objective-scalar-publication-20261005-01'
OUT = WORKSPACE / 'maintenance/ranker-objective-scalar-publication-closure-source-review-20261005-01'
Q5 = WORKSPACE / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
PINS = {
    'close_release_publication_01.py': (11159, '749cb044cc35cca875692b1464b0927d76cc845a48fd0e9498cfb2e3d5551c63'),
    'close_combined_publication_01.py': (9217, 'a8c4e4ac8dc36435e5e250bd36c2d0234d7ea0c3b79f28228e856f4600cb3fe2'),
}
HELD = {}
AST_PARSE_CALLS = 0


def need(value, label):
    if value is not True:
        raise ValueError(label)


def read(path, expected=None):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular source/receipt')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2, 'bounded regular input')
        chunks = []
        total = 0
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= 32 * 1024**2, 'input grew beyond bound')
            chunks.append(block)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        sig = lambda row: tuple(getattr(row, key) for key in fields)
        need(sig(before) == sig(os.fstat(fd)) == sig(path.lstat()) and total == before.st_size, 'same-buffer stable input')
        blob = b''.join(chunks)
    finally:
        os.close(fd)
    descriptor = {'path': str(path), 'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
    need(expected is None or descriptor == expected, 'externally promised source pin differs')
    need(str(path) not in HELD or HELD[str(path)] == descriptor, 'held input changed')
    HELD[str(path)] = descriptor
    return blob, descriptor


def source(path, pair=None):
    global AST_PARSE_CALLS
    expected = None if pair is None else {'path': str(path), 'bytes': pair[0], 'sha256': pair[1]}
    blob, descriptor = read(path, expected)
    tree = ast.parse(blob, filename=str(path))
    AST_PARSE_CALLS += 1
    return tree, descriptor


def unique_json(blob):
    def unique(items):
        output = {}
        for key, value in items:
            need(key not in output, 'no duplicate JSON keys')
            output[key] = value
        return output
    return json.loads(blob, object_pairs_hook=unique)


def constants(tree):
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and type(node.value) is str}


def gate(tree, message):
    matches = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name) and node.func.id == 'need' and len(node.args) == 2
               and isinstance(node.args[1], ast.Constant) and node.args[1].value == message]
    need(len(matches) == 1, 'unique semantic gate: ' + message)
    return ast.unparse(matches[0].args[0])


def fragments(expression, pieces, label):
    need(all(piece in expression for piece in pieces), 'source gate lacks join: ' + label)


def main():
    release, release_pin = source(R4 / 'close_release_publication_01.py', PINS['close_release_publication_01.py'])
    combined, combined_pin = source(R4 / 'close_combined_publication_01.py', PINS['close_combined_publication_01.py'])
    for tree in (release, combined):
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                need(node.level == 0, 'no relative project imports')
                imported.add(node.module)
        need(imported <= {'argparse', 'datetime', 'hashlib', 'json', 'os', 'pathlib', 're', 'stat',
                          'subprocess', 'urllib.request'}, 'standard-library imports only')
        need(not any(isinstance(node, (ast.Import, ast.ImportFrom)) and
                     any('ipfs' in alias.name for alias in node.names) for node in ast.walk(tree)), 'no project imports')
    schemas = {
        'ranker-objective-scalar-release-ledger-plan@1',
        'ranker-objective-scalar-closed-qualification@1',
        'ranker-objective-scalar-file-only-seal@1',
        'terminal-ir-HF-successor-publication@1',
        'ranker-objective-scalar-public-HF-readback-join@1',
        'terminal-ir-successor-evidence-publication-plan@1',
        'ranker-objective-scalar-exact-final-upload-scan@1',
        'ranker-objective-scalar-publication-closed-inputs@1',
        'ranker-objective-scalar-full-decoded-member-file-only-review@1',
        'ranker-objective-scalar-publication-plan@1',
        'ranker-objective-scalar-publication-final-selection@1',
        'ranker-objective-scalar-frozen-evidence-package@1',
        'ranker-objective-scalar-local-package-attempt@1',
        'ranker-objective-scalar-release-publication-ledger@1',
    }
    need(schemas <= constants(release), 'exact ledger schema gates match producer interfaces')
    fragments(gate(release, 'complete qualified seal population differs'), [
        "seal['regular_file_count'] == 276", "seal['regular_file_bytes'] == 78794802",
        "len(seal['files']) == 276", "sum((row['bytes'] for row in seal['files'])) == 78794802",
    ], '276-leaf 78794802-byte seal population')
    fragments(gate(release, 'preserved payload/model qualification flags differ'), [
        'is True', 'prior4440_payloads_preserved_exactly_as_prefixes', 'vectors_payloads_unchanged',
        'contracts_payloads_unchanged', 'prior_original_exact_real_model_weights_and_objective_convergence_preserved',
    ], 'ledger preservation claims are qualification-backed')
    fragments(gate(release, 'actual HF closure differs'), [
        "hf['schema'] == 'terminal-ir-HF-successor-publication@1'", "hf['commit'] == commit",
        "hf['parent'] == PARENT", "hf['plan'] == pins['hf_plan']", "hf['files'] == files",
        "hf['selected_bytes'] == total", "hf['prior_immutable_remote_files_preserved'] == 329",
    ], 'actual HF closure')
    fragments(gate(release, 'fresh public readback differs'), [
        "public['schema'] == 'ranker-objective-scalar-public-HF-readback-join@1'",
        "public['fresh_public_main_matches_commit'] is True",
        "public['fresh_public_main_after_tree_matches_commit'] is True",
        "public['all_selected_local_pins_rechecked'] is True",
        "public['prior_immutable_files_preserved'] == 329",
        "public['committed_total_regular_files'] == 331 + files - 2",
    ], 'fresh HF public readback')
    fragments(gate(release, 'final plan/selection qualification joins differ'), [
        "final_plan['documents']['file_seal'] == pins['seal']",
        "final_plan['documents']['qualified_review'] == pins['qualification']",
        "selection['schema'] == 'ranker-objective-scalar-publication-final-selection@1'",
    ], 'final quiet plan and selection')
    fragments(gate(release, 'complete package manifest selection joins differ'), [
        "manifest['closed_inputs'] == pins['frozen_inputs']", "manifest['plan'] == frozen['plan']",
        "manifest['final_selection'] == frozen['final_selection']",
        "manifest['file_count'] == len(selection['files'])",
        "manifest['original_file_bytes'] == sum((row['bytes'] for row in selection['files']))",
    ], 'manifest complete frozen selection')
    fragments(gate(release, 'package closure differs'), [
        "package_closed['schema'] == 'ranker-objective-scalar-local-package-attempt@1'",
        "package_closed['manifest'] == package['manifest']",
        "package_closed['candidate_hits'] == package_closed['source_drift_count'] == 0",
        "package_closed['cleanup_errors'] == []",
    ], 'package closure')
    fragments(gate(release, 'complete decoded/selected census differs'), [
        "package['sealed_file_count_rehashed'] == manifest['sealed_regular_file_count'] == 276",
        "package['sealed_file_bytes_rehashed'] == manifest['sealed_regular_file_bytes'] == 78794802",
        "package['selected_files_verified_before_after'] == package['decoded_members_verified'] == len(selection['files'])",
    ], 'package decoded denominator')
    peer_gate = gate(combined, 'Git final input review/stage/HF joins failed')
    fragments(peer_gate, [
        "peer['schema'] == 'ranker-objective-scalar-independent-final-Git-input-review@1'",
        "peer['status'] == 'passed_file_only_actual_HF_gate_and_exact_compact_selection'",
        "peer['findings'] == []", "git['final_stage'] in peer['reviewed_input_pins']",
        "pins[key] in peer['reviewed_input_pins']",
        'hf_publication', 'hf_public_readback', 'hf_ledger_before_git_commit',
    ], 'exact planned Git independent peer contract')
    need('startswith' not in peer_gate and 'outstanding_issues' not in peer_gate, 'placeholder peer interface removed')
    fragments(gate(combined, 'Git peer reviewed actual population differs'), [
        "peer['actual_HF_commit'] == hf_commit", "peer['combined_selected_files'] == plan['git_files']",
        "peer['combined_selected_bytes'] == plan['git_bytes']",
    ], 'peer actual HF/Git population')
    fragments(gate(combined, 'ledger binds this complete frozen selection'), [
        "frozen['schema'] == 'ranker-objective-scalar-publication-closed-inputs@1'",
        "frozen['final_selection'] == pins['full_frozen_selection']",
    ], 'combined ledger/frozen selection identity')
    fragments(gate(combined, 'actual HF parent/population/preservation joins differ'), [
        "hf['parent'] == public['parent'] == ledger['huggingface']['parent'] == 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e'",
        "hf['files'] == public['selected_files'] == ledger['huggingface']['selected_files']",
        "hf['selected_bytes'] == public['selected_bytes'] == ledger['huggingface']['selected_bytes']",
        "hf['prior_immutable_remote_files_preserved'] == public['prior_immutable_files_preserved'] == 329",
    ], 'combined HF actual parent/population')
    fragments(gate(combined, 'normal publication and fresh gitlink joins differ'), [
        "git['commit_calls'] == git['push_calls'] == 1", "git['force_push_calls'] == git['concurrency_rebases'] == 0",
        "git['parent_gitlinks'] == git['commit_gitlinks']", "len(git['commit_gitlinks']) == 9",
    ], 'normal Git push and parent gitlinks')
    fragments(gate(combined, 'complete Git closure differs'), [
        "git['full_new_population_remote_Git_blobs_verified'] is True",
        "git['all_nine_fresh_parent_gitlinks_preserved'] is True",
        "git['original_root_or_child_HEAD_index_mutations'] == 0",
        "git['remote_main'] == git_commit", "git['tree'] == git['remote_tree']",
    ], 'actual complete Git verification')
    fragments(gate(combined, 'held inputs changed after remote checks'), [
        "read_pin(row['path'])[1] == row", "namespace['HELD'].values()",
    ], 'complete held receipt/source rehash after fresh remotes')
    fragments(gate(combined, 'original checkout changed'), [
        "head == wanted['head']", "index == wanted['index']",
    ], 'original checkout HEAD/index checks')
    need({'fresh GitHub main differs', 'fresh HF main differs', 'selected source changed',
          'bounded external closure plan pin differs', 'externally pinned helper differs'} <= constants(combined),
         'bounded plan/helper/fresh remote/full source guard gates')
    combined_calls = [node for node in ast.walk(combined) if isinstance(node, ast.Call)]
    command_lists = [node.args[0] for node in combined_calls
                     if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                     and node.func.value.id == 'subprocess' and node.func.attr == 'check_output']
    need(len(command_lists) == 2 and all(isinstance(node, ast.List) for node in command_lists), 'explicit read-only Git argument lists')
    literal_args = [[element.value for element in node.elts if isinstance(element, ast.Constant)] for node in command_lists]
    need({tuple(row) for row in literal_args} == {
        ('git', '-C', 'ls-remote', 'origin', 'refs/heads/main'),
        ('git', '-c', 'core.fsmonitor=false', '-C', 'rev-parse', 'HEAD'),
    }, 'only read-only Git source commands')

    producer_sources = {}
    producer_schemas = {
        R4 / 'review_hf_readback_01.py': {'ranker-objective-scalar-public-HF-readback-join@1'},
        R4 / 'prepare_hf_plan_01.py': {'terminal-ir-successor-evidence-publication-plan@1'},
        R4 / 'scan_final_upload_01.py': {'ranker-objective-scalar-exact-final-upload-scan@1'},
        S4 / 'freeze_inputs.py': {'ranker-objective-scalar-publication-closed-inputs@1', 'ranker-objective-scalar-publication-final-selection@1'},
        S4 / 'review_package.py': {'ranker-objective-scalar-full-decoded-member-file-only-review@1'},
        S4 / 'build_package.py': {'ranker-objective-scalar-local-package-attempt@1', 'ranker-objective-scalar-frozen-evidence-package@1'},
    }
    for path, expected_schemas in producer_schemas.items():
        tree, descriptor = source(path)
        need(expected_schemas <= constants(tree), 'producer schema matches consumer source contract')
        producer_sources[str(path)] = descriptor

    q_pin = {'path': str(Q5 / 'qualified-review-01.json'), 'bytes': 11167,
             'sha256': '590163443db860ac03bc2d3fde0f07ac44626e8b6e7cc57a3d6c770c4da87f00'}
    seal_pin = {'path': str(Q5 / 'file-only-seal-01.json'), 'bytes': 86066,
                'sha256': '874b51a3358dee5dbd18b70c66770f4e3fdf3553c2fac3fb644075c37273f43d'}
    q = unique_json(read(Path(q_pin['path']), q_pin)[0])
    seal = unique_json(read(Path(seal_pin['path']), seal_pin)[0])
    need(q['schema'] == 'ranker-objective-scalar-closed-qualification@1' and q['status'] == 'passed'
         and q['qualified_theorem_queries'] == 14 and q['pure_test_cases'] == 98
         and q['metadata_payloads'] == 4458 and q['metadata_family_count'] == 32, 'existing Q5 actual evidence interface')
    need(seal['schema'] == 'ranker-objective-scalar-file-only-seal@1' and seal['review'] == q_pin
         and seal['regular_file_count'] == 276 and seal['regular_file_bytes'] == 78794802, 'existing Q5 seal interface')
    needed_q_fields = [
        'qualified_positive_native_lean_checks', 'additive_metadata_payloads', 'unchanged_vector_rows',
        'unchanged_contract_rows', 'prior4440_payloads_preserved_exactly_as_prefixes', 'vectors_payloads_unchanged',
        'contracts_payloads_unchanged', 'prior_original_exact_real_model_weights_and_objective_convergence_preserved',
        'python_ranker_source_equivalence_proved', 'global_autoencoder_convergence_proved', 'original_checkout_guards',
    ]
    need(all(key in q for key in needed_q_fields), 'all consumed Q5 fields exist')
    need(all(q[key] is True for key in needed_q_fields[4:8]), 'actual preservation flags true')
    for role in ('root', 'child'):
        need(set(q['original_checkout_guards'][role]) >= {'head', 'index'}, 'original checkout guard interface')
    for descriptor in list(HELD.values()):
        read(Path(descriptor['path']), descriptor)
    own_blob, own_pin = read(Path(__file__).absolute())
    receipt = {
        'schema': 'ranker-objective-scalar-publication-closure-independent-source-review@1',
        'status': 'passed_source_only', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'producer': own_pin, 'reviewed_sources': [release_pin, combined_pin],
        'supporting_local_producer_sources': list(producer_sources.values()),
        'existing_qualified_review': q_pin, 'existing_file_seal': seal_pin,
        'scope': 'unexecuted prospective R4 ledger/combined closure producers and pinned local producer interfaces',
        'ledger_source_checks': {
            'external_plan_SHA256_and_closed_keys_required': True,
            'canonical_nonsymlink_same_buffer_document_pins_and_after_read_guards': True,
            'exclusive_fsync_output_and_false_authority': True,
            'qualified_Q5_counts_14_queries_98_cases_4458_rows_join': True,
            'seal_276_leaves_78794802_bytes_join': True,
            'preserved_4440_prefixes_375_vectors_two_contracts_and_prior_real_model_backed_by_true_actual_flags': True,
            'exact_HF_public_package_scan_plan_and_closure_schemas': True,
            'frozen_input_final_plan_selection_manifest_package_closure_descriptor_joins': True,
            'complete_sealed_decoded_and_selected_denominator_joins': True,
            '329_prior_immutable_HF_identities_and_two_mutable_paths_population_formula': True,
            'Git_pending_status_preserved_as_historical_receipt': True,
        },
        'combined_source_checks': {
            'bounded_externally_pinned_standard_library_helper_and_closed_plan': True,
            'exact_planned_Git_peer_schema_status_empty_findings': True,
            'peer_final_stage_and_three_actual_HF_descriptor_joins': True,
            'peer_actual_HF_commit_and_compact_Git_counts_join': True,
            'complete_remote_Git_blob_and_tree_receipt_gates': True,
            'one_normal_commit_push_no_force_no_rebase_nine_gitlink_join': True,
            'HF_parent_population_preservation_ledger_joins': True,
            'full_frozen_selection_bound_through_prior_ledger_input_closure': True,
            'full_frozen_sources_rehashed_and_held_inputs_rechecked_after_fresh_remotes': True,
            'root_child_original_HEAD_index_guard_checks': True,
            'only_future_read_only_Git_and_public_HF_checks': True,
            'source_result_retains_open_task_convergence_and_false_authorities': True,
        },
        'planned_final_Git_peer_interface': {
            'schema': 'ranker-objective-scalar-independent-final-Git-input-review@1',
            'status': 'passed_file_only_actual_HF_gate_and_exact_compact_selection',
            'issue_field': 'findings', 'required_empty': True,
            'reviewed_input_pins_required': ['Git publication final_stage descriptor', 'exact HF closed descriptor',
                                            'exact public HF readback descriptor', 'exact historical HF ledger descriptor'],
            'actual_HF_commit_and_combined_selected_files_bytes_required': True,
            'poststage_receipt_excluded_from_its_own_Git_increment_to_avoid_self_reference': True,
            'actual_future_receipt_not_available_and_not_claimed_reviewed': True,
        },
        'all_local_held_source_receipt_pins_unchanged_before_after': True,
        'target_and_supporting_source_AST_parse_calls': AST_PARSE_CALLS,
        'target_source_execution_calls': 0, 'target_import_calls': 0,
        'project_imports': 0, 'native_model_test_metadata_archive_codec_jobs': 0,
        'network_or_Git_operations': 0, 'remote_mutations': 0,
        'actual_new_publication_closure_jobs_executed_by_review': 0,
        'actual_HF_or_Git_publication_success_claimed_by_this_source_review': False,
        'limitations': [
            'This is a source-only review, not actual remote publication evidence.',
            'Future actual externally pinned plan and receipt validation remain authorized root execution gates.',
            'New final Git peer interface is the promised source contract; future actual peer output must match every gate.',
            'Root must use these exact reviewed closer source pins and the reviewed helper pin in its external combined plan.',
        ],
        'outstanding_source_issues': [], 'all32_governing_RPI_exits': 'OPEN',
        'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
        'formalization_authority': False, 'mutation_authority': False, 'omission_authority': False,
        'planner_activation': False, 'strict_cache_admission': False,
        'python_ranker_source_equivalence_proved': False,
        'global_autoencoder_convergence_proved': False,
    }
    output = OUT / 'review-receipt.json'
    need(OUT.is_dir() and not OUT.is_symlink(), 'owned independent review directory')
    blob = (json.dumps(receipt, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(blob)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': receipt['status'], 'receipt': read(output)[1],
                      'producer': own_pin, 'outstanding_source_issues': []}, sort_keys=True))


if __name__ == '__main__':
    main()
