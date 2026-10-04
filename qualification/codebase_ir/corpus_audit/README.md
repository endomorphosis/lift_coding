# CodebaseIR corpus split auditor

This offline standard library tool groups source files before evaluating declared train, tune, canary, and untouched final splits. It addresses the roadmap's normalized AST clone, related revision, dependency group, and training ancestry gap. It never imports the production trainer, opens a database, executes source, fits a model, or selects a checkpoint.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_corpus_audit.py \
  qualification/codebase_ir/corpus_audit/examples/clean_input.json \
  --output /tmp/codebase-ir-clean-report.json

python3 -m unittest discover \
  -s qualification/codebase_ir/corpus_audit -p 'test_*.py'

ruff check qualification/codebase_ir/corpus_audit
```

The report path must be new and its parent directory must exist. Reports use mode `0600`, cannot overwrite inputs or earlier results, and contain no timestamps. The same bytes and Python AST version produce the same report. Exit codes are `0` for complete declared scope without detected leakage, `1` for detected leakage, `2` for incomplete evidence without detected leakage, and `3` for invalid input or output failure. Status `leaks_found` can coexist with incomplete evidence; check `complete_for_declared_scope` as well as `status`.

## Integration contract

The manifest is a closed JSON object. Every listed field is required; unknown fields, duplicate JSON keys, nonfinite numbers, duplicate source IDs, ambiguous source representations, role aliases, unbound sources, and budget violations are rejected.

```json
{
  "schema": "codebase-ir-corpus-audit-input@1",
  "units": [
    {
      "id": "selected-source",
      "role": "train",
      "repository_id": "repository:example",
      "path": "calc.py",
      "revision": "snapshot:example",
      "content_sha256": "<64 lowercase hexadecimal SHA-256 characters>",
      "source": {"file": "captured/calc.py"},
      "dependencies": [],
      "dependencies_complete": true,
      "related_revisions": [],
      "revision_relations_complete": true
    }
  ],
  "native_records": [],
  "ancestral_training": [],
  "ancestry_complete": true
}
```

`role` is exactly `train`, `tune`, `canary`, or `final`. `source` is exactly `{"file": "relative/file.py"}` or `{"bytes_hex": "<canonical lowercase exact hexadecimal bytes>"}`. Input files must remain within the manifest directory, must be regular files, and cannot be final-component symlinks. Repository source paths are canonical relative `.py` paths. The auditor checks the content SHA-256 before parsing UTF-8 Python source. IDs beginning with `native/` or `ancestral/` are reserved.

Dependencies and related revisions refer to other unit IDs. Dependency grouping is undirected and transitive: a train source and an evaluation source sharing a helper belong to the same group. Explicit related revisions connect renames or other known lineage. The same repository/path is also grouped across all supplied revisions, even when the byte digest changes. All relation types participate in a combined transitive grouping, with retained edges explaining the connection.

Missing references produce completeness issues. Two sources referencing the same missing dependency still share the declared dependency group, and the report retains the unresolved reference. False completeness flags, missing split roles, and undeclared ancestry prevent a clean result. These flags express the caller's recorded inventory scope; the auditor cannot establish that omitted repository files, imports, dynamic calls, ancestry, or revision relationships were actually enumerated.

Ancestral training identities use the closed shape `{"repository_id": "...", "path": "...", "content_sha256": "..."}`. Each is counted as train exposure. If a matching verified source identity appears in the manifest or a native export, its exact bytes and declared relation metadata are reused. Otherwise the identity remains an explicit unresolved train exposure: path/digest collisions can still be reported, while AST and relation completeness remain unknown. A changed evaluation revision at an ancestral training path therefore never looks independent.

## Native export adapter

`native_records` accepts exact exported checkpoints containing `report.codebase_provenance`, or the standalone `codebase-source-feature-lineage@1` provenance object. A source training record containing only version/digest references is insufficient because it does not retain target bodies. Each export must be copied under the manifest directory and listed with its exact file SHA-256:

```json
{
  "version_id": "sha256:<native-version-identity>",
  "file": "captured-checkpoint.json",
  "sha256": "<exact checkpoint file SHA-256>",
  "unit_metadata": {}
}
```

The adapter reads `training_targets`, `tuning_targets`, `canary_targets`, and `replay_targets` from the current native provenance profile. Replay is conservatively treated as training exposure. It binds embedded `source_bytes_hex` to `source_binding.content_sha256`, the CIDv1/raw/sha2-256 source CID, entry path/raw-path/size, structural unit references, source head/revision, and the native source-target digest. It requires nonauthoritative envelope/provenance flags. Supplied parent exports must form an acyclic lineage with matching ancestral training identity inventories. Unavailable parents are completeness issues.

Native unit IDs are `native/<version_id>/<batch_field>/<zero_based_index>`, for example `native/sha256:abc/training_targets/0`. `unit_metadata` may supply a closed object for any generated unit ID containing `dependencies`, `dependencies_complete`, `related_revisions`, and `revision_relations_complete`. Metadata for unknown IDs is rejected. Native targets currently lack dependency and revision closure inventories; absence of supplemental metadata sets both flags false. A manifest can add explicitly held-out `final` units alongside native exports.

This adapter extracts and checks source identities for split auditing. It performs no production target replay, registry receipt validation, numerical state validation, producer authentication, live-source fencing, or semantic qualification. Caller-provided version IDs and relation declarations remain manifest claims. Reports explicitly retain `native_replay_performed: false`, `training_executed: false`, `proof_authority: false`, and `promotion_authority: false`.

## Retained evidence and limits

[`artifacts/codebase_ir_parallel_qualification/corpus_audit/native-provenance-20261002-01/`](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-provenance-20261002-01/report.json) contains exact snapshots of the 2026-10-02 source-training qualification parent and child checkpoint exports, their source locations/hashes/version IDs, the audit manifest, and the result. Reproduce into a new report path:

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_corpus_audit.py \
  artifacts/codebase_ir_parallel_qualification/corpus_audit/native-provenance-20261002-01/input.json \
  --output /tmp/codebase-ir-retained-native-report.json
```

That run returns `2`: zero detected cross-role groups and 21 completeness issues. The exports omit dependency and revision closure metadata and contain no untouched final cohort. This is useful evidence about the current export format; it cannot establish independent evaluation splits.

Clone normalization uses whole-module `ast.dump(..., include_attributes=False)` with `type_comments=True`. It removes ordinary comments, parentheses, and formatting while retaining names, operators, constants (including changed literals/guards), statement order, docstrings, annotations, and type metadata. Type-ignore line fields are preserved. Names are not alpha-renamed. Renamed cross-path/cross-repository clones, extracted fragments, and runtime equivalence therefore require additional evidence; normalized AST equality is a conservative grouping signal, not a semantic equivalence proof. Python parsing applies Python's identifier normalization, and the report records the interpreter's major/minor AST version.

Default ceilings are 512 units including ancestry, 16 native exports, 16 MiB per JSON file/32 MiB total, 200,000 JSON nodes/depth 64, 64 KiB per source/4 MiB total, 4,096 AST nodes/depth 64 per source, 8,192 declared links, and 512 ancestral identities. CLI callers cannot increase these limits. The API accepts explicit positive limits for controlled qualification. Inputs are bounded before reads, source parsing, or graph expansion; sources are never executed. A clean result applies only to the pinned, explicitly declared scope and implemented grouping signals.

## Source metadata reconstruction

`codebase_ir_source_metadata.py` reconstructs a candidate manifest from captured source bytes. It resolves static Python imports across the supplied repository paths and revisions, including package initializers, relative imports, parent package imports, imported submodules, and simple exported bindings. It retains original target IDs, batch positions, source digests, head digests, model parent links, exact export file bytes, and all caller-declared dependencies/revision references. Repeated targets are retained separately; their equivalent AST groups are recorded.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_source_metadata.py \
  --manifest artifacts/codebase_ir_parallel_qualification/corpus_audit/native-provenance-20261002-01/input.json \
  --supplement qualification/codebase_ir/corpus_audit/examples/untouched_final_input.json \
  --output /tmp/codebase-ir-reconstructed-source-scope
```

The output directory must be fresh and its parent must exist. It contains `candidate_manifest.json`, `candidate_audit_report.json`, `reconstruction_report.json`, and hash-bound `native_exports/` snapshots. The exporter returns `0` whenever these valid artifacts are produced, including an incomplete or leaky candidate; audit findings appear in the reports. Invalid inputs/output fail with `3`. This keeps artifact generation distinct from the candidate's audit disposition.

Default reconstruction preserves the caller's completeness claims and checks them against discovered frontiers. Native targets lacking relation closure metadata remain unreviewed even when static source imports are fully resolved. To record a deliberate caller closure claim for the supplied source/snapshot scope, add `--accept-supplied-scope`. The claim is recorded explicitly; unresolved imports, symbols, revision ambiguity, missing parents/ancestor sources, or unsupported dynamic lookup still block completeness. The report always sets `whole_repository_coverage: false` and `unseen_rename_ancestry_verified: false`. A scoped clean result does not establish whole-repository independence.

Dependency resolution first uses source entries from the importing unit's repository and exact captured revision. When that revision is unavailable, it retains all observed alternatives and flags different source paths/digests as ambiguous. Package initializers are required; implicit namespace packages and custom import search paths are outside this profile. Unknown external/standard-library imports remain explicit frontiers. It refuses to infer closure through dynamic import APIs or aliases, `eval`/`exec`, globals/nonlocal rebinding, wildcards, unbound global names, unknown receiver calls, attribute/module namespace mutations, or unsupported comprehension/exception/pattern/lambda/assignment-expression scopes. Sources are parsed and inspected; imports are never executed. Observed same-path revision links indicate grouping, and do not assert chronological source ancestry. Native model ancestry is separately checked by the existing auditor.

The two files in `fixtures/untouched_final/` were independently authored for this qualification increment. Their pinned manifest, `examples/untouched_final_input.json`, assigns only `final` roles. They are supplied only to this offline split audit; no training or promotion operation consumes them. `examples/final_helper_leak_input.json` is a negative control importing the native train helper. `examples/final_ancestor_leak_input.json` is a renamed ancestral source with preserved names/operators/literal and an explicit relation to the parent training target.

The retained source reconstruction run is under [`artifacts/codebase_ir_parallel_qualification/corpus_audit/native-source-metadata-20261002-01/`](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-source-metadata-20261002-01/conservative-final/reconstruction_report.json):

| Case | Audit result | What the evidence supports |
| --- | --- | --- |
| `conservative-final` | Incomplete; 20 closure issues, zero detected leaks | Static source imports were reconstructed, while native closure claims remain unreviewed. |
| `scoped-final` | Clean within explicitly supplied scope | An opt-in caller claim covers the three exported native paths and two new final fixtures; whole repository coverage remains false. |
| `final-helper-leak` | Dependency leakage; one unresolved revision issue | The final consumer connects to train helpers across the available revisions. |
| `final-ancestor-leak` | Normalized AST and explicit revision leakage | A new final path retains ancestral training exposure. |

Tests include package/relative/unknown import controls, dynamic import refusal, ambiguous revisions, repeated target IDs, missing ancestry, changed guards/literals, deterministic private reports, strict budgets, source tampering, manifest read races, and unsupported Python scope/mutation forms.

## Native closure evidence handoff

`codebase_ir_closure_requests.py` binds unresolved closure claims to the exact native version, target batch/index, target/source digest, source head, snapshot, manifest, source CID, AST CID, entry CID, and publication receipt. It can corroborate retained source-owner CAS bytes, Git commit/tree/blob objects, and qualification source-head records without opening source/model databases or executing the authored source. It emits an owner handoff inventory; recovered structural facts do not authorize closure flags.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_closure_requests.py \
  --manifest artifacts/codebase_ir_parallel_qualification/corpus_audit/native-source-metadata-20261002-01/conservative-final/candidate_manifest.json \
  --source-cas external/ipfs_datasets/workspace/codebase-source-training-qualification-20261002/source-artifacts \
  --git-repository external/ipfs_datasets/workspace/codebase-source-training-qualification-20261002/authored_repository \
  --qualification-report external/ipfs_datasets/workspace/codebase-source-training-qualification-20261002/fixture-report.json \
  --output /tmp/codebase-ir-native-closure-handoff
```

