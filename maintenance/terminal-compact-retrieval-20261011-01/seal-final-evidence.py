"""Hash an explicit public-evidence allowlist without traversing private state."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).parent
FILES = [
    'changes.patch', 'source-manifest.json', 'changes-final.patch', 'source-manifest-final.json',
    'protocol-review.json', 'runtime-qualification-review.json', 'postrun-review.json',
    'usage-review.json', 'result-summary.json', 'validation-summary.json', 'validation-summary-final.json',
    'guidance-validation-receipt.json', 'guidance-validation.json', 'legacy-codec-replay.json',
    'next-work.json', 'next-work-after-pilot.json', 'audit-hardening.json',
    'audit-public-timing-07.json', 'audit-genuine-preparation-fix/report.json',
    'audit-genuine-preparation-fix/focused-01/result.json',
    'installed-qualification-01/qualification.json',
    'runtime-archive-verification.json', 'runtime-archive-verification-v11.json',
    'runtime-archive-verification-v12.json', 'runtime-v10-v11-delta.json', 'runtime-v10-v12-delta.json',
    'runtime-archive-v10/manifest.json', 'runtime-archive-v11/manifest.json', 'runtime-archive-v12/manifest.json',
    'pinned-dependencies-v10/snapshot-receipt.json',
    'comparison-01/comparison.json', 'comparison-followup-01/comparison.json',
    'pilot/code-expanded-01/receipt.json', 'pilot/code-expanded-01/preparation.json', 'pilot/code-expanded-01/config.json',
    'pilot/code-compact-01/receipt.json', 'pilot/code-compact-01/preparation.json', 'pilot/code-compact-01/config.json',
    'codec-validation-01.xml', 'codec-controls-validation-05.xml', 'audit-validation-05.xml',
    'router-regression-01.xml', 'job-name-baseline.xml', 'job-name-fixed.xml',
    'adapter-regression-01.xml', 'audit-budget-fixed.xml', 'guidance-validation-01.xml',
    'guidance-legacy-validation-01.xml', 'wrapper-validation-03/tests.xml',
    'audit-genuine-preparation-fix/focused-01/tests.xml',
    'followup-integration-01.xml', 'final-review.json',
    'build-result-summary.py', 'package-changes-final.py', 'seal-final-evidence.py',
]
entries = []
for relative in FILES:
    path = ROOT / relative
    assert path.is_file() and not path.is_symlink(), relative
    raw = path.read_bytes()
    entries.append({'path': relative, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
sources = json.loads((ROOT / 'source-manifest-final.json').read_text())
checkout = Path(sources['checkout'])
assert all(hashlib.sha256((checkout / r['path']).read_bytes()).hexdigest() == r['after_sha256']
    for r in sources['files'])
report = {
    'schema': 'terminal-compact-retrieval-public-evidence-manifest@1',
    'files': entries,
    'enumeration': 'Explicit public evidence allowlist only; no recursive discovery.',
    'raw_model_transcripts_hidden_verifier_logs_credentials_private_keys_and_databases_excluded': True,
    'all_final_source_hashes_match': True,
    'failed_pilot_retained_and_not_reclassified': True,
    'final_fixes_not_in_tested_v12_runtime': True,
    'original_dirty_checkout_or_git_index_mutated_by_this_work': False,
    'new_cloud_training_or_publication_performed': False,
}
(ROOT / 'evidence-manifest-final.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({'public_evidence_files': len(entries), 'all_final_source_hashes_match': True}))
