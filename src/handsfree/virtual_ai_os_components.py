"""Virtual AI OS component repository contracts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class VirtualAiOsComponentRepoContract:
    """Environment, pin, and bootstrap contract for one component repo."""

    component_id: str
    path: str
    upstream_url: str
    role: str
    env_root_var: str
    bootstrap_mode: str
    auth_assumption: str
    pin_policy: str
    recursive_bootstrap: bool
    detached_worktree_policy: str
    dirty_worktree_policy: str

    def resolved_root(
        self,
        environ: Mapping[str, str],
        repo_root: Path | None = None,
    ) -> Path:
        override = environ.get(self.env_root_var)
        if override:
            return Path(override).expanduser()
        root = Path.cwd() if repo_root is None else repo_root
        return root / self.path

    def as_dict(
        self,
        environ: Mapping[str, str],
        repo_root: Path | None = None,
    ) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "path": self.path,
            "upstream_url": self.upstream_url,
            "role": self.role,
            "env_root_var": self.env_root_var,
            "resolved_root": str(self.resolved_root(environ, repo_root)),
            "bootstrap_mode": self.bootstrap_mode,
            "auth_assumption": self.auth_assumption,
            "pin_policy": self.pin_policy,
            "recursive_bootstrap": self.recursive_bootstrap,
            "detached_worktree_policy": self.detached_worktree_policy,
            "dirty_worktree_policy": self.dirty_worktree_policy,
        }


ROOT_GITLINK_PIN_POLICY = (
    "the superproject gitlink is the reviewed pin; bootstrap may initialize "
    "or sync a component but must not fetch, checkout, or advance it unless a "
    "pin-refresh task explicitly requests that change after validation evidence "
    "exists for the new component commit"
)

STATUS_ONLY_PIN_POLICY = (
    "status-only component for device readiness; initialize only when a local "
    "native validation task requires it, and do not advance the superproject pin"
)

COMPONENT_AUTH_ASSUMPTION = (
    "public HTTPS clone/fetch is the default; private forks or write operations "
    "must use the operator's existing git credential helper or gh auth without "
    "embedding tokens in task boards, discovery artifacts, or environment dumps"
)

DETACHED_WORKTREE_POLICY = (
    "supervisor and daemon implementations run in detached task worktrees under "
    "the namespace worktree root; component submodule pins are read from the "
    "superproject and are not advanced from those detached worktrees"
)

VIRTUAL_AI_OS_COMPONENT_REPO_CONTRACTS: tuple[
    VirtualAiOsComponentRepoContract, ...
] = (
    VirtualAiOsComponentRepoContract(
        component_id="ipfs_datasets_py",
        path="external/ipfs_datasets",
        upstream_url="https://github.com/endomorphosis/ipfs_datasets_py",
        role="semantic routing, datasets, backlog orchestration, and MCP grounding",
        env_root_var="HANDSFREE_VAI_IPFS_DATASETS_ROOT",
        bootstrap_mode="init_root_submodule",
        auth_assumption=COMPONENT_AUTH_ASSUMPTION,
        pin_policy=ROOT_GITLINK_PIN_POLICY,
        recursive_bootstrap=False,
        detached_worktree_policy=DETACHED_WORKTREE_POLICY,
        dirty_worktree_policy="fail before checkout when local changes are present",
    ),
    VirtualAiOsComponentRepoContract(
        component_id="ipfs_accelerate_py",
        path="external/ipfs_accelerate",
        upstream_url="https://github.com/endomorphosis/ipfs_accelerate_py",
        role="execution placement and acceleration plane",
        env_root_var="HANDSFREE_VAI_IPFS_ACCELERATE_ROOT",
        bootstrap_mode="init_root_submodule",
        auth_assumption=COMPONENT_AUTH_ASSUMPTION,
        pin_policy=ROOT_GITLINK_PIN_POLICY,
        recursive_bootstrap=False,
        detached_worktree_policy=DETACHED_WORKTREE_POLICY,
        dirty_worktree_policy="fail before checkout when local changes are present",
    ),
    VirtualAiOsComponentRepoContract(
        component_id="ipfs_kit_py",
        path="external/ipfs_kit",
        upstream_url="https://github.com/endomorphosis/ipfs_kit_py",
        role="IPFS content, packaging, and provenance plane",
        env_root_var="HANDSFREE_VAI_IPFS_KIT_ROOT",
        bootstrap_mode="init_root_submodule_status_nested",
        auth_assumption=COMPONENT_AUTH_ASSUMPTION,
        pin_policy=ROOT_GITLINK_PIN_POLICY,
        recursive_bootstrap=False,
        detached_worktree_policy=DETACHED_WORKTREE_POLICY,
        dirty_worktree_policy="status-only nested traversal until nested pins are verified",
    ),
    VirtualAiOsComponentRepoContract(
        component_id="swissknife",
        path="swissknife",
        upstream_url="https://github.com/endomorphosis/swissknife",
        role="local UI, ORB, MCP++, and operator-facing virtual desktop plane",
        env_root_var="HANDSFREE_VAI_SWISSKNIFE_ROOT",
        bootstrap_mode="init_root_submodule",
        auth_assumption=COMPONENT_AUTH_ASSUMPTION,
        pin_policy=ROOT_GITLINK_PIN_POLICY,
        recursive_bootstrap=False,
        detached_worktree_policy=DETACHED_WORKTREE_POLICY,
        dirty_worktree_policy="preserve local UI worktree changes; never auto-checkout dirty state",
    ),
    VirtualAiOsComponentRepoContract(
        component_id="hallucinate_app",
        path="hallucinate_app",
        upstream_url="https://github.com/endomorphosis/hallucinate_app.git",
        role="GUI shell, daemon manager, and developer workstation plane",
        env_root_var="HANDSFREE_VAI_HALLUCINATE_APP_ROOT",
        bootstrap_mode="init_root_submodule",
        auth_assumption=COMPONENT_AUTH_ASSUMPTION,
        pin_policy=ROOT_GITLINK_PIN_POLICY,
        recursive_bootstrap=False,
        detached_worktree_policy=DETACHED_WORKTREE_POLICY,
        dirty_worktree_policy="fail before checkout when local changes are present",
    ),
    VirtualAiOsComponentRepoContract(
        component_id="mcp_plus_plus",
        path="Mcp-Plus-Plus",
        upstream_url="https://github.com/endomorphosis/Mcp-Plus-Plus.git",
        role="case-sensitive standalone MCP++ spec/docs source",
        env_root_var="HANDSFREE_VAI_MCP_PLUS_PLUS_ROOT",
        bootstrap_mode="init_root_submodule",
        auth_assumption=COMPONENT_AUTH_ASSUMPTION,
        pin_policy=ROOT_GITLINK_PIN_POLICY,
        recursive_bootstrap=False,
        detached_worktree_policy=DETACHED_WORKTREE_POLICY,
        dirty_worktree_policy="fail before checkout when local changes are present",
    ),
    VirtualAiOsComponentRepoContract(
        component_id="meta_wearables_dat_android",
        path="external/meta-wearables-dat-android",
        upstream_url="https://github.com/facebook/meta-wearables-dat-android",
        role="Android native DAT compatibility reference",
        env_root_var="HANDSFREE_VAI_META_DAT_ANDROID_ROOT",
        bootstrap_mode="optional_device_validation_submodule",
        auth_assumption=COMPONENT_AUTH_ASSUMPTION,
        pin_policy=STATUS_ONLY_PIN_POLICY,
        recursive_bootstrap=False,
        detached_worktree_policy=DETACHED_WORKTREE_POLICY,
        dirty_worktree_policy="initialize only for Android DAT validation evidence",
    ),
    VirtualAiOsComponentRepoContract(
        component_id="meta_wearables_dat_ios",
        path="external/meta-wearables-dat-ios",
        upstream_url="https://github.com/facebook/meta-wearables-dat-ios",
        role="iOS native DAT compatibility reference",
        env_root_var="HANDSFREE_VAI_META_DAT_IOS_ROOT",
        bootstrap_mode="optional_device_validation_submodule",
        auth_assumption=COMPONENT_AUTH_ASSUMPTION,
        pin_policy=STATUS_ONLY_PIN_POLICY,
        recursive_bootstrap=False,
        detached_worktree_policy=DETACHED_WORKTREE_POLICY,
        dirty_worktree_policy="initialize only for iOS DAT validation evidence",
    ),
)


def get_virtual_ai_os_component_repo_contracts(
    environ: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
) -> list[dict[str, object]]:
    """Return stable component repo contracts with environment overrides applied."""

    source = os.environ if environ is None else environ
    return [
        contract.as_dict(source, repo_root)
        for contract in VIRTUAL_AI_OS_COMPONENT_REPO_CONTRACTS
    ]


def get_virtual_ai_os_component_environment_contract() -> dict[str, str]:
    """Return root-path environment variables by component id."""

    return {
        contract.component_id: contract.env_root_var
        for contract in VIRTUAL_AI_OS_COMPONENT_REPO_CONTRACTS
    }


def get_virtual_ai_os_component_pin_contract() -> dict[str, str]:
    """Return pin policies by component id."""

    return {
        contract.component_id: contract.pin_policy
        for contract in VIRTUAL_AI_OS_COMPONENT_REPO_CONTRACTS
    }


def get_virtual_ai_os_component_bootstrap_contract() -> dict[str, dict[str, object]]:
    """Return bootstrap policies by component id."""

    return {
        contract.component_id: {
            "path": contract.path,
            "bootstrap_mode": contract.bootstrap_mode,
            "auth_assumption": contract.auth_assumption,
            "recursive_bootstrap": contract.recursive_bootstrap,
            "detached_worktree_policy": contract.detached_worktree_policy,
            "dirty_worktree_policy": contract.dirty_worktree_policy,
        }
        for contract in VIRTUAL_AI_OS_COMPONENT_REPO_CONTRACTS
    }
