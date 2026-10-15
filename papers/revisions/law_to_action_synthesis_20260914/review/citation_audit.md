# Citation audit — Law to Action

Checked 14 September 2026. **All 40 references cited in the revised PDF correspond to real primary sources.** Every citation key resolves, and the selected bibliography contains no unused entries.

The review checked titles, author lists, dates, venues, pagination, DOI/arXiv identities, and the background claims supported by each reference. It used official proceedings, publisher-deposited Crossref metadata, author/institution pages, arXiv records and selected PDFs, official protocol documentation, and the pinned dataset APIs. Matching a DOI URL alone was not treated as sufficient verification. This is a citation audit, not a replication of the referenced studies.

## Corrections and version choices

- Zanzibar: replaced the incorrect author list using current USENIX metadata.
- Code-model paper: corrected Michael Petrov and pinned arXiv v2.
- Cedar: restored the published author form Andrew M. Wells.
- Clover and AgentSpec: replaced valid preprint entries with verified published versions.
- Progent: aligned the year with the cited 2026 revision.
- AgentHarm: retained all 14 authors of the author-updated arXiv v3 and identified that version explicitly. The original proceedings version has 12 authors; this is a version difference, not a fabricated reference.
- libp2p: corrected the specification title and 2022 revision date. IPFS and UCAN entries now use access dates without inventing publication years.
- Added separate source-package citations for CVEfixes and SkillCenter; their exact revisions were verified via the primary dataset API.
- Corrected the prose to distinguish Catala from the Mlang French tax compiler, and to identify LeanDojo as theorem proving.
- The pinned SkillCenter card declares a custom license category. The checklist no longer describes it as unqualified MIT packaging; nested source terms remain distinct.

The original 39 bibliography entries, including the uncited workshop page, were all checked. The workshop entry was moved to the format audit, and two dataset entries were added, leaving 40 cited references. Miller's dissertation was confirmed through live indexed author and institutional primary pages; direct PDF retrieval was blocked or timed out. The audit does not claim a full direct reading of that PDF. The accompanying JSON records the primary evidence and access limitation for each reference.

## Reference-by-reference primary evidence

