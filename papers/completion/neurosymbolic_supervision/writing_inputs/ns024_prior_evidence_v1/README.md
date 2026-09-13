# Prior evidence input for NS022 and NS024

This directory makes the accepted anonymous prior-evidence component available to ordinary manuscript and artifact workers. `component/` contains its exact 16 files. It is a supporting writing input, not a manuscript output, completion receipt or new scientific result.

For NS022, read `component/README.md`, `component/pilot/summary.json`, `component/pilot/timing_disclosure.json`, and `component/costs/summary.json`. The developmental pilot contains 24 cells across four historical families, A/B and three nested repetitions. The separately frozen final comparison contains 32 cells across eight different original final families, A/B local cold and two nested repetitions. Keep their populations, outcomes and costs separate; do not pool them or treat this component as final 32 evidence.

The pilot retains 10 useful outcomes (five per arm). That does not establish that all 24 pilot cells met a strict 600-second interpretation: ten child durations exceeded 595 seconds by less than 1 ms, and pilot cell 20 exceeded 600 seconds in both wrapper and gateway clocks. Preserve these deviations and original outcome labels. Do not retrospectively apply final-run resource rules to relabel the pilot. Passing collected tests does not establish semantic correctness or human fidelity.

For NS024, preserve the complete `component/` inventory as a standalone directory. Its existing standard-library numerical replay is:

```sh
cd papers/completion/neurosymbolic_supervision/writing_inputs/ns024_prior_evidence_v1/component
python3 -B source/reproduce.py
```

That command checks inventory and reconstructs released pilot and cost summaries from released rows. It performs no provider, scorer, native, network, hidden-test or original-signature replay. The included original analyzer is reference source; its command-line main is not the public replay entrypoint. This source adoption does not repeat the already retained replay.

The component is unsigned. Original private signed records remain unchanged in custody; their signatures do not authenticate these public projections. Preserve the derived-digest/original-role mapping in `component/manifest.json`. Unknown settlement, missing resource measurements and unmeasured setup/authoring costs are not zero. Sum only like clocks within their named scope; nested child/wrapper/gateway/host intervals and reused pilot cost projections must not be charged twice. Lease occupancy is not compute usage.

The whole anonymous supplement is still pending. This input does not satisfy all source, license, baseline, permitted-candidate, final 32, reproduction or hidden-oracle-custody obligations by itself. Combine it later with the separately reviewed complete final evidence and actual executed source lineage, preserve upstream attribution, and run the ordinary final artifact/privacy checks. No task status, manuscript output, submission or readiness claim is changed here.
