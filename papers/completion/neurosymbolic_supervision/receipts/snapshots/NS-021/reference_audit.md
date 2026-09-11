# NS-021 reference and attribution audit

Status on 2026-09-11: this record verifies the twelve bibliography entries, their in-text uses, and the adjacent technical statements. It does not rewrite the manuscript (NS-022), confirm author identity or LLM disclosure (NS-024), or produce experimental results.

Primary sources used here are Crossref works retrieved on 2026-09-11 and, for the dissertation, the live EECS technical-report catalog title for `UCB/EECS-2008-176`. The draft PDF transcription in `paper_extracted.txt` (SHA-256 `809af88bfd4e8f78fc7fbc7c067dc5d41392c6c2d4aaf75ec02ec813036a23a4`) is the statement baseline. Structured BibTeX is in `verified_references.bib`. Internal workstream labels are resolved in `artifact_citation_map.json`. Companion-paper overlap is in `related_paper_overlap.md`.

NS-001 preserved literal bibliography strings and assigned metadata verification to this task. Those literal `@misc` note fields are not independently verified records; this audit replaces them.

## Findings

1. All twelve reconstructed entries resolve to a primary bibliographic record (Crossref DOI or the EECS dissertation catalog page).
2. Every in-text bibliographic citation `[1]`–`[12]` supports the adjacent statement, with one grouped CEGAR/CEGIS citation that is acceptable because the two clauses are paired.
3. The draft already bounds novelty: the twelve works are foundations or baselines, not newly invented algorithms, and the paper does not claim to be the first neurosymbolic agent or that combination automatically improves performance.
4. Internal D/A/N/K/P/W acronyms, Table 13 program names, and the §H.3 companion handoff are not bibliographic sources. Each is mapped to an anonymous supplement identifier, a scientific description, or explicit removal.
5. No author-repository, Overleaf, or username URL belongs in the verified bibliography. Those identifying strings that still sit in the reconstructed manuscript or author-only appendices are listed for NS-022/NS-024 removal.

## Method

- Transcribed entries `[1]`–`[12]` from PDF page 10 (numbered lines 308–335).
- Resolved publisher metadata through Crossref `https://api.crossref.org/works/{doi}` on 2026-09-11.
- Confirmed the Solar-Lezama dissertation title against the EECS catalog HTML title `Program Synthesis By Sketching` at technical report `UCB/EECS-2008-176` (the neighboring number `EECS-2008-164` is a different report).
- Compared each in-text citation with the cited work's actual contribution.
- Did not treat arXiv mirrors as a substitute for the venue record when a publisher DOI exists.
- Did not execute research experiments or claim that citing a method means this paper reimplemented it.

## Entry-by-entry verification

### [1] `baseline01` — Necula, Proof-carrying code, POPL 1997

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Author | George C. Necula | George C. Necula |
| Title | Proof-carrying code | Proof-carrying code |
| Venue | POPL, 1997 | POPL '97, Paris, 15–17 January 1997 |
| Pages | 106–119 | 106–119 |
| DOI | `10.1145/ 263699.263712` (line-wrapped space) | `10.1145/263699.263712` |

Adjacent statement (PDF p. 9 line 283): proof-carrying code attaches checkable policy evidence to untrusted code. That is the paper's contribution. **Supported.**

Correction: join the wrapped DOI; do not leave a space after `10.1145/`.

### [2] `baseline02` — Cousot and Cousot, Abstract interpretation, POPL 1977

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | Patrick Cousot and Radhia Cousot | Patrick Cousot and Radhia Cousot |
| Title | Abstract interpretation: a unified lattice model for static analysis of programs by construction or approximation of fixpoints | Same title; Crossref splits title/subtitle but the full string is the work's title |
| Venue | POPL, 1977 | POPL '77, Los Angeles, 17–19 January 1977 |
| Pages | 238–252 | 238–252 |
| DOI | omitted | `10.1145/512950.512973` |

Adjacent statements: abstract interpretation reasons over approximations (p. 9 lines 283–284). **Supported.** The work is the standard lattice-theoretic AI paper; it is not CEGAR.

