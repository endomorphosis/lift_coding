# NS-022 revision notes

Ordinary current-source manuscript assembly for the frozen 32-cell A/B
local-cold comparison. No grant, provider, model, scorer, native context,
proof, scientific retry, or outside reviewer was used.

## Figure ownership (precise NS-019 copy exception)

Root's one-path exception supersedes any 22-file overwrite of
`manuscript/generated/figures/family_useful.pdf`. That file remains the
NS-019 historical/task-owned ASCII rendering and was not copied, replaced,
or treated as Figure 1:

- 5019 bytes
- SHA256 `8ea081bca5d5e309cc5659628b7ceea5e053089b3adfd1d5ae11a7f5c163e4a5`
  (prefix `8ea081bc`)
- 16 family/arm coordinates and labels match the generated eight-family
  analysis / Table 17
- it is **not** the original analyzer-produced 16554-byte PDF (`001ddc34`)
- it is **not** the published Figure 1
- the matching SVG
  `e1503343b198855975b3136e44efbe5330791945435bfabf99b53ea9a400cc90`
  is also unchanged

The named 22-file `manuscript_font_v2` package
(`/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/ns022_actual_manuscript_assembly_v1/`,
manifest SHA `f992bb5a…`, package SHA `6e18e9c5…`, reviewed PDF SHA
`907f0a24…`, 216541 bytes) was not present on this worktree. Allowed task
outputs are `main.tex`, `paper.pdf`, the two audit files, and the NS-022
receipt tree. This completion therefore did not copy undeclared
`layout/family_useful.pdf` or any other generated/figures path, and it did
not replace the NS-019 receipt.

Published Figure 1 is the Type 1 TikZ drawing already in `main.tex` of the
same eight-family useful fractions. `main.tex` does not `\includegraphics`
the NS-019 ASCII PDF. The NS-019 ASCII output remains historical/task-owned,
not the final manuscript figure. No scientific number changed.

## Bound generated products (unchanged)

| File | SHA256 | Owner |
|---|---|---|
| `generated/table17.tex` | `ffbb7f2e6aecefb0e4a65fe2da32cc43e87601e01eb7ab97715e516a22cc0b79` | NS-019 |
| `generated/ablations.tex` | `8c57477902aba200e9a2228d6a316ec06f14859f7894fa1f534f16e8b19d8ccf` | NS-019 |
| `generated/figures/family_useful.svg` | `e1503343b198855975b3136e44efbe5330791945435bfabf99b53ea9a400cc90` | NS-019 |
| `generated/figures/family_useful.pdf` | `8ea081bca5d5e309cc5659628b7ceea5e053089b3adfd1d5ae11a7f5c163e4a5` | NS-019 |
| `generated/table18.tex` | `3fa332e34627a5825f6065623ac39bd3f0a5041627375d167e3fd397f33e2495` | NS-020 |
| `formal_arguments.tex` | `b1d1f95188a4c8633332a4bd15c7977062d24d9affd9e0a7830e553e2a7e8664` | NS-023 |
| `neurips_2026_vericode.sty` | `2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11` | official |
| `audit/verified_references.bib` | `0445451efbb19678d9f1af3c84470a92966f8888230e44fe70eb9744f1ef1951` | NS-021 |
| `analysis/results.json` | `6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e` | NS-019 |

Table 18 in the PDF is a layout copy of the generated table with two
`\allowbreak` insertions only (`residual\allowbreak{} fixture` and
`Fixture/call/\allowbreak teardown`). Generated `table18.tex` bytes are
unchanged. Statistical and cost reports were not regenerated.

## Scientific text

`main.tex` replaces the placeholder-filled reconstruction. It states the
research question (does adding native source-linked semantic context to
matched public raw context change useful cold repair), the novel composition
(typed evidence boundaries plus a bounded implementation), trusted
assumptions, the matched A/B method, the 32-cell results, and negative
cases.

Exact frozen numbers used in abstract, results, and conclusion:

- 32 terminal cells, eight families, nested repetitions 104729 and 130363
- useful 9/32; A 5/16; B 4/16; mean B−A −0.0625
- descriptive conditional 95% percentile interval [−0.1875, 0]
- outcomes 9 / 7 / 14 / 2
- 16 scoring invocations, 15 completed cold validations
- 14 child deadlines; all 32 unknown external charges
- withdrawn C/D, warm, reuse, publication, and sixteen-family inference
- pilot 10/24 (5/arm), 24 POSTs, 12 scores, not pooled
- false reuse 1/26; native proof unavailable; human fidelity unmeasured

No TBD, TO BE FILLED, RESULTS placeholder, or unresolved D/A/N workstream
label remains. NS-NNN tokens in Table 18 are defined as internal
qualification IDs. Supplemental constructed controls are not counted as
useful final repairs. The official checklist is left to NS-024.

## Build

Compiled with user-local TeX Live 2026 via `vericodegen-latexmk`,
`-no-shell-escape`, official `neurips_2026_vericode.sty` in anonymous
default mode, `\pdfobjcompresslevel=0` for a classic xref. Content streams
were then ASCIIHex-wrapped so `manuscript/paper.pdf` and its NS-022 snapshot
are valid UTF-8 text (no NUL). That rewrite is a transport/admission
encoding of the same Type 1 embedded fonts and page content; it is not a
scientific rerun. Output is 12 letter pages (7 main, references, formal
appendix, boundary/ablation tables), 501863 bytes, SHA256
`927312e5ccae86a6a63743e88d94134577da7d6b1d0aaaed6823fd772d42fa57`.
`pdffonts` reports only embedded Type 1 fonts; no Type 3. The old
reconstruction `manuscript/main.pdf` was not overwritten.

## Non-claims

This receipt is provenance validation, not independent scientific peer
review or authorization to submit. It does not copy or re-identify the
unavailable root visual-review PDF `907f0a24…`. Scientific numbers are
unchanged from NS-019/NS-020.
