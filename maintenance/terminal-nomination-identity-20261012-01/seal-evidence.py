"""Generation03-only named-public evidence seal, after root final review.

No discovery, archive/database/key/auth/raw-worker-log reads, native imports,
tests or providers. --dry-run performs the same guards without writing a seal.
Review schema/field constants must match the actual final public review before
the root freezes and executes this helper.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import xml.etree.ElementTree as ET

O = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('o_named_public_guards', O / 'check-preservation.py')
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
C, N = g.C, g.N
MAX_FILES = 200
MAX_LITERAL_NAMES = 224
MAX_TOTAL = 64_000_000
REVIEW_SCHEMA = 'terminal-nomination-identity-final-independent-review@1'
REVIEW_BLOCKERS = 'blocking_summary_claim_findings'
REQUIRED = (
 'source-manifest-03.json', 'changes-03.patch', 'patch-qualification-03.json', 'preservation-check-03.json',
 'final-source-pins-03.json', 'focused-validation-03.json', 'final-review-03.json', 'result-summary.json', 'next-work.json',
 'beginning-source-pins.json', 'prior-stage-pins.json', 'additional-identity-baseline-03.json', 'supplemental-test-baseline-03.json',
 'package-stage.py', 'check-preservation.py', 'seal-evidence.py',
 'runtime-archive-fixed-03/manifest.json', 'runtime-archive-fixed-03-verification.json',
 'actual-harbor-lifecycle-03/qualification.json',
 'actual-harbor-lifecycle-01/qualification.json', 'actual-harbor-lifecycle-02/qualification.json',
 'actual-lifecycle-03-independent-review.json',
 'identity-validation.json', 'identity-validation-02.json', 'identity-focused-01.xml', 'identity-focused-02.xml',
 'identity-focused-03.xml', 'identity-focused-04.xml', 'identity-focused-05.xml',
 'identity-focused-03-failure-analysis.json', 'prepatch-identity-reproduction-01.json',
 'generation-02-before-source-pins.json', 'generation-02-catalog-guard-labels.json',
 'generation-02-guard-equivalence.json', 'generation-02-helper-retention.json', 'generation-03-helper-retention.json',
 'native-identity-validation-02.json', 'native-identity-tests-03.xml', 'native-identity-sidechannel-tests-01.xml',
 'complete-validation-04.json', 'complete-focused-04.xml',
 'default-validation-03.json', 'default-regression-03.xml',
 'native-identity-unit-freeze/test_native_task_identity.py', 'native-identity-validation.json',
 'native-identity-production-independent-review-03.json', 'source-analysis-update-04.json',
)
OPTIONAL = (
 'source-manifest.json', 'changes.patch', 'patch-qualification.json', 'preservation-check.json', 'final-source-pins.json',
 'source-manifest-02.json', 'changes-02.patch', 'patch-qualification-02.json', 'preservation-check-02.json',
 'final-source-pins-02.json', 'focused-validation.json', 'focused-validation-02.json',
 'production-source-pins-01.json', 'identity-source-pins-before-04.json', 'identity-source-pins-after-04.json',
 'identity-source-pins-before-05.json', 'identity-source-pins-after-05.json', 'identity-validation-write-attempt-01.json',
 'check-preservation-before-opaque-archive-fix.py', 'preservation-prewrite-failure-01.json',
 'preservation-path-guard-preflight-01.json', 'preservation-path-guard-preflight-02.json',
 'runtime-archive/manifest.json', 'runtime-archive-verification.json',
 'runtime-archive-final-02/manifest.json', 'runtime-archive-final-02-verification.json',
 'runtime-archive-fixed-03/requirements.txt', 'runtime-archive-fixed-03/runtime-reference.json',
 'public-task-metadata.json', 'public-task-image.json', 'public-task-inputs/instruction.md',
 'public-task-inputs/task.toml', 'public-task-inputs/environment/Dockerfile',
 'public-task-inputs/reviewed-intent-contract.json', 'qualify-retained-harbor.py', 'build-pinned-runtime.py',
 'build-stage-results.py',
 'complete-validation-03.json', 'complete-focused-03.xml', 'complete-source-pins-before-03.json', 'complete-source-pins-after-03.json',
 'complete-validation-04.json', 'complete-focused-04.xml', 'complete-source-pins-before-04.json', 'complete-source-pins-after-04.json',
 'generation-03-before-source-pins.json', 'production-source-pins-03.json', 'native-identity-fixture-readiness-03.json',
 'native-identity-tests-01.xml', 'native-identity-tests-02.xml',
 'native-identity-06.xml', 'native-identity-07.xml', 'native-identity-08.xml', 'native-identity-09.xml',
 'result-summary-before-timing-review03.json',
 'final-review-before-checker-correction-03.json',
 'generation-02-helpers-before/package-stage.py', 'generation-02-helpers-before/check-preservation.py',
 'generation-02-helpers-before/check-preservation-generation01-original.py',
 'generation-03-helpers-before/package-stage.py', 'generation-03-helpers-before/check-preservation.py',
 'generation-03-supplemental-helper-retention.json',
 'generation-03-supplemental-helpers-before/package-stage.py',
 'generation-03-supplemental-helpers-before/check-preservation.py',
 'generation-03-supplemental-helpers-before/seal-evidence.py',
 'generation-03-sealer-before-final.py', 'generation-03-sealer-final-adaptation-baseline.json',
 'packaging.stdout', 'packaging.stderr', 'preservation.stdout', 'preservation.stderr',
 'packaging-02.stdout', 'packaging-02.stderr', 'preservation-02.stdout', 'preservation-02.stderr',
 'packaging-03.stdout', 'packaging-03.stderr', 'preservation-03.stdout', 'preservation-03.stderr',
)
ACTUAL_NAMES = (
 'qualification.json', 'named-owner-public-metadata.stdout', 'named-owner-public-metadata.stderr',
 'installed-import-provenance.stdout', 'installed-import-provenance.stderr', 'original-head.txt',
 'deployment/deployment.json', 'worker-boundary/deployment.json',
 'worker-boundary/installation/installation.json', 'worker-boundary/qualification/qualification.json',
 'lifecycle/controller-result.json', 'lifecycle/template.json', 'lifecycle/baseline.json',
 'lifecycle/authored-review.json', 'lifecycle/prepare_only-public-report.json', 'lifecycle/resume-public-report.json',
 'lifecycle/prepare_only-attempt.json', 'lifecycle/resume-attempt.json',
 'lifecycle/prepare_only-execution.json', 'lifecycle/resume-execution.json',
)
NAMES = set(REQUIRED) | set(OPTIONAL)
for tag in ('01', '02', '03'):
    NAMES.update('actual-harbor-lifecycle-' + tag + '/' + name for name in ACTUAL_NAMES)
for name in g.AUTHORIZED:
    NAMES.add('generation-01/sources/' + name)
    NAMES.add('generation-02/sources/' + name)
FILES, PINS = {}, []


def add(path, expected_sha=None, expected_bytes=None):
    path = g.public_path(path)
    g.require(path.is_relative_to(O) or path.is_relative_to(C), 'Only named O evidence/current source')
    g.require(path.suffix != '.log' and not str(path).endswith(('.tar', '.tar.gz', '.zip', '.tgz')),
        'No raw logs or archive payloads')
    if str(path) not in FILES: FILES[str(path)] = g.capture(path, maximum=8_000_000)[0]
    pin = FILES[str(path)]
    g.require(len(FILES) <= MAX_FILES and sum(row['bytes'] for row in FILES.values()) <= MAX_TOTAL,
        'Explicit evidence census/bytes exceeded')
    if expected_sha is not None: g.require(pin['sha256'] == g.digest(expected_sha), 'Named SHA mismatch')
    if expected_bytes is not None: g.require(pin['bytes'] == g.count(expected_bytes), 'Named size mismatch')
    if expected_sha is not None or expected_bytes is not None:
        PINS.append({'path': str(path), 'expected_sha256': expected_sha, 'expected_bytes': expected_bytes, 'matched': True})
    return pin


def doc(name, expected_sha=None):
    path = O / g.relative(name); pin = add(path, expected_sha); before = g.witnesses[str(path)]
    result = g.document(path, expected_sha)
    g.require(pin == g.cache[str(path)] and before == g.witnesses[str(path)], 'Named document changed before parse')
    return result


def referenced_pin(row):
    g.require(type(row) is dict and type(row.get('path')) is str, 'Bounded explicit named pin required')
    path = g.public_path(row['path']); g.require(path.is_relative_to(O), 'Report stays under O')
    name = path.relative_to(O).as_posix(); g.require(name in NAMES, 'Unlisted report cannot be followed')
    return add(path, row['sha256'], row['bytes'])


def pinned_doc(row):
    pin = referenced_pin(row)
    return doc(Path(pin['path']).relative_to(O).as_posix(), pin['sha256'])


def normalized_case(case):
    classname = case.attrib.get('classname', '')
    if classname.startswith('test.api.'):
        classname = classname.removeprefix('test.')
    return classname, case.attrib['name']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-manifest', 'preservation', 'final-review', 'result-summary', 'next-work'):
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--dry-run', action='store_true'); args = parser.parse_args()
    output = O / 'evidence-manifest.json'
    g.require(not output.exists() and not output.is_symlink(), 'No existing seal replacement')
    review = doc('final-review-03.json', args.final_review_sha256)
    g.require(review['schema'] == REVIEW_SCHEMA and review['review_passed'] is True and review[REVIEW_BLOCKERS] == [],
        'Exact pinned scoped final review must pass')
    source = doc('source-manifest-03.json', args.source_manifest_sha256)
    preservation = doc('preservation-check-03.json', args.preservation_sha256)
    result = doc('result-summary.json', args.result_summary_sha256)
    next_work = doc('next-work.json', args.next_work_sha256)
    g.require(result['schema'] == 'terminal-nomination-identity-result-summary@1'
        and next_work['schema'] == 'terminal-nomination-identity-next-work@1', 'Exact final summary/work schemas required')
    for value in (result, next_work):
        for claim in ('full_task_satisfaction_established', 'source_equivalence_proved', 'model_convergence_proved',
                'provider_total_session_token_savings_established'):
            g.require(value[claim] is False, 'Final summary/work claim must remain explicitly false: ' + claim)
    for claim in ('proof_authority', 'execution_authority', 'completion_authority'):
        g.require(next_work[claim] is False, 'Next-work instruction is not authority: ' + claim)
    scope = g.source_scope(O / 'additional-identity-baseline-03.json', g.ADDITIONAL_BASELINE_SHA, '03',
        O / 'supplemental-test-baseline-03.json', g.SUPPLEMENTAL_TEST_SHA)
    heads = g.final_sources(source, scope)
    g.require(len(heads) == 11 and len(scope['before']) == 8 and preservation['all_checks_passed'] is True,
        'Exact gen03 eleven heads/eight original captures/qualified preservation required')
    for name, row in heads.items(): add(C / name, row['sha256'], row['bytes'])
    for row in scope['before'].values(): add(Path(row['baseline']), row['sha256'], row['bytes'])
    add(O / 'changes-03.patch', source['patch_sha256'], source['patch_bytes'])
    # Fixed N documents are metadata anchors; prior bodies are rechecked by
    # the separate preservation receipt, including its two exact probe streams.
    g.prior_stage_pins()
    g.require(len(NAMES) <= MAX_LITERAL_NAMES, 'Static literal whitelist exceeded')
    absent = []
    for name in sorted(NAMES):
        path = O / g.relative(name)
        try: os.lstat(path)
        except FileNotFoundError:
            g.require(name not in REQUIRED, 'Missing literal required artifact: ' + name)
            absent.append(name); continue
        add(path)
    focused = doc('focused-validation-03.json')
    g.require(focused['schema'] == 'terminal-nomination-identity-focused-validation@1'
        and type(focused['generation']) is int and focused['generation'] == 3
        and focused['all_passed'] is True and focused['all11_current_source_heads_match_final_freeze'] is True
        and focused['full_selected33_source_pins_unchanged'] is True,
        'Exact final generation03 test/source qualification required')
    for claim in ('full_task_satisfaction_established', 'source_equivalence_proved', 'model_convergence_proved',
            'provider_total_session_token_savings_established'):
        g.require(focused[claim] is False, 'Unit tests cannot establish: ' + claim)
    for row in (focused['complete_validation'], focused['default_validation'], focused['native_identity_validation'],
            focused['final_source_pins'], result['tests']['focused_validation']):
        pinned_doc(row)
    reports = focused['selected_reports']
    expected_reports = {'complete-focused-04.xml': 469, 'default-regression-03.xml': 149,
        'native-identity-tests-03.xml': 76, 'native-identity-sidechannel-tests-01.xml': 14}
    g.require(type(reports) is list and len(reports) == 4, 'Exact four selected report list required')
    g.require({str(Path(row['path']).relative_to(O)) for row in reports} == set(expected_reports),
        'Exact final generation03 selected reports required')
    keys, outcomes, selected, physical = set(), {'failures': 0, 'errors': 0, 'skips': 0}, [], 0
    for row in reports:
        g.require(type(row) is dict and set(row) == {'path', 'sha256', 'bytes', 'cases', 'distinct_cases'},
            'Closed selected XML descriptor required')
        pin = referenced_pin(row)
        _, raw = g.capture(Path(pin['path']), maximum=2_000_000, retain=True)
        cases = list(ET.fromstring(raw).iter('testcase'))
        report_keys = {normalized_case(case) for case in cases}
        expected_count = expected_reports[Path(pin['path']).name]
        g.require(len(cases) == g.count(row['cases']) == len(report_keys) == g.count(row['distinct_cases'])
            == expected_count, 'Exact physical/distinct per-report census required')
        physical += len(cases)
        for case in cases:
            keys.add(normalized_case(case))
            for label, element in (('failures', 'failure'), ('errors', 'error'), ('skips', 'skipped')):
                outcomes[label] += case.find(element) is not None
        selected.append({**pin, 'case_rows': len(cases)})
    g.require(not any(outcomes.values()), 'Latest selected reports must have zero failures/errors/skips')
    g.require(len(keys) == physical == g.count(focused['distinct_cases']) == g.count(focused['unique_count'])
        == g.count(focused['physical_selected_cases']) == 708 and g.count(focused['duplicate_cases']) == 0
        and set(focused['outcomes']) == {'error', 'failure', 'skipped'}
        and all(g.count(value) == 0 for value in focused['outcomes'].values()),
        'Final normalized union must be exactly708, with zero duplicate/failure/error/skip counts')
    g.require(result['tests']['all_passed'] is True and g.count(result['tests']['distinct_latest_cases']) == 708
        and g.count(result['tests']['duplicate_cases']) == 0, 'Final result test census must agree')
    native_identity = doc('native-identity-validation-02.json')
    g.require(native_identity['schema'] == 'supervisor-native-task-identity-validation@2'
        and native_identity['all_checks_passed'] is True and g.count(native_identity['latest_unique_count']) == 90,
        'Native identity union/source qualification required')
    pinned_doc(native_identity['prior_validation_receipt'])
    referenced_pin(native_identity['prior_unit_test_exact_reconstructed_capture'])
    for row in (result['package']['source_manifest'], result['package']['patch_qualification'],
            result['preservation']['receipt'], result['installed']['qualification'],
            result['installed']['independent_review'], result['independent_production_review'],
            result['source_analysis_amendment'], result['next_work']):
        pinned_doc(row)
    referenced_pin(result['package']['patch'])
    g.require(result['package']['source_manifest']['sha256'] == args.source_manifest_sha256
        and result['preservation']['receipt']['sha256'] == args.preservation_sha256
        and result['next_work']['sha256'] == args.next_work_sha256,
        'Summary package/preservation/work must join the independent supplied pins')
    g.require(result['preservation']['all_passed'] is True and result['preservation']['unexpected_deltas'] == []
        and g.count(result['preservation']['pin_checks']) == g.count(preservation['pin_checks']) == 1413
        and g.count(result['preservation']['unique_checked_paths']) == g.count(preservation['unique_checked_paths']) == 1065
        and g.count(result['preservation']['unique_hashed_paths']) == g.count(preservation['unique_hashed_paths']) == 1071,
        'Summary and qualified preservation census must join exactly')
    archive = doc('runtime-archive-fixed-03/manifest.json')
    verification = doc('runtime-archive-fixed-03-verification.json')
    actual = doc('actual-harbor-lifecycle-03/qualification.json')
    actual_review = doc('actual-lifecycle-03-independent-review.json')
    actual_sha = FILES[str(O / 'actual-harbor-lifecycle-03/qualification.json')]['sha256']
    actual_review_sha = FILES[str(O / 'actual-lifecycle-03-independent-review.json')]['sha256']
    g.require(next_work['based_on']['actual_qualification_sha256'] == actual_sha
        and next_work['based_on']['actual_independent_review_sha256'] == actual_review_sha
        and next_work['based_on']['source_manifest_sha256'] == args.source_manifest_sha256
        and result['package']['runtime_archive_sha256'] == archive['archive_sha256']
        and result['installed']['rendered_model_input_replay_verified'] is True
        and result['installed']['actual_lifecycle_qualified'] is False,
        'Final summary/work must bind this actual replay and its unqualified lifecycle')
    g.require(actual['schema'] == 'actual-nomination-identity-qualification@1' and actual['qualified'] is False
        and actual['rendered_model_input_replay_verified'] is True
        and actual['full_task_satisfaction_established'] is False and actual['source_equivalence_proved'] is False
        and actual['model_convergence_proved'] is False and actual['provider_total_session_token_savings_established'] is False,
        'Verified input replay must remain separate from unqualified lifecycle/task/source/model/token claims')
    g.require(actual_review['schema'] == 'terminal-nomination-identity-actual-independent-review@3'
        and actual_review['review_assertions_passed'] is True
        and actual_review['rendered_model_input_replay_qualified'] is True
        and actual_review['actual_observer_lifecycle_qualified'] is False,
        'Exact independent actual input-replay/lifecycle review required')
    g.require(actual['fresh_container_removed'] is True and actual['runtime_archive_sha256'] == archive['archive_sha256']
        == verification['archive_sha256'] and verification['all_members_match_declared_bytes_modes_and_digests'] is True,
        'Exact actual/runtime archive verification joins required')
    members = g.by_path(archive['files']); imports = actual['installed_import_provenance']['records']
    g.require(type(imports) is list and 1 <= len(imports) <= 32
        and actual['installed_import_provenance']['all_actual_imports_join_archive'] is True,
        'Bounded actual imported provenance required')
    for imported in imports:
        g.require(type(imported['uid']) is int and imported['uid'] == 0
            and type(imported['path']) is str and imported['path'].startswith('/opt/ipfs-supervisor/source/'),
            'Protected imported source')
        member = members.get('source/' + imported['path'].removeprefix('/opt/ipfs-supervisor/source/'))
        g.require(member is not None and member['bytes'] == imported['bytes'] and member['sha256'] == imported['sha256'],
            'Actual imported producer differs from that archive')
    for name, recorded in g.witnesses.items():
        handle, parent, info = g.opened(Path(name))
        try: g.require(g.witness(info) == recorded == g.witness(os.stat(Path(name).name, dir_fd=parent, follow_symlinks=False)),
                'Named witness changed before sealing')
        finally: os.close(handle); os.close(parent)
    value = {'schema': 'terminal-nomination-identity-explicit-public-evidence-seal@1', 'stage': str(O),
        'checkout': str(C), 'files': [FILES[name] for name in sorted(FILES)], 'file_count': len(FILES),
        'source_count': len(heads), 'original_capture_count': len(scope['before']), 'generation': '03',
        'pin_joins': PINS, 'all_named_guards_passed': True, 'final_review_sha256': args.final_review_sha256,
        'source_manifest_sha256': args.source_manifest_sha256, 'preservation_sha256': args.preservation_sha256,
        'result_summary_sha256': args.result_summary_sha256, 'next_work_sha256': args.next_work_sha256,
        'selected_reports': selected, 'distinct_latest_test_cases': len(keys), 'latest_outcomes': outcomes,
        'actual03_qualified_reported': actual['qualified'], 'actual03_container_removed': True,
        'actual03_rendered_model_input_replay_verified': True, 'actual03_overall_lifecycle_qualified': False,
        'actual_imported_producer_count': len(imports), 'all_actual_imports_join_archive_manifest': True,
        'optional_literal_names_absent': absent, 'previous_generation_reports_counted_in_latest_tests': False,
        'recursive_filesystem_discovery': False, 'archive_bodies_reopened': False, 'database_or_key_or_auth_or_raw_log_bodies_read': False,
        'prior_n_mutation': False, 'source_or_git_mutation': False, 'tests_or_provider_jobs_executed_here': False,
        'source_semantics_or_equivalence_proved': False, 'model_convergence_proved': False,
        'task_success_or_provider_zero_billing_or_token_savings_inferred_by_seal': False}
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    summary = {'dry_run': args.dry_run, 'all_named_guards_passed': True, 'file_count': len(FILES),
        'manifest_bytes': len(raw), 'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'distinct_latest_cases': len(keys)}
    if not args.dry_run:
        with output.open('xb') as stream: stream.write(raw)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
