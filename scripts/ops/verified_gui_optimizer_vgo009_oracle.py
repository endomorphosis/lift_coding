#!/usr/bin/env python3
"""Independent, read-only acceptance oracle for the sealed VGO-009 contract."""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib.util
import json
import math
import os
import selectors
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

SCHEMA = "verified-gui-optimizer-vgo009-oracle@1"
MAX_OUTPUT_BYTES = 65_536
TOTAL_DEADLINE_SECONDS = 20.0
WORKER_TIMEOUT_SECONDS = 25.0
ABSTRACT_STEP_LIMIT = 50_000
AUTHORITY_SOURCE_LIMIT = 1_500_000
AUTHORITY_TEST_LIMIT = 1_500_000
PACKAGE_SOURCE_LIMIT = 200_000
ORACLE_STARTED_AT = time.monotonic()
ROOT = Path(__file__).resolve().parents[2]
ACCELERATOR = ROOT / "external" / "ipfs_accelerate"
AUTHORITY_TEST = ACCELERATOR / "test" / "api" / "test_gui_optimizer_authority.py"
PACKAGE_SOURCE = (
    ACCELERATOR / "ipfs_accelerate_py" / "agent_supervisor" / "gui_optimizer" / "__init__.py"
)
AUTHORITY_SOURCE = (
    ACCELERATOR / "ipfs_accelerate_py" / "agent_supervisor" / "gui_optimizer" / "authority.py"
)
CANDIDATE_MODULE_NAME = "_verified_gui_optimizer_vgo009_candidate_authority"
DECLARED_PACKAGE_MODULES = frozenset(
    {
        "artifact_store",
        "authority",
        "benchmark",
        "check_plan",
        "cli",
        "improvement_loop",
        "patch_scope",
        "proposal",
        "run_journal",
        "worktree_executor",
    }
)


def _preload_git_revision(path: Path) -> str:
    """Resolve HEAD through read-only git metadata without spawning a process."""
    marker = path / ".git"
    if marker.is_dir():
        git_dir = marker
    elif marker.is_file():
        line = marker.read_text(encoding="utf-8").strip()
        if not line.startswith("gitdir: "):
            return ""
        candidate = Path(line.removeprefix("gitdir: "))
        git_dir = candidate if candidate.is_absolute() else (path / candidate).resolve()
    else:
        return ""
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head if len(head) == 40 else ""
    reference = head.removeprefix("ref: ")
    common_dir = git_dir
    common_marker = git_dir / "commondir"
    if common_marker.is_file():
        relative = Path(common_marker.read_text(encoding="utf-8").strip())
        common_dir = relative if relative.is_absolute() else (git_dir / relative).resolve()
    for root in (git_dir, common_dir):
        loose = root / reference
        if loose.is_file():
            revision = loose.read_text(encoding="utf-8").strip()
            return revision if len(revision) == 40 else ""
    packed = common_dir / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line.startswith(("#", "^")):
                continue
            fields = line.split(" ", 1)
            if len(fields) == 2 and fields[1] == reference:
                return fields[0] if len(fields[0]) == 40 else ""
    return ""


PARENT_REVISION = _preload_git_revision(ROOT)
ACCELERATOR_REVISION = _preload_git_revision(ACCELERATOR)
AUDIT_VIOLATIONS: list[str] = []
FORBIDDEN_CANDIDATE_IMPORT_ATTEMPTS: list[str] = []
CANDIDATE_EXECUTION_DEPTH = 0
_JSON_DUMPS = json.dumps
_JSON_LOADS = json.loads
_OS_WRITE = os.write
_ISFINITE = math.isfinite


class OracleSideEffect(BaseException):
    """Candidate execution attempted a mutation outside the protected contract."""


def _read_regular_utf8(path: Path, maximum_bytes: int, label: str) -> str:
    """Read one exact, stable regular-file snapshot without following a final symlink."""
    if not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("protected regular-file reads require O_NOFOLLOW")
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise RuntimeError(f"{label} is outside the protected repository root") from exc
    current = ROOT
    for part in relative.parts[:-1]:
        if part in {"", ".", ".."}:
            raise RuntimeError(f"{label} has a noncanonical source path")
        current /= part
        directory = current.lstat()
        if not stat.S_ISDIR(directory.st_mode):
            raise RuntimeError(f"{label} has a non-directory or symlink ancestor")
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum_bytes:
        raise RuntimeError(f"{label} must be a bounded regular file")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        identity_opened = (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        )
        if identity_opened != identity_before or not stat.S_ISREG(opened.st_mode):
            raise RuntimeError(f"{label} changed before its protected read")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, maximum_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum_bytes:
                raise RuntimeError(f"{label} exceeds its source-size bound")
        after = os.fstat(descriptor)
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if identity_after != identity_opened or total != opened.st_size:
            raise RuntimeError(f"{label} changed during its protected read")
    finally:
        os.close(descriptor)
    try:
        return b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{label} is not exact UTF-8 source") from exc


@contextlib.contextmanager
def _candidate_execution_scope():
    global CANDIDATE_EXECUTION_DEPTH
    CANDIDATE_EXECUTION_DEPTH += 1
    try:
        yield
    finally:
        CANDIDATE_EXECUTION_DEPTH -= 1


class _CandidateOutputSink:
    total = 0
    encoding = "utf-8"
    errors = "replace"

    @property
    def buffer(self) -> _CandidateOutputSink:
        return self

    def write(self, value: str | bytes) -> int:
        encoded = value.encode("utf-8", errors="replace") if type(value) is str else bytes(value)
        size = len(encoded)
        type(self).total += size
        if type(self).total > MAX_OUTPUT_BYTES:
            if len(AUDIT_VIOLATIONS) < 20:
                AUDIT_VIOLATIONS.append("candidate_output_exceeded_64KiB")
            raise OracleSideEffect("candidate output exceeded protected bound")
        return len(value)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False


@contextlib.contextmanager
def _candidate_output_scope(sink: _CandidateOutputSink):
    previous = (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__)
    sys.stdout = sink  # type: ignore[assignment]
    sys.stderr = sink  # type: ignore[assignment]
    sys.__stdout__ = sink  # type: ignore[assignment]
    sys.__stderr__ = sink  # type: ignore[assignment]
    try:
        yield
    finally:
        sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__ = previous


def _candidate_audit_hook(event: str, args: tuple[Any, ...]) -> None:
    blocked = False
    if CANDIDATE_EXECUTION_DEPTH and event == "open" and args:
        raw_path = args[0]
        if isinstance(raw_path, (str, bytes, os.PathLike)):
            try:
                opened = Path(os.fsdecode(raw_path)).resolve()
            except (OSError, ValueError):
                opened = None
            if opened == AUTHORITY_TEST.resolve():
                if len(FORBIDDEN_CANDIDATE_IMPORT_ATTEMPTS) < 20:
                    FORBIDDEN_CANDIDATE_IMPORT_ATTEMPTS.append("open_authority_test")
                blocked = True
    if CANDIDATE_EXECUTION_DEPTH and event == "import" and args:
        module_name = str(args[0])
        if "test_gui_optimizer_authority" in module_name or module_name.startswith(
            "ipfs_accelerate_py"
        ):
            if len(FORBIDDEN_CANDIDATE_IMPORT_ATTEMPTS) < 20:
                FORBIDDEN_CANDIDATE_IMPORT_ATTEMPTS.append(f"import:{module_name}")
            blocked = True
    if CANDIDATE_EXECUTION_DEPTH and event == "exec" and args:
        code = args[0]
        filename = str(getattr(code, "co_filename", ""))
        if filename and Path(filename).resolve() == AUTHORITY_TEST.resolve():
            if len(FORBIDDEN_CANDIDATE_IMPORT_ATTEMPTS) < 20:
                FORBIDDEN_CANDIDATE_IMPORT_ATTEMPTS.append("exec_authority_test")
            blocked = True
    if event == "open" and len(args) >= 3:
        mode = args[1]
        flags = args[2]
        if isinstance(mode, str) and any(marker in mode for marker in "wax+"):
            blocked = True
        if isinstance(flags, int) and flags & (
            os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        ):
            blocked = True
    elif event in {
        "os.remove",
        "os.rename",
        "os.mkdir",
        "os.rmdir",
        "os.link",
        "os.symlink",
        "os.chmod",
        "os.chown",
        "os.truncate",
        "os.utime",
        "os.setxattr",
        "os.removexattr",
        "os.chdir",
        "os.putenv",
        "os.unsetenv",
        "os.system",
        "os.fork",
        "os.forkpty",
        "os.kill",
        "os.killpg",
        "os.setgid",
        "os.setgroups",
        "os.setpgid",
        "os.setpgrp",
        "os.setregid",
        "os.setresgid",
        "os.setresuid",
        "os.setreuid",
        "os.setsid",
        "os.setuid",
        "os.spawn",
        "os.posix_spawn",
        "os.posix_spawnp",
        "os.exec",
        "os.unshare",
        "subprocess.Popen",
        "pty.spawn",
        "_thread.start_new_thread",
        "_interpreters.create",
        "ctypes.dlopen",
        "socket.__new__",
        "socket.bind",
        "socket.connect",
        "socket.connect_ex",
        "socket.getaddrinfo",
    }:
        blocked = True
    if blocked:
        if len(AUDIT_VIOLATIONS) < 20:
            AUDIT_VIOLATIONS.append(event)
        raise OracleSideEffect(f"protected oracle blocked candidate side effect: {event}")


class OracleTimeout(BaseException):
    """A candidate-controlled call exceeded the protected oracle deadline."""


def _alarm(_signum: int, _frame: Any) -> None:
    raise OracleTimeout("candidate authority call timed out")


def _remaining_budget(maximum: float) -> float:
    remaining = TOTAL_DEADLINE_SECONDS - (time.monotonic() - ORACLE_STARTED_AT)
    if remaining <= 0:
        raise OracleTimeout("protected oracle total deadline exceeded")
    return min(maximum, remaining)


def _validate_candidate_authority_source() -> str:
    source = _read_regular_utf8(
        AUTHORITY_SOURCE,
        AUTHORITY_SOURCE_LIMIT,
        "candidate authority",
    )
    tree = ast.parse(source, filename=str(AUTHORITY_SOURCE))
    _validate_candidate_authority_tree(tree)
    return source


def _validate_candidate_authority_tree(tree: ast.Module) -> None:
    reserved_runtime_names = {
        "__builtins__",
        "__loader__",
        "__name__",
        "__package__",
        "__spec__",
    }
    protected_builtin_names = {"object", "super", "type"}
    protected_bindings = reserved_runtime_names | protected_builtin_names
    allowed_plain_imports = {"copy", "json", "math", "re"}
    allowed_from_imports = {
        "__future__": {"annotations"},
        "collections.abc": {"Mapping", "Sequence"},
        "dataclasses": {"dataclass", "field"},
        "enum": {"Enum"},
        "math": {"isfinite"},
        "pathlib": {"PurePosixPath"},
        "types": {"MappingProxyType"},
        "typing": {"Any", "Final"},
        "urllib.parse": {"unquote", "unquote_plus"},
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name not in allowed_plain_imports or alias.asname in protected_bindings
                for alias in node.names
            ):
                raise RuntimeError("candidate authority imports an unapproved module")
        elif isinstance(node, ast.ImportFrom):
            allowed_names = allowed_from_imports.get(str(node.module or ""))
            if (
                node.level
                or allowed_names is None
                or any(
                    alias.name not in allowed_names
                    or alias.name == "*"
                    or alias.asname in protected_bindings
                    for alias in node.names
                )
            ):
                raise RuntimeError("candidate authority imports an unapproved symbol")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and (
            node.name in protected_bindings
        ):
            raise RuntimeError("candidate authority shadows runtime identity")
        elif isinstance(node, ast.arg) and node.arg in protected_builtin_names:
            raise RuntimeError("candidate authority shadows protected builtins")
        elif isinstance(node, ast.ExceptHandler) and node.name in protected_bindings:
            raise RuntimeError("candidate authority shadows runtime identity")
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and (node.name in protected_bindings):
            raise RuntimeError("candidate authority shadows runtime identity")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {
                "__import__",
                "breakpoint",
                "compile",
                "delattr",
                "eval",
                "exec",
                "getattr",
                "globals",
                "input",
                "locals",
                "open",
                "setattr",
                "vars",
            }:
                raise RuntimeError("candidate authority uses dynamic runtime access")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {
                "exec_module",
                "find_loader",
                "find_module",
                "find_spec",
                "load_module",
                "module_from_spec",
                "spec_from_file_location",
                "start_new_thread",
            }:
                raise RuntimeError("candidate authority uses dynamic module or thread access")
        elif isinstance(node, ast.Name):
            if node.id == "__builtins__" or (
                node.id in protected_bindings and isinstance(node.ctx, (ast.Store, ast.Del))
            ):
                raise RuntimeError("candidate authority accesses runtime identity dynamically")
        elif isinstance(node, ast.Attribute):
            if not node.attr.startswith("__"):
                continue
            safe_dunder = isinstance(node.ctx, ast.Load) and (
                (
                    node.attr == "__setattr__"
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "object"
                )
                or (
                    node.attr == "__init__"
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "super"
                    and not node.value.args
                    and not node.value.keywords
                )
                or (
                    node.attr == "__name__"
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "type"
                    and len(node.value.args) == 1
                    and not node.value.keywords
                )
            )
            if not safe_dunder:
                raise RuntimeError("candidate authority uses reflective runtime access")


def _load_candidate_authority() -> Any:
    """Load only the owned authority module, without executing package initializers."""
    module_name = CANDIDATE_MODULE_NAME
    previous_handler = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, _remaining_budget(5.0))
    sink = _CandidateOutputSink()
    try:
        source = _validate_candidate_authority_source()
        code = compile(
            source,
            str(AUTHORITY_SOURCE),
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        spec = importlib.util.spec_from_loader(
            module_name, loader=None, origin=str(AUTHORITY_SOURCE)
        )
        if spec is None:
            raise RuntimeError("cannot create candidate authority module specification")
        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(AUTHORITY_SOURCE)
        sys.modules[module_name] = module
        with (
            _candidate_execution_scope(),
            _candidate_output_scope(sink),
        ):
            exec(code, module.__dict__)  # noqa: S102 - exact validated bytes in isolated worker
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous_handler)
    return module


