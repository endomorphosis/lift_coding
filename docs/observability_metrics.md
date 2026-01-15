# Observability Metrics

This document describes the lightweight observability metrics implementation for the HandsFree Dev Companion API.

## Overview

The metrics system provides lightweight, in-process metrics collection for monitoring the command flow without requiring external infrastructure like Prometheus. Metrics are collected in memory and can be queried via a REST endpoint.

## Features

- **Command Latency Tracking**: Records p50 and p95 latency percentiles for `/v1/command` endpoint
- **Intent Counting**: Tracks the number of times each intent is executed
- **Status Tracking**: Counts commands by status (ok, needs_confirmation, error)
- **Confirmation Tracking**: Records confirmation outcomes (ok, not_found, error)
- **Thread-Safe**: Safe to use in multi-worker environments (each worker maintains its own state)
- **Gated Access**: Endpoint is disabled by default and must be explicitly enabled

## Configuration

### Enabling Metrics

Metrics collection is always active, but the metrics endpoint is disabled by default. To enable the `/v1/metrics` endpoint, set the environment variable:

```bash
export HANDSFREE_ENABLE_METRICS=true
```

The following values enable metrics: `true`, `True`, `TRUE`, `1`, `yes`

## API Endpoint

### GET /v1/metrics

Returns a snapshot of current metrics.

**Response (200 OK):**

```json
{
  "intent_counts": {
    "inbox.list": 42,
    "pr.summarize": 15,
    "pr.request_review": 8
  },
  "status_counts": {
    "ok": 45,
    "needs_confirmation": 10,
    "error": 2
  },
  "confirm_outcomes": {
    "ok": 8,
    "not_found": 1,
    "error": 1
  },
  "command_latency_ms": {
    "p50": 150.5,
    "p95": 420.3,
    "count": 57
  }
}
```

**Response (404 Not Found)** - When metrics are disabled:

```json
{
  "error": "not_found",
  "message": "Metrics endpoint not available. Set HANDSFREE_ENABLE_METRICS=true to enable."
}
```

## Metrics Reference

### intent_counts

Counts the number of times each intent has been executed. Keys are intent names (e.g., `inbox.list`, `pr.summarize`).

### status_counts

Counts commands by their final status:
- `ok`: Command executed successfully
- `needs_confirmation`: Command requires user confirmation
- `error`: Command failed with an error

### confirm_outcomes

Tracks confirmation request outcomes:
- `ok`: Confirmation succeeded
- `not_found`: Pending action not found or expired
- `error`: Confirmation failed with an error
- `other`: Other confirmation outcomes

### command_latency_ms

Latency statistics for the `/v1/command` endpoint:
- `p50`: 50th percentile (median) latency in milliseconds
- `p95`: 95th percentile latency in milliseconds
- `count`: Total number of latency samples

## Implementation Notes

### Multi-Worker Considerations

Each worker process maintains its own in-memory metrics state. This means:

1. Metrics are process-local and not aggregated across workers
2. Querying `/v1/metrics` returns metrics for the worker that handled the request
3. This is by design for simplicity and avoiding external dependencies
4. For production monitoring, consider using application-level monitoring tools that aggregate across workers

### Memory Usage

Metrics are stored in memory with the following characteristics:

- **Intent counts**: O(n) where n is the number of unique intents
- **Status counts**: O(1) - fixed set of statuses
- **Confirmation outcomes**: O(1) - fixed set of outcomes  
- **Latency samples**: O(m) where m is the number of commands processed

The latency samples list grows unbounded, which is acceptable for most use cases but may need periodic reset in long-running processes with very high traffic.

### Thread Safety

All metrics operations use a thread lock to ensure thread-safe access in multi-threaded environments. This has minimal performance impact due to the fast nature of counter increments and list appends.

## Usage Examples

### Enabling Metrics

```bash
# Set environment variable
export HANDSFREE_ENABLE_METRICS=true

# Start the server
python -m handsfree.server
```

### Querying Metrics

```bash
# Get current metrics
curl http://localhost:8080/v1/metrics

# Pretty print with jq
curl -s http://localhost:8080/v1/metrics | jq .
```

### Monitoring Script Example

```bash
#!/bin/bash
# Simple monitoring script

while true; do
  echo "=== Metrics at $(date) ==="
  curl -s http://localhost:8080/v1/metrics | jq '{
    total_commands: (.command_latency_ms.count),
    p50_latency: .command_latency_ms.p50,
    p95_latency: .command_latency_ms.p95,
    error_rate: (.status_counts.error / .command_latency_ms.count)
  }'
  sleep 30
done
```

## Testing

The metrics system includes comprehensive tests in `tests/test_metrics.py`:

- Thread-safety tests
- Endpoint gating tests
- Integration tests with actual API endpoints
- Percentile calculation tests

Run tests with:

```bash
make test
```

Or run just metrics tests:

```bash
pytest tests/test_metrics.py -v
```

## Future Enhancements

Potential future improvements:

1. **Prometheus Integration**: Export metrics in Prometheus format
2. **Metric Retention**: Add time-based windowing for metrics
3. **Additional Metrics**: Track more granular metrics (e.g., per-user rates)
4. **Reset Endpoint**: Add an endpoint to reset metrics
5. **Worker Aggregation**: Implement cross-worker metric aggregation
