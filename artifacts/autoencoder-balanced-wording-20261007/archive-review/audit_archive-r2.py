"""Independently verify a completed evidence archive using bounded stdlib I/O.

Never extract members, import numerical owners, or operate on resource leases.
Run only after the parent explicitly signals immutable archive completion.
"""
from __future__ import annotations

import ast
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile

R = Path(__file__).resolve().parents[1]
W = R.parents[1]
RUN = W / "external/ipfs_datasets/workspace/test-logs/decoder-balanced-wording-20261007"
CHUNK = 1_048_576
MAX_SOURCE = 300_000_000
MAX_ARCHIVE = 90_000_000


def identity(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def file_binding(path):
    path = Path(path)
    if path.resolve() != path or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("symbolic source refused: " + str(path))
    before = identity(path.stat())
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        if identity(os.fstat(stream.fileno())) != before:
            raise ValueError("opened source replacement")
        for block in iter(lambda: stream.read(CHUNK), b""):
            count += len(block)
            digest.update(block)
        if identity(os.fstat(stream.fileno())) != before:
            raise ValueError("opened source mutation")
    if identity(path.stat()) != before or count != before[2]:
        raise ValueError("source mutation")
    return {"bytes": count, "sha256": digest.hexdigest()}


def safe_name(name, prefixes):
    if not isinstance(name, str):
        raise ValueError("non-string archive name")
    parts = PurePosixPath(name)
    if parts.is_absolute() or str(parts) != name or any(part in {".", "..", ""} for part in parts.parts):
        raise ValueError("unsafe archive name: " + name)
    if not any(name.startswith(prefix + "/") for prefix in prefixes):
        raise ValueError("foreign archive root: " + name)
    return name


def verify_archive(path, expected_entries, workspace, prefixes, *, compare_local=True,
                   max_source=MAX_SOURCE, max_archive=MAX_ARCHIVE):
    """One bounded payload pass, with independent compressed and local hashes."""
    archive_before = identity(Path(path).stat())
    archive_binding = file_binding(path)
    if identity(Path(path).stat()) != archive_before:
        raise ValueError("archive changed during initial digest")
    if archive_binding["bytes"] > max_archive:
        raise ValueError("compressed cap exceeded")
    expected = {}
    names = []
    for entry in expected_entries:
        if set(entry) != {"path", "bytes", "sha256"}:
            raise ValueError("manifest member schema")
        name = safe_name(entry["path"], prefixes)
        if name in expected:
            raise ValueError("duplicate manifest member")
        if type(entry["bytes"]) is not int or entry["bytes"] < 0:
            raise ValueError("invalid manifest member size")
        if not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in entry["sha256"]):
            raise ValueError("invalid manifest member digest")
        expected[name] = entry
        names.append(name)
    if names != sorted(names, key=lambda name: PurePosixPath(name).parts):
        raise ValueError("manifest order is not deterministic")
    if sum(entry["bytes"] for entry in expected_entries) > max_source:
        raise ValueError("source cap exceeded")
    seen = []
    total = 0
    member_digest = hashlib.sha256()
    with Path(path).open("rb") as raw:
        if identity(os.fstat(raw.fileno())) != archive_before:
            raise ValueError("opened archive replacement")
        with gzip.GzipFile(fileobj=raw, mode="rb") as decompressed:
            with tarfile.open(fileobj=decompressed, mode="r|") as archive:
                for member in archive:
                    name = safe_name(member.name, prefixes)
                    if name in seen:
                        raise ValueError("duplicate tar member")
                    if not member.isfile() or member.sparse is not None or member.linkname:
                        raise ValueError("nonregular tar member")
                    if name not in expected:
                        raise ValueError("unmanifested tar member")
                    entry = expected[name]
                    if member.size != entry["bytes"] or member.mode != 0o644 or member.mtime != 0:
                        raise ValueError("tar member metadata mismatch")
                    digest = hashlib.sha256()
                    count = 0
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise ValueError("unreadable tar member")
                    with stream:
                        for block in iter(lambda: stream.read(CHUNK), b""):
                            count += len(block)
                            digest.update(block)
                    observed = {"path": name, "bytes": count, "sha256": digest.hexdigest()}
                    if observed != entry:
                        raise ValueError("tar payload digest mismatch: " + name)
                    if compare_local and file_binding(Path(workspace) / name) != {"bytes": count, "sha256": digest.hexdigest()}:
                        raise ValueError("current source differs from archived member: " + name)
                    total += count
                    if total > max_source:
                        raise ValueError("streamed source cap exceeded")
                    member_digest.update((json.dumps(observed, sort_keys=True, separators=(",", ":")) + "\n").encode())
                    seen.append(name)
            # Consume remaining padding and the gzip footer, checking CRC/truncation.
            for block in iter(lambda: decompressed.read(CHUNK), b""):
                if any(block):
                    raise ValueError("nonzero material after tar terminator")
        if identity(os.fstat(raw.fileno())) != archive_before:
            raise ValueError("archive changed during read")
    if identity(Path(path).stat()) != archive_before:
        raise ValueError("archive replaced after read")
    if seen != names:
        raise ValueError("missing or out-of-order tar members")
    return {"archive": archive_binding, "member_count": len(seen), "source_bytes": total,
            "ordered_member_bindings_sha256": member_digest.hexdigest(),
            "every_member_matches_manifest": True, "every_member_matches_current_source": compare_local,
            "gzip_footer_crc_and_zero_remaining_padding_verified": True}


