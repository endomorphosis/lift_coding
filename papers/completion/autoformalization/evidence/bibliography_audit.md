# AF-022 bibliography audit

Primary sources were checked against the recovered PDF reference list
(`manuscript/pages/page-10.txt`, original lines 376--404) and public
bibliographic records (arXiv identifiers, journal/proceedings metadata, and
DOIs cited below). No unrelated autoformalization or verified-coding benchmark
was executed for this paper.

## Original PDF references [1]--[10]

| PDF | Key | Primary-source check | Status |
| --- | --- | --- | --- |
| [1] | `wu2022autoformalization` | Wu, Jiang, Li, Rabe, Staats, Jamnik, Szegedy. *Autoformalization with Large Language Models*. NeurIPS 35, 2022. arXiv:2205.12615. | Verified. Title, author list, venue, and year match the PDF. |
| [2] | `azerbayev2023proofnet` | Azerbayev, Piotrowski, Schoelkopf, Ayers, Radev, Avigad. *ProofNet: Autoformalizing and formally proving undergraduate-level mathematics*. arXiv:2302.12433, 2023. | Verified as an arXiv preprint. The PDF does not claim a conference version; none is invented here. |
| [3] | `benzmuller2020logikey` | Benzmüller, Parent, van der Torre. *Designing normative theories for ethical and legal reasoning: LogiKEy framework, methodology, and tool support*. Artificial Intelligence 287:103348, 2020. doi:10.1016/j.artint.2020.103348. | Verified. |
| [4] | `goguen1992institutions` | Goguen and Burstall. *Institutions: Abstract model theory for specification and programming*. JACM 39(1):95--146, 1992. doi:10.1145/147508.147524. | Verified. |
| [5] | `kifer1995flogic` | Kifer, Lausen, Wu. *Logical foundations of object-oriented and frame-based languages*. JACM 42(4):741--843, 1995. doi:10.1145/210332.210335. | Verified. Recovered PDF spelling ``framebased'' corrected to the journal hyphenation; authors/year/pages unchanged. |
| [6] | `kowalski1986events` | Kowalski and Sergot. *A logic-based calculus of events*. New Generation Computing 4:67--95, 1986. doi:10.1007/BF03037383. | Verified. |
| [7] | `pnueli1998translation` | Pnueli, Siegel, Singerman. *Translation validation*. TACAS, LNCS 1384, pp. 151--166, 1998. doi:10.1007/BFb0054170. | Verified. |
| [8] | `yi2018nsvqa` | Yi, Wu, Gan, Torralba, Kohli, Tenenbaum. *Neural-symbolic VQA*. NeurIPS 31, 2018. arXiv:1810.02338. | Verified. Recovered PDF wrapped the arXiv URL across a line break; the identifier is unchanged. |
| [9] | `jiang2024multilanguage` | Jiang, Li, Jamnik. *Multi-language diversity benefits autoformalization*. NeurIPS 37, 2024, as printed on the supplied PDF. | Recovered from the PDF. Closely related public preprint: *Multilingual Mathematical Autoformalization*, arXiv:2311.03755 (Jiang, Li, Jamnik). Venue/year are retained as recovered; this paper does not import MMA/ProofNet numbers as results. |
| [10] | `jiang2022thor` | Jiang, Li, Tworkowski, Czechowski, Odrzygóźdź, Miłoś, Wu, Jamnik. *Thor: Wielding hammers to integrate language models and automated theorem provers*. NeurIPS 35, 2022. | Verified. Author list and title match the PDF. |

No original reference was dropped. No citation was retargeted to a different work.

## Missing material comparisons (added, not run)

The recovered related-work section had ten references and little comparison
with current verified-coding or autoformalization systems. The rewrite adds
the following *placement* citations. Each is labeled in `references.bib` and
in Section 8 of `main.tex` as comparison only.

| Key | Why it belongs | What is *not* claimed |
| --- | --- | --- |
| `yang2023leandojo` | Retrieval-augmented theorem proving; closest public analogue to the paper's retrieval+ITP route. | LeanDojo numbers were not measured. |
| `jiang2023dsp` | Informal-to-formal proving; distinguishes planning/sketches from checked proofs. | DSP/miniF2F were not measured. |
| `blanchette2013sledgehammer` | Hammer reconstruction contract that Thor extends. | Sledgehammer was not executed. |
| `first2023baldur` | Whole-proof generation/repair with LLMs; relevant to Leanstral-style proposals. | Baldur was not executed. |
| `leroy2009compcert` | Machine-checked compiler as a verified-coding use case. | CompCert was not re-benchmarked. |
| `klein2009sel4` | Machine-checked OS kernel as a verified-coding use case. | seL4 was not re-benchmarked. |
| `leino2010dafny` | SMT-backed program verifier for functional correctness. | Dafny was not re-benchmarked. |

## Guardrails

- Related-work citations are not result rows.
- Table 13 constructed retrieval/planning diagnostics are not LeanDojo, DSP, or Sledgehammer evaluations.
- The synthetic policy--code--trace example is not CompCert, seL4, or Dafny.
- Finite AF-006 checks are not ProofNet or miniF2F accuracy.
- Uncited theorem-proving leaderboards (AlphaProof, CoqGym, PACT, GPT-f, HyperTree, Verus, F\*, Clover) were not added as padding and were not run.
