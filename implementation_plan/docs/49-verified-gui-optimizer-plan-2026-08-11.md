# VerifiedGuiOptimizer implementation and supervision plan

Date: 2026-08-11

Status: sealed for configured-board supervisor execution after control-plane
validation

Objective heap:
implementation_plan/docs/49-verified-gui-optimizer.objectives.md

Taskboard:
implementation_plan/docs/49-verified-gui-optimizer.todo.md

Task prefix: VGO-

Board namespace: verified-gui-optimizer-v1

Runtime root: data/agent_supervisor/verified_gui_optimizer

Initial application and screen: SwissKnife Agent Supervisor console,
application ID and route ID agent-supervisor

Primary target source: swissknife/web/js/apps/agent-supervisor.js

## Outcome and exact claim boundary

VerifiedGuiOptimizer is a standalone, evidence-driven GUI improvement
subsystem. For one bounded screen and one or a few declared objectives per
iteration, it will:

1. statically derive versioned component, state, action, layout, accessibility,
   route, policy, style, localization, test, and screenshot facts;
2. build a typed component/state dependency graph and compact semantic capsules;
3. calculate an explicit, bounded invalidation plan for a proposed change;
4. create a token-accounted context pack containing exact edit targets and
   compact unchanged context;
5. accept a bounded patch proposal or obtain one through a provider-neutral
   adapter;
6. apply the proposal only in an isolated Git worktree;
7. run affected checks first and expand deterministically when extraction
   confidence or impact closure is incomplete;
8. compare state reachability, interactions, accessibility observations,
   screenshots, and objective metrics against a content-addressed baseline;
9. reject regressions in required interaction, accessibility, confirmation,
   policy, security, and scope invariants; and
10. emit a content-addressed receipt that binds the repository, component
    versions, scenarios, artifacts, commands, outcomes, and evidence levels.

Formal machinery is used only for bounded structural and transition
properties. It does not prove beauty, emotional appeal, complete security,
complete accessibility, or global optimality. Visual hierarchy and perceived
polish remain heuristic or human-reviewed claims.

A claim is labeled formally verified only when a supported, exact bounded
obligation was discharged by the declared checker with all premises and tool
versions bound in its receipt. Parser validation, content integrity, tests,
screenshots, and heuristic assessments retain their distinct labels.

The required completion statement is:

> The selected GUI workflow was incrementally analyzed and improved against
> declared interaction, accessibility, policy, and visual-regression criteria,
> with content-addressed evidence for the evaluated scenarios.

The project must not state that the GUI is proved optimal.

## Reviewed source state and isolation

The plan is bound to these exact committed revisions:

| Repository | Reviewed commit | Role |
| --- | --- | --- |
| lift_coding superproject | ce448eae6ab5706832d3ae88b041f9d38ac82ae8 | control plan and gitlink authority |
| swissknife | 26f06277888b09a3e7c9b4a3b844001f1dbc0841 | target UI, browser tests, UI/UX IR interoperability |
| external/ipfs_datasets | a2f5400b7cb89c8481819379a1b7b9959fe81d45 | closed contracts, canonical identities, bounded constraints |
| external/ipfs_accelerate | ea11293bb996f052d620eae989f5377a956764b1 | reviewed agent supervisor, isolated execution, orchestration base |

Before sealing the board, one narrow accelerator control-plane change was
reviewed, tested, and committed as
`4784c932f87aafbd949714c05439836ab0f446a7`. It adds backward-compatible
configured-board projection for explicit retry-budget, dependency, and
reconciliation guardrail booleans. The VGO profile sets all three false; other
profiles retain their existing enabled defaults. This descendant is the
accelerator planning revision used at launch, while the table preserves the
exact implementation commit inspected before planning.

The user's original checkout contained unrelated tracked and untracked work in
all three repositories. Planning and supervisor execution therefore use the
dedicated clean worktree
/home/barberb/lift_coding/.worktrees/verified-gui-optimizer-control on branch
feature/verified-gui-optimizer. Datasets and SwissKnife are checked out at the
reviewed commits above; accelerator is checked out at the tested narrow
planning descendant recorded immediately below the table. No task may edit,
clean, reset, or use uncommitted code from the original checkout as
implementation authority.

The plan records source identities rather than trusting documentation or
submodule pins alone. Supervisor preflight must verify the current branch,
required ancestor, nested HEADs, clean submodules, protected control files, and
planning revision ancestry before any lane starts.

## Repository inspection findings

### Canonical SwissKnife surfaces

- The live target is web/js/apps/agent-supervisor.js. Its direct Playwright
  coverage is test/e2e/agent-supervisor-console.spec.ts; governed lifecycle
  coverage is test/e2e/agent-supervisor-goal-task-lifecycle.spec.ts.
- The canonical application inventory is
  src/services/apps/virtual-desktop-app-manifest.ts. The reviewed manifest
  contains 45 verified application definitions. The browser loader registry
  exposes 47 entries because it also includes host/remote entries. Counts and
  claims must be derived from source categories, not copied from prose.
- Browser mounting and one manually duplicated runtime registration map live in
  web/js/main-simple.js. The optimizer records both the canonical manifest and
  this runtime projection, and reports divergence rather than silently
  selecting one.