AUDIT_HOOK_INSTALLED = False
AUTHORITY_LOAD_ERROR: dict[str, str] | None = None
auth: Any = None
GUI_AUTHORITY_ERROR_TYPE: type[ValueError] | None = None


def _initialize_candidate_authority() -> None:
    global AUDIT_HOOK_INSTALLED, AUTHORITY_LOAD_ERROR, GUI_AUTHORITY_ERROR_TYPE, auth
    if auth is not None or AUTHORITY_LOAD_ERROR is not None:
        return
    if not AUDIT_HOOK_INSTALLED:
        sys.addaudithook(_candidate_audit_hook)
        AUDIT_HOOK_INSTALLED = True
    try:
        auth = _load_candidate_authority()
    except BaseException as exc:  # candidate import must never crash the oracle
        AUTHORITY_LOAD_ERROR = {"observed": type(exc).__name__}
        return
    error_type = auth.__dict__.get("GuiAuthorityError")
    if not (
        type(error_type) is type
        and error_type.__name__ == "GuiAuthorityError"
        and auth.__name__ == CANDIDATE_MODULE_NAME
        and error_type.__module__ == CANDIDATE_MODULE_NAME
        and error_type.__bases__ == (ValueError,)
    ):
        AUTHORITY_LOAD_ERROR = {"observed": "unsafe_GuiAuthorityError"}
        auth = None
        return
    GUI_AUTHORITY_ERROR_TYPE = error_type


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64

STRING_FIELDS = (
    ("AuthorityEvidence", "kind"),
    ("AuthorityEvidence", "evidence_id"),
    ("AuthorityEvidence", "binds_action_id"),
    ("AuthorityEvidence", "binds_argument_digest"),
    ("AuthorityEvidence", "policy_decision_id"),
    ("AuthorityEvidence", "notes"),
    ("AcceptanceAuthorityRequest", "intended_action_id"),
    ("AcceptanceAuthorityRequest", "intended_argument_digest"),
    ("AcceptanceAuthorityRequest", "browser_policy_outcome"),
    ("AcceptanceAuthorityRequest", "policy_decision_id"),
    ("AcceptanceAuthorityRequest", "confirmation_action_id"),
    ("AcceptanceAuthorityRequest", "confirmation_argument_digest"),
    ("PatchPathClaim", "path"),
)
BOOL_FIELDS = (
    ("AuthorityEvidence", "valid"),
    ("AuthorityEvidence", "policy_fresh"),
    ("AcceptanceAuthorityRequest", "ui_visible"),
    ("AcceptanceAuthorityRequest", "ui_enabled"),
    ("AcceptanceAuthorityRequest", "browser_policy_authoritative_claim"),
    ("AcceptanceAuthorityRequest", "policy_fresh"),
    ("AcceptanceAuthorityRequest", "confirmation_required"),
    ("AcceptanceAuthorityRequest", "confirmation_granted"),
    ("AcceptanceAuthorityRequest", "accessibility_regression"),
    ("AcceptanceAuthorityRequest", "security_regression"),
    ("BrowserHostInput", "fixture_only"),
    ("BrowserHostInput", "uses_production_credentials"),
    ("BrowserHostInput", "uses_production_services"),
    ("BrowserHostInput", "uses_production_mcp_tools"),
    ("BrowserHostInput", "uses_user_or_legal_data"),
    ("PatchPathClaim", "declared"),
)
ARRAY_FIELDS = (
    ("AcceptanceAuthorityRequest", "change_kinds"),
    ("AcceptanceAuthorityRequest", "evidence"),
    ("BrowserHostInput", "selected_host_paths"),
    ("BrowserHostInput", "selected_commands"),
    ("BrowserHostInput", "selected_executables"),
    ("PatchPathClaim", "change_kinds"),
)
DIGEST_FIELDS = (
    ("AcceptanceAuthorityRequest", "intended_argument_digest"),
    ("AcceptanceAuthorityRequest", "confirmation_argument_digest"),
    ("AuthorityEvidence", "binds_argument_digest"),
)
STRING_BAD = {"null": None, "number": 1, "boolean": True, "json_array": [], "json_object": {}}
BOOL_BAD = {"null": None, "number": 1, "string": "true", "json_array": [], "json_object": {}}
ARRAY_BAD = {
    "null": None,
    "string": "x",
    "number": 1,
    "boolean": True,
    "json_object": {},
    "python_tuple": ("x",),
}
PAYLOAD_BAD = {
    "null": None,
    "string": "x",
    "number": 1,
    "boolean": True,
    "json_array": [],
    "non_dict_mapping": __import__("collections").UserDict({"x": 1}),
}
DIGEST_BAD = {
    "uppercase": "sha256:" + "A" * 64,
    "leading_whitespace": " " + DIGEST_A,
    "trailing_whitespace": DIGEST_A + " ",
    "other_algorithm": "blake2b:" + "a" * 64,
    "short": "sha256:" + "a" * 63,
    "long": "sha256:" + "a" * 65,
    "empty": "",
    "arbitrary_equal_noncanonical": "not-canonical",
}
RECURSIVE_IDS = (
    "nested_tuple",
    "nested_non_string_object_key",
    "nested_non_json_container",
    "nested_nan",
    "nested_positive_infinity",
    "nested_negative_infinity",
    "adversarial_dict_subclass",
    "adversarial_list_subclass",
    "adversarial_string_value_subclass",
    "adversarial_string_key_subclass",
)

BASE_AUTH_IDS = (
    "auth:present_null:binds_action_id",
    "auth:present_null:binds_argument_digest",
    "auth:present_null:policy_decision_id_evidence",
    "auth:present_null:notes",
    "auth:present_null:intended_action_id",
    "auth:present_null:intended_argument_digest",
    "auth:present_null:browser_policy_outcome",
    "auth:present_null:policy_decision_id_request",
    "auth:present_null:confirmation_action_id",
    "auth:present_null:confirmation_argument_digest",
    "auth:strict_coercion:string_boolean",
    "auth:unknown_field",
    "auth:caller_policy_unbound",
    "auth:digest_grammar:uppercase",
    "auth:digest_grammar:not_canonical_equal",
    "auth:recursive_json_shape",
    "auth:encoded_selector:host_path_encoded_double",
    "auth:encoded_selector:workingDirectoryEncoded",
    "auth:encoded_selector:fileUriEncoded",
    "auth:encoded_selector:credentialEncoded",
    "auth:value:generic_target_path",
    "auth:value:unc_and_encoded_windows",
    "auth:value:encoded_command",
    "auth:value:encoded_credential_and_aliases",
    "auth:evidence_binding_mismatch",
    "auth:evidence_not_current",
    "auth:scope_and_computed_override",
)
MANDATORY_AUTH_IDS = (
    "auth:policy_configuration:path_scan_not_disableable",
    "auth:policy_configuration:command_scan_not_disableable",
    "auth:policy_configuration:credential_scan_not_disableable",
    "auth:string_subclass_cannot_forge_action_or_digest_binding",
    "auth:string_subclass_cannot_forge_confirmation_binding",
    "auth:string_subclass_cannot_forge_nonempty_evidence_identity",
    "auth:string_subclass_cannot_forge_policy_decision_binding",
    "auth:value:generic_target_relative_traversal",
    "auth:value:windows_drive_relative_path",
    "auth:direct_patch_change_kinds_null",
    "auth:value:cmd_without_exe",
    "auth:value:powershell_exe",
    "auth:value:shell_whitespace_and_metacharacters",
    "auth:key:extended_credential_aliases",
    "auth:direct_claims_sequence_subclass_rejected",
    "auth:patch_allowed_roots_string_subclass_rejected",
    "auth:wire_enum_evidence_kind_rejected",
    "auth:wire_enum_patch_change_kind_rejected",
    "auth:wire_enum_acceptance_change_kind_rejected",
    "auth:wire_model_evidence_entry_rejected",
    "auth:patch_allowed_roots_sequence_subclass_rejected_before_truthiness",
    "auth:wire_evidence_dict_subclass_rejected_before_attribute_access",
)


_TRAP_EVENT_COUNT = 0


class _TrapMeta(type):
    def __setattr__(cls, name: str, value: Any) -> None:
        global _TRAP_EVENT_COUNT
        if name == "touched" and value is True:
            _TRAP_EVENT_COUNT += 1
        super().__setattr__(name, value)


class AdversarialStr(str, metaclass=_TrapMeta):
    touched = False
    fixture_hash_permitted = False

    def __getattribute__(self, name: str) -> Any:
        AdversarialStr.touched = True
        raise RuntimeError(f"string subclass attribute accessed: {name}")

    def __eq__(self, other: object) -> bool:
        AdversarialStr.touched = True
        raise RuntimeError("string subclass equality accessed")

    def __ne__(self, other: object) -> bool:
        AdversarialStr.touched = True
        raise RuntimeError("string subclass inequality accessed")

    def __str__(self) -> str:
        AdversarialStr.touched = True
        raise RuntimeError("string subclass conversion accessed")

    def __bool__(self) -> bool:
        AdversarialStr.touched = True
        raise RuntimeError("string subclass truthiness accessed")

    def __hash__(self) -> int:
        if AdversarialStr.fixture_hash_permitted:
            return str.__hash__(self)
        AdversarialStr.touched = True
        raise RuntimeError("string subclass hash accessed")

    def __repr__(self) -> str:
        AdversarialStr.touched = True
        raise RuntimeError("string subclass representation accessed")

    def __format__(self, _format_spec: str) -> str:
        AdversarialStr.touched = True
        raise RuntimeError("string subclass formatting accessed")

    def strip(self, *_args: Any, **_kwargs: Any) -> str:
        AdversarialStr.touched = True
        raise RuntimeError("string subclass strip accessed")

    def lower(self) -> str:
        AdversarialStr.touched = True
        raise RuntimeError("string subclass lower accessed")


class TrapTuple(tuple, metaclass=_TrapMeta):
    touched = False

    def __getattribute__(self, name: str) -> Any:
        TrapTuple.touched = True
        raise RuntimeError(f"tuple subclass attribute accessed: {name}")

    def __bool__(self) -> bool:
        TrapTuple.touched = True
        raise RuntimeError("tuple subclass truthiness accessed")

    def __iter__(self):
        TrapTuple.touched = True
        raise RuntimeError("tuple subclass iteration accessed")

    def __len__(self) -> int:
        TrapTuple.touched = True
        raise RuntimeError("tuple subclass length accessed")

    def __hash__(self) -> int:
        TrapTuple.touched = True
        raise RuntimeError("tuple subclass hash accessed")

    def __eq__(self, _other: object) -> bool:
        TrapTuple.touched = True
        raise RuntimeError("tuple subclass equality accessed")


class TrapClaims(list, metaclass=_TrapMeta):
    touched = False

    def __getattribute__(self, name: str) -> Any:
        TrapClaims.touched = True
        raise RuntimeError(f"claims subclass attribute accessed: {name}")

    def __bool__(self) -> bool:
        TrapClaims.touched = True
        raise RuntimeError("claims subclass truthiness accessed")

    def __iter__(self):
        TrapClaims.touched = True
        raise RuntimeError("claims subclass iteration accessed")

    def __len__(self) -> int:
        TrapClaims.touched = True
        raise RuntimeError("claims subclass length accessed")

    def __getitem__(self, _key: Any) -> Any:
        TrapClaims.touched = True
        raise RuntimeError("claims subclass indexing accessed")

    def __eq__(self, _other: object) -> bool:
        TrapClaims.touched = True
        raise RuntimeError("claims subclass equality accessed")


class TrapDict(dict, metaclass=_TrapMeta):
    touched = False

    def __getattribute__(self, name: str) -> Any:
        TrapDict.touched = True
        raise RuntimeError(f"dict subclass attribute accessed: {name}")

    def __iter__(self):
        TrapDict.touched = True
        raise RuntimeError("dict subclass iteration accessed")

    def __len__(self) -> int:
        TrapDict.touched = True
        raise RuntimeError("dict subclass length accessed")

    def __bool__(self) -> bool:
        TrapDict.touched = True
        raise RuntimeError("dict subclass truthiness accessed")

    def __getitem__(self, _key: Any) -> Any:
        TrapDict.touched = True
        raise RuntimeError("dict subclass indexing accessed")


class EvidenceDict(dict, metaclass=_TrapMeta):
    touched = False

    def __getattribute__(self, name: str) -> Any:
        EvidenceDict.touched = True
        raise RuntimeError(f"evidence subclass attribute accessed: {name}")

    def __iter__(self):
        EvidenceDict.touched = True
        raise RuntimeError("evidence subclass iteration accessed")

    def __len__(self) -> int:
        EvidenceDict.touched = True
        raise RuntimeError("evidence subclass length accessed")

    def __bool__(self) -> bool:
        EvidenceDict.touched = True
        raise RuntimeError("evidence subclass truthiness accessed")

    def __getitem__(self, _key: Any) -> Any:
        EvidenceDict.touched = True
        raise RuntimeError("evidence subclass indexing accessed")


class TrapList(list, metaclass=_TrapMeta):
    touched = False

    def __getattribute__(self, name: str) -> Any:
        TrapList.touched = True
        raise RuntimeError(f"list subclass attribute accessed: {name}")

    def __iter__(self):
        TrapList.touched = True
        raise RuntimeError("list subclass iteration accessed")

    def __len__(self) -> int:
        TrapList.touched = True
        raise RuntimeError("list subclass length accessed")

    def __bool__(self) -> bool:
        TrapList.touched = True
        raise RuntimeError("list subclass truthiness accessed")

    def __getitem__(self, _key: Any) -> Any:
        TrapList.touched = True
        raise RuntimeError("list subclass indexing accessed")

    def __eq__(self, _other: object) -> bool:
        TrapList.touched = True
        raise RuntimeError("list subclass equality accessed")


