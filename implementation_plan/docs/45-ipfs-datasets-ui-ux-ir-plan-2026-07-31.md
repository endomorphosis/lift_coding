# UI/UX Intermediate Representation for `ipfs_datasets_py.logic`

Status: implementation-ready plan
Date: 2026-07-31
Program prefix: `UIR`
Board namespace: `ipfs-datasets-ui-ux-ir-v1`

Companion supervisor artifacts:

- `implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.objectives.md`
- `implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md`

## 1. Outcome

Create a canonical, bidirectional UI/UX intermediate representation in
`external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/` that can:

1. import supported UI declarations and interaction contracts into a stable,
   source-grounded semantic model;
2. compile that model into linked first-order/frame, temporal-deontic, event
   calculus, and deontic cognitive event calculus views;
3. reconstruct a semantically equivalent UI/UX declaration from those formal
   views, with every unsupported or lossy detail reported;
4. synthesize bounded UI/UX declarations from Intent IR, MCP-IDL, program
   invocation contracts, and reviewed formal constraints;
5. project one declaration to desktop/web, mobile, voice/headless, and
   spatial/Meta-glasses capability profiles;
6. normalize mouse, keyboard, touch, speech, gesture, gaze/head pose, Meta
   Neural Band/captouch, and agent input into one policy-mediated interaction
   path; and
7. retain content identity, provenance, policy decisions, proof authority,
   projection loss, and runtime receipts without mixing observations into the
   immutable declaration.

The deliverable is not a universal pixel-perfect source-code translator. Its
contract is semantic equivalence over a declared supported subset: component
roles, data and action bindings, state transitions, UX flow, accessibility,
modality alternatives, temporal/deontic constraints, and observable effects.

## 2. Repository baseline and reuse decision

The new package must reuse the following landed systems.

| Concern | Existing authority | Reuse decision |
| --- | --- | --- |
| Canonical bytes, identity, provenance, schemas, diagnostics, claims, result authority, manifests | `external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/` | Import directly; do not fork |
| Program goals, actions, conditions, effects, verification, and control flow | `external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/` | Reference by stable ID/CID; do not duplicate |
| Governed invocation, actor, delegation, scope, rollback, and verification | `logic/intent_ir/invocation/model.py` | Bind UI actions to `InvocationIntentEnvelope` templates |
| Domain-neutral formal views and translation receipts | `logic/formalization/` | Extend through UI/UX adapters and views |
| TDFOL and FOL | `logic/TDFOL/`, `logic/fol/` | Target through public compiler contracts |
| DCEC and event calculus | `logic/CEC/native/` | Target through adapters; do not couple schema to internal AST variants |
| Frame logic | `logic/flogic/` and modal/frame bridge | Reuse for structural and capability facts |
| Multi-view logic routing | `logic/bridge/` | Register a UI/UX formalization adapter late in integration |
| MCP-IDL callable semantics | `swissknife/src/services/mcp/mcp-idl.ts` | Treat as the service/operation source contract |
| Verified MCP interface identity | `external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/mcplusplus/idl_registry.py` | Reuse its CIDv1/raw/sha2-256/base32 preimage-verification profile through an adapter; keep UIIR identity separate |
| Existing schema-driven UI profile | `swissknife/src/services/mcp/mcp-ui-profile.ts` and `mcp-schema-ui-generator.ts` | Convert to/from UI/UX IR through a TypeScript codec |
| Deontic UI projection and ORB gate | `swissknife/src/services/mcp/mcp-deontic-interface-broker.ts` | Keep as a runtime consumer; replace local semantic duplication incrementally |
| Multimodal envelopes and receipts | `swissknife/src/services/mcp/mcp-control-surface-mediator.ts` and `swissknife/contracts/` | Align with canonical UI interaction artifacts |
| Meta-glasses projection | `swissknife/src/services/glasses/idl-to-glasses-compiler.ts` and related profiles | Implement a target adapter and conformance suite |

This program extends, rather than supersedes,
`implementation_plan/docs/22-multimodal-control-surface-logic-idl.md`. That
plan owns multimodal mediation around ORB calls. This plan adds the missing
canonical UI declaration, bidirectional formalization, target projection, and
semantic round-trip contracts.

### 2.1 P0 interoperability debt to close

The audit found legacy identities and policy defaults that cannot be inherited
silently:

- current descriptor fixtures use `sha256:*`, mock `bafy-*`, weak pseudo-CIDs,
  and real CIDv1 values interchangeably;
- the `ipfs_datasets_py.mcp_server.interface_descriptor` identity path labels
  raw canonical bytes as DAG-PB, excludes some returned descriptor fields from
  identity, and can cache identity on mutable data;
