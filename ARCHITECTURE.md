# HandsFree Dev Companion - Architecture

This document provides a comprehensive overview of the HandsFree Dev Companion system architecture, component relationships, and data flows.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [API Architecture](#api-architecture)
6. [Mobile Architecture](#mobile-architecture)
7. [Database Schema](#database-schema)
8. [Authentication & Security](#authentication--security)
9. [Deployment Architecture](#deployment-architecture)
10. [Scaling Considerations](#scaling-considerations)

---

## System Overview

HandsFree Dev Companion is a voice-first AI assistant for GitHub development workflows, designed for hands-free operation through mobile devices and Meta AI Glasses.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interface Layer                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────┐         ┌─────────────────┐         ┌───────────────┐ │
│  │   Meta Glasses   │ ◄─BT──► │   Mobile App    │ ◄─HTTPS─► │  Web UI      │ │
│  │   (Audio I/O)    │         │  (iOS/Android)  │         │  (Future)     │ │
│  └──────────────────┘         └─────────────────┘         └───────────────┘ │
│                                        │                                      │
└────────────────────────────────────────┼──────────────────────────────────────┘
                                         │
                                         │ HTTPS/WSS
                                         │
┌────────────────────────────────────────▼──────────────────────────────────────┐
│                            Application Layer                                  │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      FastAPI Backend Server                          │    │
│  │                                                                       │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │   Command    │  │     TTS      │  │     STT      │              │    │
│  │  │  Processing  │  │   Service    │  │   Service    │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  │                                                                       │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │    Intent    │  │  Notification│  │    Agent     │              │    │
│  │  │  Recognition │  │   Manager    │  │  Delegation  │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  │                                                                       │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │   GitHub     │  │     Auth     │  │   Webhook    │              │    │
│  │  │  Integration │  │   Service    │  │   Handler    │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
└────────────────────────────────────────┬──────────────────────────────────────┘
                                         │
                                         │
┌────────────────────────────────────────▼──────────────────────────────────────┐
│                              Data Layer                                       │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │    DuckDB    │    │    Redis     │    │  File System │                  │
│  │  (Embedded)  │    │   (Cache)    │    │  (Temp Files)│                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         │
┌────────────────────────────────────────▼──────────────────────────────────────┐
│                          External Services Layer                              │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  GitHub API  │    │  OpenAI API  │    │  Expo Push   │                  │
│  │              │    │  (TTS/STT)   │    │  Service     │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ Agent Runner │    │    Vault     │    │     S3       │                  │
│  │  (GitHub)    │    │  (Secrets)   │    │  (Storage)   │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Voice-First**: Optimized for hands-free operation
2. **Fixture-Based Development**: Test with realistic data before implementing
3. **Safe Policy-Driven**: Confirmation required for destructive operations
4. **Agent Delegation**: Offload complex tasks to external agents
5. **Offline-Capable**: Local data persistence with DuckDB

---

## Component Architecture

### Backend Server

**Technology**: Python 3.11+, FastAPI

**Core Modules**:

```
src/handsfree/
├── api/                    # FastAPI endpoints
│   ├── v1/                # API v1 routes
│   │   ├── commands.py    # Command processing
│   │   ├── tts.py         # Text-to-speech
│   │   ├── notifications.py
│   │   ├── webhooks.py
│   │   └── admin.py
│   └── middleware/        # Auth, logging, CORS
│
├── services/              # Business logic
│   ├── command_processor.py
│   ├── intent_recognizer.py
│   ├── tts_service.py
│   ├── stt_service.py
│   ├── github_service.py
│   ├── notification_service.py
│   └── agent_delegate.py
│
├── db/                    # Database models & queries
│   ├── connection.py      # DuckDB connection
│   ├── migrations.py      # Schema migrations
│   ├── commands.py        # Command history
│   ├── notifications.py
│   ├── api_keys.py
│   └── pending_actions.py
│
├── providers/             # External service integrations
│   ├── github/
│   │   ├── client.py
│   │   ├── webhook_parser.py
│   │   └── fixtures.py    # Fixture mode
│   ├── tts/
│   │   ├── openai.py
│   │   └── stub.py
│   ├── stt/
│   │   ├── openai.py
│   │   └── stub.py
│   └── push/
│       └── expo.py
│
└── secrets/               # Secret management
    ├── factory.py
    ├── vault_secrets.py
    └── gcp_secrets.py
```

**Key Services**:

1. **Command Processor**
   - Receives user commands (text or audio)
   - Calls STT service for audio transcription
   - Passes to Intent Recognizer
   - Generates response with spoken text and UI cards
   - Returns structured response

2. **Intent Recognizer**
   - Parses command text
   - Maps to intent (e.g., `inbox.summary`, `pr.merge`)
   - Extracts entities (PR numbers, user names)
   - Returns intent + entities

3. **TTS Service**
   - Converts text to speech audio
   - Supports multiple providers (OpenAI, stub)
   - Formats: WAV, MP3, OPUS
   - Caches generated audio

4. **STT Service**
   - Transcribes audio to text
   - Supports multiple providers (OpenAI, stub)
   - Handles various audio formats

5. **GitHub Service**
   - Wraps GitHub API
   - Two modes: Live (real API) and Fixture (sample data)
   - Handles rate limiting and authentication
   - Caches responses in Redis

6. **Notification Service**
   - Manages user notifications
   - Triggered by GitHub webhooks
   - Sends push notifications via Expo
   - Tracks read/unread state

7. **Agent Delegate**
   - Delegates tasks to external agents
   - Creates dispatch issues in GitHub
   - Tracks task progress
   - Correlates PRs back to tasks

### Mobile App

**Technology**: React Native, Expo

**Core Structure**:

```
mobile/
├── src/
│   ├── api/                      # Backend API client
│   │   ├── config.js            # BASE_URL, auth config
│   │   └── client.js            # API methods
│   │
│   ├── screens/                 # App screens
│   │   ├── StatusScreen.js      # Backend status
│   │   ├── CommandScreen.js     # Voice/text commands
│   │   ├── ConfirmationScreen.js
│   │   ├── TTSScreen.js
│   │   ├── SettingsScreen.js
│   │   └── GlassesDiagnosticsScreen.js
│   │
│   ├── components/              # Reusable UI components
│   │   ├── AudioRecorder.js
│   │   ├── AudioPlayer.js
│   │   └── NotificationBanner.js
│   │
│   └── utils/                   # Utilities
│       ├── storage.js           # AsyncStorage wrapper
│       ├── permissions.js
│       └── bluetooth.js
│
├── modules/                     # Native modules
│   └── expo-glasses-audio/      # Bluetooth audio routing
│       ├── ios/                 # Swift implementation
│       │   ├── ExpoGlassesAudioModule.swift
│       │   ├── AudioRouteMonitor.swift
│       │   ├── GlassesRecorder.swift
│       │   └── GlassesPlayer.swift
│       ├── android/             # Kotlin implementation
│       │   └── src/main/java/expo/modules/glassesaudio/
│       └── index.ts             # JS interface
│
├── App.js                       # Root component
├── index.js                     # Entry point
└── app.json                     # Expo configuration
```

**Key Features**:

1. **Voice Command Capture**
   - Records audio from microphone
   - Uploads to backend dev endpoint
   - Sends audio URI to `/v1/command`

2. **TTS Playback**
   - Fetches TTS audio from backend
   - Routes playback through Bluetooth (glasses) or phone speaker
   - Auto-plays responses when enabled

3. **Push Notifications**
   - Registers device token with backend
   - Receives push notifications via Expo
   - Auto-speaks notifications when enabled
   - Deep-links to relevant screens

4. **Bluetooth Integration**
   - Native iOS/Android modules
   - Monitors audio route changes
   - Records from Bluetooth microphone
   - Plays through Bluetooth speakers

### Native Bluetooth Module

**expo-glasses-audio**: Custom Expo module for Bluetooth audio routing

**iOS Implementation** (Swift):

- `AVAudioSession` for audio session management
- Real-time audio route monitoring
- Native recording from Bluetooth mic
- Native playback through Bluetooth speakers

**Android Implementation** (Kotlin):

- `AudioManager` for audio routing
- Bluetooth SCO (Synchronous Connection-Oriented) for voice
- `MediaRecorder` for recording
- `MediaPlayer` for playback

---

## Data Flow

### Voice Command Flow

```
┌──────────┐
│   User   │
└─────┬────┘
      │ Speaks: "Show my inbox"
      ▼
┌──────────────────┐
│  Meta Glasses    │
│  (Microphone)    │
└─────┬────────────┘
      │ Audio via Bluetooth
      ▼
┌──────────────────┐
│   Mobile App     │
│  (iOS/Android)   │
└─────┬────────────┘
      │ 1. Record audio
      │ 2. Upload to /v1/dev/audio → file:// URI
      │ 3. POST /v1/command with audio URI
      ▼
┌──────────────────┐
│  Backend API     │
│  (Command EP)    │
└─────┬────────────┘
      │ 4. Call STT service
      ▼
┌──────────────────┐
│  STT Service     │
│  (OpenAI)        │
└─────┬────────────┘
      │ 5. Transcript: "Show my inbox"
      ▼
┌──────────────────┐
│ Intent Recognizer│
└─────┬────────────┘
      │ 6. Intent: inbox.summary
      ▼
┌──────────────────┐
│  GitHub Service  │
└─────┬────────────┘
      │ 7. Fetch PRs, issues
      ▼
┌──────────────────┐
│  Response Builder│
└─────┬────────────┘
      │ 8. Generate response:
      │    - spoken_text: "You have 3 PRs..."
      │    - ui_cards: [PR 123, PR 124, ...]
      ▼
┌──────────────────┐
│   Mobile App     │
└─────┬────────────┘
      │ 9. Display UI cards
      │ 10. POST /v1/tts with spoken_text
      ▼
┌──────────────────┐
│   TTS Service    │
│   (OpenAI)       │
└─────┬────────────┘
      │ 11. Generate audio (WAV/MP3)
      ▼
┌──────────────────┐
│   Mobile App     │
│  (Audio Player)  │
└─────┬────────────┘
      │ 12. Play via Bluetooth
      ▼
┌──────────────────┐
│  Meta Glasses    │
│   (Speakers)     │
└──────────────────┘
      │
      ▼
┌──────────┐
│   User   │ Hears: "You have 3 PRs awaiting review..."
└──────────┘
```

### Confirmation Flow

```
┌──────────┐
│   User   │ Speaks: "Merge PR 123"
└─────┬────┘
      ▼
┌──────────────────┐
│  Backend API     │
└─────┬────────────┘
      │ Recognizes destructive intent
      ▼
┌──────────────────┐
│ Pending Actions  │
│  (Database)      │
└─────┬────────────┘
      │ Store action with token
      ▼
┌──────────────────┐
│   Response       │
│ status: pending  │
│ requires_confirm │
└─────┬────────────┘
      ▼
┌──────────────────┐
│   Mobile App     │
└─────┬────────────┘
      │ TTS: "Ready to merge PR 123. Say confirm."
      │ UI: Show Confirm/Cancel buttons
      ▼
┌──────────┐
│   User   │ Speaks: "Confirm"
└─────┬────┘
      ▼
┌──────────────────┐
│   Mobile App     │
│ POST /v1/commands│
│     /confirm     │
└─────┬────────────┘
      │ confirmation_token
      ▼
┌──────────────────┐
│  Backend API     │
└─────┬────────────┘
      │ Verify token
      │ Execute action
      ▼
┌──────────────────┐
│  GitHub API      │
│  Merge PR 123    │
└─────┬────────────┘
      │ Success
      ▼
┌──────────────────┐
│   Response       │
│ status: success  │
└─────┬────────────┘
      ▼
┌──────────┐
│   User   │ Hears: "PR 123 merged successfully"
└──────────┘
```

### Webhook → Notification Flow

```
┌──────────────────┐
│  GitHub Webhook  │
│  (PR opened)     │
└─────┬────────────┘
      │ POST /v1/webhooks/github
      ▼
┌──────────────────┐
│  Webhook Handler │
└─────┬────────────┘
      │ 1. Verify signature
      │ 2. Parse event
      ▼
┌──────────────────┐
│ Notification     │
│   Service        │
└─────┬────────────┘
      │ 3. Create notification
      │ 4. Store in database
      ▼
┌──────────────────┐
│  Push Service    │
│  (Expo)          │
└─────┬────────────┘
      │ 5. Send push notification
      ▼
┌──────────────────┐
│   Mobile App     │
└─────┬────────────┘
      │ 6. Receive notification
      │ 7. If enabled, auto-speak via TTS
      │ 8. Display banner/alert
      ▼
┌──────────┐
│   User   │ Hears/Sees: "PR 123 opened by Alice"
└──────────┘
```

### Agent Delegation Flow

```
┌──────────┐
│   User   │ "Ask agent to fix issue 918"
└─────┬────┘
      ▼
┌──────────────────┐
│  Backend API     │
│ Intent: agent.   │
│       delegate   │
└─────┬────────────┘
      │
      ▼
┌──────────────────┐
│ Agent Delegate   │
│    Service       │
└─────┬────────────┘
      │ 1. Create dispatch issue
      │    in GitHub repo
      ▼
┌──────────────────┐
│  GitHub API      │
│ POST /repos/.../│
│     issues       │
└─────┬────────────┘
      │ 2. Issue created
      ▼
┌──────────────────┐
│ Agent Task DB    │
└─────┬────────────┘
      │ 3. Store task_id
      │    correlation_id
      ▼
┌──────────────────┐
│  External Agent  │
│  (GitHub Action) │
└─────┬────────────┘
      │ 4. Monitors dispatch repo
      │ 5. Processes issue
      │ 6. Creates PR
      ▼
┌──────────────────┐
│  GitHub Webhook  │
│  (PR opened)     │
└─────┬────────────┘
      │ 7. POST /v1/webhooks/github
      ▼
┌──────────────────┐
│  Webhook Handler │
└─────┬────────────┘
      │ 8. Correlate PR to task
      │ 9. Update task status
      ▼
┌──────────────────┐
│  Notification    │
│    Service       │
└─────┬────────────┘
      │ 10. Notify user
      ▼
┌──────────┐
│   User   │ "Agent completed task, PR 999 ready"
└──────────┘
```

---

## Technology Stack

### Backend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI | Web framework with async support |
| **Language** | Python 3.11+ | Application code |
| **Database** | DuckDB | Embedded SQL database |
| **Cache** | Redis | Caching and job queues |
| **TTS** | OpenAI API | Text-to-speech generation |
| **STT** | OpenAI API | Speech-to-text transcription |
| **GitHub** | PyGithub, REST API | GitHub integration |
| **Secrets** | Vault, GCP Secret Manager | Secret storage |
| **Deployment** | Docker, Docker Compose | Containerization |

### Mobile

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | React Native | Cross-platform mobile |
| **Build Tool** | Expo | Development & build |
| **Navigation** | React Navigation | Screen navigation |
| **Storage** | AsyncStorage | Local data persistence |
| **Audio** | expo-av | Audio playback |
| **Notifications** | expo-notifications | Push notifications |
| **Native Modules** | Expo Modules API | Bluetooth integration |
| **iOS Audio** | AVAudioSession (Swift) | iOS audio routing |
| **Android Audio** | AudioManager (Kotlin) | Android audio routing |

### Development

| Tool | Purpose |
|------|---------|
| **Ruff** | Python linting & formatting |
| **pytest** | Python testing |
| **OpenAPI** | API specification |
| **Make** | Build automation |
| **Git** | Version control |

---

## API Architecture

### RESTful Endpoints

**Base URL**: `https://api.handsfree.dev` (or `http://localhost:8080` for dev)

**API Version**: v1

#### Core Endpoints

```
POST   /v1/command              # Process voice/text command
POST   /v1/commands/confirm     # Confirm pending action
GET    /v1/status               # Health check
POST   /v1/tts                  # Generate TTS audio
POST   /v1/dev/audio            # Upload audio (dev mode)
```

#### Notifications

```
GET    /v1/notifications                      # List notifications
GET    /v1/notifications/{id}                 # Get notification
POST   /v1/notifications/subscriptions        # Register device
DELETE /v1/notifications/subscriptions/{id}   # Unregister device
```

#### Admin

```
POST   /v1/admin/api-keys        # Create API key
GET    /v1/admin/api-keys         # List API keys
DELETE /v1/admin/api-keys/{id}    # Revoke API key
```

#### Webhooks

```
POST   /v1/webhooks/github       # GitHub webhook ingestion
```

#### Agent Delegation

```
POST   /v1/agent/delegate        # Delegate task to agent
GET    /v1/agent/tasks           # List agent tasks
GET    /v1/agent/tasks/{id}      # Get task status
```

### Authentication Modes

1. **Dev Mode** (`HANDSFREE_AUTH_MODE=dev`)
   - Accepts `X-User-ID` header
   - Falls back to fixture user
   - No credentials required

2. **JWT Mode** (`HANDSFREE_AUTH_MODE=jwt`)
   - Requires `Authorization: Bearer <jwt>`
   - Extracts `user_id` from token claims

3. **API Key Mode** (`HANDSFREE_AUTH_MODE=api_key`)
   - Requires `Authorization: Bearer <api_key>`
   - Keys stored hashed in database

### Request/Response Format

**Command Request**:

```json
{
  "input": {
    "type": "text",
    "text": "show my inbox"
  },
  "profile": "terse",
  "client_context": {
    "device_type": "mobile",
    "app_version": "1.0.0",
    "session_id": "abc123"
  }
}
```

**Command Response**:

```json
{
  "status": "success",
  "intent": "inbox.summary",
  "spoken_text": "You have 3 pull requests awaiting review...",
  "ui_cards": [
    {
      "type": "pr_summary",
      "pr_number": 123,
      "title": "Add feature",
      "author": "alice",
      "url": "https://github.com/..."
    }
  ],
  "requires_confirmation": false,
  "debug": {
    "processing_time_ms": 234,
    "provider": "fixture"
  }
}
```

---

## Mobile Architecture

### Screen Flow

```
App Launch
    │
    ▼
┌─────────────────────┐
│  Tab Navigator      │
├─────────────────────┤
│                     │
│  ┌───────────────┐  │     ┌──────────────────┐
│  │  Status       │──┼────►│ Backend Config   │
│  └───────────────┘  │     └──────────────────┘
│                     │
│  ┌───────────────┐  │     ┌──────────────────┐
│  │  Command      │──┼────►│ Voice Recording  │
│  └───────────────┘  │     │ Text Input       │
│                     │     │ Response Display │
│                     │     └──────────────────┘
│  ┌───────────────┐  │
│  │ Confirmation  │  │
│  └───────────────┘  │
│                     │
│  ┌───────────────┐  │     ┌──────────────────┐
│  │  TTS Test     │──┼────►│ Audio Player     │
│  └───────────────┘  │     └──────────────────┘
│                     │
│  ┌───────────────┐  │     ┌──────────────────┐
│  │  Settings     │──┼────►│ User ID Config   │
│  └───────────────┘  │     │ Backend URL      │
│                     │     │ Notification     │
│  ┌───────────────┐  │     │ Settings         │
│  │  Glasses      │──┼────►└──────────────────┘
│  │  Diagnostics  │  │
│  └───────────────┘  │     ┌──────────────────┐
│                     │     │ Audio Route Info │
└─────────────────────┘     │ Recording Test   │
                            │ Playback Test    │
                            └──────────────────┘
```

### State Management

- **Local State**: React hooks (`useState`, `useEffect`)
- **Persistent State**: AsyncStorage
  - User ID
  - Backend URL
  - Notification preferences
- **Session State**: In-memory during app lifecycle

### Native Module Integration

**JavaScript Layer**:

```javascript
import * as GlassesAudio from './modules/expo-glasses-audio';

// Get audio route
const route = GlassesAudio.getAudioRoute();
// { inputDevice, outputDevice, isBluetoothConnected }

// Start recording
const result = await GlassesAudio.startRecording(10);
// { uri, duration, size }

// Play audio
await GlassesAudio.playAudio(fileUri);

// Listen for route changes
const sub = GlassesAudio.addAudioRouteChangeListener((route) => {
  console.log('Route changed:', route);
});
```

**Native Layer** (iOS):

```swift
@objc(ExpoGlassesAudioModule)
public class ExpoGlassesAudioModule: Module {
  public func definition() -> ModuleDefinition {
    Name("ExpoGlassesAudio")
    
    Function("getAudioRoute") { () -> [String: Any] in
      return AudioRouteMonitor.shared.getCurrentRoute()
    }
    
    AsyncFunction("startRecording") { (duration: Int) -> [String: Any] in
      return try await GlassesRecorder.shared.record(duration: duration)
    }
    
    Events("onAudioRouteChange")
  }
}
```

---

## Database Schema

**Technology**: DuckDB (embedded SQL database)

### Core Tables

#### `commands`

Stores command history for analytics and debugging.

```sql
CREATE TABLE commands (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  input_type VARCHAR NOT NULL,  -- 'text' or 'audio'
  input_text VARCHAR,
  input_uri VARCHAR,
  intent VARCHAR,
  status VARCHAR,  -- 'success', 'failed', 'pending'
  response_text VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  processing_time_ms INTEGER
);
```

#### `pending_actions`

Stores actions requiring user confirmation.

```sql
CREATE TABLE pending_actions (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  action_type VARCHAR NOT NULL,  -- 'pr.merge', 'pr.request_review', etc.
  action_data JSON NOT NULL,
  confirmation_token VARCHAR UNIQUE NOT NULL,
  status VARCHAR DEFAULT 'pending',  -- 'pending', 'confirmed', 'cancelled', 'expired'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  confirmed_at TIMESTAMP,
  executed_at TIMESTAMP
);
```

#### `notifications`

Stores user notifications from GitHub webhooks.

```sql
CREATE TABLE notifications (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  type VARCHAR NOT NULL,  -- 'pr_opened', 'pr_review_requested', etc.
  title VARCHAR NOT NULL,
  body VARCHAR,
  data JSON,
  read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  read_at TIMESTAMP
);
```

#### `notification_subscriptions`

Stores device push tokens for notifications.

```sql
CREATE TABLE notification_subscriptions (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  push_token VARCHAR NOT NULL,
  platform VARCHAR NOT NULL,  -- 'ios', 'android', 'web'
  device_id VARCHAR,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_used_at TIMESTAMP
);
```

#### `api_keys`

Stores hashed API keys for authentication.

```sql
CREATE TABLE api_keys (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  key_hash VARCHAR NOT NULL,  -- SHA256 hash
  label VARCHAR,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_used_at TIMESTAMP,
  revoked_at TIMESTAMP
);
```

#### `agent_tasks`

Tracks agent delegation tasks.

```sql
CREATE TABLE agent_tasks (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  task_type VARCHAR NOT NULL,
  task_data JSON NOT NULL,
  provider VARCHAR,  -- 'copilot', 'github_issue_dispatch'
  dispatch_issue_url VARCHAR,
  correlation_id VARCHAR,
  status VARCHAR DEFAULT 'dispatched',  -- 'dispatched', 'running', 'completed', 'failed'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  result_pr_url VARCHAR
);
```

#### `webhook_events`

Stores raw GitHub webhook payloads for replay.

```sql
CREATE TABLE webhook_events (
  id VARCHAR PRIMARY KEY,
  event_type VARCHAR NOT NULL,  -- 'pull_request', 'issue_comment', etc.
  payload JSON NOT NULL,
  signature VARCHAR,
  processed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  processed_at TIMESTAMP
);
```

---

## Authentication & Security

### Authentication Flow

1. **Client** sends request with credentials:
   - Dev mode: `X-User-ID` header
   - JWT mode: `Authorization: Bearer <jwt>`
   - API key mode: `Authorization: Bearer <api_key>`

2. **Middleware** validates credentials:
   - Dev mode: Always passes, uses provided user ID or fixture
   - JWT mode: Verifies signature, extracts user ID from claims
   - API key mode: Hashes key, looks up in database

3. **Request** proceeds with authenticated `user_id`

### API Key Security

- **Never stored in plaintext**: SHA256 hashed before storage
- **One-way hash**: Cannot recover original key
- **Revocable**: Can be deactivated without deleting
- **Labeled**: User-friendly labels for management
- **Tracked**: Last used timestamp for auditing

### GitHub Token Security

- **Secret Storage**: Stored in Vault or GCP Secret Manager (not in code/DB)
- **Scoped Permissions**: Minimal required scopes (repo, read:org)
- **User-Specific**: Each user has their own GitHub token
- **OAuth Flow**: Supports GitHub OAuth for token acquisition

### HTTPS/TLS

- **Required for production**: All external traffic over HTTPS
- **Certificate Pinning**: Recommended for mobile apps
- **Secure WebSockets**: WSS for real-time updates (future)

---

## Deployment Architecture

### Development Environment

```
┌──────────────────────────────────────────────────────────────┐
│  Developer Machine                                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │  Backend Server │         │  Redis          │           │
│  │  (localhost:8080)│        │  (Docker)       │           │
│  └─────────────────┘         └─────────────────┘           │
│           │                                                  │
│           │ File System                                      │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │  DuckDB         │                                        │
│  │  (./data/db)    │                                        │
│  └─────────────────┘                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                       │
                       │ Network (WiFi/LAN)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Mobile Device (iPhone)                                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐                                        │
│  │  Mobile App     │                                        │
│  │  (Expo Dev)     │                                        │
│  └─────────────────┘                                        │
│           │                                                  │
│           │ Bluetooth                                        │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │  Meta Glasses   │                                        │
│  └─────────────────┘                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Production Environment

```
┌──────────────────────────────────────────────────────────────┐
│  Cloud Platform (AWS/GCP/Azure)                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Load Balancer (HTTPS)                              │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                       │
│       ┌──────────────┼──────────────┐                       │
│       │              │              │                       │
│       ▼              ▼              ▼                       │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                  │
│  │ Backend │   │ Backend │   │ Backend │                  │
│  │Instance1│   │Instance2│   │Instance3│                  │
│  └─────────┘   └─────────┘   └─────────┘                  │
│       │              │              │                       │
│       └──────────────┼──────────────┘                       │
│                      │                                       │
│       ┌──────────────┼──────────────┐                       │
│       │              │              │                       │
│       ▼              ▼              ▼                       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │  Redis   │   │  DuckDB  │   │  Vault   │               │
│  │ (Managed)│   │  (EBS)   │   │(Secrets) │               │
│  └──────────┘   └──────────┘   └──────────┘               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                       │
                       │ HTTPS
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Mobile Devices (iPhone, Android)                           │
└──────────────────────────────────────────────────────────────┘
```

### Docker Deployment

**Dockerfile**: Multi-stage build for smaller images

```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY src/ ./src/
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "handsfree.api:app", "--host", "0.0.0.0", "--port", "8080"]
```

**docker-compose.yml**: Multi-service orchestration

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - REDIS_HOST=redis
      - DUCKDB_PATH=/app/data/handsfree.db
    volumes:
      - handsfree-data:/app/data
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  handsfree-data:
  redis-data:
```

---

## Scaling Considerations

### Horizontal Scaling

- **Stateless API**: Backend instances are stateless, can scale horizontally
- **Load Balancer**: Distribute requests across multiple instances
- **Redis for State**: Shared cache for session data
- **DuckDB Limitations**: Embedded DB, consider PostgreSQL for multi-instance deployments

### Performance Optimizations

1. **Caching**:
   - GitHub API responses cached in Redis (TTL: 5 minutes)
   - TTS audio cached for common phrases
   - Intent recognition results cached per transcript

2. **Async Processing**:
   - TTS generation async (return 202, poll for result)
   - Webhook processing in background jobs
   - Agent delegation non-blocking

3. **Rate Limiting**:
   - GitHub API: Respect rate limits, use conditional requests
   - TTS API: Queue requests, batch when possible
   - Mobile API: Rate limit per user/device

4. **Database Optimization**:
   - Indexes on frequently queried columns (user_id, created_at)
   - Partition old data (archive commands older than 90 days)
   - VACUUM regularly to reclaim space

### Monitoring

- **Metrics**: Prometheus-compatible `/v1/metrics` endpoint
- **Logging**: Structured JSON logs to stdout
- **Tracing**: Correlation IDs for request tracking
- **Alerting**: Monitor error rates, latency, resource usage

---

## Future Enhancements

### Planned Features

1. **WebSocket Support**: Real-time bidirectional communication
2. **Multi-User Collaboration**: Team workspaces and shared contexts
3. **Voice Profiles**: User-specific voice models and preferences
4. **Offline Mode**: Local processing with sync when online
5. **Web UI**: Browser-based interface for desktop use
6. **Plugin System**: Extensible integrations beyond GitHub
7. **Analytics Dashboard**: Usage insights and command patterns

### Technical Debt

1. **Database Migration**: DuckDB → PostgreSQL for production scale
2. **Audio Storage**: Local files → S3/Cloud Storage
3. **Secret Management**: Migrate all secrets to Vault
4. **API Versioning**: Implement v2 API with breaking changes
5. **Mobile CI/CD**: Automated testing and deployment for mobile

---

## Contributing to Architecture

When proposing architectural changes:

1. **Document Design**: Create a design doc in `implementation_plan/`
2. **Review Existing Patterns**: Follow established patterns
3. **Consider Scale**: How will this work with 10x/100x growth?
4. **Security First**: Review security implications
5. **Test Strategy**: Plan for testing and rollback

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

**Architecture Documentation Version**: 1.0  
**Last Updated**: 2026-01-20  
**Maintainer**: Development Team