- The current UI/UX IR wire codec is
  src/services/mcp/ui-ux-ir-codec.ts with schema ui-ux-ir/v1. The bounded web
  renderer is src/services/mcp/ui-ux-ir-web-renderer.ts, and glasses projection
  uses src/services/glasses/ui-ux-ir-glasses-adapter.ts. These are stable
  interoperability inputs, not an existing GUI semantic scanner.
- Device and responsive projection logic is present in
  src/services/mcp/mcp-deontic-interface-broker.ts and related deontic
  manifests.
- Application action authority is described by
  src/services/apps/all-app-executable-backend-contract.ts and
  all-app-live-tool-bindings.ts.
- The browser-to-host choke point is
  src/services/mcp/all-app-tool-gateway.ts. It uses fixed same-origin routes and
  rejects credentials, arbitrary host paths, and process commands.
- src/services/mcp/mcp-control-surface-mediator.ts is the fail-closed policy
  mediator: it re-evaluates current actions and arguments, and presentation is
  not authorization. app-capability-policy.ts and
  mcp-deontic-ui-manifest.ts are supporting policy sources.
- Relevant boundary tests include
  test/browser/all-app-tool-gateway.test.ts,
  test/browser/agent-supervisor-console-gateway.test.ts,
  test/browser-compat/browser-deployment-policy.test.js, and
  test/mcp-plus-plus/ui-ux-ir-orb-mediation.test.ts.
- The canonical unit configuration is
  build-tools/configs/vitest.config.ts. Agent Supervisor Playwright uses
  build-tools/configs/playwright.agent-supervisor.config.ts; app improvement
  uses playwright.app-improvement.config.ts.
- scripts/run-virtual-desktop-app-improvement.mjs,
  test/e2e/virtual-desktop-all-app-improvement.spec.ts, and
  src/services/apps/virtual-desktop-app-audit-playwright-driver.ts provide
  existing screenshot and audit workflows.

### Canonical datasets and accelerator surfaces

- external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/canonical.py supplies
  strict canonical JSON behavior, Unicode normalization, collection
  semantics, and ambiguity rejection.
- logic/ir_core/identity.py supplies real domain-separated CIDv1/SHA-256
  identity. utils/cid_utils.py supplies strict DAG-JSON and CIDv1 helpers.
  Permissive serializers that fall back to repr are not identity authority.
- logic/software_verification/state.py and transitions.py provide reusable
  state/transition representations.
- logic/backends/smt/compiler.py supports bounded cvc5 and Z3 compilation.
  The installed cvc5 1.3.3 may be used after a capability probe. The installed
  Z3 4.16.0 is newer than the repository's declared maximum 4.15.4 and must
  not be treated as authoritative until the supported environment is pinned.
- logic/formalization/constraint_contracts.py and
  software_verification/receipts.py are reusable structural patterns; GUI
  wrappers remain closed and independently versioned.
- external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor contains the
  canonical implementation supervisor, lease/fencing logic, isolated
  worktrees, retry/watchdog support, and merge reconciliation.
- agent_supervisor/core/multiformats_identity.py is a second real CIDv1
  implementation suitable for cross-language identity vectors.
- proof/formal_verification_contracts.py may supply typed status vocabulary.
  No formal-verification cache is used.

### Legacy, duplicated, or insufficient surfaces

- swissknife/web/legacy-archive, emergency-archive, cleanup-archive,
  config/archive, and test/archived are not runtime authority.
- Older web/src component implementations and browser-main/main-working
  variants do not replace the live web/index.html and web/js/main-simple.js
  path.
- virtual-desktop-live-gateway.ts may synthesize a browser-side allow result
  from consent and therefore is not authorization authority for this project.
- Existing all-app accessibility coverage is primarily simulator and
  heuristic based. It is evidence, but not a full live-DOM accessibility
  audit and not WCAG certification.
- Existing screenshots are useful evidence captures but do not constitute a
  complete pixel-diff baseline system. Synthetic deterministic PNG fixtures
  must never be reported as browser screenshots.
- An untracked ipfs_datasets_py/logic/ui_ux_ir tree exists in the user's
  original checkout. It is not in the reviewed datasets commit and is
  explicitly excluded.

## Baseline commands and known pre-change failures

The SwissKnife package requires Node >=22.19.0. The host default during
inspection was Node 18.19.1. The clean control worktree was provisioned only
from the committed package lock with Node 22.19.0 and npm 10.8.2. The same
ignored, fixed toolchain directory is prepended to `PATH` for validator,
preflight, launch, and all managed lanes; the implementation daemon's bounded
shared-dependency mechanism exposes the lock-provisioned
`swissknife/node_modules` inside its managed worktrees.

Recorded commands and outcomes:

