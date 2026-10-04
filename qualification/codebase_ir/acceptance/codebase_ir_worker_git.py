"""Bounded read-only verification of retained SHA1 Git loose objects."""
from __future__ import annotations

import hashlib
import zlib
from pathlib import Path
from typing import Any

from codebase_ir_admission_evidence import need

MAX_OBJECT_BYTES = 2 * 1024 * 1024
MAX_OBJECTS = 128
MAX_TREE_ENTRIES = 128
MAX_TREE_VISITS = 128
MAX_EXPANDED_ENTRIES = 256


def hex_digest(value: Any, length: int) -> bool:
    return type(value) is str and len(value) == length and all(character in "0123456789abcdef" for character in value)


class LooseGit:
    def __init__(self, repository: Path, reader):
        self.repository, self.reader = repository, reader
        self.objects: dict[str, tuple[str, bytes]] = {}
        self.tree_visits, self.expanded_entries = 0, 0

    def object(self, oid: str, expected_type: str) -> bytes:
        need(hex_digest(oid, 40), "exact SHA1 Git object identity required")
        if oid not in self.objects:
            need(len(self.objects) < MAX_OBJECTS, "Git object count cap exceeded")
            compressed = self.reader.read(self.repository / ".git" / "objects" / oid[:2] / oid[2:])
            decompressor = zlib.decompressobj()
            try:
                raw = decompressor.decompress(compressed, MAX_OBJECT_BYTES + 1)
            except zlib.error as exc:
                raise ValueError("malformed retained Git loose-object compression") from exc
            need(len(raw) <= MAX_OBJECT_BYTES and decompressor.eof and not decompressor.unused_data
                 and not decompressor.unconsumed_tail, "bounded single Git loose object required")
            header, separator, body = raw.partition(b"\0")
            kind, space, size = header.partition(b" ")
            need(separator == b"\0" and space == b" " and size.isdigit() and size == str(len(body)).encode()
                 and hashlib.sha1(raw).hexdigest() == oid, "Git object header, bytes or identity drift")
            self.objects[oid] = kind.decode("ascii"), body
        kind, body = self.objects[oid]
        need(kind == expected_type, "Git object type differs from required publication role")
        return body

    def commit(self, oid: str) -> tuple[str, list[str]]:
        body = self.object(oid, "commit")
        header, separator, _ = body.partition(b"\n\n")
        need(separator == b"\n\n", "Git commit header missing")
        trees, parents = [], []
        for line in header.splitlines():
            if line.startswith(b"tree "):
                trees.append(line[5:].decode("ascii"))
            elif line.startswith(b"parent "):
                parents.append(line[7:].decode("ascii"))
        need(len(trees) == 1 and hex_digest(trees[0], 40) and all(hex_digest(parent, 40) for parent in parents)
             and len(parents) == len(set(parents)), "Git commit tree or parent population malformed")
        return trees[0], parents

    def tree(self, oid: str, *, prefix: str = "", depth: int = 0) -> dict[str, tuple[str, bytes]]:
        self.tree_visits += 1
        need(self.tree_visits <= MAX_TREE_VISITS, "Git expanded tree traversal cap exceeded")
        need(depth <= 8, "Git tree depth cap exceeded")
        body = self.object(oid, "tree")
        cursor, result, names = 0, {}, set()
        while cursor < len(body):
            self.expanded_entries += 1
            need(self.expanded_entries <= MAX_EXPANDED_ENTRIES, "Git expanded tree entry cap exceeded")
            separator = body.find(b"\0", cursor)
            need(separator >= 0 and separator + 21 <= len(body), "Git tree entry truncated")
            mode, space, raw_name = body[cursor:separator].partition(b" ")
            name = raw_name.decode("utf-8")
            need(space == b" " and name not in {"", ".", ".."} and "/" not in name and name not in names,
                 "Git tree selector duplicate or unsafe")
            names.add(name)
            need(len(names) <= MAX_TREE_ENTRIES, "Git tree entry count cap exceeded")
            child = body[separator + 1:separator + 21].hex()
            cursor = separator + 21
            if mode == b"40000":
                result.update(self.tree(child, prefix=prefix + name + "/", depth=depth + 1))
            else:
                need(mode in {b"100644", b"100755"}, "Git tree symlink/submodule/special mode refused")
                result[prefix + name] = mode.decode(), self.object(child, "blob")
            need(len(result) <= MAX_TREE_ENTRIES, "Git leaf population cap exceeded")
        return result


def verify_publication(repository: Path, reader, result: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    git = LooseGit(repository, reader)
    original, published = result["original_commit"], result["published_commit"]
    old_tree, _ = git.commit(original)
    new_tree, parents = git.commit(published)
    need(parents == result["published_commit_parents"] and len(parents) == 2 and parents[0] == original,
         "published Git merge must retain the exact two-parent baseline")
    implementation_tree, implementation_parents = git.commit(parents[1])
    need(implementation_parents == [original] and implementation_tree == new_tree,
         "published Git merge detached from the baseline implementation commit")
    before, after = git.tree(old_tree), git.tree(new_tree)
    need(set(before) == set(after), "published Git source population changed")
    changed = sorted(path for path in before if before[path] != after[path])
    need(changed == result["changed_paths"] == ["calc.py"], "Git publication exceeded the exact calc.py output")
    manifest = candidate["finite_admission"]["declaration"]["payload"]["manifest"]["payload"]
    need(set(before) == set(manifest["sources"]), "Git baseline detached from complete signed inventory")
    for path, (mode, raw) in before.items():
        expected = manifest["sources"][path]
        need(hashlib.sha256(raw).hexdigest() == expected["sha256"]
             and (mode == "100755") is expected["executable"] and after[path][0] == mode,
             "Git baseline or published source bytes/mode differ")
    edit = candidate["edit"]
    need(hashlib.sha256(before["calc.py"][1]).hexdigest() == edit["before_sha256"]
         and hashlib.sha256(after["calc.py"][1]).hexdigest() == edit["after_sha256"], "Git edit preimage/postimage differs")
    return {"git_object_verification_performed": True, "scope": "retained SHA1 loose commit/tree/blob bytes only; no live Git invocation",
        "object_count": len(git.objects), "original_commit": original, "published_commit": published,
        "implementation_commit": parents[1], "published_commit_parents": parents, "published_tree": new_tree,
        "changed_paths": changed, "before_source_sha256": {path: hashlib.sha256(raw).hexdigest() for path, (_, raw) in before.items()},
        "after_source_sha256": {path: hashlib.sha256(raw).hexdigest() for path, (_, raw) in after.items()}}
