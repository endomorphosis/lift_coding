# Selected normative decoders reuse retained native inputs

The additive [datasets API](https://github.com/endomorphosis/ipfs_datasets_py/blob/c4382ae53ab9497245fccdf85855f0e314711fbc/docs/autoencoders/normative_cached_legal_ir_runtime.md)
reuses the original selected zero/auxiliary states at 384D/768D with the retained
exposed-v3 source-only cache. The [improvement plan](../../implementation_plan/docs/63-retained-native-decoder-inputs-2026-10-07.md)
keeps semantic IR, prose, long-span and proof-index work separate.

| Observation | Result | Scope |
| --- | --- | --- |
| Existing runtime/numerical/output controls | 240 pass | Original behavior retained |
| New cache contract controls | 105 pass | Synthetic metadata/inert numerical calls, no quality claim |
| Independent source review | Approved | 27 current owners, actual receipt refusals and file custody |
| Actual cached inference | Four selected states × 48 rows, all EOS | Original native embeddings; CPU1, batch8, output512 |
| Archived same-state comparison | 48/48 exact token/status/EOS per state | Separate process after predictions were durable |
| Independent result review | Approved | All 192 typed outputs and source/hash/span/mask bindings |
| GitHub source byte readback | 28 files agree | 27 reviewed owners plus lazy Hub gateway at pinned datasets commit |

Generation opened no targets or previous predictions, and ran no encoder,
optimizer, fitting, network or database operation. The generator asserted model
tensor, input and ambient RNG invariance. Independent review checked retained
bytes and tensor/report joins; it did not rerun the model or independently
execute RNG checks.

This exposed wording cohort is not a fresh semantic holdout. No new semantic
gold scores, original-text exactness or prose quality were measured. Recorded
producer consistency does not cryptographically attest a historical encoder
execution. Actual source execution budgets stay 512; the 768D historical 8192
profile remains metadata. Native IR selectors stay null and runtime, teacher,
quality and proof qualification stay false. Existing weights remain registered
and publicly uploaded; this runtime extension creates no checkpoint release.

The retention manifest pins 24 evidence/script files, the actual 27 source owners
and exact publication copies. Raw vectors, model weights and databases are not
copied. The retained original locators and witness policy preserve the two
384D archived producer files with 26 links and the first-attempt source artifact
path. Checkpoints, caches and current owners still require single-link files.
Joint closing endpoints do not provide an atomic cross-file snapshot.

Useful records: [preflight](preflight/retained-assets-preflight.json),
[generation](generation/generation-result.json), [archived parity](archived-output-parity.json),
[source review](independent-review.json), [result review](independent-result-check.json),
[test/source controls](test-and-source-review.json),
[GitHub source readback](source-github-byte-readback.json),
[retention manifest](retention-manifest.json).
