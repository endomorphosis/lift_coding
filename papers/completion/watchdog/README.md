# Three-paper board watchdog

Native Quack boards for Autoformalization, Law to Action, and Neurosymbolic
Supervision are inspected every 10 minutes by a durable Grok scheduler. The
local helper is:

```sh
python3 scripts/paper_board_watchdog.py
```

It writes `latest.json` and appends `journal.jsonl`. It restarts a dead
campaign controller only when incomplete native work remains. It never marks a
scientific task complete.

Markdown `paper.todo.md` files are reviewed import sources, not the live board.
Live remaining work is currently Law LA-032/LA-031, held by a registration hold
for a bounded host model owner and restricted worker transport.
