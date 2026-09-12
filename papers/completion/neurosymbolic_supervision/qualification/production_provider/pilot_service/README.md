# NS028 pilot host handoff

This directory is a staged NS028 input. It provides a real host queue client and a deferred integration patch. Its presence does not authorize a provider call, activate a grant or establish a scientific result. Keep NS026's existing development route and its consumed grant unchanged.

The root installed the reviewed host package at `/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/neurosymbolic_supervision/pilot-host-20260912-v1`. This path is host-only: the worker must not mount or attempt to read STATE, credentials, original private grants or scorer custody. The worker communicates through the exact root-provided `host_handoff/` below this directory. Its offers contain public verifier data encoded in JSON; no credential/key files belong in the paper proposal.

## Integrate after NS027

NS027 owns the existing experiment files. Root can commit this NEW directory now, while NS027 works. Do not apply `runner_integration.patch` to its active workspace. After NS027's committed result, inspect `integration_manifest.json` and run:

```sh
python3 qualification/production_provider/pilot_service/integrate_after_ns027.py --repo /ABS/NS028_WORKSPACE
```

Run that command from the paper directory, or use the full script path. The default inspects only. `--apply` writes the exact three reviewed files and adds the inactive profile section only if every old hash still matches; it does not stage, commit or activate anything. If NS027 changed any preimage, it refuses. NS028 must rebase only the hooks below, preserve NS027's mechanism changes, and obtain a new source review/hash binding before activation. A partially applied source edit requires inspection; it is never retried as if clean.

The proposed hooks are:

- `production_gateway.dispatch`: production + pilot routes to the reviewed worker adapter. The development branch remains unchanged. `verify_host_response` and `host_oracle` add the corresponding pilot verification/scalar interpretation branches.
- `run_comparison.AttemptExecutor.execute`: both development and pilot host dispatch occur BEFORE `materialize_live_task`. Pending host input/request returns `terminal_published=false`; no local oracle reconstruction or terminal scientific ledger row. Pilot receipt metadata remains distinct. Host resource measurements stay unavailable when no remote aggregate receipt exists.
- `score_runs.score_host_attempt`: reverify the exact signed source/candidate/schedule and interpret retained cold scalar evidence for development or pilot. It performs no new request, model call, hidden read or scorer run.
- `pilot_profile.template.json`: a separate `pilot_host_handoff` section; both activation hashes are null. Preserve the rest of `experiments/production_profile.json`, especially NS026's existing development binding.

The integration tests use constructed public metadata and explicit scalar/verifier doubles. They make no model, native, historical-source or scorer calls. Run `python3 qualification/production_provider/pilot_service/test_worker_delivery.py -v` from the paper directory. These tests verify the packaged reference patch. After a rebase, run equivalent checks against the actual integrated files too.

## Scientific activation must precede outcomes

The 48-cell plan is preserved. This host transport implements only the four predeclared pilot A/local_cold/repetition-0 cells (dnspython, bottle, idna, protego). A is a baseline, not a proxy for B/C/D. NS028 requires an actual between-arm comparison. Before the first paid pilot proposal, root must approve at least TWO distinct retained original arms, including A, their actual source/qualification hashes and shared context policy. Every omitted arm requires a pre-outcome scientific removal amendment. Arm names or different labels alone cannot establish mechanisms. Four A outcomes cannot complete NS028 or admit final experiments.

`context_selection.py` is an exact source-only copy of the host selection policy for inspection. The client does not run it or expose historical source to the host through worker-chosen arguments. The host freezes public-source request/context commitments before outcomes. The existing public-baseline compatibility runs are preparation evidence, not pilot outcomes or hidden-test passes.

## Late root activation and courier

Do not create offers while NS027 is active or while the comparison mechanism/profile freeze is incomplete. Grants expire after two hours. Once the actual NS028 workspace and integrated source are fixed:

1. Root uses the installed host `build_batch_inputs.py` and `pilot_gateway.py prepare` following the installed README, binding the real worker queue root, private batch root, four unit manifests, shared context profile and source. This creates no paid effect, but each preparation is one-use and failures remain retained.
2. Root creates a private `ns028-scientific-pilot-activation-review/v1` document. Required fields are enforced by `build_offer_drop.py`: accepted/frozen_before_comparison_outcomes/comparison_scope_frozen true; reviewer_kind ai_operator; host_package_sha256; planned_cells 48; final_admitted false; retained_arms (2–4, includes A); distinct_mechanisms_verified true; retained_arm_profiles keyed by each arm with distinct mechanism_id and source_sha256/qualification_sha256; mechanism_context_profile_sha256; worker_source_review_sha256; actual worker_source_files (the three experiment files plus worker_adapter and pilot_client); exact batch_sha256. If any arm is removed, add scientific_arm_removal_amendment_sha256. These fields summarize a real reviewed decision; booleans cannot substitute for that review.
3. Root runs the following staging command on the HOST with four real metadata paths. No worker supplies paths or authority:

```sh
python3 /ABS/DELIVERED/pilot_service/build_offer_drop.py \
  --worker /ABS/ACTUAL_NS028_WORKSPACE \
  --grant /PRIVATE/CELL1/grant.json --grant /PRIVATE/CELL2/grant.json \
  --grant /PRIVATE/CELL3/grant.json --grant /PRIVATE/CELL4/grant.json \
  --review /PRIVATE/scientific_activation_review.json --review-sha256 EXACT_SHA \
  --out /PRIVATE/NEW_DROP_REVIEW
```

This produces only `offer_drop.json` and `production_profile.proposed.json` in a fresh review directory. It creates zero grants/calls and does not install into the worker. Root reviews and installs those exact bytes into `pilot_service/host_handoff/offer_drop.json` and the actual worker's `experiments/production_profile.json`, preserving the old profile outside the added section. Bind the drop/profile SHA in the operator handoff record and task input receipt. The drop additionally pins the actual canonical workspace and all five source hashes. A copied offer in a different workspace or changed source/profile refuses.
4. The worker invokes its normal production runner with `--record-kind pilot --arm A --cache local_cold --repetition 0` and one exact admitted task ID. The client writes only the grant's exact request object. Pending means wait for the same root-owned request, never request a new grant or publish a failure outcome just because the host has not replied.
5. Root executes the reserved host proposal once. After termination and sealing, an independent AI/operator reviews the exact public candidate diff. Root binds that review using `review-template` and then `score-reviewed`. Scorer custody stays private. No automatic retry, changed/unknown-consumed grant replay, or score-before-review is permitted. Root returns/couriers the signed response to the same queue. The worker resumes the same command, then rescoring only verifies retained signed evidence. Preserve the complete signed offer/response and activation bindings as declared task artifacts; ephemeral queue traffic must not be swept into an unreviewed proposal.

The drop is a reviewed runtime input, not worker-generated authority. A successor must report missing root inputs as pending with their concrete schema/path, while continuing mechanism preparation. This package does not authorize new B/C/D implementations, final grants, human labels or adversarial scorer-integrity claims.
