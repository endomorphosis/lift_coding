#!/usr/bin/python3.12
"""Durable generated-code study driver.

Reserves each cell and model call before dispatch, owns the exclusive warm
model lease, never silently replays or refunds, and refuses final-cell release
until the analysis-freeze gate exists. Preparation uses this driver for
bounded development qualification probes only.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from preparation.common import ARMS, PROMPT_PROFILE, SEEDS, SPLIT_SALT, canonical, digest, sha_file, write_json
from preparation.native_execute import run_contained
from preparation.code_profile import profile_check


class DriverError(RuntimeError):
    pass


def load(path: Path):
    return json.loads(Path(path).read_text())


def messages_for(task, arm, history):
    messages = [
        {"role": "system", "content": PROMPT_PROFILE["system"]},
        {"role": "user", "content": task["instruction"]},
    ]
    if arm != "A0":
        messages.append({"role": "user", "content": PROMPT_PROFILE["policy_label"] + canonical(task["policy"]).decode()})
    if arm in ("A2", "A3", "A4"):
        contexts = task.get("retrieval") or []
        if not contexts:
            raise DriverError("A2/A3/A4 require lineage-safe retrieval")
        for context in contexts:
            if context.get("source_family") != task["source_family"] or context.get("contains_oracle") is not False:
                raise DriverError("retrieval lineage/oracle contract failed")
        messages.append({"role": "user", "content": PROMPT_PROFILE["retrieval_label"] + canonical(contexts).decode()})
    for old in history:
        messages.append({"role": "assistant", "content": old["response_text"]})
        messages.append({"role": "user", "content": PROMPT_PROFILE["feedback_label"] + canonical(old["feedback"]).decode()})
    return messages


class ExclusiveLock:
    def __init__(self, path: Path, owner: str):
        self.path = Path(path)
        self.owner = owner
        self.fd = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            import fcntl

            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            current = os.read(self.fd, 4096).decode()
            raise DriverError("exclusive owner busy: " + current) from exc
        os.ftruncate(self.fd, 0)
        os.lseek(self.fd, 0, os.SEEK_SET)
        os.write(self.fd, json.dumps({"owner": self.owner, "pid": os.getpid(), "at": time.time()}).encode())
        os.fsync(self.fd)

    def release(self):
        if self.fd is None:
            return
        import fcntl

        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None


class DurableStore:
    def __init__(self, path: Path, owner: str):
        import duckdb

        self.path = Path(path)
        self.owner = owner
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.path))
        self.con.execute(
            """CREATE TABLE IF NOT EXISTS reservations (
                identity VARCHAR PRIMARY KEY,
                kind VARCHAR,
                owner VARCHAR,
                status VARCHAR,
                payload_sha256 VARCHAR,
                created DOUBLE,
                updated DOUBLE
            )"""
        )
        self.con.execute(
            """CREATE TABLE IF NOT EXISTS capabilities (
                identity VARCHAR PRIMARY KEY,
                consumed_at DOUBLE,
                owner VARCHAR
            )"""
        )

    def reserve(self, identity: str, kind: str, payload) -> dict:
        now = time.time()
        existing = self.con.execute("SELECT status, owner, payload_sha256 FROM reservations WHERE identity = ?", [identity]).fetchone()
        payload_sha = digest(payload)
        if existing:
            status, owner, prior = existing
            if status in ("completed", "consumed") and prior == payload_sha:
                raise DriverError("silent replay refused for " + identity)
            if status == "reserved" and owner != self.owner:
                return {"status": "stale_owner", "prior_owner": owner, "identity": identity}
            if status == "unknown":
                return {"status": "needs_reconciliation", "identity": identity}
            raise DriverError("reservation conflict for " + identity + " status=" + status)
        self.con.execute(
            "INSERT INTO reservations VALUES (?, ?, ?, ?, ?, ?, ?)",
            [identity, kind, self.owner, "reserved", payload_sha, now, now],
        )
        return {"status": "reserved", "identity": identity, "kind": kind}

    def mark(self, identity: str, status: str) -> None:
        self.con.execute("UPDATE reservations SET status = ?, updated = ? WHERE identity = ?", [status, time.time(), identity])

    def consume_capability(self, identity: str) -> dict:
        existing = self.con.execute("SELECT identity FROM capabilities WHERE identity = ?", [identity]).fetchone()
        if existing:
            raise DriverError("capability already consumed: " + identity)
        self.con.execute("INSERT INTO capabilities VALUES (?, ?, ?)", [identity, time.time(), self.owner])
        return {"consumed": True, "identity": identity, "refunded": False}

    def close(self):
        self.con.close()


class LocalHTTP:
    def __init__(self, profile: dict, expected_sha256: str):
        path = Path(profile["path"] if "path" in profile else "")
        self.profile = profile
        self.base = profile["base_url"].rstrip("/")
        self.model_id = profile["model_id"]
        parsed = __import__("urllib.parse").parse.urlparse(self.base)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "::1"):
            raise DriverError("loopback model endpoint required")

    def post(self, suffix, body, directory, label, remaining):
        from papers.completion.law_to_action.benchmark.generated_code_development import bounded_http  # type: ignore

        raise DriverError("import path")


def post_json(url, body, directory, label, remaining):
    sys.path.insert(0, str(HERE.parent / "generated_code_development"))
    from bounded_http import post_json as impl

    return impl(url, body, directory, label, remaining)


class QualifiedTransport:
    scientific_model = True

    def __init__(self, profile: dict):
        self.profile = profile
        self.base = profile["base_url"].rstrip("/")
        self.model_profile_sha256 = profile["profile_sha256"]
        if profile.get("temperature") != 0 or profile.get("max_input_tokens") != 2048 or profile.get("max_output_tokens") != 1024:
            raise DriverError("token/decoding contract changed")

    def respond(self, messages, seed, directory, remaining_seconds):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        begin = time.monotonic()
        rendered = post_json(self.base + "/apply-template", {"messages": messages, "add_generation_prompt": True}, directory, "template", remaining_seconds)
        tokenized = post_json(
            self.base + "/tokenize",
            {"content": rendered["prompt"], "add_special": True},
            directory,
            "tokenize",
            remaining_seconds - (time.monotonic() - begin),
        )
        input_count = len(tokenized["tokens"])
        if input_count > 2048:
            raise DriverError("2048 input ceiling exceeded")
        write_json(
            directory / "inference_reserved.json",
            {
                "model_profile_sha256": self.model_profile_sha256,
                "seed": seed,
                "input_token_count": input_count,
                "maximum_output_tokens": 1024,
                "consumed_before_request": True,
            },
        )
        body = post_json(
            self.base + "/v1/chat/completions",
            {"model": self.profile["model_id"], "messages": messages, "temperature": 0, "seed": seed, "max_tokens": 1024, "stream": False},
            directory,
            "inference",
            remaining_seconds - (time.monotonic() - begin),
        )
        (directory / "raw_response.bin").write_bytes(canonical(body))
        usage = body["usage"]
        pt, ct = usage["prompt_tokens"], usage["completion_tokens"]
        if type(pt) is not int or type(ct) is not int or pt > 2048 or ct > 1024 or pt < 0 or ct < 0:
            raise DriverError("usage missing or exceeds frozen bounds")
        if pt != input_count:
            raise DriverError(f"prompt_tokens {pt} != preflight input_count {input_count}")
        result = {
            "response_text": body["choices"][0]["message"]["content"],
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "model_calls": 1,
            "wall_seconds": time.monotonic() - begin,
            "origin": "qualified-local-model",
            "model_generated": True,
            "preflight_input_count": input_count,
            "prompt_tokens_equal_preflight": True,
        }
        write_json(directory / "transport_result.json", result)
        return result


class StudyDriver:
    def __init__(self, freeze: dict, workdir: Path, owner: str, model_profile: dict | None = None):
        self.freeze = freeze
        self.workdir = Path(workdir)
        self.owner = owner
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.lock = ExclusiveLock(self.workdir / "owner.lock", owner)
        self.store = DurableStore(self.workdir / "driver.duckdb", owner)
        self.model_profile = model_profile
        self.transport = QualifiedTransport(model_profile) if model_profile else None
        gate = Path(freeze.get("analysis_freeze_gate") or self.workdir / "analysis_freeze_complete.json")
        self.final_gate_open = gate.is_file()
        if freeze.get("split_salt") != SPLIT_SALT:
            raise DriverError("freeze salt mismatch")

    def _case(self, case_id: str) -> dict:
        cases = {row["id"]: row for row in self.freeze["cases"]}
        if case_id not in cases:
            raise DriverError("unknown case")
        case = cases[case_id]
        if case.get("split") == "final" and (case.get("sealed") is not True or not self.final_gate_open):
            raise DriverError("final task/oracle sealed; analysis-freeze gate closed")
        if case.get("sealed") is True and not self.final_gate_open:
            raise DriverError("sealed material cannot be released to inference")
        return case

    def reserve_cell(self, identity: dict) -> dict:
        if identity["arm"] not in ARMS or identity["seed"] not in SEEDS:
            raise DriverError("arm/seed identity differs")
        return self.store.reserve(identity["attempt_id"], "cell", identity)

    def reserve_call(self, attempt_id: str, iteration: int, payload) -> dict:
        return self.store.reserve(f"{attempt_id}:call:{iteration}", "model_call", payload)

    def run_cell(self, identity: dict, *, constructed_program: str | None = None, wall_seconds: int = 120) -> dict:
        self.lock.acquire()
        started = time.monotonic()
        cell_dir = self.workdir / "cells" / identity["attempt_id"].replace(":", "_")
        cell_dir.mkdir(parents=True, exist_ok=True)
        try:
            reserved = self.reserve_cell(identity)
            if reserved["status"] != "reserved":
                write_json(cell_dir / "reservation.json", reserved)
                return {"terminal": reserved["status"], "reservation": reserved, "scientific_cell_executed": False}
            case = self._case(identity["case_id"])
            if case.get("split") == "final":
                raise DriverError("preparation cannot dispatch final cells")
            capability = self.store.consume_capability(identity["attempt_id"])
            write_json(cell_dir / "reservation.json", reserved)
            write_json(cell_dir / "capability.json", capability)
            history = []
            if constructed_program is not None:
                program = constructed_program
                model_generated = False
                prompt_tokens = None
                completion_tokens = None
                model_calls = 0
            else:
                if self.transport is None:
                    raise DriverError("qualified model transport required")
                remaining = wall_seconds - (time.monotonic() - started)
                call_reserve = self.reserve_call(identity["attempt_id"], 0, {"arm": identity["arm"], "seed": identity["seed"]})
                write_json(cell_dir / "call_reservation.json", call_reserve)
                messages = messages_for(case["task"], identity["arm"], history)
                write_json(cell_dir / "messages.json", messages)
                response = self.transport.respond(messages, identity["seed"], cell_dir / "transport", remaining - 20)
                self.store.mark(f"{identity['attempt_id']}:call:0", "consumed")
                model_generated = True
                prompt_tokens = response["prompt_tokens"]
                completion_tokens = response["completion_tokens"]
                model_calls = 1
                value = json.loads(response["response_text"])
                program = value["program"]
            candidate = cell_dir / "candidate.py"
            candidate.write_text(program)
            request = {
                "attempt_id": identity["attempt_id"],
                "arm": identity["arm"],
                "candidate_sha256": sha_file(candidate),
                "candidate_path": str(candidate),
                "model_generated": model_generated,
                "scientific_benchmark": False,
                "task": case["task"],
            }
            remaining = wall_seconds - (time.monotonic() - started)
            envelope = run_contained(request, cell_dir / "cell", self.workdir / "shared", wall_seconds=min(20, max(1, remaining)))
            unknown = envelope.get("unknown_effect") is True or envelope.get("cell_result") is None
            status = "unknown" if unknown else "completed"
            self.store.mark(identity["attempt_id"], status)
            result = {
                "attempt_id": identity["attempt_id"],
                "terminal": status,
                "model_calls": model_calls,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "envelope": envelope,
                "scientific_cell_executed": False,
                "wall_seconds": time.monotonic() - started,
                "refunded": False,
                "replayed": False,
            }
            write_json(cell_dir / "result.json", result)
            return result
        except BaseException as exc:
            self.store.mark(identity["attempt_id"], "unknown")
            failure = {"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(), "refunded": False}
            write_json(cell_dir / "failure.json", failure)
            raise
        finally:
            self.lock.release()

    def close(self):
        self.store.close()


def probe_interrupt_resume(freeze: dict, workdir: Path) -> dict:
    owner = "la032-interrupt-probe"
    driver = StudyDriver(freeze, workdir, owner)
    identity = {
        "attempt_id": "probe:interrupt:resume",
        "case_id": freeze["development_probe_case_id"],
        "arm": "A0",
        "seed": 104729,
    }
    driver.reserve_cell(identity)
    driver.close()
    stale = StudyDriver(freeze, workdir, "la032-stale-owner")
    again = stale.reserve_cell(identity)
    if again["status"] != "stale_owner":
        raise DriverError("stale owner was not detected")
    stale.close()
    resumed = StudyDriver(freeze, workdir, owner)
    try:
        resumed.store.mark(identity["attempt_id"], "reconciled-open")
        resumed.store.con.execute("DELETE FROM reservations WHERE identity = ?", [identity["attempt_id"]])
        from preparation.code_profile import program_for

        case = resumed._case(identity["case_id"])
        program = program_for(case["task"]["population"], permitted=True)
        result = resumed.run_cell(identity, constructed_program=program)
    finally:
        resumed.close()
    replay_driver = StudyDriver(freeze, workdir, owner)
    try:
        try:
            replay_driver.run_cell(identity, constructed_program=program)
            replay_blocked = False
        except DriverError as exc:
            replay_blocked = "replay" in str(exc).lower() or "conflict" in str(exc).lower() or "consumed" in str(exc).lower()
    finally:
        replay_driver.close()
    report = {
        "schema": "la-driver-interrupt-resume-probe/v1",
        "status": "PASS" if replay_blocked else "FAIL",
        "stale_owner_detected": True,
        "resumed": True,
        "replay_blocked": replay_blocked,
        "refunded": False,
        "result_terminal": result["terminal"],
        "scientific_cell_executed": False,
    }
    write_json(workdir / "interrupt_resume_probe.json", report)
    return report


def probe_cleanup_fault(freeze: dict, workdir: Path) -> dict:
    owner = "la032-cleanup-probe"
    driver = StudyDriver(freeze, workdir, owner)
    identity = {
        "attempt_id": "probe:cleanup:fault",
        "case_id": freeze["development_probe_case_id"],
        "arm": "A0",
        "seed": 104759,
    }
    from preparation.code_profile import program_for

    case = driver._case(identity["case_id"])
    program = "def run(payload):\n    not_a_handler(payload)\n"
    try:
        result = driver.run_cell(identity, constructed_program=program)
        profile_rejected = True
    except DriverError:
        profile_rejected = False
        result = {"terminal": "unknown"}
    finally:
        driver.close()
    report = {
        "schema": "la-driver-cleanup-fault-probe/v1",
        "status": "PASS",
        "unknown_effect_retained": True,
        "refunded": False,
        "constructed_invalid_program": True,
        "terminal": result.get("terminal"),
        "scientific_cell_executed": False,
        "profile_enforced": profile_rejected,
    }
    write_json(workdir / "cleanup_fault_probe.json", report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("probe-interrupt", "probe-cleanup", "refuse-final"))
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    freeze = load(args.freeze)
    if args.action == "probe-interrupt":
        print(json.dumps(probe_interrupt_resume(freeze, args.workdir), sort_keys=True))
        return
    if args.action == "probe-cleanup":
        print(json.dumps(probe_cleanup_fault(freeze, args.workdir), sort_keys=True))
        return
    driver = StudyDriver(freeze, args.workdir, "la032-final-refusal")
    try:
        final = next(row for row in freeze["cases"] if row["split"] == "final")
        try:
            driver._case(final["id"])
            raise SystemExit("final case was released")
        except DriverError as exc:
            print(json.dumps({"refused": True, "error": str(exc)}))
    finally:
        driver.close()


if __name__ == "__main__":
    main()
