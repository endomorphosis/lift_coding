# Steering-route build — progress (2026-10-14)

## Established architecture (code-verified)
- Console (swissknife/web/js/apps/agent-supervisor.js) steering pane submits
  capability `supervisor.prompt-steering.request` (method
  `agent_supervisor.prompt_steering.request`, governed-write, policy `confirm`,
  owner ipfs_accelerate_py) via `invokeCapability` → `window.agentSupervisorGateway`
  = desktop client's `createSupervisorGateway()` (web/js/core/mcp-plus-plus-desktop-client.js).
- Console payload: {target_type, target_id, prompt, dry_run,
  confirmation_token: `confirm-agent-supervisor:<type>:<id>:<clientRequestId>`
  (only when confirmed), client_request_id, expected_normalized_target}.
  Success data shape (normalizeSteeringAccepted): {request_id, accepted,
  dry_run, normalized_target, policy_class, affected_task_ids,
  planned_mcp_action, receipt{receipt_id,...}, event_dag}.
- Gateway today maps NO steering capability → typed capability_unavailable
  (B10). Audit3 R7: dry runs fall back to local preview ONLY when gateway
  result is unavailable/capability_unavailable — a real available result
  (incl. a denial) is passed through untouched.
- Gateway governed-write patterns to mirror: supervisorGovernedWriteDenial
  (requires payload.confirmation_token for governed-write; returns
  state:'denied', reason confirmation_required), invokeProfileGSupervisorWrite
  (requires access governed-write + payload.confirmed; demands receipt CID).
