"""pytest configuration for HandsFree tests."""

import contextlib
import os
import shutil
import subprocess
import sys
import time
import uuid
import warnings
from pathlib import Path

import pytest

try:
    import fcntl
except ImportError:  # pragma: no cover - fcntl is POSIX-only
    fcntl = None  # type: ignore[assignment]

# Add src directory to path so tests can import handsfree
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set DUCKDB_PATH to :memory: for all tests to ensure test isolation
os.environ["DUCKDB_PATH"] = ":memory:"

# Image fetching configuration for tests
# Enable local image URIs for testing (gated by env var for security)
os.environ["HANDSFREE_ALLOW_LOCAL_IMAGE_URIS"] = "1"
# Disable strict host checking for tests to avoid requiring allowlist configuration
os.environ["IMAGE_STRICT_HOST_CHECKING"] = "0"
# Limit maximum image size (in bytes) for tests (5 MiB)
os.environ["IMAGE_MAX_SIZE_BYTES"] = "5242880"
# Set a reasonable timeout (in seconds) for fetching images in tests
os.environ["IMAGE_FETCH_TIMEOUT_SECONDS"] = "10"


def _external_submodule_sources(name: str) -> list[Path]:
    repo_root = Path(__file__).resolve().parents[1]
    candidates: list[Path] = []
    configured_root = os.environ.get("HANDSFREE_EXTERNAL_SUBMODULE_ROOT")
    if configured_root:
        candidates.append(Path(configured_root) / name)
    candidates.extend(parent / "external" / name for parent in repo_root.parents)
    return candidates


def _path_has_files(path: Path) -> bool:
    if path.is_symlink():
        return path.exists()
    if not path.exists() or not path.is_dir():
        return False
    return any(path.iterdir())


# HAO-756: bootstrap resilience knobs. Under heavy parallel worktree/agent
# load the host can run short on memory/process slots (spawn ENOENT-style
# faults) which previously surfaced as an uncaught exception raised at
# collection time from this module-level bootstrap loop. That crashed the
# *entire* test session (not just the tests that needed the submodule),
# which is indistinguishable from a real implementation/validation failure
# to the retry-budget guardrail. The knobs below make the bootstrap retry
# transient failures, time-box each attempt, and never let a bootstrap
# failure abort collection.
_SUBMODULE_BOOTSTRAP_ATTEMPTS = int(os.environ.get("HANDSFREE_SUBMODULE_BOOTSTRAP_ATTEMPTS", "3"))
_SUBMODULE_BOOTSTRAP_RETRY_SECONDS = float(
    os.environ.get("HANDSFREE_SUBMODULE_BOOTSTRAP_RETRY_SECONDS", "0.5")
)
_SUBMODULE_BOOTSTRAP_TIMEOUT_SECONDS = float(
    os.environ.get("HANDSFREE_SUBMODULE_BOOTSTRAP_TIMEOUT_SECONDS", "120")
)


@contextlib.contextmanager
def _submodule_bootstrap_lock(target: Path):
    """Serialize concurrent bootstrap attempts for the same target.

    Multiple pytest workers (or parallel test invocations sharing a
    worktree) can otherwise race to clone/copy into the same ``target``
    directory at once, multiplying memory/CPU/disk pressure and increasing
    the odds of a transient spawn failure. The lock is advisory and
    best-effort: if ``fcntl`` is unavailable (non-POSIX platforms) the
    bootstrap simply proceeds without serialization.
    """
    if fcntl is None:
        yield
        return

    lock_path = target.parent / f".{target.name}.bootstrap.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "a+")
    try:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
        except OSError:
            # Locking failed (e.g. filesystem doesn't support flock) -- fall
            # back to running unsynchronized rather than failing collection.
            pass
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


def _clone_or_copy_submodule(source: Path, target: Path) -> None:
    if target.exists() and target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    elif target.exists() or target.is_symlink():
        target.unlink()

    try:
        subprocess.run(
            ["git", "clone", "--local", "--quiet", str(source), str(target)],
            check=True,
            capture_output=True,
            text=True,
            timeout=_SUBMODULE_BOOTSTRAP_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target, symlinks=True)


def _ensure_external_submodule(name: str) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "external" / name
    if _path_has_files(target):
        return

    source = next(
        (
            candidate
            for candidate in _external_submodule_sources(name)
            if _path_has_files(candidate)
        ),
        None,
    )
    if source is None:
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    with _submodule_bootstrap_lock(target):
        if _path_has_files(target):
            # Another process populated it while we waited for the lock.
            return
        for attempt in range(1, _SUBMODULE_BOOTSTRAP_ATTEMPTS + 1):
            try:
                _clone_or_copy_submodule(source, target)
                return
            except Exception as exc:
                last_error = exc
                if attempt < _SUBMODULE_BOOTSTRAP_ATTEMPTS:
                    time.sleep(_SUBMODULE_BOOTSTRAP_RETRY_SECONDS * attempt)

    if last_error is not None:
        # Never let a bootstrap failure abort test collection: warn and let
        # individual tests that actually need the submodule fail/skip on
        # their own with an actionable message instead of taking down the
        # whole session with an unrelated-looking collection error.
        warnings.warn(
            f"HAO-756: failed to bootstrap external submodule {name!r} into "
            f"{target} after {_SUBMODULE_BOOTSTRAP_ATTEMPTS} attempt(s): "
            f"{last_error!r}. Tests depending on external/{name} may fail or "
            "be skipped.",
            RuntimeWarning,
            stacklevel=2,
        )


for _submodule_name in (
    "ipfs_kit",
    "meta-wearables-dat-android",
    "meta-wearables-dat-ios",
):
    try:
        _ensure_external_submodule(_submodule_name)
    except Exception as _bootstrap_exc:
        warnings.warn(
            f"HAO-756: unexpected error bootstrapping external submodule "
            f"{_submodule_name!r}: {_bootstrap_exc!r}. Continuing collection "
            "so unrelated tests are not blocked.",
            RuntimeWarning,
            stacklevel=2,
        )


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    # Use a fixed UUID for consistent testing
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def test_user_id_2():
    """Generate a second test user ID."""
    return str(uuid.UUID("87654321-4321-4321-4321-210987654321"))
