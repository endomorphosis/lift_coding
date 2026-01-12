# Security Policy

This document outlines security practices and guidelines for the HandsFree Dev Companion project.

## Threat Model

This application handles sensitive data and privileged operations. Key threats include:

- **Token theft** → repository compromise
- **Unauthorized merges/actions** → unintended code changes
- **Leaking proprietary code** through logs, summaries, or transcripts
- **Malicious webhook spoofing** → unauthorized actions
- **Voice command injection** → unintended side effects

## Security Controls

### Authentication & Authorization
- **GitHub App integration**: Prefer GitHub App with least-privilege access over personal access tokens
- **Short-lived tokens**: Session tokens expire after reasonable timeouts
- **Webhook verification**: All incoming webhooks must pass signature verification and replay protection
- **Least-privilege scopes**: Request minimum required GitHub permissions
- **Rate limiting**: Implement anomaly detection for side-effect actions

### Webhook Security

**Signature Verification**
- Always verify GitHub webhook signatures using HMAC-SHA256
- Use the `X-Hub-Signature-256` header
- Reject unsigned or invalidly signed webhooks

**Replay Protection**
- Track webhook delivery IDs to prevent replay attacks
- Use idempotency keys for side-effect actions
- Implement timestamp checks for webhook freshness

## Secret Management

### General Principles

1. **Never log secrets**: Tokens, API keys, and credentials must never appear in logs, metrics, or error messages
2. **Encrypt at rest**: Use KMS or equivalent for secret storage
3. **Short-lived tokens**: Prefer temporary credentials with minimal scope
4. **Principle of least privilege**: Request only the permissions you need
5. **Rotate regularly**: Implement token rotation strategy for long-lived credentials

### What to Store Securely

**DO:**
- Store secrets in environment variables or secure secret management systems (e.g., AWS KMS, HashiCorp Vault)
- Use short-lived tokens where possible
- Encrypt secrets at rest using KMS or equivalent
- Rotate tokens regularly
- Use GitHub App installation tokens (scoped, short-lived) instead of personal access tokens

**DON'T:**
- Never commit secrets, tokens, or API keys to source control
- Never log secrets in plain text
- Never include secrets in error messages or exception details
- Never send secrets to external systems without encryption

### Environment Variables

**NEVER** commit secrets to source control. Use environment variables or secret management services.

```bash
# Good: Load from environment
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Bad: Hardcoded secret
GITHUB_TOKEN = "ghp_abc123..."  # NEVER DO THIS
```

Store secrets in environment variables or a secure secret manager:
```bash
# Example: .env file (DO NOT COMMIT)
GITHUB_APP_PRIVATE_KEY=...
REDIS_PASSWORD=...
DATABASE_ENCRYPTION_KEY=...
```

Add `.env` files to `.gitignore` to prevent accidental commits.

### Secret Storage by Environment

**Local Development**:
- Store secrets in `.env` files (ensure `.env` is in `.gitignore`)
- Use environment variables for configuration
- Never commit secrets to version control

**Production**:
- Use GitHub Secrets for CI/CD
- Use environment variables or secret management service (AWS Secrets Manager, Azure Key Vault, etc.)
- Encrypt secrets at rest using KMS
- Use short-lived session tokens when possible

### GitHub Token Handling

- **Prefer GitHub Apps over Personal Access Tokens**
  - Use fine-grained permissions (read-only when possible)
  - Minimize scope to specific repositories
  
- **Token storage**: Encrypt at rest using KMS or equivalent
- **Token scope**: Request minimum required scopes (e.g., `repo:status`, `read:org`)
- **Never log tokens**: Redact tokens in all log output

```python
# Good: redacted in logs
logger.info("GitHub API call", extra={"token": "[REDACTED]"})

# Bad: exposes token
logger.info(f"Using token {token}")
```

Example environment variables:
```bash
export GITHUB_TOKEN=ghp_...
export REDIS_PASSWORD=...
```

## Redaction Policies

### Log Redaction

All logging output must redact sensitive information before writing to disk or external services.

**Always redact:**
- GitHub tokens (PATs, installation tokens, OAuth tokens)
- API keys and secrets
- Webhook signatures
- Repository content (code snippets, file contents)
- User PII (emails, names when not necessary)
- Session tokens and authentication credentials
- Private repository names (when in strict privacy mode)