- Serving stack: vite :3001 → gateway rpc → accelerate compat adapter :3003
  (scripts/all-tools-evidence-lib.cjs startAccelerateCompatServer):
  Profile G methods → HTTP proxy to upstream :9000 REST bindings;
  tools/call → POST {upstream}/mcp/tools/<name> for tools in upstream's real
  list; mcp++/dag/* → adapter-local EventDag service.
- Upstream :9000 = `python -m ipfs_accelerate_py.mcp_server --fastapi`:
  FastAPI facade (Profile G REST catch-all → mcplusplus/profile_g_transport
  dispatcher, in-process store) + mounted MCP server app (server.py,
  HierarchicalToolManager) at /mcp with /mcp/tools list + /mcp/tools/<name>
  call routes. server.py registers an `agent_supervisor` category LAZILY
  (register_category_loader) — tools appear when the category is loaded.
- agent_supervisor MCP tools (package ipfs_accelerate_py/mcp_server/tools/
  agent_supervisor_tools/): catalog-driven factory over the closed Operation
  catalog; includes plan_create_preview/apply, plan_steer_preview/apply,
  workflow_preview/materialize (PDR-032). Control service resolved only at
  invocation; env allowlists AGENT_SUPERVISOR_*_ALLOWLIST.

## Backend steering candidates (code-verified)
- facade.Supervisor.steer(run_id, prompt): thin — validates run exists in the
  instance's in-memory _runs + non-empty prompt; returns observation with
  steering_prompt_cid (CID over body-free steer-ref) and effect_applied=False
  ("steer accepted as intent only; no policy widening"). NOTHING in the MCP
  server stack instantiates the facade Supervisor (no live session to steer;
  open() needs an authorized, activated production composition).
- api/external_handoff.ExternalHandoffAPI.steer: in-memory run registry,
  admission/authority-id session model; appends durable event to a run. Not
  hosted by the MCP server either.
- control plane plan_steer_apply (Operation.PLAN_STEER_APPLY): the supervisor's
  live create/steer surface, published as MCP tool
  agent_supervisor_plan_steer_apply on the upstream server; preview/apply pair
  (preview = no-mutation, apply = admitted mutation with permit/lease/fence/
  idempotency). Parameter contract is closed (control_contracts.py):
  apply requires apply_request or preview bindings (preview_ref/preview_root).

## Open questions for live probes
1. Does upstream /mcp/tools include agent_supervisor_plan_* tools (lazy
   category load triggered how?) and do they execute without allowlist env?
2. Profile G seeding via POST /mcp/goals + /mcp/tasks — shapes + read-back.
3. plan_create_apply minimal viable request → resulting plan identity/state;
   plan_steer_preview/apply round trip → observable revision change.

## Design (to finalize after probes)
Gateway maps supervisor.prompt-steering.request → governed write executed
against the accelerate backend's real steering surface; confirmation enforced
in the gateway via supervisorGovernedWriteDenial (confirmation_token), same
layer as receipts.persist/event-dag.checkpoint. Dry runs must NOT execute
(audit3 local preview preserved: gateway result for dry runs stays the
typed-unavailable path OR a real preview call — decide from probe evidence;
R7 fallback triggers only on unavailable/capability_unavailable).

## Deep-dive additions (verified, later same session)

- Upstream :9000 = fastapi_service.create_fastapi_app: explicit routes only
  /healthz + POST /mcp/policy/evaluate; the /mcp/{path} catch-all is the
  Profile G REST dispatcher (shadowing the mounted MCP tool app). Live:
  GET :9000/mcp/tools -> 404 "unknown MCP++ REST operation"; adapter upstream
  catalog real_tool_names = [] -> adapter tools/list = 18 facade tools;
  NO agent_supervisor_* tool is HTTP-reachable in this stack.
- prompt_entrypoints._open_supervisor(): injected Supervisor wins
  (configure_prompt_lifecycle_supervisor); otherwise a FRESH Supervisor.open()
  per call with an empty _runs registry (open() never rehydrates runs).
  Repo-wide grep: no production caller of configure_prompt_lifecycle_supervisor.
  => A serving route must HOST one long-lived session (the designed embedder hook).
- Production scheduler config: service_factory.SCHEDULER_CONFIG_RELATIVE =
  config/agent_supervisor_prompt_only_self_improvement_v3_scheduler.json;
  EXISTS in the ipfs_accelerate checkout; protected_runtime_activation =
  ASE3-026 completed, objective refill + monitor enabled.
- probe_facade.py (repo=lift_coding): open() -> SupervisorConfigurationError
  "no production scheduler config ... open from an authorized repository root".
- probe_facade2.py (repo=external/ipfs_accelerate): open() SUCCEEDS;
  run() FAILS: facade._run_from_prompt -> prompt/plan_create_service.py ->
  analysis/planning_analysis_factory.py -> imports
  ipfs_datasets_py.logic.formalization.autoencoder.source_screening ->
  ModuleNotFoundError. Module verified MISSING from both datasets checkouts
  (pinned submodule + ~/workspace/ipfs_datasets_py). Cross-repo pin skew;
  datasets logic is outside this build's edit scope.
- facade.steer semantics: returns SupervisorObservation with values
  {steering_prompt_cid, effect_applied: False} — admitted intent record by
  design ("steer accepted as intent only; no policy widening"); mutates nothing.
- Accelerate upstream's Profile G service = datasets get_profile_g_service()
  with NO validators -> its mutations fail closed (G_AUTHORITY_DENIED) by
  design; the datasets adapter worker uses ProfileGService(trusted_local=True),
  so the console target seed chain goes through :3002. Console snapshot reads
  merge Profile G across services, so the seeded task surfaces as a target.

## BOUNDARY (precise)
Route dispatch is genuine end-to-end; the terminal step that cannot complete
today is RUN CREATION (Supervisor.run blocked by the missing datasets module
ipfs_datasets_py.logic.formalization.autoencoder.source_screening). The worker
surfaces that exact typed failure fail-closed; no receipt is fabricated. When
the datasets pin gains that module, the same route executes unchanged: the
worker seeds its session run at startup and steers it.

## Route design (as built)
1. NEW swissknife/scripts/mcpplusplus-supervisor-steering.cjs — persistent
   Python worker bridge (JSON-lines, Profile G bridge pattern). Worker opens
   ONE production Supervisor for the server-configured repository (env
   IPFS_ACCELERATE_AGENT_REPOSITORY, default sibling external/ipfs_accelerate;
   never client-supplied), injects it via configure_prompt_lifecycle_supervisor,
   attempts the seed run (env IPFS_ACCELERATE_SUPERVISOR_SEED_PROMPT or a
   default backlog prompt), dispatches agent_supervisor_steer + same-session
   agent_supervisor_status read-back.
2. all-tools-evidence-lib.cjs startAccelerateCompatServer: JSON-RPC branch for
   agent_supervisor.prompt_steering.request -> steering bridge; failure ->
   JSON-RPC error -32051 with the real backend message (fail-closed).
3. mcp-plus-plus-desktop-client.js createSupervisorGateway:
   supervisor.prompt-steering.request ->
   dry_run: same typed capability_unavailable result as before (R7 local
     preview fallback engages; backend never called);
   no confirmation_token: supervisorGovernedWriteDenial
     (denied/confirmation_required, same layer as receipts.persist);
   confirmed: rpc ipfs_accelerate_py agent_supervisor.prompt_steering.request;
     success -> governedActionAccepted data with REAL receipt from the
     backend steering_prompt_cid; failure -> server_unavailable with the
     real cause (never capability_unavailable -> no preview masking).
4. Console agent-supervisor.js: unchanged.

## Status
- [x] Investigation + probes
- [x] Steering bridge module (scripts/mcpplusplus-supervisor-steering.cjs)
- [x] Adapter JSON-RPC branch (all-tools-evidence-lib.cjs) — live probe adapter-steer-probe.json: session open=true, composition baguqeerauqzq7q…, run blocked at the named datasets module
- [x] Gateway mapping (invokeSupervisorPromptSteering) — check_gateway.mjs PASSED (dry-run typed / unconfirmed denied / confirmed dispatched + verbatim cause)
- [x] Unit checks (gateway + adapter)
- [x] Profile G seed chain (artifacts validate locally; wire = G_AUTHORITY_DENIED fail-closed, seed_profile_g.out) + Playwright drive (drive-results.json, drive-confirmed-results.json, fv-18/fv-19): dry-run local preview rcpt-prompt-steering-d0d1923a, confirmed -> server_unavailable with verbatim ModuleNotFoundError cause
- [x] Docs: BROKEN_CONTRACT_MAP.md (P17, B10 rewritten, S1-S3 fix table), FEATURE_MATRIX.md (F-15, fv-18/19), SWISSKNIFE_FIX_NOTES.md (steering-route section)
- [x] audit3 check_fix2 PASSED; vitest batch 1 = 17/17; batch-2 surface = only pre-existing B9 failure
- [x] Integration suite re-run: 528 passed / 29 skipped / 0 failed (283.91 s) — baseline held exactly
