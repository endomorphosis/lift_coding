#!/usr/bin/env python3
"""Execute one scoped SVF task; the accelerator supervisor owns task status.

Model output is a proposal. Only this worker can apply declared edits, and a
separate invocation rechecks task evidence before lane_resume marks completion.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import datetime as dt
import errno
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = "config/swissknife_visual_functional_supervisor.json"
EXECUTION_FAILURE_SCHEMA = "swissknife.visual-functional-execution-failure.v1"


class ValidationCommandError(RuntimeError):
    def __init__(self, argv, returncode, stdout, stderr):
        self.argv, self.returncode = argv, returncode
        self.stdout, self.stderr = stdout, stderr
        super().__init__(f"command exit {returncode}: {(stdout + chr(10) + stderr)[-16000:]}")


class BrowserContention(RuntimeError):
    """A shared browser lease is unavailable; application repair cannot free it."""


class StoragePressure(RuntimeError):
    """Typed transient admission refusal, never application/model failure."""
    def __init__(self, reason: str, number: int | None = None):
        if (reason, number) not in {("insufficient_free_bytes", None), ("ENOSPC", errno.ENOSPC), ("EDQUOT", errno.EDQUOT)}:
            raise ValueError("invalid storage pressure identity")
        self.reason, self.errno = reason, number
        super().__init__("storage admission withheld: " + reason)


def _storage_api():
    from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate
    bootstrap_ipfs_accelerate(__file__, include_script_dir=True)
    from ipfs_accelerate_py.agent_supervisor.rescue import storage_pressure
    return storage_pressure


def storage_refusal(error: Exception) -> StoragePressure | None:
    if isinstance(error, StoragePressure):
        return error
    if isinstance(error, OSError) and _storage_api().is_storage_pressure(error):
        return StoragePressure(errno.errorcode[error.errno], error.errno)
    return None


def assert_storage_available(profile: dict) -> None:
    """Durably probe real work/output/temp filesystems before admitting work."""
    result = _storage_api().check_storage_capacity([ROOT, runtime_root(profile), Path(tempfile.gettempdir())])
    if result["ok"] is not True:
        raise StoragePressure(result["reason"], result.get("errno"))


def execution_failure_path(profile: dict, task: dict) -> Path:
    if not re.fullmatch(r"SVF-[A-Z0-9-]{1,64}", task["task_id"]):
        raise ValueError("invalid execution failure task identity")
    return path_in_root(str(runtime_root(profile) / "tasks" / task["task_id"] / "last-execution-failure.json"))


def failure_task_context(task: dict) -> str:
    # Readonly dependency migrations do not erase concrete observed failures.
    # This is repair context, never an acceptance or execution authorization.
    return stable({k: task.get(k) for k in ("task_id", "kind", "app_id", "acceptance", "edit_paths")})


def remember_execution_failure(profile: dict, task: dict, error: Exception, *, stage: str,
                               attempt: Path | None = None, review_output: Path | None = None) -> Path:
    """Retain the exact producer failure separately from rejected model proposals."""
    path = execution_failure_path(profile, task)
    diagnostic = None
    driver_record = None
    if attempt is not None:
        attempt = path_in_root(str(attempt))
        if not attempt.is_relative_to(path.parent):
            raise ValueError("failure attempt escaped its task")
        report = path_in_root(str(attempt / "failure.json"))
        if not report.is_file():
            # Independent sessions retain their actual diagnostics under the
            # failing canonical viewport. Never guess among multiple failures.
            children = [path_in_root(str(attempt / name / "failure.json")) for name in ("desktop", "mobile")]
            if any(child.exists() and not child.is_file() for child in children):
                raise ValueError("viewport failure evidence must be a regular file")
            children = [child for child in children if child.is_file()]
            if len(children) > 1:
                raise ValueError("workflow has ambiguous independent viewport failures")
            if children:
                report = children[0]
        if report.is_file() and report.stat().st_size <= 131072:
            data = json.loads(report.read_text())
            if (type(data) is dict and data.get("schema") == "swissknife.visual-functional-workflow-failure.v1"
                    and data.get("app_id") == task.get("app_id")
                    and data.get("completion_authority") is False and data.get("work_complete") is False):
                check_artifacts(data.get("artifacts", []), allowed_prefix=attempt) if data.get("artifacts") else None
                driver_record = artifact(report)
                diagnostic = data
                # Failed owner/DOM observations are bounded, sanitized by the
                # producer, and hash checked here. They remain diagnostic only.
                payloads = []
                for item in data.get("artifacts", []):
                    source = path_in_root(item["path"])
                    if source.suffix == ".json" and item["bytes"] <= 49152:
                        payloads.append({"original": item, "observation": json.loads(source.read_text())})
                if payloads:
                    diagnostic = {**data, "retained_observations": payloads}
    value = {"schema": EXECUTION_FAILURE_SCHEMA, "task_id": task["task_id"],
             "task_context_sha256": failure_task_context(task), "task_spec_sha256": stable(task),
             "source_sha256": repair_target_hashes(task), "stage": stage,
             "error": {"code": "browser_contention" if isinstance(error, BrowserContention) else type(error).__name__,
                       "message": str(error)[-24000:]},
             "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
             "work_complete": False, "completion_authority": False}
    if driver_record:
        value.update(driver_failure=driver_record, diagnostic=diagnostic)
    if review_output is not None and review_output.is_file():
        from swissknife_visual_functional_llm import _read, RECEIPT_SCHEMA
        review_output = path_in_root(str(review_output))
        if not review_output.is_relative_to(path.parent):
            raise ValueError("review failure escaped its task")
        review = json.loads(_read(ROOT, str(review_output.relative_to(ROOT)), 4194304))
        if (review.get("schema") == RECEIPT_SCHEMA and review.get("task_id") == task["task_id"]
                and review.get("mode") == "review" and review.get("success") is True):
            response = review.get("response")
            if type(response) is dict and len(json.dumps(response).encode()) <= 24000:
                value["visual_review"] = {"original": artifact(review_output), "response": response}
    if diagnostic is not None:
        observations = diagnostic.get("retained_observations", [])
        value["diagnostic"] = {k: v for k, v in diagnostic.items() if k != "retained_observations"}
        value["diagnostic"]["retained_observations"] = []
        for observed in observations:
            value["diagnostic"]["retained_observations"].append(observed)
            if len(json.dumps(value, indent=2).encode()) > 49152:
                value["diagnostic"]["retained_observations"].pop()
        if len(value["diagnostic"]["retained_observations"]) != len(observations):
            value["diagnostic"]["observation_note"] = "Some payloads omitted by the context bound; exact originals remain hash-bound in artifacts."
    if len(json.dumps(value, indent=2).encode()) > 57344:
        # Exact typed assertion details take priority over optional payloads.
        value["diagnostic"] = {k: v for k, v in (diagnostic or {}).items()
                               if k in {"schema", "app_id", "error", "phase", "step", "artifacts"}}
        value["error"]["message"] = value["error"]["message"][-8000:]
    if len(json.dumps(value, indent=2).encode()) > 65536:
        raise ValueError("failure diagnostic exceeds its explicit context bound")
    archived = path.parent / "execution-failures" / (uuid.uuid4().hex + ".json")
    atomic_json(archived, value)
    atomic_json(path, value)
    return archived


def load_execution_failure(profile: dict, task: dict) -> dict | None:
    """Only current source-bound failure evidence can inform a repair call."""
    from swissknife_visual_functional_llm import _read
    path = execution_failure_path(profile, task)
    if not path.exists():
        return None
    try:
        value = json.loads(_read(ROOT, str(path.relative_to(ROOT)), 262144))
        if (type(value) is not dict or value.get("schema") != EXECUTION_FAILURE_SCHEMA
                or value.get("task_id") != task["task_id"]
                or value.get("task_context_sha256") != failure_task_context(task)
                or value.get("source_sha256") != repair_target_hashes(task)
                or value.get("completion_authority") is not False or value.get("work_complete") is not False):
            return None
        driver = value.get("driver_failure")
        if driver is not None:
            check_artifacts([driver], allowed_prefix=path.parent)
            diagnostic = value.get("diagnostic", {})
            for name, digest in diagnostic.get("source_sha256", {}).items():
                if sha(path_in_root(name)) != digest:
                    return None
            scenario_digest = diagnostic.get("scenario_sha256")
            if scenario_digest is not None:
                scenario = path_in_root("swissknife/test/e2e/functional-workflows/" + task["app_id"] + ".json")
                if sha(scenario) != scenario_digest:
                    return None
            for item in diagnostic.get("artifacts", []):
                check_artifacts([item], allowed_prefix=path_in_root(driver["path"]).parent)
        if value.get("visual_review"):
            check_artifacts([value["visual_review"]["original"]], allowed_prefix=path.parent)
        return {"original": artifact(path), "failure": value, "authority": "repair context only; no task acceptance"}
    except (ValueError, KeyError, TypeError, OSError, AttributeError):
        return None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def path_in_root(value: str, *, root: Path | None = None) -> Path:
    root = Path(root or ROOT).resolve()
    if type(value) is not str or not value or "\x00" in value:
        raise ValueError("invalid repository path")
    raw = Path(value)
    if raw.is_absolute():
        raw = raw.relative_to(root)
    if any(part in {"..", ".git"} for part in raw.parts):
        raise ValueError("path traversal or Git metadata is forbidden")
    path = root
    for part in raw.parts:
        path /= part
        if path.is_symlink():
            raise ValueError("symbolic-link evidence/source paths are forbidden")
    path.resolve().relative_to(root)
    return path


def runtime_root(profile: dict) -> Path:
    path = path_in_root(profile["runtimeRoot"])
    namespace = path_in_root("data/agent_supervisor/swissknife_visual_functional")
    if not path.is_relative_to(namespace):
        raise ValueError("runtime artifacts must remain in this campaign namespace")
    return path


def atomic_json(path: Path, value: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".svf-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            # Generated repair context is nested as a JSON string in the prompt.
            # Formatting whitespace costs bytes there without adding evidence.
            json.dump(value, handle, indent=None if compact else 2,
                      separators=(",", ":") if compact else None, allow_nan=not compact)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load(profile_path: str = DEFAULT_PROFILE) -> tuple[dict, dict]:
    profile = json.loads(path_in_root(profile_path).read_text())
    spec = json.loads(path_in_root(profile["taskSpecPath"]).read_text())
    return profile, spec


def workflow_fixtures(profile: dict) -> tuple[Path, dict] | None:
    """Explicit qualified owner inputs, never fabricated execution evidence."""
    name = profile.get("workflowFixturesPath")
    if name is None:
        return None
    from swissknife_visual_functional_llm import _read, _parse_json
    path = path_in_root(name)
    value = _parse_json(_read(ROOT, str(path.relative_to(ROOT)), 65536).decode())
    required = {"inference_model", "notes_collection"}
    if (type(value) is not dict or not required <= set(value)
            or set(value) - required - {"artifact_cids", "dataset_file", "dataset_cid", "gateway"}
            or value["inference_model"] != "gpt2"
            or type(value["notes_collection"]) is not str
            or re.fullmatch(r"svf-notes-[0-9a-f]{32}", value["notes_collection"]) is None):
        raise ValueError("workflow fixtures must identify the qualified CPU model and isolated existing notes collection")
    qualified_cids = []
    if "artifact_cids" in value:
        cids = value["artifact_cids"]
        if type(cids) is not dict or not cids or set(cids) - {"file-manager", "github"}:
            raise ValueError("artifact fixtures accept only file-manager/github owner CIDs")
        qualified_cids.extend(cids.values())
    if "dataset_cid" in value or "gateway" in value:
        if (not {"dataset_cid", "gateway"} <= set(value) or type(value["gateway"]) is not str or value["gateway"] not in {
                "http://127.0.0.1:8091", "http://127.0.0.1:8091/",
                "http://127.0.0.1:8092", "http://127.0.0.1:8092/"}
                or value["gateway"] != profile.get("backendReadiness", {}).get("ipfsGateway")):
            raise ValueError("dataset CID requires the exact configured loopback IPFS gateway")
        qualified_cids.append(value["dataset_cid"])
    for cid in qualified_cids:
        if type(cid) is not str or re.fullmatch(r"b[a-z2-7]{58}", cid) is None:
            raise ValueError("artifact fixture needs canonical CIDv1 raw sha256 base32")
        decoded = base64.b32decode(cid[1:].upper() + "=" * ((-len(cid[1:])) % 8))
        if (len(decoded) != 36 or decoded[:4] != b"\x01\x55\x12\x20"
                or base64.b32encode(decoded).decode().lower().rstrip("=") != cid[1:]):
            raise ValueError("artifact fixture needs canonical CIDv1 raw sha256 base32")
    if "dataset_file" in value:
        dataset = value["dataset_file"]
        prefix = "data/agent_supervisor/swissknife_visual_functional/backends/fixtures/"
        if (type(dataset) is not str or not dataset.startswith(prefix)
                or re.fullmatch(r"model-catalog[A-Za-z0-9_-]*\.json", dataset[len(prefix):]) is None):
            raise ValueError("dataset fixture must be a canonical campaign model-catalog JSON file")
        data = _parse_json(_read(ROOT, dataset, 65536).decode())
        if type(data) not in {dict, list} or not data:
            raise ValueError("dataset fixture must contain a bounded nonempty JSON object or array")
    return path, value


def validate_dag(tasks: list[dict]) -> list[str]:
    if type(tasks) is not list or not tasks:
        raise ValueError("task DAG must be a nonempty list")
    for task in tasks:
        if type(task) is not dict or type(task.get("task_id")) is not str or re.fullmatch(r"SVF-[A-Z0-9-]+", task["task_id"]) is None:
            raise ValueError("invalid task id")
        dependencies = task.get("dependencies", [])
        if type(dependencies) is not list or any(type(dep) is not str for dep in dependencies) or len(set(dependencies)) != len(dependencies):
            raise ValueError("dependencies must be unique task ids")
    ids = [item["task_id"] for item in tasks]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate task ids")
    indexed = {item["task_id"]: item for item in tasks}
    visiting, done, ordered = set(), set(), []

    def visit(task_id: str) -> None:
        if task_id not in indexed:
            raise ValueError(f"unknown dependency {task_id}")
        if task_id in visiting:
            raise ValueError(f"dependency cycle at {task_id}")
        if task_id in done:
            return
        visiting.add(task_id)
        for dependency in indexed[task_id].get("dependencies", []):
            visit(dependency)
        visiting.remove(task_id)
        done.add(task_id)
        ordered.append(task_id)
    for task_id in ids:
        visit(task_id)
    return ordered


def artifact(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path), "bytes": path.stat().st_size}


def check_artifacts(records: list[dict], *, allowed_prefix: Path | None = None,
                    allowed_sources: list[str] | None = None) -> None:
    if type(records) is not list or not records:
        raise ValueError("task evidence has no artifacts")
    sources = {path_in_root(path) for path in allowed_sources or []}
    seen = set()
    for item in records:
        if (type(item) is not dict or set(item) != {"path", "sha256", "bytes"}
                or type(item.get("sha256")) is not str or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None
                or type(item.get("bytes")) is not int or item["bytes"] < 0):
            raise ValueError("invalid artifact record")
        p = path_in_root(item["path"])
        if p in seen:
            raise ValueError("duplicate artifact record")
        seen.add(p)
        if allowed_prefix is not None and not p.is_relative_to(allowed_prefix) and p not in sources:
            raise ValueError("artifact escaped its task directory or declared source scope")
        if not p.is_file() or sha(p) != item["sha256"] or p.stat().st_size != item["bytes"]:
            raise ValueError(f"evidence changed or missing: {item['path']}")


def run(argv: list[str], *, timeout: int = 600, env: dict[str, str] | None = None) -> dict:
    if not argv or any("\x00" in part for part in argv):
        raise ValueError("invalid validation argv")
    executable = Path(argv[0]).name
    if executable not in {"python3", "python", "node", "npm", "npx"}:
        raise ValueError(f"unsupported executable {executable}")
    if executable in {"python3", "python"}:
        argv = [sys.executable, *argv[1:]]
    print("SVF run " + json.dumps(argv), flush=True)
    # Capture owners handle SIGTERM by closing their exact browser/server.
    # subprocess.run's timeout uses SIGKILL immediately, skipping that cleanup.
    # Overrides belong to this child only; retain PATH and the inherited lease.
    environment = {"env": {**os.environ, **env}} if env is not None else {}
    with subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **environment) as child:
        try:
            stdout, stderr = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:
                child.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate(timeout=5)
            raise RuntimeError("validation command timed out after owned-child cleanup") from None
        returncode = child.returncode
    tail = (stdout + "\n" + stderr)[-16000:]
    if returncode:
        raise ValidationCommandError(argv, returncode, stdout, stderr)
    if "--test" in argv and not re.search(r"(?m)^(?:#|ℹ)\s+pass\s+[1-9][0-9]*\s*$|\b[1-9][0-9]* passed\b", tail):
        raise ValueError("test command supplied no passing execution evidence")
    return {"argv": argv, "exit_code": 0, "output_tail": tail}


def dirty_paths() -> set[str]:
    # Share the supervisor's real nested-repository/index/conflict inspection.
    from swissknife_visual_functional_supervisor import dirty_paths as inspect_dirty_paths
    return set(inspect_dirty_paths(ROOT))


def check_owned_sources(profile: dict, paths: list[str]) -> None:
    campaign = runtime_root(profile)
    ledger_path = campaign / "owned-source-hashes.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    dirty = dirty_paths()
    for name in paths:
        p = path_in_root(name)
        name = str(p.relative_to(ROOT))
        # Runtime artifacts are confined to this campaign's namespace.
        if p.is_relative_to(campaign):
            continue
        overlap = [item for item in dirty if name == item or item.startswith(name.rstrip("/") + "/")
                   or name.startswith(item.rstrip("/") + "/")]
        if overlap and (any(item != name for item in overlap) or not p.is_file() or ledger.get(name) != sha(p)):
            raise RuntimeError(f"unowned dirty path: {name}; wait_for_owner_then_recheck")


def remember_owned_sources(profile: dict, paths: list[str]) -> None:
    ledger_path = runtime_root(profile) / "owned-source-hashes.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    for name in paths:
        p = path_in_root(name)
        if p.is_file():
            ledger[str(p.relative_to(ROOT))] = sha(p)
    atomic_json(ledger_path, ledger)


def assert_no_campaign_hold(profile: dict) -> None:
    campaign = runtime_root(profile)
    directories = (ROOT, campaign, campaign / "state", campaign / "watchdog")
    if any((directory / name).exists() for directory in directories
           for name in ("HOLD", "OPERATOR_STOP", "watchdog.disabled", "hold", "operator.hold")):
        raise RuntimeError("coordinator hold is active; no new model invocation or source apply")


def ensure_lease(profile: dict) -> None:
    assert_no_campaign_hold(profile)
    from swissknife_visual_functional_supervisor import assert_campaign_lease
    assert_campaign_lease(profile, root=ROOT)


def _review_projection(path: Path) -> dict:
    """Compact visual context, retaining exact source identity and omission counts.

    Repeated console/network rows are diagnostic context, not evidence the
    visual model needs to reread in full. The original capture remains intact.
    """
    data = json.loads(path.read_text())
    schema = data.get("schema")
    if schema == "swissknife.visual-functional-workflow.v2":
        from swissknife_visual_functional_final_coverage import projection
        return projection(ROOT, path)
    projection = {"schema": "swissknife.visual-functional-review-input.v1", "projection_only": True,
                  "original": artifact(path), "original_schema": schema,
                  "app_id": data.get("app_id"), "source_sha256": data.get("source_sha256"),
                  "contract_sha256": data.get("contract_sha256")}
    if schema == "swissknife.visual-functional-baseline.v1":
        projection.update(baseline_only=data.get("baseline_only"), capture_complete=data.get("capture_complete"),
                          acceptance_decision=data.get("acceptance_decision"), captured_at=data.get("captured_at"),
                          boundary=data.get("boundary"), viewports=[])
        for view in data.get("viewports", []):
            compact = {key: view.get(key) for key in ("viewport", "launch", "layout", "functional_acceptance",
                       "screenshot", "primary_screenshot", "dom_file", "screenshot_sha256", "primary_screenshot_sha256", "dom_sha256")}
            console = view.get("console_events", [])
            groups: dict[tuple[str, str], dict] = {}
            for event in console:
                if type(event) is not dict:
                    continue
                text = str(event.get("text", event.get("message", "")))
                kind = str(event.get("type", event.get("level", "unknown")))
                key = kind, hashlib.sha256(text.encode()).hexdigest()
                if key not in groups:
                    groups[key] = {"type": kind[:40], "message_sha256": key[1], "sample": text[:180], "count": 0}
                groups[key]["count"] += 1
            compact["console_summary"] = {"total_events": len(console), "unique_events": len(groups),
                "samples": sorted(groups.values(), key=lambda row: (-row["count"], row["type"], row["message_sha256"]))[:6],
                "sample_limit": 6, "original_events_retained": True,
                "capture_truncated": view.get("console_events_truncated") is True}
            network = view.get("network_events", [])
            methods = Counter(str(event.get("method", "unknown")) for event in network if type(event) is dict)
            statuses = Counter(str(event.get("status", "unobserved")) for event in network if type(event) is dict)
            compact["network_summary"] = {"total_events": len(network), "methods": dict(methods), "statuses": dict(statuses),
                "capture_truncated": view.get("network_events_truncated") is True, "original_events_retained": True}
            focus = view.get("keyboard_focus_observations", [])
            compact["keyboard_focus_observations"] = focus[:16]
            compact["keyboard_focus_total"] = len(focus)
            projection["viewports"].append(compact)
    elif schema == "swissknife.visual-functional-workflow.v1":
        projection.update(passed=data.get("passed"), actual_desktop=data.get("actual_desktop"), source_template=data.get("source_template"))
        projection["checks"] = [{"kind": item.get("kind"), "passed": item.get("passed")} for item in data.get("checks", [])]
        projection["semantic_assertions"] = [{"requirement_id": item.get("requirement_id"), "requirement_text": item.get("requirement_text"),
            "passed": item.get("passed"), "observed_sha256": stable(item.get("observed"))} for item in data.get("semantic_assertions", [])]
        projection["backend_observations"] = [{key: item.get(key) for key in ("owner", "tool_id", "transport", "correlation_id", "outcome",
            "receipt_id", "event_dag_cid", "receipt_verified", "semantic_result_verified")} for item in data.get("backend_observations", [])]
        projection["artifacts"] = data.get("artifacts", [])
        projection["note"] = "Exact observed values remain in the hashed original report; visual review does not replace the independent workflow validator."
    else:
        raise ValueError("review input needs an explicit supported evidence projection")
    return projection


def _source_excerpt(path: Path, byte_budget: int) -> dict:
    """Explicit whole-line excerpts, with immutable identity and native read path."""
    raw = path.read_bytes()
    lines = raw.decode("utf-8").splitlines(keepends=True)
    symbols = []
    pattern = re.compile(r"^\s*(?:(?:export|async)\s+)*(?:def|class|function)\s+([A-Za-z_][A-Za-z0-9_]*)")
    for index, line in enumerate(lines, 1):
        match = pattern.match(line)
        if match:
            symbols.append({"line": index, "symbol": match[1][:100]})
    projection = {"schema": "swissknife.visual-functional-source-excerpt.v1", "excerpt_only": True,
                  "original": {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
                  "full_source_read_path": str(path.relative_to(ROOT)),
                  "line_count": len(lines), "symbol_index": symbols[:32], "symbol_count": len(symbols),
                  "instruction": "These are partial source lines, not a full replacement. Read the exact full_source_read_path if omitted context is needed; preserve unseen code."}
    head, tail = min(120, len(lines)), min(80, max(0, len(lines) - 120))
    while True:
        ranges = []
        if head:
            ranges.append({"start_line": 1, "end_line": head, "content": "".join(lines[:head])})
        if tail:
            ranges.append({"start_line": len(lines) - tail + 1, "end_line": len(lines), "content": "".join(lines[-tail:])})
        projection.update(line_ranges=ranges, omitted_line_count=len(lines) - head - tail,
                          symbol_index_truncated=len(projection["symbol_index"]) < len(symbols))
        encoded = json.dumps(projection, indent=2, ensure_ascii=False).encode("utf-8")
        if len(encoded) <= byte_budget:
            return projection
        if head >= tail and head:
            head -= 1
        elif tail:
            tail -= 1
        elif projection["symbol_index"]:
            projection["symbol_index"].pop()
        else:
            raise ValueError("source excerpt metadata exceeds its explicit byte budget")


def _css_rule_excerpts(content: str):
    """Yield exact leaf-rule bytes and enclosing conditions, not cascade verdicts."""
    stack = []
    start = index = 0
    quote = None
    while index < len(content):
        char = content[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif content.startswith("/*", index):
            end = content.find("*/", index + 2)
            if end < 0:
                return
            if not content[start:index].strip():
                start = end + 2
            index = end + 2
            continue
        elif char in {"'", '"'}:
            quote = char
        elif char == "{":
            if stack:
                stack[-1]["nested"] = True
            header = content[start:index].strip()
            stack.append({"start": start, "header": header, "nested": False})
            start = index + 1
        elif char == "}":
            if not stack:
                return
            rule = stack.pop()
            if not rule["nested"]:
                yield {"header": rule["header"], "start_line": content.count("\n", 0, rule["start"]) + 1,
                       "end_line": content.count("\n", 0, index) + 1,
                       "conditions": [parent["header"] for parent in stack],
                       "content": content[rule["start"]:index + 1]}
            start = index + 1
        elif char == ";":
            start = index + 1
        index += 1


# Exact flags emitted by the real driver's collectWorkflowLayout(). Context
# phase/probe can still describe the preceding backend step, so do not infer
# layout applicability from those fields or from unstructured exception text.
_DRIVER_LAYOUT_VIOLATIONS = frozenset({
    "primary_content_not_visible", "app_window_outside_horizontal_viewport",
    "app_window_outside_vertical_viewport", "primary_content_outside_app_window",
    "primary_content_empty",
})


def _repair_needs_stylesheet_context(failure: dict) -> bool:
    """Select readonly CSS for current visual review or typed driver layout failure."""
    if type(failure) is not dict:
        return False
    if failure.get("visual_review"):
        return True
    diagnostic = failure.get("diagnostic")
    if type(diagnostic) is not dict or diagnostic.get("schema") != "swissknife.visual-functional-workflow-failure.v1":
        return False
    error = diagnostic.get("error")
    if type(error) is not dict or error.get("code") != "POSTCONDITION_FAILED":
        return False
    details = error.get("details")
    if type(details) is not dict or details.get("operator") != "equals" or details.get("expected") != []:
        return False
    actual = details.get("actual")
    return (type(actual) is list and 0 < len(actual) <= len(_DRIVER_LAYOUT_VIOLATIONS)
            and all(type(flag) is str and flag in _DRIVER_LAYOUT_VIOLATIONS for flag in actual))


def _repair_native_embedding_context(task: dict, editable: list[str], byte_budget: int = 1500) -> tuple[dict | None, list[dict]]:
    """Quote declared native mounting rules; never infer rendered/computed layout."""
    anchors = {
        "swissknife/web/js/main-simple.js": (
            '<div class="window-content">', '<div class="window-app-content">', '<div id="${windowId}-content">',
            '<div class="live-tool-gateway-host" id="${windowId}-gateway"></div>'),
        "swissknife/web/js/all-app-backend-status.js": (
            'for (const output of scope.querySelectorAll("output[data-gateway-status]")) {',
            'group.dataset.nativeOperationDetails = "true";',
            'group.style.cssText = ', 'parent.append(group);',
            'group.querySelector("[data-native-operation-body]").append(output);'),
    }
    declared = set(task.get("execution_inputs", [])) | set(editable)
    sources, excerpts = [], []
    for name, markers in anchors.items():
        if name not in declared or not path_in_root(name).is_file():
            continue
        source = artifact(path_in_root(name))
        lines = path_in_root(name).read_text().splitlines()
        selected = []
        for marker in markers:
            matches = [(index + 1, line.strip()) for index, line in enumerate(lines)
                       if line.strip().startswith(marker)]
            if len(matches) == 1:
                selected.append(matches[0])
        if selected:
            sources.append(source)
            excerpts.append({**source, "lines": selected})
    if not excerpts:
        return None, []
    context = {"authority": "Readonly exact mounts, not observed/computed layout or edit permission. "
               "Preserve app/gateway/details controls.", "sources": excerpts}
    if len(json.dumps(context, ensure_ascii=False, indent=2).encode()) > byte_budget:
        raise ValueError("native embedding source context exceeds its bound")
    return context, sources


def _repair_stylesheet_context(task: dict, editable: list[str], byte_budget: int = 12288) -> tuple[dict | None, list[dict]]:
    """Expose shared selector collisions even when native file reads are disabled.

    This is bounded readonly diagnostic context. Complete edit targets, source
    fences, browser checks and the independent visual decision remain required.
    """
    names = [name for name in dict.fromkeys(task.get("execution_inputs", [])) if name.endswith(".css")]
    if not names:
        return None, []
    # Retry input ordering is a source inventory, not the browser's cascade.
    # Derive known load positions from the actual declared desktop document.
    page_name = "swissknife/web/index.html"
    page = path_in_root(page_name)
    page_source = None
    load_order = {}
    if page_name in task.get("execution_inputs", []) and page.is_file():
        class Stylesheets(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                href = attrs.get("href", "")
                if tag == "link" and "stylesheet" in attrs.get("rel", "").split() and href.startswith("/css/"):
                    name = "swissknife/web" + href
                    if name not in load_order:
                        load_order[name] = len(load_order)
        Stylesheets().feed(page.read_text())
        page_source = artifact(page)
    tokens = set()
    for name in editable:
        source = path_in_root(name)
        if not source.is_file():
            continue
        body = source.read_text()
        tokens.update(re.findall(r"[.#]([A-Za-z_][A-Za-z0-9_-]*)", body))
        for classes in re.findall(r"\bclass\s*=\s*[\"']([^\"']+)[\"']", body):
            tokens.update(re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", classes))
    prefix = task.get("app_id", "")
    prefixes = tuple(value for value in (prefix, prefix.replace("-", "_")) if value)
    sources, candidates = [], []
    for input_order, name in enumerate(names):
        order = load_order.get(name)
        source = path_in_root(name)
        original = artifact(source)
        sources.append(original)
        for rule in _css_rule_excerpts(source.read_text()):
            selector = re.sub(r"/\*.*?\*/", "", rule.pop("header"), flags=re.S)
            matched = tokens.intersection(re.findall(r"[.#]([A-Za-z_][A-Za-z0-9_-]*)", selector))
            if not matched:
                continue
            priority = 0 if prefixes and any(token.startswith(prefixes) for token in matched) else 1
            candidates.append((priority, order if order is not None else len(load_order) + input_order,
                               {"path": name, "stylesheet_order": order,
                                                "matched_tokens": sorted(matched), **rule}))
    projection = {"schema": "swissknife.visual-functional-shared-css-context.v1", "excerpt_only": True,
                  "instruction": "Readonly exact shared CSS rules matching this app. Check inherited layout and selector specificity; conditions may restrict applicability. Preserve mobile overrides. These excerpts do not prove rendered layout or grant edit authority.",
                  "sources": sources, "stylesheet_order_document": page_source,
                  "matched_rule_count": len(candidates), "omitted_rule_count": len(candidates), "rules": []}
    for _priority, _order, rule in sorted(candidates, key=lambda row: (row[0], row[1], row[2]["start_line"])):
        projection["rules"].append(rule)
        projection["omitted_rule_count"] = len(candidates) - len(projection["rules"])
        if len(json.dumps(projection, ensure_ascii=False).encode()) > byte_budget:
            projection["rules"].pop()
            projection["omitted_rule_count"] += 1
    if len(json.dumps(projection, ensure_ascii=False).encode()) > byte_budget:
        raise ValueError("shared stylesheet identity exceeds its context bound")
    return projection, [*sources, *([page_source] if page_source else [])]


def _repair_inputs(profile: dict, task: dict, inputs: list[str], context_path: Path,
                   context_dir: Path, budget: int) -> tuple[list[str], list[dict], list[dict]]:
    """Give complete declared targets priority over supporting context excerpts."""
    from swissknife_visual_functional_llm import ModelContextBudgetError

    def encoded_size(path: str, content: str) -> int:
        return len(json.dumps({"path": path, "content": content}, ensure_ascii=False, separators=(",", ":")).encode())

    records = []
    for index, path in enumerate(dict.fromkeys(inputs)):
        source = path_in_root(path)
        content = source.read_text()
        records.append({"path": path, "source": source, "content": content, "index": index,
                        "cost": encoded_size(path, content), "artifact": artifact(source)})
    task_text = json.dumps(task, ensure_ascii=False)
    if profile.get("todoPath"):
        board = path_in_root(profile["todoPath"]).read_text()
        match = re.search(r"^## " + re.escape(task["task_id"]) + r"[^\n]*\n.*?(?=^## |\Z)", board, re.M | re.S)
        if match:
            task_text = match.group(0)
    # Account for JSON escaping, inline task context and the board's exact
    # task block, with room for adapter instructions and source hash records.
    overhead = (encoded_size(str(context_path.relative_to(ROOT)), context_path.read_text())
                + len(json.dumps(task_text, ensure_ascii=False).encode())
                + 4096 + 256 * len(task.get("edit_paths", [])))
    remaining = budget - overhead
    minimum = 2048
    if remaining < minimum * len(records):
        raise ModelContextBudgetError(overhead + minimum * len(records), budget)
    targets = set(task.get("edit_paths", []))
    mandatory_paths = targets | set(task.get("_required_context_paths", []))
    ordered = sorted(records, key=lambda row: (row["path"] not in mandatory_paths, row["index"]))
    selected = {}

    def fits_whole(row: dict, pending: int) -> bool:
        return len(row["content"].encode()) <= 250000 and row["cost"] <= remaining - minimum * (pending - 1)

    # Inline-only repair has no way to recover omitted edit bytes. Supporting
    # sources may be projected, but complete existing targets are mandatory.
    if profile.get("llm", {}).get("repairReadPolicy") == "inline_only":
        mandatory = [row for row in ordered if row["path"] in mandatory_paths]
        for row in mandatory:
            size = len(row["content"].encode())
            if size > 250000:
                raise ModelContextBudgetError(size, 250000)
        required = overhead + sum(row["cost"] for row in mandatory) + minimum * (len(records) - len(mandatory))
        if required > budget:
            raise ModelContextBudgetError(required, budget)
        for row in mandatory:
            selected[row["path"]] = row["path"]
            remaining -= row["cost"]
    # Reserve at least a labelled identity/excerpt for each other input, while
    # retaining all fitting edit targets in full before supporting sources.
    for row in ordered:
        if row["path"] not in selected and row["path"] in targets and fits_whole(row, len(records) - len(selected)):
            selected[row["path"]] = row["path"]
            remaining -= row["cost"]
    for row in ordered:
        if row["path"] in selected:
            continue
        pending = len(records) - len(selected)
        if fits_whole(row, pending):
            selected[row["path"]] = row["path"]
            remaining -= row["cost"]
            continue
        allowance = remaining - minimum * (pending - 1)
        target = context_dir / f"source-{row['index']}.json"
        relative = str(target.relative_to(ROOT))
        excerpt_budget = min(250000, allowance)
        while True:
            projected = _source_excerpt(row["source"], excerpt_budget)
            content = json.dumps(projected, indent=2, ensure_ascii=False) + "\n"
            cost = encoded_size(relative, content)
            if cost <= allowance:
                break
            excerpt_budget -= max(128, cost - allowance)
            if excerpt_budget < 768:
                raise ModelContextBudgetError(budget + cost - allowance, budget)
        atomic_json(target, projected)
        selected[row["path"]] = relative
        remaining -= cost
    complete = [row["artifact"] for row in ordered if row["path"] in targets and selected[row["path"]] == row["path"]]
    return [selected[row["path"]] for row in ordered], [row["artifact"] for row in records], complete


REPAIR_FEEDBACK_SCHEMA = "swissknife.visual-functional-repair-feedback.v1"
EDIT_ERROR_CODES = {"edit_anchor_match_count", "edit_empty_anchor_nonempty_file", "edit_source_hash_mismatch", "edit_result_too_large"}
MODEL_ERROR_CODES = {"stream_frame_budget_exceeded", "stream_tainted", "provider_timeout_with_activity", "provider_timeout_without_events",
                     "provider_timeout_without_response",
                     "native_max_turns", "native_max_tokens", "native_refusal", "native_cancelled", "native_schema_rejected",
                     "native_execution_error", "native_process_error", "provider_or_response_contract_failure"}


def repair_error_hint(value: Any, source_hashes: dict) -> dict | None:
    """Only typed, body-free diagnostics may cross a scheduled retry."""
    if type(value) is not dict:
        return None
    code = value.get("code")
    if code in {"model_invocation_failed", "task_validation_failed", "source_apply_failed", "model_declined_scope"}:
        if set(value) - {"code", "codes"}:
            return None
        codes = value.get("codes", [])
        if type(codes) is not list or len(codes) > 16 or any(type(v) is not str or v not in MODEL_ERROR_CODES for v in codes):
            return None
        return {"code": code, "codes": codes}
    fields = {"code", "path", "hunk_index", "match_count", "old_bytes", "new_bytes", "old_sha256", "new_sha256", "current_sha256", "expected_sha256"}
    if code not in EDIT_ERROR_CODES or set(value) - fields or value.get("path") not in source_hashes:
        return None
    if type(value.get("hunk_index")) is not int or not 1 <= value["hunk_index"] <= 32:
        return None
    for key in ("match_count", "old_bytes", "new_bytes"):
        if key in value and (type(value[key]) is not int or not 0 <= value[key] <= 2097152):
            return None
    for key in ("old_sha256", "new_sha256", "current_sha256", "expected_sha256"):
        if key in value and value[key] is not None and (type(value[key]) is not str or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None):
            return None
    return dict(value)


def repair_target_hashes(task: dict) -> dict:
    from swissknife_visual_functional_llm import _paths, _snapshot
    return {name: _snapshot(ROOT, name)["sha256"] for name in _paths(ROOT, task.get("edit_paths", []), 128)}


def repair_feedback_path(profile: dict, task: dict) -> Path:
    if not re.fullmatch(r"SVF-[A-Z0-9-]{1,64}", task["task_id"]):
        raise ValueError("invalid repair feedback task identity")
    return path_in_root(str(runtime_root(profile) / "tasks" / task["task_id"] / "last-repair-error.json"))


def load_repair_feedback(profile: dict, task: dict) -> dict | None:
    """A retry hint has no authority and is valid only for these exact bytes."""
    from swissknife_visual_functional_llm import _read, _response, _json, _sha, safe_rejected_response
    try:
        path = repair_feedback_path(profile, task)
        value = json.loads(_read(ROOT, str(path.relative_to(ROOT)), 16384))
        if (type(value) is not dict or set(value) - {"schema", "task_id", "task_spec_sha256", "source_sha256", "error", "completion_authority", "rejected_response"}
                or value.get("schema") != REPAIR_FEEDBACK_SCHEMA or value.get("task_id") != task["task_id"]
                or value.get("task_spec_sha256") != stable(task) or value.get("source_sha256") != repair_target_hashes(task)
                or value.get("completion_authority") is not False):
            return None
        error = repair_error_hint(value.get("error"), value["source_sha256"])
        if error is None:
            return None
        value["error"] = error
        # Retained model bodies are read only from an independently hashed,
        # bounded, declared-path JSON candidate, never from provider logs.
        candidate = value.get("rejected_response")
        if candidate is not None:
            if (type(candidate) is not dict or set(candidate) != {"path", "sha256", "bytes", "response_sha256"}
                    or type(candidate.get("bytes")) is not int or not 0 < candidate["bytes"] <= 2097152):
                return None
            target = path_in_root(candidate["path"])
            if not target.is_relative_to(path.parent / "rejected-responses"):
                return None
            raw = _read(ROOT, candidate["path"], 2097152)
            response = _response(json.loads(raw), task["task_id"], "repair", [], ROOT, task.get("edit_paths", []), validate_edit_bytes=False)
            if (_sha(raw) != candidate["sha256"] or len(raw) != candidate["bytes"]
                    or _sha(_json(response).encode()) != candidate["response_sha256"] or not safe_rejected_response(response)):
                return None
        return value
    except (ValueError, TypeError, KeyError, OSError, AttributeError):
        return None


def remember_repair_failure(profile: dict, task: dict, *, source_hashes: dict, output: Path | None = None,
                            previous_output_sha256: str | None = None, validation_failed: bool = False,
                            apply_failed: bool = False, declined: bool = False) -> None:
    """Keep body-free retry diagnostics across worker/scheduler invocations."""
    from swissknife_visual_functional_llm import RECEIPT_SCHEMA, _read, _response, _json, _sha, safe_rejected_response
    try:
        if source_hashes != repair_target_hashes(task):
            return  # A concurrent or admitted source change invalidates the hint.
    except (ValueError, OSError):
        return
    path = repair_feedback_path(profile, task)
    feedback = {"schema": REPAIR_FEEDBACK_SCHEMA, "task_id": task["task_id"], "task_spec_sha256": stable(task),
                "source_sha256": source_hashes, "error": {"code": "model_declined_scope" if declined else "source_apply_failed" if apply_failed else "task_validation_failed" if validation_failed else "model_invocation_failed"},
                "completion_authority": False}
    if output is not None and output.is_file() and sha(output) != previous_output_sha256:
        try:
            receipt = json.loads(_read(ROOT, str(output.relative_to(ROOT)), 3145728))
            recorded_sources = {item["path"]: item.get("sha256") for item in receipt.get("input_files", []) if item.get("path") in source_hashes}
            if (receipt.get("schema") == RECEIPT_SCHEMA and receipt.get("task_id") == task["task_id"]
                    and receipt.get("mode") == "repair" and receipt.get("success") is False and recorded_sources == source_hashes):
                codes = receipt.get("failure_diagnostics", {}).get("codes", [])
                if type(codes) is list:
                    feedback["error"]["codes"] = [code for code in codes if type(code) is str and code in MODEL_ERROR_CODES][:16]
                detail = receipt.get("edit_validation_error", {})
                hint = repair_error_hint(detail, source_hashes)
                if hint:
                    feedback["error"] = hint
                response = receipt.get("rejected_response")
                if response is not None:
                    response = _response(response, task["task_id"], "repair", [], ROOT, task.get("edit_paths", []), validate_edit_bytes=False)
                    digest = _sha(_json(response).encode())
                    if digest == receipt.get("rejected_response_sha256") and safe_rejected_response(response):
                        target = path_in_root(str(path.parent / "rejected-responses" / (digest + ".json")))
                        atomic_json(target, response)
                        feedback["rejected_response"] = {**artifact(target), "response_sha256": digest}
        except (ValueError, TypeError, KeyError, OSError, AttributeError):
            pass  # Malformed or unallowlisted data never becomes retry input.
    atomic_json(path, feedback)



def _backend_checks_fence(profile: dict, task: dict, expected: dict | None = None) -> dict:
    """A backend probe is admitted work: lease, owned sources and capacity first."""
    ensure_lease(profile)
    check_owned_sources(profile, task.get("edit_paths", []))
    assert_storage_available(profile)
    from swissknife_visual_functional_native_context import backend_source_hashes
    current = backend_source_hashes(ROOT, task)
    if expected is not None and current != expected:
        raise ValueError("backend static sources changed during original checks")
    return current


def _backend_original_checks(profile: dict, task: dict) -> dict:
    """Run original checks before asking a backend model to guess a repair."""
    from swissknife_visual_functional_native_context import write_backend_check_report, backend_output_tail
    if profile.get("runtimeRoot") != "data/agent_supervisor/swissknife_visual_functional":
        raise ValueError("backend checks require the registered campaign namespace")
    sources = _backend_checks_fence(profile, task)
    observed = []
    diagnostic = None
    for index, command in enumerate(task["checks"]):
        _backend_checks_fence(profile, task, sources)
        try:
            actual = run(command, timeout=task.get("timeout_seconds", 1200))
        except ValidationCommandError as error:
            stdout = error.stdout.encode()[-16000:].decode(errors="ignore")
            stderr = error.stderr.encode()[-16000:].decode(errors="ignore")
            observed.append({"index": index, "declared_argv": command, "executed_argv": error.argv,
                             "exit_code": error.returncode, "output_tail": backend_output_tail(stdout, stderr)})
            diagnostic = {"stage": "command", "code": "ValidationCommandError", "check_index": index,
                          "argv": error.argv, "exit_code": error.returncode,
                          "stdout_tail": stdout, "stderr_tail": stderr}
            _backend_checks_fence(profile, task, sources)
            break
        _backend_checks_fence(profile, task, sources)
        observed.append({"index": index, "declared_argv": command, "executed_argv": actual["argv"],
                         "exit_code": actual["exit_code"], "output_tail": actual["output_tail"].encode()[-16000:].decode(errors="ignore")})
    _backend_checks_fence(profile, task, sources)
    return write_backend_check_report(ROOT, task, source_sha256=sources, checks=observed, diagnostic=diagnostic)


def _backend_producer_fence(profile: dict, task: dict, reference: dict) -> dict:
    from swissknife_visual_functional_native_context import load_backend_check_report
    _backend_checks_fence(profile, task)
    loaded = load_backend_check_report(ROOT, task, reference)
    report = loaded["report"]
    birth = Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19]
    if report["producer_pid"] != os.getpid() or report["producer_birth"] != birth:
        raise ValueError("backend model requires this worker's fresh actual producer observation")
    return loaded


def model(profile_path: str, task: dict, mode: str, inputs: list[str], screenshots: list[str], output: Path,
          *, recovery_context: dict | None = None, preserve_feedback: bool = False,
          edit_paths_override: list[str] | None = None, backend_producer: dict | None = None,
          remediation_payment: tuple[dict, str] | None = None) -> dict:
    from swissknife_visual_functional_llm import invoke_task_model, validate_model_receipt, model_call_limits, RECEIPT_SCHEMA
    profile, _spec = load(profile_path)
    assert_no_campaign_hold(profile)
    assert_storage_available(profile)
    if not output.is_relative_to(runtime_root(profile)):
        raise ValueError("model output must remain in this campaign runtime")
    contracts = json.loads(path_in_root(profile["appContractPath"]).read_text())
    if task.get("kind") == "final-app-verify" and mode != "review":
        raise ValueError("final-app-verify cannot create paid repair admissions")
    context_keys = ("task_id", "title", "kind", "app_id", "acceptance") if mode == "review" else (
        "task_id", "title", "kind", "app_id", "acceptance", "checks", "edit_paths", "dependencies", "llm_limits", "conflict_policy")
    context_task = {key: task[key] for key in context_keys if key in task}
    editable = task.get("edit_paths", [])
    if edit_paths_override is not None:
        from swissknife_visual_functional_llm import _paths
        editable = _paths(ROOT, edit_paths_override, 128)
        if not set(editable) <= set(task.get("edit_paths", [])):
            raise ValueError("recovery edit scope exceeds the original task")
        context_task["edit_paths"] = editable
    context = {"task": context_task, "authority": "proposal_only; do not manufacture test evidence"}
    supporting_sources = []
    absent_final_sources = []
    review_reports = ([path_in_root(name) for name in inputs if Path(name).name == "workflow.json"]
                      if mode == "review" and task.get("kind") in {"verify", "final-app-verify"} else [])
    independent_review = task.get("kind") == "final-app-verify" or any(
        json.loads(report.read_text()).get("schema") == "swissknife.visual-functional-workflow.v2"
        for report in review_reports)
    if independent_review:
        from swissknife_visual_functional_final_coverage import binding
        if len(review_reports) != 1:
            raise ValueError("final viewport review needs one exact independent workflow parent")
        final_evidence = validate_workflow(profile, task, review_reports[0])
        if screenshots != [item["path"] for item in final_evidence["images"]]:
            raise ValueError("final viewport review images differ from the exact ordered result screenshots")
        context["final_workflow_evidence"] = binding(task, final_evidence)
        for name, expected in final_evidence["data"]["source_sha256"].items():
            if expected is None:
                source = path_in_root(name)
                if source.exists() or source.is_symlink():
                    raise ValueError("final viewport absent optional source materialized during review assembly")
                absent_final_sources.append(name)
                continue
            record = artifact(path_in_root(name))
            if record["sha256"] != expected:
                raise ValueError("final viewport source changed during review context assembly")
            supporting_sources.append(record)
    checked_backend = None
    if backend_producer is not None:
        if mode != "repair" or task.get("kind") != "backend-repair":
            raise ValueError("backend producer observations cannot qualify another model mode")
        from swissknife_visual_functional_native_context import backend_check_model_context
        checked_backend = _backend_producer_fence(profile, task, backend_producer)
        context["backend_original_checks"] = backend_check_model_context(checked_backend)
        supporting_sources.append(checked_backend["original"])
    native_foundation = None
    if mode == "repair":
        from swissknife_visual_functional_native_context import load_native_foundation_context
        native_foundation = load_native_foundation_context(ROOT, task)
        if native_foundation is not None:
            context["native_foundation_context"] = native_foundation["context"]
            supporting_sources += native_foundation["sources"]
            inputs = [name for name in inputs if name not in native_foundation["replace_inputs"]]
            inputs = list(dict.fromkeys([*inputs, *native_foundation["full_inputs"]]))
    fixtures = workflow_fixtures(profile)
    qualified_fixture_sources = set()
    if fixtures is not None:
        fixture_path, fixture_values = fixtures
        context["qualified_workflow_inputs"] = {"values": fixture_values, "original": artifact(fixture_path),
            "authority": "fixture inputs only; current genuine owner results and original checks still decide acceptance"}
        supporting_sources.append(artifact(fixture_path))
        if fixture_values.get("dataset_file"):
            dataset_source = artifact(path_in_root(fixture_values["dataset_file"]))
            context["qualified_workflow_inputs"]["dataset_source"] = dataset_source
            supporting_sources.append(dataset_source)
            qualified_fixture_sources.add(dataset_source["path"])
    included_failure_copy = False
    if recovery_context is not None:
        source_bindings = recovery_context.get("source_before", {})
        context["bounded_recovery"] = {**recovery_context,
            "source_before": {name: value for name, value in source_bindings.items() if name in editable},
            "original_source_identity": {"sha256": stable(source_bindings), "source_count": len(source_bindings),
                "authority": "full admission source map remains fenced by the recovery bridge; only declared edits are model writable"}}
        for name, value in recovery_context.get("feedback_inputs", {}).items():
            if value.get("included") is True and name == str(execution_failure_path(profile, task).relative_to(ROOT)):
                observed = load_execution_failure(profile, task)
                if observed is None or observed["original"]["sha256"] != value["sha256"]:
                    raise ValueError("recovery failure evidence is stale; reproduce the original producer before repair")
                included_failure_copy = True
                # Its body is supplied once through the immutable feedback copy.
                supporting_sources.append(observed["original"])
                failure = observed["failure"]
                if failure.get("driver_failure"):
                    supporting_sources.append(failure["driver_failure"])
                    supporting_sources += failure.get("diagnostic", {}).get("artifacts", [])
                    supporting_sources += [artifact(path_in_root(p)) for p in failure.get("diagnostic", {}).get("source_sha256", {})]
    limits = model_call_limits(profile, mode, task.get("llm_limits"))
    if mode == "repair":
        # Some command tasks have no declared immutable failure-copy input.
        # They still need the current source-bound producer error. Suppress its
        # inline body only when this exact failure was supplied in the packet.
        observed_failure = load_execution_failure(profile, task) if not included_failure_copy and checked_backend is None else None
        if observed_failure is not None:
            context["latest_execution_failure"] = observed_failure
            supporting_sources.append(observed_failure["original"])
            failure = observed_failure["failure"]
            if failure.get("driver_failure"):
                supporting_sources.append(failure["driver_failure"])
                supporting_sources += failure.get("diagnostic", {}).get("artifacts", [])
                supporting_sources += [artifact(path_in_root(name))
                                       for name in failure.get("diagnostic", {}).get("source_sha256", {})]
            if failure.get("visual_review"):
                supporting_sources.append(failure["visual_review"]["original"])
            context["repair_evidence_scope"] = ("The retained producer failure is diagnostic context, not acceptance. "
                "Use its actual assertion/backend observations to propose a scoped fix. A repair proposal does not require "
                "performing final visual review; the original browser checks and a separate screenshot review still decide acceptance.")
        previous_feedback = load_repair_feedback(profile, task)
        if previous_feedback:
            context["last_repair_error"] = previous_feedback
            context["retry_instruction"] = ("Correct this exact preceding failure before proposing changes. The rejected_response artifact, if present, "
                "is a bounded rejected JSON proposal supplied as context, not applied code. Use current target hashes and exact unique anchors. "
                "Do not repeat the rejected hunk or infer success from this feedback.")
            if previous_feedback.get("rejected_response"):
                inputs = [*inputs, previous_feedback["rejected_response"]["path"]]
        context["repair_scope"] = ("Return one small, concrete patch for this existing application and its declared workflow scenario. "
            "Start with the latest concrete validation error or highest-priority finding. Preserve working behavior and previously passing changes. "
            "Use existing UI controls and infrastructure; avoid redesigning the application or building a new framework. "
            "The original checks and browser verification still decide acceptance; never replace checks or invent observed results."
            if task.get("app_id") else
            "One bounded implementation step; preserve previously applied passing changes and address the latest concrete validation error.")
        if previous_feedback and {"provider_timeout_without_response", "provider_timeout_with_activity"}.intersection(previous_feedback.get("error", {}).get("codes", [])):
            context["retry_instruction"] += (" The preceding call reached its deadline without a usable validated response; "
                "any partial provider output was not applied. Produce the smallest useful exact patch now instead of planning a complete rewrite.")
        if checked_backend is not None:
            context["retry_instruction"] = ("Use the freshly executed original backend checks below; older repair feedback is historical. "
                "If these checks passed and the supplied source needs no fix, return a fresh repair-mode pass with edits=[]; "
                "do not invent a failure or manufacture evidence. Original checks still rerun after your response.")
        context["proposal_contract"] = {"edits": [{"path": "one declared edit path", "before_sha256": "original SHA-256 or null for a new file",
            "old": "exact unique existing text; empty only for a missing/empty file", "new": "replacement text"}],
            "validation_owner": "The supervisor applies checked hunks under its lease, then runs every declared task check."}
        context["model_context_bytes"] = limits["modelContextBytes"]
        context["complete_edit_targets"] = []
        context["read_policy"] = ("Use the inline full contents and SHA-256 of complete_edit_targets for exact hunks. "
            "Use native read_file only when an explicit source excerpt omits needed lines. "
            "Do not reread complete targets or explore campaign/repository files.")
        if profile.get("llm", {}).get("repairReadPolicy") == "inline_only":
            context["read_policy"] = ("Native tools are disabled. Use only supplied complete source and bounded rejected-proposal context. "
                "Never guess omitted source or claim completed work. Return blocked with a precise missing-context finding if needed.")
    if task.get("app_id"):
        app = next(a for a in contracts["apps"] if a["app_id"] == task["app_id"])
        context["app_contract"] = ({key: app[key] for key in ("app_id", "title", "disposition", "launch", "primary_workflow", "visual_checks", "backend_boundary") if key in app}
                                   if mode == "review" else app)
        if mode == "review":
            context["review_scope"] = ("baseline_visual_triage" if task["kind"] == "review" else
                "independent_desktop_mobile_semantic_final_review" if independent_review else "final_visual_review")
        elif mode == "repair":
            # The canonical app contract is already supplied above. Whole-app
            # repository catalogues add unrelated entries and can displace the
            # complete edit targets. Preserve their identities and recheck the
            # original bytes after the call instead of inlining those bodies.
            context["app_contract_source"] = artifact(path_in_root(profile["appContractPath"]))
            supporting_sources.append(context["app_contract_source"])
            from swissknife_visual_functional_native_context import load_native_app_context
            native_contract = load_native_app_context(ROOT, task)
            if native_contract is not None:
                context["native_backend_contract"] = native_contract
                supporting_sources.append(native_contract["original"])
            catalogues = {"swissknife/src/services/apps/virtual-desktop-app-manifest.ts",
                          "swissknife/src/services/apps/all-app-executable-backend-contract.ts"}
            omitted = [artifact(path_in_root(path)) for path in dict.fromkeys(inputs)
                       if path in catalogues and path not in editable]
            if omitted:
                context["omitted_repository_metadata"] = omitted
                context["metadata_scope"] = "Readonly global catalogues omitted; use the canonical app_contract for this app. Edit targets remain complete."
                supporting_sources += omitted
                inputs = [path for path in inputs if path not in {item["path"] for item in omitted}]
            scenario_contract = "swissknife/docs/visual-functional-driver-contract.md"
            inputs = [*inputs, scenario_contract]
            native_sources = [artifact(path_in_root(name)) for name in (
                "swissknife/web/js/live-tool-gateway.js", "swissknife/web/js/apps/network-native-tools.js")
                if path_in_root(name).is_file()]
            supporting_sources += native_sources
            context["scenario_input_contract"] = {
                "path": scenario_contract,
                "native_sources": native_sources,
                "instruction": "Use exact documented scenario grammar; runner/validators/acceptance are readonly. "
                    "Native ESM API: import {invokeNativeTool} from '../live-tool-gateway.js' in apps/ modules "
                    "('./live-tool-gateway.js' in web/js/); never window/global. "
                    "invokeNativeTool(container,appId,bindingId,{executionMode:'execute',toolId,payload,trigger}). "
                    "Use /mcp/tools/bindings?app_id=<id> controls.safe_payloads[toolId] for qualified argument defaults; never invent CIDs/paths. "
                    "Use app_contract.backend_roles exact binding/tool candidates/transports. Governed means mutates_remote_state "
                    "or policy_class not read/media_capture: click its REAL gateway confirmation via trusted browser action. "
                    "Ungoverned read/media_capture has NO dialog; await actual result. Never infer policy from tool name, "
                    "synthesize/move/poll consent controls or bypass proof. invokeNetworkNativeTool(container,appId,tool,payload,trigger) "
                    "takes an exact mcp++ operation key, NOT a binding ID, and does not forward executionMode. "
                    "Use canonical invokeNativeTool for real binding execution. Confirmation starts async dispatch; "
                    "wait for native result readiness before assertions/reopen, never a fixed sleep. "
                    "Keep the native window frame bounded with app-scoped flex/min-height:0 and internal scrolling; "
                    "never hide shared controls or weaken layout checks."}
    elif not task.get("recovery_canary") and native_foundation is None:
        context["canonical_apps"] = [{"app_id": a["app_id"], "title": a["title"], "disposition": a["disposition"]} for a in contracts["apps"]]
    stylesheet_budget = 12288
    stylesheet_sources = []
    if mode == "repair":
        visual_failure = load_execution_failure(profile, task)
        if visual_failure is not None and _repair_needs_stylesheet_context(visual_failure["failure"]):
            embedding_context, embedding_sources = _repair_native_embedding_context(task, editable)
            if embedding_context is not None:
                context["native_embedding_context"] = embedding_context
                supporting_sources += embedding_sources
            stylesheet_context, stylesheet_sources = _repair_stylesheet_context(task, editable, byte_budget=stylesheet_budget)
            if stylesheet_context is not None:
                context["shared_stylesheet_context"] = stylesheet_context
                supporting_sources += stylesheet_sources
    context_dir = output.parent / "model-inputs" / (output.stem + "-" + uuid.uuid4().hex)
    context_path = context_dir / "context.json"
    atomic_json(context_path, context, compact=mode == "repair")
    # Avoid sending the full 45-app task database into every model turn.
    inputs = [p for p in inputs if p not in {profile["taskSpecPath"], profile["appContractPath"]}]
    if mode == "repair":
        inputs = [path for path in inputs if path != profile["humanPlanPath"]]
        # A preceding attempt can have created a target which was absent when
        # execute() assembled its initial input list. Include its current bytes
        # on the next call instead of asking the model to recreate its design.
        inputs = list(dict.fromkeys([*inputs, *[path for path in editable if path_in_root(path).is_file()]]))
    cache_input_paths = list(inputs)
    original_sources = []
    if mode == "review":
        inputs = [path for path in inputs if path != profile["humanPlanPath"]]
        compact_inputs = []
        for index, path in enumerate(inputs):
            source = path_in_root(path)
            original_sources.append(artifact(source))
            projected = _review_projection(source)
            target = context_dir / f"evidence-{index}.json"
            atomic_json(target, projected)
            compact_inputs.append(str(target.relative_to(ROOT)))
        inputs = compact_inputs
    elif mode == "repair":
        compact_inputs = []
        projected_reviews = []
        for index, path in enumerate(inputs):
            source = path_in_root(path)
            review = None
            if source.suffix == ".json" and path not in editable:
                try:
                    data = json.loads(source.read_text())
                    if (type(data) is dict and data.get("schema") == RECEIPT_SCHEMA and data.get("mode") == "review"
                            and data.get("success") is True and type(data.get("response")) is dict):
                        review = data
                except (ValueError, OSError):
                    pass
            if review is None:
                compact_inputs.append(path)
                continue
            original = artifact(source)
            supporting_sources.append(original)
            target = context_dir / f"review-context-{index}.json"
            atomic_json(target, {"schema": "swissknife.visual-functional-review-context.v1", "original": original,
                                 "response": review["response"], "authority": "repair context only; original evidence remains authoritative"})
            projected_reviews.append(original)
            compact_inputs.append(str(target.relative_to(ROOT)))
        if projected_reviews:
            context["projected_review_sources"] = projected_reviews
        atomic_json(context_path, context, compact=mode == "repair")
        inputs = compact_inputs
        required_feedback = [value["path"] for value in (recovery_context or {}).get("feedback_inputs", {}).values()
                             if value.get("included") is True]
        if native_foundation is not None:
            required_feedback += native_foundation["full_inputs"]
        # Optional shared CSS must not displace complete edit targets or the
        # required producer failure. Rebuild only this readonly projection,
        # before any provider admission/call, with a finite local retry bound.
        from swissknife_visual_functional_llm import ModelContextBudgetError
        for context_attempt in range(3):
            try:
                inputs, original_sources, complete = _repair_inputs(profile,
                    dict(task, edit_paths=editable, _required_context_paths=required_feedback),
                    inputs, context_path, context_dir, limits["modelContextBytes"])
                break
            except ModelContextBudgetError as error:
                if ("shared_stylesheet_context" not in context or context_attempt == 2
                        or error.limit_bytes != limits["modelContextBytes"]):
                    raise
                next_budget = stylesheet_budget - (error.actual_bytes - error.limit_bytes) - 1024
                if next_budget <= 0:
                    raise
                projection, rebuilt_sources = _repair_stylesheet_context(task, editable, byte_budget=next_budget)
                if rebuilt_sources != stylesheet_sources:
                    raise ValueError("shared stylesheet source identity changed during context assembly")
                context["shared_stylesheet_context"] = projection
                stylesheet_budget = next_budget
                atomic_json(context_path, context, compact=mode == "repair")
        context["complete_edit_targets"] = complete
        atomic_json(context_path, context, compact=mode == "repair")
    inputs = list(dict.fromkeys([str(context_path.relative_to(ROOT)), *inputs]))
    assert_no_campaign_hold(profile)
    source_hashes = repair_target_hashes(task) if mode == "repair" else {}
    previous_output_sha256 = sha(output) if output.is_file() else None
    blocked_scope = None
    current_failure = None
    blocked_directory = runtime_root(profile) / "tasks" / task["task_id"] / "blocked-repairs"
    if mode == "repair":
        from swissknife_visual_functional_blocked import build_scope, build_proposal_scope, build_producer_scope, raise_if_blocked
        current_failure = load_execution_failure(profile, task) if checked_backend is None else None
        # A backend's actual check output is a producer observation. Until it
        # has its own verified stable identity it must not be silently folded
        # into the no-producer proposal-decline cache.
        backend_check_feedback = any(
            path_in_root(name).parent == runtime_root(profile) / "tasks" / task["task_id"]
            and re.fullmatch(r"failure-[1-9][0-9]*\.txt", Path(name).name)
            for name in cache_input_paths)
        backend_proposal = (task.get("kind") == "backend-repair" and current_failure is None
                            and not backend_check_feedback and checked_backend is None)
        if checked_backend is not None or backend_proposal or (current_failure is not None and current_failure["failure"]["error"].get("code") != "browser_contention"):
            # Original stable dependencies qualify a new proposal. Generated
            # attempt contexts, progress and receipts must never defeat a
            # negative result merely by acquiring new paths/correlations.
            readonly = {}
            records = [*supporting_sources, *original_sources]
            names = [*cache_input_paths, *task.get("context_paths", []), *task.get("execution_inputs", []),
                     "scripts/swissknife_visual_functional_worker.py", "scripts/swissknife_visual_functional_llm.py",
                     "scripts/swissknife_visual_functional_blocked.py", "scripts/swissknife_visual_functional_phase_budget.py",
                     *[name for name in source_hashes if name not in editable],
                     *list(checked_backend["report"]["source_sha256"] if checked_backend is not None else [])]
            for name in dict.fromkeys(names):
                path = path_in_root(name)
                if name not in editable and not path.is_relative_to(runtime_root(profile)):
                    records.append({"path": name, "sha256": sha(path) if path.is_file() else None})
            for record in records:
                name = record["path"]
                if name in editable or (path_in_root(name).is_relative_to(runtime_root(profile))
                                        and name not in qualified_fixture_sources):
                    continue
                if name in readonly and readonly[name] != record["sha256"]:
                    raise ValueError("negative repair source identity changed during context assembly")
                readonly[name] = record["sha256"]
            if checked_backend is not None:
                blocked_scope = build_producer_scope(ROOT, task=dict(task, edit_paths=editable), route=profile["llm"],
                    edit_hashes={name: source_hashes[name] for name in editable}, readonly_hashes=readonly,
                    producer=backend_producer, producer_task=task)
                context["producer_identity_sha256"] = stable(blocked_scope["identity"]["producer"])
                context["proposal_scope_fingerprint"] = blocked_scope["fingerprint"]
                atomic_json(context_path, context, compact=mode == "repair")
            elif backend_proposal:
                blocked_scope = build_proposal_scope(ROOT, task=dict(task, edit_paths=editable), route=profile["llm"],
                    edit_hashes={name: source_hashes[name] for name in editable}, readonly_hashes=readonly)
                context["proposal_scope_fingerprint"] = blocked_scope["fingerprint"]
                atomic_json(context_path, context, compact=mode == "repair")
            else:
                blocked_scope = build_scope(ROOT, task=dict(task, edit_paths=editable), route=profile["llm"],
                    edit_hashes={name: source_hashes[name] for name in editable}, readonly_hashes=readonly,
                    failure=current_failure)
            raise_if_blocked(ROOT, blocked_directory, blocked_scope)
    # A changed readonly dependency can requalify semantic retries, but cannot
    # replenish paid attempts at the same required acceptance barrier.
    phase_admission = None
    phase_finished = False
    remediation_admission = None
    remediation_finished = False
    # Recheck after potentially large context assembly and immediately before
    # phase/provider admission. A pre-admission refusal spends nothing.
    assert_no_campaign_hold(profile)
    assert_storage_available(profile)
    if checked_backend is not None:
        _backend_producer_fence(profile, task, backend_producer)
    if mode == "repair" and task.get("kind") != "scoped-remediation" and current_failure is not None and current_failure["failure"].get("visual_review"):
        from swissknife_visual_functional_phase_budget import admit
        phase_admission = admit(ROOT, task, current_failure["failure"]["visual_review"]["original"], source_hashes)
    if task.get("kind") == "scoped-remediation" and remediation_payment != (task, "proposal"):
        raise ValueError("scoped remediation cannot bypass its single proposal admission")
    if remediation_payment is not None:
        child, role = remediation_payment
        if not ((role == "proposal" and task == child and mode == "repair")
                or (role == "assessment" and mode == "review" and task["task_id"] == child["phase_remediation"]["original_task"]["task_id"])):
            raise ValueError("remediation payment role/task/mode differs")
    def before_remediation_provider(metadata):
        nonlocal remediation_admission
        ensure_lease(profile)
        assert_no_campaign_hold(profile)
        assert_storage_available(profile)
        from swissknife_visual_functional_phase_remediation import admit_payment
        remediation_admission = admit_payment(ROOT, profile, _spec, remediation_payment[0], remediation_payment[1], metadata)
    print(f"SVF router grok_cli/grok-4.7 task={task['task_id']} mode={mode}", flush=True)
    declined = False
    try:
        receipt = invoke_task_model(profile_path, task["task_id"], mode, input_paths=inputs,
                                    screenshot_paths=screenshots,
                                    predicted_files=editable if mode == "repair" else [],
                                    output_path=str(output.relative_to(ROOT)), root=ROOT, task_limits=task.get("llm_limits"),
                                    **({"before_provider": before_remediation_provider} if remediation_payment is not None else {}))
        validate_model_receipt(ROOT, receipt, task_id=task["task_id"], mode=mode,
                               require_visual=mode == "review", predicted_files=editable)
        if original_sources or supporting_sources:
            # A failed workflow names the same app source that is also supplied in
            # full as an edit target. Shared identity is expected; conflicting
            # snapshots of that identity still invalidate the call.
            snapshots = {}
            for item in [*supporting_sources, *original_sources]:
                if item["path"] in snapshots and snapshots[item["path"]] != item:
                    raise ValueError("source evidence changed between failure context and supplied source")
                snapshots[item["path"]] = item
            check_artifacts(list(snapshots.values()))
        for name in absent_final_sources:
            source = path_in_root(name)
            if source.exists() or source.is_symlink():
                raise ValueError("final viewport absent optional source materialized during model invocation")
        response = receipt.get("response", {})
        if checked_backend is not None:
            _backend_producer_fence(profile, task, backend_producer)
        if phase_admission is not None:
            from swissknife_visual_functional_phase_budget import finish
            finish(ROOT, task, phase_admission, receipt_path=receipt.get("attempt_receipt_path", output))
            phase_finished = True
        if remediation_admission is not None:
            from swissknife_visual_functional_phase_remediation import finish_payment
            finish_payment(ROOT, profile, remediation_payment[0], remediation_admission,
                           receipt=artifact(output))
            remediation_finished = True
        if mode == "repair" and (response.get("decision") == "blocked"
                or response.get("decision") == "needs_changes" and not response.get("edits")):
            if blocked_scope is not None and response.get("decision") == "blocked" and response.get("edits") == []:
                from swissknife_visual_functional_blocked import remember_blocked
                remember_blocked(ROOT, blocked_directory, blocked_scope, output)
            declined = True
            raise ValueError("model declined this scoped repair; no task completion or source application")
    except Exception as error:
        resource = storage_refusal(error)
        if resource is not None:
            # Already-admitted work retains its durable spend; do not refund,
            # emit app repair feedback or attempt more writes to a full disk.
            raise resource from None
        if phase_admission is not None and not phase_finished:
            from swissknife_visual_functional_phase_budget import finish
            finish(ROOT, task, phase_admission, receipt_path=output if output.is_file() and sha(output) != previous_output_sha256 else None,
                   error_type=type(error).__name__)
        if remediation_admission is not None and not remediation_finished:
            from swissknife_visual_functional_phase_remediation import finish_payment
            finish_payment(ROOT, profile, remediation_payment[0], remediation_admission,
                           error_type=type(error).__name__)
        if mode == "repair":
            remember_repair_failure(profile, task, source_hashes=source_hashes, output=output,
                                    previous_output_sha256=previous_output_sha256, declined=declined)
        raise
    if mode == "repair" and not preserve_feedback:
        repair_feedback_path(profile, task).unlink(missing_ok=True)
    return receipt


def baseline_files(profile: dict, task: dict, report: Path) -> list[Path]:
    directory = report.parent
    if not directory.is_relative_to(runtime_root(profile)):
        raise ValueError("baseline escaped this campaign runtime")
    data = json.loads(report.read_text())
    if data.get("schema") != "swissknife.visual-functional-baseline.v1" or data.get("app_id") != task["app_id"]:
        raise ValueError("baseline identity/schema mismatch")
    if data.get("baseline_only") is not True or data.get("capture_complete") is not True or data.get("acceptance_decision") != "not_evaluated":
        raise ValueError("a baseline cannot claim workflow acceptance")
    # Reuse the capture owner's independent artifact/source/DOM validator. It
    # imports no browser session and performs no captures or backend operations.
    validator = (
        "import fs from 'node:fs';import{validateBaselineEvidence}from './swissknife/scripts/capture-visual-functional-baseline.mjs';"
        "const[p,d]=process.argv.slice(1);validateBaselineEvidence(JSON.parse(fs.readFileSync(p,'utf8')),d);"
    )
    run(["node", "--input-type=module", "-e", validator, str(report), str(directory)], timeout=90)
    files = [report]
    for name in ["desktop.png", "mobile.png", "desktop-primary.png", "mobile-primary.png"]:
        image = directory / name
        if not image.is_file() or image.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or image.stat().st_size < 128:
            raise ValueError(f"missing actual screenshot {image}")
        files.append(image)
    for viewport in data["viewports"]:
        dom = path_in_root(str((directory / viewport["dom_file"]).relative_to(ROOT)))
        if not dom.is_relative_to(directory) or not dom.is_file():
            raise ValueError("baseline DOM artifact escaped the capture attempt")
        files.append(dom)
    return files


def baseline(profile: dict, task: dict, directory: Path) -> list[Path]:
    assert_no_campaign_hold(profile)
    assert_storage_available(profile)
    directory.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="attempt-", dir=directory))
    run(["node", "swissknife/scripts/capture-visual-functional-baseline.mjs", "--app", task["app_id"],
         "--output-dir", str(attempt)], timeout=task.get("timeout_seconds", 900))
    return baseline_files(profile, task, attempt / "baseline.json")


def resolve_baseline(profile: dict, task_id: str) -> tuple[Path, list[str]]:
    spec = json.loads(path_in_root(profile["taskSpecPath"]).read_text())
    task = next((item for item in spec["tasks"] if item["task_id"] == task_id and item["kind"] == "baseline"), None)
    if task is None:
        raise ValueError("review refers to an unknown baseline task")
    receipt = validate(profile, task)
    reports = [path_in_root(item["path"]) for item in receipt["artifacts"] if Path(item["path"]).name == "baseline.json"]
    if len(reports) != 1:
        raise ValueError("baseline receipt must identify exactly one successful attempt")
    report = reports[0]
    data = json.loads(report.read_text())
    screenshots = []
    for viewport in data["viewports"]:
        for key in ["screenshot", "primary_screenshot"]:
            image = path_in_root(str((report.parent / viewport[key]).relative_to(ROOT)))
            if not image.is_relative_to(report.parent):
                raise ValueError("baseline screenshot escaped its successful attempt")
            screenshots.append(str(image.relative_to(ROOT)))
    return report, screenshots


def workflow(profile: dict, task: dict, directory: Path, *, timeout_seconds: int | None = None) -> tuple[list[Path], list[dict]]:
    from urllib.parse import urlsplit

    # Admission's general assertion shape is broader than the real executor's
    # supported checkpoint roles. Refuse those known runtime-invalid inputs
    # before opening Chrome or allowing a genuine owner request.
    scenario_path = path_in_root("swissknife/test/e2e/functional-workflows/" + task["app_id"] + ".json")
    if scenario_path.is_file():
        from swissknife_visual_functional_llm import _read
        scenario = json.loads(_read(ROOT, str(scenario_path.relative_to(ROOT)), 1048576))
        phases = scenario.get("phases", {}) if type(scenario) is dict else {}
        checkpoints = []
        if type(phases) is dict:
            for phase, steps in phases.items():
                if type(steps) is not list:
                    continue  # The runner owns the remaining schema admission.
                for index, step in enumerate(steps):
                    if type(step) is not dict:
                        continue
                    if "retained_from" in step and step.get("checkpoint_id") != "error_image_retained":
                        raise ValueError("INVALID_SCENARIO: retained_from is only allowed on error_image_retained")
                    if "checkpoint_id" in step:
                        checkpoints.append((phase, index, step))
        errors = [row for row in checkpoints if row[2]["checkpoint_id"] == "error_observed"]
        retained = [row for row in checkpoints if row[2]["checkpoint_id"] == "error_image_retained"]
        if (any(phase != "failure_recovery" or step.get("op") != "assert"
                or step["checkpoint_id"] not in {"error_observed", "error_image_retained"}
                or "requirement_id" in step for phase, _, step in checkpoints)
                or len(errors) > 1 or len(retained) > 1 or retained and len(errors) != 1):
            raise ValueError("INVALID_SCENARIO: checkpoint_id is only error_observed once in failure_recovery; "
                             "one typed error_image_retained may follow it before recovery")
        if retained:
            _, index, step = retained[0]
            probe = step.get("probe", {})
            refs = step.get("retained_from")
            if (index <= errors[0][1] or type(probe) is not dict or probe.get("kind") != "image_state"
                    or "temporal_ms" in probe or type(refs) is not dict
                    or set(refs) != {"primary_result", "persist_reopen"}
                    or any(type(action) is not dict or action.get("op") not in {"assert", "capture", "wait_for", "wait_ms"}
                           or action.get("op") == "assert" and (action.get("requirement_id")
                               or type(action.get("probe", {})) is not dict
                               or action.get("probe", {}).get("kind") == "backend_result")
                           for action in phases["failure_recovery"][errors[0][1]+1:index])):
                raise ValueError("INVALID_SCENARIO: retained image must follow the error before recovery UI or owner action")
            for phase in ("primary_result", "persist_reopen"):
                source_index = refs[phase]
                source_steps = phases.get(phase)
                source = (source_steps[source_index] if type(source_steps) is list
                          and type(source_index) is int and 0 <= source_index < min(64, len(source_steps)) else None)
                if (type(source) is not dict or source.get("op") != "assert"
                        or type(source.get("probe")) is not dict
                        or source.get("probe", {}).get("kind") != "image_state"
                        or "temporal_ms" in source.get("probe", {})
                        or not (re.fullmatch(r"result_[1-9][0-9]*", str(source.get("requirement_id", "")))
                                if phase == "primary_result" else source.get("requirement_id") == phase)):
                    raise ValueError("INVALID_SCENARIO: retained_from must identify the declared original image assertions")
    backend_variables = {"ipfs_kit_py": "SWISSKNIFE_IPFS_KIT_MCP_URL",
                         "ipfs_datasets_py": "SWISSKNIFE_IPFS_DATASETS_MCP_URL",
                         "ipfs_accelerate_py": "SWISSKNIFE_IPFS_ACCELERATE_MCP_URL"}
    backend_endpoints = {}
    environment = {}
    fixtures = workflow_fixtures(profile)
    if fixtures is not None:
        environment["SWISSKNIFE_VDG_PAYLOAD_FIXTURES"] = str(fixtures[0])
    if profile.get("backends") is not None:
        backends = profile["backends"]
        if type(backends) is not dict or set(backends) != set(backend_variables):
            raise ValueError("workflow needs all three configured backend endpoints")
        for owner, name in backend_variables.items():
            raw = backends[owner]
            if type(raw) is not str or raw != raw.strip() or any(char.isspace() for char in raw):
                raise ValueError("workflow backend endpoint must be a loopback HTTP URL")
            parsed = urlsplit(raw)
            if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                    or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
                    or parsed.path.rstrip("/") not in {"", "/mcp", "/api/mcp/status"}
                    or parsed.port is not None and not 1 <= parsed.port <= 65535):
                raise ValueError("workflow backend endpoint must be a loopback HTTP MCP endpoint")
            # Vite expects the complete MCP endpoint, not only its base origin.
            endpoint = parsed._replace(path="/mcp").geturl()
            backend_endpoints[owner] = endpoint
            environment[name] = endpoint
    # This runner is an explicit implementation deliverable of SVF-030.
    runner = ROOT / "swissknife/scripts/run-visual-functional-workflow.mjs"
    if not runner.is_file():
        raise RuntimeError("SVF-030 workflow runner has not been implemented and validated")
    directory = path_in_root(str(directory))
    if not directory.is_relative_to(runtime_root(profile) / "tasks" / task["task_id"]):
        raise ValueError("workflow attempts must remain in their own task directory")
    assert_no_campaign_hold(profile)
    assert_storage_available(profile)
    directory.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="attempt-", dir=directory))
    try:
        checks = [run(["node", str(runner.relative_to(ROOT)), "--app", task["app_id"],
                       "--contracts", profile["appContractPath"], "--output-dir", str(attempt)]
                      + (["--independent-viewports"] if task.get("kind") in {"verify", "final-app-verify"} else []), timeout=min(1200, timeout_seconds) if timeout_seconds is not None else 1200,
                      **({"env": environment} if environment else {}))]
    except Exception as error:
        resource = storage_refusal(error)
        if resource is not None:
            raise resource from None
        # A failed producer cannot justify repair while its actual output
        # filesystems lack capacity, regardless of the driver error wording.
        assert_storage_available(profile)
        transient = False
        if isinstance(error, ValidationCommandError):
            for line in error.stderr.splitlines():
                try:
                    payload = json.loads(line)
                except ValueError:
                    continue
                if type(payload) is dict and payload.get("error") == "BROWSER_CONTENTION":
                    transient = True
        if transient:
            error = BrowserContention("another browser/evidence producer owns the shared browser lease; wait for its owner")
        remember_execution_failure(profile, task, error, stage="workflow", attempt=attempt)
        error.execution_failure_recorded = True
        if transient:
            raise error from None
        raise
    if backend_endpoints:
        checks[0]["configured_backend_endpoints"] = backend_endpoints
    report = attempt / "workflow.json"
    validate_workflow(profile, task, report)
    data = json.loads(report.read_text())
    if task.get("kind") in {"verify", "final-app-verify"} and data.get("schema") != "swissknife.visual-functional-workflow.v2":
        raise ValueError("fresh app verification requires independent desktop/mobile workflow V2")
    files = [report]
    for item in data["artifacts"]:
        files.append(path_in_root(item["path"]))
    return files, checks


def retained_workflow_report(profile: dict, task: dict, receipt: dict, directory: Path) -> Path:
    """Select one hashed report tied to its exact successful producer command.

    Never choose the newest directory or a mutable latest pointer. Historical
    fixed-path reports remain valid only with the same retained producer proof.
    All semantic/source/backend checks still run in validate_workflow().
    """
    if task.get("kind") == "final-app-verify":
        from swissknife_visual_functional_final_coverage import retained_final_report
        return retained_final_report(ROOT, profile, task, receipt, directory, validate_report=validate_workflow)
    directory = path_in_root(str(directory))
    owner = runtime_root(profile) / "tasks" / task["task_id"]
    if not directory.is_relative_to(owner) or directory == owner:
        raise ValueError("workflow report scope escaped its task")
    all_reports = [item for item in receipt.get("artifacts", [])
                   if type(item) is dict and Path(str(item.get("path", ""))).name == "workflow.json"]
    reports = [item for item in all_reports if path_in_root(item["path"]).is_relative_to(directory)]
    if task.get("kind") == "verify" and len(reports) != len(all_reports):
        raise ValueError("workflow report escaped the task verification scope")
    if task.get("kind") == "verify":
        for record in reports:
            candidate = path_in_root(record["path"])
            if candidate.parent.parent == directory:
                check_artifacts([record], allowed_prefix=directory)
                if json.loads(candidate.read_text()).get("schema") == "swissknife.visual-functional-workflow.v2":
                    from swissknife_visual_functional_final_coverage import retained_final_report
                    return retained_final_report(ROOT, profile, task, receipt, directory, validate_report=validate_workflow)
    if len(reports) != 1:
        raise ValueError("task receipt must retain exactly one successful workflow report per app")
    record = reports[0]
    report = path_in_root(record["path"])
    legacy = report == directory / "workflow.json"
    if not legacy and (report.parent.parent != directory
                       or re.fullmatch(r"attempt-[A-Za-z0-9_-]{6,80}", report.parent.name) is None):
        raise ValueError("workflow report is not an owned immutable attempt or proven legacy path")
    check_artifacts([record], allowed_prefix=directory)
    expected = ["node", "swissknife/scripts/run-visual-functional-workflow.mjs", "--app", task["app_id"],
                "--contracts", profile["appContractPath"], "--output-dir"]
    producers = []
    for check in receipt.get("checks", []):
        argv = check.get("argv") if type(check) is dict else None
        if (type(argv) is list and len(argv) == len(expected) + 1 and argv[:len(expected)] == expected
                and type(check.get("exit_code")) is int and check["exit_code"] == 0
                and path_in_root(argv[-1]) == report.parent):
            producers.append(check)
    if len(producers) != 1:
        raise ValueError("workflow report lacks its exact successful producer invocation")
    validate_workflow(profile, task, report)
    return report


def regression_workflow_reports(profile: dict, task: dict) -> dict[str, Path]:
    """An aggregate consumes the regression's validated receipt, not filenames."""
    spec = json.loads(path_in_root(profile["taskSpecPath"]).read_text())
    owner_task = next((item for item in spec["tasks"] if item["task_id"] == task.get("regression_task")), None)
    if owner_task is None or owner_task.get("kind") != "regression":
        raise ValueError("aggregate regression owner is missing or has the wrong kind")
    if task.get("task_id") == "SVF-990" or "final_app_tasks" in task:
        from swissknife_visual_functional_final_coverage import final_task_map, validate_coverage
        final_task_map(ROOT, profile, task, spec)
        if task["final_app_tasks"] != owner_task.get("final_app_tasks"):
            raise ValueError("aggregate and regression final app task maps differ")
        receipt = validate(profile, owner_task)
        coverage = validate_coverage(ROOT, profile, owner_task, receipt, validate_task=validate,
            retained_report=retained_workflow_report, validate_report=validate_workflow)
        return {group["app_id"]: path_in_root(group["review_join"]["workflow"]["path"]) for group in coverage["groups"]}
    receipt = validate(profile, owner_task)
    directory = runtime_root(profile) / "tasks" / owner_task["task_id"]
    apps = json.loads(path_in_root(profile["appContractPath"]).read_text())["apps"]
    return {app["app_id"]: retained_workflow_report(profile, dict(owner_task, app_id=app["app_id"]), receipt,
                                                    directory / app["app_id"]) for app in apps}


