# VAI-013 MCP++ Canonical Source Resolution

Captured: 2026-06-23T06:22:05Z

## Commands

```text
$ git ls-remote https://github.com/endomorphosis/mcp_plus_plus HEAD refs/heads/main refs/heads/master || true
remote: Repository not found.
fatal: repository 'https://github.com/endomorphosis/mcp_plus_plus/' not found
```

```text
$ git ls-remote https://github.com/endomorphosis/Mcp-Plus-Plus.git HEAD refs/heads/main refs/heads/master || true
29343be704da4e193ff143bac7daae9b0f98435d	HEAD
29343be704da4e193ff143bac7daae9b0f98435d	refs/heads/main
```

```text
$ git ls-files -s Mcp-Plus-Plus
160000 29343be704da4e193ff143bac7daae9b0f98435d 0	Mcp-Plus-Plus
```

```text
$ git submodule status Mcp-Plus-Plus
 29343be704da4e193ff143bac7daae9b0f98435d Mcp-Plus-Plus (heads/implementation/vai-001-attempt-1-1781237885-submodule-Mcp-Plus-Plus)
```

```text
$ git config -f .gitmodules --get-regexp 'submodule\.Mcp-Plus-Plus\.(path|url)'
submodule.Mcp-Plus-Plus.path Mcp-Plus-Plus
submodule.Mcp-Plus-Plus.url https://github.com/endomorphosis/Mcp-Plus-Plus.git
```

## Decision

- Do not add a lowercase `mcp_plus_plus` root submodule; the requested snake-case upstream still returns `Repository not found`.
- Keep the existing case-sensitive `Mcp-Plus-Plus` gitlink as the standalone MCP++ spec/docs source because `https://github.com/endomorphosis/Mcp-Plus-Plus.git` resolves and its `main` ref matches the root gitlink `29343be704da4e193ff143bac7daae9b0f98435d`.
- Keep root `.gitmodules` mapped to `https://github.com/endomorphosis/Mcp-Plus-Plus.git`; no pin or path change is needed.
- Runtime MCP++ behavior remains a distributed protocol surface across SwissKnife, `ipfs_datasets_py`, and `ipfs_accelerate_py` unless a distinct standalone implementation is reviewed and pinned separately.
