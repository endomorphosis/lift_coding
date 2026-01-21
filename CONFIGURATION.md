# Configuration Guide

This guide covers all configuration options for the HandsFree Dev Companion system, including environment variables, mobile app settings, and deployment configurations.

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Backend Configuration](#backend-configuration)
3. [Mobile App Configuration](#mobile-app-configuration)
4. [Development vs Production](#development-vs-production)
5. [Authentication Configuration](#authentication-configuration)
6. [External Services](#external-services)
7. [Feature Flags](#feature-flags)
8. [Troubleshooting Configuration Issues](#troubleshooting-configuration-issues)

---

## Environment Variables

### Quick Setup

**For Development** (minimal configuration):

```bash
# Copy example environment
cp .env.example .env

# Or create .env with minimal settings:
cat > .env << 'EOF'
# Authentication
HANDSFREE_AUTH_MODE=dev

# TTS/STT (stub = no API keys needed)
HANDSFREE_TTS_PROVIDER=stub
HANDS_FREE_STT_PROVIDER=stub

# GitHub (fixture = uses sample data)
GITHUB_LIVE_MODE=false

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
EOF
```

**For Production/Realistic Testing**:

```bash
cat > .env << 'EOF'
# Authentication
HANDSFREE_AUTH_MODE=api_key

# TTS/STT (requires OpenAI API key)
HANDSFREE_TTS_PROVIDER=openai
HANDS_FREE_STT_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# GitHub (requires personal access token)
GITHUB_LIVE_MODE=true
GITHUB_TOKEN=ghp_your-token-here

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379

# Push Notifications (optional)
EXPO_PUSH_TOKEN=ExponentPushToken[...]
EOF
```

---

## Backend Configuration

### Core Settings

#### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Port for the API server |
| `HOST` | `0.0.0.0` | Host to bind to (`0.0.0.0` for network access) |
| `RELOAD` | `false` | Auto-reload on code changes (dev only) |
| `LOG_LEVEL` | `info` | Logging level: `debug`, `info`, `warning`, `error` |

**Example**:

```bash
PORT=8080
HOST=0.0.0.0
LOG_LEVEL=debug
```

#### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DUCKDB_PATH` | `./data/handsfree.db` | Path to DuckDB database file |
| `DUCKDB_READONLY` | `false` | Open database in read-only mode |

**Example**:

```bash
DUCKDB_PATH=/app/data/handsfree.db
DUCKDB_READONLY=false
```

**Note**: For Docker deployments, mount a persistent volume at the database path to preserve data across container restarts.

#### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_ENABLED` | `true` | Enable/disable Redis caching |
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_PASSWORD` | _(empty)_ | Redis password (if required) |
| `REDIS_SSL` | `false` | Use SSL/TLS for Redis connection |

**Example**:

```bash
REDIS_ENABLED=true
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_SSL=true
```

---

### Authentication Configuration

#### Auth Modes

| Variable | Options | Description |
|----------|---------|-------------|
| `HANDSFREE_AUTH_MODE` | `dev`, `jwt`, `api_key` | Authentication mode |

**Development Mode** (`dev`):

```bash
HANDSFREE_AUTH_MODE=dev
```

- No authentication required
- Accepts `X-User-ID` header for testing
- Falls back to fixture user if not provided
- **⚠️ NOT FOR PRODUCTION**

**JWT Mode** (`jwt`):

```bash
HANDSFREE_AUTH_MODE=jwt
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256  # Optional, defaults to HS256
```

- Requires valid JWT bearer tokens
- Extracts `user_id` from token claims (`user_id`, `sub`, or `uid`)
- Token verification using shared secret

**API Key Mode** (`api_key`):

```bash
HANDSFREE_AUTH_MODE=api_key
```

- Requires API keys stored in database
- Keys are hashed (SHA256) before storage
- Manage keys via CLI: `python scripts/manage_api_keys.py`

---

### External Services

#### GitHub Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_LIVE_MODE` | `false` | Use real GitHub API vs fixtures |
| `GITHUB_TOKEN` | _(empty)_ | Personal access token for GitHub API |
| `GITHUB_APP_ID` | _(empty)_ | GitHub App ID (optional) |
| `GITHUB_APP_PRIVATE_KEY_PEM` | _(empty)_ | GitHub App private key (optional) |
| `GITHUB_INSTALLATION_ID` | _(empty)_ | GitHub App installation ID (optional) |

**Fixture Mode** (default):

```bash
GITHUB_LIVE_MODE=false
# No token required - uses canned sample data
```

- Fast and predictable
- No rate limits
- No external dependencies
- Perfect for development and testing

**Live Mode**:

```bash
GITHUB_LIVE_MODE=true
GITHUB_TOKEN=ghp_your-personal-access-token-here
```

- Real GitHub API calls
- Requires valid token
- Subject to rate limits
- Use for realistic testing

**Token Scopes Required**:
- `repo` - Full control of private repositories
- `read:org` - Read org membership
- `workflow` - Update GitHub Actions workflows (optional)

**Creating a Token**:
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select required scopes
4. Copy token and add to `.env`

#### OpenAI Integration (TTS/STT)

| Variable | Default | Description |
|----------|---------|-------------|
| `HANDSFREE_TTS_PROVIDER` | `stub` | TTS provider: `stub`, `openai` |
| `HANDS_FREE_STT_PROVIDER` | `stub` | STT provider: `stub`, `openai` |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key |
| `OPENAI_TTS_MODEL` | `tts-1` | TTS model: `tts-1`, `tts-1-hd` |
| `OPENAI_STT_MODEL` | `whisper-1` | STT model |

**Stub Mode** (no API key needed):

```bash
HANDSFREE_TTS_PROVIDER=stub
HANDS_FREE_STT_PROVIDER=stub
# No API key required
```

- Returns deterministic placeholder responses
- Fast and free
- Great for development without external dependencies

**OpenAI Mode** (realistic audio):

```bash
HANDSFREE_TTS_PROVIDER=openai
HANDS_FREE_STT_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key-here
```

- High-quality TTS and STT
- Requires valid API key and billing
- Costs: ~$0.015 per 1000 TTS characters, ~$0.006 per minute STT

**Getting an API Key**:
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add to `.env`

#### Push Notifications (Expo)

| Variable | Default | Description |
|----------|---------|-------------|
| `EXPO_PUSH_TOKEN` | _(empty)_ | Expo push notification token (optional) |

**Setup**:

```bash
EXPO_PUSH_TOKEN=ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]
```

- Optional for development
- Required for push notifications to work
- Token is generated by mobile app and registered with backend

---

### Agent Delegation

| Variable | Default | Description |
|----------|---------|-------------|
| `HANDSFREE_AGENT_DEFAULT_PROVIDER` | _(auto)_ | Default agent provider: `copilot`, `github_issue_dispatch` |
| `HANDSFREE_AGENT_DISPATCH_REPO` | _(empty)_ | GitHub repo for issue dispatch (e.g., `owner/dispatch-repo`) |

**Automatic Provider Selection**:

1. **Explicit provider** in API call → Always used
2. **`HANDSFREE_AGENT_DEFAULT_PROVIDER`** → If set, use this
3. **`github_issue_dispatch`** → If `HANDSFREE_AGENT_DISPATCH_REPO` + `GITHUB_TOKEN` configured
4. **`copilot`** → Fallback

**Example Configuration**:

```bash
HANDSFREE_AGENT_DISPATCH_REPO=myorg/agent-dispatch
GITHUB_TOKEN=ghp_...
# Will automatically use github_issue_dispatch provider
```

For detailed setup, see [docs/agent-runner-setup.md](docs/agent-runner-setup.md).

---

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `HANDSFREE_ENABLE_METRICS` | `false` | Enable Prometheus metrics at `/v1/metrics` |
| `HANDSFREE_ENABLE_WEBHOOKS` | `true` | Enable GitHub webhook endpoints |
| `HANDSFREE_ENABLE_NOTIFICATIONS` | `true` | Enable notification system |

**Example**:

```bash
HANDSFREE_ENABLE_METRICS=true
HANDSFREE_ENABLE_WEBHOOKS=true
HANDSFREE_ENABLE_NOTIFICATIONS=true
```

---

## Mobile App Configuration

### In-App Settings

The mobile app includes an in-app Settings screen for configuration:

1. **User ID**: Set your user identifier (used in `X-User-ID` header)
2. **Backend URL**: Configure backend server URL
3. **Notification Settings**: Enable/disable auto-speaking notifications

**Default Values**:

- **Backend URL**: `http://localhost:8080` (iOS Simulator)
- **User ID**: Auto-generated UUID
- **Auto-speak notifications**: Enabled in dev builds, disabled in production

### Configuration File

Edit `mobile/src/api/config.js` to set default backend URL:

```javascript
// For iOS Simulator
export const BASE_URL = 'http://localhost:8080';

// For Android Emulator
// export const BASE_URL = 'http://10.0.2.2:8080';

// For physical device on same network
// export const BASE_URL = 'http://192.168.1.100:8080';

// For production
// export const BASE_URL = 'https://api.handsfree.dev';
```

### app.json Configuration

Expo configuration in `mobile/app.json`:

```json
{
  "expo": {
    "name": "handsfree-mobile",
    "slug": "handsfree-mobile",
    "version": "1.0.0",
    "orientation": "portrait",
    "ios": {
      "bundleIdentifier": "com.handsfree.mobile",
      "buildNumber": "1",
      "infoPlist": {
        "NSMicrophoneUsageDescription": "Record voice commands",
        "NSBluetoothAlwaysUsageDescription": "Connect to Meta AI Glasses"
      }
    },
    "android": {
      "package": "com.handsfree.mobile",
      "permissions": [
        "RECORD_AUDIO",
        "BLUETOOTH",
        "BLUETOOTH_CONNECT"
      ]
    }
  }
}
```

---

## Development vs Production

### Development Configuration

**Purpose**: Fast iteration, no external dependencies

```bash
# .env.development
HANDSFREE_AUTH_MODE=dev
HANDSFREE_TTS_PROVIDER=stub
HANDS_FREE_STT_PROVIDER=stub
GITHUB_LIVE_MODE=false
REDIS_HOST=localhost
LOG_LEVEL=debug
```

**Characteristics**:
- ✅ No API keys required
- ✅ Fast and predictable responses
- ✅ No rate limits
- ✅ Detailed debug logging
- ⚠️ Not secure - dev auth mode only

### Staging Configuration

**Purpose**: Realistic testing before production

```bash
# .env.staging
HANDSFREE_AUTH_MODE=jwt
JWT_SECRET_KEY=staging-secret-key-here
HANDSFREE_TTS_PROVIDER=openai
HANDS_FREE_STT_PROVIDER=openai
OPENAI_API_KEY=sk-staging-key-here
GITHUB_LIVE_MODE=true
GITHUB_TOKEN=ghp_staging-token-here
REDIS_HOST=redis-staging.example.com
REDIS_PASSWORD=staging-redis-password
LOG_LEVEL=info
```

**Characteristics**:
- ✅ Real external services
- ✅ JWT authentication
- ✅ Isolated from production data
- ✅ Safe for testing

### Production Configuration

**Purpose**: Live deployment

```bash
# .env.production
HANDSFREE_AUTH_MODE=api_key
HANDSFREE_TTS_PROVIDER=openai
HANDS_FREE_STT_PROVIDER=openai
OPENAI_API_KEY=sk-prod-key-here
GITHUB_LIVE_MODE=true
GITHUB_TOKEN=ghp_prod-token-here
REDIS_HOST=redis-prod.example.com
REDIS_PASSWORD=prod-redis-password
REDIS_SSL=true
HANDSFREE_ENABLE_METRICS=true
LOG_LEVEL=warning
```

**Characteristics**:
- ✅ Secure authentication (API keys)
- ✅ SSL/TLS for Redis
- ✅ Metrics enabled
- ✅ Warning-level logging (not debug)
- ⚠️ Never commit this file to git!

**Production Checklist**:

- [ ] `HANDSFREE_AUTH_MODE` set to `jwt` or `api_key` (NOT `dev`)
- [ ] Secrets stored in secure secret manager (Vault, AWS Secrets Manager)
- [ ] HTTPS enabled with valid certificates
- [ ] Redis uses SSL/TLS
- [ ] Database backed up regularly
- [ ] Metrics and monitoring enabled
- [ ] Log aggregation configured
- [ ] Rate limiting enabled

---

## Docker Configuration

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - HANDSFREE_AUTH_MODE=${HANDSFREE_AUTH_MODE:-dev}
      - REDIS_HOST=redis
      - DUCKDB_PATH=/app/data/handsfree.db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    env_file:
      - .env
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
    command: redis-server --appendonly yes

volumes:
  handsfree-data:
  redis-data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY pyproject.toml .

# Install package
RUN pip install -e .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/v1/status || exit 1

# Run server
CMD ["uvicorn", "handsfree.api:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Running with Docker

```bash
# Build image
docker build -t handsfree-api .

# Run with environment file
docker run -d \
  --name handsfree-api \
  -p 8080:8080 \
  --env-file .env \
  -v handsfree-data:/app/data \
  handsfree-api

# Or use docker compose
docker compose up -d

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

---

## Troubleshooting Configuration Issues

### Backend Won't Start

**Symptom**: Server crashes on startup

**Check**:

1. **Environment variables are loaded**:
   ```bash
   printenv | grep HANDSFREE
   ```

2. **Python version is 3.11+**:
   ```bash
   python --version
   ```

3. **Dependencies are installed**:
   ```bash
   pip list | grep fastapi
   ```

4. **Redis is accessible** (if enabled):
   ```bash
   redis-cli ping  # Should return PONG
   ```

### Mobile App Can't Connect

**Symptom**: "Connection failed" in Status screen

**Check**:

1. **Backend URL is correct**:
   - iOS Simulator: `http://localhost:8080`
   - Android Emulator: `http://10.0.2.2:8080`
   - Physical Device: `http://YOUR_COMPUTER_IP:8080`

2. **Backend is accessible from device**:
   ```bash
   # From device, try:
   curl http://YOUR_BACKEND_IP:8080/v1/status
   ```

3. **Firewall allows connections**:
   ```bash
   # macOS
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps
   
   # Linux
   sudo ufw status
   ```

4. **Backend binds to 0.0.0.0** (not 127.0.0.1):
   ```bash
   uvicorn handsfree.api:app --host 0.0.0.0 --port 8080
   ```

### API Keys Not Working

**Symptom**: 401 Unauthorized with API key auth

**Check**:

1. **Auth mode is set to api_key**:
   ```bash
   echo $HANDSFREE_AUTH_MODE  # Should be "api_key"
   ```

2. **API key exists in database**:
   ```bash
   python scripts/manage_api_keys.py list USER_ID
   ```

3. **Key is not revoked**:
   - Check `active` and `revoked_at` columns

4. **Authorization header is correct**:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8080/v1/command
   ```

### TTS/STT Not Working

**Symptom**: Stub responses or errors

**Check**:

1. **Provider is set correctly**:
   ```bash
   echo $HANDSFREE_TTS_PROVIDER  # Should be "openai" for realistic audio
   ```

2. **API key is valid**:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   # Should return list of models
   ```

3. **Check backend logs** for API errors

### GitHub Integration Not Working

**Symptom**: Empty inbox or errors

**Check**:

1. **Live mode is enabled**:
   ```bash
   echo $GITHUB_LIVE_MODE  # Should be "true"
   ```

2. **Token has correct scopes**:
   - Visit https://github.com/settings/tokens
   - Verify token has `repo` and `read:org` scopes

3. **Token is not expired**:
   ```bash
   curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
   # Should return your user info
   ```

4. **Rate limit not exceeded**:
   ```bash
   curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/rate_limit
   ```

---

## Configuration Examples

### Minimal Development Setup

```bash
# .env
HANDSFREE_AUTH_MODE=dev
HANDSFREE_TTS_PROVIDER=stub
HANDS_FREE_STT_PROVIDER=stub
GITHUB_LIVE_MODE=false
REDIS_ENABLED=true
REDIS_HOST=localhost
```

### Realistic Testing Setup

```bash
# .env
HANDSFREE_AUTH_MODE=dev
HANDSFREE_TTS_PROVIDER=openai
HANDS_FREE_STT_PROVIDER=openai
OPENAI_API_KEY=sk-...
GITHUB_LIVE_MODE=true
GITHUB_TOKEN=ghp_...
REDIS_ENABLED=true
REDIS_HOST=localhost
```

### Production Setup

```bash
# .env (managed by secret manager, not committed to git)
HANDSFREE_AUTH_MODE=api_key
HANDSFREE_TTS_PROVIDER=openai
HANDS_FREE_STT_PROVIDER=openai
OPENAI_API_KEY=${SECRET_OPENAI_API_KEY}
GITHUB_LIVE_MODE=true
GITHUB_TOKEN=${SECRET_GITHUB_TOKEN}
REDIS_ENABLED=true
REDIS_HOST=redis-prod.example.com
REDIS_PORT=6380
REDIS_PASSWORD=${SECRET_REDIS_PASSWORD}
REDIS_SSL=true
HANDSFREE_ENABLE_METRICS=true
LOG_LEVEL=warning
```

---

## Additional Resources

- **[Getting Started Guide](GETTING_STARTED.md)** - Full setup instructions
- **[Architecture Documentation](ARCHITECTURE.md)** - System design
- **[Authentication Guide](docs/AUTHENTICATION.md)** - Detailed auth documentation
- **[Agent Runner Setup](docs/agent-runner-setup.md)** - Agent delegation
- **[Secret Management](docs/SECRET_STORAGE_AND_SESSIONS.md)** - Vault and secret storage

---

**Configuration Guide Version**: 1.0  
**Last Updated**: 2026-01-20