| Command | Baseline outcome |
| --- | --- |
| node --version | v18.19.1; below package engine |
| npm run test:e2e:app-improvement -- --app mcp-control | blocked under Node 18 by the engine/toolchain requirement; this reconnaissance preceded final target selection |
| npx -p node@22.19.0 -p npm@10.8.2 node scripts/verify-browser-toolchain.mjs | passed without changing repository dependencies |
| npm run test:e2e:app-improvement -- --app mcp-control under ephemeral Node 22 | Vite startup failed because the existing install lacks @ucans/ucans; this is a pre-change environment/dependency failure |
| focused Vitest run of ui-ux-ir-codec, ui-ux-ir-web-renderer, and mcp-dashboard-browser-policy | 43 of 44 passed; the pre-existing policy test expected “in-browser Python runtime” while source says “in-browser Python code interpreter” |
| broader focused manifest/UI/browser group | 94 passed and 4 failed; two manifest-loader assertions expected 39 importers rather than the current 45 application definitions, and two Node-18 zlib.crc32 failures were environment-specific |
| `npx --yes -p node@22.19.0 -p npm@10.8.2 npm ci` in the clean SwissKnife submodule | completed from the committed package lock; 3,014 packages installed; npm reported 117 pre-existing dependency audit findings (15 low, 56 moderate, 35 high, 11 critical); no audit rewrite was performed |
| eight focused target/policy/UI-IR Vitest files under the supported clean toolchain | 76 tests passed |
| Agent Supervisor governed lifecycle Playwright scenario under Node 22.19.0 | 1 test passed |
| direct `agent-supervisor-console.spec.ts` with the reviewed Playwright configurations | no test was discovered; the reviewed configurations exclude this file, so VGO-068 owns a dedicated target configuration |
| exact configured-board scheduler tests after the narrow sealed-guardrail projection change | 21 tests passed |
| existing strict-sharding supervisor tests | 17 of 19 combined checks passed; two pre-existing fixtures assume `ACCEL-001` maps to shard 1 although the runtime's full-ID SHA-256 rule maps it to shard 0 |

Playwright's expected Chromium build 1187 and headless shell were provisioned
in the operator cache. The dedicated VGO Playwright configuration still pins
`channel: chromium`, uses a path-derived unique port, disables server reuse,
and includes only the controlled VGO target specifications. A first missing-
browser failure and the existing configuration's no-test discovery are
recorded as baseline environment/configuration failures, not product
regressions.

Current declared SwissKnife commands are:

- build: cd swissknife && npm run build:web
- type checking: cd swissknife && npm run typecheck
- focused unit tests: cd swissknife && npm run test:run -- followed by
  explicit test paths
- target browser tests after VGO-068: cd swissknife && node
  scripts/run_playwright_test.mjs test -c
  build-tools/configs/playwright.verified-gui-optimizer.config.ts followed by
  the exact controlled VGO specification path
- governed lifecycle: the same configuration with
  test/e2e/agent-supervisor-goal-task-lifecycle.spec.ts
- current repository-wide screenshot workflow: cd swissknife && npm run
  test:e2e:app-improvement -- --all --viewport-matrix; the reviewed runner
  does not support combining `--viewport-matrix` with a single `--app`, so the
  optimizer adds a dedicated selected-screen viewport matrix
- current accessibility workflow: cd swissknife && npm run
  test:e2e:accessibility

VGO-068 must reproduce the selected target checks in the clean control
worktree with Node 22.19.0, install only from the committed lock, and record all
remaining failures before implementation. A known failure is never silently
converted into a post-change regression or ignored acceptance criterion.

## Selected target and bounded first improvement

The Agent Supervisor console is selected because it is stable, directly
tested, policy-sensitive, responsive, and already exposes deterministic
loading, ready, empty, failure, service-availability, confirmation, steering,
dispatch, and receipt states. It exercises all three package boundaries
without requiring production services.

Static inspection identified a bounded first candidate:

- update() replaces the entire root with outerHTML and then rebinds events;
  form or control focus can be lost across deterministic rerenders;
- steering and dispatch validation feedback is rendered but field-to-error
  association and invalid-state semantics require exact live-DOM verification;
  and
- controls use aria-disabled in places where native disabled semantics may
  better match the actual dispatch guard.

VGO-080 may implement only the accepted subset established by the baseline,
initially “preserve focus across controlled rerenders and associate form errors
without weakening confirmation or action guards.” It must declare intended
files, components, state changes, visual regions, tests, and screenshot
changes. If evidence does not confirm the premise, the task records a rejected
proposal instead of manufacturing a change.

## Hard dependency boundary

VerifiedGuiOptimizer is standalone. It must not import, call, require, or
derive authority from:

- a semantic-index module created by an earlier task;
- a semantic-capsule module created by an earlier task;
- a proof-cache or formal-verification-cache module;
- a model-routing or provider-routing module; or
- the untracked datasets UI/UX IR implementation.

The subsystem may reuse only stable reviewed primitives named in this plan:
strict canonical identity, basic state/transition IR, bounded SMT compilation,
the supervisor's lease/worktree mechanics, and SwissKnife's current public
manifest, policy, gateway, UI/UX IR wire codec, and browser test harness.

No content-addressed artifact cache is a proof cache. Receipts are immutable
evidence records; verification is recomputed for the current source/scenario
identity. The provider-neutral proposal interface exposes caller-selected
routes but does not choose or route models.

Narrow adapters in lift_coding or hallucinate_app are permitted only for
fixed-path CLI launch or schema interoperability. They may not become a new
authority layer.

