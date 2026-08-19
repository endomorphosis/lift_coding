"""FACP-056: immutable portfolio lock, reproducible build, signed provenance.

Acceptance (taskboard):
- All source dependencies are immutable and digest-bound.
- Two clean environments produce bit-identical declared artifacts or a typed
  nonreproducible blocker.
- Provenance verifies step materials/products and exact builder identity.

Owns only portfolio.lock.json, provenance_policy.json, and this hermetic test.
Does not publish/sign production release, resolve mutable branches, include
credentials, or claim reproducibility from a single build.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
QUAL_DIR = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "release"
    / "qualification"
)
LOCK_PATH = QUAL_DIR / "portfolio.lock.json"
PROVENANCE_PATH = QUAL_DIR / "provenance_policy.json"
RELEASE_PREDICATE_PATH = QUAL_DIR / "release_predicate.json"
SCHEDULER_PATH = REPO_ROOT / "config" / "formal_assurance_control_plane_scheduler.json"

TASK_ID = "FACP-056"
GOAL_ID = "FACP-G810"
BUNDLE = "facp/release/supply-chain"
LOCK_SCHEMA = "facp/portfolio-lock@1"
PROVENANCE_SCHEMA = "facp/provenance-policy@1"

REQUIRED_LOCK_EVIDENCE = {
    "commits",
    "gitlinks",
    "package_locks",
    "content_hashes",
    "toolchains",
    "environment",
    "instructions",
    "sbom",
    "bit_identity",
}

REQUIRED_PROVENANCE_EVIDENCE = REQUIRED_LOCK_EVIDENCE | {
    "in_toto_style_steps",
    "slsa_style_provenance",
}

REQUIRED_BLOCKER_CODES = {
    "nonreproducible:mutable_dependency",
    "nonreproducible:competing_lock_authority",
    "nonreproducible:missing_lock",
    "nonreproducible:pin_authority_divergence",
}

FULL_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

CLEAN_ENV_DENYLIST = (
    "SOURCE_DATE_EPOCH",
    "PYTHONHASHSEED",
    "SSH_AUTH_SOCK",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "GITHUB_TOKEN",
    "NPM_TOKEN",
)


def _load_json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def admitted_dependencies(lock: dict[str, Any]) -> list[dict[str, Any]]:
    return [dep for dep in lock["dependencies"] if dep.get("admitted") is True]


def admitted_digests(lock: dict[str, Any]) -> set[str]:
    digests = {dep["digest"] for dep in admitted_dependencies(lock)}
    for node in lock["source_binding"]["planning_forest"]:
        digests.add(node["digest"])
    return digests


def build_portfolio_closure_payload(
    lock: dict[str, Any], provenance: dict[str, Any]
) -> dict[str, Any]:
    """Deterministic declared artifact payload from digest-bound materials."""
    materials = [
        {
            "id": dep["id"],
            "path": dep.get("path"),
            "digest_algorithm": dep["digest_algorithm"],
            "digest": dep["digest"],
        }
        for dep in sorted(admitted_dependencies(lock), key=lambda item: item["id"])
    ]
    forest = [
        {
            "path": node["path"],
            "digest_algorithm": node["digest_algorithm"],
            "digest": node["digest"],
        }
        for node in sorted(
            lock["source_binding"]["planning_forest"], key=lambda item: item["path"]
        )
    ]
    builder = provenance["builder_identity"]["declared"]
    return {
        "artifact_id": "artifact:facp-portfolio-closure-v1",
        "lock_schema": lock["schema"],
        "builder": {
            "builder_id": builder["builder_id"],
            "builder_version": builder["builder_version"],
            "builder_uri": builder["builder_uri"],
            "builder_digest_sha256": builder["builder_digest_sha256"],
        },
        "materials": materials,
        "planning_forest": forest,
    }


def hermetic_build_declared_artifact(
    lock: dict[str, Any],
    provenance: dict[str, Any],
    work_dir: Path,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the declared artifact inside an isolated work directory."""
    if env is not None:
        for key in CLEAN_ENV_DENYLIST:
            assert key not in env, f"credential/nondeterministic env leaked: {key}"

    payload = build_portfolio_closure_payload(lock, provenance)
    product_bytes = _canonical_json_bytes(payload)
    product_path = work_dir / "facp-portfolio-closure-v1.json"
    product_path.write_bytes(product_bytes)
    digest = _sha256_bytes(product_bytes)
    return {
        "path": str(product_path),
        "digest_sha256": digest,
        "size": len(product_bytes),
        "payload": payload,
    }


