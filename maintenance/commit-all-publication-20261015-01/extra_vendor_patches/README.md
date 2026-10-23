# Preserved third-party source changes

These patches preserve existing local edits discovered in nested repositories. They are inactive historical alternatives, not a claim that the changes are tested, accepted upstream, or part of a benchmark runtime. Original checkouts are unchanged. Duplicate copies are recorded with their own original paths. Each patch applies only to its recorded repository base commit.

The patches use zero context to avoid copying unrelated sensitive source. In a separate disposable checkout at the exact recorded base commit, use `git apply --check --unidiff-zero PATCH` and `git apply --unidiff-zero PATCH`. Compare the resulting file SHA256 values with `manifest.json`. Do not apply these commands to a live checkout with existing changes.

Recorded validation used read-only reverse patch checks against the actual changed working files, source hashes, credential-pattern scanning, and Python AST parsing. No third-party code was imported or executed. Inherited Python syntax failures, if any, are retained as findings, not repaired silently. Root license and notice files are copied from each pinned base; attribution and source licensing continue to apply.
