"""Prepare the final metadata addition only from closed publication receipts."""
from pathlib import Path
import argparse
import hashlib
import json
import runpy

BASE = Path(__file__).resolve().parent
RELEASE = 'releases/20261004-terminal-codebase-ir-evidence-v1'
REPO = 'Publicus/codebase-ir-proof-index'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bulk-directory', type=Path, required=True)
    args = parser.parse_args()
    bulk_directory = args.bulk_directory
    if (not bulk_directory.is_absolute() or bulk_directory.resolve(strict=True) != bulk_directory or
            bulk_directory.parent != BASE or not bulk_directory.name.startswith('bulk-publication-')):
        raise ValueError('canonical owned bulk publication directory required')
    publisher = BASE / 'publish_successor_evidence_02.py'
    if hashlib.sha256(publisher.read_bytes()).hexdigest() != '670e064a8222ce1b0c962e202985974741a9a4476630b0541c7ec880b32009f2':
        raise ValueError('reviewed publisher source changed')
    reader = runpy.run_path(str(publisher), run_name='terminal_ir_metadata_preparer')
    pin, stable_read, save = reader['pin'], reader['stable_read'], reader['save']

    def document(path):
        binding, raw = stable_read(path, retain_plan_bytes=True)
        return binding, json.loads(raw)

    bulk_path = bulk_directory / 'closed.json'
    bulk_pin, bulk = document(bulk_path)
    if (bulk['status'] != 'PUBLISHED_AND_SELECTED_REMOTE_IDENTITIES_VERIFIED' or
            not bulk['all_selected_files_verified'] or bulk['uploaded_files'] != bulk['file_count']):
        raise ValueError('actual verified bulk publication required')
    if (bulk['manifest']['sha256'] != '4e7c722f5938877a2b868945f842011a8e65678f77a867fdfdcf2fe613c7a9b9' or
            bulk['root_review']['sha256'] != 'e4bce17560db481d35f315dda29dda2e4f2a528e78c2e8fdef5699c30a6ea9c8'):
        raise ValueError('reviewed public subset changed')
    package = BASE / 'successor-source-model-package-02'
    package_pin, package_closed = document(package / 'closed.json')
    if package_closed['status'] != 'passed_local_frozen_package' or package_closed['cleanup_errors']:
        raise ValueError('closed package required')
    manifest_pin, manifest = document(Path(package_closed['manifest']['path']))
    if manifest_pin != package_closed['manifest'] or manifest['file_count'] != 417:
        raise ValueError('frozen package manifest mismatch')
    package_review_path = package / 'file-only-review-01.json'
    package_review_pin, package_review = document(package_review_path)
    if package_review_pin['sha256'] != '142ac6862e5fa656b13c5e93bd7b6190e939ce0885c27a8dae9ace5cf9d9a2a4':
        raise ValueError('closed package review changed')
    publisher_review_path = BASE / 'successor-publisher-source-review-02/review.json'
    publisher_review_pin, publisher_review = document(publisher_review_path)
    if publisher_review_pin['sha256'] != '17ea2e8ae7b2be5e12c8df66c27eaced7db632b003bb9e55483f10c45e51eb2b':
        raise ValueError('closed publisher source review changed')
    result_path = BASE.parents[2] / 'qualification/codebase_ir/source-model-next-stage-20261004-01/qualified-result.json'
    result_pin, result = document(result_path)
    if (result['new_fits'] != 0 or result['optimizer_updates'] != 0 or result['planner_activation'] or
            result['official_benchmark_score'] is not None or result['all32_governing_RPI_exits'] != 'OPEN'):
        raise ValueError('original qualification scope changed')
    root_path = BASE.parent / 'root-source-model-03/publication-closed-01.json'
    root_pin, root = document(root_path)
    child_path = BASE.parent / 'accelerate-source-model-02/docs-publication-closed-01.json'
    child_pin, child = document(child_path)
    if root['remote_main'] != root['commit'] or child['remote_main_verified'] != child['commit']:
        raise ValueError('verified GitHub source publications required')
    case_path = BASE.parents[2] / 'qualification/codebase_ir/full-task-reference-metrics-20261005-01/qualified-review.json'
    case_pin, case = document(case_path)
    if (case_pin['sha256'] != 'e63564f7396e879ca24f8e022550265dfda97fe2add23238bc98ea17da0e5429' or
            case['eight_strict_threshold_comparisons'] != 'passed' or
            case['four_structural_clauses'] != 'passed' or case['input_byte_frame'] != 'passed' or
            case['native_lean_calls'] != 2 or case['positive_lean_theorems'] != 8 or
            case['official_benchmark_score'] is not None or case['whole_source_equivalence_proved'] or
            case['asymptotic_optimizer_convergence_proved'] or case['autoencoder_convergence_proved'] or
            case['training_calls'] or case['optimizer_updates'] or case['PlanCreate_calls'] or
            case['cleanup_errors'] or case['RPI_macrocriteria']['open'] != 32):
        raise ValueError('closed authored-case qualification changed')
    package_v2 = BASE / 'successor-source-model-package-03'
    package_v2_pin, package_v2_closed = document(package_v2 / 'closed.json')
    if package_v2_closed['status'] != 'passed_local_frozen_package' or package_v2_closed['cleanup_errors']:
        raise ValueError('closed authored-case public package required')
    manifest_v2_pin, manifest_v2 = document(Path(package_v2_closed['manifest']['path']))
    if manifest_v2_pin != package_v2_closed['manifest']:
        raise ValueError('authored-case package manifest changed')
    review_v2_path = package_v2 / 'file-only-review-01.json'
    review_v2_pin, review_v2 = document(review_v2_path)
    if review_v2['status'] != 'passed':
        raise ValueError('authored-case package review failed')
    output = BASE / 'successor-publication-preparation-02'
    if not output.is_dir(): raise ValueError('prepared release card directory required')
    status = {'schema': 'terminal-ir-publication-status@2',
        'status': 'verified_scoped_archive_and_qualified_source_model_evidence',
        'release_prefix': RELEASE, 'repo_id': REPO, 'bulk_archive_publication_complete': True,
        'complete_original_raw_byte_publication': False,
        'archive': {'commit': bulk['final_commit'], 'publication_closure': bulk_pin,
                    'manifest': bulk['manifest'], 'root_classification_review': bulk['root_review'],
                    'file_count': bulk['file_count'], 'uploaded_bytes': bulk['selected_uploaded_bytes'],
                    'included_captured_file_paths': 2449876, 'included_logical_file_bytes': 111967916066,
                    'excluded_captured_file_paths': 8, 'metadata_only_regular_paths': 4,
                    'unresolved_original_containers': 4, 'denied_original_candidates': 4,
                    'quarantine_originals_retained_local': True, 'source_atomic': False,
                    'universal_secret_free_claim': False},
        'source_model_package': {'manifest': manifest_pin, 'closure': package_pin,
                                'file_count': manifest['file_count'],
                                'original_file_bytes': manifest['original_file_bytes'],
                                'compressed_bytes': manifest['compressed_bytes'],
                                'transient_lock_exclusions': len(manifest['exclusions'])},
        'authored_case_source_model_package': {'manifest': manifest_v2_pin, 'closure': package_v2_pin,
            'review': review_v2_pin, 'file_count': manifest_v2['file_count'],
            'original_file_bytes': manifest_v2['original_file_bytes'],
            'compressed_bytes': manifest_v2['compressed_bytes']},
        'authored_case_qualification': case, 'authored_case_qualification_binding': case_pin,
        'github_publication_snapshots': {'root': root['commit'], 'ipfs_accelerate': child['commit'],
            'ipfs_datasets': 'a3e7ea91cfbbf2e68d68b1362e0a22690cb09d97',
            'ipfs_kit': '8ac00bb1974b1378e12091d546d8425af34049e0',
            'JevOps': '9af1ebb6a4245ce2b4e673ac277e4988da4d5caa'},
        'qualified_increment': result, 'qualified_increment_binding': result_pin,
        'activation_criteria_open': 32, 'proof_authority': False, 'planner_activation': False,
        'whole_source_equivalence_proved': False, 'full_task_satisfaction_proved': False,
        'asymptotic_optimizer_convergence_proved': False, 'global_autoencoder_convergence_proved': False,
        'official_benchmark_score': None}
    save(output / 'publication-status.json', status)
    files = []

    def add(local, remote):
        files.append({'local': pin(local), 'remote': remote})

    add(output / 'README.md', 'README.md')
    add(output / 'publication-status.json', RELEASE + '/publication-status.json')
    successor = RELEASE + '/successor-source-model-v1/'
    add(Path(manifest_pin['path']), successor + 'manifest.json')
    add(package / 'closed.json', successor + 'package-closure.json')
    for shard in manifest['data_shards']:
        add(Path(shard['path']), successor + shard['archive'])
    add(package_review_path, successor + 'package-review.json')
    add(result_path, successor + 'qualified-result.json')
    add(root_path, successor + 'github-root-publication.json')
    add(child_path, successor + 'github-accelerator-publication.json')
    add(publisher_review_path, successor + 'publisher-source-review.json')
    add(BASE / 'successor-publisher-reader-controls-01/closed.json', successor + 'publisher-input-controls.json')
    successor_v2 = RELEASE + '/successor-source-model-v2/'
    add(Path(manifest_v2_pin['path']), successor_v2 + 'manifest.json')
    add(package_v2 / 'closed.json', successor_v2 + 'package-closure.json')
    add(review_v2_path, successor_v2 + 'package-review.json')
    add(case_path, successor_v2 + 'qualified-review.json')
    for shard in manifest_v2['data_shards']:
        add(Path(shard['path']), successor_v2 + shard['archive'])
    archive = RELEASE + '/archive-payload-v1/'
    for path, name in [
        (bulk_path, 'publication-closure.json'),
        (BASE / bulk_directory.name.replace('bulk-publication-', 'bulk-publication-outer-') / 'closed.json', 'publication-outer-closure.json'),
        (BASE / 'root-physical-review-01/review.json', 'physical-review.json'),
        (BASE / 'archive-classification-01/public/archive-manifest.json', 'original-classifier-manifest.json'),
        (BASE / 'archive-classification-outer-01/closed.json', 'classification-outer-closure.json'),
        (BASE / 'classification-closed-exceptions-01.json', 'classification-exceptions.json'),
        (BASE / 'classification-approvals-01.json', 'classification-approvals.json'),
        (BASE / 'independent-source-review-02/review.json', 'classifier-source-review.json'),
        (BASE / 'fixture-provenance-02/review.json', 'four-public-fixture-provenance.json'),
        (BASE / 'oauthlib-public-fixture-provenance-02/review.json', 'oauthlib-public-fixture-provenance.json')]:
        add(path, archive + name)
    if bulk_directory.name != 'bulk-publication-01':
        for path, name in [
            (BASE / 'bulk-publication-outer-01/closed.json', 'first-upload-interrupted-outer.json'),
            (BASE / 'bulk-transfer-stall-diagnostics-01/observation.json', 'first-upload-stall-observation.json'),
            (BASE / 'bulk-transfer-stall-diagnostics-01/closed-and-remote-readback.json', 'first-upload-remote-reconciliation.json')]:
            add(path, archive + name)
    plan = {'schema': 'terminal-ir-successor-evidence-publication-plan@1', 'repo_id': REPO,
        'expected_parent_commit': bulk['final_commit'], 'files': files,
        'all_files_have_exact_local_bindings': True, 'bulk_closure': bulk_pin,
        'package_closure': package_pin, 'package_manifest': manifest_pin,
        'authored_case_package_closure': package_v2_pin, 'authored_case_package_manifest': manifest_v2_pin,
        'prepared_without_remote_mutation': True, 'proof_authority': False}
    save(output / 'file-plan.json', plan)
    print(json.dumps({'status': 'PREPARED_FROM_VERIFIED_CLOSURES', 'plan': pin(output / 'file-plan.json'),
                      'files': len(files), 'bytes': sum(item['local']['bytes'] for item in files)}))


if __name__ == '__main__': main()