The fresh private output directory contains `closure_requests.json` (`codebase-ir-native-closure-requests@1`), `owner_facts.json`, the baseline audit, pinned input/native exports, retained verified CAS/Git bytes, and a conservative metadata re-audit under `comparison/`. The exporter returns `0` for a valid incomplete handoff, and `3` for invalid inputs, binding failures, or budgets. Summary fields separate the unresolved audit disposition from report-generation success; `native_closure_certification_verified` remains false and `closure_claims_applied` stays zero.

Owner manifest/snapshot/source-entry/AST/publication-receipt CIDs are recomputed using the declared native strict DAG-JSON profile. The same target/source bindings must agree with the owner records. Git objects are read by exact OID, their object hashes are recomputed, and source bytes are compared to the committed blobs. A working source overlay remains distinct from the shared Git commit. A source marked `git-clean` that differs from its committed blob is refused. Missing owner files and content drift remain explicit frontiers. Retained qualification records are copied and their source-head claims compared; no independent execution or registry attestation is inferred from them.

Recovery and comparison remain tied to the first captured input and export bytes. Later changes to original manifests, file sources, or export paths cannot change the comparison cohort. CAS reads use the remaining byte budget before allocation. Recovery defaults permit 128 CAS files/16 MiB total, 256 manifest/tree entries, 128 Git objects/1 MiB each, and a 30-second Git recovery deadline with five-second child limits. Git uses no replacement objects or optional locks, clears injected repository/object/config environment variables, disables lazy fetching where supported, and forbids every transport protocol. No network or remote helper is required. Qualification JSON is separately bounded by the auditor's 16 MiB file ceiling.

The retained actual handoff run is [native-closure-handoff-20261002-02](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-closure-handoff-20261002-02/closure_requests.json). It recovers two owner manifests, six source/AST facts, nine exact target bindings, and one source-head predecessor link. The two heads share one retained Git root commit/tree; generation 2 contains the `n + 2` working overlay, while the committed train blob remains `n + 1`. All captured AST import/call/effect/unsupported/diagnostic inventories and semantic edge inventories are empty within this authored fixture.

These facts leave **all 20 native dependency/revision closure claims open**. The handoff groups them into four source-identity requests, each naming affected training/evaluation/ancestral exposures and proposed owner inputs: a dependency-group certificate with source membership, extraction/assumption policy and frontiers, and a revision-family certificate with rename/clone search scope, working overlays and missing ancestry. Captured structural inventories and one Git root commit do not supply those certificates or establish whole-repository independence.

Controls cover embedded and retained manifest drift, missing model ancestors, CAS preallocation/file budgets, manifest entry budgets, immutable comparison under late input changes, missing owner artifacts, deterministic private inventories, dirty-overlay/false-clean relationships, and blocked promisor transport/helper execution. The qualification fixtures and handoff tool retain all original role assignments; no final source enters fitting or promotion.

## Proposed owner response review

`codebase_ir_closure_response.py` reviews a supplemental response to the exact retained request inventory. Generate a response template first, then review an edited copy against the original request bundle:

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_closure_response.py \
  --requests artifacts/codebase_ir_parallel_qualification/corpus_audit/native-closure-handoff-20261002-02/closure_requests.json \
  --output /tmp/codebase-ir-owner-response-template

python3 qualification/codebase_ir/corpus_audit/codebase_ir_closure_response.py \
  --requests artifacts/codebase_ir_parallel_qualification/corpus_audit/native-closure-handoff-20261002-02/closure_requests.json \
  --response /tmp/codebase-ir-owner-response-template/response_template.json \
  --output /tmp/codebase-ir-owner-response-review
```

The requests file must stay beside its original `pinned_input.json`, `owner_facts.json`, and native exports. The reviewer rechecks captured source bytes and native target bindings before considering a response. Response inputs are strict closed JSON with schema `codebase-ir-proposed-owner-response@1`. The generated template binds exact request-file bytes, owner-facts bytes, pinned manifest bytes, and a canonical captured-scope digest containing every source identity, role, revision, source hash, existing relation/completeness flag, and native head/target binding. Each response repeats the exact request ID, request digest, source identity, affected IDs, and native-target inventory digest. Stale scopes, changed heads or target positions, duplicate IDs/JSON keys, malformed enums, out-of-scope references, and tampered evidence files are refused.

Template `observations` belong to an affected unit ID. An observation retains `dependency_inventory_claim` and `revision_inventory_claim` as `partial` or records a proposed `captured_scope` inventory claim; it names evidence IDs, explicit `{code, detail}` frontiers, and relationships. Each relationship has exactly `kind`, `target_unit_id`, and `evidence_ids`. Supported kinds are `dependency`, `related_revision`, `dependency_group_disjoint`, and `revision_family_disjoint`. Targets must be exact unit IDs in the captured scope, including ancestral training or untouched final units. A related revision groups sources and does not assert chronological ancestry. New relationships are added only to a separate preview; no relation or closure flag is written back to a native export.

Evidence rows contain exactly `id`, `kind`, canonical relative `file`, SHA-256, and exact `size_bytes`. `retained_artifact` bytes must match the captured owner-facts/CAS/Git/qualification hash inventory. `proposed_owner_statement` files use schema `codebase-ir-proposed-owner-evidence@1`, exact request/scope digests, and a bounded description. Evidence files are copied privately and deduplicated by hash; retained IDs remain separately addressable. Producer identity/method/policy remain unverified descriptions. This profile requires `native_certification_claimed: false` and `producer.authentication: "unverified"`; it does not authenticate an owner or accept a native closure certificate.

The preview detects cross-role dependency/revision leakage using the existing auditor and retains every original completeness issue. It flags disjointness claims contradicted by captured or proposed transitive groups, including same-path and normalized-AST revision grouping. A proposed complete inventory with unresolved frontiers is contradictory. Sparse responses preserve unanswered requests and unit IDs. Absence of a detected contradiction cannot establish relationship truth, dependency absence, repository closure, or independence from omitted sources.

Each fresh output directory contains the byte-pinned request/response/evidence, `captured_scope.json`, a new editable `response_template.json`, baseline audit, `proposed_relation_audit_report.json` when a response is supplied, and `response_review_report.json` (`codebase-ir-owner-response-review@1`). Report `disposition` is `awaiting_response`, `proposed_evidence_incomplete`, `leaks_found`, or `contradictory`; leak findings remain available alongside contradictions. Summary fields include request/observation/relation counts, unanswered IDs, baseline/proposed issue counts, contradiction/leakage counts, and retained evidence descriptors. Every review sets `native_closure_certification_verified: false`, `relationship_truth_verified: false`, `closure_claims_applied: 0`, and `whole_repository_coverage: false`. Exit `0` means valid review artifacts were generated, including adverse findings; `3` means malformed, stale, tampered, over-budget, or unwritable input/output.

Default response ceilings are 64 requests, 512 observations, 1,024 relationships/frontiers, 32 evidence files, 1 MiB per evidence file/8 MiB total, and 64 MiB total captured input bytes, in addition to the auditor's source/JSON/AST limits. Reads use remaining budgets before allocation. No source or evidence code executes, no Git recovery runs during review, and no fitting, database access, publication, or owner-state write occurs.

The authored controls in `fixtures/owner_response/` bind the exact retained native handoff: `positive.json` proposes grouping the two captured train revisions; `final-dependency.json` and `final-revision.json` deliberately connect train to untouched final sources; `contradictory-independence.json` also declares those train revisions disjoint. Their statement is proposed qualification evidence, not an owner attestation. Actual results are retained under [native-owner-response-20261002-02](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-owner-response-20261002-02/positive/response_review_report.json): the template roundtrip and positive control keep all 20 native issues open with no detected leakage, both final controls detect leakage, and the independence control reports a contradiction. Tests cover these relationships, transitive contradiction, missing model ancestry, stale head/target/scope bindings, strict malformed inputs, evidence tampering, repeated artifact bytes, budgets, pinned response read races, and deterministic private reports.

## Complete captured cohort inventory

`codebase_ir_cohort_inventory.py` enumerates every connected group in a response review, including singleton sources and groups with a single role. Generate a fresh response review with the current reviewer, then supply its report:

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_closure_response.py \
  --requests artifacts/codebase_ir_parallel_qualification/corpus_audit/native-closure-handoff-20261002-02/closure_requests.json \
  --response qualification/codebase_ir/corpus_audit/fixtures/owner_response/positive.json \
  --output /tmp/codebase-ir-current-response-review

python3 qualification/codebase_ir/corpus_audit/codebase_ir_cohort_inventory.py \
  --review /tmp/codebase-ir-current-response-review/response_review_report.json \
  --output /tmp/codebase-ir-captured-cohort
```

Template-only reviews are also supported. Current response reports contain exact hash/size descriptors for the request, owner facts, scope, baseline, response template, and response/relationship preview when present. The inventory verifies those byte pins and retained evidence, checks native head/target/source bindings and roles, and refuses source-population, identity, role, completeness, or baseline-relationship drift. Older reviews lacking the artifact inventory are explicitly refused; generating a new review supplies current pins without retroactively claiming that old artifacts were pinned. Artifact generation returns `0`; malformed, detached, missing, or over-budget inputs return `3`. Fresh directories/files remain private and immutable.

Groups join exact source-byte hashes, normalized AST hashes, repeated repository paths, captured declared dependencies/revisions, proposed owner dependency/revision additions, and ancestral train exposure. Unresolved dependency references participate in connectivity and remain named frontier nodes; sources sharing an unresolved reference cannot appear independent. Proposed disjointness is an annotation and cannot remove an existing connection. Every group reports source role/path/revision/digest, every original native version/head/target batch/index membership, ancestry exposures, explaining edges, unresolved claims, original false completeness claims, owner frontiers, proposed relationship annotations, and contradictions. Scope-wide unknowns remain separately visible and are marked as applicable to each group.

