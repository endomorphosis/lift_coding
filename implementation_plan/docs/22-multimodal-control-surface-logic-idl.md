# Multimodal Control Surface Logic IDL Upgrade

> Canonical AI-OS home: `hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md`
>
> This `lift_coding` document should be treated as the Meta-glasses integration-facing copy. The shared control-surface logic, policy mediation, and AI operating system ownership belong in `hallucinate_app`, with `lift_coding` retaining only the device-slice and transport-specific integration concerns.

## Objective
Upgrade the interface description layer so a single interface can safely expose and mediate:
- voice commands,
- gesture controls,
- mouse clicks / touch selection,
- and AI-agent initiated actions,

against the same control surfaces and the same user-defined policy rules.

The key design goal is to reuse the existing MCP-IDL / ORB descriptor approach already present in this repo, while using the `ipfs_datasets_py` logic stack as the policy and reasoning substrate. The upgrade should make rules like "ignore my wrist gestures at night, because I'm sleeping" compile into formal policy objects, evaluate against current context, and suppress or reshape invocation before the underlying interface method executes.

## Design Thesis
Do not create separate control contracts for voice, gesture, mouse, and agents.

Instead:
1. Keep one canonical interface descriptor for the service or widget.
2. Add an explicit multimodal control-surface section to that descriptor.
3. Normalize all incoming interactions into one frame-first intent IR.
4. Compile natural-language user rules into temporal-deontic policy artifacts.
5. Evaluate every attempted interaction against those policy artifacts before ORB invocation.
6. Emit a receipt that records the control surface, reasoning inputs, policy decision, and resulting action.

This preserves the current ORB/MCP++ architecture while moving policy mediation into a reusable reasoning layer instead of scattering it across UI handlers.

## Existing Assets To Reuse
This repo already has most of the substrate required for the upgrade.

### Descriptor and control-plane assets
- `swissknife/src/services/meta-glasses-mobile-orb-bridge.ts`
  - already defines MCP-IDL-like descriptors, operation policies, permissions, state model, and data contracts for the phone-edge ORB bridge.
- `spec/meta_glasses_mobile_orb_bridge_interface.json`
  - already models normalized device events, service binding, invocation, transport selection, and render-target dispatch.
- `src/handsfree/meta_glasses_display_widget_contract.py`
  - already aligns action ids and ORB operations for display-widget control surfaces.

### Logic and policy assets in `ipfs_datasets_py`
- `external/ipfs_datasets/ipfs_datasets_py/logic/api.py`
  - already exposes a stable logic API surface and lazy exports for NL policy compilation and evaluation.
- `external/ipfs_datasets/ipfs_datasets_py/logic/integration/nl_ucan_policy_compiler.py`
  - already provides a full NL -> DCEC -> Policy + UCAN compiler pipeline with explanation output.
- `external/ipfs_datasets/ipfs_datasets_py/processors/legal_data/reasoner/hybrid_legal_ir.py`
  - already provides a frame-first IR with `ActionFrame`, `EventFrame`, `StateFrame`, `TemporalConstraint`, and `Norm`.
- `external/ipfs_datasets/docs/logic/COMPREHENSIVE_LOGIC_REFACTORING_PLAN_2026_v16.md`
  - indicates the relevant policy compiler, evaluator cache, audit log, and conflict-detection phases are complete enough to serve as a foundation rather than a research dependency.

## Scope
This plan covers:
- descriptor-schema upgrades,
- runtime normalization of control surfaces,
- natural-language rule compilation,
- policy mediation before invocation,
- explainability and audit artifacts,
- staged rollout across backend, mobile, simulator, and Swissknife.

This plan does not require replacing the current ORB transport or existing service descriptors. It extends them.

## Target Architecture
The target architecture has five layers.

### 1. Interface descriptor layer
Each interface descriptor remains the authoritative description of operations, schemas, permissions, and state projections, but gains a new multimodal mediation section.

