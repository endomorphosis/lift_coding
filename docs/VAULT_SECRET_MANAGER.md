# HashiCorp Vault Secret Manager

This document provides detailed information about the `VaultSecretManager` implementation for production-ready secret storage.

## Overview

The `VaultSecretManager` provides secure, production-ready secret storage using HashiCorp Vault. It implements the `SecretManager` interface and supports both token-based authentication (for development) and AppRole authentication (recommended for production).

## Features

- ✅ **Encryption at rest** - Handled by Vault's backend storage
- ✅ **Access audit logging** - Comprehensive audit trail maintained by Vault
- ✅ **Multiple authentication methods** - Token and AppRole support
- ✅ **TLS/HTTPS communication** - Secure transport to Vault server
- ✅ **Namespace support** - Full support for Vault Enterprise namespaces
- ✅ **Fail-fast validation** - Clear error messages for configuration issues
- ✅ **Reference-based storage** - Secrets stored with `vault://` references
- ✅ **Comprehensive error handling** - Detailed logging and error reporting

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_MANAGER_TYPE` | Yes | `env` | Set to `vault` to use VaultSecretManager |
| `VAULT_ADDR` | Yes | - | Vault server address (e.g., `https://vault.example.com:8200`) |
| `VAULT_TOKEN` | Conditional* | - | Direct token for authentication (development/testing) |
| `VAULT_ROLE_ID` | Conditional* | - | AppRole role ID (production, recommended) |
| `VAULT_SECRET_ID` | Conditional* | - | AppRole secret ID (production, recommended) |
| `VAULT_MOUNT` | No | `secret` | KV secrets engine mount point |
| `VAULT_NAMESPACE` | No | - | Vault namespace (Vault Enterprise only) |

\* Either `VAULT_TOKEN` OR both `VAULT_ROLE_ID` and `VAULT_SECRET_ID` must be provided.

### Basic Configuration

```bash
# For development/testing (token authentication)
export SECRET_MANAGER_TYPE=vault
export VAULT_ADDR=https://vault.example.com:8200
export VAULT_TOKEN=s.xxxxxxxxxxxxxx

# For production (AppRole authentication - recommended)
export SECRET_MANAGER_TYPE=vault
export VAULT_ADDR=https://vault.example.com:8200
export VAULT_ROLE_ID=your-role-id
export VAULT_SECRET_ID=your-secret-id

# Optional: Custom mount point
export VAULT_MOUNT=my-secrets

# Optional: Vault Enterprise namespace
export VAULT_NAMESPACE=my-namespace
```

## Usage

### Basic Usage

```python
from handsfree.secrets import get_default_secret_manager

# Get the configured secret manager (automatically uses Vault if configured)
secret_manager = get_default_secret_manager()

# Store a secret
token_ref = secret_manager.store_secret(
    key="github_token_user_123",
    value="ghp_xxxxxxxxxxxxxxxxxxxx",
    metadata={"scopes": "repo,user", "expires_at": "2026-12-31"}
)
# Returns: "vault://github_token_user_123"

# Retrieve a secret
actual_token = secret_manager.get_secret(token_ref)
# Returns: "ghp_xxxxxxxxxxxxxxxxxxxx"

# Update a secret
success = secret_manager.update_secret(token_ref, "ghp_new_token_value")

# Delete a secret
success = secret_manager.delete_secret(token_ref)

# List all secrets (optionally with prefix filter)
all_refs = secret_manager.list_secrets()
github_refs = secret_manager.list_secrets(prefix="github_token")
```

### Direct Instantiation

```python
from handsfree.secrets import VaultSecretManager

# Create manager with explicit configuration
manager = VaultSecretManager(
    vault_addr="https://vault.example.com:8200",
    vault_token="s.xxxxxxxxxxxxxx",
    vault_mount="secret",
    vault_namespace="my-namespace"
)

# Use the manager
token_ref = manager.store_secret("my_secret", "secret_value")
```

## Setting Up Vault

### Development Setup (Dev Mode)

For local development and testing:

```bash
# Start Vault in dev mode (in-memory, not for production)
vault server -dev -dev-root-token-id=root

# In another terminal, configure environment
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=root
export SECRET_MANAGER_TYPE=vault

# Test the connection
vault status
```

### Production Setup

#### 1. Enable KV Secrets Engine

```bash
# Enable KV v2 secrets engine at the default "secret/" mount
vault secrets enable -version=2 kv

# Or at a custom mount point
vault secrets enable -path=handsfree-secrets -version=2 kv
```