Final membership is explicit. A final source connected to train, tune, or canary has `final_exposure_risk: "connected_to_training_or_evaluation"`. Other final groups say only that no connection was observed in the captured scope, including whether their own or scope-wide unknowns remain. No group is certified independent: report and group `independence_verified`/`closure_certified` are false, `native_closure_certification_verified` is false, and `closure_claims_applied` remains zero. Source role assignments and populations are preserved; inventory output cannot filter, reassign, train on, or promote any source. Content checks authenticate byte relationships only; owner truth and whole-repository coverage remain unverified.

The output `cohort_inventory.json` uses schema `codebase-ir-captured-cohort-inventory@1`. Summary fields include exact `review_sha256`, review disposition, unit/group/cross-role counts, final and connected-final group counts, native membership and ancestral exposure counts, baseline/inventory issue counts, frontiers, and contradictions. Defaults bound 48 artifacts/64 MiB aggregate input, 16,384 explaining edges, and 512 group rows, alongside existing JSON/source limits. Captured artifacts are copied into the private result directory; reads use remaining budgets before allocation and no source/evidence code runs.

Actual retained controls are under [native-cohort-inventory-20261002-02](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-cohort-inventory-20261002-02/authored_control_summary.json). Template and positive reviews contain 12 exposures in five groups, nine native target memberships, one ancestral train exposure, two final groups, zero detected cross-role connections, and all 20 native issues. Both train/final negative controls produce four groups and one cross-role final group while retaining all 20 issues. The independence control keeps five groups and records its contradiction. Tests include all-group/singleton coverage, repeated native membership, train ancestry, positive and leaky proposed relationships, shared unknown dependency grouping, attached unknown/frontier counts, template-only review, detached byte/role/completeness drift, omitted baseline issues, unreviewed relations, explicit older-report refusal, budgets, and deterministic private output.

## Retained reviewed-candidate join capture

`codebase_ir_retained_join.py` captures the selected corpus subset of the reviewed candidate/adaptation join. It uses the existing native checkpoint adapter; it introduces no model replay or new source-role interpretation. The strict capture spec explicitly maps the recorded producer root to a current retained root, which permits relocation without rewriting the native checkpoint, head, target, or report bytes:

```json
{
  "schema": "codebase-ir-retained-join-capture-input@1",
  "path_mapping": {
    "declared_root": "/original/retained/fixture",
    "retained_root": "/current/retained/fixture"
  },
  "result_sha256": "<exact result.json SHA-256>",
  "independent_audit_sha256": "<exact independent-audit.json SHA-256>",
  "artifact_pins_sha256": "<exact artifact-pins.json SHA-256>",
  "context_paths": [
    "root-training-context", "root-frozen-context",
    "child-training-context", "child-frozen-context"
  ]
}
```

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_retained_join.py \
  --manifest artifacts/codebase_ir_parallel_qualification/corpus_audit/reviewed-candidate-source-cohort-20261002-02/input.json \
  --output /tmp/codebase-ir-current-reviewed-join
```

The selected subset is the result, independent review, original primary-pin inventory, and four native contexts with their checkpoint, lineage, and model-record files. The tool checks exact result/review/pin hash joins, each selected primary pin, checkpoint descriptors, native train/frozen version correspondence, embedded lineage checkpoint bytes, complete terminal parent chains, record/report correspondence, source head and recorded feature-basis identities. Checkpoint source and target checks use the existing auditor. Original roles and replay exposures are retained; no native exposure becomes final. Only the unchanged existing `examples/untouched_final_input.json` fixture units are appended as final. Metadata-only source paths are recorded without inventing a train/evaluation role or declaring their dependency closure.

Native continuation, context/contract/state identities, source heads, feature columns and frozen-basis equality are retained as byte-bound claims. The adapter does not reconstruct numerical state, Adam updates, registry/version authentication, source-runtime semantics, producer truth, or absent forks. `fork_status` explicitly says that a fork was not declared by the captured profile. `numerical_state_replayed`, `registry_opened`, and `training_executed` are false. Independent audit status and its primary-pin count describe the retained upstream report; this tool does not rerun that audit or verify the entire primary artifact set.

The private output retains exact selected raw files and exports, `audit_input.json`, baseline audit, conservative `source-metadata/`, `closure-requests/`, a proposed-response template, and all-group `cohort-inventory/`. `retained_join_report.json` uses `codebase-ir-retained-join-corpus@1`; its summary binds the capture spec/result/review/pin bytes, relocation mapping, selected file/hash inventory, native context/version/target/ancestral memberships, metadata-only paths, original/reconstructed issues, clone findings and groups. Exit `0` means these artifacts were generated, including leakage or unknown closure; invalid/drifting/over-budget inputs return `3`. `closure_claims_applied` remains zero, and independence/native closure/whole-repository certification remain false.

Defaults permit 2,048 primary-pin descriptors, 32 selected files/32 MiB total and 16 lineage rows, alongside existing JSON/source/AST limits. The original primary and context descriptor sizes cap reads before allocation; disagreement is refused before reading. Pin inventory parsing does not open its unselected SQL, Parquet, proof, key, or registry entries. Neither original fixture state nor any model owner is opened or modified.

The current retained corpus run is [reviewed-candidate-source-cohort-20261002-02](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/reviewed-candidate-source-cohort-20261002-02/capture/retained_join_report.json), bound to `finite-reviewed-candidate-qualification-20261002-07`. Its selected 19 files total 11,331,195 bytes, compared with 1,637 upstream primary descriptors; the complete upstream artifact set is not re-audited. Two model versions contribute 13 original native target memberships and two ancestral training exposures. The four selected native paths are `calc.py`, `known_variant.py`, `tune.py`, and `canary.py`; six other authored paths remain explicitly metadata-only.

This source audit detects **train/tune/canary normalized-AST overlap**: original `calc.py`, tuning, and canary files share the annotated `increment(n)` body returning `n + 1`, differing only by comments. Successor `calc.py` returning `n + 2` also matches the known training variant. Same-path lineage connects those captured revisions, producing one combined train/tune/canary group of 15 exposures plus two singleton final groups. Both baseline and conservative reconstruction retain 30 unresolved dependency/revision claims and five bound closure requests. The original authored experiment already described its cohort as transductive; these findings do not establish blind generalization, alter its roles, or confer any numerical, behavioral, or promotion qualification. Controls cover explicit relocation, raw/context/primary pin drift, missing ancestry, complete context population, immutable retained input under later source changes, descriptor-size preallocation, budgets, fixed final fixture bytes, and deterministic private outputs.

## Authored final protocol and exported-prediction scoring

`codebase_ir_final_evaluation.py` prepares a separate evaluation record from exact source, label and prediction files. It loads no model, executes no target source, calls no checker, and opens no native owner or database. The new bundle in `fixtures/final_protocol/` contains three authored pure Int/Bool expression sources, one explicitly unsupported call, and three separately authored comparator sources labeled train/tune/canary for the declared split screen. The comparator labels do not claim that any training occurred. The previously retained native roles and final fixtures remain separate.

These are qualification-authored sources and targets. Authoring does not certify absence from earlier model training. `unknown_pretraining_exposure` stays true, `authoring_training_absence_certified` is false, and no result certifies held-out independence or generalization. The tool cannot certify native dependency closure or the completeness of omitted parent/source inventories. FINAL sources, labels and results never select a candidate, tune a model or decide promotion.

Run the authored demonstration:

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_final_evaluation.py \
  --manifest qualification/codebase_ir/corpus_audit/fixtures/final_protocol/manifest.json \
  --output /tmp/codebase-ir-authored-final-evaluation
```

The manifest uses `codebase-ir-final-evaluation-input@1` and exactly four descriptors: `protocol`, `cohort`, `targets`, and `predictions`. Each descriptor has a canonical relative `path`, lowercase `sha256`, and exact integer `size_bytes`. Paths stay inside the original manifest directory; absolute paths, traversal, hidden/dot selectors, aliases, symlinks and special files refuse. Source descriptors inside `cohort.json` use the same fields. Pass the original manifest path, or copy the entire bundle while preserving its relative layout. The output directory must be fresh and outside the input bundle.

`protocol.json` pins the qualification source profile, metric definitions, unknown parent exposure and forbidden selection/promotion policy. `cohort.json` binds every supplied source ID, role, repository/path/revision, template family, dependency and related-revision claims. The existing corpus auditor checks byte/AST clones, repeated paths, dependency-connected revisions and unresolved references. Template-family cross-role connections are reported separately rather than relabeled as actual revision facts. A final connection remains a finding; no filtering or reassignment occurs. Screening only the supplied authored comparator scope cannot establish independence from native models or unseen parent training.

`targets.json` gives every final source a supported or unsupported disposition, exact source SHA/function/UTF-8 byte span/slice SHA, and source-derived target or explicit missing target. Desired intent is a separate field with `intent_used_as_label: false`. The nonexecuting source projection independently reconstructs the authored labels and refuses altered literals, operators, source spans or desired-intent substitutions. The source profile is **`qualification/pure-int-bool-expression@1`**, using one LF-only standalone function, ordinary required Int/Bool parameters and one return expression. It supports bounded integer literals, Boolean literals, references, `Add`/`Sub`/`Mult`, `USub`/`Not`, comparisons and Boolean conjunction/disjunction. Calls and broader statement/effect grammar remain unsupported. The function slice must reproduce the selected AST exactly, including multibyte identifiers.

This is a qualification representation, not a new registered native source384 decoder or semantic lowering profile. Annotations are declared assumptions, and exact structural projection does not prove runtime types, CPython behavior or source semantics. `teacher_semantics_certified` and `native_decoder_compatibility_verified` remain false.

Prediction inputs use `codebase-ir-final-predictions@1`, an exact protocol SHA, a closed producer record and bounded rows. Each row contains `prediction_id`, `case_id`, `mode` (`learned`, `model_off`, `zero_head`), the source binding, and separate `raw`/`constrained` outputs. Outputs have `state` (`candidate`, `abstained`, `unsupported`), `origin`, and `target`; constrained output also declares `mechanism` (`none`, `grammar_constraints`, `teacher_substitution`). `none` must preserve raw output exactly. Wrong bindings, teacher substitution, malformed/ill-typed candidates and a model-off candidate produce score findings. Zero-head chance matches stay in their own mode; they cannot establish learned weight dependence.

**`simulated_predictions.json` is entirely hand-authored simulation data. It contains no numerical predictions, checkpoint or model execution.** Its producer origin is `authored_simulation`; candidate origins must match that designation. Future external exports may use `unverified_export` with a claimed checkpoint SHA for learned/zero-head rows and candidate origin `model_output`. Adapting the existing native output codec into this qualification representation needs explicit owner review; this CLI performs no automatic native conversion. Producer origin, mode, checkpoint and constraint mechanisms remain unverified claims even after exact byte pins pass. Numerical, constraint-transformation, native teacher compatibility and learned-dependence qualification require their owners' independent evidence.

