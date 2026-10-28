# SwissKnife Real Desktop Objective Heap (SVF)

Profile: `config/swissknife_visual_functional_supervisor.json`. Execution board: `implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.todo.md`. Full requirements: `swissknife/config/visual-functional-app-contracts.json`.

All goals begin active. Passing tasks supplies evidence; it does not promote a goal to verified_complete. The canonical goal lifecycle owns that separate decision.

## SVF-G000 All 45 actual desktop applications perform their intended user workflows with truthful MCP++ integration

- Status: active
- Parent: 
- Priority: P0
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G000
- Goal: All 45 actual desktop applications perform their intended user workflows with truthful MCP++ integration
- Evidence: 
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Fresh desktop/mobile visual inspection, semantic workflow and recovery evidence for every canonical app, genuine relevant backend outcomes, and all cross-app regressions; objective verification remains separately governed.

## SVF-G001 Canonical plan ingestion and safe autonomous execution

- Status: active
- Parent: SVF-G000
- Priority: P0
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G001
- Goal: Canonical plan ingestion and safe autonomous execution
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-000/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Canonical plan ingestion and safe autonomous execution

## SVF-G010 Exact model route and real three-owner backend readiness

- Status: active
- Parent: SVF-G000
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G010
- Goal: Exact model route and real three-owner backend readiness
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-010/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-011/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-040/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-041/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-042/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Exact model route and real three-owner backend readiness

## SVF-G020 Actual desktop visual baselines and actionable findings for every application

- Status: active
- Parent: SVF-G000
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G020
- Goal: Actual desktop visual baselines and actionable findings for every application
- Evidence: 
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Actual desktop visual baselines and actionable findings for every application

## SVF-G030 Trustworthy workflow runner, compact usable UI and accessible recovery

- Status: active
- Parent: SVF-G000
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G030
- Goal: Trustworthy workflow runner, compact usable UI and accessible recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-030/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Trustworthy workflow runner, compact usable UI and accessible recovery

## SVF-G040 Application-specific repairs with preserved intended behavior

- Status: active
- Parent: SVF-G000
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G040
- Goal: Application-specific repairs with preserved intended behavior
- Evidence: 
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Application-specific repairs with preserved intended behavior

## SVF-G050 Current full regression and cross-application workflows

- Status: active
- Parent: SVF-G000
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G050
- Goal: Current full regression and cross-application workflows
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-900/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-910/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-920/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-930/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Current full regression and cross-application workflows

## SVF-G090 Evidence-based closeout without historical or model self-certification

- Status: active
- Parent: SVF-G000
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G090
- Goal: Evidence-based closeout without historical or model self-certification
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-990/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Evidence-based closeout without historical or model self-certification

## SVF-G101 Image Viewer: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G101
- Goal: Image Viewer: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-110/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-111/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-112/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-113/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: An image is visibly decoded with positive natural dimensions; transformed image remains usable and CID bytes match; Reopen the same real artifact and compare decoded dimensions and bytes; Absent CID, corrupt bytes or unsupported format never becomes a blank success

## SVF-G101-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G101
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G101-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-110/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-111/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G101-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G101
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G101-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-112/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G101-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G101
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G101-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-113/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G102 Notes: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G102
- Goal: Notes: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-120/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-121/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-122/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-123/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Saved/reopened text matches the editor and search returns relevant actual notes with meaningful provenance; Reload or retrieve the note artifact and compare exact title/body plus conflict state; Storage failure, conflicting edit or failed search retains unsaved text

## SVF-G102-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G102
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G102-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-120/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-121/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G102-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G102
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G102-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-122/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G102-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G102
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G102-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-123/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G103 Accelerate Panel: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G103
- Goal: Accelerate Panel: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-130/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-131/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-132/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-133/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Actual model output is usable for the input; queue/running/terminal states reflect owner state and preview is not execution; Reopen the real run record and match selected model, input, output and timestamps; Unsupported model, invalid input or no capacity stays visible and preserves form input

## SVF-G103-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G103
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G103-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-130/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-131/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G103-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G103
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G103-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-132/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G103-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G103
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G103-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-133/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G104 SwissKnife Terminal: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G104
- Goal: SwissKnife Terminal: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-140/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-141/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-142/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-143/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Output describes the real local operation, history retains entered commands, and the prompt remains usable; Reopen the terminal and verify declared history retention without inventing a remote shell; Unsupported command or command timeout leaves a readable result and an enabled prompt

## SVF-G104-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G104
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G104-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-140/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-141/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G104-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G104
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G104-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-142/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G104-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G104
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G104-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-143/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G105 VibeCode: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G105
- Goal: VibeCode: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-150/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-151/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-152/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-153/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Editor and reopened bytes contain the intended change; diff and any requested analysis describe that function; Reopen the returned artifact and compare exact saved UTF-8 bytes with the editor content; Invalid source or unavailable storage retains unsaved edits and exposes a useful error