def _typed_equal(actual: Any, expected: Any) -> bool:
    # JSON encodings distinguish booleans, numbers and strings, including in
    # nested values. Non-finite numbers are never valid observed evidence.
    return json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)


def validate_observed(value: Any) -> None:
    if type(value) is not dict or set(value) != {"operator", "actual", "expected"}:
        raise ValueError("observed evidence must contain operator, actual and expected")
    operator, actual, expected = value["operator"], value["actual"], value["expected"]
    if operator == "equals":
        passed = _typed_equal(actual, expected)
    elif operator == "not_equals":
        passed = not _typed_equal(actual, expected)
    elif operator == "contains":
        if type(actual) is str and type(expected) is str and expected:
            passed = expected in actual
        elif type(actual) is list and expected is not None:
            passed = any(_typed_equal(item, expected) for item in actual)
        else:
            passed = False
    elif operator == "at_least":
        passed = (type(actual) in {int, float} and type(expected) in {int, float}
                  and expected > 0 and actual >= expected)
        _typed_equal(actual, expected)  # Reject non-finite values even here.
    else:
        raise ValueError("unsupported observed-evidence operator")
    if not passed:
        raise ValueError("observed values contradict a passed assertion")


def _json_pointer(value: Any, pointer: str) -> Any:
    if type(pointer) is not str or not pointer.startswith("/") or len(pointer) > 2048:
        raise ValueError("backend result assertion requires a bounded JSON pointer")
    for raw in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw):
            raise ValueError("invalid JSON pointer escape")
        part = raw.replace("~1", "/").replace("~0", "~")
        if type(value) is list:
            if re.fullmatch(r"0|[1-9][0-9]*", part) is None:
                raise ValueError("invalid JSON pointer index")
            value = value[int(part)]
        elif type(value) is dict:
            value = value[part]
        else:
            raise ValueError("backend result pointer traverses a scalar")
    return value