## Architecture and repository ownership

### ipfs_datasets_py: closed evidence contracts

Create a narrowly scoped package under
external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer. It owns:

- closed, versioned Python models and unknown-field rejection;
- canonical bytes, real CIDv1/SHA-256 identity profiles, and golden vectors;
- bounded state and invariant contracts;
- typed evidence and receipt validation; and
- deterministic serialization used across package boundaries.

It does not scan repository code, apply patches, select models, or cache
proofs.

### SwissKnife: GUI observation and evaluation

Create narrowly scoped modules under swissknife/src/services/gui-optimizer.
They own:

- safe static JavaScript/TypeScript/TSX/JSX/HTML/CSS extraction;
- component/dependency graphs, state machines, semantic capsules, and
  invalidation;
- deterministic scenario fixtures;
- live-DOM accessibility, interaction, and screenshot observations;
- context-pack construction and token accounting; and
- target-specific evaluator and test adapters.

Static analysis uses parser APIs and direct file reads only. It never imports,
evaluates, bundles, or executes arbitrary repository source.

### ipfs_accelerate_py: bounded execution

Create a narrowly scoped package under
external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer.
It owns:

- proposal contracts and patch-scope enforcement;
- isolated worktree application;
- affected-check selection and conservative fallback;
- the journaled/resumable improvement state machine;
- provider-neutral proposal hooks; and
- CLI orchestration and final receipt assembly.

The executor accepts only repository-relative allowlisted paths and fixed
argument-vector commands. Browser input cannot supply paths or subprocesses.
Canonical branch mutation occurs only after an accepted patch has complete
evidence and the supervisor merge fence succeeds.

A task that changes more than one repository commits each nested repository
first, leaves every nested worktree clean, and hands off one atomic
superproject commit containing every changed gitlink plus any declared root
artifact. The merge queue serializes that handoff; a partial nested commit or
unrecorded gitlink is not task completion.

### Wire contract

Boundaries exchange closed JSON documents with explicit schema version,
identity profile, evidence classification, verification status, source
revision, and completeness boundary. Golden vectors require TypeScript and
Python to produce identical canonical bytes, digest, and real CID for the same
payload.

## Required closed models

At minimum implement these versioned schemas:

- GuiApplicationIdentity
- GuiScreenIdentity
- UiComponentIdentity
- UiComponentVersion
- UiDependencyEdge
- UiStateDefinition
- UiEventDefinition
- UiTransitionDefinition
- UiActionBinding
- UiLayoutConstraint
- UiAccessibilityContract
- UiSemanticCapsule
- UiChangeSet
- UiInvalidationPlan
- UiEvaluationScenario
- UiBaseline
- UiContextPack
- GuiImprovementProposal
- VisualRegressionReceipt
- AccessibilityReceipt
- InteractionReceipt
- UiConstraintReceipt
- GuiImprovementReceipt

Closed-schema decoders reject unknown keys, wrong enum values, malformed
identities, duplicate map keys, non-finite numbers, invalid path forms, and
unsupported schema versions. Optional fields are explicit rather than an
open extension bag.

Stable logical identities bind application ID, route/screen ID, component
qualified name, component kind, and package/interface namespace. Line numbers
are provenance spans, never primary identity.

Component version identity binds:

- stable identity;
- normalized JSX/TSX/HTML or template-literal structure;
- relevant props/types and component-local state;
- event, keyboard, focus, accessibility, and action bindings;
- imported styles, design tokens, media queries, and localization keys;
- optimizer schema version and extractor version.

Normalization excludes comments, unrelated sibling edits, absolute checkout
paths, and nonsemantic formatting. A meaningful target-component change must
change the version identity, while an unrelated edit elsewhere in a containing
file must not change the stable identity. All CID strings must be produced and
verified by a real CIDv1 implementation; CID-looking labels are forbidden.

## Static scanner and dependency graph

The scanner covers React functions/classes, TSX/JSX hierarchy, HTML and
template literals, routes, dialogs, menus, forms, buttons, links, inputs,
labels, validation, conditional states, props, local state, reducers, event
handlers, async operations, keyboard/focus behavior, ARIA, CSS modules, style
objects, design tokens, breakpoints, media queries, localization keys, action
and service/MCP bindings, confirmations, destructive actions, external
navigation, and browser-host crossings.

Every typed edge carries source/target stable identity, relation, source span
when present, extraction method, exact extractor version, and one of exact,
conservative, heuristic, or opaque confidence. Required relations are:

- renders, contains, routes_to;
- opens_dialog, closes_dialog;
- updates_state, reads_state;
- submits, validates, invokes_action;
- requires_confirmation, depends_on_policy, depends_on_schema;
- styled_by, uses_design_token, localized_by;
- tested_by, screenshot_by;
- responsive_variant_of, device_projection_of.

Dynamic component construction, runtime HTML insertion,
dangerouslySetInnerHTML, unknown plugins/widgets, dynamic styles or remote
scripts, constructed action names, unresolved browser globals, imperative DOM
mutation, uncontrolled delegation, or generated forms lowers classification
to conservative, heuristic, or opaque. Opaque targets require raw source in
the context pack and prevent automatic acceptance when the unresolved region
intersects a required invariant.