## SVF-G105-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G105
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G105-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-150/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-151/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G105-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G105
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G105-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-152/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G105-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G105
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G105-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-153/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G106 Music Studio: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G106
- Goal: Music Studio: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-160/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-161/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-162/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-163/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Track/note state reflects edits and audible playback or a truthful audio-permission state is present; Reopen the saved local project and compare tracks, tempo and edited notes; Denied audio permission or invalid project does not claim successful playback

## SVF-G106-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G106
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G106-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-160/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-161/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G106-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G106
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G106-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-162/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G106-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G106
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G106-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-163/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G107 AI Chat: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G107
- Goal: AI Chat: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-170/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-171/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-172/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-173/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Answer addresses the known question, cites retrieved content and preserves user/assistant messages with authentic owner results; Reopen the stored conversation and verify message text and citation targets; Unavailable model or failed retrieval leaves the user prompt editable and shows the actual failure

## SVF-G107-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G107
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G107-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-170/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-171/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G107-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G107
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G107-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-172/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G107-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G107
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G107-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-173/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G108 File Manager: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G108
- Goal: File Manager: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-180/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-181/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-182/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-183/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Selection, preview and reopened file agree with actual bytes; the original remains intact; Reload or reopen the returned artifact and compare content and metadata; Missing folder, storage failure or filename conflict preserves selection and explains the problem

## SVF-G108-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G108
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G108-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-180/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-181/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G108-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G108
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G108-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-182/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G108-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G108
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G108-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-183/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G109 Task Manager: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G109
- Goal: Task Manager: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-190/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-191/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-192/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-193/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: List and filter reflect the actual open applications; unavailable host metrics are explicitly labeled; Reopen Task Manager and reconcile state against currently open desktop applications; Stale or unavailable task source is marked with its observation time rather than fabricated metrics

## SVF-G109-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G109
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G109-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-190/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-191/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G109-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G109
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G109-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-192/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G109-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G109
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G109-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-193/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G110 Todo and Goals: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G110
- Goal: Todo and Goals: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-200/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-201/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-202/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-203/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Edited title and completion state are correct; dependencies are shown honestly without claiming remote dispatch; Reload the local task list and verify task identifiers, edited title and completion state; Invalid/empty title or unavailable local storage leaves existing tasks intact

## SVF-G110-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G110
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G110-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-200/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-201/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G110-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G110
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G110-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-202/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G110-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G110
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G110-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-203/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G111 AI Model Manager: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G111
- Goal: AI Model Manager: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-210/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-211/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-212/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-213/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Selected model is in the owner catalog; a terminal owner result contains usable prompt-related output and actual run status; Reopen the run artifact or history and match selected model, input and actual output; Unsupported model or insufficient capacity does not display a fabricated generated answer

## SVF-G111-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G111
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G111-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-210/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-211/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G111-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G111
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G111-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-212/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G111-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G111
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G111-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-213/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G112 Hugging Face Hub: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G112
- Goal: Hugging Face Hub: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-220/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-221/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-222/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-223/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Selected card and prepared artifact refer to the same actual item; unsupported download or inference stays explicit; Reopen stored selection metadata and compare repository identity and immutable revision where available; Offline provider, rate limit or missing credential keeps filters and selection usable

## SVF-G112-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G112
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G112-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-220/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-221/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G112-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G112
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G112-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-222/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G112-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G112
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G112-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-223/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G113 OpenRouter Hub: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G113
- Goal: OpenRouter Hub: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-230/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-231/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-232/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-233/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Actual provider output or truthful unavailable/authentication state is visible; secret values never enter DOM or evidence; Reopen only nonsensitive provider preferences or conversation state supported by the app; Missing credential, quota or provider error never masquerades as a Python-owner result

## SVF-G113-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G113
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G113-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-230/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-231/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G113-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G113
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G113-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-232/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G113-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G113
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G113-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-233/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: External-provider boundary; no Python-owner dispatches and no credentials in DOM, console, requests recorded to evidence or screenshots.

## SVF-G114 IPFS Explorer: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G114
- Goal: IPFS Explorer: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-240/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-241/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-242/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-243/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Retrieved bytes hash to the requested CID and visible preview matches their type; pin state is actual observed state; Reopen the same CID and compare exact bytes and displayed metadata; Invalid or absent CID shows a readable error without replacing good content with fake data

## SVF-G114-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G114
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G114-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-240/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-241/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G114-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G114
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G114-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-242/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G114-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G114
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G114-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-243/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G115 Device Manager: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G115
- Goal: Device Manager: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-250/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-251/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-252/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-253/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser device access and owner hardware are labeled separately; values have a real source and observation time; Reopen the device view and distinguish retained selection from newly observed hardware state; Denied permission or unsupported diagnostic never claims a scan or benchmark occurred

