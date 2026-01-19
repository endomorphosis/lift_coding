# Plan vs code gap matrix

**Last Updated:** 2026-01-19  
**Status:** ✅ Complete

## Executive Summary

This document provides the authoritative mapping of the implementation plan (`implementation_plan/docs/*` and `spec/openapi.yaml`) to the current backend and mobile implementation in `src/handsfree/*` and `mobile/*`.

### Key Findings

**Backend Implementation:**
- ✅ **31/31 OpenAPI endpoints implemented** (100% coverage)
- ✅ All core MVP1-MVP4 backend features functional
- ✅ Comprehensive fixture/stub support for offline development
- ✅ Live GitHub API integration available via env config
- ✅ Full policy engine, confirmation flow, audit logging

**Mobile Implementation:**
- ✅ iOS + Android audio capture (Ray-Ban Meta glasses support)
- ✅ Audio playback through Bluetooth devices
- ✅ Push notification delivery working
- ✅ Command submission + TTS playback integrated
- ⚠️ UI polish needed (settings, OAuth flow, profile selector)

**MVP Status:**
- **MVP1:** ✅ Functionally complete (minor UI polish needed)
- **MVP2:** ✅ Functionally complete (profile UI missing)
- **MVP3:** ⚠️ Mostly complete (voice confirmation UI needed)
- **MVP4:** ⚠️ Mostly complete (task status UI + notifications)

**Critical Demo Blockers (iOS + Ray-Ban Meta):**
1. 🔴 Mobile settings screen for backend URL configuration
2. 🔴 Bluetooth microphone reliability (workaround exists: use phone mic)

**Recommended Next Steps:**
- **PR-067:** Mobile settings screen (HIGH priority, unblocks demo setup)
- **PR-068:** Audio source selector (HIGH priority, improves reliability)
- **PR-069-075:** Mobile UI polish + production config (MEDIUM/LOW priority)

---

## Sources
- Implementation plan: `implementation_plan/docs/*`
- API contract: `spec/openapi.yaml`
- Implementation: `src/handsfree/*`
- Mobile: `mobile/*`

---

## Matrix: OpenAPI coverage

