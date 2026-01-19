# Authentication System

The HandsFree Dev Companion API supports multiple authentication modes to enable both local development/testing and production deployment.

## Configuration

Authentication is configured via the `HANDSFREE_AUTH_MODE` environment variable:

```bash
# Development mode (default) - allows X-User-Id header fallback
export HANDSFREE_AUTH_MODE=dev

# JWT mode - requires valid JWT bearer tokens
export HANDSFREE_AUTH_MODE=jwt
export JWT_SECRET_KEY=your-secret-key-here
export JWT_ALGORITHM=HS256  # Optional, defaults to HS256

# API Key mode - requires valid API keys
export HANDSFREE_AUTH_MODE=api_key
```

## Authentication Modes

### Dev Mode (Default)

Development mode is designed for local testing and development. It allows flexible authentication:

- **X-User-Id header**: If provided, the API uses this user ID (must be valid UUID)
- **No authentication**: Falls back to fixture user ID (`00000000-0000-0000-0000-000000000001`)

**Example:**
```bash
# With header
curl -X POST http://localhost:8080/v1/command \
  -H "X-User-Id: 12345678-1234-1234-1234-123456789012" \
  -H "Content-Type: application/json" \
  -d '{"input": {"type": "text", "text": "inbox"}, "profile": "default", "client_context": {"device": "test", "locale": "en-US", "timezone": "UTC", "app_version": "0.1.0"}}'

# Without header (uses fixture user)
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{"input": {"type": "text", "text": "inbox"}, "profile": "default", "client_context": {"device": "test", "locale": "en-US", "timezone": "UTC", "app_version": "0.1.0"}}'
```

### JWT Mode

JWT (JSON Web Token) mode is for production deployments. It requires valid JWT tokens with user identification.

**Requirements:**
- `JWT_SECRET_KEY` environment variable must be set
- Tokens must include one of: `user_id`, `sub` (subject), or `uid` claim
- User ID must be a valid UUID
- Tokens are validated for signature and expiration

**Example:**
```python
import jwt
from datetime import datetime, timedelta, UTC

# Create a JWT token
user_id = "12345678-1234-1234-1234-123456789012"
secret_key = "your-secret-key"

payload = {
    "user_id": user_id,
    "iat": datetime.now(UTC),
    "exp": datetime.now(UTC) + timedelta(hours=1)
}

token = jwt.encode(payload, secret_key, algorithm="HS256")
```

**Using the token:**
```bash
curl -X POST http://localhost:8080/v1/command \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"input": {"type": "text", "text": "inbox"}, "profile": "default", "client_context": {"device": "test", "locale": "en-US", "timezone": "UTC", "app_version": "0.1.0"}}'
```

**Error responses:**
- `401 Unauthorized`: Missing or invalid token
- `401 Unauthorized`: Token expired
- `401 Unauthorized`: Token missing user identifier
- `500 Internal Server Error`: JWT_SECRET_KEY not configured

### API Key Mode

API key authentication allows machine-to-machine communication using API keys managed through the admin endpoints.

**Requirements:**
- API keys must be created via the admin API endpoints (`/v1/admin/api-keys`)
- Keys are sent in the `Authorization: Bearer <api_key>` header
- Keys are validated against the database and checked for revocation
- Each key is associated with a specific user_id

**Creating an API Key:**
```bash
# Using the admin endpoint (requires appropriate authorization)
curl -X POST http://localhost:8080/v1/admin/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "12345678-1234-1234-1234-123456789012",
    "label": "Production API key"
  }'
```

**Using an API Key:**
```bash
curl -X POST http://localhost:8080/v1/command \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"input": {"type": "text", "text": "inbox"}, "profile": "default", "client_context": {"device": "test", "locale": "en-US", "timezone": "UTC", "app_version": "0.1.0"}}'
```

**Error responses:**
- `401 Unauthorized`: Missing API key
- `401 Unauthorized`: Invalid API key
- `401 Unauthorized`: Revoked API key

