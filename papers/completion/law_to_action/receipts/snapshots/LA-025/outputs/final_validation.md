# LA-025 final validation

Paper: From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents.
Task: isolated retained-data reproduction, package audit, optional author handoff.
Recorded: 2026-09-13T04:08:03.264807+00:00.
Activity class: **automated**. Independent human review was not collected and is not required.

This record is technical reproduction and artifact integrity evidence. It is not workshop submission, acceptance, author impersonation, or independent human validation.

## Environment (authoritative validation PATH)

| Field | Value |
| --- | --- |
| PATH | `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin` |
| Python | `/usr/bin/python3.12` (3.12.3) |
| Python SHA-256 | `1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f` |
| HOME | private directory `home` |
| XDG cache/config/data/state | `$HOME/.cache`, `$HOME/.config`, `$HOME/.local/share`, `$HOME/.local/state` |
| latexmk | `absent` |
| pdflatex | `absent` |
| pdfinfo | `/usr/bin/pdfinfo` |
| pdftotext | `/usr/bin/pdftotext` |
| git HEAD | `2995f20e6b36ed0fa0f703765bb5bd567f0209b7` |
| repository dirty files | 1 |

`latexmk` and `pdflatex` are absent from the sealed PATH. The documented PDF rebuild (`./build_pdf.sh`) was **not executed** in this environment. The existing LA-024 compiled `paper.pdf` was inspected with `pdfinfo`/`pdftotext` against the retained `main.aux`/`main.log`. That is a toolchain capability gap for a fresh TeX rebuild, not a missing scientific run.

## Commands actually executed (automated)

1. Isolated extract of `papers/completion/law_to_action/submission/anonymous_supplement.zip` into a fresh directory.
2. `./reproduce.sh --output <fresh-analysis>` from the extracted package, with sealed PATH and private HOME.
3. `pdfinfo` and `pdftotext -layout` on the live `submission/paper.pdf`.
4. Source, checklist, template-checksum, claim, and placeholder audits in this process.
5. Optional live CFP GET of `https://vericodegen.github.io/cfp.html`.

Exact argv, exit codes, and logs are retained under `papers/completion/law_to_action/receipts/snapshots/LA-025/`.

## Observed reproduction outcomes

The bounded reproduction is retained-data analysis. It does **not** rerun the 900-cell operator matrix, Docker cells, solvers, or models.

| Check | Observed |
| --- | --- |
| package files verified | `True` |
| 9,933 reducer inputs verified | `True` |
| 45 paired family-bootstrap contrasts recomputed | `True` |
| scientific rows | `900` |
| host attempts | `902` |
| group CPU seconds | `1608.817478` |
| startup CPU counted once | `0.118787` |
| new scientific executions | `0` |
| compact analysis exit | `0` |
| recovery analysis exit | `0` |

Recomputed modeled-policy rates (independent effect counters):

| Arm | Split | Forbidden effects | Allowed useful work | False denials |
| --- | --- | --- | --- | --- |
| A0 | overall | 90/90 | 90/90 | 0/90 |
| A1 | overall | 90/90 | 90/90 | 0/90 |
| A2 | overall | 90/90 | 90/90 | 0/90 |
| A3 | overall | 33/90 | 90/90 | 0/90 |
| A4 | overall | 0/90 | 90/90 | 0/90 |
| A0 | final | 54/54 | 54/54 | 0/54 |
| A3 | final | 18/54 | 54/54 | 0/54 |
| A4 | final | 0/54 | 54/54 | 0/54 |

These equal the manuscript Table 3 and the admitted `summary.json`. They remain finite, policy-relative sandbox observations, not legal correctness or universal prevention.

## Manuscript and artifact audit (automated)