| Area | Endpoint | Status | Implementation Files | Config / Missing E2E Pieces |
|---|---|---|---|---|
| **Core Commands** |
| Status | `GET /v1/status` | ✅ Implemented | [`api.py:185`](../src/handsfree/api.py#L185) | No config required. Returns health + DB status. |
| Commands | `POST /v1/command` | ✅ Implemented | [`api.py:634`](../src/handsfree/api.py#L634), [`commands/router.py`](../src/handsfree/commands/router.py), [`commands/intent_parser.py`](../src/handsfree/commands/intent_parser.py) | **Env:** `HANDSFREE_STT_PROVIDER` (stub/openai), `GITHUB_TOKEN` or `GITHUB_LIVE_MODE=true`. Supports text/audio/image input. Full idempotency, policy, rate limiting. **Mobile:** Audio capture + upload integrated. |
| Confirmations | `POST /v1/commands/confirm` | ✅ Implemented | [`api.py:1212`](../src/handsfree/api.py#L1212), [`db/pending_actions.py`](../src/handsfree/db/pending_actions.py) | **Env:** `GITHUB_TOKEN` for live mode. Exactly-once semantics. Writes audit logs. **Mobile:** Confirmation screen exists ([`ConfirmationScreen.js`](../mobile/src/screens/ConfirmationScreen.js)). |
| Inbox | `GET /v1/inbox` | ✅ Implemented | [`api.py:1869`](../src/handsfree/api.py#L1869), [`handlers/inbox.py`](../src/handsfree/handlers/inbox.py) | **Env:** `GITHUB_TOKEN` for live GitHub data. Falls back to fixtures if unavailable. Profile-based filtering supported. |
| Metrics | `GET /v1/metrics` | ✅ Implemented | [`api.py:232`](../src/handsfree/api.py#L232), [`metrics.py`](../src/handsfree/metrics.py) | **Env:** `HANDSFREE_ENABLE_METRICS=true` (disabled by default). Returns 404 if disabled. In-memory metrics only. |
| **Webhooks** |
| GitHub webhook | `POST /v1/webhooks/github` | ✅ Implemented | [`api.py:284`](../src/handsfree/api.py#L284), [`webhooks.py`](../src/handsfree/webhooks.py), [`db/webhook_events.py`](../src/handsfree/db/webhook_events.py) | **Env:** `GITHUB_WEBHOOK_SECRET` (optional in dev mode). Signature verification, replay protection, event storage, installation lifecycle, notification emission. |
| Webhook retry | `POST /v1/webhooks/retry/{event_id}` | ✅ Implemented (dev-only) | [`api.py:430`](../src/handsfree/api.py#L430) | Dev mode only. Returns 403 in production. |
| **Actions (Policy-Gated)** |
| Request review | `POST /v1/actions/request-review` | ✅ Implemented | [`api.py:1921`](../src/handsfree/api.py#L1921), [`github/client.py`](../src/handsfree/github/client.py) | **Env:** `GITHUB_TOKEN` for live mode. Idempotency, rate limiting, policy evaluation, confirmation flow, audit logging. |
| Rerun checks | `POST /v1/actions/rerun-checks` | ✅ Implemented | [`api.py:2245`](../src/handsfree/api.py#L2245), [`github/client.py`](../src/handsfree/github/client.py) | **Env:** `GITHUB_TOKEN` for live mode. Same capabilities as request_review. |
| Merge PR | `POST /v1/actions/merge` | ✅ Implemented | [`api.py:2517`](../src/handsfree/api.py#L2517), [`github/client.py`](../src/handsfree/github/client.py) | **Env:** `GITHUB_TOKEN` for live mode. **Always requires confirmation.** Deny-by-default policy. |
| **TTS & Dev Tools** |
| TTS | `POST /v1/tts` | ✅ Implemented | [`api.py:3753`](../src/handsfree/api.py#L3753), [`tts/`](../src/handsfree/tts/) | **Env:** `HANDSFREE_TTS_PROVIDER` (stub/openai). Returns audio/wav or audio/mpeg. **Mobile:** TTS playback integrated via [`useGlassesPlayer`](../mobile/src/hooks/useGlassesPlayer.js), iOS/Android native players. |
| Dev audio upload | `POST /v1/dev/audio` | ✅ Implemented (dev-only) | [`api.py:538`](../src/handsfree/api.py#L538) | **Env:** `HANDSFREE_DEV_AUDIO_DIR` (default: data/dev_audio). Base64 upload, returns file:// URI. Dev mode only. **Mobile:** Audio upload integrated. |
| **Notifications** |
| List notifications | `GET /v1/notifications` | ✅ Implemented | [`api.py:3692`](../src/handsfree/api.py#L3692), [`db/notifications.py`](../src/handsfree/db/notifications.py) | Poll-based retrieval with `since` timestamp filtering. **Mobile:** Push integration exists ([`src/push/`](../mobile/src/push/)). |
| Get notification | `GET /v1/notifications/{notification_id}` | ✅ Implemented | [`api.py:4597`](../src/handsfree/api.py#L4597), [`db/notifications.py`](../src/handsfree/db/notifications.py) | Returns single notification by ID. |
| Create sub | `POST /v1/notifications/subscriptions` | ✅ Implemented | [`api.py:4476`](../src/handsfree/api.py#L4476), [`db/notification_subscriptions.py`](../src/handsfree/db/notification_subscriptions.py) | Registers push token. **Env:** `HANDSFREE_NOTIFICATION_PROVIDER` (logger/webpush/apns/fcm). **Mobile:** Token registration integrated. |
| List subs | `GET /v1/notifications/subscriptions` | ✅ Implemented | [`api.py:4517`](../src/handsfree/api.py#L4517) | Lists user's push subscriptions. |
| Delete sub | `DELETE /v1/notifications/subscriptions/{subscription_id}` | ✅ Implemented | [`api.py:4551`](../src/handsfree/api.py#L4551) | Unregisters push token. |
| **Repo Subscriptions** |
| Create repo sub | `POST /v1/repos/subscriptions` | ✅ Implemented | [`api.py:4331`](../src/handsfree/api.py#L4331), [`db/repo_subscriptions.py`](../src/handsfree/db/repo_subscriptions.py) | Associates user with repo for webhook notifications. Requires `installation_id`. |
| List repo subs | `GET /v1/repos/subscriptions` | ✅ Implemented | [`api.py:4381`](../src/handsfree/api.py#L4381) | Lists user's repo subscriptions. |
| Delete repo sub | `DELETE /v1/repos/subscriptions/{repo_full_name}` | ✅ Implemented | [`api.py:4425`](../src/handsfree/api.py#L4425) | Removes repo subscription. |
| **GitHub OAuth & Connections** |
| OAuth start | `GET /v1/github/oauth/start` | ✅ Implemented | [`api.py:4030`](../src/handsfree/api.py#L4030) | **Env:** `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`, `GITHUB_OAUTH_REDIRECT_URI`. Returns authorization URL with state token. |
| OAuth callback | `GET /v1/github/oauth/callback` | ✅ Implemented | [`api.py:4104`](../src/handsfree/api.py#L4104) | Exchanges code for access token. State validation. Stores token securely via secret manager. |
| Create connection | `POST /v1/github/connections` | ✅ Implemented | [`api.py:3841`](../src/handsfree/api.py#L3841), [`db/github_connections.py`](../src/handsfree/db/github_connections.py) | Securely stores GitHub token. **Env:** `SECRET_MANAGER_TYPE` (env/vault/aws/gcp). |
| List connections | `GET /v1/github/connections` | ✅ Implemented | [`api.py:3920`](../src/handsfree/api.py#L3920) | Lists user's GitHub connections (tokens not returned). |
| Get connection | `GET /v1/github/connections/{connection_id}` | ✅ Implemented | [`api.py:3952`](../src/handsfree/api.py#L3952) | Gets single connection details. |
| Delete connection | `DELETE /v1/github/connections/{connection_id}` | ✅ Implemented | [`api.py:3993`](../src/handsfree/api.py#L3993) | Removes GitHub connection. |
| **Agent Tasks (Dev-Only)** |
| Start task | `POST /v1/agents/tasks/{task_id}/start` | ✅ Implemented (dev-only) | [`api.py:4645`](../src/handsfree/api.py#L4645), [`agents/service.py`](../src/handsfree/agents/service.py) | Dev mode only. Transitions task created→running. |
| Complete task | `POST /v1/agents/tasks/{task_id}/complete` | ✅ Implemented (dev-only) | [`api.py:4722`](../src/handsfree/api.py#L4722), [`agents/service.py`](../src/handsfree/agents/service.py) | Dev mode only. Transitions task running→completed. |
| Fail task | `POST /v1/agents/tasks/{task_id}/fail` | ✅ Implemented (dev-only) | [`api.py:4800`](../src/handsfree/api.py#L4800), [`agents/service.py`](../src/handsfree/agents/service.py) | Dev mode only. Transitions task to failed state. |
| **Admin - API Keys** |
| Create API key | `POST /v1/admin/api-keys` | ✅ Implemented | [`api.py:4883`](../src/handsfree/api.py#L4883), [`db/api_keys.py`](../src/handsfree/db/api_keys.py) | Creates user API key. Returns plaintext key once. |
| List API keys | `GET /v1/admin/api-keys` | ✅ Implemented | [`api.py:4931`](../src/handsfree/api.py#L4931) | Lists user's API keys (no plaintext). Filter by `include_revoked`. |
| Revoke API key | `DELETE /v1/admin/api-keys/{key_id}` | ✅ Implemented | [`api.py:4967`](../src/handsfree/api.py#L4967) | Revokes API key. Ownership verified. |

### Summary
- **Total OpenAPI endpoints:** 31
- **Implemented:** 31 ✅ (100%)
- **Partial:** 0
- **Missing:** 0

**All endpoints are fully implemented.** The backend has comprehensive fixture/stub support for offline development, with live integrations available via environment configuration.

## Matrix: MVP checklist coverage

### MVP1: Read-only PR Inbox

| Component | Item | Status | Implementation | Gaps / Notes |
|---|---|---|---|---|
| **Audio Capture** | Wearable audio capture → mobile | ✅ Implemented | iOS: [`glasses/ios/GlassesRecorder.swift`](../mobile/glasses/ios/GlassesRecorder.swift), Android: [`glasses/android/GlassesRecorder.kt`](../mobile/glasses/android/GlassesRecorder.kt), React Native bridge: [`modules/expo-glasses-audio`](../mobile/modules/expo-glasses-audio/) | **Working:** 16kHz WAV recording from Bluetooth mic. **Known issue:** iOS Bluetooth mic can be unreliable (HSP/HFP profile switching). **Fallback:** Phone mic via [`AudioRouteMonitor`](../mobile/glasses/ios/AudioRouteMonitor.swift). |
| **STT** | STT (backend or on-device) → text | ✅ Implemented | Backend: [`stt/`](../src/handsfree/stt/), OpenAI provider: [`stt/openai_provider.py`](../src/handsfree/stt/openai_provider.py), Stub provider: [`stt/stub_provider.py`](../src/handsfree/stt/stub_provider.py) | **Config:** `HANDSFREE_STT_PROVIDER=openai` + `OPENAI_API_KEY=sk-...` for live. Stub mode for deterministic dev. No on-device STT yet (future). |
| **Intent** | Intent: inbox.list | ✅ Implemented | [`commands/intent_parser.py`](../src/handsfree/commands/intent_parser.py), [`handlers/inbox.py`](../src/handsfree/handlers/inbox.py) | Supports "show my inbox", "list PRs", "what's new". Profile-based filtering (workout mode, etc.). |
| **GitHub Auth** | GitHub auth (GitHub App or OAuth) | ✅ Implemented | OAuth flow: [`api.py:4030-4104`](../src/handsfree/api.py#L4030), Connections: [`db/github_connections.py`](../src/handsfree/db/github_connections.py), Secret storage: [`secrets/`](../src/handsfree/secrets/) | **Config:** `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET` for OAuth. Or `GITHUB_TOKEN` for PAT. Or `GITHUB_APP_ID` + private key for GitHub App. **Mobile:** OAuth not integrated in mobile UI yet (use PAT). |
| **Fetch PRs** | Fetch PR list + checks | ✅ Implemented | GitHub provider: [`github/`](../src/handsfree/github/), Live client: [`github/live_provider.py`](../src/handsfree/github/live_provider.py), Fixtures: [`github/fixture_provider.py`](../src/handsfree/github/fixture_provider.py) | Live mode requires `GITHUB_TOKEN` or OAuth. Fetches open PRs, checks status, reviews. Falls back to fixtures. |
| **TTS Playback** | TTS response playback | ✅ Implemented | Backend: [`tts/`](../src/handsfree/tts/), Mobile: iOS player: [`glasses/ios/GlassesPlayer.swift`](../mobile/glasses/ios/GlassesPlayer.swift), Android: [`glasses/android/GlassesPlayer.kt`](../mobile/glasses/android/GlassesPlayer.kt), React Native hook: [`hooks/useGlassesPlayer.js`](../mobile/src/hooks/useGlassesPlayer.js) | **Config:** `HANDSFREE_TTS_PROVIDER=openai` for realistic voice. Stub returns deterministic audio. **Mobile:** Playback through glasses speakers working. Known latency: ~100-200ms Bluetooth. |
| **Action Log** | Basic action log | ✅ Implemented | DB table: [`db/action_logs.py`](../src/handsfree/db/action_logs.py), Audit logging in all action endpoints | Logs all side-effect actions (request_review, rerun_checks, merge). Includes user_id, timestamp, action_type, outcome. |
| **E2E Demo** | Complete MVP1 demo flow | ⚠️ **Partial** | Runbook: [`docs/ios-rayban-mvp1-demo-runbook.md`](../docs/ios-rayban-mvp1-demo-runbook.md), Checklist: [`docs/mvp1-demo-checklist.md`](../docs/mvp1-demo-checklist.md) | **Working:** Backend + mobile components all built. **Gap:** Mobile UI needs polish (settings screen for backend URL, OAuth flow not integrated). **Workaround:** Command-line curl + manual token setup works. |

### MVP2: PR Summary

| Component | Item | Status | Implementation | Gaps / Notes |
|---|---|---|---|---|
| **Intent** | Intent: pr.summarize | ✅ Implemented | [`commands/intent_parser.py`](../src/handsfree/commands/intent_parser.py), [`handlers/pr_summary.py`](../src/handsfree/handlers/pr_summary.py) | Supports "summarize PR 123", "tell me about PR one two three". Extracts PR number, fetches details. |
| **Summary** | Summarize description + diff stats + checks + reviews | ✅ Implemented | [`handlers/pr_summary.py`](../src/handsfree/handlers/pr_summary.py) | Returns title, author, diff stats, check status, review count, merge readiness. Profile-aware (shorter in workout mode). |
| **Navigation** | "Repeat" + "next" navigation | ✅ Implemented | Intent parser handles `inbox.next`, `inbox.previous`, `repeat`. Session state tracked in Redis (when enabled) or in-memory. | **Config:** `REDIS_ENABLED=true` for persistent sessions across requests. In-memory fallback available. |
| **Profile** | Profile: Workout (shorter summaries) | ✅ Implemented | [`commands/profiles.py`](../src/handsfree/commands/profiles.py), [`commands/router.py`](../src/handsfree/commands/router.py) | Supports `workout`, `commute`, `default` profiles. Affects verbosity, confirmation requirements. **Mobile:** Profile selection not in UI yet (default profile used). |

### MVP3: One Safe Write Action

| Component | Item | Status | Implementation | Gaps / Notes |
|---|---|---|---|---|
| **Intents** | Intent: pr.request_review OR checks.rerun | ✅ Implemented | Request review: [`api.py:1921`](../src/handsfree/api.py#L1921), Rerun checks: [`api.py:2245`](../src/handsfree/api.py#L2245) | Both intents fully functional. Also supports `pr.merge` (MVP3+). |
| **Confirmation** | Confirmation required | ✅ Implemented | Confirmation flow: [`api.py:1212`](../src/handsfree/api.py#L1212), Pending actions: [`db/pending_actions.py`](../src/handsfree/db/pending_actions.py) | Exactly-once semantics. Pending action created, expires in 5 minutes. **Mobile:** Confirmation screen exists ([`ConfirmationScreen.js`](../mobile/src/screens/ConfirmationScreen.js)). **Gap:** Voice-based confirmation ("yes"/"no") not integrated in mobile UI flow yet. |
| **Policy** | Policy gate (repo allowlist) | ✅ Implemented | [`policy.py`](../src/handsfree/policy.py), Policy evaluation in all action endpoints | Configurable policies: ALLOW, REQUIRE_CONFIRMATION (default), DENY. Repo allowlists, action-specific policies. **Config:** Policies currently hardcoded in code. No config file or admin UI yet. |
| **Audit** | Audit entry + spoken confirmation | ✅ Implemented | Action logs: [`db/action_logs.py`](../src/handsfree/db/action_logs.py), Spoken confirmation in action responses | All actions logged. Response includes spoken confirmation: "Review requested from Alice on PR 123." |

### MVP4: Agent Delegation

| Component | Item | Status | Implementation | Gaps / Notes |
|---|---|---|---|---|
| **Intent** | Intent: agent.delegate | ✅ Implemented | Intent parser + router, Agent providers: [`agent_providers.py`](../src/handsfree/agent_providers.py) | Supports "create a PR to fix issue 123", "delegate this to an agent". Provider types: copilot (stub), mock (test), github_issue_dispatch (real). |
| **Task Lifecycle** | Task lifecycle tracking | ✅ Implemented | [`agents/service.py`](../src/handsfree/agents/service.py), DB: [`db/agent_tasks.py`](../src/handsfree/db/agent_tasks.py) | Task states: created, running, needs_input, completed, failed. State transitions via API endpoints (dev mode). **Gap:** No mobile UI for task status yet. |
| **Notify** | Notify on PR creation / completion | ⚠️ **Partial** | Notification system: [`db/notifications.py`](../src/handsfree/db/notifications.py), Push delivery: [`notifications/`](../src/handsfree/notifications/) | Notification emission works. Push delivery configured (`HANDSFREE_NOTIFICATION_PROVIDER=apns/fcm`). **Gap:** Agent runner doesn't emit notifications yet (needs integration). **Mobile:** Push receive handler exists, TTS playback of notifications not automated. |

### Summary

- **MVP1:** ✅ **Functionally complete.** All backend + mobile components implemented. Minor UI polish needed (settings, OAuth flow).
- **MVP2:** ✅ **Functionally complete.** PR summary and navigation working. Profile selection not in mobile UI.
- **MVP3:** ⚠️ **Mostly complete.** Write actions + confirmation backend working. Voice confirmation flow not integrated in mobile UI.
- **MVP4:** ⚠️ **Mostly complete.** Agent delegation backend working. Mobile task status UI and notification automation missing.

## Demo blockers (iOS + Ray-Ban Meta)

Based on the MVP1 demo requirements and current implementation status, here are the critical blockers ranked by impact:

### 1. **Mobile Settings Screen: Backend URL Configuration** (HIGH - Demo Blocker)
**Problem:** No UI for setting backend URL. Current demo requires hardcoded IP or manual config file edits.

**Impact:** Cannot easily switch between local backend (dev machine) and remote backend (demo server). First-time demo setup is error-prone.

**Current State:** [`SettingsScreen.js`](../mobile/src/screens/SettingsScreen.js) exists but lacks backend URL input field.

**Fix Required:**
- Add backend URL input to Settings screen
- Persist URL to AsyncStorage
- Update [`api/config.js`](../mobile/src/api/config.js) to read from storage
- Add "Test Connection" button that calls `/v1/status`

**Workaround:** Manually edit `mobile/src/api/config.js` before build. Works but not demo-friendly.

---

### 2. **Bluetooth Microphone Reliability on iOS** (HIGH - Demo Blocker)
**Problem:** iOS Bluetooth microphone (via Ray-Ban Meta glasses) can be unreliable. Audio profile switching (A2DP ↔ HFP/HSP) causes dropouts, latency spikes, or complete audio loss.

**Impact:** Voice commands may not be captured consistently. Demo can fail mid-flow if Bluetooth mic disconnects or switches profiles.

**Current State:** Audio route monitor implemented ([`AudioRouteMonitor.swift`](../mobile/glasses/ios/AudioRouteMonitor.swift)). Fallback to phone mic exists but not exposed in UI.

**Fix Required:**
- Add audio source selector in mobile UI (Bluetooth mic / Phone mic / Manual switch)
- Expose route monitor events in React Native layer
- Show notification when route changes unexpectedly
- OR: Default to phone mic, use glasses only for playback (recommended for MVP1 demos)

**Workaround:** Use phone mic for capture, glasses for playback. This is the recommended setup per [`ios-rayban-mvp1-demo-runbook.md`](../docs/ios-rayban-mvp1-demo-runbook.md). **Demo-ready with this workaround.**

---

### 3. **OAuth Flow Not Integrated in Mobile UI** (MEDIUM - Not Critical for MVP1)
**Problem:** GitHub OAuth flow works on backend, but mobile app doesn't have UI to initiate OAuth or handle callback.

**Impact:** Cannot demo "login with GitHub" flow. Must use pre-configured PAT or manual token setup.

**Current State:** Backend OAuth endpoints implemented ([`api.py:4030-4104`](../src/handsfree/api.py#L4030)). Mobile has no OAuth screen.

**Fix Required:**
- Add "Login with GitHub" button to Settings screen
- Open OAuth URL in WebView or system browser
- Handle redirect URI (deep link or custom scheme)
- Store connection_id in AsyncStorage
- Include connection_id in API requests

**Workaround:** Set `GITHUB_TOKEN` in backend `.env` file. All API calls use this token. **Works for demos**, but not user-friendly.

---

### 4. **Voice Confirmation Flow (MVP3)** (MEDIUM - Required for Write Actions)
**Problem:** Confirmation screen exists ([`ConfirmationScreen.js`](../mobile/src/screens/ConfirmationScreen.js)) but requires tapping buttons. No voice-based "yes"/"no" confirmation.

**Impact:** Cannot demo hands-free write actions (request review, rerun checks, merge). Must touch phone screen to confirm.

**Current State:** Backend confirmation endpoint works ([`api.py:1212`](../src/handsfree/api.py#L1212)). Mobile screen requires manual tap.

**Fix Required:**
- After pending action created, listen for "yes"/"no"/"confirm"/"cancel" voice commands
- Send confirmation request to `/v1/commands/confirm` on "yes"
- Show timeout countdown (5 minutes) in UI
- Auto-dismiss confirmation screen on timeout or completion

**Workaround:** Tap "Confirm" button on phone screen. **Acceptable for MVP1 demos** (inbox is read-only). **Blocks MVP3 demos.**

---

### 5. **Push Notification → Spoken Summary (MVP1/MVP4)** (LOW - Not Critical)
**Problem:** Push notifications work (backend → mobile), but TTS playback of notification content is not automated. User must open app and navigate to notification screen.

**Impact:** Cannot demo "notification arrives, spoken aloud immediately" flow. Reduces hands-free value.

**Current State:**
- Backend push delivery works ([`notifications/`](../src/handsfree/notifications/))
- Mobile push receive handler exists ([`push/notificationsHandler.js`](../mobile/src/push/notificationsHandler.js))
- TTS playback works ([`useGlassesPlayer.js`](../mobile/src/hooks/useGlassesPlayer.js))

**Fix Required:**
- On push notification received, fetch notification content via `/v1/notifications/{notification_id}`
- Call `/v1/tts` with notification summary
- Automatically play TTS audio through glasses (even if app is backgrounded)
- Requires iOS/Android background audio permissions and implementation

**Workaround:** User opens app and navigates to notification manually. **Not hands-free**, but demonstrates the pieces work. **Not critical for MVP1 inbox demo.**

---

### 6. **Profile Selection in Mobile UI** (LOW - Not Critical)
**Problem:** Backend supports profiles (workout, commute, default) but mobile UI has no profile selector.

**Impact:** Cannot demo "shorter summaries during workout" or other profile-based behavior changes. Always uses default profile.

**Current State:** Backend profiles implemented ([`commands/profiles.py`](../src/handsfree/commands/profiles.py)). Mobile sends no profile in requests.

**Fix Required:**
- Add profile dropdown to Settings screen or Command screen
- Include selected profile in `CommandRequest.context` payload
- Persist profile preference to AsyncStorage

**Workaround:** Backend uses default profile for all requests. **Acceptable for MVP1.** Profile-specific behavior can be demoed via curl with manual profile parameter.

---

### Priority Fix for Next PR

For a **fully hands-free iOS + Ray-Ban Meta MVP1 demo**, fix **#1 (Settings Screen)** and use **#2 workaround (phone mic + glasses playback)**. This makes the demo setup reproducible and reliable.

Items #3-#6 are enhancements for future MVPs (MVP2-MVP4) but do not block MVP1 inbox/summary demo. 

## Proposed PR sequence

This section proposes 5-10 PRs to close the remaining gaps, prioritized by MVP and demo impact. Each PR builds on previous work and has clear dependencies.

---

### PR-067: Mobile Settings Screen - Backend URL + Connection Test
**Goal:** Enable easy backend URL configuration in mobile UI for demos.

**Scope:**
- Add backend URL input field to Settings screen
- Persist URL to AsyncStorage
- Add "Test Connection" button → calls `/v1/status`
- Display connection status (✅ connected / ❌ failed)

**Dependencies:** None

**Files:**
- `mobile/src/screens/SettingsScreen.js`
- `mobile/src/api/config.js`

**Acceptance Criteria:**
- User can enter backend URL (e.g., `http://192.168.1.100:8080`)
- URL persisted across app restarts
- Test connection validates URL before saving
- Error handling for invalid URLs or unreachable backends

**Priority:** 🔴 **HIGH - MVP1 Demo Blocker**

---

### PR-068: Mobile Audio Source Selector (Bluetooth vs Phone Mic)
**Goal:** Give users manual control over audio input source to work around Bluetooth mic reliability issues.

**Scope:**
- Add audio source toggle to Settings or Diagnostics screen (Bluetooth Mic / Phone Mic / Auto)
- Expose audio route change events from native layer to React Native
- Show in-app notification when route changes unexpectedly
- Persist audio source preference

**Dependencies:** None (uses existing `AudioRouteMonitor` native module)

**Files:**
- `mobile/src/screens/SettingsScreen.js` or `mobile/src/screens/GlassesDiagnosticsScreen.js`
- `mobile/glasses/ios/AudioRouteMonitor.swift`
- `mobile/glasses/android/AudioRouteMonitor.kt`

**Acceptance Criteria:**
- User can force phone mic or Bluetooth mic
- Route change notifications appear in UI
- Audio diagnostics screen shows current input/output devices

**Priority:** 🔴 **HIGH - MVP1 Demo Reliability**

---

### PR-069: Mobile OAuth Flow Integration (GitHub Login)
**Goal:** Enable GitHub OAuth login from mobile app.

**Scope:**
- Add "Login with GitHub" button to Settings screen
- Open OAuth flow in WebView or system browser
- Handle redirect URI via deep link (e.g., `handsfree://oauth/callback`)
- Exchange code for connection_id
- Store connection_id, include in API requests via `X-Connection-ID` header

**Dependencies:** None (backend OAuth flow already implemented)

**Files:**
- `mobile/src/screens/SettingsScreen.js`
- `mobile/src/api/client.js` (add connection_id to headers)
- `mobile/app.json` (register deep link scheme)

**Acceptance Criteria:**
- User taps "Login with GitHub", completes OAuth in browser
- App receives callback, stores connection securely
- API requests include connection_id
- Logout button clears connection

**Priority:** 🟡 **MEDIUM - MVP1 Polish** (not required for demo with PAT)

---

### PR-070: Voice-Based Confirmation Flow (MVP3)
**Goal:** Enable fully hands-free confirmation for write actions.

**Scope:**
- After pending action created, show confirmation screen
- Listen for voice commands: "yes", "no", "confirm", "cancel"
- On "yes": Call `/v1/commands/confirm`
- On "no": Dismiss screen, no action taken
- Show 5-minute countdown timer, auto-cancel on timeout

**Dependencies:** PR-067 (backend URL config)

**Files:**
- `mobile/src/screens/ConfirmationScreen.js`
- `mobile/src/screens/CommandScreen.js` (handle pending action state)
- Update command flow to listen for confirmation keywords

**Acceptance Criteria:**
- User speaks "yes" or "no" to confirm/cancel action
- No screen taps required
- Timeout after 5 minutes with spoken notice
- Works with request_review, rerun_checks, merge actions

**Priority:** 🟡 **MEDIUM - MVP3 Requirement** (not needed for MVP1 read-only inbox)

---

### PR-071: Profile Selection UI (MVP2)
**Goal:** Allow user to select profile (workout, commute, default) in mobile app.

**Scope:**
- Add profile dropdown to Settings screen
- Persist profile selection to AsyncStorage
- Include profile in `CommandRequest.context.profile`
- Show current profile in Command screen UI

**Dependencies:** None

**Files:**
- `mobile/src/screens/SettingsScreen.js`
- `mobile/src/screens/CommandScreen.js`
- `mobile/src/api/client.js` (include profile in request context)

**Acceptance Criteria:**
- User can select workout, commute, or default profile
- Profile included in all command requests
- Backend respects profile (shorter summaries in workout mode)

**Priority:** 🟢 **LOW - MVP2 Enhancement** (default profile sufficient for MVP1)

---

### PR-072: Push Notification Auto-TTS Playback (MVP1/MVP4)
**Goal:** Automatically speak notification content when push arrives.

**Scope:**
- On push notification received, fetch full notification via `/v1/notifications/{notification_id}`
- Extract spoken summary or title
- Call `/v1/tts` to generate audio
- Play TTS audio through glasses automatically (even if app backgrounded)
- Requires iOS/Android background audio permissions

**Dependencies:** None (uses existing TTS + push infrastructure)

**Files:**
- `mobile/src/push/notificationsHandler.js`
- iOS: Enable background audio in Xcode project capabilities
- Android: Request foreground service permission for background audio

**Acceptance Criteria:**
- Push arrives → audio plays through glasses within 5 seconds
- No user interaction required
- Works when app is backgrounded or locked (iOS background modes)
- User can disable auto-speak in Settings

**Priority:** 🟢 **LOW - MVP1/MVP4 Enhancement** (nice-to-have, not critical)

---

### PR-073: Policy Configuration File (MVP3)
**Goal:** Move hardcoded policies to a configuration file or admin API.

**Scope:**
- Create `config/policies.yaml` or similar
- Load policies at startup or via admin endpoint
- Support repo allowlists, action-specific policies (ALLOW/REQUIRE_CONFIRMATION/DENY)
- Admin API endpoints for CRUD operations on policies (optional)

**Dependencies:** None

**Files:**
- `src/handsfree/policy.py` (read from config file)
- `config/policies.yaml` (new)
- Optional: `src/handsfree/api.py` (admin policy endpoints)

**Acceptance Criteria:**
- Policies configurable without code changes
- Supports per-repo and per-action policies
- Reloads policies without backend restart (optional)

**Priority:** 🟢 **LOW - MVP3 Enhancement** (hardcoded policies work for demo)

---

### PR-074: Agent Task Status UI (MVP4)
**Goal:** Show agent task status in mobile UI.

**Scope:**
- Add "My Tasks" screen or section
- List active agent tasks (created, running, needs_input, completed, failed)
- Show task details: description, state, created_at, updated_at, PR link (if completed)
- Poll `/v1/agents/tasks` endpoint (when implemented) or infer from notifications

**Dependencies:** Backend needs task listing endpoint (not currently in OpenAPI spec)

**Files:**
- `mobile/src/screens/TasksScreen.js` (new)
- Navigation updates to include Tasks tab

**Acceptance Criteria:**
- User can see list of delegated tasks
- Task state updates in real-time or on refresh
- Tapping completed task opens PR in browser

**Priority:** 🟢 **LOW - MVP4 Enhancement** (agent delegation works without UI, user gets notification on completion)

---

### PR-075: Agent Notification Integration
**Goal:** Emit notifications when agent tasks complete or fail.

**Scope:**
- Update agent runner or task completion logic to call notification API
- Emit notification on task state changes: running → completed, running → failed
- Include PR URL in notification payload
- Mobile app already handles notifications (no changes needed)

**Dependencies:** Agent runner integration

**Files:**
- External agent runner code (if using GitHub Actions)
- OR: `src/handsfree/agents/service.py` (if backend task completion triggers notifications)

**Acceptance Criteria:**
- Task completion → push notification sent
- Notification includes "PR created: <url>" or "Task failed: <reason>"
- User receives push on mobile device

**Priority:** 🟢 **LOW - MVP4 Enhancement** (agent delegation works, just missing notification hookup)

---

### Dependencies Graph

```
PR-067 (Settings Screen) ──────┐
                               ├──> PR-070 (Voice Confirmation)
                               │
PR-068 (Audio Source) ─────────┤
                               │
PR-069 (OAuth Flow) ───────────┤
                               │
                               └──> [All future PRs can proceed independently]

PR-071 (Profile UI) ──────────> [Independent]
PR-072 (Auto-TTS Notif) ──────> [Independent]
PR-073 (Policy Config) ───────> [Independent]
PR-074 (Task Status UI) ──────> [Independent]
PR-075 (Agent Notif) ─────────> [Independent]
```

---

### Recommended Sequence

**For MVP1 Demo (Next 1-2 PRs):**
1. ✅ **PR-067** (Settings Screen) - Unblocks repeatable demo setup
2. ✅ **PR-068** (Audio Source Selector) - Improves demo reliability

**For MVP2/MVP3 (Next 3-4 PRs):**
3. **PR-069** (OAuth Flow) - Polishes user experience
4. **PR-070** (Voice Confirmation) - Enables MVP3 hands-free write actions
5. **PR-071** (Profile UI) - Completes MVP2 profile feature

**For MVP4 (Future PRs):**
6. **PR-072** (Auto-TTS Notifications) - Enhances notification UX
7. **PR-073** (Policy Config) - Production-ready policy management
8. **PR-074** (Task Status UI) - Agent task visibility
9. **PR-075** (Agent Notifications) - Closes MVP4 notification loop

---

**Total PRs:** 9 (PR-067 through PR-075)

All backend work is complete. These PRs focus on **mobile UI polish** and **production configuration** to close the remaining MVP gaps. 
