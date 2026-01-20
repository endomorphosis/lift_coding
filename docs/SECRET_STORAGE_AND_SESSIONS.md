# Secret Storage and Session Token Management

This document explains the production-ready abstractions for secret storage and session token management in the HandsFree Dev Companion.

## Overview

The system provides two key abstractions:

1. **SecretManager** - For storing and retrieving secrets (like GitHub tokens) from various backends
2. **SessionTokenManager** - For managing short-lived session tokens for mobile and wearable clients

## Secret Management

### Architecture

The secret management system uses a pluggable architecture that allows different storage backends while maintaining a consistent API.

```
┌─────────────────────────────────────┐
│  Application Code                   │
│  (uses token_ref from database)     │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  SecretManager Interface            │
│  - store_secret()                   │
│  - get_secret()                     │
│  - update_secret()                  │
│  - delete_secret()                  │
└───────────────┬─────────────────────┘
                │
    ┌───────────┴───────────┬─────────────┬──────────────┐
    ▼                       ▼             ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ EnvSecret    │  │ VaultSecret  │  │ AWSSecret    │  │ GCPSecret    │
│ Manager      │  │ Manager      │  │ Manager      │  │ Manager      │
│ (dev/test)   │  │ (production) │  │ (production) │  │ (production) │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

### Security Model

- **Database stores only references** - The `github_connections.token_ref` field stores a reference (e.g., `env://HANDSFREE_SECRET_GITHUB_TOKEN_USER_123`), not the actual token
- **Secrets retrieved on-demand** - Tokens are fetched from the secret manager when needed, never cached in the application database
- **Backend-specific encryption** - Each backend (AWS Secrets Manager, Vault, etc.) handles encryption at rest
- **No logging of secrets** - Secret values are never logged

### Usage

#### Basic Usage

```python
from handsfree.secrets import get_default_secret_manager

# Get the configured secret manager
secret_manager = get_default_secret_manager()

# Store a secret (e.g., GitHub token)
token_ref = secret_manager.store_secret(
    key="github_token_user_123",
    value="ghp_xxxxxxxxxxxxxxxxxxxx",
    metadata={"scopes": "repo,user", "expires_at": "2026-12-31"}
)
# Returns: "env://HANDSFREE_SECRET_GITHUB_TOKEN_USER_123"

# Store the reference in the database
create_github_connection(
    conn=db_conn,
    user_id="user-123",
    token_ref=token_ref,  # Store the reference, not the token!
    scopes="repo,user"
)

# Later, retrieve the secret when needed
connection = get_github_connection(db_conn, connection_id)
if connection.token_ref:
    actual_token = secret_manager.get_secret(connection.token_ref)
    # Use actual_token to make GitHub API calls
```

#### Integration with GitHub Connections

```python
from handsfree.db import init_db
from handsfree.db.github_connections import create_github_connection
from handsfree.secrets import get_default_secret_manager

# Initialize
db = init_db()
secret_manager = get_default_secret_manager()

# User completes OAuth flow, we receive their token
github_token = "ghp_xxxxxxxxxxxxxxxxxxxx"
user_id = "user-123"

# Store the token securely
token_ref = secret_manager.store_secret(
    key=f"github_token_{user_id}",
    value=github_token,
    metadata={"source": "oauth", "scopes": "repo,user"}
)

# Store only the reference in the database
connection = create_github_connection(
    conn=db,
    user_id=user_id,
    token_ref=token_ref,
    scopes="repo,user"
)

# When making GitHub API calls, retrieve the token
actual_token = secret_manager.get_secret(connection.token_ref)
```

### Configuration

Set the `SECRET_MANAGER_TYPE` environment variable to choose the backend:

```bash
# Development (default) - stores secrets as environment variables
export SECRET_MANAGER_TYPE=env

# Production - AWS Secrets Manager (NOT YET IMPLEMENTED - see documentation below for planned specification)
export SECRET_MANAGER_TYPE=aws
export AWS_REGION=us-east-1
# Option 1: IAM role authentication (recommended for EC2/ECS/Lambda)
# Uses the instance/task IAM role automatically - no additional env vars needed
# Option 2: Access key authentication (development/testing)
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
# Optional configuration
export AWS_SECRETS_MANAGER_ENDPOINT=https://secretsmanager.us-east-1.amazonaws.com  # Custom endpoint

# Production - HashiCorp Vault
export SECRET_MANAGER_TYPE=vault
export VAULT_ADDR=https://vault.example.com:8200
# Option 1: Token authentication (development/testing)
export VAULT_TOKEN=s.xxxxxx
# Option 2: AppRole authentication (production, recommended)
export VAULT_ROLE_ID=your-role-id
export VAULT_SECRET_ID=your-secret-id
# Optional configuration
export VAULT_MOUNT=secret  # KV mount point (default: secret)
export VAULT_NAMESPACE=your-namespace  # For Vault Enterprise

# Production - Google Secret Manager (NOT YET IMPLEMENTED - see documentation below for planned specification)
export SECRET_MANAGER_TYPE=gcp
export GCP_PROJECT_ID=my-project
# Option 1: Application Default Credentials (recommended for GCE/GKE/Cloud Run)
# Uses the instance/pod service account automatically - no additional env vars needed
# Option 2: Service account key authentication (development/testing)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
# Optional configuration
export GCP_SECRET_MANAGER_ENDPOINT=https://secretmanager.googleapis.com  # Custom endpoint
```

#### HashiCorp Vault Configuration

The VaultSecretManager provides production-ready secret storage with the following features:

**Security Features:**
- Encryption at rest (handled by Vault)
- Access audit logging (handled by Vault)
- Token-based or AppRole authentication
- TLS/HTTPS communication
- Support for Vault namespaces (Enterprise)

**Required Configuration:**
- `VAULT_ADDR`: Vault server address (e.g., `https://vault.example.com:8200`)
- Authentication (choose one):
  - `VAULT_TOKEN`: Direct token authentication (development/testing)
  - `VAULT_ROLE_ID` + `VAULT_SECRET_ID`: AppRole authentication (production, recommended)

**Optional Configuration:**
- `VAULT_MOUNT`: KV secrets engine mount point (default: `secret`)
- `VAULT_NAMESPACE`: Vault namespace for Enterprise installations

**Reference Format:**
Secrets are stored with references in the format `vault://secret_key`. For example:
```python
token_ref = secret_manager.store_secret("github_token_user_123", "ghp_xxxx")
# Returns: "vault://github_token_user_123"
```

**Setup Example:**

1. Start Vault (development mode for testing):
```bash
vault server -dev -dev-root-token-id=root
```

2. Configure environment:
```bash
export SECRET_MANAGER_TYPE=vault
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=root
```

3. Use in code:
```python
from handsfree.secrets import get_default_secret_manager

secret_manager = get_default_secret_manager()
token_ref = secret_manager.store_secret("my_secret", "secret_value")
# Stores in Vault and returns "vault://my_secret"

retrieved = secret_manager.get_secret(token_ref)
# Retrieves "secret_value" from Vault
```

**Production Setup with AppRole:**

1. Enable AppRole authentication in Vault:
```bash
vault auth enable approle
vault write auth/approle/role/handsfree-app \
    token_policies="handsfree-policy" \
    token_ttl=1h \
    token_max_ttl=4h
```

2. Get credentials:
```bash
vault read auth/approle/role/handsfree-app/role-id
vault write -f auth/approle/role/handsfree-app/secret-id
```

3. Configure application:
```bash
export SECRET_MANAGER_TYPE=vault
export VAULT_ADDR=https://vault.example.com:8200
export VAULT_ROLE_ID=<role-id-from-step-2>
export VAULT_SECRET_ID=<secret-id-from-step-2>
```

**Error Handling:**

The VaultSecretManager provides fail-fast error handling with clear messages:
- Missing `VAULT_ADDR`: Raises `ValueError` with clear message
- Missing authentication credentials: Raises `ValueError` explaining required variables
- Authentication failure: Raises `VaultError` with connection details
- Network issues: Raises `VaultError` with underlying error

#### AWS Secrets Manager Configuration

