This proposal expands the generated-program boundary for the sixty prepared
task cases. It is an implementation design, not a qualification or scientific
result. It binds the frozen candidate source inventory at
`../law_study_preparation_20260914/source_preparation_inventory.json`; source
eligibility and the original 900-cell schedule remain separate admission gates.

Use a declared Python syntax subset interpreted from the exact generated UTF-8
bytes. One `run(payload)` function may use local assignment, literals, indexing,
bounded `for`, `if`, arithmetic, comparisons, Boolean expressions and `return`.
Calls must name sealed primitives directly. Reject imports, attributes,
reflection, decorators, annotations, type parameters, classes, closures,
user-defined helper functions, recursion, generators, comprehensions, arbitrary
exceptions, dynamic call targets and file/module objects. The interpreter
passes only bounded JSON-shaped values and never invokes Python `eval` or
`exec` on candidate bytes. Supported pure semantics must be checked against
CPython on constructed examples; this is not support for unrestricted Python.

The candidate computes its decisions and output data. General primitives can
encode JSON/base64, hash/HMAC, split/replace/join text, inspect collections and
serialize data. No primitive takes a task ID or returns the task's final
expected answer. Files, database records, configuration and service state are
accessible only through separately audited effect primitives. Generic parser,
template and fixed-program adapters expose their actual selected parameters,
results and nested effects; they do not force the safe task-specific choice
inside a hidden solver.

| Primitive group | Proposed interface | Candidate's responsibility |
| --- | --- | --- |
| Pure values | `length`, `keys`, `append`, `text_lower`, `text_replace`, `text_split`, `text_join`, `url_parse`, `safe_path_join`, `json_parse`, `json_encode`, `base64url_encode`, `base64url_decode`, `sha256`, `hmac_sha256`, `constant_time_equal` | Select fields, calculate amounts/scores, validate claims/time windows, build names/configuration and decide which operation to request |
| Files | `read_text(path)`, `write_text(path,text)`, `write_json(path,value)`, `list_files(prefix)`, `copy_file(source,destination)` | Choose the correct source/destination and preserve/redact/filter bytes; path normalization does not decide the task's permitted subset |
| State | `state_read(store,key)`, `state_write(store,key,value)`, `state_delete(store,key)`, `state_compare_delete(store,key,expected)` | Check trusted session/permission data and decide read/write/delete; compare-and-delete is generic atomic storage, not a backup-code solver |
| Local service/event sinks | `fixture_query(service,request)`, `emit_event(channel,value)` | Construct the request, enforce the task's preconditions, compute/project the returned raw fixture data, and route keys/notices correctly |
| SQLite | `sqlite_query(database,sql,parameters)` | Construct the query and bind literal parameters. A0-A2 can submit unsafe SQL inside the isolated fixture database so the contrast is observable; global containment limits writes/resources uniformly |
| XML | `xml_parse(text,options)` returning a bounded structural tree | Choose entity/network options and extract the requested literal text; all resolver reads pass through the effect dispatcher with no unobserved default fallback |
| Templates | `template_render(template,variables,environment)` | Select the standard sandbox environment and handle success/error; actual variable state before/after is observed. Dangerous host object/module access is excluded uniformly by the declared template adapter profile |
| Archives | `archive_list(path)`, `archive_extract_member(path,member,destination)` | Calculate ancestor/file budgets, choose permitted regular members and destination paths, and stop when a limit is exhausted |
| Fixed programs | `run_program(program_id,argv)` | Select the program and exact argument vector; IDs resolve to pinned binaries. Benign disallowed-program controls remain callable in A0-A2 inside the fixture boundary, so A4 denial is observable |

Effect handlers must never use expected outputs or the oracle implementation.
The universal containment boundary is the complete isolated fixture tree;
each task's permitted directory is a narrower policy boundary. A normalized
write outside `data/` but inside that fixture tree can therefore be observed
in A0-A2 and denied by A4. Shared path containment must not accidentally enforce
every task policy in all arms and erase the intended contrast.
Each task's trusted initial fixtures, model-visible input and hidden oracle are
separate. The task specifies a bounded local policy independently of candidate
bytes. Policy defines resources, operations, parameter constraints and declared
secret-field/flow constraints. JSON leaf provenance should propagate through
pure operations and branch contexts for the declared output-flow checks;
covert timing channels or general noninterference are not claimed.

The real native fact extractor first observes the exact candidate bytes.
Independently enumerated supported direct call sites must reconcile with its
mapped calls, including repeated/conditional sites. Pure primitive names are
authorized by the frozen language profile; effect names and resources are
authorized by the task policy. Unsupported or incomplete extraction remains a
failed candidate, never silently accepted as an empty fact set.

Native invocation checks then apply to every actual effect using its evaluated
arguments. A0/A1/A2 share the same containment and handlers; policy/retrieval
differences belong in the qualified model prompt. A3 applies the actual native
declared-policy and UCAN verifier. A4 adds checked policy obligations,
context-bound receipts/capabilities, durable consumption and
`SupervisorPreInvocationEnforcement.authorize_and_delegate` around the real
handler invocation. Fresh effect-index nonces bind candidate hash, task hash,
argument/resource digests and prior state version. Nested XML resolver reads
and parser/template effects cannot bypass this path.

The old `baselines.run_ucan_policy` hardcodes `export_json` and one resource;
`check_obligation` also instantiates the old export-effect formula. Reusing
these wrappers unchanged would not authorize the new operations correctly.
The new adapter must use the underlying real UCAN/AuthorizationGate and native
receipt/enforcement APIs with the actual operation/resource and a reviewed
generic policy predicate compiler. Native libraries and historical receipts
stay unchanged. Actual API acceptance and negative controls are required
before claiming this integration works.

The parent observer must independently snapshot and hash fixture files/state,
check an append-only trusted event stream, and reconcile every reserved,
admitted, started and completed effect. The candidate cannot write that stream
or return observation-complete flags. Missing events, incomplete reads, torn
receipts or unknown descendant counters remain unknown/failure. Allowed useful
work requires both the independent oracle and complete observed effects;
merely generating a safe-looking program or returning success is insufficient.

Implement and qualify the common interpreter, generic file/state/event
handlers and actual A4 delegation first on constructed examples that perform
real computation, allowed writes, disallowed writes and repair. Next add the
generic library/program adapters needed by the coverage table, with exact
dependencies and source-specific limitations preserved. A constructed
development example is not one of the thirty scientific family batches.
The parent is separately qualifying cgroup observation diagnostics, and the
other agent is preparing model transport. No model calls or scientific
admission are authorized by this design document.
