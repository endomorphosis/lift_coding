# Technical Architecture

## High-level diagram (logical)

Wearable (mic/cam/speaker)
  -> Mobile App (session, capture, UI, local policy hints)
    -> Backend API (auth, command routing, integrations)
      -> Integrations (GitHub, CI providers, Agent runner)
    <- Backend pushes events/notifications
  <- Mobile plays TTS / shows brief UI (if available)

## Components
1. Wearable I/O
- Audio input (voice)
- Optional camera capture
- Audio output (TTS playback)

2. Mobile app
- Manages wearable connection and permissions
- Push-to-talk / recording UX
- Streams audio to backend or runs on-device STT (optional)
- Plays TTS responses
- Receives push notifications and renders short summaries

3. Backend API
- Authentication + user identity
- Command Router (intent -> tool calls)
- Policy Engine (authorization + safety constraints)
- Event Ingest (webhooks)
- Notification Service (push -> device)

4. Integrations (plugins)
- GitHub: PRs, issues, checks, comments, merges
- CI: optional direct integration if needed
- Agent Orchestrator: Copilot agent / custom agent runner

## Data flows
### Command flow
Voice -> STT -> Intent parse -> Validate -> Execute tool -> Compose response -> TTS -> Playback

### Event flow
Webhook -> Normalize event -> Update state -> Decide notify? -> Push -> Spoken summary

## Key design choices
- Plugin-based integrations
- Stateless API endpoints + durable event store
- Explicit policy checks before side-effecting actions
- Profiles adjust summarization and confirmations

## Tight iteration loop (overview)
See `docs/11-devloop-vscode.md`:
- local wearable simulator (no glasses required)
- fixture-driven GitHub and agent mocks
- contract tests against OpenAPI
- replay tools for webhook payloads and command transcripts
- CI gates so regressions are caught before you try on-device