- the strongest current MCP-IDL identity implementation is
  `external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/mcplusplus/idl_registry.py`,
  which verifies real CIDv1/raw/sha2-256/base32 preimages;
- a UIIR CID and an MCP interface CID identify different domains and must never
  be compared as if they were interchangeable;
- the Hallucinate Python mediator has historically allowed a no-match policy
  path while the SwissKnife TypeScript mediator fails closed to confirmation;
- current ORB paths can make policy optional and some streaming checks omit the
  real input, defeating input-sensitive rules; and
- the legacy dynamic web renderer has unsafe HTML/direct-HTTP paths that must
  not become a UIIR renderer shortcut.

The implementation therefore records both `ui_ir_cid` and a separately
verified `interface_cid`, retains legacy interface identifiers only as typed
aliases, publishes cross-language identity vectors, makes missing/invalid
policy fail closed on every transport and stream, and routes UIIR rendering
through escaped semantic adapters plus the governed invocation path.

## 3. Architectural boundaries

### 3.1 Ownership model

```text
MCP-IDL                 Intent IR / invocation IR       reviewed policy
   |                              |                           |
   +-------------- source adapters / stable references ------+
                                  |
                           UI/UX IR declaration
                                  |
                 +----------------+----------------+
                 |                                 |
          formalization views               target projection
   FOL/F-logic | EC | TDFOL | DCEC       web | mobile | glasses | voice
                 |                                 |
          proof/monitor results              projection + loss receipt
                 +----------------+----------------+
                                  |
                       mediated runtime interpreter
                                  |
       normalized input -> policy decision -> ORB/program invocation
                                  |
                    state transition + feedback receipt
```

The boundaries are strict:

- MCP-IDL owns callable service contracts and argument/result schemas.
- Intent IR owns program goals, procedures, and control flow.
- Invocation IR owns an attempted governed call.
- UI/UX IR owns human/agent interaction semantics and presentation-neutral
  affordances.
- Device adapters own raw sensor SDKs and renderer details.
- The mediator owns runtime authorization. Hiding or disabling a control is
  never authorization.
- Formal proof, satisfiability, bounded monitoring, accessibility validation,
  and policy approval remain distinct result-authority families.

### 3.2 Declaration versus derived/runtime artifacts

`UIIRDocument` is immutable. The following are separate content-addressed
artifacts and must not change declaration identity:

- a target-specific projection;
- a device-capability negotiation result;
- a formalization or reconstruction artifact;
- proof, countermodel, monitor, accessibility, or policy results;
- an input observation or recognized intent;
- a mediation decision;
- an ORB/program invocation receipt;
- a runtime state snapshot or replay trace; and
- timing, device health, confidence calibration, or performance telemetry.

## 4. Canonical UI/UX IR v1

The v1 wire identifier is `ui-ux-ir/v1`. The JSON contract is closed by
default, declares collection semantics for canonicalization, rejects dangling
references, and supports extensions only through versioned namespaced extension
records.

### 4.1 Document envelope

The document contains:

- `schema_version`, `document_id`, title, locale defaults, and tags;
- immutable `SourceRef`, producer, configuration, review, and trust bindings;
- semantic component nodes and composition edges;
- abstract layout regions and constraints;
- design-token references rather than device-specific pixel values;
- state variables, states, events, transitions, guards, and effects;
- UX tasks, journeys, success/failure/recovery paths, and feedback contracts;
- accessibility and localization semantics;
- input/output modality requirements and alternatives;
- device-capability requirements and adaptive variants;
- data bindings and content references;
- stable program, Intent IR, invocation, and MCP-IDL bindings;
- formal constraint and proof-obligation references; and
- explicit entry components, initial states, and terminal outcomes.

### 4.2 Component graph

Components are semantic nodes, not framework widgets. Required concepts are:

- stable component ID and role;
- purpose and accessible name/description references;
- value, selection, validation, and enabled/visible semantics;
- parent, child, slot, label, described-by, owns, and flow relationships;
- action affordances and accepted modality bindings;
- data source/query/update references;
- feedback channels and error/recovery surfaces;
- privacy sensitivity and presentation classification; and
- optional target hints that cannot override semantic requirements.

Initial roles should align with ARIA where possible while allowing namespaced
domain roles. Framework-specific names such as React component classes are
source-map metadata, not canonical roles.

### 4.3 Abstract layout and adaptation

Layout is represented as constraints over regions, order, containment,
alignment, adjacency, priority, visibility, minimum readable size, and resource
budgets. It must support:

- flow, grid, stack, overlay, spatial anchor, and audio sequence regions;
- responsive breakpoints expressed as capability predicates;
- safe-area, field-of-view, text-density, action-count, update-rate, latency,
  and attention-budget constraints;
