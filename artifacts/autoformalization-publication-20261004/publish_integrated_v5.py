"""Batch exact source and ancestry checks to reduce races with advancing main."""
from __future__ import annotations

import hashlib
from pathlib import Path

OWNER = Path(__file__).with_name("publish_integrated_v4.py")
OWNER_SHA = "510a110fc086d7380e3488e4794d0f5f94f9ca7c569c5ba8d245a6861e47201d"
owner_bytes = OWNER.read_bytes()
if hashlib.sha256(owner_bytes).hexdigest() != OWNER_SHA:
    raise ValueError("frozen V4 publisher differs")
LIB = {"__name__": "frozen_v4_library", "__file__": __file__}
exec(compile(owner_bytes, str(OWNER), "exec"), LIB)
CTX = LIB["CTX"]
require, OID, safe_path = LIB["require"], LIB["OID"], LIB["safe_path"]
BASE_OPS, BASE_PREPARED, BASE_SAVE = CTX["GitOperations"], CTX["check_prepared"], CTX["sealed_save"]
ACTIVE = []


class BatchOperations(BASE_OPS):
    def __init__(self, directory):
        super().__init__(directory)
        self.ancestry_pairs = set()
        self.batch_qualified_head_count = 0
        self.qualified_head_set_sha256 = None
        ACTIVE.append(self)

    def run(self, repo, args, **kwargs):
        if len(args) == 4 and args[:2] == ["merge-base", "--is-ancestor"] and (str(Path(repo).resolve()), args[2], args[3]) in self.ancestry_pairs:
            # The single recorded rev-list set-difference operation established
            # this exact ancestry relation. No individual command is claimed.
            return b"", 0
        return super().run(repo, args, **kwargs)


def check_prepared(ops, plan, prepared):
    repo, tip = Path(plan["fresh_worktree"]).resolve(), prepared["integrated_tip"]
    heads = sorted({head["oid"] for head in plan["heads"]})
    require(OID.fullmatch(tip) and heads and all(OID.fullmatch(oid) for oid in heads), "exact batch ancestry identities required")
    data, _ = ops.run(repo, ["rev-list", *heads, "--not", tip])
    require(data == b"", "a selected head has commits outside the proposed main history")
    ops.ancestry_pairs.update((str(repo), oid, tip) for oid in heads)
    ops.batch_qualified_head_count = len(heads)
    ops.qualified_head_set_sha256 = hashlib.sha256(LIB["raw"](heads)).hexdigest()
    return BASE_PREPARED(ops, plan, prepared)


def check_source_pins(ops, repo, tree, plan):
    rows = plan.get("authoritative_source", {}).get("selected_files", [])
    sizes = {}
    for row in rows:
        name = safe_path(row["path"])
        entry = tree.get(name)
        if row["state"] in {"absent", "deleted"}:
            require(entry is None and not any(p.startswith(name + "/") for p in tree), "deleted source path remains")
            continue
        require(entry is not None and entry["kind"] == "blob" and entry["mode"] == row["mode"], "source mode/type differs")
        require(type(row.get("bytes")) is int and 0 <= row["bytes"] <= 1024 ** 3, "explicit bounded source byte count required")
        require(entry["oid"] not in sizes or sizes[entry["oid"]] == row["bytes"], "duplicate source object sizes differ")
        sizes[entry["oid"]] = row["bytes"]
    chunks, current, total = [], [], 0
    for oid, size in sizes.items():
        if current and total + size + 100 > 32 * 1024 ** 2:
            chunks.append(current)
            current, total = [], 0
        current.append(oid)
        total += size + 100
    if current:
        chunks.append(current)
    cache = {}
    for chunk in chunks:
        # Oversized individual source blobs retain the owner's streaming hash.
        if len(chunk) == 1 and sizes[chunk[0]] > 32 * 1024 ** 2:
            cache[chunk[0]] = ops.run(repo, ["cat-file", "blob", chunk[0]], hash_only=True, limit=1024 ** 3)
            continue
        data, _ = ops.run(repo, ["cat-file", "--batch"], input_data="".join(oid + "\n" for oid in chunk).encode())
        offset = 0
        for oid in chunk:
            end = data.index(b"\n", offset)
            header = data[offset:end].split()
            require(header == [oid.encode(), b"blob", str(sizes[oid]).encode()], "batch source identity or size differs")
            offset = end + 1
            body = data[offset:offset + sizes[oid]]
            require(len(body) == sizes[oid] and data[offset + sizes[oid]:offset + sizes[oid] + 1] == b"\n", "truncated source blob")
            cache[oid] = {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
            offset += sizes[oid] + 1
        require(offset == len(data), "unexpected source batch bytes")
    checks = []
    for row in rows:
        name = row["path"]
        if row["state"] in {"absent", "deleted"}:
            checks.append({"path": name, "state": "absent"})
            continue
        entry, actual = tree[name], cache[tree[name]["oid"]]
        require(actual["sha256"] == row["sha256"] and actual["bytes"] == row["bytes"], "source bytes differ")
        checks.append({"path": name, **entry, "sha256": actual["sha256"], "bytes": actual["bytes"]})
    return checks


def save(path, value):
    if path.name == "publication.json":
        value = {**value, "publisher_V4_owner_binding": {"path": str(OWNER), "bytes": len(owner_bytes), "sha256": OWNER_SHA},
            "publisher_V4_owner_bytes_unchanged": OWNER.read_bytes() == owner_bytes,
            "selected_head_ancestry_recipe": "one_recorded_rev_list_selected_heads_not_tip_empty_set",
            "selected_head_batch_qualification": [{"unique_head_count": ops.batch_qualified_head_count,
                "head_set_sha256": ops.qualified_head_set_sha256} for ops in ACTIVE],
            "source_SHA256_recipe": "exact_raw_git_cat_file_batches_with_per_object_headers_sizes_and_SHA256"}
    return BASE_SAVE(path, value)


CTX.update(GitOperations=BatchOperations, check_prepared=check_prepared, check_source_pins=check_source_pins, sealed_save=save)

if __name__ == "__main__":
    LIB["main"]()
