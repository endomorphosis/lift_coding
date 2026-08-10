#!/usr/bin/env python3
"""Emit / accept operator approval records for historic PTR tasks.

Historic tasks PTR-000, PTR-001, PTR-011, and PTR-041 cannot close from
managed-merge queue rows alone.  This tool:

1. ``draft`` — writes unsigned draft approval (and retrospective) records
   bound to the current clean checkout identity and task CIDs.
2. ``accept`` — records an explicit local operator attestation and seals
   the approval so the task-evidence collector can consume it.

Approvals are **not** invented: ``accept`` requires an explicit operator id
and writes an attestation that the operator reviewed the bound commit and
task CID.  This is a local operator control, not a substitute for external
ceremony or production key authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
TODO_REL = "implementation_plan/docs/46-proof-backed-test-reuse.todo.md"
OBJECTIVE_REL = "implementation_plan/docs/46-proof-backed-test-reuse.objectives.md"
STATE_ROOT = Path(
    os.environ.get(
        "IPFS_ACCELERATE_PROOF_REUSE_STATE_ROOT",
        str(
            Path.home()
            / ".local"
            / "state"
            / "ipfs_accelerate_py"
            / "proof-backed-test-reuse-v1"
        ),
    )
)
APPROVAL_DIR = STATE_ROOT / "projection" / "completion" / "operator_approvals"
IDENTITY_SNAPSHOT = (
    STATE_ROOT
    / "projection"
    / "completion"
    / "validation_receipts"
    / "identity_snapshot.json"
)

HISTORIC_TASKS = ("PTR-000", "PTR-001", "PTR-011", "PTR-041")


def _ensure_accel() -> None:
    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _content_identity(payload: dict[str, Any]) -> str:
    _ensure_accel()
    from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import (
        content_identity,
    )

    return content_identity(payload)


def _seal(body: dict[str, Any], field: str) -> dict[str, Any]:
    payload = {k: v for k, v in body.items() if k != field}
    return {**payload, field: _content_identity(payload)}


def _load_identity() -> dict[str, Any]:
    # Prefer the live clean checkout. A stale validation-receipt identity
    # snapshot must not re-bind historic approvals to a previous tip after a
    # tip advance (otherwise --require-ready fails with APPROVAL_TARGET_NOT_CURRENT).
    dirty = bool(_git("status", "--porcelain"))
    if dirty:
        raise SystemExit("checkout is dirty; rebind validation receipts first")
    commit = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    live = {
        "repository_id": "lift_coding/proof-backed-test-reuse",
        "repository_state_cid": f"git-commit:{commit}",
        "git_commit_id": commit,
        "git_tree_id": tree,
        "gitlink_state_cid": "gitlinks:unresolved",
        "repository_forest_cid": "forest:unresolved",
        "dirty": False,
        "dirty_overlay_cid": "cid:dirty-overlay:none",
        "policy_cid": "policy:proof-backed-test-reuse-v1",
    }
    if IDENTITY_SNAPSHOT.is_file():
        try:
            snap = json.loads(IDENTITY_SNAPSHOT.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            snap = {}
        identity = snap.get("identity") if isinstance(snap, dict) else None
        if isinstance(identity, dict) and identity.get("git_commit_id") == commit:
            # Same tip: reuse snapshot pins (forest/gitlink/policy) when present.
            merged = dict(live)
            for key in (
                "gitlink_state_cid",
                "repository_forest_cid",
                "policy_cid",
                "capability_cid",
                "verifying_key_cid",
                "circuit_cid",
                "dirty_overlay_cid",
            ):
                if identity.get(key):
                    merged[key] = identity[key]
            if "dirty" in identity:
                merged["dirty"] = bool(identity["dirty"])
            return merged
    return live


def _task_cids() -> dict[str, str]:
    _ensure_accel()
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )

    tasks = parse_task_file(REPO_ROOT / TODO_REL, "## PTR-")
    return {t.task_id: t.canonical_task_cid for t in tasks}


def _objective_revision() -> str:
    data = (REPO_ROOT / OBJECTIVE_REL).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    return f"objective-sha256:{digest}"


def _planning_seal_cid(objective_revision: str, head: str) -> str:
    return _content_identity(
        {
            "kind": "planning_seal",
            "objective_revision": objective_revision,
            "head_commit": head,
            "board_namespace": "proof-backed-test-reuse-v1",
        }
    )


def _integration_receipt_cid(task_id: str, commit: str, target: str) -> str:
    return _content_identity(
        {
            "kind": "integration_receipt",
            "task_id": task_id,
            "integrated_commit_id": commit,
            "integration_target_commit_id": target,
        }
    )


def draft_records(
    *,
    identity: dict[str, Any],
    task_cids: dict[str, str],
    reviewer_placeholder: str = "operator@local",
) -> dict[str, Any]:
    head = str(identity["git_commit_id"])
    objective_revision = _objective_revision()
    policy_cid = str(identity.get("policy_cid") or "policy:proof-backed-test-reuse-v1")
    capability_cid = str(
        identity.get("capability_cid") or "capability:proof-backed-test-reuse-v1"
    )
    key_cid = str(identity.get("verifying_key_cid") or "key:activation-gap-none")
    circuit_cid = str(identity.get("circuit_cid") or "circuit:test-pass-v4")

    drafts: dict[str, Any] = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-operator-approval-drafts@1",
        "authority": False,
        "status": "draft",
        "head_commit": head,
        "objective_revision": objective_revision,
        "policy_cid": policy_cid,
        "capability_cid": capability_cid,
        "verifying_key_cid": key_cid,
        "circuit_cid": circuit_cid,
        "tasks": {},
        "instructions": [
            "Review each draft approval against the bound commit and task CID.",
            "Run: python3 scripts/emit_proof_backed_test_reuse_operator_approvals.py accept --operator-id YOU@example.com",
            "Then re-run: python3 scripts/materialize_proof_backed_test_reuse_closeout_inputs.py",
            "These local attestations are operator-owned closeout inputs, not production skip keys.",
        ],
    }

    for task_id in HISTORIC_TASKS:
        task_cid = task_cids[task_id]
        if task_id == "PTR-000":
            body = {
                "task_id": task_id,
                "task_cid": task_cid,
                "kind": "operator_planning_seal",
                "approved": True,
                "reviewer_id": reviewer_placeholder,
                "planning_seal_cid": _planning_seal_cid(objective_revision, head),
                "sealed_objective_revision": objective_revision,
                "integrated_commit_id": head,
                "integration_target_commit_id": head,
            }
            sealed = _seal(body, "approval_cid")
            drafts["tasks"][task_id] = {
                "approval": sealed,
                "retrospective": None,
                "required_kind": "operator_planning_seal",
            }
            continue
        if task_id in {"PTR-001", "PTR-011"}:
            body = {
                "task_id": task_id,
                "task_cid": task_cid,
                "kind": "operator_reviewed_integration",
                "approved": True,
                "reviewer_id": reviewer_placeholder,
                "integrated_commit_id": head,
                "integration_target_commit_id": head,
                "integration_receipt_cid": _integration_receipt_cid(
                    task_id, head, head
                ),
            }
            sealed = _seal(body, "approval_cid")
            drafts["tasks"][task_id] = {
                "approval": sealed,
                "retrospective": None,
                "required_kind": "operator_reviewed_integration",
            }
            continue
        # PTR-041 retrospective
        retrospective_body = {
            "task_id": task_id,
            "task_cid": task_cid,
            "integrated_commit_id": head,
            "kind": "retrospective_history",
        }
        retrospective = _seal(retrospective_body, "ancestry_receipt_cid")
        approval_body = {
            "task_id": task_id,
            "task_cid": task_cid,
            "kind": "retrospective_review",
            "approved": True,
            "reviewer_id": reviewer_placeholder,
            "integrated_commit_id": head,
            "approved_policy_cid": policy_cid,
        }
        approval = _seal(approval_body, "policy_approval_cid")
        drafts["tasks"][task_id] = {
            "approval": approval,
            "retrospective": retrospective,
            "required_kind": "retrospective_review",
        }
    return drafts


def accept_drafts(
    *,
    operator_id: str,
    identity: dict[str, Any],
    drafts: dict[str, Any],
) -> dict[str, Any]:
    if not operator_id.strip() or "@" not in operator_id:
        raise SystemExit("--operator-id must look like an email / operator identity")
    accepted_at_ms = int(time.time() * 1000)
    head = str(identity["git_commit_id"])
    out: dict[str, Any] = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-operator-approvals@1",
        "authority": False,
        "status": "accepted",
        "operator_id": operator_id.strip(),
        "head_commit": head,
        "accepted_at_ms": accepted_at_ms,
        "approvals": {},
        "retrospectives": {},
        "attestations": {},
        "policy_cid": drafts.get("policy_cid"),
        "capability_cid": drafts.get("capability_cid"),
        "verifying_key_cid": drafts.get("verifying_key_cid"),
        "circuit_cid": drafts.get("circuit_cid"),
        "objective_revision": drafts.get("objective_revision"),
    }
    for task_id, payload in (drafts.get("tasks") or {}).items():
        approval = dict(payload["approval"])
        approval["reviewer_id"] = operator_id.strip()
        # Re-seal after reviewer_id replacement.
        field = (
            "policy_approval_cid"
            if task_id == "PTR-041"
            else "approval_cid"
        )
        approval.pop("approval_cid", None)
        approval.pop("policy_approval_cid", None)
        approval.pop("operator_approval_cid", None)
        approval = _seal(approval, field)
        out["approvals"][task_id] = approval
        if payload.get("retrospective"):
            out["retrospectives"][task_id] = payload["retrospective"]
        attestation_body = {
            "task_id": task_id,
            "operator_id": operator_id.strip(),
            "head_commit": head,
            "task_cid": approval["task_cid"],
            "approval_cid": approval[field],
            "accepted": True,
            "accepted_at_ms": accepted_at_ms,
            "statement": (
                f"I, {operator_id.strip()}, reviewed task {task_id} at commit "
                f"{head} and accept this historic completion approval for "
                "proof-backed-test-reuse closeout inputs only."
            ),
        }
        out["attestations"][task_id] = _seal(attestation_body, "attestation_cid")
    return out


def write_runbook(path: Path, drafts: dict[str, Any]) -> None:
    lines = [
        "# Operator approvals for proof-backed test reuse",
        "",
        "Historic tasks still require explicit operator/reviewer provenance:",
        "",
        "| Task | Kind |",
        "| --- | --- |",
        "| PTR-000 | operator_planning_seal |",
        "| PTR-001 | operator_reviewed_integration |",
        "| PTR-011 | operator_reviewed_integration |",
        "| PTR-041 | retrospective_review + history |",
        "",
        f"Bound head: `{drafts.get('head_commit')}`",
        f"Objective revision: `{drafts.get('objective_revision')}`",
        "",
        "## Accept",
        "",
        "```bash",
        "python3 scripts/emit_proof_backed_test_reuse_operator_approvals.py accept \\",
        "  --operator-id you@example.com",
        "python3 scripts/materialize_proof_backed_test_reuse_closeout_inputs.py",
        "```",
        "",
        "These local attestations close **task evidence** gaps only. They do not",
        "install production Groth16 keys or authorize warm skip by themselves.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("draft", help="Write unsigned draft approvals")
    acc = sub.add_parser("accept", help="Accept drafts with an operator id")
    acc.add_argument("--operator-id", required=True)
    sub.add_parser("status", help="Show approval directory status")
    args = parser.parse_args(argv)

    APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    identity = _load_identity()
    task_cids = _task_cids()

    if args.cmd == "draft":
        drafts = draft_records(identity=identity, task_cids=task_cids)
        _write(APPROVAL_DIR / "drafts.json", drafts)
        write_runbook(APPROVAL_DIR / "OPERATOR_APPROVALS.md", drafts)
        for task_id, payload in drafts["tasks"].items():
            _write(APPROVAL_DIR / f"{task_id}.draft.json", payload)
        print(
            json.dumps(
                {
                    "status": "draft",
                    "path": str(APPROVAL_DIR / "drafts.json"),
                    "runbook": str(APPROVAL_DIR / "OPERATOR_APPROVALS.md"),
                    "head_commit": drafts["head_commit"],
                    "tasks": list(HISTORIC_TASKS),
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "accept":
        draft_path = APPROVAL_DIR / "drafts.json"
        if not draft_path.is_file():
            drafts = draft_records(identity=identity, task_cids=task_cids)
            _write(draft_path, drafts)
        else:
            drafts = json.loads(draft_path.read_text(encoding="utf-8"))
        if drafts.get("head_commit") != identity.get("git_commit_id"):
            # Re-draft against current head so approvals stay bound.
            drafts = draft_records(identity=identity, task_cids=task_cids)
            _write(draft_path, drafts)
        accepted = accept_drafts(
            operator_id=args.operator_id,
            identity=identity,
            drafts=drafts,
        )
        _write(APPROVAL_DIR / "accepted.json", accepted)
        for task_id, approval in accepted["approvals"].items():
            _write(APPROVAL_DIR / f"{task_id}.approval.json", approval)
        for task_id, retro in accepted["retrospectives"].items():
            _write(APPROVAL_DIR / f"{task_id}.retrospective.json", retro)
        for task_id, att in accepted["attestations"].items():
            _write(APPROVAL_DIR / f"{task_id}.attestation.json", att)
        print(
            json.dumps(
                {
                    "status": "accepted",
                    "path": str(APPROVAL_DIR / "accepted.json"),
                    "operator_id": accepted["operator_id"],
                    "tasks": sorted(accepted["approvals"]),
                    "next": "python3 scripts/materialize_proof_backed_test_reuse_closeout_inputs.py",
                },
                indent=2,
            )
        )
        return 0

    # status
    accepted = APPROVAL_DIR / "accepted.json"
    drafts = APPROVAL_DIR / "drafts.json"
    print(
        json.dumps(
            {
                "approval_dir": str(APPROVAL_DIR),
                "drafts_present": drafts.is_file(),
                "accepted_present": accepted.is_file(),
                "files": sorted(p.name for p in APPROVAL_DIR.glob("*")),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
