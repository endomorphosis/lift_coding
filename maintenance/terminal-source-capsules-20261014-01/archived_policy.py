"""Distinct bootstrap from two exact sealed retained native policy sources.

This profile does not satisfy or relax the predecessor loader's requirement to
verify live original files. It verifies the named sealed retained bytes only.
The unchanged native consumer later performs its real-host, attach-only
scheduler admission; bootstrap never opens that scheduler's state.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parent
TYPED = ROOT.parent / "terminal-typed-ir-proof-index-20261014-01"
OVERLAY = TYPED / "native-policy-overlay-01"
MANIFEST = TYPED / "evidence-manifest.json"
PINFILE = OVERLAY / "source-pins.json"
PACKAGE = "ipfs_datasets_py.optimizers.logic_theorem_optimizer"
ORDER = (PACKAGE + ".proof_resource_safety", PACKAGE + ".resource_scheduler")
PROFILE = "sealed-retained-native-policy-source-bootstrap@1"
MANIFEST_SHA256 = "fec478e685ac2b3f1a4412cd798d51468406cbcccbae09173c68855c41910f35"
MANIFEST_BYTES = 66609
PINFILE_SHA256 = "8f4a904d6dbd53c00d1958376cb8f544aa19a8842c0f7258ed9456b24c21829d"
PINFILE_BYTES = 1529
SOURCE_PINS = (
    {"module": ORDER[0], "filename": "proof_resource_safety.py", "bytes": 15543,
        "sha256": "3655923785cb99409171caaba8c523354f03dbe8d82b6deb45a7b46db8394633"},
    {"module": ORDER[1], "filename": "resource_scheduler.py", "bytes": 121503,
        "sha256": "7c889bc858ff092e18bd2e97ff5a6407973e226eae33cddc9e5eef1d21f35986"},
)


class ArchivedPolicyError(ValueError):
    """The explicit sealed profile or process-local native class boundary differs."""


def _need(condition, message):
    if not condition:
        raise ArchivedPolicyError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path, maximum):
    _need(isinstance(path, Path) and path.is_absolute(), "absolute retained policy path required")
    try:
        _need(path.resolve(strict=True) == path, "canonical no-symlink retained path required")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise ArchivedPolicyError("named retained source is unavailable; refresh refused") from error
    try:
        before = os.fstat(descriptor)
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= maximum,
            "bounded single-link regular retained source required")
        parts, size = [], 0
        while size <= maximum:
            block = os.read(descriptor, min(65536, maximum + 1 - size))
            if not block:
                break
            parts.append(block)
            size += len(block)
        after = os.fstat(descriptor)
        witness = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
        _need(size <= maximum and size == before.st_size and witness(before) == witness(after),
            "retained source changed during bounded acquisition")
        return b"".join(parts)
    finally:
        os.close(descriptor)


def _exact(path, count, digest):
    raw = _read(path, count)
    _need(len(raw) == count and _sha(raw) == digest, "frozen retained bytes or digest differs; refresh refused")
    return raw


def _parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, "duplicate archive JSON key")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, RecursionError) as error:
        if isinstance(error, ArchivedPolicyError): raise
        raise ArchivedPolicyError("bounded archive JSON required") from error


def _validate_order(records):
    _need(type(records) is list and len(records) == 2
        and all(type(row) is dict for row in records)
        and tuple(row.get("module") for row in records) == ORDER,
        "retained collector must load before its matching native scheduler")


def _verified_archive():
    """Read only manifest, pinfile and two explicitly selected retained sources."""
    inventory_raw = _exact(MANIFEST, MANIFEST_BYTES, MANIFEST_SHA256)
    inventory = _parse(inventory_raw)
    _need(type(inventory) is dict and inventory.get("schema") == "terminal-codebase-ir-evidence-integrity-seal@1"
        and type(inventory.get("files")) is list and len(inventory["files"]) <= 4096,
        "closed selected predecessor integrity inventory required")
    expected = {"native-policy-overlay-01/source-pins.json": (PINFILE_BYTES, PINFILE_SHA256)}
    expected.update({"native-policy-overlay-01/" + row["filename"]: (row["bytes"], row["sha256"])
        for row in SOURCE_PINS})
    entries = {}
    for row in inventory["files"]:
        if row.get("path") in expected:
            _need(row["path"] not in entries, "duplicate selected archived inventory member")
            entries[row["path"]] = row
    _need(set(entries) == set(expected), "complete selected retained inventory required")
    for name, (size, digest) in expected.items():
        row = entries[name]
        _need(type(row.get("bytes")) is int and row["bytes"] == size and row.get("sha256") == digest
            and row.get("mode") == 0o444, "selected archived inventory pin differs")
    pin_raw = _exact(PINFILE, PINFILE_BYTES, PINFILE_SHA256)
    pin = _parse(pin_raw)
    _need(type(pin) is dict and pin.get("schema") == "terminal-native-policy-source-overlay@1"
        and pin.get("overlay_root") == str(OVERLAY)
        and pin.get("only_selected_two_modules") is True and pin.get("pinned_v10_modified") is False
        and pin.get("original_public_sources_modified") is False and pin.get("shared_scheduler_state_modified") is False
        and pin.get("runtime_telemetry_overlay_required") is False,
        "original frozen two-module provenance differs")
    records = pin.get("modules")
    _validate_order(records)
    modules, bodies = [], []
    public_root = ROOT.parent.parent / "external" / "ipfs_datasets" / "ipfs_datasets_py" / "optimizers" / "logic_theorem_optimizer"
    for row, expected in zip(records, SOURCE_PINS):
        retained = OVERLAY / expected["filename"]
        # The historical public-source NAME is checked as data. Its path is
        # never opened, statted, imported, or used to refresh retained bytes.
        _need(row.get("retained_source") == str(retained)
            and row.get("public_source") == str(public_root / expected["filename"])
            and type(row.get("bytes")) is int and row["bytes"] == expected["bytes"]
            and row.get("sha256") == expected["sha256"] and row.get("retained_source_exact") is True
            and row.get("public_source_pre_post_equal") is True,
            "historical selected source record differs from frozen archive")
        bodies.append(_exact(retained, expected["bytes"], expected["sha256"]))
        modules.append({"module": expected["module"], "path": str(retained),
            "bytes": expected["bytes"], "sha256": expected["sha256"]})
    return {"manifest": {"path": str(MANIFEST), "bytes": MANIFEST_BYTES, "sha256": MANIFEST_SHA256},
        "pinfile": {"path": str(PINFILE), "bytes": PINFILE_BYTES, "sha256": PINFILE_SHA256},
        "modules": modules}, tuple(bodies)


def _guard_prior_imports(parent):
    namespace = vars(parent)
    _need(not any(name in sys.modules for name in ORDER),
        "native policy module already loaded; mixed class identity refused")
    _need(not any(name.rsplit(".", 1)[1] in namespace for name in ORDER),
        "native policy package attribute already cached")
    _need(not any(getattr(value, "__module__", None) in ORDER for value in namespace.values()),
        "native policy class or function already exported by package")


def load_archived_policy():
    """Execute two exact sealed retained modules under canonical native names."""
    verified, bodies = _verified_archive()
    # Do not reinterpret a prior consumer's existing class objects. This is
    # deliberately not an idempotent loader or a refresh of an imported module.
    parent = importlib.import_module(PACKAGE)
    _guard_prior_imports(parent)
    installed = []
    try:
        for row, raw in zip(verified["modules"], bodies):
            name, source_path = row["module"], row["path"]
            specification = importlib.util.spec_from_file_location(name, source_path)
            module = importlib.util.module_from_spec(specification)
            sys.modules[name] = module
            setattr(parent, name.rsplit(".", 1)[1], module)
            installed.append(name)
            # Execute the already verified bytes, with no second loader read,
            # source refresh, bytecode writing, pool construction, or sampler.
            exec(compile(raw, source_path, "exec"), module.__dict__)
        observed, observed_bodies = _verified_archive()
        _need(observed == verified and observed_bodies == bodies,
            "selected sealed archive changed during process-local bootstrap")
    except BaseException:
        for name in reversed(installed):
            sys.modules.pop(name, None)
            vars(parent).pop(name.rsplit(".", 1)[1], None)
        raise
    return {"schema": "terminal-sealed-retained-native-policy-loaded@1", "profile": PROFILE,
        **verified, "copied_policy_executes_under_canonical_names": True,
        "retained_source_bytes_verified_before_and_after": True,
        "live_original_policy_sources_read": False, "live_original_policy_sources_verified": False,
        "predecessor_live_original_condition_satisfied": False,
        "predecessor_live_original_condition_waived": False,
        "source_refresh_performed": False, "mutable_public_modules_executed": False,
        "shared_scheduler_state_opened": False, "shared_scheduler_state_modified_by_bootstrap": False,
        "host_resource_sampler_called_by_bootstrap": False, "native_pool_created_or_reset": False,
        "complete_transitive_loaded_code_closure": False,
        "execution_scope": "process-local bootstrap; unchanged consumer performs genuine attach-only native admission"}