- logical reading/focus order independent of visual order;
- a design-token vocabulary for type, spacing, color intent, emphasis, motion,
  haptics, and audio cues; and
- explicit `preserve`, `adapt`, `summarize`, `fallback`, and `omit` policies.

Projection uses constraint solving and returns a loss report. It must never
silently drop a required action, confirmation, error, privacy indicator, or
accessibility alternative.

### 4.4 Behavior and UX flow

Behavior uses a bounded hierarchical state-machine model:

- typed state variables and derived state;
- input, domain, lifecycle, timer, and program-result events;
- deterministic transition priority and conflict handling;
- guards referencing facts or formal constraints;
- effects referencing Intent actions or IDL operations;
- cancel, retry, undo, rollback, compensation, and timeout paths;
- parallel regions and joins;
- focus/navigation state;
- pending confirmation and consent state; and
- success, failure, partial, unavailable, and degraded outcomes.

Executable code, callbacks, and arbitrary expressions are forbidden in the
declaration. Only stable references or a reviewed, closed expression language
may be used.

### 4.5 Program bindings

Every action binding selects exactly one declared semantic target:

- MCP-IDL interface CID plus method and schema references;
- Intent IR document/action ID;
- Invocation Intent template CID;
- a local state-only transition; or
- a versioned composite workflow reference.

Bindings carry preconditions, expected effects, verification, rollback,
idempotency, risk class, confirmation class, audience, and result-to-state
mappings. They do not contain implementation code or grant authority.

### 4.6 Accessibility, localization, and cognitive UX

V1 must model:

- accessible name, description, role, value, state, relationships, and live
  announcements;
- keyboard/focus navigation and focus restoration;
- a modality alternative for every essential action and output;
- contrast/emphasis intent without hard-coding a single theme;
- reduced motion, reduced audio, magnification, captions, transcripts, haptic
  alternatives, and time-extension preferences;
- translatable message IDs, variables, plural/select behavior, text direction,
  and locale fallback;
- interaction cost, urgency, interruption class, confirmation load, and
  attention budget; and
- clear recovery and consequence previews for risky actions.

### 4.7 Modalities and capability profiles

Canonical input capabilities include:

- pointer/mouse, keyboard, switch, touchscreen, pen;
- microphone/speech intent and audio;
- hand gesture, gaze, head pose, motion/orientation;
- D-pad/captouch and normalized Neural Band intent;
- agent proposal and delegated autonomous action; and
- composite/multimodal input.

Canonical output capabilities include display, spatial display, audio/speech,
haptic, notification, mobile companion, and agent-readable structured output.

Raw camera, microphone, biometric, gaze, or neural signals remain in trusted
device adapters. The canonical runtime event contains a recognized event or
intent, confidence/calibration, source capability, consent/purpose, freshness,
and a redacted evidence reference. It must not claim raw EMG access. The
current Meta Web Apps path exposes Neural Band/captouch behavior as Arrow/Enter
style events, so the reference adapter maps those to abstract intent tokens.

## 5. Formal semantics

The compiler emits separate linked views. A monolithic mixed-logic string is
not a valid output.

| View | UI/UX meaning | Example obligations |
| --- | --- | --- |
| FOL and F-logic/frame | Components, roles, containment, slots, values, data/program bindings, actors, devices, and capabilities | Every actionable control has one declared action; IDs are unique; labels resolve; required bindings exist |
| Event calculus | Events, fluents, lifecycle, focus, navigation, pending state, timeout, cancellation, effects, and persistence | Clicking submit initiates pending; success terminates pending and initiates complete; cancel terminates confirmation |
| TDFOL | Temporal invariants plus permission, prohibition, and obligation | A destructive call is never invoked before confirmation; a denial remains non-invocable; a required error remains perceivable until acknowledged |
| DCEC | Perception, knowledge, belief, intention, communication, consent, delegation, and accountable agency | An agent may act only when it has a valid delegation; the user is informed of material consequences; consent must be known before sensor use |
| Accessibility/conformance constraints | Perceivability, operability, modality equivalence, focus, timing, and feedback | Every essential pointer action has a non-pointer alternative; focus is not lost after modal close |

Cross-view links bind the same component, event, action, actor, state, source,
and program operation across views. Coverage reports list every UI semantic
element as `represented`, `approximated`, `unsupported`, or `intentionally
non-formal`.

### 5.1 Logic-to-UI reconstruction

Reconstruction is constraint-guided:

1. decode typed formal views and validate cross-view identity;
2. recover semantic components, actions, states, guards, effects, norms, and
   modality obligations;
