# VAI-025 MCP++ canonical source re-check

Captured: 2026-05-26T01:13:31Z / 2026-05-25 America/Los_Angeles

## Commands

```text
$ git ls-remote https://github.com/endomorphosis/mcp_plus_plus HEAD refs/heads/main refs/heads/master || true
remote: Repository not found.
fatal: repository 'https://github.com/endomorphosis/mcp_plus_plus/' not found
```

```text
$ git ls-remote https://github.com/endomorphosis/Mcp-Plus-Plus HEAD refs/heads/main refs/heads/master || true
29343be704da4e193ff143bac7daae9b0f98435d	HEAD
29343be704da4e193ff143bac7daae9b0f98435d	refs/heads/main
```

```text
$ git ls-files -s Mcp-Plus-Plus
160000 29343be704da4e193ff143bac7daae9b0f98435d 0	Mcp-Plus-Plus
```

```text
$ git -C Mcp-Plus-Plus remote -v
origin	https://github.com/endomorphosis/Mcp-Plus-Plus.git (fetch)
origin	https://github.com/endomorphosis/Mcp-Plus-Plus.git (push)
```

```text
$ git -C Mcp-Plus-Plus log -1 --oneline --decorate
29343be (HEAD -> implementation/vai-025-attempt-1-1779757879-submodule-Mcp-Plus-Plus, origin/main, origin/HEAD, main, ...) Merge pull request #3 from endomorphosis/copilot/refactor-documentation-files
```

## Source scope

The local `Mcp-Plus-Plus` checkout identifies MCP++ as a documentation-first project defining optional, backward-compatible execution profiles for MCP. Its docs index calls `docs/` the canonical documentation set for the MCP++ project, with draft profile, transport, CID artifact, UCAN, policy, event DAG, and scheduling specs.

## Decision

- Do not add a standalone submodule that points at `https://github.com/endomorphosis/mcp_plus_plus`; the requested snake-case source still returns `Repository not found`.
- Keep and wire the existing root-tracked `Mcp-Plus-Plus` gitlink as the standalone MCP++ specification source because `https://github.com/endomorphosis/Mcp-Plus-Plus.git` resolves and its `main` branch matches the recorded root pin `29343be704da4e193ff143bac7daae9b0f98435d`.
- Treat `Mcp-Plus-Plus` as the canonical spec/docs pin. Runtime MCP++ behavior remains a distributed protocol surface across SwissKnife, `ipfs_datasets_py`, and `ipfs_accelerate_py` until a reviewed standalone service implementation exists with scope distinct from those component integrations.

## Follow-up constraints

- `.gitmodules` should map the existing `Mcp-Plus-Plus` gitlink to `https://github.com/endomorphosis/Mcp-Plus-Plus.git` so `git submodule status -- Mcp-Plus-Plus` works.
- Do not rename the path to snake-case or add the broken snake-case URL.
- Do not advance the `Mcp-Plus-Plus` pin as part of this evidence refresh; the current root gitlink already matches upstream `main`.
