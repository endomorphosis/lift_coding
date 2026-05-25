# HAO-025 Implementation Unknowns Discovery

Date: 2026-05-25
Task: HAO-025
Scope: Hallucinate App, Swissknife, `ipfs_datasets_py`, and remote clients

## Outcome

New multimodal control-surface unknowns were found. This is not a
no-new-unknowns report. During HAO-025, these daemon-parseable HAO
task-board entries were recorded as historical discovery outputs:

- `HAO-036` for remote-client schema/envelope alignment.
- `HAO-037` for fail-open JavaScript and Swissknife mediation gates.
- `HAO-038` for real `ipfs_datasets_py` evaluator compatibility.
- `HAO-039` for end-to-end coverage that exercises real mediation instead of a
  test-only policy hook.

## Queue State Evidence

The initial queue is not fully clear in the current backlog: `HAO-008` and
`HAO-009` still have `Status: todo`, and the strategy file still lists both in
`blocked_tasks`. Existing retry-budget tasks `HAO-028` and `HAO-029` already
track those blockers, so this discovery does not duplicate them.

Evidence commands:

```bash
nl -ba hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md | sed -n '112,132p;299,308p'
rg -n "HAO-008|HAO-009" /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_strategy.json
```

## Findings

### Remote clients still publish local policy artifacts

Remote-client paths do not yet show the canonical
`control_surface_contract`, `interaction_envelope`, `normalized_intent`, or
`mediation_receipt` fields in the Meta-glasses/mobile bridge artifacts and
schema surfaces.

Evidence command:

```bash
rg -n "control_surface_contract|interaction_envelope|normalized_intent|mediation_receipt" spec/meta_glasses_mobile_orb_bridge_interface.json mobile src/handsfree hallucinate_app/swissknife/src/services/meta-glasses-mobile-orb-bridge.ts hallucinate_app/swissknife/src/services/meta-glasses-display-orb-adapter.ts
```

The command returned no matches. In addition,
`src/handsfree/meta_glasses_mobile_orb_artifacts.py:231` builds a local
`permit` decision and `src/handsfree/meta_glasses_mobile_orb_artifacts.py:279`
stores published glasses events with `accepted: True` rather than a canonical
Hallucinate App mediation receipt.

### Swissknife descriptor mediation is descriptor-only

`hallucinate_app/swissknife/src/services/control-surface-mediator.ts:356`
builds an interaction envelope and receipt, but the decision is derived from
descriptor binding errors only. Lines 371-372 set the outcome to `deny` when
descriptor reasons exist and `allow` otherwise. The path records
`policy_hooks`, but it does not call a Hallucinate App policy bundle evaluator
or the Python mediation engine.

### Daemon-managed service invocation fails open without a hook

`hallucinate_app/hallucinate_app/node/control_surface_invocation.js:52`
sets `hookDecision` to `null` when no policy hook is configured, and line 211
normalizes the missing decision to `allow`. This means a daemon-managed service
can emit a shaped `policy_decision` and `mediation_receipt` while bypassing the
runtime policy bundle store unless every caller remembered to register a hook.

### `ipfs_datasets_py` evaluation has no real allow-path regression

`data/hallucinate_multimodal_control/discovery/logic-api-inventory.md:25`
records that sampled `evaluate_nl_policy` calls fail closed because the bridge
passes `at_time` to an evaluator whose parameter is currently `now`.
`hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py`
uses a fake logic API, so it proves adapter shape but not compatibility with the
real upstream evaluator.

### E2E coverage uses a test-only policy hook

`hallucinate_app/test/e2e/multimodal-control-surface.spec.ts:186` installs a
test-only `setControlSurfacePolicyHook` callback. This proves envelope
normalization through the Node gate, but it does not prove that persisted policy
bundles, strict/general compiler results, or the Python mediation evaluator
drive the final decision for voice, gesture, mouse, agent, and remote clients.

## Backlog Expansion Rationale

The appended HAO tasks keep remediation separate and reviewable:

- Remote-client schema work can land independently of policy-evaluator wiring.
- Fail-open gate hardening is a security and runtime behavior change, so it
  should not be hidden inside a docs or fixture task.
- Upstream logic compatibility needs a focused adapter regression because the
  current tests deliberately fake the upstream API.
- E2E coverage should only assert real policy behavior after the remote envelope
  and policy-hook hardening tasks are complete.
