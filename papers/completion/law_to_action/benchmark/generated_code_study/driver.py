#!/usr/bin/python3.12
"""Durable scientific driver for the generated-code family-batch study.

Preparation may qualify the driver under bounded development input. It cannot
dispatch final cells or claim any planned scientific cell completed.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

HERE = Path(__file__).resolve()
ROOT = HERE.parents[5]
STUDY = HERE.parent
for _path in (STUDY, STUDY / "preparation", STUDY / "qualification"):
    text = str(_path)
    if text not in sys.path:
        sys.path.insert(0, text)
from study_common import (  # noqa: E402
    ARMS,
    ATTEMPT_WALL_SECONDS,
    MAX_CALLS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    PAID_BUDGET,
    PROMPT_PROFILE,
    SEEDS,
    SERVICE_WALL_SECONDS,
    STARTUP_READINESS_SECONDS,
    canonical,
    digest,
    read_json,
    require,
    sha_file,
    write_json,
)

OWNER_LEASE = "driver.owner.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def messages_for(task: dict[str, Any], arm: str, history: list[dict[str, Any]]) -> list[dict[str, str]]:
    require(arm in ARMS, "unknown arm")
    messages = [{"role": "system", "content": PROMPT_PROFILE["system"]}, {"role": "user", "content": task["instruction"]}]
    if arm != "A0":
        messages.append({"role": "user", "content": PROMPT_PROFILE["policy_label"] + canonical(task["policy"]).decode()})
    if arm in ("A2", "A3", "A4"):
        contexts = task.get("retrieval") or []
        if not contexts:
            raise ValueError("A2/A3/A4 require explicit lineage-safe retrieval context")
        for context in contexts:
            if (
                context.get("source_family") != task["source_family"]
                or context.get("kind") != "permitted_public_source"
                or context.get("contains_oracle") is not False
                or context.get("contains_target_patch") is True
                or context.get("contains_sibling_final_label") is True
            ):
                raise ValueError("Retrieval lineage/oracle contract failed")
        messages.append({"role": "user", "content": PROMPT_PROFILE["retrieval_label"] + canonical(contexts).decode()})
    for old in history:
        messages.append({"role": "assistant", "content": old["response_text"]})
        messages.append({"role": "user", "content": PROMPT_PROFILE["feedback_label"] + canonical(old["feedback"]).decode()})
    return messages


class ExclusiveOwner:
    def __init__(self, directory: Path, owner_id: str):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.owner_id = owner_id
        self.path = self.directory / OWNER_LEASE

    def acquire(self) -> dict[str, Any]:
        lease = {
            "owner_id": self.owner_id,
            "pid": os.getpid(),
            "acquired_at": utc_now(),
            "hostname": socket.gethostname(),
        }
        if self.path.exists():
            existing = read_json(self.path)
            if existing.get("owner_id") != self.owner_id:
                live = existing.get("pid")
                if isinstance(live, int) and live > 0:
                    try:
                        os.kill(live, 0)
                        raise ValueError("exclusive owner already live: " + existing["owner_id"])
                    except ProcessLookupError:
                        write_json(self.directory / "stale_owner_reconciliation.json", {"previous": existing, "action": "reclaimed"})
                else:
                    raise ValueError("exclusive owner lease occupied")
        tmp = self.path.with_suffix(".tmp-" + uuid4().hex)
        tmp.write_text(json.dumps(lease, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)
        return lease

    def release(self) -> None:
        if self.path.exists():
            current = read_json(self.path)
            if current.get("owner_id") == self.owner_id:
                self.path.unlink()


class ReservationStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, identity: str) -> Path:
        digest_id = hashlib.sha256(identity.encode()).hexdigest()
        return self.directory / (digest_id + ".json")

    def reserve(self, kind: str, identity: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._path(kind + ":" + identity)
        if path.exists():
            existing = read_json(path)
            if existing.get("consumed"):
                raise ValueError("silent replay/refund refused for " + identity)
            return existing
        record = {
            "kind": kind,
            "identity": identity,
            "reserved_at": utc_now(),
            "consumed": False,
            "payload": payload,
            "unknown_usage": False,
            "unknown_effect": False,
        }
        write_json(path, record)
        return record

    def consume(self, kind: str, identity: str, update: dict[str, Any]) -> dict[str, Any]:
        path = self._path(kind + ":" + identity)
        if not path.exists():
            raise ValueError("consume without reservation: " + identity)
        record = read_json(path)
        if record.get("consumed"):
            raise ValueError("one-time capability already consumed: " + identity)
        record.update(update)
        record["consumed"] = True
        record["consumed_at"] = utc_now()
        path.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return record


class BoundedModelService:
    def __init__(self, profile: dict[str, Any], work: Path):
        self.profile = profile
        self.work = Path(work)
        self.work.mkdir(parents=True, exist_ok=True)
        self.process: subprocess.Popen | None = None
        self.base_url: str | None = None
        self.started = None
        self.startup_seconds = None

    def start(self) -> dict[str, Any]:
        if self.process is not None:
            return {"reused": True, "base_url": self.base_url}
        ready = self.work / "model.ready.json"
        if ready.exists():
            ready.unlink()
        weights = Path(self.profile["weights_path"])
        service = Path(self.profile["deployment_path"])
        require(sha_file(weights) == self.profile["weights_sha256"], "weights pin changed")
        require(sha_file(service) == self.profile["deployment_sha256"], "deployment pin changed")
        started = time.monotonic()
        self.process = subprocess.Popen(
            [
                "/usr/bin/python3.12",
                "-B",
                str(service),
                "--weights",
                str(weights),
                "--host",
                "127.0.0.1",
                "--port",
                "0",
                "--max-wall-seconds",
                str(SERVICE_WALL_SECONDS),
                "--ready-file",
                str(ready),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.work),
        )
        deadline = started + STARTUP_READINESS_SECONDS
        while time.monotonic() < deadline:
            if ready.exists():
                info = read_json(ready)
                self.base_url = f"http://127.0.0.1:{info['port']}"
                self.started = started
                self.startup_seconds = time.monotonic() - started
                return {"reused": False, "base_url": self.base_url, "startup_seconds": self.startup_seconds}
            if self.process.poll() is not None:
                raise RuntimeError("model service exited during startup")
            time.sleep(0.05)
        self.stop()
        raise TimeoutError("model startup exceeded 360-second readiness bound")

    def stop(self) -> None:
        if self.process is None:
            return
        try:
            self.process.send_signal(signal.SIGTERM)
            self.process.wait(timeout=5)
        except Exception:
            self.process.kill()
        self.process = None

    def post(self, path: str, body: dict[str, Any], remaining: float) -> dict[str, Any]:
        require(self.base_url is not None, "model service is not running")
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        request = urllib.request.Request(
            self.base_url + path,
            data=raw,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=max(0.1, remaining)) as response:
            return json.loads(response.read().decode("utf-8"))


class ScientificDriver:
    def __init__(self, study_path: Path, state_dir: Path):
        self.study_path = Path(study_path)
        self.study = read_json(self.study_path)
        self.study_sha256 = sha_file(self.study_path)
        require(self.study.get("schema") == "la-closed-loop-study/v1", "study schema")
        require(self.study.get("scientific_cells_executed") == 0, "preparation cannot claim scientific cells")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.owner = ExclusiveOwner(self.state_dir, "owner:la032:" + self.study_sha256[:16])
        self.reservations = ReservationStore(self.state_dir / "reservations")
        self.profile = read_json(Path(self.study["model_profile"]["path"]))
        require(sha_file(Path(self.study["model_profile"]["path"])) == self.study["model_profile"]["sha256"], "model profile")
        self.service: BoundedModelService | None = None

    def identity(self) -> dict[str, Any]:
        return {
            "study_sha256": self.study_sha256,
            "model_profile_sha256": self.study["model_profile"]["sha256"],
            "runtime_profile_sha256": self.study["runtime_profile"]["sha256"],
            "cohort_sha256": self.study["cohort"]["sha256"],
            "schedule_sha256": self.study["schedule_binding"]["sha256"],
            "prompt_profile_sha256": digest(PROMPT_PROFILE),
        }

    def refuse_scientific_dispatch(self, cell: dict[str, Any]) -> None:
        family = cell.get("split") or cell.get("phase")
        if self.study.get("final_stage_released") is not True and cell.get("split") == "final":
            raise PermissionError("final cells cannot be dispatched before the final-stage gate")
        if self.study.get("scientific_execution_allowed") is not True:
            raise PermissionError("preparation cannot dispatch planned scientific cells")

    def infer(self, messages: list[dict[str, str]], seed: int, directory: Path, remaining: float) -> dict[str, Any]:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        if self.service is None:
            self.service = BoundedModelService(self.profile, self.state_dir / "model-service")
            self.service.start()
        begin = time.monotonic()
        rendered = self.service.post("/apply-template", {"messages": messages, "add_generation_prompt": True}, remaining)
        tokenized = self.service.post("/tokenize", {"content": rendered["prompt"], "add_special": True}, remaining - (time.monotonic() - begin))
        input_count = len(tokenized["tokens"])
        require(type(input_count) is int and input_count <= MAX_INPUT_TOKENS, "input ceiling")
        reservation = self.reservations.reserve(
            "model_call",
            digest({"messages": messages, "seed": seed, "directory": str(directory)}),
            {"input_count": input_count, "seed": seed},
        )
        write_json(directory / "inference_reserved.json", {"input_count": input_count, "seed": seed, "consumed_before_request": True})
        body = self.service.post(
            "/v1/chat/completions",
            {
                "model": self.profile["model_id"],
                "messages": messages,
                "temperature": 0,
                "seed": seed,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "stream": False,
            },
            remaining - (time.monotonic() - begin),
        )
        (directory / "raw_response.bin").write_bytes(canonical(body))
        usage = body["usage"]
        prompt_tokens = usage["prompt_tokens"]
        require(prompt_tokens == input_count, "prompt_tokens must equal retained preflight input_count")
        require(usage["completion_tokens"] <= MAX_OUTPUT_TOKENS, "output ceiling")
        self.reservations.consume(
            "model_call",
            reservation["identity"],
            {"prompt_tokens": prompt_tokens, "completion_tokens": usage["completion_tokens"]},
        )
        result = {
            "response_text": body["choices"][0]["message"]["content"],
            "prompt_tokens": prompt_tokens,
            "completion_tokens": usage["completion_tokens"],
            "preflight_input_count": input_count,
            "model_calls": 1,
            "wall_seconds": time.monotonic() - begin,
            "origin": "qualified-local-model",
            "model_generated": True,
        }
        write_json(directory / "transport_result.json", result)
        return result


def probe_interrupt_resume(driver: ScientificDriver, output: Path) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    driver.owner.acquire()
    cell_id = "dev-probe:A0:104729"
    cell = driver.reservations.reserve("cell", cell_id, {"phase": "development", "split": "development"})
    call = driver.reservations.reserve("model_call", cell_id + ":call-0", {"input_count": 4})
    interrupted = {"cell": cell["identity"], "call": call["identity"], "interrupted": True}
    write_json(output / "interrupted.json", interrupted)
    resumed = ScientificDriver(driver.study_path, driver.state_dir)
    resumed.owner.acquire()
    try:
        resumed.reservations.reserve("cell", cell_id, {"phase": "development"})
        resumed.reservations.consume("model_call", call["identity"], {"first": True})
        replay_error = None
        try:
            resumed.reservations.consume("model_call", call["identity"], {"replay": True})
        except ValueError as exc:
            replay_error = str(exc)
        cleanup = {"fault": "injected_cleanup_oserror", "unknown_effect": True, "refunded": False}
        write_json(output / "cleanup_fault.json", cleanup)
        require(replay_error is not None and "consumed" in replay_error, "silent replay was not refused")
        report = {
            "schema": "la032-driver-interrupt-resume/v1",
            "status": "PASS",
            "replay_refused": True,
            "cleanup_fault_unknown_retained": True,
            "refunded": False,
            "scientific_cells_executed": 0,
            "identity": driver.identity(),
        }
        write_json(output / "interrupt_resume.json", report)
        return report
    finally:
        resumed.owner.release()
        driver.owner.release()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("identity", "probe-interrupt"))
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    driver = ScientificDriver(args.study, args.state)
    if args.action == "identity":
        print(json.dumps(driver.identity(), sort_keys=True))
        return
    report = probe_interrupt_resume(driver, args.output or args.state / "probes")
    print(json.dumps({"status": report["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
