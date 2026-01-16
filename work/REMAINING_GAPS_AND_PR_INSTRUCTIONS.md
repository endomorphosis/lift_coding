# Remaining Implementation Gaps - Draft PR Creation Instructions

## Summary
After reviewing the merged PRs (#122-126, #131, #133-138), most of the implementation plan has been completed. Three remaining backend gaps have been identified and tracking documents created.

## Verified Completions ✅

The following items from the original gap list have been **fully implemented**:

### MVP1: Read-only PR inbox
- ✅ Production audio HTTPS fetch (PR-020)
  - File: `src/handsfree/audio_fetch.py`
  - Features: allowlists, size limits, timeouts, content-type validation
  
- ✅ Push delivery providers (PR-015, PR-024)
  - Files: `src/handsfree/notifications/provider.py`
  - Providers: WebPushProvider, APNSProvider (stub), FCMProvider (stub)

### MVP3: One safe write action
- ✅ Auth for production clients (PR-018, PR-023)
  - API key authentication: `src/handsfree/api.py` (API key endpoints)
  - GitHub OAuth: `src/handsfree/api.py` (OAuth start/callback)
  - Token storage via SecretManager

### MVP4: Agent delegation
- ✅ Real agent provider (PR-016, PR-022)
  - File: `src/handsfree/agent_providers.py`
  - Provider: `GitHubIssueDispatchProvider` - creates GitHub issues for tasks
  - Webhook correlation: `_correlate_pr_with_agent_tasks()` in `api.py`
  
- ✅ Agent intents use authenticated user_id (PR-022, PR-138)
  - File: `src/handsfree/agents/service.py`
  - No more hardcoded "default-user" placeholders

## Remaining Gaps ❌

### PR-026: Automatic push notification delivery
**Tracking doc**: `tracking/PR-026-notification-push-delivery.md`

**Gap**: Notifications are created in the database but not automatically pushed to users via their registered subscriptions.

**What exists**:
- Notification creation: `create_notification()` in `db/notifications.py`
- Polling endpoint: `GET /v1/notifications`
- Delivery providers: WebPush, APNS, FCM in `notifications/provider.py`

**What's missing**:
- Automatic invocation of delivery providers when notifications are created
- Bridge between notification creation and provider selection/delivery
- Delivery tracking (success/failure logging)

**Suggested approach**:
- Add `src/handsfree/notifications/delivery.py` service
- Call delivery service from `create_notification()`
- Query user subscriptions, select provider by platform, deliver
- Add env var `NOTIFICATIONS_AUTO_PUSH_ENABLED` for control

### PR-027: Profile-based summary verbosity tuning
**Tracking doc**: `tracking/PR-027-profile-verbosity-tuning.md`

**Gap**: User profiles (workout/commute/kitchen/focused/relaxed) are accepted in requests but don't affect response verbosity or formatting.

**What exists**:
- Profiles accepted in `/v1/command` client_context
- Router recognizes profiles
- Summary generation doesn't adapt to profile

**What's missing**:
- Verbosity rules for each profile (workout=ultra-brief, relaxed=detailed, etc.)
- Profile-aware response formatting in intent handlers
- Tests for profile-specific responses

**Suggested approach**:
- Create `src/handsfree/profiles.py` with verbosity configs
- Update PR summary generation to use profile hints
- Update inbox listing to filter/prioritize by profile
- Add tests for each profile variant

### PR-028: External agent runner setup
**Tracking doc**: `tracking/PR-028-external-agent-runner-setup.md`

**Gap**: No external agent runner exists to process dispatched GitHub issues and perform actual work.

**What exists**:
- Backend can dispatch tasks by creating GitHub issues
- Backend correlates PRs back to tasks via webhooks
- Task state is tracked end-to-end

**What's missing**:
- Actual agent runner (GitHub Actions, Copilot agent, custom runner)
- Documentation for setting up a runner
- Example runner implementations

**Suggested approach** (docs + examples, not backend code):
- Create `docs/agent-runner-setup.md` with setup instructions
- Add `.github/workflows/agent-runner-example.yml` (disabled)
- Add `docker-compose.agent-runner.yml` for custom runner
- Document required permissions and correlation mechanism

## Draft PR Creation Instructions

Since I cannot create PRs directly, here are the commands to create draft PRs for the remaining gaps:

### Create branches and PRs

```bash
# Set variables
REPO="endomorphosis/lift_coding"
BASE_BRANCH="main"

# PR-026: Notification push delivery
git checkout -b draft/pr-026-notification-push-delivery
git add tracking/PR-026-notification-push-delivery.md
git commit -m "PR-026: add tracking doc"
git push -u origin draft/pr-026-notification-push-delivery
gh pr create \
  --repo "$REPO" \
  --base "$BASE_BRANCH" \
  --head draft/pr-026-notification-push-delivery \
  --title "PR-026: Automatic push notification delivery" \
  --body-file tracking/PR-026-notification-push-delivery.md \
  --draft \
  --label copilot-agent

# PR-027: Profile verbosity tuning
git checkout main
git checkout -b draft/pr-027-profile-verbosity-tuning
git add tracking/PR-027-profile-verbosity-tuning.md
git commit -m "PR-027: add tracking doc"
git push -u origin draft/pr-027-profile-verbosity-tuning
gh pr create \
  --repo "$REPO" \
  --base "$BASE_BRANCH" \
  --head draft/pr-027-profile-verbosity-tuning \
  --title "PR-027: Profile-based summary verbosity tuning" \
  --body-file tracking/PR-027-profile-verbosity-tuning.md \
  --draft \
  --label copilot-agent

# PR-028: External agent runner setup
git checkout main
git checkout -b draft/pr-028-external-agent-runner-setup
git add tracking/PR-028-external-agent-runner-setup.md
git commit -m "PR-028: add tracking doc"
git push -u origin draft/pr-028-external-agent-runner-setup
gh pr create \
  --repo "$REPO" \
  --base "$BASE_BRANCH" \
  --head draft/pr-028-external-agent-runner-setup \
  --title "PR-028: External agent runner setup guide" \
  --body-file tracking/PR-028-external-agent-runner-setup.md \
  --draft \
  --label copilot-agent
```

## Alternative: Manual PR Creation via GitHub UI

If CLI is not available, create PRs manually:

1. Push branches:
   ```bash
   git checkout -b draft/pr-026-notification-push-delivery
   git add tracking/PR-026-notification-push-delivery.md
   git commit -m "PR-026: add tracking doc"
   git push -u origin draft/pr-026-notification-push-delivery
   ```

2. Go to https://github.com/endomorphosis/lift_coding/pulls/new
3. Select base: `main`, compare: `draft/pr-026-notification-push-delivery`
4. Title: "PR-026: Automatic push notification delivery"
5. Body: Copy content from `tracking/PR-026-notification-push-delivery.md`
6. Mark as draft, add label `copilot-agent`
7. Create pull request

Repeat for PR-027 and PR-028.

## Expected PR URLs

Once created, the PRs should be at:
- https://github.com/endomorphosis/lift_coding/pull/XXX (PR-026)
- https://github.com/endomorphosis/lift_coding/pull/YYY (PR-027)
- https://github.com/endomorphosis/lift_coding/pull/ZZZ (PR-028)

Where XXX, YYY, ZZZ are the next available PR numbers (likely 139, 140, 141 or similar).

## Priority Order

Suggested implementation priority:

1. **PR-026** (Notification push delivery) - High impact, enables real-time push
2. **PR-027** (Profile verbosity) - Medium impact, improves UX
3. **PR-028** (Agent runner setup) - External/infra, can be done separately

## Notes

- All tracking documents are committed to the current PR branch
- The checklist has been updated to reflect actual implementation status
- Client-side gaps (mobile/wearable) are documented in PR-025 but out of scope for backend work
