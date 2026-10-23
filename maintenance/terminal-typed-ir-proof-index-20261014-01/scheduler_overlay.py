"""Load two exact retained native policy modules before consumer class imports.

This loader changes process-local imports only. It never opens a scheduler state
or imports the mutable external dependency tree as a package.
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
PINFILE = ROOT / "native-policy-overlay-01" / "source-pins.json"
PACKAGE = "ipfs_datasets_py.optimizers.logic_theorem_optimizer"
ORDER = (PACKAGE + ".proof_resource_safety", PACKAGE + ".resource_scheduler")
EXPECTED_SHA256 = (
    "3655923785cb99409171caaba8c523354f03dbe8d82b6deb45a7b46db8394633",
    "7c889bc858ff092e18bd2e97ff5a6407973e226eae33cddc9e5eef1d21f35986",
)


class PolicyOverlayError(ValueError):
    """A copied policy, public source or prior consumer import differs."""


def _read(path: Path, maximum: int = 512 * 1024) -> bytes:
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise PolicyOverlayError("canonical source-only policy path required")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > maximum):
            raise PolicyOverlayError("policy source must be bounded single-link regular file")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    witness = lambda item: (item.st_dev, item.st_ino, item.st_size,
                            item.st_mtime_ns, item.st_ctime_ns)
    if len(raw) > maximum or witness(before) != witness(after):
        raise PolicyOverlayError("policy source changed during bounded acquisition")
    return raw


def _verify_source(record: dict) -> bytes:
    expected = record["sha256"]
    retained = _read(Path(record["retained_source"]))
    public = _read(Path(record["public_source"]))
    if (hashlib.sha256(retained).hexdigest() != expected
            or hashlib.sha256(public).hexdigest() != expected
            or len(retained) != record["bytes"] or retained != public):
        raise PolicyOverlayError("retained or original public policy source drift; refresh refused")
    return retained


def _metadata() -> dict:
    raw = _read(PINFILE, 65536)
    value = json.loads(raw)
    if (type(value) is not dict or value.get("schema") != "terminal-native-policy-source-overlay@1"
            or value.get("overlay_root") != str(PINFILE.parent)
            or value.get("only_selected_two_modules") is not True
            or value.get("pinned_v10_modified") is not False
            or value.get("original_public_sources_modified") is not False
            or value.get("shared_scheduler_state_modified") is not False):
        raise PolicyOverlayError("closed two-module policy provenance required")
    modules = value.get("modules")
    _validate_order(modules)
    public_root = ROOT.parent.parent / "external" / "ipfs_datasets" / "ipfs_datasets_py" / "optimizers" / "logic_theorem_optimizer"
    for record, module, digest in zip(modules, ORDER, EXPECTED_SHA256):
        filename = module.rsplit(".", 1)[1] + ".py"
        if (record.get("sha256") != digest
                or record.get("retained_source") != str(PINFILE.parent / filename)
                or record.get("public_source") != str(public_root / filename)
                or type(record.get("bytes")) is not int
                or not 0 < record["bytes"] <= 512 * 1024
                or record.get("public_source_pre_post_equal") is not True
                or record.get("retained_source_exact") is not True):
            raise PolicyOverlayError("policy source record differs from the frozen named profile")
    return value


def _validate_order(modules) -> None:
    if (type(modules) is not list or len(modules) != 2
            or any(type(record) is not dict for record in modules)
            or tuple(record.get("module") for record in modules) != ORDER):
        raise PolicyOverlayError("collector must load before its matching native scheduler")


def _guard_prior_imports(parent) -> None:
    namespace = vars(parent)
    if any(module in sys.modules for module in ORDER):
        raise PolicyOverlayError("native policy module already loaded; mixed class identity refused")
    if any(module.rsplit(".", 1)[1] in namespace for module in ORDER):
        raise PolicyOverlayError("native policy package attribute already cached")
    if any(getattr(value, "__module__", None) in ORDER for value in namespace.values()):
        raise PolicyOverlayError("native policy class or function already exported by package")


def load_overlay() -> dict:
    """Install exactly the copied matching policy before any native consumers."""
    pin = _metadata()
    bodies = [_verify_source(record) for record in pin["modules"]]
    # Parent initializers are lazy and do not import the policy modules.
    parent = importlib.import_module(PACKAGE)
    _guard_prior_imports(parent)
    installed = []
    try:
        for record, raw in zip(pin["modules"], bodies):
            module_name = record["module"]
            source_path = record["retained_source"]
            specification = importlib.util.spec_from_file_location(module_name, source_path)
            module = importlib.util.module_from_spec(specification)
            sys.modules[module_name] = module
            setattr(parent, module_name.rsplit(".", 1)[1], module)
            installed.append(module_name)
            # Execute the verified bytes, without a second mutable loader read
            # or bytecode-cache writes. Relative imports resolve canonical names.
            exec(compile(raw, source_path, "exec"), module.__dict__)
        for record in pin["modules"]:
            _verify_source(record)
    except BaseException:
        for name in reversed(installed):
            sys.modules.pop(name, None)
            vars(parent).pop(name.rsplit(".", 1)[1], None)
        raise
    return {"schema": "terminal-native-policy-overlay-loaded@1",
            "modules": [{"module": record["module"], "path": record["retained_source"],
                         "sha256": record["sha256"], "bytes": record["bytes"]}
                        for record in pin["modules"]],
            "shared_scheduler_state_opened": False,
            "mutable_public_modules_executed": False,
            "copied_policy_executes_under_canonical_names": True}
