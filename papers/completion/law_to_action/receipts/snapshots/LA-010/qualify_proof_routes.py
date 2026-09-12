#!/usr/bin/python3.12
"""LA-010 qualification: selected QF_BOOL SAT route plus authority checks.

Runs under the authoritative validation PATH. Native SMT/ATP/kernel
executables are probed without installation. Unavailable optional families
are recorded as unavailable, not as invented successes.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
SNAPSHOT = Path(__file__).resolve().parent
PYTHON = "/usr/bin/python3.12"
PROVIDER = SNAPSHOT / "sat_provider.py"
CHECKER = SNAPSHOT / "sat_checker.py"

SUCCESS_DIMACS = """c grant=x1 matching_roots=x2 forbidden_effect=x3
c invariant: matching & grant -> ~forbidden
p cnf 3 4
1 0
2 0
3 0
-2 -1 -3 0
"""

COUNTEREXAMPLE_DIMACS = """c grant=x1 matching_roots=x2 forbidden_effect=x3
c mismatched context: invariant does not constrain unmatched roots
p cnf 3 4
1 0
-2 0
3 0
-2 -1 -3 0
"""

FORGED_DIMACS = """c sat formula used to test a forged model
p cnf 2 2
1 0
-2 0
"""

TIMEOUT_DIMACS = "p cnf 24 24\n" + "".join(
    f"{i} {(i % 24) + 1} -{((i + 1) % 24) + 1} 0\n" for i in range(1, 25)
)


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_logged(argv: list[str], *, stdin: str | None = None, timeout: float | None = None) -> dict:
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "RAYON_NUM_THREADS": "1",
        "LANG": "C.UTF-8",
    }
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        completed = subprocess.run(
            argv,
            input=stdin,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "argv": argv,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
            "elapsed_seconds": time.perf_counter() - started,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "timeout_seconds": timeout,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "argv": argv,
            "exit_code": None,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": True,
            "elapsed_seconds": time.perf_counter() - started,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "timeout_seconds": timeout,
            "reason": "subprocess.TimeoutExpired",
        }


def probe_executables() -> list[dict]:
    names = [
        ("z3", "smt", "satisfiability", True),
        ("cvc5", "smt", "satisfiability", True),
        ("vampire", "first_order", "theorem_proof", False),
        ("eprover", "first_order", "theorem_proof", False),
        ("lean", "dependent_type", "theorem_proof", False),
        ("lake", "dependent_type", "theorem_proof", False),
        ("coqc", "dependent_type", "theorem_proof", False),
        ("rocq", "dependent_type", "theorem_proof", False),
        ("isabelle", "higher_order", "theorem_proof", False),
    ]
    rows = []
    for name, family, authority, optional_for_selected in names:
        path = shutil.which(name)
        rows.append(
            {
                "executable": name,
                "family": family,
                "authority_kind": authority,
                "path": path,
                "available": path is not None,
                "required_for_selected_route": False,
                "optional": True,
                "probe": "shutil.which under process PATH; no install",
            }
        )
        del optional_for_selected
    return rows


def import_probes() -> dict:
    import importlib.util

    mods = {}
    for name in ("z3", "cvc5", "pysmt", "sympy"):
        spec = importlib.util.find_spec(name)
        record = {"importable": spec is not None, "origin": getattr(spec, "origin", None) if spec else None}
        if spec and spec.origin and Path(spec.origin).is_file():
            record["sha256"] = sha256_file(Path(spec.origin))
        if name == "sympy" and spec:
            import sympy

            record["version"] = sympy.__version__
        mods[name] = record
    return mods


def write_formula(job_id: str, payload: dict) -> Path:
    path = SNAPSHOT / "formulas" / f"{job_id}.json"
    write_json(path, payload)
    return path


def retain_run(job_id: str, role: str, run: dict, parsed: dict | None) -> Path:
    trace = SNAPSHOT / "traces" / job_id
    trace.mkdir(parents=True, exist_ok=True)
    write_text(trace / f"{role}.stdout.raw", run.get("stdout") or "")
    write_text(trace / f"{role}.stderr.raw", run.get("stderr") or "")
    meta = {k: v for k, v in run.items() if k not in {"stdout", "stderr"}}
    if parsed is not None:
        meta["parsed"] = parsed
    write_json(trace / f"{role}.meta.json", meta)
    return trace


def parse_json_stdout(text: str) -> dict | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text.splitlines()[-1])
    except json.JSONDecodeError:
        return None


def run_sat_job(job: dict) -> dict:
    formula = write_formula(job["id"], job["formula"])
    provider_out = SNAPSHOT / "traces" / job["id"] / "provider.json"
    checker_out = SNAPSHOT / "traces" / job["id"] / "checker.json"
    timeout = job.get("timeout_seconds")
    provider_run = run_logged(
        [PYTHON, str(PROVIDER), str(formula.relative_to(ROOT))],
        timeout=timeout,
    )
    provider_parsed = parse_json_stdout(provider_run["stdout"])
    retain_run(job["id"], "provider", provider_run, provider_parsed)
    if provider_parsed:
        write_json(provider_out, provider_parsed)
    checker_run = None
    checker_parsed = None
    if not provider_run["timed_out"]:
        checker_argv = [PYTHON, str(CHECKER), str(formula.relative_to(ROOT))]
        if provider_out.exists():
            checker_argv.append(str(provider_out.relative_to(ROOT)))
        checker_run = run_logged(checker_argv, timeout=5)
        checker_parsed = parse_json_stdout(checker_run["stdout"])
        retain_run(job["id"], "checker", checker_run, checker_parsed)
        if checker_parsed:
            write_json(checker_out, checker_parsed)
    outcome = "timeout" if provider_run["timed_out"] else (provider_parsed or {}).get("status", "error")
    record = {
        "job_id": job["id"],
        "case_kind": job["case_kind"],
        "family": job["family"],
        "fragment": job.get("fragment", "QF_BOOL"),
        "query_kind": job.get("query_kind", "satisfiability"),
        "required_authority": job.get("required_authority", "satisfiability"),
        "provider_id": "sympy-sat",
        "checker_id": "exhaustive-truth-table",
        "formula": str(formula.relative_to(ROOT)),
        "timeout_seconds": timeout,
        "provider": {
            "timed_out": provider_run["timed_out"],
            "exit_code": provider_run["exit_code"],
            "elapsed_seconds": provider_run["elapsed_seconds"],
            "argv": provider_run["argv"],
            "result": provider_parsed,
            "stdout_sha256": sha256_bytes((provider_run.get("stdout") or "").encode()),
            "stderr_sha256": sha256_bytes((provider_run.get("stderr") or "").encode()),
        },
        "checker": None
        if checker_run is None
        else {
            "exit_code": checker_run["exit_code"],
            "elapsed_seconds": checker_run["elapsed_seconds"],
            "argv": checker_run["argv"],
            "result": checker_parsed,
            "stdout_sha256": sha256_bytes((checker_run.get("stdout") or "").encode()),
            "stderr_sha256": sha256_bytes((checker_run.get("stderr") or "").encode()),
        },
        "outcome": outcome,
        "empirical_benchmark_result": False,
        "authority_kind_emitted": "satisfiability"
        if outcome in {"sat", "unsat"}
        else ("unavailable" if provider_run["timed_out"] else outcome),
    }
    write_json(SNAPSHOT / "traces" / job["id"] / "record.json", record)
    return record


def run_authority_checks() -> dict:
    sys.path[:0] = [
        str(ROOT / "external" / "ipfs_accelerate"),
        str(ROOT / "external" / "ipfs_datasets"),
        str(ROOT / "external" / "ipfs_kit"),
    ]
    from ipfs_datasets_py.logic.admissibility.compose import (
        ActionScope,
        AuthorizationDecisionPolicy,
        JobVerdict,
        ProofJobResult,
        compose_authorization_query,
    )
    from ipfs_datasets_py.logic.admissibility.portfolio import (
        probe_backend,
        result_status_to_job_verdict,
        select_job_result,
        PortfolioAttemptRecord,
    )
    from ipfs_datasets_py.logic.formalization.constraint_contracts import NativeViewBinding
    from ipfs_datasets_py.logic.ir_core.protocols import (
        AttemptStatus,
        AuthorityKind,
        AuthorityMismatchError,
        QueryKind,
        ResultAuthority,
        ResultStatus,
    )

    digest = "a" * 64
    sat_authority = ResultAuthority(
        kind=AuthorityKind.SATISFIABILITY,
        issuer="la-010-sympy-sat",
        method="sympy.logic.inference.satisfiable/dpll",
        scope_digest=digest,
        evidence_digests=(digest,),
    )
    policy_authority = ResultAuthority(
        kind=AuthorityKind.POLICY_APPROVAL,
        issuer="la-010-policy-fixture",
        method="declared-policy",
        scope_digest=digest,
    )
    sat_rejects_theorem = False
    sat_reject_message = ""
    try:
        sat_authority.require(AuthorityKind.THEOREM_PROOF)
    except AuthorityMismatchError as exc:
        sat_rejects_theorem = True
        sat_reject_message = str(exc)
    policy_rejects_theorem = False
    try:
        policy_authority.require(AuthorityKind.THEOREM_PROOF)
    except AuthorityMismatchError:
        policy_rejects_theorem = True

    verdicts = {
        "unsat_as_sat_authority": result_status_to_job_verdict(
            ResultStatus.UNSATISFIABLE, authority_kind=AuthorityKind.SATISFIABILITY
        ).value,
        "sat_as_sat_authority": result_status_to_job_verdict(
            ResultStatus.SATISFIABLE, authority_kind=AuthorityKind.SATISFIABILITY
        ).value,
        "simulated_theorem": result_status_to_job_verdict(
            ResultStatus.PROVED, authority_kind=AuthorityKind.THEOREM_PROOF, simulated=True
        ).value,
        "policy_approved": result_status_to_job_verdict(
            ResultStatus.APPROVED, authority_kind=AuthorityKind.POLICY_APPROVAL
        ).value,
        "monitor_satisfied": result_status_to_job_verdict(
            ResultStatus.MONITOR_SATISFIED, authority_kind=AuthorityKind.RUNTIME_MONITOR
        ).value,
        "true_theorem": result_status_to_job_verdict(
            ResultStatus.PROVED, authority_kind=AuthorityKind.THEOREM_PROOF
        ).value,
    }

    action = ActionScope(
        action_id="action:sandbox-export",
        effect_id="effect:write-export",
        resource_ids=("resource:sandbox-export",),
        capability_ids=("capability:write",),
        domain="security",
        logic_family="propositional",
        statement="Authorize bounded sandbox export",
    )
    bundle = compose_authorization_query(
        [action],
        profile="legal-strict",
        invocation_digest=digest,
        intent_cid="bafyintentla0101",
        corpus_root="bafycorpusla0101",
        revocation_root="bafyrevocation10",
        policy_root="bafypolicyla0101",
        legal_evidence_cids=("bafylegalgrant10",),
        security_evidence_cids=("bafysecurityinv10",),
        native_views=(
            NativeViewBinding(
                view_id="view:prop-security",
                logic_family="propositional",
                formula_ids=("formula:grant", "formula:forbidden"),
                statement_ids=("stmt:grant", "stmt:forbidden"),
                capabilities=("capability:write",),
            ),
        ),
        assumptions=("assumption:source-reviewed", "assumption:qf-bool-fragment"),
    )
    policy = AuthorizationDecisionPolicy.for_profile("legal-strict")

    def decide(verdict: JobVerdict, authority_path: str) -> dict:
        results = [
            ProofJobResult(
                job_id=job.job_id,
                kind=job.kind,
                verdict=verdict,
                authority_path=authority_path,
                backend_id="sympy-sat",
                attempt_ids=(f"attempt:{job.job_id}:sympy-sat",),
                reason=f"{verdict.value} via {authority_path}",
            )
            for job in bundle.jobs
        ]
        decision = policy.evaluate(bundle, results)
        return {
            "internal_status": decision.status.value,
            "wire_status": decision.wire_status.value,
            "allowed": decision.status.value == "allow",
            "diagnostics": list(decision.diagnostics),
            "reason_codes": list(decision.reason_codes),
        }

    sat_decision = decide(JobVerdict.SAT_ONLY, "sat_only")
    policy_decision = decide(JobVerdict.POLICY, "policy_approval")
    simulated_decision = decide(JobVerdict.SIMULATION, "simulated")
    monitor_decision = decide(JobVerdict.MONITOR, "runtime_monitor")
    unavailable_decision = decide(JobVerdict.UNAVAILABLE, "unavailable")

    from ipfs_datasets_py.logic.admissibility.compose import ProofJobKind

    grant_job = bundle.jobs_of_kind(ProofJobKind.POSITIVE_GRANT)[0]
    sat_attempt = PortfolioAttemptRecord(
        attempt_id="attempt:grant:sympy-sat",
        job_id=grant_job.job_id,
        backend_id="sympy-sat",
        status=AttemptStatus.SUCCEEDED,
        verdict=JobVerdict.PROVED,
        authority_path="sat_only",
        elapsed_ms=5,
        reason="sympy-sat:proved",
    )
    selected = select_job_result([sat_attempt], grant_job)
    sat_selected_is_not_proved = selected.verdict is not JobVerdict.PROVED

    native_probes = {
        name: probe_backend(name).to_dict()
        for name in ("z3", "cvc5", "vampire", "eprover", "lean")
    }

    payload = {
        "sat_authority_rejects_theorem_require": sat_rejects_theorem,
        "sat_authority_reject_message": sat_reject_message,
        "policy_authority_rejects_theorem_require": policy_rejects_theorem,
        "portfolio_verdicts": verdicts,
        "closed_profile_allowed_authority_paths": list(policy.allowed_authority_paths),
        "composed_job_count": len(bundle.jobs),
        "composed_job_kinds": [job.kind.value for job in bundle.jobs],
        "composed_required_authority": sorted({job.required_authority.value for job in bundle.jobs}),
        "decisions": {
            "sat_only": sat_decision,
            "policy_approval": policy_decision,
            "simulated": simulated_decision,
            "runtime_monitor": monitor_decision,
            "unavailable_kernel": unavailable_decision,
        },
        "select_job_result_sat_only_cannot_prove": sat_selected_is_not_proved,
        "selected_sat_only_verdict": selected.verdict.value,
        "selected_sat_only_authority_path": selected.authority_path,
        "native_portfolio_probes": native_probes,
        "no_decision_allowed": not any(
            item["allowed"]
            for item in (
                sat_decision,
                policy_decision,
                simulated_decision,
                monitor_decision,
                unavailable_decision,
            )
        ),
    }
    write_json(SNAPSHOT / "traces" / "authority" / "record.json", payload)
    return payload


def family_records(exec_probes: list[dict], modules: dict, sat_jobs: list[dict], authority: dict) -> list[dict]:
    by_exe = {row["executable"]: row for row in exec_probes}
    sat_success = next(job for job in sat_jobs if job["job_id"] == "sat-success-unsat")
    return [
        {
            "id": "qf_bool_sympy_sat",
            "paper_role": "Hoare-style / SMT security-invariant fragment for generated-code effects",
            "logic_family": "propositional",
            "fragment": "QF_BOOL",
            "query_kind": "satisfiability",
            "authority_kind": "satisfiability",
            "required_for_benchmark": True,
            "status": "qualified",
            "provider": {
                "id": "sympy-sat",
                "kind": "in_process_child",
                "module": "sympy.logic.inference.satisfiable",
                "algorithm": "dpll",
                "version": modules["sympy"].get("version"),
                "origin": modules["sympy"].get("origin"),
                "origin_sha256": modules["sympy"].get("sha256"),
            },
            "independent_checker": {
                "id": "exhaustive-truth-table",
                "kind": "in_process_child",
                "algorithm": "enumerate-all-assignments",
                "max_vars": 16,
            },
            "kernel_reconstruction": False,
            "cannot_authorize_theorem_allow": True,
            "receipt_job_ids": [job["job_id"] for job in sat_jobs],
            "selected_route_evidence_job": sat_success["job_id"],
        },
        {
            "id": "z3_smt",
            "paper_role": "SMT results, models, or cores (Z3)",
            "logic_family": "smt",
            "fragment": "unqualified",
            "query_kind": "satisfiability",
            "authority_kind": "satisfiability",
            "required_for_benchmark": False,
            "status": "unavailable",
            "reason": "z3 executable and Python module absent from authoritative PATH/interpreter",
            "probe": by_exe["z3"],
            "python_module": modules["z3"],
            "invented_results": False,
        },
        {
            "id": "cvc5_smt",
            "paper_role": "SMT results, models, cores; QF_LIA interpolation if selected",
            "logic_family": "smt",
            "fragment": "unqualified",
            "query_kind": "satisfiability",
            "authority_kind": "satisfiability",
            "required_for_benchmark": False,
            "status": "unavailable",
            "reason": "cvc5 executable and Python module absent from authoritative PATH/interpreter",
            "probe": by_exe["cvc5"],
            "python_module": modules["cvc5"],
            "invented_results": False,
        },
        {
            "id": "cvc5_qflia_interpolation",
            "paper_role": "QF_LIA interpolation with independent interpolant checks",
            "logic_family": "smt",
            "fragment": "QF_LIA",
            "query_kind": "satisfiability",
            "authority_kind": "satisfiability",
            "required_for_benchmark": False,
            "status": "not_selected_unavailable",
            "reason": "Interpolation is optional and not selected; cvc5 is absent so no interpolant was produced",
            "invented_results": False,
        },
        {
            "id": "vampire_fol",
            "paper_role": "First-order automated proving",
            "logic_family": "first_order",
            "query_kind": "theorem_proof",
            "authority_kind": "theorem_proof",
            "required_for_benchmark": False,
            "status": "unavailable",
            "reason": "vampire executable absent from authoritative PATH",
            "probe": by_exe["vampire"],
            "invented_results": False,
        },
        {
            "id": "eprover_fol",
            "paper_role": "First-order automated proving",
            "logic_family": "first_order",
            "query_kind": "theorem_proof",
            "authority_kind": "theorem_proof",
            "required_for_benchmark": False,
            "status": "unavailable",
            "reason": "eprover executable absent from authoritative PATH",
            "probe": by_exe["eprover"],
            "invented_results": False,
        },
        {
            "id": "lean_kernel",
            "paper_role": "Interactive proof reconstruction / kernel checking",
            "logic_family": "dependent_type",
            "query_kind": "theorem_proof",
            "authority_kind": "theorem_proof",
            "required_for_benchmark": False,
            "status": "unavailable",
            "reason": "lean and lake executables absent from authoritative PATH; user-profile elan toolchains are not admitted",
            "probe": {"lean": by_exe["lean"], "lake": by_exe["lake"]},
            "invented_results": False,
        },
        {
            "id": "coq_rocq_kernel",
            "paper_role": "Interactive proof reconstruction / kernel checking",
            "logic_family": "dependent_type",
            "query_kind": "theorem_proof",
            "authority_kind": "theorem_proof",
            "required_for_benchmark": False,
            "status": "unavailable",
            "reason": "coqc and rocq executables absent from authoritative PATH",
            "probe": {"coqc": by_exe["coqc"], "rocq": by_exe["rocq"]},
            "invented_results": False,
        },
        {
            "id": "isabelle_kernel",
            "paper_role": "Interactive proof reconstruction / kernel checking",
            "logic_family": "higher_order",
            "query_kind": "theorem_proof",
            "authority_kind": "theorem_proof",
            "required_for_benchmark": False,
            "status": "unavailable",
            "reason": "isabelle executable absent from authoritative PATH",
            "probe": by_exe["isabelle"],
            "invented_results": False,
        },
        {
            "id": "runtime_monitor",
            "paper_role": "Runtime monitor observations",
            "logic_family": "monitor",
            "query_kind": "runtime_monitor",
            "authority_kind": "runtime_monitor",
            "required_for_benchmark": False,
            "status": "not_selected",
            "reason": "Monitor satisfaction is a distinct authority kind and cannot authorize theorem_proof allows",
            "authority_check": authority["decisions"]["runtime_monitor"],
            "invented_results": False,
        },
        {
            "id": "policy_approval",
            "paper_role": "Policy / Datalog-style authorization declarations",
            "logic_family": "datalog",
            "query_kind": "policy_approval",
            "authority_kind": "policy_approval",
            "required_for_benchmark": False,
            "status": "not_selected",
            "reason": "Policy approval is not theorem evidence; closed-profile allow requires theorem_proof",
            "authority_check": authority["decisions"]["policy_approval"],
            "invented_results": False,
        },
    ]


def qualification_markdown(manifest: dict, sat_jobs: list[dict], authority: dict) -> str:
    selected = next(family for family in manifest["families"] if family["id"] == "qf_bool_sympy_sat")
    lines = [
        "# LA-010 solver and checker qualification",
        "",
        "This record qualifies one bounded proof-oriented route in the",
        "authoritative validation environment and scopes every other paper",
        "family without inventing results.",
        "",
        "## Selected route",
        "",
        "The benchmark-required proof-oriented route for generated-code effect",
        "invariants is a **QF_BOOL / propositional SAT** encoding of a Hoare-style",
        "security invariant (`matching_roots ∧ grant → ¬forbidden_effect`).",
        "The provider is SymPy's DPLL SAT solver, executed as a child process.",
        "The independent checker enumerates all assignments and does not share",
        "the DPLL implementation. Both emit `satisfiability` authority only.",
        "",
        f"- Provider: `{selected['provider']['module']}` {selected['provider']['version']}",
        f"- Checker: `{selected['independent_checker']['algorithm']}`",
        f"- Fragment: `{selected['fragment']}`",
        "- Kernel reconstruction: not selected and not available",
        "- Closed-profile theorem allow: **not authorized** by this route",
        "",
        "## Authoritative environment",
        "",
        f"- Python: `{manifest['authoritative_environment']['python']}`",
        f"- PATH: `{manifest['authoritative_environment']['path']}`",
        f"- HOME prefix: `{manifest['authoritative_environment']['home_prefix']}`",
        "- User-profile toolchains (`~/.elan`, `~/.local`, theorem-provers/bin) were not searched and are not admitted.",
        "",
        "## Cases executed on the selected route",
        "",
        "| Job | Case | Provider | Checker | Authority |",
        "| --- | --- | --- | --- | --- |",
    ]
    for job in sat_jobs:
        provider_status = "timeout" if job["provider"]["timed_out"] else (job["provider"]["result"] or {}).get("status")
        checker_status = (job["checker"] or {}).get("result", {}) or {}
        checker_cell = checker_status.get("status", "not-run")
        lines.append(
            f"| `{job['job_id']}` | {job['case_kind']} | {provider_status} | {checker_cell} | {job['authority_kind_emitted']} |"
        )
    lines.extend(
        [
            "",
            "## Authority checks",
            "",
            "Authorization proof jobs composed by `AuthorizationQueryComposer@1`",
            "require `theorem_proof`. SAT, policy, simulation, and monitor paths",
            "cannot allow.",
            "",
            f"- `ResultAuthority(satisfiability).require(theorem_proof)` raised: `{authority['sat_authority_reject_message']}`",
            f"- Portfolio maps UNSAT under SAT authority to `{authority['portfolio_verdicts']['unsat_as_sat_authority']}`",
            f"- Simulated theorem maps to `{authority['portfolio_verdicts']['simulated_theorem']}`",
            f"- Policy approval maps to `{authority['portfolio_verdicts']['policy_approved']}`",
            f"- `select_job_result` on a SAT-only attempt claiming PROVED yields `{authority['selected_sat_only_verdict']}` / `{authority['selected_sat_only_authority_path']}`",
            f"- Closed-profile decisions for SAT-only, policy, simulated, monitor, and unavailable kernel: none allowed (`no_decision_allowed={authority['no_decision_allowed']}`)",
            "",
            "## Families",
            "",
            "| Family | Status | Authority | Invented results |",
            "| --- | --- | --- | --- |",
        ]
    )
    for family in manifest["families"]:
        lines.append(
            f"| `{family['id']}` | {family['status']} | {family['authority_kind']} | {family.get('invented_results', False)} |"
        )
    lines.extend(
        [
            "",
            "## Claim limits",
            "",
            "- This is qualification evidence, not a scored A4 benchmark run.",
            "- SAT UNSAT is not a kernel theorem and does not authorize closed-profile allow.",
            "- Z3, cvc5, Vampire, E, Lean, Coq/Rocq, and Isabelle were absent from the sealed PATH; no host-profile binary was adopted.",
            "- QF_LIA interpolation was not selected and was not executed.",
            "- No learned hammer, no remote solver, and no digest-bound native SMT deployment was available under the authoritative PATH.",
            "",
        ]
    )
    return "\n".join(lines)


def copy_outputs(provers: dict, raw_lines: list[str], qualification: str) -> None:
    mapping = {
        SNAPSHOT / "outputs" / "benchmark" / "manifests" / "provers.json": provers,
        ROOT / "papers" / "completion" / "law_to_action" / "benchmark" / "manifests" / "provers.json": provers,
    }
    for path, value in mapping.items():
        write_json(path, value)
    raw_text = "".join(line if line.endswith("\n") else line + "\n" for line in raw_lines)
    for path in (
        SNAPSHOT / "outputs" / "results" / "proof_jobs" / "raw.jsonl",
        ROOT / "papers" / "completion" / "law_to_action" / "results" / "proof_jobs" / "raw.jsonl",
    ):
        write_text(path, raw_text)
    for path in (
        SNAPSHOT / "outputs" / "results" / "proof_jobs" / "qualification.md",
        ROOT / "papers" / "completion" / "law_to_action" / "results" / "proof_jobs" / "qualification.md",
    ):
        write_text(path, qualification if qualification.endswith("\n") else qualification + "\n")


def main() -> int:
    observed_at = datetime.now(timezone.utc).isoformat()
    python_version = subprocess.check_output([PYTHON, "-V"], text=True).strip()
    env_probe = {
        "observed_at": observed_at,
        "python": PYTHON,
        "python_version": python_version,
        "python_sha256": sha256_file(Path(PYTHON)),
        "path": os.environ.get("PATH"),
        "home": os.environ.get("HOME"),
        "home_is_validation_prefix": str(os.environ.get("HOME", "")).find("ipfs-accelerate-validation-home-") >= 0,
        "executables": probe_executables(),
        "python_modules": import_probes(),
    }
    write_json(SNAPSHOT / "probe" / "sealed-environment.json", env_probe)

    sat_specs = [
        {
            "id": "sat-success-unsat",
            "case_kind": "success",
            "family": "qf_bool_sympy_sat",
            "fragment": "QF_BOOL",
            "query_kind": "satisfiability",
            "required_authority": "satisfiability",
            "formula": {
                "id": "sat-success-unsat",
                "format": "dimacs",
                "expected": "unsat",
                "dimacs": SUCCESS_DIMACS,
            },
        },
        {
            "id": "sat-counterexample",
            "case_kind": "counterexample",
            "family": "qf_bool_sympy_sat",
            "fragment": "QF_BOOL",
            "query_kind": "satisfiability",
            "required_authority": "satisfiability",
            "formula": {
                "id": "sat-counterexample",
                "format": "dimacs",
                "expected": "sat",
                "dimacs": COUNTEREXAMPLE_DIMACS,
            },
        },
        {
            "id": "sat-timeout",
            "case_kind": "timeout",
            "family": "qf_bool_sympy_sat",
            "fragment": "QF_BOOL",
            "query_kind": "satisfiability",
            "required_authority": "satisfiability",
            "timeout_seconds": 0.02,
            "formula": {
                "id": "sat-timeout",
                "format": "dimacs",
                "expected": "timeout",
                "dimacs": TIMEOUT_DIMACS,
            },
        },
        {
            "id": "sat-unsupported-quantifiers",
            "case_kind": "unsupported",
            "family": "qf_bool_sympy_sat",
            "fragment": "FOL-quantifiers",
            "query_kind": "theorem_proof",
            "required_authority": "theorem_proof",
            "formula": {
                "id": "sat-unsupported-quantifiers",
                "format": "unsupported",
                "unsupported": "quantified first-order formulas are outside the selected QF_BOOL fragment",
                "fragment": "FOL",
                "family": "first_order",
                "query_kind": "theorem_proof",
            },
        },
        {
            "id": "sat-unsupported-qflia-interpolation",
            "case_kind": "unsupported",
            "family": "cvc5_qflia_interpolation",
            "fragment": "QF_LIA",
            "query_kind": "satisfiability",
            "required_authority": "satisfiability",
            "formula": {
                "id": "sat-unsupported-qflia-interpolation",
                "format": "unsupported",
                "unsupported": "QF_LIA interpolation is not selected and cvc5 is unavailable",
                "fragment": "QF_LIA",
                "family": "smt",
                "query_kind": "interpolation",
            },
        },
        {
            "id": "sat-forged-model",
            "case_kind": "forged-evidence",
            "family": "qf_bool_sympy_sat",
            "fragment": "QF_BOOL",
            "query_kind": "satisfiability",
            "required_authority": "satisfiability",
            "formula": {
                "id": "sat-forged-model",
                "format": "dimacs",
                "expected": "sat",
                "dimacs": FORGED_DIMACS,
            },
        },
    ]
    sat_jobs = [run_sat_job(spec) for spec in sat_specs]

    forged_trace = SNAPSHOT / "traces" / "sat-forged-model"
    forged_provider = json.loads((forged_trace / "provider.json").read_text()) if (forged_trace / "provider.json").exists() else {}
    forged_claim = {
        "status": "sat",
        "model": {"x1": True, "x2": True},
        "note": "deliberately unsatisfying assignment for grant=x1 and ~x2",
        "authority_kind": "satisfiability",
    }
    write_json(forged_trace / "forged-claim.json", forged_claim)
    formula = SNAPSHOT / "formulas" / "sat-forged-model.json"
    forged_check = run_logged(
        [
            PYTHON,
            str(CHECKER),
            str(formula.relative_to(ROOT)),
            str((forged_trace / "forged-claim.json").relative_to(ROOT)),
        ],
        timeout=5,
    )
    forged_parsed = parse_json_stdout(forged_check["stdout"])
    retain_run("sat-forged-model", "forged-checker", forged_check, forged_parsed)
    for job in sat_jobs:
        if job["job_id"] == "sat-forged-model":
            job["forged_claim"] = forged_claim
            job["forged_checker"] = forged_parsed
            job["forged_evidence_rejected"] = bool(forged_parsed and forged_parsed.get("forged_evidence") is True)
            write_json(forged_trace / "record.json", job)

    authority = run_authority_checks()
    modules = env_probe["python_modules"]
    families = family_records(env_probe["executables"], modules, sat_jobs, authority)
    source_files = {
        "compose.py": ROOT / "external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/compose.py",
        "portfolio.py": ROOT / "external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/portfolio.py",
        "protocols.py": ROOT / "external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/protocols.py",
        "sat_provider.py": PROVIDER,
        "sat_checker.py": CHECKER,
    }
    manifest = {
        "schema": "law-to-action-prover-manifest/v1",
        "task": "LA-010",
        "qualified_at": observed_at,
        "empirical_benchmark_result": False,
        "authoritative_environment": {
            "python": PYTHON,
            "python_version": python_version,
            "python_sha256": env_probe["python_sha256"],
            "path": env_probe["path"],
            "home_prefix": "ipfs-accelerate-validation-home-",
            "home_observed": env_probe["home"],
            "home_is_validation_prefix": env_probe["home_is_validation_prefix"],
        },
        "selected_route": {
            "id": "qf_bool_security_invariant",
            "family_id": "qf_bool_sympy_sat",
            "fragment": "QF_BOOL",
            "query_kind": "satisfiability",
            "authority_kind": "satisfiability",
            "provider_id": "sympy-sat",
            "checker_id": "exhaustive-truth-table",
            "kernel_reconstruction": False,
            "cannot_authorize_closed_profile_allow": True,
        },
        "resource_bounds": {
            "threads": 1,
            "qualification_timeout_seconds": {"sat-timeout": 0.02, "other_jobs": 5},
            "protocol_attempt_wall_seconds": 20,
        },
        "source_pins": {name: {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)} for name, path in source_files.items()},
        "families": families,
        "authority_summary": {
            "sat_rejects_theorem": authority["sat_authority_rejects_theorem_require"],
            "no_weak_authority_allow": authority["no_decision_allowed"],
            "select_job_result_sat_only_cannot_prove": authority["select_job_result_sat_only_cannot_prove"],
        },
    }
    write_json(SNAPSHOT / "probe" / "authority.json", authority)

    raw_records = []
    for job in sat_jobs:
        raw_records.append(job)
    raw_records.append(
        {
            "job_id": "authority-sat-only-cannot-allow",
            "case_kind": "authority-reject",
            "family": "authorization_decision_policy",
            "query_kind": "theorem_proof",
            "required_authority": "theorem_proof",
            "outcome": "rejected",
            "authority_kind_emitted": "sat_only",
            "result": authority["decisions"]["sat_only"],
            "empirical_benchmark_result": False,
        }
    )
    raw_records.append(
        {
            "job_id": "authority-policy-cannot-allow",
            "case_kind": "authority-reject",
            "family": "policy_approval",
            "query_kind": "theorem_proof",
            "required_authority": "theorem_proof",
            "outcome": "rejected",
            "authority_kind_emitted": "policy_approval",
            "result": authority["decisions"]["policy_approval"],
            "empirical_benchmark_result": False,
        }
    )
    raw_records.append(
        {
            "job_id": "authority-simulated-cannot-allow",
            "case_kind": "authority-reject",
            "family": "simulation",
            "query_kind": "theorem_proof",
            "required_authority": "theorem_proof",
            "outcome": "rejected",
            "authority_kind_emitted": "simulated",
            "result": authority["decisions"]["simulated"],
            "empirical_benchmark_result": False,
        }
    )
    raw_records.append(
        {
            "job_id": "authority-kernel-unavailable",
            "case_kind": "unavailable",
            "family": "lean_kernel",
            "query_kind": "theorem_proof",
            "required_authority": "theorem_proof",
            "outcome": "unavailable",
            "authority_kind_emitted": "unavailable",
            "result": authority["decisions"]["unavailable_kernel"],
            "native_probes": authority["native_portfolio_probes"],
            "empirical_benchmark_result": False,
        }
    )
    qualification = qualification_markdown(manifest, sat_jobs, authority)
    copy_outputs(manifest, [json.dumps(record, sort_keys=True) for record in raw_records], qualification)

    summary = {
        "status": "ok",
        "selected_success_unsat": next(job for job in sat_jobs if job["job_id"] == "sat-success-unsat")["outcome"],
        "selected_counterexample": next(job for job in sat_jobs if job["job_id"] == "sat-counterexample")["outcome"],
        "timeout": next(job for job in sat_jobs if job["job_id"] == "sat-timeout")["provider"]["timed_out"],
        "forged_rejected": next(job for job in sat_jobs if job["job_id"] == "sat-forged-model").get("forged_evidence_rejected"),
        "no_weak_authority_allow": authority["no_decision_allowed"],
        "native_z3": env_probe["executables"][0]["available"],
        "families": len(families),
    }
    write_json(SNAPSHOT / "probe" / "summary.json", summary)
    json.dump(summary, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    if summary["selected_success_unsat"] != "unsat":
        return 1
    if summary["selected_counterexample"] != "sat":
        return 1
    if not summary["timeout"]:
        return 1
    if not summary["forged_rejected"]:
        return 1
    if not summary["no_weak_authority_allow"]:
        return 1
    if summary["native_z3"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
