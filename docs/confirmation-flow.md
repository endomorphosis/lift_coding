# Confirmation Flow

HandsFree uses a token-based confirmation workflow for sensitive actions.

Source of truth:
- `src/handsfree/commands/pending_actions.py`
- `src/handsfree/db/pending_actions.py`
- `POST /v1/commands/confirm`

## Flow Overview

1. User issues a command that may be destructive or policy-gated.
2. Backend returns `needs_confirmation` with a pending action token.
3. Client submits the token to `POST /v1/commands/confirm`.
4. Backend validates token, checks expiry, executes action if valid.
5. Token is consumed so confirmation is one-time.

## Token Semantics

- tokens are generated with secure randomness
- tokens expire after a TTL (default manager TTL is short-lived)
- expired tokens are rejected
- confirmed tokens are removed (single-use)

## Storage Modes

- in-memory manager (development fallback)
- Redis-backed manager for persistence and atomic token consumption
- DB-backed pending action records for durable audit and workflow tracking

## API Behavior

`POST /v1/commands/confirm`:

- `200`: confirmation accepted and action handled
- `404`: pending action token not found or expired

Related endpoint examples:

- `POST /v1/actions/merge` may force confirmation
- `POST /v1/actions/request-review` can be policy-gated
- `POST /v1/actions/comment` can be policy-gated

## Mobile UX

The confirmation UI is available in:

- `mobile/src/screens/ConfirmationScreen.js`

It accepts:

- confirmation token
- optional idempotency key
