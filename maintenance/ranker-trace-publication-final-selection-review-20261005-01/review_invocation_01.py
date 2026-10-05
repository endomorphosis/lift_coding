"""File-only join of the actual final scan, publication plan, and invocation."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
OWNER = WORKSPACE / 'maintenance/ranker-trace-publication-root-20261005-01'
HF = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
EXPECTED = {
    OWNER / 'final-hf-selection-01.json': 'a53a4b11ab8e5cf257ada4f7d0e8525aa4738516edd2cc2e86e281b3cab908e7',
    OWNER / 'final-plan-01/metadata-scan-closed.json': '01a1234e1c958a48a474df3ef7895d3bb42a1f1f0641fe06a50115a183601207',
    OWNER / 'final-plan-01/plan.json': '3ccf91f6df39ea96e893d6bb69bd5efbb2b45e92772bfb4a313904bf3393cfe0',
    OWNER / 'hf-publication-invocation-01.json': 'ed72e897cffd7f0a6bbccb8d5e6608a6cb16f7bd69b8599d45ccfffc65163349',
    OWNER / 'prepare_publication_metadata.py': 'ac90a026b3dec72592cfb9f82df7081018851426e6c4325c6ca9a44428373154',
    HF / 'publish_successor_evidence_02.py': '670e064a8222ce1b0c962e202985974741a9a4476630b0541c7ec880b32009f2',
    HF / 'run_frozen_publication_phase.py': '8d9955df76155f75326fdda8039119bacab9bad3ca71306f241be9b2124d01b8',
    ROOT / 'selection-card-receipt-review-01.json': '338c1baaa1b82025cde7e0ba57a7e745a95ca526e5b065f2725c12b9180fae17',
}


def signature(value):
    return tuple(getattr(value, 'st_' + key) for key in
                 ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns'))


def pin(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        initial = os.fstat(fd)
        assert stat.S_ISREG(initial.st_mode) and initial.st_nlink == 1 and initial.st_size <= 16 * 1024**2
        digest, size = hashlib.sha256(), 0
        while block := os.read(fd, 1024**2):
            digest.update(block)
            size += len(block)
        assert size == initial.st_size
        assert signature(initial) == signature(os.fstat(fd)) == signature(path.lstat())
        return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)


def body(path):
    return json.loads(Path(path).read_bytes())


def main():
    before = {str(path): pin(path) for path in EXPECTED}
    assert all(before[str(path)]['sha256'] == digest for path, digest in EXPECTED.items())
    for path in EXPECTED:
        if path.suffix == '.py': ast.parse(path.read_bytes())
    selection = body(OWNER / 'final-hf-selection-01.json')
    scan = body(OWNER / 'final-plan-01/metadata-scan-closed.json')
    plan = body(OWNER / 'final-plan-01/plan.json')
    invocation = body(OWNER / 'hf-publication-invocation-01.json')
    clearance = body(ROOT / 'selection-card-receipt-review-01.json')
    assert clearance['status'] == 'passed_no_blocking_findings'
    assert scan['schema'] == 'terminal-ranker-trace-supplemental-metadata-scan@1' and scan['status'] == 'passed'
    assert scan['selection'] == clearance['selection'] == before[str(OWNER / 'final-hf-selection-01.json')]
    assert scan['source'] == before[str(OWNER / 'prepare_publication_metadata.py')]
    assert scan['primary_error_type'] is None and scan['selected_files_scanned'] == len(scan['scanned_files']) == 38
    assert scan['decoded_work_bytes'] == 91185689 <= scan['decoded_work_limit_bytes'] == 512 * 1024**2
    assert scan['per_container_limit_bytes'] == 16 * 1024**2
    assert scan['qualified_shards_independently_rescanned'] == selection['qualified_package_shards']
    assert scan['new_native_jobs'] == scan['external_mutations'] == 0
    assert scan['model_activation'] is scan['proof_authority'] is scan['universal_secret_absence_claim'] is False
    for scanned, selected in zip(scan['scanned_files'], selection['files']):
        assert scanned['local'] == selected['local'] and scanned['remote'] == selected['remote']
        assert scanned['scan_hits'] == [] and pin(scanned['local']['path']) == scanned['local']
    for binding in scan['helpers'].values():
        assert pin(binding['path']) == binding
    namespace = 'releases/20261004-terminal-codebase-ir-evidence-v1/successor-ranker-trace-v1/'
    scan_remote = namespace + 'publication/metadata-scan-closed.json'
    scan_pin = before[str(OWNER / 'final-plan-01/metadata-scan-closed.json')]
    assert plan['files'] == selection['files'] + [{'local': scan_pin, 'remote': scan_remote}]
    assert len(plan['files']) == 39 and sum(row['local']['bytes'] for row in plan['files']) == 7835110
    assert plan['schema'] == 'terminal-ir-successor-evidence-publication-plan@1'
    assert plan['repo_id'] == selection['repo_id'] == 'Publicus/codebase-ir-proof-index'
    parent = '580717c7b45e7162ce6f1b5e63309fc76b962b44'
    assert plan['expected_parent_commit'] == selection['expected_parent_commit'] == parent
    assert invocation['schema'] == 'terminal-ir-frozen-publication-phase-invocation@1'
    assert invocation['phase'] == 'ranker-trace-evidence-publication-01' and invocation['cwd'] == str(WORKSPACE)
    assert invocation['wall_seconds'] == 900
    assert invocation['argv'] == ['/usr/bin/env', 'HF_HUB_DISABLE_XET=1', 'HF_HUB_ENABLE_HF_TRANSFER=0',
        '/home/barberb/.local/bin/python', str(HF / 'publish_successor_evidence_02.py'), '--plan',
        str(OWNER / 'final-plan-01/plan.json'), '--expected-plan-sha256',
        before[str(OWNER / 'final-plan-01/plan.json')]['sha256'], '--expected-parent-commit', parent,
        '--output', str(OWNER / 'hf-publication-01')]
    assert invocation['remote_mutation_scope'] == {'expected_parent': parent,
        'explicit_mutable_paths': ['README.md', 'releases/20261004-terminal-codebase-ir-evidence-v1/publication-status.json'],
        'force': False, 'new_paths': 37, 'repo_id': 'Publicus/codebase-ir-proof-index', 'repo_type': 'dataset', 'revision': 'main'}
    inputs = invocation['pinned_inputs']
    assert len(inputs) == len({row['path'] for row in inputs}) == 41
    expected_inputs = {row['local']['path']: row['local'] for row in plan['files']}
    expected_inputs.update({str(OWNER / 'final-plan-01/plan.json'): before[str(OWNER / 'final-plan-01/plan.json')],
                            str(OWNER / 'final-hf-selection-01.json'): before[str(OWNER / 'final-hf-selection-01.json')]})
    assert {row['path']: row for row in inputs} == expected_inputs
    for row in inputs:
        assert pin(row['path']) == row
    assert all(pin(path) == before[str(path)] for path in EXPECTED)
    result = {'schema': 'ranker-trace-final-HF-plan-and-invocation-file-only-review@1',
        'status': 'passed_no_blocking_findings', 'producer': pin(Path(__file__).resolve()), 'inputs': before,
        'scan_actual_status_passed_bound': True, 'scan_all38_selected_files_and3qualified_shards_bound': True,
        'scan_declared_decoded_work_bytes': 91185689, 'scan_candidate_hits': 0,
        'exact39_upload_files_selected_bytes': 7835110, 'invocation_unique_input_pins': 41,
        'exact38_selection_plus_one_fixed_scan_receipt': True, 'exact_parent_required': parent,
        'explicit_mutable_paths': invocation['remote_mutation_scope']['explicit_mutable_paths'],
        'new_namespace_paths': 37, 'ordinary_main_commit_force_false': True,
        'frozen_publisher02_and_wrapper_source_reviewed': True,
        'publisher_requires_fresh_parent_unoccupied_immutable_paths_and_remote_byte_or_LFS_readback': True,
        'publisher_preserves_all_other_existing_remote_identities': True,
        'wrapper_requested_wall_seconds': 900, 'wrapper_child_wait_additional_grace_seconds': 60,
        'wrapper_complete_descendant_cleanup_is_not_claimed': True,
        'failed_external_effect_attempts_preserved': True, 'blocking_findings': [],
        'publication_not_executed_by_this_review': True, 'remote_write_or_readback_success_not_asserted_here': True,
        'operations_this_review': {'file_JSON_AST_only': True, 'native_jobs': 0, 'project_imports': 0,
            'test_repeats': 0, 'classifier_calls': 0, 'archive_decodes': 0, 'credential_reads': 0,
            'network_calls': 0, 'git_calls': 0, 'uploads': 0},
        'historical_origin_proved': False, 'asymptotic_convergence_proved': False, 'proof_authority': False,
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown',
        'planner_activation': False, 'official_benchmark_score': None}
    target = ROOT / 'final-plan-invocation-review-01.json'
    with target.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(pin(target), sort_keys=True))


if __name__ == '__main__':
    main()
