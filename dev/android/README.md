# Android (Termux) Dev Tools

This folder contains small utilities intended to run on an Android phone via Termux.

## termux_github_dispatcher.py

A tiny HTTP server that creates GitHub issues in a dispatch repo.

### Setup (Termux)

```bash
pkg update
pkg install python
pip install --upgrade pip
pip install httpx
```

### Run

```bash
export GITHUB_TOKEN="<your_pat>"
export DISPATCH_REPO="owner/repo"

python dev/android/termux_github_dispatcher.py --host 0.0.0.0 --port 8765
```

### Test

```bash
curl -sS -X POST http://127.0.0.1:8765/dispatch \
  -H 'Content-Type: application/json' \
  -d '{"title":"Test dispatch","body":"hello from phone","labels":["agent-task"]}' | cat
```
