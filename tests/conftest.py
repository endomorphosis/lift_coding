"""pytest configuration for HandsFree tests."""

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

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


def _ensure_external_submodule(name: str) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "external" / name
    if _path_has_files(target):
        return

    source = next((candidate for candidate in _external_submodule_sources(name) if _path_has_files(candidate)), None)
    if source is None:
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.is_dir() and not target.is_symlink():
        target.rmdir()
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        subprocess.run(
            ["git", "clone", "--local", "--quiet", str(source), str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target, symlinks=True)


for _submodule_name in (
    "ipfs_kit",
    "meta-wearables-dat-android",
    "meta-wearables-dat-ios",
):
    _ensure_external_submodule(_submodule_name)


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    # Use a fixed UUID for consistent testing
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def test_user_id_2():
    """Generate a second test user ID."""
    return str(uuid.UUID("87654321-4321-4321-4321-210987654321"))
