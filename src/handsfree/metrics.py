"""Lightweight observability metrics for command flow.

This module provides in-process metrics collection without external dependencies.
Metrics are best-effort in multi-worker environments (each worker has its own state).
"""

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricsCollector:
    """In-memory metrics collector for observability.

    Thread-safe implementation for multi-worker environments.
    Each worker process maintains its own metrics state.
    """

    # Counters for intent names
    intent_counts: dict[str, int] = field(default_factory=dict)

    # Counters for status values (ok, needs_confirmation, error)
    status_counts: dict[str, int] = field(default_factory=dict)

    # Counters for confirmation outcomes
    confirm_outcomes: dict[str, int] = field(default_factory=dict)

    # Latency samples for /v1/command endpoint (in milliseconds)
    command_latencies: list[float] = field(default_factory=list)

    # Thread lock for safe concurrent access
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_command(
        self,
        intent_name: str,
        status: str,
        latency_ms: float,
    ) -> None:
        """Record metrics for a command execution.

        Args:
            intent_name: Name of the intent (e.g., "inbox.list", "pr.summarize")
            status: Status of the command (ok, needs_confirmation, error)
            latency_ms: Latency in milliseconds
        """
        with self._lock:
            # Increment intent counter
            self.intent_counts[intent_name] = self.intent_counts.get(intent_name, 0) + 1

            # Increment status counter
            self.status_counts[status] = self.status_counts.get(status, 0) + 1

            # Record latency
            self.command_latencies.append(latency_ms)

    def record_confirmation(self, outcome: str) -> None:
        """Record metrics for a confirmation request.

        Args:
            outcome: Outcome of confirmation (ok, not_found, error)
        """
        with self._lock:
            self.confirm_outcomes[outcome] = self.confirm_outcomes.get(outcome, 0) + 1

    def _calculate_percentile(self, sorted_values: list[float], percentile: float) -> float | None:
        """Calculate a percentile from sorted values.

        Args:
            sorted_values: List of values sorted in ascending order
            percentile: Percentile to calculate (0.0 to 1.0)

        Returns:
            The percentile value, or None if list is empty
        """
        if not sorted_values:
            return None

        n = len(sorted_values)
        idx = int(n * percentile)
        return sorted_values[min(idx, n - 1)]

    def get_snapshot(self) -> dict[str, Any]:
        """Get a snapshot of current metrics.

        Returns:
            Dictionary with all metrics including percentiles.
        """
        with self._lock:
            # Calculate latency percentiles
            latency_p50 = None
            latency_p95 = None

            if self.command_latencies:
                sorted_latencies = sorted(self.command_latencies)
                latency_p50 = self._calculate_percentile(sorted_latencies, 0.5)
                latency_p95 = self._calculate_percentile(sorted_latencies, 0.95)

            return {
                "intent_counts": dict(self.intent_counts),
                "status_counts": dict(self.status_counts),
                "confirm_outcomes": dict(self.confirm_outcomes),
                "command_latency_ms": {
                    "p50": latency_p50,
                    "p95": latency_p95,
                    "count": len(self.command_latencies),
                },
            }

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.intent_counts.clear()
            self.status_counts.clear()
            self.confirm_outcomes.clear()
            self.command_latencies.clear()


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None
_metrics_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector instance.

    Returns:
        The global MetricsCollector instance.
    """
    global _metrics_collector
    with _metrics_lock:
        if _metrics_collector is None:
            _metrics_collector = MetricsCollector()
        return _metrics_collector


def is_metrics_enabled() -> bool:
    """Check if metrics collection is enabled via environment variable.

    Returns:
        True if HANDSFREE_ENABLE_METRICS=true, False otherwise.
    """
    import os

    return os.getenv("HANDSFREE_ENABLE_METRICS", "false").lower() in ("true", "1", "yes")