def _raw_cid(data: bytes) -> str:
    multihash = bytes([1, 0x55, 0x12, 0x20]) + hashlib.sha256(data).digest()
    return "b" + base64.b32encode(multihash).decode("ascii").lower().rstrip("=")


def _native_succeeded(value: Any) -> None:
    if type(value) is not dict:
        raise ValueError("raw owner result must be an object")
    if (value.get("isError") is True or value.get("success") is False or value.get("ok") is False
            or value.get("error") or value.get("status") in {"error", "failed", "backend_error", "unavailable"}
            or value.get("outcome") in {"failed", "denied", "unsupported", "unreachable"}):
        raise ValueError("retained native owner result reports failure")
    if type(value.get("result")) is dict:
        _native_succeeded(value["result"])
    for item in value.get("content", []):
        if type(item) is dict and type(item.get("json")) is dict:
            _native_succeeded(item["json"])
        elif type(item) is dict and item.get("type") == "text":
            try:
                decoded = json.loads(item["text"])
            except (ValueError, TypeError):
                continue
            if type(decoded) is dict:
                _native_succeeded(decoded)


def validate_backend_observation(observation: dict, *, app_id: str, artifact_paths: set[Path]) -> None:
    if type(observation) is not dict or observation.get("route") != "/mcp/tools/call" or observation.get("outcome") != "executed":
        raise ValueError("owner did not execute through MCP++")
    required = ["owner", "tool_id", "transport", "correlation_id", "receipt_id", "event_dag_cid"]
    if not all(type(observation.get(key)) is str and observation[key] for key in required):
        raise ValueError("incomplete backend observation")
    if observation["transport"] not in {"http", "libp2p"}:
        raise ValueError("unsupported observed owner transport")
    if observation.get("receipt_verified") is not True or observation.get("semantic_result_verified") is not True:
        raise ValueError("receipt/result verification was not performed")
    raw_records = {}
    for kind, cid_field, path_field in (("receipt", "receipt_id", "receipt_artifact"), ("event", "event_dag_cid", "event_artifact")):
        path = path_in_root(observation[path_field])
        if path not in artifact_paths:
            raise ValueError("raw backend receipt/event is not in the hashed workflow artifacts")
        raw = path.read_bytes()
        if _raw_cid(raw) != observation[cid_field]:
            raise ValueError("raw backend artifact CID does not match its retained bytes")
        payload = json.loads(raw)
        if type(payload) is not dict or payload.get("kind") != kind:
            raise ValueError("retained backend artifact kind is invalid")
        call = payload.get("call", {})
        for key in ["owner", "tool_id", "correlation_id", "route", "transport"]:
            if call.get(key) != observation[key]:
                raise ValueError("retained backend call does not match its observation")
        if call.get("app_id") != app_id or call.get("input", {}).get("correlation_id") != observation["correlation_id"]:
            raise ValueError("backend receipt does not belong to this app/correlation")
        _native_succeeded(payload.get("result"))
        raw_records[kind] = payload
    if raw_records["event"]["call"] != raw_records["receipt"]["call"] or not _typed_equal(raw_records["event"]["result"], raw_records["receipt"]["result"]):
        raise ValueError("receipt and event disagree about native execution")
    owner_receipt = raw_records["receipt"].get("result", {}).get("result", {}).get("receipt", {})
    if owner_receipt.get("tool") != observation["tool_id"]:
        raise ValueError("native owner receipt does not name the executed tool")
    assertion = observation.get("result_assertion")
    if type(assertion) is not dict or set(assertion) != {"pointer", "operator", "actual", "expected"}:
        raise ValueError("backend result requires an assertion bound to retained receipt content")
    actual = _json_pointer(raw_records["receipt"], assertion["pointer"])
    if not _typed_equal(actual, assertion["actual"]):
        raise ValueError("backend semantic assertion is detached from actual owner result")
    validate_observed({key: assertion[key] for key in ["operator", "actual", "expected"]})


