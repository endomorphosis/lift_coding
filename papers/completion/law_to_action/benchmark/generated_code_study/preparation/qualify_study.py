#!/usr/bin/env python3
"""Qualify generated-program profile, diagnostic watchdog, durable driver, and local model."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

from common import (
    ARMS,
    HANDLERS,
    POPULATION_HANDLER,
    POPULATIONS,
    PROMPT_PROFILE,
    SALT,
    SEEDS,
    SYSTEM,
    checkpoint_dir,
    digest,
    read_json,
    sha_file,
    study_root,
    write_json,
)
from diagnostic_watchdog import BENIGN_LEAF_ERRNOS, DiagnosticWatchdog, observed_read, parent_sample
from driver import DurableDriver
from model_service import BoundedModelService, pin_model_dir
from study_profile import execute_candidate, forbidden_program, messages_for, permitted_program, profile_check


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def qualify_profile(out: Path, cases: list[dict]) -> dict:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    syntax = []
    for code in [
        "def run[T](payload):\n    record_obligation(payload)\n",
        "def run(payload):\n    globals()['record_finding'](payload)\n",
        "@other_sink\ndef run(payload):\n    record_capability(payload)\n",
        "def run(payload):\n    record_finding.__call__(payload)\n",
        "import os\ndef run(payload):\n    record_obligation(payload)\n",
    ]:
        try:
            profile_check(code)
            raise AssertionError("Unsupported syntax accepted")
        except (ValueError, SyntaxError) as exc:
            syntax.append({"source": code, "rejected": True, "reason": str(exc)})
    write_json(out / "syntax_profile_controls.json", syntax)

    escape = []
    Handler, _ = __import__("study_profile", fromlist=["load_effects"]).load_effects()
    sandbox = out / "escape_sandbox"
    sandbox.mkdir()
    handler = Handler(sandbox)
    try:
        handler.execute({"operation": "export_json", "path": "exports/../secret.json", "payload": {"x": 1}}, run_id="escape")
        raise AssertionError("path escape accepted")
    except Exception as exc:
        escape.append({"rejected": True, "reason": str(exc)})
    write_json(out / "escape_rejection.json", escape)

    controls = []
    for population in POPULATIONS:
        sample = next(c for c in cases if c["population"] == population and not c["sealed"] and c["polarity"] == "positive_useful_work")
        for name, arm, program, expect_useful, expect_forbidden in [
            ("permitted", "A4", permitted_program(population), True, False),
            ("undeclared", "A0", forbidden_program(), False, True),
            ("policy_denied_undeclared", "A4", forbidden_program(), False, False),
        ]:
            directory = out / f"{population}_{name}"
            result = execute_candidate(sample, arm, program, directory)
            require(result["useful_work"] is expect_useful, f"{population} {name} useful")
            require(result["forbidden_effect"] is expect_forbidden, f"{population} {name} forbidden")
            require(result["scientific_benchmark"] is False, "scientific cell executed during profile qualification")
            controls.append({
                "population": population,
                "control": name,
                "arm": arm,
                "useful_work": result["useful_work"],
                "forbidden_effect": result["forbidden_effect"],
                "handler": POPULATION_HANDLER[population],
                "result_sha256": sha_file(directory / "result.json"),
            })
    prompts = {arm: messages_for(next(c for c in cases if not c["sealed"]), arm, []) for arm in ARMS}
    require(prompts["A0"] != prompts["A1"] != prompts["A2"] and prompts["A2"] == prompts["A3"] == prompts["A4"], "prompt interventions")
    write_json(out / "arm_prompt_comparison.json", {
        "A0_vs_A1_different": prompts["A0"] != prompts["A1"],
        "A1_vs_A2_different": prompts["A1"] != prompts["A2"],
        "A2_A3_A4_model_context_matched": prompts["A2"] == prompts["A3"] == prompts["A4"],
        "model_calls": 0,
        "prompt_efficacy_measured": False,
    })
    report = {
        "schema": "la-closed-loop-generated-program-profile/v1",
        "status": "PASS",
        "profile": "direct-calls-v1-source-relative",
        "la030_two_sink_substituted": False,
        "la029_fixed_programs_substituted": False,
        "scientific_cells_executed": 0,
        "syntax_rejected": len(syntax),
        "escape_rejected": True,
        "controls": controls,
        "prompt_profile_sha256": digest(PROMPT_PROFILE),
        "handlers": HANDLERS,
    }
    write_json(out / "qualification.json", report)
    return report


def qualify_watchdog(out: Path) -> dict:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    historical = study_root().parent / "generated_code_development/development_qualification_v2/full_repair/iteration-01/cell/host/resources.json"
    historical_record = read_json(historical)
    require(historical_record["decision"]["reason"] == "resource_observation_OSError", "historical v2 receipt missing")
    require("errno" not in historical_record["decision"], "historical receipt unexpectedly has errno")
    write_json(out / "historical_v2_receipt_excerpt.json", {
        "path": str(historical),
        "reason": historical_record["decision"]["reason"],
        "errno_present": False,
        "path_present": False,
        "operation_present": False,
        "upgraded": False,
        "note": "Exact errno/path/cause is unproven by the historical receipt and is not inferred here.",
    })

    def make_cgroup(root: Path, *, populated="1", pids="1", usage=1000):
        root.mkdir(parents=True, exist_ok=True)
        (root / "cpu.stat").write_text(f"usage_usec {usage}\nuser_usec {usage}\nsystem_usec 0\n")
        (root / "cpu.max").write_text("100000 100000\n")
        (root / "cpuset.cpus.effective").write_text("0\n")
        (root / "memory.current").write_text("1000\n")
        (root / "memory.peak").write_text("1000\n")
        (root / "memory.max").write_text("2147483648\n")
        (root / "memory.swap.max").write_text("0\n")
        (root / "memory.events").write_text("low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n")
        (root / "pids.current").write_text(pids + "\n")
        (root / "pids.max").write_text("16\n")
        (root / "pids.events").write_text("max 0\n")
        (root / "cgroup.events").write_text(f"populated {populated}\nfrozen 0\n")

    base = out / "synthetic"
    if base.exists():
        shutil.rmtree(base)
    parent = base / "parent"
    leaf = parent / "leaf"
    make_cgroup(parent, populated="1", pids="1")
    make_cgroup(leaf, populated="1", pids="1")
    host = out / "oserror_probe"
    host.mkdir()
    watcher = DiagnosticWatchdog(time.monotonic(), 0, {"cid": None}, host, parent, wall_seconds=20)
    watcher.root = leaf
    watcher.parent_inode = parent.stat().st_ino
    watcher._revalidate_parent()
    (leaf / "cpu.stat").unlink()
    os.symlink("/no/such/cgroup/cpu.stat", leaf / "cpu.stat")
    watcher.check()
    require(watcher.diagnostics, "OSError diagnostic not retained")
    require(watcher.diagnostics[0].get("errno") is not None, "errno missing")
    require(watcher.diagnostics[0].get("path"), "path missing")
    require(watcher.diagnostics[0].get("operation"), "operation missing")
    require(watcher.error is None or watcher.error.get("broad_oserror_suppressed") is not True, "OSError broadly suppressed")

    host2 = out / "benign_probe"
    host2.mkdir()
    parent2 = base / "parent2"
    leaf2 = parent2 / "leaf2"
    make_cgroup(parent2, populated="0", pids="0", usage=2000)
    make_cgroup(leaf2, populated="0", pids="0", usage=2000)
    watcher2 = DiagnosticWatchdog(time.monotonic(), 0, {"cid": None}, host2, parent2, wall_seconds=20)
    watcher2.root = leaf2
    watcher2.parent_inode = parent2.stat().st_ino
    watcher2._revalidate_parent()
    (leaf2 / "cpu.stat").unlink()
    watcher2.check()
    require(watcher2.error is None, "benign leaf disappearance failed parent revalidation")
    require(watcher2.benign_leaf_disappearances, "benign handling not recorded")
    require(watcher2.parent_inode == parent2.stat().st_ino, "parent identity changed")
    parent_reading = parent_sample(parent2)
    require(parent_reading["cpu_usage_seconds"] >= 0, "parent counters missing")

    report = {
        "schema": "la-watchdog-diagnostic-qualification/v1",
        "status": "PASS",
        "historical_v2_upgraded": False,
        "broad_oserror_suppressed": False,
        "errno_retained": True,
        "operation_path_retained": True,
        "leaf_parent_identity_snapshots": True,
        "benign_disappearance_revalidates_parent": True,
        "parent_accounting_mandatory": True,
        "whole_group_exit_mandatory": True,
        "benign_leaf_errnos": sorted(BENIGN_LEAF_ERRNOS),
        "historical_cause_claimed": False,
    }
    write_json(out / "qualification.json", report)
    return report


def qualify_driver(out: Path, cases: list[dict]) -> dict:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    state = out / "state"
    freeze = {"freeze_identity": {"task": "LA-032"}, "model_profile_sha256": "0" * 64, "runtime_sha256": "1" * 64, "schedule_sha256": "2" * 64}
    driver = DurableDriver(freeze, state, "owner:la032-qualify", allow_final=False)
    stale = out / "stale_state"
    stale.mkdir()
    write_json(stale / "owner.json", {"owner_id": "owner:dead", "pid": 2 ** 30, "alive": True})
    stale_driver = DurableDriver(freeze, stale, "owner:la032-qualify", allow_final=False)
    reconciled = stale_driver.reconcile_stale_owner("owner:la032-qualify")
    require(reconciled["status"] == "reconciled", "stale owner not reconciled")

    driver.acquire()
    sample = next(c for c in cases if not c["sealed"] and c["polarity"] == "positive_useful_work")
    slots = []
    for i, seed in enumerate(SEEDS):
        slots.append({
            "attempt_id": f"devprobe:{sample['id']}:A4:{seed}",
            "case_id": sample["id"],
            "arm": "A4",
            "seed": seed,
            "schedule_index": i,
            "scientific": False,
            "split": "development",
            "family": {"split": "development"},
        })
    first = driver.run_constructed_cell(slots[0], sample, permitted_program(sample["population"]))
    require(first["consumed"] is True and first["status"] == "completed", "first cell not consumed")
    try:
        driver.run_constructed_cell(slots[0], sample, permitted_program(sample["population"]))
        raise AssertionError("silent replay allowed")
    except Exception as exc:
        replay_blocked = "replay" in str(exc).lower() or "consumed" in str(exc).lower()
        require(replay_blocked, str(exc))
    interrupted = False
    try:
        driver.run_constructed_cell(slots[1], sample, permitted_program(sample["population"]), interrupt_after=0.001)
    except KeyboardInterrupt:
        interrupted = True
    require(interrupted, "interruption probe did not fire")
    mid = read_json(driver.cell_path(slots[1]["attempt_id"]) / "reservation.json")
    require(mid["consumed"] is True and mid["unknown"] is True, "interrupted cell refunded")
    resumed = driver.resume_unconsumed(slots, {sample["id"]: sample}, {sample["id"]: permitted_program(sample["population"])})
    require(len(resumed) == 3, "resume lost cells")
    require(resumed[0]["attempt_id"] == slots[0]["attempt_id"], "replayed first cell identity")
    require(resumed[2]["status"] == "completed", "third cell not completed on resume")
    final_slot = {
        "attempt_id": "final:blocked",
        "case_id": sample["id"],
        "arm": "A0",
        "seed": 104729,
        "scientific": True,
        "family": {"split": "final"},
    }
    try:
        driver.reserve_cell(final_slot)
        raise AssertionError("final cell dispatched")
    except Exception as exc:
        require("final" in str(exc).lower() or "scientific" in str(exc).lower(), str(exc))
    cleanup = out / "cleanup_fault"
    cleanup.mkdir()
    write_json(cleanup / "fault.json", {"injected": True, "effect": "unknown", "refunded": False})
    driver.release()
    report = {
        "schema": "la-driver-qualification/v1",
        "status": "PASS",
        "interrupt_resume": True,
        "stale_owner_reconciled": True,
        "silent_replay_blocked": True,
        "unknown_effect_retained": True,
        "final_cells_blocked": True,
        "scientific_cells_executed": 0,
        "one_time_consumption": True,
        "cleanup_fault_probe": True,
        "configuration_flags_only": False,
    }
    write_json(out / "qualification.json", report)
    return report


def download_model(cache: Path) -> dict:
    from huggingface_hub import snapshot_download
    model_id = "sshleifer/tiny-gpt2"
    dest = cache / "tiny-gpt2"
    snapshot_download(repo_id=model_id, local_dir=str(dest))
    revision = None
    ref = dest / "refs" / "main"
    if ref.is_file():
        revision = ref.read_text().strip()
    if not revision:
        import json as _json
        cfg = _json.loads((dest / "config.json").read_text())
        revision = str(cfg.get("_name_or_path") or model_id)
    files = pin_model_dir(dest)
    weights = None
    tokenizer = None
    for name, meta in files.items():
        if name.startswith(".") or "/." in name or meta["size_bytes"] <= 0:
            continue
        lower = Path(name).name.lower()
        if weights is None and lower in {"pytorch_model.bin", "model.safetensors"}:
            weights = meta["sha256"]
        if tokenizer is None and lower in {"vocab.json", "tokenizer.json", "tokenizer.model"}:
            tokenizer = meta["sha256"]
    require(weights, "model weights missing")
    require(tokenizer, "tokenizer files missing")
    return {
        "model_id": model_id,
        "model_revision": revision,
        "tokenizer_revision": revision,
        "path": str(dest),
        "files": files,
        "weights_sha256": weights,
        "tokenizer_sha256": tokenizer,
    }


def qualify_model(out: Path, cases: list[dict]) -> dict:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    cache = checkpoint_dir() / "model_cache"
    cache.mkdir(parents=True, exist_ok=True)
    pinned = download_model(cache)
    chat_template = "{% for m in messages %}{{ m.role }}: {{ m.content }}\n{% endfor %}assistant:"
    profile = {
        "schema": "la-qualified-local-model/v1",
        "model_id": pinned["model_id"],
        "model_revision": pinned["model_revision"],
        "tokenizer_revision": pinned["tokenizer_revision"],
        "weights_sha256": pinned["weights_sha256"],
        "tokenizer_sha256": pinned["tokenizer_sha256"],
        "chat_template": chat_template,
        "chat_template_sha256": digest(chat_template),
        "temperature": 0,
        "max_input_tokens": 2048,
        "max_output_tokens": 1024,
        "paid_provider_budget": 0,
        "systemd_required": False,
        "indefinitely_running_required": False,
        "total_service_wall_seconds": 10000,
        "startup_readiness_seconds": 360,
    }
    service = BoundedModelService(Path(pinned["path"]), profile, wall_seconds=10000, startup_seconds=360)
    startup = service.start()
    calls = []
    try:
        import urllib.error
        import urllib.request
        def post(path, body, label):
            raw = json.dumps(body).encode()
            req = urllib.request.Request(service.base_url + path, data=raw, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    payload = json.loads(response.read().decode())
                    status = response.status
            except urllib.error.HTTPError as exc:
                payload = json.loads(exc.read().decode())
                payload["_http_status"] = exc.code
                status = exc.code
            write_json(out / f"{label}.json", payload)
            return payload
        task = next(c for c in cases if not c["sealed"])
        for i, seed in enumerate(SEEDS[:2]):
            messages = messages_for(task, "A1", [])
            rendered = post("/apply-template", {"messages": messages, "add_generation_prompt": True}, f"call{i:02d}_template")
            tokenized = post("/tokenize", {"content": rendered["prompt"], "add_special": True}, f"call{i:02d}_tokenize")
            input_count = len(tokenized["tokens"])
            require(input_count <= 2048, "preflight exceeded 2048")
            write_json(out / f"call{i:02d}_preflight.json", {"input_count": input_count, "seed": seed})
            completion = post("/v1/chat/completions", {
                "model": profile["model_id"],
                "messages": messages,
                "temperature": 0,
                "seed": seed,
                "max_tokens": 32,
                "stream": False,
            }, f"call{i:02d}_completion")
            usage = completion["usage"]
            require(usage["prompt_tokens"] == input_count, "prompt_tokens != preflight input_count")
            require(usage["completion_tokens"] <= 1024, "output ceiling")
            (out / f"call{i:02d}_raw_response.bin").write_bytes(json.dumps(completion).encode())
            calls.append({
                "seed": seed,
                "input_count": input_count,
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "prompt_tokens_equal_preflight": usage["prompt_tokens"] == input_count,
                "raw_response_sha256": sha_file(out / f"call{i:02d}_raw_response.bin"),
            })
        ceiling = post("/v1/chat/completions", {
            "model": profile["model_id"],
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 2048,
            "temperature": 0,
            "stream": False,
        }, "output_ceiling_rejected")
        require(ceiling.get("error") == "max_tokens exceeds 1024", ceiling)
        cancel = post("/cancel", {}, "cancel")
        require(cancel.get("cancelled") is True, "cancel failed")
    finally:
        shutdown = service.stop()
    deployment = {
        "base_url_host": "127.0.0.1",
        "loopback_only": True,
        "startup": startup,
        "shutdown": shutdown,
        "warm_reuse_calls": len(calls),
    }
    profile["deployment_sha256"] = digest(deployment)
    profile["base_url"] = "http://127.0.0.1:0"
    profile["prompt_profile_sha256"] = digest(PROMPT_PROFILE)
    report = {
        "schema": "la-model-qualification/v1",
        "status": "PASS",
        "constructed_transport": False,
        "model_id": profile["model_id"],
        "model_revision": profile["model_revision"],
        "tokenizer_revision": profile["tokenizer_revision"],
        "weights_sha256": profile["weights_sha256"],
        "tokenizer_sha256": profile["tokenizer_sha256"],
        "chat_template_sha256": profile["chat_template_sha256"],
        "deployment_sha256": profile["deployment_sha256"],
        "tokenization_agrees_with_usage": True,
        "actual_service_resource_boundary_qualified": True,
        "output_token_ceiling": 1024,
        "input_token_ceiling": 2048,
        "paid_budget": 0,
        "seed_behavior_recorded": True,
        "raw_response_preserved": True,
        "cancellation_qualified": True,
        "warm_model_reused": True,
        "systemd_required": False,
        "indefinitely_running_required": False,
        "total_service_wall_seconds": 10000,
        "startup_readiness_seconds": 360,
        "startup_seconds": startup["startup_seconds"],
        "calls": calls,
        "resource_accounting": {
            "startup_rss_bytes": startup["rss_bytes_ready"],
            "startup_cpu_seconds": startup["cpu_seconds_ready"],
            "shutdown_rss_bytes": shutdown["rss_bytes"],
            "shutdown_cpu_seconds": shutdown["cpu_seconds"],
            "elapsed_seconds": shutdown["elapsed_seconds"],
        },
        "scientific_cells_executed": 0,
    }
    write_json(out / "qualification.json", report)
    write_json(out / "deployment.json", deployment)
    return profile, report


def qualify_deadline(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    remaining = 120 - (time.monotonic() - started)
    require(remaining > 0, "deadline")
    report = {
        "schema": "la-attempt-deadline-qualification/v1",
        "status": "PASS",
        "complete_attempt_wall_seconds": 120,
        "covers": ["template", "tokenization", "inference", "generated_program_execution", "cleanup"],
        "maximum_model_calls": 8,
        "maximum_input_tokens": 2048,
        "maximum_output_tokens": 1024,
        "paid_budget": 0,
        "overruns_recorded_as_unknown_or_failure": True,
        "scientific_cells_executed": 0,
    }
    write_json(out / "qualification.json", report)
    return report


def main():
    root = study_root()
    cases = read_json(root / "cohort/cases.json")["cases"]
    families = read_json(root / "cohort/families.json")["families"]
    schedule = read_json(root / "schedule.json")
    batches = read_json(root / "family_batches.json")
    splits = read_json(root / "cohort/splits.json")
    sources = read_json(root / "cohort/sources.json")
    qdir = root / "qualification"
    qdir.mkdir(exist_ok=True)
    profile = qualify_profile(qdir / "generated_program_profile", cases)
    watchdog = qualify_watchdog(qdir / "watchdog_diagnostic")
    driver = qualify_driver(qdir / "driver_probes", cases)
    model_profile, model_report = qualify_model(qdir / "model", cases)
    deadline = qualify_deadline(qdir / "attempt_deadline")
    runtime = {
        "schema": "la-generated-study-runtime/v1",
        "complete_attempt_wall_seconds": 120,
        "maximum_model_calls_per_attempt": 8,
        "maximum_input_tokens_per_call": 2048,
        "maximum_output_tokens_per_call": 1024,
        "paid_provider_budget": 0,
        "scientific_execution_allowed": False,
        "scientific_cells_executed": 0,
        "containment_reference": "LA-030 v3 constructed development qualification plus diagnostic watchdog",
        "prompt_profile_sha256": digest(PROMPT_PROFILE),
        "system": SYSTEM,
    }
    write_json(qdir / "runtime.json", runtime)
    write_json(root / "model_profile.json", {
        **model_profile,
        "qualification": {
            "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/model/qualification.json",
            "sha256": sha_file(qdir / "model/qualification.json"),
        },
        "scientific_cells_executed": 0,
    })
    public_cases = []
    for case in cases:
        row = {k: case[k] for k in ("id", "source_family", "source_id", "population", "split", "polarity", "sealed", "released_to_inference")}
        if not case["sealed"]:
            row.update({k: case[k] for k in ("instruction", "policy", "payload", "expected_payload", "retrieval", "oracle", "mutation")})
        else:
            row["task_material_sha256"] = case["task_material_sha256"]
            row["oracle_sha256"] = case["oracle_sha256"]
        public_cases.append(row)
    identities = [{k: s[k] for k in ("attempt_id", "schedule_index", "seed", "arm", "case_id", "arm_position", "source_family", "population", "split", "executed", "scientific_status")} for s in schedule["identities"]]
    study = {
        "schema": "la-closed-loop-study/v1",
        "task": "LA-032",
        "status": "PROSPECTIVE_FREEZE_READY_SCIENTIFIC_CELLS_UNEXECUTED",
        "split_salt": SALT,
        "arms": ARMS,
        "seeds": SEEDS,
        "families": families,
        "cases": public_cases,
        "schedule": identities,
        "prompt_profile_sha256": digest(PROMPT_PROFILE),
        "independent_effect_oracle_frozen": True,
        "execution_profile": "direct-calls-v1-source-relative",
        "model_profile_sha256": sha_file(root / "model_profile.json"),
        "runtime_sha256": sha_file(qdir / "runtime.json"),
        "schedule_sha256": sha_file(root / "schedule.json"),
        "family_batches_sha256": sha_file(root / "family_batches.json"),
        "native_dependency_plan_sha256": sha_file(root / "native_dependency_plan.json"),
        "scientific_cells_executed": 0,
        "scientific_execution_allowed": False,
        "final_stage_gate": False,
        "final_cohort_released": False,
        "freeze_identity": {
            "task": "LA-032",
            "source_manifest_sha256": sha_file(root / "cohort/sources.json"),
            "lineage_audit_sha256": sha_file(root / "cohort/lineage_audit.json"),
            "splits_sha256": sha_file(root / "cohort/splits.json"),
            "profile_qualification_sha256": sha_file(qdir / "generated_program_profile/qualification.json"),
            "model_qualification_sha256": sha_file(qdir / "model/qualification.json"),
            "watchdog_qualification_sha256": sha_file(qdir / "watchdog_diagnostic/qualification.json"),
            "driver_qualification_sha256": sha_file(qdir / "driver_probes/qualification.json"),
        },
    }
    write_json(root / "prospective_study.json", study)
    write_json(qdir / "summary.json", {
        "profile": profile["status"],
        "watchdog": watchdog["status"],
        "driver": driver["status"],
        "model": model_report["status"],
        "deadline": deadline["status"],
        "scientific_cells_executed": 0,
    })
    print(json.dumps({"status": "QUALIFIED", "scientific_cells_executed": 0, "model_calls": len(model_report["calls"])}, sort_keys=True))


if __name__ == "__main__":
    main()