def constants_from_retainer(path):
    wanted = {"SUFFIXES", "EXCLUDED_PARTS", "EXCLUDED_NAMES", "MAX_SOURCE_BYTES", "MAX_ARCHIVE_BYTES"}
    tree = ast.parse(Path(path).read_text())
    return {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in wanted}


def main():
    manifest_path = R / "retention-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if manifest["schema"] != "balanced-wording-evidence-retention/v1" or manifest["passed"] is not True or manifest["findings"]:
        raise ValueError("unclean archive manifest")
    constants = constants_from_retainer(R / "retain_evidence.py")
    if constants["MAX_SOURCE_BYTES"] != MAX_SOURCE or constants["MAX_ARCHIVE_BYTES"] != MAX_ARCHIVE:
        raise ValueError("reviewed archive cap drift")
    prefixes = [R.relative_to(W).as_posix(), RUN.relative_to(W).as_posix()]
    archived_path = W / manifest["archive"]["path"]
    if archived_path != R / "balanced-wording-evidence.tar.gz":
        raise ValueError("unexpected archive location")
    result = verify_archive(archived_path, manifest["entries"], W, prefixes)
    if result["archive"] != {key: manifest["archive"][key] for key in ("bytes", "sha256")} or result["source_bytes"] != manifest["source_bytes"]:
        raise ValueError("manifest archive/source aggregate mismatch")
    names = {entry["path"] for entry in manifest["entries"]}
    excluded = set(manifest["excluded_local_bodies"])
    if len(excluded) != len(manifest["excluded_local_bodies"]) or names & excluded:
        raise ValueError("invalid exclusion census")
    if manifest["checkpoint_bodies_archived"] or manifest["prepared_embedding_bodies_archived"] or manifest["model_execution_performed"] or manifest["qualification_granted"]:
        raise ValueError("archive execution/qualification claim drift")
    if manifest.get("embedding_exclusion_scope") != "raw producer output and prepared source/bank inventories" or manifest.get("retained_vector_observations") != "inherited reconstructed_input outputs and normalized training feature observations":
        raise ValueError("native inventory/output observation scope drift")
    root_prefix = prefixes[0] + "/"
    run_prefix = prefixes[1] + "/"
    required = [
        root_prefix + name for name in [
            "README.md", "RESULTS.md", "initial-state.json", "retain_evidence.py", "predeclared-comparison-protocol.json",
            "documentation/reconstruction-decision.json", "documentation/sampled-outputs.json",
            "documentation-review/evidence-documentation-and-retention-source-review.json",
            "candidates/source-results-freeze.json", "candidates/source/build_balanced_wording_candidates.py",
            "review/candidate-pair-independent-review-draft-r3.json",
            "preparation-review/actual-preparation-r2-audit.json",
            "preflight-review/failed-preflight-384-r1-independent-review.json",
            "preflight-review/actual-preflight-384-r2-independent-review.json",
            "training-review/failed-training-384-r1-independent-review.json",
            "training-review/actual-training-384-r2-independent-review.json",
            "training-review/actual-training-384-r2-compact.json",
            "evaluation-review/actual-evaluation-r1-independent-review.json",
            "evaluation-review/actual-evaluation-r1-compact.json",
            "evaluation-review/actual-evaluation-r1-parent-comparison.json",
            "next-retention-plan/dual_bank_retention.py", "next-retention-plan/test_dual_bank_retention.py", "next-retention-plan/design.md",
            "archive-review/audit_archive.py", "archive-review/test_audit_archive.py", "archive-review/auditor-source-freeze.json",
        ]
    ]
    required += [root_prefix + f"candidates/results/draft-r{revision}/{name}.json"
                 for revision in (1, 2, 3) for name in ("candidate-bank", "rejected-drafts", "original90-target-identities", "overlap-and-exposure")]
    successes = ("preparation-r2", "preflight-384-r2", "training-384-r2", "evaluation-r1")
    failures = ("preflight-384-r1", "training-384-r1")
    required += [run_prefix + phase + suffix for phase in successes for suffix in ("-guardian-exit.json", "/resources-final.json", "/child-exit.json", "/results/summary.json")]
    required += [run_prefix + phase + suffix for phase in failures for suffix in ("-guardian-exit.json", "/failure.json", "/child.log", "/child-exit.json")]
    for arm in ("control-wording-ce", "balanced-wording-ce"):
        required.append(run_prefix + "training-384-r2/results/" + arm + "/training.json")
        for role in ("selected", "last-attempt"):
            for cohort in ("original_train48", "normative_train48", "new_balanced_train48", "exposed_v3_48"):
                for name in ("actual-formula-fidelity.json", "source-head-trace.json", "actual-predictions.json"):
                    required.append(run_prefix + "evaluation-r1/results/" + arm + "/" + role + "/" + cohort + "/" + name)
    missing = sorted(set(required) - names)
    if missing:
        raise ValueError("required evidence missing: " + json.dumps(missing))
    included_run = set()
    excluded_run = set()
    for path in RUN.rglob("*"):
        if not path.is_file() or path.suffix not in constants["SUFFIXES"]:
            continue
        relative = path.relative_to(W).as_posix()
        checkpoint = path.name in {"initial-state.json", "selected-state.json", "last-attempt-state.json"}
        if constants["EXCLUDED_PARTS"].intersection(path.parts) or path.name in constants["EXCLUDED_NAMES"] or checkpoint:
            excluded_run.add(relative)
            continue
        if "pipeline" in path.relative_to(RUN).parts or path.name in {"publish_integration.py", "publisher_review_tests.py", "prepare_publication.py"}:
            continue
        included_run.add(relative)
    if not included_run <= names or not excluded_run <= excluded:
        raise ValueError("incomplete actual RUN evidence/exclusion census")
    for name in names:
        path = PurePosixPath(name)
        if constants["EXCLUDED_PARTS"].intersection(path.parts) or path.name in constants["EXCLUDED_NAMES"]:
            raise ValueError("excluded cache/status/publication body retained")
        if name.startswith(run_prefix) and path.name in {"initial-state.json", "selected-state.json", "last-attempt-state.json"}:
            raise ValueError("actual model checkpoint body retained")
        if path.suffix not in constants["SUFFIXES"] or "pipeline" in path.parts:
            raise ValueError("foreign archive suffix/scope")
    bindings = {
        str(manifest_path): file_binding(manifest_path),
        str(archived_path): file_binding(archived_path),
        str(Path(__file__)): file_binding(Path(__file__)),
        str(R / "retain_evidence.py"): file_binding(R / "retain_evidence.py"),
        str(R / "archive-review/auditor-source-freeze.json"): file_binding(R / "archive-review/auditor-source-freeze.json"),
    }
    report = {
        "schema": "balanced-wording-completed-archive-independent-review/v1", "passed": True, "findings": [],
        "artifacts": bindings, "streamed_archive_result": result,
        "required_member_count": len(set(required)), "all_required_members_present": True,
        "all_current_completed_RUN_eligible_members_present": True,
        "current_RUN_eligible_member_count": len(included_run), "current_RUN_excluded_body_count": len(excluded_run),
        "checkpoint_bodies_archived": False, "raw_native_source_inventory_bodies_archived": False,
        "saved_vector_valued_forward_output_observations_retained": True,
        "source_cap_bytes": MAX_SOURCE, "compressed_cap_bytes": MAX_ARCHIVE,
        "qualified": False, "admitted": False, "proof_authority": False, "lake_executed": False,
        "Constitution_formalized": False, "model_execution_performed": False,
        "numerical_auditors_rerun": False, "resource_or_foreign_scheduler_actions_performed": False,
        "limits": [
            "Every semantic tar member is streamed and hashed without extraction; gzip CRC/padding and compressed physical bytes are verified.",
            "Each member is matched to its frozen manifest and current source with descriptor/path identity fences.",
            "Model checkpoint and raw prepared native-cache/bank inventories are excluded; references and inherited vector-valued numerical observations remain.",
            "Completeness checks bind selected required artifacts and all current eligible completed RUN evidence; the manifest does not attest unrelated external owner trees.",
            "Archive integrity grants no semantic/proof/runtime admission, replication or fresh-holdout authority.",
        ],
    }
    output = Path(__file__).parent / "actual-archive-independent-review.json"
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"path": str(output), **file_binding(output), **result}))


if __name__ == "__main__":
    main()
