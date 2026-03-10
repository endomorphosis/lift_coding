# Documentation Gap Analysis: HandsFree Dev Companion

Historical note: this file is a point-in-time audit snapshot from March 9, 2026. It may intentionally describe gaps that have since been closed, so treat the current active docs and code as the source of truth.

**Analysis Date:** March 9, 2026  
**Scope:** Comparison of CODEBASE_INVENTORY.md features against README.md, GETTING_STARTED.md, ARCHITECTURE.md, CONFIGURATION.md, mobile/README.md, AUTHENTICATION.md, and spec/openapi.yaml

---

## Executive Summary

The codebase has **47 identified documentation gaps** across 10 categories. **18 High-severity gaps** require immediate attention (blocking understanding of core features), **16 Medium-severity gaps** improve clarity and maintainability, and **13 Low-severity gaps** enhance optional feature discoverability.

**Priority:** Implement High-severity PRs in order. Medium-severity PRs improve developer experience. Low-severity PRs can be deferred.

---

## HIGH SEVERITY GAPS (18 items)

### 1. Database Schema Not Documented
**Severity:** HIGH  
**Category:** Database Schema  
**What's Missing:** Complete ER diagram and table relationship documentation

- `CODEBASE_INVENTORY.md` lists 20 database tables in detail
- `migrations/` folder has 15 migration files with cryptic names (e.g., `006_add_notification_throttling_dedupe.sql`)
- `ARCHITECTURE.md` shows only 8 sample tables (commands, pending_actions, notifications, etc.)
- **Missing:** Foreign keys, indexes, constraints, query patterns, data lifecycle

**Code Location:**
- [migrations/](migrations/) - 15 migration files
- [src/handsfree/db/](src/handsfree/db/) - Connection and model files
- [src/handsfree/db/](src/handsfree/db/): commands.py, notifications.py, webhook_events.py, etc.