### 2. Interaction normalization layer
Voice, gesture, mouse, and agent actions are translated into the same canonical interaction envelope and then into the frame-first IR.

### 3. Policy compilation layer
Natural-language rules from the user are compiled by the `ipfs_datasets_py` logic stack into temporal-deontic policy objects and optional UCAN-compatible delegations.

### 4. Runtime mediation layer
Before an interface method is invoked, the runtime evaluates whether the normalized interaction is permitted, forbidden, required to confirm, rate-limited, or transformed into another action.

### 5. Audit and explanation layer
Every decision yields a receipt containing the control-surface source, normalized intent, relevant context, policy references, and explanation metadata.

## Proposed IDL Upgrade
Add a new top-level descriptor section named `control_surface_contract`.

This should be supported by Swissknife descriptors first and then mirrored in backend/mobile/spec artifacts.

### Proposed descriptor shape
```json
{
  "control_surface_contract": {
    "version": "0.1.0",
    "control_surfaces": [
      {
        "id": "voice",
        "kind": "voice_command",
        "event_types": ["utterance", "confirm", "cancel"],
        "intent_resolver": "nl_policy_compiler",
        "confidence_policy": {
          "min_confidence": 0.85,
          "clarify_below": 0.92
        }
      },
      {
        "id": "gesture",
        "kind": "captouch_or_wrist",
        "event_types": ["tap", "swipe", "hold", "wrist_raise"],
        "intent_resolver": "gesture_mapping_table"
      },
      {
        "id": "mouse",
        "kind": "pointer",
        "event_types": ["click", "double_click", "hover", "focus"],
        "intent_resolver": "pointer_mapping_table"
      },
      {
        "id": "agent",
        "kind": "ai_agent",
        "event_types": ["proposal", "autonomous_invoke", "scheduled_action"],
        "intent_resolver": "structured_agent_intent"
      }
    ],
    "intent_bindings": [
      {
        "intent": "display.focus_next",
        "method": "focus_next",
        "allowed_surfaces": ["gesture", "mouse", "voice", "agent"]
      },
      {
        "intent": "display.activate",
        "method": "activate",
        "allowed_surfaces": ["gesture", "mouse", "voice", "agent"]
      }
    ],
    "policy_hooks": {
      "compile_api": "ipfs_datasets_py.logic.api.compile_nl_to_policy",
      "evaluate_api": "ipfs_datasets_py.logic.api.evaluate_nl_policy",
      "decision_receipt": true
    },
    "context_schema": {
      "state_frames": ["sleeping", "driving", "meeting", "screen_locked"],
      "time_context": true,
      "location_context": true,
      "device_context": true,
      "agent_identity": true
    },
    "conflict_resolution": {
      "default": "deny_over_permit",
      "requires_explanation": true,
      "requires_user_confirmation_for": ["destructive", "financial", "communication.send"]
    }
  }
}
```

### Why this shape
- It preserves the existing interface/method schema.
- It avoids embedding raw logic expressions directly in the public descriptor.
- It separates static control-surface affordances from compiled dynamic policy state.
- It gives the runtime a stable place to attach resolution, mediation, and explanation metadata.

## Canonical Runtime Envelope
Every control surface should normalize into one envelope before policy evaluation.

### Proposed envelope
```json
{
  "interaction_id": "cid-or-uuid",
  "surface": "voice|gesture|mouse|agent",
  "surface_event": "utterance|tap|click|proposal",
  "raw_payload": {},
  "normalized_intent": {
    "intent": "display.activate",
    "method": "activate",
    "target_ref": "widget:primary-action",
    "arguments": {},
    "confidence": 0.94
  },
  "actor": {
    "type": "user|agent",
    "id": "...",
    "delegation_chain": []
  },
  "context": {
    "local_time": "2026-05-23T23:15:00-07:00",
    "state_frames": ["sleeping"],
    "device_mode": "quiet_hours",
    "platform": "meta_glasses"
  }
}
```

