"""Record an independent source-only review of the pinned Git helper successor.

This program reads source/JSON only. It does not import reviewed targets or use
Git, HTTP, classifiers, codecs, native checkers, tests, model or metadata jobs.
The substantive review is recorded explicitly below; assertions bind it to the
exact final source buffers and inspect their static interfaces.
"""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
ROOT = W / 'maintenance/ranker-objective-scalar-git-helper-source-20261005-01'
OUT = W / 'maintenance/ranker-objective-scalar-git-helper-review-20261005-01'
EXPECTED = {
    'prepare_compact_selection_03.py': (21399, 'f309a55c855520067152df4503217a6cac7a2da15a2ac26d4dccfe480ef75f3e'),
    'prepare_safe_receipts_01.py': (13224, '78cc14a0781bd7194bd925c9bfdf06e5f051b51ced2fbafd77f8cf728cda5f0e'),
    'stage_verified_increment_01.py': (18467, '17af06863f57aaf324f95787d6983f297fd09ae920d597f5cddf638854a6a98d'),
    'publish_git_increment_01.py': (22428, '9bb95c4410a884f54d5f35ef6d1d587ac54c7be58264f368b84dfa0d616e8525'),
    'publication-policy.json': (3103, 'e74a2bc5fbd2c3c40f94d4e5460b675c49b786ac1e672eded0b5fc2738c20425'),
    'SOURCE_API.md': (5066, 'cfd5ced3fef64f9f39d12995a138305f57f16a0340f7390ed5502b9a362c4aa6'),
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and 0 <= first.st_size <= 1024**2, 'bounded regular review source')
        pieces, size = [], 0
        while block := os.read(fd, 65536):
            size += len(block)
            need(size <= first.st_size, 'review source grew')
            pieces.append(block)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        sig = lambda value: tuple(getattr(value, key) for key in keys)
        need(sig(first) == sig(os.fstat(fd)) == sig(path.lstat()) and size == first.st_size, 'review source changed')
        return b''.join(pieces)
    finally:
        os.close(fd)


def pin(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def function(tree, name):
    rows = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    need(len(rows) == 1, 'unique reviewed function')
    return rows[0]


def calls(tree, name):
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name]


