# Live GitHub Provider Mode

This document describes the live GitHub provider implementation that allows switching between fixture-based and live API modes.

## Overview

The GitHub provider now supports two modes:
1. **Fixtures mode** (default): Returns deterministic data from fixture files
2. **Live mode**: Makes real GitHub API calls using authentication tokens

This implementation preserves fixture-based testing while enabling live API integration for production use.

## Architecture

### Provider Classes

#### `GitHubProvider` (Legacy)
- Supports both fixture and live modes via `GitHubAuthProvider`
- Used by existing code that passes `user_id` parameter
- Maintained for backward compatibility

#### `LiveGitHubProvider` (New)
- Simplified interface using `TokenProvider`
- Falls back to fixtures when token unavailable or API not implemented
- Designed for future live API implementation

### Token Provider Interface

#### `TokenProvider` (Abstract Base)
```python
class TokenProvider(ABC):
    @abstractmethod
    def get_token(self) -> str | None:
        """Get a GitHub token."""
        pass
```

#### Implementations

1. **`FixtureTokenProvider`**: Always returns `None` (fixture-only mode)
2. **`EnvTokenProvider`**: Reads token from `GITHUB_TOKEN` environment variable

### Factory Function

```python
def get_token_provider() -> TokenProvider:
    """Get a token provider based on environment configuration."""
```

Checks the following environment variables (in order):
1. `HANDS_FREE_GITHUB_MODE=live` - New, preferred environment variable
2. `GITHUB_LIVE_MODE=true|1|yes` - Legacy compatibility

Requires `GITHUB_TOKEN` to be set for live mode to activate.

## Usage

### Basic Usage

```python
from handsfree.github import LiveGitHubProvider, get_token_provider

# Create a live provider (will fall back to fixtures if not configured)
token_provider = get_token_provider()
provider = LiveGitHubProvider(token_provider)

# Use the provider
prs = provider.list_user_prs("octocat")
details = provider.get_pr_details("owner/repo", 123)
checks = provider.get_pr_checks("owner/repo", 123)
reviews = provider.get_pr_reviews("owner/repo", 123)
```

### Environment Configuration

#### Enable Live Mode (Recommended)
```bash
export HANDS_FREE_GITHUB_MODE=live
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

#### Legacy Configuration
```bash
export GITHUB_LIVE_MODE=true
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

#### Fixture Mode (Default)
```bash
# No environment variables needed
# Or explicitly set:
export HANDS_FREE_GITHUB_MODE=fixtures
```

### Testing

Tests use mocked HTTP calls and do not hit GitHub in CI:

```python
import pytest
from handsfree.github.auth import FixtureTokenProvider
from handsfree.github import LiveGitHubProvider

def test_with_fixtures():
    """Test using fixtures."""
    provider = LiveGitHubProvider(FixtureTokenProvider())
    prs = provider.list_user_prs("testuser")
    assert len(prs) == 3  # From fixture

def test_with_live_mode(monkeypatch):
    """Test with live mode enabled."""
    monkeypatch.setenv("HANDS_FREE_GITHUB_MODE", "live")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
    
    from handsfree.github.auth import get_token_provider
    provider = LiveGitHubProvider(get_token_provider())
    # Would make live API calls if implemented
```

## API Methods

All methods return normalized dictionaries with consistent structure:

### `list_user_prs(user: str) -> list[dict[str, Any]]`
Lists PRs where the user is a requested reviewer or assignee.

**Returns:**
```python
[
    {
        "repo": "owner/repo",
        "pr_number": 123,
        "title": "Add new feature",
        "url": "https://github.com/owner/repo/pull/123",
        "priority": 5,
        ...
    },
    ...
]
```

### `get_pr_details(repo: str, pr_number: int) -> dict[str, Any]`
Gets PR details including title, description, labels, and change statistics.

**Returns:**
```python
{
    "pr_number": 123,
    "title": "Add new feature X",
    "repo": "owner/repo",
    "author": "octocat",
    "state": "open",
    "additions": 150,
    "deletions": 50,
    "changed_files": 10,
    ...
}
```