class TrapInt(int, metaclass=_TrapMeta):
    touched = False

    def __getattribute__(self, name: str) -> Any:
        TrapInt.touched = True
        raise RuntimeError(f"integer subclass attribute accessed: {name}")

    def __int__(self) -> int:
        TrapInt.touched = True
        raise RuntimeError("integer subclass conversion accessed")

    def __bool__(self) -> bool:
        TrapInt.touched = True
        raise RuntimeError("integer subclass truthiness accessed")

    def __hash__(self) -> int:
        TrapInt.touched = True
        raise RuntimeError("integer subclass hash accessed")

    def __eq__(self, _other: object) -> bool:
        TrapInt.touched = True
        raise RuntimeError("integer subclass equality accessed")

    def __repr__(self) -> str:
        TrapInt.touched = True
        raise RuntimeError("integer subclass representation accessed")


class TrapFloat(float, metaclass=_TrapMeta):
    touched = False

    def __getattribute__(self, name: str) -> Any:
        TrapFloat.touched = True
        raise RuntimeError(f"float subclass attribute accessed: {name}")

    def __float__(self) -> float:
        TrapFloat.touched = True
        raise RuntimeError("float subclass conversion accessed")

    def __bool__(self) -> bool:
        TrapFloat.touched = True
        raise RuntimeError("float subclass truthiness accessed")

    def __hash__(self) -> int:
        TrapFloat.touched = True
        raise RuntimeError("float subclass hash accessed")

    def __eq__(self, _other: object) -> bool:
        TrapFloat.touched = True
        raise RuntimeError("float subclass equality accessed")

    def __repr__(self) -> str:
        TrapFloat.touched = True
        raise RuntimeError("float subclass representation accessed")


@dataclass(frozen=True)
class Probe:
    case_id: str
    invoke: Callable[[], Any]
    expected: str = "gui_error"
    guard: type[Any] | None = None
    reason: str = ""


def _adversarial_string_key_mapping() -> dict[AdversarialStr, int]:
    key = AdversarialStr("x")
    AdversarialStr.fixture_hash_permitted = True
    try:
        return {key: 1}
    finally:
        AdversarialStr.fixture_hash_permitted = False


WIRE_ERROR_REASONS = frozenset(
    {
        "invalid_authority_input",
        "invalid_collection_type",
        "invalid_authority_evidence",
        "unknown_field",
        "noncanonical_argument_digest",
        "empty_argument_digest",
        "evidence_identity_required",
        "path_absolute_or_traversal",
    }
)


def _wire_ids() -> set[str]:
    ids = {
        f"wire:string:{owner}.{field}:{category}"
        for owner, field in STRING_FIELDS
        for category in STRING_BAD
    }
    ids |= {
        f"wire:bool:{owner}.{field}:{category}"
        for owner, field in BOOL_FIELDS
        for category in BOOL_BAD
    }
    ids |= {
        f"wire:array:{owner}.{field}:{category}"
        for owner, field in ARRAY_FIELDS
        for category in ARRAY_BAD
    }
    ids |= {f"wire:payload:BrowserHostInput.payload:{category}" for category in PAYLOAD_BAD}
    ids |= {
        f"wire:digest:{owner}.{field}:{category}"
        for owner, field in DIGEST_FIELDS
        for category in DIGEST_BAD
    }
    ids |= {f"wire:recursive:{category}" for category in RECURSIVE_IDS}
    return ids


def _assignment_value(tree: ast.Module, name: str) -> ast.expr:
    matches: list[tuple[ast.expr, ast.Name]] = []
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            matches.append((node.value, node.targets[0]))
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and node.value is not None
        ):
            matches.append((node.value, node.target))
    if len(matches) != 1:
        raise ValueError(f"manifest declaration {name} must have one direct assignment")
    value, initial_target = matches[0]
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id == name
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and node is not initial_target
        ):
            raise ValueError(f"manifest declaration {name} is rebound")
        if isinstance(node, ast.arg) and node.arg == name:
            raise ValueError(f"manifest declaration {name} is shadowed")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and (
            node.name == name
        ):
            raise ValueError(f"manifest declaration {name} is shadowed")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound = alias.asname or (
                    alias.name.split(".", 1)[0] if isinstance(node, ast.Import) else alias.name
                )
                if bound == name:
                    raise ValueError(f"manifest declaration {name} is shadowed")
        if isinstance(node, ast.ExceptHandler) and node.name == name:
            raise ValueError(f"manifest declaration {name} is shadowed")
        if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name == name:
            raise ValueError(f"manifest declaration {name} is shadowed")
    return value


def _literal_tuple(tree: ast.Module, name: str) -> tuple[Any, ...]:
    value = ast.literal_eval(_assignment_value(tree, name))
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a literal tuple")
    return value


def _literal_dict_keys(tree: ast.Module, name: str) -> tuple[str, ...]:
    value = _assignment_value(tree, name)
    if not isinstance(value, ast.Dict):
        raise ValueError(f"{name} must be a literal dictionary")
    keys: list[str] = []
    for key in value.keys:
        if not isinstance(key, ast.Constant) or type(key.value) is not str:
            raise ValueError(f"{name} has a non-literal key")
        keys.append(key.value)
    return tuple(keys)


def _declaration_is_immutable(tree: ast.Module, name: str) -> bool:
    def rooted(node: ast.AST) -> bool:
        current = node
        while isinstance(current, (ast.Attribute, ast.Subscript)):
            current = current.value
        return isinstance(current, ast.Name) and current.id == name

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(rooted(target) and not isinstance(target, ast.Name) for target in node.targets):
                return False
            if any(
                isinstance(child, ast.Name) and child.id == name and isinstance(child.ctx, ast.Load)
                for child in ast.walk(node.value)
            ):
                return False
        elif isinstance(node, ast.AnnAssign):
            if rooted(node.target) and not isinstance(node.target, ast.Name):
                return False
            if node.value is not None and any(
                isinstance(child, ast.Name) and child.id == name and isinstance(child.ctx, ast.Load)
                for child in ast.walk(node.value)
            ):
                return False
        elif isinstance(node, (ast.AugAssign, ast.Delete)):
            targets = [node.target] if isinstance(node, ast.AugAssign) else node.targets
            if any(rooted(target) for target in targets):
                return False
        elif isinstance(node, ast.NamedExpr) and rooted(node.target):
            return False
        elif isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom)):
            if node.value is not None and any(
                isinstance(child, ast.Name) and child.id == name and isinstance(child.ctx, ast.Load)
                for child in ast.walk(node.value)
            ):
                return False
        elif isinstance(node, ast.Lambda) and any(
            isinstance(child, ast.Name) and child.id == name and isinstance(child.ctx, ast.Load)
            for child in ast.walk(node.body)
        ):
            return False
        elif isinstance(node, ast.Call):
            if rooted(node.func):
                if not (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "items"
                    and not node.args
                    and not node.keywords
                ):
                    return False
            for argument in (*node.args, *[item.value for item in node.keywords]):
                if not any(
                    isinstance(child, ast.Name)
                    and child.id == name
                    and isinstance(child.ctx, ast.Load)
                    for child in ast.walk(argument)
                ):
                    continue
                if not (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "len"
                    and len(node.args) == 1
                    and node.args[0] is argument
                    and not node.keywords
                ):
                    return False
    return True


def _builder_assignment(tree: ast.Module, name: str, builder: str) -> bool:
    matches: list[ast.expr] = []
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            matches.append(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and node.value is not None
        ):
            matches.append(node.value)
    if len(matches) != 1:
        return False
    value = matches[0]
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == builder
        and not value.args
        and not value.keywords
    )


def _function_node(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    rebound = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id == name
            and isinstance(node.ctx, (ast.Store, ast.Del))
        ):
            rebound = True
        elif isinstance(node, ast.arg) and node.arg == name:
            rebound = True
        elif isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            rebound = True
        elif isinstance(node, ast.FunctionDef) and node.name == name and node not in matches:
            rebound = True
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound = alias.asname or (
                    alias.name.split(".", 1)[0] if isinstance(node, ast.Import) else alias.name
                )
                if bound == name:
                    rebound = True
        elif isinstance(node, ast.ExceptHandler) and node.name == name:
            rebound = True
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name == name:
            rebound = True
    if len(matches) != 1 or rebound:
        raise ValueError(f"manifest function {name} must have one stable definition")
    return matches[0]


def _plain_authorization_case_helper(tree: ast.Module, name: str) -> bool:
    function = _function_node(tree, name)
    expected_keys = (
        {"id", "mode", "runner", "reason"}
        if name == "_auth_error"
        else {"id", "mode", "runner", "reason", "allow"}
    )
    positional = [item.arg for item in function.args.args]
    keyword_only = [item.arg for item in function.args.kwonlyargs]
    expected_keyword_only = ["reason"] if name == "_auth_error" else ["reason", "allow"]
    if (
        function.decorator_list
        or len(function.body) != 1
        or function.args.posonlyargs
        or positional != ["case_id", "runner"]
        or keyword_only != expected_keyword_only
        or function.args.vararg is not None
        or function.args.kwarg is not None
        or function.args.defaults
    ):
        return False
    keyword_defaults = function.args.kw_defaults
    if name == "_auth_error" and keyword_defaults != [None]:
        return False
    if name == "_auth_decision" and not (
        len(keyword_defaults) == 2
        and keyword_defaults[0] is None
        and isinstance(keyword_defaults[1], ast.Constant)
        and keyword_defaults[1].value is False
    ):
        return False
    statement = function.body[0]
    if not isinstance(statement, ast.Return) or not isinstance(statement.value, ast.Dict):
        return False
    keys: list[str] = []
    for key in statement.value.keys:
        if not isinstance(key, ast.Constant) or type(key.value) is not str:
            return False
        keys.append(key.value)
    if len(keys) != len(set(keys)) or set(keys) != expected_keys:
        return False
    entries = dict(zip(keys, statement.value.values, strict=True))
    expected_names = {
        "id": "case_id",
        "runner": "runner",
        "reason": "reason",
    }
    if name == "_auth_decision":
        expected_names["allow"] = "allow"
    if any(
        not isinstance(entries[key], ast.Name) or entries[key].id != expected_name
        for key, expected_name in expected_names.items()
    ):
        return False
    mode = entries["mode"]
    expected_mode = "error" if name == "_auth_error" else "decision"
    return isinstance(mode, ast.Constant) and mode.value == expected_mode


def _plain_wire_dispatch_helper(tree: ast.Module) -> bool:
    try:
        function = _function_node(tree, "_apply_wire_case")
    except ValueError:
        return False
    if (
        function.decorator_list
        or function.args.posonlyargs
        or [item.arg for item in function.args.args] != ["owner", "field", "value"]
        or function.args.vararg is not None
        or function.args.kwonlyargs
        or function.args.kwarg is not None
        or function.args.defaults
        or function.args.kw_defaults
    ):
        return False
    protected = ast.parse(
        """
if owner == "AuthorityEvidence":
    _apply_authority_evidence_field(field, value)
elif owner == "AcceptanceAuthorityRequest":
    _apply_acceptance_field(field, value)
elif owner == "BrowserHostInput":
    _apply_browser_field(field, value)
elif owner == "PatchPathClaim":
    _apply_patch_field(field, value)
else:
    raise AssertionError(f"unknown owner {owner}")
"""
    )
    observed = ast.Module(body=function.body, type_ignores=[])
    return ast.dump(observed, include_attributes=False) == ast.dump(
        protected,
        include_attributes=False,
    )


def _canonical_pytest_binding(tree: ast.Module) -> bool:
    allowed_test_from_imports = {
        "__future__": {"annotations"},
        "collections": {"UserDict"},
        "collections.abc": {"Mapping", "Sequence"},
        "enum": {"Enum"},
        "typing": {"Any", "Callable"},
    }
    candidate_import_roots = {
        "ipfs_accelerate_py.agent_supervisor.gui_optimizer",
        "ipfs_accelerate_py.agent_supervisor.gui_optimizer.authority",
    }
    parents = {
        id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }
    imports = [
        (index, alias)
        for index, node in enumerate(tree.body)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "pytest" and alias.asname is None
    ]
    if len(imports) != 1:
        return False
    required_candidate_bindings = {
        "AuthorityReasonCode": 0,
        "GuiAuthorityError": 0,
    }
    for node in tree.body:
        if isinstance(node, ast.Import):
            if any(
                alias.name not in {"math", "pytest"} or alias.asname is not None
                for alias in node.names
            ):
                return False
        elif isinstance(node, ast.ImportFrom):
            module_name = str(node.module or "")
            if module_name in candidate_import_roots:
                if node.level or any(
                    alias.name == "*" or alias.asname is not None for alias in node.names
                ):
                    return False
                for alias in node.names:
                    if alias.name in required_candidate_bindings:
                        required_candidate_bindings[alias.name] += 1
            else:
                allowed_names = allowed_test_from_imports.get(module_name)
                if allowed_names is None or any(
                    alias.name not in allowed_names or alias.asname is not None
                    for alias in node.names
                ):
                    return False
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == "pytest":
                return False
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.rsplit(".", 1)[-1]
                if bound == "pytest" and not (alias.name == "pytest" and alias.asname is None):
                    return False
        if isinstance(node, ast.ImportFrom) and any(
            (alias.asname or alias.name) == "pytest" for alias in node.names
        ):
            return False
    if any(count != 1 for count in required_candidate_bindings.values()):
        return False
    import_index = imports[0][0]
    for node in tree.body[:import_index]:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            continue
        if (
            isinstance(node, ast.Name)
            and node.id == "pytest"
            and isinstance(node.ctx, (ast.Store, ast.Del))
        ):
            return False
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            targets: list[ast.AST] = []
            if isinstance(node, ast.Assign):
                targets.extend(node.targets)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets.append(node.target)
            else:
                targets.extend(node.targets)
            for target in targets:
                root = target
                while isinstance(root, (ast.Attribute, ast.Subscript)):
                    root = root.value
                if isinstance(root, ast.Name) and root.id == "pytest":
                    return False
        if isinstance(node, ast.arg) and node.arg == "pytest":
            return False
        if isinstance(node, ast.ExceptHandler) and node.name == "pytest":
            return False
        if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name == "pytest":
            return False
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "sys" and node.attr == "modules":
                return False
            if node.value.id == "builtins" and node.attr == "len":
                return False
        if isinstance(node, ast.Attribute):
            chain: list[str] = []
            current: ast.AST = node
            while isinstance(current, ast.Attribute):
                chain.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name) and current.id == "pytest":
                access = tuple(reversed(chain))
                if access not in {("mark",), ("mark", "parametrize"), ("raises",)}:
                    return False
        if isinstance(node, ast.Name) and node.id == "pytest" and isinstance(node.ctx, ast.Load):
            if not isinstance(parents.get(id(node)), ast.Attribute):
                return False
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {
                "__import__",
                "compile",
                "delattr",
                "eval",
                "exec",
                "getattr",
                "globals",
                "locals",
                "setattr",
                "vars",
            }:
                return False
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "__setattr__"
        ):
            return False
    protected_bindings = {"AuthorityReasonCode", "GuiAuthorityError"}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id in protected_bindings
            and isinstance(node.ctx, (ast.Store, ast.Del))
        ):
            return False
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and (
            node.name in protected_bindings
        ):
            return False
        if isinstance(node, ast.arg) and node.arg in protected_bindings:
            return False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == "len":
                return False
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            if any(
                isinstance(child, ast.Name)
                and child.id == "len"
                and isinstance(child.ctx, (ast.Store, ast.Del))
                for child in ast.walk(node)
            ):
                return False
        if isinstance(node, (ast.Import, ast.ImportFrom)) and any(
            (alias.asname or alias.name.rsplit(".", 1)[-1]) == "len" for alias in node.names
        ):
            return False
    return True