## SVF-G115-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G115
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G115-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-250/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-251/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G115-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G115
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G115-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-252/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G115-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G115
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G115-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-253/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G116 Settings: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G116
- Goal: Settings: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-260/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-261/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-262/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-263/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Saved preference changes actual browser UI state; invalid values remain rejected and reversible; Reload and verify saved value then restore the original setting; Invalid preference or failed persistence leaves last saved state intact

## SVF-G116-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G116
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G116-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-260/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-261/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G116-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G116
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G116-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-262/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G116-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G116
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G116-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-263/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G117 MCP Control: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G117
- Goal: MCP Control: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-270/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-271/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-272/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-273/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Schema, owner, exact tool and result agree; actual status and authentic correlation/receipt are inspectable; Reopen the diagnostic detail and match retained receipt and result to its owner/tool; Owner outage or invalid parameters show a specific failure and retain the selected tool

## SVF-G117-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G117
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G117-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-270/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-271/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G117-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G117
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G117-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-272/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G117-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G117
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G117-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-273/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G118 API Keys: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G118
- Goal: API Keys: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-280/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-281/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-282/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-283/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Credential values are absent from rendered/evidence output and every Python-owner dispatch remains policy-blocked; Reopen only opaque reference metadata and verify removal or saved reference state; Invalid reference or denied action exposes policy guidance without leaking credential values

## SVF-G118-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G118
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G118-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-280/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-281/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G118-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G118
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G118-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-282/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G118-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G118
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G118-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-283/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Credential-isolation boundary; Python-owner dispatch stays policy-blocked and only opaque local reference metadata may be evidenced.

## SVF-G119 GitHub: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G119
- Goal: GitHub: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-290/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-291/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-292/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-293/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Displayed repository/file identity and review evidence refer to actual selected content; any write remains confirmation-bound; Reopen the retained review artifact and compare repository identity and content revision; Authentication, rate limit or missing repository yields an actionable actual error

## SVF-G119-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G119
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G119-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-290/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-291/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G119-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G119
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G119-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-292/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G119-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G119
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G119-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-293/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G120 OAuth Login: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G120
- Goal: OAuth Login: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-300/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-301/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-302/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-303/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Provider lifecycle is truthful; authorization codes/tokens are not rendered, logged or retained in screenshots; Reopen only opaque session status and verify logout/expiration behavior; Blocked popup, rejected scope or unavailable provider remains an external auth failure

## SVF-G120-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G120
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G120-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-300/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-301/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G120-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G120
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G120-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-302/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G120-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G120
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G120-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-303/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: External-provider boundary; no Python-owner dispatches and no credentials in DOM, console, requests recorded to evidence or screenshots.

## SVF-G121 AI Cron: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G121
- Goal: AI Cron: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-310/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-311/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-312/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-313/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Next-run and paused state match local configuration; local timers are not labeled backend jobs; Reload to verify retained schedule state, then verify deleted schedule is absent; Invalid schedule expression or past/ambiguous time has a clear inline error

## SVF-G121-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G121
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G121-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-310/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-311/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G121-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G121
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G121-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-312/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G121-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G121
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G121-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-313/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G122 NAVI: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G122
- Goal: NAVI: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-320/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-321/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-322/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-323/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Matched context is relevant and any executed action has an actual owner result; ambiguity is not silently guessed; Reopen retained intent/context history if supported and preserve the selected target; No match, owner outage or ambiguous target retains the editable original intent

## SVF-G122-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G122
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G122-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-320/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-321/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G122-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G122
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G122-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-322/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G122-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G122
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G122-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-323/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G123 P2P Network Manager: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G123
- Goal: P2P Network Manager: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-330/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-331/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-332/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-333/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Known peer, connected peer and empty swarm states are distinct and come from actual owner responses; Reopen the view and refresh current peer state rather than replaying stale connectivity; Owner offline or unavailable transport marks data stale/unavailable without invented peers

## SVF-G123-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G123
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G123-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-330/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-331/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G123-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G123
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G123-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-332/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G123-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G123
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G123-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-333/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G124 P2P Chat: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G124
- Goal: P2P Chat: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-340/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-341/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-342/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-343/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: A sent/delivered state is supported by actual peer acknowledgement; queued is not delivered; message content remains exact; Reopen local conversation and compare message body, peer identity and delivery state; Offline peer, denied send or owner outage preserves the unsent message

## SVF-G124-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G124
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G124-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-340/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-341/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G124-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G124
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G124-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-342/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G124-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G124
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G124-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-343/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G125 Neural Network Designer: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G125
- Goal: Neural Network Designer: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-350/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-351/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-352/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-353/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Graph geometry and schema agree; invalid shapes are rejected; any compile result belongs to the exact saved graph; Reopen the graph artifact and compare node IDs, edges and parameters; Invalid edge or unavailable compile capability does not claim successful compilation

