# Android Emulator in Docker (Exploration Notes)

This is a planning doc for a Docker-based Android emulator runner.

Key questions to answer:
- Which base image? (e.g., budtmo/docker-android or custom)
- How to expose ADB reliably?
- What networking model do we want (backend in same compose network vs host)?
- How to require and validate KVM (`/dev/kvm`) at startup?

This doc is intentionally lightweight and meant to support parallel implementation.
