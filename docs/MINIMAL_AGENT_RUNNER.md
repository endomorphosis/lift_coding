# Minimal Agent Runner Guide

This guide explains how to use the minimal agent runner that processes tasks from the local database.

## Overview

The minimal agent runner is a simple Python-based task processor that:
1. Polls for tasks in `created` state from the local DuckDB database
2. Transitions tasks through their lifecycle: `created` → `running` → `completed`/`failed`
3. Handles errors gracefully and marks tasks as failed when exceptions occur
4. Provides progress logging for monitoring

This is suitable for development, demos, and lightweight production use cases.

## Key Features

- **Simple**: No external dependencies beyond the database
- **Safe by default**: No GitHub write actions, just state transitions
- **Flexible**: Can be run once or in continuous loop mode
- **Observable**: Clear logging at each step
- **Testable**: Comprehensive unit tests with mocked database

## Architecture

The runner consists of three main components:

1. **Runner Module** (`src/handsfree/agents/runner.py`):
   - Core logic for task transitions
   - State machine: created → running → completed/failed
   - Progress updates and error handling

2. **CLI Script** (`scripts/minimal_agent_runner.py`):
   - Command-line interface for running the agent
   - Argument parsing and configuration
   - Database connection management

3. **Tests** (`tests/test_minimal_runner.py`):
   - Comprehensive unit tests
   - Mocked database for isolation
   - Error handling scenarios

## Requirements

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HANDSFREE_AGENT_RUNNER_ENABLED` | Yes | - | Must be set to `true` to enable the runner |
| `HANDSFREE_DB_PATH` | No | `handsfree.duckdb` | Path to the DuckDB database file |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Python Dependencies

The runner requires:
- `duckdb` - for database access
- Standard library modules (no additional dependencies)

Install with:
```bash
pip install -e .
```

## Usage

### Basic Usage

#### Run Once (Recommended for Testing)

Process all pending tasks once and exit:

```bash
HANDSFREE_AGENT_RUNNER_ENABLED=true python scripts/minimal_agent_runner.py --once
```

This will:
1. Connect to the database
2. Start all `created` tasks → `running`
3. Complete all `running` tasks → `completed`
4. Exit

#### Continuous Loop Mode

Run continuously, processing tasks every N seconds:

```bash
HANDSFREE_AGENT_RUNNER_ENABLED=true python scripts/minimal_agent_runner.py --loop --interval 5
```

This will:
1. Connect to the database
2. Every 5 seconds:
   - Start new `created` tasks
   - Complete `running` tasks
3. Continue until interrupted (Ctrl+C)

### Advanced Usage

#### Custom Database Path

Specify a custom database file:

```bash
HANDSFREE_AGENT_RUNNER_ENABLED=true \
  python scripts/minimal_agent_runner.py \
  --once \
  --db-path /path/to/custom.duckdb
```

#### Verbose Logging

Enable debug logging for troubleshooting:

```bash
HANDSFREE_AGENT_RUNNER_ENABLED=true \
LOG_LEVEL=DEBUG \
  python scripts/minimal_agent_runner.py --once
```

#### Background Process

Run in the background (Linux/macOS):

```bash
HANDSFREE_AGENT_RUNNER_ENABLED=true \
  nohup python scripts/minimal_agent_runner.py --loop --interval 10 \
  > runner.log 2>&1 &
```

Stop with:
```bash
pkill -f minimal_agent_runner.py
```

## Sample Flow

### 1. Create a Test Task

Using the Python API:

```python
from handsfree.db.connection import get_connection
from handsfree.db.agent_tasks import create_agent_task

conn = get_connection()

task = create_agent_task(
    conn=conn,
    user_id="demo-user",
    provider="minimal-runner",
    instruction="Test task for demonstration",
)