## SVF-G125-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G125
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G125-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-350/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-351/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G125-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G125
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G125-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-352/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G125-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G125
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G125-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-353/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G126 Training Manager: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G126
- Goal: Training Manager: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-360/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-361/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-362/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-363/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Job identity, queue/running/terminal transitions and output/checkpoint are actual owner state; previews are labeled previews; Reopen the real run/checkpoint record and match input dataset and selected model; Invalid data, no capacity or failed job leaves configuration editable and exposes actual cause

## SVF-G126-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G126
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G126-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-360/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-361/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G126-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G126
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G126-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-362/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G126-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G126
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G126-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-363/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G127 Calculator: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G127
- Goal: Calculator: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-370/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-371/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-372/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-373/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: 12.5 × 4 equals 50; invalid arithmetic remains explicit; history restores the exact expression without fake proof IDs; Reopen supported local history and compare expression/result; Division by zero or invalid expression leaves keypad and clear/backspace usable

## SVF-G127-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G127
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G127-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-370/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-371/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G127-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G127
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G127-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-372/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G127-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G127
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G127-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-373/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G128 Clock and Timers: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G128
- Goal: Clock and Timers: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-380/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-381/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-382/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-383/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Elapsed timer state follows wall time within declared tolerance and notification state is honest; Reload and verify retained alarm and declared timer behavior without inventing remote scheduling; Denied notifications or invalid alarm time is visible without claiming delivery

## SVF-G128-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G128
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G128-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-380/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-381/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G128-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G128
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G128-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-382/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G128-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G128
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G128-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-383/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G129 Calendar and Events: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G129
- Goal: Calendar and Events: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-390/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-391/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-392/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-393/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Event is on the correct date/time, edit persists and overlapping events remain understandable; Reload and verify event title, timezone and time; delete the disposable event after verification; Invalid date/time or conflicting input shows recoverable validation

## SVF-G129-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G129
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G129-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-390/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-391/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G129-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G129
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G129-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-392/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G129-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G129
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G129-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-393/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G130 PeerTube: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G130
- Goal: PeerTube: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-400/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-401/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-402/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-403/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Video frames or supported audio decode, playback time advances, seeking changes time and failure is honest; Reopen saved selection/history if supported and compare real media identity; Unavailable CID/source or codec failure retains playback controls and useful recovery

## SVF-G130-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G130
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G130-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-400/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-401/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G130-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G130
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G130-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-402/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G130-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G130
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G130-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-403/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G131 Friends and Network: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G131
- Goal: Friends and Network: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-410/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-411/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-412/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-413/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Contact identity and state changes are actual retained records; unavailable presence is not called online; Reload and verify contact name and relationship/blocking state; Missing identity, denied update or stale presence has a clear visible explanation

## SVF-G131-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G131
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G131-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-410/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-411/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G131-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G131
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G131-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-412/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G131-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G131
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G131-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-413/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G132 Media Player: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G132
- Goal: Media Player: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-420/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-421/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-422/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-423/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Playback currentTime advances, seek position is honored and media identity/duration come from decoded content; Reopen the supported playlist/selection and compare media identity and ordering; Missing codec, unavailable source or denied audio displays an actual recoverable failure

## SVF-G132-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G132
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G132-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-420/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-421/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G132-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G132
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G132-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-422/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G132-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G132
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G132-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-423/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G133 System Monitor: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G133
- Goal: System Monitor: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-430/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-431/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-432/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-433/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Values come from actual observations, stale age is explicit and unavailable metrics are never randomly generated; Reopen and distinguish retained chart history from fresh samples; Owner failure marks the last sample stale/unavailable and does not fabricate a new sample

## SVF-G133-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G133
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G133-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-430/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-431/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G133-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G133
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G133-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-432/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G133-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G133
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G133-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-433/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G134 Neural Photoshop: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G134
- Goal: Neural Photoshop: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-440/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-441/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-442/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-443/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Canvas pixels/layer state reflect the edit; actual output image decodes and corresponds to the requested operation; Reopen stored result/source and compare dimensions, bytes and editable project metadata where supported; Invalid image, policy denial or failed job leaves original and edits recoverable

## SVF-G134-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G134
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G134-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-440/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-441/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G134-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G134
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G134-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-442/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G134-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G134
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G134-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-443/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G135 Cinema: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G135
- Goal: Cinema: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-450/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-451/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-452/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-453/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Timeline changes persist; export is an actual playable artifact or clearly unsupported, never a fabricated render; Reopen project and compare track ordering, clip trim points and output reference; Unsupported codec, export failure or owner outage preserves the project and last good media

