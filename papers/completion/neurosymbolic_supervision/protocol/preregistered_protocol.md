# NS core comparison preregistration v1

This is the NS-004 protocol specification, frozen as a content-addressed bundle
before any final observation. `experiment_manifest.json` contains its version,
the hashes of this document and `measurement_schema.json`, and a canonical
bundle hash. NS-016 must additionally freeze actual data, scorer, runner, model
identity, dependency forest and resource admission in `final_experiment_freeze.json`
before NS-017/018 dispatch. This specification is complete; final execution is
not yet ready. None of the counts below is an observed result.

The scientific scope is the NS-003 ledger at source commit
`43f60dac61e35f9bc6ccf2b7fa39c73d797b2b08`. NS-004 does not narrow the paper goal,
remove the required live comparison, change the acceptance oracle, or certify
any empirical Table 17/18 cell. Missing prerequisites retain their native owners.

## Questions, arms and matching

Evaluate bounded genuine historical **one-proposal repairs** under a common
independent acceptance oracle. A task starts from its exact pre-fix snapshot;
no arm sees a target patch. One proposal is a declared budget for this study,
not a claim about unrestricted multi-turn agents. Nontrivial live residual
repair must occur in the pilot and final population; a no-call or deny-all
experiment cannot discharge the core obligations.

| Arm | Proposal context and control | Validation/publication |
|---|---|---|
| A | Visible issue/specification, raw source and deterministic lexical retrieval | Full selected validation; common independent cold scoring |
| B | Same visible information, deterministic source-linked semantic pack | Exactly A's validation and scorer |
| C | B plus obligation-aware routing and qualified lifecycle-bound test/proof reuse | Only covered unchanged obligations may reuse; unknown coverage falls back to the same full validation |
| D | C plus governed claim/evidence lifecycle and parent-bound publication/recovery | Same acceptance standard; solved additionally requires an admitted current-parent publication receipt |
| C-no-route | C with only obligation-aware routing disabled | All other C settings preserved; residual proposal route uses the common model |
| C-no-reuse | C with only reuse disabled | Cold full validation, with C routing and context unchanged |

The four A--D conditions measure package effects. B/A also isolates context;
C/C-no-route and C/C-no-reuse isolate those respective mechanisms. A C or D
package advantage never credits every constituent. All arms use identical
task IDs/preimages, model endpoint and returned identity, settings, scoped edit
permissions, visible test access, one-proposal budget, container image, CPU
allocation, elapsed limit and independent oracle. Context composition and the
declared factors are the only differences. Record both context size and
information coverage; A is not deliberately deprived of necessary source.

No arm may edit acceptance tests, the oracle, protected inputs or its budget.
Generated tests are supplementary only. Deterministic closure may count as
useful only when it computes a new task-valid solution on the admitted real
consumer and passes the same hidden oracle; retrieving an existing target
patch, replaying a fixture answer, or injecting an oracle patch is prohibited.
Every routing decision records consumed evidence IDs and its next actual action.
Unknown-frontier widening and fallback costs remain attributed to that arm.

## Population, splits and access

Plan 24 independent upstream repository-lineage families: four development,
four pilot and sixteen final. Use one genuine pre-fix issue/fix per family.
Forks, vendored mirrors and related derivatives form one family; the same
family cannot appear twice or cross splits. This is a planned recruitment
target, not a claim that 24 eligible tasks have already been found. NS-005 owns
the actual provenance, licensing/access review, near-duplicate checks against
all three papers and the 40 existing fixtures, source snapshots and exclusions.
The old 40 semantic fixtures remain qualification/preliminary data exclusively.

Before pilot outcome access, NS-005 records a finite candidate registry with
family IDs, issue/spec text, timestamps, pre/fix commits, language/dynamic class
and inclusion decisions. Eligibility requires a genuine documented bug, a
bounded Python repair surface, a valid unchanged regression suite and an
independently justified acceptance test that fails for the stated reason on
the pre-fix state and passes on a privately held reference fix. Compile failures,
missing dependencies and an empty suite do not satisfy this baseline check.
The reference fix demonstrates oracle applicability; it is never an arm answer.

