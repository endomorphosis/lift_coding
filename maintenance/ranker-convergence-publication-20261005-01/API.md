# Convergence publication interface

This directory contains publication source only. No helper, codec, classifier,
Git or remote operation may run while Q3 or the source plan is active. The final
root seal, passed qualification review, exact fact policy, and a quiet final
publication plan are required before input freezing or packaging.

The final plan is `plan.json` with schema
`ranker-convergence-publication-plan@1`, status `frozen_final_plan`, both
`source_and_artifacts_quiet` and `source_plan_quiet` true, and the exact fixed
`publication_profile` from the source. `plan-template.json` is an unready example
and cannot execute. Supply independent final plan and builder SHA256 arguments.

`documents` contains exact `{path, bytes, sha256}` descriptors named `file_seal`,
`qualified_review`, and all actual native `check-result.json` receipts, plus any
metadata, model binding or boundary documents used by the observed fact policy.
`seal_schema` and `review_schema` name their exact final schemas. The seal must
bind the review, list every Q3 regular file once, provide regular-file count and
bytes and the SHA256 of sorted-key compact ASCII JSON for `files` with no newline.
Only dependency subtree exclusions copied exactly from the seal are allowed.
This interface accepts no fixture symlinks; no alias traversal or body omission
is performed. Every zero-byte lock remains selected.

`semantic_policy` pins `required-facts.json`, a nonempty list of exact
`{document, pointer, equals}` observations with unique document/pointer pairs.
All actual native attempt roles appear in `native_checks`, and every status must
be explicitly fact-gated. This includes inconclusive attempts. Every passed
native role must retain exact frozen source/profile bindings, its complete
theorem-axiom queries, complete chunks and full objects, and unchanged native
limits. Statements about the actual original real-model convergence must be
observed facts from final passed kernel receipts and the qualified review.
There is no automatic promotion of source drafts to qualified results.

`explicit_additions` pins at least the builder, reviewer, freezer, fact policy and
seal self-file, and can include this API or source review receipt. The complete
quiet P4 source-plan regular population is captured separately as source-only
history. All Q3 sealed regular bodies, failed profiles, dependency manifests,
empty exports, proof chunks and full objects are retained. The plan and generated
closed inputs/selection are excluded from the package to avoid self-reference;
retain them separately in the HF upload plan. Nothing from the earlier large
curvature package is reuploaded. `prior_HF_commit` is
`8b7b8c896749e0ca3884114cedbed782a88f4702` and `old_HF_bundle_reuploaded` is false.

Fixed limits: total raw population 256 MiB; raw member sum per shard and per file
14 MiB; complete decoded GNU tar 16 MiB; compressed shard 16 MiB; total charged
decoded work 1 GiB; 10,000 recursive members; depth six; 64 shards; 180 seconds
for each packaging/review phase. Compression uses `/usr/bin/zstd -T1 -3`.
The first decoded traversal verifies complete tar bytes and every member's
identity and SHA256 while the pinned classifier checks complete PEM blocks,
cached credential values and nested containers. Every decode and member stream
is charged; no second uncharged verification decode is used. Native limits stay
at 20-second wall/CPU, 256 KiB source, 64 KiB output, 16 MiB workspace.

After the final root seal and source review, freeze inputs:

```text
python freeze_inputs.py --plan /absolute/path/to/plan.json \
  --expected-plan-sha256 FINAL_PLAN_SHA \
  --expected-builder-sha256 FINAL_BUILDER_SHA
```

The freezer creates only new `final-selection.json` and `closed-inputs.json`
in this directory. It executes no codec or classifier. Build into a fresh sibling
`maintenance/ranker-convergence-publication-package-...`:

```text
python build_package.py --closed-inputs /absolute/path/to/closed-inputs.json \
  --expected-closed-inputs-sha256 CLOSED_SHA --output /absolute/new/package/root
```

Review the complete decoded package:

```text
python review_package.py --closed-inputs /absolute/path/to/closed-inputs.json \
  --expected-closed-inputs-sha256 CLOSED_SHA \
  --manifest /absolute/new/package/root/package/manifest.json \
  --expected-manifest-sha256 MANIFEST_SHA \
  --expected-builder-sha256 FINAL_BUILDER_SHA \
  --output /absolute/path/to/package-review-01.json
```

The HF upload plan must select fewer than or equal to 100 new files, use a fresh
parent check, preserve all earlier immutable files, retain the old package by
reference, and exclude every raw SDK stdout/stderr log. Git publication uses an
isolated private checkout, a normal push, current parent Git links and unchanged
original root/child HEAD/index guards. Publication code itself grants no proof,
execution, completion, planner or full-task authority. Source/Float equivalence,
binary64 error bounds, autoencoder/global task claims remain separately gated.
