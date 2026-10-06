# Grouped decoder support training and qualifier occurrence transport

The consolidated grouped-v2 head now has a matched two-arm continuation targeting one-clause modal deletion and misspelling. Both recipes execute 200 AdamW updates with identical parent model/optimizer, positive batches, learning rate 0.0005 and support gate 0.5. The [package contribution](https://github.com/endomorphosis/ipfs_datasets_py/pull/1273) preserves producer/default weights and adds the experimental study plus a source-occurrence proposal interface.

| Fresh authored final panel | Original-negative control | Position-local negatives |
| --- | ---: | ---: |
| Exact positives |56/64|55/64|
| Learned refusals |21/64|54/64|
| Unsupported requests emitted |23/64|7/64|
| Exact positive or learned refusal |77/128 (60.2%)|109/128 (85.2%)|

The targeted model improves refusal with one fewer exact positive; seven unsupported requests remain. Selection picks 100 versus 200 additional updates while both recipes complete 200. New source groups/lexemes and split references were fixed before fitting; both selections were durable before final references were parsed. Each split has 38 correlated parent groups. This is one-seed engineering evidence; the final is now exposed and is not independently reviewed law.

The targeted model retains 128/128 exposed earlier positives and refuses 128/128 earlier negatives. Its fourteen probes of seven previously exposed official paragraphs still all refuse, so real-law formalization coverage is not established. Existing 8D/384D/768D weights remain unchanged; these are raw-source grouped heads.

Both selected checkpoints and 49 release files are on [Hugging Face at an immutable revision](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/27667843f4a6cfda36f4763b27d08a080cad9fd3/experiments/grouped-boundary-20261006/run-01). All 2,409 prior files remain, with only additive LFS attributes. Downloaded models/Adam states restore exactly; the public registry retains raw predictions and correctly appends rendering blockers. Separate-process replay reproduces 256 fresh outputs, actual `lake build legal` accepts an eight-member scope witness and rejects a false narrow claim, and 571 tests pass without skips. These checks do not verify a statute's meaning. Hosted CI could not start under GitHub's account billing lock.

The new untrained occurrence adapter reuses canonical-normative-scope-declaration/v1 for one O/P/F rule with explicit modality/actor/action and nullable object/opaque-condition spans. It binds original source bytes and exact Unicode occurrences, preserves explicit attachment and repeated terms, emits no formula/Lean and keeps all five masks zero, coverage unassessed and context unavailable. Grouped v2 lacks the additional endpoints; this is a future qualifier-decoder representation boundary, not trained qualifier coverage or the eight-family floor.

The live formal_logic_text intake observes 372 source-bridge rows, all unqualified for training and without independent validation. The open-US-law default view is a 51-jurisdiction census. Those views do not establish semantic gold. The next qualifier or latent-conditioning study should reuse existing statement-scope, review-intake and alignment owners with separately qualified source occurrences and authentic encoder lineage.

Curated [results](../../artifacts/legal-decoder-followup-20261006-01/training-results.json), [retention](../../artifacts/legal-decoder-followup-20261006-01/post-selection-retention.json), [checkpoint/native replay](../../artifacts/legal-decoder-followup-20261006-01/checkpoint-replay-native.json) and [Hub readback](../../artifacts/legal-decoder-followup-20261006-01/hub-readback.json) bind these claims. Full targets/predictions and selected weights are in the immutable Hub release.
