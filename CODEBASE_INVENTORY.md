# HandsFree Dev Companion - Codebase Inventory

**Last Updated:** March 9, 2026 | **Status:** Complete analysis of implemented features

---

## 📋 Executive Summary

This document provides a comprehensive inventory of all implemented features, modules, providers, and integrations in the HandsFree Dev Companion codebase. Organized by subsystem with core vs. experimental features clearly marked.

---

## 🏗️ Backend Architecture (`src/handsfree/`)

### Core Modules

| Module | Components | Status |
|--------|-----------|--------|
| **api.py** | FastAPI server, route handlers, request/response models | ✅ Core |
| **server.py** | Server initialization, middleware | ✅ Core |
| **auth.py** | Authentication modes (dev, jwt, api_key) | ✅ Core |
| **models.py** | Pydantic models for all API types (~100+ models) | ✅ Core |
| **policy.py** | Policy evaluation engine for safe operations | ✅ Core |
| **policy_config.py** | Policy configuration management | ✅ Core |
| **logging_utils.py** | Structured logging with request tracing | ✅ Core |
| **rate_limit.py** | Rate limiting with Retry-After headers | ✅ Core |
| **metrics.py** | Observability & metrics collection | ✅ Core |
| **redis_client.py** | Redis connection factory & cache management | ✅ Core |
| **sessions.py** | Session management & context | ✅ Core |

### Commands Module (`commands/`)

| Component | Purpose | Status |
|-----------|---------|--------|
| **intent_parser.py** | Pattern-based intent recognition (100+ intents) | ✅ Core |
| **router.py** | Intent → handler routing, response composition | ✅ Core |
| **pending_actions.py** | In-memory + Redis-backed confirmation flow | ✅ Core |
| **profiles.py** | Workout/Kitchen/Commute/Default profiles | ✅ Core |
| **session_context.py** | Multi-provider session state management | ✅ Core |

### Agents Module (`agents/`)

| Component | Purpose | Status |
|-----------|---------|--------|
| **service.py** | Agent lifecycle management | ✅ Core |
| **delegation.py** | Agent delegation framework | ✅ Core |
| **runner.py** | Agent task execution | ✅ Core |
| **results_views.py** | Result aggregation and filtering | ✅ Core |

### Actions Module (`actions/`)

| Component | Purpose | Status |
|-----------|---------|--------|
| **service.py** | Action execution (merge, comment, request-review, rerun-checks) | ✅ Core |

### AI Module (`ai/`)

| Component | Purpose | Status |
|-----------|---------|--------|
| **capabilities.py** | AI capability descriptors | ✅ Core |
| **policy.py** | AI backend policy evaluation | ✅ Core |
| **models.py** | AI request/response schemas | ✅ Core |
| **history.py** | AI execution history tracking | ✅ Core |
| **observability.py** | AI performance metrics | ✅ Core |
| **serialization.py** | AI result serialization | ✅ Core |

### GitHub Integration (`github/`)

| Component | Purpose | Status |
|-----------|---------|--------|
| **client.py** | GitHub REST API client wrapper | ✅ Core |
| **provider.py** | GitHub provider for agent delegation | ✅ Core |
| **auth.py** | GitHub OAuth & token management | ✅ Core |
| **execution.py** | PR/issue operations execution | ✅ Core |

### Database Layer (`db/`)

| Module | Purpose | Status |
|--------|---------|--------|
| **connection.py** | DuckDB connection management | ✅ Core |
| **migrations.py** | Schema migration system | ✅ Core |
| **commands.py** | Command history storage | ✅ Core |
| **action_logs.py** | Action execution logging | ✅ Core |
| **agent_tasks.py** | Agent task lifecycle tracking | ✅ Core |
| **github_connections.py** | OAuth connection storage | ✅ Core |
| **notifications.py** | Real-time notification storage | ✅ Core |
| **notification_subscriptions.py** | User notification preferences | ✅ Core |
| **notification_delivery_tracking.py** | Push delivery logging (APNS/FCM) | ✅ Core |
| **repo_subscriptions.py** | Repository subscription tracking | ✅ Core |
| **repo_policies.py** | Per-repo action policies | ✅ Core |
| **pending_actions.py** | Confirmation token & state | ✅ Core |
| **webhook_events.py** | Webhook event deduplication & processing | ✅ Core |
| **api_keys.py** | API key credential storage | ✅ Core |
| **oauth_states.py** | OAuth state validation | ✅ Core |
| **idempotency_keys.py** | Request idempotency tracking | ✅ Core |
| **ai_history_index.py** | AI execution history indexing | ✅ Core |
| **ai_backend_policy_snapshots.py** | Policy snapshot capturing | ✅ Core |
| **peer_chat.py** | P2P message persistence | ✅ Experimental |
| **transport_session_cursors.py** | Transport session state | ✅ Experimental |

