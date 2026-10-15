#!/usr/bin/env python3
"""Deliver only the validated empirical AF revision; preserve the previous handoff."""
import datetime
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
FINAL = REPO / 'papers/final'

def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def info(path, base):
    return {'path': str(path.relative_to(base)), 'bytes': path.stat().st_size, 'sha256': sha(path)}

def load(name):
    return json.loads((ROOT / name).read_text())

def main():
    build = load('paper_build_validation.json')
    bundle = load('supplement_build_validation.json')
    replay = load('supplement_reproduction.json')
    visual = load('paper_visual_review.json')
    assert build['main_pages'] <= 9
    assert sha(ROOT / 'editable/build/main.pdf') == build['pdf_sha256']
    assert sha(ROOT / 'supplement.zip') == bundle['archive_sha256']
    assert replay['all_payload_hashes_match'] and replay['all_component_reproductions_passed']
    assert visual['passed'] and visual['pdf_sha256'] == build['pdf_sha256']
    numbers = load('editable/results/table_generation.json')['complete_denominators']
    assert numbers == {'sources': 1913, 'direct_model_sources': 100, 'guidance_source_seed_pairs': 5739, 'constructed_proof_goals': 64}
    handoff = ROOT / 'handoff_assembly'
    handoff.mkdir(exist_ok=False)
    (handoff / 'editable/manuscript').mkdir(parents=True)
    (handoff / 'editable/results').mkdir(parents=True)
    (handoff / 'provenance').mkdir()
    copied = []
    def copy(src, rel):
        dst = handoff / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied.append({'path': 'autoformalization/' + rel, 'bytes': dst.stat().st_size, 'sha256': sha(dst),
                       'lineage': {'paper': 'autoformalization', 'operation': 'copy_validated_empirical_revision',
                                   'source': {'path': str(src), 'sha256': sha(src)}, 'destination': str(FINAL / 'autoformalization' / rel)}})
    copy(ROOT / 'editable/build/main.pdf', 'paper.pdf')
    copy(ROOT / 'supplement.zip', 'supplement.zip')
    copy(ROOT / 'build_paper.py', 'build_paper.py')
    for folder in ['manuscript', 'results']:
        for path in sorted((ROOT / 'editable' / folder).glob('*')):
            if path.is_file() and path.suffix in ['.tex', '.sty', '.bib', '.json']:
                copy(path, 'editable/' + folder + '/' + path.name)
    for name in ['paper_build_validation.json', 'paper_visual_review.json', 'supplement_build_validation.json',
                 'supplement_reproduction.json', 'citation_verification.md', 'FINAL_PROTOCOL_FREEZE.json',
                 'infrastructure_amendment_review.json', 'freeze_drift_review.json', 'post_execution_freeze_review.json', 'runtime_manifest.json', 'original_programme_crosswalk.json', 'supervisor_audit_20260914.json', 'supervisor_audit_20260914.md']:
        copy(ROOT / name, 'provenance/' + name)
    (handoff / 'BUILD.md').write_text(
        '# Build and evidence\n\n'
        'This directory contains the completed empirical revision of the autoformalization paper. '
        'The upload pair is `paper.pdf` and `supplement.zip`. The manuscript uses the unmodified official workshop style.\n\n'
        'From this directory, with Python 3, pdfLaTeX, BibTeX, and Poppler installed, run:\n\n'
        '```sh\npython build_paper.py\n```\n\n'
        'The script compiles `editable/manuscript/main.tex`, resolves citations, and checks the main-page limit, '
        'placeholder absence, PDF size, and anonymous metadata. Output is `editable/build/main.pdf`; '
        'the delivered `paper.pdf` is preserved until an author explicitly adopts a rebuild. '
        'Typesetting bytes can vary with installed TeX versions.\n\n'
        'Extract `supplement.zip` separately and run its `python reproduce.py` command using Python 3.12 '
        'and NumPy 1.26.4. This regenerates metrics and tables from actual observations. Add `--proofs` '
        'with Lean 4.33.1 on PATH to recheck the 12 admitted generated proofs. Full model weights and '
        'the complete external runtime are not included.\n\n'
        f'The validated manuscript has {build["main_pages"]} main pages. Its empirical populations are '
        '1,913 units per native compiler arm, 100 direct-model units, three learned seeds on all 1,913 units, '
        '5,739 learned check-order source/seed pairs, and 64 constructed proof goals. Independent '
        'legal-semantic accuracy remains unmeasured. The historical status-filled paper is preserved '
        'under the empirical revision directory, not as the current handoff.\n\n'
        '`provenance/` and editable sources are local author support and can contain private host paths. '
        'Upload only the PDF and anonymous ZIP. No submission or author acknowledgment was performed.\n')
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (handoff / 'provenance/author_handoff.md').write_text(
        '# Empirical author handoff\n\n'
        f'Prepared at {now}. The previous final PDF was incomplete; its primary held-out cells had not been run. '
        'This revision replaces them with complete bounded automated observations, preserves negative results and '
        'failures, and removes any implication of independently measured legal-semantic fidelity.\n\n'
        'The original 29/29 supervisor task count remains a historical workflow count. It was not evidence that '
        'the held-out study had run. The new revision has separate per-record evidence, metric reproduction, '
        'citation verification, and PDF validation.\n\n'
        'Review the current PDF for presentation and author responsibility before using the existing registered '
        'submission. No outside reviewer or annotation is a prerequisite for these automated results.\n')
    old = FINAL / 'autoformalization'
    baseline = ROOT / 'prior_handoff'
    actual = {str(p.relative_to(old)): sha(p) for p in old.rglob('*') if p.is_file()}
    expected = {str(p.relative_to(baseline)): sha(p) for p in baseline.rglob('*') if p.is_file()}
    assert actual == expected, 'Current AF handoff changed while revision ran; preserve and review those edits before replacing'
    backup = ROOT / 'prior_handoff_at_delivery'
    assert not backup.exists()
    # Both trees are on the same filesystem. Retain the entire original tree.
    os.rename(old, backup)
    os.rename(handoff, old)
    # Read the current shared manifest only now, preserving other papers' concurrent revisions.
    manifest = json.loads((FINAL / 'manifest.json').read_text())
    manifest['copy_lineage'] = [row for row in manifest.get('copy_lineage', []) if not row['path'].startswith('autoformalization/')]
    manifest['copy_lineage'].extend(copied)
    manifest['updated_at'] = now
    manifest['autoformalization_empirical_revision'] = {
        'prepared_at': now, 'revision_root': str(ROOT), 'main_pages': build['main_pages'],
        'pdf_sha256': build['pdf_sha256'], 'supplement_sha256': bundle['archive_sha256'],
        'complete_denominators': numbers, 'source_semantic_fidelity_measured': False,
        'metric_reproduction_passed': True, 'prior_handoff_preserved': str(backup),
        'historical_task_counts_are_not_experiment_completion_evidence': True}
    manifest['historical_top_level_workflow_fields_scope'] = (
        'Original supervisor handoff records. The autoformalization_empirical_revision entry supersedes '
        'their AF scientific readiness interpretation; other papers retain their existing lineage.')
    readme = (FINAL / 'README.md').read_text()
    paragraph = (f'Autoformalization was empirically revised on 14 September 2026: all 1,913 native-source units, '
                 'the fixed 100-source direct-model subset, three learned seeds, 5,739 check-order pairs, '
                 f'and 64 constructed proof goals were evaluated. The revised PDF has {build["main_pages"]} main pages; '
                 'its supplement reproduces measured metrics and tables. Independent legal-semantic fidelity remains unmeasured. '
                 'Historical supervisor task totals describe workflows and must not be read as evidence that earlier unrun experiments occurred.\n\n')
    readme = paragraph + readme
    readme = readme.replace('AF: 9 main pages, references begin on page 10, 21 total;',
                            f'AF: {build["main_pages"]} main pages (updated empirical revision);')
    (FINAL / 'README.md').write_text(readme)
    files = sorted(p for p in FINAL.rglob('*') if p.is_file() and p not in [FINAL / 'manifest.json', FINAL / 'SHA256SUMS'])
    manifest['files'] = [info(p, FINAL) for p in files]
    manifest['payload_bytes'] = sum(row['bytes'] for row in manifest['files'])
    (FINAL / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    files.append(FINAL / 'manifest.json')
    (FINAL / 'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(FINAL)}\n' for p in sorted(files)))
    report = {'delivered_at': now, 'pdf': info(old / 'paper.pdf', FINAL),
              'supplement': info(old / 'supplement.zip', FINAL), 'original_preserved': str(backup),
              'other_paper_payloads_changed': False, 'external_submission_performed': False}
    (ROOT / 'delivery_receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
