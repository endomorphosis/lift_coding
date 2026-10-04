---
license: agpl-3.0
tags:
- formal-logic
- experimental-decoder
---

# Additional experimental formula decoders: fixed six-lineage cutoff

This release preserves 24 endpoints from six explicitly selected historical
lineages. It contains six final 4096D source-conditioned formula heads, six 8D
head-rate comparison states, six 8D preconditioning comparison states, and six
selected-parent continuation states at 384D/768D. These are formula decoders;
no learned vector reconstruction autoencoder or embedding backbone is included.

The retained budget is 2,040 historical updates: a 20-update 4096D pilot,
three 200-update conditioning arms, two 200-update balanced-cohort arms, and
six 170-update arms across the other three comparisons. Initial and selected
endpoints do not each inherit the final fit's optimizer age. The two continuation
arms are 384D and 768D. No optimizer moments or exact optimizer resume are supplied.

The 4096D states were extracted from saved report model_state fields, preserving
the exact canonical JSON weight digest. Their compact envelopes retain the
32-token codec, native-input normalization statistics, structural geometry and
producer-declared provenance hashes. Whole training reports, source vectors,
reference banks, generated predictions and update histories are excluded.
The source path is explicitly identity reconstruction; two learned source
paths condition hidden initialization and every token embedding. The declared
native profile is last-pool/L2/single-sequence/512 tokens with layer reclamation.
Serialized hashes do not create a fresh native-owner capability or establish
batch/order/token-policy independence. No Leanstral backbone weights are included.

The remaining 18 checkpoint files are exact saved JSON bytes, including the
architecture, codec and preprocessing metadata. Their source interface requires
the saved transformed vector and explicit clause-context contract; input width
alone does not make checkpoints interchangeable.

## Integrity and restore scope

Download the complete release, select the manifest SHA256 from its publication
receipt, then run:

```sh
python -I -B verify_additional_decoder_release.py --directory . --expected-manifest-sha256 SELECTED_SHA256
```

The checker verifies files, seals, finite JSON weights and canonical weight
digests without an ML import or forward pass. Runtime tensor hashes remain
producer declarations. The capsule retains exact selected producer/dependency
versions, with explicit per-lineage associations in the manifest. It is not an
installable complete native runtime, dependency or private-input closure.
No numerical downloaded-checkpoint restore smoke was executed. Native producer
entry points require live runtime results; archived metadata cannot authorize
those calls. Production-loader compatibility remains unqualified.

These exposed authored diagnostic lineages do not establish fresh-holdout gain,
global logic-family support, authentic semantic-label admission, source fidelity,
proof authority or production qualification. All authority flags remain false.
This cutoff excludes later experiments and makes no claim that it contains all
models that might subsequently become available.
