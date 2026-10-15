# Live verification of modern scholarly citations

Checked 2026-09-14. All 16 assigned papers are real, and all seven DOI strings already present among these entries identify the intended publications. Verification used primary publication records, author papers, arXiv records/PDFs, and publisher-deposited DOI metadata. No shared manuscript or bibliography files were edited.

The main corrections are **Michael Petrov**, the full name **Andrew M. Wells**, explicit version handling for **AgentHarm** and **Progent**, and optional publication updates for **Clover** and **AgentSpec**. The prose should name **theorem proving** when grouping LeanDojo with code generation and autoformalization.

Suggested replacements are in `corrections_modern.bib`. Raw publisher metadata and arXiv metadata are retained in `modern_primary_metadata/`. Valid initial-preprint citations are distinguished from errors; no unsupported DOI, venue, or page range was added.

## catala — verified

**Metadata:** Catala: a programming language for the law. Venue/year: ['Proceedings of the ACM on Programming Languages'] / 2021. Pages: 1-29. Publication DOI: 10.1145/3473582.

- No substantive correction. All authors, title, year, journal, volume, issue, DOI, and article pagination agree. Article 77 spans pages 1–29; 77:1–77:29 is a legitimate article-number pagination rendering.

**Claim checked:** Catala makes legal specifications executable and has been applied to tax law.

