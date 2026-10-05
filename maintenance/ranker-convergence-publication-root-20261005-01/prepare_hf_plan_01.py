"""Prepare the exact second successor upload from passed, frozen local evidence."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
R = Path(__file__).resolve().parent
S = ROOT / 'maintenance/ranker-convergence-publication-20261005-01'
P = ROOT / 'maintenance/ranker-convergence-publication-package-20261005-01'
Q = ROOT / 'qualification/codebase_ir/ranker-real-convergence-20261005-01'
I = ROOT / 'maintenance/ranker-convergence-publication-input-review-20261005-01'
M = ROOT / 'maintenance/ranker-convergence-math-review-20261005-01'
PREFIX = 'releases/20261004-terminal-codebase-ir-evidence-v1'
NAMESPACE = PREFIX + '/successor-ranker-convergence-v1'
PARENT = '8b7b8c896749e0ca3884114cedbed782a88f4702'

def read(path):
    path = Path(path).absolute()
    assert not path.is_symlink() and path.is_file()
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
    assert identity(before) == identity(after)
    assert len(raw) == before.st_size
    return raw

def pin(path):
    path = Path(path).absolute()
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def load(path, expected=None):
    path = Path(path).absolute()
    raw = read(path)
    if expected is not None:
        actual = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if isinstance(expected, str):
            assert actual['sha256'] == expected
        else:
            assert actual == expected
    return json.loads(raw)

def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)

def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()

def main():
    if not __debug__:
        raise RuntimeError('optimized Python would disable publication gates')
    baseline = load(R / 'HF-parent-preflight-01.json', 'bfaa2cb0b42af891854b956074a72c757ad60a7b55c8964a4282056143933841')
    assert baseline['parent_commit'] == PARENT and baseline['complete_regular_file_count'] == 227
    assert baseline['namespace_unoccupied'] and baseline['namespace'] == NAMESPACE
    assert all(pin(x['path']) == x for x in baseline['mutable_pointer_source_pins'])
    local_close = load(P / 'closed.json')
    assert local_close['status'] == 'passed_local_frozen_package'
    manifest_pin = pin(P / 'package/manifest.json')
    assert manifest_pin == local_close['manifest']
    manifest = load(manifest_pin['path'], local_close['manifest'])
    assert manifest['file_count'] == 401 and manifest['original_file_bytes'] == 147838468
    assert manifest['semantic_fact_count_verified'] == 329 and manifest['native_attempt_count_fact_gated'] == 9
    assert manifest['scan_hits'] == [] and manifest['actual_duplicate_verification_decoder_invocations'] == 0
    package_review = load(S / 'package-review-01.json', '80e52bb19948125571ceec442e82bc2bed5fe2b792ed32222cdcd2c8c43b0f93')
    assert package_review['status'] == 'passed'
    assert package_review['manifest'] == manifest_pin
    input_review = load(I / 'review-receipt.json', '28b43224125a231e7dc9036de5cca61165e4292583429620985d87624900cf25')
    assert input_review['status'] == 'passed_file_only_final_publication_input_review'
    assert input_review['outstanding_issues'] == []
    review = load(Q / 'qualified-review-01.json', 'eebf40b5de2822faef1293a62578da208b582131e44c8a1f3e0d060071b6d0e7')
    assert review['original_exact_real_model_weights_convergence_proved']
    assert review['original_exact_real_objective_convergence_proved']
    assert review['native_lean_calls'] == 9 and review['inconclusive_native_lean_checks_retained'] == 2
    assert review['metadata_payloads'] == 4417 and review['metadata_family_count'] == 32
    for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation',
                'python_ranker_source_equivalence_proved', 'binary64_error_bound_proved',
                'global_autoencoder_convergence_proved', 'native_Float_optimizer_convergence_proved'):
        assert review[key] is False
    assert review['full_task_satisfaction'] == 'unknown' and review['official_benchmark_score'] is None
    card = read(R / 'prior-HF-README-01.md').decode()
    card += '''

## Original exact-real ranker global convergence

This successor establishes the remaining exact-real convergence result for the
original four-pair, 80-coordinate ranker. Earlier sections record the evidence
available at their own revisions. The new Lean theorem
`RankerRealCurvature.originalReal_model_converges` proves existence and uniqueness
of a global minimizer and convergence of both weights and objective values from
every initial real vector under the original exact-real gradient recurrence.
It does not assume a minimizer, contraction, or convergence conclusion. The proof
derives these from the original bound corpus and exact parameters through strong
convexity, minimizer existence, stationarity, quadratic growth and geometric
loss-gap contraction.

Nine actual native Lean attempts yielded seven accepted modules with 39 queried
theorem entries and two retained inconclusive attempts. All accepted queries use
only the existing standard Lean axioms. The accepted modules retain complete
compiled objects and bounded chunks. Every attempt retains its source, complete
dependency manifest, output and qualification or refusal result.
Native proof and supervisor limits remain unchanged. This phase performed no
new fitting, feature preparation, gradient evaluation, optimizer update or
training trace replay.

Native DuckDB/DuckLake now contains 4,417 payloads across the same 32 families.
All 4,378 prior payloads remain exact family prefixes; all 4,417 passed complete
export comparison and fresh-process readback. The 39 additions include actual
check records, module proof records, four pinned Python ASTs and checked-import
graph edges. Vectors and the empty contracts family remain unchanged. These
proof rows add no strict-cache admissions or operational authority.

The complete 401-file, 147,838,468-byte selected population is retained in
`releases/20261004-terminal-codebase-ir-evidence-v1/successor-ranker-convergence-v1`.
It includes all 378 sealed regular evidence files, the seal itself, source-only
planning history and explicitly pinned publication provenance. The archive and
independent decoded-member review retain every lock, empty export, failed
profile, proof object and chunk. Earlier immutable evidence and archive exclusions
are preserved; the prior large archives are referenced without reuploading them.

The exact-real probability branch interpretation agrees with the analytic
gradient. The four Python AST inventories identify source shapes. Python
interpreter semantics, `math.fsum`, binary64/libm refinement and finite native
optimizer convergence remain open, along with general codebase IR preservation,
autoencoder convergence and full Terminal Bench task satisfaction. The infinite
real recurrence theorem applies to the stated convex ranker, with its exact
original data and parameters. All 32 governing RPI exits remain OPEN; planner,
proof, execution and completion authority stay false, and no benchmark score is
claimed.
'''
    new_card = save(R / 'HF-README-01.md', card.encode())
    prior_status_pin = next(x for x in baseline['mutable_pointer_source_pins'] if x['path'].endswith('prior-HF-publication-status-01.json'))
    status = load(R / 'prior-HF-publication-status-01.json', prior_status_pin)
    status['status'] = 'PUBLISHED_PRIOR_EVIDENCE_WITH_EXACT_REAL_RANKER_CONVERGENCE_SUCCESSOR'
    status['ranker_exact_real_convergence_qualification'] = {
        'qualified_review': pin(Q / 'qualified-review-01.json'), 'file_seal': pin(Q / 'file-only-seal-01.json'),
        'original_exact_real_model_weights_convergence_proved': True,
        'original_exact_real_objective_convergence_proved': True,
        'geometric_original_exact_real_gap_rate_proved': True,
        'theorem': 'RankerRealCurvature.originalReal_model_converges',
        'scope': 'Original fixed four-pair, 80-coordinate convex exact-real ranker and its infinite real recurrence only',
        'actual_native_lean_attempts': 9, 'accepted_modules': 7, 'queried_theorem_entries': 39,
        'retained_inconclusive_attempts': 2, 'metadata_families': 32, 'metadata_payloads': 4417,
        'prior_metadata_payloads_preserved': 4378, 'additive_metadata_payloads': 39,
        'new_fits': 0, 'new_gradient_evaluations': 0, 'new_optimizer_updates': 0,
        'new_strict_proof_cache_admissions': 0, 'native_limits_unchanged': True,
        'source_AST_obligations': pin(Q / 'source-model-obligations-01.json'),
        'next_obligations': pin(Q / 'next-obligations.json'),
        'python_ranker_source_equivalence_proved': False, 'native_Float_optimizer_convergence_proved': False,
        'binary64_error_bound_proved': False, 'global_autoencoder_convergence_proved': False,
        'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
    status['ranker_exact_real_convergence_package'] = {
        'prefix': NAMESPACE, 'manifest': manifest_pin, 'decoded_member_review': pin(S / 'package-review-01.json'),
        'selected_regular_files': 401, 'selected_regular_bytes': 147838468,
        'source_package_parent_HF_commit': PARENT, 'all_prior_225_immutable_remote_files_preserved_required': True,
        'old_HF_bundle_reuploaded': False, 'raw_external_dependency_bodies_published': False,
        'verified_successor_commit_recorded_in_external_publication_receipts': True,
        'qualification_grants_operational_authority': False}
    for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation',
                'global_autoencoder_convergence_proved', 'full_task_satisfaction_proved',
                'whole_source_equivalence_proved', 'whole_source_runtime_equivalence_proved'):
        assert status[key] is False
    new_status = save(R / 'HF-publication-status-01.json', json_bytes(status))
    files = []
    def add(local, relative):
        files.append({'local': pin(local), 'remote': NAMESPACE + '/' + relative})
    for item in manifest['data_shards']:
        assert pin(item['path']) == {k:item[k] for k in ('path', 'bytes', 'sha256')}
        add(item['path'], 'package/' + item['archive'])
    add(P / 'package/manifest.json', 'package/manifest.json')
    add(S / 'package-review-01.json', 'package/package-review-01.json')
    add(P / 'closed.json', 'package/local-package-closed-01.json')
    for name in ('plan.json', 'required-facts.json', 'final-selection.json', 'closed-inputs.json', 'source-review-01.json'):
        add(S / name, 'publication-inputs/' + name)
    for name in ('qualified-review-01.json', 'file-only-seal-01.json', 'README.md', 'next-obligations.json', 'source-model-obligations-01.json'):
        add(Q / name, 'qualification/' + name)
    plan = load(S / 'plan.json', '44674a6e9901d49db15acac1264706cb0aa5ed6a5136ad3dcd38354dd1ef594b')
    for role in plan['native_checks']:
        descriptor = plan['documents'][role]
        assert pin(descriptor['path']) == descriptor
        add(descriptor['path'], 'native-receipts/' + role + '.json')
    add(Q / 'evidence/metadata-convergence-01/metadata-readback.json', 'native-receipts/metadata-readback.json')
    for folder, prefix, names in ((I, 'input-review', ('review_inputs.py', 'review-receipt.json')),
                                  (M, 'math-review', ('review_native_math.py', 'review-receipt.json')),
                                  (R, 'root-publication-source', ('prepare_phase_invocations_01.py', 'prepare_phase_invocations_02.py', 'prepare_hf_plan_01.py', 'scan_final_upload_01.py', 'prepare_upload_phase_01.py'))):
        for name in names:
            add(folder / name, prefix + '/' + name)
    for name in ('package-outer-01/closed.json', 'package-review-outer-01/closed.json', 'package-review-outer-02/closed.json'):
        add(R / name, 'root-attempt-receipts/' + name.replace('/', '-'))
    files.extend([{'local': new_card, 'remote': 'README.md'},
                  {'local': new_status, 'remote': PREFIX + '/publication-status.json'}])
    assert len({row['remote'] for row in files}) == len(files) <= 100
    assert all(x['local']['bytes'] <= 256 * 1024 ** 2 for x in files)
    upload = {'schema': 'terminal-ir-successor-evidence-publication-plan@1',
              'repo_id': 'Publicus/codebase-ir-proof-index', 'expected_parent_commit': PARENT,
              'immutable_namespace': NAMESPACE, 'scope': status['ranker_exact_real_convergence_qualification']['scope'],
              'large_prior_archive_reupload': False, 'old_immutable_files_preserved': True, 'files': files}
    target = R / 'hf-plan-01.json'
    descriptor = save(target, json_bytes(upload))
    print(json.dumps({'plan': descriptor, 'selected_files': len(files),
                      'selected_bytes': sum(x['local']['bytes'] for x in files),
                      'shards': len(manifest['data_shards'])}, sort_keys=True))

if __name__ == '__main__':
    main()
