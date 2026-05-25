# MGW-014 Validation Guardrail Report

Date: 2026-05-22
Task: MGW-014 Add supervisor validation-environment and retry-budget guardrails
Outcome: Added repo-local Android validation environment enforcement and retry-budget discovery generation.

## Evidence

MGW-010 repeatedly failed daemon validation because the daemon ran:

```bash
cd mobile/android && ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false
```

under the shell default Java 8 runtime. Gradle failed before compiling the Android display bridge with:

```text
Dependency requires at least JVM runtime version 11. This build uses a Java 8 JVM.
```

The task agents then proved the same Android bridge-only build passed when `JAVA_HOME` pointed at the repo-local JDK 17 under `.tools/jdk17/jdk-17.0.18+8`.

## Guardrails

- The display-widget daemon and supervisor wrappers now bootstrap `JAVA_HOME`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, and `PATH` from repo-local `.tools` paths before importing or spawning the upstream implementation-daemon package.
- The supervisor-managed child daemon command is routed through `scripts/meta_glasses_display_todo_daemon.py`, so the child process also enforces the same environment.
- Bare Android Gradle validation commands in the MGW board are normalized to include the repo-local JDK/Android SDK environment.
- Repeated validation failures now have a retry budget. For active non-completed tasks, the wrapper writes a discovery report, appends a daemon-parseable follow-up MGW task, and adds the source task to strategy `blocked_tasks` instead of allowing indefinite retries.

## Validation

The MGW-014 validation commands are:

```bash
PYTHONPATH=external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py
PYTHONPATH=external/ipfs_datasets python3 scripts/meta_glasses_display_todo_supervisor.py --once
```