3. preserve ambiguity as alternatives or clarification requirements;
4. synthesize only from reviewed templates and capability vocabularies;
5. emit `ReconstructionReceipt` and `SemanticRoundTripReport`; and
6. reject a reconstruction that would hide an obligation, broaden authority,
   fabricate source grounding, or silently weaken a safety/accessibility rule.

The decompiler cannot recreate arbitrary original source text, CSS, React
component structure, or visual artwork. Those are retained only through source
maps or target artifacts.

### 5.2 Equivalence policy

Round-trip quality is evaluated in layers:

1. canonical identity for unchanged declarations;
2. graph isomorphism for semantic component and binding graphs;
3. state-machine trace equivalence over bounded generated traces;
4. formula equivalence or mutual entailment for supported formal fragments;
5. deontic non-weakening for permissions, prohibitions, and obligations;
6. accessibility-role/name/action equivalence;
7. modality coverage and fallback equivalence; and
8. declared projection/reconstruction loss below a reviewed threshold.

Source-code or pixel equality is explicitly outside the equivalence claim.

## 6. Bidirectional pipelines

### 6.1 Existing UI to formal logic

```text
supported DOM/ARIA, MCP UI profile, glasses manifest, or mobile descriptor
  -> bounded source adapter + source map
  -> validate UIIRDocument
  -> canonical bytes + CID
  -> UI formalization adapter
  -> FOL/F-logic + event calculus + TDFOL + DCEC views
  -> proof/monitor/coverage artifacts
```

### 6.2 Formal logic or program IR to UI

```text
Intent IR / invocation templates / MCP-IDL / reviewed formal constraints
  -> bounded semantic synthesizer
  -> candidate UIIRDocument + ambiguity diagnostics
  -> schema, policy, accessibility, and satisfiability gates
  -> target capability projection + explicit loss
  -> web/mobile/glasses/voice renderer artifact
```

### 6.3 Runtime interaction and orchestration

```text
raw device signal
  -> trusted input adapter
  -> canonical UIInteractionEvent
  -> target and intent resolution
  -> multimodal fusion/arbitration
  -> state-machine candidate transition
  -> temporal/deontic/cognitive policy evaluation
  -> allow | deny | confirm | defer | rewrite | fallback | rate-limit
  -> governed Intent/ORB invocation when allowed
  -> result mapping, verification, state transition, feedback
  -> immutable mediation/invocation/replay receipts
```

Human input has interaction-priority over an autonomous proposal, but it does
not bypass policy. Simultaneous inputs are correlated and deduplicated rather
than blindly executing twice.

## 7. Proposed package and adapter layout

```text
external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/
  README.md
  __init__.py                    # late integration only
  schema.py
  ui_ux_ir.schema.json
  canonicalize.py
  decoder.py
  migrations.py
  protocols.py
  provenance.py
  model/
    components.py
    layout.py
    behavior.py
    experience.py
    modality.py
    bindings.py
  formalize/
    contracts.py
    ontology.py
    compiler.py
    flogic.py
    event_calculus.py
    tdfol.py
    dcec.py
    decompiler.py
    roundtrip.py
    synthesis.py
  source_adapters/
    mcp_idl_identity.py
    mcp_idl.py
    intent_ir.py
    dom_aria.py
  projection/
    capabilities.py
    solver.py
    loss.py
    web.py
    mobile.py
    glasses.py
    voice.py
  runtime/
    events.py
    input/
      conventional.py
      speech.py
      embodied.py
    fusion.py
    state_machine.py
    mediator.py
    receipts.py
  assurance/
    accessibility.py
    privacy.py
    security.py
  conformance.py
```

TypeScript/mobile adapters live with their runtimes and consume the same JSON
Schema and golden vectors:

- `swissknife/src/services/mcp/ui-ux-ir-codec.ts`
- `swissknife/src/services/mcp/ui-ux-ir-web-renderer.ts`
- `swissknife/src/services/glasses/ui-ux-ir-glasses-adapter.ts`
- `mobile/src/orb/uiUxIrMobileAdapter.js`

Existing cross-runtime integration surfaces are modified only by their
single-owner tasks:

- `swissknife/src/services/mcp/mcp-orb-capability-router.ts`
- `hallucinate_app/python/hallucinate_app/control_surface_mediator.py`
- `swissknife/web/src/orb-dynamic-app-renderer.ts`

Subpackage `__init__.py` files are owned by `UIR-069`; the root `__init__.py`,
shared exports, logic submodule registry, bridge registry, and public API are
owned by the serialized `UIR-070`. No other task edits those late integration
surfaces.

## 8. Public API target

The initial Python surface should be small and side-effect free:

```python
decode_ui_ir(payload) -> UIIRDocument
canonicalize_ui_ir(document) -> bytes
ui_ir_identity(document) -> CanonicalIdentity
compile_ui_ir(document, request) -> UIFormalizationArtifact
decompile_ui_formalization(artifact, request) -> UIReconstructionArtifact
roundtrip_ui_ir(document, policy) -> SemanticRoundTripReport
synthesize_ui_ir(inputs, constraints, policy) -> UISynthesisResult
project_ui_ir(document, device_profile, policy) -> UIProjectionArtifact
normalize_ui_interaction(raw_event, adapter_context) -> UIInteractionEvent
evaluate_ui_interaction(document, event, runtime_context) -> UIMediationDecision
```

Optional solvers, model runtimes, browser runtimes, and device SDKs resolve
lazily. Importing `ipfs_datasets_py.logic.ui_ux_ir` performs no network,
process, hardware, or model action.

## 9. Invariants and safety gates

The following are non-negotiable:

1. Canonical declaration identity excludes observations and derived results.
2. All references resolve and all set/ordered collection semantics are
   declared.
3. Unsupported import, formalization, projection, or reconstruction semantics
   are explicit; no silent coercion.
4. A renderer may adapt presentation but cannot remove a required action,
   obligation, consequence, error, consent prompt, or accessibility path.
5. UI visibility and enabled state never replace runtime authorization.
6. Every external effect passes through the existing governed
   Intent/Invocation/ORB path and produces a receipt.
7. Raw sensor and biometric/neural data are minimized, purpose-bound, and
   adapter-local.
8. Low-confidence or conflicting high-impact input requires clarification or
   confirmation.
9. Agent actions carry delegation and cannot gain a broader capability through
   a UI binding.
10. Learned synthesis and retrieval provide candidates only; deterministic
    schema, policy, formal, accessibility, and capability gates admit them.
11. Proof, satisfiability, runtime monitor, policy approval, and conformance
    results are never substituted for one another.
12. Every migration and cross-language codec has canonical golden vectors.
13. `ui_ir_cid`, verified MCP `interface_cid`, and any legacy descriptor alias
    remain different typed identities with verified preimages.
14. Missing policy, missing real streaming input, and direct-renderer transport
    bypasses fail closed.

## 10. Implementation waves and parallelism

The objective heap and taskboard contain the authoritative details. The safe
execution shape is:

| Wave | Work | Parallelism |
| --- | --- | --- |
| 0 | Boundary ADR, vocabulary, source/threat inventory, and MCP-IDL identity profile | architecture and identity lanes in sequence |
| 1 | V1 envelope, JSON Schema, exact decoder, canonical vectors, and typed external identities | one schema lane plus independent identity-vector work |
| 2 | Components/layout; behavior/UX/accessibility; modality/program bindings; provenance/artifacts | four exclusive Python lanes |
| 3 | Formal ontology; IDL/Intent adapters; TS codec; projection capabilities; runtime event model | five lanes |
| 4 | F-logic, event calculus, TDFOL, and DCEC compilers; web/mobile/glasses/voice projections; modality adapters | logic and platform lanes with exclusive files |
| 5 | Cross-view compiler, decompiler/round-trip, ORB mediator, state runtime, privacy/accessibility validators | bounded integration lanes |
| 6 | Synthesis, receipts/replay, property/model tests, Python/TS golden parity | assurance lanes |
| 7 | Internal package surfaces, public API/registries, and four vertical pilots | two serialized export owners followed by independent pilot lanes |
| 8 | Benchmarks, simulator E2E, migration guide, root conformance/release gate | release lanes, then single closeout |

The approximate critical path is:

```text
UIR-001 -> UIR-010 -> UIR-020 -> UIR-025 -> UIR-062 -> UIR-069 -> UIR-070
        -> platform/runtime pilots -> UIR-081 -> UIR-083

UIR-001 -> UIR-002 -> UIR-030/UIR-032 -> UIR-062 -> UIR-069 -> UIR-070
```

Parallel workers must treat `schema.py`, each package export tier,
`logic/api.py`, `logic/submodule_registry.py`, `logic/bridge/registry.py`, and
existing SwissKnife broker/mediator files as single-owner conflict surfaces.

## 11. Milestones

### M0 — reviewed contract

- Architecture boundary and terminology approved.
- Supported v1 subset and explicit non-goals frozen.
- MCP-IDL identity authority, real-CID profile, legacy aliases, and
  cross-language preimage vectors frozen without conflating interface and
  UIIR identities.
- Threat, privacy, accessibility, and proof-authority rules recorded.

### M1 — canonical UI/UX IR

- Immutable model, JSON Schema, decoder, identity, provenance, and migrations.
- Cross-reference, mutation, and canonical-vector tests pass.

### M2 — formal semantic bridge

