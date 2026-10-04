# Richer material inventory — 2026-10-03

This bounded, read-only inspection identified richer authored regression material,
but **zero independently reviewed natural-source evaluation corpora** within its
stated scope. This is an inspection result, not a claim that no such material
exists elsewhere. No model was loaded, no solver was called, and no test or
canary row factory was invoked. No sealed partition rows or outcomes were opened.

The scopes were the datasets repository's nearby autoencoder configurations,
selected logic-fixture manifests/generators, three Legal IR unit-test sources,
and two already known development artifacts. File reads were bounded to 1 MiB.
Directory searches stayed within those scopes. Counts below distinguish
materialized study inputs from fixture declarations and adapter recipes.

## Existing development admission

The [base study configuration](../../external/ipfs_datasets/configs/autoencoders/alignment_study_development_v1.json)
admits the original Legal panel: 360 training and 120 exposed development rows
with cached native 384D source vectors. It labels targets
`synthetic_authored_unreviewed`, independent source review unavailable, and
cached encoder execution unauthenticated. These records remain eligible for the
existing unqualified diagnostic, not an independent fidelity endpoint.

The [V3 preparation manifest](../source-native-v3-20261001/run-02/preparation.json)
lists train/validation files for Legal, Intent, Security, and UI domains.
Its generator declares 15 training and five validation groups per domain,
six variants per group per style, and four augmented styles: 360 training
and 120 validation rows per domain. The manifest explicitly sets
`real_world_corpus=false`; test/canary split declarations do not authorize
opening those partitions. The Legal target generator assigns empty
conditions, exceptions, and temporal lists, so the currently admitted
480-row Legal panel supplies no nonempty qualifier examples.

The [current review receipt](retrieval-01/review_admission.json) contains
40 pending items, zero completed distinct reviews, and zero preliminary
adjudication candidates. Reviewer attestation and author independence remain
unauthenticated; independent fidelity is unavailable. A runnable admission
process is not completed human review.

## Richer candidates and their authority limits

| Material and exact path | Count observed or declared | Richer content | Permitted interpretation |
| --- | --- | --- | --- |
| [Intent source contracts](../../external/ipfs_datasets/tests/fixtures/logic/intent_source_coverage_v1/cases.py) | 15 declared cases: eight prepared references and seven blocked/mutation cases. | Assumptions, intentions, preconditions, effects/postconditions, and explicit finite Boolean state/effect bindings. | Authored exposed adapter regressions. Targets are built through `source_target` or the existing parser, so they are not independently authored source gold. Mutations must remain negative cases. |
| [UI guard declarations](../../external/ipfs_datasets/tests/fixtures/logic/native_dcec_ui_v1/guard_cases.py) | Five declared cases share one exact source. | Boolean and compound guards, an explicit state interpretation, timeout, and a binding mismatch. | The fixture explicitly disclaims training and independent fidelity. Caller-declared auxiliary interpretations vary under the same source; source-only labels cannot silently absorb those assumptions. |
| [Security styles V4](../../external/ipfs_datasets/tests/fixtures/logic/source_security_styles_v4.py) | Declared 21 train/seven validation groups; 1,344 augmented training and 504 validation rows. | Typed binary program expressions, polarity/operator families, function names and nuisance styles. | Synthetic known-vocabulary recombination, `real_world_corpus=false`. Counts are generator metadata, not a new vector-cache or checkpoint admission. Test/canary descriptors remain excluded. |
| [Authorization manifest](../../external/ipfs_datasets/tests/fixtures/logic/attested_authorization/manifest.json) | 41 indexed cases; all 41 are `public_synthetic`. | Conditional obligations, exception scope, effective-time and authority bindings, and adversarial integrity cases. | The name “attested” does not establish independent NL review. The manifest identifies a synthetic fixture and offline expected outcomes. Useful authority-boundary tests, not natural-source fidelity gold. |
| [Proof-tactician manifest](../../external/ipfs_datasets/tests/fixtures/logic/proof_tactician/manifest.json) | 53 recipes in 12 scenario families. | Loop invariants, contracts/frames, temporal fairness, first-order inconsistencies, protocol attacks and proof-gap scenarios. | Synthetic recipes; `live_verification=false`, network/optional-solver/model requirements false. Expected authority ceilings are not current checker receipts or independently reviewed NL/formal pairs. |
| [Provider conformance manifest](../../external/ipfs_datasets/tests/fixtures/logic/software_verification/conformance/manifest.json) | Ten recipes, 22 adapters and 13 logic families. | First/higher-order, temporal, transition, separation, refinement, program, protocol, authorization and other family contracts. | Offline fake runners are mandatory; real-tool lanes are opt-in. This inventories family regression opportunities, not measured cross-family source fidelity. |

