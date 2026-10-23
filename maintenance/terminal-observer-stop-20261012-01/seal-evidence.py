"""Seal explicit public P evidence only; --dry-run never publishes a manifest."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import types
import xml.etree.ElementTree as ET

P = Path('/home/barberb/lift_coding/maintenance/terminal-observer-stop-20261012-01')
CHECKER_SHA = '7126ae6981c4e33bfa3c46201672c93d91c2296358eea6885a1174a5ab977b05'
raw = (P / 'check-preservation.py').read_bytes()
if hashlib.sha256(raw).hexdigest() != CHECKER_SHA:
    raise ValueError('Frozen public checker changed')
m = types.ModuleType('p_explicit_public_guards'); m.__file__ = str(P / 'check-preservation.py')
exec(compile(raw, m.__file__, 'exec'), m.__dict__)
g, C = m.g, m.C

REQUIRED = (
    'baseline-manifest.json', 'baseline-manifest-02.json', 'final-source-pins.json',
    'source-manifest.json', 'changes.patch', 'patch-qualification.json', 'preservation-check.json',
    'focused-validation.json', 'root-focused-03.xml', 'new-stop-tests-03.xml', 'new-stop-validation-03.json',
    'focused-validation-independent-review.json', 'package-validation-independent-review.json',
    'actual-lifecycle-independent-review.json', 'final-review.json', 'result-summary.json', 'next-work.json',
    'runtime-archive/manifest.json', 'runtime-archive-verification.json',
    'package-helper.py', 'check-preservation.py', 'seal-evidence.py', 'experiment-plan.json',
    'actual-harbor-lifecycle/qualification.json',
)
OPTIONAL = (
    'root-wiring-review.json', 'current-helper-review.json', 'final-review-prewrite-attempt-01.json',
    'root-focused-01.xml', 'root-focused-02.xml', 'new-stop-tests-01.xml', 'new-stop-tests-02.xml',
    'root-focused-01.stdout', 'root-focused-01.stderr', 'root-focused-02.stdout', 'root-focused-02.stderr',
    'root-focused-03.stdout', 'root-focused-03.stderr',
    'new-stop-tests-01.stdout', 'new-stop-tests-01.stderr', 'new-stop-tests-02.stdout', 'new-stop-tests-02.stderr',
    'new-stop-tests-03.stdout', 'new-stop-tests-03.stderr',
    'new-stop-validation-01.json', 'new-stop-validation-02.json',
    'new-stop-tests-source-pins-03-before.json', 'new-stop-tests-source-pins-03-after.json',
    'root-focused-source-pins-before-03.json', 'root-focused-source-pins-after-03.json',
    'package-helper.py.before-scope-expansion', 'check-preservation.py.before-scope-expansion',
    'packaging.stdout', 'packaging.stderr', 'preservation.stdout', 'preservation.stderr',
    'public-task-metadata.json', 'public-task-image.json', 'experiment-plan-02.json',
    'public-task-inputs/instruction.md', 'public-task-inputs/task.toml', 'public-task-inputs/environment/Dockerfile',
    'public-task-inputs/reviewed-intent-contract.json',
    'qualify-retained-harbor.py', 'build-runtime.py', 'build-pinned-runtime.py', 'build-results.py',
    'runtime-archive-build.stdout', 'runtime-archive-build.stderr',
)
ACTUAL = (
    'named-owner-public-metadata.stdout', 'named-owner-public-metadata.stderr',
    'installed-import-provenance.stdout', 'installed-import-provenance.stderr', 'original-head.txt',
    'deployment/deployment.json', 'worker-boundary/deployment.json',
    'worker-boundary/installation/installation.json', 'worker-boundary/qualification/qualification.json',
    'lifecycle/controller-result.json', 'lifecycle/baseline.json', 'lifecycle/template.json',
    'lifecycle/authored-review.json', 'lifecycle/prepare_only-attempt.json', 'lifecycle/resume-attempt.json',
    'lifecycle/prepare_only-execution.json', 'lifecycle/resume-execution.json',
    'lifecycle/prepare_only-public-report.json', 'lifecycle/resume-public-report.json',
)
NAMES = set(REQUIRED) | set(OPTIONAL) | {'actual-harbor-lifecycle/' + name for name in ACTUAL}
NAMES |= {'baseline/' + name for name in m.EXISTING}
FILES = {}


def add(path, sha=None, size=None):
    path = g.public_path(path)
    g.require(path.is_relative_to(P) or path.is_relative_to(C), 'Only explicit P/current-source files')
    pin, _ = g.capture(path, maximum=4_000_000)
    g.require((sha is None or pin['sha256'] == g.digest(sha)) and
        (size is None or pin['bytes'] == g.count(size)), 'Explicit artifact pin differs')
    FILES[str(path)] = pin
    g.require(len(FILES) <= 160 and sum(x['bytes'] for x in FILES.values()) <= 32_000_000,
        'Named public census/bytes exceeded')
    return pin


def doc(name, sha=None):
    add(P / name, sha)
    return g.document(P / name, sha)


def named_pin(row):
    path = g.public_path(row['path'])
    g.require(path.is_relative_to(P) and path.relative_to(P).as_posix() in NAMES, 'Unlisted public pin')
    return add(path, row['sha256'], row['bytes'])


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('source-manifest', 'preservation', 'final-review', 'result-summary', 'next-work'):
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--dry-run', action='store_true'); args = parser.parse_args()
    output = P / 'evidence-manifest.json'
    g.require(not output.exists() and not output.is_symlink(), 'No existing seal replacement')
    review = doc('final-review.json', args.final_review_sha256)
    g.require(review['schema'] == 'terminal-observer-stop-final-independent-review@1'
        and review['review_passed'] is True and review['blocking_findings'] == [], 'Scoped final review must pass')
    source = doc('source-manifest.json', args.source_manifest_sha256)
    preservation = doc('preservation-check.json', args.preservation_sha256)
    result = doc('result-summary.json', args.result_summary_sha256)
    work = doc('next-work.json', args.next_work_sha256)
    g.require(result['schema'] == 'terminal-observer-stop-result-summary@1'
        and work['schema'] == 'terminal-observer-stop-next-work@1'
        and all(x is False for x in result['claims_not_established'].values())
        and all(x is False for x in work['claims_not_yet_established'].values()), 'No expanded task/proof/billing claims')
    before = m.baseline(); heads = m.final_sources(source, before, source_manifest=True)
    g.require(len(heads) == 6 and len(before) == 4 and preservation['all_checks_passed'] is True
        and g.count(preservation['pin_checks']) == 1667 and preservation['prior_o_sealed_entries'] == 186
        and preservation['prior_o_logical_rows'] == 1413 and preservation['unexpected_deltas'] == [],
        'Exact six-head/four-capture qualified preservation')
    for name, row in heads.items(): add(C / name, row['sha256'], row['bytes'])
    for row in before.values(): add(Path(row['baseline_path']), row['sha256'], row['bytes'])
    add(P / 'changes.patch', source['patch_sha256'], source['patch_bytes'])
    absent = []
    for name in sorted(NAMES):
        path = P / name
        try: os.lstat(path)
        except FileNotFoundError:
            g.require(name not in REQUIRED, 'Missing required explicit artifact: ' + name)
            absent.append(name); continue
        add(path)
    for row in result['evidence']: named_pin(row)
    focused = doc('focused-validation.json'); cases = set(); selected = []
    g.require(focused['qualified'] is True and focused['previous_cached_or_failed_runs_counted'] is False
        and focused['all_six_source_heads_match_before_and_after'] is True, 'Current executed tests required')
    for row in focused['groups']:
        pin = named_pin(row)
        g.require(Path(pin['path']).name in {'root-focused-03.xml', 'new-stop-tests-03.xml'}, 'Exact selected XML')
        _, raw = g.capture(Path(pin['path']), maximum=2_000_000, retain=True)
        nodes = list(ET.fromstring(raw).iter('testcase'))
        keys = {(x.attrib['classname'], x.attrib['name']) for x in nodes}
        g.require(len(nodes) == len(keys) == g.count(row['executed']) == g.count(row['passed'])
            and keys == {tuple(x) for x in row['cases']} and all(x.find('failure') is None
                and x.find('error') is None and x.find('skipped') is None for x in nodes), 'Executed passing XML census')
        cases |= keys; selected.append({**pin, 'executed_cases': len(nodes)})
    g.require(len(selected) == 2 and len(cases) == g.count(focused['distinct_executed_passed_cases']) == 408
        and all(g.count(focused[k]) == 0 for k in ('failed', 'errors', 'skipped')), 'Exact408 distinct passing tests')
    qualification = doc('patch-qualification.json')
    g.require(qualification['qualified'] is True and qualification['git_apply_check_passed'] is True
        and qualification['git_apply_passed'] is True, 'Qualified clean source patch')
    archive = doc('runtime-archive/manifest.json'); verification = doc('runtime-archive-verification.json')
    actual = doc('actual-harbor-lifecycle/qualification.json'); actual_review = doc('actual-lifecycle-independent-review.json')
    g.require(actual['schema'] == 'actual-observer-stop-qualification@1' and actual['qualified'] is True
        and actual['rendered_model_input_replay_verified'] is True and actual['fresh_container_removed'] is True
        and actual['lifecycle']['qualified'] is True and actual['lifecycle']['task_completed'] is False
        and actual['lifecycle']['provider_usage_or_billing_complete'] is False
        and actual['lifecycle']['official_wall_budget_qualified'] is False
        and actual['environment_call_counts'] == {'start': 1, 'stop': 1}
        and all(type(actual['environment_call_counts'][k]) is int for k in ('start', 'stop')),
        'Actual observer-only clean lifecycle')
    g.require(actual_review['schema'] == 'actual-observer-stop-independent-review@1'
        and actual_review['review_passed'] is True and actual_review['blocking_findings'] == [], 'Actual peer review required')
    g.require(actual['runtime_archive_sha256'] == archive['archive_sha256'] == verification['archive_sha256']
        and verification['all_members_match_declared_bytes_modes_and_digests'] is True, 'Verified exact archive metadata join')
    members = g.by_path(archive['files']); imports = actual['installed_import_provenance']['records']
    g.require(type(imports) is list and len(imports) == 23
        and actual['installed_import_provenance']['all_actual_imports_join_archive'] is True, 'Exact23 imported producers')
    for row in imports:
        g.require(type(row['uid']) is int and row['uid'] == 0 and row['path'].startswith('/opt/ipfs-supervisor/source/'),
            'Protected imported producer')
        member = members['source/' + row['path'].removeprefix('/opt/ipfs-supervisor/source/')]
        g.require(member['bytes'] == row['bytes'] and member['sha256'] == row['sha256'], 'Imported producer/archive join')
    m.final_witnesses()
    value = {'schema': 'terminal-observer-stop-explicit-public-evidence-seal@1', 'stage': str(P),
        'files': [FILES[name] for name in sorted(FILES)], 'file_count': len(FILES), 'source_count': 6,
        'original_capture_count': 4, 'all_named_guards_passed': True, 'selected_reports': selected,
        'distinct_executed_passed_cases': 408, 'preservation_checks': 1667, 'prior_o_sealed_entries': 186,
        'prior_o_logical_rows': 1413, 'actual_imported_producer_count': 23, 'actual_observer_lifecycle_qualified': True,
        'source_manifest_sha256': args.source_manifest_sha256, 'preservation_sha256': args.preservation_sha256,
        'final_review_sha256': args.final_review_sha256, 'result_summary_sha256': args.result_summary_sha256,
        'next_work_sha256': args.next_work_sha256, 'optional_literal_names_absent': absent,
        'archive_or_raw_log_database_auth_key_bodies_read': False, 'recursive_discovery': False,
        'source_or_prior_stage_mutation': False, 'provider_or_native_or_test_jobs_executed_here': False,
        'source_equivalence_or_model_convergence_proved': False, 'full_task_or_provider_billing_or_token_savings_established': False}
    raw = m.canonical(value)
    if not args.dry_run: m.exclusive(output, raw)
    print(json.dumps({'dry_run': args.dry_run, 'all_named_guards_passed': True, 'files': len(FILES),
        'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}))


if __name__ == '__main__': main()
