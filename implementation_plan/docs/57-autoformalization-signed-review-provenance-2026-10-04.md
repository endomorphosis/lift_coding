# Autoformalization signed review provenance

Date: 2026-10-04. This continues the review-process dependency in the [relation-mask handoff plan](56-autoformalization-relation-mask-handoff-2026-10-04.md) and AFI-04 in the [implementation backlog](50-autoformalization-alignment-implementation-backlog-2026-10-04.md). The [comprehensive improvement plan](49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) still governs the independent 8D, 384D, 768D and optional Leanstral lanes, decoding, logic families and prover evaluation. This slice checks signature provenance. It does not qualify supervision or change historical models.

## Signature and admission boundaries

The new [provenance owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_review_provenance.py) adds a closed dictionary interface:

`verify_train_review_provenance(declaration, handoff_envelope, registry, policy, attestations, *, expected_bindings)`

It replays the preceding TRAIN declaration and mask-handoff receipt before evaluating attestations. Independent pins select those complete values, the registry, the verification policy and the complete attestation bundle. Submitted attestations do not select their key resolver, callback, provider, key bytes or trust policy. Rehashed substitutions for another externally selected generation fail.

Only unavailable and explicitly synthetic engineering registries are supported in this version. There is no authenticated-human mode. The receipt reports selected-key-to-payload integrity separately from declared registry/policy matching; a mathematically valid signature can still be denied for its scope or purpose. It leaves human enrollment, independence, source fidelity, semantic agreement, all supervision masks and actual fitting authorization false. Formal-target or proof authority still requires its separate exact-statement evidence.

The existing [Profile G verifier](../../external/ipfs_datasets/ipfs_datasets_py/logic/profile_g.py) uses a resolver and signatures over its CID recipe. The new owner uses direct construction from registry-selected raw public-key bytes and its own explicit signing profile. It does not reinterpret old Profile G attestations or use the service's trusted-local bypass.

## Selected records and signing recipe

| Input | Bound information |
| --- | --- |
| Declaration and handoff | Exact TRAIN order, source/context/input/formal-view identities, original role selections, scope, review references and the complete saved preflight. |
| Registry | Process, immutable generation and revocation generation; principal/key associations; declared role, action, audience and semantic scope; key validity and selected revocation time. |
| Verification policy | Registry/process/generations, intended action and audience, supported mode and explicitly supplied UTC evaluation time. |
| Detached claim | Attestation ID, kind, principal/key/role, action/audience/process/generations, declaration/handoff/policy/registry hashes, issuance/expiry, exact endpoint subjects, scope and the bound review/adjudication reference. |
| Bundle | Complete selected declaration/handoff/registry/policy generations and the ordered submitted envelopes. |

The signing bytes are the fixed domain prefix `alignment-review-provenance-attestation/v1` followed by NUL and the canonical payload bytes. The payload uses sorted compact UTF-8 JSON with no normalization. Public keys are exactly 32 decoded bytes and signatures exactly 64 decoded bytes, encoded as canonical lowercase hexadecimal. The signature covers the payload rather than its own enclosing envelope, so review references need no self-referential file hash.

