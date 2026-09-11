#!/usr/bin/env python3
"""Deterministic PDF-text reconstruction, not recovery of the original LaTeX.

Only writes within this staging directory. The bounding-box extraction establishes
paragraph boundaries; reviewed JSON supplies the seven editable tables. Original
PDF page and printed line references are retained as source comments and JSON.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PAPER = ROOT / 'papers/from_law_to_action_corpus_grounded-1.pdf'
EXTRACTION = HERE.parent / 'extracted.txt'
OUT = HERE / 'manuscript'
OUT.mkdir(exist_ok=True)
NS = {'x': 'http://www.w3.org/1999/xhtml'}

# These are actual compound hyphens, not discretionary line-break hyphens.
KEEP_HYPHEN = {3, 7, 21, 25, 34, 50, 91, 153, 189, 197, 217, 290, 342, 345, 398}
# Paragraphs crossing an original PDF page break.
CONTINUATIONS = {36, 147, 293, 390, 516, 544}
CITE_KEYS = ['mcp', 'mcp-auth', 'catala', 'cvefixes', 'quack', 'ipfs', 'libp2p', 'ucan']

lines, page_of = {}, {}
for page, text in enumerate(EXTRACTION.read_text().split('\f'), 1):
    for raw in text.splitlines():
        match = re.match(r'\s*(\d+)\s{2,}(.*)', raw)
        if match:
            number = int(match[1])
            assert number not in lines, number
            lines[number] = match[2].rstrip()
            page_of[number] = page
assert set(lines) == set(range(1, 550))

starts = set()
for page in ET.parse(HERE / 'original.bbox.html').findall('.//x:page', NS):
    blocks = page.findall('.//x:block', NS)
    numbers = []
    for block in blocks:
        for line in block.findall('x:line', NS):
            value = ' '.join(word.text or '' for word in line.findall('x:word', NS))
            if float(line.get('xMax')) < 101 and value.isdigit():
                numbers.append((int(value), float(line.get('yMin')) + 2.765))
    for block in blocks:
        if float(block.get('xMin')) < 104 or float(block.get('yMax')) > 730:
            continue
        covered = [n for n, y in numbers if float(block.get('yMin')) < y < float(block.get('yMax'))]
        if covered:
            starts.add(min(covered))
starts -= CONTINUATIONS
starts.add(550)


def joined(first, last):
    value = ''
    for number in range(first, last + 1):
        text = lines[number]
        if value and lines[number - 1].endswith('-'):
            if number - 1 not in KEEP_HYPHEN:
                value = value[:-1]
            value += text
        else:
            value += (' ' if value else '') + text
    return re.sub(r'\s+', ' ', value)


def tex(text):
    substitutions = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
                     '_': r'\_\allowbreak{}', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}',
                     '^': r'\textasciicircum{}', '’': "'", '‘': '`', '“': '``', '”': "''",
                     '–': '--', '—': '---', 'ﬁ': 'fi', 'ﬂ': 'fl'}
    value = ''.join(substitutions.get(character, character) for character in text)
    value = re.sub(r'\[([1-8](?:, [1-8])*)\]',
                   lambda match: r'\citep{' + ','.join(CITE_KEYS[int(n)-1] for n in match[1].split(', ')) + '}', value)
    # Exact hashes/identifiers remain contiguous in source but may break in print.
    value = re.sub(r'\b[0-9a-f]{40}\b', lambda m: r'\path{' + m[0] + '}', value)
    return value


tables = json.loads((HERE / 'tables.json').read_text())
tables_after = {table['after_line']: table for table in tables}
for table in tables:
    table_text = [f"% Original PDF pp. {', '.join(map(str, table['pages']))}; Table {table['id']}.",
                  r'\begingroup', r'\renewcommand{\thetable}{' + table['id'] + '}',
                  r'\begin{longtable}{@{}>{\raggedright\arraybackslash}p{.24\linewidth} >{\raggedright\arraybackslash}p{.32\linewidth} >{\raggedright\arraybackslash}p{.38\linewidth}@{}}',
                  r'\caption{' + tex(table['caption']) + r'}\label{tab:' + table['id'] + r'}\\', r'\toprule',
                  ' & '.join(r'\textbf{' + tex(cell) + '}' for cell in table['headers']) + r' \\',
                  r'\midrule', r'\endfirsthead',
                  ' & '.join(r'\textbf{' + tex(cell) + '}' for cell in table['headers']) + r' \\',
                  r'\midrule', r'\endhead', r'\bottomrule', r'\endlastfoot']
    table_text += [' & '.join(tex(cell) for cell in row) + r' \\[3pt]' for row in table['rows']]
    table_text += [r'\end{longtable}', r'\endgroup', '']
    (OUT / f"table-{table['id']}.tex").write_text('\n'.join(table_text))

chain = '''pinned source revision + raw artifact bytes
  -> bounded source record + content identity + use policy
  -> LegalIR | SecurityIR | IntentIR declaration
  -> native formal views + source map + loss/coverage diagnostics
  -> selected applicable constraints + exact invocation
  -> proof jobs + checked evidence + decision receipt
  -> authenticated capability / execution permit
  -> guarded effect + operational observation + durable record'''
steps = [
    'Resolve source and declaration manifests by exact revision/CID.',
    'Import skill procedure as data; derive or validate IntentIR.',
    'Select applicable LegalIR and reviewed SecurityIR constraints.',
    'Bind actual requested tool, arguments, actor and expected effects.',
    'Correlate intent-side effects with code/handler-side observations.',
    'Compose and execute the required formal jobs; retain non-successes.',
    'Produce an exact-context decision, not an effect.',
    'Check signed delegation and host-controlled current policy/state.',
    'In enforce mode, revalidate and consume the exact permitted use.',
    'Dispatch once through the selected protected path.',
    'Record observed outcome separately from proof and authorization.',
    'Commit operational progression through the DuckDB owner.',
]

body, inventory = [], []
boundaries = sorted(starts)
for first, stop in zip(boundaries, boundaries[1:]):
    last = stop - 1
    if 342 <= first <= 363:
        continue
    pages = sorted({page_of[n] for n in range(first, last+1)})
    body.append(f"% Original PDF pp. {', '.join(map(str, pages))}; printed lines {first}--{last}.")
    value = joined(first, last)
    heading = re.fullmatch(r'([1-8](?:\.[1-9])?|[A-F](?:\.[1-9])?)\s{2,}(.+)', lines[first]) if first == last else None
    kind = 'paragraph'
    if first == 1:
        kind = 'abstract'
        body += [r'\begin{abstract}', tex(value), r'\end{abstract}']
    elif first == 341:
        kind = 'references'
        body += [r'\clearpage', r'\nocite{' + ','.join(CITE_KEYS) + '}',
                 r'\bibliographystyle{unsrtnat}', r'\bibliography{references}', r'\clearpage', r'\appendix']
    elif heading:
        kind = 'subsection' if '.' in heading[1] else 'section'
        body.append('\\' + kind + '{' + tex(heading[2]) + '}')
    else:
        body.append(tex(value))
    inventory.append({'kind': kind, 'original_pages': pages, 'printed_line_start': first,
                      'printed_line_end': last, 'normalized_text': value})
    if last in tables_after:
        body.append(r'\input{table-' + tables_after[last]['id'] + '}')
    if last == 439:
        body += ['% Original PDF p. 12: unnumbered provenance-chain code block.',
                 r'\begin{verbatim}', chain, r'\end{verbatim}']
    if last == 507:
        body += ['% Original PDF p. 15: unnumbered twelve-step trace.', r'\begin{enumerate}']
        body += [r'\item ' + tex(step) for step in steps]
        body += [r'\end{enumerate}']
    body.append('')

preamble = r'''% Reconstructed from the supplied PDF, not recovered original author LaTeX.
% See ../source_recovery.md and ../inventory.json for provenance and limitations.
\documentclass{article}
\PassOptionsToPackage{numbers,compress}{natbib}
\usepackage{neurips_2026_vericode}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\usepackage{url}
\usepackage{booktabs}
\usepackage{amsfonts}
\usepackage{nicefrac}
\usepackage{microtype}
\usepackage{xcolor}
\usepackage{longtable,array}
\hypersetup{pdftitle={From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents},pdfauthor={}}
\title{From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents}
\workshoptitle{NeurIPS 2026 Workshop on AI for Verifiable Coding}
\author{Anonymous Author(s)}
\begin{document}
\maketitle
'''
(OUT / 'main.tex').write_text(preamble + '\n'.join(body) + '\n\\end{document}\n')
shutil.copy2(ROOT / 'papers/neurips_2026_vericode.sty', OUT / 'neurips_2026_vericode.sty')
shutil.copy2(ROOT / 'papers/checklist.tex', OUT / 'checklist.supplied.tex')
shutil.copy2(ROOT / 'papers/neurips_2026_vericode_workshop.tex', HERE / 'research-template.supplied.tex')

inventory_object = {
    'schema': 'law-to-action-pdf-reconstruction/v1',
    'status': 'staging-reconstruction-pending-final-fidelity-and-author-review',
    'pdf': str(PAPER.relative_to(ROOT)), 'pdf_page_count': 17,
    'printed_line_coverage': {'first': 1, 'last': 549, 'missing': []},
    'units': inventory,
    'tables': [{'id': t['id'], 'original_pages': t['pages'], 'data_rows': len(t['rows']),
                'file': f"manuscript/table-{t['id']}.tex"} for t in tables],
    'references': [{'number': i+1, 'key': key, 'original_page': 9} for i, key in enumerate(CITE_KEYS)],
    'equations': [], 'figures': [], 'author_footnotes': [],
    'unnumbered_structures': [{'kind': 'provenance-chain', 'page': 12, 'lines': chain.splitlines()},
                            {'kind': 'enumerated-trace', 'page': 15, 'items': steps}],
    'hyphenation_decisions': [{'printed_line': n, 'preserve_hyphen': n in KEEP_HYPHEN}
                             for n, value in lines.items() if value.endswith('-')],
    'inputs_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in [PAPER, EXTRACTION, ROOT / 'papers/neurips_2026_vericode_workshop.tex',
                                   ROOT / 'papers/neurips_2026_vericode.sty', ROOT / 'papers/checklist.tex']},
}
(HERE / 'inventory.json').write_text(json.dumps(inventory_object, indent=2) + '\n')
print(json.dumps({'paragraph_units': len(inventory), 'tables': len(tables), 'numbered_lines': len(lines),
                  'output': str(OUT / 'main.tex')}, indent=2))
