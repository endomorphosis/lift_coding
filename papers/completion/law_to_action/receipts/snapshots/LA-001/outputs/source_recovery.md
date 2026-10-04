# Law-to-action manuscript source reconstruction

The supplied PDF has been reconstructed into editable [main.tex](manuscript/main.tex) and [references.bib](manuscript/references.bib). The local build produces [main.pdf](manuscript/main.pdf): 17 pages, with eight main-text pages and references on page 9. This completes the bounded source-reconstruction work in LA-001. It does not complete the paper's scientific evaluations, code audit, final anonymization, checklist, or author approval.

The original author LaTeX and bibliography were not recovered. The user-provided Overleaf project remains inaccessible to this session, its paper membership is unverified, and no source download is claimed. Its private project URL and missing author/provenance fields are recorded only in [private/source_provenance.json](private/source_provenance.json). Repository history records the supplied PDF in the campaign-input commit; no manuscript-specific LaTeX/BibTeX was supplied. Unavailable author records did not block reconstruction.

The available `papers/neurips_2026_vericode_workshop.tex`, `papers/neurips_2026_vericode.sty`, and `papers/checklist.tex` are formatting/checklist inputs, not recovered manuscript text. The reconstruction uses the research shell's default anonymous style and package choices. The canonical manuscript finds the unchanged shared style through its LaTeX input path; all seven reconstructed tables are inline and editable. The original shared files were not changed. Competition and generic NeurIPS styles were not used.

## Build and content evidence

From `papers/completion/law_to_action/manuscript`, run:

```sh
/home/barberb/.local/bin/vericodegen-latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

The installed wrapper resolves local TeX Live binaries even with a restricted shell PATH. Building requires no remote editor. The actual successful canonical build is preserved in [canonical-build.log](source_recovery_staging/canonical-build.log). Tools were Latexmk 4.88, pdfTeX 1.40.29 / TeX Live 2026, BibTeX 0.99e, and Poppler pdftotext 24.02.0. Exact version outputs are in [source-toolchain-inspection.log](source_recovery_staging/source-toolchain-inspection.log). The canonical build has no undefined references/citations and no overfull boxes; eight underfull warnings reflect ordinary paragraph/page spacing.

From the repository root, run:

```sh
python papers/completion/law_to_action/source_recovery_staging/audit_reconstruction.py
```

The actual audit and its [log](source_recovery_staging/fidelity-audit.log) are preserved in [fidelity_audit.json](source_recovery_staging/fidelity_audit.json). All 549 numbered PDF lines are accounted for, including the 22 bibliography lines. All 122 narrative/heading units and all eight complete reference entries are present in the compiled PDF after normalization of whitespace, punctuation, case and ligatures. Every original source page and printed-line range remains a comment in the editable source and a record in [inventory.json](source_recovery_staging/inventory.json).

The seven tables contain 50 data rows and 150 cells. Of these, 140 original cells match normalized bounding-box text automatically. Ten cells in Table C1 require visual checking because Poppler interleaves the original second and third columns. Those cells were checked by the assistant against [original page 13](source_recovery_staging/original-page-13.png); this is explicitly not independent human review. All 150 cells, all table headings and captions match the compiled PDF extraction. The compiled evaluation table was also visually inspected and remains readable.

## Section accounting

Page numbers below refer to the supplied PDF unless identified as reconstructed. Exact paragraph coverage is in the inventory; unchanged wording includes each incomplete evaluation statement.

| Original location | Content accounted for | Reconstructed pages |
| --- | --- | --- |
| p1, lines 1–17 | Title, anonymous author block and abstract | 1 |
| pp1–2, 18–37 | §1 Introduction | 1–2 |
| pp2–4, 38–130 | §2; §§2.1 Legal IR, 2.2 Security IR, 2.3 Intent IR, 2.4 common lineage | 2–4 |
| pp4–5, 131–169 | §3; §§3.1 logic families and 3.2 translation/checking/reuse | 4–5 |
| pp5–6, 170–214 | §4; §§4.1 admission, 4.2 proof jobs, 4.3 enforcement | 5–6 |
| p6, 215–243 | §5 DuckDB and operational state | 6 |
| pp7–8, 244–296 | §6; §§6.1 IPFS, 6.2 libp2p, 6.3 UCAN, 6.4 MCP++ | 6–8 |
| p8, 297–327 | §7 unexecuted worked trace and evaluation plan | 8 |
| p8, 328–340 | §8 Scope and conclusion | 8 |
| p9, 341–363 | References [1]–[8] | 9 |
| pp10–12, 364–443 | Appendix A; A.1 legal releases, A.2 CVE controls, A.3 SkillCenter, A.4 provenance chain | 10–12 |
| pp12–13, 444–467 | Appendix B; B.1 semantics and B.2 proof/result classes | 12–13 |
| pp13–14, 468–503 | Appendix C; C.1 storage, C.2 owner, C.3 network/content, C.4 capabilities | 13–14 |
| pp14–15, 504–511 | Appendix D implementation map, twelve-step trace and failure attribution | 14–16 |
| pp15–16, 512–534 | Appendix E; E.1 populations/results template, E.2 negatives/ablations | 16 |
| pp16–17, 535–549 | Appendix F scope, unavailable ongoing work and original disclosure | 17 |

## Tables and non-prose structures

| Item | Original pages | Data rows | Disposition |
| --- | --- | ---: | --- |
| Table 1: source-to-IR paths | 3–4 | 3 | All cells preserved; continuation joined as editable longtable |
| Table 2: formal views/checking | 4 | 7 | All cells preserved |
| Table A1: legal sources | 10 | 6 | All cells preserved |
| Table B1: logic meanings | 12–13 | 10 | Includes final linear/separation row on original p13 |
| Table C1: storage/protocol roles | 13–14 | 6 | Includes UCAN continuation; ten interleaved cells visually checked |
| Table D1: implementation trace | 15 | 10 | All symbol names and evidence requirements preserved |
| Table E1: result placeholders | 16 | 8 | Five “Not run” and three inspected-but-pending states preserved |
| Provenance chain | 12, after line 439 | 8 lines | Verbatim source-to-effect chain preserved |
| Enumerated implementation trace | 15, before line 508 | 12 items | All numbered steps preserved |

There are no displayed mathematical equations, numbered equations, figure panels, or author footnotes in the supplied PDF. The provenance chain is a code-like diagram, not an equation. The only page-1 footnote-like element is the workshop submission footer; the unchanged research style supplies it. The original anonymous author block is reproduced by the style, and compiled PDF author metadata is empty. The source contains no newly supplied author names or private Overleaf link.

The bibliography retains, in the original order, [1] MCP specification, [2] MCP authorization, [3] Catala, [4] CVEfixes, [5] Quack, [6] IPFS CIDs, [7] libp2p connections, and [8] UCAN. Author lists, titles, years, DOI/URL fields, revision dates and reported access dates match the original normalized entries. URLs split across original lines were rejoined. Access dates and external source assertions were transcribed, not newly verified.

## Discrepancies and remaining uncertainty

1. **Source provenance:** This is a reconstruction from visible PDF content. Original macros, exact inline font choices, source comments and author editing history are unavailable. The private companion described in original Appendix D is not available; no repository pin or author identity was invented.
2. **Typography:** Paragraph boundaries were inferred from bounding boxes and cross-page continuations. The audit records all 32 line-final hyphen decisions. True compound hyphens were preserved; discretionary splits were joined. Table widths, row spacing, caption/header weight, line numbering and page breaks differ. Main text remains eight pages, but §6 begins on reconstructed page 6, Appendix E moves to page 16, and Appendix F starts on page 17. Repeated table headers and an enumerated list are typeset anew. These are layout discrepancies, not missing material.
3. **Coverage limits:** Normalized text matching ignores punctuation, spacing, case and ligature differences. It confirms content coverage, not pixel equivalence. Table C1's ten original cells received an explicit assistant visual check. Independent final PDF proofreading remains LA-025.
4. **Unverified claims preserved:** Municipal counts (567 jurisdictions; fourth-drop 300, 448,090, 41 states), Netherlands 4,999/89,737, Belgium 9,116/282, CVE 12,987/12,714/273/85,169/167,364, and SkillCenter 216,972/24/216,972 remain reported-source quantities. Their source revisions, licenses, counts and code correspondence require LA-002/004/023. Preserving these statements does not certify them.
5. **No scientific results added:** Table E1 remains incomplete. The §7 walkthrough remains unexecuted. The original Appendix F disclosure remains verbatim, including its statement about no tests in that earlier revision. It is a historical draft statement and must be updated by LA-024 to reflect actual subsequent work. Source compilation and receipt validation are not model/solver benchmark results.
6. **Checklist and blind review:** The supplied checklist remains unchanged as a separate formatting input; the original PDF contained no checklist, so none was silently filled or inserted. The original draft's implementation symbols and third-party dataset handles remain in the reconstruction for fidelity. LA-024 must review identifiability and methodology-relevant LLM disclosure, complete the checklist truthfully, and create the final anonymous package. The private provenance file and any snapshot containing it must be excluded from anonymous releases.
7. **Scope:** LA-001's reconstruction criteria are supported by the source, audit, private unknown-field record and actual local build. LA-002 through LA-025 retain their separate obligations. No authoritative task database, lane worktree, provider run or supervisor status was changed by this source work.

## Input integrity

The inventory, private provenance record and immutable task receipt store SHA-256 hashes for the supplied PDF, original extraction, research shell, research style and checklist. The audit verifies that the style, shell and checklist copies are byte-identical to the shared inputs. The source PDF is always the evidence origin, not the rebuilt PDF. The rebuilt PDF hash and actual build/audit logs are recorded independently.
