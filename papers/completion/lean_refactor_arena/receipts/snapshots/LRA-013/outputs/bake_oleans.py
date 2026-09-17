#!/usr/bin/env python3
"""Bake lake .olean caches and per-tag Putnam Mathlib+Aesop lake projects.

First ``lake build`` is hours. Record **Strata v4.26.0** first, then the other
``(clone, commit, tag)`` units, then one Putnam Mathlib+Aesop lake project per
JSONL Putnam tag. Missing oleans under ``network=deny`` fail closed. Putnam is
never ``Tmp.lean`` and never a guessed PutnamBench GitHub URL.

This module plans, materializes lakefiles, and checks the olean cache. A live
``lake build`` runs only when a tag-pinned elan ``lake`` is installed and
network is allowed. Self-check does not compile, does not start llama-server,
and does not claim Arena scores.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
PUTNAM_README = HERE / "putnam_lake" / "README.md"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
STRATA_SOURCE = "strata"
PUTNAM_SOURCE = "putnambench"
STRATA_FIRST_TAG = "v4.26.0"
STRATA_FIRST_COMMIT = "451e5f047bafa010d178856db76c00029bfa4d7f"
STRATA_URL = "https://github.com/strata-org/Strata"
SOURCE_ORDER = ("strata", "physlib", "cslib", "arklib", "putnambench")
PUTNAM_TAGS: tuple[str, ...] = ("v4.25.0", "v4.26.0", "v4.27.0")
MATHLIB_GIT = "https://github.com/leanprover-community/mathlib4.git"
AESOP_GIT = "https://github.com/leanprover-community/aesop.git"
PUTNAM_PACKAGE = "putnam_lake"
PUTNAM_LIB = "Putnam"
PUTNAM_MODULE = "Putnam.Candidate"
PUTNAM_CANDIDATE_RELPATH = "Putnam/Candidate.lean"
PUTNAM_ROOT_RELPATH = "Putnam.lean"
FORBIDDEN_PUTNAM_BASENAME = "Tmp.lean"
MEASUREMENT_MAX_HEARTBEATS = 400000
ELAN_TOOLCHAIN_DIRNAME_PREFIX = "leanprover--lean4---"
KERNEL_COMMAND_TEMPLATE = "{lake} env {lean} --json {source_file}"
BAKE_ARGV_TEMPLATE = "{lake} build"
DEFAULT_LAKE_TIMEOUT_SECONDS = 28800
NETWORK_DENY_VALUES = frozenset({"deny", "offline", "none", "no", "0", "false", "off"})
STATE_RELATIVE = Path("ipfs_accelerate_py") / "vericodegen-2026" / "lean_refactor_arena"
GIT_BIN = Path("/usr/bin/git")

FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
        "shutil",
    }
)
FORBIDDEN_CALLS = frozenset({"which", "find_executable", "LOCK_EX"})
FORBIDDEN_SCORE_NAMES = frozenset(
    {
        "arena_score",
        "arena_score_tokens",
        "arena_score_elab",
        "official_track2_score",
        "token_savings",
    }
)
FORBIDDEN_PUTNAM_URL_NEEDLES = (
    "github.com/trishullab/PutnamBench",
    "github.com/trishullab/putnambench",
    "github.com/openai/putnam-bench",
)


class BakeError(RuntimeError):
    """Fail-closed olean-bake or Putnam lake-project error."""


class OleanCacheMissing(BakeError):
    """Required .olean cache is absent while network is denied."""


class BakeToolchainMissing(BakeError):
    """Tag-pinned elan lake/lean is not installed. Not a PATH fallback."""


@dataclass(frozen=True)
class VersionPin:
    lean_tag: str
    git_commit: str

    def to_dict(self) -> dict[str, str]:
        return {"lean_tag": self.lean_tag, "git_commit": self.git_commit}


@dataclass(frozen=True)
class PutnamPin:
    lean_tag: str
    mathlib_git: str
    mathlib_rev: str
    aesop_git: str
    aesop_rev: str
    jsonl_version_pin: str
    package: str = PUTNAM_PACKAGE
    lib: str = PUTNAM_LIB
    module: str = PUTNAM_MODULE
    candidate_relpath: str = PUTNAM_CANDIDATE_RELPATH
    putnambench_url: None = None
    tmp_lean: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BakeJob:
    kind: str
    source: str
    lean_tag: str
    git_commit: str
    url: str
    cache_key: str
    phase: int
    record_names: tuple[str, ...]
    file_paths: tuple[str, ...]
    module: str
    mathlib_rev: str = ""
    aesop_rev: str = ""
    lakefile_required: bool = False
    putnambench_url: None = None
    arena_score: None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["record_names"] = list(self.record_names)
        payload["file_paths"] = list(self.file_paths)
        payload["arena_score"] = None
        return payload


@dataclass
class BakePlan:
    jobs: list[BakeJob] = field(default_factory=list)
    frozen_warmup_sha256: str = FROZEN_WARMUP_SHA256
    jsonl_bytes: int = 0
    n_records: int = 0
    arena_score: None = None

    @property
    def first_job(self) -> BakeJob:
        if not self.jobs:
            raise BakeError("bake plan is empty")
        return self.jobs[0]

    def to_dict(self) -> dict[str, Any]:
        first = self.first_job
        return {
            "arena_score": None,
            "bake_argv_template": BAKE_ARGV_TEMPLATE,
            "first_is_strata_v4_26": (
                first.kind == "repo"
                and first.source == STRATA_SOURCE
                and first.lean_tag == STRATA_FIRST_TAG
                and first.git_commit == STRATA_FIRST_COMMIT
            ),
            "first_job": first.to_dict(),
            "frozen_warmup_sha256": self.frozen_warmup_sha256,
            "jsonl_bytes": self.jsonl_bytes,
            "jobs": [job.to_dict() for job in self.jobs],
            "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
            "measurement_maxHeartbeats": MEASUREMENT_MAX_HEARTBEATS,
            "n_jobs": len(self.jobs),
            "n_putnam_jobs": sum(1 for job in self.jobs if job.kind == "putnam"),
            "n_records": self.n_records,
            "n_repo_jobs": sum(1 for job in self.jobs if job.kind == "repo"),
            "putnam_module": PUTNAM_MODULE,
            "putnam_not_tmp_lean": True,
            "putnam_tags": list(PUTNAM_TAGS),
            "score": None,
            "strata_first_tag": STRATA_FIRST_TAG,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def default_elan_home() -> Path:
    raw = os.environ.get("ELAN_HOME")
    if raw is not None and str(raw).strip():
        return Path(str(raw)).expanduser()
    return Path.home() / ".elan"


def default_state_root() -> Path:
    raw = os.environ.get("LRA_STATE_ROOT")
    if raw is not None and str(raw).strip():
        return Path(str(raw)).expanduser()
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg is not None and str(xdg).strip():
        return Path(xdg) / STATE_RELATIVE
    return Path.home() / ".local" / "state" / STATE_RELATIVE


def network_mode(value: Optional[str] = None) -> str:
    raw = value if value is not None else os.environ.get("LRA_NETWORK")
    if raw is None or not str(raw).strip():
        raw = os.environ.get("IPFS_ACCELERATE_LRA_NETWORK", "allow")
    text = str(raw).strip().lower()
    if text in NETWORK_DENY_VALUES:
        return "deny"
    return "allow"


def normalize_lean_tag(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BakeError("lean tag must be a nonempty string")
    text = value.strip()
    if text.startswith(ELAN_TOOLCHAIN_DIRNAME_PREFIX):
        text = text[len(ELAN_TOOLCHAIN_DIRNAME_PREFIX) :]
    elif ":" in text:
        text = text.rsplit(":", 1)[-1]
    text = text.strip()
    if not text:
        raise BakeError(f"lean tag {value!r} normalized to empty")
    return text


def elan_toolchain_dirname(lean_tag: str) -> str:
    return f"{ELAN_TOOLCHAIN_DIRNAME_PREFIX}{normalize_lean_tag(lean_tag)}"


def tag_pinned_paths(lean_tag: str, *, elan_home: Optional[Path] = None) -> dict[str, Any]:
    """Return elan ``lean``/``lake`` paths. Never searches PATH."""

    home = Path(elan_home) if elan_home is not None else default_elan_home()
    tag = normalize_lean_tag(lean_tag)
    toolchain_dir = home / "toolchains" / elan_toolchain_dirname(tag)
    lean_path = toolchain_dir / "bin" / "lean"
    lake_path = toolchain_dir / "bin" / "lake"
    return {
        "lean_tag": tag,
        "elan_home": str(home),
        "toolchain_dir": str(toolchain_dir),
        "lean_path": str(lean_path),
        "lake_path": str(lake_path),
        "lean_installed": _is_executable(lean_path),
        "lake_installed": _is_executable(lake_path),
        "installed": _is_executable(lean_path) and _is_executable(lake_path),
        "executable_paths": {"lean": str(lean_path), "lake": str(lake_path)},
    }


def _is_executable(path: Path) -> bool:
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode) and bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def iter_version_pins(version_info: Any) -> list[VersionPin]:
    if not isinstance(version_info, list):
        raise BakeError("version_info must be a list of {lean_tag: git_commit} maps")
    pins: list[VersionPin] = []
    for index, item in enumerate(version_info):
        if isinstance(item, dict) and item:
            for tag, commit in item.items():
                if not isinstance(tag, str) or not tag.strip():
                    raise BakeError(f"version_info[{index}] has an empty lean tag")
                if commit is None:
                    commit_text = ""
                elif isinstance(commit, str):
                    commit_text = commit.strip()
                else:
                    raise BakeError(
                        f"version_info[{index}] git commit must be a string, not {type(commit).__name__}"
                    )
                pins.append(VersionPin(lean_tag=normalize_lean_tag(tag), git_commit=commit_text))
            continue
        raise BakeError(f"version_info[{index}] is not a {{lean_tag: git_commit}} map")
    if not pins:
        raise BakeError("version_info is empty")
    return pins


def _url_cache_key(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or "no-host"
    path = parsed.path.strip("/") or "unnamed"
    return f"{host}/{path}"


def putnam_pin(lean_tag: str, *, jsonl_version_pin: str = "") -> PutnamPin:
    tag = normalize_lean_tag(lean_tag)
    if tag not in PUTNAM_TAGS:
        raise BakeError(f"Putnam lake project is not defined for lean tag {tag}")
    return PutnamPin(
        lean_tag=tag,
        mathlib_git=MATHLIB_GIT,
        mathlib_rev=tag,
        aesop_git=AESOP_GIT,
        aesop_rev=tag,
        jsonl_version_pin=jsonl_version_pin,
    )


def render_lean_toolchain(lean_tag: str) -> str:
    return f"leanprover/lean4:{normalize_lean_tag(lean_tag)}\n"


def render_lakefile(lean_tag: str) -> str:
    """Per-tag Mathlib+Aesop lakefile. Candidate module is Putnam.Candidate, not Tmp.lean."""

    pin = putnam_pin(lean_tag)
    return (
        "import Lake\n"
        "open Lake DSL\n"
        "\n"
        f"package «{pin.package}» where\n"
        f"  moreLeanArgs := #[\"-DmaxHeartbeats={MEASUREMENT_MAX_HEARTBEATS}\"]\n"
        f"  moreServerArgs := #[\"-DmaxHeartbeats={MEASUREMENT_MAX_HEARTBEATS}\"]\n"
        "\n"
        "require mathlib from git\n"
        f'  "{pin.mathlib_git}" @ "{pin.mathlib_rev}"\n'
        "\n"
        "require aesop from git\n"
        f'  "{pin.aesop_git}" @ "{pin.aesop_rev}"\n'
        "\n"
        "@[default_target]\n"
        f"lean_lib «{pin.lib}» where\n"
        f"  globs := #[.submodules `{pin.lib}]\n"
    )


def render_putnam_root() -> str:
    return f"import {PUTNAM_MODULE}\n"


def render_putnam_candidate_stub() -> str:
    return (
        "/-\n"
        "  LRA Putnam candidate module.\n"
        "\n"
        "  The compile worker overwrites this file with header + statement +\n"
        "  tactic block via splice.lake_candidate_source. This is a module in\n"
        "  the per-tag Mathlib+Aesop lake project, not Tmp.lean, and not\n"
        "  `lake env lean Tmp.lean` without a lakefile.\n"
        "-/\n"
        "\n"
        "theorem lra_putnam_candidate_placeholder : True := by\n"
        "  trivial\n"
    )


def putnam_project_files(lean_tag: str, *, jsonl_version_pin: str = "") -> dict[str, str]:
    pin = putnam_pin(lean_tag, jsonl_version_pin=jsonl_version_pin)
    pins_json = json.dumps(pin.to_dict(), indent=2, sort_keys=True) + "\n"
    return {
        "lakefile.lean": render_lakefile(pin.lean_tag),
        "lean-toolchain": render_lean_toolchain(pin.lean_tag),
        PUTNAM_ROOT_RELPATH: render_putnam_root(),
        PUTNAM_CANDIDATE_RELPATH: render_putnam_candidate_stub(),
        "pins.json": pins_json,
    }


def materialize_putnam_project(
    lean_tag: str,
    dest: Path,
    *,
    jsonl_version_pin: str = "",
) -> dict[str, str]:
    files = putnam_project_files(lean_tag, jsonl_version_pin=jsonl_version_pin)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for relpath, text in files.items():
        path = dest / relpath
        if path.name == FORBIDDEN_PUTNAM_BASENAME:
            raise BakeError("refusing to materialize Tmp.lean")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    forbidden = dest / FORBIDDEN_PUTNAM_BASENAME
    if forbidden.exists():
        raise BakeError("Putnam lake project must not contain Tmp.lean")
    return {relpath: str(dest / relpath) for relpath in files}


def collect_bake_jobs(records: Sequence[Mapping[str, Any]]) -> list[BakeJob]:
    if len(records) != WARMUP_N:
        raise BakeError(f"warmup JSONL must contain {WARMUP_N} records, got {len(records)}")
    repo_groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    putnam_groups: dict[str, dict[str, Any]] = {}
    for record in records:
        name = str(record.get("name") or "")
        source = str(record.get("source") or "")
        if source not in SOURCE_ORDER:
            raise BakeError(f"{name}: unknown source {source!r}")
        url = record.get("url") or ""
        file_path = record.get("file_path") or ""
        if not isinstance(url, str) or not isinstance(file_path, str):
            raise BakeError(f"{name}: url and file_path must be strings")
        pins = iter_version_pins(record.get("version_info"))
        if source == PUTNAM_SOURCE:
            if url.strip() or file_path.strip():
                raise BakeError(
                    f"{name}: Putnam url/file_path must be empty; do not guess a PutnamBench GitHub URL"
                )
            header = record.get("header") or ""
            if not isinstance(header, str) or "import Mathlib" not in header or "import Aesop" not in header:
                raise BakeError(f"{name}: Putnam header must import Mathlib and Aesop")
            for pin in pins:
                group = putnam_groups.setdefault(
                    pin.lean_tag,
                    {"names": [], "commit": pin.git_commit},
                )
                if group["commit"] != pin.git_commit:
                    raise BakeError(
                        f"Putnam tag {pin.lean_tag} has disagreeing JSONL pins "
                        f"{group['commit']!r} vs {pin.git_commit!r}"
                    )
                group["names"].append(name)
            continue
        if not url.strip():
            raise BakeError(f"{name}: repo record is missing url")
        if not file_path.strip():
            raise BakeError(f"{name}: repo record is missing file_path")
        for pin in pins:
            key = (source, url, pin.git_commit, pin.lean_tag)
            group = repo_groups.setdefault(
                key,
                {"names": [], "files": []},
            )
            group["names"].append(name)
            if file_path not in group["files"]:
                group["files"].append(file_path)

    jobs: list[BakeJob] = []
    strata_first_keys = [
        key
        for key in repo_groups
        if key[0] == STRATA_SOURCE and key[3] == STRATA_FIRST_TAG
    ]
    strata_first_keys.sort(key=lambda key: (key[1], key[2], key[3]))
    remaining_keys = [key for key in repo_groups if key not in set(strata_first_keys)]
    remaining_keys.sort(key=lambda key: (SOURCE_ORDER.index(key[0]), key[1], key[3], key[2]))

    def repo_job(key: tuple[str, str, str, str], phase: int) -> BakeJob:
        source, url, commit, tag = key
        group = repo_groups[key]
        return BakeJob(
            kind="repo",
            source=source,
            lean_tag=tag,
            git_commit=commit,
            url=url,
            cache_key=f"repo/{_url_cache_key(url)}/{commit}/{tag}",
            phase=phase,
            record_names=tuple(group["names"]),
            file_paths=tuple(group["files"]),
            module=group["files"][0],
            lakefile_required=True,
        )

    for key in strata_first_keys:
        jobs.append(repo_job(key, phase=0))
    for key in remaining_keys:
        jobs.append(repo_job(key, phase=1))
    for tag in PUTNAM_TAGS:
        if tag not in putnam_groups:
            raise BakeError(f"missing Putnam JSONL tag {tag}")
        group = putnam_groups[tag]
        pin = putnam_pin(tag, jsonl_version_pin=group["commit"])
        jobs.append(
            BakeJob(
                kind="putnam",
                source=PUTNAM_SOURCE,
                lean_tag=tag,
                git_commit=group["commit"],
                url="",
                cache_key=f"putnam/{tag}",
                phase=2,
                record_names=tuple(group["names"]),
                file_paths=(PUTNAM_CANDIDATE_RELPATH,),
                module=PUTNAM_MODULE,
                mathlib_rev=pin.mathlib_rev,
                aesop_rev=pin.aesop_rev,
                lakefile_required=True,
                putnambench_url=None,
            )
        )
    extra_putnam = sorted(set(putnam_groups) - set(PUTNAM_TAGS))
    if extra_putnam:
        raise BakeError(f"unexpected Putnam tags {extra_putnam}")
    if not jobs or jobs[0].source != STRATA_SOURCE or jobs[0].lean_tag != STRATA_FIRST_TAG:
        raise BakeError("bake plan must record Strata v4.26.0 first")
    return jobs


def plan_bake(path: Optional[Path] = None) -> BakePlan:
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    jobs = collect_bake_jobs(records)
    return BakePlan(
        jobs=jobs,
        frozen_warmup_sha256=digest,
        jsonl_bytes=len(raw),
        n_records=len(records),
        arena_score=None,
    )


def job_cache_dir(job: BakeJob, state_root: Optional[Path] = None) -> Path:
    root = Path(state_root) if state_root is not None else default_state_root()
    return root / "oleans" / job.cache_key


def putnam_project_dir(job: BakeJob, state_root: Optional[Path] = None) -> Path:
    if job.kind != "putnam":
        raise BakeError("putnam_project_dir is only defined for Putnam jobs")
    root = Path(state_root) if state_root is not None else default_state_root()
    return root / "putnam_lake" / job.lean_tag


def cache_marker_path(cache_dir: Path) -> Path:
    return cache_dir / "BAKED"


def olean_paths(cache_dir: Path) -> list[Path]:
    if not cache_dir.is_dir():
        return []
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(cache_dir):
        dirnames.sort()
        for name in sorted(filenames):
            if name.endswith(".olean"):
                found.append(Path(dirpath) / name)
    return found


def cache_present(job: BakeJob, state_root: Optional[Path] = None) -> bool:
    cache_dir = job_cache_dir(job, state_root)
    return cache_marker_path(cache_dir).is_file() and bool(olean_paths(cache_dir))


def plant_synthetic_cache(job: BakeJob, state_root: Path, *, n_oleans: int = 1) -> Path:
    """Write a dummy olean cache. Not a live lake bake."""

    cache_dir = job_cache_dir(job, state_root)
    build_dir = cache_dir / ".lake" / "build" / "lib"
    build_dir.mkdir(parents=True, exist_ok=True)
    for index in range(n_oleans):
        (build_dir / f"LraBake{index}.olean").write_bytes(b"LRA-013-synthetic-olean\n")
    receipt = {
        "schema": "lra-olean-bake/v1",
        "cache_key": job.cache_key,
        "kind": job.kind,
        "lean_tag": job.lean_tag,
        "synthetic": True,
        "lake_build_executed": False,
        "arena_score": None,
    }
    (cache_dir / "bake-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    cache_marker_path(cache_dir).write_text("synthetic\n", encoding="utf-8")
    return cache_dir


def require_cache(
    job: BakeJob,
    *,
    network: str,
    state_root: Optional[Path] = None,
) -> dict[str, Any]:
    present = cache_present(job, state_root)
    cache_dir = job_cache_dir(job, state_root)
    if present:
        return {
            "ok": True,
            "status": "cache-hit",
            "cache_key": job.cache_key,
            "cache_dir": str(cache_dir),
            "n_oleans": len(olean_paths(cache_dir)),
            "network": network,
            "arena_score": None,
        }
    if network == "deny":
        raise OleanCacheMissing(
            "olean cache missing for "
            f"{job.cache_key} under network=deny; first lake build is hours and "
            "must be pre-vendored before the 48h clock. Never falling back to "
            "PATH lean, Tmp.lean, or a guessed PutnamBench GitHub URL."
        )
    return {
        "ok": False,
        "status": "cache-missing",
        "cache_key": job.cache_key,
        "cache_dir": str(cache_dir),
        "n_oleans": 0,
        "network": network,
        "arena_score": None,
    }


def require_plan_caches(
    plan: BakePlan,
    *,
    network: str,
    state_root: Optional[Path] = None,
) -> list[dict[str, Any]]:
    return [require_cache(job, network=network, state_root=state_root) for job in plan.jobs]


def lake_argv(lean_tag: str, *args: str, elan_home: Optional[Path] = None) -> list[str]:
    pin = tag_pinned_paths(lean_tag, elan_home=elan_home)
    return [pin["lake_path"], *args]


def _run_tag_pinned_lake(
    lean_tag: str,
    args: Sequence[str],
    *,
    cwd: Path,
    timeout: float,
    env: Optional[Mapping[str, str]] = None,
    elan_home: Optional[Path] = None,
) -> dict[str, Any]:
    """Run tag-pinned lake. Never PATH ``lake``. Not used by --self-check."""

    import subprocess

    pin = tag_pinned_paths(lean_tag, elan_home=elan_home)
    if not pin["installed"]:
        raise BakeToolchainMissing(
            "tag-pinned elan toolchain not installed at "
            f"{pin['toolchain_dir']} (lean_tag={lean_tag!r}; never falling back "
            "to PATH lean/lake)"
        )
    argv = [pin["lake_path"], *list(args)]
    if Path(argv[0]).name != "lake":
        raise BakeError(f"expected tag-pinned lake, got {argv[0]!r}")
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
        env=dict(env) if env is not None else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "lake_path": pin["lake_path"],
        "lean_path": pin["lean_path"],
        "arena_score": None,
    }


def bake_job(
    job: BakeJob,
    *,
    network: str,
    state_root: Optional[Path] = None,
    timeout: float = DEFAULT_LAKE_TIMEOUT_SECONDS,
    execute: bool = False,
) -> dict[str, Any]:
    """Return a cache hit, fail closed under network=deny, or bake if asked."""

    hit = require_cache(job, network="allow", state_root=state_root)
    if hit["ok"]:
        hit["status"] = "cache-hit"
        hit["lake_build_executed"] = False
        return hit
    if network == "deny":
        require_cache(job, network="deny", state_root=state_root)
    pin = tag_pinned_paths(job.lean_tag)
    if not pin["installed"]:
        raise BakeToolchainMissing(
            "tag-pinned elan lake is not installed at "
            f"{pin['lake_path']}; capability gap, not PATH lake usability"
        )
    if not execute:
        return {
            "ok": False,
            "status": "ready-to-bake",
            "cache_key": job.cache_key,
            "network": network,
            "lake_build_executed": False,
            "lake_path": pin["lake_path"],
            "arena_score": None,
        }
    root = Path(state_root) if state_root is not None else default_state_root()
    if job.kind == "putnam":
        project = putnam_project_dir(job, root)
        materialize_putnam_project(job.lean_tag, project, jsonl_version_pin=job.git_commit)
        result = _run_tag_pinned_lake(
            job.lean_tag, ["build"], cwd=project, timeout=timeout
        )
        if result["exit_code"] != 0:
            raise BakeError(f"lake build failed for Putnam {job.lean_tag}: exit {result['exit_code']}")
        _copy_oleans(project / ".lake", job_cache_dir(job, root) / ".lake")
    else:
        clone = root / "clones" / _url_cache_key(job.url)
        if not (clone / ".git").is_dir():
            if not GIT_BIN.is_file():
                raise BakeToolchainMissing(f"git is not at {GIT_BIN}; cannot clone {job.url}")
            import subprocess

            clone.parent.mkdir(parents=True, exist_ok=True)
            cloned = subprocess.run(
                [str(GIT_BIN), "clone", "--", job.url, str(clone)],
                capture_output=True,
                text=True,
                check=False,
            )
            if cloned.returncode != 0:
                raise BakeError(f"git clone failed for {job.url}: {cloned.stderr.strip()}")
        import subprocess

        checked = subprocess.run(
            [str(GIT_BIN), "-C", str(clone), "checkout", "--detach", job.git_commit],
            capture_output=True,
            text=True,
            check=False,
        )
        if checked.returncode != 0:
            raise BakeError(f"git checkout {job.git_commit} failed: {checked.stderr.strip()}")
        result = _run_tag_pinned_lake(job.lean_tag, ["build"], cwd=clone, timeout=timeout)
        if result["exit_code"] != 0:
            raise BakeError(f"lake build failed for {job.cache_key}: exit {result['exit_code']}")
        _copy_oleans(clone / ".lake", job_cache_dir(job, root) / ".lake")
    cache_dir = job_cache_dir(job, root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_marker_path(cache_dir).write_text("baked\n", encoding="utf-8")
    return {
        "ok": True,
        "status": "baked",
        "cache_key": job.cache_key,
        "cache_dir": str(cache_dir),
        "n_oleans": len(olean_paths(cache_dir)),
        "network": network,
        "lake_build_executed": True,
        "lake_argv": lake_argv(job.lean_tag, "build"),
        "arena_score": None,
    }


def _copy_oleans(src: Path, dest: Path) -> None:
    if not src.is_dir():
        raise BakeError(f"expected .lake directory at {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    _copytree(src, dest)


def _copytree(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        target = dest / entry.name
        if entry.is_dir():
            _copytree(entry, target)
        else:
            target.write_bytes(entry.read_bytes())


def write_candidate(lean_tag: str, source_text: str, dest: Optional[Path] = None) -> Path:
    """Copy a Putnam candidate into Putnam/Candidate.lean. Never Tmp.lean."""

    if dest is None:
        dest = putnam_project_dir(
            BakeJob(
                kind="putnam",
                source=PUTNAM_SOURCE,
                lean_tag=normalize_lean_tag(lean_tag),
                git_commit="",
                url="",
                cache_key=f"putnam/{normalize_lean_tag(lean_tag)}",
                phase=2,
                record_names=(),
                file_paths=(PUTNAM_CANDIDATE_RELPATH,),
                module=PUTNAM_MODULE,
                lakefile_required=True,
            )
        )
    dest = Path(dest)
    if dest.name == FORBIDDEN_PUTNAM_BASENAME or dest.name == "Tmp":
        raise BakeError("refusing to write Putnam candidate as Tmp.lean")
    path = dest / PUTNAM_CANDIDATE_RELPATH if dest.is_dir() else dest
    if path.name == FORBIDDEN_PUTNAM_BASENAME:
        raise BakeError("refusing to write Putnam candidate as Tmp.lean")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source_text, encoding="utf-8")
    return path


def _imported_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".", 1)[0])
    return names


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    text = Path(__file__).read_text(encoding="utf-8") if source is None else source
    tree = ast.parse(text)
    imported = _imported_names(text)
    calls = {_call_name(child.func) for child in ast.walk(tree) if isinstance(child, ast.Call)}
    string_constants = [
        child.value
        for child in ast.walk(tree)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    ]
    forbidden_urls = sorted(
        {
            value
            for value in string_constants
            if "://" in value
            and any(needle.lower() in value.lower() for needle in FORBIDDEN_PUTNAM_URL_NEEDLES)
        }
    )
    score_assignments: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg in FORBIDDEN_SCORE_NAMES:
            if not (
                isinstance(node.value, ast.Constant) and node.value.value is None
            ):
                score_assignments.append(str(node.arg))
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in FORBIDDEN_SCORE_NAMES and not (
                isinstance(node.value, ast.Constant) and node.value.value is None
            ):
                score_assignments.append(node.target.id)
    forbidden_imports = sorted(imported & FORBIDDEN_IMPORT_NAMES)
    forbidden_calls = sorted(calls & FORBIDDEN_CALLS)
    has_tmp_constant = FORBIDDEN_PUTNAM_BASENAME in string_constants
    has_putnam_module = PUTNAM_MODULE in string_constants
    has_mathlib_git = MATHLIB_GIT in string_constants
    has_aesop_git = AESOP_GIT in string_constants
    return {
        "imported_names": sorted(imported),
        "forbidden_imports": forbidden_imports,
        "forbidden_calls": forbidden_calls,
        "forbidden_putnambench_urls": forbidden_urls,
        "score_assignments": score_assignments,
        "has_tmp_lean_constant": has_tmp_constant,
        "has_putnam_module": has_putnam_module,
        "has_mathlib_git": has_mathlib_git,
        "has_aesop_git": has_aesop_git,
        "uses_fcntl": "fcntl" in imported,
        "uses_shutil_which": "shutil" in imported and "which" in calls,
        "ok": (
            not forbidden_imports
            and not forbidden_calls
            and not forbidden_urls
            and not score_assignments
            and has_tmp_constant
            and has_putnam_module
            and has_mathlib_git
            and has_aesop_git
        ),
    }


def _synthetic_fail_closed(plan: BakePlan) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="lra-013-oleans-") as tmp:
        root = Path(tmp)
        first = plan.first_job
        planted = plant_synthetic_cache(first, root)
        hit = require_cache(first, network="deny", state_root=root)
        missing_raised = False
        missing_message = ""
        putnam_job = next(job for job in plan.jobs if job.kind == "putnam")
        try:
            require_cache(putnam_job, network="deny", state_root=root)
        except OleanCacheMissing as exc:
            missing_raised = True
            missing_message = str(exc)
        allow_missing = require_cache(putnam_job, network="allow", state_root=root)
        write_denied = False
        try:
            write_candidate(STRATA_FIRST_TAG, "theorem x : True := by trivial", dest=root / FORBIDDEN_PUTNAM_BASENAME)
        except BakeError:
            write_denied = True
        materialized: dict[str, Any] = {}
        for job in plan.jobs:
            if job.kind != "putnam":
                continue
            dest = root / "putnam_lake" / job.lean_tag
            files = materialize_putnam_project(job.lean_tag, dest, jsonl_version_pin=job.git_commit)
            lakefile = (dest / "lakefile.lean").read_text(encoding="utf-8")
            toolchain = (dest / "lean-toolchain").read_text(encoding="utf-8").strip()
            pins = json.loads((dest / "pins.json").read_text(encoding="utf-8"))
            materialized[job.lean_tag] = {
                "dest": str(dest),
                "files": sorted(files),
                "has_lakefile": (dest / "lakefile.lean").is_file(),
                "has_tmp_lean": (dest / FORBIDDEN_PUTNAM_BASENAME).exists(),
                "toolchain": toolchain,
                "mathlib_in_lakefile": "mathlib" in lakefile and MATHLIB_GIT in lakefile,
                "aesop_in_lakefile": "aesop" in lakefile and AESOP_GIT in lakefile,
                "candidate_module": pins.get("module"),
                "putnambench_url": pins.get("putnambench_url"),
                "tmp_lean": pins.get("tmp_lean"),
                "jsonl_version_pin": pins.get("jsonl_version_pin"),
            }
        return {
            "planted_cache_dir": str(planted),
            "planted_n_oleans": len(olean_paths(planted)),
            "deny_cache_hit_on_planted_strata_v4_26": hit["ok"] is True and hit["status"] == "cache-hit",
            "missing_putnam_under_network_deny_raises": missing_raised,
            "missing_message_mentions_network_deny": "network=deny" in missing_message,
            "allow_missing_does_not_raise": allow_missing["ok"] is False
            and allow_missing["status"] == "cache-missing",
            "write_candidate_rejects_tmp_lean": write_denied,
            "materialized_putnam": materialized,
            "all_putnam_tags_materialized": set(materialized) == set(PUTNAM_TAGS),
            "any_putnam_tmp_lean": any(row["has_tmp_lean"] for row in materialized.values()),
            "all_putnam_have_mathlib_aesop_lakefile": all(
                row["has_lakefile"] and row["mathlib_in_lakefile"] and row["aesop_in_lakefile"]
                for row in materialized.values()
            ),
            "all_putnam_module_candidate": all(
                row["candidate_module"] == PUTNAM_MODULE for row in materialized.values()
            ),
            "all_putnambench_url_null": all(
                row["putnambench_url"] is None for row in materialized.values()
            ),
        }


def probe_toolchain(tags: Iterable[str] | None = None) -> dict[str, Any]:
    if tags is None:
        tags = (STRATA_FIRST_TAG, *PUTNAM_TAGS)
    wanted: list[str] = []
    for tag in tags:
        if tag not in wanted:
            wanted.append(tag)
    pins = [tag_pinned_paths(tag) for tag in wanted]
    installed = [pin["lean_tag"] for pin in pins if pin["installed"]]
    missing = [pin["lean_tag"] for pin in pins if not pin["installed"]]
    return {
        "arena_score": None,
        "default_elan_home": str(default_elan_home()),
        "elan_home_env": os.environ.get("ELAN_HOME"),
        "installed_tags": installed,
        "lake": False,
        "missing_tags": missing,
        "path": os.environ.get("PATH"),
        "pins": pins,
        "validation_home": str(Path.home()),
        "capability_gap": (
            "No tag-pinned elan lean/lake binaries are installed under the "
            "resolver elan home. Paths remain tag-pinned; this is not PATH "
            "lake usability and is not a completed olean bake."
            if missing and not installed
            else ""
        ),
    }


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    plan = plan_bake(jsonl)
    first = plan.first_job
    audit = audit_source()
    synthetic = _synthetic_fail_closed(plan)
    toolchain = probe_toolchain()
    putnam_jobs = [job for job in plan.jobs if job.kind == "putnam"]
    repo_jobs = [job for job in plan.jobs if job.kind == "repo"]
    phases = [job.phase for job in plan.jobs]
    first_phase_ok = phases[:1] == [0] and all(phase >= 0 for phase in phases)
    strata_v426_before_rest = all(
        job.phase == 0
        for job in plan.jobs
        if job.source == STRATA_SOURCE and job.lean_tag == STRATA_FIRST_TAG
    ) and all(job.phase > 0 for job in plan.jobs if not (
        job.source == STRATA_SOURCE and job.lean_tag == STRATA_FIRST_TAG
    ))
    putnam_headers_ok = True
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    putnam_records = [record for record in records if record.get("source") == PUTNAM_SOURCE]
    for record in putnam_records:
        header = record.get("header") or ""
        if "import Mathlib" not in header or "import Aesop" not in header:
            putnam_headers_ok = False
        if (record.get("url") or "").strip() or (record.get("file_path") or "").strip():
            putnam_headers_ok = False
    report: dict[str, Any] = {
        "ok": False,
        "arena_score": None,
        "score": None,
        "compiled": False,
        "lake": False,
        "lake_build_executed": False,
        "oleans_baked": False,
        "llama_server_started": False,
        "frozen_warmup_sha256": digest,
        "jsonl_bytes": len(raw),
        "jsonl_unchanged": digest == FROZEN_WARMUP_SHA256,
        "n_records": len(records),
        "n_jobs": len(plan.jobs),
        "n_repo_jobs": len(repo_jobs),
        "n_putnam_jobs": len(putnam_jobs),
        "n_putnam_records": len(putnam_records),
        "first_job": first.to_dict(),
        "first_is_strata_v4_26": (
            first.kind == "repo"
            and first.source == STRATA_SOURCE
            and first.lean_tag == STRATA_FIRST_TAG
            and first.git_commit == STRATA_FIRST_COMMIT
            and first.url == STRATA_URL
            and first.phase == 0
        ),
        "first_cache_key": first.cache_key,
        "strata_v4_26_recorded_first": True,
        "strata_v426_before_rest": strata_v426_before_rest,
        "first_phase_ok": first_phase_ok,
        "putnam_tags": [job.lean_tag for job in putnam_jobs],
        "putnam_tags_match": tuple(job.lean_tag for job in putnam_jobs) == PUTNAM_TAGS,
        "putnam_module": PUTNAM_MODULE,
        "putnam_not_tmp_lean": all(job.module == PUTNAM_MODULE for job in putnam_jobs)
        and all(FORBIDDEN_PUTNAM_BASENAME not in job.file_paths for job in putnam_jobs),
        "putnam_headers_import_mathlib_aesop": putnam_headers_ok,
        "putnam_url_file_path_empty": all(not job.url for job in putnam_jobs),
        "putnambench_url_not_guessed": all(job.putnambench_url is None for job in putnam_jobs),
        "missing_cache_fails_closed_under_network_deny": bool(
            synthetic["missing_putnam_under_network_deny_raises"]
            and synthetic["missing_message_mentions_network_deny"]
            and synthetic["deny_cache_hit_on_planted_strata_v4_26"]
        ),
        "measurement_maxHeartbeats": MEASUREMENT_MAX_HEARTBEATS,
        "kernel_command_template": KERNEL_COMMAND_TEMPLATE,
        "bake_argv_template": BAKE_ARGV_TEMPLATE,
        "default_state_root": str(default_state_root()),
        "network_env": os.environ.get("LRA_NETWORK"),
        "protocol": "LRA/v1",
        "audit": audit,
        "synthetic": {
            key: value
            for key, value in synthetic.items()
            if key != "materialized_putnam"
        },
        "putnam_projects": synthetic["materialized_putnam"],
        "toolchain": toolchain,
        "jobs": [job.to_dict() for job in plan.jobs],
        "warmup_path": str(jsonl.relative_to(REPO_ROOT)),
        "putnam_readme_exists": PUTNAM_README.is_file(),
    }
    report["ok"] = bool(
        report["n_records"] == WARMUP_N
        and report["jsonl_unchanged"]
        and report["n_jobs"] == 15
        and report["n_repo_jobs"] == 12
        and report["n_putnam_jobs"] == 3
        and report["first_is_strata_v4_26"]
        and report["strata_v426_before_rest"]
        and report["putnam_tags_match"]
        and report["putnam_not_tmp_lean"]
        and report["putnam_headers_import_mathlib_aesop"]
        and report["putnam_url_file_path_empty"]
        and report["putnambench_url_not_guessed"]
        and report["missing_cache_fails_closed_under_network_deny"]
        and synthetic["all_putnam_tags_materialized"]
        and not synthetic["any_putnam_tmp_lean"]
        and synthetic["all_putnam_have_mathlib_aesop_lakefile"]
        and synthetic["all_putnam_module_candidate"]
        and synthetic["all_putnambench_url_null"]
        and synthetic["write_candidate_rejects_tmp_lean"]
        and audit["ok"]
        and report["compiled"] is False
        and report["lake"] is False
        and report["lake_build_executed"] is False
        and report["oleans_baked"] is False
        and report["arena_score"] is None
        and report["score"] is None
        and report["putnam_readme_exists"]
    )
    return report


def _print_json(payload: Mapping[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="plan, fail-closed cache, Putnam lakefiles; no lake build")
    parser.add_argument("--plan", action="store_true", help="print the bake plan; Strata v4.26 first")
    parser.add_argument("--probe-toolchain", action="store_true", help="record tag-pinned elan paths; do not run lake")
    parser.add_argument("--dump-putnam-project", action="store_true", help="print one per-tag Putnam lake project")
    parser.add_argument("--require-cache", action="store_true", help="fail closed if oleans are missing")
    parser.add_argument("--materialize-putnam", type=Path, default=None, help="write per-tag Putnam lake projects under this directory")
    parser.add_argument("--tag", default=STRATA_FIRST_TAG, help="Putnam/Lean tag for dump/materialize (default v4.26.0)")
    parser.add_argument("--network", default=None, help="allow or deny (default: LRA_NETWORK or allow)")
    parser.add_argument("--jsonl", type=Path, default=None, help="warmup JSONL path")
    parser.add_argument("--state-root", type=Path, default=None, help="olean/putnam_lake state root")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.self_check or argv is None or argv == []:
        report = self_check(args.jsonl)
        _print_json(report)
        return 0 if report["ok"] else 1

    if args.plan:
        plan = plan_bake(args.jsonl)
        _print_json(plan.to_dict())
        return 0

    if args.probe_toolchain:
        _print_json(probe_toolchain())
        return 0

    if args.dump_putnam_project:
        plan = plan_bake(args.jsonl)
        tag = normalize_lean_tag(args.tag)
        job = next((item for item in plan.jobs if item.kind == "putnam" and item.lean_tag == tag), None)
        pin_commit = job.git_commit if job is not None else ""
        files = putnam_project_files(tag, jsonl_version_pin=pin_commit)
        _print_json(
            {
                "arena_score": None,
                "files": files,
                "lean_tag": tag,
                "module": PUTNAM_MODULE,
                "not_tmp_lean": True,
                "putnambench_url": None,
                "jsonl_version_pin": pin_commit,
            }
        )
        return 0

    if args.materialize_putnam is not None:
        plan = plan_bake(args.jsonl)
        dest_root = Path(args.materialize_putnam)
        written: dict[str, Any] = {}
        for job in plan.jobs:
            if job.kind != "putnam":
                continue
            dest = dest_root / job.lean_tag
            files = materialize_putnam_project(job.lean_tag, dest, jsonl_version_pin=job.git_commit)
            written[job.lean_tag] = files
        _print_json(
            {
                "arena_score": None,
                "dest": str(dest_root),
                "module": PUTNAM_MODULE,
                "not_tmp_lean": True,
                "putnambench_url": None,
                "written": written,
            }
        )
        return 0

    if args.require_cache:
        plan = plan_bake(args.jsonl)
        network = network_mode(args.network)
        state_root = args.state_root
        results = []
        try:
            results = require_plan_caches(plan, network=network, state_root=state_root)
        except OleanCacheMissing as exc:
            _print_json(
                {
                    "ok": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "network": network,
                    "arena_score": None,
                    "first_job": plan.first_job.to_dict(),
                }
            )
            return 1
        _print_json(
            {
                "ok": True,
                "network": network,
                "n_jobs": len(results),
                "results": results,
                "arena_score": None,
                "first_job": plan.first_job.to_dict(),
            }
        )
        return 0

    parser.error(
        "choose --self-check, --plan, --probe-toolchain, --dump-putnam-project, "
        "--materialize-putnam, or --require-cache"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