Supported. The publisher abstract describes executable statutory specifications and evaluations involving US income tax and French family benefits. This supports an executable-law precedent, not automated legal-fidelity validation for this manuscript.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2103.03198)
- [publisher-deposited DOI registration metadata](https://api.crossref.org/works/10.1145/3473582)
- [primary publication, conference, author, or publisher source](https://doi.org/10.1145/3473582)

## cvefixes — verified

**Metadata:** CVEfixes: automated collection of vulnerabilities and their fixes from open-source software. Venue/year: ['Proceedings of the 17th International Conference on Predictive Models and Data Analytics in Software Engineering'] / 2021. Pages: 30-39. Publication DOI: 10.1145/3475960.3475985.

- No substantive correction. Publisher-deposited author is Guru Bhandari, while arXiv spells the first name Guru Prasad Bhandari. These are source-name variants, not a wrong author. Publication year, venue, pages 30–39, and DOI match.

**Claim checked:** CVEfixes links vulnerability records to repositories and fixes.

Supported. The author abstract describes gathering NVD/CVE records, vulnerable source code, fixes, and repository information. The publication does not establish the manuscript-specific sample counts or transfer to its export handler.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2107.08760)
- [publisher-deposited DOI registration metadata](https://api.crossref.org/works/10.1145/3475960.3475985)

## cutler2024cedar — author name refinement

**Metadata:** Cedar: A New Language for Expressive, Fast, Safe, and Analyzable Authorization. Venue/year: ['Proceedings of the ACM on Programming Languages'] / 2024. Pages: 670-697. Publication DOI: 10.1145/3649835.

- Refine the last author to Andrew M. Wells: both the publisher deposit and the extended PDF title page include M. The arXiv abstract omits it.
- Title, year, journal 8(OOPSLA1), pages 670–697, and DOI match the published article. The arXiv version has Extended Version appended to its title and should not replace the published title when the publication is cited.

**Claim checked:** Policy languages provide ways to restrict authority.

Supported. Cedar supplies a policy language and evaluation engine for access decisions, together with policy validation and analysis. It is relevant to authorization; no claim of source-to-law fidelity follows.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2403.04651)
- [publisher-deposited DOI registration metadata](https://api.crossref.org/works/10.1145/3649835)
- [primary publication, conference, author, or publisher source](https://arxiv.org/pdf/2403.04651v2)
- [primary publication, conference, author, or publisher source](https://assets.amazon.science/96/a8/1b427993481cbdf0ef2c8ca6db85/cedar-a-new-language-for-expressive-fast-safe-and-analyzable-authorization.pdf)

## chen2021codex — author correction

**Metadata:** Evaluating Large Language Models Trained on Code. Venue/year: arXiv preprint / 2021. Pages: not established for this version. Publication DOI: not claimed/established.

- Correct Mikhail Petrov to Michael Petrov. Both arXiv v2 metadata and the PDF title page independently confirm Michael. All other listed authors match.
- The 2021 preprint year and title are correct. Pin v2 (14 July 2021) for a fully specified citation; no conference venue or proceedings pagination is supplied by this source.

**Claim checked:** Code-generation benchmarks emphasize functional correctness.

Supported. The abstract and Section 2 describe HumanEval and unit-test-based functional correctness of synthesized programs.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2107.03374)
- [primary publication, conference, author, or publisher source](https://arxiv.org/pdf/2107.03374v2)

## jimenez2024swebench — verified

**Metadata:** SWE-bench: Can Language Models Resolve Real-World GitHub Issues?. Venue/year: The Twelfth International Conference on Learning Representations / 2024. Pages: not established for this version. Publication DOI: not claimed/established.

- No substantive correction. Title, seven authors, ICLR 2024 venue/year, and arXiv identifier match. The author project site adds middle initial R to Karthik Narasimhan, whereas the proceedings and arXiv omit it; current form is supported.
- Add the official proceedings URL if desired. The unversioned arXiv currently resolves to v3 (11 November 2024); proceedings paper remains the primary venue record.

**Claim checked:** Issue-resolution benchmarks emphasize useful coding work.

Supported. The official proceedings describe editing repositories to resolve real GitHub issues; the authors project page explains the fail-to-pass testing signal.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2310.06770)
- [primary publication, conference, author, or publisher source](https://proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html)
- [primary publication, conference, author, or publisher source](https://www.swebench.com/original.html)

## sun2024clover — publication update available

**Metadata:** Clover: Closed-Loop Verifiable Code Generation. Venue/year: ['Lecture Notes in Computer Science', 'AI Verification'] / 2024. Pages: 134-155. Publication DOI: 10.1007/978-3-031-65112-0_7.

- The 2023 arXiv entry is a real initial-preprint citation, not a fabricated year. Prefer the published SAIV 2024 chapter: AI Verification, LNCS 14846, pages 134–155, DOI 10.1007/978-3-031-65112-0_7.
- All four authors and title agree. Latest arXiv is v4, dated 16 November 2024; the publisher chapter appeared 17 July 2024.

**Claim checked:** Verified generation connects programs and specifications to formal checks.

Supported. Clover checks consistency among code, docstrings, and formal annotations using formal-verification tools and language models.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2310.17807)
- [publisher-deposited DOI registration metadata](https://api.crossref.org/works/10.1007/978-3-031-65112-0_7)
- [primary publication, conference, author, or publisher source](https://link.springer.com/chapter/10.1007/978-3-031-65112-0_7)
- [primary publication, conference, author, or publisher source](https://theory.stanford.edu/~barrett/pubs/SSP%2B24-abstract.html)

## yang2023leandojo — verified

**Metadata:** LeanDojo: Theorem Proving with Retrieval-Augmented Language Models. Venue/year: ['Advances in Neural Information Processing Systems 36'] / 2023. Pages: 21573-21612. Publication DOI: 10.52202/075280-0944.

- No substantive bibliographic correction. Official NeurIPS BibTeX independently confirms the complete current author list, year 2023, volume 36, pages 21573–21612, and DOI 10.52202/075280-0944.
- The arXiv/PDF use Aidan M. Swope, Ryan Prenger, and Anima Anandkumar; official proceedings metadata uses Aidan Swope, Ryan J Prenger, and Animashree Anandkumar. Current entry follows the latter and is not an identity error.

**Claim checked:** Verified generation and autoformalization connect programs or specifications to formal checks.

Supported only with more precise grouping. LeanDojo concerns retrieval-augmented theorem proving in Lean, not natural-language autoformalization or ordinary program generation. Change the umbrella phrase to verified code generation, theorem proving, and autoformalization.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2306.15626)
- [publisher-deposited DOI registration metadata](https://api.crossref.org/works/10.52202/075280-0944)
- [primary publication, conference, author, or publisher source](https://proceedings.neurips.cc/paper_files/paper/2023/hash/4441469427094f8873d0fecb0c4e1cee-Abstract-Datasets_and_Benchmarks.html)
- [primary publication, conference, author, or publisher source](https://proceedings.neurips.cc/paper_files/paper/20324-/bibtex)

## wu2022autoformalization — verified

**Metadata:** Autoformalization with Large Language Models. Venue/year: ['Advances in Neural Information Processing Systems 35'] / 2022. Pages: 32353-32368. Publication DOI: 10.52202/068431-2344.

- No substantive correction. Publisher BibTeX confirms year 2022, volume 35, pages 32353–32368, and DOI 10.52202/068431-2344.
- Current Albert Q. Jiang and Markus N. Rabe match the paper/arXiv; publisher metadata expands Albert Qiaochu Jiang and shortens Markus Rabe. These are valid name variants.

**Claim checked:** Autoformalization connects specifications to formal checks.

Supported. The paper translates informal mathematical problems into Isabelle/HOL specifications and trains/evaluates a theorem prover. It does not report legal-language compilation.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2205.12615)
- [publisher-deposited DOI registration metadata](https://api.crossref.org/works/10.52202/068431-2344)
- [primary publication, conference, author, or publisher source](https://proceedings.neurips.cc/paper_files/paper/2022/hash/d0c6bc641a56bebee9d985b937307367-Abstract-Conference.html)
- [primary publication, conference, author, or publisher source](https://proceedings.neurips.cc/paper_files/paper/18162-/bibtex)

## debenedetti2024agentdojo — verified

**Metadata:** AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents. Venue/year: ['Advances in Neural Information Processing Systems 37'] / 2024. Pages: 82895-82920. Publication DOI: 10.52202/079017-2636.

- No substantive correction. Official NeurIPS BibTeX confirms all six authors, 2024, volume 37, pages 82895–82920, DOI 10.52202/079017-2636. The Balunovic/Balunović difference is a diacritic variant; current accented form is supported by arXiv.

**Claim checked:** AgentDojo examines attacks and motivates measuring successful work alongside forbidden effects.

Supported. The abstract and introduction explicitly discuss agent task utility and prompt-injection security, with state-based checks. Do not treat it as a scored external baseline in this paper.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2406.13352)
- [publisher-deposited DOI registration metadata](https://api.crossref.org/works/10.52202/079017-2636)
- [primary publication, conference, author, or publisher source](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html)
- [primary publication, conference, author, or publisher source](https://proceedings.neurips.cc/paper_files/paper/23699-/bibtex)

## ruan2024toolemu — verified

**Metadata:** Identifying the Risks of LM Agents with an LM-Emulated Sandbox. Venue/year: The Twelfth International Conference on Learning Representations / 2024. Pages: not established for this version. Publication DOI: not claimed/established.

- No substantive correction. Official ICLR 2024 proceedings and PDF confirm all nine authors and title. Chris J. Maddison is confirmed by the PDF, although the landing page omits J. No proceedings page range or publication DOI was supplied in the official record inspected.

**Claim checked:** ToolEmu examines risky actions of tool-using agents.

Supported. It emulates tools and evaluates safety risks using language models, with human validation of parts of the emulation/evaluation. Its observations are emulated risks, unlike this manuscript filesystem journals.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2309.15817)
- [primary publication, conference, author, or publisher source](https://proceedings.iclr.cc/paper_files/paper/2024/hash/7274ed909a312d4d869cc328ad1c5f04-Abstract-Conference.html)
- [primary publication, conference, author, or publisher source](https://proceedings.iclr.cc/paper_files/paper/2024/file/7274ed909a312d4d869cc328ad1c5f04-Paper-Conference.pdf)

## zhan2024injecagent — verified

**Metadata:** InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents. Venue/year: ['Findings of the Association for Computational Linguistics ACL 2024'] / 2024. Pages: 10471-10506. Publication DOI: 10.18653/v1/2024.findings-acl.624.

- No substantive correction. ACL Anthology confirms exact title, all four authors, Findings of ACL 2024, pages 10471–10506, and DOI 10.18653/v1/2024.findings-acl.624.

**Claim checked:** InjecAgent examines attacks on tool-using agents.

Supported. It benchmarks indirect prompt injection with attack goals involving direct user harm and private-data exfiltration.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2403.02691)
- [publisher-deposited DOI registration metadata](https://api.crossref.org/works/10.18653/v1/2024.findings-acl.624)
- [primary publication, conference, author, or publisher source](https://aclanthology.org/2024.findings-acl.624/)

## yao2024taubench — verified

**Metadata:** $\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains. Venue/year: arXiv preprint / 2024. Pages: not established for this version. Publication DOI: not claimed/established.

- No substantive correction. arXiv v1 (17 June 2024) confirms the title and all four authors; this record remains an arXiv preprint without a claimed conference venue/pages. Pin v1 if normalizing version references.

**Claim checked:** Tau-bench examines policy following in tool-user-agent interactions.

Supported. The abstract describes domain-specific APIs, policy guidelines, dynamic conversations, goal-state checking, and repeated-trial reliability. It is not itself a prompt-injection security benchmark.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2406.12045)
- [primary publication, conference, author, or publisher source](https://arxiv.org/abs/2406.12045v1)

## andriushchenko2025agentharm — version clarification

**Metadata:** AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents. Venue/year: The Thirteenth International Conference on Learning Representations / 2025. Pages: not established for this version. Publication DOI: not claimed/established.

- Version clarification required. Official ICLR proceedings landing page and PDF have 12 authors. arXiv v3 metadata AND PDF have 14, adding Eric Winsor and Jerome Wynne; the updated PDF is itself labeled Published as a conference paper at ICLR 2025.
- Preserve all 14 credited authors and explicitly link/pin the author-updated arXiv v3 (18 April 2025), documenting the author update. Alternatively, cite the original 12-author proceedings record consistently. Do not call the two additional authors fabricated.

**Claim checked:** AgentHarm examines harmful tool use.

Supported. The paper evaluates explicitly malicious multi-step agent tasks, refusal behavior, preserved capability, and benign counterparts. Harm is assessed through synthetic tool tasks, not this manuscript actual protected mutation.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2410.09024)
- [primary publication, conference, author, or publisher source](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c493d23af93118975cdbc32cbe7323f5-Abstract-Conference.html)
- [primary publication, conference, author, or publisher source](https://proceedings.iclr.cc/paper_files/paper/2025/file/c493d23af93118975cdbc32cbe7323f5-Paper-Conference.pdf)
- [primary publication, conference, author, or publisher source](https://arxiv.org/pdf/2410.09024v3)

## debenedetti2025camel — verified

**Metadata:** Defeating Prompt Injections by Design. Venue/year: arXiv preprint / 2025. Pages: not established for this version. Publication DOI: not claimed/established.

- Existing 2025 arXiv v2 citation is internally correct: title and all ten authors match; v2 is dated 24 June 2025.
- An official SaTML 2026 program entry also exists and lists the ten authors. Its abstract reports 67% whereas the v2 abstract reports 77%; retain the explicit v2 reference unless intentionally citing the conference version. No conference DOI or pages were established here, so none are invented.

**Claim checked:** CaMeL uses capabilities to isolate agent data flow.

Supported. The v2 abstract states that CaMeL extracts trusted control/data flow and enforces capabilities against unauthorized flows at tool calls. Keep any future quoted performance tied to a version: v1/conference program reports 67%, while v2 abstract reports 77%.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2503.18813v2)
- [primary publication, conference, author, or publisher source](https://satml.org/2026/program/)

## wang2025agentspec — publication update available

**Metadata:** AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents. Venue/year: ['Proceedings of the 2026 IEEE/ACM 48th International Conference on Software Engineering'] / 2026. Pages: 2938-2950. Publication DOI: 10.1145/3744916.3764546.

- Existing 2025 arXiv v3 citation is real and correctly dated (31 July 2025). A published ICSE 2026 version now exists: DOI 10.1145/3744916.3764546. Prefer this official publication for a current bibliography.
- ACM-deposited Crossref metadata gives pages 2938–2950. The author-hosted advance PDF says 12 pages; use publisher pagination, or omit pages if avoiding that minor advance/final difference. Title and all three authors agree.

**Claim checked:** AgentSpec supplies runtime triggers, predicates, and enforcement rules.

Supported. The arXiv abstract, author paper, and official ICSE program describe a DSL with triggers, predicates, and runtime enforcement mechanisms.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2503.18666v3)
- [publisher-deposited DOI registration metadata](https://api.crossref.org/works/10.1145/3744916.3764546)
- [primary publication, conference, author, or publisher source](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/29/AgentSpec-Customizable-Runtime-Enforcement-for-Safe-and-Reliable-LLM-Agents)
- [primary publication, conference, author, or publisher source](https://cposkitt.github.io/files/publications/agentspec_llm_enforcement_icse26.pdf)

## shi2025progent — version year clarification

**Metadata:** Progent: Securing AI Agents with Privilege Control. Venue/year: arXiv preprint / 2026. Pages: not established for this version. Publication DOI: not claimed/established.

- Version/year clarification required. Current title and explicit v3 URL refer to the version revised 14 May 2026, but year is 2025. Prefer year 2026 with v3. The original 16 April 2025 v1 title is Progent: Programmable Privilege Control for LLM Agents.
- All seven authors and arXiv identifier are correct. No conference venue/pages or separate publication DOI were established. Keeping 2025 solely as first-preprint year is defensible only if version date is explicit; suggested replacement uses the cited-version year.

**Claim checked:** Progent checks symbolic tool privileges and policy updates.

Supported by v3. The abstract defines policies over tool names/arguments and SMT classification of proposed policy updates into narrowing and expansion. This is a 2026-version claim; do not backdate that exact version to 2025 without explaining the initial-preprint convention.

**Primary sources:**

- [author-deposited arXiv record](https://arxiv.org/abs/2504.11703v3)
- [primary publication, conference, author, or publisher source](https://arxiv.org/abs/2504.11703v1)

## Primary-source disagreements and access limits

- AgentHarm has a genuine authorship difference between the official proceedings artifact and author-updated arXiv v3. Preserve the full 14-author updated credit by pinning that version; the alternate 12-author proceedings record is also documented.
- Several author-name expansions differ between publisher metadata and arXiv/PDFs (CVEfixes, LeanDojo, autoformalization, SWE-bench, ToolEmu). These are not classified as fabricated authors.
- Some ACM landing pages returned HTTP 403. Their DOI identities and bibliographic fields were verified with live publisher-deposited Crossref records and corroborating author/primary papers. All three NeurIPS DOI entries are also present in the official publisher BibTeX.
- AgentSpec publisher pagination is 2938–2950; an advance author PDF says 12 pages. The proposed entry follows publisher pagination.
- CaMeL 2026 program abstract and arXiv v2 report different performance figures. The present manuscript does not quote those figures; any future quotation must specify the version.
