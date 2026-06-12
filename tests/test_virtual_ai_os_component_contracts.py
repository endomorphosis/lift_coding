from __future__ import annotations

import subprocess
from pathlib import Path

from handsfree.config import get_virtual_ai_os_observability_contract
from handsfree.virtual_ai_os_components import (
    VIRTUAL_AI_OS_COMPONENT_REPO_CONTRACTS,
    get_virtual_ai_os_component_bootstrap_contract,
    get_virtual_ai_os_component_environment_contract,
    get_virtual_ai_os_component_pin_contract,
    get_virtual_ai_os_component_repo_contracts,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _gitmodules_entries() -> dict[str, str]:
    completed = subprocess.run(
        [
            "git",
            "config",
            "--file",
            ".gitmodules",
            "--get-regexp",
            r"^submodule\..*\.(path|url)$",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    entries: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        key, value = line.split(" ", 1)
        entries[key] = value
    return entries


def test_component_repo_contracts_cover_root_gitmodules() -> None:
    entries = _gitmodules_entries()
    contracts = {
        contract.path: contract for contract in VIRTUAL_AI_OS_COMPONENT_REPO_CONTRACTS
    }
    gitmodule_paths = {
        value for key, value in entries.items() if key.endswith(".path")
    }

    assert set(contracts) == gitmodule_paths
    for submodule_path, contract in contracts.items():
        matching_names = [
            key.rsplit(".", 1)[0]
            for key, value in entries.items()
            if key.endswith(".path") and value == submodule_path
        ]
        assert len(matching_names) == 1
        url_key = f"{matching_names[0]}.url"
        assert entries[url_key] == contract.upstream_url


def test_component_contract_environment_overrides_are_applied(tmp_path) -> None:
    override = tmp_path / "datasets"
    contracts = get_virtual_ai_os_component_repo_contracts(
        {"HANDSFREE_VAI_IPFS_DATASETS_ROOT": str(override)},
        repo_root=REPO_ROOT,
    )
    contract_by_id = {
        str(contract["component_id"]): contract for contract in contracts
    }

    assert contract_by_id["ipfs_datasets_py"]["resolved_root"] == str(override)
    assert contract_by_id["ipfs_accelerate_py"]["resolved_root"] == str(
        REPO_ROOT / "external" / "ipfs_accelerate"
    )


def test_component_pin_and_bootstrap_contracts_are_guarded() -> None:
    pins = get_virtual_ai_os_component_pin_contract()
    bootstrap = get_virtual_ai_os_component_bootstrap_contract()
    environment = get_virtual_ai_os_component_environment_contract()

    assert "superproject gitlink is the reviewed pin" in pins["ipfs_kit_py"]
    assert "must not fetch, checkout, or advance" in pins["swissknife"]
    assert bootstrap["ipfs_kit_py"]["bootstrap_mode"] == (
        "init_root_submodule_status_nested"
    )
    assert bootstrap["ipfs_kit_py"]["recursive_bootstrap"] is False
    assert bootstrap["meta_wearables_dat_ios"]["bootstrap_mode"] == (
        "optional_device_validation_submodule"
    )
    assert environment["mcp_plus_plus"] == "HANDSFREE_VAI_MCP_PLUS_PLUS_ROOT"


def test_observability_contract_surfaces_component_repo_contracts() -> None:
    contract = get_virtual_ai_os_observability_contract({})
    component_ids = {
        str(component["component_id"]) for component in contract["component_repos"]
    }

    assert "ipfs_datasets_py" in component_ids
    assert "mcp_plus_plus" in component_ids
    assert contract["component_environment"]["swissknife"] == (
        "HANDSFREE_VAI_SWISSKNIFE_ROOT"
    )
    assert contract["component_bootstrap"]["hallucinate_app"]["bootstrap_mode"] == (
        "init_root_submodule"
    )
