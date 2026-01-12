# HandsFree Dev Companion — Overview

## What this is
A hands-free assistant that lets you stay productive while your hands are occupied (lifting, cooking, walking, commuting).
It connects wearable inputs (voice + optional camera) to developer workflows (PRs, issues, CI, agent tasks) and returns
short, safe, spoken feedback.

## Primary capabilities
- PR inbox + spoken summaries
- CI / check status and alerts
- Safe actions: comment, request review, rerun checks, merge-under-policy
- Delegate tasks to coding agents (Copilot or custom agents) with progress updates
- Profiles for different contexts (Workout, Kitchen, Walk, Commute)
- Tight dev loop with VS Code: local simulator, fixtures, contract tests, and CI

## Non-goals (for MVP)
- Full IDE-in-the-glasses
- Long-form code editing by voice
- Always-on wake word (start with push-to-talk)

## Design principles
- Lowest cognitive load: short prompts, minimal back-and-forth
- Safety first: confirmation + policy gates for risky actions
- Event-driven: notify only when useful, batch updates
- Extensible: integrations are plugins; commands are intents + tools
- Debuggable: simulate the wearable + deterministic fixtures for every integration