def _validate_candidate_package_source() -> None:
    source = _read_regular_utf8(
        PACKAGE_SOURCE,
        PACKAGE_SOURCE_LIMIT,
        "candidate package initializer",
    )
    tree = ast.parse(source, filename=str(PACKAGE_SOURCE))
    for index, node in enumerate(tree.body):
        if (
            index == 0
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and type(node.value.value) is str
        ):
            continue
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__" and not node.level:
                if [alias.name for alias in node.names] == ["annotations"]:
                    continue
            if node.module == "typing" and not node.level:
                if [alias.name for alias in node.names] == ["Final"]:
                    continue
            if node.module in DECLARED_PACKAGE_MODULES and node.level == 1:
                if all(alias.name != "*" and alias.asname is None for alias in node.names):
                    continue
            raise ValueError("candidate package initializer imports unapproved code")
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            try:
                value = ast.literal_eval(node.value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "candidate package initializer has executable assignments"
                ) from exc
            if type(value) is str or (
                type(value) is tuple and all(type(item) is str for item in value)
            ):
                continue
        raise ValueError("candidate package initializer is not a pure re-export module")


def _canonical_ids_expression(node: ast.AST, manifest_name: str) -> bool:
    if not isinstance(node, ast.ListComp) or len(node.generators) != 1:
        return False
    generator = node.generators[0]
    if (
        generator.is_async
        or generator.ifs
        or not isinstance(generator.target, ast.Name)
        or generator.target.id != "case"
        or not isinstance(generator.iter, ast.Name)
        or generator.iter.id != manifest_name
    ):
        return False
    element = node.elt
    return (
        isinstance(element, ast.Subscript)
        and isinstance(element.value, ast.Name)
        and element.value.id == "case"
        and isinstance(element.slice, ast.Constant)
        and element.slice.value == "id"
    )


def _protected_manifest_test_body(manifest_name: str) -> str:
    if manifest_name == "WIRE_TYPE_CASES":
        source = """
with pytest.raises(GuiAuthorityError) as exc:
    _apply_wire_case(case["owner"], case["field"], case["value"])
assert exc.value.reason_code in {
    AuthorityReasonCode.INVALID_AUTHORITY_INPUT.value,
    AuthorityReasonCode.INVALID_COLLECTION_TYPE.value,
    AuthorityReasonCode.INVALID_AUTHORITY_EVIDENCE.value,
    AuthorityReasonCode.NONCANONICAL_ARGUMENT_DIGEST.value,
    AuthorityReasonCode.EMPTY_ARGUMENT_DIGEST.value,
    AuthorityReasonCode.EVIDENCE_IDENTITY_REQUIRED.value,
    AuthorityReasonCode.PATH_ABSOLUTE_OR_TRAVERSAL.value,
}
"""
    else:
        source = """
if case["mode"] == "error":
    with pytest.raises(GuiAuthorityError) as exc:
        case["runner"]()
    assert exc.value.reason_code == case["reason"]
    return
decision = case["runner"]()
if case.get("allow"):
    assert decision.allowed
    return
assert not decision.allowed
assert case["reason"] in decision.reason_codes
"""
    module = ast.parse(source)
    return ast.dump(module, annotate_fields=True, include_attributes=False)


PROTECTED_MANIFEST_TEST_BODIES = {
    manifest_name: _protected_manifest_test_body(manifest_name)
    for manifest_name in ("WIRE_TYPE_CASES", "AUTHORIZATION_CASES")
}


def _manifest_test_body_is_exact(node: ast.FunctionDef, manifest_name: str) -> bool:
    module = ast.Module(body=node.body, type_ignores=[])
    return (
        ast.dump(module, annotate_fields=True, include_attributes=False)
        == PROTECTED_MANIFEST_TEST_BODIES[manifest_name]
    )


def _parametrized_manifest_uses(tree: ast.Module, manifest_name: str) -> int:
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "__test__" for target in targets):
                return -1
            if any(
                isinstance(target, ast.Name) and target.id == "pytestmark" for target in targets
            ):
                value = node.value
                if value is not None and any(
                    isinstance(child, ast.Attribute) and child.attr in {"skip", "skipif", "xfail"}
                    for child in ast.walk(value)
                ):
                    return -1
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {
            "pytest_collection_modifyitems",
            "pytest_generate_tests",
        }:
            return -1
    if any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "pytest"
        and node.func.attr in {"skip", "xfail", "importorskip"}
        for node in ast.walk(tree)
    ):
        return -1
    count = 0
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        if any(
            isinstance(child, ast.Attribute) and child.attr in {"skip", "skipif", "xfail"}
            for decorator in node.decorator_list
            for child in ast.walk(decorator)
        ):
            continue
        if any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr in {"skip", "xfail"}
            for child in ast.walk(node)
        ):
            continue
        if len(node.decorator_list) != 1:
            continue
        decorator = node.decorator_list[0]
        if not isinstance(decorator, ast.Call) or len(decorator.args) != 2:
            continue
        if len(decorator.keywords) != 1 or decorator.keywords[0].arg != "ids":
            continue
        if not _canonical_ids_expression(decorator.keywords[0].value, manifest_name):
            continue
        function = decorator.func
        if not (
            isinstance(function, ast.Attribute)
            and function.attr == "parametrize"
            and isinstance(function.value, ast.Attribute)
            and function.value.attr == "mark"
            and isinstance(function.value.value, ast.Name)
            and function.value.value.id == "pytest"
        ):
            continue
        parameter = decorator.args[0]
        cases = decorator.args[1]
        exact_arguments = (
            not node.args.posonlyargs
            and [item.arg for item in node.args.args] == ["case"]
            and node.args.vararg is None
            and not node.args.kwonlyargs
            and node.args.kwarg is None
            and not node.args.defaults
            and not node.args.kw_defaults
        )
        try:
            stable_definition = _function_node(tree, node.name) is node
        except ValueError:
            stable_definition = False
        externally_referenced = any(
            isinstance(child, ast.Name)
            and child.id == node.name
            and isinstance(child.ctx, ast.Load)
            for item in tree.body
            if item is not node
            for child in ast.walk(item)
        )
        disabled = any(
            isinstance(item, (ast.Assign, ast.AnnAssign))
            and any(
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == node.name
                and target.attr == "__test__"
                for target in (item.targets if isinstance(item, ast.Assign) else [item.target])
            )
            for item in tree.body
        )
        if (
            isinstance(parameter, ast.Constant)
            and parameter.value == "case"
            and isinstance(cases, ast.Name)
            and cases.id == manifest_name
            and exact_arguments
            and _manifest_test_body_is_exact(node, manifest_name)
            and stable_definition
            and not externally_referenced
            and not disabled
        ):
            count += 1
    return count


def _manifest_assignment_and_mutation_counts(
    tree: ast.Module,
    manifest_name: str,
) -> tuple[int, int]:
    parents = {
        id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }

    def rooted_at_manifest(node: ast.AST) -> bool:
        current = node
        while isinstance(current, (ast.Subscript, ast.Attribute)):
            current = current.value
        return isinstance(current, ast.Name) and current.id == manifest_name

    initial_targets: set[int] = set()
    assignments = 0
    for statement in tree.body:
        targets: tuple[ast.expr, ...] = ()
        if isinstance(statement, ast.Assign):
            targets = tuple(statement.targets)
        elif isinstance(statement, ast.AnnAssign):
            targets = (statement.target,)
        for target in targets:
            if isinstance(target, ast.Name) and target.id == manifest_name:
                assignments += 1
                initial_targets.add(id(target))

    mutations = 0
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id == manifest_name
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and id(node) not in initial_targets
        ):
            mutations += 1
        elif isinstance(node, ast.Assign):
            if any(
                rooted_at_manifest(target)
                and not (
                    isinstance(target, ast.Name)
                    and target.id == manifest_name
                    and id(target) in initial_targets
                )
                for target in node.targets
            ):
                mutations += 1
        elif isinstance(node, ast.AnnAssign):
            if rooted_at_manifest(node.target) and not (
                isinstance(node.target, ast.Name) and id(node.target) in initial_targets
            ):
                mutations += 1
        elif isinstance(node, ast.AugAssign) and rooted_at_manifest(node.target):
            mutations += 1
        elif isinstance(node, ast.Delete) and any(
            rooted_at_manifest(target) for target in node.targets
        ):
            mutations += 1
        elif isinstance(node, ast.arg) and node.arg == manifest_name:
            mutations += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and (
            node.name == manifest_name
        ):
            mutations += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound = alias.asname or (
                    alias.name.split(".", 1)[0] if isinstance(node, ast.Import) else alias.name
                )
                if bound == manifest_name:
                    mutations += 1
        elif isinstance(node, ast.ExceptHandler) and node.name == manifest_name:
            mutations += 1
        elif isinstance(node, ast.MatchAs) and node.name == manifest_name:
            mutations += 1
        elif isinstance(node, ast.MatchStar) and node.name == manifest_name:
            mutations += 1
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {
                "eval",
                "exec",
                "globals",
                "locals",
                "vars",
                "getattr",
                "setattr",
                "delattr",
            }:
                mutations += 1
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Name)
            and node.id == manifest_name
            and isinstance(node.ctx, ast.Load)
        ):
            continue
        parent = parents.get(id(node))
        if (
            isinstance(parent, ast.Call)
            and isinstance(parent.func, ast.Name)
            and parent.func.id == "len"
            and parent.args == [node]
            and not parent.keywords
        ):
            continue
        ancestor = parent
        allowed_parametrize = False
        while ancestor is not None:
            if isinstance(ancestor, ast.Call):
                allowed_parametrize = (
                    isinstance(ancestor.func, ast.Attribute)
                    and ancestor.func.attr == "parametrize"
                    and isinstance(ancestor.func.value, ast.Attribute)
                    and ancestor.func.value.attr == "mark"
                    and isinstance(ancestor.func.value.value, ast.Name)
                    and ancestor.func.value.value.id == "pytest"
                    and len(ancestor.args) == 2
                    and isinstance(ancestor.args[1], ast.Name)
                    and ancestor.args[1].id == manifest_name
                    and len(ancestor.keywords) == 1
                    and ancestor.keywords[0].arg == "ids"
                    and _canonical_ids_expression(ancestor.keywords[0].value, manifest_name)
                )
                break
            ancestor = parents.get(id(ancestor))
        if not allowed_parametrize:
            mutations += 1
    return assignments, mutations


def _static_builder_environment(tree: ast.Module) -> dict[str, Any]:
    environment: dict[str, Any] = {}
    for node in tree.body:
        name = ""
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                name, value = target.id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name, value = node.target.id, node.value
        if not name or value is None:
            continue
        try:
            environment[name] = ast.literal_eval(value)
            continue
        except (ValueError, TypeError):
            pass
        if isinstance(value, ast.Dict):
            keys: list[str] = []
            for key in value.keys:
                if not isinstance(key, ast.Constant) or type(key.value) is not str:
                    keys = []
                    break
                keys.append(key.value)
            if keys:
                environment[name] = {key: None for key in keys}
    return environment


def _abstract_value(node: ast.AST, environment: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in environment:
            raise ValueError(f"unsupported builder name {node.id}")
        return environment[node.id]
    if isinstance(node, ast.Tuple):
        return tuple(_abstract_value(item, environment) for item in node.elts)
    if isinstance(node, ast.List):
        return [_abstract_value(item, environment) for item in node.elts]
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for item in node.values:
            if isinstance(item, ast.Constant) and type(item.value) is str:
                parts.append(item.value)
            elif isinstance(item, ast.FormattedValue):
                parts.append(str(_abstract_value(item.value, environment)))
            else:
                raise ValueError("unsupported manifest f-string")
        return "".join(parts)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "items"
        and not node.args
        and not node.keywords
    ):
        mapping = _abstract_value(node.func.value, environment)
        if type(mapping) is not dict:
            raise ValueError("manifest .items() target is not a literal dictionary")
        return tuple(mapping.items())
    raise ValueError(f"unsupported manifest expression {type(node).__name__}")


def _bind_abstract_target(
    target: ast.expr,
    value: Any,
    environment: dict[str, Any],
) -> None:
    if isinstance(target, ast.Name):
        if target.id in {"cases", "_auth_error", "_auth_decision"}:
            raise ValueError(f"manifest loop cannot rebind reserved name {target.id}")
        environment[target.id] = value
        return
    if isinstance(target, (ast.Tuple, ast.List)):
        values = tuple(value)
        if len(values) != len(target.elts):
            raise ValueError("manifest loop destructuring length mismatch")
        for child, item in zip(target.elts, values, strict=True):
            _bind_abstract_target(child, item, environment)
        return
    raise ValueError("unsupported manifest loop target")


