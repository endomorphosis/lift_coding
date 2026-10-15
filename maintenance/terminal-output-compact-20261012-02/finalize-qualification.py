#!/usr/bin/env python3
"""Seal authored and live evidence without treating missing usage as zero."""
from pathlib import Path
import hashlib
import json
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
HEAD = '487647c68f8a419cd39586b4bd5eb2de8fc54012'
ARCHIVE = '54a2b6f65ac03a7b4694b7029333a66627aa8be0bbccbf16156f25b244aaf6b7'


def read(name):
    return json.loads((ROOT / name).read_text())


assert subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() == HEAD
assert not subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain'], text=True).strip()
benchmark = read('benchmark.json')
assert benchmark['source_commit'] == HEAD and benchmark['archive_sha256'] == ARCHIVE
assert not benchmark['all_trials_comparison_eligible']
rows = benchmark['trials']
assert rows[0]['official_reward'] == 1.0 and rows[0]['complete_tokens']['total_tokens'] == 460754
assert rows[1]['official_reward'] == 0.0 and rows[1]['complete_tokens']['total_tokens'] is None
assert all(row['state'] == 'pending' for row in rows[2:])
halt = read('independent-halt-review.json')
assert halt['all_checks_passed'] and halt['check_count'] == 41
assert halt['source_commit'] == HEAD and halt['archive_sha256'] == ARCHIVE
assert halt['benchmark_sha256'] == hashlib.sha256((ROOT / 'benchmark.json').read_bytes()).hexdigest()
assert halt['resources']['all_owned_project_containers_absent']
assert halt['trials'][1]['failure_reason_code'] == 'rate_limit'
install = read('fresh-installer-probe/report.json')
assert install['completed'] and install['owned_container_absent']
assert read('source-validation.json')['source_files_stable']
assert read('source-validation.json')['test_counts'] == dict(tests=719, passed=713, skipped=6, errors=0, failures=0)
review = read('independent-review.json')
assert review['check_count'] == 71 and sum(c['passed'] for c in review['checks']) == 66
wire = read('authored-wire-comparison.json')
fixture = next(row for row in wire['rows'] if row['case'] == 'ascii_stdout_4096')
legacy_bytes = fixture['legacy']['read_1024_byte_middle_page']['capture_plus_read_cli_bytes']
compact_bytes = fixture['compact']['read_1024_byte_middle_page']['capture_plus_read_cli_bytes']
report = {
    'schema': 'terminal-output-compact-installer-qualification@1',
    'created_at': datetime.now(timezone.utc).isoformat(),
    'status': 'live_comparison_incomplete_after_provider_rate_limit',
    'source_commit': HEAD, 'archive_sha256': ARCHIVE, 'source_worktree_clean': True,
    'local_commits': ['4185bcabd7580a59d4afe34663df02158f693ba5', HEAD],
    'pushed_to_remote': False, 'default_output_policy': 'legacy',
    'experimental_output_policy': 'artifact-preview@2',
    'source_tests': read('source-validation.json')['test_counts'],
    'root_bundle_tests': {'passed': 6, 'skipped_nonroot_only_case': 1},
    'campaign_tool_tests': read('recovery-tooling-validation.json')['tests'],
    'independent_compact_checks': 129, 'independent_installer_process_probes': 4,
    'fresh_arm64_install': {'passed': True, 'owned_container_absent': True,
        'provider_calls': 0, 'seconds': read('fresh-installer-probe/report.json')['elapsed_seconds']},
    'installer_architectures': ['Linux ARM64', 'Linux x86-64'],
    'x86_64_qualification_scope': 'Official registry integrity and binary hashes verified; hermetic architecture tests passed; no native x86-64 execution on this ARM64 host.',
    'authored_wire_example': {'fixture': '4096-byte ASCII capture plus one 1024-byte exact retrieval',
        'legacy_cli_json_bytes': legacy_bytes, 'compact_cli_json_bytes': compact_bytes,
        'reduction_percent': (1 - compact_bytes / legacy_bytes) * 100,
        'provider_token_measurement': False},
    'requested_trials': 4, 'settled_trials': 2, 'unstarted_trials': 2,
    'trial_outcomes': [{'trial': row['name'], 'policy': row['requested_policy'],
        'state': row['state'], 'official_reward': row.get('official_reward'),
        'total_tokens': row['complete_tokens']['total_tokens'],
        'comparison_eligible': row['comparison_eligible']} for row in rows],
    'failed_treatment_reason': {'phase': 'planning', 'provider_reason_code': 'rate_limit',
        'coding_invoked': False, 'compact_advisory_observed': False,
        'token_usage_known': False, 'hard_quota_or_reset_time_established': False},
    'live_comparison_eligible': False, 'live_token_savings_established': False,
    'compact_wire_format_adoption_established': False,
    'independent_live_verifier': {'checks': 71, 'passed': 66,
        'failed_qualification_requirements': ['compact coding phase absent', 'compact exact input audit absent',
            'compact advisory unobserved', 'compact worker cleanup census unknown', 'compact helper census absent']},
    'halt_review': halt,
    'previous_failed_campaign': '../terminal-output-compact-20261012-01/qualification.json',
    'limitations': [
        'Subset pytest counts overlap the combined source suite and are not additional cases.',
        'Smaller helper JSON is not evidence of lower native provider tokens or billing.',
        'The rate-limited treatment remains in its requested arm; unknown usage is not zero.',
        'The compact policy never reached coding in the failed trial, so policy effectiveness cannot be inferred.',
        'A native session completion event does not establish accounting completeness or task success.',
        'The current helper-use receipts do not observe per-call response-format selection.',
        'Resource backoff passed authored simulations; this campaign did not inject live external pressure.',
        'Sampled resource health does not guarantee system stability.',
    ],
    'next_gaps': [
        'Add explicit provider-stop metadata and keep session closure separate from usage completeness.',
        'Record bounded per-call response-format emission metadata without raw command content.',
        'After provider availability is established, prepare a fresh balanced comparison and retain both prior campaigns.',
        'Require repeated task success and complete native usage before considering a default policy change.',
    ],
}
evidence = ['benchmark.json', 'benchmark.csv', 'comparison-protocol.json', 'launcher-protocol.json',
    'source-freeze.json', 'source-validation.json', 'recovery-tooling-validation.json',
    'authored-wire-comparison.json', 'independent-compact-probes.json',
    'independent-installer-process-probes.json', 'independent-installer-frozen-binding.json',
    'independent-preparation-review.json', 'independent-review.json', 'independent-halt-review.json',
    'fresh-installer-probe/report.json', 'official-codex-linux-x64-0.160.0-pins.json',
    'recovery-provenance.json', 'tooling-amendment.json', 'finalize-qualification.py']
report['evidence_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in evidence}
with (ROOT / 'qualification.json').open('x') as stream:
    json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
    stream.write('\n')
print(json.dumps({'status': report['status'], 'comparison_eligible': False,
                  'qualification_sha256': hashlib.sha256((ROOT / 'qualification.json').read_bytes()).hexdigest()}))
