# AF-002 deadline and scope decision record

**Checked:** 2026-09-11 UTC against the live official [VeriCodeGen 2026 CFP](https://vericodegen.github.io/cfp.html). No submission, portal action, public release, or author-sign-off decision was made.

## Live CFP record

The official page lists tentative AoE deadlines: abstract **2026-09-11** and paper **2026-09-13**. It requires the workshop LaTeX template/style, 4–9 main-text pages (references and appendices excluded), a 50 MB full-submission PDF maximum, and an anonymized supplementary ZIP up to 100 MB. It also requires double-blind handling of linked/supplementary material and disclosure of methodologically material LLM use. The dates are explicitly tentative: an author must recheck the CFP and OpenReview before an external action.

The reconstructed manuscript is already nine main-text pages. No A–E or T0–T5 result exists, and independent annotation, frozen corpus/splits, checker/runtime preflight, and model/GPU scheduling remain pending. Therefore this record does not represent the full empirical route as ready.

## Resource and coordination record

The prespecified allocation is one shared GPU/model-service slot, one condition at a time, 16 GiB RAM, 30 minutes per learned seed, 10 minutes per item for search/validation, and three fixed seeds. Current availability is `unavailable_pending_AF-003_preflight_and_shared_scheduler_reservation`: it is not a capacity reservation or evidence that a GPU, native checker, external model route, or teacher is usable. Runs must use this paper's own run directory and isolated code worktree; measurements from other papers are out of scope.

## Options fixed before outcomes

| Option | Preconditions | Permitted claims | Not permitted | Status |
| --- | --- | --- | --- | --- |
| Full empirical route | Pinned data/teachers/checkers/resources and retained admissible records for A–E/T0–T5. | Only individually measured claim-map claims, with coverage, intervals, failures, and cost. | Universal soundness, fixture/teacher-only claims, unmeasured availability. | Planned; unrun. |
| Narrowed methods/protocol route | Full-route dependency or time blocker persists. | Architecture, protocol, conformance boundary, and explicit limitations. | Performance, training gain, useful proof coverage, activation/deployment, CUDA speedup, or full-goal completion. | Concrete fallback; not an experiment. |
| No external action | No author approval or live CFP/format conditions change. | Internal planning only. | Submission, public release, or author-approval assertion. | Default here. |

Selecting the narrowed route requires author choice and an explicit claim edit saying empirical conditions are unmeasured. It does **not** make any condition measured, change a run from unrun/unavailable, or complete the full empirical objective. Any later scope revision must be versioned before affected outcome inspection and preserve the final-test lock in the experiment plan.