def validate_workflow(profile: dict, task: dict, report: Path) -> dict | None:
    data = json.loads(report.read_text())
    if task.get("kind") == "final-app-verify" or data.get("schema") == "swissknife.visual-functional-workflow.v2":
        from swissknife_visual_functional_final_coverage import validate_dual_workflow
        return validate_dual_workflow(ROOT, profile, task, report,
            observation_validator=validate_observed, backend_validator=validate_backend_observation)
    contracts = json.loads(path_in_root(profile["appContractPath"]).read_text())
    app = next(a for a in contracts["apps"] if a["app_id"] == task["app_id"])
    if data.get("schema") != "swissknife.visual-functional-workflow.v1" or data.get("app_id") != app["app_id"]:
        raise ValueError("workflow identity/schema mismatch")
    if data.get("passed") is not True or data.get("source_template") is not False or data.get("actual_desktop") is not True:
        raise ValueError("workflow did not pass on the actual desktop")
    if data.get("contract_sha256") != sha(path_in_root(profile["appContractPath"])):
        raise ValueError("workflow contract is stale")
    if not report.is_relative_to(runtime_root(profile)):
        raise ValueError("workflow report escaped this campaign runtime")
    check_artifacts(data.get("artifacts", []), allowed_prefix=report.parent)
    for raw in app["source_paths"]:
        name = raw if raw.startswith("swissknife/") else "swissknife/" + raw
        if data.get("source_sha256", {}).get(name) != sha(path_in_root(name)):
            raise ValueError(f"workflow source is stale: {name}")
    required = {"primary_result", "keyboard", "desktop_layout", "mobile_layout", "error_recovery"}
    checks = data.get("checks", [])
    if type(checks) is not list or any(type(item) is not dict or item.get("passed") is not True for item in checks):
        raise ValueError("workflow checks contain a missing or failed observation")
    observed = {item.get("kind") for item in checks}
    if len(observed) != len(checks):
        raise ValueError("workflow check kinds must be unique")
    for item in checks:
        validate_observed(item.get("observation"))
    if not required <= observed:
        raise ValueError(f"missing real workflow postconditions: {sorted(required - observed)}")
    assertions = data.get("semantic_assertions", [])
    primary = app["primary_workflow"]
    expected_texts = {f"result_{i + 1}": text for i, text in enumerate(primary["expected_results"])}
    expected_texts.update(persist_reopen=primary["persist_reopen"], failure_recovery=primary["error"] + " Recovery: " + primary["recovery"])
    required_semantics = set(expected_texts)
    if type(assertions) is not list or not assertions or any(type(a) is not dict or a.get("passed") is not True for a in assertions):
        raise ValueError("missing app-specific semantic assertions")
    observed_ids = [a.get("requirement_id") for a in assertions]
    if len(set(observed_ids)) != len(observed_ids) or set(observed_ids) != required_semantics:
        raise ValueError("workflow omitted intended results, persistence, or recovery requirements")
    for assertion in assertions:
        if assertion.get("requirement_text") != expected_texts[assertion["requirement_id"]]:
            raise ValueError("semantic assertion is not bound to its app requirement")
        validate_observed(assertion.get("observed"))
    if app["disposition"] == "tool_backed":
        if not data.get("backend_observations"):
            raise ValueError("tool-backed workflow lacks real owner execution evidence")
        paths = {path_in_root(item["path"]) for item in data["artifacts"]}
        for observation in data["backend_observations"]:
            validate_backend_observation(observation, app_id=app["app_id"], artifact_paths=paths)
    elif type(data.get("unexpected_backend_calls")) is not int or data["unexpected_backend_calls"] != 0 or data.get("backend_observations") != []:
        raise ValueError("local/external/policy boundary violated")