def main():
    need(__debug__, 'optimized review refused')
    need(Path(__file__).resolve().parent == OUT and not (OUT/'review-receipt.json').exists(), 'fresh owned review namespace')
    held, trees, reviewed = {}, {}, []
    for name, (size, digest) in EXPECTED.items():
        path = ROOT/name; raw = read(path)
        need((len(raw), hashlib.sha256(raw).hexdigest()) == (size, digest), 'final helper source pin differs')
        held[path] = raw; reviewed.append(pin(path, raw))
        if path.suffix == '.py':
            tree = ast.parse(raw, filename=str(path)); trees[name] = tree
            need(all(not isinstance(node, ast.ImportFrom) or node.level == 0 for node in ast.walk(tree)), 'no project-relative import')
            for node in calls(tree, 'need'):
                first = node.args[0]
                need(not isinstance(first, ast.Name) or first.id == '__debug__', 'strict Boolean API has no bare container guard')
            for node in ast.walk(tree):
                if isinstance(node, ast.BoolOp) and isinstance(node.values[-1], ast.Call):
                    end = node.values[-1]
                    need(not (isinstance(end.func, ast.Attribute) and isinstance(end.func.value, ast.Name) and
                              end.func.value.id == 're' and end.func.attr == 'fullmatch'), 'regex Match never used as final Boolean operand')
    gate = [ast.dump(function(tree, 'validate_HF_gate'), include_attributes=False) for tree in trees.values()]
    need(len(set(gate)) == 1, 'one exact HF gate shared by all four helpers')
    policy = json.loads(held[ROOT/'publication-policy.json'])
    need(policy['schema'] == 'ranker-objective-scalar-private-Git-publication-policy@1' and
         policy['expected_prior_HF_commit'] == 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e' and
         policy['expected_prior_immutable_HF_files'] == 329 and policy['Q5_sealed_regular_files'] == 276 and
         policy['Q5_sealed_regular_bytes'] == 78794802 and policy['native_accepted_modules'] == 2 and
         policy['native_accepted_theorem_queries'] == 14 and policy['metadata_payloads'] == 4458 and
         policy['metadata_families'] == 32 and policy['prior_payload_prefixes_preserved'] == 4440 and
         policy['vectors_unchanged'] == 375 and policy['unchanged_mathematical_projection_domains'] == 2,
         'exact narrow observed qualification policy')
    for name in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation',
                 'force_push_allowed', 'rebase_allowed', 'python_ranker_source_equivalence_proved',
                 'host_parser_correctness_theorem_proved', 'binary64_error_bound_proved',
                 'full_objective_semantics_proved', 'full_preparation_semantics_proved',
                 'full_training_semantics_proved', 'whole_IR_semantic_preservation_proved',
                 'global_autoencoder_convergence_proved'):
        need(policy[name] is False, 'authority and broad proof frontiers remain false')
    need(policy['full_task_satisfaction'] == 'unknown' and policy['official_benchmark_score'] is None, 'task frontier remains open')
    selector = held[ROOT/'prepare_compact_selection_03.py'].decode()
    safe = held[ROOT/'prepare_safe_receipts_01.py'].decode()
    stage = held[ROOT/'stage_verified_increment_01.py'].decode()
    publisher = held[ROOT/'publish_git_increment_01.py'].decode()
    need(selector.index('gate_documents = validate_HF_gate(read, gate)') < selector.index('before = guards()'), 'HF gate before Git reads')
    for token in ('original_planning_extractor_not_selected_for_Git', 'already_published_unchanged',
                  'byte_exact_clone', 'final selected source/captured/original planning input changed',
                  "need(len(selected) > 0", "'stage_calls': 0, 'commit_calls': 0, 'push_calls': 0"):
        need(token in selector, 'complete selected/omitted source partition and preserved parent')
    for token in ('closed_exact_frozen_compact_candidate_base', 'safe_selector_request', "receipts['base_selection'] = base_pin",
                  'selected_file_count', 'selected_file_bytes', 'git-final-input-review', 'census(request'):
        need(token in safe, 'safe-selector exact request/base/census interface')
    for token in ('f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036',
                  'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8',
                  'Budget(seconds=120', 'decoded_bytes=16*1024**2', 'members=1, depth=0',
                  'complete cached-credential/PEM classifier veto', 'staged blob differs from scanned source',
                  'all nine fresh parent Git links must remain unchanged'):
        need(token in stage, 'pinned complete classifier and bounded full staged readback')
    need(publisher.index("peer['schema']") < publisher.index("git('-c', 'core.hooksPath=/dev/null', 'commit'"), 'external peer before commit')
    need(publisher.index("write_new('commit-observed-01.json'") < publisher.index("'push', 'origin'"), 'durable observed commit before push')
    for token in ('poststage peer must bind this exact final stage and all three actual HF gate receipts',
                  'remote parent advanced before push', 'complete new population changed during remote readback',
                  'failed_retained_without_force_or_rebase', "'force_push_calls': 0", 'os.fsync(fd)'):
        need(token in publisher, 'normal publication, complete readback and retained failure')
    for path, raw in held.items():
        need(read(path) == raw, 'reviewed helper source changed')
    own = read(Path(__file__).resolve())
    result = {
        'schema': 'ranker-objective-scalar-Git-helper-independent-source-review@1', 'status': 'passed_source_only',
        'findings': [], 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': pin(Path(__file__).resolve(), own), 'reviewed_sources': reviewed,
        'review_method': 'Independent full source and API reading, AST parse/static interface inspection; reviewed targets never imported or executed.',
        'source_findings': {
            'actual_HF_gate_before_candidate_Git_reads': True,
            'one_same_buffer_HF_gate_shared_all_four_helpers': True,
            'closed_frozen_Q5_seal_plan_selection_joins': True,
            'complete_full_HF_denominator_selected_or_omitted': True,
            'raw_binary_chunk_DB_log_lock_environment_metadata_payload_cache_private_inputs_excluded_from_Git': True,
            'P6_extractor_omitted_P7_exact_frozen_copies_unqualified': True,
            'entire_fresh_parent_and_all_nine_links_preserved': True,
            'safe_receipts_full_explicit_root_census_request_base_joins': True,
            'fixed_classifier_helpers_full_PEM_cached_credential_veto_no_codec': True,
            'exact_candidate_base_receipts_external_SHA_inputs': True,
            'complete_staged_and_committed_remote_blob_readbacks': True,
            'exact_external_final_stage_and_HF_peer_before_commit': True,
            'durable_observed_commit_before_push_and_retained_failures': True,
            'no_force_push_or_rebase_and_remote_parent_advance_refusal': True,
            'original_root_and_child_HEAD_index_guard_checks': True,
            'strict_Boolean_namespace_and_nonempty_selection_refusals_corrected_in_new_selector03': True,
        },
        'source_only_not_actual_execution_or_publication_gate': True,
        'reviewed_target_imports': 0, 'Git_HTTP_classifier_codec_native_model_test_metadata_jobs': 0,
        'prior_failed_selector01_02_retained_unchanged': True,
        'qualified_scope': 'Partial exact-real scalar and emitted stable-loss/sign-split-factor leaf proofs: two native modules,14queries,98purecases,4458metadata,4440priorprefix,375vectors,2unchangedcontracts.',
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False,
        'limitations': ['This receipt reviews sources; actual candidate, exact safe selector request, classifier stage, final external peer, normal Git commit/push and remote readback remain later separately pinned gates.',
                        'Reviewed old selector failures were fail-closed strict-Boolean interface mistakes; no successful target execution is inferred here.'],
    }
    target = OUT/'review-receipt.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'status': result['status'], 'reviewer': result['reviewer'], 'receipt': pin(target, read(target))}))


if __name__ == '__main__':
    main()