def _abstract_case_id(
    node: ast.expr,
    environment: dict[str, Any],
    *,
    builder_kind: str,
) -> str:
    if builder_kind == "wire" and isinstance(node, ast.Dict):
        keys: list[str] = []
        for key in node.keys:
            if not isinstance(key, ast.Constant) or type(key.value) is not str:
                raise ValueError("manifest case dictionaries cannot unpack or compute keys")
            keys.append(key.value)
        if len(keys) != len(set(keys)) or keys.count("id") != 1:
            raise ValueError("manifest case dictionary has duplicate or missing keys")
        case_id = _abstract_value(node.values[keys.index("id")], environment)
        if type(case_id) is str:
            return case_id
        raise ValueError("manifest case id is not a string")
    if (
        builder_kind == "authorization"
        and isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"_auth_error", "_auth_decision"}
        and node.args
    ):
        case_id = _abstract_value(node.args[0], environment)
        if type(case_id) is str:
            return case_id
    raise ValueError("unsupported manifest case construction")


def _abstract_builder_ids(tree: ast.Module, function_name: str) -> list[str]:
    """Derive the IDs actually appended by a constrained builder, without exec."""
    function = _function_node(tree, function_name)
    if (
        function.decorator_list
        or function.args.posonlyargs
        or function.args.args
        or function.args.vararg is not None
        or function.args.kwonlyargs
        or function.args.kwarg is not None
        or function.args.defaults
        or function.args.kw_defaults
    ):
        raise ValueError("manifest builder must be an undecorated zero-argument function")
    builder_kind = "wire" if function_name == "_build_wire_type_cases" else "authorization"
    maximum_ids = 221 if builder_kind == "wire" else 49
    global_environment = _static_builder_environment(tree)
    ids: list[str] = []
    returned_cases = False
    cases_initialized = False
    abstract_steps = 0

    def consume_step() -> None:
        nonlocal abstract_steps
        abstract_steps += 1
        if abstract_steps > ABSTRACT_STEP_LIMIT:
            raise ValueError("manifest builder exceeds the abstract execution budget")

    def append_id(case_id: str) -> None:
        if len(ids) >= maximum_ids:
            raise ValueError("manifest builder exceeds the sealed case count")
        ids.append(case_id)

    def validate_nested_definition(
        statement: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        if statement.name in {"cases", "_auth_error", "_auth_decision"}:
            raise ValueError(f"nested manifest helper shadows {statement.name}")
        if statement.decorator_list:
            raise ValueError("nested manifest helpers cannot have decorators")
        evaluated_expressions: list[ast.expr] = [
            *statement.args.defaults,
            *[item for item in statement.args.kw_defaults if item is not None],
        ]
        for argument in (
            *statement.args.posonlyargs,
            *statement.args.args,
            *statement.args.kwonlyargs,
        ):
            if argument.annotation is not None:
                evaluated_expressions.append(argument.annotation)
        if statement.args.vararg and statement.args.vararg.annotation is not None:
            evaluated_expressions.append(statement.args.vararg.annotation)
        if statement.args.kwarg and statement.args.kwarg.annotation is not None:
            evaluated_expressions.append(statement.args.kwarg.annotation)
        if statement.returns is not None:
            evaluated_expressions.append(statement.returns)
        if any(
            isinstance(child, ast.Call) or (isinstance(child, ast.Name) and child.id == "cases")
            for expression in evaluated_expressions
            for child in ast.walk(expression)
        ):
            raise ValueError("nested manifest helper has an executable declaration")
        if any(
            isinstance(child, ast.Name) and child.id == "cases" for child in ast.walk(statement)
        ):
            raise ValueError("nested manifest helper closes over cases")

    def execute(statements: list[ast.stmt], environment: dict[str, Any]) -> bool:
        nonlocal cases_initialized, returned_cases
        for index, statement in enumerate(statements):
            consume_step()
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                validate_nested_definition(statement)
                continue
            if isinstance(statement, ast.For):
                iterable = _abstract_value(statement.iter, environment)
                for item in iterable:
                    consume_step()
                    child_environment = dict(environment)
                    _bind_abstract_target(statement.target, item, child_environment)
                    if execute(statement.body, child_environment):
                        return True
                if statement.orelse:
                    if execute(statement.orelse, dict(environment)):
                        return True
                continue
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                call = statement.value
                is_cases_call = (
                    isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "cases"
                )
                if not is_cases_call:
                    raise ValueError("manifest builder has an unsupported standalone call")
                if (
                    call.func.attr not in {"append", "extend"}
                    or len(call.args) != 1
                    or call.keywords
                ):
                    raise ValueError(f"unsupported cases mutation {call.func.attr}")
                if call.func.attr == "append":
                    append_id(
                        _abstract_case_id(call.args[0], environment, builder_kind=builder_kind)
                    )
                    continue
                if call.func.attr == "extend":
                    values = call.args[0]
                    if not isinstance(values, (ast.List, ast.Tuple)):
                        raise ValueError("manifest extend must use a literal sequence")
                    for item in values.elts:
                        consume_step()
                        append_id(_abstract_case_id(item, environment, builder_kind=builder_kind))
                    continue
            if isinstance(statement, ast.Return):
                if isinstance(statement.value, ast.Name) and statement.value.id == "cases":
                    if index != len(statements) - 1:
                        raise ValueError("manifest builder has statements after return")
                    returned_cases = True
                    return True
                raise ValueError("manifest builder must return cases directly")
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                target: ast.expr | None = None
                value: ast.expr | None = None
                if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                    target, value = statement.targets[0], statement.value
                elif isinstance(statement, ast.AnnAssign):
                    target, value = statement.target, statement.value
                if isinstance(target, ast.Name) and target.id == "cases":
                    if cases_initialized or not isinstance(value, ast.List) or value.elts:
                        raise ValueError("manifest cases must be initialized exactly once as []")
                    cases_initialized = True
                    continue
                raise ValueError("manifest builder has an unsupported assignment")
            if isinstance(statement, ast.Pass):
                continue
            raise ValueError(
                f"unsupported statement in manifest builder: {type(statement).__name__}"
            )
        return False

    execute(function.body, global_environment)
    if not cases_initialized or not returned_cases:
        raise ValueError(f"{function_name} does not return cases")
    return ids


def _read_owned_manifest_declarations_unbounded() -> tuple[
    list[str], list[str], list[dict[str, Any]]
]:
    """Inspect candidate test evidence as inert AST; never execute candidate tests."""
    source = _read_regular_utf8(
        AUTHORITY_TEST,
        AUTHORITY_TEST_LIMIT,
        "authority test evidence",
    )
    tree = ast.parse(source, filename=str(AUTHORITY_TEST))
    failures: list[dict[str, Any]] = []
    if not _canonical_pytest_binding(tree):
        failures.append(
            {
                "check": "pytest_binding",
                "expected": "one stable canonical import pytest binding",
            }
        )

    declared_string_fields = _literal_tuple(tree, "_STRING_FIELDS")
    declared_bool_fields = _literal_tuple(tree, "_BOOL_FIELDS")
    declared_array_fields = _literal_tuple(tree, "_ARRAY_FIELDS")
    declared_digest_fields = _literal_tuple(tree, "_DIGEST_FIELDS")
    declared_string_bad = _literal_dict_keys(tree, "_STRING_TYPE_BAD")
    declared_bool_bad = _literal_dict_keys(tree, "_BOOL_TYPE_BAD")
    declared_array_bad = _literal_dict_keys(tree, "_ARRAY_TYPE_BAD")
    declared_payload_bad = _literal_dict_keys(tree, "_PAYLOAD_TYPE_BAD")
    declared_digest_bad = _literal_dict_keys(tree, "_DIGEST_GRAMMAR_BAD")

    expected_declarations = {
        "_STRING_FIELDS": (declared_string_fields, STRING_FIELDS),
        "_BOOL_FIELDS": (declared_bool_fields, BOOL_FIELDS),
        "_ARRAY_FIELDS": (declared_array_fields, ARRAY_FIELDS),
        "_DIGEST_FIELDS": (declared_digest_fields, DIGEST_FIELDS),
        "_STRING_TYPE_BAD": (declared_string_bad, tuple(STRING_BAD)),
        "_BOOL_TYPE_BAD": (declared_bool_bad, tuple(BOOL_BAD)),
        "_ARRAY_TYPE_BAD": (declared_array_bad, tuple(ARRAY_BAD)),
        "_PAYLOAD_TYPE_BAD": (declared_payload_bad, tuple(PAYLOAD_BAD)),
        "_DIGEST_GRAMMAR_BAD": (declared_digest_bad, tuple(DIGEST_BAD)),
    }
    for label, (observed, expected) in expected_declarations.items():
        if observed != expected:
            failures.append(
                {
                    "check": f"manifest_declaration:{label}",
                    "expected": list(expected),
                    "observed": list(observed),
                }
            )
        if not _declaration_is_immutable(tree, label):
            failures.append(
                {
                    "check": f"manifest_declaration_binding:{label}",
                    "expected": "one immutable, unaliased declaration",
                }
            )

    for helper_name in ("_auth_error", "_auth_decision"):
        if not _plain_authorization_case_helper(tree, helper_name):
            failures.append(
                {
                    "check": f"manifest_helper:{helper_name}",
                    "expected": "plain unmarked case dictionary",
                }
            )
    if not _plain_wire_dispatch_helper(tree):
        failures.append(
            {
                "check": "manifest_helper:_apply_wire_case",
                "expected": "one stable exact wire-case dispatcher",
            }
        )

    wire_ids = _abstract_builder_ids(tree, "_build_wire_type_cases")
    authorization_ids = _abstract_builder_ids(tree, "_build_authorization_cases_exact")
    if len(wire_ids) != len(set(wire_ids)):
        failures.append(
            {
                "check": "WIRE_TYPE_CASES_duplicates",
                "observed": len(wire_ids) - len(set(wire_ids)),
            }
        )
    if len(authorization_ids) != len(set(authorization_ids)):
        failures.append(
            {
                "check": "AUTHORIZATION_CASES_duplicates",
                "observed": len(authorization_ids) - len(set(authorization_ids)),
            }
        )

    if not _builder_assignment(tree, "WIRE_TYPE_CASES", "_build_wire_type_cases"):
        failures.append(
            {
                "check": "WIRE_TYPE_CASES_assignment",
                "expected": "_build_wire_type_cases()",
            }
        )
    if not _builder_assignment(tree, "AUTHORIZATION_CASES", "_build_authorization_cases_exact"):
        failures.append(
            {
                "check": "AUTHORIZATION_CASES_assignment",
                "expected": "_build_authorization_cases_exact()",
            }
        )
    for manifest_name in ("WIRE_TYPE_CASES", "AUTHORIZATION_CASES"):
        assignments, mutations = _manifest_assignment_and_mutation_counts(tree, manifest_name)
        if assignments != 1 or mutations:
            failures.append(
                {
                    "check": f"{manifest_name}_binding",
                    "expected": "one assignment and zero later mutations",
                    "assignments": assignments,
                    "mutations": mutations,
                }
            )
        uses = _parametrized_manifest_uses(tree, manifest_name)
        if uses != 1:
            failures.append(
                {
                    "check": f"{manifest_name}_execution",
                    "expected": "one direct pytest parametrization",
                    "observed": uses,
                }
            )
    return wire_ids, authorization_ids, failures


def _read_owned_manifest_declarations() -> tuple[list[str], list[str], list[dict[str, Any]]]:
    previous_handler = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, _remaining_budget(3.0))
    try:
        _validate_candidate_package_source()
        return _read_owned_manifest_declarations_unbounded()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous_handler)


def _apply_wire(owner: str, field: str, value: Any) -> Any:
    if owner == "AuthorityEvidence":
        evidence = {
            "kind": "contract_verification",
            "valid": True,
            "evidence_id": "e1",
            "binds_action_id": "dispatch_task",
            "binds_argument_digest": DIGEST_A,
        }
        evidence[field] = value
        return auth.GuiAcceptanceAuthority().evaluate(
            {
                "intended_action_id": "dispatch_task",
                "intended_argument_digest": DIGEST_A,
                "evidence": [evidence],
            }
        )
    if owner == "AcceptanceAuthorityRequest":
        request = {"intended_action_id": "dispatch_task", "intended_argument_digest": DIGEST_A}
        request[field] = value
        return auth.GuiAcceptanceAuthority().evaluate(request)
    if owner == "BrowserHostInput":
        request = {"fixture_only": True, "payload": {"view": "queue"}, field: value}
        return auth.GuiHostBoundaryPolicy().evaluate(request)
    claim = {
        "path": "swissknife/web/js/apps/agent-supervisor.js",
        "declared": True,
        "change_kinds": [],
    }
    claim[field] = value
    return auth.GuiPatchAuthority().evaluate_claims([claim])


def _wire_probes() -> list[Probe]:
    probes = [
        Probe(
            f"wire:string:{o}.{f}:{c}",
            lambda o=o, f=f, v=v: _apply_wire(o, f, v),
            reason="invalid_authority_input",
        )
        for o, f in STRING_FIELDS
        for c, v in STRING_BAD.items()
    ]
    probes += [
        Probe(
            f"wire:bool:{o}.{f}:{c}",
            lambda o=o, f=f, v=v: _apply_wire(o, f, v),
            reason="invalid_authority_input",
        )
        for o, f in BOOL_FIELDS
        for c, v in BOOL_BAD.items()
    ]
    probes += [
        Probe(
            f"wire:array:{o}.{f}:{c}",
            lambda o=o, f=f, v=v: _apply_wire(o, f, v),
            reason="invalid_collection_type",
        )
        for o, f in ARRAY_FIELDS
        for c, v in ARRAY_BAD.items()
    ]
    probes += [
        Probe(
            f"wire:payload:BrowserHostInput.payload:{c}",
            lambda v=v: auth.GuiHostBoundaryPolicy().evaluate({"payload": v}),
            reason="invalid_collection_type",
        )
        for c, v in PAYLOAD_BAD.items()
    ]
    probes += [
        Probe(
            f"wire:digest:{o}.{f}:{c}",
            lambda o=o, f=f, v=v: _apply_wire(o, f, v),
            reason=("empty_argument_digest" if c == "empty" else "noncanonical_argument_digest"),
        )
        for o, f in DIGEST_FIELDS
        for c, v in DIGEST_BAD.items()
    ]
    recursive: dict[str, Any] = {
        "nested_tuple": {"x": (1,)},
        "nested_non_string_object_key": {"x": {1: "v"}},
        "nested_non_json_container": {"x": {1}},
        "nested_nan": {"x": float("nan")},
        "nested_positive_infinity": {"x": float("inf")},
        "nested_negative_infinity": {"x": float("-inf")},
        "adversarial_dict_subclass": {"x": TrapDict(y=1)},
        "adversarial_list_subclass": {"x": TrapList([1])},
        "adversarial_string_value_subclass": {"x": AdversarialStr("value")},
        "adversarial_string_key_subclass": _adversarial_string_key_mapping(),
    }
    guards = {
        "adversarial_dict_subclass": TrapDict,
        "adversarial_list_subclass": TrapList,
        "adversarial_string_value_subclass": AdversarialStr,
        "adversarial_string_key_subclass": AdversarialStr,
    }
    probes += [
        Probe(
            f"wire:recursive:{c}",
            lambda v=v: auth.GuiHostBoundaryPolicy().evaluate({"payload": v}),
            guard=guards.get(c),
            reason="invalid_collection_type",
        )
        for c, v in recursive.items()
    ]
    return probes