| PDF no. | Citation key | Verified work and primary evidence | Action |
|---|---|---|---|
| 1 | `mcp` | [Model Context Protocol specification, revision 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25) | Retained verified metadata. |
| 2 | `mcp-auth` | [Model Context Protocol: Authorization, revision 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) | Retained verified metadata. |
| 3 | `saltzer1975protection` | [The protection of information in computer systems](https://web.mit.edu/Saltzer/www/publications/pubs.html) | Retained verified metadata. |
| 4 | `schneider2000enforceable` | [Enforceable security policies](https://www.cs.cornell.edu/fbs/fullist.html) | Retained verified metadata. |
| 5 | `erlingsson2000irm` | [IRM enforcement of Java stack inspection](https://www.cs.cornell.edu/fbs/fullist.html) | Retained verified metadata. |
| 6 | `ligatti2005edit` | [Edit automata: enforcement mechanisms for run-time security policies](https://link.springer.com/article/10.1007/s10207-004-0046-8) | Retained verified metadata. |
| 7 | `hamlen2006enforcement` | [Computability classes for enforcement mechanisms](https://www.cs.cornell.edu/fbs/fullist.html) | Retained verified metadata. |
| 8 | `wang2025agentspec` | [AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/29/AgentSpec-Customizable-Runtime-Enforcement-for-Safe-and-Reliable-LLM-Agents) | Updated the valid preprint citation to ICSE 2026 publication metadata. |
| 9 | `shi2025progent` | [Progent: Securing AI Agents with Privilege Control](https://arxiv.org/abs/2504.11703v3) | Aligned year 2026 with the explicitly cited revised arXiv v3. |
| 10 | `debenedetti2025camel` | [Defeating Prompt Injections by Design](https://arxiv.org/abs/2503.18813v2) | Retained verified metadata. |
| 11 | `sergot1986bna` | [The British Nationality Act as a logic program](https://www.doc.ic.ac.uk/~rak/papers/rak.html) | Retained verified metadata. |
| 12 | `prakken2015lawlogic` | [Law and logic: A review from an argumentation perspective](https://research-portal.uu.nl/en/publications/law-and-logic-a-review-from-an-argumentation-perspective/) | Retained verified metadata. |
| 13 | `benzmueller2020logikey` | [Designing normative theories for ethical and legal reasoning: LogiKEy framework, methodology, and tool support](https://arxiv.org/abs/1903.10187) | Retained verified metadata. |
| 14 | `catala` | [Catala: a programming language for the law](https://arxiv.org/abs/2103.03198) | Retained verified metadata. |
| 15 | `merigoux2021tax` | [A modern compiler for the French tax code](https://www.microsoft.com/en-us/research/publication/a-modern-compiler-for-the-french-tax-code/) | Retained verified metadata. |
| 16 | `necula1997pcc` | [Proof-carrying code](https://doi.org/10.1145/263699.263712) | Retained verified metadata. |
| 17 | `appel1999pca` | [Proof-carrying authentication](https://collaborate.princeton.edu/en/publications/proof-carrying-authentication/) | Retained verified metadata. |
| 18 | `pnueli1998translation` | [Translation validation](https://link.springer.com/chapter/10.1007/BFb0054170) | Retained verified metadata. |
| 19 | `leroy2009compcert` | [Formal verification of a realistic compiler](https://xavierleroy.org/publi/compcert-CACM.pdf) | Retained verified metadata. |
| 20 | `miller2006robust` | [Robust Composition: Towards a Unified Approach to Access Control and Concurrency Control](https://www.erights.org/talks/thesis/) | Retained verified metadata. |
| 21 | `birgisson2014macaroons` | [Macaroons: Cookies with Contextual Caveats for Decentralized Authorization in the Cloud](https://www.ndss-symposium.org/ndss2014/accepted-papers/) | Retained verified metadata. |
| 22 | `pang2019zanzibar` | [Zanzibar: Google's Consistent, Global Authorization System](https://www.usenix.org/conference/atc19/presentation/pang) | Corrected author list using current official USENIX metadata. |
| 23 | `cutler2024cedar` | [Cedar: A New Language for Expressive, Fast, Safe, and Analyzable Authorization](https://arxiv.org/abs/2403.04651) | Restored Andrew M. Wells as printed in the published paper. |
| 24 | `ucan` | [User Controlled Authorization Network (UCAN) Specification](https://ucan.xyz/specification/) | Removed unsupported publication year; recorded consultation date. |
| 25 | `chen2021codex` | [Evaluating Large Language Models Trained on Code](https://arxiv.org/pdf/2107.03374v2) | Corrected Michael Petrov; pinned arXiv v2. |
| 26 | `jimenez2024swebench` | [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770) | Retained verified metadata. |
| 27 | `sun2024clover` | [Clover: Closed-Loop Verifiable Code Generation](https://link.springer.com/chapter/10.1007/978-3-031-65112-0_7) | Updated the valid preprint citation to the published SAIV 2024 chapter. |
| 28 | `yang2023leandojo` | [LeanDojo: Theorem Proving with Retrieval-Augmented Language Models](https://arxiv.org/abs/2306.15626) | Retained verified metadata. |
| 29 | `wu2022autoformalization` | [Autoformalization with Large Language Models](https://arxiv.org/abs/2205.12615) | Retained verified metadata. |
| 30 | `debenedetti2024agentdojo` | [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352) | Retained verified metadata. |
| 31 | `ruan2024toolemu` | [Identifying the Risks of LM Agents with an LM-Emulated Sandbox](https://arxiv.org/abs/2309.15817) | Retained verified metadata. |
| 32 | `zhan2024injecagent` | [InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents](https://arxiv.org/abs/2403.02691) | Retained verified metadata. |
| 33 | `yao2024taubench` | [$\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045) | Retained verified metadata. |
| 34 | `andriushchenko2025agentharm` | [AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents](https://arxiv.org/pdf/2410.09024v3) | Explicitly cited author-updated arXiv v3 to match the 14-author list. |
| 35 | `cvefixes` | [CVEfixes: automated collection of vulnerabilities and their fixes from open-source software](https://arxiv.org/abs/2107.08760) | Retained verified metadata. |
| 36 | `cvefixes-source` | [hitoshura25/cvefixes](https://huggingface.co/api/datasets/hitoshura25/cvefixes/revision/d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2) | Added citation for the exact source package; pinned revision verified via primary API. |
| 37 | `skillcenter-source` | [SkillCenter Bundles](https://huggingface.co/api/datasets/Tommysha/skillcenter-bundles/revision/f9dd4fec3c86d85ebf116c7408ac5ce602c418a1) | Added dataset citation; pinned revision and card metadata verified via primary API. |
| 38 | `quack` | [Quack: The DuckDB Client-Server Protocol](https://duckdb.org/2026/05/12/quack-remote-protocol) | Retained verified metadata. |
| 39 | `ipfs` | [Content Identifiers (CIDs)](https://docs.ipfs.tech/concepts/content-addressing/) | Removed unsupported publication year; recorded consultation date. |
| 40 | `libp2p` | [Connection Establishment in libp2p](https://github.com/libp2p/specs/blob/master/connections/README.md) | Corrected specification title and revision year 2022. |

## Format and scientific scope

The revised paper has **7 main pages**, including the figure and tables. References and appendices bring the full PDF to 23 pages. The [official workshop policy](https://vericodegen.github.io/cfp.html) permits 4–9 main pages and excludes references and technical appendices from that count. The supplied style, anonymous author block, and checklist questions/answers remain unchanged.

The original architecture has been integrated with the existing 900-cell fixed-action study. Richer logical views, learned proposals, context minification, program-state reuse, and closed-loop planning are separated from measured claims. No new experiment, semantic validation, or scientific result was added during this revision.