Correction: add the omitted DOI.

### [3] `baseline03` — Clarke et al., Counterexample-guided abstraction refinement, CAV 2000

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | Edmund M. Clarke, Orna Grumberg, Somesh Jha, Yuan Lu, and Helmut Veith | Crossref records the first given name as Edmund; the original PDF's `Edmund M.` is the conventional form and is retained |
| Title | Counterexample- guided abstraction refinement | Counterexample-Guided Abstraction Refinement |
| Venue | CAV, 2000, pp. 154–169 | Computer Aided Verification (LNCS 1855), 2000, pp. 154–169 |
| DOI | `10.1007/10722167_15` | `10.1007/10722167_15` |

Adjacent statements: CEGAR refines approximations with counterexamples (p. 9); CEGAR versus CEGIS (p. 5 lines 141–142). **Supported.** CEGAR changes the abstraction; it does not search bounded program sketches.

Correction: drop the line-break hyphen in `Counterexample- guided`; record LNCS 1855.

### [4] `baseline04` — Pnueli, Siegel, and Singerman, Translation validation, TACAS 1998

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | Amir Pnueli, Michael Siegel, and Eli Singerman | Crossref stores initials; the TACAS paper and the draft use the full given names, which are retained |
| Title | Translation validation | Translation validation |
| Venue | TACAS, 1998, pp. 151–166 | Tools and Algorithms for the Construction and Analysis of Systems, LNCS 1384, 1998, pp. 151–166 |
| DOI | omitted | `10.1007/BFb0054170` |

Adjacent statements: translation validation checks a produced transformation rather than trusting every conversion (p. 3 line 83; p. 9 lines 284–286). **Supported.** This is the same work cited as companion-paper bibliography entry `original07` in the autoformalization draft; the literature overlap is disclosed in `related_paper_overlap.md` and is not independent experimental replication.

Correction: add the omitted DOI and LNCS 1384.

### [5] `baseline05` — Solar-Lezama, Program Synthesis by Sketching, PhD dissertation, 2008

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Author | Armando Solar-Lezama | Armando Solar-Lezama |
| Title | Program Synthesis by Sketching | Program Synthesis By Sketching (EECS catalog title) |
| Venue | PhD dissertation, University of California, Berkeley, 2008 | Same. Catalog report `UCB/EECS-2008-176`, HTML title confirmed 2026-09-11 |
| Identifier | none | `https://www2.eecs.berkeley.edu/Pubs/TechRpts/2008/EECS-2008-176.html` |

Adjacent statements: CEGIS searches bounded candidates against accumulated counterexamples (p. 5, p. 9). **Supported.** Sketching/CEGIS is the dissertation's core method. OpenAlex lists Rastislav Bodík as a coauthor; that is catalog noise for the advisor and is not copied into the bibliography.

Correction: add the verified technical-report number `UCB/EECS-2008-176`. Do not cite `EECS-2008-164`, whose catalog title is a different dissertation.

### [6] `baseline06` — Willsey et al., egg, PACMPL 2021

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | Max Willsey, Chandrakana Nandi, Yisu Remy Wang, Oliver Flatt, Zachary Tatlock, and Pavel Panchekha | Same six authors, same order |
| Title | egg: Fast and extensible equality saturation | egg: Fast and extensible equality saturation |
| Venue | POPL, 2021 | Proc. ACM Program. Lang. 5, POPL (2021), pp. 1–29 |
| DOI | `10.1145/3434304` | `10.1145/3434304` |

Adjacent statement: equality saturation represents alternatives under rewrite relations (p. 9 line 286). **Supported.**

Correction: give the PACMPL volume/issue and pages; the short POPL label is the issue, not a missing DOI.

### [7] `baseline07` — Mokhov, Mitchell, and Peyton Jones, Build systems à la carte, ICFP 2018 / JFP 2020

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | Andrey Mokhov, Neil Mitchell, and Simon Peyton Jones | Same three authors |
| Title | Build systems à la carte | Same. Expansion: Build systems à la carte: Theory and practice |
| Venue | ICFP 2018; JFP 30, 2020 | PACMPL 2(ICFP), 2018, pp. 1–29, doi `10.1145/3236774`; JFP 30, e11, 2020, doi `10.1017/S0956796820000088` |

