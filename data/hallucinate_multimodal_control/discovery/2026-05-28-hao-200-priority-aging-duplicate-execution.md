# HAO-200 Fix: Priority Aging Duplicate Task Execution

Date: 2026-05-28
Task: HAO-200
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/advanced_thread_pool_manager.py:1171

## Finding

The `_apply_task_aging` method in `AdvancedThreadPoolManager` attempted to boost a
waiting task's priority by creating a new `PrioritizedTask` with a lower priority
value and calling `current_queue.put(boosted_task)`. However, the original task
object was left in the queue in `PENDING` state. The annotated comment read:

```
# This is a hack that depends on queue implementation
```

## Root Cause

`PriorityQueue.put()` appends; it does not replace. After the aging call, two
entries for the same logical task existed in the queue:

1. The original `task` (higher priority number = lower urgency) still in `PENDING`
2. The `boosted_task` (lower priority number = higher urgency) newly enqueued

`pool.active_tasks[task_id]` was updated to `boosted_task`, so once
`boosted_task` was dequeued and executed it deleted that dict entry. When the
worker later dequeued the original `task`, its `state` was still `PENDING`, so
the worker executed the underlying function a second time and attempted to set the
already-resolved `Future` again.

## Fix

Before calling `current_queue.put(boosted_task)`, set the original task's state
to `TaskState.CANCELLED`. The `_task_scheduler` worker already handles `CANCELLED`
by calling `task_done()` and continuing without executing, so the original entry
in the queue is safely discarded without double-execution.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/advanced_thread_pool_manager.py
```

Passes cleanly.
