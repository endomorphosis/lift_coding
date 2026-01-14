# PR-014: Security + observability hardening pass

## Goal
Implement the plan's minimum security/privacy + observability expectations in a concrete, testable way.

## Background
The plan calls for structured logs with request IDs, redaction guarantees, and separation of audit vs debug logging.

## Scope
- Add/propagate a request ID for API calls (header and/or generated).
- Ensure tokens are never logged (audit and debug logs).
- Make logs more structured/consistent (key/value fields).
- Add one or two targeted tests for redaction behavior (e.g., ensure Authorization header never appears in logs, if feasible).

## Non-goals
- Full SIEM integration.
- KMS/secret encryption at rest (infra concern).

## Acceptance criteria
- Request ID shows up in logs for `/v1/command`.
- No accidental token leakage via logs.
- CI stays green.

## Implementation Details

### Request ID Propagation
- Accept `X-Request-ID` header or generate UUID for each request
- Add request ID to logging context
- Include in all log statements for request tracing

### Token Redaction
- Create `redact_secrets()` utility function
- Redact GitHub tokens (ghp_, ghs_, gho_ patterns)
- Redact Authorization headers
- Apply to all logging statements

### Structured Logging
- Use structured logging with key-value pairs
- Include context fields: request_id, user_id, endpoint
- Consistent format across all log statements

### Testing
- Test that Authorization headers are never logged
- Test that GitHub tokens are redacted
- Test that request IDs appear in logs
- Verify structured logging format