### `get_pr_checks(repo: str, pr_number: int) -> list[dict[str, Any]]`
Gets check runs for a PR.

**Returns:**
```python
[
    {
        "name": "CI/Tests",
        "status": "completed",
        "conclusion": "success",
        ...
    },
    ...
]
```

### `get_pr_reviews(repo: str, pr_number: int) -> list[dict[str, Any]]`
Gets reviews for a PR.

**Returns:**
```python
[
    {
        "user": "reviewer1",
        "state": "APPROVED",
        "submitted_at": "2024-01-15T10:30:00Z",
        ...
    },
    ...
]
```

## Error Handling

### Missing Token
When live mode is requested but no token is available:
```python
RuntimeError: GitHub token not available for live API calls
```

The provider automatically falls back to fixtures in this case.

### Rate Limiting

The provider handles GitHub API rate limits as follows (implemented in [PR-077](https://github.com/endomorphosis/lift_coding/pull/289)):

1. **Primary Rate Limit Detection**: When the GitHub API returns HTTP 429 (rate limit exceeded), the provider:
   - Extracts the `X-RateLimit-Reset` header to determine when the limit resets
   - Logs an error with the reset time
   - Raises a `RuntimeError` with details about when to retry

2. **Automatic Fallback**: When a rate limit error occurs, the provider automatically falls back to fixture data to maintain functionality during development and testing.

3. **Authentication Errors**: The provider also detects and handles:
   - HTTP 401 (Unauthorized) - invalid or expired token
   - HTTP 403 (Forbidden) - insufficient permissions

**User-facing errors:**
- Rate limit exceeded: `"GitHub API rate limit exceeded. Try again after {reset_time}"`
- Authentication failures: `"GitHub API authentication failed. Token may be invalid or expired."`
- Permission issues: `"GitHub API access forbidden. Token may lack required permissions."`

**Note**: The current implementation does not include automatic retry with exponential backoff. When rate limits are hit, the user must wait until the rate limit reset time before retrying, or the system will use cached fixture data.

## Security Considerations

1. **Token Storage**: Tokens are only stored in memory, never logged
2. **Authorization Header**: Uses `Bearer` token format
3. **Environment Variables**: Tokens should be set via secure environment configuration
4. **User Agent**: Identifies as `HandsFree-Dev-Companion/1.0`

## Future Work

### Live API Implementation
The `_make_request()` method is currently a stub. Full implementation will:
- Use `httpx` or `requests` for HTTP calls
- Handle rate limiting and retries
- Parse and validate GitHub API responses
- Cache responses where appropriate

### Write Operations
Future PRs will add:
- `request_review()` - Request reviewers on a PR
- `merge_pr()` - Merge a pull request
- Other GitHub write operations

## Migration Guide

### From GitHubProvider to LiveGitHubProvider

**Before:**
```python
from handsfree.github import GitHubProvider
provider = GitHubProvider()
prs = provider.list_user_prs("user", user_id="123")
```

**After:**
```python
from handsfree.github import LiveGitHubProvider, get_token_provider
provider = LiveGitHubProvider(get_token_provider())
prs = provider.list_user_prs("user")
```

Note: `user_id` parameter is no longer needed as authentication is handled by the token provider.

## Troubleshooting

### Live mode not activating
Check that both environment variables are set:
```bash
echo $HANDS_FREE_GITHUB_MODE  # Should be "live"
echo $GITHUB_TOKEN  # Should be your token
```

### Tests using live API instead of fixtures
Ensure test setup clears environment variables:
```python
def test_something(monkeypatch):
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    # Test code here
```

### Token not being used
Verify token provider is correctly instantiated:
```python
from handsfree.github.auth import get_token_provider
provider = get_token_provider()
print(type(provider))  # Should be EnvTokenProvider if live mode enabled
print(provider.get_token())  # Should print your token (be careful!)
```