def validate_cross_workflow(profile: dict, task: dict) -> None:
    """Cross-app scripts must retain current semantic evidence, not just exit 0."""
    directory = runtime_root(profile) / "tasks" / task["task_id"] / "cross-workflow"
    report = directory / "workflow.json"
    data = json.loads(report.read_text())
    if (data.get("schema") != "swissknife.visual-functional-cross-workflow.v1"
            or data.get("task_id") != task["task_id"] or data.get("task_spec_sha256") != stable(task)
            or data.get("passed") is not True or data.get("actual_desktop") is not True
            or data.get("source_template") is not False):
        raise ValueError("cross-app workflow identity/current execution is invalid")
    contracts = path_in_root(profile["appContractPath"])
    if data.get("contract_sha256") != sha(contracts):
        raise ValueError("cross-app workflow contract is stale")
    indexed = {app["app_id"]: app for app in json.loads(contracts.read_text())["apps"]}
    apps = data.get("apps")
    if type(apps) is not list or len(apps) < 2 or len(set(apps)) != len(apps) or any(app not in indexed for app in apps):
        raise ValueError("cross-app workflow must identify distinct canonical apps")
    check_artifacts(data.get("artifacts", []), allowed_prefix=directory)
    artifact_paths = {path_in_root(item["path"]) for item in data["artifacts"]}
    sources = set(task.get("edit_paths", []))
    for app_id in apps:
        sources.update(raw if raw.startswith("swissknife/") else "swissknife/" + raw for raw in indexed[app_id]["source_paths"])
    if not sources or any(data.get("source_sha256", {}).get(path) != sha(path_in_root(path)) for path in sources):
        raise ValueError("cross-app workflow source is stale or incomplete")
    assertions = data.get("semantic_assertions")
    required = {"primary_result", "persist_reopen", "failure_recovery"}
    if (type(assertions) is not list or len(assertions) != len(required)
            or {a.get("requirement_id") for a in assertions} != required):
        raise ValueError("cross-app workflow omitted semantic requirements")
    for assertion in assertions:
        if assertion.get("passed") is not True or assertion.get("requirement_text") != task["acceptance"]:
            raise ValueError("cross-app assertion is detached from the task contract")
        validate_observed(assertion.get("observed"))
    screenshots = data.get("screenshots", {})
    if type(screenshots) is not dict or set(screenshots) != {"desktop", "mobile"}:
        raise ValueError("cross-app workflow lacks desktop/mobile screenshots")
    for path in screenshots.values():
        image = path_in_root(path)
        if image not in artifact_paths or image.stat().st_size < 128 or image.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("cross-app screenshot is missing or outside retained artifacts")
    observations = data.get("backend_observations")
    if type(observations) is not list or not observations:
        raise ValueError("cross-app workflow lacks owner execution evidence")
    for observation in observations:
        if observation.get("app_id") not in apps:
            raise ValueError("cross-app owner observation belongs to another app")
        validate_backend_observation(observation, app_id=observation["app_id"], artifact_paths=artifact_paths)
    required_owners = {"SVF-910": {"ipfs_kit_py", "ipfs_datasets_py", "ipfs_accelerate_py"},
                       "SVF-920": {"ipfs_kit_py"}, "SVF-930": {"ipfs_accelerate_py"}}
    if not required_owners.get(task["task_id"], set()) <= {o["owner"] for o in observations}:
        raise ValueError("cross-app workflow omitted a required backend owner")


