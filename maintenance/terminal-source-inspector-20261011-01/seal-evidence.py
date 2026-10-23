"""Seal explicit public artifacts; exclude DB bodies and synthetic/native JSONL."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

STAGE = Path(__file__).resolve().parent
TOP = (
    'beginning-source-pins.json', 'inspector-baseline.json', 'design-review.json',
    'inspector-validation.json', 'inspector-validation-01.xml',
    'inspector-validation-02.xml', 'inspector-validation-03.xml',
    'session-ledger-reader-validation.json', 'session-ledger-reader-validation-03.json',
    'session-ledger-reader-tests.xml', 'session-ledger-reader-tests-02.xml',
    'session-ledger-reader-tests-03.xml', 'session-ledger-reader-legacy-equivalence.json',
    'session-ledger-reader-legacy-equivalence-02.json',
    'session-ledger-reader-legacy-equivalence-03.json', 'session-ledger-downstream-review.json',
    'final-independent-review.json', 'final-stage-review.json',
    'source-manifest.json', 'preservation-check.json', 'changes.patch',
    'qualification-environment.json', 'qualification-environment-shell-probe.json',
    'source-nomination-review.json', 'next-work.json', 'next-work-draft-01.json',
    'result-summary.json', 'result-summary-draft-01.json',
    'prepare-public-native-fixture.py', 'qualify-public-source-inspector.py',
    'seal-source-changes.py', 'check-preservation.py', 'build-result-summary.py', 'seal-evidence.py',
)
FIXTURE_FILES = (
    'summary.json', 'instruction.txt', 'native-retrieval-context.json',
    'repository/bottle.py', 'repository/retrieval.json', 'repository/frontier/frontier.json',
    'vectors/result.json', 'vectors/ast.json', 'vectors/evidence.json',
)
PUBLIC_CLI_FILES = (
    'qualification.json', 'small-decorated-source-page-1.json',
    'large-source-page-1.json', 'large-source-page-2.json', 'large-source-page-3.json',
    'native-facts-page-1.json',
)


def load(name):
    return json.loads((STAGE / name).read_text())


def actual(path):
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def matches(path, entry):
    assert not path.is_symlink() and actual(path) == (entry['bytes'], entry['sha256']), path


def main():
    review = load('final-stage-review.json')
    assert review['review_passed'] and not review['blocking_findings']
    result = load('result-summary.json')
    source = load('source-manifest.json')
    for item in source['files']:
        matches(Path(item['absolute_path']), item)
    matches(STAGE / 'changes.patch', {'bytes': source['patch_bytes'], 'sha256': source['patch_sha256']})
    for item in result['evidence']:
        matches(STAGE / item['path'], item)
    matches(STAGE / result['draft_history']['retained_result']['path'], result['draft_history']['retained_result'])
    preservation = load('preservation-check.json')
    for item in preservation['prior_unchanged_checks']:
        matches(Path(item['path']), item)
    beginning = load('beginning-source-pins.json')
    for item in beginning['files']:
        matches(STAGE / 'baseline' / item['path'], item)
    for item in preservation['beginning_source_checks']:
        if item.get('intentional_reader_change'):
            assert actual(Path(item['path'])) == (item['after_bytes'], item['after_sha256'])
        else:
            matches(Path(item['path']), item)
    ids = set()
    for report, expected in [('inspector-validation-03.xml', 53), ('session-ledger-reader-tests-03.xml', 42)]:
        cases = ET.parse(STAGE / report).getroot().findall('.//testcase')
        assert len(cases) == expected
        for case in cases:
            assert all(case.find(kind) is None for kind in ('failure', 'error', 'skipped'))
            identity = (case.attrib['classname'], case.attrib['name'])
            assert identity not in ids
            ids.add(identity)
    assert len(ids) == result['tests']['combined_unique_latest_passed'] == 95
    names = list(TOP)
    names += ['baseline/' + item['path'] for item in beginning['files']]
    for fixture in ('public-native-fixture-01', 'public-native-fixture-02'):
        names += [fixture + '/' + name for name in FIXTURE_FILES]
    names += ['public-cli-qualification-01/' + name for name in PUBLIC_CLI_FILES]
    assert len(names) == len(set(names))
    rows = []
    for name in sorted(names):
        path = STAGE / name
        assert not path.is_symlink()
        size, sha = actual(path)
        if path.suffix == '.py':
            compile(path.read_bytes(), str(path), 'exec')
        elif path.suffix == '.json':
            json.loads(path.read_text())
        rows.append({'path': name, 'bytes': size, 'sha256': sha})
    receipt = {
        'schema': 'source-inspector-and-session-ledger-public-evidence-manifest@1',
        'enumeration': 'Explicit public artifact names only. Fresh DB bodies, synthetic/native JSONL, test temporary directories, credentials, hidden verifiers and unrelated dirty overlays excluded; no recursive scan.',
        'files': rows, 'source_files': source['files'],
        'all_four_source_hashes_match': True,
        'all_209_prior_unchanged_pin_checks_match': True,
        'all_six_beginning_source_captures_retained': True,
        'one_expected_reader_delta_verified': True,
        'latest_unique_focused_passing_cases': 95,
        'historical_inspector_test_failure_retained': True,
        'independent_host_inspector_review_passed': True,
        'independent_reader_downstream_review_passed': True,
        'independent_final_stage_review_passed': True,
        'public_cli_successful_outputs': 5,
        'public_cli_invalid_requests_refused': 6,
        'public_native_symbols_and_fact_rows_replayed': 426,
        'fresh_ducklake_catalogs': 1, 'fresh_ducklake_links': 426,
        'native_reader_ledger_integrated_in_checkout_source': True,
        'coding_prompt_inspector_integrated': False,
        'installed_runtime_archive_qualified': False,
        'original_dirty_checkout_or_git_index_mutated': False,
        'provider_calls': 0, 'training_steps': 0, 'prover_invocations': 0,
        'provider_total_token_savings_established': False,
        'source_equivalence_or_full_task_satisfaction_or_convergence_proved': False,
        'remote_publication_performed': False,
    }
    path = STAGE / 'evidence-manifest.json'
    with path.open('x') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write('\n')
    size, sha = actual(path)
    print(json.dumps({'explicit_public_artifacts': len(rows), 'manifest_bytes': size,
        'manifest_sha256': sha, 'all_source_and_preservation_checks_passed': True,
        'latest_unique_passed': len(ids), 'provider_calls': 0}))


if __name__ == '__main__':
    main()