print(f"Created task: {task.id} in state: {task.state}")
# Output: Created task: 550e8400-e29b-41d4-a716-446655440000 in state: created
```

### 2. Run the Runner

```bash
HANDSFREE_AGENT_RUNNER_ENABLED=true python scripts/minimal_agent_runner.py --once
```

Expected output:
```
2026-01-19 18:30:00 - minimal-agent-runner - INFO - Connected to database: handsfree.duckdb
2026-01-19 18:30:00 - minimal-agent-runner - INFO - Running agent runner once...
2026-01-19 18:30:00 - handsfree.agents.runner - INFO - Auto-started task 550e8400-e29b-41d4-a716-446655440000
2026-01-19 18:30:00 - handsfree.agents.runner - INFO - Processing task 550e8400-e29b-41d4-a716-446655440000: Test task for demonstration
2026-01-19 18:30:01 - handsfree.agents.runner - INFO - Task 550e8400-e29b-41d4-a716-446655440000 completed successfully
2026-01-19 18:30:01 - minimal-agent-runner - INFO - Run completed: {'enabled': True, 'tasks_started': 1, 'tasks_completed': 1, 'tasks_failed': 0, 'tasks_skipped': 0, 'timestamp': '2026-01-19T18:30:01.123456Z'}
```

### 3. Verify Task State

```python
from handsfree.db.agent_tasks import get_agent_task_by_id

task_after = get_agent_task_by_id(conn, task.id)
print(f"Task state: {task_after.state}")
# Output: Task state: completed

print(f"Trace: {task_after.trace}")
# Output: Trace: {'auto_started_at': '2026-01-19T18:30:00...', 'completed_at': '2026-01-19T18:30:01...', ...}
```

## State Transitions

The runner implements the following state machine:

```
created ──────────> running ──────────> completed
   │                   │
   │                   └──────────────> failed
   │
   └──────────────────────────────────> failed (on error)
```

### Valid Transitions

- `created` → `running`: Auto-started by runner
- `running` → `completed`: Task successfully processed
- `running` → `failed`: Error during processing
- `created` → `failed`: Error before starting (rare)

### State Descriptions

| State | Description |
|-------|-------------|
| `created` | Task has been created but not yet started |
| `running` | Task is being processed by the runner |
| `completed` | Task finished successfully |
| `failed` | Task encountered an error and could not complete |

## Task Processing Logic

The runner uses a "stubbed work" approach:

```python
def process_running_task(conn, task_id, simulate_work=True):
    """
    1. Verify task exists and is in 'running' state
    2. Simulate work (0.5 second delay)
    3. Update progress in trace
    4. Transition to 'completed' state
    5. Handle errors by transitioning to 'failed'
    """
```

This is intentionally minimal. In a production implementation, you would:
- Call external APIs (GitHub, LLMs, etc.)
- Execute code generation or analysis
- Create pull requests or issues
- Perform actual work based on the task instruction

## Error Handling

The runner handles errors at multiple levels:

### 1. Task-Level Errors

If an error occurs while processing a task, the task is marked as `failed`:

```python
try:
    # Process task
    update_agent_task_state(conn, task_id, "completed", {...})
except Exception as e:
    # Mark as failed
    update_agent_task_state(conn, task_id, "failed", {"error": str(e)})
```

### 2. Loop-Level Errors

If an error occurs in the runner loop, it's logged and the loop continues:

```python
while True:
    try:
        run_once(conn)
    except Exception as e:
        logger.error("Error in runner loop: %s", e)
    time.sleep(interval_seconds)
```

### 3. Invalid State Transitions

If a task cannot transition (e.g., already completed), it's skipped:

```python
try:
    update_agent_task_state(conn, task_id, "running")
except ValueError as e:
    logger.warning("Invalid transition: %s", e)
    # Task is skipped