## SVF-G135-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G135
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G135-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-450/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-451/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G135-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G135
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G135-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-452/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G135-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G135
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G135-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-453/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G136 Strudel: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G136
- Goal: Strudel: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-460/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-461/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-462/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-463/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Valid pattern executes in the local audio engine; syntax errors identify the real failure and do not claim remote inference; Reload supported local session and compare source/tempo; Compile failure or denied audio leaves source editable and transport recoverable

## SVF-G136-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G136
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G136-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-460/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-461/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G136-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G136
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G136-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-462/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G136-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G136
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G136-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-463/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G137 Strudel AI DAW: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G137
- Goal: Strudel AI DAW: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-470/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-471/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-472/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-473/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Local composition and undo are real; assistance is not labeled executed unless a declared genuine capability exists; Reload supported project and compare editable source, tracks and tempo; Invalid pattern, failed audio or unavailable assistance does not discard local edits

## SVF-G137-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G137
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G137-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-470/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-471/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G137-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G137
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G137-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-472/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G137-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G137
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G137-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-473/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G138 Music Studio Classic: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G138
- Goal: Music Studio Classic: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-480/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-481/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-482/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-483/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Classic workflow remains usable and local; legacy alias does not silently open another app or claim remote rendering; Reopen saved classic project and verify track edit, tempo and selected instrument; Invalid project or unavailable audio shows explicit recovery without deleting the project

## SVF-G138-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G138
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G138-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-480/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-481/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G138-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G138
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G138-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-482/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G138-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G138
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G138-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-483/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G139 P2P Chat Classic: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G139
- Goal: P2P Chat Classic: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-490/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-491/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-492/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-493/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Legacy message delivery is backed by real peer state, offline messages remain queued and migration is explicit; Reopen retained history and compare peer identity, exact message and delivery state; Offline peer or denied send leaves composed text recoverable

## SVF-G139-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G139
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G139-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-490/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-491/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G139-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G139
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G139-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-492/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G139-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G139
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G139-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-493/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G140 Datasets Browser: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G140
- Goal: Datasets Browser: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-500/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-501/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-502/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-503/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Visible rows and schema match real loaded data; filtering selects the known record and failures are honest; Reopen the chosen dataset/artifact and compare immutable identity, schema and row values; Invalid source, unavailable dataset or bad query retains selection and shows actual loader/query failure

## SVF-G140-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G140
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G140-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-500/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-501/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G140-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G140
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G140-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-502/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G140-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G140
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G140-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-503/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G141 IDL Explorer: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G141
- Goal: IDL Explorer: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-510/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-511/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-512/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-513/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Displayed schema matches selected descriptor, valid input passes and invalid field has a useful local explanation; Reopen descriptor selection and compare stable descriptor identity and field definitions; Missing descriptor or invalid parameter has explicit local unavailable/validation state

## SVF-G141-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G141
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G141-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-510/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-511/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G141-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G141
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G141-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-512/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G141-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G141
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G141-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-513/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G142 Glasses Preview: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G142
- Goal: Glasses Preview: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-520/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-521/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-522/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-523/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Preview content matches packet data and its display constraints; physical device delivery is never claimed by the simulator; Reopen supported replay data and compare packet identity/content; Unsupported display/camera/audio permission exposes actual fallback rationale

## SVF-G142-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G142
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G142-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-520/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-521/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G142-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G142
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G142-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-522/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G142-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G142
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G142-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-523/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Browser-local workflow; zero Python-owner tool dispatches. Future remote roles require a separately reviewed manifest/contract change.

## SVF-G143 ORB Auto-UI: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G143
- Goal: ORB Auto-UI: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-530/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-531/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-532/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-533/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Rendered field requirements match schema, invalid arguments cannot execute and output belongs to the chosen owner/tool; Reopen descriptor/result artifact and compare descriptor identity, validated input and output; Schema mismatch, denied action or unavailable tool is visible without substitute success

## SVF-G143-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G143
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G143-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-530/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-531/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G143-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G143
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G143-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-532/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G143-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G143
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G143-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-533/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G144 MCP++ Explorer: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G144
- Goal: MCP++ Explorer: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-540/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-541/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-542/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-543/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Transport is actual observed HTTP/libp2p, peer identity verifies and retained result/receipt agree on owner/tool/correlation; Reopen the receipt/event-DAG detail and verify retained proof addresses actual content; Invalid identity, unavailable transport or unsupported profile cannot become an executed success

## SVF-G144-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G144
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G144-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-540/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-541/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G144-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G144
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G144-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-542/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G144-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G144
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G144-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-543/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G145 Agent Supervisor: useful visual layout and intended workflow