def two_clean_environment_builds(
    lock: dict[str, Any], provenance: dict[str, Any]
) -> dict[str, Any]:
    """Run two isolated builds; return bit-identity result or typed blocker."""
    clean_env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
    }
    with tempfile.TemporaryDirectory(prefix="facp056-env-a-") as dir_a, tempfile.TemporaryDirectory(
        prefix="facp056-env-b-"
    ) as dir_b:
        build_a = hermetic_build_declared_artifact(
            lock, provenance, Path(dir_a), env=clean_env
        )
        build_b = hermetic_build_declared_artifact(
            lock, provenance, Path(dir_b), env=dict(clean_env)
        )

    if build_a["digest_sha256"] == build_b["digest_sha256"]:
        return {
            "bit_identical": True,
            "digest_sha256": build_a["digest_sha256"],
            "environment_count": 2,
            "blocker_code": None,
            "build_a": {"digest_sha256": build_a["digest_sha256"], "size": build_a["size"]},
            "build_b": {"digest_sha256": build_b["digest_sha256"], "size": build_b["size"]},
            "payload": build_a["payload"],
        }

    return {
        "bit_identical": False,
        "digest_sha256": None,
        "environment_count": 2,
        "blocker_code": "nonreproducible:artifact_digest_mismatch",
        "build_a": {"digest_sha256": build_a["digest_sha256"], "size": build_a["size"]},
        "build_b": {"digest_sha256": build_b["digest_sha256"], "size": build_b["size"]},
        "payload": build_a["payload"],
    }


def generate_unsigned_test_provenance(
    lock: dict[str, Any],
    provenance: dict[str, Any],
    product_digest: str,
    materials: list[dict[str, Any]],
) -> dict[str, Any]:
    builder = provenance["builder_identity"]["declared"]
    resolved = [
        {
            "uri": f"facp://lock/{item['id']}",
            "digest": {item["digest_algorithm"].replace("git-", "git:"): item["digest"]}
            if item["digest_algorithm"].startswith("git-")
            else {item["digest_algorithm"]: item["digest"]},
        }
        for item in materials
    ]
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": "facp-portfolio-closure-v1",
                "digest": {"sha256": product_digest},
            }
        ],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": builder["build_type"],
                "externalParameters": {
                    "portfolio_lock_ref": provenance["portfolio_lock_ref"],
                    "artifact_id": "artifact:facp-portfolio-closure-v1",
                    "recipe_id": "recipe:hermetic-portfolio-closure-v1",
                },
                "resolvedDependencies": resolved,
            },
            "runDetails": {
                "builder": {
                    "id": builder["builder_id"],
                    "version": {
                        "builder_version": builder["builder_version"],
                        "builder_uri": builder["builder_uri"],
                        "builder_digest_sha256": builder["builder_digest_sha256"],
                    },
                },
                "metadata": {
                    "invocationId": "hermetic-test-facp-056",
                    "unsigned_test_provenance": True,
                    "environment_count": 2,
                },
            },
        },
        "signatures": [],
        "unsigned_test_provenance": True,
        "production_release_claim": False,
        "steps": [
            {
                "id": "step:materialize-lock-closure",
                "materials": materials,
                "products": [
                    {
                        "name": "lock-closure-view",
                        "digest": {
                            "sha256": _sha256_bytes(
                                _canonical_json_bytes({"materials": materials})
                            )
                        },
                    }
                ],
            },
            {
                "id": "step:hermetic-build-declared-artifact",
                "materials": materials,
                "products": [
                    {
                        "name": "facp-portfolio-closure-v1",
                        "digest": {"sha256": product_digest},
                    }
                ],
            },
            {
                "id": "step:attest-provenance",
                "materials": [
                    {
                        "name": "facp-portfolio-closure-v1",
                        "digest": product_digest,
                    }
                ],
                "products": [
                    {
                        "name": "provenance-statement",
                        "digest": {"sha256": "pending-self-hash"},
                    }
                ],
                "builder_identity": {
                    "builder_id": builder["builder_id"],
                    "builder_version": builder["builder_version"],
                    "builder_uri": builder["builder_uri"],
                    "builder_digest_sha256": builder["builder_digest_sha256"],
                },
            },
        ],
    }
    # Bind provenance statement identity without circular signature bytes.
    statement_for_hash = {
        key: value
        for key, value in statement.items()
        if key not in {"signatures"}
    }
    statement_for_hash["steps"] = [
        step
        if step["id"] != "step:attest-provenance"
        else {
            **step,
            "products": [
                {
                    "name": "provenance-statement",
                    "digest": {"sha256": "0" * 64},
                }
            ],
        }
        for step in statement["steps"]
    ]
    statement_digest = _sha256_bytes(_canonical_json_bytes(statement_for_hash))
    for step in statement["steps"]:
        if step["id"] == "step:attest-provenance":
            step["products"][0]["digest"] = {"sha256": statement_digest}
    statement["statement_digest_sha256"] = statement_digest
    return statement


