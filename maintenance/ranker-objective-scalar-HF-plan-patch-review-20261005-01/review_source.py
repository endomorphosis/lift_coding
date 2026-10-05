"""Independent inert-source HF preparation patch and file-population review."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
HERE = Path(__file__).resolve().parent
R = W / 'maintenance/ranker-objective-scalar-publication-root-20261005-01'
S = W / 'maintenance/ranker-objective-scalar-publication-20261005-01'
Q = W / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
OLD = R / 'prepare_hf_plan_01.py'
NEW = R / 'prepare_hf_plan_02.py'
PINS = {
    OLD: (16950, 'f1babaf4f90463dab973f5d185fce6d0c52c5fb9df6729a878ed878b6c45cfb1'),
    NEW: (18728, '03fcaed1c081acab3cb4ac558db9dfa4e0db02771efb2cd304c35bbe17bdef02'),
    R / 'hf-preparation-attempt-01.json': (1612, '7518151c5c546640ce12d50d42143ca90cbcbd015bd86a20f49ddfaf4a1d0cc1'),
    R / 'HF-README-01.md': (16744, '5b45e603272ffbad96970cb2a64335dbea08f2e2a7057a10a3fba42a0817c58e'),
    R / 'HF-publication-status-01.json': (88779, '1d63726fb3abfbaec640e3cb11e540c31b5dea4ebf416397306492f205e2f871'),
    Q / 'file-only-seal-01.json': (86066, '874b51a3358dee5dbd18b70c66770f4e3fdf3553c2fac3fb644075c37273f43d'),
    S / 'package-review-01.json': (3274, '99b05a23c48461fb8356a045665e7aa2e83e8c50a920c56bb5af5a9817f8197b'),
    R / 'prepare_invocation_01.py': (11102, '223fcd8ce7918879c97da16e972da4ff4af59ff468e74e9465cd3a8ef76af72f'),
    R / 'scan_final_upload_01.py': (4887, '9972c1291344a43485378f25c6853df1f8394c2d0bdf33ee24b7aa249beccd6b'),
    R / 'review_hf_readback_01.py': (8944, '263e3c8a7879f310c1079ceda64e18df98821198491026f6978cf81111fef812'),
}
HELD = {}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path, expected=None):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical bounded review input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and 0 <= first.st_size <= 1024**2, 'source/receipt review read cap')
        chunks, total = [], 0
        while block := os.read(fd, 65536):
            total += len(block)
            need(total <= 1024**2, 'running source read bound')
            chunks.append(block)
        raw = b''.join(chunks)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda row: tuple(getattr(row, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and total == first.st_size, 'review input drift')
    finally:
        os.close(fd)
    row = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if expected is not None:
        need((row['bytes'], row['sha256']) == expected, 'independent pinned source or receipt')
    need(str(path) not in HELD or HELD[str(path)] == row, 'previous review input changed')
    HELD[str(path)] = row
    return raw, row


def population():
    result = set()
    for current, directories, files in os.walk(Q, followlinks=False):
        for name in directories:
            path = Path(current) / name
            need(stat.S_ISDIR(path.lstat().st_mode) and not path.is_symlink(), 'qualification directory aliases refused')
        for name in files:
            path = Path(current) / name
            need(stat.S_ISREG(path.lstat().st_mode) and path.resolve(strict=True) == path, 'qualification leaf alias/special file')
            result.add(str(path))
    return result


def main():
    need(__debug__, 'optimized source review refused')
    need(not (HERE / 'review-receipt.json').exists(), 'fresh external patch receipt')
    inputs = {path: read(path, expected)[0] for path, expected in PINS.items()}
    old_text, new_text = inputs[OLD].decode(), inputs[NEW].decode()
    old_tree, new_tree = ast.parse(old_text), ast.parse(new_text)
    normalized = new_text.replace("'HF-README-02.md'", "'HF-README-01.md'")
    normalized = normalized.replace("'HF-publication-status-02.json'", "'HF-publication-status-01.json'")
    normalized = normalized.replace("for name in ('qualified-review-01.json','file-only-seal-01.json','source-model-obligations-01.json'):",
                                    "for name in ('README.md','qualified-review-01.json','file-only-seal-01.json','source-model-obligations-01.json'):")
    start = normalized.index('    # The executed producer and failed file-only attempt remain immutable history.\n')
    end = normalized.index('    files.extend(', start)
    normalized = normalized[:start] + normalized[end:]
    need(ast.dump(ast.parse(normalized), include_attributes=False) == ast.dump(old_tree, include_attributes=False),
         'only pointer paths, missing README omission and explicit audited preparation history changed')
    for fragment in ("peer['schema']=='ranker-objective-scalar-HF-plan-independent-patch-review@1'",
        "peer['status']=='passed_source_only' and peer['findings']==[]",
        "peer['corrected_producer']==own and peer['reviewer']==pin(peer_root/'review_source.py')",
        "attempt['producer']==pin(R/'prepare_hf_plan_01.py')", "attempt['archive_decoded_member_review']==review_pin",
        "attempt['hf_plan_created'] is False and attempt['remote_mutations']==0",
        "{str(R/'HF-README-01.md'),str(R/'HF-publication-status-01.json')}",
        "pin(row['path'])==row,'failed-attempt partial output changed'", "NS+'/publication-root/failed-prepare-01/'",
        "NS+'/publication-root/prepare-02-provenance/'", "save(R/'hf-plan-01.json',encoded(plan))"):
        need(fragment in new_text, 'patch history/source review/fixed downstream interface gate')
    seal = json.loads(inputs[Q / 'file-only-seal-01.json'])
    need(seal['regular_file_count'] == 276 and seal['regular_file_bytes'] == 78794802 and
         len(seal['files']) == 276, 'actual sealed qualification denominator')
    observed = population()
    expected = {row['path'] for row in seal['files']} | {str(Q / 'file-only-seal-01.json')}
    need(len(observed) == 277 and observed == expected, 'whole actual qualification leaf census equals seal plus self')
    need(str(Q / 'README.md') not in expected and not (Q / 'README.md').exists(), 'omitted README is neither sealed nor present')
    need(all(str(Q / name) in expected for name in ['qualified-review-01.json', 'file-only-seal-01.json', 'source-model-obligations-01.json']), 'all real overview files retained')
    failure = json.loads(inputs[R / 'hf-preparation-attempt-01.json'])
    need(failure['status'] == 'failed_before_frozen_upload_plan' and failure['hf_plan_created'] is False and
         failure['remote_mutations'] == failure['native_jobs'] == failure['model_jobs'] == failure['frozen_archive_mutations'] ==
         failure['sealed_qualification_mutations'] == 0 and failure['producer'] == HELD[str(OLD)], 'actual safe retained failure')
    need(failure['partial_outputs'] == [HELD[str(R / 'HF-README-01.md')], HELD[str(R / 'HF-publication-status-01.json')]], 'partial output pin joins')
    package = json.loads(inputs[S / 'package-review-01.json'])
    need(package['status'] == 'passed' and package['selected_files_verified_before_after'] == package['decoded_members_verified'] == 335 and
         package['sealed_file_count_rehashed'] == 276 and package['sealed_file_bytes_rehashed'] == 78794802 and
         failure['archive_decoded_member_review'] == HELD[str(S / 'package-review-01.json')], 'actual full decoded archive independent receipt join')
    downstream = [R / 'prepare_invocation_01.py', R / 'scan_final_upload_01.py', R / 'review_hf_readback_01.py',
                  R / 'close_release_publication_01.py', R / 'close_combined_publication_01.py']
    for path in downstream:
        if path not in inputs:
            inputs[path] = read(path)[0]
        tree = ast.parse(inputs[path])
        literals = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and type(node.value) is str}
        need('HF-README-01.md' not in literals and 'HF-publication-status-01.json' not in literals,
             'downstream helper does not force old local pointer filenames')
    invoke = inputs[R / 'prepare_invocation_01.py'].decode()
    need("for item in plan['files']:expected[item['local']['path']]=item['local']" in invoke and
         "plan=load(R/'hf-plan-01.json')" in invoke, 'invocation pins dynamic upload rows at unchanged plan path')
    readback = inputs[R / 'review_hf_readback_01.py'].decode()
    need('ROOT / "hf-plan-01.json"' in readback and 'args.expected_files' in readback and 'args.expected_bytes' in readback,
         'readback uses dynamic actual upload populations')
    own = read(Path(__file__).resolve())[1]
    need(population() == observed and all(read(path, (row['bytes'], row['sha256']))[1] == row
         for path, row in list(HELD.items())), 'all source/receipt pins and qualification path census rechecked')
    receipt = {'schema': 'ranker-objective-scalar-HF-plan-independent-patch-review@1', 'status': 'passed_source_only',
        'findings': [], 'corrected_producer': HELD[str(NEW)], 'reviewer': own, 'prior_executed_producer': HELD[str(OLD)],
        'failed_attempt': HELD[str(R / 'hf-preparation-attempt-01.json')], 'retained_partial_outputs': failure['partial_outputs'],
        'actual_decoded_archive_review': HELD[str(S / 'package-review-01.json')], 'qualified_seal': HELD[str(Q / 'file-only-seal-01.json')],
        'actual_qualification_path_census': {'sealed_regular_files': 276, 'sealed_regular_bytes': 78794802,
            'regular_leaf_paths_including_seal_self': 277, 'missing_or_extra_paths': [], 'README_present_or_declared': False,
            'all_three_real_overview_files_retained': True},
        'all_AST_outside_explicit_patch_normalizes_to_prior_source': True,
        'only_behavior_changes': ['omit nonexistent unsealed qualification README.md',
            'create fresh local HF-README-02.md and HF-publication-status-02.json',
            'retain old/new producer, failure, old partial bodies and exact external patch review as immutable audit rows'],
        'unchanged_plan_output_path': str(R / 'hf-plan-01.json'),
        'unchanged_downstream_source_pins': [HELD[str(path)] for path in downstream],
        'downstream_invocation_scanner_readback_and_closers_compatible': True,
        'prior_expected_HF_parent': 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e',
        'upload_max_unique_files': 100, 'only_existing_mutable_remote_paths': ['README.md', 'releases/20261004-terminal-codebase-ir-evidence-v1/publication-status.json'],
        'fixed_archive_population_unchanged': {'files': 335, 'bytes': 80792847},
        'package_or_codec_rebuild_required_by_patch': False, 'source_claims_native_caps_and_publication_caps_unchanged': True,
        'reviewed_target_imports_or_execution': False, 'codec_classifier_native_model_metadata_Git_HTTP_or_remote_jobs_run': False,
        'sealed_qualification_or_publication_input_mutations_by_reviewer': 0,
        'review_scope_limitations': ['Only qualification leaf paths were recounted here; sealed log/binary/database bodies were not read.',
            'The actual complete archive decode and protected-input digest checks are bound through the previously completed independent package review.',
            'The new producer and downstream jobs remain unexecuted by this reviewer; no future publication success is claimed.'],
        'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
    with (HERE / 'review-receipt.json').open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'review': read(HERE / 'review-receipt.json')[1], 'corrected_producer': receipt['corrected_producer']}))


if __name__ == '__main__':
    main()