This envelope becomes the input to the policy layer and the source material for audit receipts.

## Logic Model
The right division of labor is:

### Frame logic for structural meaning
Use the existing frame-first IR in `hybrid_legal_ir.py` to model:
- what interface method an interaction targets,
- which entity or widget it acts on,
- which actor initiated it,
- which state the device and user are in.

Examples:
- `ActionFrame`: `activate(widget_action)`
- `EventFrame`: `wrist_raise`, `voice_utterance`, `mouse_click`, `agent_proposal`
- `StateFrame`: `sleeping`, `driving`, `focus_mode`, `display_locked`

### Event calculus for temporal mediation
Use temporal constraints to express when an interaction should or should not be active.

Examples:
- ignore wrist gestures during quiet hours,
- allow voice wake words only after a hardware wake event,
- suppress autonomous agent clicks while a human confirmation window is open,
- expire control grants after the user leaves a context.

### Deontic logic for normative decisions
Use deontic norms to express:
- permission: a surface may invoke a method,
- prohibition: a surface must not invoke a method,
- obligation: a system must request confirmation or must route through a safer surface.

Examples:
- a mouse click may activate a button,
- a gesture must not activate outbound communication while sleeping,
- an agent must ask for confirmation before sending a message.

## Natural-Language Rule Compilation
User-authored rules should enter as natural language and compile into policy artifacts, not ad hoc booleans.

### Example rule
"Ignore my wrist gestures at night, because I'm sleeping."

### Desired compilation path
1. Parse the sentence into a frame-first norm:
   - actor: user
   - surface: gesture / wrist
   - target: gesture-bound interface methods
   - condition: at night AND sleeping
   - effect: prohibit / suppress invocation
2. Compile into temporal-deontic policy clauses using `compile_nl_to_policy`.
3. Persist the compiled rule with a stable CID and explanation string.
4. Attach the policy CID to the active user profile and runtime mediation context.
5. Evaluate the rule for every gesture-originated interaction.

### Recommended compiler strategy
Use a two-lane policy compiler.

#### Lane A: strict template compiler
Use constrained templates for high-confidence user rules tied to device behavior.

Examples:
- "Ignore my {surface} at {time_window}."
- "Allow {surface} to {method} only when {state}."
- "Require confirmation before {method}."
- "Never let agents {method} unless I said yes."

This lane should compile deterministically and be the default for settings UI and profile rules.

#### Lane B: general natural-language compiler
Use the broader `NLUCANPolicyCompiler` pipeline for freeform user rules, with explanation output and clarification fallback.

This lane should be enabled behind review and confidence thresholds.

## Mediation Semantics
A policy decision must be richer than allow or deny.

### Proposed runtime decisions
- `allow`
- `deny`
- `require_confirmation`
- `defer`
- `rewrite`
- `fallback_surface`
- `rate_limit`

### Example cases
- Voice says "open this" with low target confidence -> `require_confirmation`
- Wrist gesture at night while `sleeping` state is active -> `deny`
- Agent proposes `send_message` without a grant -> `require_confirmation`
- Mouse click on a disabled widget -> `deny`
- Voice command unavailable on glasses display -> `fallback_surface` to mobile card or audio summary

## Descriptor Changes By Layer

### Swissknife descriptor layer
Extend descriptor builders so MCP-IDL profiles can advertise:
- supported control surfaces,
- per-method surface bindings,
- mediation defaults,
- and policy-hook metadata.

Initial implementation target:
- `swissknife/src/services/meta-glasses-mobile-orb-bridge.ts`

### Spec layer
Extend the JSON interface spec so control-surface contracts are portable across backend, mobile, simulator, and test fixtures.

Initial implementation target:
- `spec/meta_glasses_mobile_orb_bridge_interface.json`

### Backend layer
Extend bind/invoke/event routes to accept normalized control-surface envelopes and attach policy receipts.