The Legal unit-test sources also provide explicit nonempty qualifiers.
The [compiler test](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_compiler.py)
contains one projected obligation with nonempty condition, exception, and temporal
facets alongside a permission. It tests typed norm projection rather than an
independent original-source annotation. The
[decompiler test](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_decompiler.py)
constructs one rule with two conditions, one exception, and two temporal atoms.
The [reconstruction test](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_decompiler_reconstruction.py)
constructs one rule with all three qualifier lists nonempty and checks
target-to-controlled-text reconstruction. The test receipts themselves distinguish
structural preservation or candidate reconstruction from source fidelity.
These examples are useful regression seeds; generated prose is not independent
natural-source ground truth.

None of these richer candidates is automatically admitted into the hybrid
retrieval corpus. The current runner expects the pinned Legal one-rule schema,
group separation, source/vector bindings, and cached native 384D input.
Adding another family, auxiliary interpretation, or qualifier-bearing panel
requires a new explicit corpus contract and evidence generation. Fixture case
counts cannot be summed into a count of independent original sources.

## Excluded panels and uninspected material

Only split descriptors and generator metadata were used for the two explicitly
sealed composition panels; no row factory was called:

| Panel | Descriptor counts per domain | Disposition |
| --- | --- | --- |
| [source384 fidelity V2](../../external/ipfs_datasets/tests/fixtures/logic/source384_fidelity_v2/panel.py) | 24 train, six tuning, six test groups; two domains. | Explicitly sealed test texts may be constructed only after compared fits are frozen. Excluded from this reuse inventory. |
| [Intent/UI compositions V1](../../external/ipfs_datasets/tests/fixtures/logic/intent_ui_source_compositions_v1/panel.py) | 96 train, 24 tuning, 24 test compositions; two domains. | Test construction is restricted until fits are sealed. Metadata also disclaims unseen lexical generalization and full-document coverage. Excluded from reuse. |

Security V4 and V3 test/canary rows were likewise not generated or opened.
Canonical unit tests reference frozen semantic-roundtrip pilot data; this
inspection did not open those pilot rows or their outcomes. The
[source-decoder evaluation configuration](../../external/ipfs_datasets/configs/autoencoders/gte_decoder_source_evaluation_v1.json)
is only a dependency pointer, not permission to inspect a locked evaluation run.

No workspace-wide natural-document search, external download, new annotation,
or reviewer authentication was performed. Independence is unavailable for this
inventory's candidates until genuine source-only annotations and reviewer/author
independence evidence are supplied. A native proof of an authored formula would
still leave the original-source correspondence as a separate obligation.

## Exact file bindings

The following SHA-256 values bind the observed file bytes, including the generator
source files used for descriptor inspection. They establish integrity within the
listed scope, not provenance authentication or a complete dependency closure.

