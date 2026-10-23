"""Run the ipfs_accelerate_py test/api plan tests in the lift_coding stack's
own configuration: accelerate code resolves ipfs_datasets_py from the
superproject's pinned submodule (external/ipfs_datasets), NOT from the
accelerate repo's vendored in-root clone (an older pin without
logic/formalization/autoencoder, which the repo-root conftest's
sys.path.insert(0, repo_root) would otherwise make win).

Pre-importing ipfs_datasets_py pins the resolution before pytest loads the
repo conftest; everything else runs unmodified.

Usage: run_api_tests.py <pytest args...>
Run with cwd = external/ipfs_accelerate and the lift_coding .venv python.
"""
import sys

sys.path.insert(0, "/home/hatch/workspace/lift_coding/external/ipfs_accelerate")
sys.path.insert(0, "/home/hatch/workspace/lift_coding/external/ipfs_kit")
sys.path.insert(0, "/home/hatch/workspace/lift_coding/external/ipfs_datasets")

import ipfs_datasets_py

assert "external/ipfs_datasets" in ipfs_datasets_py.__file__, ipfs_datasets_py.__file__
import ipfs_datasets_py.logic.formalization.autoencoder.source_screening  # noqa: F401

import pytest

if __name__ == "__main__":
    sys.exit(pytest.main(sys.argv[1:]))