Initial implementation targets:
- `src/handsfree/api.py`
- `src/handsfree/models.py`
- `src/handsfree/meta_glasses_mobile_orb_artifacts.py`
- new mediation module in `src/handsfree/`

### Mobile and simulator layer
Publish normalized voice/gesture/mouse/simulator events into the same ORB event path.

Initial implementation targets:
- `mobile/src/orb/`
- simulator artifacts under `dev/` and related tests

Remote-client rule:
- Meta-glasses, mobile, and simulator clients are remote interaction surface
  adapters for Hallucinate App, not separate policy or control-contract owners.
- Each path publishes a normalized `interaction_envelope` with the canonical
  `surface`, `surface_event`, `normalized_intent`, actor, context, descriptor
  refs, and correlation/receipt metadata required by the Hallucinate App
  mediator.
- Client-specific details stay in `raw_payload` and context metadata. Examples
  include DAT display state, Web App display actions, Neural Band/captouch
  values, mobile-card input, simulator trace entries, location, and sensor data.
- `context.platform` identifies `meta_glasses`, `mobile`, or `simulator`, while
  `context.device_context.remote_surface` records the concrete transport path
  such as `dat-native-display`, `meta-rayban-display-webapp`,
  `mobile-shell`, or `meta-rayban-display-simulator`.
- The mobile ORB bridge and simulator can cache edge-session and binding data,
  but the `policy_decision`, `mediation_receipt`, fallback routing, and final
  allow/deny/confirmation result come from Hallucinate App.

## Proposed New Runtime Modules
The upgrade should add a narrow mediation slice instead of baking policy logic into each route.

### Backend modules
- `src/handsfree/control_surface_intents.py`
  - normalize raw surface events into canonical interaction envelopes.
- `src/handsfree/control_surface_policy.py`
  - compile or resolve user policy bundles and perform decisions.
- `src/handsfree/control_surface_receipts.py`
  - emit stable mediation receipts and explanation payloads.
- `src/handsfree/control_surface_context.py`
  - build runtime context from time, device, profile, session, and state frames.

### Shared schema updates
- add `control_surface_contract` to descriptor artifacts
- add `interaction_envelope` schema
- add `policy_decision` / `mediation_receipt` schema

### `ipfs_datasets_py` extension points
Prefer reusing the current stable API surface before adding new logic modules.

Primary candidates:
- `ipfs_datasets_py.logic.api.compile_nl_to_policy`
- `ipfs_datasets_py.logic.api.evaluate_nl_policy`
- `ipfs_datasets_py.logic.integration.nl_ucan_policy_compiler.NLUCANPolicyCompiler`
- `ipfs_datasets_py.processors.legal_data.reasoner.hybrid_legal_ir`

Only add new upstream logic entry points if the current API cannot express multimodal device policies without leaking UI-specific assumptions into legal-domain modules.

## Control Surface Mapping Strategy
The same method should be invokable by different surfaces without duplicating business logic.

### Method-centric binding
Every interface method gets an intent id and a surface map.

Example:
- method: `activate`
- canonical intent: `display.activate`
- bound surfaces:
  - voice: utterances like "select", "open", "activate"
  - gesture: tap / pinch / wrist-tap patterns
  - mouse: click / enter key
  - agent: structured intent with delegation

### Surface-specific adapters
Each surface should only do enough work to normalize its own raw input.

Examples:
- voice adapter: ASR transcript -> intent candidates + confidence
- gesture adapter: captouch signal -> canonical gesture token
- mouse adapter: click/focus target -> canonical widget target
- agent adapter: action proposal -> structured intent + delegation context

The adapter must not decide final policy. That belongs to the mediation layer.

### Remote interaction surfaces
Meta-glasses hardware, the mobile companion shell, and the browser simulator are
client paths around those canonical adapters. They may expose different
capabilities and transports, but their control contract is the Hallucinate App
contract.

Mapping expectations:
- Meta-glasses DAT, Web App, Neural Band, captouch, display, audio, sensor, and
  location events normalize through the mobile edge before mediation.
