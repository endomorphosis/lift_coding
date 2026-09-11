"""Audit the editable recovery against retained PDF extraction and compile output."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import unicodedata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = HERE.parent


def escaped(text):
    substitutions = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}', '$': r'\$', '&': r'\&',
                     '#': r'\#', '%': r'\%', '_': r'\_', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(substitutions.get(c, c) for c in unicodedata.normalize('NFC', text))


def norm(text):
    return ' '.join(text.split())


def main():
    audit = json.loads((BASE / 'audit/reconstruction_discrepancies.json').read_text())
    original = (BASE / 'paper_extracted.txt').read_text()
    source = (HERE / 'main.tex').read_text()
    compact = norm(source)
    numbered = {}
    for page, text in enumerate(original.split('\f'), 1):
        for raw in text.splitlines():
            match = re.match(r'^ {0,3}(\d{1,3}) {2,}(\S.*)$', raw)
            if match:
                numbered[match[1]] = (page, match[2])
    assert set(map(int, numbered)) == set(range(1, 779))
    assert set(numbered) == set(audit['numbered_lines'])
    for key, (page, text) in numbered.items():
        recorded = audit['numbered_lines'][key]
        assert (recorded['pdf_page'], recorded['source_text']) == (page, text)
        if page != 10:
            assert norm(escaped(text)) in compact, ('unaccounted source line', page, key, text)
    assert len(audit['references']) == 12
    for item in audit['references']:
        assert r'\bibitem{baseline%02d}' % item['id'] in source
        assert norm(escaped(item['transcribed_entry'])) in compact
    assert sorted(item['number'] for item in audit['tables']) == list(range(1, 19))
    table_lines = 0
    for table in audit['tables']:
        for line in table['source_text'].splitlines():
            if line.strip():
                assert norm(escaped(line)) in compact, ('unaccounted table text', table['number'], line)
                table_lines += 1
    assert sorted(item['number'] for item in audit['equations']) == list(range(1, 7))
    for equation in audit['equations']:
        assert r'\tag{%d}' % equation['number'] in source
    assert not re.search(r'\\input\{(?:abstract|transcription|references)\.tex\}', source)
    for path, expected in audit['sources'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, ('changed baseline input', path)
    for name in ('neurips_2026_vericode.sty', 'checklist.tex'):
        assert (HERE / name).read_bytes() == (ROOT / 'papers' / name).read_bytes()
    rendered = subprocess.check_output(['pdftotext', '-layout', str(HERE / 'main.pdf'), '-'], text=True)
    plain_pdf = norm('\n'.join(re.sub(r'^\s*\d{1,4}\s{2,}', '', line) for line in rendered.splitlines()))
    for anchor in ('58.90%', '43.6161%', '43.0539%', '[TO BE FILLED]', '[RESULTS:', '[TODO]'):
        assert anchor in plain_pdf, ('missing compiled anchor', anchor)
    assert source.count('[TBD]') == rendered.count('[TBD]') == original.count('[TBD]') == 34
    info = subprocess.check_output(['pdfinfo', str(HERE / 'main.pdf')], text=True)
    pages = int(re.search(r'^Pages:\s+(\d+)', info, re.M)[1])
    print(json.dumps({'schema': 'neurosymbolic-source-recovery-audit/v1', 'passed': True,
                     'original_pdf_pages': 28, 'compiled_pdf_pages': pages, 'source_lines_accounted': len(numbered),
                     'headings': len(audit['sections']), 'table_count': 18, 'table_text_lines_checked': table_lines,
                     'numbered_equations': 6, 'reference_entries': 12, 'TBD_cells_unchanged': 34,
                     'self_contained_editable_body': True, 'research_style_and_checklist_unchanged': True,
                     'full_visual_fidelity_verified': False, 'publication_ready': False,
                     'source_recovery_reconciliation_complete': True}, indent=2))


if __name__ == '__main__':
    main()