- Status: active
- Parent: SVF-G040
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G145
- Goal: Agent Supervisor: useful visual layout and intended workflow
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-550/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-551/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-552/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-553/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Task completion follows actual output validation, dependencies explain blockers and heartbeat alone is not progress; Reopen taskboard/run details and match task identity, validated output and retained event history; Missing dependency, stalled worker, provider failure or timeout shows a concrete blocker and bounded recovery

## SVF-G145-V Real desktop and narrow viewport inspection

- Status: active
- Parent: SVF-G145
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G145-V
- Goal: Real desktop and narrow viewport inspection
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-550/receipt.json, data/agent_supervisor/swissknife_visual_functional/tasks/SVF-551/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.

## SVF-G145-F Semantic workflow, persistence and failure recovery

- Status: active
- Parent: SVF-G145
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G145-F
- Goal: Semantic workflow, persistence and failure recovery
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-552/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.

## SVF-G145-M Truthful backend and policy boundary

- Status: active
- Parent: SVF-G145
- Priority: P1
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G145-M
- Goal: Truthful backend and policy boundary
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-553/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Only declared gateway bindings may dispatch; semantic result and authenticated receipt are required. A preview or dry run does not prove a completed side effect.

## SVF-G031 Validate scenario admission and independent observation detectors

- Status: active
- Parent: SVF-G030
- Priority: P0
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G031
- Goal: Validate scenario admission and independent observation detectors
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-031/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Run the implemented strict scenario admission, exact semantic requirement binding, typed observation evaluator, DOM readers and genuine blank/clipped/nonplaying media refusal tests. This stage establishes reusable foundation primitives only; browser execution and app acceptance remain unimplemented until subsequent stages pass.


## SVF-G032 Implement the actual desktop lifecycle and scenario action engine

- Status: active
- Parent: SVF-G030
- Priority: P0
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G032
- Goal: Implement the actual desktop lifecycle and scenario action engine
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-032/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Extend openRealDesktopSession and executeScenarioPhase, preserving stage1 behavior. Reuse capture-visual-functional-baseline.mjs owned-server/Chrome lifecycle, canonical manifest launch and viewport capture; open actual canonical app windows, never setContent or a simulator. Implement bounded click/fill/select/key/close/reopen/wait/assert actions and read actual DOM/media values. Keep original app identity and storage across close/reopen. Add independent tests for wrong result, lost persisted data, clipped/blank content, focus, failure checkpoint and recovery. Wire foundation-check stage2 to concrete lifecycle/action-engine tests, retain explicit failure for unimplemented proof/pilot stages. Keep this patch limited to browser lifecycle/actions; do not implement MCP proof collection yet.


## SVF-G033 Implement raw MCP proof collection and workflow report assembly

- Status: active
- Parent: SVF-G030
- Priority: P0
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G033
- Goal: Implement raw MCP proof collection and workflow report assembly
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-033/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Extend collectBackendProof and runWorkflow using the existing stage2 session/action engine and strict stage1 scenario schema. Observe genuine browser /mcp/tools/call request/result pairs, exact owner/tool/route/transport/correlation/app metadata, native outcome, raw receipt and event DAG artifact bytes with matching CIDs. Reuse established gateway/UCAN verification; never invent proofs, receipt bytes or success. Join raw call/result records and evaluate result_assertion RFC6901 pointers against retained raw receipt values. Produce the complete workflow.json schema required by final SVF-030 acceptance and the independent campaign worker, with source/contract hashes, actual viewports/screenshots/trace, all exact result_N/persist_reopen/failure_recovery assertions and five observed checks. Browser-local/external/policy apps must enforce zero unexpected Python-owner calls. Stage3 CLI and unit tests must reject absent/tampered receipts, mismatched joins, fabricated flags and stale sources. Retain stage1/2 guarantees; no app acceptance from unit fixtures.


## SVF-G034 Run a real Calculator foundation integration pilot

- Status: active
- Parent: SVF-G030
- Priority: P0
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G034
- Goal: Run a real Calculator foundation integration pilot
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-034/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Implement runCalculatorPilot using the actual canonical Calculator in the completed desktop driver. Perform actual arithmetic, keyboard arithmetic and clear/retry recovery; independently read the rendered result for each. Capture real desktop/mobile PNGs and current driver/application source hashes. Emit pilot/pilot.json schema swissknife.visual-functional-driver-pilot.v1, app_id calculator, actual_desktop:true, foundation_integration_only:true, functional_acceptance:false. observations are exactly arithmetic_result, keyboard_result and clear_recovery, each with typed observation {operator,actual,expected} evaluated from actual UI reads. artifacts retain root-relative path/sha256/bytes, including desktop.png/mobile.png. This pilot proves driver integration only, not full Calculator acceptance or all app workflow completion. --foundation-check pilot --output-dir <dir> runs the real pilot, bounded and lease-owned; fail truthfully when unavailable.

## SVF-G005 An exhausted task repairs itself inside its existing lease