- Mobile shell controls normalize as the same voice, gesture, pointer, or agent
  interaction envelopes used by the desktop shell.
- Simulator fixtures and traces replay the same envelopes so allowed, denied,
  confirmation-required, rewrite, and fallback cases can be compared with
  mobile diagnostics.
- No remote client introduces client-local `allowed_surfaces`,
  `policy_hooks`, or conflict-resolution rules that differ from the descriptor
  owned by Hallucinate App.

## Conflict Handling
Multimodal systems will create real conflicts.

### Common conflict classes
- two surfaces target the same method simultaneously,
- a user action conflicts with an autonomous agent action,
- one rule permits and another prohibits the same method,
- a gesture has low confidence and overlaps with another mapped gesture,
- a method is available on mouse but forbidden on glasses while sleeping.

### Resolution policy
Start with these defaults:
- explicit prohibition beats permission,
- live human input beats autonomous agent proposals,
- higher-confidence direct input beats lower-confidence inferred intent,
- confirmation obligations suspend autonomous execution,
- transport capability limits are evaluated after policy approval, not before.

Use the existing explanation path in the logic pipeline so denials and rewrites produce understandable traces.

## Persistence Model
Persist three things separately.

### 1. Static descriptor
The versioned interface descriptor with control-surface affordances.

### 2. Compiled user policy bundle
User rules compiled to policy objects and addressed by CID.

### 3. Runtime decision receipts
Per-invocation receipts containing:
- interaction envelope hash,
- descriptor CID,
- policy CID,
- decision status,
- explanation,
- downstream ORB receipt or denial reason.

This separation keeps descriptors stable while allowing user policy and runtime context to change independently.

## Phased Implementation Plan

### Phase 1: Descriptor contract definition
Define the new `control_surface_contract` schema and add it to one descriptor end to end.

Deliverables:
- schema extension in Swissknife descriptor builder
- mirrored JSON spec update
- backend model fields for control-surface metadata
- one canonical example descriptor for the Meta glasses mobile ORB bridge

Acceptance:
- one descriptor can advertise voice, gesture, mouse, and agent bindings for the same method set without ambiguity

### Phase 2: Canonical interaction envelope
Normalize all surface events into one envelope before invocation.

Deliverables:
- shared backend schema
- mobile/simulator adapters
- event publication path updates
- tests for envelope stability and receipt correlation

Acceptance:
- the same `activate` intent can arrive from mouse, gesture, voice, or agent and produce the same canonical operation target

### Phase 3: Policy compilation profile for device-control rules
Introduce a narrow rule profile focused on multimodal UI control, backed by the existing logic compiler.

Deliverables:
- strict rule templates for common device policies
- freeform NL rule compilation path with explanation output
- profile/schema for policy storage by user and device context

Acceptance:
- rules like sleep-time gesture suppression, confirmation for destructive actions, and agent gating compile into explainable policy artifacts

### Phase 4: Runtime mediation engine
Insert mediation between normalized interaction and ORB invocation.

Deliverables:
- policy evaluation module
- context builder for state frames and temporal constraints
- decision receipt generator
- backend route integration for bind/invoke/event flows

Acceptance:
- denied or gated interactions never reach the underlying method executor and always emit a structured explanation

### Phase 5: AI-agent delegation and policy bridge
Make AI-agent initiated actions use the same policy path, plus delegation metadata.

Deliverables:
- agent interaction envelope adapter
- delegation-chain capture
- policy rule support for agent-specific grants and prohibitions

Acceptance:
- an agent cannot invoke a control surface more broadly than the human user or policy grants permit

### Phase 6: Explainability and observability
Expose mediation decisions to diagnostics, simulator traces, and operator tooling.

Deliverables:
- mediation receipts in diagnostics endpoints
- structured logs and provenance refs
- simulator fixture support for allowed, denied, and confirmation-required interactions