Prefer a temporally later held-out fix within each designated final source
family, with no development exposure from that family. Freeze the candidate
registry, deterministic SHA-256 ranking and exact split/task IDs before final
outcomes; commit dates and prior model exposure are reported, not assumed
uncontaminated. No favorable task replacement or post-result exclusions.
If fewer than 24 eligible independent families are available, NS-016 may issue
a versioned pre-final design amendment supported by recruitment/feasibility
evidence; this v1 schedule is not silently relabeled. After final dispatch,
shortfalls are missing scheduled units, with no denominator reduction.

Proposal generation can read only the issue/specification, admitted pre-fix
source, public baseline tests and allowed tool output. Hold fixed target patches,
hidden tests, scoring decisions and oracle logs in a separate scorer principal
and directory that the proposal sandbox cannot mount or query. NS-005 documents
the oracle authoring/provenance and separation; NS-006 proves the interface and
leakage checks. The scorer receives the proposed patch and frozen preimage and
runs independently, without trusting an arm's `accepted`, `closes_claim`, or
queue-completion flags. Any hidden-oracle access is an incident retained in
the denominator and blocks promotion. No inferred human-independent reviewer.

## Repetitions, order and cache state

Final design: 16 families x 6 arms x 2 repetitions x 2 cache profiles = 384
scheduled live comparison units. A--D contribute 256; the two additional
ablation arms contribute 128. Both repetitions start from the same clean
pre-fix state with independent candidate state. Repetition labels are 104729
and 130363; these seed scheduling, not a claim that an unsupported provider
sampling seed is enforced. Development is 4 x 4 A--D x 1 cold repetition = 16
units. Pilot is 4 x 6 arms x 2 cache profiles x 1 repetition = 48 units.

For each family/repetition/cache block, order all six final arms by ascending
SHA-256 of UTF-8 `ns-core-v1|family_id|repetition|cache|arm`; break any tie by arm
name. Order blocks with the same rule and suffix `block`. Pilot uses a distinct
`ns-core-v1-pilot` prefix. Freeze the resulting schedule before final dispatch.
No outcome-based ordering, rescheduling a failed arm for a quieter period, or
unlogged retries. Each paired block uses one admitted served model identity;
a model/endpoint/settings change suspends dispatch and is a recorded deviation.

`local_cold` removes the arm's task-local semantic index, validation/reuse and
publication caches before setup. `local_warm` first builds the arm-specific
index and full visible pre-fix validation evidence on that exact snapshot,
then measures a fresh proposal. The deterministic prime contains no target
patch, hidden oracle output or prior arm solution. Prime costs and storage are
measured separately and included at the specified reuse horizon. Arm/repetition
cache namespaces never share answers. Provider-side cache state may be
uncontrollable: record actual cached tokens or unavailable, and describe these
profiles as local cold/warm, never universally cold/warm model inference.

## Live provider and resource feasibility

The retained implementation log proves an actual quota-guarded fallback to
OpenAI Codex 0.154.0, model `gpt-5.6-terra`, reasoning `high`, on 2026-09-11 at
17:45:48 UTC. It contains real tool reads and an interrupted implementation
attempt. It is **not** a benchmark repair result, remaining-quota reservation,
billing measurement, or qualification of the scientific runner. Its exact hash
and the observed host resources are retained in the NS-004 feasibility snapshot.
No provider call was made to write this protocol.

Proposed scientific model profile is that same Terra HIGH endpoint through
the existing authorized, quota-guarded native route. NS-006/016 must demonstrate
an actual bounded useful proposal on pilot-only data, capture the served model
identifier and all exposed revision metadata, and freeze CLI/runtime/image/source
hashes. Unsupported temperature/sampling-seed/max-token controls are recorded
as unavailable; they are not asserted set. If immutable weights are not exposed,
label matching as operational endpoint/alias/settings within the recorded run
window and explicitly disclaim exact-weight reproducibility. Never invent a
snapshot revision. Any disclosed identity change stops the paired block.