The scorer retains original prediction bytes unchanged under `inputs/`, with separate canonical extracts in `raw_outputs.json` and `constrained_outputs.json`. It never repairs a raw prediction with the label. Scores stay separate by mode and stage. Source-binding denominators cover all exported rows; type/exact-reconstruction denominators cover supported-source rows. Reference/operator/literal denominators cover supported rows whose source target has that structure, so absent literals cannot inflate a literal score. Unsupported-source rows have their own disposition denominator. Per-case/per-mode coverage lists missing modes explicitly; omitting every prediction for a final source refuses. Multiple authored corruption controls for one case remain separate rows, not independent samples.

`final_evaluation.json` uses `codebase-ir-final-evaluation@1`. `status: "passed"` and exit `0` mean a bounded scoring record was produced, including wrong predictions, split leakage or unknown closure. They do not indicate passing accuracy, a qualified model or an independent final cohort. Invalid/drifting/over-budget inputs produce `status: "refused"` and exit `3`. The report pins `manifest_sha256`, all captured input files and sizes, protocol/prediction hashes, score denominators, row findings, split/template exposures, coverage and all false execution/authority/selection/promotion claims. Inputs are reread before and after private retention; exact descriptor sizes and remaining budgets cap reads before allocation.

Defaults bound 128 input files/8 MiB aggregate, 1 MiB per JSON file, 64 KiB per source, 32 final cases, 128 supplied units, 128 prediction rows and 256 expression nodes/32 expression levels, alongside existing JSON/AST audit limits. The authored controls cover raw/constrained separation, changed operators/literals/reference order, Boolean-versus-integer typing, wrong source/teacher/model-off/zero-head output, separate desired intent, unsupported and missing cases, mode coverage, template/revision/dependency/clone connections, unknown ancestry, Unicode/LF spans, malformed/duplicate inputs, bounded reads, aliases/special files, input races and deterministic reports.

The retained [authored demonstration](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/final-protocol-authored-20261002-02/final_evaluation.json) binds 43,757 captured bytes, seven source units, four final cases (three supported and one unsupported), and 15 simulated rows with all three modes represented for every case. It produces 18 intentional prediction findings and an incomplete split screen because ancestral exposure is unknown. No final connection was observed among the seven supplied authored sources; that observation does not certify training absence. The manifest SHA is `1b45eed57419aed50e63568edf326f7cfe19e284eb05d86a94e004dcbf87e9bd`. All 121 corpus-lane tests, including 22 final-protocol tests, and repository-profile Ruff checks pass.

## Locking FINAL inputs across prediction exports

The separate `codebase_ir_final_lock.py` workflow fixes the exact authored protocol, cohort, targets and every selected source file before later prediction exports are scored. It does not change the original fixture generation, scorer or retained demonstrations. It reads and validates the fixed inputs, independently rederives source labels, and retains their original bytes. It validates the declared prediction descriptor without reading that body; the predictions file may be absent when the lock is created.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_final_lock.py \
  --manifest qualification/codebase_ir/corpus_audit/fixtures/final_protocol/manifest.json \
  --output /tmp/codebase-ir-final-lock
```

The resulting `final_lock.json` has schema `codebase-ir-final-input-lock@1`. Its `locked_identity_sha256` covers the protocol ID, raw/canonical JSON descriptors for `protocol`, `cohort` and `targets`, and the sorted raw/normalized-AST source inventory. All source roles, template families, revisions, dependencies, case IDs, source-only labels, desired intent, metrics and split policies are therefore fixed. Exact JSON formatting and relative selectors are fixed as well. The original evaluation manifest is retained and pinned as provenance, including its original prediction descriptor, but that whole manifest and the mutable prediction rows are excluded from the locked evaluation identity. Mutable predictions cannot share a path with a locked file.

`final_lock_report.json` uses `codebase-ir-final-input-lock-report@1`; it reports the original `manifest_sha256`, receipt `lock_sha256`, `locked_identity_sha256`, protocol ID, source/case counts, exact selected file inventory, `prediction_bodies_read: false`, input stability and false authority/execution claims. `status: "passed"` and exit `0` mean that the unsigned byte lock was produced. Invalid or drifting inputs return `3`; no lock is published as successful.

Run a later export against an explicitly pinned lock:

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_locked_final_evaluation.py \
  --manifest /path/to/later-export/manifest.json \
  --lock /tmp/codebase-ir-final-lock/final_lock.json \
  --lock-sha256 <exact-raw-receipt-SHA-256> \
  --output /tmp/codebase-ir-locked-final-evaluation
```

The current export must preserve the fixed JSON/source bytes and relative layout. The prediction descriptor and prediction body may change, and the current manifest may have a different filename or bundle location. The required raw receipt SHA prevents replacing or re-pinning the lock implicitly. The validator reconstructs the entire receipt from its retained `inputs/` bundle and compares the current fixed identity before creating the fresh output directory. Output must be outside both the current evaluation bundle and the original lock bundle. Malformed, wrong, missing or detached locks create no output.

The locked evaluator captures current predictions once, evaluates a private copy of that first complete capture with the unchanged scorer, and verifies the resulting manifest and full input hash/size population. It retains the original receipt, original fixed baseline and current evaluation bytes separately. It rereads the receipt, retained baseline and current inputs before and after scoring; drift produces refusal rather than success with mixed source bindings. The top-level `final_evaluation.json` preserves `codebase-ir-final-evaluation@1` and adds exact `lock_sha256`, `lock_enforced: true`, `locked_identity_sha256`, the original lock manifest SHA and shared input bounds. The raw and constrained score artifacts remain separate under `scored/`.

The lock authenticates selected byte relationships only. It is unsigned, and the caller must deliberately trust its explicit raw receipt pin as the evaluation baseline. It does not establish producer identity, globally unique protocol IDs, native decoder compatibility, numerical provenance, source semantics, training absence or held-out independence. Creating and explicitly selecting a different lock is a different baseline; this tool opens no global protocol registry. Unknown parent exposure remains true, all numerical/semantic/native/authority/selection/promotion certification claims remain false, and valid negative predictions still yield a produced scoring record rather than a qualified model.

The workflows share a preallocation budget of 256 first-capture files and 16 MiB across the receipt, retained baseline and current export, alongside the original evaluation's per-bundle file/JSON/source/AST limits. Every known descriptor size and remaining aggregate budget bounds allocation before a read; sequential stability rereads use captured exact sizes. The 26 new controls include coherent same-ID source/label changes, role/family/dependency and desired-intent edits, missing/new cases, metrics/split-policy changes, changed receipt pins, detached source bodies, strict JSON, symlinks/traversal, output protection, descriptor/aggregate budgets, missing predictions, current/receipt read races, private scorer population substitution and deterministic seals/reports.

The [retained lock demonstration](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/final-input-lock-authored-20261002-01/authored_demonstration.json) seals 12,548 bytes of the original selected fixed inputs, then scores both the unchanged authored exports and a separately labeled later authored simulation. Only the later prediction producer label and one raw literal change; all fixed source/protocol/cohort/target bytes and the locked identity remain equal. Both records retain four cases, 15 simulated rows, 18 intentional findings and unknown ancestral exposure. Receipt SHA `402d53e03ae1059bd9d38ad60d19e9c98bfff5e1040dae86bd050d9066aa696e` binds identity `496f8ecdd302dc0b9697baac2b4bf777d209aa17f535e2590be65944f51e4359`. The demonstration verifies that every prior fixture file remains unchanged. All 147 corpus-lane tests and repository-profile Ruff checks pass.

## Comparing two locked FINAL exports

`codebase_ir_paired_final_evaluation.py` compares explicitly selected before/after exports under the same raw FINAL receipt. Its input has schema `codebase-ir-paired-final-evaluation-input@1`, a `lock` descriptor, and `before`/`after` objects containing `manifest` and `report` descriptors. Every descriptor has exactly `path`, `sha256` and `size_bytes`; paths are absolute, canonical nonsymlink regular files and raw hashes/sizes are mandatory. The output must be fresh and outside the input spec, both export bundles, the lock baseline and both pinned report scopes.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_paired_final_evaluation.py \
  --manifest artifacts/codebase_ir_parallel_qualification/corpus_audit/paired-final-evaluation-input-20261003-01/paired_final_input.json \
  --output /tmp/codebase-ir-paired-final-evaluation
```

Before creating output, the tool reconstructs the receipt from its retained original fixed inputs and verifies both export identities with the existing lock validator. It captures exact selected inputs, then uses the unchanged locked scorer on private copies to independently reconstruct both complete pinned reports. Canonical equality covers every report field, including row population, metric denominators, flags, source inventory, exposure findings and bounds; no summary-only assertion is trusted. Reports produced with different scoring bounds are different records and refuse this exact reconstruction profile. Exact original manifest, prediction, lock, baseline and report bytes are retained; originals and all declared raw copies, including the privately rederived input populations, are reread before successful publication.

Pairing uses `prediction_id` with an unchanged `case_id` and mode. Moving a retained ID between cases or modes refuses. Removed and new IDs remain separate `missing_after`/`missing_before` records. Matching by output, highest score or case alone is never used. For each paired record, raw and constrained bodies remain separate, original source bindings and findings are preserved, and each relevant metric reports a gain, regression, unchanged correct or unchanged incorrect transition. Unsupported-source disposition remains separate; absent structural features and missing records contribute no success. Learned, model-off and zero-head records each have their own transition tables.

These are counts of exported records, not independent samples. Every case/mode population lists both ID sets and multiplicities. A mode's `unique_case_summaries` is `unknown` if any case has multiple controls, missing mode coverage or unpaired IDs; no control is chosen or discarded to create a case-level accuracy estimate. A summary can be `available` when all cases have one identically paired record, without establishing held-out independence or learned weight dependence. Producer labels, modes, constraints, checkpoint provenance and numerical origin remain unverified even when raw pins and the full reports agree.

`paired_final_evaluation.json` uses `codebase-ir-paired-final-evaluation@1`. A passed record binds `manifest_sha256`, `lock_sha256`, `locked_identity_sha256`, both source manifest/report hashes, the complete selected input inventory, record and case/mode populations, and full per-record transitions. `source_reports_independently_rederived`, `lock_enforced`, `input_files_unchanged` and `raw_outputs_retained_unmodified` are true only for a completed audit. Existing native/training/authority/selection/promotion/numerical/semantic/independence flags remain false, alongside `learned_quality_improvement_verified`, `independent_samples_established` and `paired_records_are_independent_samples`. Parent exposure remains unknown. Exit `0` means a bounded comparison record was generated, including adverse or missing results; it never selects or qualifies a model. Invalid or drifting inputs return `3`.

First reads are bounded to 518 files/38 MiB across both locked export captures and outer descriptor inputs. Each underlying locked export keeps its 256-file/16 MiB ceiling; outer JSON descriptors are limited to 1 MiB each. Budgets, regular-file checks, exact declared sizes and remaining bytes bound reads before allocation, with captured-size stability rereads afterward. Twenty-eight new controls cover late retained-copy drift, correlated report forgery, typed flag/population changes, changed fixed identity, wrong lock pins, explicit ID pairing, reordered rows, missing modes/IDs/cases, duplicate controls, separate raw/constrained gains and regressions, unsupported relevance, teacher/model-off findings, source-binding changes, strict JSON, aliases/special files, output protection, bounds, read races and deterministic raw retention.

The [retained paired demonstration](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/paired-final-evaluation-authored-20261003-02/paired_final_evaluation.json) independently reconstructs the earlier original and later authored locked reports. It retains all 15 pairs across four cases, 39 distinct selected files and 54 first reads totaling 148,683 bytes. One raw literal and the producer label changed; constrained outputs stayed identical, with zero measured metric gains or regressions. Learned/model-off unique-case summaries remain unknown because the delta case has three/two authored control records; the zero-head summary is available only as recorded case transitions. Both producers are explicitly authored simulations, and no learned quality gain is established. Input SHA `1e70ea43603d95abafda69bced9a2ac4d2620c55e2997fcca70d51dec74b08cb` binds report SHA `08198e2745e5707421f66f463cfc0f91c4606c193063105fc7e270e32e1bf267`. All 175 corpus-lane tests and repository-profile Ruff checks pass.

## Source-only contrast generation before prediction exports

`codebase_ir_contrast_cohort.py` creates a separately authored generation from exact source bytes with the unchanged nonexecuting source projection and FINAL validator. It does not create or read prediction bodies. The committed `fixtures/final_protocol_v2/` generation has 28 FINAL cases, 21 supported structural labels and seven explicit unsupported targets, plus three comparator sources with declared train/tune/canary roles. The comparator roles do not claim numerical training. Original fixtures, FINAL scorer and lock implementations remain unchanged.

Ten predeclared contrast pairs cover small/large literals, strict/inclusive guards, guard polarity, operand order, symbol selection, Unicode identifiers, Boolean connectives, Int/Bool literals, comment-only normalized clones and related same-path revisions. A helper/consumer dependency group preserves the unsupported callable consumer. All 31 units remain in connected template/AST/path/dependency/revision groups with explaining edges; those groups are not independent samples. Unknown parent exposure and unresolved calls remain explicit. Native vocabulary membership, Python semantics, native decoder compatibility and semantic equivalence of superficially similar contrasts are unverified.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_contrast_cohort.py \
  --output /tmp/codebase-ir-new-source-only-cohort

python3 qualification/codebase_ir/corpus_audit/codebase_ir_final_lock.py \
  --manifest qualification/codebase_ir/corpus_audit/fixtures/final_protocol_v2/manifest.json \
  --output /tmp/codebase-ir-contrast-final-lock
```