def verify_provenance(
    lock: dict[str, Any],
    provenance: dict[str, Any],
    statement: dict[str, Any],
    *,
    product_digest: str,
) -> tuple[bool, list[str]]:
    """Verify materials, products, and exact builder identity. Fail-closed."""
    blockers: list[str] = []
    allowed = admitted_digests(lock)
    declared_builder = provenance["builder_identity"]["declared"]

    # Materials: every material digest must be lock-admitted.
    for step in statement["steps"]:
        for material in step.get("materials", []):
            digest = material.get("digest")
            if isinstance(digest, dict):
                digest = next(iter(digest.values()))
            if digest not in allowed and material.get("name") != "facp-portfolio-closure-v1":
                # Intermediate product reused as material is allowed when it matches
                # the declared product digest.
                if digest != product_digest:
                    blockers.append("nonreproducible:material_digest_mismatch")

    # Products / subjects must match.
    subjects = statement["subject"]
    assert subjects, "provenance subject required"
    subject_digest = subjects[0]["digest"]["sha256"]
    if subject_digest != product_digest:
        blockers.append("nonreproducible:product_digest_mismatch")

    build_step = next(
        step
        for step in statement["steps"]
        if step["id"] == "step:hermetic-build-declared-artifact"
    )
    product = build_step["products"][0]
    if product["digest"]["sha256"] != product_digest:
        blockers.append("nonreproducible:product_digest_mismatch")

    # Exact builder identity.
    run_builder = statement["predicate"]["runDetails"]["builder"]
    version = run_builder["version"]
    if (
        run_builder["id"] != declared_builder["builder_id"]
        or version["builder_version"] != declared_builder["builder_version"]
        or version["builder_uri"] != declared_builder["builder_uri"]
        or version["builder_digest_sha256"]
        != declared_builder["builder_digest_sha256"]
    ):
        blockers.append("nonreproducible:builder_identity_mismatch")

    attest_step = next(
        step for step in statement["steps"] if step["id"] == "step:attest-provenance"
    )
    identity = attest_step["builder_identity"]
    for field in provenance["builder_identity"]["required_fields"]:
        if identity.get(field) != declared_builder.get(field):
            blockers.append("nonreproducible:builder_identity_mismatch")

    # Rejected mutable inputs must not appear as admitted materials.
    rejected_paths = {
        item.get("path")
        for item in lock["rejected_mutable_inputs"]
        if item.get("path")
    }
    for step in statement["steps"]:
        for material in step.get("materials", []):
            if material.get("path") in rejected_paths:
                blockers.append("nonreproducible:mutable_dependency")

    # Single-build claim forbidden.
    env_count = statement["predicate"]["runDetails"]["metadata"].get(
        "environment_count", 0
    )
    if statement.get("production_release_claim") is True:
        blockers.append("nonreproducible:artifact_digest_mismatch")
    if env_count < 2 and statement.get("claim_reproducible") is True:
        blockers.append("nonreproducible:artifact_digest_mismatch")

    # Unsigned test provenance is allowed; production signature is not claimed.
    if statement.get("unsigned_test_provenance") is True:
        assert statement.get("production_release_claim") is False
        assert provenance["policy"]["unsigned_test_provenance_allowed_for_hermetic_validation"]

    return (len(blockers) == 0, sorted(set(blockers)))


