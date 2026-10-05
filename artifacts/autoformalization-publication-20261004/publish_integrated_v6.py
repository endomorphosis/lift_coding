"""Permit removal beside an already exact HF pointer; retain collision rejection."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

OWNER = Path(__file__).with_name("publish_integrated_v5.py")
OWNER_SHA = "dd61d092177945d90f9d41d2347f02aed513f031129c33918ba3bbd37d21dab9"
owner_bytes = OWNER.read_bytes()
if hashlib.sha256(owner_bytes).hexdigest() != OWNER_SHA:
    raise ValueError("frozen V5 publisher differs")
LIB = {"__name__": "frozen_v5_library", "__file__": __file__}
exec(compile(owner_bytes, str(OWNER), "exec"), LIB)
V4 = LIB["LIB"]
CTX = LIB["CTX"]
BASE_SAVE = CTX["sealed_save"]


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError("frozen owner extension context differs")
    return source.replace(before, after, 1)


def frozen_function(name):
    source = LIB["owner_bytes"].decode("utf-8")
    matches = [node for node in ast.parse(source).body
               if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise ValueError("unique frozen function required")
    segment = ast.get_source_segment(source, matches[0])
    if segment is None:
        raise ValueError("frozen function source unavailable")
    return segment + "\n"


audit = frozen_function("audit_history")
audit = replace_once(audit,
    '                require(mode in {b"100644", b"100755"} and name + b".hf.json" not in names, "historical HF reference collision")\n',
    '                require(mode in {b"100644", b"100755"}, "historical payload mode differs")\n'
    '                adjacent = name + b".hf.json"\n'
    '                if adjacent in names:\n'
    '                    matches = [row for row in entries if row[1] == adjacent]\n'
    '                    require(matches == [(mode, adjacent, report["reference_blob_oids"][path])],\n'
    '                            "historical existing HF reference differs in mode or Git identity")\n'
    '                    continue\n')
exec(compile(audit, str(__file__) + ":exact_coalescing_audit", "exec"), V4)

transform = frozen_function("transform")
transform = replace_once(transform,
    '        require(old["kind"] == "blob" and old["mode"] in {"100644", "100755"}\n'
    '                and adjacent not in expected, "reference substitution collision or mode differs")\n',
    '        require(old["kind"] == "blob" and old["mode"] in {"100644", "100755"}, "payload mode differs")\n')
transform = replace_once(transform,
    '        del expected[path]\n',
    '        require(adjacent not in expected or expected[adjacent] == new, "existing HF reference identity differs")\n'
    '        del expected[path]\n')
exec(compile(transform, str(__file__) + ":exact_coalescing_transform", "exec"), V4)


def save(path, value):
    if path.name == "publication.json":
        value = {**value, "publisher_V5_owner_binding": {"path": str(OWNER), "bytes": len(owner_bytes), "sha256": OWNER_SHA},
            "publisher_V5_owner_bytes_unchanged": OWNER.read_bytes() == owner_bytes,
            "historical_pointer_coalescing_policy": "existing_adjacent_pointer_must_match_exact_selected_mode_and_GitOID",
            "different_existing_pointer_collision_rejected": True}
    return BASE_SAVE(path, value)


CTX["sealed_save"] = save

if __name__ == "__main__":
    V4["main"]()