def _blocked(value: Any) -> bool:
    return hasattr(value, "allowed") and not bool(value.allowed)


def _reason_codes(value: Any) -> tuple[str, ...]:
    raw = getattr(value, "reason_codes", ())
    if type(raw) is not tuple or not all(type(item) is str for item in raw):
        return ()
    return raw


def _base_auth_probes() -> list[Probe]:
    probes: list[Probe] = []
    evidence_names = {
        "binds_action_id": "binds_action_id",
        "binds_argument_digest": "binds_argument_digest",
        "policy_decision_id": "policy_decision_id_evidence",
        "notes": "notes",
    }
    for field, suffix in evidence_names.items():

        def evidence_null(field: str = field) -> Any:
            item = {"kind": "contract_verification", "valid": True, "evidence_id": "e", field: None}
            return auth.GuiAcceptanceAuthority().evaluate({"evidence": [item]})

        probes.append(
            Probe(
                f"auth:present_null:{suffix}",
                evidence_null,
                reason="invalid_authority_input",
            )
        )
    for field, suffix in (
        ("intended_action_id", "intended_action_id"),
        ("intended_argument_digest", "intended_argument_digest"),
        ("browser_policy_outcome", "browser_policy_outcome"),
        ("policy_decision_id", "policy_decision_id_request"),
        ("confirmation_action_id", "confirmation_action_id"),
        ("confirmation_argument_digest", "confirmation_argument_digest"),
    ):
        probes.append(
            Probe(
                f"auth:present_null:{suffix}",
                lambda field=field: auth.GuiAcceptanceAuthority().evaluate({field: None}),
                reason="invalid_authority_input",
            )
        )
    probes.extend(
        (
            Probe(
                "auth:strict_coercion:string_boolean",
                lambda: auth.GuiAcceptanceAuthority().evaluate({"policy_fresh": "true"}),
                reason="invalid_authority_input",
            ),
            Probe(
                "auth:unknown_field",
                lambda: auth.GuiAcceptanceAuthority().evaluate({"forged_allow": True}),
                reason="unknown_field",
            ),
            Probe(
                "auth:caller_policy_unbound",
                lambda: auth.GuiAcceptanceAuthority().evaluate(
                    {
                        "intended_action_id": "dispatch_task",
                        "intended_argument_digest": DIGEST_A,
                        "policy_decision_id": "p",
                        "policy_fresh": True,
                    }
                ),
                "blocked",
                reason="caller_policy_not_authority",
            ),
            Probe(
                "auth:digest_grammar:uppercase",
                lambda: auth.GuiAcceptanceAuthority().evaluate(
                    {"intended_argument_digest": "sha256:" + "A" * 64}
                ),
                reason="noncanonical_argument_digest",
            ),
            Probe(
                "auth:digest_grammar:not_canonical_equal",
                lambda: auth.GuiAcceptanceAuthority().evaluate(
                    {
                        "intended_action_id": "dispatch_task",
                        "intended_argument_digest": "not-canonical",
                        "evidence": [
                            {
                                "kind": "contract_verification",
                                "valid": True,
                                "evidence_id": "e",
                                "binds_action_id": "dispatch_task",
                                "binds_argument_digest": "not-canonical",
                            }
                        ],
                    }
                ),
                reason="noncanonical_argument_digest",
            ),
            Probe(
                "auth:recursive_json_shape",
                lambda: auth.GuiHostBoundaryPolicy().evaluate({"payload": {"x": (1,)}}),
                reason="invalid_collection_type",
            ),
            Probe(
                "auth:encoded_selector:host_path_encoded_double",
                lambda: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {"host_path_encoded": "%252Ftmp%252Fx"}}
                ),
                "blocked",
                reason="browser_host_path_forbidden",
            ),
            Probe(
                "auth:encoded_selector:workingDirectoryEncoded",
                lambda: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {"workingDirectoryEncoded": "/tmp"}}
                ),
                "blocked",
                reason="browser_host_path_forbidden",
            ),
            Probe(
                "auth:encoded_selector:fileUriEncoded",
                lambda: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {"fileUriEncoded": "FILE:///etc/passwd"}}
                ),
                "blocked",
                reason="browser_host_path_forbidden",
            ),
            Probe(
                "auth:encoded_selector:credentialEncoded",
                lambda: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {"credentialEncoded": "secret%3Atoken"}}
                ),
                "blocked",
                reason="browser_credential_forbidden",
            ),
            Probe(
                "auth:value:generic_target_path",
                lambda: auth.GuiHostBoundaryPolicy().evaluate({"payload": {"target": "/home/x"}}),
                "blocked",
                reason="browser_host_path_forbidden",
            ),
            Probe(
                "auth:value:unc_and_encoded_windows",
                lambda: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {"x": "C:%5Csecret", "y": "\\\\server\\share"}}
                ),
                "blocked",
                reason="browser_host_path_forbidden",
            ),
            Probe(
                "auth:value:encoded_command",
                lambda: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {"x": "cmd%2Eexe%20%2Fc"}}
                ),
                "blocked",
                reason="browser_command_forbidden",
            ),
            Probe(
                "auth:value:encoded_credential_and_aliases",
                lambda: auth.GuiHostBoundaryPolicy().evaluate({"payload": {"x": "secret%3Atoken"}}),
                "blocked",
                reason="browser_credential_forbidden",
            ),
            Probe(
                "auth:evidence_binding_mismatch",
                lambda: auth.GuiAcceptanceAuthority().evaluate(
                    {
                        "intended_action_id": "dispatch_task",
                        "intended_argument_digest": DIGEST_A,
                        "evidence": [
                            {
                                "kind": "contract_verification",
                                "valid": True,
                                "evidence_id": "e",
                                "binds_action_id": "other",
                                "binds_argument_digest": DIGEST_A,
                            }
                        ],
                    }
                ),
                "blocked",
                reason="evidence_binding_mismatch",
            ),
            Probe(
                "auth:evidence_not_current",
                lambda: auth.GuiAcceptanceAuthority().evaluate(
                    {
                        "intended_action_id": "dispatch_task",
                        "intended_argument_digest": DIGEST_A,
                        "evidence": [
                            {
                                "kind": "host_policy_reevaluation",
                                "valid": True,
                                "evidence_id": "e",
                                "binds_action_id": "dispatch_task",
                                "binds_argument_digest": DIGEST_A,
                                "policy_fresh": False,
                            }
                        ],
                    }
                ),
                "blocked",
                reason="evidence_not_current",
            ),
            Probe(
                "auth:scope_and_computed_override",
                _scope_and_override,
                "blocked_pair",
                reason="scope_and_computed_override",
            ),
        )
    )
    return probes


def _scope_and_override() -> tuple[Any, Any, Any]:
    scope = auth.GuiAcceptanceAuthority().evaluate(
        {
            "intended_action_id": "dispatch_task",
            "intended_argument_digest": DIGEST_A,
            "evidence": [{"kind": "scope_declaration", "valid": True, "evidence_id": "e"}],
        }
    )
    forged = auth.AuthorityDecision(
        auth.AuthorityVerdict.ALLOW,
        ("allowed",),
        interface="caller",
    )
    computed_host = auth.default_security_authority().evaluate_proposal(
        claims=[{"path": "swissknife/web/js/apps/agent-supervisor.js"}],
        browser_input={"payload": {"host_path": "/tmp/x"}},
        acceptance={
            "intended_action_id": "dispatch_task",
            "intended_argument_digest": DIGEST_A,
            "host_boundary_decision": forged,
            "patch_authority_decision": forged,
        },
    )
    computed_patch = auth.default_security_authority().evaluate_proposal(
        claims=[
            {
                "path": "swissknife/web/js/apps/agent-supervisor.js",
                "change_kinds": ["backend_authorization"],
            }
        ],
        acceptance={
            "intended_action_id": "dispatch_task",
            "intended_argument_digest": DIGEST_A,
            "change_kinds": [],
            "patch_authority_decision": forged,
            "evidence": [
                {
                    "kind": "contract_verification",
                    "valid": True,
                    "evidence_id": "e",
                    "binds_action_id": "dispatch_task",
                    "binds_argument_digest": DIGEST_A,
                }
            ],
        },
    )
    return scope, computed_host, computed_patch


def _mandatory_auth_probes() -> list[Probe]:
    extended = {
        name: "x"
        for name in (
            "accessToken",
            "authToken",
            "clientSecret",
            "privateKey",
            "sessionToken",
            "refreshToken",
            "authorizationHeader",
            "apiToken",
            "oauthToken",
        )
    }
    evidence = {
        "kind": "contract_verification",
        "valid": True,
        "evidence_id": "e",
        "binds_action_id": "dispatch_task",
        "binds_argument_digest": DIGEST_A,
    }
    return [
        Probe(
            MANDATORY_AUTH_IDS[0],
            lambda: auth.GuiHostBoundaryPolicy(forbid_absolute_path_strings=False),
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[1],
            lambda: auth.GuiHostBoundaryPolicy(forbid_command_like_strings=False),
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[2],
            lambda: auth.GuiHostBoundaryPolicy(
                forbid_absolute_path_strings=False, forbid_command_like_strings=False
            ),
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[3],
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {
                    "intended_action_id": AdversarialStr("dispatch_task"),
                    "intended_argument_digest": DIGEST_A,
                    "evidence": [evidence],
                }
            ),
            guard=AdversarialStr,
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[4],
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {
                    "intended_action_id": "dispatch_task",
                    "intended_argument_digest": DIGEST_A,
                    "confirmation_required": True,
                    "confirmation_granted": True,
                    "confirmation_action_id": AdversarialStr("dispatch_task"),
                    "confirmation_argument_digest": DIGEST_A,
                    "evidence": [evidence],
                }
            ),
            guard=AdversarialStr,
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[5],
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {
                    "evidence": [
                        {
                            "kind": "scope_declaration",
                            "valid": True,
                            "evidence_id": AdversarialStr("e"),
                        }
                    ]
                }
            ),
            guard=AdversarialStr,
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[6],
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {"policy_decision_id": AdversarialStr("p"), "policy_fresh": False}
            ),
            guard=AdversarialStr,
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[7],
            lambda: auth.GuiHostBoundaryPolicy().evaluate({"payload": {"target": ".\\..\\secret"}}),
            "blocked",
            reason="browser_host_path_forbidden",
        ),
        Probe(
            MANDATORY_AUTH_IDS[8],
            lambda: auth.GuiHostBoundaryPolicy().evaluate({"payload": {"target": "C:secret"}}),
            "blocked",
            reason="browser_host_path_forbidden",
        ),
        Probe(
            MANDATORY_AUTH_IDS[9],
            lambda: auth.GuiPatchAuthority().evaluate_change_kinds(None),
            reason="invalid_collection_type",
        ),
        Probe(
            MANDATORY_AUTH_IDS[10],
            lambda: auth.GuiHostBoundaryPolicy().evaluate({"payload": {"x": "cmd /c whoami"}}),
            "blocked",
            reason="browser_command_forbidden",
        ),
        Probe(
            MANDATORY_AUTH_IDS[11],
            lambda: auth.GuiHostBoundaryPolicy().evaluate(
                {"payload": {"x": "powershell.exe -c whoami"}}
            ),
            "blocked",
            reason="browser_command_forbidden",
        ),
        Probe(
            MANDATORY_AUTH_IDS[12],
            lambda: auth.GuiHostBoundaryPolicy().evaluate({"payload": {"x": "sh\t-c\tid|whoami"}}),
            "blocked",
            reason="browser_command_forbidden",
        ),
        Probe(
            MANDATORY_AUTH_IDS[13],
            lambda: auth.GuiHostBoundaryPolicy().evaluate({"payload": extended}),
            "blocked",
            reason="browser_credential_forbidden",
        ),
        Probe(
            MANDATORY_AUTH_IDS[14],
            lambda: auth.GuiPatchAuthority().evaluate_claims(
                TrapClaims([{"path": "swissknife/web/js/apps/agent-supervisor.js"}])
            ),
            guard=TrapClaims,
            reason="invalid_collection_type",
        ),
        Probe(
            MANDATORY_AUTH_IDS[15],
            lambda: auth.GuiPatchAuthority(allowed_roots=(AdversarialStr("swissknife/"),)),
            guard=AdversarialStr,
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[16],
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {
                    "evidence": [
                        {
                            "kind": auth.AuthorityEvidenceKind.SCOPE_DECLARATION,
                            "valid": True,
                            "evidence_id": "e",
                        }
                    ]
                }
            ),
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[17],
            lambda: auth.GuiPatchAuthority().evaluate_claims(
                [
                    {
                        "path": "swissknife/web/js/apps/agent-supervisor.js",
                        "change_kinds": [auth.ForbiddenChangeKind.BACKEND_AUTHORIZATION],
                    }
                ]
            ),
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[18],
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {"change_kinds": [auth.ForbiddenChangeKind.BACKEND_AUTHORIZATION]}
            ),
            reason="invalid_authority_input",
        ),
        Probe(
            MANDATORY_AUTH_IDS[19],
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {
                    "evidence": [
                        auth.AuthorityEvidence(
                            kind=auth.AuthorityEvidenceKind.SCOPE_DECLARATION,
                            valid=True,
                            evidence_id="e",
                        )
                    ]
                }
            ),
            reason="invalid_authority_evidence",
        ),
        Probe(
            MANDATORY_AUTH_IDS[20],
            lambda: auth.GuiPatchAuthority(allowed_roots=TrapTuple(("swissknife/",))),
            guard=TrapTuple,
            reason="invalid_collection_type",
        ),
        Probe(
            MANDATORY_AUTH_IDS[21],
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {
                    "intended_action_id": "dispatch_task",
                    "intended_argument_digest": DIGEST_A,
                    "evidence": [EvidenceDict(evidence)],
                }
            ),
            guard=EvidenceDict,
            reason="invalid_authority_evidence",
        ),
    ]