- F-logic, event calculus, TDFOL, and DCEC views emitted with source maps.
- Cross-view coverage and unsupported semantics are complete.
- Semantic decompile/round-trip gate passes the reviewed corpus.

### M3 — ORB/IDL and program integration

- MCP-IDL and Intent/Invocation adapters are live.
- Python and TypeScript codecs agree on canonical vectors.
- Existing TypeScript and Python control-surface mediation fail closed and
  gate every external effect, including streaming inputs.
- The legacy dynamic renderer has no direct-transport or untrusted-HTML path.

### M4 — adaptive projections and multimodal runtime

- Web, mobile, glasses, and voice/headless projections return explicit loss.
- Mouse/keyboard/touch, voice, hand/gaze, Neural Band/captouch, and agent
  events share one runtime model.
- Fallback, confirmation, conflict, and replay behavior are deterministic.

### M5 — vertical proof

- Responsive form on web/mobile.
- Destructive workflow requiring confirmation.
- Meta-glasses pilot using D-pad/Neural Band/captouch-style normalized input
  with mobile fallback.
- Dynamic agent-supervisor/program interface generated from IDL + Intent IR.

### M6 — release candidate

- Property, mutation, accessibility, privacy, round-trip, cross-language,
  browser, mobile, and glasses-simulator gates pass.
- Performance and complexity budgets are met.
- Migration and extension guidance is published.

## 12. Evaluation and release criteria

Release requires current-tree evidence for all of the following:

- identical canonical bytes and identity across Python and TypeScript for the
  golden corpus;
- verified interface-CID preimages remain distinct from UIIR CIDs, and
  pseudo-CIDs or mismatched legacy aliases are rejected;
- deterministic decode, validate, migrate, compile, decompile, synthesize,
  project, and replay behavior;
- no dangling references, mutation-after-construction, or unknown-version
  acceptance;
- formal coverage disposition for every semantic node and transition;
- no deontic weakening across supported round trips;
- bounded trace equivalence for state machines;
- no required affordance or accessibility alternative silently lost during
  projection;
- denied, confirmation-required, deferred, rate-limited, or ambiguous actions
  do not reach an executor;
- missing/invalid policy, omitted streaming input, unsafe HTML, and direct
  renderer transport attempts fail closed;
- exact actor/delegation, policy, program, interface, input, projection, state,
  and result bindings in receipts;
- adversarial sensor, prompt-injection, stale-event, duplicate-event,
  confused-deputy, and unauthorized-agent fixtures fail closed;
- hardware-free desktop/mobile/glasses replay succeeds; and
- cold import remains side-effect free.

Initial benchmark targets, to be revised only with measured evidence:

- decode + validate p95 under 20 ms for a 1,000-node document;
- deterministic projection p95 under 100 ms for a 1,000-node document without
  an external solver;
- event mediation p95 under 25 ms excluding external policy/prover latency;
- canonical artifacts bounded to 10 MiB and 10,000 semantic nodes in v1; and
- every solver/model/browser/device call has an explicit timeout and output
  bound.

## 13. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| A universal schema becomes an unmaintainable widget taxonomy | Model semantics and capabilities; keep framework widgets in adapters |
| “Round trip” is mistaken for source/pixel recovery | Publish layered semantic equivalence and loss receipts |
| UI policy shaping is mistaken for authorization | Gate every effect again at invocation and test bypass attempts |
| Mixed logics create unsound claims | Emit typed linked views and preserve exact result authority |
| Device constraints silently weaken obligations | Fail projection or require fallback when mandatory semantics cannot fit |
| Neural/biometric input overclaims available hardware data | Model normalized capabilities; retain raw signals in consented adapters; make unsupported explicit |
| Free-form expressions become a code-execution channel | Closed expression grammar and stable references only |
| Parallel agents collide in shared exports and schemas | Exclusive file ownership and late single-owner integration |
| Learned synthesis fabricates semantics | Candidate-only authority plus deterministic admission and provenance |
| Imported UI source is ambiguous | Supported-subset profiles, source maps, diagnostics, and clarification artifacts |
| Legacy descriptor IDs are mistaken for canonical CIDs | Typed identity domains, verified preimages, frozen interop vectors, and explicit legacy aliases |
| A renderer or streaming transport bypasses policy | Remove direct transport/HTML paths and enforce the same fail-closed policy with the real bounded input on every invocation |

## 14. Explicit non-goals for v1

- arbitrary React, SwiftUI, Jetpack Compose, Flutter, CSS, or binary UI source
  recovery;
- pixel-perfect or stylistically identical reconstruction;
- direct execution of callbacks or code embedded in an imported UI;
- raw Meta Neural Band EMG processing unless a separately reviewed official
  adapter contract becomes available;
- replacing MCP-IDL, Intent IR, Invocation IR, ORB routing, or existing proof
  backends;