### Handlers Module (`handlers/`)

| Handler | Function | Status |
|---------|----------|--------|
| **inbox.py** | Aggregate inbox items (PRs, mentions, checks) | ✅ Core |
| **pr_summary.py** | PR summarization from intent data | ✅ Core |

### TTS/STT Providers (`tts/`, `stt/`)

| Provider | Service | Status |
|----------|---------|--------|
| **openai_provider.py** (TTS) | OpenAI TTS API integration | ✅ Core |
| **openai_provider.py** (STT) | OpenAI Whisper integration | ✅ Core |
| **stub_provider.py** | No-op stubs for CI/testing | ✅ Core |

### Secrets Management (`secrets/`)

| Manager | Storage Backend | Status |
|---------|-----------------|--------|
| **env_secrets.py** | Environment variables | ✅ Core |
| **aws_secrets.py** | AWS Secrets Manager | ✅ Optional |
| **gcp_secrets.py** | GCP Secret Manager | ✅ Optional |
| **vault_secrets.py** | HashiCorp Vault | ✅ Optional |
| **factory.py** | Auto-detection & initialization | ✅ Core |

### MCP Integration (`mcp/`)

| Component | Purpose | Status |
|-----------|---------|--------|
| **client.py** | MCP client for tool calls | ✅ Experimental |
| **config.py** | MCP server configuration | ✅ Experimental |
| **catalog.py** | Capability & provider registry | ✅ Experimental |
| **capabilities.py** | MCP capability definitions | ✅ Experimental |
| **models.py** | MCP request/response schemas | ✅ Experimental |

### Transport Layer (`transport/`)

| Component | Purpose | Status |
|-----------|---------|--------|
| **libp2p_bluetooth.py** | Bluetooth P2P transport scaffold | ✅ Experimental |
| **stub_provider.py** | No-op transport for testing | ✅ Core |

### OCR Module (`ocr/`)

| Component | Purpose | Status |
|-----------|---------|--------|
| **provider.py** | OCR capability abstraction | ✅ Experimental |

### Utility Modules

| Module | Purpose | Status |
|--------|---------|--------|
| **audio_fetch.py** | Fetch audio from URIs with validation | ✅ Core |
| **image_fetch.py** | Fetch images from URIs with validation | ✅ Core |
| **webhooks.py** | GitHub webhook signature verification | ✅ Core |
| **peer_chat.py** | P2P message encryption/routing | ✅ Experimental |
| **installation_lifecycle.py** | GitHub App lifecycle hooks | ✅ Optional |
| **ipfs_*.py** | IPFS provider adapters | ✅ Experimental |

---

## 📱 Mobile App Architecture (`mobile/`)

### Screens

| Screen | Features | Status |
|--------|----------|--------|
| **CommandScreen.js** | Voice/text input, intent parsing | ✅ Core |
| **ConfirmationScreen.js** | Action confirmation UI | ✅ Core |
| **NotificationsScreen.js** | Notification feed, actions | ✅ Core |
| **ResultsScreen.js** | Agent task results, filtering | ✅ Core |
| **ActiveTasksScreen.js** | Running task monitoring | ✅ Core |
| **TaskDetailScreen.js** | Task details, control buttons | ✅ Core |
| **StatusScreen.js** | Backend/dependency health | ✅ Core |
| **SettingsScreen.js** | Profile, privacy, profile selection | ✅ Core |
| **TTSScreen.js** | Text-to-speech player | ✅ Core |
| **GlassesDiagnosticsScreen.js** | Meta Glasses audio debugging | ✅ Experimental |
| **PeerChatDiagnosticsScreen.js** | P2P chat debugging | ✅ Experimental |

### Components

| Component | Purpose | Status |
|-----------|---------|--------|
| **UICardList.js** | Render API response cards | ✅ Core |
| **ActionPromptModal.js** | Inline action execution | ✅ Core |
| **ProfileSelector.js** | Workout/Kitchen/Commute selection | ✅ Core |
| **AudioSourceSelector.js** | Microphone selection | ✅ Core |
| **FollowOnTaskCard.js** | Follow-on task visualization | ✅ Core |
| **PeerChatDiagnosticsPanel.js** | P2P connection status | ✅ Experimental |
| **PeerChatOutboxPanel.js** | Message queue visualization | ✅ Experimental |
| **RefreshStatusCard.js** | Retry/health refresh | ✅ Core |

### Hooks