```

## Testing

### Run Unit Tests

```bash
python -m pytest tests/test_minimal_runner.py -v
```

Expected output:
```
tests/test_minimal_runner.py::test_is_runner_enabled PASSED
tests/test_minimal_runner.py::test_auto_start_created_tasks PASSED
tests/test_minimal_runner.py::test_simulate_progress_update PASSED
tests/test_minimal_runner.py::test_process_running_task_success PASSED
tests/test_minimal_runner.py::test_process_running_task_not_found PASSED
tests/test_minimal_runner.py::test_process_running_task_wrong_state PASSED
tests/test_minimal_runner.py::test_process_running_tasks PASSED
tests/test_minimal_runner.py::test_run_once_disabled PASSED
tests/test_minimal_runner.py::test_run_once_full_cycle PASSED
tests/test_minimal_runner.py::test_run_once_error_handling PASSED
tests/test_minimal_runner.py::test_process_running_task_marks_failed_on_exception PASSED
```

### Manual Testing

1. **Create test database**:
   ```bash
   rm -f test.duckdb  # Clean slate
   ```

2. **Create test task**:
   ```python
   from handsfree.db.connection import get_connection
   from handsfree.db.agent_tasks import create_agent_task
   import os
   
   os.environ["HANDSFREE_DB_PATH"] = "test.duckdb"
   conn = get_connection()
   
   task = create_agent_task(
       conn=conn,
       user_id="test",
       provider="test",
       instruction="Manual test task",
   )
   print(f"Task ID: {task.id}")
   conn.close()
   ```

3. **Run the runner**:
   ```bash
   HANDSFREE_AGENT_RUNNER_ENABLED=true \
   HANDSFREE_DB_PATH=test.duckdb \
     python scripts/minimal_agent_runner.py --once
   ```

4. **Verify completion**:
   ```python
   from handsfree.db.connection import get_connection
   from handsfree.db.agent_tasks import get_agent_task_by_id
   import os
   
   os.environ["HANDSFREE_DB_PATH"] = "test.duckdb"
   conn = get_connection()
   
   task = get_agent_task_by_id(conn, "YOUR_TASK_ID")
   print(f"State: {task.state}")
   print(f"Trace: {task.trace}")
   conn.close()
   ```

## Troubleshooting

### Runner Won't Start

**Problem**: `Agent runner is disabled` message

**Solution**: Set the environment variable:
```bash
export HANDSFREE_AGENT_RUNNER_ENABLED=true
```

### Database Not Found

**Problem**: `Failed to connect to database`

**Solution**: Create the database or specify the correct path:
```bash
# Create database
python -c "from handsfree.db.connection import get_connection; get_connection()"

# Or specify path
HANDSFREE_DB_PATH=/path/to/db.duckdb python scripts/minimal_agent_runner.py --once
```

### Tasks Not Processing

**Problem**: Tasks remain in `created` or `running` state

**Solutions**:
1. Check runner is enabled: `echo $HANDSFREE_AGENT_RUNNER_ENABLED`
2. Check logs for errors: `LOG_LEVEL=DEBUG python scripts/minimal_agent_runner.py --once`
3. Verify database path: `ls -lh $HANDSFREE_DB_PATH`
4. Check task state in database directly

### Permission Errors

**Problem**: `Permission denied` when accessing database

**Solution**: Check file permissions:
```bash
chmod 644 handsfree.duckdb
# Or run as the owner of the database file
```

## Integration with HandsFree Backend

The minimal runner can be used alongside the HandsFree backend:

1. **Backend creates tasks**: Via API or agent delegation
2. **Runner processes tasks**: Transitions them through states
3. **Backend monitors**: Via webhooks or polling

The runner is intentionally decoupled from the backend to allow:
- Independent scaling
- Separate deployment
- Different runtimes (local dev vs. production)

## Deployment Options

### Development

Run locally with:
```bash
HANDSFREE_AGENT_RUNNER_ENABLED=true python scripts/minimal_agent_runner.py --loop --interval 5
```

### Production

#### Option 1: systemd Service (Linux)

Create `/etc/systemd/system/agent-runner.service`:
```ini
[Unit]
Description=HandsFree Minimal Agent Runner
After=network.target