`future_predictions.json` is absent. Its empty-byte descriptor is a placeholder accepted by the unchanged source-only seal, not a prediction artifact or expected numerical output. A later separately retained bundle supplies its exact mutable prediction descriptor under the existing fixed-input lock. FINAL outcomes never select or promote a model. The [source-only preparation](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/contrast-final-preparation-20261003-01/lock/final_lock_report.json) seals manifest `be1aa3906531e33f00b5b59d8a91bccc0977c07b8f6a9beb7a421a2b57b4b5af`, receipt `6438f5c68738883bac7bcfde67213ce6ed0620ecb7fc9d0c203bdb1ad688fd6d`, and locked identity `2cec7cdef4d1f21878e7c57885f49be8c6b6c491f6fd222651948a27d11071bd`. Its separately created [authored validation](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/contrast-final-preparation-20261003-01/authored_validation.json) scores 84 simulations only after the source-only seal and preserves every original fixture byte. Ten new controls check contrasted labels, typed literals, multibyte spans, complete grouping, unsupported coverage, immutable later exports and deterministic preparation.

## Public native source384 export diagnostics

`codebase_ir_native_source384_diagnostics.py` reads four selected public export roles under an exact public acceptance-manifest pin. It preserves the registered `structured-source-384-autoencoder/v1` codec and native outputs; it does not convert them into the authored FINAL representation or run any native code.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_native_source384_diagnostics.py \
  --manifest artifacts/codebase_ir_parallel_qualification/corpus_audit/native-source384-diagnostics-input-20261003-01/native_source384_input.json \
  --output /tmp/codebase-ir-native-source384-diagnostics
```

The closed input uses `codebase-ir-native-source384-diagnostics-input@1` and exactly `schema`, `release`, `public_manifest` and `exports`. `release` has a claimed datasets repository and exact commit; it does not authenticate Git custody. `public_manifest` and the four `exports` roles (`learned`, `zero_head`, `source_label_baseline`, `qualification`) use canonical absolute nonsymlink regular-file descriptors with exact raw SHA and size. Each selected body must match its original public-manifest relative selector, size and hash. Unselected children remain named without being opened. Fresh output must be outside every original selected input scope.

The reader checks closed native envelopes/rows, exact scalar class and finite 384D recorded projection layouts, source/candidate contract digests, checkpoint joins, typed authority flags and recorded source spans. Pairing uses exact native IDs and source digests, with unchanged learned/zero-head source-generation/projection bindings. Missing mode records remain explicit; duplicate IDs refuse. Recognized binary candidates and unsupported codec shapes have separate dispositions. Target access, teacher forcing and ablation metadata are recorded claims or explicit unknowns, with adverse findings retained. The original bytes and returned candidates remain separate from any claimed source-check status.

The native model-off artifact is a **deterministic source-label baseline**, not numerical model inference or an abstention. Its own route and candidate-digest comparisons stay separate; it is never mapped to the authored scorer's `model_off` policy. Returned native candidates are not assumed to be preconstraint raw decoding. The selected codec supplies source hashes and span commitments without independently pinned raw source inputs. Accordingly, source-derived accuracy, held-out independence, learned weight dependence, numerical/producer authentication and semantic qualification remain false. The report's `source_only_handoff` names exact native IDs/source digests and retained span commitments while requesting raw source bytes/selectors, ancestry, output-stage declarations and owner-reviewed codec policy. It opens no owner state and contacts no producer.

`native_source384_diagnostics.json` uses `codebase-ir-native-source384-diagnostics@1`, binding both `manifest_sha256` and `public_manifest_sha256`. Passed status means a bounded diagnostic record was produced, including unknowns, missing rows or adverse metadata. First reads are capped at six files, 1 MiB per file and 8 MiB aggregate, 32 rows per numerical/baseline role and 64 public-manifest children. Descriptor sizes and remaining bytes constrain reads before allocation. Strict JSON, canonical paths, no-follow file checks and hard-link alias refusal precede output; original inputs and retained copies are reread before success. Recorded costs and training flags remain distinct from the auditor's zero native/training execution claims.

The [retained public diagnostic](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-source384-diagnostics-retained-20261003-03/native_source384_diagnostics.json) selects exact inert child copies from the release lane's pinned datasets commit `8de37ba8d216cd21a5d7134292de01d9e12c9a56`. Its public manifest SHA is `5496c7585a741526c27d7d7529510a865e562a707d14ad60d58f5fefca549907`; input SHA is `4310d4c7ed94f8d585dd581b9bf29e6121e6ecde8f54ad5740bff6d0bfd839fa`. Three learned, three zero-head and three source-label rows form three complete ID/source pairs. Learned returned candidate digests match the three recorded source-label candidate digests; zero-head candidates differ. This is an archived three-case diagnostic, not measured held-out accuracy or a learned quality gain. All 210 corpus-lane tests, including 25 native diagnostic controls, and project Ruff checks pass.

## Exact public source comparison for historical native fragments

`codebase_ir_native_source_comparison.py` extends the archived diagnostic with the exact source text already declared in its public `public/replay-identity.json` child. It uses the unchanged source projection and prior diagnostic reader. The earlier reader, its selected four-role profile, all FINAL scorers, and both fixture generations remain unchanged.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_native_source_comparison.py \
  --manifest artifacts/codebase_ir_parallel_qualification/corpus_audit/native-source-comparison-input-20261003-01/native_source_comparison_input.json \
  --output /tmp/codebase-ir-native-source-comparison
```

The closed input schema is `codebase-ir-native-source-comparison-input@1`, with exactly `schema`, `diagnostics_input`, `diagnostics`, `source_replay` and `public_manifest`. Each descriptor has a canonical absolute `path`, exact raw `sha256` and exact `size_bytes`. The source replay must match the original public child declaration. The original diagnostic input must name the same public manifest. Every prior retained copy is checked against pins independently derived from that input; the full original diagnostic is then reproduced byte for byte from its raw native bodies. Re-pinning an edited report cannot replace that reconstruction. All original inputs, previous copies, new copies and separate source exports are checked again before success.

Source text is decoded into exact UTF-8 bytes, joined by native ID and whole-source digest, and checked against every available recorded byte span. The unchanged `derive_source` labels the function under declared Int/Bool annotation assumptions. A separate adapter handles only two integer parameters and one binary arithmetic operation or comparison over both distinct parameter references. It derives the expected native expression fragment and compares the returned operator, result sort, operand order, references and complete closed fragment. It does not reconstruct a model-produced function name or signature from absent native fields. Literal, guard and effectful structures outside this codec, unsupported returned codecs and missing modes retain explicit dispositions and contribute no match. The deterministic source-label baseline has its own digest comparison and is never counted as numerical model-off inference.

The new report names row digests `claimed_model_head_sha256` and `claimed_model_projection_sha256`: these are recorded numerical state claims, not source-head identities or verified weights. `captured_source_head_canonical_sha256` binds the separate replay source metadata, which must equal the baseline's captured source head. Matching either metadata identity grants no source-owner authority, numerical provenance or learned weight dependence. Output stage remains a returned native candidate with an unknown preconstraint/postconstraint boundary. Missing ancestral train/tune/canary exposure remains unknown; these historical cases are not assigned to a new FINAL partition.

`native_source_comparison.json` uses `codebase-ir-native-source-comparison@1`. It independently binds `manifest_sha256`, `diagnostics_input_sha256`, `diagnostics_report_sha256`, `source_replay_sha256` and `public_manifest_sha256`. Passed status means a source structural comparison record was produced. Source semantics, runtime equivalence, native execution admission, numerical/producer authentication, held-out independence, learned quality, head state validation, model selection and promotion remain false. The workflow bounds 17 first input reads and 16 MiB aggregate, 1 MiB per body, 32 replay cases, 64 KiB per source and 2 MiB of source text. Prior diagnostic limits remain unchanged; combined declared sizes reserve its reads and old retained copies before allocation. Original and copied bodies are reread with captured exact sizes. The 26 new authored controls cover coherent source/span/hash and candidate changes, missing/duplicate IDs, report replacement, native/source head confusion, unsupported codec/source outcomes, target-access unknowns, baseline separation, multibyte spans, aggregate bounds and late original/copy mutations.

The [retained historical comparison](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-source-comparison-retained-20261003-01/native_source_comparison.json) binds input SHA `6bd41310acb052c81c525dfab8d5ca672d8df2f1aefd54cd7981c702be86ad66`, source replay SHA `e439c955b9d02db4268656887d3cb4132ff7161230055b676506d38a7370d680`, and report SHA `43a18d14d2ca0a4ee553bf001187883eb6aa1fd7815179ca0f851bcd81b0c253`. All three exact 85-byte sources match their released native source digests and recorded spans. Learned returned fragments match all three independently derived structural labels; zero-head fragments match none. The three deterministic baseline digests match separately. These are historical structural observations with unknown exposure and unverified numerical provenance, not evidence of held-out quality improvement. All 236 corpus-lane tests and project Ruff checks pass.

