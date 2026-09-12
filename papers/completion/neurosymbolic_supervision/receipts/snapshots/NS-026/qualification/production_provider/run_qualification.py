#!/usr/bin/env python3
"""NS-026 production-provider qualification. Executes real dispatch and historical materialization."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for candidate in [cur, *cur.parents]:
        marker = candidate / "papers/completion/neurosymbolic_supervision/protocol/experiment_manifest.json"
        if marker.is_file():
            return candidate
    raise SystemExit("cannot locate repository root")


ROOT = _repo_root()
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
EXP = PAPER / "experiments"
QUAL = PAPER / "qualification" / "production_provider"
PYTHON = sys.executable


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = obj if isinstance(obj, str) else canonical(obj) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def run(argv, *, cwd=None, timeout=180, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    raise SystemExit("Retained pre-recovery draft only: this script would create another independent fixture call. It is disabled. Use host_service/README.md and an exact reviewed host grant; preserve prior consumed effects and results.")
    started = utcnow()
    origin = time.perf_counter()
    QUAL.mkdir(parents=True, exist_ok=True)
    store = Path(tempfile.mkdtemp(prefix="ns026-upstream-"))
    report = {
        "schema": "paper-ns-026-qualification/v1",
        "started_at": started,
        "commands": {},
        "checks": [],
        "ok": False,
    }

    probe_out = QUAL / "probe.json"
    probe = run(
        [PYTHON, str(EXP / "production_gateway.py"), "probe", "--out", str(probe_out)],
        timeout=30,
    )
    report["commands"]["probe"] = {
        "exit_code": probe.returncode,
        "stdout_tail": probe.stdout[-1500:],
        "stderr_tail": probe.stderr[-1500:],
    }
    if probe.returncode != 0 or not probe_out.is_file():
        report["error"] = "gateway probe failed"
        atomic_write(QUAL / "qualification_report.json", report)
        return 1
    probe_data = load(probe_out)
    report["checks"].append(
        {
            "name": "production_not_admitted",
            "ok": probe_data["production"]["admitted"] is False,
        }
    )
    report["checks"].append(
        {
            "name": "development_amendment_frozen",
            "ok": bool(probe_data.get("amendment_id")),
            "amendment_id": probe_data.get("amendment_id"),
        }
    )

    # --- actual development provider invocation ---
    dev_dir = QUAL / "development_invocation"
    dev_dir.mkdir(parents=True, exist_ok=True)
    ledger = Path(tempfile.mkdtemp(prefix="ns026-dev-ledger-"))
    attempt_path = dev_dir / "attempt.json"
    argv = [
        PYTHON,
        str(EXP / "run_comparison.py"),
        "one-task",
        "--task-id",
        "ns-dev-boundary-add",
        "--arm",
        "A",
        "--cache",
        "local_cold",
        "--repetition",
        "0",
        "--record-kind",
        "development",
        "--path",
        "development",
        "--admitted-provider",
        "--upstream-store",
        str(store),
        "--ledger",
        str(ledger),
        "--out",
        str(attempt_path),
    ]
    invoked = run(argv, timeout=180)
    (dev_dir / "stdout.log").write_text(invoked.stdout, encoding="utf-8")
    (dev_dir / "stderr.log").write_text(invoked.stderr, encoding="utf-8")
    report["commands"]["development_invocation"] = {
        "argv": argv,
        "exit_code": invoked.returncode,
        "stderr_tail": invoked.stderr[-2000:],
    }
    if invoked.returncode != 0 or not attempt_path.is_file():
        report["error"] = "admitted development invocation failed to publish a receipt"
        atomic_write(QUAL / "qualification_report.json", report)
        return 1
    attempt = load(attempt_path)
    receipt = attempt["provider_receipt"]
    measurement = attempt["measurement"]
    stubby = receipt.get("served_model") == "ns-006-deterministic-dev-stub"
    actual = (
        receipt.get("dispatched") is True
        and receipt.get("simulated") is False
        and receipt.get("admitted_production") is False
        and receipt.get("served_provider") == "xai"
        and bool(receipt.get("served_model"))
        and bool(receipt.get("logical_effect_id"))
        and bool(receipt.get("runtime_receipt_id"))
        and not stubby
    )
    report["checks"].append(
        {
            "name": "actual_development_provider_not_stub",
            "ok": actual,
            "terminal_state": measurement.get("terminal_state"),
            "terminal_reason": measurement.get("terminal_reason"),
            "served_provider": receipt.get("served_provider"),
            "served_model": receipt.get("served_model"),
            "served_revision": receipt.get("served_revision"),
            "runtime_receipt_id": receipt.get("runtime_receipt_id"),
            "usage_receipt_id": receipt.get("usage_receipt_id"),
            "logical_effect_id": receipt.get("logical_effect_id"),
            "possibly_charged": receipt.get("possibly_charged"),
            "source_preimage_id": attempt["bindings"].get("source_preimage_id"),
            "input_tokens": measurement["measurements"]["input_tokens"],
            "output_tokens": measurement["measurements"]["output_tokens"],
            "provider_charge": measurement["measurements"]["provider_charge"],
            "active_elapsed_seconds": measurement["measurements"]["active_elapsed_seconds"],
            "stages": [row.get("stage") for row in measurement.get("stages") or []],
        }
    )

    scored_path = dev_dir / "scored.json"
    scored_run = run(
        [
            PYTHON,
            str(EXP / "score_runs.py"),
            "--attempt",
            str(attempt_path),
            "--out",
            str(scored_path),
        ],
        timeout=60,
    )
    report["commands"]["independent_rescore"] = {
        "exit_code": scored_run.returncode,
        "stdout_tail": scored_run.stdout[-1500:],
        "stderr_tail": scored_run.stderr[-1500:],
    }
    scored = load(scored_path) if scored_path.is_file() else {}
    oracle = (scored.get("measurement") or {}).get("oracle") or {}
    report["checks"].append(
        {
            "name": "independent_score_after_seal",
            "ok": scored_run.returncode == 0 and oracle.get("independent_scorer_id") == "ns-026-independent-historical-scorer",
            "oracle": oracle,
            "terminal_state": (scored.get("measurement") or {}).get("terminal_state"),
            "effect_unchanged": (scored.get("provider_receipt") or {}).get("logical_effect_id")
            == receipt.get("logical_effect_id"),
        }
    )

    resume_path = dev_dir / "resume.json"
    resumed = run(argv[:-1] + [str(resume_path)], timeout=60)
    resume_obj = load(resume_path) if resume_path.is_file() else {}
    campaign = load(ledger / "campaign.json")
    report["commands"]["resume_same_unit"] = {"exit_code": resumed.returncode}
    report["checks"].append(
        {
            "name": "resume_no_duplicate_dispatch",
            "ok": (
                resumed.returncode == 0
                and campaign.get("provider_effects_dispatched") == 1
                and (resume_obj.get("provider_receipt") or {}).get("replayed") is True
            ),
            "provider_effects_dispatched": campaign.get("provider_effects_dispatched"),
            "provider_calls_by_effect": campaign.get("provider_calls_by_effect"),
            "replayed": (resume_obj.get("provider_receipt") or {}).get("replayed"),
        }
    )
    atomic_write(dev_dir / "campaign.json", campaign)

    # --- historical materialization + canary ---
    hist_dir = QUAL / "historical"
    hist_dir.mkdir(parents=True, exist_ok=True)
    dest = Path(tempfile.mkdtemp(prefix="ns026-hist-proposal-"))
    mat = run(
        [
            PYTHON,
            str(EXP / "production_gateway.py"),
            "materialize",
            "--task-id",
            "ns-hist-01-xmltodict",
            "--mode",
            "proposal",
            "--store",
            str(store),
            "--dest",
            str(dest),
            "--out",
            str(hist_dir / "materialize.json"),
        ],
        timeout=90,
    )
    report["commands"]["materialize"] = {"exit_code": mat.returncode, "stderr_tail": mat.stderr[-1500:]}
    material = load(hist_dir / "materialize.json") if (hist_dir / "materialize.json").is_file() else {}
    export_files = {}
    for path in dest.rglob("*"):
        if path.is_file():
            export_files[path.relative_to(dest).as_posix()] = path.read_text(encoding="utf-8", errors="replace")
    scan = {
        "files": sorted(export_files),
        "git_present": (dest / ".git").exists(),
        "scorer_payload_present": any("scorer_only" in name or "fail_to_pass" in name for name in export_files),
        "fix_commit_file_present": any("f0322e578184421693434902547f330f4f0a44c3" in name for name in export_files),
        "xmltodict_sha256": sha(dest / "xmltodict.py") if (dest / "xmltodict.py").is_file() else None,
        "expected_xmltodict_sha256": "7084494972ac820ecc41625b35fda59f2da1556ea34ab46414696471369cfe63",
        "isolation": material.get("isolation"),
        "used_caller_git": material.get("used_caller_git"),
        "archive_sha256": material.get("archive_sha256"),
        "expected_archive_sha256": "72e6f909de6a20c7700a2398dcf9587a7d9263be68b6bd50361f2a375f909fda",
    }
    atomic_write(hist_dir / "proposal_export_scan.json", scan)
    report["checks"].append(
        {
            "name": "pinned_pre_fix_proposal_export",
            "ok": (
                material.get("ok") is True
                and scan["xmltodict_sha256"] == scan["expected_xmltodict_sha256"]
                and scan["archive_sha256"] == scan["expected_archive_sha256"]
                and scan["git_present"] is False
                and scan["scorer_payload_present"] is False
                and scan["used_caller_git"] is False
                and scan["files"] == ["xmltodict.py"]
            ),
            "scan": scan,
        }
    )

    canary_dir = Path(tempfile.mkdtemp(prefix="ns026-canary-"))
    (canary_dir / "pkg").mkdir()
    (canary_dir / "pkg" / "leak.py").write_text(
        "hidden = 'receipts/snapshots/NS-005/scorer_only/oracles'\nfix_commit = 'sentinel'\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(EXP))
    import importlib.util

    spec = importlib.util.spec_from_file_location("ns026_run", EXP / "run_comparison.py")
    runmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runmod)
    canary_iso = runmod.inspect_isolation(canary_dir, ROOT)
    canary = {
        "hidden_markers_found": canary_iso.get("hidden_markers_found"),
        "scope_preserved": canary_iso.get("scope_preserved"),
        "rejected": bool(canary_iso.get("hidden_markers_found")),
    }
    atomic_write(hist_dir / "isolation_canary.json", canary)
    report["checks"].append({"name": "boundary_canary_rejects_scorer_payload", "ok": canary["rejected"] is True, "canary": canary})

    full_dest = Path(tempfile.mkdtemp(prefix="ns026-hist-full-"))
    full_mat = run(
        [
            PYTHON,
            str(EXP / "production_gateway.py"),
            "materialize",
            "--task-id",
            "ns-hist-01-xmltodict",
            "--mode",
            "full_pre_fix",
            "--store",
            str(store),
            "--dest",
            str(full_dest),
            "--out",
            str(hist_dir / "full_materialize.json"),
        ],
        timeout=90,
    )
    nodes = [
        "tests/test_xmltodict.py::XMLToDictTestCase::test_simple",
        "tests/test_xmltodict.py::XMLToDictTestCase::test_list",
        "tests/test_xmltodict.py::XMLToDictTestCase::test_minimal",
    ]
    baseline_cmd = [PYTHON, "-m", "pytest", "-q", "--tb=line", *nodes]
    baseline = run(baseline_cmd, cwd=full_dest, timeout=60)
    baseline_rec = {
        "materialize_exit": full_mat.returncode,
        "pytest_exit": baseline.returncode,
        "stdout_tail": baseline.stdout[-2000:],
        "stderr_tail": baseline.stderr[-2000:],
        "nodes": nodes,
        "nonempty": baseline.returncode == 0,
        "source_unchanged": sha(full_dest / "xmltodict.py") == scan["expected_xmltodict_sha256"] if (full_dest / "xmltodict.py").is_file() else False,
    }
    atomic_write(hist_dir / "baseline.json", baseline_rec)
    report["checks"].append(
        {
            "name": "nonempty_unchanged_baseline",
            "ok": baseline_rec["nonempty"] is True and baseline_rec["source_unchanged"] is True,
            "pytest_exit": baseline.returncode,
        }
    )

    # --- historical independent scorer on sealed empty candidate ---
    scorer_dir = QUAL / "scorer"
    scorer_dir.mkdir(parents=True, exist_ok=True)
    sealed = json.loads(canonical(attempt))
    sealed["bindings"]["task_id"] = "ns-hist-01-xmltodict"
    sealed["bindings"]["family_id"] = "upstream:martinblech/xmltodict"
    sealed["bindings"]["source_preimage_id"] = "468ebe23fac4d77395df52faea4d8ac94edfb7d82ec941e9fd3236bdb40fbcb7"
    sealed["measurement"]["identity"]["task_id"] = "ns-hist-01-xmltodict"
    sealed["measurement"]["identity"]["family_id"] = "upstream:martinblech/xmltodict"
    sealed["measurement"]["identity"]["source_preimage_id"] = sealed["bindings"]["source_preimage_id"]
    sealed["runner"]["live_repair_admitted"] = True
    sealed["runner"]["sandbox_files"] = {"xmltodict.py": (dest / "xmltodict.py").read_text(encoding="utf-8")}
    sealed["runner"]["candidate"] = {
        "kind": "generated_patch",
        "files": {"xmltodict.py": sealed["runner"]["sandbox_files"]["xmltodict.py"]},
        "patch_text": "",
    }
    sealed["path_class"] = "production"
    sealed["provider_receipt"]["path_class"] = "production"
    sealed["provider_receipt"]["simulated"] = False
    sealed["provider_receipt"]["admitted_production"] = False
    sealed_path = scorer_dir / "historical_sealed_unsolved.json"
    atomic_write(sealed_path, sealed)
    hist_scored_path = scorer_dir / "historical_scored.json"
    env = dict(os.environ)
    env["NS_NS026_UPSTREAM_STORE"] = str(store)
    hist_score = run(
        [PYTHON, str(EXP / "score_runs.py"), "--attempt", str(sealed_path), "--out", str(hist_scored_path)],
        timeout=90,
        env=env,
    )
    hist_scored = load(hist_scored_path) if hist_scored_path.is_file() else {}
    hist_oracle = (hist_scored.get("measurement") or {}).get("oracle") or {}
    atomic_write(
        scorer_dir / "bindings.json",
        {
            "source_preimage_id": sealed["bindings"]["source_preimage_id"],
            "logical_effect_id": sealed["provider_receipt"]["logical_effect_id"],
            "runtime_receipt_id": sealed["provider_receipt"]["runtime_receipt_id"],
            "oracle_status": hist_oracle.get("status"),
            "candidate_valid": hist_oracle.get("candidate_valid"),
            "independent_scorer_id": hist_oracle.get("independent_scorer_id"),
            "blanket_refusal": hist_oracle.get("reason", "").startswith("Live hidden"),
        },
    )
    report["commands"]["historical_score"] = {
        "exit_code": hist_score.returncode,
        "stderr_tail": hist_score.stderr[-2000:],
        "stdout_tail": hist_score.stdout[-1500:],
    }
    report["checks"].append(
        {
            "name": "historical_scorer_no_blanket_refusal",
            "ok": (
                hist_score.returncode == 0
                and hist_oracle.get("independent_scorer_id") == "ns-026-independent-historical-scorer"
                and not str(hist_oracle.get("reason") or "").startswith("Live hidden")
                and hist_oracle.get("status") in {"passed", "failed", "unavailable", "timed_out"}
            ),
            "oracle": hist_oracle,
        }
    )

    # scorer admission path: same sealed historical attempt with admitted_production true is allowed to become solved if tests pass
    admit_probe = json.loads(canonical(sealed))
    admit_probe["provider_receipt"]["admitted_production"] = True
    admit_probe["measurement"]["terminal_state"] = "unsolved"
    admit_path = scorer_dir / "production_admission_path.json"
    atomic_write(admit_path, admit_probe)
    admit_out = scorer_dir / "production_admission_path.scored.json"
    admit_run = run(
        [PYTHON, str(EXP / "score_runs.py"), "--attempt", str(admit_path), "--out", str(admit_out)],
        timeout=90,
        env=env,
    )
    admit_scored = load(admit_out) if admit_out.is_file() else {}
    report["commands"]["production_admission_path"] = {"exit_code": admit_run.returncode}
    report["checks"].append(
        {
            "name": "scorer_can_admit_production_without_blanket_refusal",
            "ok": admit_run.returncode == 0
            and "Live hidden" not in str(((admit_scored.get("measurement") or {}).get("oracle") or {}).get("reason") or ""),
            "oracle": (admit_scored.get("measurement") or {}).get("oracle"),
            "terminal_state": (admit_scored.get("measurement") or {}).get("terminal_state"),
            "note": "Scorer-path qualification on a sealed historical candidate. Not a live production arm result.",
        }
    )

    # --- stub interrupt / unknown production ---
    resume_dir = QUAL / "resume"
    resume_dir.mkdir(parents=True, exist_ok=True)
    crash_ledger = Path(tempfile.mkdtemp(prefix="ns026-crash-"))
    crash_out = resume_dir / "crash.json"
    crash = run(
        [
            PYTHON,
            str(EXP / "run_comparison.py"),
            "one-task",
            "--task-id",
            "ns-dev-boundary-add",
            "--arm",
            "A",
            "--path",
            "development",
            "--record-kind",
            "development",
            "--repetition",
            "11",
            "--crash-after",
            "provider",
            "--ledger",
            str(crash_ledger),
            "--out",
            str(crash_out),
        ],
        timeout=30,
    )
    resume_crash = run(
        [
            PYTHON,
            str(EXP / "run_comparison.py"),
            "one-task",
            "--task-id",
            "ns-dev-boundary-add",
            "--arm",
            "A",
            "--path",
            "development",
            "--record-kind",
            "development",
            "--repetition",
            "11",
            "--ledger",
            str(crash_ledger),
            "--out",
            str(resume_dir / "resumed.json"),
        ],
        timeout=30,
    )
    crash_campaign = load(crash_ledger / "campaign.json")
    atomic_write(resume_dir / "crash_campaign.json", crash_campaign)
    unknown_out = resume_dir / "unknown_production.json"
    unknown = run(
        [
            PYTHON,
            str(EXP / "run_comparison.py"),
            "one-task",
            "--task-id",
            "ns-hist-01-xmltodict",
            "--arm",
            "A",
            "--path",
            "production",
            "--record-kind",
            "development",
            "--crash-after",
            "reserve",
            "--upstream-store",
            str(store),
            "--ledger",
            str(Path(tempfile.mkdtemp(prefix="ns026-unknown-"))),
            "--out",
            str(unknown_out),
        ],
        timeout=90,
    )
    unknown_rec = load(unknown_out) if unknown_out.is_file() else {}
    report["commands"]["interrupt"] = {"crash_exit": crash.returncode, "resume_exit": resume_crash.returncode}
    report["commands"]["unknown_production"] = {"exit_code": unknown.returncode}
    report["checks"].append(
        {
            "name": "stub_interrupt_no_duplicate_dispatch",
            "ok": crash.returncode == 75 and resume_crash.returncode == 0 and crash_campaign.get("provider_effects_dispatched") == 1,
            "campaign": {
                "provider_effects_dispatched": crash_campaign.get("provider_effects_dispatched"),
                "provider_calls_by_effect": crash_campaign.get("provider_calls_by_effect"),
                "unknown_effects": crash_campaign.get("unknown_effects"),
            },
        }
    )
    report["checks"].append(
        {
            "name": "production_unknown_or_unavailable_not_solved",
            "ok": unknown.returncode == 0
            and unknown_rec.get("measurement", {}).get("terminal_state") in {"unavailable", "unsolved"}
            and unknown_rec.get("measurement", {}).get("terminal_state") != "solved"
            and unknown_rec.get("provider_receipt", {}).get("admitted_production") is False,
            "terminal_state": unknown_rec.get("measurement", {}).get("terminal_state"),
            "terminal_reason": unknown_rec.get("measurement", {}).get("terminal_reason"),
        }
    )

    report["finished_at"] = utcnow()
    report["elapsed_seconds"] = time.perf_counter() - origin
    report["ok"] = all(item.get("ok") for item in report["checks"])
    atomic_write(QUAL / "qualification_report.json", report)
    shutil.rmtree(store, ignore_errors=True)
    print(canonical({"ok": report["ok"], "checks": [{k: c[k] for k in ("name", "ok") if k in c} for c in report["checks"]]}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