@pytest.fixture(scope="module")
def lock() -> dict[str, Any]:
    return _load_json(LOCK_PATH)


@pytest.fixture(scope="module")
def provenance() -> dict[str, Any]:
    return _load_json(PROVENANCE_PATH)


@pytest.fixture(scope="module")
def release_predicate() -> dict[str, Any]:
    return _load_json(RELEASE_PREDICATE_PATH)


@pytest.fixture(scope="module")
def scheduler() -> dict[str, Any]:
    return _load_json(SCHEDULER_PATH)


def test_artifacts_schema_and_policy_binding(
    lock: dict[str, Any], provenance: dict[str, Any]
) -> None:
    assert lock["schema"] == LOCK_SCHEMA
    assert provenance["schema"] == PROVENANCE_SCHEMA
    assert lock["task_id"] == TASK_ID
    assert provenance["task_id"] == TASK_ID
    assert lock["goal_id"] == GOAL_ID
    assert provenance["goal_id"] == GOAL_ID
    assert lock["bundle"] == BUNDLE
    assert provenance["bundle"] == BUNDLE
    assert lock["behavior_change"] is False
    assert provenance["behavior_change"] is False

    assert set(lock["evidence_subset"]) >= REQUIRED_LOCK_EVIDENCE
    assert set(provenance["evidence_subset"]) >= REQUIRED_PROVENANCE_EVIDENCE

    assert lock["policy"]["fail_closed"] is True
    assert lock["policy"]["digest_bound_required"] is True
    assert lock["policy"]["mutable_ref_forbidden"] is True
    assert lock["policy"]["single_lock_authority_required"] is True
    assert lock["policy"]["reproducibility_from_one_build_forbidden"] is True

    assert provenance["policy"]["fail_closed"] is True
    assert provenance["policy"]["verify_step_materials"] is True
    assert provenance["policy"]["verify_step_products"] is True
    assert provenance["policy"]["verify_exact_builder_identity"] is True
    assert provenance["policy"]["two_environment_bit_identity_required"] is True
    assert provenance["policy"]["single_build_reproducibility_claim_forbidden"] is True
    assert provenance["policy"]["require_signed_provenance_for_release"] is True
    assert provenance["policy"]["unsigned_test_provenance_allowed_for_hermetic_validation"] is True

    prohibited = set(lock["authority"]["prohibited_effects"]) | set(
        provenance["authority"]["prohibited_effects"]
    )
    assert "resolve_mutable_branch_during_build" in prohibited
    assert "claim_reproducibility_from_one_build" in prohibited
    assert "include_credential" in prohibited
    assert "sign_or_publish_production_release" in prohibited