Adjacent statement: build-system research separates scheduling from rebuilding (p. 9 lines 290–291). **Supported.** That separation is the paper's central distinction (schedule vs rebuild). The draft's reuse design is then correctly described as additional statement/fixture/trust/authority conditions, not as a claim that Mokhov et al. already published those conditions.

Correction: add both DOIs and the JFP article number `e11`.

### [8] `baseline08` — Yang et al., SWE-agent, NeurIPS 2024

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | John Yang, Carlos E. Jimenez, Alexander Wettig, Kilian Lieret, Shunyu Yao, Karthik Narasimhan, and Ofir Press | Crossref omits Jimenez's middle initial; the draft's `Carlos E.` is retained as the conventional published form |
| Title | SWE-agent: Agent-computer interfaces enable automated software engineering | SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering |
| Venue | NeurIPS 37, 2024 | Advances in Neural Information Processing Systems 37, 2024, pp. 50528–50652 |
| DOI | omitted | `10.52202/079017-1601` |

Adjacent statements: repository agents make the agent–tool boundary central to useful repair (p. 1 lines 23–24); coding-agent baseline (p. 9 lines 291–293). **Supported.** SWE-agent is about the agent–computer interface, not about proof-carrying supervision.

Correction: add the NeurIPS DOI and page range. Citing SWE-agent does not mean this paper ran SWE-bench.

### [9] `baseline09` — Yang et al., LeanDojo, NeurIPS 2023

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | Kaiyu Yang, Aidan Swope, Alex Gu, Rahul Chalamala, Peiyang Song, Shixing Yu, Saad Godil, Ryan J. Prenger, and Animashree Anandkumar | Same nine authors (Crossref: Ryan J Prenger) |
| Title | LeanDojo: Theorem proving with retrieval-augmented language models | LeanDojo: Theorem Proving with Retrieval-Augmented Language Models |
| Venue | NeurIPS 36, 2023 | Advances in Neural Information Processing Systems 36, 2023, pp. 21573–21612 |
| DOI | omitted | `10.52202/075280-0944` |

Adjacent statement: premise-retrieval systems are relevant baselines (p. 9 lines 292–293). **Supported.** LeanDojo is retrieval-augmented theorem proving. It is not a coding-agent repair result and is not claimed as one.

Correction: add DOI and pages.

### [10] `baseline10` — Jiang et al., Thor, NeurIPS 2022

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | Albert Qiaochu Jiang, Wenda Li, Szymon Tworkowski, Konrad Czechowski, Tomasz Odrzygóźdź, Piotr Miłoś, Yuhuai Wu, Mateja Jamnik | Same eight authors. The PDF OCR-folded Polish names (`Odrzygóźdź`, `Miłoś`); Crossref ASCII-folds them. The verified BibTeX uses the scholarly Unicode/TeX forms |
| Title | Thor: Wielding hammers to integrate language models and automated theorem provers | Thor: Wielding Hammers to Integrate Language Models and Automated Theorem Provers |
| Venue | NeurIPS 35, 2022 | Advances in Neural Information Processing Systems 35, 2022, pp. 8360–8373 |
| DOI | omitted | `10.52202/068431-0608` |

Adjacent statement: hammer systems are relevant baselines (p. 9 lines 292–293). **Supported.** Thor couples language models with automated theorem provers/hammers.

This work is also reconstructed bibliography entry `original10` in the autoformalization draft. Shared literature is not shared experimental evidence; see `related_paper_overlap.md`.

Correction: restore names, add DOI and pages, drop the `in- tegrate` line break.