#### 2. Set Up AppRole Authentication

```bash
# Enable AppRole auth method
vault auth enable approle

# Create a policy for the application
vault policy write handsfree-policy - <<EOF
# Allow managing secrets under handsfree path
path "secret/data/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/*" {
  capabilities = ["list", "read", "delete"]
}
EOF

# Create an AppRole
vault write auth/approle/role/handsfree-app \
    token_policies="handsfree-policy" \
    token_ttl=1h \
    token_max_ttl=4h \
    secret_id_ttl=0

# Get the role ID
vault read auth/approle/role/handsfree-app/role-id
# Save the role_id from the output

# Generate a secret ID
vault write -f auth/approle/role/handsfree-app/secret-id
# Save the secret_id from the output
```

#### 3. Configure Application

```bash
export SECRET_MANAGER_TYPE=vault
export VAULT_ADDR=https://vault.example.com:8200
export VAULT_ROLE_ID=<role-id-from-step-2>
export VAULT_SECRET_ID=<secret-id-from-step-2>
```

### Vault Enterprise with Namespaces

```bash
# Create a namespace
vault namespace create handsfree

# Set namespace in environment
export VAULT_NAMESPACE=handsfree

# All subsequent commands will use this namespace
vault secrets enable -version=2 kv
```

## Reference Format

Secrets are stored with references in the `vault://` format:

```
vault://secret_key
```

Examples:
- `vault://github_token_user_123`
- `vault://slack_webhook_team_456`
- `vault://api_key_service_789`

The secret key is converted to a Vault path by replacing dots and underscores with forward slashes:
- `github.token.user.123` → `secret/data/github/token/user/123`
- `github_token_user_123` → `secret/data/github/token/user/123`

## Error Handling

The VaultSecretManager provides fail-fast error handling with clear messages:

### Configuration Errors

```python
# Missing VAULT_ADDR
VaultSecretManager()
# Raises: ValueError: VAULT_ADDR environment variable or vault_addr parameter is required

# Missing authentication
VaultSecretManager(vault_addr="https://vault.example.com")
# Raises: ValueError: Either VAULT_TOKEN or both VAULT_ROLE_ID and VAULT_SECRET_ID must be set
```

### Connection Errors

```python
# Invalid Vault address or token
manager = VaultSecretManager(
    vault_addr="https://invalid.vault.com",
    vault_token="invalid-token"
)
# Raises: VaultError: Failed to initialize Vault client: <connection error details>
```

### Operation Errors

```python
# Secret not found
value = manager.get_secret("vault://nonexistent")
# Returns: None (not an error)

# Invalid reference format
value = manager.get_secret("invalid://format")
# Returns: None (logged as warning)

# Network/Vault errors during operations
value = manager.get_secret("vault://some_secret")
# Raises: VaultError: Failed to retrieve secret: <error details>
```

## Testing

### Unit Tests

The implementation includes comprehensive unit tests with mocked Vault clients:

```bash
# Run all VaultSecretManager tests
pytest tests/test_secrets.py::TestVaultSecretManager -v

# Run a specific test
pytest tests/test_secrets.py::TestVaultSecretManager::test_store_and_retrieve_secret -v
```

### Integration Tests

For integration testing with a real Vault instance:

```bash
# Start Vault in dev mode
vault server -dev -dev-root-token-id=root &

# Set environment variables
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=root
export SECRET_MANAGER_TYPE=vault

# Run integration test
python -c "
from handsfree.secrets import get_default_secret_manager

manager = get_default_secret_manager()
ref = manager.store_secret('test_key', 'test_value')
value = manager.get_secret(ref)
assert value == 'test_value'
print('✓ Integration test passed!')
"
```

## Security Best Practices

1. **Use AppRole for Production** - Never use token authentication in production. AppRole provides better security with secret rotation capabilities.

2. **Enable TLS** - Always use HTTPS for Vault communication in production:
   ```bash
   export VAULT_ADDR=https://vault.example.com:8200
   ```

3. **Rotate Secrets** - Implement regular rotation of both Vault authentication credentials and stored secrets.

4. **Use Namespaces** - If using Vault Enterprise, leverage namespaces for multi-tenancy isolation.

5. **Monitor Audit Logs** - Enable and monitor Vault audit logs for security events:
   ```bash
   vault audit enable file file_path=/var/log/vault/audit.log
   ```

6. **Limit Token TTL** - Configure appropriate TTLs for AppRole tokens:
   ```bash
   vault write auth/approle/role/handsfree-app \
       token_ttl=1h \
       token_max_ttl=4h
   ```

