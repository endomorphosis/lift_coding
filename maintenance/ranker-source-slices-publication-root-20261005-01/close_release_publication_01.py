"""Join pinned qualification and public HF receipts into a safe release ledger.

This local, file-only closure grants no proof, execution, completion, or planner
authority. Git publication remains pending until its separate remote closure.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
COMMIT = 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
PARENT = 'd6b6e333f3b1bcfe9028a8ca5ac3be6b12256e8a'
INPUTS = {
    'qualification': ('qualification/codebase_ir/ranker-source-semantics-20261005-01/qualified-review-01.json', '39c403afd19b5972a28281813c23fdd13eddea1c32fa63747b4dd3258b07e550'),
    'seal': ('qualification/codebase_ir/ranker-source-semantics-20261005-01/file-only-seal-01.json', '21a459ac9bfcf399132943708e32445c93cb66fa0fab8fb2878beeb01dcf8b65'),
    'frozen_inputs': ('maintenance/ranker-source-slices-publication-20261005-01/closed-inputs.json', '4a22f424af31259af6f9914a98452ae365f8d5da2354b3b4c5cc34c2fe00e2aa'),
    'package_review': ('maintenance/ranker-source-slices-publication-20261005-01/package-review-01.json', '11f6a1ddc624cb35cb6b7d398f3d68b0f6983b9f447e287148e53f3b0b4d7b4b'),
    'hf_plan': ('maintenance/ranker-source-slices-publication-root-20261005-01/hf-plan-01.json', 'f063bb98cbc6e97137be63af7cc912484a503f4a366223b0fe31b6fa6637381f'),
    'final_scan': ('maintenance/ranker-source-slices-publication-root-20261005-01/final-upload-scan-01.json', 'a5aa2abe3d937614db19687ccde76fd92b837e0db64a24414455e6f70e446d59'),
    'hf_closed': ('maintenance/ranker-source-slices-publication-root-20261005-01/hf-publication-01/closed.json', '25893c408afc28cb6f14ee67a335488271c347b7d7c0a5e2153ca1f6a71edef0'),
    'public_readback': ('maintenance/ranker-source-slices-publication-root-20261005-01/hf-public-readback-01.json', '59093213bb8558b7087d9a17a020ddda46b7036e4dee98d1a2dee5581badec66'),
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read_pin(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2, 'bounded regular input required')
        blocks, size = [], 0
        while block := os.read(fd, 1024**2):
            size += len(block)
            need(size <= 32 * 1024**2, 'input exceeded read cap')
            blocks.append(block)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda info: tuple(getattr(info, key) for key in keys)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and size == before.st_size, 'input changed during read')
        raw = b''.join(blocks)
        return raw, {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    finally:
        os.close(fd)


def main():
    docs, pins = {}, {}
    for name, (relative, expected) in INPUTS.items():
        raw, descriptor = read_pin(WORKSPACE / relative)
        need(descriptor['sha256'] == expected, 'independently expected input digest differs: ' + name)
        docs[name], pins[name] = json.loads(raw), descriptor
    q, sealed = docs['qualification'], docs['seal']
    closed, public = docs['hf_closed'], docs['public_readback']
    need(q.get('status') == 'passed' and sealed['review'] == pins['qualification'], 'qualified review/seal join required')
    need(q['qualified_theorem_queries'] == 21 and q['qualified_positive_native_lean_checks'] == 2 and
         q['pure_test_cases_per_compiler_version'] == 137 and q['metadata_payloads'] == 4440 and q['metadata_family_count'] == 32,
         'qualified scope differs')
    need(all(q.get(key) is False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')) and
         q['python_ranker_source_equivalence_proved'] is False and q['global_autoencoder_convergence_proved'] is False and
         q['full_task_satisfaction'] == 'unknown', 'authority and open source/model boundary differs')
    need(closed.get('status') == 'PUBLISHED_AND_VERIFIED' and closed['commit'] == COMMIT and closed['parent'] == PARENT and
         closed['remote_readback_verified'] is True and closed['plan'] == pins['hf_plan'] and closed['files'] == 57 and
         closed['selected_bytes'] == 15799007 and closed['prior_immutable_remote_files_preserved'] == 274, 'actual HF closure differs')
    need(public.get('status') == 'passed' and public['commit'] == COMMIT and public['parent'] == PARENT and
         public['fresh_public_main_matches_commit'] is True and public['fresh_public_main_after_tree_matches_commit'] is True and
         public['all_selected_local_pins_rechecked'] is True and public['selected_files'] == 57 and public['selected_bytes'] == 15799007 and
         public['prior_immutable_files_preserved'] == 274 and public['committed_total_regular_files'] == 331 and
         public['verification_methods'] == {'committed_LFS_SHA256_and_size': 8, 'downloaded_small_file_SHA256_and_size': 49},
         'complete fresh public readback differs')
    for name, descriptor in pins.items():
        need(read_pin(Path(descriptor['path']))[1] == descriptor, 'input changed after parsing: ' + name)
    ledger = {
        'schema': 'ranker-source-slices-release-publication-ledger@1',
        'status': 'HF_PUBLISHED_AND_VERIFIED_GITHUB_PUBLICATION_PENDING',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'producer': read_pin(Path(__file__).resolve())[1],
        'input_receipts': pins,
        'huggingface': {
            'repo_id': 'Publicus/codebase-ir-proof-index', 'commit': COMMIT, 'parent': PARENT,
            'url': 'https://huggingface.co/datasets/Publicus/codebase-ir-proof-index/commit/' + COMMIT,
            'status': 'PUBLISHED_AND_VERIFIED', 'selected_files': 57, 'selected_bytes': 15799007,
            'prior_immutable_files_preserved': 274, 'committed_total_regular_files': 331,
            'public_readback': pins['public_readback'],
        },
        'github': {'remote_target': 'origin/main', 'status': 'pending_separate_fresh_checkout_commit_and_remote_readback', 'commit': None},
        'qualified_scope': {
            'source_slices': ['_dot product generator', 'train weight update expression with supplied mathematical gradient'],
            'numeric_backend': 'exact_real', 'qualified_native_modules': 2, 'qualified_theorem_queries': 21,
            'pure_test_cases_per_compiler_version': 137, 'metadata_payloads': 4440, 'metadata_family_count': 32,
            'additive_metadata_payloads': 23, 'prior4417_payloads_preserved': True, 'prior375_vectors_preserved': True,
            'projection_domain_contracts': 2, 'projection_domains_runtime_enforced': False,
            'prior_original_exact_real_model_convergence_preserved': True,
            'supplied_mathematical_gradient_update_joins_original_exact_real_step': True,
        },
        'open_obligations': ['host parser correctness', 'CPython math.fsum and binary64 semantics', '_objective translation and computed gradient',
                             'feature preparation and full training loop translation', 'whole codebase IR semantic preservation',
                             'general autoencoder convergence', 'full Terminal Bench task satisfaction'],
        'next_objective_IR_plan_status': 'source_only_uncompiled_unqualified',
        'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None,
        'raw_SDK_logs_read': False, 'model_training_calls': 0, 'prover_calls': 0, 'remote_mutations': 0,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False,
        'full_task_satisfaction': 'unknown',
    }
    target = ROOT / 'release-publication-ledger-01.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(ledger, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': ledger['status'], 'ledger': read_pin(target)[1]}))


if __name__ == '__main__':
    main()