## Semantic capsules and evidence vocabulary

Each component/screen capsule includes stable identity, version identity,
application/screen, type, purpose, props, emitted events, state variables,
visible states, transitions, actions and side effects, action bindings,
confirmation, layout/responsive behavior, keyboard/focus behavior,
accessibility contract, localization, loading/empty/success/error behavior,
children/dependencies, tests, screenshots, known violations, unresolved
dynamic behavior, completeness boundary, analysis classification, and
verification status.

Analysis classification is one of:

- exact: parser-derived and fully resolved within the stated boundary;
- conservative: all known candidates retained but resolution is incomplete;
- heuristic: inferred description or metric requiring corroboration;
- opaque: behavior cannot be safely reduced by the extractor.

Verification status is independently one of:

- verified;
- structurally_valid;
- integrity_valid;
- unverified;
- stale;
- invalid;
- simulated.

Content identity proves integrity, not truth. A hash cannot promote a
heuristic visual description to verified. Simulated screenshots or actions
remain simulated.

## State extraction and bounded formal invariants

The selected screen's explicit state model covers initial, loading, ready,
empty, success, failure, confirmation, disabled, offline/unavailable,
terminal, and recovery states where applicable. Events cover click, submit,
cancel, Escape, keyboard activation, timeout, network success/failure,
validation failure, confirmation grant/denial, and service unavailability.

The exact finite graph validator and, where supported, the existing cvc5
compiler check the following bounded obligations:

### State completeness

- every declared event in a reachable state has an outcome or explicit no-op;
- no transition targets an undefined state;
- a nonterminal failure has a recovery or explicit terminal explanation;
- each represented asynchronous operation has loading and failure behavior;
- required actions are not reachable only through impossible states.

### Destructive, sensitive, and policy-shaped actions

- destructive actions require confirmation bound to exact action/arguments;
- presentation components do not access credentials;
- browser policy output is never authoritative;
- prohibited/disabled actions have no executable hidden dispatch path;
- displayed actions resolve to exactly one intended method and schema;
- current action and arguments are re-evaluated at runtime;
- a stale policy decision cannot authorize the current action.

### Form integrity

- every input has an accessible name;
- required inputs expose required-state semantics;
- errors associate with the relevant field;
- submission does not silently discard validation failure;
- success follows confirmed effect completion.

### Modal, focus, identity, and accessibility structure

- modal opening moves focus inside, Tab is contained, Escape/cancel is
  defined, closing restores initiating focus, and hidden elements do not
  retain interactive focus;
- rendered scenarios have no duplicate IDs;
- interactive controls have accessible names;
- meaningful images have alternatives and decorative images are hidden;
- nonnative controls have keyboard activation;
- heading structure remains intelligible.

Unsupported dynamic premises produce unverified or opaque receipts, never a
proof. These checks do not establish complete accessibility or security.

## Incremental invalidation

UiChangeSet normalization feeds an explicit UiInvalidationPlan with reasons,
affected identities, scenarios, checks, confidence, and fallback triggers:

| Change | Required direct invalidation |
| --- | --- |
| component implementation | component capsule, direct tests, containing screenshots, relevant accessibility scenarios |
| props/event contract | parents/consumers, action bindings, interface descriptors, tests |
| state machine | reachability/formal checks, interaction scenarios, loading/error/success screenshots |
| CSS/design token | dependent screenshots, responsive, contrast, clipping and overflow scenarios |
| action binding | policy/confirmation, browser-host boundary, invocation tests |
| localization | text-layout screenshots, accessible-name checks, affected locale scenarios |

Graph closure stops at typed dependency boundaries. An unrelated style change
must not invalidate every application screenshot. Missing, stale,
conservative, or opaque edges expand to a documented broader fallback rather
than pretending precision.

## Deterministic evaluation scenarios

Controlled fixtures for agent-supervisor cover:

- initial load;
- normal success;
- empty data;
- loading;
- recoverable error;
- unrecoverable error;
- invalid steering/dispatch input;
- valid confirmed submission;
- keyboard-only navigation;
- 390x844 narrow/mobile;
- 1280x800 standard desktop;
- 1600x1000 wide desktop;
- 200 percent text scaling or equivalent zoom;
- reduced-motion preference;
- dark mode when the screen advertises support;
- service unavailable;
- confirmation granted;
- confirmation denied.

Fixtures freeze application data, locale, timezone, animation, random values,
network outcomes, and service descriptors. They use no production
credentials, services, user/legal data, production MCP tools, or effectful
external operations.

Objective metrics include accessibility violation counts/severity, unlabeled
and keyboard-unreachable controls, focus order/trap failures, duplicate IDs,
contrast, horizontal overflow, clipping, viewport overflow, missing
loading/error behavior, interaction/keyboard steps, required action
reachability, confirmation and action-binding validity, test failures,
pixel-diff percentage, unexplained layout shifts, screenshot dimensions, and
missing/extra controls.