| Check | Observed |
| --- | --- |
| paper.pdf SHA-256 | `b306a5d4c64961f9e9a1c061dac99645fbc3fca406621092ba813bc3cd221ecb` |
| paper.pdf bytes | 215003 |
| main-text pages | 7 (required 4–9) |
| total PDF pages | 23 |
| official anonymous block | present |
| workshop footer | present |
| scientific PDF placeholders | none |
| ZIP SHA-256 | `e46b58516a47020e3df826bb7cdc3f870566c28a6a3eb92c5abf53c64ed679e1` |
| ZIP bytes | 31209772 |
| shared templates unchanged | `True` |
| copied style SHA-256 | `2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11` |
| checklist answers (16) | Yes, Yes, NA, Yes, Yes, Yes, Yes, Yes, Yes, No, NA, Yes, Yes, NA, NA, NA |
| source-IR span linkage | 60/60 |
| source-IR schema validity | 50/60 |
| model calls in scored study | 0 |
| human_agreement / human_fidelity | `None` / unmeasured |

Style-generated `Anonymous Author(s)`, `Affiliation`, `Address`, and `email` were exempted from the residual-placeholder scan. Scientific and checklist placeholders remain failures; none were found.

## Automated versus human activities

**Automated (this task):** isolated ZIP extract; `reproduce.sh` retained-data analysis; PDF text/metadata inspection; template checksums; checklist completeness; claim-to-raw comparison; CFP fetch attempt; checksum generation; handoff/metadata drafting.

**Human, not performed and not required:** independent legal/security/intent annotation; inter-annotator agreement; expert legal fidelity scoring; optional author scientific sign-off; OpenReview/CFP portal submission; workshop acceptance.

Missing outside reviewers and missing optional author feedback are **not blockers**. Missing required execution evidence or invalid artifact claims **would be blockers**; the bounded reproduction and live artifact hashes succeeded.

## Discrepancies

- AUTOMATED capability gap: latexmk/pdflatex are absent from PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin. Documented ./build_pdf.sh was not run. Live paper.pdf b306a5d4c64961f9e9a1c061dac99645fbc3fca406621092ba813bc3cd221ecb was inspected instead of rebuilt.
- HISTORICAL: submission/template_inputs.json compiled.pdf_sha256 e51fbbdc79f6f29f74899b6861d1bc36d34f3df15a8daafce0a98d4ccd042c43 records the earlier LA-024 compile; live paper.pdf is the public_redaction_v4 file b306a5d4c64961f9e9a1c061dac99645fbc3fca406621092ba813bc3cd221ecb. Not a scientific outcome change.
- HISTORICAL: submission/template_inputs.json compiled.zip_sha256 bce0e313c66fab971fbb86b613125bcb098f6bf20039b1307eb27660d787dd22 records the earlier LA-024 archive; live ZIP is the public_redaction_v4 file e46b58516a47020e3df826bb7cdc3f870566c28a6a3eb92c5abf53c64ed679e1. Not a scientific outcome change.
- WORKTREE: papers/completion/law_to_action/manuscript/main.log is a stale 2026-09-11 compile and is not the submission PDF log. Citation/overflow checks used the retained LA-024 public_redaction_v4 build_evidence logs.

## Residual limitations (not converted into results)

- Closed-loop generated-code planning remains withdrawn (`900/900` not started; model calls `0`).
- Expert legal fidelity, human agreement, and legal-validity rates remain unmeasured.
- LA-009 `18/18` is shared-producer conformance, not independent checker agreement.
- Original LA-015/rescue and LA-016/LA-017 comparison wording are protocol-unadmitted diagnostics.
- LA-020 traces are separate diagnostic replays.
- SAT/UNSAT on the selected QF_BOOL route has satisfiability authority only.
- Native Docker/runtime binaries, private keys, and corpus bodies are not in the anonymous ZIP; retrieving a hash is not a fresh scientific rerun.
- `latexmk` is absent from the sealed PATH, so this task did not rebuild the PDF.

## Submission status

No file was uploaded, no author identity was asserted, and no workshop decision is implied. Proposed metadata for the authors is in `metadata.json`. Optional author review instructions are in `author_handoff.md`.
