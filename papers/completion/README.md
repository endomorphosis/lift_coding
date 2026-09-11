# VeriCodeGen 2026 paper completion program

Reviewed 2026-09-11. This program prepares **three independent
`ipfs_accelerate_py.agent_supervisor` implementation supervisors**, one per PDF.
Each has a root goal, subgoals, a dependency-ordered taskboard, a detailed review,
and its own configuration. Research tasks are open; creating these boards does
not establish experimental results. Supervisors have not been started.

| Paper | Review | Native goals and TODOs | Main text / total PDF pages | Main missing evidence |
| --- | --- | --- | --- | --- |
| Compiler-Guided Autoformalization with Adaptive Multi-View Representations | [Review](autoformalization/review.md) | [Goals](autoformalization/paper.objectives.md), [25 tasks](autoformalization/paper.todo.md), [config](autoformalization/supervisor.json) | 9 / 27 | 44 TBD cells across A–E source-to-proof and T0–T5 training matrices; independently judged fidelity, genuine proof transfer, actual training and consumer evidence |
| From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents | [Review](law_to_action/review.md) | [Goals](law_to_action/paper.objectives.md), [25 tasks](law_to_action/paper.todo.md), [config](law_to_action/supervisor.json) | 8 / 17 | Five “Not run” and three pending evaluation rows; corpus fidelity, actual protected effects, durable capability use, real solver/crypto/network integration |
| Proof-Carrying Neurosymbolic Supervision: State, Logic-Governed Decisions, and Test-Evidence Reuse | [Review](neurosymbolic_supervision/review.md) | [Goals](neurosymbolic_supervision/paper.objectives.md), [25 tasks](neurosymbolic_supervision/paper.todo.md), [config](neurosymbolic_supervision/supervisor.json) | 9 / 28 | 34 TBD cells, unfinished abstract/results/disclosures; live paired A–D experiments, provider receipts, cold-oracle test reuse, measured costs |

The 75 tasks sit under 22 subgoals and three root goals. Every task names its
paper evidence, dependencies, deliverables, acceptance criteria and candidate
implementation paths. Existing mocks, source inspections, estimates and dry-run
telemetry are explicitly separated from executed evidence in the reviews.

## Sources and supplied templates

The user supplied [this Overleaf project](https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0).
Access from this environment returned HTTP 403 on 2026-09-11. Its contents and
which manuscripts it contains remain unverified; no manuscript source was
downloaded. Each first task attempts authorized source recovery and can
reconstruct LaTeX from the PDF with a discrepancy audit. Independent code and
protocol tasks do not depend on Overleaf access.

[source_inputs.json](source_inputs.json) records hashes of the nine supplied
PDF/template inputs and review-time repository commits. These commits are
starting locations, not a claim that the dirty workspace is a frozen experiment.

The user also supplied these local **research-paper** inputs:

- [neurips_2026_vericode_workshop.tex](../neurips_2026_vericode_workshop.tex): manuscript shell.
- [neurips_2026_vericode.sty](../neurips_2026_vericode.sty): unmodified workshop style.
- [checklist.tex](../checklist.tex): 16 questions, with actual Yes/No/N/A answers and justifications to fill separately for each paper.

These are formatting templates, not the editable manuscripts. Use the research
package in default submission mode. The supplied competition variants follow a
different track and do not apply to these three research submissions. Preserve
the originals; each manuscript gets its own checklist copy. Default anonymous
author text produced by the official style is expected, and must not be
misclassified as an unfinished author field. Remove genuine draft result and
checklist placeholders in the completed manuscripts.

## Submission priorities and timing