The optional provider is imported lazily. The direct Ed25519 interface accepts raw public bytes and raises `InvalidSignature` when verification fails; the selected local provider is cryptography 44.0.0. These key sizes and verification behavior follow its [official documentation](https://cryptography.io/en/44.0.0/hazmat/primitives/asymmetric/ed25519/). Provider absence or lack of algorithm support cannot yield a passing signature result. No package installation runs through this owner.

## Exact associations and denied outcomes

Source/formal reviews bind a singleton endpoint; relation reviews and pair adjudications bind the directed source `i` → formal target `j` association. Source hashes, context hashes and complete input hashes are distinct bindings. The semantic scope and assumptions also remain distinct from the representation-lane profile. A signature for another source, context, formal view, scope, role, action, audience or generation supplies no matching review provenance.

References identify the separately bound source review, formal review, relation review or adjudication in the preceding snapshot. Signing a hash-shaped reference does not verify that referenced file's bytes or its substantive contents. Those checks remain explicit future process requirements. A signature for a useful demonstration likewise cannot supply semantic equivalence supervision.

The evaluation time is supplied and pinned. The adapter checks issuance, expiry, key validity and the selected registry's revocation information against it. It uses no trusted live clock, network revocation lookup or claim of current enrollment. Duplicate local attestation IDs and associations cannot inflate the ledger. Multiple keys for one declared principal do not establish multiple independent people. This version permits one fixture attestation per kind/subject; support for multiple independent human reviews needs a process-owned version. Persistent replay-ID consumption across calls remains a separate process responsibility.

Malformed or substituted structures fail validation. Well-shaped but invalid, expired, revoked, wrong-purpose or otherwise mismatched attestations remain denied evidence. Missing attestations remain explicit in complete endpoint and ordered-pair diagnostics; the verifier does not shrink the cohort or fill gaps with implicit diagonal positives.

## Actual-data and fixture evidence

The [unavailable preflight runner](../../artifacts/autoformalization-alignment-20261003/assay_review_provenance.py) consumes the preceding pinned 16-row TRAIN generation and handoff. Its [saved actual-data assay](../../artifacts/autoformalization-alignment-20261003/review-provenance-01/unavailable/assay.json) retains all 256 ordered pairs and all 544 signature slots: 32 endpoint reviews and 512 pair reviews/adjudications. Every slot remains missing, with no selected genuine process/registry, no attestations and no admitted supervision. This path creates no keys, imports no crypto or model stack, reads no formal-target bodies and runs no numerical objective.

The separate [fixture runner](../../artifacts/autoformalization-alignment-20261003/assay_review_provenance_fixtures.py) and [saved canary](../../artifacts/autoformalization-alignment-20261003/review-provenance-01/synthetic/assay.json) check real signature mathematics using fixed, disposable engineering keys and authored metadata. The two-row fixture initializes two deterministic private-key objects, generates no random keys and creates 12 signatures. All 12 pass signature and declared-scope checks. Flipping one signature bit, while reselecting the complete tampered bundle, yields 11 passing signatures and one denied signature. All four objective/admission matrices and all five supervision masks remain false or zero in both receipts. The keys and principal IDs are test values; these checks establish no human reviews, independent fidelity or training authorization.

The selected root virtual environment uses cryptography 44.0.0. The canary pins three provider files and ten fixture implementation/helper files, checks loaded provider paths, and executes in a fresh child with 10/15-second CPU limits, 768 MiB address-space limit, 8 MiB output-file limit and a 30-second parent wall deadline. This is a trusted local worker with resource limits, not an OS sandbox or a complete binary dependency manifest. The root collector repeats the authored fixture in a separate bounded child without writing another persistent fixture generation and compares the complete results.

The I/O bootstrap and selected provenance owner/test are hash-checked before the same bytes are compiled. Transitive fixture imports are observed before and after execution; this is not a fully preverified dependency closure. Read-only review completed after the successful canary and found a failure-evidence limitation in its standalone launcher: timeout or oversized-output errors can raise before saving parent exit evidence, and worker resource observations are held in memory until publication. Preserve that successful generation and its sources. The final collector saves its own bounded replay exit metadata before accepting or rejecting the child, with a separate five-second cleanup wait after its 30-second child execution deadline; standalone failed-attempt journaling needs a separate corrected launcher version. These failure paths are not qualified by this successful run.

The [overall validation receipt](../../artifacts/autoformalization-alignment-20261003/review-provenance-01/validation.json) records 407 passing targeted tests, including 70 new [provenance cases](../../external/ipfs_datasets/tests/unit/logic/formalization/autoencoder/test_alignment_review_provenance.py) and 337 unchanged handoff/declaration/lane/stage cases, saved evidence replay, lint for the five new Python files, and rechecks of the preceding 245 bound files. The combined test command completed in 4.23 seconds with no errors, failures or skips. Test coverage uses synthetic engineering inputs; its signature operations are separate from the specifically counted canary. Existing legacy and numerical-launcher limitations remain preserved. Dependency selections cover the named files; they are not a complete software or OS confinement attestation.

## Remaining real-process work

A future authenticated version needs an independently selected, process-owned registry and actual review submissions. Verify enrollment and stable person identity, role competence, relationships to authors/model developers, exposed inputs and assessment/adjudication ownership. Preserve unknown or conflicting provenance rather than interpreting a valid signing key as an independent expert.

Then admit exact reviewed derivations and whole-source/formal-view fidelity under the relevant family/profile/assumptions. Unsupported representation, unresolved ambiguity, omissions, scope loss and unreviewed alternatives remain ineligible. Directed relation decisions need their own supported meaning assessment. Only that separate admission version may enable TRAIN relation masks.

This work establishes no retrieval gain, formalization accuracy or proof coverage. The broad 40-family pilot, objective-bound projection checkpoints, private reload and finite-gradient gates, reference confinement, and Leanstral embedding qualification remain distinct work in the comprehensive plan.
