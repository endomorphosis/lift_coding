# Agent Todos

## HAO-001 Resolve dirty main checkout blocking 21 worktree merges

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Fingerprint: f41150c33a8d59ea7ba33376fde33c796112722f
- Dedupe key: reconciliation_guardrail:main_checkout_dirty
- Depends on:
- Outputs: data/hallucinate_multimodal_control/discovery, implementation_plan/docs/24-hallucinate-multimodal-control.todo.md
- Validation: test -f /home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-06-07-hao-001-reconciliation-ddcbf9a43226.md
- Acceptance: Reconciliation guardrail filed this because 21 branch or worktree cleanup candidates are blocked by main_checkout_dirty. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-06-07-hao-001-reconciliation-ddcbf9a43226.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## HAO-002 Resolve 53 dirty backlogged worktrees blocked by content_not_in_target

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Fingerprint: bb64bae868098066736cc7c2c3980d10b27ebb21
- Dedupe key: reconciliation_guardrail:dirty_backlogged_worktree:content_not_in_target
- Depends on:
- Outputs: data/hallucinate_multimodal_control/discovery, implementation_plan/docs/24-hallucinate-multimodal-control.todo.md
- Validation: test -f /home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-06-07-hao-002-reconciliation-bb64bae86809.md
- Acceptance: Reconciliation guardrail filed this because 53 branch or worktree cleanup candidates are blocked by content_not_in_target. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-06-07-hao-002-reconciliation-bb64bae86809.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## HAO-003 Resolve 13 dirty backlogged worktrees blocked by unsupported_status

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Fingerprint: ab689090ed4d18ff1e83b5c0cf5eb1ac02cd83cb
- Dedupe key: reconciliation_guardrail:dirty_backlogged_worktree:unsupported_status
- Depends on:
- Outputs: data/hallucinate_multimodal_control/discovery, implementation_plan/docs/24-hallucinate-multimodal-control.todo.md
- Validation: test -f /home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-06-07-hao-003-reconciliation-bd6cd4184e9c.md
- Acceptance: Reconciliation guardrail filed this because 13 branch or worktree cleanup candidates are blocked by unsupported_status. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-06-07-hao-003-reconciliation-bd6cd4184e9c.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.