| Workspace-relative path | Bytes | File SHA-256 |
| --- | ---: | --- |
| [external/ipfs_datasets/configs/autoencoders/alignment_study_development_v1.json](../../external/ipfs_datasets/configs/autoencoders/alignment_study_development_v1.json) | 3177 | `413e7250098d39e3e1ff59405c75c5eca283ec5820828d8be7fb00beb01e2f31` |
| [external/ipfs_datasets/configs/autoencoders/gte_decoder_source_evaluation_v1.json](../../external/ipfs_datasets/configs/autoencoders/gte_decoder_source_evaluation_v1.json) | 842 | `13b65fbf97a02005b9880ab9e0caf2cfb7c0fdd132324f144a5b48a08becc009` |
| [external/ipfs_datasets/tests/fixtures/logic/source_reconstruction_v3.py](../../external/ipfs_datasets/tests/fixtures/logic/source_reconstruction_v3.py) | 7576 | `5498592e48f174e872b059b055da596aff543fbce76709408f835ca92bfd36da` |
| [external/ipfs_datasets/tests/fixtures/logic/intent_source_coverage_v1/cases.py](../../external/ipfs_datasets/tests/fixtures/logic/intent_source_coverage_v1/cases.py) | 6022 | `7f0a9bcec6faf5b01b884244c00cbad1f1010d85373f3e57b0604cf6d01afb7c` |
| [external/ipfs_datasets/tests/fixtures/logic/native_dcec_ui_v1/guard_cases.py](../../external/ipfs_datasets/tests/fixtures/logic/native_dcec_ui_v1/guard_cases.py) | 4085 | `a1680b54df4f346bd262329f984e0f01852199fe497792361a5292823459c0fd` |
| [external/ipfs_datasets/tests/fixtures/logic/source_security_styles_v4.py](../../external/ipfs_datasets/tests/fixtures/logic/source_security_styles_v4.py) | 3935 | `e8384bb692d486f851f45e0f11438292220deab81acbfdcf4fa0778d59bc74fe` |
| [external/ipfs_datasets/tests/fixtures/logic/source384_fidelity_v2/panel.py](../../external/ipfs_datasets/tests/fixtures/logic/source384_fidelity_v2/panel.py) | 3627 | `2ecb6dbc51ed20ddc0e5da52304b1d07b4c709f1cf39ebbd51ca82e47d4a0a6b` |
| [external/ipfs_datasets/tests/fixtures/logic/intent_ui_source_compositions_v1/panel.py](../../external/ipfs_datasets/tests/fixtures/logic/intent_ui_source_compositions_v1/panel.py) | 3322 | `99a1ee0330e2a73e0f78051e8a6623605746b1c74b56f83fdbe6f484965bfc33` |
| [external/ipfs_datasets/tests/fixtures/logic/attested_authorization/manifest.json](../../external/ipfs_datasets/tests/fixtures/logic/attested_authorization/manifest.json) | 28187 | `202a7f7536817cce5b47075b893c1ea8ca2a564b9a488d6950f8dbbbc4c44e1e` |
| [external/ipfs_datasets/tests/fixtures/logic/proof_tactician/manifest.json](../../external/ipfs_datasets/tests/fixtures/logic/proof_tactician/manifest.json) | 166789 | `168c7902c975dc93a803558d4974e9a2c73f6fb07eabb9d93564935b1f61b02d` |
| [external/ipfs_datasets/tests/fixtures/logic/software_verification/conformance/manifest.json](../../external/ipfs_datasets/tests/fixtures/logic/software_verification/conformance/manifest.json) | 13164 | `9a6f1a0d02fa151116ebf2febfe3a50fce06c1e677b0b88b620a3fde9a919ce1` |
| [external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_compiler.py](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_compiler.py) | 17327 | `7c4934b32f44755646e137704a0d6eeb4310127d99d1f584e3e2f1e1c23625d5` |
| [external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_decompiler.py](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_decompiler.py) | 11500 | `e90ca3ac4359057220f60bb398235b27feec7a3cdce03a2ad9dda76515031684` |
| [external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_decompiler_reconstruction.py](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_decompiler_reconstruction.py) | 7496 | `afe11b1fcfc5003df40e136cc2de095f7d6ba708c6ee3f06a09cd6f7f4c8c0b0` |
| [artifacts/source-native-v3-20261001/run-02/preparation.json](../../artifacts/source-native-v3-20261001/run-02/preparation.json) | 3008 | `688d06be83671d0274801958fcc47c725c5023f0ca9e41a8330cff657eafb914` |
| [artifacts/autoformalization-alignment-20261003/retrieval-01/review_admission.json](../../artifacts/autoformalization-alignment-20261003/retrieval-01/review_admission.json) | 82817 | `37ff0abb003f5f525784733ae97cef80fcb81f2e6aa4e2a3e26f7ffdd7e73c0c` |

This inventory performs no training or evaluation and grants no qualification,
production admission, source-fidelity authority, or proof authority.

