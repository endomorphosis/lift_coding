SUB-PR-007: Confirmation execution + idempotency

Goal: Complete PR-007 acceptance criteria by implementing DB-backed pending action confirmation for request_review and ensuring confirm retries are exactly-once.

Work items:
- Wire /v1/commands/confirm to execute DB pending_actions (action_type=request_review)
- Ensure confirm is idempotent and audited
- Add tests for confirm+retry
