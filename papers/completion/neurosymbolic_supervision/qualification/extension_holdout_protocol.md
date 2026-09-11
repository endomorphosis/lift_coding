# NS-015 independent holdout protocol for optional extensions

Status on 2026-09-11: this is the independent protocol that any *retained*
procedure, world-consumption, or refactoring extension would have to satisfy.
NS-015 retains **no** such extension. The protocol is therefore the reopening
condition and the leakage/authority boundary, not a currently executed
experiment.

The earlier NS-002 capability record describes its sealed Python profile.
This checkpoint performs source review only and does not retest that profile
or execute an extension. A future retained extension must qualify its actual
validation environment and record current commands, versions and outcomes.
NS-014's unavailable native-proof qualification remains unchanged; CLI help,
imports or key files are not proof evidence.

## 1. Retention gate (fail-closed)

An extension may be retained only when all of the following are true:

1. An actual implementation is located under a digest-bound path whose
   identifier matches the claim. A nearby similarly scoped module is not a
   substitute (`ProcedureCegis` ≠ `FormalAssuranceCegis`; incoming memory ≠
   deterministic failure memory).
2. This protocol's holdout, control, isolation, and rollback rules are bound
   before any evaluation.
3. Consumed-result evidence exists: a verified pre-state, an admitted action,
   independent validation, and an accepted or rejected post-state. Sidecar
   logging, snapshot queries, and mutation-free world views do not count.

If any gate fails, the extension is `untested` / `out of scope` / `future work`.
Missing evidence is recorded as `null` with a reason, never as zero success.

## 2. Isolation: training and synthesis cannot inspect final acceptance

Before any training, anti-unification, or synthesis:

- Freeze the operator/task family, source forest, capture/abstraction
  profiles, and family/time splits.
- Hide target patches, acceptance oracles, and final holdout labels from
  proposal generation, training, and synthesis.
- Generated tests may supplement but may not silently replace the hidden
  oracle.
- Split identity, scorer identity, and oracle identity are recorded in the
  extension receipt *before* the first evaluation attempt.

A later protocol change that exposes holdout labels to training is a new
revision, not a silent reuse of this protocol.

## 3. Holdout construction

Use **both** of:

- **Family holdout.** Repository/task families used for mining, anti-unification,
  or training are disjoint from families used for final applicability and
  downstream-repair scoring.
- **Time holdout.** Trajectories admitted after the freeze instant are
  evaluation-only.

Do not mix observed, synthetic, and static-derived examples without labeling
them. Valid alternatives are distinct from wrong predictions. Required
holdouts that cannot be formed (as in PGIR-014's compiler, domain, lineage,
time, and related splits) close the learned claim rather than shrinking the
split after outcomes.

Pilot or developmental tasks are labeled and excluded from final holdouts
(NS-016). This protocol does not create those tasks.

## 4. Controls that must remain visible

Every retained evaluation reports, and does not drop from denominators:

| Control | Role |
|---|---|
| Static | Type, import, alias, effect, and contract pruning. Uncertainty is not exclusion. |
| History | Independently admitted trajectories and rejected episodes (negative memory). |
| Lexical | Token/string baselines. |
| Embedding | Similarity may nominate; it never substitutes for exact subject resolution. |
| Template | Built-in or previously verified procedures before model sketches. |

Report candidate recall before ranking, top-k, calibration, abstention,
unsupported cases, replay validity, and **downstream repair/usefulness**.
Model scores, attention weights, proximity, and generated CIDs are not
facts, certificates, or required evidence.

## 5. Applicability, abstention, bad predictions, rollback

Execution of a retained procedure or world transition must recheck **current**
applicability and authority. The following remain first-class visible
outcomes, never recoded as success or omitted:

- applicability failure
- abstention
- bad prediction / wrong residual
- independent-validation rejection
- rollback, including rollback cost in the declared resource units
- unavailable backend or missing frozen artifact (`null`, not zero)

Negative memory persists failed applicability, counterexamples, and migration
costs so the same rejected pair is not silently re-promoted.

## 6. Consumption modes (not interchangeable)

World / program-world rollout is:

`bootstrap → shadow_write → shadow_read → guarded → required`

These are distinct from W3 sealing gates
(`shadow_hash → shadow_reuse → shadow_proof → protected → required`) and from
refactor/procedure promotion (`candidate → independent qualification →
shadow use → policy-authorized promotion`).

| Mode | What it may do | What it does not establish |
|---|---|---|
| `shadow_write` | Write sidecar artifacts | Authority change; task completion; Table 18 consumption |
| `shadow_read` | Score hypothetical decisions | Influence on behavior; required self-hosting |
| `guarded` | Bounded consumption under independent checks | Required-mode completion; worker-chosen promotion |
| `required` | Consume verified pre-root; publish observations, validation, accepted/rejected transition, post-root | Nothing unless those artifacts are actually observed |

A deployment that writes optional semantic metadata while continuing to
decide from raw prompts has not demonstrated required self-hosting.

Workers may not modify rollout, keys, protected specifications, or their own
acceptance validator. No worker self-promotion. Guarded and required
consumption require separate approval from shadow modes.

## 7. Independent validation and rollback

Validation is a different owner from synthesis:

- The synthesizer neither executes nor certifies nor promotes its output.
- Independent scoring is cold with respect to proposal generation.
- Rollback is exact and costed; a failed applicability or rejected partition
  is retained.
- Public API, mutable-state, security, legal, payment, key, release-authority,
  and wire-protocol changes keep their human-approval ceilings. Learned
  benefit or lower context cost cannot raise those ceilings.

## 8. What this protocol does *not* run in NS-015

Because no extension passed the retention gate, this task does **not**:

- train or evaluate a learned world/procedure/graph model
- synthesize or promote a `ProcedureCegis` operator
- consume a required-mode pre-root or publish a post-root
- execute remodularization, CST/AST relinking, or SCC partition rewrites
- inspect final A–D acceptance outputs for training
- block the planned core evaluation (NS-007–NS-013 and the four core Table 18 rows)

Reopen only by satisfying Sections 1–7 on a bounded operator/task family and
recording paired consumed pre/post evidence under this isolation rule.