- claiming that an LLM-generated UI or formula is proved because it validates;
- making target renderer artifacts part of canonical declaration identity; or
- shipping a high-risk autonomous UI action without runtime policy mediation.

## 15. Supervisor ingestion and launch

The checked-in `.objectives.md` file is durable intent. The `.todo.md` file is
the reviewed legacy-Markdown execution projection requested for immediate
parallel work. Generated objective graphs, discovery findings, bundle shards,
indexes, worktrees, merge queues, and state belong under
`data/agent_supervisor/ui_ux_ir/` and are not hand authored.

Audit the objective heap without generating or appending gap tasks:

```bash
PYTHONPATH=external/ipfs_accelerate \
python -m ipfs_accelerate_py.agent_supervisor.objectives.objective_daemon \
  --repo-root . \
  --objective-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.objectives.md \
  --todo-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md \
  --discovery-dir data/agent_supervisor/ui_ux_ir/discovery \
  --bundle-dir data/agent_supervisor/ui_ux_ir/bundles \
  --dataset-dir data/agent_supervisor/ui_ux_ir/datasets \
  --graph-path data/agent_supervisor/ui_ux_ir/objective_graph.json \
  --task-prefix UIR- \
  --max-findings 0 \
  --no-persist-ast-dataset \
  --no-generate-bounded-work \
  --no-reconcile-goal-completion
```

Dry-run the executable taskboard scheduler without invoking an implementation
agent:

```bash
PYTHONPATH=external/ipfs_accelerate \
python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon \
  --once \
  --todo-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md \
  --task-source-kind legacy-markdown \
  --task-prefix UIR- \
  --production-provider-policy grok-implement-codex-independent-review \
  --state-dir data/agent_supervisor/ui_ux_ir/state \
  --state-prefix uiir_dry_run \
  --worktree-root data/agent_supervisor/ui_ux_ir/worktrees/dry-run \
  --merge-queue-dir data/agent_supervisor/ui_ux_ir/dry-run-merge-queue \
  --worktree-submodule-path external/ipfs_datasets \
  --worktree-submodule-path external/ipfs_accelerate \
  --worktree-submodule-path swissknife \
  --worktree-submodule-path hallucinate_app \
  --objective-scan-max-findings 0 \
  --codebase-scan-max-findings 0 \
  --implementation-protected-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir-plan-2026-07-31.md \
  --implementation-protected-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.objectives.md \
  --implementation-protected-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md
```

The original reviewed board contained 47 canonical tasks, with `UIR-001` ready
and 46 dependency-waiting tasks. Before each restart, compare the dry run with
the live board instead of treating those initial counts as immutable: the
current reviewed projection contains 48 tasks, including the added recovery
task `UIR-084`, and has two authoritative completions (`UIR-001` and
`UIR-084`). To execute in parallel, start six long-running supervisor processes,
one for each `lane` value from 0 through 5. All lanes share the board and merge
queue but use isolated state and worktree roots:

Before launching, commit the reviewed plan/objective/taskboard and the required
accelerator baseline, advance the parent gitlinks, and choose an existing clean
integration branch explicitly. In particular, reconcile the configured
`hallucinate_app` integration branch with the parent gitlink before `UIR-034`;
the supervisor must not silently merge divergent nested histories. Do not rely
on the daemon's `main`/`master` fallback when the reviewed work lives on another
branch.

Production implementation routing is fail closed and must select the typed
`grok-implement-codex-independent-review` policy. Implementation is pinned to
Grok `grok-4.5`. Grok may yield a Terra proposal only when the native,
structured Grok result proves an exact HTTP 402 balance exhaustion; stderr
text, HTTP 429, authentication failures, missing executables, malformed output,
and generic nonzero exits are not fallback authority. The fallback is pinned to
`gpt-5.6-terra` with `medium` reasoning and runs proposal-only: it cannot write,
merge, consume an attempt, or approve its own output. Its current state-bound
pending latch prevents duplicate invocation only while the exact artifact is
present; an immutable authenticated approve/reject lifecycle remains required
before any Terra-authored effect can be admitted.
The separate independent implementation review remains pinned to Codex
`gpt-5.6-sol`; Terra cannot substitute for or bypass it. Raw fallback commands
are disabled, and production execution requires Linux `/proc` confinement so
detached provider descendants cannot escape the native subreaper.

The published accelerator checkpoint for this policy is
`8a68d43d2ca743ef6b70c65ac1ffca3c017ba2f8`. It also fences completed
post-merge correction repairs to their origin event stream, preventing foreign
lanes from amplifying a lane-local authorization failure. The six-lane fleet
remains stopped: `UIR-010` has a durable `correction_failed` head from attempt
2, and its exact `UIR-085` repair must not be completed until the typed packet
route carries the bound five-finding correction evidence through provider
review and write admission.

