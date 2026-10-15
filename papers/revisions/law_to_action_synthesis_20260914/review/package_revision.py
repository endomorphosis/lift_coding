from pathlib import Path
import hashlib, importlib.util, json, re, subprocess, tempfile, zipfile
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
previous = root.parent / 'law_to_action_editorial_20260914'
sha = lambda b: hashlib.sha256(b).hexdigest()
record = lambda b: {'bytes': len(b), 'sha256': sha(b)}
for item in json.loads((root / 'review/baseline.json').read_text()):
    assert sha(Path(item['path']).read_bytes()) == item['sha256'], item['path']
oldzip = previous / 'supplement.zip'
assert sha(oldzip.read_bytes()) == 'a659ed7b30d96244b30ac3716d2148eb497569a3fe3f5759e46209db09d7437e'
log = (root / 'review/publication-build/main.log').read_text()
assert not re.search(r'Warning|Overfull|Underfull|undefined', log)
assert '23 pages' in log
aux = (root / 'review/publication-build/main.aux').read_text()
assert re.search(r'\\newlabel\{la-main-text-end\}\{\{9\}\{7\}', aux)
pdf = (root / 'paper.pdf').read_bytes()
assert pdf == (root / 'review/publication-build/main.pdf').read_bytes()
assert len(pdf) < 50_000_000
source = {str(p.relative_to(root)): p.read_bytes() for p in sorted((root / 'manuscript').iterdir()) if p.is_file()}
assert 'manuscript/references.bib' not in source
assert sha(source['manuscript/neurips_2026_vericode.sty']) == '2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11'

def normalize_checklist(s):
    return '\n'.join(line.split(' % Replace by')[0] for line in s.splitlines() if 'Justification:' not in line)
assert normalize_checklist((previous / 'manuscript/checklist.tex').read_text()) == normalize_checklist(source['manuscript/checklist.tex'].decode())
rendered = (root / 'review/revised.txt').read_text()
assert not re.search(r'\[\s*tbd\s*\]|\bTODO\b|\bFIXME\b|\?\?', rendered, re.I)
assert not re.search(r'/home/barberb|lift_coding|overleaf.com/project', rendered)
cited = set(k for s in re.findall(r'\\citation\{([^}]+)\}', aux) for k in s.split(','))
entries = re.findall(r'^@\w+\{([^,]+),', source['manuscript/related_work.bib'].decode(), re.M)
assert len(entries) == len(set(entries)) == 40 and set(entries) == cited
fonts = subprocess.check_output(['pdffonts', str(root / 'paper.pdf')], text=True)
for line in fonts.splitlines()[2:]:
    assert re.search(r'\byes\s+yes\s+yes\s+\d+\s+\d+\s*$', line), line

