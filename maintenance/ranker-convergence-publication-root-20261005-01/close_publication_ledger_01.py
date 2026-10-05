"""Close the verified HF increment; Git's own commit closure stays external."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/barberb/lift_coding')
R = Path(__file__).resolve().parent
S = ROOT / 'maintenance/ranker-convergence-publication-20261005-01'
Q = ROOT / 'qualification/codebase_ir/ranker-real-convergence-20261005-01'
P = ROOT / 'maintenance/ranker-convergence-publication-package-20261005-01'
COMMIT = 'd6b6e333f3b1bcfe9028a8ca5ac3be6b12256e8a'
PARENT = '8b7b8c896749e0ca3884114cedbed782a88f4702'

def read(path):
    path = Path(path).absolute()
    assert path.resolve(strict=True) == path and not path.is_symlink()
    before = path.stat()
    raw = path.read_bytes()
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
    assert identity(before) == identity(path.stat()) and len(raw) == before.st_size
    return raw

def pin(path):
    path = Path(path).absolute()
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def load(path, expected_sha=None):
    raw = read(path)
    if expected_sha is not None:
        assert hashlib.sha256(raw).hexdigest() == expected_sha
    return json.loads(raw)

def git_head(cwd):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd, text=True).strip()

def main():
    if not __debug__:
        raise RuntimeError('optimized Python would disable closure gates')
    review = load(Q / 'qualified-review-01.json', 'eebf40b5de2822faef1293a62578da208b582131e44c8a1f3e0d060071b6d0e7')
    seal = load(Q / 'file-only-seal-01.json', '6ee7b5d675777e8cc9744c9072ee7f885cb8fc47a9204c1a40d9724632012648')
    selection = load(S / 'final-selection.json', '9877c6ef83bc9e554fdd12209152eb749067d47730b294e0928356cf86fc773b')
    for item in selection['files']:
        assert pin(item['path']) == {k:item[k] for k in ('path', 'bytes', 'sha256')}
    assert len(selection['files']) == 401 and sum(x['bytes'] for x in selection['files']) == 147838468
    assert seal['regular_file_count'] == 378 and seal['regular_file_bytes'] == 147093916
    guards = review['original_checkout_guards']
    for role, cwd in (('root', ROOT), ('child', ROOT / 'external/ipfs_accelerate')):
        assert git_head(cwd) == guards[role]['head']
        assert pin(guards[role]['index']['path']) == guards[role]['index']
    hf = load(R / 'hf-publication-01/closed.json', '35df9327cca8fc205507de3222ba3885a9826df6485eb98724ea464ef429b0b1')
    public = load(R / 'hf-public-readback-01.json', 'ae264df8e038e4b4e2cacde49081e1062f546f6179153c60d9d475a3ce3440fe')
    observed = load(R / 'hf-publication-01/commit-observed.json', '9f148b82f6c8732f1b06e4595f2db57e683be0e59b0a075ee9044c219312584c')
    assert hf['status'] == 'PUBLISHED_AND_VERIFIED' and hf['remote_readback_verified']
    assert hf['commit'] == public['commit'] == observed['commit'] == COMMIT
    assert hf['parent'] == public['parent'] == observed['parent'] == PARENT
    assert public['status'] == 'passed' and public['fresh_public_main_matches_commit']
    assert public['fresh_public_main_after_tree_matches_commit']
    assert public['prior_immutable_files_preserved'] == hf['prior_immutable_remote_files_preserved'] == 225
    assert public['committed_total_regular_files'] == 276 and public['all_selected_local_pins_rechecked']
    assert hf['files'] == public['selected_files'] == 51 and hf['selected_bytes'] == public['selected_bytes'] == 27316939
    receipts = [R / 'hf-plan-01.json', R / 'hf-publication-invocation-01.json',
                R / 'hf-publication-01/remote-before.json', R / 'hf-publication-01/commit-observed.json',
                R / 'hf-publication-01/verified-files.json', R / 'hf-publication-01/closed.json',
                R / 'hf-public-readback-01.json', R / 'final-upload-scan-01.json',
                S / 'package-review-01.json', P / 'closed.json', P / 'package/manifest.json']
    before = [pin(x) for x in receipts]
    phases = {}
    for name in ('package-outer-01', 'package-review-outer-01', 'package-review-outer-02',
                 'final-upload-scan-outer-01', 'hf-publication-outer-01'):
        path = R / name / 'closed.json'
        value = load(path)
        assert value['input_pins_unchanged'] and value['cleanup_errors'] == []
        expected = ('failed_phase_preserved', 1) if name == 'package-review-outer-01' else ('closed_phase', 0)
        assert (value['status'], value['returncode']) == expected
        phases[name] = {'receipt': pin(path), 'status': value['status'], 'returncode': value['returncode'],
                        'input_pins_unchanged': True, 'elapsed_seconds': value['elapsed_seconds']}
    assert [pin(x) for x in receipts] == before
    ledger = {
        'schema': 'ranker-convergence-release-publication-ledger@1',
        'status': 'closed_verified_HF_increment_Git_commit_recorded_externally',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': pin(__file__),
        'huggingface': {'repo_id': 'Publicus/codebase-ir-proof-index', 'commit': COMMIT, 'parent': PARENT,
                       'url': 'https://huggingface.co/datasets/Publicus/codebase-ir-proof-index/commit/' + COMMIT,
                       'selected_files': 51, 'selected_bytes': 27316939, 'prior_immutable_files_preserved': 225,
                       'committed_total_regular_files': 276, 'public_readback': pin(R / 'hf-public-readback-01.json'),
                       'verification_methods': public['verification_methods'], 'old_large_archives_reuploaded': False},
        'hf_publication_completed_and_verified': True,
        'github': {'repo': 'endomorphosis/lift_coding', 'required_branch': 'origin/main',
                   'prior_published_commit': '769dc97d372ae2515b71d32a380d42de069c5d1d',
                   'new_commit_and_normal_push_closure_recorded_externally': True,
                   'Git_publication_pending_at_ledger_creation': True},
        'mathematical_result': {'theorem': 'RankerRealCurvature.originalReal_model_converges',
                                'scope': 'Original four-pair, 80-coordinate convex exact-real objective and infinite gradient recurrence',
                                'unique_global_minimizer_proved': True,
                                'weights_converge_from_every_initial_real_vector': True,
                                'objective_values_converge_to_minimum': True,
                                'minimizer_or_convergence_premise_required': False,
                                'actual_native_lean_attempts': 9, 'accepted_modules': 7,
                                'accepted_theorem_query_entries': 39, 'retained_inconclusive_native_attempts': 2},
        'metadata': {'engine': 'native DuckDB/DuckLake', 'families': 32, 'payloads': 4417,
                     'prior_exact_prefix_payloads': 4378, 'additive_payloads': 39,
                     'complete_export_comparison_and_fresh_process_readback_verified': True,
                     'vectors_and_empty_contracts_unchanged': True, 'new_strict_cache_admissions': 0},
        'archive': {'manifest': pin(P / 'package/manifest.json'), 'decoded_member_review': pin(S / 'package-review-01.json'),
                    'file_seal': pin(Q / 'file-only-seal-01.json'), 'qualified_review': pin(Q / 'qualified-review-01.json'),
                    'sealed_regular_file_count': 378, 'sealed_regular_file_bytes': 147093916,
                    'complete_selected_regular_file_count': 401, 'complete_selected_regular_file_bytes': 147838468,
                    'shards': 14, 'compressed_shard_bytes': 26110063, 'typed_semantic_facts_verified': 329,
                    'raw_external_environment_dependency_bodies_published': False,
                    'native_limits_changed': False, 'publication_profile': load(S / 'closed-inputs.json')['publication_profile']},
        'publication_attempts': phases,
        'publication_review_failure_retained': 'Attempt01 decoded then refused a mismatched output path; attempt02 used the existing fixed reviewer output path and passed',
        'safe_receipt_pins': before, 'original_checkout_guards_unchanged': guards,
        'new_feature_preparations': 0, 'new_fits': 0, 'new_autoencoder_fits': 0,
        'new_gradient_evaluations': 0, 'new_optimizer_updates': 0, 'new_training_trace_replays': 0,
        'python_ranker_source_equivalence_proved': False, 'binary64_error_bound_proved': False,
        'native_Float_optimizer_convergence_proved': False, 'general_codebase_IR_preservation_proved': False,
        'global_autoencoder_convergence_proved': False, 'full_task_satisfaction': 'unknown',
        'official_benchmark_score': None, 'all32_governing_RPI_exits': 'OPEN',
        'next_obligations': pin(Q / 'next-obligations.json'), 'raw_SDK_logs_read_or_published': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
    target = R / 'release-publication-ledger-01.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(ledger, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'ledger': pin(target), 'HF_commit': COMMIT, 'status': ledger['status']}))

if __name__ == '__main__':
    main()
