#!/usr/bin/env python3
"""Read-only recovery canary assertion; this checker grants no completion authority."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PARTS = ("data", "agent_supervisor", "swissknife_visual_functional")
MAX_FIXTURE_BYTES = 4096
EXPECTED_STATE = {"recovery_state": "repaired_by_scoped_model"}


class CanaryError(ValueError):
    pass


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise CanaryError("duplicate JSON field")
        value[key] = item
    return value


def verify_fixture(fixture: str, *, root: Path = ROOT) -> dict:
    """Inspect exact bytes beneath an anchored directory descriptor; never write."""
    if not isinstance(fixture, str) or len(fixture) > 1024 or "\\" in fixture or "\x00" in fixture:
        raise CanaryError("invalid fixture path")
    parts = fixture.split("/")
    if (len(parts) < len(RUNTIME_PARTS) + 1 or len(parts) > 24
            or tuple(parts[:len(RUNTIME_PARTS)]) != RUNTIME_PARTS
            or any(part in {"", ".", ".."} for part in parts) or not parts[-1].endswith(".json")):
        raise CanaryError("fixture must be a root-relative JSON file in the SVF runtime")
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        try:
            info = os.fstat(file_descriptor)
            if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= MAX_FIXTURE_BYTES:
                raise CanaryError("fixture must be a bounded regular file")
            raw = bytearray()
            while len(raw) <= MAX_FIXTURE_BYTES:
                chunk = os.read(file_descriptor, MAX_FIXTURE_BYTES + 1 - len(raw))
                if not chunk:
                    break
                raw.extend(chunk)
            if len(raw) > MAX_FIXTURE_BYTES:
                raise CanaryError("fixture grew beyond its byte bound")
            # A directory moved during traversal cannot relocate this read
            # outside the named campaign namespace unnoticed.
            observed = Path(os.readlink(f"/proc/self/fd/{file_descriptor}"))
            if observed != root / Path(*parts):
                raise CanaryError("fixture path changed during verification")
        finally:
            os.close(file_descriptor)
    finally:
        os.close(descriptor)
    try:
        def reject_constant(_value):
            raise CanaryError("non-finite JSON value")
        value = json.loads(bytes(raw).decode("utf-8"), object_pairs_hook=_object, parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CanaryError("fixture is not valid UTF-8 JSON") from exc
    if type(value) is not dict or value != EXPECTED_STATE:
        raise CanaryError("recovery fixture has not reached the exact repaired state")
    return {"verified": True, "fixture": fixture, "assertion": "exact_repaired_state",
            "read_only": True, "work_complete": False, "completion_authority": False,
            "gui_acceptance": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.add_argument("--fixture", required=True)
    args = parser.parse_args(argv)
    try:
        result = verify_fixture(args.fixture)
    except (CanaryError, OSError) as exc:
        print(json.dumps({"verified": False, "error_type": type(exc).__name__, "reason": str(exc),
                          "read_only": True, "work_complete": False, "completion_authority": False}), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
