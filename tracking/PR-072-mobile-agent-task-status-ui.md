# PR-072: Mobile agent task status UI + notifications

## Goal
Make agent delegation demoable on mobile by showing task status and speaking task completion/failure notifications.

## Why
Backend agent task lifecycle exists, and notifications are emitted; mobile needs a minimal UI to surface tasks and help the user understand progress hands-free.

## Scope
Mobile-only.

## Deliverables
- A simple "Agent Tasks" section that:
  - Lists recent tasks (poll via existing backend endpoints if available; if not, add a basic polling endpoint usage already in OpenAPI).
  - Shows state and last update.
- When a `task_completed` or `task_failed` notification arrives, speak it (can reuse PR-071 plumbing).

## Acceptance criteria
- After delegating an agent task, the mobile UI shows it within 10 seconds (poll acceptable).
- When a task completes/fails (via webhook or dev endpoints), user hears a spoken summary.

## Test plan
- Manual:
  - Create a dev task, start/complete/fail via dev endpoints, confirm UI updates and audio plays.
