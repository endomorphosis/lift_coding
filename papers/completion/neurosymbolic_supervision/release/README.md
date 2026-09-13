# Anonymous NS-024 release package

This directory is the ordinary NS-024 anonymous package. It binds a reviewed
20-page workshop PDF and a three-component numerical supplement. It is ready
for author proofread. It is not a submission, publication, or independent
scientific peer review.

## Artifacts

| File | Bytes | SHA256 | Role |
|---|---:|---|---|
| `paper.pdf` | 252576 | `0fb82abbec94c3858b6c9e63fcd456b16a5ad4aa2f294c4b52d08a8592c59862` | Reviewed integrated PDF: main pages 1–6, references 7, technical appendices 8–12, LLM disclosure 13, official 16-item checklist 14–20. |
| `supplement.zip` | 2280657 | `48cee756e4e1bcdcf4d541b6c8721f21cba0800e990e1159a64f3eeb888a0b07` | Combined anonymous supplement, 468 ZIP entries, three unpooled components. |
| `reproduce.sh` | wrapper | see `manifest.json` | Fresh extraction plus the included `reproduce.py`. |
| `manifest.json` | bindings | see file | PDF/ZIP, component, freeze, template, and source bindings. |

The PDF is below 50 MB. The ZIP is below 100 MB. Main text excluding
references and appendices is 6 pages (workshop bound 4–9), subject to live
CFP verification. The build used the local research `neurips_2026_vericode.sty`
unchanged in anonymous default mode, with workshop footer and review line
numbers. Shared user templates were not modified.

Editable 20-page sources, including the official style, disclosure, and
answered checklist, are retained under
`papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-024/manuscript_source_v1/`.
They are not a rewrite of the NS-022-owned `manuscript/main.tex` or
`manuscript/paper.pdf`. Live NS-019 generated figure
`manuscript/generated/figures/family_useful.pdf` is unchanged.

## Clean-environment numerical reproduction

Python 3.12 and the standard library are sufficient. From a copy of this
directory:

```sh
chmod +x reproduce.sh
./reproduce.sh /absolute/path/to/new-extract /absolute/path/to/new-output
```

Equivalent direct form after extracting `supplement.zip`:

```sh
python3 -B reproduce.py --root /absolute/path/to/extract --output /absolute/path/to/new-output
```

The wrapper checks every combined and child manifest, then runs the three
exact child numerical reproducers (`final32/`, `prior/`, `boundary/`) once.
It regenerates retained scalar summaries and table joins from frozen
anonymous derivatives. It does not:

- call models, providers, or scorers
- execute candidates or hidden tests
- rerun historical qualification programs
- authenticate original private signatures
- pool the three populations or sum unlike clocks

The three child reproducers were already run once before ZIP creation in the
inherited root packaging. A worker extraction rerun is a new after-extraction
command; the two epochs stay separate.

## Frozen scientific scope

The governing design is the already frozen 32-cell A/B local-cold comparison
across eight original final families and two nested repetitions (104729,
130363). Canonical freeze
`ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d`; freeze
file SHA256
`7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a`.
Original 192-order/filter lineage, 160 removed factor cells, eight unrecruited
families, prior pilot/protocol failures, and all costs are retained. C/D
routing, warm caches, reuse, publication-comparison efficacy, and original
16-family inferential objectives remain withdrawn. Human semantic fidelity,
expert agreement, and human time remain unmeasured.

## Explicit reproduction limits

A clean environment can install this frozen artifact and regenerate the
reported anonymous tables. That is narrower than original-signature
verification, confidential-oracle rescoring, or a new scientific experiment.
Exact served Grok 4.6 revision and weights are unavailable. Hidden tests,
reference patches, credentials, keys, and raw private operational logs are
excluded. Historical absolute host paths inside retained metadata are
historical commitments, not runnable commands. Unsettled provider charges
are not zero. This package does not authorize submission or publication.