**Security Features:**
- API keys are stored as SHA256 hashes, never in plaintext
- Keys can be revoked without deletion (maintains audit trail)
- Each key tracks last_used_at timestamp
- Keys are scoped to a specific user_id

## Supported JWT Claims

The authentication system looks for user identification in the following JWT claims (in order of priority):

1. `user_id` - Preferred claim name
2. `sub` (subject) - Standard JWT claim for user identifier
3. `uid` - Alternative user identifier claim

All claims must contain a valid UUID string.

## Protected Endpoints

All endpoints that read or write user data are protected by authentication:

- `POST /v1/command` - Submit voice/text commands
- `POST /v1/commands/confirm` - Confirm pending actions
- `POST /v1/actions/request-review` - Request PR reviews
- `POST /v1/github/connections` - Create GitHub connections
- `GET /v1/github/connections` - List GitHub connections
- `GET /v1/github/connections/{id}` - Get specific connection
- `GET /v1/notifications` - Get user notifications

## Testing

The authentication system includes comprehensive tests:

### Unit Tests (`tests/test_auth.py`)
- 24 tests covering auth mode detection, JWT validation, API key validation, and dependency behavior
- Tests for all three authentication modes: dev, jwt, and api_key

### Integration Tests (`tests/test_auth_integration.py`)
- 23 tests covering real API calls in dev, JWT, and API key modes
- Tests user isolation and data segregation across all modes
- Tests API key revocation and validation

### Database Tests (`tests/test_api_keys.py`)
- 25 tests covering API key generation, storage, validation, and management
- Tests secure hashing, revocation, and user isolation

### Existing Tests
- All existing tests continue to pass with dev mode (default)
- No breaking changes to existing functionality

**Run tests:**
```bash
# All auth tests
pytest tests/test_auth.py tests/test_auth_integration.py tests/test_api_keys.py -v

# Specific test class
pytest tests/test_auth.py::TestJWTValidation -v

# Integration tests only
pytest tests/test_auth_integration.py -v

# API key tests only
pytest tests/test_api_keys.py -v
```

## Migration Guide

### For Developers

No changes needed! Dev mode is the default and maintains backward compatibility with the X-User-Id header.

### For Production Deployments

1. Set `HANDSFREE_AUTH_MODE=jwt`
2. Set `JWT_SECRET_KEY` to a secure secret (e.g., 256-bit random string)
3. Optionally set `JWT_ALGORITHM` (defaults to HS256)
4. Update your JWT token issuer to include `user_id` claim with UUID
5. Update API clients to send `Authorization: Bearer <token>` header

### Token Generation Example

```python
import jwt
import uuid
from datetime import datetime, timedelta, UTC

def create_user_token(user_id: str, secret_key: str, expires_hours: int = 24) -> str:
    """Create a JWT token for a user."""
    payload = {
        "user_id": user_id,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=expires_hours)
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")

# Usage
user_id = str(uuid.uuid4())
secret = "your-production-secret-key"
token = create_user_token(user_id, secret)
```

## Security Considerations

1. **JWT_SECRET_KEY**: Use a strong, randomly generated secret in production
2. **Token expiration**: Set reasonable expiration times (e.g., 1-24 hours)
3. **HTTPS only**: Always use HTTPS in production to protect tokens in transit
4. **Token rotation**: Implement token refresh mechanisms for long-lived sessions
5. **Secret management**: Never commit secrets to source control; use environment variables or secret management services

## Future Enhancements

- **OAuth2/OIDC**: Support for third-party identity providers
- **Token refresh**: Automatic token renewal mechanisms for JWT mode
- **Rate limiting**: Per-user rate limits based on authentication
- **Audit logging**: Enhanced logging of authentication events
- **API key rotation**: Automatic key rotation policies
- **X-API-Key header**: Optional support for X-API-Key header as alternative to Bearer token