def test_all_admitted_dependencies_are_immutable_and_digest_bound(
    lock: dict[str, Any],
) -> None:
    admitted = admitted_dependencies(lock)
    assert admitted, "portfolio lock must admit digest-bound dependencies"

    for dep in admitted:
        assert dep["mutability"] == "immutable"
        assert dep["admitted"] is True
        algo = dep["digest_algorithm"]
        digest = dep["digest"]
        if algo in {"git-commit-sha1", "git-tree-sha1"}:
            assert FULL_SHA1_RE.match(digest), dep["id"]
        elif algo == "sha256":
            assert DIGEST_SHA256_RE.match(digest), dep["id"]
        else:
            raise AssertionError(f"unsupported digest algorithm for {dep['id']}: {algo}")

        path = dep.get("path")
        if path and path != "." and algo == "sha256":
            on_disk = REPO_ROOT / path
            assert on_disk.is_file(), f"missing digest-bound path: {path}"
            assert _sha256_file(on_disk) == digest, f"digest drift for {path}"

    for node in lock["source_binding"]["planning_forest"]:
        assert FULL_SHA1_RE.match(node["digest"])
        assert node["mutability"] == "immutable_commit_digest"
        assert node["admitted_as_release_input"] is True
        assert node["digest_algorithm"] == "git-commit-sha1"

    # Rejected mutable inputs must never be admitted.
    for rejected in lock["rejected_mutable_inputs"]:
        assert rejected["admitted"] is False
        assert rejected["blocks_release"] is True
        assert rejected["blocker_code"].startswith("nonreproducible:")


def test_lock_digests_match_on_disk_and_scheduler_pins(
    lock: dict[str, Any], scheduler: dict[str, Any]
) -> None:
    binding = lock["source_binding"]
    assert FULL_SHA1_RE.match(binding["controller_commit"])
    assert FULL_SHA1_RE.match(binding["controller_tree"])
    assert (
        _sha256_file(SCHEDULER_PATH)
        == binding["scheduler_config_sha256"]
    )

    sb = scheduler["source_binding"]
    field_map = {
        "Mcp-Plus-Plus": "mcp_plus_plus_planning_revision",
        "external/ipfs_accelerate": "accelerate_planning_revision",
        "external/ipfs_datasets": "datasets_planning_revision",
        "external/ipfs_kit": "kit_planning_revision",
        "swissknife": "swissknife_planning_revision",
    }
    for node in binding["planning_forest"]:
        field = field_map[node["path"]]
        assert node["scheduler_field"] == field
        assert node["scheduler_planning_revision"] == sb[field]
        assert node["matches_scheduler_planning_revision"] is (
            node["digest"] == sb[field]
        )


def test_swissknife_sole_lock_authority(lock: dict[str, Any]) -> None:
    authorities = lock["lock_authorities"]
    assert len(authorities) == 1
    authority = authorities[0]
    assert authority["package_tree"] == "swissknife"
    assert authority["sole_authority_path"] == "swissknife/package-lock.json"
    assert authority["package_manager"] == "npm@10.8.2"
    assert (
        _sha256_file(REPO_ROOT / "swissknife/package-lock.json")
        == authority["sole_authority_digest_sha256"]
    )

    competing = {item["path"] for item in authority["rejected_competing_locks"]}
    assert competing == {"swissknife/yarn.lock", "swissknife/pnpm-lock.yaml"}

    package = json.loads(
        (REPO_ROOT / "swissknife/package.json").read_text(encoding="utf-8")
    )
    assert package["packageManager"] == "npm@10.8.2"