### [11] `baseline11` — Mündler et al., SWT-Bench, NeurIPS 2024

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | Niels Mündler, Mark Niklas Müller, Jingxuan He, and Martin Vechev | Crossref records Mark Müller; the draft's `Mark Niklas Müller` is retained as the conventional published form |
| Title | SWT-Bench: Testing and validating real-world bug-fixes with code agents | SWT-Bench: Testing and Validating Real-World Bug-Fixes with Code Agents |
| Venue | NeurIPS 37, 2024 | Advances in Neural Information Processing Systems 37, 2024, pp. 81857–81887 |
| DOI | omitted | `10.52202/079017-2601` |

Adjacent statements: automated testing studies and test-generation benchmarks (p. 1 lines 23–24; p. 9 lines 291–292). **Supported.** SWT-Bench evaluates tests for real-world bug-fixes with code agents. It is a baseline for the agent–test boundary, not a result of this paper.

Correction: add DOI and pages.

### [12] `baseline12` — Pan et al., LLMLingua-2, Findings of ACL 2024

| Field | Draft transcription | Verified primary record |
|---|---|---|
| Authors | Zhuoshi Pan et al. | Zhuoshi Pan, Qianhui Wu, Huiqiang Jiang, Menglin Xia, Xufang Luo, Jue Zhang, Qingwei Lin, Victor Rühle, Yuqing Yang, Chin-Yew Lin, H. Vicky Zhao, Lili Qiu, and Dongmei Zhang |
| Title | LLMLingua-2: Data distillation for efficient and faithful task-agnostic prompt compression | LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression |
| Venue | Findings of ACL, 2024, pp. 963–981 | Findings of the Association for Computational Linguistics: ACL 2024, pp. 963–981 |
| DOI | `10.18653/v1/2024.findings-acl.57` | `10.18653/v1/2024.findings-acl.57` |

Adjacent statement: prompt compression provides a relevant baseline (p. 9 lines 292–293). **Supported.** The citation does not claim that this paper uses or outperforms LLMLingua-2.

Correction: expand `et al.` to the Crossref author list.

## In-text citation support

Bibliographic citations appear only in the reconstructed scientific text at these sites (reference-list markers on PDF p. 10 are inventory, not uses).

| Site | Citation | Adjacent claim | Support |
|---|---|---|---|
| p. 1 lines 23–24 | `[8, 11]` | Agent–tool boundary is central to useful repair | SWE-agent `[8]` is an agent-interface paper; SWT-Bench `[11]` is a test-validation benchmark. Supported as problem-setting baselines, not as this paper's measurements. |
| p. 3 line 83 | `[4]` | Translation validation checks the particular conversion | Pnueli et al. Supported. |
| p. 5 lines 141–142 | `[3, 5]` | CEGAR refines abstractions after spurious traces; CEGIS refines bounded candidates | Clarke et al. `[3]` and Solar-Lezama `[5]`. The pair covers both clauses. Supported. Do not read `[3]` as a CEGIS citation in isolation. |
| p. 9 lines 283–287 | `[1]`, `[2, 3]`, `[4, 5]`, `[6]` | Foundations: PCC, AI, CEGAR, translation validation, CEGIS, equality saturation | Each work matches the attributed idea. The draft then states these are not newly invented here. Supported. |
| p. 9 lines 290–293 | `[7]`, `[8, 11]`, `[9, 10]`, `[12]` | Build systems, coding agents/tests, retrieval/hammers, prompt compression as baselines | Each work matches the attributed baseline class. Supported. None is a claim that this paper reran those benchmarks. |

No bibliographic citation is used to underwrite a numerical result, a first-of-kind claim, or a deployment.

## Novelty bound (no invented first-of-kind claim)

The draft's own wording is the bound this audit retains:

- PDF p. 9 line 287: the twelve methods “are foundations, not newly invented algorithms in this work.”
- PDF p. 9 lines 288–290: the intended difference is composition at the agent's operational boundary — persistent semantic state, explicit obligations, residual model authorization, phase-aware test evidence, and accepted-transition publication.
- PDF p. 9 lines 293–294: “We do not claim that this is the first neurosymbolic agent or that combining these techniques automatically improves performance.”
- PDF p. 1 lines 17–19 and p. 9 lines 304–306: the thesis is a method for governing repository evolution with explicit evidence, to be decided by paired evaluation, not a claim that hashing, model confidence, or every solver proves arbitrary Python.

