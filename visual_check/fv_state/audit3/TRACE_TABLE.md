# Audit3 interaction trace table (step 7)

Generated 2026-10-14T08:19:08.530Z from inventory-raw.json (census computed from the file) + P15 + audit3 fixes.

## Census — 45 apps, 1401 static controls (1095 buttons, 189 inputs, 86 selects, 31 textareas)

| App | Controls (B/I/S/T) | Class |
|---|---|---|
| terminal | 10 (8/2/0/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| vibecode | 9 (7/0/0/2) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| music-studio-unified | 42 (35/4/1/2) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| ai-chat | 16 (13/1/1/1) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| file-manager | 48 (37/8/1/2) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| task-manager | 21 (16/3/2/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| todo | 11 (7/3/1/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| model-browser | 27 (25/2/0/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| huggingface | 57 (35/13/7/2) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| openrouter | 38 (24/7/5/2) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| ipfs-explorer | 53 (43/7/3/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| device-manager | 28 (28/0/0/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| settings | 22 (5/9/8/0) | declared local / external (no ORB/IDL claim) |
| mcp-control | 61 (42/11/6/2) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| api-keys | 41 (28/9/4/0) | declared local / external (no ORB/IDL claim) |
| github | 35 (21/8/5/1) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| oauth-login | 26 (20/6/0/0) | declared local / external (no ORB/IDL claim) |
| cron | 56 (39/9/6/2) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| navi | 15 (12/1/2/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| p2p-network | 83 (78/4/1/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| p2p-chat-unified | 14 (12/1/0/1) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| neural-network-designer | 33 (27/5/0/1) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| training-manager | 37 (21/10/6/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| calculator | 113 (109/2/2/0) | declared local / external (no ORB/IDL claim) |
| clock | 27 (19/6/2/0) | declared local / external (no ORB/IDL claim) |
| calendar | 32 (20/8/3/1) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| peertube | 34 (27/5/1/1) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| friends-list | 44 (38/2/3/1) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| image-viewer | 28 (26/2/0/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| notes | 27 (23/2/1/1) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| media-player | 29 (24/4/1/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| system-monitor | 14 (10/2/2/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| neural-photoshop | 58 (44/11/3/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| cinema | 18 (16/2/0/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| strudel | 15 (14/1/0/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| strudel-ai-daw | 68 (49/11/5/3) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| music-studio | 22 (21/1/0/0) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| p2p-chat | 11 (10/0/0/1) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| datasets-browser | 8 (6/0/2/0) | generated descriptor surface (see surface table) |
| accelerate-panel | 5 (5/0/0/0) | generated descriptor surface (see surface table) |
| idl-explorer | 4 (4/0/0/0) | generated descriptor surface (see surface table) |
| glasses-preview | 7 (7/0/0/0) | generated descriptor surface (see surface table) |
| orb-auto-ui | 5 (5/0/0/0) | generated descriptor surface (see surface table) |
| mcp-plus-plus | 27 (19/3/2/3) | tool_backed — backend-connected via mediated live-tool gateway panel (P15) |
| agent-supervisor | 22 (16/4/0/2) | console — capability-mapped (see supervisor capability table) |

## Generated surfaces (source-verified control counts)

| Surface | Controls | Backend | Local | Fixed by audit3 | Typed |
|---|---|---|---|---|---|
| datasets-browser | 8 | 6 | 2 | 8 | 0 |
| accelerate-panel | 5 | 4 | 0 | 5 | 1 |
| idl-explorer | 6 | 3 | 3 | 0 | 0 |
| orb-auto-ui | 8 | 3 | 5 | 0 | 0 |
| glasses-preview | 7 | 0 | 7 | 0 | 0 |
| agent-supervisor VDA-G054 section (subset of the console census row) | 8 | 0 | 8 | 8 | 0 |

## Supervisor capabilities (15 contract capabilities; steering shown in its two modes = 16 rows)

| Capability | Owner | Disposition | Route / reason |
|---|---|---|---|
| supervisor.health.read | ipfs_accelerate_py | executes | desktop-client inspectAll across the three mediated services |
| supervisor.queue.read | ipfs_accelerate_py | executes | Profile G mcp++/tasks/list |
| supervisor.goals.read | ipfs_accelerate_py | executes | Profile G mcp++/goals/list |
| supervisor.subgoals.read | ipfs_accelerate_py | executes | Profile G mcp++/goals/list |
| supervisor.receipts.read | ipfs_kit_py | executes | Profile G tasks/list + per-task schedule status |
| supervisor.logs.read | ipfs_accelerate_py | executes — audit3 fix 3 (R-d) | accelerate adapter mcp++/dag/history backed by its real EventDag; events normalized to log entries |
| supervisor.receipts.persist | ipfs_kit_py | executes — audit3 fix 3 (R-c) | kit POST /mcp/artifacts/put; confirmation_token-gated; gateway computes the canonical CIDv1-raw+sha2-256 over the receipt bytes |
| supervisor.content.retrieve | ipfs_kit_py | executes — audit3 fix 3 (R-c) | kit GET /mcp/artifacts/<cid> |
| supervisor.event-dag.checkpoint | ipfs_kit_py | executes — audit3 fix 3 (R-c) | kit POST /mcp/dag/append; confirmation_token-gated |
| supervisor.prompt-steering.request — dry run | ipfs_accelerate_py | local preview — audit3 fix 2 (R-b) | designed local no-mutation policy preview; no backend steering route exists |
| supervisor.prompt-steering.request — confirmed | ipfs_accelerate_py | typed-unavailable | Supervisor.steer exists in the accelerate facade; NO MCP adapter route serves it — genuine backend gap, never simulated |
| supervisor.task-control.request | ipfs_accelerate_py | typed-unavailable | no gateway route exists for governed task dispatch |
| supervisor.taskboard.links.read | ipfs_datasets_py | typed-unavailable | zero implementations in ipfs_datasets_py (verified by search) |
| supervisor.run-history.search | ipfs_datasets_py | typed-unavailable | zero implementations in ipfs_datasets_py (verified by search) |
| supervisor.policy.assist | ipfs_datasets_py | typed-unavailable | zero implementations in ipfs_datasets_py (verified by search) |
| supervisor.semantic-goal.assist | ipfs_datasets_py | typed-unavailable | zero implementations in ipfs_datasets_py (verified by search) |

Capability totals: executes 9, local preview 1, typed-unavailable 6.

Unmapped-and-fixed controls: 21 (datasets-browser 8, accelerate-panel 5, VDA-G054 8). Unmapped-and-typed: 6 supervisor capabilities + accelerate Cancel (1 control). No inventoried control remains silently unmapped.
