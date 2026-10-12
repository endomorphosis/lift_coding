# Supervisor numerical obligation retrieval — 2026-10-12

The existing numerical context retained full obligations in its source reports,
but its 8,192-byte planning summary could omit every individual row. The shared
datasets pager and accelerator consumer now provide exact, bounded access to
that retained work. Complete counts by obligation kind remain in the planning
summary, with retrieval discovery and explicit omission counts.

On the permitted public `largest-eigenval` files, the hardened implementation
retrieved **45/45 pending obligations in 12 pages**. The largest complete page
was 6,282 UTF-8 bytes against an 8,192-byte bound. The summary was 8,094 bytes.
All 12 pages reproduced exactly in a fresh process after reopening the real
metadata/world DuckLakes. Exact filters and five mutation controls passed;
source files and producer hashes remained unchanged.

The datasets library owns exact source/report replay, filtering and pagination.
The supervisor additionally binds pages to the selected context receipt,
source tree and retained report, validates index bytes before following file
locators, checks report bytes before parsing, and checks currentness after
retrieval. Continuations cannot cross owners, sources or queries. Exact receipt
comparisons also reject bool/integer substitutions.

Final local validation passed **263 tests** with no failures/errors/skips:
42 datasets pager cases, 28 owner wrapper cases and 193 integration/regression
cases. Planner and coding dispatch tests use authored provider responses and
verify exact transport of the counts/discovery. A separate owner-side test
resolves an omitted row from the coding evidence's receipt reference.

This is an owner-side retrieval API. It does not yet provide an isolated coding
agent with a qualified model tool or RPC into the owner's private lakes, and
planning remains one provider request. No new live benchmark, token score,
training or proof discharge is claimed. All 45 source obligations remain
pending. The next step is a task-bound owner-mediated expansion protocol,
then a new controlled benchmark measuring every provider session.

The source-bound evidence and usage guide are published with the accelerator
implementation; the parent pins both repositories to include this change while
preserving concurrent source-view and legal-training work.

Published source revisions:

- Accelerator: `911a1cb0e6dd6585de7d19f1416637031be29961`.
- Datasets: `f47161b757190380e9898aff155067c1ad609217`.

The [bounded evidence and exact source hashes](https://github.com/endomorphosis/ipfs_accelerate_py/tree/911a1cb0e6dd6585de7d19f1416637031be29961/docs/agent_supervisor/evidence/numerical-obligation-retrieval-20261012)
retain both public probe revisions and the final local test gates. A trailing
blank line in the new integration test was removed for publication; an explicit
byte/AST comparison records the unchanged assertions. All production bytes
remain those qualified by the final tests. Local documentation gates passed.
The hosted [documentation job](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38211445466/job/114686303356)
did not start because GitHub reports an account billing lock. This is neither
a successful hosted check nor a code-test failure.