The native primary remains Grok with independently verified quota-only Codex
fallback. A scientific run may not bypass that quota gate to force Codex. If
the actual admitted provider differs from the frozen Terra profile, record
`unavailable:model_profile_mismatch` before a scientific call; an alternative
profile requires a pre-final pilot and versioned freeze, with no mixed-model
table silently pooled. Exhausted/unknown remaining capacity is a readiness
failure, not evidence that a no-call system saved model use.

Hard proposed allocation: one active NS scientific container, one reserved CPU
core, 2 GiB aggregate cgroup memory, 32 aggregate process/thread slots, 2 GiB
task scratch space, zero required GPU, and no new paid-provider/cloud spend.
Host observation found 20 affinity CPUs and ample memory; observation is not
a reservation. Root must admit this share alongside the other papers. Provider
remote compute is not charged as host CPU. No optional Groth16, learned model,
procedure or federation campaign is added to this budget.

Each unit allows at most one external proposal effect, 64 KiB serialized visible
request bytes (including tool/context wrappers), 16 KiB admitted patch bytes,
180 seconds provider wall time, 300 seconds total active unit wall time and
240 aggregate host CPU seconds. Provider reasoning/output token use is metered
when returned; bytes are not called token counts. NS-006 must prove stream/
process/container enforcement and record overshoot and unknown paid effects;
if a control cannot be enforced, pilot readiness fails. Frozen client controls
supplement rather than replace aggregate resource limits. Independent cold
scoring has a separate 120-second/120 CPU-second cap per unit and 2 GiB memory.
Timeout is non-success, not a valid rejection or an oracle pass.

All development, pilot and final units require at most 448 proposal effects;
reserve 64 additional explicitly registered NS-006 boundary-qualification units
before final freeze, for a hard campaign limit of 512 proposal effects. Quota
checks and retries are separately counted; any possibly dispatched effect
consumes a slot and is not replayed without native reconciliation. No scientific
unit gets a second proposal from that reserve. A required route without available
existing authorization/quota remains unavailable; no new billing is inferred.

The aggregate allocation is 60 host CPU-hours, 72 active elapsed hours, and a
20 GiB retained artifact cap for this whole study including priming, cold
scoring, setup, boundary tests and recovery. Limits are stopping ceilings, not
runtime estimates or available deadline time. A 448-unit ceiling at 420 seconds
including cold scoring is 52.267 serial hours before setup/qualification; at
360 CPU seconds it is 44.8 CPU-hours before those costs. NS-016 must use measured
pilot upper-tail costs plus remaining non-outcome-dependent work to check both
this allocation and actual time to the author packaging cutoff. If it does not
fit, issue an explicit pre-final amendment or leave the study not ready; do not
promise the current workshop deadline or prune bad outcomes after dispatch.

## Terminal outcomes, denominators and independent scoring

Every scheduled unit gets one record, including not-started units after a
global stop. Distinguish `solved`, `unsolved`, `rejected`, `abstained`,
`timed_out`, `unavailable`, `cancelled`, and `missing`. Record stage/reason,
dispatch/effect identity, admission and publication separately. An unresolved
provider effect is an unavailable/unknown-effect outcome with consumed budget,
preserved native history, and no claim of either no charge or useful repair.

Let S be all scheduled units for an arm/cache profile. Solved requires a
nonempty permitted patch or qualified computed deterministic solution, correct
preimage/scope, independent cold oracle pass, all mandatory current evidence,
and actual admission; D also requires current-parent publication. Report solved
/ S, raw counts by terminal state and dispatched solved / dispatched units.
The conditional rate is undefined when its denominator is zero. Rejected,
failed, timeout, unavailable, cancelled and missing units remain in S as not solved.

