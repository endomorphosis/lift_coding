# Primary-source notes for the narrative fragments

Checked on 13 September 2026. These are brief paraphrases, not quotations.
Repository-specific design and limitations come from the frozen study scope
and the already reviewed methods input, rather than from these references.

- `baseline01`, Necula, Proof-carrying code, POPL 1997, DOI
  `10.1145/263699.263712`. The [original project bibliography](https://www.cs.cmu.edu/~fox/pcc-bib.html)
  confirms the paper and publication metadata. The [primary project description](https://www.cs.cmu.edu/~fox/pcc.html)
  describes a consumer's policy, producer-supplied evidence, and consumer
  validation. The bibliography's legacy POPL abstract endpoint returned 502;
  it is not asserted to have been read. The author's [paper archive](https://people.eecs.berkeley.edu/~necula/Papers/)
  also lists the original POPL PostScript. The fragment uses only the general
  producer/evidence/consumer-policy relationship; it asserts no theorem or
  performance figure from the inaccessible abstract.
- `baseline07`, Mokhov, Mitchell and Peyton Jones, Build systems a la carte,
  ICFP 2018, DOI `10.1145/3236774`. The [official publication page](https://www.microsoft.com/en-us/research/publication/build-systems-la-carte/)
  links the [final paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2018/03/build-systems-final.pdf).
  Page 1 identifies the order of building tasks and the decision whether to
  rebuild as separate design choices. The narrative's evidence-applicability
  conditions are our design, not an additional result attributed to this paper.
- `baseline08`, Yang et al., SWE-agent, NeurIPS 2024, DOI
  `10.52202/079017-1601`. The [official abstract](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html)
  describes interface design for navigation, code editing, and program
  execution. The fragment claims no matched evaluation or comparative
  performance result between SWE-agent and the present study.