## Independent source-bound ProgramIR graph conformance

`codebase_ir_native_program_graph.py` checks the complete native ProgramIR documents retained inside historical source contracts, beyond the earlier returned expression-fragment comparison. It reads the exact original source comparison input and report, reproduces that comparison with the unchanged reader, and checks its retained native bodies and exact source exports. Earlier readers, sources, fixture generations, reports and FINAL locks remain unchanged.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_native_program_graph.py \
  --manifest artifacts/codebase_ir_parallel_qualification/corpus_audit/native-program-graph-input-20261003-01/native_program_graph_input.json \
  --output /tmp/codebase-ir-native-program-graph
```

The closed input `codebase-ir-native-program-graph-input@1` contains exactly `schema`, `source_comparison_input` and `source_comparison`. Both descriptors contain canonical absolute `path`, exact raw `sha256` and exact `size_bytes`. The complete earlier report must reproduce byte for byte from its pinned chain; re-pinning a changed report cannot replace that reconstruction. Transitive original input scopes are protected before output creation. The combined outer/nested workflow reserves 20 first input reads and 20 MiB before nested capture, with 1 MiB body limits, 32 historical cases, 64 KiB source limits and 128 items per graph collection. Original inputs, all nested retained bodies and every graph extract are checked again with exact captured sizes.

The separately declared `qualification/source-bound-two-int-binary-program-graph@1` profile covers one standalone function with two Int parameters, one arithmetic operation over both distinct parameter references, and one return. It independently derives parameter order, types, operands, operation, seven exact AST spans, return and function structure from source bytes. Native symbol/reference identities must resolve to those declarations. The return command and one-block CFG must contain the same expression, in source evaluation order. Command/function read footprints must contain the referenced parameters, with no assignment writes. Recorded effect refinements must bind these current footprints, and recorded type refinements must bind the actual typed graph members. Unsupported source/graph profiles and missing projections remain explicit; no graph is created to fill missing output.

The syntax bridge's embedded document must preserve the retained native graph. Candidate/source-reference maps and operator mappings must bind the actual returned learned candidate. A missing or wrong learned candidate cannot be replaced by the teacher-derived program. Only the explicitly separate deterministic source-label baseline uses a source-derived fragment for its label binding; its row/lowering program hashes and recorded footprints must match its own native graph.

These full graphs are **deterministic source-contract projections after validation**, not independently generated learned full-program outputs. Structural conformance does not verify runtime semantics, absence of runtime effects/exceptions, free-running full-program quality, numerical provenance or held-out independence. Other serialized effects retain the narrow profile's declared assumptions. The recorded before-effect program is unavailable, so the report does not certify the producer's prior graph or transformation history. Native program IDs and synthetic source URIs remain selected metadata claims; the URIs are never opened. Ancestral exposure remains unknown, and no new FINAL assignment, fitting, model selection or promotion occurs.

`native_program_graph.json` uses `codebase-ir-native-program-graph@1`, binding `manifest_sha256`, `source_comparison_input_sha256`, `source_comparison_report_sha256`, and the independently joined source replay/public-manifest hashes. Its role metrics distinguish present/conformant/missing/unsupported graphs, with the deterministic baseline separate from learned and zero-head observations. Passed status means this bounded source structural record was produced. The 29 controls include coherent graph/operator/operand/reference changes, byte spans with recomputed hashes, changed effect audits and footprints, CFG/return changes, bridge substitution, type refinements, missing candidates, teacher substitution, baseline joins, unsupported sources/codecs, changed report pins, aggregate limits, output protection and late original/copy drift.

The [retained graph comparison](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-program-graph-retained-20261003-02/native_program_graph.json) binds input SHA `86a8bca8cf3a3866ac967a4ca0afc83a19784178f06e570f3e41aa2c53fec373` and report SHA `a9c15470fd04a545e6ca3abc0ba47d0f8295eb6a6c2cd8e9f0eee6c66971bb74`. The same three historical 85-byte sources support three learned source-contract projections and three separate baseline projections. All six graphs conform to the declared structural profile; all three zero-head projections remain missing. This supplies no new model-quality or semantic qualification. All 265 corpus-lane tests and scoped project Ruff checks pass.


## Independent emitted Lean projection correspondence

`codebase_ir_native_lean_projection.py` checks the next retained compiler stage after the source-bound ProgramIR audit. It parses inert exported `SecuritySourcePrograms.lean` bodies and reconciles their closed declarations with the exact pinned graph. It never imports an owner compiler, runs Lake/Lean, executes source or trains a model. Every earlier module, fixture, report and FINAL lock remains unchanged.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_native_lean_projection.py \
  --manifest artifacts/codebase_ir_parallel_qualification/corpus_audit/native-lean-projection-input-20261003-01/native_lean_projection_input.json \
  --output /tmp/codebase-ir-native-lean-projection
```

The closed input `codebase-ir-native-lean-projection-input@1` contains exactly `schema`, `program_graph_input`, `program_graph_report`, `learned_lake_receipt`, `learned_lean`, `source_label_baseline_lake_receipt` and `source_label_baseline_lean`. Each descriptor has a canonical absolute `path`, exact raw `sha256` and exact `size_bytes`. The unchanged graph workflow must reproduce its entire prior report byte for byte. All four additional bodies must independently match the original released acceptance manifest's exact relative child paths, sizes and hashes. Re-pinning an edited report or local body cannot replace those joins.

The declared `qualification/source-bound-two-int-binary-lean-projection@1` profile resolves the native symbol-to-store-slot and expression-to-definition maps in deterministic identity order. It reconstructs each integer expression, ordered operands, one return outcome, declared syntactic read/write summaries and 17 descriptive evidence definitions directly from the pinned graph. Extracted metadata, source references, effect audits, assumption strings and false authority declarations must match exactly. The metadata-empty operational view's body hash is rederived under its recorded program ID; that ID's origin remains unauthenticated. The historical per-row compiler declaration digest has an unavailable producer recipe and stays a recorded claim, separately from the independently hashed raw emitted namespace body.

This is **closed textual compiler-output correspondence**, not a semantic compiler proof or free-running learned prediction. The ledger explicitly records that native IDs become generated slot/definition names, one-block control flow becomes the specialized return definition, metadata becomes evidence strings, and individual source spans are retained in the graph without separate Lean span declarations. Semantic projection losses and operational/runtime/universal semantics remain unavailable. The producer's archived compiler execution metadata is retained as a claim and never replayed. Numerical provenance, producer authentication, learned weight dependence, held-out quality and full ancestral exposure remain unverified; the zero-head's missing graphs are never filled with teacher projections.

`native_lean_projection.json` uses `codebase-ir-native-lean-projection@1`. It binds the raw outer manifest and all six selected descriptor hashes, plus the independently joined source replay and public-manifest hashes. The combined capture reserves the unchanged graph workflow's 20-file/20-MiB budget within a 32-file/40-MiB ceiling. Outer bodies have a 2-MiB ceiling; Lean bodies are capped at 64 KiB before allocation and 2,048 lines before parsing. Original transitive source/compiler scopes are protected before output creation. All originals, old retained graph/source inputs, the nested public/native diagnostic copies actually consumed, and new exact retained bodies are checked again before success.

The [retained projection comparison](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-lean-projection-retained-20261003-01/native_lean_projection.json) binds input SHA `7f10a6dbe7e7389692c73dec86986302bd2104dc740f8aa18d668bdd2b43cf1e` and report SHA `fd312fdf926038392e28d129cdd0c8d469fc85fc99a0556af7e941dcab75b9b8`. Three historical learned projections and three separate deterministic baseline projections conform to the declared text profile. The two 20,251-byte emitted Lean bodies are identical: this is compiler-output equality, with no measured learned gain. Their six projections contain 18 expression definitions, 18 store slots, six return definitions and 102 descriptive evidence definitions. Forty-two source-span occurrences remain in the native graphs and zero are individually emitted. All three zero-head projections remain missing.

Twenty-nine new authored controls carry embedded inert native graph/Lean fragments, so implementation snapshots need no external `.lean` fixture or owner path. They refresh inner receipt and outer public/input/report hashes before changing operators, operand order, slots, return types/references, source commitments, extracted evidence and authority flags. They also cover native ID populations, missing/unsupported dispositions, teacher substitution, original and nested-copy drift, budgets, late copy growth and output-scope protection. These fixtures are codec controls, not a new numerical or FINAL evaluation.

## Frozen source-bound feature vocabulary coverage

`codebase_ir_native_feature_coverage.py` independently projects every scalar atom in the two already captured source-bound feature exports onto their unchanged vocabulary. It records exact JSON paths, scalar types, values and counts before measuring vocabulary omissions and identical count signatures. It does not decode checkpoint state, replay the native feature numerical route, apply normalization, run a model or execute source.

```sh
python3 qualification/codebase_ir/corpus_audit/codebase_ir_native_feature_coverage.py \
  --manifest artifacts/codebase_ir_parallel_qualification/corpus_audit/native-feature-coverage-input-20261003-01/native_feature_coverage_input.json \
  --output /tmp/codebase-ir-native-feature-coverage
```

The closed `codebase-ir-native-feature-coverage-input@1` input contains exactly `schema`, `provenance_input`, `parent_export` and `child_export`. Each descriptor requires a canonical absolute path, exact raw SHA and exact `size_bytes`. The original captured provenance manifest independently joins both export selectors, raw hashes and version labels. The child must retain the parent's complete feature basis, and that basis must equal the independently enumerated parent training atoms. All earlier qualification modules, fixtures, reports and FINAL locks remain unchanged.

The `qualification/source-bound-scalar-feature-basis-coverage@1` profile derives one-Int-parameter arithmetic literal labels from exact source, separately checking raw native declarations, literals, ordered references, return/CFG population and UTF-8 byte spans. It reconstructs the source target's positional feature view, retaining unknown `any` sorts and the native reference labels that remain inside effect/order fields. Missing source profile support is explicit and preserves the target and its unknown-sort inventory. Source provenance and spans remain retained outside the feature expressions; their removal from the scalar vocabulary is reported as a projection loss. This is structural accounting under declared annotation assumptions, not a source/runtime theorem or a new native decoder.

The [retained coverage ledger](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/native-feature-coverage-retained-20261003-02/native_feature_coverage.json) binds the captured parent export SHA `8c436a2cc3f6467e8b06b5548c2136e7b5749aad07785a7e6ad2575421f80758` and child SHA `292c11b048348f23a825a530349cd784646a21e857799f13adc19cce760856af`. Nine original targets retain train/tune/canary/replay roles across four exact source literals: `1`, `2`, `3`, and `5`. Both exports have the same 53 columns, SHA `c6c2fa94c3f0b04f691c8860dff61ad5f4a6ba1e51ce169c5cbf74af1ffc86c8`. Each target contains 53 scalar atoms. Five target observations lose one literal atom each: values `2`, `3` and `5` have no corresponding column and therefore share the same 53-column count signature across train, tune and canary. Four observations of literal `1` retain all atoms. Eighteen native expression `any` sorts remain unknown.

