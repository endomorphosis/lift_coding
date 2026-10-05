"""Join externally pinned actual receipts into a file-only publication ledger."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parent
WORKSPACE = Path('/home/barberb/lift_coding')
PARENT = 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
HELD = {}
AUTHORITY = {key: False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read_pin(path):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular document required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and first.st_size <= 32 * 1024**2, 'bounded parsed document required')
        blocks, total = [], 0
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= 32 * 1024**2, 'parsed input grew')
            blocks.append(block)
        signature = lambda info: tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and total == first.st_size, 'document changed during read')
        raw = b''.join(blocks)
    finally:
        os.close(fd)
    observed = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    need(str(path) not in HELD or HELD[str(path)] == observed, 'previously parsed input changed')
    HELD[str(path)] = observed
    return raw, observed


def document(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'exact descriptor required')
    raw, actual = read_pin(row['path'])
    need(actual == row, 'same-buffer document pin differs')
    return json.loads(raw)


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    return read_pin(path)[1]


def get_plan(schema):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    need(__debug__ is True and re.fullmatch('[0-9a-f]{64}', args.plan_sha256) is not None, 'unoptimized externally pinned plan required')
    raw, pin = read_pin(args.plan)
    need(pin['sha256'] == args.plan_sha256, 'external plan pin differs')
    plan = json.loads(raw)
    need(plan['schema'] == schema, 'exact plan schema required')
    return plan, pin


def main():
    plan, plan_pin = get_plan('ranker-objective-scalar-release-ledger-plan@1')
    need(set(plan) == {'schema', 'hf_commit', 'hf_parent', 'selected_files', 'selected_bytes', 'input_receipts'}, 'closed ledger plan required')
    commit = plan['hf_commit']
    need(type(commit) is str and re.fullmatch('[0-9a-f]{40}', commit) is not None and plan['hf_parent'] == PARENT, 'actual successor commit required')
    files, total = plan['selected_files'], plan['selected_bytes']
    need(type(files) is int and 0 < files <= 100 and type(total) is int and 0 < total <= 256 * 1024**2, 'exact bounded upload population')
    pins = plan['input_receipts']
    need(set(pins) == {'qualification', 'seal', 'frozen_inputs', 'package_review', 'hf_plan', 'final_scan', 'hf_closed', 'public_readback'}, 'complete actual receipt set')
    docs = {name: document(row) for name, row in pins.items()}
    q, seal = docs['qualification'], docs['seal']
    need(q['schema'] == 'ranker-objective-scalar-closed-qualification@1' and q['status'] == 'passed' and seal['schema'] == 'ranker-objective-scalar-file-only-seal@1' and seal['review'] == pins['qualification'], 'qualified seal/review joins differ')
    for key, value in (('qualified_theorem_queries', 14), ('qualified_positive_native_lean_checks', 2), ('pure_test_cases', 98), ('metadata_payloads', 4458), ('metadata_family_count', 32), ('additive_metadata_payloads', 18), ('unchanged_vector_rows', 375), ('unchanged_contract_rows', 2)):
        need(type(q[key]) is int and q[key] == value, 'qualified narrow count differs: ' + key)
    need(all(q[key] is False for key in AUTHORITY) and q['python_ranker_source_equivalence_proved'] is False and q['global_autoencoder_convergence_proved'] is False and q['full_task_satisfaction'] == 'unknown' and q['all32_governing_RPI_exits'] == 'OPEN', 'open scope/authority differs')
    need(seal['regular_file_count'] == 276 and seal['regular_file_bytes'] == 78794802 and len(seal['files']) == 276 and sum(row['bytes'] for row in seal['files']) == 78794802, 'complete qualified seal population differs')
    need(all(q[key] is True for key in ('prior4440_payloads_preserved_exactly_as_prefixes', 'vectors_payloads_unchanged', 'contracts_payloads_unchanged', 'prior_original_exact_real_model_weights_and_objective_convergence_preserved')), 'preserved payload/model qualification flags differ')
    hf, public, upload, scan, package = [docs[key] for key in ('hf_closed', 'public_readback', 'hf_plan', 'final_scan', 'package_review')]
    need(hf['schema'] == 'terminal-ir-HF-successor-publication@1' and hf['status'] == 'PUBLISHED_AND_VERIFIED' and hf['commit'] == commit and hf['parent'] == PARENT and hf['remote_readback_verified'] is True and hf['plan'] == pins['hf_plan'] and hf['files'] == files and hf['selected_bytes'] == total and hf['prior_immutable_remote_files_preserved'] == 329, 'actual HF closure differs')
    need(public['schema'] == 'ranker-objective-scalar-public-HF-readback-join@1' and public['status'] == 'passed' and public['commit'] == commit and public['parent'] == PARENT and public['fresh_public_main_matches_commit'] is True and public['fresh_public_main_after_tree_matches_commit'] is True and public['all_selected_local_pins_rechecked'] is True and public['selected_files'] == files and public['selected_bytes'] == total and public['prior_immutable_files_preserved'] == 329 and public['committed_total_regular_files'] == 331 + files - 2, 'fresh public readback differs')
    need(upload['schema'] == 'terminal-ir-successor-evidence-publication-plan@1' and scan['schema'] == 'ranker-objective-scalar-exact-final-upload-scan@1' and upload['expected_parent_commit'] == PARENT and len(upload['files']) == files and sum(row['local']['bytes'] for row in upload['files']) == total and scan['plan'] == pins['hf_plan'] and scan['status'] == 'passed' and scan['candidate_hits'] == 0 and scan['selected_files'] == files and scan['selected_bytes'] == total, 'upload population/scan joins differ')
    frozen = docs['frozen_inputs']
    need(frozen['schema'] == 'ranker-objective-scalar-publication-closed-inputs@1' and package['schema'] == 'ranker-objective-scalar-full-decoded-member-file-only-review@1' and package['status'] == 'passed' and package['closed_inputs'] == pins['frozen_inputs'] and package['native_attempt_denominator_verified'] == 2, 'package/input closure join differs')
    final_plan, selection, manifest, package_closed = [document(row) for row in (frozen['plan'], frozen['final_selection'], package['manifest'], package['package_closure'])]
    need(final_plan['schema'] == 'ranker-objective-scalar-publication-plan@1' and final_plan['status'] == 'frozen_final_plan' and final_plan['documents']['file_seal'] == pins['seal'] and final_plan['documents']['qualified_review'] == pins['qualification'] and selection['schema'] == 'ranker-objective-scalar-publication-final-selection@1', 'final plan/selection qualification joins differ')
    need(manifest['schema'] == 'ranker-objective-scalar-frozen-evidence-package@1' and manifest['closed_inputs'] == pins['frozen_inputs'] and manifest['plan'] == frozen['plan'] and manifest['final_selection'] == frozen['final_selection'] and manifest['file_count'] == len(selection['files']) and manifest['original_file_bytes'] == sum(row['bytes'] for row in selection['files']), 'complete package manifest selection joins differ')
    need(package_closed['schema'] == 'ranker-objective-scalar-local-package-attempt@1' and package_closed['status'] == 'passed_local_frozen_package' and package_closed['manifest'] == package['manifest'] and package_closed['candidate_hits'] == package_closed['source_drift_count'] == 0 and package_closed['cleanup_errors'] == [], 'package closure differs')
    need(package['sealed_file_count_rehashed'] == manifest['sealed_regular_file_count'] == 276 and package['sealed_file_bytes_rehashed'] == manifest['sealed_regular_file_bytes'] == 78794802 and package['selected_files_verified_before_after'] == package['decoded_members_verified'] == len(selection['files']), 'complete decoded/selected census differs')
    need(all(read_pin(row['path'])[1] == row for row in list(HELD.values())), 'held receipt changed before ledger')
    result = {'schema': 'ranker-objective-scalar-release-publication-ledger@1', 'status': 'HF_PUBLISHED_AND_VERIFIED_GITHUB_PUBLICATION_PENDING', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': read_pin(Path(__file__).resolve())[1], 'plan': plan_pin, 'input_receipts': pins,
        'huggingface': {'repo_id': 'Publicus/codebase-ir-proof-index', 'commit': commit, 'parent': PARENT, 'url': 'https://huggingface.co/datasets/Publicus/codebase-ir-proof-index/commit/' + commit, 'status': 'PUBLISHED_AND_VERIFIED', 'selected_files': files, 'selected_bytes': total, 'prior_immutable_files_preserved': 329, 'committed_total_regular_files': 331 + files - 2, 'public_readback': pins['public_readback']},
        'github': {'remote_target': 'origin/main', 'status': 'pending_separate_fresh_checkout_commit_and_remote_readback', 'commit': None},
        'qualified_scope': {'numeric_backend': 'partial_exact_real', 'source_slices': ['stable loss scalar leaf', 'sign-split factor scalar leaf'], 'qualified_native_modules': 2, 'qualified_theorem_queries': 14, 'pure_test_cases': 98, 'metadata_payloads': 4458, 'metadata_family_count': 32, 'additive_metadata_payloads': 18, 'prior4440_payloads_preserved': True, 'prior375_vectors_preserved': True, 'projection_domain_contracts_unchanged': 2, 'prior_original_exact_real_model_convergence_preserved': True},
        'open_obligations': ['host parser correctness', 'containers/means/regularization and computed gradient source projection', 'CPython math.fsum/binary64/libm semantics', 'feature preparation and full training loop translation', 'whole codebase IR semantic preservation', 'general autoencoder convergence', 'full Terminal Bench task satisfaction'],
        'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None, 'full_task_satisfaction': 'unknown', 'raw_SDK_logs_read': False, 'model_training_calls': 0, 'prover_calls': 0, 'remote_mutations': 0, **AUTHORITY}
    print(json.dumps({'status': result['status'], 'ledger': save(ROOT / 'release-publication-ledger-01.json', result)}))


if __name__ == '__main__':
    main()
