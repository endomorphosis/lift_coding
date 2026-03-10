# PR Summary: Webhook User Mapping + Production Secret Config

## Overview

This PR improves webhook handling to map events to the correct user(s) and tightens production configuration.

## Changes Made

### 1. Database Schema
- **Migration 003**: Added `repo_subscriptions` table to map repositories to users
- Supports both direct repo subscriptions and GitHub App installation-based routing
- Includes indexes for efficient lookup by repo name and installation_id

### 2. User Mapping Module
- **New file**: `src/handsfree/db/repo_subscriptions.py`
- Functions to create/query subscriptions
- Support for looking up users by repo name or installation_id
- Fallback to `github_connections` table for installation-based routing

### 3. Webhook Handler Updates
- **Updated**: `src/handsfree/webhooks.py`
  - Added `get_webhook_secret()` to read from environment
  - Added `extract_installation_id()` to parse webhook payloads
  
- **Updated**: `src/handsfree/api.py`
  - Modified webhook endpoint to use `GITHUB_WEBHOOK_SECRET` env var
  - Refactored `_emit_webhook_notification()` to map users correctly
  - No longer emits to fixture user unconditionally
  - Logs info message when no subscriptions found (no-op)

### 4. Environment-Controlled Signature Verification
- **Dev/Test Mode** (no `GITHUB_WEBHOOK_SECRET` set):
  - Accepts special signature `"dev"` for testing
  - All existing tests work unchanged
  
- **Production Mode** (`GITHUB_WEBHOOK_SECRET` set):
  - Rejects `"dev"` signature
  - Requires valid HMAC-SHA256 signature
  - Uses GitHub's standard webhook signature format

### 5. Testing
- **New test file**: `tests/test_webhook_user_mapping.py`
  - 13 comprehensive tests covering all new functionality
  - Tests for dev/prod signature modes
  - Tests for repo-based routing
  - Tests for installation-based routing
  - Tests for multi-user notifications
  - Tests for no-op behavior

- **Updated**: `tests/test_notifications_api.py`
  - Added subscription setup for fixture user in webhook tests
  - All 3 webhook notification tests still pass

- **All tests**: 48 webhook/notification tests pass
  - 14 tests in `test_webhooks.py`
  - 21 tests in `test_notifications_api.py`
  - 13 tests in `test_webhook_user_mapping.py`

### 6. Documentation
- **New file**: `docs/webhook_user_mapping.md`
  - Configuration guide for dev vs prod modes
  - Examples of setting up subscriptions
  - Troubleshooting section
  
- **New file**: `dev/test_webhook_mapping.py`
  - Manual test script demonstrating all features
  - Shows user mapping in action
  - Validates all acceptance criteria

## Acceptance Criteria Met

✅ **Webhook notifications are created for the correct user_id(s) when mapping exists**
- Tests validate routing by repo subscription
- Tests validate routing by installation_id
- Tests validate multiple users per webhook

✅ **Missing mapping results in no-op (or logged) rather than misrouting to fixture user**
- No notifications created when no subscriptions exist
- Info-level log message emitted for debugging
- Test validates no fixture user notification

✅ **Signature verification behavior is env-controlled**
- Dev mode accepts "dev" signature
- Production mode requires GITHUB_WEBHOOK_SECRET
- Production mode validates HMAC-SHA256 signatures
- Tests validate both modes

## Backward Compatibility

- Existing tests updated minimally (added subscription setup)
- Dev mode behavior unchanged (accepts "dev" signature)
- All fixture-based tests continue to work
- No breaking changes to API endpoints

## Production Deployment

To enable production webhook secret verification:
```bash
export GITHUB_WEBHOOK_SECRET="your-secret-from-github"
```

To set up user subscriptions, use the provided functions in `repo_subscriptions.py` or create GitHub connections with `installation_id`.

See `docs/webhook_user_mapping.md` for complete configuration guide.
