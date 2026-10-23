"""Seal only explicit public receipts and scripts; never discover private state."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
PRIOR = ROOT.parent / 'terminal-compact-retrieval-20261011-01'
FILES = [
    'continuation-baseline.json', 'build-pinned-runtime-v13.py',
    'runtime-archive-verification-v13.json', 'runtime-archive-v13/manifest.json',
    'compact-worker-probe.py', 'compact-worker-probe-adaptation.json',
    'installed-full-audit-probe.py', 'probe-adaptation-review.json',
    'qualify-installed-runtime.py', 'installed-qualification-01/qualification.json',
    'installed-qualification-review.json', 'protocol-readiness.json', 'protocol-review.json',
    'probe-review.json', 'controller-static-review-01.json', 'full-audit-independent-review.json',
    'experiment-controls-review.json', 'usage-review.json', 'postrun-review.json',
    'prior-usage-diagnostics.json', 'wire-delivery-next-step.json', 'source-grounding-next-step.json',
    'pilot/code-expanded-01/preparation.json', 'pilot/code-expanded-01/config.json',
    'pilot/code-expanded-01/receipt.json', 'pilot/code-compact-01/preparation.json',
    'pilot/code-compact-01/config.json', 'pilot/code-compact-01/receipt.json',
    'comparison-01/comparison.json', 'comparison-01/comparison.md',
    'build-experiment-summary.py', 'result-summary.json', 'next-work.json', 'seal-evidence.py',
]
entries = []
for relative in FILES:
    path = ROOT / relative
    assert path.is_file() and not path.is_symlink(), relative
    raw = path.read_bytes()
    entries.append({'path': relative, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
source_path = PRIOR / 'source-manifest-final.json'
sources = json.loads(source_path.read_text())
checkout = Path(sources['checkout'])
assert all(hashlib.sha256((checkout / row['path']).read_bytes()).hexdigest() == row['after_sha256']
    and (checkout / row['path']).stat().st_size == row['after_bytes'] for row in sources['files'])
qualification = json.loads((ROOT / 'installed-qualification-01/qualification.json').read_text())
assert qualification['qualified'] is True and qualification['qualification_container_removed'] is True
summary = json.loads((ROOT / 'result-summary.json').read_text())
assert summary['retained_attempt_count'] == 4
assert summary['current_pair']['verified_inputs_both'] is True
assert summary['current_pair']['official_pass_and_native_completion_both'] is True
assert summary['current_pair']['complete_usage_both'] is True
assert summary['current_pair']['post_publication_refresh_complete_both'] is False
report = {
    'schema': 'terminal-retrieval-qualified-pair-public-evidence-manifest@1',
    'files': entries,
    'enumeration': 'Explicit public evidence allowlist; no recursive discovery.',
    'source_manifest': str(source_path),
    'source_manifest_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
    'all_18_source_files_unchanged': True,
    'prior_534_focused_test_reference': str(PRIOR / 'validation-summary-final.json'),
    'prior_focus_tests_not_repeated_without_source_changes': True,
    'qualified_new_runtime_and_both_live_input_audits': True,
    'compact_post_publication_refresh_incomplete_not_reclassified': True,
    'old_failed_attempt_not_reclassified': True,
    'raw_model_rollouts_hidden_verifier_content_credentials_private_keys_and_databases_excluded': True,
    'original_dirty_checkout_or_git_index_mutated_by_this_work': False,
    'github_or_huggingface_publication_performed': False,
}
(ROOT / 'evidence-manifest.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({'public_files': len(entries), 'source_files_unchanged': len(sources['files']),
    'retained_attempts': summary['retained_attempt_count']}))
