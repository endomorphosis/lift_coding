# Prospective authored development wording, generation 1

This recipe is fixed before any new encoder forward, source-head query or fit.
It supplies wording development, with previously exposed authored meanings;
it supplies no independently reviewed semantics or fresh semantic holdout.
References may be loaded only after all compared endpoints have saved their
free-running source-only predictions. Neither these sources nor their label
bodies are TRAIN inputs or endpoint-selection inputs.

The pure owner is
`external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/prospective_normative_development.py`.
Its API is
`build(validation_bank, training_bank, prior_sources_by_dataset, codec, sealed_recipe_sha256, validate_rule)`
using keyword arguments. Both original banks are closed
`{id, source_text, target_ids}` rows. The builder requires all declared prior
inventories, and returns separate `source_rows`, `references`, and `receipt`.
Source rows contain exactly `{id, source_text}`. References have split
`prospective_authored_development` and label provenance `authored_development`.

The original raw validation inventory is
`external/ipfs_datasets/workspace/test-logs/decoder-distillation-limits-20261002/prepared-r1/prepared384-validation.json`.
Read-only inventory inspection on 2026-10-06 found 60 source rows, 30 unique
complete seven-field rules, two original renderings per rule, ten rules per
modality, and five actor/action groups:

- registrar / preserve
- trustee / publish
- secretary / examine
- treasurer / deliver
- notary / approve

Those five groups are wholly disjoint from the 15 original TRAIN groups in the
180-row `original-training-bank-used.json` under R4 preparation. Each validation
group has both objects and all three modalities. No incompatible or colliding
rule will be removed to make the counts pass. A complete incompatible bank
refuses the whole generation.

Each unique validation rule receives exactly these two authored renderings:

| Template | Obligation | Permission | Prohibition |
| --- | --- | --- | --- |
| `normative_that_clause_v1` | `It is mandatory that the {actor} {action} the {object}.` | `It is permissible that the {actor} {action} the {object}.` | `It is prohibited that the {actor} {action} the {object}.` |
| `actor_norm_possession_v1` | `The {actor} bears a duty to {action} the {object}.` | `The {actor} holds permission to {action} the {object}.` | `The {actor} faces a ban on {gerund} the {object}.` |

The complete gerund table is `approve → approving`, `preserve → preserving`,
`publish → publishing`, `examine → examining`, and `deliver → delivering`.
The target preserves `modality`, `actor`, `action`, `object`, `conditions`,
`exceptions` and `temporal`. This bank has empty qualifiers; the renderer refuses
nonempty qualifiers. Source IDs bind exact source SHA-256; ordering is template
ordinal then canonical original-rule SHA-256. The result has 60 single clauses,
20 of each modality, 30 of each template. No paragraph recombination is implied.

The templates were specified by a separate preparation owner from the upcoming
TRAIN wording owner, using the unchanged lexical inventory. No model queries
were used to select them. This is engineering separation, not authenticated
independent human linguistic review. Their new strings do not make their old
validation meanings previously unseen.

Every generated literal and its case-folded whitespace-normalized form must
avoid complete prior paragraphs and their component clauses. Required source
inventories are the ten R4 named sets (`exposed_r6`, `exposed_r8`, `exposed_v3`,
`original_train_bank`, `paragraph_train`, `paragraph_validation`, `raw_canary`,
`raw_test`, `raw_train`, `raw_validation`) plus `r4_training_paraphrases`,
`composition64`, and `new_training_wordings`. Names alone do not authenticate
those files; the handoff manifest binds their exact bytes separately.

The exact sealed source rows, separate reference file, complete generated
receipt, recipe JSON, and actual input file bindings will be stored under
`artifacts/autoencoder-wording-fit-20261006/development/` before native
preparation or fitting. No native or numerical execution has occurred in this
preparation task. Model source-head and generated-formula scores cannot be used
to redesign this generation after its seal.

The context remains 512, output limit 512, temperature zero; no weights are
downloaded. Targets use the unchanged 32-token codec. Formal syntax checks and
authored alignment grant no Lake admission, semantic qualification, promotion,
or Constitution formalization. Every related flag remains false.