For independently scored candidates record: valid+admitted, valid+denied,
invalid+admitted, invalid+denied, and unscored. False acceptance is invalid+
admitted / all admitted **scored** candidates, with an additional scheduled-unit
count/rate. False denial is valid+denied / all independently valid scored
candidates. Separate admission attempts with missing scores and give worst-case
upper bounds by treating each unresolved admitted candidate as invalid; never
call them safe. Abstention without a candidate is not false denial. Report the
counts/denominators, not just percentages. Missing score/admission/publication
evidence blocks a positive claim, even if the process exited zero.

Prespecify per-family and dynamic-feature strata, but do not promote post-hoc
subgroups. Report time-to-first-independent-valid-solution (censored at the unit
cap), event-to-replan latency, invalidation/fallback/replan counts, churn, manual
interventions, cold-oracle reuse disagreement, recovery latency and useful
continuation. Unavailable endpoints remain null with an explicit reason.

## Quality, uncertainty and promotion

The primary package comparison is D versus A, separately for local cold and
local warm. B/A, C/A and ablation comparisons are reported as prespecified
secondary estimates, not additional opportunities to choose a winning primary.
No arm selection is based on final outcomes.

Report attempt-level solved counts and paired family-mean differences. For the
promotion quality gate, define robust family success as both scheduled
repetitions solved for that arm/cache; any missing or non-success repetition
makes that family's robust indicator zero. This deliberately stricter endpoint
is separately labeled and does not replace the Table 17 attempt denominators.
The noninferiority margin is **0.05 absolute probability** (five percentage
points) on this robust useful-completion endpoint. Minimum useful completion
is **0.25** robust family probability. These are tolerability/design thresholds,
not empirically calibrated effects or a power guarantee.

Use a conservative paired bound: for N=16 families let g count D-success/
A-failure and l count D-failure/A-success. For each cache profile use a one-sided
alpha=0.025 primary quality decision. Compute a Clopper--Pearson lower bound
L(g,N,alpha/2) and upper bound U(l,N,alpha/2); the quality lower bound is
L(g,N,0.0125)-U(l,N,0.0125). This union bound accounts for the two components
without treating repeated attempts as independent. Require this difference
strictly above -0.05. Also require the one-sided 97.5% Clopper--Pearson lower
bound for D robust successes to be at least 0.25. Cold/warm alpha splitting
controls the two opportunities for primary quality claims; requiring all
conditions within a claim is an intersection gate, not a new winning test.

Clopper--Pearson endpoints use beta quantiles, with L=0 at zero successes and
U=1 at N successes. For zero observed failures, report U=1-alpha**(1/N), with
the actual independent-family denominator and confidence level. Never use a
degenerate all-equal bootstrap as proof of exact equality or universal safety.
With 16 independent families, even zero events has a 95% upper bound about
0.1707; uncertainty can easily prevent a five-point noninferiority conclusion.
This bounded study offers estimation and falsification, not a guaranteed
significance/power result. If true independence/exchangeability of recruited
families is not defensible, label intervals conditional/descriptive and decline
population-level promotion.