notes = '''# Law to Action: citation verification and synthesis

The revision combines the architecture developed in the original 17-page draft with the existing measured results and the polished editorial manuscript. The registered title and all scientific observations remain unchanged.

## Restored ideas

- Explain the legal, security, and procedural source streams, their source identities, and the distinction between source interpretation and executable constraints.
- Separate domain representations, logical views, and checker backends; describe richer temporal, deontic, and event representations without attributing those semantics to the scored propositional checks.
- State a typed admission condition and distinguish satisfiability, truth-table, and kernel-checked evidence. Add an architecture figure connecting source records, proof obligations, current authority, durable consumption, and observed effects.
- Explain proposal/checker separation, evidence reuse and freshness, exact invocation binding, and current-state revalidation.
- Clarify the evaluated DuckDB owner and the separate roles of IPFS artifact identity, libp2p transport, UCAN authority, and optional MCP extensions.
- Recover ContextPacks, semantic minification, program-state reuse, and closed-loop planning as explicitly unmeasured extensions.

## Citations and presentation

All 40 final references were verified against primary sources. Author-list corrections, publication/version choices, documentation dates, source-package citations, and claim-attribution corrections are documented in `review/citation_audit.md` and `.json`. The duplicate inherited bibliography is excluded from this source package. The audit records its access limitation for Miller's thesis and does not claim full-text reading of every reference.

The main paper has **7 pages**, including its figure and tables; the complete PDF has **23 pages**, including references, appendices, and the checklist. The official workshop policy permits 4–9 main pages, excluding references and technical appendices: https://vericodegen.github.io/cfp.html . The supplied anonymous style, margins, font sizes, and line spacing are unchanged. All 16 checklist questions, guidelines, and answers are retained; their justifications were updated where needed, including the typed admission condition and source licensing scope.

The prose presents the contribution as a research argument. Detailed execution accounting and provenance remain in appendices. The existing 900-cell study, 902 host attempts, split definitions, seeds, estimates, uncertainty intervals, source checks, and resource accounting are preserved. Richer semantics and closed-loop ideas are distinguished from measured claims. No new experiment or semantic validation was performed for this revision.

## Validation and artifacts

A fresh pdflatex/BibTeX build completes without warnings, unresolved citations, or overfull/underfull boxes. All fonts are embedded. Main pages, the figure, tables, and references were visually inspected. Separate reviews checked citation metadata, the original architecture, numerical invariants, and the scope of restored claims.

The matching supplement updates manuscript and revision documentation only. Scientific records, implementation sources, reproduction programs, licenses, and inner evidence archives are byte-identical to the previous editorial supplement. ZIP integrity, source equality, inventory, and content hashes are checked using the included inventory verifier. The retained-data analysis was not rerun for this editorial change.

The original manuscript and previous handoffs remain unchanged. These files have not been submitted or uploaded to Overleaf.
'''
(root / 'REVISION_NOTES.md').write_text(notes)
readme = '''# Law to Action — revised manuscript, 14 September 2026

Start with `paper.pdf`: 7 main pages and 23 pages in total.

- `manuscript/main.tex`: editable entry point.
- `latex_sources.zip`: portable LaTeX sources, official style, bibliography, citation audit, and build script.
- `supplement.zip`: matching anonymous supplement with unchanged scientific evidence.
- `review/citation_audit.md`: verification and corrections for all 40 references.
- `REVISION_NOTES.md`: restored ideas, presentation changes, and validation scope.
- `review/validation.json` and `checksums.sha256`: build and artifact integrity records.

Upload the files inside `manuscript/` to Overleaf and select `main.tex`. For a local build with pdflatex and BibTeX installed, run from this directory:

```sh
./build_pdf.sh /tmp/law-synthesis-build
```

Choose an output directory that does not exist. The script installs nothing; the output is `main.pdf`. The supplied workshop style stays in anonymous mode. `related_work.bib` is the single selected bibliography.

This revision combines the original architecture with the existing results; future extensions remain explicitly unmeasured. The previous handoffs remain unchanged. No external upload or submission has been performed.
'''
(root / 'README.md').write_text(readme)
source_readme = '''# Law to Action — editable sources

This manuscript has 7 main pages and 23 pages in total. Upload the files in `manuscript/` to Overleaf and choose `main.tex` as the main document.

For a local build with pdflatex and BibTeX installed, run `./build_pdf.sh /tmp/law-synthesis-build` from this directory, choosing an output directory that does not exist. The output is `main.pdf`; the script installs nothing. The official anonymous workshop style is unchanged, and `related_work.bib` is the sole selected bibliography.

See `REVISION_NOTES.md` for restored ideas and validation scope, and `review/citation_audit.md` and `.json` for verification of all 40 final references. This source package does not contain the experimental evidence; that is supplied in the matching supplement.
'''
audit = {n: (root / n).read_bytes() for n in ['review/citation_audit.md', 'review/citation_audit.json']}
portable = {**source, **audit, 'build_pdf.sh': (root / 'build_pdf.sh').read_bytes(), 'README.md': source_readme.encode(), 'REVISION_NOTES.md': notes.encode()}
for name, data in portable.items():
    assert not re.search(rb'/home/barberb|lift_coding|overleaf.com/project', data), name

def write_zip(path, prefix, members):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(prefix + name)
            info.external_attr = ((0o100755 if name.endswith('.sh') else 0o100644) << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)