[Service]
Type=simple
User=handsfree
WorkingDirectory=/opt/handsfree
Environment="HANDSFREE_AGENT_RUNNER_ENABLED=true"
Environment="HANDSFREE_DB_PATH=/var/lib/handsfree/db.duckdb"
ExecStart=/usr/bin/python3 /opt/handsfree/scripts/minimal_agent_runner.py --loop --interval 10
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable agent-runner
sudo systemctl start agent-runner
sudo systemctl status agent-runner
```

#### Option 2: Docker Container

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app
RUN pip install -e .

ENV HANDSFREE_AGENT_RUNNER_ENABLED=true
ENV HANDSFREE_DB_PATH=/data/handsfree.duckdb

CMD ["python", "scripts/minimal_agent_runner.py", "--loop", "--interval", "10"]
```

Build and run:
```bash
docker build -t agent-runner .
docker run -d \
  -v /path/to/data:/data \
  -e HANDSFREE_AGENT_RUNNER_ENABLED=true \
  --name agent-runner \
  agent-runner
```

#### Option 3: Kubernetes Deployment

See `docker-compose.agent-runner.yml` for a complete example that can be adapted to Kubernetes.

## Limitations

The minimal runner has intentional limitations:

1. **No real work**: Tasks are completed with simulated work only
2. **No GitHub integration**: Doesn't create PRs or issues
3. **No LLM calls**: No code generation or AI processing
4. **Single-threaded**: Processes one task at a time
5. **Local database only**: No distributed locking

For production use cases requiring these features, see:
- **Full agent runner**: `agent-runner/runner.py`
- **GitHub Actions workflow**: `.github/workflows/agent-runner.yml`
- **Agent delegation**: `docs/agent-runner-setup.md`

## Extending the Runner

To add real work processing:

### Option 1: Modify process_running_task

```python
def process_running_task(conn, task_id, simulate_work=True):
    task = get_agent_task_by_id(conn, task_id)
    
    # Add your custom logic here
    if task.provider == "github":
        result = process_github_task(task)
    elif task.provider == "llm":
        result = process_llm_task(task)
    else:
        result = default_process(task)
    
    # Update state based on result
    if result.success:
        update_agent_task_state(conn, task_id, "completed", result.trace)
    else:
        update_agent_task_state(conn, task_id, "failed", result.error)
```

### Option 2: Create a Plugin System

```python
# plugins/github_processor.py
class GitHubProcessor:
    def process(self, task):
        # Your logic here
        pass

# runner.py
PROCESSORS = {
    "github": GitHubProcessor(),
    "llm": LLMProcessor(),
}

def process_running_task(conn, task_id):
    task = get_agent_task_by_id(conn, task_id)
    processor = PROCESSORS.get(task.provider)
    if processor:
        return processor.process(task)
```

## Related Documentation

- [Full Agent Runner Setup](./agent-runner-setup.md) - Complete guide with GitHub integration
- [Agent Runner Quickstart](./AGENT_RUNNER_QUICKSTART.md) - GitHub Actions workflow setup
- [Agent Delegation](../tracking/PR-016-agent-delegation-integration.md) - Backend integration details
- [Database Schema](../migrations/001_initial_schema.sql) - Database structure

## Support

For questions or issues:

1. Check the troubleshooting section above
2. Review the test cases for examples
3. Open an issue in the repository
4. Consult the related documentation

## Summary

The minimal agent runner provides a simple, reliable foundation for task processing:

✅ **Easy to use**: Single command to start  
✅ **Well tested**: Comprehensive unit tests  
✅ **Observable**: Clear logging at each step  
✅ **Safe**: No external side effects by default  
✅ **Extensible**: Easy to add custom processing logic  

Perfect for development, demos, and as a foundation for production deployments.
