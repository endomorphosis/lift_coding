# Notification System - Throttling and Deduplication

This document describes the notification throttling and deduplication features implemented for the HandsFree notification system.

## Overview

The notification system now supports:
1. **Deduplication**: Automatically collapses duplicate notifications within a time window
2. **Throttling**: Profile-aware filtering based on notification priority

## Deduplication

Deduplication prevents the same notification from being delivered multiple times within a short time window.

### How it works

- Each notification generates a **dedupe key** based on:
  - Event type (e.g., `webhook.pr_opened`)
  - Repository name
  - Target reference (PR number, issue number, branch, or commit)

- Notifications with the same dedupe key within the **dedupe window** (default: 5 minutes) are collapsed.

- The first notification is created; subsequent duplicates within the window return `None` without creating a new notification.

### Example

```python
from handsfree.db.notifications import create_notification

# First notification is created
notif1 = create_notification(
    conn=db,
    user_id="user123",
    event_type="webhook.pr_opened",
    message="PR #123 opened in owner/repo",
    metadata={"repo": "owner/repo", "pr_number": 123}
)
# Returns: Notification object

# Duplicate within 5 minutes is blocked
notif2 = create_notification(
    conn=db,
    user_id="user123",
    event_type="webhook.pr_opened",
    message="PR #123 opened in owner/repo",
    metadata={"repo": "owner/repo", "pr_number": 123}
)
# Returns: None (deduplicated)
```

### Custom Dedupe Window

You can customize the dedupe window duration:

```python
notif = create_notification(
    conn=db,
    user_id="user123",
    event_type="webhook.pr_opened",
    message="PR #123 opened",
    metadata={"repo": "owner/repo", "pr_number": 123},
    dedupe_window_seconds=600  # 10 minutes
)
```

## Throttling

Throttling filters notifications based on their priority and the user's current profile.

### Priority Levels

Notifications are assigned priority levels from 1 (lowest) to 5 (highest):

| Priority | Description | Example Events |
|----------|-------------|----------------|
| 5 | Critical | PR merged, deployment failures, security alerts, check suite failures |
| 4 | Important | PR opened/closed, review requested, review submitted |
| 3 | Medium | PR synchronized, PR reopened, check suite completed |
| 2 | Low | PR labeled/unlabeled, issue comments |
| 1 | Very Low | Minor updates |

Priority is automatically determined from the event type, but can be manually overridden.

### Profile-Based Throttling

Different profiles apply different throttling thresholds:

| Profile | Threshold | Allowed Priorities | Use Case |
|---------|-----------|-------------------|----------|
| workout | 4+ | Only critical and important events | Exercising, need minimal interruptions |
| commute | 3+ | Medium priority and above | Driving/commuting, moderate filtering |
| kitchen | 2+ | Low priority and above | Cooking, some filtering |
| default | 1+ | All events | Normal use, no filtering |

### Example

```python
# Low priority notification with workout profile
notif = create_notification(
    conn=db,
    user_id="user123",
    event_type="webhook.pr_labeled",  # Priority 2 (low)
    message="PR labeled",
    profile="workout"  # Requires priority 4+
)
# Returns: None (throttled)

# High priority notification with workout profile
notif = create_notification(
    conn=db,
    user_id="user123",
    event_type="webhook.pr_merged",  # Priority 5 (critical)
    message="PR merged",
    profile="workout"  # Requires priority 4+
)
# Returns: Notification object (allowed)
```

### Priority Override

You can manually override the priority if needed:

```python
notif = create_notification(
    conn=db,
    user_id="user123",
    event_type="webhook.pr_labeled",  # Normally priority 2
    message="Important PR label",
    profile="workout",
    priority=5  # Manual override to bypass throttling
)
# Returns: Notification object (allowed due to override)
```

## API Changes

### create_notification

New optional parameters:

```python
def create_notification(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    profile: str = "default",  # NEW: User profile for throttling
    priority: int | None = None,  # NEW: Manual priority override (1-5)
    dedupe_window_seconds: int = 300,  # NEW: Dedupe window duration
) -> Notification | None:  # Returns None if throttled or deduplicated
```

### Notification Object

New fields:

```python
@dataclass
class Notification:
    id: str
    user_id: str
    event_type: str
    message: str
    metadata: dict[str, Any] | None
    created_at: datetime
    priority: int = 3  # NEW: Priority level (1-5)
    profile: str = "default"  # NEW: Profile used at creation
```

### Database Schema

New columns in `notifications` table:

- `priority` (INTEGER): Priority level (1-5), default 3
- `dedupe_key` (TEXT): Hash for deduplication
- `profile` (TEXT): Profile used at creation time, default 'default'

Indexes:
- `idx_notifications_dedupe_key`: Fast dedupe lookups
- `idx_notifications_priority`: Priority-based filtering

## Backward Compatibility

All changes are backward compatible:

- Existing code works without modification
- Default values ensure expected behavior
- All existing tests pass unchanged
- New fields are optional

## Testing

Comprehensive tests are provided in `tests/test_notification_throttling_dedupe.py`:

- Dedupe key generation
- Event priority assignment
- Throttling logic
- Deduplication behavior
- Profile-aware throttling
- Backward compatibility
- Priority override

Run tests:
```bash
pytest tests/test_notification_throttling_dedupe.py -v
```