Acceptance:
- every decision can be reconstructed from descriptor CID, policy CID, context snapshot, and interaction envelope

### Phase 7: Human authoring UX
Provide user-facing ways to manage rules without exposing raw logic syntax.

Deliverables:
- suggested rule templates
- generated explanations of current policy state
- conflict warnings for contradictory user rules

Acceptance:
- a non-technical user can author and understand rules like quiet-hours gesture suppression and confirmation requirements

## Testing Strategy

### Unit tests
- descriptor schema validation
- surface-to-intent normalization
- strict-rule template compilation
- mediation decision precedence
- explanation rendering

### Integration tests
- mobile ORB event -> mediation -> allowed invocation
- mobile ORB event -> mediation -> denied invocation
- agent proposal -> confirmation gate
- simulator trace replay through mediation pipeline

### Regression tests
- the same canonical intent from different surfaces resolves to the same target method
- user rules remain stable under paraphrase where the compiler claims semantic equivalence
- policy denials do not regress transport routing or widget rendering state

### Validation corpus
Create a curated corpus of multimodal policy statements and control events.

Seed examples:
- "Ignore my wrist gestures at night."
- "Let voice commands navigate widgets, but never send messages without confirmation."
- "Allow my mouse clicks on desktop, but not when the glasses are locked."
- "My assistant can open dashboards, but cannot post or purchase anything."

## Risks and Mitigations

### Risk: descriptor bloat
If too much runtime policy is embedded into the descriptor, versioning becomes fragile.

Mitigation:
- keep descriptors declarative,
- keep compiled policy bundles separate and CID-addressed,
- keep runtime context out of the static descriptor.

### Risk: NL rule ambiguity
Freeform rules can compile incorrectly.

Mitigation:
- start with strict templates,
- require explanation output,
- use clarification prompts below confidence thresholds,
- store both source text and compiled artifact.

### Risk: UI-specific logic leaking into upstream logic packages
If the logic layer learns too much about widgets or glasses, reuse will collapse.

Mitigation:
- keep the upstream logic layer framed in terms of actions, events, states, actors, and temporal constraints,
- keep interface-method and widget binding logic inside this repo.

### Risk: inconsistent surface mappings
Voice, gesture, and mouse adapters may drift.

Mitigation:
- make canonical intent ids part of the descriptor,
- validate adapters against a shared corpus,
- keep one source of truth for method-to-intent binding.

## Recommended First Implementation Slice
The smallest high-value slice is:

1. Extend the Meta glasses mobile ORB bridge descriptor with `control_surface_contract`.
2. Add a canonical interaction envelope for `gesture`, `voice`, `mouse`, and `agent` sources.
3. Implement one backend mediation path for `display.activate` and `display.focus_next`.
4. Support two user rule templates:
   - ignore `{surface}` at `{time_window}`
   - require confirmation before `{method}`
5. Emit mediation receipts in diagnostics.

This is the cheapest slice that can disconfirm the central design assumption. If it proves too awkward to express one method set across all four surfaces without descriptor or runtime contortions, the architecture should be revised before wider rollout.

## Success Criteria
- one descriptor can describe multiple control surfaces for the same method set,
- one runtime mediation engine can gate all four surface types,
- user-authored natural-language rules compile into explainable policy objects,
- denied actions are blocked before method execution and produce structured receipts,
- agent actions use the same policy pathway as direct user interaction,
- the simulator, mobile path, and backend tests all consume the same control-surface contract.

## Immediate Follow-On Tasks
After approving this plan, the next engineering tasks should be:

1. add the descriptor schema extension in Swissknife and the JSON spec,
2. add backend models for `control_surface_contract`, `interaction_envelope`, and `mediation_receipt`,
3. wire one strict-template policy compiler path using `ipfs_datasets_py.logic.api`,
4. connect the Meta glasses event path to the mediation layer,
5. add focused tests for sleep-time gesture suppression and confirmation-required agent actions.