def _bound_request(**updates: Any) -> dict[str, Any]:
    evidence = {
        "kind": "contract_verification",
        "valid": True,
        "evidence_id": "evidence-1",
        "binds_action_id": "dispatch_task",
        "binds_argument_digest": DIGEST_A,
    }
    request: dict[str, Any] = {
        "intended_action_id": "dispatch_task",
        "intended_argument_digest": DIGEST_A,
        "evidence": [evidence],
    }
    request.update(updates)
    return request


def _bound_request_with_evidence(**updates: Any) -> dict[str, Any]:
    request = _bound_request()
    evidence = dict(request["evidence"][0])
    evidence.update(updates)
    request["evidence"] = [evidence]
    return request


def _positive_probes() -> list[Probe]:
    contract = {
        "kind": "contract_verification",
        "valid": True,
        "evidence_id": "contract-1",
        "binds_action_id": "dispatch_task",
        "binds_argument_digest": DIGEST_A,
    }
    human_review = {**contract, "kind": "human_review", "evidence_id": "human-1"}
    return [
        Probe(
            "positive:declared_gui_patch",
            lambda: auth.GuiPatchAuthority().evaluate_claims(
                [
                    {
                        "path": "swissknife/web/js/apps/agent-supervisor.js",
                        "declared": True,
                        "change_kinds": [],
                    }
                ]
            ),
            "allowed",
            reason="allowed",
        ),
        Probe(
            "positive:benign_fixture_browser_payload",
            lambda: auth.GuiHostBoundaryPolicy().evaluate(
                {"fixture_only": True, "payload": {"view": "queue"}}
            ),
            "allowed",
            reason="allowed",
        ),
        Probe(
            "positive:exact_bound_current_contract",
            lambda: auth.GuiAcceptanceAuthority().evaluate(_bound_request()),
            "allowed",
            reason="allowed",
        ),
        Probe(
            "positive:exact_confirmation_binding",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {
                    "intended_action_id": "dispatch_task",
                    "intended_argument_digest": DIGEST_A,
                    "confirmation_required": True,
                    "confirmation_granted": True,
                    "confirmation_action_id": "dispatch_task",
                    "confirmation_argument_digest": DIGEST_A,
                }
            ),
            "allowed",
            reason="allowed",
        ),
        Probe(
            "positive:sensitive_contract_verified",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request(
                    change_kinds=["unverified_action_binding"],
                )
            ),
            "allowed",
            reason="allowed",
        ),
        Probe(
            "positive:always_human_kind_with_bound_review",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                {
                    "intended_action_id": "dispatch_task",
                    "intended_argument_digest": DIGEST_A,
                    "change_kinds": ["backend_authorization"],
                    "evidence": [human_review],
                }
            ),
            "allowed",
            reason="allowed",
        ),
        Probe(
            "positive:safe_facade_proposal",
            lambda: auth.default_security_authority().evaluate_proposal(
                claims=[
                    {
                        "path": "swissknife/web/js/apps/agent-supervisor.js",
                        "declared": True,
                        "change_kinds": [],
                    }
                ],
                browser_input={
                    "fixture_only": True,
                    "payload": {"view": "queue"},
                },
                acceptance=_bound_request(),
            ),
            "allowed",
            reason="allowed",
        ),
    ]


def _supplemental_probes() -> list[Probe]:
    """Expand compound sealed cases so one rejection cannot mask a sibling bypass."""
    probes: list[Probe] = []
    host_values = (
        ("relative_parent", "../etc/passwd"),
        ("relative_nested", "../../etc/passwd"),
        ("relative_windows", ".\\..\\secret"),
        ("relative_encoded", "..%2F..%2Fetc%2Fpasswd"),
        ("drive_relative", "C:secret"),
        ("unc", "\\\\server\\share"),
        ("unc_encoded", "%5C%5Cserver%5Cshare"),
        ("windows_encoded", "C:%5Csecret"),
        ("file_uri", "FILE:///etc/passwd"),
    )
    for label, value in host_values:
        probes.append(
            Probe(
                f"supplemental:path:{label}",
                lambda value=value: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {"target": value}}
                ),
                "blocked",
                reason="browser_host_path_forbidden",
            )
        )
    for key in (
        "hostFilePath",
        "workingDirectory",
        "cwd",
        "fileUri",
        "hostFilesystemPath",
        "host_path_encoded",
    ):
        probes.append(
            Probe(
                f"supplemental:path_key:{key}",
                lambda key=key: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {key: "%252Fetc%252Fpasswd"}}
                ),
                "blocked",
                reason="browser_host_path_forbidden",
            )
        )
    command_values = (
        ("cmd", "cmd /c whoami"),
        ("cmd_exe", "cmd.exe /c whoami"),
        ("powershell", "powershell -Command whoami"),
        ("powershell_exe", "powershell.exe -Command whoami"),
        ("tabs", "sh\t-c\tid"),
        ("pipe", "id|whoami"),
        ("redirect", "id > /tmp/x"),
        ("encoded", "cmd%2Eexe%20%2Fc%20whoami"),
    )
    for label, value in command_values:
        probes.append(
            Probe(
                f"supplemental:command:{label}",
                lambda value=value: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {"hint": value}}
                ),
                "blocked",
                reason="browser_command_forbidden",
            )
        )
    for key in (
        "accessToken",
        "authToken",
        "clientSecret",
        "privateKey",
        "sessionToken",
        "refreshToken",
        "authorizationHeader",
        "apiToken",
        "oauthToken",
    ):
        probes.append(
            Probe(
                f"supplemental:credential_key:{key}",
                lambda key=key: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {key: "fixture-value"}}
                ),
                "blocked",
                reason="browser_credential_forbidden",
            )
        )

    subclass_requests = (
        (
            "request_action",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request(intended_action_id=AdversarialStr("dispatch_task"))
            ),
        ),
        (
            "request_digest",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request(intended_argument_digest=AdversarialStr(DIGEST_A))
            ),
        ),
        (
            "evidence_action",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request_with_evidence(binds_action_id=AdversarialStr("dispatch_task"))
            ),
        ),
        (
            "evidence_digest",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request_with_evidence(binds_argument_digest=AdversarialStr(DIGEST_A))
            ),
        ),
        (
            "confirmation_action",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request(
                    confirmation_required=True,
                    confirmation_granted=True,
                    confirmation_action_id=AdversarialStr("dispatch_task"),
                    confirmation_argument_digest=DIGEST_A,
                )
            ),
        ),
        (
            "confirmation_digest",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request(
                    confirmation_required=True,
                    confirmation_granted=True,
                    confirmation_action_id="dispatch_task",
                    confirmation_argument_digest=AdversarialStr(DIGEST_A),
                )
            ),
        ),
        (
            "evidence_identity",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request_with_evidence(evidence_id=AdversarialStr(""))
            ),
        ),
        (
            "request_policy_id",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request(
                    policy_decision_id=AdversarialStr("policy-1"),
                    policy_fresh=True,
                )
            ),
        ),
        (
            "evidence_policy_id",
            lambda: auth.GuiAcceptanceAuthority().evaluate(
                _bound_request_with_evidence(
                    kind="host_policy_reevaluation",
                    policy_decision_id=AdversarialStr("policy-1"),
                    policy_fresh=True,
                )
            ),
        ),
    )
    probes.extend(
        Probe(
            f"supplemental:string_subclass:{label}",
            invoke,
            guard=AdversarialStr,
            reason="invalid_authority_input",
        )
        for label, invoke in subclass_requests
    )
    probes.extend(
        (
            Probe(
                "supplemental:recursive:int_subclass",
                lambda: auth.GuiHostBoundaryPolicy().evaluate({"payload": {"value": TrapInt(1)}}),
                guard=TrapInt,
                reason="invalid_collection_type",
            ),
            Probe(
                "supplemental:recursive:float_subclass",
                lambda: auth.GuiHostBoundaryPolicy().evaluate(
                    {"payload": {"value": TrapFloat(1.5)}}
                ),
                guard=TrapFloat,
                reason="invalid_collection_type",
            ),
        )
    )
    return probes


def _evaluate_probe_result(probe: Probe, value: Any) -> tuple[bool, str]:
    passed = probe.expected == "blocked" and _blocked(value)
    if probe.expected == "allowed":
        passed = bool(getattr(value, "allowed", False))
        if probe.reason:
            passed = passed and probe.reason in _reason_codes(value)
    if probe.expected == "blocked_pair":
        expected_reasons = (
            "scope_declaration_not_authority",
            "browser_host_path_forbidden",
            "sensitive_change_requires_review",
        )
        passed = (
            type(value) is tuple
            and len(value) == len(expected_reasons)
            and all(
                _blocked(item) and reason in _reason_codes(item)
                for item, reason in zip(value, expected_reasons, strict=True)
            )
        )
    elif passed and probe.reason:
        passed = probe.reason in _reason_codes(value)
    verdict = getattr(
        getattr(value, "verdict", None),
        "value",
        type(value).__name__,
    )
    return passed, str(verdict)[:160]


def _run_probes(probes: list[Probe]) -> tuple[int, list[dict[str, str]]]:
    failures: list[dict[str, str]] = []
    executed = 0
    for probe in probes:
        trap_count_before = _TRAP_EVENT_COUNT
        try:
            call_budget = _remaining_budget(1.0)
        except OracleTimeout:
            failures.append(
                {
                    "case_id": probe.case_id,
                    "observed": "oracle_total_deadline",
                    "expected": probe.expected,
                }
            )
            break
        if probe.guard is not None:
            probe.guard.touched = False
        previous_handler = signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, call_budget)
        sink = _CandidateOutputSink()
        executed += 1
        try:
            with (
                _candidate_execution_scope(),
                _candidate_output_scope(sink),
            ):
                value = probe.invoke()
                passed, observed = _evaluate_probe_result(probe, value)
        except OracleSideEffect:
            failures.append(
                {
                    "case_id": probe.case_id,
                    "observed": "oracle_side_effect_guard",
                    "expected": probe.expected,
                }
            )
            continue
        except OracleTimeout:
            failures.append(
                {
                    "case_id": probe.case_id,
                    "observed": "timeout",
                    "expected": probe.expected,
                }
            )
            continue
        except GUI_AUTHORITY_ERROR_TYPE as exc:
            if probe.guard is not None and _TRAP_EVENT_COUNT > trap_count_before:
                failures.append(
                    {
                        "case_id": probe.case_id,
                        "observed": "GuiAuthorityError_after_subclass_dispatch",
                        "expected": "predispatch_GuiAuthorityError",
                    }
                )
            elif probe.expected != "gui_error":
                failures.append(
                    {
                        "case_id": probe.case_id,
                        "observed": "GuiAuthorityError",
                        "expected": probe.expected,
                    }
                )
            else:
                try:
                    with (
                        _candidate_execution_scope(),
                        _candidate_output_scope(sink),
                    ):
                        observed_reason = str(getattr(exc, "reason_code", ""))[:160]
                except BaseException as classification_error:
                    failures.append(
                        {
                            "case_id": probe.case_id,
                            "observed": type(classification_error).__name__,
                            "expected": "guarded_stable_error_reason",
                        }
                    )
                    continue
                expected_reason = probe.reason
                reason_matches = (
                    observed_reason == expected_reason
                    if expected_reason
                    else observed_reason in WIRE_ERROR_REASONS
                )
                if reason_matches:
                    continue
                failures.append(
                    {
                        "case_id": probe.case_id,
                        "observed": observed_reason,
                        "expected": expected_reason or "stable_fail_closed_input_reason",
                    }
                )
            continue
        except BaseException as exc:
            failures.append(
                {
                    "case_id": probe.case_id,
                    "observed": type(exc).__name__,
                }
            )
            continue
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, previous_handler)
        if passed and probe.guard is not None and _TRAP_EVENT_COUNT > trap_count_before:
            failures.append(
                {
                    "case_id": probe.case_id,
                    "observed": "subclass_dispatch",
                    "expected": "predispatch_rejection",
                }
            )
            continue
        if not passed:
            failures.append(
                {
                    "case_id": probe.case_id,
                    "observed": observed,
                    "expected": probe.expected,
                }
            )
    return executed, failures


def _git_revision(path: Path) -> str:
    if path == ROOT:
        return PARENT_REVISION
    if path == ACCELERATOR:
        return ACCELERATOR_REVISION
    return ""