| Hook | Purpose | Status |
|------|---------|--------|
| **useGlassesRecorder.js** | Meta Glasses audio capture | ✅ Experimental |
| **useGlassesPlayer.js** | Meta Glasses audio playback | ✅ Experimental |
| **useMetaWearablesDat.js** | Meta wearables integration | ✅ Experimental |
| **useAudioSource.js** | Audio source management | ✅ Core |
| **usePeerChatDiagnostics.js** | P2P connection debugging | ✅ Experimental |
| **useNowTicker.js** | Real-time clock updates | ✅ Core |

### Native Modules

| Module | Target | Status |
|--------|--------|--------|
| **expo-glasses-audio** | Meta Glasses audio I/O (iOS) | ✅ Experimental |
| **expo-meta-wearables-dat** | Wearables data (iOS/Android) | ✅ Experimental |
| **glasses-audio/** | Native implementation | ✅ Experimental |
| **glasses-audio-player/** | Player component | ✅ Experimental |

### API Client

| Feature | Status |
|---------|--------|
| Command execution | ✅ Core |
| Action responses | ✅ Core |
| Notification subscriptions | ✅ Core |
| TTS synthesis | ✅ Core |
| Follow-on task visualization | ✅ Core |
| Error normalization | ✅ Core |

### Push Notifications (Expo)

| Feature | Status |
|---------|--------|
| Token registration | ✅ Core |
| Push delivery | ✅ Core |
| Notification listening | ✅ Core |
| Deep linking | ✅ Core |

---

## 🔌 API Endpoints

### Command Processing

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/command` | POST | Process voice/text/image commands | ✅ Core |
| `/v1/commands/action` | POST | Execute card actions | ✅ Core |
| `/v1/commands/confirm` | POST | Submit confirmation tokens | ✅ Core |

### Inbox & Notifications

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/inbox` | GET | Aggregate inbox (PRs, mentions, checks) | ✅ Core |
| `/v1/notifications` | GET | Fetch notification feed | ✅ Core |
| `/v1/notifications/subscriptions` | POST/GET/DELETE | Manage subscriptions | ✅ Core |

### Agent Tasks

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/agents/tasks` | GET | List agent tasks | ✅ Experimental |
| `/v1/agents/tasks/{task_id}` | GET | Get task details | ✅ Experimental |
| `/v1/agents/tasks/{task_id}/results` | GET | Get task results | ✅ Experimental |
| `/v1/agents/tasks/{task_id}/pause` | POST | Pause task | ✅ Experimental |
| `/v1/agents/tasks/{task_id}/resume` | POST | Resume paused task | ✅ Experimental |
| `/v1/agents/tasks/{task_id}/cancel` | POST | Cancel task | ✅ Experimental |
| `/v1/agents/tasks/{task_id}/start` | POST | Start task | ✅ Experimental |
| `/v1/agents/tasks/{task_id}/complete` | POST | Mark complete | ✅ Experimental |
| `/v1/agents/tasks/{task_id}/fail` | POST | Mark failed | ✅ Experimental |
| `/v1/agents/tasks/{task_id}/media` | POST | Upload task media | ✅ Experimental |

### GitHub Integration

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/github/connections` | POST/GET | Create/list connections | ✅ Core |
| `/v1/github/connections/{connection_id}` | GET/DELETE | Get/remove connection | ✅ Core |
| `/v1/github/oauth/start` | GET | Initiate OAuth flow | ✅ Core |
| `/v1/github/oauth/callback` | GET | OAuth callback handler | ✅ Core |
| `/v1/repos/subscriptions` | POST/GET/DELETE | Manage repo subscriptions | ✅ Core |

### GitHub Actions

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/actions/request-review` | POST | Request PR reviewers | ✅ Core |
| `/v1/actions/rerun-checks` | POST | Rerun failed checks | ✅ Core |
| `/v1/actions/comment` | POST | Add PR comment | ✅ Core |
| `/v1/actions/merge` | POST | Merge PR | ✅ Core |

### AI/ML Capabilities

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/ai/execute` | POST | Execute generic AI capability | ✅ Core |
| `/v1/ai/copilot/explain-pr` | POST | Copilot PR analysis | ✅ Core |
| `/v1/ai/copilot/summarize-diff` | POST | Copilot diff summarization | ✅ Core |
| `/v1/ai/copilot/explain-failure` | POST | Copilot failure analysis | ✅ Core |
| `/v1/ai/rag-summary` | POST | RAG-based PR summary | ✅ Core |
| `/v1/ai/accelerated-rag-summary` | POST | Accelerated RAG summary | ✅ Experimental |
| `/v1/ai/failure-rag-explain` | POST | RAG-based failure explain | ✅ Core |
| `/v1/ai/accelerated-failure-explain` | POST | Accelerated failure explain | ✅ Experimental |
| `/v1/ai/find-similar-failures` | POST | Find similar CI failures | ✅ Core |
| `/v1/ai/read-stored-output` | POST | Read IPFS-stored results | ✅ Core |
| `/v1/ai/accelerate-generate-and-store` | POST | Generate + store to IPFS | ✅ Experimental |

### Webhooks

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/webhooks/github` | POST | GitHub webhook handler | ✅ Core |
| `/v1/webhooks/retry/{event_id}` | POST | Retry webhook processing | ✅ Core |

### TTS

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/tts` | POST | Synthesize speech | ✅ Core |

### System

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/health` | GET | Health check (liveness) | ✅ Core |
| `/v1/status` | GET | Detailed service status | ✅ Core |
| `/v1/metrics` | GET | Prometheus metrics | ✅ Core |

### Admin

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/admin/api-keys` | POST/GET/DELETE | API key management | ✅ Core |
| `/v1/admin/ai/backend-policy` | GET | View AI policy | ✅ Core |
| `/v1/admin/ai/backend-policy/history` | GET | Policy history | ✅ Core |
| `/v1/admin/ai/backend-policy/snapshots` | GET | Policy snapshots | ✅ Core |

### Development/Testing

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/v1/dev/audio` | POST | Upload test audio | ✅ Core |
| `/v1/dev/media` | POST | Upload test media | ✅ Core |
| `/v1/dev/peer-envelope` | POST | Test P2P envelope | ✅ Experimental |
| `/v1/dev/peer-chat` | GET/POST | P2P chat debugging | ✅ Experimental |
| `/v1/dev/peer-chat/send` | POST | Send P2P message | ✅ Experimental |
| `/v1/dev/peer-chat/outbox/{peer_id}` | GET | View message queue | ✅ Experimental |
| `/v1/dev/transport-sessions` | GET/DELETE | Transport session mgmt | ✅ Experimental |
| `/simulator` | GET | Web simulator UI | ✅ Testing |

---

## 🗄️ Database Schema

### Core Tables

| Table | Purpose | Status |
|-------|---------|--------|
| `commands` | Command execution history | ✅ |
| `action_logs` | Action invocation audit trail | ✅ |
| `pending_actions` | Confirmation tokens & expiry | ✅ |
| `idempotency_keys` | Request deduplication | ✅ |
| `api_keys` | Admin/user API credentials | ✅ |
| `oauth_states` | OAuth flow state validation | ✅ |

### GitHub & Integration

| Table | Purpose | Status |
|-------|---------|--------|
| `github_connections` | OAuth connection tokens | ✅ |
| `repo_subscriptions` | User-subscribed repositories | ✅ |
| `repo_policies` | Per-repo action policies | ✅ |
| `webhook_events` | GitHub webhook event log | ✅ |

### Notifications

| Table | Purpose | Status |
|-------|---------|--------|
| `notifications` | Application notifications | ✅ |
| `notification_subscriptions` | User preferences (APNS/FCM) | ✅ |
| `notification_delivery_tracking` | Push delivery status | ✅ |

### Agents & Tasks

| Table | Purpose | Status |
|-------|---------|--------|
| `agent_tasks` | MCP agent task lifecycle | ✅ |
| `ai_history_index` | AI execution records | ✅ |
| `ai_backend_policy_snapshots` | Policy version history | ✅ |

### Experimental/P2P

| Table | Purpose | Status |
|-------|---------|--------|
| `peer_chat_messages` | P2P message persistence | ✅ |
| `transport_session_cursors` | Transport state cursors | ✅ |

---

## 🎯 Implemented Features

### Core Intents (100+ Patterns)

#### System Commands
- `system.repeat` - Repeat last response
- `system.next` - Show next result/page
- `system.cancel` - Cancel operation
- `system.confirm` - Confirm action
- `system.set_profile` - Switch profile (Workout/Kitchen/Commute)

#### Debug & Observability
- `debug.transcript` - Explain what was heard

#### Inbox & Alerts
- `inbox.list` - Show PRs needing attention, failing checks, mentions

#### PR Operations
- `pr.summarize` - Summarize PR (#N or "last")
- `pr.merge` - Merge PR (confirmation required)
- `pr.comment` - Add PR comment (confirmation required)
- `pr.request_review` - Request reviewer (confirmation required)

#### Check Operations
- `checks.rerun` - Rerun failed checks (confirmation required)

#### Agent Operations
- `agent.delegate` - Delegate task to external agent
- `agent.delegate.confirmed` - Confirmed delegation
- `agent.result_open` - Open agent result
- `agent.result_details` - Show result details
- `agent.result_related` - Show similar results
- `agent.result_actions` - List available actions
- `agent.result_read` - Read CID from IPFS
- `agent.result_share` - Share result CID
- `agent.result_pin` - Pin result locally/remotely
- `agent.result_unpin` - Remove local/remote pin
- `agent.result_rerun` - Rerun workflow
- `agent.result_rerun_fetch` - Rerun URL fetch
- `agent.result_rerun_dataset` - Rerun dataset search
- `agent.result_save_ipfs` - Persist result to IPFS

#### AI/ML Operations
- `ai.read_cid` - Load stored analysis from IPFS CID
- `ai.rag_summary` - PR summary with RAG retrieval
- `ai.accelerated_rag_summary` - Fast RAG summary
- `ai.failure_rag_explain` - Failure analysis with RAG
- `ai.accelerated_failure_explain` - Fast failure analysis
- `ai.find_similar_failures` - Find similar CI failures
- `ai.accelerate_generate_and_store` - Generate & persist to IPFS

#### Peer Chat (Experimental)
- `peer.message_send` - Send P2P message
- `peer.conversation_list` - List conversations

---

## 🔧 Configuration & Environment

### Database
- `DUCKDB_PATH` - DuckDB file location (default: `data/handsfree.db`)
- Schema auto-migration via `migrations/` folder
- 15 migration files implemented

### Authentication
- `HANDSFREE_AUTH_MODE` - `dev`, `jwt`, or `api_key`
- Support for FastAPI Bearer tokens
- API key credential storage

### Redis (Optional)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_ENABLED`
- Used for: pending actions, caching, session context
- Graceful fallback to in-memory with warning

### External Services
- `GITHUB_TOKEN` - GitHub API access
- `OPENAI_API_KEY` - TTS/STT/embeddings
- `EXPO_ACCESS_TOKEN` - Push notifications
- AWS Secrets, GCP Secret Manager, Vault support

### Secrets Management
- Auto-detection of available backend
- Environment variable override
- Per-secret encryption support

### Audio/Image Fetching
- `AUDIO_MAX_SIZE_BYTES` - Upload limit (default: 10MB)
- `AUDIO_FETCH_TIMEOUT_SECONDS` - Network timeout
- `AUDIO_ALLOWED_HOSTS`, `AUDIO_DENIED_HOSTS` - Host filtering
- Similar for images
- `HANDSFREE_ALLOW_LOCAL_IMAGE_URIS` - Dev mode local file access

### Agent Delegation
- `HANDSFREE_AGENT_DEFAULT_PROVIDER` - Default provider
- `HANDSFREE_AGENT_DISPATCH_REPO` - GitHub dispatch repo
- Auto-selection: explicit > env var > github_issue_dispatch > copilot

### AI/ML Configuration
- `HANDSFREE_ENABLE_AI_ENHANCED_COMMANDS` - Feature flag
- Policy-based AI capability control
- Cost tracking & usage limits

### Platform Configuration
- `HANDSFREE_TRANSPORT_PROVIDER` - libp2p_bluetooth or stub
- `HANDSFREE_OCR_PROVIDER` - OCR service provider
- MCP server configuration

---

## 📊 Provider Systems

### Transport Providers
| Provider | Type | Status |
|----------|------|--------|
| `libp2p_bluetooth` | P2P mesh via Bluetooth | ✅ Experimental |
| `stub_provider` | No-op (testing) | ✅ Core |

### Agent Providers
| Provider | Dispatch Mechanism | Status |
|----------|-------------------|--------|
| `github_issue_dispatch` | Create dispatch issues → GH Actions | ✅ Core |
| `copilot` | Direct Copilot CLI integration | ✅ Optional |
| `copilot_cli_provider` | Enhanced CLI-based delegation | ✅ Experimental |

### MCP Providers (Experimental)
| Provider | Capabilities | Status |
|----------|--------------|--------|
| `ipfs_accelerate_mcp` | Workflow acceleration, fetch | ✅ Experimental |
| `ipfs_datasets_mcp` | Dataset discovery | ✅ Experimental |
| `ipfs_kit_mcp` | IPFS operations | ✅ Experimental |

### TTS Providers
| Provider | Service | Status |
|----------|---------|--------|
| `openai_provider` | OpenAI TTS API | ✅ Core |
| `stub_provider` | No-op (testing) | ✅ Core |

### STT Providers
| Provider | Service | Status |
|----------|---------|--------|
| `openai_provider` | OpenAI Whisper API | ✅ Core |
| `stub_provider` | No-op (testing) | ✅ Core |

### Storage Providers
| Provider | Type | Status |
|----------|------|--------|
| DuckDB | Embedded relational DB | ✅ Core |
| Redis | Session/action caching | ✅ Optional |
| S3 (IPFS) | Long-term result storage | ✅ Optional |

### Secret Managers
| Manager | Backend | Status |
|---------|---------|--------|
| `env_secrets` | Environment variables | ✅ Core |
| `aws_secrets` | AWS Secrets Manager | ✅ Optional |
| `gcp_secrets` | GCP Secret Manager | ✅ Optional |
| `vault_secrets` | HashiCorp Vault | ✅ Optional |

---

## 📦 Native Features & Integrations

### OAuth & Authentication
- ✅ GitHub OAuth 2.0 flow (3-legged)
- ✅ API key credential storage & rotation
- ✅ JWT Bearer token support
- ✅ Development/test fixture mode

### Real-Time Communications
- ✅ Push notifications (APNS/FCM via Expo)
- ✅ Webhook signature verification
- ✅ Event deduplication
- ✅ Retry logic with backoff

### GitHub Operations
- ✅ PR listing, summary, merge
- ✅ Issue comments, status
- ✅ Check runs reruns
- ✅ Code review requests
- ✅ Rate limit handling (429, 403)
- ✅ Webhook event handling

### AI/ML Integration
- ✅ OpenAI TTS synthesis
- ✅ OpenAI Whisper STT
- ✅ RAG-based summarization
- ✅ Policy-driven capability control
- ✅ Failure similarity analysis
- ✅ IPFS result persistence

### Data Persistence
- ✅ Command history audit trail
- ✅ Action log tracking
- ✅ Notification delivery status
- ✅ AI history indexing
- ✅ Policy snapshots
- ✅ Idempotency keys

### Privacy & Security
- ✅ Privacy mode (STRICT/BALANCED/DEBUG)
- ✅ Confirmation-required operations
- ✅ Policy-driven access control
- ✅ Secrets encryption
- ✅ Rate limiting

### Media Processing
- ✅ Audio URI fetching with size/timeout limits
- ✅ Image URI fetching with validation
- ✅ HTTPS pre-signed URL support
- ✅ Host-based access control
- ✅ Local file access (dev mode)

### Mobile Platform Integration
- ✅ Deep linking support
- ✅ Bluetooth audio I/O (experimental)
- ✅ Meta wearables integration (experimental)
- ✅ Notification listener
- ✅ Token registration

---

## 🧪 Test Coverage

### Test Files (140+)

#### Core Features
- `test_smoke.py` - Integration smoke tests
- `test_api_contract.py` - API contract validation
- `test_status_endpoint.py` - Health checks
- `test_metrics.py` - Metrics collection
- `test_commands.py` - Command routing
- `test_agent_commands.py` - Agent intent handling

#### Commands & Intents
- `test_agent_intents.py` - Agent intent parsing
- `test_agent_provider_selection.py` - Provider selection logic
- `test_checks_rerun_intent.py` - Rerun checks intent
- `test_pr_comment_intent.py` - PR comment intent
- `test_request_review_integration.py` - Request review flow

#### Agent System
- `test_agent_tasks.py` - Task lifecycle (create, state transitions, control)
- `test_agent_runner.py` - Task execution
- `test_agent_service.py` - Agent service
- `test_agent_delegation_integration.py` - End-to-end delegation
- `test_agent_workflow.py` - Workflow coordination
- `test_agent_state_machine.py` - State machine validation

#### AI System
- `test_ai_capabilities.py` - Capability descriptors
- `test_ai_policy.py` - Policy evaluation
- `test_ai_backend_policy_snapshots.py` - Snapshot storage
- `test_ai_execute_models.py` - Execution models
- `test_ai_history.py` - History tracking
- `test_ai_history_index.py` - History indexing
- `test_ai_serialization.py` - Result serialization
- `test_ai_observability.py` - Metrics

#### GitHub Integration
- `test_github_provider.py` - GitHub provider
- `test_github_client.py` - GitHub API client
- `test_github_auth.py` - Auth flows
- `test_github_oauth.py` - OAuth 
- `test_github_execution.py` - PR/issue operations
- `test_github_rate_limit.py` - Rate limit handling
- `test_github_rate_limit_handling.py` - Retry logic
- `test_github_connection_api.py` - Connection endpoints
- `test_live_github_provider.py` - Integration tests
- `test_live_github_api.py` - Live API tests

#### Actions & Confirmation
- `test_action_service.py` - Action execution
- `test_action_logs.py` - Action logging
- `test_pending_actions.py` - Confirmation flow
- `test_merge_action.py` - PR merge
- `test_request_review_live_mode.py` - Live review requests
- `test_rerun_checks_live_mode.py` - Live check reruns

#### API & Protocol
- `test_api_keys.py` - API credential management
- `test_api_rate_limiting.py` - API rate limiting
- `test_api_idempotency.py` - Request idempotency
- `test_auth.py` - Authentication modes
- `test_auth_integration.py` - Auth integration

#### Notifications & Subscriptions
- `test_notifications.py` - Notification system
- `test_notifications_api.py` - Notification endpoints
- `test_notification_subscriptions.py` - Subscription management
- `test_notification_delivery.py` - Delivery tracking
- `test_notification_throttling_dedupe.py` - Deduplication

#### GitHub Events
- `test_webhook_events.py` - Webhook processing
- `test_webhooks.py` - Webhook handlers
- `test_webhook_user_mapping.py` - User mapping

#### Repositories
- `test_repo_subscriptions_api.py` - Subscription endpoints
- `test_pr_correlation.py` - PR correlation

#### Privacy & Security
- `test_privacy_mode_integration.py` - Privacy mode
- `test_profile_privacy_mode.py` - Profile-based privacy
- `test_router_privacy_mode.py` - Router privacy
- `test_security_observability.py` - Security metrics
- `test_abuse_prevention.py` - Abuse detection

#### Sessions & State
- `test_sessions.py` - Session management
- `test_session_context.py` - Context management
- `test_session_context_e2e.py` - E2E context
- `test_redis_session_context.py` - Redis session storage

#### Database & Persistence
- `test_persistent_db.py` - DuckDB persistence
- `test_migrations.py` - Schema migrations
- `test_redis_integration.py` - Redis integration
- `test_redis_pending_actions.py` - Redis action storage

#### Input Processing
- `test_audio_input.py` - Audio input handling
- `test_image_input.py` - Image input handling
- `test_dev_audio_upload.py` - Dev audio endpoint
- `test_dev_media_upload.py` - Dev media endpoint

#### TTS/STT
- `test_tts.py` - TTS endpoint
- `test_tts_factory.py` - TTS provider factory
- `test_tts_provider.py` - Provider abstraction
- `test_stt_providers.py` - STT provider abstraction

#### Transport & P2P
- `test_transport_providers.py` - Transport abstraction
- `test_dev_peer_envelope.py` - P2P envelope format
- `test_dev_peer_chat_send.py` - Message sending
- `test_dev_peer_chat_history.py` - Chat history
- `test_peer_chat_persistence.py` - Message persistence

#### MCP Integration
- `test_mcp_config.py` - MCP configuration
- `test_mcp_catalog.py` - MCP capability catalog
- `test_mcp_result_envelope.py` - MCP result format
- `test_mcp_ipfs_provider.py` - IPFS MCP provider

#### IPFS Integration
- `test_ipfs_accelerate_adapters.py` - IPFS Accelerate
- `test_ipfs_datasets_routers.py` - IPFS Datasets
- `test_ipfs_kit_adapters.py` - IPFS Kit

#### CLI & Utilities
- `test_cli_adapters.py` - CLI adapter testing
- `test_copilot_cli_provider.py` - Copilot CLI provider
- `test_debug_command.py` - Debug commands

#### Advanced Features
- `test_pr_summary.py` - PR summarization
- `test_policy.py` - Policy engine
- `test_policy_config.py` - Policy configuration
- `test_user_identity.py` - User ID handling
- `test_user_token_provider.py` - Token provider

#### Platform-Specific
- `test_apns_fcm_platforms.py` - Push platform selection
- `test_push_providers_real_mode.py` - Real push delivery

---

## 🔄 Data Flows

### Command → Execution Flow
```
POST /v1/command
├─ Parse intent (router → intent_parser)
├─ Evaluate policy (policy engine)
├─ Route to handler (router)
├─ Execute action/fetch data
├─ Log action (action_logs)
└─ Return response (cards, pending action, or follow-on task)
```

### Confirmation Flow
```
Command → needs_confirmation status
├─ Generate token (pending_actions)
├─ Return token with expiry
└─ POST /v1/commands/confirm {token}
```

### Agent Delegation Flow
```
agent.delegate intent
├─ Create agent task (agent_tasks)
├─ Select provider (github_issue_dispatch, copilot, etc.)
├─ Poll/webhook for completion
├─ Store task result
└─ Emit notification → mobile app
```

### GitHub Webhook Flow
```
POST /v1/webhooks/github
├─ Verify signature (webhooks.py)
├─ Normalize event type
├─ Deduplicate (webhook_events table)
├─ Process event (handlers)
├─ Emit notifications
└─ Return 202 Accepted
```

### Notification Flow
```
Notification created
├─ Store in DB (notifications table)
├─ Resolve subscriptions (notification_subscriptions)
├─ Send push (APNS/FCM via Expo)
├─ Track delivery (notification_delivery_tracking)
└─ Notify mobile app
```

---

## 📚 External Integrations

### Repository Integrations
| Project | File | Purpose | Status |
|---------|------|---------|--------|
| **IPFS Accelerate** | `external/ipfs_accelerate/` | Workflow acceleration, data fetching | ✅ Integrated |
| **IPFS Datasets** | `external/ipfs_datasets/` | Dataset discovery & management | ✅ Integrated |
| **IPFS Kit** | `external/ipfs_kit/` | IPFS operations & CLI | ✅ Integrated |
| **Meta Wearables DAT (iOS)** | `external/meta-wearables-dat-ios/` | Ray-Ban glasses integration | ✅ Integrated |
| **Meta Wearables DAT (Android)** | `external/meta-wearables-dat-android/` | Wearables on Android | ✅ Integrated |

### Third-Party Services
| Service | Use Case | Status |
|---------|----------|--------|
| **GitHub API** | PR/issue ops, webhooks, OAuth | ✅ Core |
| **OpenAI** | TTS (text-to-speech), STT (Whisper) | ✅ Core |
| **Expo** | Push notifications (APNs/FCM gateway) | ✅ Core |
| **Vault** | Secrets management | ✅ Optional |
| **AWS Secrets Manager** | Secrets management | ✅ Optional |
| **GCP Secret Manager** | Secrets management | ✅ Optional |

---

## 🚀 Deployment & DevOps

### Docker Support
- ✅ `Dockerfile` - Backend containerization
- ✅ `docker-compose.yml` - Full stack (backend + DuckDB + Redis)
- ✅ `docker-compose.agent-runner.yml` - Agent runner deployment
- ✅ Agent runner container in `agent-runner/`

### CI/CD
- ✅ Pytest test framework
- ✅ Conftest fixtures for integration tests
- ✅ GitHub Actions workflow hooks
- ✅ Pre-signed URL support for deployment

### Monitoring & Observability
- ✅ Structured logging with request ID tracing
- ✅ Prometheus `/v1/metrics` endpoint
- ✅ Policy snapshot tracking
- ✅ AI history indexing
- ✅ Security anomaly detection
- ✅ Rate limit tracking

### Documentation
- ✅ Architecture guide (`ARCHITECTURE.md`)
- ✅ Getting started guide (`GETTING_STARTED.md`)
- ✅ Configuration guide (`CONFIGURATION.md`)
- ✅ Contributing guide (`CONTRIBUTING.md`)
- ✅ Security documentation (`SECURITY.md`)
- ✅ Privacy documentation (`PRIVACY_MODES_IMPLEMENTATION.md`)
- ✅ Mobile documentation (`mobile/README.md`)
- ✅ Multiple runbooks for iOS/Android testing
- ✅ Implementation summaries for recent PRs

---

## 📋 Summary Table

| Category | Core Features | Experimental | Optional |
|----------|---------------|--------------|----------|
| **Backend Modules** | 20+ | 8+ | 4+ |
| **API Endpoints** | 40+ | 15+ | 5+ |
| **Commands/Intents** | 50+ | 15+ | 10+ |
| **Database Tables** | 16 | 2 | - |
| **Providers** | 6 | 5 | 3 |
| **Mobile Screens** | 9 | 2 | - |
| **Test Files** | 140+ tests across all systems | - | - |
| **Documentation** | 15+ guides & implementation summaries | - | - |

**Total Test Coverage Points:** 140+ test files with 500+ individual test cases validating all major features.

---

## 🎓 Key Architectural Patterns

1. **Provider-based abstraction** - Transport, TTS, STT, agents, secrets
2. **Confirmation workflow** - Safety via pending_actions + tokens
3. **Event-driven notifications** - Task completion → notification → mobile UI
4. **Agent delegation** - Create issue → poll → webhook correlation
5. **Policy evaluation** - Fine-grained control over AI capabilities
6. **Multi-backend secrets** - Env, AWS, GCP, Vault with auto-detection
7. **Idempotent operations** - Deduplication via idempotency_keys
8. **Webhook deduplication** - Event filtering via webhook_events table
9. **RAG-based AI** - History indexing for contextual responses
10. **Mobile-backend sync** - Follow-on tasks keep UI in sync with backend state

---

## 📝 Notes

- **Status**: This inventory reflects the codebase as of March 9, 2026
- **Feature Maturity**: Core features are production-ready; experimental features are in active development
- **Test Validation**: All major features have corresponding test coverage
- **Integration**: External integrations are submodule-based and independently versioned
- **Documentation**: Rich inline documentation and multiple runbooks available

---

**Generated by: Codebase Analysis Agent**  
**Scope: Complete inventory of handsfree-dev-companion backend + mobile**
