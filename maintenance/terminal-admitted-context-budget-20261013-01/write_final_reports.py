"""Describe the selected, already completed experiment; no jobs or imports."""
import hashlib
import json
import os
from pathlib import Path
import sys

A = Path(__file__).resolve().parent
Z = A.parent / 'terminal-checked-worker-context-20261013-01'
os.umask(0o077)

def read(p):
    return json.loads(Path(p).read_bytes())

def pin(p):
    p = Path(p)
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def save(name, v):
    with (A / name).open('x') as f:
        json.dump(v, f, sort_keys=True, indent=2)
        f.write('\n')

cfg = read(sys.argv[1])
actual = read(cfg['actual_result'])
summary = read(Path(cfg['actual_public']) / 'summary.json')
model = read(cfg['model_result'])
tests = read(cfg['tests_report'])
package = read(cfg['package_report'])
inventory = read(A / 'actual-public-inventory.json')
preservation = read(A / 'preservation-final.json')
assert all(v.get('qualified') is True for v in (actual, summary, model, tests, package, inventory, preservation))
assert summary['native_admitted_benchmark_runtime_START_used'] is True
assert summary['actual_native_worker_observer_invocations'] == 1
assert tests['counts']['tests'] == tests['counts']['unique_tests'] >= 819
assert all(tests['counts'][k] == 0 for k in ('failures', 'errors', 'skips'))
assert tests['source_bytes_unchanged'] is True and len(tests['source_pins_before']) == 9
assert actual['container_disposal']['container_absent'] is True
assert actual['container_disposal']['only_exact_owned_container_removed'] is True
budget = read(Path(cfg['actual_public']) / 'final-budget-state.json')
assert budget['closed'] is True and budget['totals']['events'] == 1
assert len(budget['records']) == 1 and budget['records'][0]['status'] == 'committed'
limits = {name: False for name in (
    'full_supervisor_entrypoint_used', 'Terminal_Bench_harness_used',
    'global_task_budget_enforced', 'durable_budget_resume_supported',
    'source_to_model_equivalence_proved', 'convergence_proved',
    'full_task_satisfaction', 'completion_authority', 'proof_authority',
    'omission_authority', 'production_admitted', 'provider_usage_measured',
    'provider_billing_savings_measured', 'task_total_savings_measured',
    'source_body_executed', 'loaded_module_code_attested',
    'transitive_dependency_closure_attested', 'root_owned_source_ancestor_attestation',
    'public_broker_claim_fence_receipt_complete',
    'all_logic_families_compiled_with_Lean', 'learned_autoencoder_trained',
    'database_bodies_included', 'private_cas_bodies_included', 'ducklake_parquet_bodies_included',
    'packed_Git_objects_supported', 'repository_scale_scan_qualified',
    'Git_read_grant_snapshots_reconstitute_authority')}