For descriptive paired family-mean differences, medians and cost distributions,
use 20,000 percentile bootstrap resamples of whole family blocks, shared across
arms/repeats/cache profiles, with analysis seed 20260911; report 95% intervals
and raw distributions. Do not bootstrap individual repetitions independently.
The method and degeneracy warnings follow the [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).
Exact binomial interval semantics follow [R's binom.test documentation](https://www.stat.math.ethz.ch/R-manual/R-devel/library/stats/html/binom.test.html).
Software versions and quantile conventions are frozen in NS-016/019.

Promotion requires all of: the prespecified quality and usefulness gates, no
false admission/reuse in the relevant scored data or retained boundary tests,
positive authorized progress for all retained boundaries, no unresolved
acceptance/identity/leakage incident, complete required measurements, and an
efficiency advantage at a named measured resource endpoint after full costs.
Choose end-to-end active elapsed as the primary efficiency endpoint; require
its family-paired 95% bootstrap upper bound for D-minus-A to be below zero,
with costs charged at the stated cache/reuse horizon. Token/currency differences
are secondary. Bootstrap efficiency inference at N=16 is approximate and
must be labeled as such; robustness and complete raw results accompany it.
No quality pass, no useful progress, any unsafe admission or inconclusive
interval means **no promotion**. Retain null, negative and inconclusive findings.

## Full economics and amortization

Every cost observation carries `actual`, `estimated` or `unavailable`, units,
measurement source and reason. Unavailable values are null, never zero. Provider
input/output/cached/reasoning tokens are separate categories with the provider's
overlap convention; do not add cached tokens again when already in input totals.
Count dispatched calls, known/unknown charges and retries. Tariff-derived money
is estimated unless a billing receipt measures it; record currency, tariff/date
and discounts. Existing subscription access is not evidence of zero marginal
currency cost. Missing charges prohibit a measured currency-savings claim, not
the separately observed elapsed/token report.

Retain actual host CPU, GPU (or explicit not-used observation), peak aggregate
memory, bytes read/written/retained, directly observed active wall time, blocked
queue/human wait, and human active effort. Instrument indexing/context,
provider, fixture setup/call/teardown, proof generate/verify, persist/seal,
publication, retry/recovery and independent cold scoring. Record overlapping
stage intervals; sum CPU only with non-overlapping process accounting and never
sum parallel stage wall durations as end-to-end elapsed. Keep worker costs and
independent scoring costs both separately and in the total experimental bill.

Report local-cold setup cost S_j, measured warm per-use cost W_j and cold per-use
cost F_j in each resource separately. For horizons H={1,10,100,1000}, project
T_warm,j(H)=S_j+H*W_j and compare H*F_j; mark horizons beyond actual repeated
uses as estimates. Cross-arm totals include each arm's own setup and cold/warm
costs. If F_j>W_j and setup/usage are measured in the same units, break-even is
max(1,ceil(S_j/(F_j-W_j))), with the integer threshold checked directly; otherwise
state never/undefined as appropriate. Include invalidation/re-prime and storage
lifetime in any measured horizon. Do not claim long-horizon reuse from one
warm observation, amortize optional training away without measurement, or
combine dollars, seconds and tokens into an unannounced scalar.

## Boundary controls, freeze and ownership

NS-007--013 must qualify the real semantic consumer, positive provider gate,
loss-aware translation, full fixture lifecycle, false-reuse attacks and
parent-bound publication/restart/valid continuation before the final freeze.
Use sixteen final-family qualification blocks, each with one valid and one
invalid case for each of the four retained Table 18 boundaries (provider,
translation, fixture lifecycle, restart publication): 128 controlled boundary
cases, separately labeled and excluded from live repair denominators. Exact
instances and applicability are frozen by NS-005; missing valid progress is a
failure, not removable after outcomes. Mutations include lost modalities,
inconsistent assumptions, removed tests, missing fixture inputs, stale maps/
keys, changed verifier keys where applicable, unknown provider outcomes and
crashes before/after publication. Optional native/world rows retain the NS-003
untested/unavailable/future-work disposition unless separately qualified.

Deny-all, translation-check-disabled and other unsafe controls run only inside
the adversarial harness with publication and external effects disabled. They
cannot count as repair success. Parallel/sequential sealing replays the same
already-scored candidate and must preserve roots/dispositions; those replays
measure sealing overhead, not additional model repair. No procedure ablation
is claimed while the learned-artifact no-go remains. Every retained mechanism
has its isolated contrast or an explicit non-attributable limitation.

NS-016 admits final runs only after real pilot evidence and signed/hash-bound
data-access/scorer isolation, model/route identity, resource reservation,
measurement completeness and useful positive paths. Pin the actual schedule,
all hashes, scorer/analysis commands and limits before the first final unit.
Record authorizations actually observed without inventing consent. A pilot
amendment increments the version and records its reason before final data;
final outcomes never justify changing oracle, margins, thresholds or samples.
NS-017/018 execute; NS-019 independently rescores/reconciles; NS-020 reconciles
Tables 17/18 and claims; NS-022--025 own manuscript and author handoff. Completing
NS-004 closes this specification task only; unrun work remains required.
