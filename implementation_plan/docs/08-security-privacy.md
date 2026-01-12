# Security & Privacy

## Threat model highlights
- Token theft -> repo compromise
- Unauthorized merges/actions
- Leaking proprietary code through logs/summaries
- Malicious webhook spoofing

## Controls
- Prefer GitHub App, least privilege
- Encrypt secrets at rest (KMS)
- Short-lived session tokens for mobile
- Webhook signature verification + replay protection
- Action policy gates + confirmations
- Audit log (who, what, when, repo, result)
- Rate limiting + anomaly detection for side-effect actions

## Privacy modes
- Strict: no images, no code snippets, summaries only
- Balanced: small excerpts permitted, redaction enabled
- Debug: verbose (never default)

## Data retention
- Minimize stored audio; ideally do not store
- Keep action logs (security) but avoid payload content
