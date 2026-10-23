# Classic-source citation audit

Verified 2026-09-14T03:23:56.401124+00:00. All 16 assigned references correspond to real works. This audit checks bibliographic identity separately from the claim each citation supports.

**Required changes:** replace the Zanzibar author list; separate the Mlang tax-compiler paper from the Catala claim. Fourteen DOI metadata responses match the intended works. One dissertation has a documented direct-access limitation; its primary records and relevant section were available through live indexed content.

The shared bibliography and manuscript were not edited. `corrections_classic.bib` contains only the corrected Zanzibar entry. Raw Crossref responses are retained under `classic_metadata/`.

## saltzer1975protection

**Metadata:** verified. The protection of information in computer systems. J.H. Saltzer; M.D. Schroeder. 1975. Venue: ['Proceedings of the IEEE']; volume 63; issue 9; pages/article 1278-1308; DOI 10.1109/proc.1975.9939.

**Cited claim:** Every access to a protected resource must pass an authorization check.

**Support:** supported. Section I.A.3(c) requires an authority check for each access and discusses initialization, recovery, shutdown, maintenance, and invalidating remembered decisions after authority changes. A design principle, not evidence that this manuscript implements complete mediation beyond its selected route.

Sources:
- [Primary source 1](https://web.mit.edu/Saltzer/www/publications/pubs.html): Author institutional publication list: full names, journal, volume 63, issue 9, September 1975, pp. 1278–1308.
- [Primary source 2](https://web.mit.edu/Saltzer/www/publications/protection/Basic.html): Author-hosted full-text rendering, Section I.A.3(c), complete mediation.
- [Primary source 3](https://api.crossref.org/works/10.1109%2FPROC.1975.9939): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## necula1997pcc

**Metadata:** verified. Proof-carrying code. George C. Necula. 1997. Venue: ["Proceedings of the 24th ACM SIGPLAN-SIGACT symposium on Principles of programming languages  - POPL '97"]; volume n/a; issue n/a; pages/article 106-119; DOI 10.1145/263699.263712.

**Cited claim:** Proof-carrying code places a checked safety proof before execution of untrusted code.

**Support:** supported. The publisher abstract specifies an untrusted producer supplying code and a safety proof of adherence to a pre-existing policy. The guarantee is relative to the specified safety policy and checking assumptions; it does not validate natural-language legal interpretation.

Sources:
- [Primary source 1](https://doi.org/10.1145/263699.263712): Publisher page returned by live search with matching title, author, POPL 1997, pp. 106–119, DOI, and abstract; direct ACM fetch separately returned HTTP 403.
- [Primary source 2](https://homes.cs.washington.edu/~mernst/teaching/6.893/readings/necula-popl97.pdf): Institution-hosted original paper, 14 pages; PDF opens, though browser text extraction returned no lines.
- [Primary source 3](https://www.cs.cmu.edu/~fox/pcc-bib.html): Original project bibliography identifies Necula, POPL, pp. 106–119, January 1997.
- [Primary source 4](https://api.crossref.org/works/10.1145%2F263699.263712): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## appel1999pca

**Metadata:** verified. Proof-carrying authentication. Andrew W. Appel; Edward W. Felten. 1999. Venue: ['Proceedings of the 6th ACM conference on Computer and communications security']; volume n/a; issue n/a; pages/article 52-62; DOI 10.1145/319709.319718.

**Cited claim:** Proof-carrying authentication places checked proof before authorization.

**Support:** supported. The abstract and Section 1 require proofs with access requests and assign proof checking to the server. The author preprint is dated August 9, 1999 and has 13 PDF pages; use the published CCS pagination 52–62, not preprint length.

Sources:
- [Primary source 1](https://collaborate.princeton.edu/en/publications/proof-carrying-authentication/): Author institution record: two authors, CCS 1999, pp. 52–62, DOI, and abstract.
- [Primary source 2](https://www.cs.princeton.edu/~appel/papers/says.pdf): Author-hosted preprint: title/authors on first page; Section 1 and Section 2 show requester proof construction and server checking.
- [Primary source 3](https://api.crossref.org/works/10.1145%2F319709.319718): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## schneider2000enforceable

**Metadata:** verified. Enforceable security policies. Fred B. Schneider. 2000. Venue: ['ACM Transactions on Information and System Security']; volume 3; issue 1; pages/article 30-50; DOI 10.1145/353323.353382.

**Cited claim:** Security automata characterize policies enforceable by execution monitoring.

**Support:** supported. The abstract describes the class of policies enforceable through execution monitoring and security automata for specifying that class. Do not extend termination-only execution monitoring results to all policies or all rewriters. Hamlen et al. refine the computability characterization.

Sources:
- [Primary source 1](https://www.cs.cornell.edu/fbs/fullist.html): Author publication list identifies TISSEC 3(1), February 2000, pp. 30–50.
- [Primary source 2](https://www.cs.cornell.edu/fbs/publications/EnfSecPols.pdf): Author-hosted published paper; abstract and security-automata treatment.
- [Primary source 3](https://api.crossref.org/works/10.1145%2F353323.353382): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## erlingsson2000irm

**Metadata:** verified. IRM enforcement of Java stack inspection. U. Erlingsson; F.B. Schneider. 2000. Venue: ['Proceeding 2000 IEEE Symposium on Security and Privacy. S&amp;P 2000']; volume n/a; issue n/a; pages/article 246-255; DOI 10.1109/secpri.2000.848461.

**Cited claim:** Inlined reference monitors enforce security policies during execution.

**Support:** supported. The paper implements Java stack inspection using a trusted rewriter that inserts checks and protects them from application circumvention. Current booktitle has the minor stylistic variant “Proceeding of”; normalizing to “Proceedings 2000 IEEE Symposium on Security and Privacy” is optional. Crossref lacks a publication year field; original IEEE copyright and author conference listing independently establish 2000.

Sources:
- [Primary source 1](https://www.cs.cornell.edu/fbs/fullist.html): Author list supplies Proceedings 2000 IEEE Symposium on Security and Privacy, Oakland May 2000, pp. 246–255.
- [Primary source 2](https://www.cs.cornell.edu/fbs/publications/sasiOakland.pdf): Original ten-page IEEE paper: title/authors and 2000 copyright; Sections 1–2 describe inlined checks and their integrity.
- [Primary source 3](https://api.crossref.org/works/10.1109%2FSECPRI.2000.848461): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## ligatti2005edit

**Metadata:** verified. Edit automata: enforcement mechanisms for run-time security policies. Jay Ligatti; Lujo Bauer; David Walker. 2005. Venue: ['International Journal of Information Security']; volume 4; issue 1-2; pages/article 2-16; DOI 10.1007/s10207-004-0046-8.

**Cited claim:** Edit automata characterize policies enforceable by runtime transformation.

**Support:** supported. The abstract distinguishes truncation, suppression, and insertion and gives set-theoretic enforceability characterizations. Use 2005 for the journal article, not the 2003 technical report or the 2004 substring in its DOI.

Sources:
- [Primary source 1](https://link.springer.com/article/10.1007/s10207-004-0046-8): Publisher page identifies all three authors, IJIS volume 4 pp. 2–16, February 2005 and DOI; abstract defines monitor actions.
- [Primary source 2](https://api.crossref.org/works/10.1007%2Fs10207-004-0046-8): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## hamlen2006enforcement

**Metadata:** verified. Computability classes for enforcement mechanisms. Kevin W. Hamlen; Greg Morrisett; Fred B. Schneider. 2006. Venue: ['ACM Transactions on Programming Languages and Systems']; volume 28; issue 1; pages/article 175-205; DOI 10.1145/1111596.1111601.

**Cited claim:** Enforcement mechanisms have formal limits and distinct computability classes.

**Support:** supported. The paper characterizes program rewriting and execution monitoring and corrects earlier overly broad execution-monitor classes. The accessible author PDF contains a 2005 copyright placeholder and unassigned page labels; use the final 2006 publisher metadata, independently confirmed by the author publication list.

Sources:
- [Primary source 1](https://www.cs.cornell.edu/fbs/fullist.html): Author publication list: TOPLAS 28(1), January 2006, pp. 175–205.
- [Primary source 2](https://www.cs.cornell.edu/fbs/publications/EnfClasses.pdf): Author-hosted prepublication manuscript: title/authors, abstract, Section 1 and Section 3 enforcement taxonomy.
- [Primary source 3](https://api.crossref.org/works/10.1145%2F1111596.1111601): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## pnueli1998translation

**Metadata:** verified. Translation validation. A. Pnueli; M. Siegel; E. Singerman. 1998. Venue: ['Lecture Notes in Computer Science', 'Tools and Algorithms for the Construction and Analysis of Systems']; volume 1384; issue n/a; pages/article 151-166; DOI 10.1007/bfb0054170.

**Cited claim:** Translation validation connects each compiler output to the semantics of its source.

**Support:** supported. The abstract defines validation after each individual translation and contrasts it with proving the compiler correct in advance. Springer shows First Online/Published dates in 2006 for the digitized chapter, but its recommended citation, copyright, TACAS edition, and Crossref year are 1998. Keep 1998.

Sources:
- [Primary source 1](https://link.springer.com/chapter/10.1007/BFb0054170): Publisher chapter: authors A. Pnueli, M. Siegel, E. Singerman; TACAS 1998, LNCS 1384, pp. 151–166, DOI. Abstract and recommended citation were inspected.
- [Primary source 2](https://api.crossref.org/works/10.1007%2FBFb0054170): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## sergot1986bna

**Metadata:** verified. The British Nationality Act as a logic program. M. J. Sergot; F. Sadri; R. A. Kowalski; F. Kriwaczek; P. Hammond; H. T. Cory. 1986. Venue: ['Communications of the ACM']; volume 29; issue 5; pages/article 370-386; DOI 10.1145/5689.5920.

**Cited claim:** Formalizing legislation requires interpretation of the source.

**Support:** supported. Printed p. 371 discusses intended interpretations where ambiguity occurs; pp. 370–372 delimit what their logical representation does and does not capture. This historical methodological citation does not supply current legal advice or validate this manuscript’s legal labels.

Sources:
- [Primary source 1](https://www.doc.ic.ac.uk/~rak/papers/rak.html): Author institutional bibliography identifies all six authors, CACM 29(5), 1986, pp. 370–386.
- [Primary source 2](https://www.doc.ic.ac.uk/~rak/papers/British%20Nationality%20Act.pdf): Author-hosted original 17-page article. Printed pp. 370–372 discuss scope, vagueness, interpretation, and the restricted objective.
- [Primary source 3](https://api.crossref.org/works/10.1145%2F5689.5920): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## prakken2015lawlogic

**Metadata:** verified. Law and logic: A review from an argumentation perspective. Henry Prakken; Giovanni Sartor. 2015. Venue: ['Artificial Intelligence']; volume 227; issue n/a; pages/article 214-245; DOI 10.1016/j.artint.2015.06.005.

**Cited claim:** Logical representations of legal sources involve interpretation and argument.

**Support:** supported. The authors distinguish applying represented rules from interpretative reasoning about statutory rules, unforeseen cases, and evidence. Supports the methodological limit; it does not establish an accuracy rate for this paper’s automatic formalization.

Sources:
- [Primary source 1](https://research-portal.uu.nl/en/publications/law-and-logic-a-review-from-an-argumentation-perspective/): Author institution record gives both authors, Artificial Intelligence 227, pp. 214–245, year 2015, DOI and abstract.
- [Primary source 2](https://logic.stanford.edu/complaw/readings/law_and_logic.pdf): Institution-hosted published article, first page with complete metadata and discussion of legal interpretation and argument.
- [Primary source 3](https://api.crossref.org/works/10.1016%2Fj.artint.2015.06.005): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## benzmueller2020logikey

**Metadata:** verified. Designing normative theories for ethical and legal reasoning: LogiKEy framework, methodology, and tool support. Christoph Benzmüller; Xavier Parent; Leendert van der Torre. 2020. Venue: ['Artificial Intelligence']; volume 287; issue n/a; pages/article 103348; DOI 10.1016/j.artint.2020.103348.

**Cited claim:** Formal ethical/legal reasoning depends on explicit normative theories and choices of logic.

**Support:** supported_as_context. The author abstract describes designers experimenting with deontic logics, combinations, domain theories, and concrete examples in higher-order logic. For the precise assertion that translating a statute entails interpretation, Sergot and Prakken–Sartor are more direct citations; LogiKEy supports the broader normative-modeling context. Article number 103348 is not a page range.

Sources:
- [Primary source 1](https://arxiv.org/abs/1903.10187): Author-deposited preprint record and abstract identify all three authors and the same title; first preprint 2019, separate from 2020 journal publication.
- [Primary source 2](https://logikey.org/): Authors’ project describes the framework as design and experimentation with legal/ethical reasoners and combined logics.
- [Primary source 3](https://api.crossref.org/works/10.1016%2Fj.artint.2020.103348): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## merigoux2021tax

**Metadata:** verified. A modern compiler for the French tax code. Denis Merigoux; Raphaël Monat; Jonathan Protzenko. 2021. Venue: ['Proceedings of the 30th ACM SIGPLAN International Conference on Compiler Construction']; volume n/a; issue n/a; pages/article 71-82; DOI 10.1145/3446804.3446850.

**Cited claim:** The current joint sentence cites this paper for Catala being applied to tax law.

**Support:** misattributed_system. The paper concerns Mlang, a replacement toolchain for the French tax authority’s legacy M-language infrastructure. It is not the Catala paper. Bibliographic metadata is correct. Split the prose: Catala provides a language for executable legal specifications; Mlang modernizes the French income-tax compiler.

Suggested wording: `Catala makes legal specifications executable \citep{catala}; Mlang modernizes the compiler used for French income-tax calculations \citep{merigoux2021tax}.`

Sources:
- [Primary source 1](https://www.microsoft.com/en-us/research/publication/a-modern-compiler-for-the-french-tax-code/): Coauthor institution publication page identifies all authors and describes Mlang.
- [Primary source 2](https://rmonat.fr/data/pubs/2021/cc21.pdf): Coauthor-hosted published paper, first page identifies CC 2021 and DOI; abstract describes Mlang.
- [Primary source 3](https://api.crossref.org/works/10.1145%2F3446804.3446850): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## miller2006robust

**Metadata:** verified_indexed_primary_access_limited. Robust Composition: Towards a Unified Approach to Access Control and Concurrency Control. Mark Samuel Miller. 2006. Venue: Johns Hopkins University; volume n/a; issue n/a; pages/article not supplied/not applicable; DOI not listed.

**Cited claim:** Object capabilities provide a way to restrict authority.

**Support:** supported_with_access_limitation. Indexed primary thesis Section 9.1 defines the object-capability model and relates references, objects, and access control. “Mark S. Miller” is compatible with the thesis’s “Mark Samuel Miller”. Thesis entries have no journal venue/page range; no DOI is listed by the author. Direct repository access failed, so this is indexed-primary verification, not a claimed fresh full-PDF download.

Sources:
- [Primary source 1](https://www.erights.org/talks/thesis/): Author thesis page returned by live search with title, full author, Johns Hopkins PhD, May 2006 and author-supplied BibTeX; direct retrieval failed.
- [Primary source 2](https://jscholarship.library.jhu.edu/bitstream/handle/1774.2/873/markm-thesis.pdf): Institutional dissertation indexed first page confirms title, Mark Samuel Miller, university and May 2006; direct PDF request returned HTTP 403.
- [Primary source 3](https://erights.org/talks/thesis/markm-thesis.pdf): Author-hosted dissertation indexed Section 9.1, printed p. 64, explains object-capability access control; direct retrieval timed out.

## birgisson2014macaroons

**Metadata:** verified. Macaroons: Cookies with Contextual Caveats for Decentralized Authorization in the Cloud. Arnar Birgisson; Joe Gibbs Politz; Úlfar Erlingsson; Ankur Taly; Michael Vrable; Mark Lentczner. 2014. Venue: ['Proceedings 2014 Network and Distributed System Security Symposium']; volume n/a; issue n/a; pages/article not supplied/not applicable; DOI 10.14722/ndss.2014.23212.

**Cited claim:** Contextual caveats attenuate decentralized authorization.

**Support:** supported. The paper’s abstract and introduction describe bearer credentials with contextual restrictions and decentralized delegation. Publisher Crossref record supplies no proceedings page range; the current entry correctly omits one. Do not infer a volume-wide range from PDF length.

Sources:
- [Primary source 1](https://www.ndss-symposium.org/ndss2014/accepted-papers/): Official proceedings list confirms the title and six authors.
- [Primary source 2](https://www.ndss-symposium.org/wp-content/uploads/2017/09/04_3_1.pdf): Official original paper: first page confirms six authors, NDSS 2014, Internet Society and DOI; abstract describes attenuating caveats.
- [Primary source 3](https://api.crossref.org/works/10.14722%2Fndss.2014.23212): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

## pang2019zanzibar

**Metadata:** correction_required. Zanzibar: {Google}'s Consistent, Global Authorization System. Ruoming Pang; Ramon Caceres; Mike Burrows; Zhifeng Chen; Pratik Dave; Nathan Germer; Alexander Golynski; Kevin Graney; Nina Kang; Lea Kissner; Jeffrey L. Korn; Abhishek Parmar; Christina D. Richards; Mengzhi Wang. 2019. Venue: 2019 {USENIX} Annual Technical Conference ({USENIX} {ATC} 19); volume n/a; issue n/a; pages/article 33–46; DOI not listed.

**Cited claim:** Relation-based authorization provides a complementary authority-control model.

**Support:** supported. Sections 2.1–2.4 encode ACLs using relation tuples, usersets, and rewrite rules, directly supporting the manuscript’s relationship-based authorization characterization. The current 16-author entry is incorrect after its first four authors. Replace it with the official publisher’s 14-author list. Current publisher metadata uses Christina D. Richards, while the original proceedings body prints Christopher D. Richards; preserve this variant in the audit and use the current publisher BibTeX for the correction.

Sources:
- [Primary source 1](https://www.usenix.org/conference/atc19/presentation/pang): Official current publication page and BibTeX give 14 authors, ATC 2019, pp. 33–46, USENIX Association, title, and abstract.
- [Primary source 2](https://www.usenix.org/system/files/atc19-pang.pdf): Official paper includes a publisher cover followed by printed pp. 33–46; Section 2 describes relation tuples and userset rewrites.

## leroy2009compcert

**Metadata:** verified. Formal verification of a realistic compiler. Xavier Leroy. 2009. Venue: ['Communications of the ACM']; volume 52; issue 7; pages/article 107-115; DOI 10.1145/1538788.1538814.

**Cited claim:** CompCert makes the translation/verification relationship explicit through verified compilation.

**Support:** supported. The author abstract reports a Coq proof of semantic preservation for the compiler, distinct from checking each translation after execution. Keep this distinction from Pnueli et al.’s per-translation validation. The existing author, 2009 year, CACM 52(7), pp. 107–115, and DOI all match.

Sources:
- [Primary source 1](https://xavierleroy.org/publi/compcert-CACM.pdf): Author-hosted paper abstract identifies CompCert, Clight-to-PowerPC compilation, Coq implementation, and semantic-preservation proof.
- [Primary source 2](https://doi.org/10.1145/1538788.1538814): Publisher DOI is matched to a successful Crossref metadata response after an initial HTTP 429; direct CACM page fetch was unavailable.
- [Primary source 3](https://api.crossref.org/works/10.1145%2F1538788.1538814): Matched title, ordered authors, year/edition, venue, pagination, and DOI; DOI resolution alone was not used.

