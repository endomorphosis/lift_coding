# Paper supervisor runtime bootstrap

These files record local setup and source provenance. They are not paper experimental results.

- `lane_bootstrap.json`: per-paper integration branches, parent/runtime commits, clean status, and local clone URIs.
- `lane_source_snapshot.json`, `accelerate_runtime_snapshot.patch`, `accelerate_quack_session_sql_test.py`: the frozen canonical tracked runtime changes and focused test copied into each lane.
- `tex_validation.json`, `tex_installation_provenance.json`, `tex_installed_packages.txt`, `tex_template_build.log`: successful user-local TeX Live installation and exact supplied-template compilation.

The parent coordinator will sync updated helpers and these bootstrap records into each lane before launch. Runtime accelerator commits currently live in the lane-local repositories; use their recorded lane_repository_uri when resolving new commits for worker submodule clones. Origin still points to the canonical local checkout, which does not automatically contain the new lane commits. No nested submodule recursion or supervisor launch was performed by this bootstrap.

For a worker with a minimal PATH, use:

```bash
/home/barberb/.local/bin/vericodegen-latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

Submodule child reachability was qualified with the actual native offline initializer and exactly three explicit dependencies. `lane_submodule_config.json` records per-worktree local URLs, and `native_submodule_proof.json` records exact pinned child heads, shared lane-local object stores, and completed cleanup. `native_submodule_proof.py` reproduces this scoped bootstrap check without starting a daemon or provider. Per-worktree Git config is not generally inherited by newly created worktrees; the native initializer succeeds by resolving `repo_root / dependency_path` and creating a linked worktree directly from that source. A generic child-side Git fallback must receive its own local URL overrides if it is used before native initialization.