This fixed-basis indistinguishability is a scoped representation fact. It measures neither learned predictions nor quality gains, and it establishes no new exposure independence, numerical provenance or production acceptance. Native contract identity claims remain separate from the canonical contract-body hash because their producer identity recipe is not independently qualified. Recorded historical training effort remains separate from the auditor's zero additional training, and no historical target receives a new FINAL role.

`native_feature_coverage.json` uses `codebase-ir-native-feature-coverage@1`; its raw bindings include the outer manifest and all three selected inputs. Four captured files, 1 MiB per file, 4 MiB total, 64 targets, 4,096 columns and 4,096 scalar atoms per projection bound the reader. Descriptor sizes and remaining budgets constrain allocation before reads; originals and retained copies are checked again after comparison. Thirty-two authored controls use embedded inert fragments, including coherent source/literal/operator/operand/span/projection forgeries, fixed-basis changes, unknown-sort omissions, exact Boolean/integer distinctions, unsupported source outcomes, multibyte offsets, detached raw pins, budgets, aliases, protected output scopes and late original/copy drift. Copied implementation tests need no owner paths or external fixtures.


The independent frozen-feature separation diagnostic (`codebase_ir_feature_separation.py`) consumes the exact prior native coverage input and retained-02 report, plus their pinned export and retained-copy bodies. Run it with `--manifest` and `--output`; the closed manifest schema is `codebase-ir-feature-separation-input@1`, and the output is `feature_separation.json` (`codebase-ir-feature-separation@1`). The selected input is retained at `artifacts/codebase_ir_parallel_qualification/corpus_audit/feature-separation-input-20261003-01/feature_separation_input.json`, with its actual report under `feature-separation-retained-20261003-01`.

All nine historical source labels and original train/tune/canary/replay roles are rederived, along with the immutable 53-column scalar counts. An exhaustive eight-subset search over the three existing missing literal columns finds three minimum two-column proposals, with a deterministic canonical tie-break. A separate three-column proposal covers all missing atoms in this cohort. These proposals exist only in diagnostic count signatures: captured feature spaces, checkpoint tensors, normalization and optimizer state are unchanged. Selection reads every historical role and is explicitly diagnostics only, with no held-out or training-only selection claim.

Authored source-only literals 4 and 6 remain indistinguishable under both proposals. They are separate counterfactual witnesses, with no native observations, model predictions or FINAL assignments. Eighteen native `any` sorts remain unknown, and the 54 original source spans remain absent from feature expressions. No feature recipe execution, source runtime equivalence, model quality improvement, complete exposure, decoder qualification or promotion is established.


Feature-separation generation 02 adds a final bounded output population fence immediately before report publication. The output root must remain a canonical nonsymlink directory containing exactly the ten retained input copies, with no directories, extra files, precreated report or nonregular members. Source and retained-copy rereads precede this fence. The current actual report is under `feature-separation-retained-20261003-02`, with validation under `feature-separation-validation-20261003-02`; generation 01 report and validation remain historical, byte-exact artifacts. Six additional controls reach the final guard and inject unexpected files, a precreated report, an extra directory, an expected-member symlink, an aliased root or a nondirectory root.


## Retained resumed source cohort and exposure accounting

`codebase_ir_resumed_cohort_audit.py --manifest INPUT --output OUTPUT` independently receives the pinned completed scan through the public inventory-resume review and native generation14 result. It reads only the 595 explicitly declared source-artifact CAS bodies and 14 scan CAS bodies, with raw CID/SHA/size pins, bounded acquisition, unchanged originals/copies and an exact output population fence. DBs, checkpoint bodies, keys, `.git`, live repository recovery and owner execution are outside this reader.

The retained cohort accounts for 300 ordered members and ten complete pages: 205 inferred, 89 budget-deferred, two unsupported targets, two opaque members, one parse failure and one unindexed member. Exact source bytes are available for 298 members; 297 captured AST records reconcile with source/revision bindings, reference and symbol spans, and independent syntax. The missing non-UTF8 source body and oversized member without a source CID remain explicit.

Independent syntax yields 293 normalized AST groups and three exact clone groups. `bulk000.py` shares syntax with the declared training path `calc.py`; `bulk100.py` shares syntax with the tuning path `tune.py`; `bulk102.py` shares syntax with the canary path `canary.py`. These are exposure relationships, with no heldout-independence claim. Constant-type-masked templates and source import edges are separate conservative syntax diagnostics.

The two retained lineage exports each declare only `calc.py` for training, `tune.py` for tuning and `canary.py` for canary monitoring. The child replay and ancestral training binding for `calc.py` reconcile with the retained root selection. Two inherited setup epochs and zero new fitting epochs/pages remain recorded historical claims. Scanning or retaining 300 members does not imply training on 300 members, complete pretraining exposure, independent evaluation, learned decoder quality or runtime semantics.

The fresh `resumed-cohort-input-20261003-01/resumed_cohort_input.json` and `resumed-cohort-retained-20261003-01/resumed_cohort_audit.json` preserve all prior corpus bodies and FINAL locks. The new 40 synthetic controls use no owner fixtures; repaired CAS/outer declarations still refuse forged source references, swapped role batches and stale page ancestry. Late original/copy drift, output root aliases and extra population members are also refused. The complete corpus suite has 399 tests, and the copied implementation runs all 40 focused controls from `/tmp`.


### Source successor syntax and historical content exposure

`codebase_ir_source_delta_analysis.py --manifest INPUT --output FRESH_DIRECTORY` receives the closed `codebase-ir-source-delta-analysis-input@1` profile and emits `source_delta_analysis.json` (`codebase-ir-source-delta-analysis@1`). Seven frozen outer metadata pins join the recorded source-delta, independent audit, ignored-file control, original failed attempt, and sealed joined-09 historical cohort/result. Only manifest-declared source and AST CID bodies are retained; owner modules, databases, checkpoints, keys and model envelopes are excluded.

The retained 300-to-300 successor has 302 union members: 297 retained entries, one changed entry, two additions and two removals. Exact byte comparison finds 295 equal pairs and one different pair. All 295 comparable captured AST identities change with snapshot provenance, while independent source syntax remains equal for 293 pairs and differs for one. Parsed sources carry independently reconstructed names, reference contexts, signatures and byte spans; unavailable/failed/unindexed inputs remain explicit. Clone/template groups, six cross-path byte matches and four syntactic import edges describe this bounded cohort. Cross-path equality does not establish a rename or authorize reuse.

Ten previous/current member records match already sealed historical source hashes with recorded train/tune/canary/replay declarations. These content matches transfer no role, ancestry or exposure qualification across repository/head contexts. Current exposure remains unknown for all 300 current members. The two affected head bindings are old/current source contexts, not two certified models. Model/proof dependencies and numerical reuse remain unavailable. The ignored-file control preserves the captured bytes and the original failed observation without certifying physical absence or replaying live presence.

Reads reserve at most 1024 original files and 64 MiB for original/copy bodies before allocation; source bodies are at most 64 KiB, AST bodies 128 KiB, sides 512 members and union 1024. Fresh outputs have a closed regular file population with exact source/copy/report rereads and a stable canonical directory. Synthetic tests exercise coherent CID/digest repairs, historical role/source forgeries, typed counts, missing/unsupported evidence, bounded allocation and reachable late file/root drift. No source/native/model execution, training, FINAL assignment, semantic truth, held-out quality or promotion is claimed.


### Source-successor prefix and child selection declarations

`codebase_ir_successor_cohort_audit.py --manifest INPUT --output FRESH_DIRECTORY` receives `codebase-ir-successor-cohort-audit-input@1` and emits `successor_cohort_audit.json` (`codebase-ir-successor-cohort-audit@1`). The frozen input is `successor-cohort-input-20261003-01/manifest.json`; `successor-cohort-retained-20261003-01` retains the first actual diagnostic. Eighty explicit inert bodies were acquired before implementation, with repeated original and retained-copy raw checks. No owner databases, model/training envelopes, optimizer states, keys or undeclared CAS children are opened.

The two separate roots declare the same ordered 300-member population. Their optimized/reference prefixes observe the same 32 unique paths, each with 22 inferred, nine budget-deferred and one unindexed entry. The other 268 members are outside these prefixes. The captured returned vectors and advisory coverage reconcile across the two pages without reexecuting inference or certifying numerical correctness. Thirty-five selected paths have 35 exact source bodies and 34 AST bodies. Source references, symbols, positional signatures and UTF-8 byte spans are reconstructed independently; source-only arithmetic labels retain annotation assumptions and unsupported dispositions.

The small inert registry export declares only the child request's `calc.py` training, `tune.py` tuning and `canary.py` canary paths. None shares exact source bytes or normalized AST syntax with a prefix path. Ninety constant-type-masked template pairs are separate syntax diagnostics, with no role or exposure equivalence. Root training selections, ancestral replay and complete pretraining exposure remain unavailable. Model, state and target digests remain recorded declarations; no optimizer continuity, learned quality, held-out independence, numerical reuse or model promotion is established. The successful attempt's two setup epochs and the failed initial attempt's two epochs remain distinct historical claims; this reader performs zero training.

The excluded 1,421,504-byte structural manifest prevents independent verification of the original semantic snapshot/entry schemas. Selected AST records require the exact official AST schema; no entries are regenerated to fill that gap. Reads reserve at most 128 originals, 256 total retained files and 8 MiB of original/copy bodies, with a 128 KiB input, 1 MiB metadata bodies, 64 KiB raw sources, 128 KiB AST bodies and a 4 MiB report. Late original, retained-copy and report rereads plus exact canonical output population guards precede successful completion. Embedded controls need no owner fixtures and run from a copied implementation. All prior fixtures, reports, modules and FINAL assignments remain unchanged.


### Complete successor page cohort and snapshot metadata

`codebase_ir_full_successor_cohort_audit.py --manifest INPUT --output FRESH_DIRECTORY` receives the closed `codebase-ir-full-successor-cohort-audit-input@1` profile and emits `full_successor_cohort_audit.json` (`codebase-ir-full-successor-cohort-audit@1`). The new `full-successor-cohort-input-20261003-01/manifest.json` freezes 42 explicitly selected inert metadata bodies before implementation. Its actual report is retained at [full-successor-cohort-retained-20261003-01](/home/barberb/lift_coding/artifacts/codebase_ir_parallel_qualification/corpus_audit/full-successor-cohort-retained-20261003-01/full_successor_cohort_audit.json). This separately qualified scope leaves the earlier prefix receipt and its unavailable snapshot-schema observations unchanged.

The default route now accounts for all 300 ordered captured members across ten pages: 205 inferred, 89 budget-deferred, two unsupported targets, two opaque members, one parse failure and one unindexed member. Two parent pages precede eight pages recorded by four distinct fresh-process receipts. Every page's membership, contiguous indexes, predecessor, returned row population, advisory coverage and completion CID reconcile independently. The reference route still supplies only one 32-member page. Its first-page entries, coverage and exported vectors equal the default route's first page; no full reference scan, all-member numerical inference or throughput qualification is established.

