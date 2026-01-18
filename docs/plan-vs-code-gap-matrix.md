# Plan vs code gap matrix

This document maps the implementation plan and OpenAPI contract to what exists in the repo today, and enumerates what remains.

## Sources
- Implementation plan: `implementation_plan/docs/*`
- API contract: `spec/openapi.yaml`
- Implementation: `src/handsfree/*`

## Matrix: OpenAPI coverage

| Area | Endpoint | Status | Notes / Files |
|---|---|---|---|
| Status | `GET /v1/status` |  |  |
| Commands | `POST /v1/command` |  |  |
| Confirmations | `POST /v1/commands/confirm` |  |  |
| Inbox | `GET /v1/inbox` |  |  |
| Webhooks | `POST /v1/webhooks/github` |  |  |
| Webhooks | `POST /v1/webhooks/retry/{event_id}` |  |  |
| TTS | `POST /v1/tts` |  |  |
| Notifications | `GET /v1/notifications` |  |  |
| Notifications | `GET /v1/notifications/{notification_id}` |  |  |
| Notification subs | `POST /v1/notifications/subscriptions` |  |  |
| Notification subs | `GET /v1/notifications/subscriptions` |  |  |
| Notification subs | `DELETE /v1/notifications/subscriptions/{subscription_id}` |  |  |
| Repo subs | `POST /v1/repos/subscriptions` |  |  |
| Repo subs | `GET /v1/repos/subscriptions` |  |  |
| Repo subs | `DELETE /v1/repos/subscriptions/{repo_full_name}` |  |  |
| GitHub OAuth | `GET /v1/github/oauth/start` |  |  |
| GitHub OAuth | `GET /v1/github/oauth/callback` |  |  |
| Admin | `POST /v1/admin/api-keys` |  |  |
| Admin | `GET /v1/admin/api-keys` |  |  |
| Admin | `DELETE /v1/admin/api-keys/{key_id}` |  |  |

## Matrix: MVP checklist coverage

| MVP | Item | Status | Notes |
|---|---|---|---|
| MVP1 | iOS hands-free loop (speak → response → play on glasses) |  |  |
| MVP1 | Inbox summary |  |  |
| MVP1 | PR summary |  |  |
| MVP1 | Safe write action w/ confirmation |  |  |
| MVP1 | Push notification -> spoken summary |  |  |

## Demo blockers (iOS + Ray-Ban Meta)

1. 
2. 
3. 

## Proposed PR sequence

1. 
2. 
3. 