Visual hierarchy, density, consistency, clarity, whitespace, polish, and
primary-action prominence are labeled heuristic or human-reviewed. No
aesthetic gain may override an accessibility, policy, functional, security,
or confirmation regression.

## Visual, accessibility, and interaction evidence

Each VisualRegressionReceipt binds application/screen, component versions,
repository revision, scenario, viewport, color scheme, locale, text scale,
browser/version, screenshot CID/digest, baseline CID, pixel and structural
metrics, decision, and human-review requirement.

Deterministic comparison supports expected-change and forbidden-change
regions, a configured maximum unexplained difference, and a manual-review
threshold. Pixel changes are observations, not automatic regressions.
Browser-native ImageData comparison is preferred over a new pixel library.

Live accessibility evaluation uses existing facilities first. If live DOM
rules remain insufficient, one exact direct axe-core 4.6.3 dependency may be
added only with a recorded necessity decision and lockfile update; an
unpinned or unrelated audit dependency is forbidden. AccessibilityReceipt
separates automated passes, violations, manual checks, unsupported WCAG
criteria, keyboard result, and unperformed screen-reader review. Automated
success is not WCAG certification.

InteractionReceipt records steps, focus sequence, keyboard activation,
events, action invocations, confirmation identity, fixture effects, recovery,
and unresolved observations. Browser content never invokes privileged host
operations during these tests.

## Compact GUI context

Implement:

    build_gui_context_pack(
        repository_state,
        application_id,
        screen_id,
        objective,
        token_budget,
        baseline,
        violations,
    ) -> UiContextPack

The pack contains objective, exact target source, exact relevant CSS/tokens,
exact affected tests, capsules for unchanged parents/children, current state
machine, invariant failures, accessibility observations, screenshot
references/descriptions/artifact identities, routes/action bindings, metric
baseline, acceptance criteria, excluded-context explanation, estimated usage,
and escalation conditions.

Raw source is mandatory for files the proposal may edit, opaque or stale
components, implementation-dependent visual failures, unresolved
state/action bindings, and failures pointing into implementation. Stale
capsules cannot substitute for source.

The receipt records raw-source, capsule, screenshot-analysis, replaced-source,
and total estimated tokens plus compression ratio against ordinary raw
dependency retrieval. Token estimation is deterministic and conservative.
The benchmark target is at least 30 percent median reduction, but actual
results are reported even if below target.

## Bounded improvement loop and patch gate

The journaled loop is:

    baseline -> select explicit objective -> impact -> context pack
    -> bounded proposal -> isolated worktree -> rescan -> invalidation
    -> affected checks -> broader fallback if uncertain -> compare
    -> accept, reject, or require human review -> receipt

Each proposal declares intended files/components, state and visual changes,
acceptance criteria, test changes, and expected screenshot changes. The gate
rejects or requires review if it touches undeclared files, backend
authorization or credentials, arbitrary HTML execution, disabled security
checks, deleted tests, unrelated applications, configured file/line limits,
or unverified action-binding changes.

An accessibility or security/confirmation regression blocks automatic
acceptance even when clicks, pixels, or subjective ratings improve. A rejected
patch remains only in the disposable worktree and never mutates the canonical
branch. Interrupted runs resume from content-addressed journal state and
revalidate current Git identities before reusing observations.

The host-owned artifact store is a narrow immutable content-addressed evidence
CAS for screenshots, accessibility observations, traces, baselines, and
receipts. It is not a semantic index or proof cache and cannot turn an old
verification into current authority. Every reuse is gated by exact repository,
component, scenario, extractor, and checker identities.

The optional proposal interface accepts caller-selected routes:
deterministic transformation, small/local model, medium model, frontier model,
or human review. It does not implement model selection. Exact labels from a
form schema, deprecated-prop replacement, token substitution, ARIA reference
repair, and exact route/action migrations may be deterministic. Ambiguous
visual intent, opaque components, policy boundaries, repeated failures, or
constraint conflicts require escalation.

## CLI contract

Provide fixed developer commands equivalent to:

- gui-opt scan agent-supervisor
- gui-opt baseline agent-supervisor
- gui-opt impact path-or-component
- gui-opt evaluate agent-supervisor
- gui-opt pack-context agent-supervisor --objective objective
- gui-opt verify worktree-or-patch
- gui-opt improve agent-supervisor --objective objective
- gui-opt report run-id

CLI paths are repository-relative and allowlisted. Commands are fixed argument
vectors, not arbitrary shell strings. JSON output is schema-versioned and
stable for automation; human output links the same receipt IDs.

## Fixture and adversarial proof matrix

Controlled fixtures must cover:

- unlabeled input and missing error association;
- keyboard-inaccessible custom control and broken modal focus;
- duplicate DOM IDs;
- loading without failure;
- destructive action without confirmation;
- disabled action whose handler still dispatches;
- narrow overflow and localization clipping;
- stale capsule and opaque third-party component;
- unrelated style, changed design token, action-binding, and state-transition
  changes;
- out-of-scope patch;
- appearance improvement with accessibility regression;
- click reduction that bypasses confirmation;
- interrupted run and deterministic rerun.