Both complete 300-entry structural manifests are independently received under an explicit 2 MiB per-manifest exception. Exact `semantic-repository-snapshot@4`, `semantic-snapshot-entry@3` and structural-unit schemas, entry/snapshot/manifest CID preimages, raw path declarations, coverage counts and complete current-root membership reconcile. Their 302-member source-delta metadata ledger retains 297 entries, changes one, adds two and removes two. Its declared source/AST CID comparisons preserve opaque and missing frontiers. No raw source or AST body is opened to certify byte equality, source correspondence or operational meaning. The embedded semantic-index container and its 590 symbol, seven edge and five artifact counts remain inert metadata; the semantic state's separate native identity recipe is unverified.

The child request's original `calc.py` training, `tune.py` tuning and `canary.py` canary declarations now lie inside the complete default page population, each with a recorded inferred disposition. Their roles are preserved. Independently recorded root tune/canary bindings refer to the previous source head; child bindings refer to the current head. Complete training/replay populations, optimizer state, numerical correctness, prior exposure and dependency/revision closure remain unavailable. Two inherited setup epochs and zero new fitting epochs during expansion are retained historical declarations, separate from the auditor's zero training. No source becomes FINAL, no model is selected or promoted, and no production task is closed.

The reader reserves at most 128 selected originals, 256 original/copy files and 16 MiB of original/copy bodies, with a 128 KiB input, 2 MiB snapshot manifests, 1 MiB other metadata bodies and a 4 MiB report. Original/copy/main-report rereads and stable canonical output-directory population checks close publication. These are ending per-file observations, not an atomic whole-repository capture or process-origin attestation. The standalone controls embed only inert metadata, check repaired typed-protocol forgeries and reachable late drift, and run from a copied two-file implementation without owner fixtures, databases, models, Git, source execution or production imports. All 110 previously captured corpus qualification bodies remain exact, with only this top-level README receiving an appended suffix.


## Retained scalar trace and declared source-symbol bindings

`codebase_ir_trace_binding_audit.py` joins the retained
`tla-counterexample-replay-qualification-20261003` metadata without importing its
production parser or rerunning a checker. Its closed input generation selects
exactly 17 metadata bodies (1,551,335 bytes): qualification, current native
result/lifecycle/fixtures/requests, two preflight generations, the historical
artifact-payload native result, complete initial/selected/joined regression
results and JUnit inventories, the initial failure log, source-evolution
metadata, and the producer report. Paths named inside those bodies are inert;
source bodies, checker files, native workspaces and their ancestors are not
followed. The fixed qualification/current-native/historical-native raw anchors
prevent changing the admitted original generations merely by rewriting a
manifest digest.

The independent grammar projects only `StateN` records with scalar assignments
of the form `symbol = literal`, bounded decimal integers, `TRUE`/`FALSE`, or
JSON-quoted scalar strings. Original labels such as `State0`, `State1`, `State2`
remain distinct from positive ordinal indexes `1`, `2`, `3`. Assignment strings
`0`, `1`, `2` are preserved exactly. Comments and stored raw state slices are
reconciled; named definitions/footer lines terminate a state block without
being evaluated. Expressions, duplicate assignments/labels, missing literals,
unsupported headers/block syntax, unterminated comments and unsupported comment
suffixes remain explicit parser frontiers. There is no general TLA expression
evaluator, transition execution, invariant reevaluation, fairness or liveness
claim.

The report covers 16 trace slots: two current native cases, two historical
native cases, and six static slots in each preflight generation. Fourteen have
trace objects; the two valid native cases have no counterexample. The total of
23 recorded parsed-state observations counts retained instances, not distinct
trajectories or independent solver runs. Three historical zero-state receipts
retain their original `replayed=true` flags and notes even though their raw
`State0`/`State1`/`State2` scalar blocks can now be projected independently. The
current invalid case's three stored states are joined to retained native output,
typed receipt/witness, raw digest, recorded three-step argv, and declared map
rows. `n` maps to the declared variable ID `variable:counter:n`; `Safety` remains
a nonassignment property declaration. These declarations are not authenticated
semantic source bindings. The unmapped negative retains its failed replay note
but lacks the original mutated map artifact, so original map absence is only a
reported declaration and is not independently replayed.

Complete JUnit IDs preserve the failed initial duplicate-diagnostic trial
(605 cases: 604 passed, one failed), its corrected selected trial (605 passed),
and the joined selected trial (2,089 passed). Each inventory has 74 trace replay
cases. The focused populations are identical and overlap the joined inventory;
these counts are not summed. Source-evolution rows are reconciled only as
retained digest declarations. Generic backend projections remain `UNKNOWN`,
and the retained typed `SATISFIED`/`VIOLATED` results do not promote generic
proof authority. No native/checker execution, production activation, source-map
semantic truth, producer authentication or additional production task closure
is claimed.

Input schema: `codebase-ir-trace-binding-audit-input@1`; report schema:
`codebase-ir-trace-binding-audit@1`. The manifest has only `schema`,
`fixture_origin`, and `selected_files`. Ordered roles are `qualification`,
`native_result`, `native_lifecycle`, `native_fixtures`, `native_request`,
`preflight_initial`, `preflight_selected`, `historical_native_result`,
`focused_initial_result`, `focused_initial_junit`, `focused_initial_log`,
`focused_selected_result`, `focused_selected_junit`, `joined_selected_result`,
`joined_selected_junit`, `source_evolution`, `report`. Each descriptor has only
`role`, absolute canonical `path`, typed `size_bytes`, and raw `sha256`.
The main report binds `selected_manifest_sha256` and these exact ordered
`selected_files[i].sha256` values. All 29 execution/semantic/authority scope
flags are literal false; its eight accounting flags are literal true and its
three additional-work counters are typed integer zero.

A successful output has exactly 19 regular files and one `inputs` directory:
17 raw selected copies, `input.json`, and `trace_binding_audit.json`. The reader
opens only these 37 distinct bodies (original manifest and 17 originals plus
19 output files), rejects physical aliases, and retains each initial inode,
size, modification/change times and raw bytes. Original and copied bodies and
the exact physical output population close twice after publication. These
rereads do not constitute an atomic filesystem snapshot. The per-body limit is
1 MiB, the manifest 128 KiB, the report 4 MiB, aggregate reservations 8 MiB,
maximum 64 body reservations; the scalar trace limit is 65,536 bytes, 128 states,
4,096 bytes per state and 32 assignment statements per state.

The retained example is
`artifacts/codebase_ir_parallel_qualification/corpus_audit/trace-binding-retained-20261003-01/trace_binding_audit.json`
(38,996 bytes; SHA256
`511813caf9140405448b8d92ec620d8183163ef2eb6c29f667253266fd08d7e9`).
Its input manifest is the sibling `trace-binding-input-20261003-01/manifest.json`
(5,696 bytes; SHA256
`0de4710f8e26822a8fc0b0958538879ac616d8651ff62d6d93bbe6ca1e06ad02`).
Acquisition froze all originals and copies before code edits and preserved the
prior full corpus bodies plus this README's original 97,805-byte prefix.

```sh
PYTHONHASHSEED=0 python qualification/codebase_ir/corpus_audit/codebase_ir_trace_binding_audit.py \
  --manifest /absolute/path/to/trace-binding-input-20261003-01/manifest.json \
  --output /absolute/path/to/fresh-output
PYTHONHASHSEED=0 python -m unittest discover \
  -s qualification/codebase_ir/corpus_audit \
  -p test_codebase_ir_trace_binding_audit.py
```

The 102 portable controls carry compressed inert metadata, never import owner
implementations, and exercise repaired raw joins, parser frontiers, typed
counts, historical gaps, overlapping complete test inventories and both
publication fences. A copied module/test pair runs from `/tmp` with empty
`PATH`/`PYTHONPATH`. Guards separately restrict the copied receiver to the 37
explicit original/output paths and prohibit process/network/owner imports.


## Retained publication dependency audit

`codebase_ir_publication_dependency_audit.py` receives thirteen fixed selected
inputs from signed successor worker08 and the private machine review captured
by the tenth-lane preflight. It implements
`audit(manifest_path, output)` and the standalone
`--manifest PATH --output PATH` command. The input schema is
`codebase-ir-publication-dependency-audit-input@1`; the report schema is
`codebase-ir-publication-dependency-audit@1`. The report binds the original
manifest SHA and all thirteen ordered originals and retained copies.

This is the publication from source generation2 to generation3. Both captured
inventories contain300 entries and300 structural units,296 successful Python
parses, one failed parse, one unindexed artifact and two opaque entries. The
complete semantic containers have590 symbols, seven edges and five artifacts.
Manifest, snapshot, entry and the two selected AST content CID recipes are
independently derived from their retained bytes.

The audit keeps three change populations separate. Exactly `calc.py` changes,
while299 entry records are identical.297 AST identifiers and unit records
change; only the unindexed artifact and two opaque units remain identical.
296 unchanged source entries therefore have changed AST identifiers. The audit
opens only the two selected `calc.py` AST bodies, so the cause of the other296
AST identifier changes remains unknown.588 semantic symbol records remain
identical. Both `calc.py` symbol records change their source CID, and only its
function version CID changes; the module version CID is preserved.

Independent stdlib AST parsing of the two archived source bodies verifies the
syntactic operand change from `n + 2` to `2 + n`, the retained function and
parameter population, references, signatures, and byte/line/column spans. It
never executes or imports either body and makes no behavioral equivalence,
difference, source intent or public-check claim.

All seven declared dependency edges remain identical. Four definite incoming
call/import edges connect the changed function's stable ID to the two public
check module IDs. A bounded reverse traversal derives that finite declared
frontier. Three unresolved lexical/global edges stay explicit. The audit
joins the inherited300-member scan root and completion to generation2, and
reconciles their differing head identity with publication generation3 and the
retained exact `StaleCodebaseError` observation. It performs no new scan or
runtime stale-head replay.

The source catalog's revision2-to3, source-file594-to891 and invalidation1-to2
counts are retained metadata observations. Native rows, DB bodies, model
bodies, keys, opaque bodies and Git objects are not opened. The native
invalidation completeness, semantic-index/stable-symbol identity recipes,
dependency semantics, full transitive dependencies, physical published
worktree, process origin and all32 production acceptances remain unqualified.
The prior full300/default and32/reference qualification is inherited metadata,
not fresh scan execution.

The reader uses closed typed JSON, exact physical selected file identities,
SHA and size checks, two complete publication closing fences and an exact
output file/directory population. Caps are4MiB per body,16MiB aggregate,
128KiB manifest,4MiB report and128 selected files. The standalone copied tests
embed the inert selected fixture and exercise repaired structural metadata,
source spans, allocation boundaries, symlink/hardlink aliases and late
original/copy/manifest/report replacement or extra output members. The actual
copied receiver read guard uses empty PATH/PYTHONPATH; the inherited whole
corpus regression uses the ordinary PATH for its previously authorized private
synthetic Git fixtures. These are separate validation scopes.
