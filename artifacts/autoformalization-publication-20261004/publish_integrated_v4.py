"""Extend the frozen V3 Git publisher with explicitly mapped HF-reference history.

The owner retains normal fast-forward publication, resource bounds and receipts.
This extension checks mapped ancestry separately from original local history.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

OWNER = Path(__file__).with_name("huggingface") / "publish_integrated_v3.py"
OWNER_SHA = "0228657ee7390fbfd5d2dc3b97e00eed3e7e3d311eaf54264fe01f7b6ce41d5f"
owner_bytes = OWNER.read_bytes()
if hashlib.sha256(owner_bytes).hexdigest() != OWNER_SHA:
    raise ValueError("frozen publisher owner differs")
CTX = {"__name__": "frozen_publisher_owner", "__file__": __file__}
exec(compile(owner_bytes, str(OWNER), "exec"), CTX)
require, raw, selected_json = (CTX[name] for name in ("require", "raw", "selected_json"))
OID, safe_path, committed_tree = (CTX[name] for name in ("OID", "safe_path", "committed_tree"))
BASE_PREPARED = CTX["check_prepared"]
BASE_PROFILE = CTX["check_prepared_fulltree_profile"]
BASE_TREE = CTX["check_full_canonical_tree"]
BASE_SAVE = CTX["sealed_save"]
PROFILE = "worktree-main-integration-hf-reference-prepublication/v3"
MANIFEST = "converted-canonical-snapshot-blob-pins/v1"


def pinned(binding):
    require(type(binding) is dict and set(binding) == {"path", "bytes", "sha256"}, "closed external file binding required")
    value, observed = selected_json(binding["path"], binding["sha256"])
    require(observed == binding, "selected file byte count differs")
    require(value.get("content_sha256") == hashlib.sha256(raw({k: v for k, v in value.items()
            if k != "content_sha256"})).hexdigest(), "selected producer seal differs")
    return value


def conversion(plan, binding):
    report = pinned(binding)
    require(report.get("schema") == "isolated-hf-history-reference-conversion/v1", "conversion schema differs")
    for key in ("all_mapped_selected_heads_ancestors", "published_main_unchanged_and_ancestor",
                "original_repository_state_preserved"):
        require(report.get(key) is True, "conversion qualification differs: " + key)
    for key in ("original_rewritten_commit_oids_remote_ancestry_claimed", "signature_headers_modified",
                "git_lfs_migration_executed", "git_lfs_upload_executed", "origin_push_executed",
                "hf_upload_executed", "training_executed"):
        require(report.get(key) is False, "conversion scope differs: " + key)
    require(report.get("newly_reachable_oversized_git_blob_count") == 0, "oversized conversion result rejected")
    mapping = report.get("commit_map")
    require(type(mapping) is dict and all(OID.fullmatch(old) and OID.fullmatch(new)
            for old, new in mapping.items()), "ordinary commit mapping required")
    require(mapping.get(report["original_tip"], report["original_tip"]) == report["converted_tip"], "converted tip mapping differs")
    require(plan["heads"] == report["mapped_selected_heads"], "mapped selected heads differ")
    for head in plan["heads"]:
        require(OID.fullmatch(head["original_oid"]) and mapping.get(head["original_oid"], head["original_oid"]) == head["oid"],
                "selected original-to-mapped head differs")
    receipts = []
    for selected in plan.get("hf_artifact_publication_receipts", []):
        receipt = pinned(selected)
        require(receipt.get("schema") == "append-only-HF-publication/v1"
                and receipt.get("status") == "published_and_verified"
                and receipt.get("all_remote_files_verified") is True, "verified HF publication receipt required")
        receipts.append(receipt)
    references = report.get("references")
    require(type(references) is dict and references and receipts, "selected HF references and receipts required")
    require(set(report["reference_blob_oids"]) == set(references), "complete reference blob identities required")
    for path, reference in references.items():
        safe_path(path)
        require(reference.get("original_path") == path and OID.fullmatch(reference["source_git_blob_oid"]), "exact original artifact identity required")
        require(type(reference["bytes"]) is int and reference["bytes"] >= 0, "ordinary artifact byte count required")
        require(type(reference["sha256"]) is str and len(reference["sha256"]) == 64, "artifact SHA required")
        matches = [r for r in receipts if (r["repo_id"], r["repo_type"], r["commit_oid"]) ==
                   (reference["hf_repo_id"], reference["hf_repo_type"], reference["hf_revision"])]
        require(len(matches) == 1, "unique immutable HF publication join required")
        files = [row for row in matches[0]["remote_files"] if row["path"] == reference["hf_path"]]
        require(len(files) == 1 and files[0]["bytes"] == reference["bytes"]
                and files[0]["sha256"] == reference["sha256"], "HF reference byte identity differs")
        payload = raw(reference) + b"\n"
        expected = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
        require(report["reference_blob_oids"][path] == expected, "reference Git blob content differs")
    return report


def transform(tree, report):
    expected = dict(tree)
    substitutions = []
    for path, reference in report["references"].items():
        old = expected.get(path)
        if old is None or old["oid"] != reference["source_git_blob_oid"]:
            continue
        adjacent = path + ".hf.json"
        require(old["kind"] == "blob" and old["mode"] in {"100644", "100755"}
                and adjacent not in expected, "reference substitution collision or mode differs")
        payload = raw(reference) + b"\n"
        new = {"mode": old["mode"], "kind": "blob", "oid": report["reference_blob_oids"][path]}
        del expected[path]
        expected[adjacent] = new
        substitutions.append({"original_path": path, "original_mode": old["mode"], "original_git_oid": old["oid"],
            "reference_path": adjacent, "reference_mode": new["mode"], "reference_git_oid": new["oid"],
            "reference_bytes": len(payload), "reference_sha256": hashlib.sha256(payload).hexdigest()})
    return expected, sorted(substitutions, key=lambda row: row["original_path"])


def audit_history(ops, repo, report):
    """Check complete raw commit and tree transformations without reading payloads."""
    preflight = pinned(report["preflight_binding"])
    excluded = preflight["published_commit_exclusions"]
    require(type(excluded) is list and excluded and all(OID.fullmatch(oid) for oid in excluded), "published history exclusions required")
    original_commits = set(ops.text(repo, ["rev-list", report["original_tip"], "--not", *excluded]).splitlines())
    require(original_commits == set(report["commit_map"]), "conversion omits unpublished historical commits")
    trees = {}
    for row in report["tree_map"]:
        require(set(row) == {"old", "prefix", "new"} and OID.fullmatch(row["old"]) and OID.fullmatch(row["new"]), "closed tree mapping required")
        prefix = row["prefix"]
        require(type(prefix) is str and (prefix == "" or prefix.endswith("/")), "tree path prefix required")
        if prefix:
            safe_path(prefix[:-1])
        require((row["old"], prefix) not in trees, "duplicate contextual tree mapping")
        trees[row["old"], prefix] = row["new"]
    ids = sorted(set(report["commit_map"]) | set(report["commit_map"].values()) |
                 {row["old"] for row in report["tree_map"]} | {row["new"] for row in report["tree_map"]})
    objects = {}
    for start in range(0, len(ids), 128):
        selected = ids[start:start + 128]
        data, _ = ops.run(repo, ["cat-file", "--batch"], input_data="".join(oid + "\n" for oid in selected).encode())
        offset = 0
        for oid in selected:
            end = data.index(b"\n", offset)
            header = data[offset:end].split()
            require(len(header) == 3 and header[0].decode() == oid and header[1] in {b"commit", b"tree"}, "historical metadata identity differs")
            size = int(header[2])
            require(0 <= size <= 32 * 1024 ** 2, "bounded historical metadata required")
            offset = end + 1
            body = data[offset:offset + size]
            require(len(body) == size and data[offset + size:offset + size + 1] == b"\n", "historical metadata truncation")
            objects[oid] = (header[1], body)
            offset += size + 1
        require(offset == len(data), "unexpected historical metadata output")
    for old, new in report["commit_map"].items():
        require(objects[old][0] == objects[new][0] == b"commit", "mapped commit type differs")
        header, separator, message = objects[old][1].partition(b"\n\n")
        require(separator and b"\ngpgsig " not in header and b"\nmergetag " not in header, "signed or malformed historical commit rejected")
        expected = []
        for line in header.split(b"\n"):
            if line.startswith(b"tree "):
                key = (line[5:].decode(), "")
                require(key in trees, "historical root tree omitted")
                line = b"tree " + trees[key].encode()
            elif line.startswith(b"parent "):
                parent = line[7:].decode()
                line = b"parent " + report["commit_map"].get(parent, parent).encode()
            expected.append(line)
        require(objects[new][1] == b"\n".join(expected) + separator + message,
                "mapped commit changes author, committer, message or unrelated headers")
    for (old, prefix), new in trees.items():
        require(objects[old][0] == objects[new][0] == b"tree", "mapped tree type differs")
        source, entries, offset = objects[old][1], [], 0
        while offset < len(source):
            space = source.index(b" ", offset)
            end = source.index(b"\0", space)
            require(end + 21 <= len(source), "truncated historical tree entry")
            entries.append((source[offset:space], source[space + 1:end], source[end + 1:end + 21].hex()))
            offset = end + 21
        names, expected = {row[1] for row in entries}, []
        for mode, name, oid in entries:
            path = prefix + name.decode("utf-8", "surrogateescape")
            if mode == b"40000" and any(target.startswith(path + "/") for target in report["references"]):
                require((oid, path + "/") in trees, "historical affected subtree omitted")
                oid = trees[oid, path + "/"]
            elif path in report["references"] and oid == report["references"][path]["source_git_blob_oid"]:
                require(mode in {b"100644", b"100755"} and name + b".hf.json" not in names, "historical HF reference collision")
                name, oid = name + b".hf.json", report["reference_blob_oids"][path]
            expected.append((mode, name, oid))
        expected.sort(key=lambda row: row[1] + (b"/" if row[0] == b"40000" else b"\0"))
        body = b"".join(mode + b" " + name + b"\0" + bytes.fromhex(oid) for mode, name, oid in expected)
        require(objects[new][1] == body, "historical tree changes unrelated source or modes")
    return {"mapped_raw_commits_verified": len(report["commit_map"]), "contextual_raw_tree_mappings_verified": len(trees),
            "published_history_excluded_at_selected_preflight": True, "original_raw_payloads_read": False,
            "raw_author_committer_message_and_parent_mapping_verified": True}


def check_prepared(ops, plan, prepared):
    if prepared.get("schema") != PROFILE:
        return BASE_PREPARED(ops, plan, prepared)
    # Only adapt the schema dispatch. The owner checks the actual mapped plan
    # heads, clean worktree, branch, origin, tip, baseline and source ancestry.
    return BASE_PREPARED(ops, plan, {**prepared, "schema": "worktree-main-integration-fulltree-prepublication/v2"})


def check_full_canonical_tree(ops, repo, tree, plan, tip):
    selected = plan.get("authoritative_full_tree_snapshot", {})
    manifest, _ = selected_json(selected["manifest_binding"]["path"], selected["manifest_binding"]["sha256"])
    if manifest.get("schema") != MANIFEST:
        return BASE_TREE(ops, repo, tree, plan, tip)
    manifest = pinned(selected["manifest_binding"])
    require(set(manifest) == {"schema", "repository", "original_snapshot_commit", "mapped_snapshot_commit",
        "original_manifest_binding", "conversion_receipt_binding", "canonical_blob_path_count",
        "canonical_gitlinks_deferred", "explicit_hf_substitutions", "final_canonical_snapshot_tree_exactly_preserved",
        "origin_push_executed", "training_executed", "content_sha256"}, "closed converted fulltree manifest required")
    require(Path(manifest["repository"]).resolve() == Path(plan["canonical_repository"]).resolve()
            and manifest["origin_push_executed"] is False and manifest["training_executed"] is False,
            "converted manifest repository or scope differs")
    report = conversion(plan, manifest["conversion_receipt_binding"])
    original, mapped = manifest["original_snapshot_commit"], manifest["mapped_snapshot_commit"]
    require(OID.fullmatch(original) and report["commit_map"].get(original, original) == mapped
            and selected["snapshot_commit"] == mapped, "canonical snapshot mapping differs")
    original_manifest = pinned(manifest["original_manifest_binding"])
    require(original_manifest.get("schema") == "complete-canonical-snapshot-blob-pins/v1", "original complete snapshot profile required")
    original_tree = committed_tree(ops, repo, original)
    original_plan = {**plan, "published_gitlinks": [], "authoritative_full_tree_snapshot": {
        "snapshot_commit": original, "manifest_binding": manifest["original_manifest_binding"]}}
    BASE_TREE(ops, repo, original_tree, original_plan, original)
    canonical = committed_tree(ops, repo, mapped)
    expected, substitutions = transform(original_tree, report)
    require(canonical == expected and manifest["explicit_hf_substitutions"] == substitutions,
            "mapped canonical tree differs from exact permitted HF substitutions")
    require(type(manifest["final_canonical_snapshot_tree_exactly_preserved"]) is bool
            and manifest["final_canonical_snapshot_tree_exactly_preserved"] == (canonical == original_tree),
            "canonical tree preservation declaration differs")
    links = [{"path": name, "mode": entry["mode"], "git_oid": entry["oid"]}
             for name, entry in sorted(canonical.items()) if entry["kind"] == "commit"]
    require(manifest["canonical_gitlinks_deferred"] == links, "converted canonical gitlinks differ")
    blobs = sum(entry["kind"] == "blob" for entry in canonical.values())
    require(manifest["canonical_blob_path_count"] == blobs, "converted canonical blob count differs")
    ops.run(repo, ["merge-base", "--is-ancestor", mapped, tip])
    overrides = {safe_path(row["path"]): row["oid"] for row in plan.get("published_gitlinks", [])}
    for name, entry in canonical.items():
        wanted = entry
        if name in overrides:
            require(entry["kind"] == "commit", "published gitlink cannot replace canonical blob")
            wanted = {"mode": "160000", "kind": "commit", "oid": overrides[name]}
        require(tree.get(name) == wanted, "complete converted canonical entry differs: " + name)
    deleted = [row["path"] for row in original_manifest["authoritative_source"]["selected_files"] if row["state"] == "deleted"]
    for name in deleted:
        require(name not in tree and not any(p.startswith(name + "/") for p in tree), "intentional deletion remains")
    return {"schema": "committed-full-canonical-tree-verification/v1", "manifest_binding": selected["manifest_binding"],
        "manifest_schema": MANIFEST, "canonical_snapshot_commit": mapped,
        "canonical_snapshot_tree_oid": ops.text(repo, ["rev-parse", mapped + "^{tree}"]),
        "canonical_tree_identity_rows_sha256": hashlib.sha256(raw(canonical)).hexdigest(),
        "canonical_blob_paths_verified": blobs, "canonical_gitlink_paths_verified": len(links),
        "intentional_deleted_paths_verified": len(deleted), "manifest_complete_against_committed_snapshot": True,
        "all_canonical_modes_kinds_GitOIDs_joined": True, "branch_only_additions_allowed": True,
        "full_blob_sha256_rehashed_by_this_publisher": False, "explicit_HF_substitution_count": len(substitutions),
        "conversion_receipt_binding": manifest["conversion_receipt_binding"],
        "scope": "complete_mapped_canonical_tree_and_exact_HF_substitutions_with_verified_published_gitlink_overrides"}


def check_profile(ops, repo, plan, prepared, plan_binding, fulltree):
    if prepared["schema"] != PROFILE:
        return BASE_PROFILE(ops, repo, plan, prepared, plan_binding, fulltree)
    require(prepared.get("content_sha256") == hashlib.sha256(raw({k: v for k, v in prepared.items()
            if k != "content_sha256"})).hexdigest(), "mapped prepared seal differs")
    require(prepared["plan_binding"] == plan_binding and prepared["fulltree_manifest_binding"] ==
            plan["authoritative_full_tree_snapshot"]["manifest_binding"], "mapped prepared bindings differ")
    require(prepared["conversion_receipt_binding"] == fulltree["conversion_receipt_binding"], "mapped conversion selection differs")
    report = conversion(plan, prepared["conversion_receipt_binding"])
    history = audit_history(ops, repo, report)
    require(prepared["original_integrated_tip"] == report["original_tip"]
            and prepared["mapped_prior_integrated_tip"] == report["converted_tip"], "mapped prior tip differs")
    require("prior_integrated_tip_ancestor" not in prepared and "all_selected_heads_ancestors" not in prepared,
            "original ancestry aliases must not be claimed for rewritten history")
    for key in ("complete_canonical_snapshot_blobs_preserved", "intentional_deleted_paths_preserved",
                "mapped_prior_integrated_tip_ancestor", "all_mapped_selected_heads_ancestors", "original_repository_state_preserved"):
        require(prepared.get(key) is True, "mapped preservation flag differs: " + key)
    for key in ("original_integrated_tip_ancestor", "original_rewritten_commit_oids_remote_ancestry_claimed",
                "all_source_python_parses_claimed", "training_executed"):
        require(prepared.get(key) is False, "mapped scope differs: " + key)
    ops.run(repo, ["merge-base", "--is-ancestor", report["converted_tip"], prepared["integrated_tip"]])
    _, original_ancestor = ops.run(repo, ["merge-base", "--is-ancestor", report["original_tip"], prepared["integrated_tip"]], accepted=(0, 1))
    require(original_ancestor == 1, "original rewritten tip unexpectedly claimed as ancestor")
    old_tree = committed_tree(ops, repo, report["original_tip"])
    new_tree = committed_tree(ops, repo, report["converted_tip"])
    require(transform(old_tree, report)[0] == new_tree, "converted final tree changes unrelated source")
    require(report["final_current_tree_exactly_preserved"] == (old_tree == new_tree)
            and prepared["final_current_tree_exactly_preserved"] == report["final_current_tree_exactly_preserved"], "final conversion tree scope differs")
    require(prepared["full_canonical_blob_path_count"] == fulltree["canonical_blob_paths_verified"], "mapped blob count differs")
    # Reuse the owner's closed syntax qualification with only the preservation
    # aliases removed from its dispatch; these are checked above with true scope.
    syntax = prepared["syntax_qualification"]
    require(set(syntax) == {"newly_invalid_executable_source", "inherited_canonical_syntax_findings",
        "excluded_fixture_vendor_and_template_paths", "examined_python_blob_count", "scope"}, "closed mapped syntax profile required")
    require(syntax["newly_invalid_executable_source"] == prepared["python_syntax_errors"] == [], "new invalid Python blocks publication")
    require(syntax["scope"] == "Changed raw Git Python blobs relative to selected origin baseline; inherited errors require identical canonical OIDs. No all-source parse claim.", "mapped syntax scope differs")
    canonical = committed_tree(ops, repo, fulltree["canonical_snapshot_commit"])
    findings = syntax["inherited_canonical_syntax_findings"]
    require(type(findings) is list and type(syntax["examined_python_blob_count"]) is int
            and len(findings) <= syntax["examined_python_blob_count"], "bounded mapped syntax findings required")
    seen = set()
    for finding in findings:
        require(set(finding) == {"path", "git_oid", "error"}, "closed mapped inherited finding required")
        path = safe_path(finding["path"])
        require(path not in seen and path.endswith(".py") and isinstance(finding["error"], str) and finding["error"], "unique mapped inherited finding required")
        seen.add(path)
        require(canonical.get(path) == {"mode": canonical.get(path, {}).get("mode"), "kind": "blob", "oid": finding["git_oid"]}
                and canonical[path]["mode"] in {"100644", "100755"}, "mapped inherited canonical blob differs")
    skipped = syntax["excluded_fixture_vendor_and_template_paths"]
    require(type(skipped) is list and len(skipped) == len(set(skipped)), "unique mapped syntax exclusions required")
    for path in skipped:
        safe_path(path)
    return {"schema": PROFILE, "conversion_receipt_binding": prepared["conversion_receipt_binding"],
        "mapped_selected_head_count": len(plan["heads"]), "original_rewritten_commit_oids_remote_ancestry_claimed": False,
        "new_invalid_executable_source_count": 0, "inherited_canonical_finding_count": len(findings),
        "all_source_python_parses_claimed_by_publisher": False, "HF_references_joined_to_verified_publication_receipts": True,
        "historical_transformation_verification": history}


def save(path, value):
    if path.name == "publication.json":
        value = {**value, "publisher_extension_owner_binding": {"path": str(OWNER), "bytes": len(owner_bytes), "sha256": OWNER_SHA},
                 "publisher_extension_owner_bytes_unchanged": OWNER.read_bytes() == owner_bytes}
    return BASE_SAVE(path, value)


CTX.update(check_prepared=check_prepared, check_full_canonical_tree=check_full_canonical_tree,
           check_prepared_fulltree_profile=check_profile, sealed_save=save)


def main():
    parser = CTX["argparse"].ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha", required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--prepared-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--published-gitlink", nargs=3, action="append", default=[], metavar=("PATH", "RECEIPT", "SHA256"))
    args = parser.parse_args()
    raise SystemExit(CTX["publish"](args))


if __name__ == "__main__":
    main()