def validate_aggregate_dependencies(profile: dict, task: dict) -> list[str]:
    spec = json.loads(path_in_root(profile["taskSpecPath"]).read_text())
    validate_dag(spec["tasks"])
    indexed = {item["task_id"]: item for item in spec["tasks"]}
    cross_tasks = [dependency for dependency in task.get("dependencies", []) if dependency != task["regression_task"]]
    if (task.get("task_id") == "SVF-990" or "final_app_tasks" in task) and set(cross_tasks) != {"SVF-910", "SVF-920", "SVF-930"}:
        raise ValueError("final aggregate requires its three original cross-app receipts")
    if not cross_tasks:
        raise ValueError("aggregate omitted cross-app dependencies")
    for task_id in cross_tasks:
        dependency = indexed[task_id]
        if dependency.get("kind") != "implementation":
            raise ValueError("aggregate cross-app dependency has the wrong kind")
        validate(profile, dependency)
        validate_cross_workflow(profile, dependency)
    return cross_tasks


def validate_foundation_pilot(profile: dict, task: dict) -> list[Path]:
    """A small real-desktop integration witness, never full app acceptance."""
    directory = runtime_root(profile) / "tasks" / task["task_id"] / "pilot"
    report = directory / "pilot.json"
    data = json.loads(report.read_text())
    if (data.get("schema") != "swissknife.visual-functional-driver-pilot.v1"
            or data.get("app_id") != "calculator" or data.get("actual_desktop") is not True
            or data.get("foundation_integration_only") is not True
            or data.get("functional_acceptance") is not False):
        raise ValueError("foundation pilot is not an actual, scoped desktop integration")
    check_artifacts(data.get("artifacts", []), allowed_prefix=directory)
    assertions = data.get("observations")
    expected = {"arithmetic_result", "keyboard_result", "clear_recovery"}
    if type(assertions) is not list or {a.get("kind") for a in assertions} != expected or len(assertions) != len(expected):
        raise ValueError("pilot omitted actual arithmetic/keyboard/recovery observations")
    for item in assertions:
        validate_observed(item.get("observation"))
    views = data.get("viewports")
    expected_views = [("desktop", 1440, 900), ("mobile", 390, 844)]
    if (type(views) is not list or len(views) != 2 or any(type(v) is not dict for v in views)
            or [(v.get("viewport", {}).get("name"), v.get("viewport", {}).get("width"), v.get("viewport", {}).get("height")) for v in views] != expected_views):
        raise ValueError("pilot must retain both canonical viewport observations")
    for view in views:
        if (view.get("actual_desktop") is not True or view.get("division_error_observed") is not True
                or type(view.get("error_text")) is not str or "zero" not in view["error_text"].lower()):
            raise ValueError("pilot did not actually observe division by zero in both viewports")
    for item in assertions:
        field, result = {"arithmetic_result": ("arithmetic", "50"), "keyboard_result": ("keyboard", "42"),
                         "clear_recovery": ("recovered", "50")}[item["kind"]]
        observed = item["observation"]
        if (observed["operator"] != "equals" or observed["expected"] != [result, result]
                or observed["actual"] != [view.get(field) for view in views]):
            raise ValueError("pilot assertions are not bound to independently specified arithmetic and actual viewports")
    sources = task.get("pilot_sources")
    if (not isinstance(sources, list) or not sources
            or any(data.get("source_sha256", {}).get(path) != sha(path_in_root(path)) for path in sources)):
        raise ValueError("pilot is not bound to current driver/application source")
    images = {Path(a["path"]).name for a in data["artifacts"] if Path(a["path"]).suffix == ".png"}
    if not {"desktop.png", "mobile.png"} <= images:
        raise ValueError("pilot omitted actual desktop/mobile screenshots")
    for item in data["artifacts"]:
        if Path(item["path"]).suffix == ".png":
            p = path_in_root(item["path"])
            if p.stat().st_size < 128 or p.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("pilot screenshot is not a PNG")
    return [report, *[path_in_root(a["path"]) for a in data["artifacts"]]]


