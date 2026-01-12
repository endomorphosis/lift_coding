# Observability

## What to measure
- Command latency (p50/p95)
- STT confidence + correction rate
- Intent success rate
- Confirmation friction (how often user cancels)
- Notification usefulness (dismiss vs engage)

## Logs
- Structured logs with request_id
- Redact tokens and code content
- Action logs are separate from debug logs

## Alerts
- Webhook failure spikes
- Auth/token refresh failures
- Elevated error rates on side-effect actions

## Debug tools
- Replay last command text (not audio) for user support
- “Explain what you heard” command for STT troubleshooting