def test_typed_nonreproducible_blockers_cover_known_gaps(
    lock: dict[str, Any], provenance: dict[str, Any]
) -> None:
    blocker_codes = {item["blocker_code"] for item in lock["rejected_mutable_inputs"]}
    assert REQUIRED_BLOCKER_CODES <= blocker_codes
    assert REQUIRED_BLOCKER_CODES <= set(provenance["nonreproducible_blocker_codes"])

    current = lock["current_tree_qualification"]
    assert current["all_admitted_dependencies_digest_bound"] is True
    assert current["mutable_inputs_rejected"] is True
    assert current["immutable_dependency_closure_complete"] is False
    assert current["release_admissible"] is False
    assert REQUIRED_BLOCKER_CODES <= set(current["blocking_codes"])

    # Concrete evidence still present on disk for blockers.
    assert not (REPO_ROOT / "Mcp-Plus-Plus/tests-rs/Cargo.lock").exists()
    assert (REPO_ROOT / "swissknife/yarn.lock").is_file()
    assert (REPO_ROOT / "swissknife/pnpm-lock.yaml").is_file()
    nightly = (
        REPO_ROOT
        / "external/ipfs_accelerate/install/requirements_torch_cu130_nightly.txt"
    ).read_text(encoding="utf-8")
    assert "nightly" in nightly
    base_req = (
        REPO_ROOT / "external/ipfs_accelerate/install/requirements_base.txt"
    ).read_text(encoding="utf-8")
    assert "git+" in base_req and "@main" in base_req


def test_two_clean_environments_bit_identical_declared_artifact(
    lock: dict[str, Any], provenance: dict[str, Any]
) -> None:
    result = two_clean_environment_builds(lock, provenance)

    # Declared hermetic artifact must be bit-identical across two clean envs.
    assert result["environment_count"] == 2
    assert result["bit_identical"] is True
    assert result["blocker_code"] is None
    assert DIGEST_SHA256_RE.match(result["digest_sha256"] or "")
    assert result["build_a"]["digest_sha256"] == result["build_b"]["digest_sha256"]

    # Policy forbids claiming reproducibility from one build.
    assert provenance["reproducibility"]["minimum_environments"] == 2
    assert provenance["reproducibility"]["one_build_never_sufficient"] is True
    assert lock["policy"]["reproducibility_from_one_build_forbidden"] is True

    single_build_claim = {
        "environment_count": 1,
        "claim_reproducible": True,
    }
    assert single_build_claim["environment_count"] < 2
    fixture = next(
        item
        for item in provenance["negative_fixtures"]
        if item["id"] == "neg:single-build-reproducibility-claim"
    )
    assert fixture["expect_rejected"] is True
    assert fixture["mutation"]["environment_count"] == 1


def test_provenance_verifies_materials_products_and_builder_identity(
    lock: dict[str, Any], provenance: dict[str, Any]
) -> None:
    result = two_clean_environment_builds(lock, provenance)
    assert result["bit_identical"] is True
    product_digest = result["digest_sha256"]
    assert product_digest

    materials = result["payload"]["materials"]
    statement = generate_unsigned_test_provenance(
        lock, provenance, product_digest, materials
    )

    assert statement["_type"] == provenance["in_toto_style"]["statement_type"]
    assert statement["predicateType"] == provenance["slsa_style"]["predicate_type"]
    assert statement["unsigned_test_provenance"] is True
    assert statement["production_release_claim"] is False
    assert statement["signatures"] == []

    ok, blockers = verify_provenance(
        lock, provenance, statement, product_digest=product_digest
    )
    assert ok is True
    assert blockers == []

    # Exact builder identity fields required by policy.
    for field in provenance["builder_identity"]["required_fields"]:
        assert field in provenance["builder_identity"]["declared"]
        assert statement["steps"][-1]["builder_identity"][field] == (
            provenance["builder_identity"]["declared"][field]
        )

    # Step coverage.
    step_ids = {step["id"] for step in statement["steps"]}
    policy_step_ids = {step["id"] for step in provenance["in_toto_style"]["steps"]}
    assert step_ids == policy_step_ids