def snapshot_foundation_sources(task: dict, directory: Path, files: list[Path]) -> tuple[list[Path], list[dict]]:
    """Retain stage bytes while the next stage extends the same source files.

    Final gate checks rerun against current source. Historical stage receipts
    bind to their immutable snapshots rather than pretending source never moved.
    """
    if not task.get("foundation_stage"):
        return files, []
    originals = {path_in_root(p): p for p in task["edit_paths"]}
    retained, snapshots = [], []
    for file in files:
        if file not in originals:
            retained.append(file)
            continue
        target = directory / "source-snapshots" / originals[file]
        target.parent.mkdir(parents=True, exist_ok=True)
        # Content addressing preserves previous retries too.
        target = target.with_name(target.name + "." + sha(file))
        if target.exists() and target.read_bytes() != file.read_bytes():
            raise ValueError("foundation source snapshot collision")
        if not target.exists():
            target.write_bytes(file.read_bytes())
        retained.append(target)
        snapshots.append({"source_path": originals[file], "snapshot": artifact(target)})
    if {s["source_path"] for s in snapshots} != set(task["edit_paths"]):
        raise ValueError("foundation stage omitted a declared source snapshot")
    return retained, snapshots


def validate_foundation_dependencies(profile: dict, spec: dict, task: dict) -> list[Path]:
    indexed = {t["task_id"]: t for t in spec["tasks"]}
    stages = task.get("foundation_stages", [])
    if stages != ["SVF-031", "SVF-032", "SVF-033", "SVF-034"]:
        raise ValueError("foundation gate lost its required stages")
    for identity in stages:
        validate(profile, indexed[identity])
    return validate_foundation_pilot(profile, indexed["SVF-034"])


def qualified_recovery(profile: dict, task: dict) -> dict | None:
    from swissknife_visual_functional_recovery import qualified_recovery as qualify
    return qualify(ROOT, profile, task)


def recover(profile_path: str, profile: dict, task: dict) -> dict:
    """Apply one admitted model proposal; the original validator owns completion."""
    if task.get("kind") == "scoped-remediation":
        raise ValueError("scoped remediation has no recovery authority")
    assert_no_campaign_hold(profile)
    assert_storage_available(profile)
    from swissknife_visual_functional_recovery import run_recovery
    return run_recovery(ROOT, profile, task,
        ensure_lease=lambda: ensure_lease(profile),
        check_owned=lambda paths: check_owned_sources(profile, paths),
        invoke_model=lambda inputs, output, context: model(profile_path, task, "repair", inputs, [], output,
            recovery_context=context, preserve_feedback=True, edit_paths_override=context.get("edit_paths"),
            backend_producer=_backend_original_checks(profile, task) if task.get("kind") == "backend-repair" else None),
        remember_owned=lambda paths: remember_owned_sources(profile, paths))


def execute(profile_path: str, profile: dict, spec: dict, task: dict) -> dict:
    ensure_lease(profile)
    if task.get("kind") != "scoped-remediation":
        check_owned_sources(profile, task.get("edit_paths", []))
    assert_storage_available(profile)
    if task.get("kind") == "verify":
        from swissknife_visual_functional_review_recheck import assert_recheck_allowed
        assert_recheck_allowed(ROOT, profile, task)
    if task.get("kind") == "final-app-verify":
        from swissknife_visual_functional_final_coverage import validate_final_task_contract, assert_final_review_allowed
        validate_final_task_contract(ROOT, profile, task, spec)
        assert_final_review_allowed(ROOT, profile, task)
    directory = path_in_root(profile["runtimeRoot"]) / "tasks" / task["task_id"]
    directory.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    checks: list[dict] = []
    detail: dict[str, Any] = {}
    kind = task["kind"]
    if kind == "seal":
        from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate
        bootstrap_ipfs_accelerate(__file__, include_script_dir=True)
        from ipfs_accelerate_py.agent_supervisor.task_sources.taskboard_ingest import load_taskboard, ingest_taskboard
        from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import parse_goal_heap
        parsed = load_taskboard(path_in_root(profile["taskSpecPath"]), repair=False)
        validate_dag(spec["tasks"])
        goals = parse_goal_heap(path_in_root(profile["objectivePath"]).read_text())
        if not goals or len(goals) != len(spec["goals"]):
            raise ValueError("objective heap did not ingest completely")
        if any(not t.get("execution_validation") for t in parsed["tasks"]):
            raise ValueError("canonical task source lost execution validators")
        detail = ingest_taskboard(board_path=path_in_root(profile["taskSpecPath"]),
                                 store_path=directory / "plan.duckdb", require_quack=False)
        if detail["task_count"] != len(spec["tasks"]):
            raise ValueError("canonical database task count mismatch")
        detail.update(goal_count=len(goals), dependency_dag_valid=True, authority="initial_plan_snapshot")
        report = directory / "ingestion.json"; atomic_json(report, detail); files = [report]
    elif kind == "model-probe":
        output = directory / "model.json"
        detail = model(profile_path, task, "probe", [profile["humanPlanPath"]], [], output)
        files = [output]
    elif kind == "backend-audit":
        observations = []
        for service, base in profile["backends"].items():
            try:
                with urllib.request.urlopen(base.rstrip("/") + "/mcp/health", timeout=15) as response:
                    payload = json.load(response)
                    observations.append({"owner": service, "url": base, "http_status": response.status,
                                         "adapter_health": payload, "upstream_ready": payload.get("upstream_available") is True,
                                         "upstream_status": "unverified" if "upstream_available" not in payload else
                                             "ready" if payload["upstream_available"] is True else "degraded"})
            except Exception as error:
                observations.append({"owner": service, "url": base, "error": type(error).__name__ + ": " + str(error), "upstream_ready": False})
        detail = {"observations": observations, "audit_complete": True, "backend_acceptance": False,
                  "degraded_owners": [o["owner"] for o in observations if not o["upstream_ready"]]}
        report = directory / "backend-audit.json"; atomic_json(report, detail); files = [report]
    elif kind in {"command", "foundation-gate"}:
        recovered = qualified_recovery(profile, task)
        if task.get("recovery_canary") and recovered is None:
            raise ValueError("recovery canary requires a genuine admitted repair before its original checks can pass")
        if kind == "foundation-gate":
            validate_foundation_dependencies(profile, spec, task)
        if not task.get("checks"):
            raise ValueError("deterministic stage has no executable semantic checks")
        checks = [run(command, timeout=task.get("timeout_seconds", 1200)) for command in task["checks"]]
        files = [path_in_root(p) for p in task.get("edit_paths", []) if path_in_root(p).is_file()]
        evidence = directory / "execution.json"
        detail = {"kind": kind, "checked_commands": len(checks), "scope": "foundation_stage_only"}
        if recovered is not None:
            files.append(path_in_root(recovered["model_path"]))
            detail["qualified_recovery_consumed"] = True
        atomic_json(evidence, detail); files.append(evidence)
        if task.get("foundation_pilot"):
            files += validate_foundation_pilot(profile, task)
    elif kind == "baseline":
        files = baseline(profile, task, directory / "baseline")
    elif kind == "review":
        screenshots: list[str] = []
        inputs = [profile["humanPlanPath"], profile["appContractPath"]]
        if task.get("app_id"):
            baseline_task = task["baseline_task"]
            report, screenshots = resolve_baseline(profile, baseline_task)
            inputs += [str(report.relative_to(ROOT))]
        output = directory / "review.json"
        detail = model(profile_path, task, "review", inputs, screenshots, output)
        files = [output]
    elif kind in {"implementation", "repair", "backend-repair"} and (recovered := qualified_recovery(profile, task)) is not None:
        ensure_lease(profile)
        checks = [run(command, timeout=task.get("timeout_seconds", 1200)) for command in task.get("checks", [])]
        if not checks:
            raise ValueError("recovered implementation has no original executable checks")
        files = [path_in_root(recovered["model_path"]), *[path_in_root(p) for p in task.get("edit_paths", []) if path_in_root(p).is_file()]]
        detail = {"qualified_recovery_consumed": True, "source_application_only": True, "completion_authority": False}
        if task.get("foundation_pilot"):
            files += validate_foundation_pilot(profile, task)
    elif kind in {"implementation", "repair", "backend-repair"}:
        from swissknife_visual_functional_llm import apply_validated_edits
        inputs = list(dict.fromkeys([profile["humanPlanPath"], profile["appContractPath"], profile["taskSpecPath"], *task.get("context_paths", []),
                                    *[p for p in task.get("edit_paths", []) if path_in_root(p).is_file()]]))
        failures = []
        for attempt in range(1, 4):
            output = directory / f"proposal-{attempt}.json"
            producer = _backend_original_checks(profile, task) if kind == "backend-repair" else None
            proposal = model(profile_path, task, "repair", inputs + ([] if producer is not None else failures[-1:]), [], output,
                             backend_producer=producer)
            ensure_lease(profile)
            check_owned_sources(profile, task.get("edit_paths", []))
            source_hashes = repair_target_hashes(task)
            try:
                applied = apply_validated_edits(ROOT, proposal["response"]["edits"], task.get("edit_paths", []), lease_check=lambda: ensure_lease(profile))
            except Exception:
                remember_repair_failure(profile, task, source_hashes=source_hashes, apply_failed=True)
                raise
            remember_owned_sources(profile, [item["path"] for item in applied["applied"]])
            try:
                checks = [run(command, timeout=task.get("timeout_seconds", 1200)) for command in task.get("checks", [])]
                if not checks:
                    raise ValueError("implementation task has no executable validation")
                files = [output, *[path_in_root(p) for p in task["edit_paths"] if path_in_root(p).is_file()]]
                if task.get("foundation_pilot"):
                    files += validate_foundation_pilot(profile, task)
                break
            except Exception as error:
                remember_repair_failure(profile, task, source_hashes=repair_target_hashes(task), validation_failed=True)
                failure = directory / f"failure-{attempt}.txt"
                failure.write_text(str(error)[-24000:])
                failures.append(str(failure.relative_to(ROOT)))
                print(f"SVF {task['task_id']} repair attempt {attempt}: {error}", flush=True)
                if attempt == 3:
                    raise
    elif kind == "final-app-verify":
        from swissknife_visual_functional_final_coverage import binding, review_join, remember_failed_review
        review_output = None
        try:
            files, checks = workflow(profile, task, directory / "verification")
            validated = validate_workflow(profile, task, files[0])
            review_output = files[0].parent / "visual-review.json"
            images = [item["path"] for item in validated["images"]]
            reviewed = model(profile_path, task, "review",
                [profile["appContractPath"], str(files[0].relative_to(ROOT))], images, review_output)
            if reviewed["response"]["decision"] != "pass":
                remember_failed_review(ROOT, profile, task, validated, review_output)
                raise ValueError("final independent desktop/mobile visual review requires scoped remediation; no new repair admission")
            ensure_lease(profile)
            validated = validate_workflow(profile, task, files[0])
            detail = {"final_viewport_review_join": review_join(ROOT, profile, task, binding(task, validated), review_output),
                      "readonly_verification": True, "repair_admissions": 0}
            files.append(review_output)
        except Exception as error:
            if isinstance(error, (BrowserContention, StoragePressure)) or storage_refusal(error) is not None:
                raise
            if not getattr(error, "execution_failure_recorded", False):
                remember_execution_failure(profile, task, error, stage="verification", review_output=review_output)
            raise
    elif kind == "scoped-remediation":
        from swissknife_visual_functional_phase_remediation import execute_child
        from swissknife_visual_functional_llm import apply_validated_edits
        files, checks, detail = execute_child(ROOT, profile_path, profile, spec, task,
            model=model, workflow=workflow, validate_workflow=validate_workflow,
            apply_edits=apply_validated_edits, ensure_lease=ensure_lease,
            check_owned=check_owned_sources, remember_owned=remember_owned_sources)
    elif kind == "verify":
        from swissknife_visual_functional_llm import apply_validated_edits
        for attempt in range(1, 4):
            review_output = None
            try:
                files, checks = workflow(profile, task, directory / "verification")
                review_output = files[0].parent / "visual-review.json"
                validated = validate_workflow(profile, task, files[0])
                if validated is None:
                    raise ValueError("fresh app verification requires independent desktop/mobile workflow V2")
                screenshots = [item["path"] for item in validated["images"]]
                detail = model(profile_path, task, "review", [profile["appContractPath"], str(files[0].relative_to(ROOT))], screenshots, review_output)
                if detail["response"]["decision"] != "pass":
                    raise ValueError("final visual review still requires changes")
                from swissknife_visual_functional_phase_budget import close_after_pass
                close_after_pass(ROOT, task, review_output, files[0], profile=profile)
                files.append(review_output)
                break
            except Exception as error:
                if isinstance(error, (BrowserContention, StoragePressure)) or storage_refusal(error) is not None:
                    raise  # Waiting for a foreign resource cannot justify an app edit.
                if not getattr(error, "execution_failure_recorded", False):
                    remember_execution_failure(profile, task, error, stage="verification", review_output=review_output)
                if attempt == 3:
                    raise
                failure = directory / f"verification-failure-{attempt}.txt"
                failure.write_text(str(error)[-24000:])
                inputs = [profile["humanPlanPath"], str(failure.relative_to(ROOT)),
                          *[p for p in task["edit_paths"] if path_in_root(p).is_file()]]
                if review_output is not None and review_output.is_file():
                    inputs.append(str(review_output.relative_to(ROOT)))
                proposal = model(profile_path, task, "repair", inputs, [], directory / f"verification-repair-{attempt}.json")
                ensure_lease(profile)
                check_owned_sources(profile, task["edit_paths"])
                applied = apply_validated_edits(ROOT, proposal["response"]["edits"], task["edit_paths"], lease_check=lambda: ensure_lease(profile))
                remember_owned_sources(profile, [item["path"] for item in applied["applied"]])
    elif kind == "regression":
        if task["task_id"] == "SVF-900" or "final_app_tasks" in task:
            from swissknife_visual_functional_final_coverage import coverage
            detail = coverage(ROOT, profile, task, validate_task=validate, retained_report=retained_workflow_report,
                              validate_report=validate_workflow, spec=spec)
            report = directory / "final-app-coverage.json"; atomic_json(report, detail); files = [report]
        else:
            for app in json.loads(path_in_root(profile["appContractPath"]).read_text())["apps"]:
                app_task = dict(task, app_id=app["app_id"])
                observed, executed = workflow(profile, app_task, directory / app["app_id"])
                files += observed; checks += executed
    elif kind == "aggregate":
        apps = json.loads(path_in_root(profile["appContractPath"]).read_text())["apps"]
        regression_workflow_reports(profile, task)
        cross_tasks = validate_aggregate_dependencies(profile, task)
        detail = {"decision": "GO", "validated_apps": len(apps), "validated_cross_tasks": cross_tasks,
                  "work_complete": False, "completion_authority": False}
        if task["task_id"] == "SVF-990" or "final_app_tasks" in task:
            owner = runtime_root(profile) / "tasks" / task["regression_task"] / "final-app-coverage.json"
            detail.update(final_app_tasks=task["final_app_tasks"], validated_final_app_reviews=45,
                          regression_coverage=artifact(owner))
        report = directory / "acceptance.json"; atomic_json(report, detail); files = [report]
    else:
        raise ValueError(f"unimplemented task kind {kind}")
    files, source_snapshots = snapshot_foundation_sources(task, directory, files)
    if source_snapshots:
        detail["source_snapshots"] = source_snapshots
        detail["scope"] = "foundation_stage_only"
    result = {"schema": "swissknife.visual-functional-task.v1", "task_id": task["task_id"],
              "kind": kind, "task_spec_sha256": stable(task), "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "artifacts": [artifact(p) for p in files], "checks": checks, "detail": detail,
              "work_complete": False, "completion_authority": False}
    atomic_json(directory / "receipt.json", result)
    validate(profile, task)
    return result


