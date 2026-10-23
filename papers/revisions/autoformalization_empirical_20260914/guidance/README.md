# Learned guidance recovered as obligation scheduling

The retained T3 model contains a real learned `obligation_family` head. Its
nontrivial probabilities rank provenance preservation before modal well-formedness
(approximately 0.5934 versus 0.4066). The retained global and frame-logic context
rows are identical, so this is a constant learned obligation prior. It is neither
an example-dependent correctness estimate nor a probability that a theorem holds.
The view-classification heads of the inspected T2 models are empty, and singleton
T3 outcome heads cannot establish successful proof prediction.

`learned_route.py` consumes the actual native T3 output and executes both required
checks in the learned order. The baseline runs modal well-formedness first. Every
check executes even after a failure, preserving the candidate, checker, and final
conjunctive result. Disabling guidance restores the exact baseline order. This is
a deliberately limited, versioned implementation of consumed learned advice;
the earlier proposed canonical-field mutation adapter remains unimplemented.

`structural_checks.py` uses the native modal types, operator registry, and source
normalizer. It checks formula structure, registered operators, source-content
hashes, normalized text, source identifiers, and span bounds. A correctly shaped
empty document can pass structure but has zero eligible formula coverage. These
checks do not establish independent legal-semantic fidelity, the truth of a
predicate, or a kernel proof.

The qualification runs five fixed constructed sources per seed through the actual native
spaCy encoder/modal compiler and native autoencoder prediction API. Ten variants per seed include
invalid operators, out-of-range spans, substituted source identifiers, changed
normalized source text, and combined failures. Each variant executes guidance
off, on, and off again. All three seeds changed check order while retaining every
check outcome, and rollback restored baseline order. Malformed predictions,
source binding changes, and unqualified final execution were rejected. Earlier
qualification attempts are retained; `qualification_v5_seed*/` binds the final
scheduler implementation. `qualification.json` binds the independent engineering
review, actual checkpoint exports, callbacks, and executed evidence by content
address. The engineering review is separate from manuscript review or human
semantic annotation.

For the final comparison, import `execute_checks`, `CHECKS`, and
`checker_contract`, and provide `qualification_required=True`, the qualification
manifest, and the frozen emitted prediction row digest. Record both check order
and actual results. An order change alone is not an increase in proof coverage or
semantic accuracy. There is no early stopping, so timing differences are noisy
scheduler measurements rather than evidence of saved verification work.

The v4 attempt failed under a four-GiB address-space ceiling while exercising
unneeded full-codec decorations. The successful v5 qualification uses the exact
native C compiler components and remains within four GiB of address space
(about one GiB peak RSS). This infrastructure correction does not change the
learned scheduler, structural checks, source set, or expected outcomes.