**Should Be Documented In:** [ARCHITECTURE.md](ARCHITECTURE.md#database-schema) - expand section with:
- Complete ERD diagram
- All 20 tables with purposes and key fields
- Relationship map
- Lifecycle stages (e.g., webhook_events: received → processed → deduped)
- Data retention policies

**PR Suggestion:**
```
Title: Docs: Add complete database schema documentation with ERD
- Create ERD diagram (graphviz/mermaid) showing all 20 tables
- Document each table: purpose, key fields, retention policy
- Add query pattern examples (e.g., webhook deduplication)
- Link from ARCHITECTURE.md and CONFIGURATION.md
```

---

### 2. OpenAPI Specification Incomplete vs API Code

**Severity:** HIGH  
**Category:** API Endpoints  
**What's Missing:** 20+ endpoints listed in CODEBASE_INVENTORY but missing from public docs

- `CODEBASE_INVENTORY.md` lists 40+ endpoints across 11 categories
- `spec/openapi.yaml` exists but incomplete (saw only 6-10 endpoints in sample)
- Main docs (README, ARCHITECTURE) mention only 6-8 endpoints
- **Missing from docs:**
  - `/v1/agents/tasks/{task_id}/*` endpoints (pause, resume, cancel, start, complete, fail, media)
  - `/v1/metrics` (observability endpoint)
  - `/v1/admin/api-keys` (API key management)
  - `/v1/dev/peer-envelope` (P2P testing)
  - `/v1/dev/transport-sessions` (transport debugging)
  - All agent task filtering/sorting parameters

**Code Location:**
- [spec/openapi.yaml](../../spec/openapi.yaml) - definition file
- [src/handsfree/api.py](src/handsfree/api.py) - endpoint handlers

**Should Be Documented In:** 
- [spec/openapi.yaml](../../spec/openapi.yaml) - complete spec
- [ARCHITECTURE.md#api-architecture](ARCHITECTURE.md#api-architecture) - endpoint summary table

**PR Suggestion:**
```
Title: Docs: Complete OpenAPI specification with all endpoints
- Add missing endpoint definitions to spec/openapi.yaml
- Include request/response examples for each endpoint
- Add endpoint categories (core, agent, admin, dev/testing)
- Link OpenAPI spec from README in "API Reference" section
- Add endpoint authentication requirements
```

---

### 3. Agent Delegation Workflow Not Clearly Documented

**Severity:** HIGH  
**Category:** Features - Agent System  
**What's Missing:** Complete end-to-end workflow documentation

- Code has `agents/`, `delegation.py`, `runner.py` modules with 7+ intents
- `README.md` mentions "Agent Delegation" section but only 1 paragraph
- Doesn't explain the full flow:
  - How tasks are created and dispatched
  - Provider selection logic (explicit vs env var vs default)
  - Correlation between dispatch issues and PRs
  - Task state transitions (spawned → running → completed → failed)
  - How results are retrieved and surfaced to user

**Code Location:**
- [src/handsfree/agents/](src/handsfree/agents/) - service.py, delegation.py, runner.py, results_views.py
- [src/handsfree/commands/](src/handsfree/commands/) - router.py (agent intent handlers)
- [src/handsfree/db/agent_tasks.py](src/handsfree/db/agent_tasks.py) - task lifecycle

**Should Be Documented In:** 
- New file: `docs/agent-delegation-workflow.md`
- Update: [ARCHITECTURE.md](ARCHITECTURE.md#agent-delegation) (expand section)

**PR Suggestion:**
```
Title: Docs: Add comprehensive agent delegation workflow guide
- Create agent-delegation-workflow.md with flowchart
- Document state transitions: spawned → running → completed
- Explain provider selection: explicit > env var > github_issue_dispatch > copilot
- Show MCP task creation and correlation examples
- Document result filtering and follow-on task behavior
- Link from README "Agent Delegation" section
```

---

### 4. Mobile App Screens and Navigation Not Comprehensively Documented

**Severity:** HIGH  
**Category:** Mobile Features  
**What's Missing:** Complete screen reference with features per screen

- `CODEBASE_INVENTORY.md` lists 11 screens (including experimental)
- `mobile/README.md` documents only 6 screens at high level
- **Missing screens from docs:**
  - GlassesDiagnosticsScreen (Bluetooth debugging)
  - PeerChatDiagnosticsScreen (P2P chat debugging)
  - ResultsScreen (Agent task results)
  - ActiveTasksScreen (Running task monitoring)
  - TaskDetailScreen (Task details)

- **Missing features per screen:**
  - ActionPromptModal (inline action execution)
  - FollowOnTaskCard (next task visualization)
  - Audio source selection UI
  - Profile selector UI

**Code Location:**
- [mobile/src/screens/](mobile/src/screens/) - all screen components
- [mobile/src/components/](mobile/src/components/) - reusable UI components

**Should Be Documented In:** 
- Update: [mobile/README.md](mobile/README.md#-app-screens) - expand section
- New file: `mobile/SCREENS_REFERENCE.md` - detailed screen guide

**PR Suggestion:**
```
Title: Docs: Add complete mobile app screens reference
- Create SCREENS_REFERENCE.md with all 11 screens
- Per screen: purpose, key features, UI elements, navigation
- Add screenshots/wireframes for each screen
- Document experimental screens (GlassesDiagnostics, PeerChat)
- Show component hierarchy and feature flags
- Link from mobile/README.md
```

---

### 5. Authentication Modes Not Linked to API Documentation

**Severity:** HIGH  
**Category:** Authentication  
**What's Missing:** Which endpoints require what auth, clear integration guide

- `docs/AUTHENTICATION.md` exists and is comprehensive
- But **not referenced** from:
  - README.md (should be in Quick Links)
  - CONFIGURATION.md (mentions auth modes, should link to detailed guide)
  - GETTING_STARTED.md
  - OpenAPI spec (auth requirements not in endpoint definitions)

- Also missing from AUTHENTICATION.md:
  - Which endpoints are public vs protected
  - Default auth mode per deployment context
  - Secrets rotation best practices
  - Auth error codes and troubleshooting

**Code Location:**
- [src/handsfree/auth.py](src/handsfree/auth.py) - auth implementation
- [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) - existing guide

**Should Be Documented In:**
- [README.md](../../README.md) - add link to AUTHENTICATION.md
- [GETTING_STARTED.md](../GETTING_STARTED.md) - add auth setup section
- [spec/openapi.yaml](../../spec/openapi.yaml) - add auth scheme definitions
- Expand [AUTHENTICATION.md](docs/AUTHENTICATION.md) with:
  - Protected vs public endpoints table
  - Auth error codes reference
  - Migration guide from dev → prod modes

**PR Suggestion:**
```
Title: Docs: Link authentication documentation and add protected endpoints table
- Add auth scheme definitions to OpenAPI spec
- Create protected endpoints reference table
- Link AUTHENTICATION.md from README.md Quick Links
- Add troubleshooting section for auth errors
- Document auth setup for each deployment context
```

---

### 6. Configuration Options - Advanced Settings Not Listed

**Severity:** HIGH  
**Category:** Configuration  
**What's Missing:** 30+ environment variables not documented

From codebase analysis, these vars exist in code but not in CONFIGURATION.md:
- `HANDSFREE_ENABLE_METRICS` - Metrics collection feature flag
- `HANDSFREE_ENABLE_AI_ENHANCED_COMMANDS` - AI features toggle
- `HANDSFREE_TTS_CACHE_ENABLED` - TTS caching
- `HANDSFREE_COMMAND_TIMEOUT_S` - Command execution timeout
- `HANDSFREE_WEBHOOK_DEDUP_WINDOW_S` - Webhook deduplication window
- `HANDSFREE_RATE_LIMIT_*` - All rate limit settings
- `HANDSFREE_MAX_CONTEXT_LENGTH` - Context window limit
- Audio/image fetch settings:
  - `AUDIO_FETCH_TIMEOUT_SECONDS`
  - `AUDIO_MAX_SIZE_BYTES`
  - `IMAGE_FETCH_TIMEOUT_SECONDS`
  - `IMAGE_MAX_SIZE_BYTES`
- Database settings:
  - `DUCKDB_VACUUM_THRESHOLD_ROWS`
  - `DUCKDB_VACUUM_INTERVAL_HOURS`
- Provider-specific:
  - `HANDSFREE_AGENT_DISPATCH_REPO`
  - `HANDSFREE_AGENT_DEFAULT_PROVIDER`
  - MCP protocol versions and timeouts
  - IPFS provider URLs and auth

**Code Location:**
- [src/handsfree/api.py](src/handsfree/api.py) - env var usage
- [src/handsfree/config/](src/handsfree/) - scattered config loading

**Should Be Documented In:** 
- [CONFIGURATION.md](../CONFIGURATION.md) - add "Advanced Configuration" section
- Create: `docs/configuration-reference.md` - complete env var guide

**PR Suggestion:**
```
Title: Docs: Add complete configuration reference for all environment variables
- Add "Advanced Configuration" section to CONFIGURATION.md
- List all 30+ undocumented env vars with:
  - Purpose and impact
  - Default values
  - Valid ranges/options
  - When to override from defaults
- Organize by subsystem: Server, Database, Cache, AI, Providers
- Add troubleshooting section for common config issues
```

---

### 7. Webhook Processing & Deduplication Not Documented

**Severity:** HIGH  
**Category:** Features - Webhooks  
**What's Missing:** How webhook deduplication works, retry logic, processing flow

- Code has `webhook_events` DB table with deduplication logic
- Code has `/v1/webhooks/retry/{event_id}` endpoint
- Code has notification throttling and deduplication
- **Missing from docs:**
  - Event ID deduplication algorithm
  - Retry policy and exponential backoff
  - How failed webhooks are handled
  - Webhook processing state machine
  - How webhook events trigger agent tasks

**Code Location:**
- [src/handsfree/webhooks.py](src/handsfree/webhooks.py) - signature verification
- [src/handsfree/db/webhook_events.py](src/handsfree/db/webhook_events.py) - event storage
- [src/handsfree/db/notifications.py](src/handsfree/db/notifications.py) - throttling/dedup

**Should Be Documented In:**
- New file: `docs/webhook-processing.md`
- Update: [ARCHITECTURE.md](../ARCHITECTURE.md) - Data Flow section

**PR Suggestion:**
```
Title: Docs: Add webhook processing and deduplication guide
- Document webhook signature verification
- Explain event ID deduplication and idempotency keys
- Show retry policy with exponential backoff
- Detail notification throttling algorithm
- Add webhook event lifecycle diagram
- Include examples of webhook payloads and responses
```

---

### 8. Profiles (Workout/Kitchen/Commute) Not Documented

**Severity:** HIGH  
**Category:** Features - Profiles  
**What's Missing:** What profiles do, how to use them, customization

- Code has `profiles.py` with default profiles
- Mobile app has ProfileSelector component and SettingsScreen
- README mentions profiles briefly: "Workout/Kitchen/Commute/Default"
- **Missing from docs:**
  - What each profile does (brevity level? response filtering? context?)
  - How to switch profiles via voice command
  - Why profiles matter for hands-free use
  - How to customize/create profiles
  - Profile impact on response format

**Code Location:**
- [src/handsfree/commands/profiles.py](src/handsfree/commands/profiles.py)
- [mobile/src/components/ProfileSelector.js](mobile/src/components/ProfileSelector.js)
- [mobile/src/screens/SettingsScreen.js](mobile/src/screens/SettingsScreen.js)

**Should Be Documented In:**
- New file: `docs/profiles-guide.md`
- Update: [README.md](../../README.md) - expand Profiles section
- Update: [mobile/README.md](mobile/README.md) - explain profile selection

**PR Suggestion:**
```
Title: Docs: Add profiles reference guide
- Create profiles-guide.md explaining each profile
- Document voice command: "set profile to kitchen"
- Show profile impact on responses (brevity, filtering)
- Explain custom profile creation
- Add use-case examples (runner in Workout mode, etc.)
- Link from README.md Features section
```

---

### 9. Pending Actions/Confirmation Flow Not Clearly Explained

**Severity:** HIGH  
**Category:** Features - Confirmation  
**What's Missing:** How confirmation tokens work, user experience, timeout handling

- Code has `pending_actions` DB table, `/v1/commands/confirm` endpoint
- CODEBASE_INVENTORY mentions "In-memory + Redis-backed confirmation flow"
- **Missing from docs:**
  - How confirmation tokens are generated and validated
  - Token expiration and timeout handling (default: 5 minutes)
  - User experience: how to confirm (voice: "confirm", UI button, etc.)
  - What happens on timeout
  - Confirmation failure handling

**Code Location:**
- [src/handsfree/commands/pending_actions.py](src/handsfree/commands/pending_actions.py)
- [src/handsfree/db/pending_actions.py](src/handsfree/db/pending_actions.py)

**Should Be Documented In:**
- Update: [ARCHITECTURE.md#data-flow](ARCHITECTURE.md#data-flow) - add confirmation flow diagram
- Update: [mobile/README.md](mobile/README.md#confirmation-screen) or new section

**PR Suggestion:**
```
Title: Docs: Add confirmation flow and pending actions guide
- Explain token generation, validation, expiration
- Document user experience: receive confirmation prompt → confirm → execute
- Show confirmation error cases and recovery
- Add flowchart: intent → confirmation required → confirm → execute
- Explain why certain intents require confirmation (pr.merge, etc.)
```

---

### 10. Privacy Modes & Multimodal Input Not in Main Docs

**Severity:** HIGH  
**Category:** Features - Privacy/Security  
**What's Missing:** Privacy modes and image input feature not mentioned in main docs

- `PRIVACY_MODES_IMPLEMENTATION.md` documents strict/balanced/debug modes
- `CODEBASE_INVENTORY.md` mentions ImageInput support
- **Missing from main docs:**
  - README doesn't mention privacy modes
  - No reference to privacy in GETTING_STARTED.md
  - ARCHITECTURE.md doesn't explain modes

**Code Location:**
- [src/handsfree/models.py](src/handsfree/models.py) - PrivacyMode enum
- [src/handsfree/handlers/pr_summary.py](src/handsfree/handlers/pr_summary.py) - privacy enforcement
- [src/handsfree/handlers/inbox.py](src/handsfree/handlers/inbox.py) - privacy enforcement

**Should Be Documented In:**
- New section in [README.md](../../README.md) - "Privacy Modes"
- Update: [ARCHITECTURE.md](../ARCHITECTURE.md) - mention privacy control
- Create: `docs/privacy-modes-guide.md` - detailed guide

**PR Suggestion:**
```
Title: Docs: Add privacy modes and multimodal input documentation
- Create privacy-modes-guide.md with mode explanations
- Document strict (default) vs balanced vs debug modes
- Add when to use each mode (public vs private context)
- Document image input support and privacy implications
- Update README.md to mention privacy-first approach
```

---

### 11. Experimental Features Not Clearly Marked or Documented

**Severity:** HIGH  
**Category:** Documentation Quality  
**What's Missing:** Which features are experimental, their stability level, roadmap

- CODEBASE_INVENTORY marks features with ✅ Core vs ✅ Experimental
- Main docs don't distinguish experimental from stable
- **Experimental features without clear docs:**
  - MCP Module (client, config, catalog, capabilities, models)
  - libp2p_bluetooth transport
  - OCR module
  - Peer chat (P2P messaging)
  - Transport sessions
  - IPFS providers (ipfs_datasets_mcp, ipfs_kit_mcp, ipfs_accelerate_mcp)
  - Native modules (expo-glasses-audio)

**Code Location:**
- Throughout codebase, marked with "Experimental" in docstrings

**Should Be Documented In:**
- New section in [README.md](../../README.md) - "Experimental Features"
- Update: [ARCHITECTURE.md](../ARCHITECTURE.md) - note experimental components
- Create: `docs/experimental-features-roadmap.md` - stability matrix

**PR Suggestion:**
```
Title: Docs: Add experimental features guide and stability matrix
- Create experimental-features-roadmap.md
- List all 8+ experimental features
- For each: current status, stability level, roadmap
- Note which are safe to use in production vs dev-only
- Add API/feature deprecation policy
- Update README.md with "Experimental Features" section
```

---

### 12. TTS/STT Provider System Not Fully Documented

**Severity:** HIGH  
**Category:** Provider System  
**What's Missing:** How provider abstraction works, how to add new providers

- Code has `tts/` and `stt/` modules with pluggable providers
- CODEBASE_INVENTORY lists: openai_provider.py, stub_provider.py
- CONFIGURATION.md only mentions:
  - `HANDSFREE_TTS_PROVIDER` (stub, openai)
  - `HANDS_FREE_STT_PROVIDER` (stub, openai)
- **Missing:**
  - How provider interface works (abstract class, methods)
  - How to implement custom TTS/STT provider
  - Provider lifecycle (init, authenticate, generate/transcribe, cache)
  - Fallback behavior when provider fails
  - Cost implications of different providers

**Code Location:**
- [src/handsfree/tts/](src/handsfree/tts/) - TTS providers
- [src/handsfree/stt/](src/handsfree/stt/) - STT providers

**Should Be Documented In:**
- New file: `docs/provider-systems.md` - complete provider guide
- Update: [CONFIGURATION.md](../CONFIGURATION.md) - expand provider sections

**PR Suggestion:**
```
Title: Docs: Add provider system architecture and extension guide
- Document provider abstraction: interfaces, lifecycle, error handling
- Create provider implementation guide with examples
- Explain provider selection and fallback logic
- Document cost considerations for each provider
- Add examples: how to implement custom TTS provider
```

---

### 13. Transport Layer Not Documented

**Severity:** HIGH  
**Category:** Provider System  
**What's Missing:** Transport abstraction, how mobile connects to backend

- Code has `transport/` module with `libp2p_bluetooth.py` and `stub_provider.py`
- README mentions "Experimental P2P Transport Template" briefly
- **Missing from docs:**
  - What transport does (message delivery, routing, encryption)
  - How mobile uses transport vs direct HTTPS
  - libp2p_bluetooth implementation details
  - Transport session management
  - When to use P2P vs direct connection

**Code Location:**
- [src/handsfree/transport/](src/handsfree/transport/) - transport providers
- [src/handsfree/db/transport_session_cursors.py](src/handsfree/db/transport_session_cursors.py)

**Should Be Documented In:**
- New file: `docs/transport-architecture.md`
- Update: [ARCHITECTURE.md](ARCHITECTURE.md#transport-layer)

**PR Suggestion:**
```
Title: Docs: Add transport layer architecture documentation
- Explain transport abstraction and role in architecture
- Document libp2p_bluetooth implementation
- Show mobile-to-backend connection options (direct vs P2P)
- Explain transport session state and cursors
- Add troubleshooting guide for Bluetooth issues
```

---

### 14. MCP (Model Context Protocol) Integration Not Documented

**Severity:** HIGH  
**Category:** Provider System  
**What's Missing:** What MCP is, how it's used, configuration guide

- Code has complete `mcp/` module with client, config, catalog, capabilities models
- README mentions "MCP" in quick links context but never explains what it is
- CODEBASE_INVENTORY lists MCP under "AI Module"
- CONFIGURATION.md mentions IPFS MCP providers but not core MCP concept
- **Missing:**
  - What MCP is and why it's used
  - MCP server vs client roles
  - Available MCP servers (IPFS datasets, IPFS kit, IPFS accelerate)
  - How to configure and use MCP
  - MCP capability discovery

**Code Location:**
- [src/handsfree/mcp/](src/handsfree/mcp/) - client, config, catalog, capabilities, models
- [src/handsfree/agents/delegation.py](src/handsfree/agents/delegation.py) - MCP task dispatch

**Should Be Documented In:**
- New file: `docs/mcp-integration.md` - MCP setup and usage guide
- Update: [README.md](../../README.md) - explain MCP role
- Update: [ARCHITECTURE.md](../ARCHITECTURE.md) - MCP section

**PR Suggestion:**
```
Title: Docs: Add MCP integration documentation and configuration guide
- Create mcp-integration.md explaining MCP concept
- Document available MCP servers (IPFS Datasets/Kit/Accelerate)
- Add configuration examples for each MCP server
- Explain capability discovery and tool invocation
- Link from README.md and ARCHITECTURE.md
```

---

### 15. Secrets Management Options Not Compared

**Severity:** HIGH  
**Category:** Configuration  
**What's Missing:** Pro/cons of each secrets backend, selection guide

- Code has `secrets/` module with: env_secrets, aws_secrets, gcp_secrets, vault_secrets
- CONFIGURATION.md mentions backends exist
- **Missing:**
  - Comparison table: env vars vs AWS vs GCP vs Vault
  - When to use each backend
  - Setup instructions for each backend
  - Rotation and expiration policies
  - Secrets access patterns (automatic, on-demand, cached)

**Code Location:**
- [src/handsfree/secrets/](src/handsfree/secrets/) - all implementations

**Should Be Documented In:**
- New file: `docs/secrets-management.md`
- Update: [CONFIGURATION.md](../CONFIGURATION.md) - expand secrets section
- Update: [docs/SECRET_STORAGE_AND_SESSIONS.md](docs/SECRET_STORAGE_AND_SESSIONS.md)

**PR Suggestion:**
```
Title: Docs: Add secrets management comparison and setup guide
- Create secrets-management.md with backend comparison table
- Add setup instructions for AWS, GCP, Vault
- Document auto-detection and fallback logic
- Explain per-secret encryption and rotation
- Link from CONFIGURATION.md
```

---

### 16. Push Notification Providers & Configuration Not Clear

**Severity:** HIGH  
**Category:** Provider System  
**What's Missing:** Expo push vs other providers, device registration flow

- Code supports Expo push notifications
- CONFIGURATION.md mentions `EXPO_PUSH_TOKEN`
- Mobile app documentation minimal
- **Missing:**
  - Device token registration flow
  - How notifications are triggered (webhook → notification service → push)
  - Notification throttling and deduplication
  - Notification delivery tracking  
  - User notification preferences/subscriptions
  - Testing notifications locally

**Code Location:**
- [src/handsfree/push/](src/handsfree/push/) - Expo provider
- [src/handsfree/db/notification_delivery_tracking.py](src/handsfree/db/notification_delivery_tracking.py)
- [mobile/src/hooks/](mobile/src/hooks/) - notification handling

**Should Be Documented In:**
- New file: `docs/push-notifications-setup.md` (expand existing push_notifications.md)
- Update: [mobile/README.md](mobile/README.md) - add notification section

**PR Suggestion:**
```
Title: Docs: Expand push notification documentation and setup guide
- Expand docs/push-notifications.md with complete setup
- Document device token registration and renewal
- Show notification lifecycle: event → throttle → dedupe → deliver
- Add troubleshooting for delivery failures
- Document notification preferences and subscription management
```

---

### 17. GitHub Integration Features Not Fully Documented

**Severity:** HIGH  
**Category:** GitHub Integration  
**What's Missing:** All GitHub capabilities, OAuth flow, connection management

- Code has comprehensive GitHub integration module
- CODEBASE_INVENTORY lists detailed GitHub features
- Main docs mention PR operations but miss other capabilities
- **Missing:**
  - GitHub OAuth flow documentation
  - Connection management (create, list, revoke)
  - Repo subscription management
  - Repo-level policy configuration
  - Rate limiting handling
  - GitHub App vs Personal Token differences

**Code Location:**
- [src/handsfree/github/](src/handsfree/github/) - client, provider, auth, execution
- [src/handsfree/db/github_connections.py](src/handsfree/db/github_connections.py)

**Should Be Documented In:**
- New file: `docs/github-integration-guide.md`
- Update: [ARCHITECTURE.md](ARCHITECTURE.md#github-integration) - detailed integration section

**PR Suggestion:**
```
Title: Docs: Add comprehensive GitHub integration guide
- Create github-integration-guide.md
- Document OAuth flow with sequence diagram
- Explain connection management endpoints
- Document repo subscription and policy features
- Show examples of PR operations (merge, comment, request-review)
- Link from README.md GitHub Integration section
```

---

### 18. API Response Card Types Not Documented

**Severity:** HIGH  
**Category:** API  
**What's Missing:** All UI card types that can be returned in API responses

- Code has UICardList component rendering "API response cards"
- Response schema references "cards" field
- **Missing documentation of all card types:**
  - pr_summary card
  - check_run card
  - mention card
  - inbox_item card
  - agent_task card
  - follow_on_task card
  - And others implied in code

- **Missing:**
  - Card field definitions
  - Available actions per card type
  - How cards map to intents

**Code Location:**
- [mobile/src/components/UICardList.js](mobile/src/components/UICardList.js)
- [spec/openapi.yaml](../../spec/openapi.yaml) - needs card type definitions

**Should Be Documented In:**
- Update: [spec/openapi.yaml](../../spec/openapi.yaml) - define card schemas
- New file: `docs/api-card-types.md` - reference for all card types

**PR Suggestion:**
```
Title: Docs: Add API response card types reference
- Create card type schema definitions in OpenAPI spec
- Document each card type with fields and examples
- List available actions per card type
- Show how cards are rendered on mobile
- Link from spec/openapi.yaml
```

---

---

## MEDIUM SEVERITY GAPS (16 items)

### 19. Intent Recognition Grammar Not Fully Documented
**Severity:** MEDIUM  
**Category:** Features - Command Processing  

Files exist (`spec/command_grammar.md`) but not linked from main docs or README. CODEBASE_INVENTORY lists 100+ intents but users don't know the complete intent vocabulary.

**Should Document:** Voice command examples for all major intents in [spec/command_grammar.md](spec/command_grammar.md), link from [README.md](../../README.md).

---

### 20. Policy Evaluation System Not Explained
**Severity:** MEDIUM  
**Category:** Features - Security  

Code has `policy.py` and `policy_config.py` for safe operation policies, but policy rules not documented. Users don't understand what operations are gated.

**Code Location:** [src/handsfree/policy.py](src/handsfree/policy.py), [src/handsfree/policy_config.py](src/handsfree/policy_config.py)

**Should Document:** Policy rules, how to configure repo-level policies, default safe operations in `docs/policy-evaluation.md`.

---

### 21. Rate Limiting Not Documented
**Severity:** MEDIUM  
**Category:** Configuration  

Code has `rate_limit.py` with Retry-After headers. Users don't know rate limits or how to handle them.

**Should Document:** Rate limits per endpoint, exceeding rate limit behavior, retry strategies in [CONFIGURATION.md](../CONFIGURATION.md).

---

### 22. Caching Strategy Not Documented
**Severity:** MEDIUM  
**Category:** Architecture  

Code uses Redis for caching but cache keys, TTLs, invalidation not documented.

**Code Location:** [src/handsfree/redis_client.py](src/handsfree/redis_client.py)

**Should Document:** Cache key patterns, TTL policy, cache invalidation triggers in [ARCHITECTURE.md](../ARCHITECTURE.md).

---

### 23. Intent Entity Extraction Not Documented
**Severity:** MEDIUM  
**Category:** Features - Command Processing  

Code extracts entities from user input (PR numbers, user names, etc.) but extraction rules not documented.

**Code Location:** [src/handsfree/commands/intent_parser.py](src/handsfree/commands/intent_parser.py)

**Should Document:** Entity types, extraction patterns, validation rules in `docs/command-processing.md`.

---

### 24. Session Context & State Management Not Explained
**Severity:** MEDIUM  
**Category:** Architecture  

Code has `session_context.py` with multi-provider state, but session concept not explained in docs.

**Should Document:** Session purpose, lifetime, state storage, provider coordination in [ARCHITECTURE.md](../ARCHITECTURE.md).

---

### 25. Observable Metrics Available Not Listed
**Severity:** MEDIUM  
**Category:** Observability  

Code has `/v1/metrics` endpoint and `metrics.py` module, but available metrics not documented.

**Should Document:** All metrics available (latency percentiles, intent counts, status counts, confirmation outcomes) in `docs/observability.md`.

---

### 26. Notification Subscription Types Not Documented
**Severity:** MEDIUM  
**Category:** Features - Notifications  

Code supports multiple notification platforms but what subscriptions look like not shown.

**Code Location:** [src/handsfree/db/notification_subscriptions.py](src/handsfree/db/notification_subscriptions.py)

**Should Document:** Subscription fields, platform types (APNS/FCM), user preferences in [CONFIGURATION.md](../CONFIGURATION.md).

---

### 27. Mobile App Hooks & State Management Not Documented
**Severity:** MEDIUM  
**Category:** Mobile Development  

Code has 6+ custom hooks (useGlassesRecorder, useAudioSource, usePeerChatDiagnostics, etc.) but not documented.

**Should Document:** Hook purpose, dependencies, examples in `mobile/HOOKS_REFERENCE.md`.

---

### 28. Idempotency Key Support Not Explained
**Severity:** MEDIUM  
**Category:** API Design  

Code has `idempotency_keys` table for request deduplication but feature not mentioned in docs.

**Should Document:** When idempotency is used, how to leverage in client requests in [ARCHITECTURE.md](ARCHITECTURE.md#api-architecture).

---

### 29. Follow-on Task Behavior Not Explained
**Severity:** MEDIUM  
**Category:** Features - Agent Tasks  

Response schema has `follow_on_task` field but current documentation doesn't explain what it means or how users interact with it.

**Code Location:** [src/handsfree/models.py](src/handsfree/models.py) - follow_on_task field

**Should Document:** When follow-on tasks are created, how users see/interact with them, examples in agent-delegation-workflow.md.

---

### 30. Result Aggregation & Filtering Not Documented
**Severity:** MEDIUM  
**Category:** Features - Agent Tasks  

Code has `results_views.py` for task result aggregation/filtering but behavior not documented.

**Should Document:** How results are aggregated, available filtering options, result sorting in `docs/agent-tasks.md`.

---

### 31. Audio/Image Fetching & Validation Not Covered
**Severity:** MEDIUM  
**Category:** Configuration  

Code has detailed audio/image fetching with size/timeout limits and host filtering. Not clearly documented.

**Should Document:** Size limits, fetch timeouts, host allow/deny lists, supported formats in [CONFIGURATION.md](../CONFIGURATION.md).

---

### 32. Request Tracing & Correlation IDs Not Documented
**Severity:** MEDIUM  
**Category:** Observability  

Code has correlation IDs for request tracing but not explained for operators/developers.

**Should Document:** Tracing concept, correlation ID usage, log analysis in `docs/observability.md`.

---

### 33. Docker & Kubernetes Deployment Not Covered
**Severity:** MEDIUM  
**Category:** Deployment  

Only basic Docker info in [ARCHITECTURE.md](../ARCHITECTURE.md). No K8s, volume management, env var setup in containers.

**Should Document:** Docker build/run, volume mounts for database, env var injection, multi-container setup in `docs/docker-deployment.md`.

---

### 34. Development vs Production Modes Not Clearly Distinguished
**Severity:** MEDIUM  
**Category:** Configuration  

Code and docs mention both but guidance on which settings differ, when to use which mode not clear.

**Should Document:** Setting table: dev vs production values for each env var in [CONFIGURATION.md](../CONFIGURATION.md).

---

---

## LOW SEVERITY GAPS (13 items)

### 35. Installation Lifecycle Hooks Not Documented
**Severity:** LOW - Optional feature  
**Category:** GitHub Integration  

Code has `installation_lifecycle.py` for GitHub App lifecycle but rarely used.

---

### 36. IPFS Provider Adapters Not Documented
**Severity:** LOW - Experimental  
**Category:** Experimental Features  

Code has `ipfs_*.py` adapters but IPFS integration is experimental.

---

### 37. Stub Providers Not Documented
**Severity:** LOW - Dev Only  
**Category:** Development  

Stub providers for TTS/STT/transport documented only implicitly (fixture mode).

---

### 38. Peer Chat Implementation Not Documented
**Severity:** LOW - Experimental  
**Category:** Experimental Features  

Peer-to-peer messaging system (`peer_chat.py`, `peer_chat_diagnostics`) experimental, few users.

---

### 39. OCR Module Not Documented
**Severity:** LOW - Experimental/Future  
**Category:** Experimental Features  

OCR provider abstraction exists but OCR not actually implemented yet.

---

### 40. Model Schemas Not Documented as Reference
**Severity:** LOW - For API consumers  
**Category:** API  

100+ Pydantic models in `models.py` not fully exposed as searchable schema reference.

---

### 41. Action Result Structures Not Documented
**Severity:** LOW - Implicit in responses  
**Category:** API  

PR merge/comment/request-review results embedded in responses but not formally documented.

---

### 42. Error Codes Not Comprehensively Listed
**Severity:** LOW - Error handling  
**Category:** API  

Code returns specific error intents/codes but comprehensive error code reference missing.

---

### 43. Logging Configuration Not Documented
**Severity:** LOW - Operations  
**Category:** Configuration  

Code has structured logging but log levels, formats, destinations not documented.

---

### 44. Health Check Endpoint Not Documented
**Severity:** LOW - Ops/monitoring  
**Category:** Observability  

Code has `/health` and `/v1/status` but differences and when to use each not clear.

---

### 45. Timezone & Locale Support Not Documented
**Severity:** LOW - Internationalization  
**Category:** Feature  

Mobile client sends timezone/locale but i18n support not documented.

---

### 46. User ID Format Requirements Not Documented
**Severity:** LOW - If not UUID  
**Category:** API Design  

Code expects UUID but format requirements not stated clearly in auth docs.

---

### 47. Async/Background Job Processing Not Documented
**Severity:** LOW - Implementation detail  
**Category:** Architecture  

Code mentions async processing for TTS, webhooks, but job queueing strategy not explained.

---

---

## SUMMARY TABLE: High-Severity Gaps with Files to Create/Update

| # | Gap | Create File | Update File | Impact |
|----|------|-------------|------------|--------|
| 1 | Database Schema | - | [ARCHITECTURE.md](../ARCHITECTURE.md) | Blocks data understanding |
| 2 | OpenAPI Completeness | Add to [spec/openapi.yaml](../../spec/openapi.yaml) | [ARCHITECTURE.md](../ARCHITECTURE.md) | Blocks API integration |
| 3 | Agent Delegation | `docs/agent-delegation-workflow.md` | [README.md](../../README.md) | Blocks agent feature use |
| 4 | Mobile Screens | `mobile/SCREENS_REFERENCE.md` | [mobile/README.md](mobile/README.md) | Blocks mobile development |
| 5 | Auth Integration | - | Multiple | Blocks auth setup |
| 6 | Advanced Config | `docs/configuration-reference.md` | [CONFIGURATION.md](../CONFIGURATION.md) | Blocks optimization |
| 7 | Webhook Processing | `docs/webhook-processing.md` | [ARCHITECTURE.md](../ARCHITECTURE.md) | Blocks webhook understanding |
| 8 | Profiles | `docs/profiles-guide.md` | [README.md](../../README.md) | Blocks profile use |
| 9 | Confirmation Flow | - | [ARCHITECTURE.md](../ARCHITECTURE.md) | Blocks UX understanding |
| 10 | Privacy Modes | `docs/privacy-modes-guide.md` | [README.md](../../README.md) | Blocks privacy feature use |
| 11 | Experimental Features | `docs/experimental-features-roadmap.md` | [README.md](../../README.md) | Blocks feature adoption |
| 12 | TTS/STT Providers | `docs/provider-systems.md` | [CONFIGURATION.md](../CONFIGURATION.md) | Blocks provider extension |
| 13 | Transport Layer | `docs/transport-architecture.md` | [ARCHITECTURE.md](../ARCHITECTURE.md) | Blocks P2P understanding |
| 14 | MCP Integration | `docs/mcp-integration.md` | [README.md](../../README.md), [ARCHITECTURE.md](../ARCHITECTURE.md) | Blocks MCP use |
| 15 | Secrets Management | `docs/secrets-management.md` | [CONFIGURATION.md](../CONFIGURATION.md) | Blocks secure deployment |
| 16 | Push Notifications | Expand `docs/push-notifications.md` | [mobile/README.md](mobile/README.md) | Blocks notification setup |
| 17 | GitHub Integration | `docs/github-integration-guide.md` | [ARCHITECTURE.md](../ARCHITECTURE.md) | Blocks GitHub feature use |
| 18 | Card Types | `docs/api-card-types.md` | [spec/openapi.yaml](../../spec/openapi.yaml) | Blocks UI integration |

---

## RECOMMENDED PR ORDER (High Severity)

### Priority Tier 1 (Core Enablers)
1. **Database Schema Documentation** - Blocks understanding of everything
2. **OpenAPI Completeness** - Blocks API integration
3. **Authentication Integration** - Blocks security setup

### Priority Tier 2 (Feature Understanding)
4. **Agent Delegation Workflow** - Complex feature needs explanation
5. **Profiles Guide** - Quick to document, high impact
6. **Privacy Modes** - Security feature needs clarity

### Priority Tier 3 (Advanced Features)
7. **Configuration Reference** - Unblocks power users
8. **Provider Systems** - Needed for extensibility
9. **MCP Integration** - Needed for advanced users

### Priority Tier 4 (Completeness)
10. **Webhook Processing**
11. **Mobile Screens Reference**
12. **Secrets Management**
13. **GitHub Integration Guide**
14. **Card Types Reference**

---

## ACTIONABLE NEXT STEPS

### Immediate (This Week)
- [ ] Create database schema ERD and documentation  
- [ ] Complete OpenAPI spec with all endpoints
- [ ] Create authentication setup guide with links

### Short Term (This Sprint)
- [ ] Create agent delegation workflow guide
- [ ] Create profiles guide
- [ ] Create privacy modes documentation
- [ ] Expand mobile screens reference

### Medium Term (Next Sprint)
- [ ] Create configuration reference
- [ ] Create provider systems documentation
- [ ] Create MCP integration guide
- [ ] Create secrets management guide

### Long Term (Nice to Have)
- [ ] Complete all Medium-severity gaps
- [ ] Complete all Low-severity gaps
- [ ] Create example projects and tutorials

---

**Last Updated:** March 9, 2026  
**Analysis Type:** Codebase Inventory vs Documentation Comparison  
**Total Gaps:** 47 (18 High, 16 Medium, 13 Low)
