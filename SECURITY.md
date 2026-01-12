# Security Policy

## Overview

This project handles sensitive data including GitHub tokens, user conversations, and repository access. Security is a critical concern.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x     | :white_check_mark: |

This is a proof-of-concept project under active development. Security patches are applied to the latest commit on `main`.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via:
- Email: security@[project-domain] (if configured)
- GitHub Security Advisories: Use the "Security" tab in this repository

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We aim to respond within 48 hours and provide a fix timeline based on severity.

## Security Best Practices

### Secret Handling

#### Never Commit Secrets

- **GitHub tokens**: Use environment variables or secret management systems
- **API keys**: Never hardcode in source code
- **Credentials**: Store securely, never in git history

#### Environment Variables

Use `.env` files (git-ignored) or system environment variables:

```bash
export GITHUB_TOKEN="ghp_..."
export REDIS_PASSWORD="..."
```

Never commit `.env` files to the repository.

### Log Redaction

All logging **must** redact sensitive data:

#### Automatic Redaction Rules

- **GitHub tokens**: Pattern `ghp_[A-Za-z0-9_]+` → `ghp_***REDACTED***`
- **GitHub App keys**: Pattern `ghs_[A-Za-z0-9_]+` → `ghs_***REDACTED***`
- **OAuth tokens**: Pattern `gho_[A-Za-z0-9_]+` → `gho_***REDACTED***`
- **Email addresses**: Redact or hash
- **User IDs**: Redact or pseudonymize when appropriate

#### Logging Guidelines

```python
# ❌ Bad - logs sensitive data
logger.info(f"Auth with token: {github_token}")

# ✅ Good - redacts automatically
logger.info(f"Auth with token: {redact_secrets(github_token)}")

# ✅ Good - structured logging without secrets
logger.info("authenticated", extra={"user_id": hash_user_id(user_id)})
```

See `docs/09-observability.md` for detailed logging standards.

### Data Privacy

#### Personal Information

- Minimize collection of personal data
- Hash or pseudonymize user identifiers when possible
- Document data retention policies
- Comply with applicable privacy regulations (GDPR, etc.)

#### GitHub Data

- Respect GitHub's terms of service
- Only access repositories with proper authorization
- Don't store repository content unnecessarily
- Implement webhook verification (HMAC)

### Code Safety

#### Input Validation

- Validate all external inputs (webhooks, API requests)
- Use schema validation (Pydantic, OpenAPI)
- Sanitize data before processing

#### Dependency Management

- Pin dependency versions in `requirements-dev.txt`
- Regularly update dependencies for security patches
- Review dependencies for known vulnerabilities

#### Safe Defaults

- Fail closed (deny by default)
- Require explicit opt-in for risky operations
- Use policy engine for action approval

### Infrastructure Security

#### Redis

- Use authentication: `requirepass` in redis.conf
- Bind to localhost only in development
- Use TLS in production
- Regularly update Redis version

#### DuckDB

- Embedded database (no network exposure)
- File permissions: readable only by application user
- Regular backups with encryption

#### Docker

- Use official base images
- Pin image versions (no `latest` tags in production)
- Run containers as non-root users
- Scan images for vulnerabilities

## Security Checklist for Contributors

Before submitting a PR, ensure:

- [ ] No secrets committed to git
- [ ] Logging includes redaction for sensitive data
- [ ] Input validation for external data
- [ ] Dependencies are up to date
- [ ] New environment variables documented
- [ ] Security implications considered and documented

## Security-Related CI Checks

CI runs automatic checks including:
- Static analysis (Ruff linter)
- Dependency vulnerability scanning (planned)
- Secret scanning (GitHub's built-in)

## Disclosure Policy

When we receive a security report:

1. **Acknowledge** receipt within 48 hours
2. **Assess** severity and impact
3. **Develop** a fix on a private branch
4. **Test** the fix thoroughly
5. **Release** the fix publicly
6. **Notify** users of the vulnerability and fix

We credit reporters unless they prefer to remain anonymous.

## Resources

- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- Project security docs: `docs/08-security-privacy.md`

## Questions?

For security questions (non-vulnerability), open a discussion or contact the maintainers.

---

Thank you for helping keep this project secure! 🔒