report = {
    'schema': 'terminal-admitted-context-budget-qualification@1', 'qualified': True,
    'scope': 'One real admitted native START/STOP with a current authored three-module CodebaseIR, original process-local owner budget, and one isolated coding-input observer. No provider invocation.',
    'native_admitted_benchmark_runtime_START_used': True,
    'actual_native_worker_observer_invocations': 1,
    'native_kernel_wrapper_and_worker_births_verified_by_live_broker': True,
    'actual_emitted_native_stdin_budgeted_before_launch': True,
    'original_owner_budget_committed': True,
    'owner_uid': 1000, 'worker_uid': 1001,
    'whole_coding_input': summary['whole_coding_input'], 'new_content': summary['new_content'],
    'actual_budget_totals': budget['totals'], 'controls': summary['controls'],
    'model_status': model['native_summary']['model_status'],
    'metadata_rows': 49, 'metadata_family_count': 20, 'fresh_Lean_processes': 3,
    'selected_model_Lean_compile_processes': 2, 'selected_model_Lean_version_probes': 1,
    'total_recorded_native_Lean_processes_this_stage': 3 * len(cfg['native_model_qualification_results']),
    'logic_proof_scope': 'Closed conditional mathematical integer caller model; Python parsing/import/runtime equivalence and learned convergence remain unproved.',
    'broker_evidence_limit': 'Pinned source enforces current native claim, grant, attempt fence, allocation and original owner checks live. Exported birth observations do not contain a complete standalone claim/fence/input binding receipt or receipt-emitter kernel identity.',
    'Git_read_permission_scope': 'Original owner grants group read/traversal only for the exact native worktree registration, selected implementation branch and bounded current loose SHA1 commit/tree/blob DAG, retaining FD/bytes through launch. No parent history, packs, submodules or group write permissions are granted; packed and large repositories remain a separate qualification gap.',
    'Git_optional_write_prevention': 'The checked post-grant callback batch requests GIT_OPTIONAL_LOCKS=0 under original guard custody and restores the exact previous process environment before prepared acknowledgement. The cooperating-context lock does not fence unrelated threads; unchanged retained/fresh directory and file stat/byte checks remain the refusal boundary. No directory timestamp waiver.',
    'worker_readiness_scope': 'One original four-second acknowledgement window covers kernel birth and bounded sameUID metadata observation. The fixed helper waits at most two seconds for initial NoNewPrivs0 to1, preserving original UID, zero capabilities, birth, command, cwd and namespaces on every poll. Two complete NoNewPrivs1 reads and current native expiry are required before release. Failure diagnostics contain only bounded stage/type/message hash/locations; no raw stderr or authority. The delayed-readiness reproduction uses authored metadata-only children and establishes no admitted coding origin.',
    'producer_ownership_limit': 'Nine declared runtime files retain root ownership and exact bytes. Three legacy proof adapters and their read-only shared directory trust the original owner. No root-owned ancestor or loaded-module attestation.',
    'test_counts': tests['counts'], 'source_pins_unchanged': True,
    'packaged_source_test_files': package['files'], 'patch_exact_application_verified': True,
    'provider_calls': 0, 'training_steps': 0, 'project_pushes': 0,
    'owned_experiment_container_removed': True,
    'actual': pin(cfg['actual_result']), 'model': pin(cfg['model_result']),
    'tests': pin(cfg['tests_report']), 'package': pin(cfg['package_report']),
    'public_inventory': pin(A / 'actual-public-inventory.json'),
    'preservation': pin(A / 'preservation-final.json'),
    'independent_review': str(A / 'independent-review.json'),
    'independent_review_required_before_sealing': True,
    **limits,
}
save('qualification-report.json', report)
previous = read(Z / 'improvement-status.json')
gaps = previous['next_ordered_gaps']
gaps[0] = {
    'priority': 1, 'gap': 'Complete admitted dispatch evidence and live fault qualification',
    'implemented': 'Native pre-Popen owner authorization after real worktree allocation; sealed original owner reserves actual full input before the owner wrapper and UID1001 worker births; successful observed receipt commits the original reservation; STOP fences and disposes children.',
    'current_limit': 'One live positive run; adversarial refusal cases are regression tests and the cumulative retry control is pure preflight. Public broker birth observations omit a standalone signed claim/fence/allocation/input/event join.',
    'implementation': 'Export a bounded data-only native dispatch evidence record linking protected launch, current task/claim/attempt/fence, allocated worktree, input/event and both kernel births. Qualify stale head, swapped allocation, changed artifact, nonce replay, disconnect and exceeded budget through separate real admitted runs.',
    'acceptance': 'Every injected fault refuses before an unauthorized birth, any ambiguous launch stays charged, and public evidence is independently reconstructable without being mistaken for live authority.',
}
status = {
    'schema': 'terminal-admitted-context-budget-improvement-status@1',
    'qualified_this_stage': [
        'Actual AdmittedBenchmarkRuntime START emitted the prompt, allocated the worktree and reached the guarded native launch path.',
        'Original owner reservation covers the complete coding input before either authenticated launch boundary.',
        'Distinct UID1001 worker observed checked-context schema2; native STOP and outer disposal completed.',
        'Fresh conditional CodebaseIR qualification produced49 metadata rows across20 families and three genuine Lean processes.',
        f"{tests['counts']['unique_tests']} unique regression tests passed with all nine changed Python files stable; exact nine-file review patch applies.",
    ],
    'next_ordered_gaps': gaps, 'provider_calls': 0, 'training_steps': 0, 'project_pushes': 0,
    'publication_status': 'Isolated source/test review package. No GitHub or Hugging Face publication in this stage.',
    **limits,
}
save('improvement-status.json', status)
history = {
    'schema': 'terminal-admitted-context-development-history@1',
    'selected_actual_result': cfg['actual_result'], 'selected_model_result': cfg['model_result'],
    'selected_tests': cfg['tests_report'], 'selected_package': cfg['package_report'],
    'failures_retained': [
        {'attempt': 'docker-boundary-01', 'reason': 'Cached image has no /usr/bin/python3; failed before source transfer or native START; exact container disposed.'},
        {'attempt': 'docker-boundary-02', 'reason': 'Successor setup omitted CONTAINER_PYTHON import; failed before source transfer or START; exact container disposed.'},
        {'attempt': 'model-qualification-03', 'reason': 'Legacy proof-cache adapter reader requires owner-owned public source files and parent. No checker waiver; narrow ownership provisioning precedes fresh model04.'},
        {'attempt': 'model-qualification-04 export', 'reason': 'Native model and three Lean processes passed; owner export attempted a root-owned parent path. Export-only05 uses the same proved model04 in an owner-owned directory; no extra Lean/training steps.'},
        {'attempt': 'final-combined-09', 'reason': '966 of968 unique cases passed; two older inert broker fixtures still supplied partial worker identity and the removed owner cwd reader. No source bytes changed during the run. Successor fixtures explicitly mock or exercise the new closed worker-helper join; no production guard is weakened.'},
        {'attempt': 'final-combined-01', 'reason': '817 passed; one test fixture exceeded AF_UNIX path length before production socket checks. Short private fixture corrected; identical818-case population subsequently passed.'},
        {'attempt': 'review-package-01', 'reason': 'Packaging assumed full POSIX permission0644; Git preserves executable mode, not all permission bits. Source unchanged; successor verifies exact bytes and Git executable mode.'},
        {'attempt': 'actual-start-04', 'reason': 'Real START reached the broker; verification attempted a remote Quack task-list RPC while holding the owner server lock and refused before reservation or child birth. Native STOP succeeded but scope close rejected its immutable nested mapping. Exact owned container was disposed. Subsequent source fixes retain complete local task verification under the original lock and accept the native Mapping receipt with exact scalar checks.'},
        {'attempt': 'actual-start-06', 'reason': 'Real START refused before reservation or child birth because the daemon selected a long-lived exclusive coordinator connection. Native STOP and both owner close operations succeeded; zero-cost ledger closed and exact container was removed. The checked typed route now selects the existing shared process-serialized coordinator without changing its claim fence or callback semantics.'},
        {'attempt': 'actual-start-07', 'reason': 'Real START passed the native claim/coordination checks but checked-context creation refused a newly created public directory made mode0700 by owner umask077. No input charge or child birth. Native STOP and both closes succeeded; exact container removed. The scope factory now provisions only its fixed generated public child using nofollow directory FDs and explicit mode0755 for newly created directories; existing unsafe directories refuse without chmod and the checker remains unchanged.'},
        {'attempt': 'actual-start-08', 'reason': 'Real START reached checked artifact loading, whose strict worker-readable allocation check correctly refused the native owner-private worktree before its permission grant. No input charge or child birth; all cleanup succeeded and exact container removed. The scope now separates canonical data/pregrant owned-source custody from the unchanged strict allocated loader after the original wrapper permission grant.'},
        {'attempt': 'checked-dispatch-git-grant-01/02', 'reason': 'First focus attempt reached a300s shutdown timeout; its original driver did not persist partial PIPE output and therefore claims no test census. Fresh verbose/faulthandler attempt completed160cases in3.12s with143passes/17failures exposing a missing stdlib re import; an old STOP fixture leaked its socket/thread when setup raised before finally. Complete second XML/log and unqualified shutdown outcome were retained before adding the import and fixture cleanup. Exact nine source/test bytes were archived; no native authority check was waived.'},
        {'attempt': 'docker-boundary-14 successor', 'reason': 'Boundary setup qualified with its exact67402-byte broker freeze. A later metadata-only false-authority assertion changed the producer bytes; the original freeze then refused offline-cache setup before fixture/model/START. Six exact original producer files were recovered individually from the explicit public source archive, no freeze was overwritten, and the exact owned container was removed. Successor15 waits for focused broker tests before final source freeze.'},
        {'attempt': 'checked-dispatch-git-readonly-01', 'reason': '202of203cases passed; only the client import test rejected newly added standard-library contextlib by a fixed whitelist. All nine inputs were retained with source-before-19 aliases; production unchanged. Corrected whitelist then203unique cases passed, preserving original custody/nonrefund checks.'},
        {'attempt': 'checked-dispatch-worker-readiness-01', 'reason': '228of229cases passed; one old fixture expected cwd/Git as its finaltwoevents before the newly required postmetadata runlease/grant expiry checks. Exact nine inputs preserved under source-before-21 before correcting only that event-tail assertion. No production checks relaxed.'},
        {'attempt': 'actual-start-17', 'reason': '1071unique regression cases and fresh conditional model qualification passed. Optional-write prevention preserved every Git custody check and the native isolatedPopen/kernel birth was reached. The sameUID metadata helper refused its combined returncode/stdout-success condition; its stderr was discarded, so the exact predicate and writer are not established. Firstpassreturned1 instead of observer-stop75. One59118-token169371-byte reservation stayedchargedaborted. NativeSTOP/broker/guard/scope cleanup succeeded, zeroowner/worker members remained and exactcontainerremoved. Exact package13 source/test bytes are preserved under source-before-20. Source review exposes a possible UID/argv-before-NoNewPrivs initialization race, which must be reproduced or diagnosed; no successful security check may be waived.'},
        {'attempt': 'actual-start-16', 'reason': '1050unique regression cases and fresh conditional model qualification passed. Real wrapper birth and one59835-token169372-byte reservation occurred. The new selected-path diagnostic established canonical .git directory mtime/ctime drift with unchanged device/inode/mode/uid/gid/linkcount/size; refusal occurred before isolatedPopen and before fresh file revalidation. The writer and post-refusal selected-file stability are not established. NativeSTOP/broker/guard/scope cleanup succeeded, the event remained chargedaborted and exactcontainerremoved. Original diagnostic and exact package12 source/test bytes are preserved under source-before-18 aliases. The producer context relabeled a caller TimeoutError as producer custody error; this does not establish producer-byte drift.'},
        {'attempt': 'actual-start-15', 'reason': '1011regression cases and fresh conditional model qualification passed. Real wrapper birth and one59330-token169371-byte reservation occurred, then the retained Git metadata stat guard refused after final native callbacks before isolatedPopen. Public failure lacked the selectedpath/field; local nativeGit-reader reproduction didnot drift, so no cause or safe waiver was established. NativeSTOP/broker/guard/scope cleanup succeeded, eventremainedchargedaborted and exactcontainerremoved. Successor16 adds bounded selectedpath/stat/hash diagnostics only, retaining every refusal condition.'},
        {'attempt': 'actual-start-13', 'reason': 'The broker authenticated both real kernel births and the narrow UID1001 working-directory observation. The worker then failed its unchanged Git worktree lookup because newly allocated native Git registration/ref/object metadata retained owner-private umask077 permissions created after installation. One59418-token reservation stayed charged as aborted; NativeSTOP and both closes succeeded, zero owner/worker members remained and exact container was removed. Successor14 retains protected original Git metadata/object custody while granting only group read/traversal for the exact allocated registration, selected implementation branch and current loose-object DAG; worker writes to canonical Git or owner state remain forbidden.'},
        {'attempt': 'actual-start-12', 'reason': 'Batched validation reached the wrapper by the28.990s sample and completed the isolated handoff before the41.842s sample, exposing PermissionError when UID1000 directly read UID1001/proc/cwd after Popen ACK. The broker refused release, marked launch ambiguity and retained one59231-token reservation as aborted. NativeSTOP, broker drain and owner close succeeded; exact container disposed. Successor13 adds a strictly closed same-UID kernel-worktree observer mode to the existing protected worker entrypoint, with no new sudo/root privileges; birth and allocation checks remain.'},
        {'attempt': 'actual-start-11', 'reason': 'The original60s observation window retained29 nonblocking progress samples. Owner aggregateCPU increased41.887s by58.518s while broker stacks progressed through repeated semantic/capsule/projection validation; a wrapper appeared around52s but no isolated worker receipt arrived. One59134-token reservation remained charged as aborted. NativeSTOP and both closes succeeded; exact container removed. Source review identified35 direct whole-scope validations across the two handoffs; successor batches per-file immutable identity/custody reads with complete verification before and after and fresh native authority rechecks after the final callback, keeping all deadlines.'},
        {'attempt': 'actual-start-10', 'reason': 'Real wrapper birth and full59489-token reservation occurred but the60s observer deadline expired before an isolated worker birth. The nonblocking broker sample located second-handoff custody verification; it did not prove a deadlock or producer-byte drift. NativeSTOP, broker drain and owner close succeeded; one aborted reservation remained charged and exact container was disposed. Successor11 adds bounded progress/aggregateCPU samples with unchanged production checks and deadlines.'},
        {'attempt': 'actual-start-09', 'reason': 'Real native owner-wrapper birth and full59951-token reservation occurred. No isolated worker observation arrived before the bounded deadline; STOP fenced children but broker close refused a still-pending handoff. The one reservation remained charged as aborted and its owner closed; exact container was disposed. A subsequent nonblocking selected-thread diagnostic and authenticated STOP socket-drain path were added without guessing the underlying stalled call.'},
    ],
    'source_byte_changes_during_each_actual_invocation': 0, 'production_source_changes_after_final_freeze': 0,
    'historical_source_aliases': [pin(A / name) for name in ('source-before-06.json', 'source-before-07.json', 'source-before-08.json', 'source-before-09.json', 'source-before-10.json', 'source-before-11.json', 'source-before-12.json', 'source-before-13.json', 'source-before-14.json', 'source-before-15.json', 'source-before-16.json', 'source-before-17.json', 'source-before-18.json', 'source-before-19.json', 'source-before-20.json', 'source-before-21.json')],
    'private_storage_bodies_exported': False, 'provider_calls': 0, 'training_steps': 0,
}
save('development-history.json', history)
print(json.dumps({'written': ['qualification-report.json', 'improvement-status.json', 'development-history.json'],
                  'whole_input': summary['whole_coding_input'], 'tests': tests['counts']}))
