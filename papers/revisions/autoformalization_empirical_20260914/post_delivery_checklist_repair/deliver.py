#!/usr/bin/env python3
"""Adopt the checklist-only repair, preserving the first empirical handoff."""
import datetime
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FINAL = ROOT.parents[2] / 'papers/final'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def save(path, body):
    path.write_text(json.dumps(body, indent=2) + '\n')

def main():
    original = json.loads((HERE / 'delivery_receipt.json').read_text())
    build = json.loads((ROOT / 'paper_build_validation.json').read_text())
    visual = json.loads((ROOT / 'paper_visual_review.json').read_text())
    assert sha(FINAL / original['pdf']['path']) == original['pdf']['sha256']
    assert sha(FINAL / original['supplement']['path']) == original['supplement']['sha256']
    assert build['main_pages'] == 9 and build['official_checklist_guideline_blocks'] == 16
    assert visual['all_prechecklist_page_text_unchanged'] and visual['passed']
    assert visual['pdf_sha256'] == build['pdf_sha256'] == sha(ROOT / 'editable/build/main.pdf')
    backup = HERE / 'first_handoff_files'
    backup.mkdir(exist_ok=False)
    changes = {
        'paper.pdf': ROOT / 'editable/build/main.pdf',
        'editable/manuscript/checklist.tex': ROOT / 'editable/manuscript/checklist.tex',
        'build_paper.py': ROOT / 'build_paper.py',
        'provenance/paper_build_validation.json': ROOT / 'paper_build_validation.json',
        'provenance/paper_visual_review.json': ROOT / 'paper_visual_review.json',
        'provenance/checklist_restoration.json': HERE / 'repair.json',
    }
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest = json.loads((FINAL / 'manifest.json').read_text())
    for rel, source in changes.items():
        target = FINAL / 'autoformalization' / rel
        if target.exists():
            preserved = backup / rel
            preserved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(target, preserved)
        shutil.copyfile(source, target)
        path = 'autoformalization/' + rel
        manifest['copy_lineage'] = [row for row in manifest['copy_lineage'] if row['path'] != path]
        manifest['copy_lineage'].append({
            'path': path, 'bytes': target.stat().st_size, 'sha256': sha(target),
            'lineage': {'paper': 'autoformalization', 'operation': 'restore_official_checklist_guidelines',
                        'source': {'path': str(source), 'sha256': sha(source)},
                        'destination': str(target)}})
    revision = manifest['autoformalization_empirical_revision']
    revision.update(pdf_sha256=build['pdf_sha256'], total_pages=22,
                    checklist_guidelines_restored_at=now)
    manifest['updated_at'] = now
    for path in (ROOT / 'README.md', ROOT.parents[2] / 'papers/completion/README.md'):
        text = path.read_text().replace('18 pages in total', '22 pages in total')
        path.write_text(text)
    readme = FINAL / 'README.md'
    text = readme.read_text().replace('AF: 9 main pages (updated empirical revision);',
                                    'AF: 9 main pages, references begin on page 10, 22 total (including the complete official checklist);')
    readme.write_text(text)
    files = sorted(p for p in FINAL.rglob('*') if p.is_file()
                   and p not in (FINAL / 'manifest.json', FINAL / 'SHA256SUMS'))
    manifest['files'] = [{'path': str(p.relative_to(FINAL)), 'bytes': p.stat().st_size,
                          'sha256': sha(p)} for p in files]
    manifest['payload_bytes'] = sum(row['bytes'] for row in manifest['files'])
    save(FINAL / 'manifest.json', manifest)
    files.append(FINAL / 'manifest.json')
    (FINAL / 'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(FINAL)}\n' for p in sorted(files)))
    receipt = dict(original)
    receipt.update(delivered_at=now, initial_empirical_delivery_at=original['delivered_at'],
                   official_checklist_restoration=str(HERE),
                   first_empirical_handoff_pdf_preserved=str(HERE / 'paper.before.pdf'))
    receipt['pdf'] = {'path': original['pdf']['path'], 'bytes': (ROOT / 'editable/build/main.pdf').stat().st_size,
                      'sha256': build['pdf_sha256']}
    save(ROOT / 'delivery_receipt.json', receipt)
    save(HERE / 'delivery.json', receipt)
    print(json.dumps(receipt, indent=2))

if __name__ == '__main__':
    main()