7. **Principle of Least Privilege** - Grant only necessary permissions in Vault policies.

## Troubleshooting

### Connection Issues

**Problem**: `VaultError: Failed to initialize Vault client`

**Solutions**:
1. Verify Vault is running: `vault status`
2. Check VAULT_ADDR is correct and accessible
3. Verify TLS certificates if using HTTPS
4. Check network connectivity and firewall rules

### Authentication Issues

**Problem**: `VaultError: Failed to authenticate with Vault`

**Solutions**:
1. Verify token is valid: `vault token lookup`
2. For AppRole, verify role and secret IDs are correct
3. Check token/role has required permissions
4. Verify namespace is correct (if using Vault Enterprise)

### Secret Not Found

**Problem**: `get_secret()` returns `None`

**Solutions**:
1. Verify the secret exists: `vault kv get secret/path/to/secret`
2. Check the mount point is correct (default: `secret`)
3. Verify you have read permissions on the path
4. Check the reference format is correct (`vault://key`)

### Permission Denied

**Problem**: `VaultError: permission denied`

**Solutions**:
1. Review Vault policy attached to token/role
2. Verify the policy grants required capabilities
3. Check namespace isolation (Vault Enterprise)

## Migration from EnvSecretManager

To migrate from `EnvSecretManager` to `VaultSecretManager`:

1. **Set up Vault** (see Production Setup above)

2. **Update configuration**:
   ```bash
   # Change from:
   export SECRET_MANAGER_TYPE=env
   
   # To:
   export SECRET_MANAGER_TYPE=vault
   export VAULT_ADDR=https://vault.example.com:8200
   export VAULT_ROLE_ID=your-role-id
   export VAULT_SECRET_ID=your-secret-id
   ```

3. **Migrate existing secrets**:
   ```python
   from handsfree.secrets import EnvSecretManager, VaultSecretManager
   
   # Create both managers
   env_manager = EnvSecretManager()
   vault_manager = VaultSecretManager(
       vault_addr="https://vault.example.com:8200",
       vault_token="your-token"
   )
   
   # List all env secrets
   env_refs = env_manager.list_secrets()
   
   # Migrate each secret
   for env_ref in env_refs:
       # Get value from env
       value = env_manager.get_secret(env_ref)
       
       # Extract key from reference (strip "env://PREFIX_")
       key = env_ref.replace("env://HANDSFREE_SECRET_", "").lower()
       
       # Store in Vault
       vault_ref = vault_manager.store_secret(key, value)
       
       # Update database to use new vault_ref
       # update_token_ref_in_database(old_ref=env_ref, new_ref=vault_ref)
   ```

4. **Restart application** with new configuration

5. **Verify migration** by testing secret retrieval

6. **Clean up** environment variables (optional)

## Performance Considerations

- **Caching**: VaultSecretManager doesn't cache secrets. Consider implementing application-level caching if needed.
- **Connection pooling**: The hvac client reuses HTTP connections for efficiency.
- **Batch operations**: For bulk operations, consider Vault's transaction capabilities.
- **Network latency**: Vault operations involve network calls. For latency-sensitive operations, consider proximity to Vault server.

## Limitations

- **KV v2 only**: Currently supports KV v2 secrets engine only
- **No secret versioning**: While Vault supports versioning, the current implementation always uses the latest version
- **No automatic rotation**: Secret rotation must be implemented at the application level
- **Synchronous operations**: All operations are synchronous (no async support yet)

## Future Enhancements

- [ ] Support for KV v1 secrets engine
- [ ] Secret version management (get specific versions)
- [ ] Automatic secret rotation support
- [ ] Async operations support
- [ ] Connection pooling configuration
- [ ] Metrics and monitoring integration
- [ ] Support for dynamic secrets
- [ ] Transit secrets engine for encryption as a service

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Vault KV Secrets Engine](https://www.vaultproject.io/docs/secrets/kv)
- [Vault AppRole Auth Method](https://www.vaultproject.io/docs/auth/approle)
- [hvac Python Client](https://hvac.readthedocs.io/)
- [Vault Security Model](https://www.vaultproject.io/docs/internals/security)

## Support

For issues or questions:
1. Check the [main documentation](../SECRET_STORAGE_AND_SESSIONS.md)
2. Review Vault logs for error details
3. Enable debug logging: `export VAULT_LOG_LEVEL=debug`
4. File an issue with relevant logs and configuration (sanitized)
