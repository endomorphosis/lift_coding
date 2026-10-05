"""Independent source-only audit; reviewed modules are never imported or run."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
HERE = Path(__file__).resolve().parent
S = W / 'maintenance/ranker-objective-scalar-publication-20261005-01'
R = W / 'maintenance/ranker-objective-scalar-publication-root-20261005-01'
OLD_S = W / 'maintenance/ranker-source-slices-publication-20261005-01'
OLD_R = W / 'maintenance/ranker-source-slices-publication-root-20261005-01'
HF = W / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
PINS = {
    S / 'SOURCE_API.md': (5246, '6bf535c98379c02efd6aa8b435f0abad76e79a889bb97e5540ec21d20cf7f3ea'),
    S / 'build_package.py': (27160, '2c4fe033d9c8fc7e19573c33fb64b722a5127cab1aa6181b1783de4160b1758f'),
    S / 'freeze_inputs.py': (3247, '2108df02a7fb64a7d0877a8dc24596ee86409f7bba145abafd1b46420f0f717e'),
    S / 'review_package.py': (18579, 'bf21b9a476731be8d10af1821c8a889c2108bd9bfa3344bfd1a20ae0889fcefb'),
    S / 'freeze_final_plan_01.py': (18928, '14807d9cf07e4a898001414c4ddc3a033056b1a2080b397b656285742607e4b1'),
    R / 'prepare_hf_plan_01.py': (16950, 'f1babaf4f90463dab973f5d185fce6d0c52c5fb9df6729a878ed878b6c45cfb1'),
    R / 'prepare_invocation_01.py': (11102, '223fcd8ce7918879c97da16e972da4ff4af59ff468e74e9465cd3a8ef76af72f'),
    R / 'review_hf_readback_01.py': (8944, '263e3c8a7879f310c1079ceda64e18df98821198491026f6978cf81111fef812'),
    R / 'scan_final_upload_01.py': (4887, '9972c1291344a43485378f25c6853df1f8394c2d0bdf33ee24b7aa249beccd6b'),
    OLD_S / 'build_package.py': (27020, 'f1269ff1b2d3e808a8e4c44a292d098a08f5d97adf9477da96e565f107d7618e'),
    OLD_S / 'freeze_inputs.py': (3233, 'baa46e4be40f7ce3c1cad6cd4aebeb2bfae10312570041553c1dcd3eacfcda56'),
    OLD_S / 'review_package.py': (18549, '150ac0bbdd63663daace169c668dfe1b0d088d9394c03480e8816c47124c1e3c'),
    OLD_R / 'prepare_hf_plan_02.py': (10632, 'd4762b7d1d30036caf83965709c7b54d61da781766c5f71669ed2194d7c66e82'),
    OLD_R / 'prepare_invocation_01.py': (7860, '652d9410c1746fb92b6875b96fa05f26b1c7340c25cb3e7500860f40c6d0d950'),
    OLD_R / 'review_hf_readback_01.py': (8935, '231f61b3bc3bc2dfcc1cce54d48bed560e6f7270ae04e461e151cccdf0c1e9f8'),
    OLD_R / 'scan_final_upload_01.py': (4876, 'b170ec89299076fc88226d28fad891923a33bd7e2fc2ba6facf620e07b123c95'),
    W / 'maintenance/ranker-source-slices-publication-source-review-20261005-01/review-receipt.json':
        (7848, 'fbfef37641d60af2e94439b53faa71a5dcfbcbfb35ea632ca9882f84561f4257'),
}
HELPERS = {
    HF / 'successor-source-model-package-03/build_package.py': '8c8eab266a053115cdf0ea11a8aea5323611c2ab049ec1541383831618e385ce',
    HF / 'build_evidence_archive_02.py': 'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036',
    HF / 'classify_and_prepare_public_archive_07.py': 'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8',
    W / 'maintenance/ranker-curvature-publication-source-plan-20261005-01/build_package.py':
        '4e14c08fc6d680e5fcbf755f649284f750353b73b42dd08b926398f4c43c9a93',
    HF / 'run_frozen_publication_phase.py': '8d9955df76155f75326fdda8039119bacab9bad3ca71306f241be9b2124d01b8',
    HF / 'publish_successor_evidence_02.py': '670e064a8222ce1b0c962e202985974741a9a4476630b0541c7ec880b32009f2',
}
EXPECTED_PROFILE = {'raw_population_max': 268435456, 'raw_member_sum_per_shard_max': 14680064,
    'per_file_max': 14680064, 'complete_decoded_tar_max': 16777216, 'compressed_shard_max': 16777216,
    'aggregate_decoded_work_max': 1073741824, 'wall_seconds': 180, 'members_max': 10000, 'depth_max': 6,
    'shards_max': 64, 'zstd_args': ['-T1', '-3'], 'duplicate_verification_decoder_invocations': 0,
    'member_readback_profile': 'same_first_decoded_tar_and_member_streams@1', 'native_qualification_limits_changed': False}
EXPECTED_NATIVE = {'timeout_seconds': 20, 'cpu_seconds': 20, 'max_input_bytes': 262144,
                   'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}
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
        need(stat.S_ISREG(first.st_mode) and 0 <= first.st_size <= 16 * 1024**2, 'bounded review input')
        chunks, size = [], 0
        while block := os.read(fd, 1024**2):
            size += len(block)
            need(size <= 16 * 1024**2, 'running source read cap')
            chunks.append(block)
        raw = b''.join(chunks)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda row: tuple(getattr(row, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and size == first.st_size, 'source drift')
    finally:
        os.close(fd)
    row = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None:
        need((row['bytes'], row['sha256']) == expected, 'reviewed source pin differs')
    need(str(path) not in HELD or HELD[str(path)] == row, 'previous source input changed')
    HELD[str(path)] = row
    return raw, row


def static(node, values):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        result = [static(child, values) for child in node.elts]
        return result if isinstance(node, ast.List) else tuple(result)
    if isinstance(node, ast.Dict):
        return {static(key, values): static(value, values) for key, value in zip(node.keys, node.values)}
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Pow)):
        left, right = static(node.left, values), static(node.right, values)
        need(type(left) is int and type(right) is int and 0 <= left <= 1024**3 and 0 <= right <= 1024**3,
             'bounded literal arithmetic')
        if isinstance(node.op, ast.Pow):
            need(right <= 4, 'bounded literal exponent')
            return left**right
        return left * right
    raise ValueError('not literal data')


def constants(tree):
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            try:
                result = static(node.value, values)
            except ValueError:
                continue
            target = node.targets[0]
            if isinstance(target, ast.Name):
                values[target.id] = result
            elif isinstance(target, ast.Tuple) and isinstance(result, tuple) and len(target.elts) == len(result):
                for name, value in zip(target.elts, result):
                    need(isinstance(name, ast.Name), 'literal data assignment')
                    values[name.id] = value
    return values


class Normalize(ast.NodeTransformer):
    def __init__(self, census=False):
        self.census = census

    def visit_Constant(self, node):
        if type(node.value) is str:
            replacements = (
                ('ranker-objective-ir-candidate-20261005-01', 'ranker-source-semantics-20261005-01'),
                ('ranker-objective-ir-source-plan-20261005-01', 'ranker-source-semantics-source-plan-20261005-01'),
                ('held_objective_scalar_publication_', 'held_convergence_publication_'),
                ('held_objective_scalar_input_freeze', 'held_convergence_input_freeze'),
                ('held_objective_scalar_package_review_', 'held_convergence_package_review_'),
                ('held_objective_scalar_upload_', 'held_convergence_upload_'),
                ('objective-scalar-package-review-', 'convergence-package-review-'),
                ('objective-scalar-final-upload-scan-', 'source-slices-final-upload-scan-'),
                ('ranker-objective-scalar', 'ranker-source-slices'),
                ('fae2e38dc882929edb2bcd2226560f0da3dfcd9e', 'd6b6e333f3b1bcfe9028a8ca5ac3be6b12256e8a'),
                ('prior source-slice bundle is referenced and preserved', 'prior convergence bundle is referenced and preserved'),
            )
            for new, old in replacements:
                node.value = node.value.replace(new, old)
        elif self.census and type(node.value) is int:
            node.value = {329: 274, 331: 276}.get(node.value, node.value)
        return node


def normalized(node, census=False):
    return ast.dump(Normalize(census).visit(copy.deepcopy(node)), include_attributes=False)


def funcs(tree):
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def top_level_inert(tree):
    allowed_imports = {'argparse', 'hashlib', 'json', 'os', 'pathlib', 're', 'stat', 'subprocess', 'tarfile',
                       'time', 'types', 'tempfile', 'collections', 'datetime', 'urllib.request'}
    for node in tree.body:
        if isinstance(node, ast.Import):
            need(all(alias.name in allowed_imports for alias in node.names), 'standard library imports only')
        elif isinstance(node, ast.ImportFrom):
            need(node.module in allowed_imports, 'standard library from-import only')
        elif isinstance(node, ast.If):
            need(normalized(node.test) == normalized(ast.parse("__name__ == '__main__'", mode='eval').body), 'sole main guard')
        elif isinstance(node, ast.Expr):
            need(isinstance(node.value, ast.Constant) and type(node.value.value) is str, 'module docstring only')
        elif isinstance(node, ast.Assign):
            for call in (child for child in ast.walk(node.value) if isinstance(child, ast.Call)):
                need((isinstance(call.func, ast.Name) and call.func.id == 'Path') or
                     (isinstance(call.func, ast.Attribute) and call.func.attr == 'resolve'), 'only path setup at module top')
        else:
            need(isinstance(node, ast.FunctionDef), 'inert definitions at top level')


def fragments(text, required):
    for value in required:
        need(value in text, 'required source binding: ' + value)


def main():
    need(__debug__, 'optimized reviewer refused')
    need(not (HERE / 'review-receipt.json').exists(), 'fresh independent source receipt')
    raw = {path: read(path, expected)[0] for path, expected in PINS.items()}
    helper_rows = []
    for path, expected_sha in HELPERS.items():
        _, row = read(path)
        need(row['sha256'] == expected_sha, 'unchanged qualified helper byte pin')
        helper_rows.append(row)
    current = [path for path in PINS if path.parent in (S, R)]
    trees = {path: ast.parse(raw[path], filename=str(path)) for path in PINS if path.suffix == '.py'}
    for path in current:
        if path.suffix == '.py':
            top_level_inert(trees[path])
    for path in (S / 'build_package.py', S / 'review_package.py', S / 'freeze_final_plan_01.py'):
        values = constants(trees[path])
        need(values['PROFILE'] == EXPECTED_PROFILE, 'unchanged full publication profile')
        if 'NATIVE_BOUNDS' in values:
            need(values['NATIVE_BOUNDS'] == EXPECTED_NATIVE, 'unchanged native bounds')
    inherited = {}
    for old_path, new_path, changed in (
        (OLD_S / 'build_package.py', S / 'build_package.py', {'check_plan'}),
        (OLD_S / 'freeze_inputs.py', S / 'freeze_inputs.py', set()),
        (OLD_S / 'review_package.py', S / 'review_package.py', set()),
        (OLD_R / 'prepare_invocation_01.py', R / 'prepare_invocation_01.py', {'main'}),
        (OLD_R / 'prepare_hf_plan_02.py', R / 'prepare_hf_plan_01.py',
         {'main', 'read', 'read_bound', 'need', 'pin', 'load_bound', 'save', 'encoded'}),
    ):
        old_f, new_f = funcs(trees[old_path]), funcs(trees[new_path])
        expected_new = {'count'} if new_path.name == 'prepare_hf_plan_01.py' else set()
        expected_removed = {'load'} if new_path.name == 'prepare_hf_plan_01.py' else set()
        need(set(new_f) - set(old_f) == expected_new and set(old_f) - set(new_f) == expected_removed, 'expected helper interface only')
        unchanged = []
        for name in old_f:
            if name not in changed and name not in expected_removed:
                need(normalized(old_f[name]) == normalized(new_f[name]), 'unchanged inherited function: ' + name)
                unchanged.append(name)
        inherited[str(new_path)] = {'unchanged_functions_after_scope_string_normalization': unchanged,
                                    'substantive_functions_reviewed_manually': sorted(changed),
                                    'added_helpers': sorted(expected_new), 'removed_unused_helpers': sorted(expected_removed)}
    for name in ('scan_final_upload_01.py', 'review_hf_readback_01.py'):
        old_tree, new_tree = copy.deepcopy(trees[OLD_R / name]), copy.deepcopy(trees[R / name])
        for tree in (old_tree, new_tree):
            if tree.body and isinstance(tree.body[0], ast.Expr):
                tree.body.pop(0)
        need(normalized(old_tree, name == 'review_hf_readback_01.py') ==
             normalized(new_tree, name == 'review_hf_readback_01.py'), 'complete inherited scanner/readback AST after scope and census normalization')
    freeze_text = raw[S / 'freeze_final_plan_01.py'].decode()
    expected_peers = {
        'candidate_source': ('ranker-objective-scalar-independent-source-review@1', 'passed_source_only', 'outstanding_source_issues'),
        'prepared_native_inputs': ('ranker-objective-scalar-prepared-input-source-review@1', 'passed_file_only', 'outstanding_source_issues'),
        'semantic_native': ('ranker-objective-scalar-independent-semantic-native-review@1', 'passed_file_only_actual_receipt_review', 'outstanding_review_issues'),
        'metadata_source_initial': ('ranker-objective-scalar-metadata-independent-source-review@1', 'passed_source_only', 'outstanding_source_issues'),
        'metadata_builder_patch': ('ranker-objective-scalar-metadata-builder-patch-independent-source-review@1', 'passed_source_only', 'outstanding_source_issues'),
        'publication_source': ('ranker-objective-scalar-publication-independent-source-review@1', 'passed_source_only', 'outstanding_source_issues'),
    }
    need(constants(trees[S / 'freeze_final_plan_01.py'])['PEERS'] == expected_peers, 'fixed required peer role/schema/status/issue mappings')
    fragments(freeze_text, ("set(PEERS)<={peer['role'] for peer in peers}",
        "len({peer['receipt']['path'] for peer in peers})==len(peers)",
        "(body['schema'],peer['expected_status'],peer['issue_field'])==PEERS[peer['role']]",
        "before==sorted([*seal['files'],request['file_seal']],key=lambda row:os.fsencode(row['path']))",
        "qualified['producer']==request['closure_producer']", "all(row==peer_bindings.get(row['path']) for row in qualified['independent_reviews'])",
        "census(Q)==before and census(P6)==source_plan", "binding==row,'capture source drift'",
        "'byte_exact_clone':True", "'old_HF_bundle_reuploaded':False"))
    invoke_text = raw[R / 'prepare_invocation_01.py'].decode()
    fragments(invoke_text, ("closed['plan']==plan_pin and closed['final_selection']==selection_pin",
        "review['fixed_inputs']=={'closed':closure,'plan':plan_pin,'selection':selection_pin,'guards':guard_pin}",
        "review['reviewer']==pin(INPUT_REVIEW/'review_inputs_01.py')", "review[key] is False",
        "guard_pin['sha256']==a.expected_guards_sha256", "all(pin(path)==binding for path,binding in list(HELD.items()))",
        "wall_seconds':900 if a.phase=='hf-publication' else 180"))
    hf_text = raw[R / 'prepare_hf_plan_01.py'].decode()
    fragments(hf_text, ("count(baseline,'complete_regular_file_count',331)", "count(baseline,'prior_immutable_files',329)",
        "manifest['closed_inputs']==frozen_pin and manifest['plan']==final_plan_pin and manifest['final_selection']==selection_pin",
        "review['package_closure']==package_closed_pin", "final_plan['documents']['file_seal']==seal_pin",
        "('qualified_theorem_queries',14)", "('pure_test_cases',98)", "('metadata_payloads',4458)",
        "('unchanged_vector_rows',375)", "('unchanged_contract_rows',2)", "'host_parser_correctness_theorem_proved'",
        "'computed_gradient_source_equivalence_proved'", "'whole_codebase_IR_semantic_preservation_proved'",
        "read_bound(R/'prior-HF-README-01.md',prior_by_name['prior-HF-README-01.md'])",
        "all(pin(path)==binding for path,binding in list(HELD.items()))"))
    prior_review_path = W / 'maintenance/ranker-source-slices-publication-source-review-20261005-01/review-receipt.json'
    prior = json.loads(raw[prior_review_path])
    need(prior['status'].startswith('passed'), 'prior sealed source review passed')
    own = read(Path(__file__).resolve())[1]
    need(all(read(path, (row['bytes'], row['sha256']))[1] == row for path, row in list(HELD.items())), 'final whole source and helper recheck')
    result = {'schema': 'ranker-objective-scalar-publication-independent-source-review@1', 'status': 'passed_source_only',
        'producer': own, 'reviewed_sources': [HELD[str(path)] for path in current],
        'prior_source_pins': [HELD[str(path)] for path in PINS if path.parent in (OLD_S, OLD_R)],
        'prior_independent_source_review': HELD[str(prior_review_path)], 'qualified_helper_pins': helper_rows,
        'source_AST_node_counts': {str(path): sum(1 for _ in ast.walk(trees[path])) for path in current if path.suffix == '.py'},
        'inherited_function_review': inherited, 'publication_profile': EXPECTED_PROFILE, 'native_bounds': EXPECTED_NATIVE,
        'narrow_scope': 'Partial exact-real scalar compiler and emitted stable-loss/sign-split-factor leaves; fourteen genuine accepted native queries in two modules. Host/Python/Float/full objective/gradient/training/full IR/global convergence remain open.',
        'expected_final_qualification_facts': {'native_attempts': 2, 'accepted_modules': 2, 'qualified_queries': 14,
            'pure_test_cases': 98, 'metadata_payloads': 4458, 'metadata_families': 32, 'prior_canonical_prefix_payloads': 4440,
            'unchanged_vectors': 375, 'unchanged_contracts': 2, 'new_contracts': 0, 'cache_admissions': 0},
        'HF_expected_parent': 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e', 'prior_public_regular_files': 331,
        'prior_public_immutable_files': 329, 'HF_namespace': 'releases/20261004-terminal-codebase-ir-evidence-v1/successor-ranker-objective-scalar-v1',
        'only_mutable_remote_paths': ['README.md', 'releases/20261004-terminal-codebase-ir-evidence-v1/publication-status.json'],
        'complete_seal_census_plus_self_required_before_after': True, 'failed_attempts_and_zero_byte_locks_retained': True,
        'complete_objects_and_chunks_retained': True, 'prior_large_archive_reupload': False,
        'raw_external_dependency_bodies_published': False, 'source_and_artifact_quiet_required': True,
        'same_buffer_external_pins_and_final_HELD_rechecks': True,
        'closed_inputs_join_plan_selection_producer': True, 'input_review_joins_closed_plan_selection_guards_reviewer': True,
        'required_peer_roles_use_fixed_schema_status_issue_fields': True, 'peer_receipt_paths_unique': True,
        'first_decoded_tar_member_readback_profile_unchanged': True,
        'qualified_nested_container_complete_PEM_cached_credential_veto_unchanged': True,
        'duplicate_decoder_or_container_exemption_added': False, 'universal_secret_free_claim': False,
        'inherited_public_HTTP_JSON_max_bytes': 4194304, 'inherited_local_readback_JSON_max_bytes': 33554432,
        'pagination_refused_for_whole_remote_tree': True, 'prior_remote_blob_and_LFS_identities_preserved': True,
        'reviewed_target_imports_or_execution': False, 'archive_codec_classifier_native_model_metadata_git_remote_jobs_run': False,
        'SDK_log_or_cached_credential_bodies_read_by_reviewer': False, 'final_seal_or_selection_created_by_reviewer': False,
        'actual_future_package_scan_publication_or_remote_state_reviewed_here': False,
        'outstanding_source_issues': [], 'source_review_limitations': ['This gate binds source bytes; final seal/review/population/request descriptors need a separate actual input review.',
            'The final-input reviewer source is a separate successor helper and is not included in this nine-file source receipt.',
            'No target job was run. The later freezer, classifier, codec, wrapper and publisher must independently enforce all recorded pins and caps.'],
        'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None,
        'atomic_whole_source_snapshot_claimed': False, 'historical_execution_origin_proved': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
    with (HERE / 'review-receipt.json').open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'review': read(HERE / 'review-receipt.json')[1], 'sources': len(current)}))


if __name__ == '__main__':
    main()