This audit does not add a priority claim. If later measured results exist, NS-022 may state the tested composition and its observed effect, still without converting baselines into “first” language. Unevaluated composition remains a specified method, not a demonstrated improvement.

Direct comparisons required by this task, all bounded as literature rather than rerun experiments:

| Class | Cited works | Comparison to this paper's intended composition |
|---|---|---|
| Proof-carrying / checkable evidence | `[1]` Necula | PCC attaches checkable policy to untrusted code. This draft additionally persists semantic state, obligations, and accepted-transition publication. It does not claim a new PCC calculus. |
| Approximation and refinement | `[2]` Cousot, `[3]` Clarke, `[5]` Solar-Lezama, `[6]` egg | AI, CEGAR, CEGIS, and equality saturation are selected tools. Table 2/7 already limit each tool's question. No row licenses a backend by citation. |
| Translation checking | `[4]` Pnueli | Used for per-conversion validation, not as a claim that every IR projection is validated. |
| Build / reuse | `[7]` Mokhov et al. | Schedule-versus-rebuild is the cited distinction. Fixture/statement/trust/authority conditions are additional design, pending qualification. |
| Agents and tests | `[8]` SWE-agent, `[11]` SWT-Bench | Relevant agent–tool and test-validation baselines. This paper's A–D protocol is not a SWE-bench or SWT-Bench run. |
| Retrieval and hammers | `[9]` LeanDojo, `[10]` Thor | Relevant proof-search baselines. Native/hammer qualification is optional and currently unavailable in the NS-014 profile. |
| Prompt compression | `[12]` LLMLingua-2 | Relevant compression baseline. Semantic context reduction is a measurable consequence, not the sole purpose, and Table 5 remains preliminary. |

## Internal shorthand and identifying links

Bracketed workstream labels (`[D1]`, `[A1–A5]`, `[N1–N14]`, `[K1–K4]`, `[P3]`, `[P6]`, `[P8]`, `[P11]`, `[W1–W4]`), Table 13 program names (ASEH, DOEP, PCPR, PCSM), PCTDD, M1–M3, and `[B1]` are not in the twelve-item reference list. They cannot stay as unresolvable shorthand.

`artifact_citation_map.json` maps each token to:

- an anonymous supplement identifier (`anon-supplement:<role>`), or
- a scientific description that already appears in the adjacent sentence, or
- explicit removal (author-local worktree `[B1]`, unused range members, Appendix K.2 campaign directives, the §H.3 companion reconciliation handoff).

Identifying strings that must not enter the anonymous submission:

- author-local worktree language at PDF p. 17 line 520;
- the companion reconciliation handoff at PDF p. 21 lines 594–596;
- Appendix K.2 “final author actions” and “separate audit/ledger is author-only” (p. 25);
- user-local toolchain paths in `manuscript/BUILD.md` (build documentation, not scientific text).

This audit's four public outputs contain no GitHub, Overleaf, username, or author-repository URL.

## Follow-up that this task does not perform

- NS-022 integrates `verified_references.bib` into the recovered manuscript, applies the label replacements, and removes author-only history from scientific text.
- NS-023 maps conditional theorem assumptions to gates.
- NS-024 performs the anonymity and disclosure audit, including live artifact URLs after they exist.
- NS-025 is the independent final readiness review.

Until those tasks run, the reconstructed `manuscript/main.tex` still contains the original shorthand. That is an NS-022 obligation, not an unverified bibliography.

## Limitations

- Crossref given-name initials sometimes differ from the papers' conventional bylines; conventional bylines are retained and the difference is recorded above.
- Native PDF author-line inspection of the NeurIPS/ACL PDFs was not repeated beyond Crossref and the EECS catalog; venue, DOI, year, and page fields are the Crossref records.
- No claim is made that the cited systems were re-executed for this workshop paper.
- Shared implementation surfaces with the autoformalization and law-to-action submissions are not independent replications; see `related_paper_overlap.md`.