The [workshop CFP](https://vericodegen.github.io/cfp.html), checked 2026-09-11,
lists tentative abstract and paper deadlines of September 11 and September 13,
2026 AoE, respectively (end of day AoE falls at noon UTC on the following day).
It requires 4–9 main-text pages, excluding references and appendices; anonymous
paper and linked artifacts; the official workshop template; methodology-relevant
LLM disclosures; and at most 50 MB PDF / 100 MB supplementary ZIP. The workshop
is non-archival. Recheck the live dates before author submission.

Each supervisor should start with source recovery and an independent
claim/code/environment audit, then freeze its smallest credible experimental
scope **before observing outcomes**. P0 marks submission-critical work; P1
supports fuller evidence. Dependency closure can bring P1 work onto a P0 path.
The full experiments are not assumed feasible before September 13. If a run
cannot finish, record the concrete limitation and remove or narrow its associated
empirical claim; never fill a result cell with an estimate or fabricated value.
An unrun experimental obligation is not marked completed merely because it is
documented. Record scope changes explicitly in the paper's claim matrix.

The three lanes can run in parallel:

1. **Autoformalization:** recover/audit → freeze independent annotations and splits
   → validate real training/proof adapters → run A–E and T0–T5 comparisons plus
   bounded ablations → analyze genuine transfer and cost → complete manuscript.
2. **Law to action:** recover/audit → freeze legal/CVE/skill cohorts and labeled
   cases → qualify real effect-observing handlers and durable enforcement → run
   matched fixed-action and closed-loop comparisons → analyze safety, utility and
   cost → complete manuscript.
3. **Neurosymbolic supervision:** recover/audit → pin the loaded repository forest
   and independent cold oracle → qualify provider admission, reuse and recovery
   → run paired A–D comparisons and isolated ablations → analyze actual model,
   proof and execution costs → complete manuscript.

Each lane ends with an independent reproduction and anonymous submission
package. Authors retain abstract registration, submission, review consent,
authorship/funding facts and final scientific sign-off. These boards authorize
preparation, not messages to organizers or an OpenReview submission.

## Native supervisor integration

The canonical implementation lives at `external/ipfs_accelerate`, with datasets
and kit dependencies under `external/ipfs_datasets` and `external/ipfs_kit`.
The older nested checkout under `hallucinate_app` is not the launch source.

From the repository root:

```bash
python3 scripts/paper_supervisors.py validate
python3 scripts/paper_supervisors.py commands
```

`validate` imports the actual native goal/task parsers and supervisor CLI/config
builder. It checks task and parent DAGs, goal membership, namespaces, outputs,
reviewed acceptance criteria, template inputs, and isolated-worktree settings.
It does not call a model, run a benchmark, or claim live provider readiness.
The checked result is saved in [validation.json](validation.json).
The 18 focused tests in `tests/test_paper_supervisors.py` cover evidence integrity,
follow-up coverage, native lane isolation, launch preflight, duplicate lane
locks, and termination using a dummy Python child. Run them with
`python3 -m unittest discover -s tests -p test_paper_supervisors.py -v`.

Use a committed integration checkout containing these inputs before live work:
native ephemeral workers start from Git commits and cannot see untracked paper
files. Existing unrelated dirty workspace changes were left untouched during
this review. Commit only the reviewed campaign inputs in the integration
checkout, or carry them to a dedicated integration branch through your normal
Git workflow. Do not discard existing work to satisfy launch preflight.

Start all three foreground supervisors with:

```bash
python3 scripts/paper_supervisors.py run --paper all
```

Or select one paper:

```bash
python3 scripts/paper_supervisors.py run --paper autoformalization
python3 scripts/paper_supervisors.py run --paper law_to_action
python3 scripts/paper_supervisors.py run --paper neurosymbolic_supervision
```

The launcher imports the native supervisor; it is not a substitute scheduler.
It leaves the existing provider/model configuration in effect, uses separate
task prefixes and state/worker directories, and supplies all three submodule
paths to native worktree initialization. A common merge queue coordinates
changes to shared libraries. Lane locks prevent duplicate launches through this
controller. Shared edits must still pass native validation and merge handling;
parallelism does not guarantee conflict-free integration.

State and logs default to
`~/.local/state/ipfs_accelerate_py/vericodegen-2026/<paper>/` (or `$XDG_STATE_HOME`).
Set `VERICODEGEN_STATE_ROOT` to choose another campaign location. Each lane logs
to `supervisor.log`; native task state and events are under `state/`. The
foreground launcher waits for the supervisors and handles interruption by
terminating its owned native process trees. No background daemon was started by
this preparation task.

Long training/benchmark jobs should checkpoint progress and publish heartbeat
logs. A task attempt has a two-hour worker limit and three attempts; a genuinely
longer experiment must be split into resumable work with explicit dependencies
and resource allocation. Each protocol task must set actual CPU/GPU/model/API
budgets from available resources; this plan does not assume three concurrent
GPU training jobs fit the host. Keep non-GPU work progressing while scarce
resources are occupied. Do not change any other paper's manuscript/results.

## Boards, follow-ups and completion evidence

`tasks.json` is the reviewed seed. `paper.objectives.md` and `paper.todo.md` are
the native runtime boards. `build` is a one-time renderer and refuses to
overwrite an existing board, preserving status and follow-up work. Source PDFs,
templates, reviews, seed manifests, configurations and the validation script are
protected worker inputs. Extend native boards with unique same-paper IDs,
explicit goal lineage/dependencies/outputs/validation and concrete acceptance
criteria when further work is discovered. The root goal must account for those
follow-ups too; a drained seed list alone is insufficient.

Twelve implementation tasks declare narrow source-edit scopes through native
`Allowed paths`; `Reuse candidates` is a discovery hint only. Additional source
repairs need explicit scope on a follow-up before dispatch. Evidence snapshot
directories are included in `Predicted files`. Baseline tests and independent
oracles must not be weakened to improve reported results. The initial
`cpu-medium` / `execution` metadata describes the implementation worker; protocol
tasks must allocate and declare actual GPU/network resources for experiments.

Each task writes
`papers/completion/<paper>/receipts/<TASK-ID>.json`, following this schema:

```json
{
  "schema": "paper-task-evidence/v1",
  "task_id": "AF-001",
  "status": "complete",
  "completed_at": "2026-09-11T18:00:00+00:00",
  "source_versions": {"repository": "actual commit; record relevant dirty overlay and dependencies"},
  "artifacts": {
    "papers/completion/autoformalization/receipts/snapshots/AF-001/main.tex": "actual sha256",
    "papers/completion/autoformalization/receipts/snapshots/AF-001/build.log": "actual sha256"
  },
  "outputs": {
    "papers/completion/autoformalization/manuscript/main.tex": "papers/completion/autoformalization/receipts/snapshots/AF-001/main.tex"
  },
  "criteria": [{
    "criterion": "Copy the exact reviewed criterion here; include every criterion in order",
    "status": "met",
    "explanation": "What the retained evidence establishes and its limits",
    "evidence": ["papers/completion/autoformalization/receipts/snapshots/AF-001/main.tex"]
  }],
  "commands": [{
    "argv": ["actual-command", "actual-argument"],
    "exit_code": 0,
    "log": "papers/completion/autoformalization/receipts/snapshots/AF-001/build.log"
  }]
}
```

The example is a schema illustration, not a receipt or experiment result.
Snapshot every declared output (all files for directory outputs); keep immutable
evidence under the task's snapshots directory. Criteria refer to those hashed
snapshots. Record the actual tools, commands, versions, data/model identities,
errors, human annotation provenance and full result denominators. Use the exact
seed criteria list; for a new native follow-up, its complete `Acceptance` field
is one criterion. Follow-up validation uses the same `verify-task` command.

```bash
python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-001
python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-G000
```

Task checks compare current deliverables against immutable snapshots. Goal
checks retain historical task evidence while reconciling later revisions of
shared outputs, so editing a manuscript in a later task does not erase its
source-recovery evidence. Receipts and passing checks establish artifact
integrity and recorded coverage; they are not independent scientific replication
or a substitute for the final independent reproduction task and author review.
The prepared program contains **no completion receipts or benchmark results**.
