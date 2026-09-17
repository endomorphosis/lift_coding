# LA-024 workshop compliance audit

Recorded: 2026-09-13T02:39:50.897794+00:00.
Live CFP retrieved 2026-09-13 from https://vericodegen.github.io/cfp.html (SHA-256 `66b5740723edb198ed6faf80430bbee3634e316ee4c0385a64da6480e0724468`).

## 1. Page count and size

- Compiled PDF pages: 23
- Main-text pages excluding references/appendices/checklist: 7 (required 4--9)
- References start page: 8
- Appendices start page: 12
- Checklist start page: 17
- PDF bytes: 239400 (limit 50 MB)
- Supplementary ZIP bytes: 48490 (limit 100 MB)

Main results supporting the ENFORCE claim remain in the main text
(Section Evaluation / Table 3), not only in the appendix.

## 2. Anonymity of the package

The anonymous ZIP is packed from the LA-023 directory bundle with prefix
`law_to_action_anonymous_supplement/`. It contains no Overleaf project URL, no
operator home path, no private `source_provenance.json`, and no credentials.
Legitimate independent-source URIs (GovInfo; Hugging Face pins for CVEfixes and
SkillCenter) are retained.

Neutral aliases used in the compiled PDF have a separate private mapping at
`papers/completion/law_to_action/receipts/snapshots/LA-024/private/alias_map.json`.
That mapping is excluded from the anonymous ZIP.

## 3. LLM and human-judgment disclosure

See `disclosure.md` and the final disclosure section of the PDF. Writing
assistants are named. The scored study executed 0 model calls. Remaining human
judgments are recorded as not collected. The official style-generated Anonymous Author(s) /
Affiliation/Address/email block is retained.

## 4. CFP dates and template version

| Item | Live CFP 2026-09-13 | Prior records |
| --- | --- | --- |
| Abstract deadline | 11 September 2026 AoE | review.md 2026-09-11 |
| Paper deadline | September 13, 2026 AoE | related_work.bib 2026-09-12 |
| Review deadline | 27 September 2026 | (live page; not previously required) |
| Notification | 29 September 2026 | (live page) |
| Camera-ready | 14 October 2026 | review.md 2026-09-11 |
| Workshop | 12 December 2026, Atlanta | related_work.bib 2026-09-12 |
| Template | `neurips_2026_vericode_workshop.tex` + `neurips_2026_vericode.sty` dated 2026-01-29 | local research inputs |
| Main text | 4--9 pages excluding references/appendices | same |
| PDF / ZIP limits | 50 MB / 100 MB | same |
| Reviewing | double-blind including linked artifacts | same |
| LLM policy | methodology-essential tools must be described | same |
| Archival | non-archival | same |

This task prepares an anonymous submission candidate. It does not submit,
upload, or impersonate authors.

## 5. Style load and forbidden substitutions

The build working copy uses `\usepackage{neurips_2026_vericode}` with no
options and loads `./neurips_2026_vericode.sty` from the manuscript/build
directory. The local copy is byte-identical to
`papers/neurips_2026_vericode.sty` (`2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11`).

Absent from the build: `final`, `preprint`, `nonanonymous`, `sglblindworkshop`,
`dblblindworkshop` as a substitute, `neurips_2026.sty`, and the competition
shell/style.

## 6. Checklist

`papers/completion/law_to_action/manuscript/checklist.tex` is a per-paper copy
of the official 16-question checklist. Only the official instruction block
(BEGIN/END INSTRUCTIONS) is removed. Heading, questions, subheadings, and
guidelines are preserved. All 16
`\answerTODO{}` / `\justificationTODO{}` fields are replaced with actual
Yes/No/N/A macros and 1--2 sentence evidence-backed justifications. The copy is
`\input` after references and appendices.

## 7. Shared templates unmodified

| Input | SHA-256 | Status |
| --- | --- | --- |
| papers/neurips_2026_vericode_workshop.tex | `c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250` | unchanged |
| papers/neurips_2026_vericode.sty | `2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11` | unchanged; copied locally |
| papers/checklist.tex | `780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6` | unchanged; per-paper copy filled separately |

The official anonymous author block may retain Affiliation/Address/email.

## 8. Footer, line numbers, placeholder policy

Default anonymous mode prints the workshop footer (``Submitted to NeurIPS 2026
Workshop on AI for Verifiable Coding. Do not distribute.''), hides
acknowledgments, and loads `lineno`. Placeholder scans treat the official
Affiliation/Address/email strings as style-generated anonymous text. Unanswered
scientific fields (`answerTODO`, `justificationTODO`, `LA-024 obligation`,
result TBD) remain failures and are absent from this build.

This audit is packaging compliance evidence, not independent scientific peer
review and not a workshop acceptance.