def validate(profile: dict, task: dict) -> dict:
    directory = runtime_root(profile) / "tasks" / task["task_id"]
    receipt = json.loads((directory / "receipt.json").read_text())
    if (receipt.get("schema") != "swissknife.visual-functional-task.v1" or receipt.get("kind") != task["kind"]
            or receipt.get("task_id") != task["task_id"] or receipt.get("task_spec_sha256") != stable(task)):
        raise ValueError("task evidence belongs to a different contract")
    if receipt.get("work_complete") is not False or receipt.get("completion_authority") is not False:
        raise ValueError("task worker cannot grant objective completion")
    check_artifacts(receipt.get("artifacts", []), allowed_prefix=directory, allowed_sources=task.get("edit_paths", []))
    if task.get("recovery_canary"):
        from swissknife_visual_functional_recovery import historical_recovery_evidence
        if historical_recovery_evidence(ROOT, profile, task) is None:
            raise ValueError("recovery canary lacks its independently qualified native model repair")
    if task.get("foundation_stage"):
        snapshots = receipt.get("detail", {}).get("source_snapshots", [])
        if (not isinstance(snapshots, list) or len(snapshots) != len(task["edit_paths"])
                or {s.get("source_path") for s in snapshots} != set(task["edit_paths"])):
            raise ValueError("foundation stage lacks immutable declared source snapshots")
        retained = {p["path"] for p in receipt["artifacts"]}
        for snapshot in snapshots:
            item = snapshot["snapshot"]
            check_artifacts([item], allowed_prefix=directory / "source-snapshots")
            if item["path"] not in retained:
                raise ValueError("foundation source snapshot omitted from receipt artifacts")
    if task["kind"] == "scoped-remediation":
        from swissknife_visual_functional_phase_remediation import validate_child_result
        spec = json.loads(path_in_root(profile["taskSpecPath"]).read_text())
        validate_child_result(ROOT, profile, spec, task, receipt, validate_workflow=validate_workflow)
    if task["kind"] == "baseline":
        reports = [path_in_root(item["path"]) for item in receipt["artifacts"] if Path(item["path"]).name == "baseline.json"]
        if len(reports) != 1:
            raise ValueError("baseline task must retain one successful capture attempt")
        expected = set(baseline_files(profile, task, reports[0]))
        retained = {path_in_root(item["path"]) for item in receipt["artifacts"]}
        if not expected <= retained:
            raise ValueError("baseline task receipt omitted screenshot/DOM artifacts")
    from swissknife_visual_functional_llm import validate_model_receipt, RECEIPT_SCHEMA
    model_receipts = []
    artifact_paths = {path_in_root(item["path"]) for item in receipt["artifacts"]}
    for path in artifact_paths:
        if path.suffix != ".json":
            continue
        try:
            payload = json.loads(path.read_text())
        except ValueError:
            continue
        if type(payload) is dict and payload.get("schema") == RECEIPT_SCHEMA:
            model_receipts.append(validate_model_receipt(ROOT, payload, task_id=task["task_id"],
                require_visual=task["kind"] in {"review", "verify", "final-app-verify"}, predicted_files=task.get("edit_paths", [])))
    required_modes = {"model-probe": "probe", "review": "review", "implementation": "repair",
                      "repair": "repair", "backend-repair": "repair", "verify": "review", "final-app-verify": "review"}
    if task["kind"] in required_modes:
        if not any(item["mode"] == required_modes[task["kind"]] for item in model_receipts):
            raise ValueError("task lacks its independently validated model receipt")
    if task["kind"] in {"implementation", "repair", "backend-repair", "command", "foundation-gate"}:
        declared = task.get("checks", [])
        checks = receipt.get("checks", [])
        if not declared or type(checks) is not list or len(checks) != len(declared):
            raise ValueError("implementation evidence omitted declared executable checks")
        for expected, actual in zip(declared, checks):
            argv = actual.get("argv", [])
            if not argv or type(actual.get("exit_code")) is not int or actual["exit_code"] != 0:
                raise ValueError("implementation check did not execute successfully")
            normalized = ["python3", *argv[1:]] if Path(argv[0]).name in {"python", "python3"} else argv
            expected = ["python3", *expected[1:]] if Path(expected[0]).name in {"python", "python3"} else expected
            if normalized != expected:
                raise ValueError("implementation evidence changed the declared validation command")
    if task.get("foundation_pilot"):
        validate_foundation_pilot(profile, task)
    if task["kind"] == "foundation-gate":
        current_spec = json.loads(path_in_root(profile["taskSpecPath"]).read_text())
        validate_foundation_dependencies(profile, current_spec, task)
    if task["kind"] == "verify":
        report = retained_workflow_report(profile, task, receipt, directory / "verification")
        if json.loads(report.read_text()).get("schema") == "swissknife.visual-functional-workflow.v2":
            from swissknife_visual_functional_final_coverage import binding, review_join
            validated = validate_workflow(profile, task, report)
            review_path = report.parent / "visual-review.json"
            if review_path not in artifact_paths:
                raise ValueError("independent app receipt omitted its exact positive visual review")
            review_join(ROOT, profile, task, binding(task, validated), review_path)
            images = {(item["path"], item["sha256"], item["bytes"]) for item in validated["images"]}
        else:
            images = {(item["path"], item["sha256"], item["bytes"]) for item in json.loads(report.read_text())["artifacts"]
                      if Path(item["path"]).suffix == ".png"}
        if not any(item["mode"] == "review" and item["response"]["decision"] == "pass"
                   and {(image["path"], image["sha256"], image["size_bytes"]) for image in item["screenshots"]} == images
                   for item in model_receipts):
            raise ValueError("final visual review still requires changes")
    if task["kind"] == "final-app-verify":
        from swissknife_visual_functional_final_coverage import validate_final_task_contract, binding, review_join
        validate_final_task_contract(ROOT, profile, task)
        report = retained_workflow_report(profile, task, receipt, directory / "verification")
        validated = validate_workflow(profile, task, report)
        joined = review_join(ROOT, profile, task, binding(task, validated), report.parent / "visual-review.json")
        if (receipt.get("detail", {}).get("final_viewport_review_join") != joined
                or receipt["detail"].get("readonly_verification") is not True
                or type(receipt["detail"].get("repair_admissions")) is not int
                or receipt["detail"]["repair_admissions"] != 0):
            raise ValueError("final app receipt lost its exact fresh independent viewport visual review join")
    if task["kind"] in {"aggregate", "regression"}:
        if task["kind"] == "regression":
            if task["task_id"] == "SVF-900" or "final_app_tasks" in task:
                from swissknife_visual_functional_final_coverage import validate_coverage
                validate_coverage(ROOT, profile, task, receipt, validate_task=validate,
                    retained_report=retained_workflow_report, validate_report=validate_workflow)
            else:
                apps = json.loads(path_in_root(profile["appContractPath"]).read_text())["apps"]
                if sum(Path(item["path"]).name == "workflow.json" for item in receipt["artifacts"]) != len(apps):
                    raise ValueError("regression receipt must retain one workflow report per canonical app")
                for app in apps:
                    retained_workflow_report(profile, dict(task, app_id=app["app_id"]), receipt, directory / app["app_id"])
        else:
            regression_workflow_reports(profile, task)
        if task["kind"] == "aggregate":
            cross = validate_aggregate_dependencies(profile, task)
            if task["task_id"] == "SVF-990" or "final_app_tasks" in task:
                records = [item for item in receipt["artifacts"] if Path(item["path"]).name == "acceptance.json"]
                if len(records) != 1:
                    raise ValueError("final aggregate omitted its exact acceptance coverage join")
                accepted = json.loads(path_in_root(records[0]["path"]).read_text())
                coverage = artifact(runtime_root(profile) / "tasks" / task["regression_task"] / "final-app-coverage.json")
                if (accepted.get("decision") != "GO" or type(accepted.get("validated_apps")) is not int
                        or accepted["validated_apps"] != 45 or type(accepted.get("validated_final_app_reviews")) is not int
                        or accepted["validated_final_app_reviews"] != 45 or accepted.get("final_app_tasks") != task["final_app_tasks"]
                        or accepted.get("regression_coverage") != coverage or accepted.get("validated_cross_tasks") != cross
                        or accepted.get("work_complete") is not False or accepted.get("completion_authority") is not False):
                    raise ValueError("final aggregate lost its 45 fresh reviews/current reports or three cross-app joins")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--source", action="append", default=[])
    args = parser.parse_args(argv)
    if args.validate and args.recover:
        parser.error("validation and source recovery are separate operations")
    profile, spec = load(args.profile)
    task = next((t for t in spec["tasks"] if t["task_id"] == args.task_id), None)
    if task is None:
        parser.error("task is not in the admitted campaign")
    try:
        if args.recover:
            result = recover(args.profile, profile, task)
            print(json.dumps({"task_id": task["task_id"], "recovered": True, "validated": False,
                              "grants_task_completion": False}), flush=True)
            return 0
        result = validate(profile, task) if args.validate else execute(args.profile, profile, spec, task)
        print(json.dumps({"task_id": result["task_id"], "validated": True, "artifacts": len(result["artifacts"])}), flush=True)
        return 0
    except Exception as error:
        from swissknife_visual_functional_phase_budget import PhaseRepairBudgetExhausted
        if isinstance(error, PhaseRepairBudgetExhausted) and task.get("kind") == "verify":
            try:
                from swissknife_visual_functional_review_recheck import remember_exhaustion
                remember_exhaustion(ROOT, profile, task, error.record)
            except Exception as fence_error:
                error = fence_error  # Preserve typed ENOSPC/EDQUOT handling for fence persistence too.
        resource = storage_refusal(error)
        if resource is not None:
            print(json.dumps({"task_id": args.task_id,
                              "error": {"code": "storage_pressure", "reason": resource.reason, "errno": resource.errno},
                              "retryable": True, "work_complete": False, "completion_authority": False}),
                  file=sys.stderr, flush=True)
            return 75
        if isinstance(error, BrowserContention):
            print(json.dumps({"task_id": args.task_id, "error": {"code": "browser_contention"},
                              "retryable": True, "work_complete": False, "completion_authority": False}),
                  file=sys.stderr, flush=True)
            return 75
        print(f"SVF {args.task_id}: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