write_zip(root / 'latex_sources.zip', 'law_to_action_synthesis_sources/', portable)
prefix = 'law_to_action_final_supplement/'
with zipfile.ZipFile(oldzip) as z:
    assert all(i.filename.startswith(prefix) and not i.is_dir() for i in z.infolist())
    inherited = {i.filename[len(prefix):]: z.read(i) for i in z.infolist()}
manifest = json.loads(inherited['manifest.json'])
old_scope = manifest['scope'].copy()
new = {name: data for name, data in inherited.items() if not name.startswith('manuscript/')}
new.update(source)
new.update(audit)
new['build_pdf.sh'] = (root / 'build_pdf.sh').read_bytes()
base_readme = inherited['README.md'].decode().split('\n## Editorial edition — 14 September 2026')[0]
base_readme = base_readme.replace('maps the eight neutral technical identifiers in the manuscript to exact included original definitions', 'maps neutral technical identifiers to exact included original definitions')
new['README.md'] = (base_readme + '\n## Citation and synthesis edition — 14 September 2026\n\nThis edition includes the revised seven-page main paper (23 pages total) and the audit of all 40 references. Manuscript and revision documentation were updated; scientific artifacts and reproduction programs are unchanged. See `submission/editorial_revision.md` and `review/citation_audit.md`. The matching PDF SHA-256 is `' + sha(pdf) + '`.\n').encode()
new['submission/editorial_revision.md'] = notes.encode()
new['submission/compliance_audit.md'] = ('''# Build and artifact verification

The revised manuscript has 7 main pages, including the figure and tables, and 23 total pages. The official workshop policy checked on 14 September 2026 permits 4–9 main pages and excludes references and technical appendices: https://vericodegen.github.io/cfp.html . The PDF and supplement are below the 50 MB and 100 MB limits respectively. The supplied anonymous workshop style is byte-identical, and all checklist questions, guidelines, and answer choices are retained.

A fresh pdflatex/BibTeX build completes without warnings, unresolved references, or overfull/underfull boxes. All fonts are embedded. The main pages, figure, tables, and references were visually inspected. All 40 final references resolve and have primary-source verification; the detailed audit records corrections and access limitations.

Matching PDF SHA-256: `''' + sha(pdf) + '''`.

Previous editorial supplement SHA-256: `''' + sha(oldzip.read_bytes()) + '''`.

All scientific records, inner evidence archives, implementation modules, reproduction programs, and licenses are unchanged. The package inventory and content hashes are verified. This revision includes no new scientific execution, retained-analysis rerun, human validation, external upload, or submission.
''').encode()
manifest['editorial_revision'] = {'date': '2026-09-14', 'revision': 'citation verification and original-architecture synthesis', 'previous_editorial_supplement_sha256': sha(oldzip.read_bytes()), 'matching_pdf': record(pdf), 'main_pages': 7, 'total_pages': 23, 'verified_cited_references': 40, 'scientific_artifact_bytes_unchanged': True}
manifest['files'] = {name: record(data) for name, data in sorted(new.items()) if name != 'manifest.json'}
assert manifest['scope'] == old_scope
new['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
changed = sorted(name for name in inherited if name in new and inherited[name] != new[name])
removed = sorted(set(inherited) - set(new))
added = sorted(set(new) - set(inherited))
assert removed == ['manuscript/references.bib']
assert all(name.startswith('manuscript/') or name in {'README.md', 'manifest.json', 'submission/editorial_revision.md', 'submission/compliance_audit.md'} for name in changed)
assert all(name.startswith('manuscript/') or name in audit for name in added)
unchanged = sorted(name for name in inherited if name in new and inherited[name] == new[name])
scientific = sorted(name for name in inherited if name.startswith(('historical_compact/', 'recovery_source_v1/', 'implementation_sources/')) or name in {'reproduce.py', 'reproduce.sh', 'symbol_aliases.json', 'environment.lock'})
assert scientific and set(scientific) <= set(unchanged)
for required in ['reproduce.py', 'reproduce.sh', 'symbol_aliases.json', 'historical_compact/anonymous_supplement.zip', 'recovery_source_v1/evidence.zip']:
    assert required in scientific
write_zip(root / 'supplement.zip', prefix, new)
assert (root / 'supplement.zip').stat().st_size < 100_000_000
with tempfile.TemporaryDirectory(prefix='law-synthesis-verify-') as temp:
    with zipfile.ZipFile(root / 'supplement.zip') as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        z.extractall(temp)
    bundle = Path(temp) / prefix.rstrip('/')
    spec = importlib.util.spec_from_file_location('law_synthesis_inventory', bundle / 'reproduce.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.check_tree(bundle)
with zipfile.ZipFile(root / 'latex_sources.zip') as z:
    assert z.testzip() is None
    assert len(z.namelist()) == len(portable)
    for name, data in portable.items():
        assert z.read('law_to_action_synthesis_sources/' + name) == data
for item in json.loads((root / 'review/baseline.json').read_text()):
    assert sha(Path(item['path']).read_bytes()) == item['sha256'], item['path']
validation = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'scope': 'citation verification and manuscript synthesis; no new scientific execution or retained-analysis rerun',
    'main_pages': 7, 'total_pages': 23, 'main_page_limit': 9,
    'workshop_policy_url': 'https://vericodegen.github.io/cfp.html',
    'verified_cited_references': 40, 'unused_bibliography_entries': 0,
    'build_log': 'review/publication-build/main.log', 'build_script_exit_code': 0,
    'tex_warnings': 0, 'unresolved_references': 0, 'overfull_boxes': 0, 'underfull_boxes': 0,
    'all_fonts_embedded': True, 'official_style_unchanged': True,
    'all_16_checklist_questions_guidelines_answers_unchanged': True,
    'original_pdf_and_previous_editorial_handoff_unchanged': True,
    'source_zip_bytes_match_built_sources': True, 'zip_crc_checks_passed': True,
    'supplement_inventory_verifier_passed': True, 'supplement_scientific_scope_unchanged': True,
    'scientific_artifacts_byte_identical': True,
    'preserved_scientific_members': {n: record(inherited[n]) for n in scientific},
    'unchanged_previous_supplement_members': unchanged,
    'changed_previous_supplement_members': changed,
    'removed_previous_supplement_members': removed, 'new_supplement_members': added,
    'artifacts': {n: record((root / n).read_bytes()) for n in ['paper.pdf', 'latex_sources.zip', 'supplement.zip']},
    'reviewed_numerical_invariants': [
        '900 scored cells, 902 host attempts, and zero scientific retries',
        '30 families, 60 cases, 6/6/18 split, seeds 104729/104759/104761',
        'Held-out A4 0/54 forbidden and 54/54 allowed; A3 18/54 forbidden; A0-A2 54/54 forbidden',
        'Overall A4 0/90 forbidden and 90/90 allowed; A3 33/90 forbidden; A0-A2 90/90 forbidden',
        'Source checks 60/60, 50/60, 60/60; CVE polarity unknown 24/24; skill shared-producer checks 18/18',
        'Bootstrap 2000 draws, seed 104729, held-out legal/CVE/skill strata 3/7/8',
        'Rounded intervals agree with retained full-precision summary',
        'Resource accounting, boundary qualifications, and diagnostic exclusions preserve scientific scope'
    ]
}
(root / 'review/validation.json').write_text(json.dumps(validation, indent=2) + '\n')
checksum_names = ['paper.pdf', 'latex_sources.zip', 'supplement.zip', 'build_pdf.sh', 'REVISION_NOTES.md', 'README.md', 'review/citation_audit.md', 'review/citation_audit.json', 'review/validation.json']
(root / 'checksums.sha256').write_text(''.join(sha((root / n).read_bytes()) + '  ' + n + '\n' for n in checksum_names))
print(json.dumps({'success': True, 'main_pages': 7, 'total_pages': 23, 'verified_references': 40, 'scientific_members_preserved': len(scientific), 'artifacts': validation['artifacts']}, indent=2))