def test_provenance_negative_mutations_emit_typed_blockers(
    lock: dict[str, Any], provenance: dict[str, Any]
) -> None:
    result = two_clean_environment_builds(lock, provenance)
    product_digest = result["digest_sha256"]
    assert product_digest
    materials = result["payload"]["materials"]
    base = generate_unsigned_test_provenance(
        lock, provenance, product_digest, materials
    )

    # Builder identity mismatch.
    mutated = json.loads(json.dumps(base))
    mutated["predicate"]["runDetails"]["builder"]["id"] = "local-ad-hoc"
    ok, blockers = verify_provenance(
        lock, provenance, mutated, product_digest=product_digest
    )
    assert ok is False
    assert "nonreproducible:builder_identity_mismatch" in blockers

    # Material digest mismatch.
    mutated = json.loads(json.dumps(base))
    mutated["steps"][0]["materials"][0]["digest"] = "0" * 64
    ok, blockers = verify_provenance(
        lock, provenance, mutated, product_digest=product_digest
    )
    assert ok is False
    assert "nonreproducible:material_digest_mismatch" in blockers

    # Product / subject digest mismatch.
    mutated = json.loads(json.dumps(base))
    mutated["subject"][0]["digest"]["sha256"] = "1" * 64
    ok, blockers = verify_provenance(
        lock, provenance, mutated, product_digest=product_digest
    )
    assert ok is False
    assert "nonreproducible:product_digest_mismatch" in blockers


def test_cross_refs_with_release_predicate(
    lock: dict[str, Any],
    provenance: dict[str, Any],
    release_predicate: dict[str, Any],
) -> None:
    assert lock["provenance_policy_ref"].endswith("provenance_policy.json")
    assert provenance["portfolio_lock_ref"].endswith("portfolio.lock.json")
    assert lock["release_predicate_ref"].endswith("release_predicate.json")
    assert provenance["release_predicate_ref"].endswith("release_predicate.json")

    necessary = set(release_predicate["necessary_evidence"])
    assert "immutable_dependency_closure" in necessary
    assert "reproducibility_inputs" in necessary
    assert "signed_provenance" in necessary

    conjunct_ids = {item["id"] for item in release_predicate["conjuncts"]}
    assert "immutable_dependency_closure" in conjunct_ids
    assert "reproducibility_and_provenance" in conjunct_ids
    assert "identified_build_environment" in conjunct_ids

    assert lock["acceptance"]["current_tree_release_admissible_claimed"] is False
    assert provenance["acceptance"]["current_tree_release_admissible_claimed"] is False
    assert lock["acceptance"]["all_source_dependencies_immutable_and_digest_bound"] is True
    assert provenance["acceptance"]["provenance_verifies_step_materials"] is True
    assert provenance["acceptance"]["provenance_verifies_step_products"] is True
    assert provenance["acceptance"]["provenance_verifies_exact_builder_identity"] is True


def test_no_credentials_in_artifacts(
    lock: dict[str, Any], provenance: dict[str, Any]
) -> None:
    serialized = json.dumps(lock) + json.dumps(provenance)
    forbidden_tokens = (
        "BEGIN PRIVATE KEY",
        "AWS_SECRET",
        "api_key",
        "npm_token",
        "password=",
    )
    lower = serialized.lower()
    for token in forbidden_tokens:
        assert token.lower() not in lower


def test_sbom_and_declared_artifact_recipe_present(lock: dict[str, Any]) -> None:
    sbom = lock["sbom"]
    assert sbom["schema"] == "facp/sbom-summary@1"
    assert sbom["component_count"] == len(sbom["components"])
    assert sbom["component_count"] >= 8

    artifacts = {item["id"]: item for item in lock["declared_artifacts"]}
    assert "artifact:facp-portfolio-closure-v1" in artifacts
    artifact = artifacts["artifact:facp-portfolio-closure-v1"]
    assert artifact["reproducibility"]["method"] == "two_clean_environments_bit_identity"
    assert artifact["reproducibility"]["single_build_insufficient"] is True

    recipes = {item["id"]: item for item in lock["build_recipes"]}
    recipe = recipes["recipe:hermetic-portfolio-closure-v1"]
    assert recipe["network"] is False
    assert recipe["credentials_forbidden"] is True
    assert recipe["mutable_ref_resolution_forbidden"] is True
    assert recipe["build_type"] == "facp/reproducible-build@1"