def _is_exact_json_tree(value: Any) -> bool:
    if value is None or type(value) in {str, bool, int}:
        return True
    if type(value) is float:
        return _ISFINITE(value)
    if type(value) is list:
        return all(_is_exact_json_tree(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _is_exact_json_tree(item) for key, item in value.items())
    return False


def _canonical_tree_failures() -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    original = {
        "items": [1, 2.5, "x", True, None],
        "nested": {"view": "queue"},
    }
    expected = _JSON_LOADS(_JSON_DUMPS(original, allow_nan=False))
    previous_handler = signal.signal(signal.SIGALRM, _alarm)
    try:
        call_budget = _remaining_budget(1.0)
    except OracleTimeout:
        return [
            {
                "check": "canonical_retained_json_tree",
                "observed": "oracle_total_deadline",
            }
        ]
    signal.setitimer(signal.ITIMER_REAL, call_budget)
    sink = _CandidateOutputSink()
    try:
        with (
            _candidate_execution_scope(),
            _candidate_output_scope(sink),
        ):
            model = auth.BrowserHostInput.from_mapping({"payload": original})
            original["items"].append("mutated")
            original["nested"]["view"] = "mutated"
            retained = model.payload
            if not _is_exact_json_tree(retained):
                failures.append(
                    {
                        "check": "canonical_retained_json_tree",
                        "observed": type(retained).__name__,
                        "expected": "recursively exact built-in finite JSON",
                    }
                )
            if type(retained) is dict:
                retained["items"].append("returned-mutation")
                retained["nested"]["view"] = "returned-mutation"
            reread = model.payload
            if reread != expected:
                failures.append(
                    {
                        "check": "canonical_retained_json_tree",
                        "observed": "returned_tree_is_mutable_or_aliased",
                        "expected": expected,
                    }
                )
            encoded = _JSON_DUMPS(
                reread,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            decoded = _JSON_LOADS(encoded)
            if decoded != expected:
                failures.append(
                    {
                        "check": "canonical_retained_json_tree",
                        "observed": "changed_or_aliased",
                        "expected": expected,
                    }
                )
    except BaseException as exc:
        failures.append(
            {
                "check": "canonical_retained_json_tree",
                "observed": type(exc).__name__,
            }
        )
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous_handler)
    return failures


def check_all() -> dict[str, Any]:
    _initialize_candidate_authority()
    if AUTHORITY_LOAD_ERROR is not None:
        return {
            "schema": SCHEMA,
            "passed": False,
            "revisions": {
                "parent": PARENT_REVISION,
                "accelerator": ACCELERATOR_REVISION,
            },
            "counts": {
                "wire_expected": 221,
                "wire_observed": 0,
                "wire_runtime": 0,
                "authorization_expected": 49,
                "authorization_observed": 0,
                "authorization_runtime": 0,
                "positive_runtime": 0,
                "supplemental_runtime": 0,
            },
            "failure_count": 1,
            "failures": [
                {
                    "check": "candidate_authority_import",
                    **AUTHORITY_LOAD_ERROR,
                }
            ],
        }
    expected_wire = _wire_ids()
    expected_auth = set(BASE_AUTH_IDS) | set(MANDATORY_AUTH_IDS)
    failures: list[dict[str, Any]] = []
    observed_wire: list[str] = []
    observed_auth: list[str] = []
    try:
        observed_wire, observed_auth, manifest_failures = _read_owned_manifest_declarations()
        failures.extend(manifest_failures)
        observed_wire_set = set(observed_wire)
        observed_auth_set = set(observed_auth)
        if len(observed_wire) != 221 or observed_wire_set != expected_wire:
            failures.append(
                {
                    "check": "WIRE_TYPE_CASES",
                    "expected": 221,
                    "observed": len(observed_wire),
                    "missing": sorted(expected_wire - observed_wire_set),
                    "extra": sorted(observed_wire_set - expected_wire),
                }
            )
        if len(observed_auth) != 49 or observed_auth_set != expected_auth:
            failures.append(
                {
                    "check": "AUTHORIZATION_CASES",
                    "expected": 49,
                    "observed": len(observed_auth),
                    "missing": sorted(expected_auth - observed_auth_set),
                    "extra": sorted(observed_auth_set - expected_auth),
                }
            )
    except BaseException as exc:
        failures.append(
            {
                "check": "owned_manifest_ast",
                "observed": type(exc).__name__,
                "detail": str(exc)[:200],
            }
        )
    wire_probes = _wire_probes()
    auth_probes = _base_auth_probes() + _mandatory_auth_probes()
    positive_probes = _positive_probes()
    supplemental_probes = _supplemental_probes()
    wire_probe_ids = [probe.case_id for probe in wire_probes]
    auth_probe_ids = [probe.case_id for probe in auth_probes]
    if len(wire_probe_ids) != 221 or set(wire_probe_ids) != expected_wire:
        failures.append(
            {
                "check": "oracle_wire_probe_inventory",
                "expected": 221,
                "observed": len(wire_probe_ids),
            }
        )
    if len(auth_probe_ids) != 49 or set(auth_probe_ids) != expected_auth:
        failures.append(
            {
                "check": "oracle_authorization_probe_inventory",
                "expected": 49,
                "observed": len(auth_probe_ids),
            }
        )
    wire_count, wire_failures = _run_probes(wire_probes)
    auth_count, auth_failures = _run_probes(auth_probes)
    positive_count, positive_failures = _run_probes(positive_probes)
    supplemental_count, supplemental_failures = _run_probes(supplemental_probes)
    failures.extend({"check": "wire_runtime", **item} for item in wire_failures)
    failures.extend({"check": "authorization_runtime", **item} for item in auth_failures)
    failures.extend({"check": "positive_runtime", **item} for item in positive_failures)
    failures.extend({"check": "supplemental_runtime", **item} for item in supplemental_failures)
    failures.extend(_canonical_tree_failures())
    if not (
        GUI_AUTHORITY_ERROR_TYPE is not None
        and auth.__dict__.get("GuiAuthorityError") is GUI_AUTHORITY_ERROR_TYPE
        and type(GUI_AUTHORITY_ERROR_TYPE) is type
        and GUI_AUTHORITY_ERROR_TYPE.__name__ == "GuiAuthorityError"
        and GUI_AUTHORITY_ERROR_TYPE.__module__ == CANDIDATE_MODULE_NAME
        and GUI_AUTHORITY_ERROR_TYPE.__bases__ == (ValueError,)
    ):
        failures.append(
            {
                "check": "candidate_error_binding",
                "observed": "changed_or_unsafe",
                "expected": "stable direct ValueError subclass",
            }
        )
    if AUDIT_VIOLATIONS:
        failures.append(
            {
                "check": "candidate_side_effect_boundary",
                "observed": list(AUDIT_VIOLATIONS),
                "expected": "no writes, process creation, network, or unbounded output",
            }
        )
    if FORBIDDEN_CANDIDATE_IMPORT_ATTEMPTS:
        failures.append(
            {
                "check": "candidate_import_boundary",
                "observed": list(FORBIDDEN_CANDIDATE_IMPORT_ATTEMPTS),
                "expected": "no parent-package or candidate-test import/execution",
            }
        )
    failure_count = len(failures)
    failures = failures[:200]
    return {
        "schema": SCHEMA,
        "passed": not failures,
        "revisions": {"parent": _git_revision(ROOT), "accelerator": _git_revision(ACCELERATOR)},
        "counts": {
            "wire_expected": 221,
            "wire_observed": len(observed_wire),
            "wire_runtime": wire_count,
            "authorization_expected": 49,
            "authorization_observed": len(observed_auth),
            "authorization_runtime": auth_count,
            "positive_runtime": positive_count,
            "supplemental_runtime": supplemental_count,
        },
        "failure_count": failure_count,
        "failures": failures,
    }


def _bounded_result_json(result: dict[str, Any]) -> str:
    encoded = _JSON_DUMPS(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
        result = {
            "schema": SCHEMA,
            "passed": False,
            "revisions": result.get("revisions", {}),
            "counts": result.get("counts", {}),
            "failure_count": 1,
            "failures": [
                {
                    "check": "oracle_output_bound",
                    "observed": "report_exceeded_64KiB",
                    "expected": f"at most {MAX_OUTPUT_BYTES} bytes",
                }
            ],
        }
        encoded = _JSON_DUMPS(
            result,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    return encoded


def _write_report(result: dict[str, Any]) -> None:
    remaining = memoryview((_bounded_result_json(result) + "\n").encode("utf-8"))
    while remaining:
        written = _OS_WRITE(1, remaining)
        if written <= 0:
            raise RuntimeError("failed to emit oracle report")
        remaining = remaining[written:]


def _watchdog_failure(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "passed": False,
        "revisions": {
            "parent": PARENT_REVISION,
            "accelerator": ACCELERATOR_REVISION,
        },
        "counts": {
            "wire_expected": 221,
            "wire_observed": 0,
            "wire_runtime": 0,
            "authorization_expected": 49,
            "authorization_observed": 0,
            "authorization_runtime": 0,
            "positive_runtime": 0,
            "supplemental_runtime": 0,
        },
        "failure_count": 1,
        "failures": [
            {
                "check": "oracle_worker_boundary",
                "observed": reason,
                "expected": "one bounded canonical worker result",
            }
        ],
    }


def _stop_worker(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    try:
        process.wait(timeout=0.5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _worker_protocol_failure(
    stdout: bytes,
    stderr: bytes,
    returncode: int,
) -> dict[str, Any] | None:
    if stderr:
        return _watchdog_failure("worker_stderr")
    try:
        decoded = stdout.decode("utf-8")
        payload = _JSON_LOADS(decoded)
    except (UnicodeDecodeError, TypeError, ValueError, RecursionError, MemoryError):
        return _watchdog_failure("worker_invalid_json")
    if type(payload) is not dict:
        return _watchdog_failure("worker_non_object_json")
    try:
        exact_json = _is_exact_json_tree(payload)
    except (RecursionError, MemoryError):
        exact_json = False
    if not exact_json:
        return _watchdog_failure("worker_invalid_json")
    try:
        canonical = (_bounded_result_json(payload) + "\n").encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError, MemoryError):
        return _watchdog_failure("worker_invalid_json")
    if stdout != canonical:
        return _watchdog_failure("worker_noncanonical_output")
    if set(payload) != {
        "schema",
        "passed",
        "revisions",
        "counts",
        "failure_count",
        "failures",
    }:
        return _watchdog_failure("worker_invalid_envelope")
    passed = payload.get("passed")
    revisions = payload.get("revisions")
    counts = payload.get("counts")
    failure_count = payload.get("failure_count")
    failures = payload.get("failures")
    if (
        type(payload.get("schema")) is not str
        or payload["schema"] != SCHEMA
        or type(passed) is not bool
        or type(revisions) is not dict
        or set(revisions) != {"parent", "accelerator"}
        or any(type(value) is not str for value in revisions.values())
        or revisions
        != {
            "parent": PARENT_REVISION,
            "accelerator": ACCELERATOR_REVISION,
        }
        or type(counts) is not dict
        or set(counts)
        != {
            "wire_expected",
            "wire_observed",
            "wire_runtime",
            "authorization_expected",
            "authorization_observed",
            "authorization_runtime",
            "positive_runtime",
            "supplemental_runtime",
        }
        or any(type(value) is not int or value < 0 for value in counts.values())
        or counts["wire_expected"] != 221
        or counts["authorization_expected"] != 49
        or counts["wire_observed"] > 221
        or counts["wire_runtime"] > 221
        or counts["authorization_observed"] > 49
        or counts["authorization_runtime"] > 49
        or counts["positive_runtime"] > 7
        or counts["supplemental_runtime"] > 43
        or type(failure_count) is not int
        or failure_count < 0
        or type(failures) is not list
        or len(failures) > 200
        or any(type(item) is not dict or not _is_exact_json_tree(item) for item in failures)
        or (failure_count <= 200 and len(failures) != failure_count)
        or (failure_count > 200 and len(failures) != 200)
        or passed != (failure_count == 0)
    ):
        return _watchdog_failure("worker_invalid_envelope")
    if passed and counts != {
        "wire_expected": 221,
        "wire_observed": 221,
        "wire_runtime": 221,
        "authorization_expected": 49,
        "authorization_observed": 49,
        "authorization_runtime": 49,
        "positive_runtime": 7,
        "supplemental_runtime": 43,
    }:
        return _watchdog_failure("worker_invalid_pass_counts")
    expected_returncode = 0 if payload["passed"] else 1
    if returncode != expected_returncode:
        return _watchdog_failure("worker_exit_mismatch")
    return None


def _run_worker_command(
    command: tuple[str, ...],
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    if (
        type(command) is not tuple
        or not command
        or any(type(item) is not str or not item for item in command)
        or type(timeout_seconds) is not float
        or not 0.0 < timeout_seconds <= WORKER_TIMEOUT_SECONDS
    ):
        return _watchdog_failure("worker_configuration_invalid")
    try:
        process = subprocess.Popen(  # noqa: S603 - fixed interpreter and local script
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
        )
    except OSError:
        return _watchdog_failure("worker_spawn_failed")
    if process.stdout is None or process.stderr is None:
        _stop_worker(process)
        return _watchdog_failure("worker_pipe_unavailable")

    selector: selectors.BaseSelector | None = None
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout_seconds
    failure: dict[str, Any] | None = None
    try:
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = _watchdog_failure("worker_timeout")
                _stop_worker(process)
                break
            for key, _events in selector.select(remaining):
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                projected = sum(len(stream) for stream in captured.values()) + len(chunk)
                if projected > MAX_OUTPUT_BYTES:
                    failure = _watchdog_failure("worker_output_limit")
                    _stop_worker(process)
                    break
                captured[key.data].extend(chunk)
            if failure is not None:
                break
        if failure is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = _watchdog_failure("worker_timeout")
                _stop_worker(process)
            else:
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    failure = _watchdog_failure("worker_timeout")
                    _stop_worker(process)
    except (OSError, ValueError):
        failure = _watchdog_failure("worker_pipe_error")
        _stop_worker(process)
    finally:
        if selector is not None:
            selector.close()
        for stream in (process.stdout, process.stderr):
            if not stream.closed:
                stream.close()
    if failure is not None:
        return failure
    stdout = bytes(captured["stdout"])
    stderr = bytes(captured["stderr"])
    protocol_failure = _worker_protocol_failure(stdout, stderr, process.returncode)
    if protocol_failure is not None:
        return protocol_failure
    return _JSON_LOADS(stdout.decode("utf-8"))


def _run_worker() -> dict[str, Any]:
    command = (
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--check-all",
        "--_oracle-worker",
    )
    return _run_worker_command(command, timeout_seconds=WORKER_TIMEOUT_SECONDS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-all", action="store_true", help="run the complete sealed VGO-009 oracle"
    )
    parser.add_argument("--_oracle-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.check_all:
        parser.error("--check-all is required")
    result = check_all() if args._oracle_worker else _run_worker()
    _write_report(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