> ⚠️ **WARNING: Not Yet Implemented** - The AWS Secrets Manager backend is not yet implemented. Setting `SECRET_MANAGER_TYPE=aws` currently raises `NotImplementedError`. The documentation in this section is provided as a specification for the planned implementation.

The AWSSecretManager provides production-ready secret storage with the following features:

**Security Features:**
- Encryption at rest with AWS KMS (handled by AWS)
- Automatic secret rotation support (configurable)
- Fine-grained IAM access control
- Audit logging via AWS CloudTrail
- VPC endpoint support for private networks
- Automatic versioning of secrets

**Required Configuration:**
- `AWS_REGION`: AWS region (e.g., `us-east-1`, `eu-west-1`)
- Authentication (choose one):
  - IAM role authentication (recommended): Automatically uses EC2 instance role, ECS task role, or Lambda execution role
  - Access key authentication: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (development/testing)

**Optional Configuration:**
- `AWS_SECRETS_MANAGER_ENDPOINT`: Custom endpoint URL (for VPC endpoints or LocalStack testing)
- `AWS_SESSION_TOKEN`: Session token for temporary credentials

**Reference Format:**
Secrets are stored with references in the format `aws://secret_name`. For example:
```python
token_ref = secret_manager.store_secret("github_token_user_123", "ghp_xxxx")
# Returns: "aws://github_token_user_123"
```

**Setup Example:**

