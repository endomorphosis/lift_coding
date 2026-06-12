# VAI-025 MCP++ canonical source re-check

Captured: 2026-06-12T07:04:42Z

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
$ git config -f .gitmodules --get-regexp 'submodule\..*Mcp-Plus-Plus|submodule\..*mcp'
submodule.Mcp-Plus-Plus.path Mcp-Plus-Plus
submodule.Mcp-Plus-Plus.url https://github.com/endomorphosis/Mcp-Plus-Plus.git
```

```text
$ git submodule status -- Mcp-Plus-Plus
 29343be704da4e193ff143bac7daae9b0f98435d Mcp-Plus-Plus (heads/implementation/vai-001-attempt-1-1781237885-submodule-Mcp-Plus-Plus)
```

```text
$ git -C Mcp-Plus-Plus remote -v
origin	https://github.com/endomorphosis/Mcp-Plus-Plus.git (fetch)
origin	https://github.com/endomorphosis/Mcp-Plus-Plus.git (push)
```

```text
$ git -C Mcp-Plus-Plus rev-parse HEAD
29343be704da4e193ff143bac7daae9b0f98435d
```

```text
$ git -C Mcp-Plus-Plus log -1 --oneline --decorate=short --decorate-refs=refs/heads/main --decorate-refs=refs/remotes/origin/main --decorate-refs=refs/remotes/origin/HEAD
29343be (origin/main, origin/HEAD, main) Merge pull request #3 from endomorphosis/copilot/refactor-documentation-files
```

## Decision

- Do not add a standalone submodule that points at `https://github.com/endomorphosis/mcp_plus_plus`; the requested snake-case source still returns `Repository not found`.
- Keep the existing root-tracked `Mcp-Plus-Plus` gitlink as the standalone MCP++ specification and documentation source because `https://github.com/endomorphosis/Mcp-Plus-Plus.git` resolves and its `main` branch still matches the recorded root pin `29343be704da4e193ff143bac7daae9b0f98435d`.
- Do not advance the `Mcp-Plus-Plus` root gitlink for this re-check; the current pin already matches the upstream `main` ref.
- Runtime MCP++ behavior remains a distributed protocol surface across SwissKnife, `ipfs_datasets_py`, and `ipfs_accelerate_py` until a reviewed standalone service implementation exists with scope distinct from those component integrations.

## Follow-up constraints

- Keep root `.gitmodules` mapped to `https://github.com/endomorphosis/Mcp-Plus-Plus.git`.
- Do not rename the path to snake-case or add the broken snake-case URL.
- Re-open the standalone runtime-service decision only if a distinct implementation upstream appears and can be reviewed without duplicating the current distributed MCP++, ORB, and routing surfaces.