- Status: active
- Parent: SVF-G001
- Priority: P0
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G005
- Goal: An exhausted task repairs itself inside its existing lease
- Evidence: data/agent_supervisor/swissknife_visual_functional/tasks/SVF-005/receipt.json
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: The original producer must genuinely fail on pending fixture data, then the registered foreground recovery hook must use Grok4.7 through llm_router without native tools to change only the isolated fixture recovery_state to repaired_by_scoped_model. Durable admission, finite budget, exact lease and source hashes and native model receipt are independently verified; only rerunning the original protected checker may complete this operational rehearsal. No app acceptance or goal completion is granted.


## SVF-G600 Final actual semantics and fresh visual acceptance at both canonical viewports

- Status: active
- Parent: SVF-G050
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G600
- Goal: Final actual semantics and fresh visual acceptance at both canonical viewports
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: All45 canonical apps have independently executed complete desktop and mobile semantic workflows, exact current source/artifact joins and fresh pinned-model visual reviews. Original900/990 consume all45 current joins and3 original cross-app receipts; no historical layout-only image can grant final coverage.

## SVF-G601 Final desktop and mobile semantic and visual acceptance for SwissKnife Terminal

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G601
- Goal: Final desktop and mobile semantic and visual acceptance for SwissKnife Terminal
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G602 Final desktop and mobile semantic and visual acceptance for VibeCode

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G602
- Goal: Final desktop and mobile semantic and visual acceptance for VibeCode
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G603 Final desktop and mobile semantic and visual acceptance for Music Studio

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G603
- Goal: Final desktop and mobile semantic and visual acceptance for Music Studio
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G604 Final desktop and mobile semantic and visual acceptance for AI Chat

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G604
- Goal: Final desktop and mobile semantic and visual acceptance for AI Chat
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G605 Final desktop and mobile semantic and visual acceptance for File Manager

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G605
- Goal: Final desktop and mobile semantic and visual acceptance for File Manager
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G606 Final desktop and mobile semantic and visual acceptance for Task Manager

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G606
- Goal: Final desktop and mobile semantic and visual acceptance for Task Manager
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G607 Final desktop and mobile semantic and visual acceptance for Todo and Goals

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G607
- Goal: Final desktop and mobile semantic and visual acceptance for Todo and Goals
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G608 Final desktop and mobile semantic and visual acceptance for AI Model Manager

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G608
- Goal: Final desktop and mobile semantic and visual acceptance for AI Model Manager
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G609 Final desktop and mobile semantic and visual acceptance for Hugging Face Hub

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G609
- Goal: Final desktop and mobile semantic and visual acceptance for Hugging Face Hub
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G610 Final desktop and mobile semantic and visual acceptance for OpenRouter Hub

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G610
- Goal: Final desktop and mobile semantic and visual acceptance for OpenRouter Hub
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G611 Final desktop and mobile semantic and visual acceptance for IPFS Explorer

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G611
- Goal: Final desktop and mobile semantic and visual acceptance for IPFS Explorer
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G612 Final desktop and mobile semantic and visual acceptance for Device Manager

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G612
- Goal: Final desktop and mobile semantic and visual acceptance for Device Manager
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G613 Final desktop and mobile semantic and visual acceptance for Settings

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G613
- Goal: Final desktop and mobile semantic and visual acceptance for Settings
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G614 Final desktop and mobile semantic and visual acceptance for MCP Control

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G614
- Goal: Final desktop and mobile semantic and visual acceptance for MCP Control
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G615 Final desktop and mobile semantic and visual acceptance for API Keys

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G615
- Goal: Final desktop and mobile semantic and visual acceptance for API Keys
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G616 Final desktop and mobile semantic and visual acceptance for GitHub

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G616
- Goal: Final desktop and mobile semantic and visual acceptance for GitHub
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G617 Final desktop and mobile semantic and visual acceptance for OAuth Login

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G617
- Goal: Final desktop and mobile semantic and visual acceptance for OAuth Login
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G618 Final desktop and mobile semantic and visual acceptance for AI Cron

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G618
- Goal: Final desktop and mobile semantic and visual acceptance for AI Cron
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G619 Final desktop and mobile semantic and visual acceptance for NAVI

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G619
- Goal: Final desktop and mobile semantic and visual acceptance for NAVI
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G620 Final desktop and mobile semantic and visual acceptance for P2P Network Manager

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G620
- Goal: Final desktop and mobile semantic and visual acceptance for P2P Network Manager
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G621 Final desktop and mobile semantic and visual acceptance for P2P Chat

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G621
- Goal: Final desktop and mobile semantic and visual acceptance for P2P Chat
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G622 Final desktop and mobile semantic and visual acceptance for Neural Network Designer

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G622
- Goal: Final desktop and mobile semantic and visual acceptance for Neural Network Designer
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G623 Final desktop and mobile semantic and visual acceptance for Training Manager

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G623
- Goal: Final desktop and mobile semantic and visual acceptance for Training Manager
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G624 Final desktop and mobile semantic and visual acceptance for Calculator

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G624
- Goal: Final desktop and mobile semantic and visual acceptance for Calculator
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G625 Final desktop and mobile semantic and visual acceptance for Clock and Timers

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G625
- Goal: Final desktop and mobile semantic and visual acceptance for Clock and Timers
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G626 Final desktop and mobile semantic and visual acceptance for Calendar and Events

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G626
- Goal: Final desktop and mobile semantic and visual acceptance for Calendar and Events
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G627 Final desktop and mobile semantic and visual acceptance for PeerTube

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G627
- Goal: Final desktop and mobile semantic and visual acceptance for PeerTube
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G628 Final desktop and mobile semantic and visual acceptance for Friends and Network

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G628
- Goal: Final desktop and mobile semantic and visual acceptance for Friends and Network
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G629 Final desktop and mobile semantic and visual acceptance for Image Viewer

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G629
- Goal: Final desktop and mobile semantic and visual acceptance for Image Viewer
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G630 Final desktop and mobile semantic and visual acceptance for Notes

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G630
- Goal: Final desktop and mobile semantic and visual acceptance for Notes
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G631 Final desktop and mobile semantic and visual acceptance for Media Player

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G631
- Goal: Final desktop and mobile semantic and visual acceptance for Media Player
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G632 Final desktop and mobile semantic and visual acceptance for System Monitor

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G632
- Goal: Final desktop and mobile semantic and visual acceptance for System Monitor
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G633 Final desktop and mobile semantic and visual acceptance for Neural Photoshop

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G633
- Goal: Final desktop and mobile semantic and visual acceptance for Neural Photoshop
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G634 Final desktop and mobile semantic and visual acceptance for Cinema

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G634
- Goal: Final desktop and mobile semantic and visual acceptance for Cinema
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G635 Final desktop and mobile semantic and visual acceptance for Strudel

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G635
- Goal: Final desktop and mobile semantic and visual acceptance for Strudel
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G636 Final desktop and mobile semantic and visual acceptance for Strudel AI DAW

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G636
- Goal: Final desktop and mobile semantic and visual acceptance for Strudel AI DAW
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G637 Final desktop and mobile semantic and visual acceptance for Music Studio Classic

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G637
- Goal: Final desktop and mobile semantic and visual acceptance for Music Studio Classic
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G638 Final desktop and mobile semantic and visual acceptance for P2P Chat Classic

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G638
- Goal: Final desktop and mobile semantic and visual acceptance for P2P Chat Classic
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G639 Final desktop and mobile semantic and visual acceptance for Datasets Browser

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G639
- Goal: Final desktop and mobile semantic and visual acceptance for Datasets Browser
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G640 Final desktop and mobile semantic and visual acceptance for Accelerate Panel

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G640
- Goal: Final desktop and mobile semantic and visual acceptance for Accelerate Panel
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G641 Final desktop and mobile semantic and visual acceptance for IDL Explorer

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G641
- Goal: Final desktop and mobile semantic and visual acceptance for IDL Explorer
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G642 Final desktop and mobile semantic and visual acceptance for Glasses Preview

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G642
- Goal: Final desktop and mobile semantic and visual acceptance for Glasses Preview
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G643 Final desktop and mobile semantic and visual acceptance for ORB Auto-UI

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G643
- Goal: Final desktop and mobile semantic and visual acceptance for ORB Auto-UI
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G644 Final desktop and mobile semantic and visual acceptance for MCP++ Explorer

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G644
- Goal: Final desktop and mobile semantic and visual acceptance for MCP++ Explorer
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

## SVF-G645 Final desktop and mobile semantic and visual acceptance for Agent Supervisor

- Status: active
- Parent: SVF-G600
- Priority: P2
- Track: visual-functional
- Bundle: swissknife/visual-functional/SVF-G645
- Goal: Final desktop and mobile semantic and visual acceptance for Agent Supervisor
- Outputs: data/agent_supervisor/swissknife_visual_functional/tasks/
- Acceptance: Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; the original task retains its existing historical repair authority and budgets; this readonly followup creates no repair authority. Never report accepted just because an event fired or text changed. This final followup must run the full unchanged scenario in two independent sessions initially at1440x900 and390x844, with separate actual semantic/backend/keyboard/persistence/recovery proof and exact result images. Require the current dual-viewport report and a fresh genuine grok_cli/grok-4.7 review-mode pass bound to both images and both child reports. This task is readonly and allocates no new automatic repair attempts; retain failures and use only separately authorized original repair scopes and existing budgets. Historical V1/layout-only mobile evidence cannot grant this final coverage.