1. Configure IAM permissions (production, recommended):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:CreateSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:DeleteSecret",
        "secretsmanager:ListSecrets"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:handsfree/*"
    }
  ]
}
```

2. Configure environment (using IAM role):
```bash
export SECRET_MANAGER_TYPE=aws
export AWS_REGION=us-east-1
# IAM role is used automatically - no credentials needed
```

3. Or configure with access keys (development/testing):
```bash
export SECRET_MANAGER_TYPE=aws
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

4. Use in code:
```python
from handsfree.secrets import get_default_secret_manager

secret_manager = get_default_secret_manager()
token_ref = secret_manager.store_secret("my_secret", "secret_value")
# Stores in AWS Secrets Manager and returns "aws://my_secret"

retrieved = secret_manager.get_secret(token_ref)
# Retrieves "secret_value" from AWS Secrets Manager
```

**Production Setup with IAM Role:**

1. Create IAM policy and attach to your service role:
```bash
aws iam create-policy \
    --policy-name HandsfreeSecretsPolicy \
    --policy-document file://policy.json

aws iam attach-role-policy \
    --role-name YourServiceRole \
    --policy-arn arn:aws:iam::ACCOUNT_ID:policy/HandsfreeSecretsPolicy
```

2. Deploy application with the service role attached (EC2, ECS, Lambda, etc.)

3. Application automatically uses the attached IAM role for authentication

**Using with VPC Endpoints (enhanced security):**

```bash
export SECRET_MANAGER_TYPE=aws
export AWS_REGION=us-east-1
export AWS_SECRETS_MANAGER_ENDPOINT=https://vpce-xxxxx-yyyyy.secretsmanager.us-east-1.vpce.amazonaws.com
```

**Error Handling:**

The AWSSecretManager provides clear error handling:
- Missing `AWS_REGION`: Raises `ValueError` with clear message
- Authentication failure: Raises `ClientError` with AWS error details
- Secret not found: Returns `None` from `get_secret()`
- Permission denied: Raises `ClientError` with IAM policy requirements
- Network issues: Raises `EndpointConnectionError` with connection details

#### Google Secret Manager Configuration

> ⚠️ **WARNING: Not Yet Implemented**  
> The Google Secret Manager backend is not yet implemented. Setting `SECRET_MANAGER_TYPE=gcp` currently raises `NotImplementedError`. The documentation below is provided as a specification for the planned implementation.

The GCPSecretManager provides production-ready secret storage with the following features:

**Security Features:**
- Encryption at rest (handled by Google Cloud)
- Automatic secret replication across regions
- Fine-grained IAM access control
- Audit logging via Cloud Audit Logs
- Secret versioning with automatic cleanup
- Customer-managed encryption keys (CMEK) support

**Required Configuration:**
- `GCP_PROJECT_ID`: Google Cloud project ID (e.g., `my-project-123`)
- Authentication (choose one):
  - Application Default Credentials (recommended): Automatically uses Compute Engine service account, GKE Workload Identity, or Cloud Run service identity
  - Service account key: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json` (development/testing)

**Optional Configuration:**
- `GCP_SECRET_MANAGER_ENDPOINT`: Custom endpoint URL (for testing or private service connect)

**Reference Format:**
Secrets are stored with references in the format `gcp://secret_name`. For example:
```python
token_ref = secret_manager.store_secret("github_token_user_123", "ghp_xxxx")
# Returns: "gcp://github_token_user_123"
```

**Setup Example:**

1. Configure IAM permissions (production, recommended):
```bash
# Grant Secret Manager Admin role to your service account
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.admin"

# Or use more granular roles:
# - roles/secretmanager.secretAccessor (read secrets)
# - roles/secretmanager.secretVersionManager (create/update secrets)
```

2. Configure environment (using Application Default Credentials):
```bash
export SECRET_MANAGER_TYPE=gcp
export GCP_PROJECT_ID=my-project-123
# Application Default Credentials are used automatically
```

3. Or configure with service account key (development/testing):
```bash
export SECRET_MANAGER_TYPE=gcp
export GCP_PROJECT_ID=my-project-123
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

4. Use in code:
```python
from handsfree.secrets import get_default_secret_manager

secret_manager = get_default_secret_manager()
token_ref = secret_manager.store_secret("my_secret", "secret_value")
# Stores in Google Secret Manager and returns "gcp://my_secret"

retrieved = secret_manager.get_secret(token_ref)
# Retrieves "secret_value" from Google Secret Manager
```

**Production Setup with Workload Identity (GKE):**

1. Enable Workload Identity on your GKE cluster:
```bash
gcloud container clusters update CLUSTER_NAME \
    --workload-pool=PROJECT_ID.svc.id.goog
```

2. Create Kubernetes service account and bind to GCP service account:
```bash
kubectl create serviceaccount handsfree-app

gcloud iam service-accounts add-iam-policy-binding \
    SERVICE_ACCOUNT_EMAIL \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/handsfree-app]"

kubectl annotate serviceaccount handsfree-app \
    iam.gke.io/gcp-service-account=SERVICE_ACCOUNT_EMAIL
```

3. Deploy application using the Kubernetes service account

**Using with Private Service Connect:**

```bash
export SECRET_MANAGER_TYPE=gcp
export GCP_PROJECT_ID=my-project-123
export GCP_SECRET_MANAGER_ENDPOINT=https://your-private-endpoint.p.googleapis.com
```

**Error Handling:**

The GCPSecretManager provides clear error handling:
- Missing `GCP_PROJECT_ID`: Raises `ValueError` with clear message
- Authentication failure: Raises `DefaultCredentialsError` with credential details
- Secret not found: Returns `None` from `get_secret()`
- Permission denied: Raises `PermissionDenied` with required IAM roles
- Network issues: Raises connection errors with details

### Implementing New Backends

To add support for a new secret manager (e.g., Azure Key Vault):

1. Create a new file `src/handsfree/secrets/azure_secrets.py`
2. Implement the `SecretManager` interface
3. Update `factory.py` to support the new backend

Example skeleton:

```python
from .interface import SecretManager

class AzureSecretManager(SecretManager):
    def __init__(self):
        # Initialize Azure client
        pass
    
    def store_secret(self, key: str, value: str, metadata: dict | None = None) -> str:
        # Store in Azure Key Vault
        # Return reference like "azure://vault-name/secret-name"
        pass
    
    def get_secret(self, reference: str) -> str | None:
        # Parse reference and retrieve from Azure
        pass
    
    # ... implement other methods
```

## Session Token Management

### Architecture

Session tokens enable mobile and wearable clients to authenticate without sending long-lived credentials with every request.

```
┌─────────────────────────────────────┐
│  Mobile/Wearable Client             │
│  (stores session token locally)     │
└───────────────┬─────────────────────┘
                │ Bearer: session_token
                ▼
┌─────────────────────────────────────┐
│  API Endpoint                       │
│  (validates session token)          │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  SessionTokenManager                │
│  (Redis-backed storage)             │
└─────────────────────────────────────┘
```

### Security Features

- **Cryptographically secure tokens** - Uses Python's `secrets` module (256 bits of entropy)
- **Hashed storage** - Tokens are hashed (SHA-256) before storage in Redis
- **Short-lived** - Default 24-hour expiration, configurable
- **Automatic expiration** - Redis handles automatic cleanup
- **Device tracking** - Sessions tied to specific devices for audit
- **Bulk revocation** - Revoke all sessions for a user or device

### Usage

#### Creating Sessions

```python
import redis
from handsfree.sessions import SessionTokenManager

# Initialize Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Create session manager
session_manager = SessionTokenManager(
    redis_client=redis_client,
    default_ttl_hours=24,  # 24-hour sessions
    key_prefix="session:"
)

# Create a new session for a user
session = session_manager.create_session(
    user_id="user-123",
    device_id="wearable-456",
    ttl_hours=24,  # Optional, uses default if not specified
    metadata={
        "device_type": "wearable",
        "app_version": "1.0.0",
        "os": "Android"
    }
)

# Return the token to the client
# Client stores this and sends it with subsequent requests
return {
    "session_token": session.token,
    "expires_at": session.expires_at.isoformat()
}
```

#### Validating Sessions

```python
from fastapi import Header, HTTPException

async def get_current_user_from_session(
    authorization: str | None = Header(default=None)
) -> str:
    """Validate session token and return user_id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing session token")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Validate the session
    session = session_manager.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return session.user_id

# Use in endpoints
@app.get("/v1/inbox")
async def get_inbox(user_id: str = Depends(get_current_user_from_session)):
    # user_id is now authenticated via session token
    return get_user_inbox(user_id)
```

#### Session Lifecycle Management

```python
# Revoke a specific session (logout)
success = session_manager.revoke_session(token)

# Revoke all sessions for a user (logout all devices)
count = session_manager.revoke_user_sessions(user_id="user-123")

# Revoke all sessions for a device (device lost/stolen)
count = session_manager.revoke_device_sessions(device_id="wearable-456")

# Extend a session (e.g., user activity detected)
success = session_manager.extend_session(token, additional_hours=24)
```

### API Integration Example

```python
from fastapi import FastAPI, Depends, Header, HTTPException
import redis
from handsfree.sessions import SessionTokenManager

app = FastAPI()

# Initialize session manager
redis_client = redis.Redis(host='localhost', port=6379, db=0)
session_manager = SessionTokenManager(redis_client)

# Dependency for session validation
async def validate_session_token(
    authorization: str | None = Header(default=None)
) -> str:
    """Validate session token and return user_id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = authorization[7:]
    session = session_manager.validate_session(token)
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return session.user_id

# Login endpoint - creates session
@app.post("/v1/auth/login")
async def login(credentials: LoginCredentials):
    # Validate credentials (OAuth, password, etc.)
    user_id = validate_user_credentials(credentials)
    
    # Create session
    session = session_manager.create_session(
        user_id=user_id,
        device_id=credentials.device_id,
        metadata={
            "device_type": credentials.device_type,
            "login_method": "oauth"
        }
    )
    
    return {
        "session_token": session.token,
        "expires_at": session.expires_at.isoformat()
    }

# Protected endpoint - requires session
@app.get("/v1/inbox")
async def get_inbox(user_id: str = Depends(validate_session_token)):
    return {"inbox": get_user_inbox(user_id)}

# Logout endpoint - revokes session
@app.post("/v1/auth/logout")
async def logout(
    user_id: str = Depends(validate_session_token),
    authorization: str = Header()
):
    token = authorization[7:]
    session_manager.revoke_session(token)
    return {"message": "Logged out successfully"}

# Logout all devices
@app.post("/v1/auth/logout-all")
async def logout_all(user_id: str = Depends(validate_session_token)):
    count = session_manager.revoke_user_sessions(user_id)
    return {"message": f"Logged out from {count} device(s)"}
```

## Testing

### Running Tests

```bash
# Run secret management tests
make test tests/test_secrets.py

# Run session token tests (requires Redis)
make compose-up  # Start Redis
make test tests/test_sessions.py

# Run all tests
make test
```

### Test Coverage

- **Secret Management**: 14 tests covering all operations and edge cases
- **Session Tokens**: 19 tests covering creation, validation, revocation, and edge cases

## Best Practices

### Secret Management

1. **Never log secrets** - Use the logging utilities that automatically redact secrets
2. **Store only references** - Never store actual tokens in the application database
3. **Use production backends** - EnvSecretManager is for development only
4. **Rotate secrets** - Implement regular token rotation for security
5. **Audit access** - Log when secrets are retrieved (but not the values)

### Session Tokens

1. **Use HTTPS** - Always transmit session tokens over HTTPS
2. **Short TTL** - Keep session lifetimes reasonable (24 hours default)
3. **Rotate on security events** - Revoke all sessions on password change
4. **Device tracking** - Use device IDs for security audit
5. **Monitor suspicious activity** - Track failed validation attempts

## Troubleshooting

### Secret Manager Issues

**Problem**: `SecretManager not found` error

**Solution**: Ensure you've installed the package and imported correctly:
```python
from handsfree.secrets import get_default_secret_manager
```

**Problem**: Secrets not persisting after restart

**Solution**: EnvSecretManager stores secrets in environment variables, which don't persist. Use a production backend (AWS Secrets Manager, Vault, etc.) for persistent storage.

### Session Token Issues

**Problem**: Sessions expiring too quickly

**Solution**: Increase the TTL:
```python
session_manager = SessionTokenManager(redis_client, default_ttl_hours=48)
```

**Problem**: Redis connection failed

**Solution**: Ensure Redis is running:
```bash
make compose-up
# Or manually: docker run -d -p 6379:6379 redis:latest
```

**Problem**: Sessions not auto-expiring

**Solution**: Verify Redis is configured correctly and the TTL is being set. Check Redis:
```bash
redis-cli
> KEYS session:*
> TTL session:xxx...
```

## Future Enhancements

### Secret Management
- [ ] AWS Secrets Manager backend (documentation complete, implementation pending)
- [x] HashiCorp Vault backend (completed)
- [ ] Google Cloud Secret Manager backend (documentation complete, implementation pending)
- [ ] Azure Key Vault backend
- [ ] Automatic secret rotation
- [ ] Secret versioning
- [ ] Access audit logging

### Session Tokens
- [ ] Refresh token support
- [ ] Rate limiting per session
- [ ] Geolocation tracking
- [ ] Anomaly detection
- [ ] Session analytics dashboard
- [ ] Multi-device session management UI

## Security Considerations

### Threat Model

1. **Token theft** - Mitigated by short TTL and token hashing
2. **Redis compromise** - Tokens are hashed, not stored in plaintext
3. **Secret exposure** - Secrets never logged or stored in application DB
4. **Replay attacks** - Sessions expire automatically
5. **Device theft** - Can revoke device sessions remotely

### Security Checklist

- [x] Tokens use cryptographically secure random generation
- [x] Tokens are hashed before storage
- [x] Short-lived sessions with automatic expiration
- [x] Secrets never logged or exposed in error messages
- [x] Database stores only references, not actual secrets
- [x] Comprehensive test coverage
- [x] Device tracking for audit
- [x] Bulk revocation capabilities

## Contributing

When adding new secret manager backends or enhancing the session system:

1. Implement the appropriate interface (`SecretManager` or similar)
2. Add comprehensive tests
3. Update this documentation
4. Ensure security review
5. Update the factory to support the new backend

## References

- [OWASP Session Management Cheat Sheet](https://cheatsheetsproject.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [NIST Digital Identity Guidelines](https://pages.nist.gov/800-63-3/)
- Implementation: `src/handsfree/secrets/` and `src/handsfree/sessions.py`
- Tests: `tests/test_secrets.py` and `tests/test_sessions.py`