Tests prove bounded invalidation, policy/interaction invalidation for bindings,
automatic rejection of accessibility/security regressions, raw inclusion for
opaque inputs, rejection of stale capsules, deterministic baseline identity,
canonical-branch isolation after rejection, complete accepted receipts, and
an evidence-level label for every visual/semantic claim.

## Initial 15-task benchmark

Run 15 controlled tasks against the selected screen/fixtures:

1. preserve focus across a controlled rerender;
2. add exact accessible names;
3. associate validation errors with fields;
4. add a missing failure/recovery state;
5. repair keyboard activation for a custom control;
6. prevent duplicate rendered IDs;
7. enforce exact destructive confirmation;
8. block a disabled hidden dispatch path;
9. remove narrow-viewport document overflow;
10. prevent localized text clipping;
11. improve empty-state guidance;
12. replace an inconsistent design token;
13. reduce steps for one non-sensitive task;
14. improve primary-action hierarchy under human review;
15. clarify unavailable-service recovery guidance.

For every task record baseline violations/screenshots, affected
components/scenarios, ordinary raw and compact context tokens, proposal files,
checks, changed screenshots, before/after objective and accessibility
metrics, interaction steps, decision, regressions, and deterministic/model/
human method.

Targets are at least 30 percent median context reduction, zero automatically
accepted critical accessibility regressions, zero automatically accepted
authorization/confirmation regressions, deterministic baseline/receipt
identities, bounded local invalidation, and measurable objective improvement
for accepted proposals. Target misses remain visible.

## Supervisor execution waves

Four strict full-ID SHA-256 hash-sharded lanes work in parallel. Within a wave,
predicted files and interfaces avoid shared mutable ownership; cross-package
contracts land before consumers. Dependencies, not the nominal wave, are the
execution authority. Objective/codebase refill and the retry-budget,
dependency, and reconciliation task producers are explicitly disabled so the
running supervisor cannot append unreviewed tasks to this exact 42-task
board. Exhausted attempts are surfaced to the operator instead of silently
expanding scope.

| Wave | Tasks | Parallel outcome |
| --- | --- | --- |
| 0 | VGO-000 | seal protected controls and reviewed-source inventory |
| 1 | VGO-001, VGO-002, VGO-009 | closed models, scanner skeleton, security authority |
| 2 | VGO-003, VGO-010, VGO-011 | scenario catalog, cross-runtime identity, graph |
| 3 | VGO-012, VGO-016 | semantic capsules and state extraction |
| 4 | VGO-020, VGO-021, VGO-023, VGO-027 | formal adapter, invariants, policy binding, invalidation |
| 5 | VGO-030, VGO-031, VGO-032, VGO-034 | context, live accessibility, visual, interaction |
| 6 | VGO-040, VGO-043, VGO-045 | evaluator/baseline, patch scope, proposal interface |
| 7 | VGO-041, VGO-050, VGO-051, VGO-061 | receipts, worktrees, affected checks, target fixtures |
| 8 | VGO-054, VGO-062 | durable run journal/artifact store and target semantic extraction |
| 9 | VGO-053 | integrated resumable improvement loop |
| 10 | VGO-060, VGO-070, VGO-071, VGO-075 | CLI bridge, fixture suites, cross-runtime identity conformance |
| 11 | VGO-068 | deterministic target browser/accessibility/visual baseline |
| 12 | VGO-072 | target baseline receipt conformance |
| 13 | VGO-083, VGO-086 | exact 15-task benchmark definitions and adversarial acceptance gates |
| 14 | VGO-080 | bounded target improvement through the integrated isolated loop |
| 15 | VGO-081 | original-defect and post-patch live regression evidence |
| 16 | VGO-090, VGO-096 | execute exact benchmark and bind architecture documentation |
| 17 | VGO-091 | independently audit automatic acceptances and live policy/browser gates |
| 18 | VGO-093 | full clean-tree integration verification at one evaluated revision |
| 19 | VGO-099 | content-addressed closeout report and receipt |

Task completion is evidence-driven. A lane may not mark a task complete based
only on code presence, a model statement, a process exit, or a hash.

## Supervisor launch, monitoring, and recovery

From the clean control worktree, bind the execution environment once and use
it unchanged for preflight, dry launch, real launch, and a clean resume:

```bash
REPO_ROOT=/home/barberb/lift_coding/.worktrees/verified-gui-optimizer-control
VGO_BIN="$REPO_ROOT/data/agent_supervisor/verified_gui_optimizer/toolchain/node_modules/.bin"
export PATH="$VGO_BIN:$PATH"
export PYTHONPATH="$REPO_ROOT/external/ipfs_accelerate:$REPO_ROOT/external/ipfs_datasets"
VGO_SCHEDULER="$REPO_ROOT/external/ipfs_accelerate/scripts/ops/agent_supervisor/configured_board_scheduler.py"
VGO_CONFIG="$REPO_ROOT/config/verified_gui_optimizer_scheduler.json"

python "$VGO_SCHEDULER" --repo-root "$REPO_ROOT" --config "$VGO_CONFIG" preflight
python "$VGO_SCHEDULER" --repo-root "$REPO_ROOT" --config "$VGO_CONFIG" launch --implement --dry-run
python "$VGO_SCHEDULER" --repo-root "$REPO_ROOT" --config "$VGO_CONFIG" launch --implement
```