The required accelerator baseline includes a fail-closed, pre-provider
submodule ancestry check. For each configured submodule containing a task-owned
output, it permits equal history or an integration target that can
fast-forward to the recorded gitlink. A child integration target already ahead
of the root gitlink, pre-existing divergence, or unverifiable commits defer the
task without calling a provider or consuming an implementation attempt. The
diagnostic records the root gitlink, child integration commit, and merge base,
and the check is repeated after acquiring the implementation lock. The locked
check's immutable root commit is then used to seed the task worktree and its
actual `HEAD` is verified before provider dispatch, so a concurrent target
branch advance cannot substitute an unchecked baseline. This turns the current
`UIR-034` Hallucinate topology mismatch into an explicit operator action before
work begins; a stale parent gitlink must likewise be advanced so validation
runs against the actual integration baseline.

```bash
UIIR_MERGE_TARGET_BRANCH=agent/ui-ux-ir  # create and review this branch first
UIIR_ROOT="$(pwd -P)"

for lane in 0 1 2 3 4 5; do
  systemctl --user stop "uiir-lane-${lane}.service" 2>/dev/null || true
  systemctl --user reset-failed "uiir-lane-${lane}.service" 2>/dev/null || true
  mkdir -p "data/agent_supervisor/ui_ux_ir/state/lane-${lane}"
  systemd-run --user --collect \
    --unit="uiir-lane-${lane}" \
    --description="UIIR agent supervisor lane ${lane}" \
    --property=Type=simple \
    --property="WorkingDirectory=${UIIR_ROOT}" \
    --property=Restart=on-failure \
    --property=RestartSec=5s \
    --property=KillMode=control-group \
    --property=TimeoutStopSec=30s \
    --property="SuccessExitStatus=143 SIGTERM" \
    --setenv=PYTHONPATH=external/ipfs_accelerate \
    --setenv=PYTHONUNBUFFERED=1 \
    /usr/bin/python3 \
    -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
    --todo-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md \
    --task-prefix UIR- \
    --production-provider-policy grok-implement-codex-independent-review \
    --state-dir "data/agent_supervisor/ui_ux_ir/state/lane-${lane}" \
    --state-prefix "uiir_lane_${lane}" \
    --worktree-root "data/agent_supervisor/ui_ux_ir/worktrees/lane-${lane}" \
    --merge-queue-dir data/agent_supervisor/ui_ux_ir/merge-queue \
    --merge-target-branch "${UIIR_MERGE_TARGET_BRANCH}" \
    --task-shard-count 6 \
    --task-shard-index "${lane}" \
    --strict-task-sharding \
    --worktree-submodule-path external/ipfs_datasets \
    --worktree-submodule-path external/ipfs_accelerate \
    --worktree-submodule-path swissknife \
    --worktree-submodule-path hallucinate_app \
    --objective-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.objectives.md \
    --objective-scan-max-findings 0 \
    --codebase-scan-max-findings 0 \
    --no-objective-goal-refinement \
    --no-objective-goal-completion-reconcile \
    --implementation-protected-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir-plan-2026-07-31.md \
    --implementation-protected-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.objectives.md \
    --implementation-protected-path implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md \
    --implement
done

systemctl --user --no-pager --full status \
  uiir-lane-{0,1,2,3,4,5}.service
```

Only launch implementation after inspecting the dry-run dependency,
protected-path, provider-capacity, and worktree evidence. The plan, objective
heap, and taskboard are protected operator inputs; implementation tasks do not
own them. Objective-generated discovery bundles remain available for future
gap refinement, but they are not required to execute this pre-authored board.
The launch above deliberately disables automatic objective completion
reconciliation. It therefore tracks implementation task progress but does not
advance goal statuses. Enable reconciliation in a separately reviewed pass
once fresh completion-evidence and completion-gate artifacts are configured;
aggregate goals then derive implementation lineage from their descendant task
goals without bypassing their own evidence or validation gates.

## 16. Decisions that require review during implementation

These are bounded design decisions, not reasons to stall foundational work:

1. choose the smallest closed expression language for guards and layout
   predicates;
2. select the supported semantic subset for DOM/ARIA import and mobile
   projection;
3. define the formal equivalence policy for concurrent/parallel state regions;
4. decide whether spatial anchors belong in v1 core or a versioned extension;
5. set measured projection and mediation latency budgets;
6. determine which formal fragments require external theorem proving versus
   deterministic validation or bounded monitoring; and
7. revise Neural Band support only when an authoritative capability source
   proves more than normalized Arrow/Enter-style intent input.