**Redaction patterns:**
```python
# Example redaction patterns
REDACT_PATTERNS = [
    r'ghp_[a-zA-Z0-9]{36}',  # GitHub personal access tokens
    r'ghs_[a-zA-Z0-9]{36}',   # GitHub app tokens
    r'-----BEGIN [A-Z ]+-----.*?-----END [A-Z ]+-----',  # Private keys
    r'[A-Za-z0-9+/]{40,}={0,2}',  # Base64 secrets (conservative)
]

# Example: redact tokens
log_message = re.sub(r'(token|key|secret)=[^\s&]+', r'\1=REDACTED', log_message)

# Example: redact bearer tokens
log_message = re.sub(r'Bearer [A-Za-z0-9_-]+', 'Bearer [REDACTED]', log_message)
```

**Implementation guidelines:**
- Use structured logging (JSON) with clearly marked sensitive fields
- Apply redaction filters before log emission
- Never log full request/response bodies containing tokens
- Redact with consistent markers: `[REDACTED]` or `***`

Example:
```python
# Bad - token in plain sight
logger.info(f"GitHub token: {token}")

# Good - redact sensitive data
logger.info("GitHub token: [REDACTED]")

# Good - use structured logging with automatic redaction
logger.info("user_authenticated", extra={
    "user_id": user_id,
    "repo": repo_name,
    # token is automatically redacted by log filter
})
```

### Log Levels and Content

- **ERROR/WARN**: Include structured context but redact tokens, emails, repo names in private mode
- **INFO**: High-level operations only (e.g., "PR summarized", "webhook received")
- **DEBUG**: Verbose mode with redaction still enabled (never log raw tokens)

## Privacy Modes

The system supports three privacy levels for data handling:

**Strict Mode** (recommended for proprietary code)
- No code snippets in logs or summaries
- No images stored or transmitted
- Summaries only: "PR #123 has 5 comments, 2 approvals"

**Balanced Mode** (default)
- Small code excerpts permitted (max 3-5 lines)
- Automatic redaction of secrets/tokens
- Images allowed but not stored long-term

**Debug Mode** (development only)
- Verbose logging enabled
- Full payloads in logs
- ⚠️ Never use in production

Configure via environment variable:
```bash
export PRIVACY_MODE=strict  # or balanced, debug
export REDACTION_ENABLED=true
export LOG_LEVEL=info
```

## Data Retention

**Minimize Storage**
- Do not store audio recordings (process and discard)
- Keep action logs for security audit but avoid full payload content
- Purge old webhook data after processing

**What We Store**
- Action audit logs (who, what, when, repo, result) - 90 days
- User session metadata - 30 days
- Webhook delivery IDs (for replay protection) - 7 days

**What We Don't Store**
- Raw audio from wearable
- Full code diffs in logs
- GitHub tokens (only encrypted at rest, never logged)

## Incident Response

If a security issue is discovered:

1. **Report**: Open a private security advisory on GitHub
2. **Do not** publicly disclose until patched
3. We aim to acknowledge within 24 hours and provide a fix timeline within 72 hours

## Development Best Practices

**For Contributors**
- Never commit secrets or tokens to git
- Use `.env` files (excluded via `.gitignore`) for local secrets
- Run `make lint` before committing to catch potential security issues
- Review logs for accidental secret exposure before pushing

**In Code**
```python
# ❌ Bad
github_token = "ghp_abc123..."
logger.info(f"Using token: {github_token}")

# ✅ Good
github_token = os.environ.get("GITHUB_TOKEN")
if not github_token:
    raise ValueError("GITHUB_TOKEN not set")
logger.info("GitHub token loaded from environment")
```

**Code Review Checklist**
- [ ] No hardcoded secrets
- [ ] Sensitive data properly redacted in logs
- [ ] User input sanitized/validated
- [ ] Webhook signatures verified
- [ ] Destructive actions gated by policy
- [ ] Tests cover security-critical paths

## Additional Resources

- [Implementation Plan: Security & Privacy](implementation_plan/docs/08-security-privacy.md)
- [Development Loop](implementation_plan/docs/11-devloop-vscode.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## Questions?

For security-related questions or to report vulnerabilities:
- **Non-sensitive topics**: Open a GitHub issue
- **Security vulnerabilities**: Open a private security advisory on GitHub