The detached launch is permitted only after preflight and dry launch agree on
the sealed projection. Never rerun `launch` while the recorded master PID is
alive. A detached launch starts a new master; it does not adopt an existing
one. If a master dies while lane PIDs survive, inspect their lifecycle
identities, leases, fences, and locks and use the supervisor's reconciliation
and fencing mechanisms before a relaunch. Rerunning the exact launch command
is a resume only after the old master and lanes are cleanly stopped or fenced;
durable task and journal state is preserved.

The operator's read-only health snapshot is:

    python scripts/ops/verified_gui_optimizer_status.py --repo-root <clean-root>

It reports lifecycle `running`, `completed`, `blocked`, or `unhealthy`; actual
master/supervisor/daemon PID liveness; wrapper-status and relevant active-task
freshness; active task/CID/phase/attempt/worktree; implementation and merge
state; `task_count`, ready/eligible/waiting/blocked/external-reserved counts;
idle/attempt-limit reasons; orphaned lanes; and suggested non-mutating
diagnostics. Quiescent task-state projections are allowed to remain byte
stable. A legitimate all-lane terminal drain returns success even though the
master and lane processes have exited. The helper never rewrites taskboard,
runtime state, leases, or completion evidence.

Monitor:

- master PID and configured-board log under the runtime root;
- each lane's supervisor status, task state, PID, heartbeat, last progress,
  active task/CID/phase/attempt/worktree, completion counts, ready/selectable/
  waiting/blocked counts, idle reason, implementation/merge return codes,
  commits, and merge error;
- worktree leases, fencing tokens, merge queue, validation receipts, and Git
  cleanliness; and
- board terminal state independently of process liveness.

Intervention order:

1. distinguish active long-running validation from a stale heartbeat;
2. inspect the exact lane log, PID, task attempt, worktree, and dependency
   reason;
3. run board validation and one read-only/once supervisor reconciliation pass
   without editing or deleting durable runtime state;
4. correct only a reproducible source/config/test problem within its owning
   task, or let the built-in watchdog and AutonomousUnstallCoordinator retry;
5. rerun clean preflight and the exact launch command only when the master and
   lanes are genuinely stopped or safely fenced;
6. preserve crash fences, leases, rejected worktrees, and receipts.

Never delete state, invent a completion status, bypass validation, merge an
unverified worktree, or loosen a security invariant to unstall a lane. Because
all automatic task producers are disabled, an exhausted task remains visibly
blocked. Any board expansion requires a newly reviewed control-plane change,
fresh validator/preflight evidence, and a clean stopped supervisor; it is not
performed by a live lane. Completion requires every scheduled task terminal
with fresh validation and VGO-099 evidence, not merely all lane processes
exited.

## Security contract

- Browser content is untrusted and cannot access privileged host operations.
- UI visibility and enabled state never authorize an action.
- No browser-synthesized allow decision is accepted.
- Runtime policy is current and binds exact action and arguments.
- Fixtures use no real credentials, user/legal data, production services, or
  production MCP tools.
- Browser input cannot name arbitrary filesystem paths or subprocesses.
- Static analysis does not execute source or silently load remote scripts.
- Screenshot/accessibility success does not prove backend security.
- Backend authorization, credential handling, payments, deployment, and
  automatic release are out of scope.

## Deliverable and final-report gate

The terminal audit requires:

1. standalone semantic scanner;
2. component/state dependency graph;
3. closed semantic-capsule schema;
4. incremental invalidation plan;
5. bounded formal UI invariants;
6. deterministic scenario runner;
7. accessibility evaluator;
8. visual receipts;
9. compact context builder;
10. isolated improvement loop;
11. patch scope/acceptance enforcement;
12. CLI;
13. complete controlled fixtures;
14. 15-task benchmark report;
15. architecture document separating formal, structural, heuristic, and human
    evidence.

The final report binds selected screen and commits; changed modules; component
graph and state-machine statistics; implemented invariants; baseline
violations; accepted and rejected proposals; accessibility, interaction,
visual, token, invalidation, and proposal-method results; commands; unresolved
limits; and exact prerequisites for a second application.

The terminal receipt identity binds the evaluated source tree and the exact
SwissKnife, datasets, and accelerator gitlinks while excluding its own CID
field and later control-only task-status commits. The observed terminal
superproject commit is recorded separately, so the receipt never makes the
impossible claim that a commit content-addresses a file containing its own
identity. VGO-099 rehashes every referenced artifact and fails closed on an
unknown schema, missing artifact, source/gitlink mismatch, or stale evidence.

Applying to another screen requires a reviewed identity/route registration,
extractor coverage report, fixture scenario map, stable browser harness,
action/policy authority mapping, baseline screenshots and accessibility
evidence, acceptance thresholds, and a source-bound extension receipt. The
optimizer does not automatically expand to every SwissKnife application.

## Non-goals

This program does not build a design application, autonomous general UI
designer, MCP++ profile, backend authorization, payment system, production
deployment, whole-repository GUI rewrite, aesthetic proof, WCAG
certification, or automatic user release.
