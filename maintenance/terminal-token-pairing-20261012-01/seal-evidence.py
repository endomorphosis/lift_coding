"""Seal an explicit public Q evidence set; no task/log/database/archive bodies."""
import hashlib
import json
import os
from pathlib import Path
import stat
import types

Q = Path(__file__).resolve().parent
P = Q.parent / 'terminal-observer-stop-20261012-01'
C = Q.parent / 'terminal-token-reduction-20261007-01/checkout'
CHECKER_SHA = '4cf2d9a1813aee89b73aed33502b6e7a55748b1393f672b3ef90eba7e3ef0a92'
P_SEAL_SHA = 'f7b244a10e6b17daea6c359d01d754ad8be3da45af97a65e0d431a22e1bd0a96'
NAMES = [
    'seal-evidence.py', 'write-result-summary.py', 'result-summary.json', 'next-work.json', 'final-review.json',
    'baseline-manifest.json', 'experiment-plan.json', 'runtime-source-pins.json', 'final-source-pins.json',
    'source-manifest.json', 'package-changes.py', 'changes.patch', 'patch-qualification.json',
    'package-independent-review.json',
    'build-pinned-runtime.py', 'qualify-retained-harbor.py', 'harness-preparation.json',
    'runtime-archive/manifest.json', 'runtime-archive-verification.json',
    'runtime-head-pins-before-build.json', 'runtime-head-pins-after-build.json',
    'runtime-head-pins-before-actual.json', 'runtime-head-pins-after-actual.json',
    'public-input-copy.json', 'public-task-metadata.json', 'public-task-image.json',
    'public-task-inputs/instruction.md', 'public-task-inputs/task.toml',
    'public-task-inputs/environment/Dockerfile', 'public-task-inputs/reviewed-intent-contract.json',
    'run-final-focused.py', 'root-final-02-before.json', 'root-final-02-run.json',
    'root-final-02.xml', 'root-final-02.stdout', 'root-final-02.stderr',
    'root-focused-01.xml', 'paired-tests-01.xml', 'paired-tests-01-failure-analysis.json',
    'paired-tests-02.xml', 'paired-validation-02.json', 'focused-validation.json',
    'focused-validation-independent-review.json', 'focused-aggregation-independent-review.json',
    'static-runtime-independent-review.json', 'check-preservation.py', 'preservation-check.json',
    'actual-token-pair-independent-review.json', 'actual-token-comparison-independent-review.json',
    'actual-lifecycle-independent-review.json',
    'actual-lifecycle-independent-review-01.json', 'actual-lifecycle-independent-review-02.json',
    'actual-harbor-token-pair-01/qualification.json', 'actual-harbor-token-pair-01/deployment/deployment.json',
    'actual-harbor-token-pair-01/local-tokenizer-setup.stdout',
    'actual-harbor-token-pair-01/local-tokenizer-setup.stderr',
    'actual-harbor-token-pair-01/local-tokenizer-supervisor-probe.stdout',
    'actual-harbor-token-pair-01/local-tokenizer-supervisor-probe.stderr',
    'actual-harbor-token-pair-01/installed-import-provenance.stdout',
    'actual-harbor-token-pair-01/installed-import-provenance.stderr',
    'actual-harbor-token-pair-01/named-owner-public-metadata.stdout',
    'actual-harbor-token-pair-01/named-owner-public-metadata.stderr',
    'actual-harbor-token-pair-01/lifecycle/prepare_only-attempt.json',
    'actual-harbor-token-pair-01/lifecycle/prepare_only-execution.json',
    'actual-harbor-token-pair-01/lifecycle/prepare_only-public-report.json',
    'actual-harbor-token-pair-01/lifecycle/resume-attempt.json',
    'actual-harbor-token-pair-01/lifecycle/resume-execution.json',
    'actual-harbor-token-pair-01/lifecycle/resume-public-report.json',
    'actual-harbor-token-pair-01/lifecycle/baseline.json',
    'actual-harbor-token-pair-01/lifecycle/template.json',
    'actual-harbor-token-pair-01/lifecycle/authored-review.json',
    'actual-harbor-token-pair-01/lifecycle/controller-result.json',
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


path = Q / 'check-preservation.py'
fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
try:
    before = os.fstat(fd)
    assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == 14427
    with os.fdopen(fd, 'rb', closefd=False) as stream:
        raw = stream.read(14428)
    witness = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    assert witness(before) == witness(os.fstat(fd)) == witness(path.lstat()) and sha(raw) == CHECKER_SHA
finally:
    os.close(fd)
module = types.ModuleType('q_sealed_public_guards'); module.__file__ = str(path)
exec(compile(raw, str(path), 'exec'), module.__dict__)
_, g = module.load_p_guards()
assert g.capture(path)[0]['sha256'] == CHECKER_SHA


def document(name):
    pin, raw = g.capture(Q / name, retain=True)
    return json.loads(raw), pin


prior, raw = g.capture(P / 'evidence-manifest.json', retain=True)
assert prior['sha256'] == P_SEAL_SHA
sealed = json.loads(raw)
for row in sealed['files']:
    current, _ = g.capture(Path(row['path']))
    assert current['bytes'] == row['bytes'] and current['sha256'] == row['sha256']
pins, pins_pin = document('final-source-pins.json')
sources, sources_pin = document('source-manifest.json')
baseline, baseline_pin = document('baseline-manifest.json')
assert sources['baseline_manifest_sha256'] == baseline_pin['sha256']
assert sources['final_source_pins_sha256'] == pins_pin['sha256']
assert len(pins['files']) == 3
for row in pins['files']:
    current, _ = g.capture(C / row['path'])
    assert current['bytes'] == row['bytes'] and current['sha256'] == row['sha256']
    captured, _ = g.capture(Q / 'final-source' / row['path'])
    assert captured['bytes'] == row['bytes'] and captured['sha256'] == row['sha256']
    NAMES.append('final-source/' + row['path'])
assert len(baseline['files']) == 3
for row in baseline['files']:
    if row['exists']:
        captured, _ = g.capture(Path(row['capture']))
        assert captured['bytes'] == row['bytes'] and captured['sha256'] == row['sha256']
NAMES.append('baseline/benchmarks/agent_supervisor/container_coding/terminal_context_audit.py')
summary, summary_pin = document('result-summary.json')
review, review_pin = document('final-review.json')
next_work, next_pin = document('next-work.json')
tests, _ = document('focused-validation.json')
preservation, _ = document('preservation-check.json')
actual, _ = document('actual-harbor-token-pair-01/qualification.json')
pair = actual['named_report_export']['reports']['resume']['token_comparison']
assert summary['qualified'] is True and review.get('review_passed', review.get('qualified')) is True
assert not review.get('blocking_findings', review.get('blockers', []))
assert review['result_summary_sha256'] == summary_pin['sha256']
assert review['next_work_sha256'] == next_pin['sha256']
assert review['source_manifest_sha256'] == sources_pin['sha256']
assert review['final_source_pins_sha256'] == pins_pin['sha256']
assert review['sealer_sha256'] == g.capture(Q / 'seal-evidence.py')[0]['sha256']
assert summary['source_changes'] == sources['files']
assert tests['qualified'] is True and tests['distinct_executed_passed_cases'] == 100
assert all(tests[k] == 0 for k in ('skipped', 'failures', 'errors', 'duplicates'))
assert preservation['all_checks_passed'] is True and len(preservation['checks']) == 1760
assert actual['qualified'] is True and actual['fresh_container_removed'] is True
assert len(actual['installed_import_provenance']['records']) == 24
assert pair['tokens_saved'] == 7588 and pair['measurements']['expanded']['tokens'] == 33873
assert pair['measurements']['compact']['tokens'] == 26285 and pair['token_reduction_fraction'] == 7588 / 33873
assert pair['provider_usage_measured'] is False and pair['provider_invocations_created'] == 0
assert all(value is False for value in summary['claims_not_established'].values())
assert len(NAMES) == len(set(NAMES))
files = [g.capture(Q / name)[0] for name in NAMES]
# Recheck every selected witness before exclusive publication. This performs
# no provider, training, native supervisor, test or proof job.
for row in files:
    current, _ = g.capture(Path(row['path']))
    assert current['bytes'] == row['bytes'] and current['sha256'] == row['sha256']
value = {'schema': 'terminal-token-pair-evidence-manifest@1', 'stage': str(Q), 'files': files,
    'file_count': len(files), 'all_named_guards_passed': True, 'final_review_sha256': review_pin['sha256'],
    'result_summary_sha256': summary_pin['sha256'], 'next_work_sha256': next_pin['sha256'],
    'source_count': 3, 'distinct_final_executed_passed_cases': 100, 'preservation_checks': 1760,
    'prior_sealed_entries_rechecked': 77, 'actual_imported_producer_count': 24,
    'local_complete_input_token_savings_established': True, 'tokens_saved': 7588,
    'provider_total_session_token_savings_established': False, 'full_task_satisfaction_established': False,
    'source_equivalence_or_model_convergence_proved': False,
    'archive_or_raw_log_database_auth_key_bodies_read': False, 'recursive_discovery': False,
    'source_or_prior_stage_mutation': False, 'provider_native_training_test_proof_jobs_executed_here': False}
encoded = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
with (Q / 'evidence-manifest.json').open('xb') as stream:
    stream.write(encoded)
print(json.dumps({'sealed': True, 'file_count': len(files), 'sha256': sha(encoded)}))
