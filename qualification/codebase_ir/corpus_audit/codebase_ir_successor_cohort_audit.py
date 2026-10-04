"""Source-only successor prefix, child-role and declaration-lineage accounting."""
from __future__ import annotations

import argparse
import ast
import base64
import copy
import hashlib
import json
import math
import os
import stat
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from codebase_ir_final_targets import derive_source

INPUT_SCHEMA = "codebase-ir-successor-cohort-audit-input@1"
REPORT_SCHEMA = "codebase-ir-successor-cohort-audit@1"
ROLES = ("review", "native_result", "independent_audit", "failed_result")
ANCHORS = dict(zip(ROLES, (
    "8a9a24c56873f97edac6e325078039fc0e2ba017c922839d11eaf3d92e7f2f91",
    "1a2de8246df5e561ae994f5b77578d69921323e3b18d9c3d0da6ff8d32638f45",
    "c096ce302f556af7f1733372de8b54cfb1f56ad23561f7ab78a860e9f0504fea",
    "b108a4ccb9ca3d75582f0204ca32c8f3a983417451b753ff78f5272941823c81",
), strict=True))
METADATA = {
    "owners_before": "owners-before.json",
    "optimized_selection": "successor-selection.json",
    "reference_selection": "reference-successor-selection.json",
    "optimized_root": "scan-root.json",
    "reference_root": "reference-scan-root.json",
    "optimized_prefix": "prefix-page.json",
    "reference_prefix": "reference-prefix-page.json",
}
TRUE_FLAGS = ("successor_cohort_accounting_produced", "prefix_population_rederived",
              "source_bytes_bindings_rederived", "captured_ast_bindings_rederived",
              "child_selection_roles_rederived", "source_clone_exposure_accounted",
              "declaration_lineage_accounted", "historical_failed_attempt_preserved",
              "input_files_unchanged", "unknown_pretraining_exposure")
FALSE_FLAGS = ("native_execution_performed", "training_executed", "current_authority_claimed",
               "owner_sources_imported", "owner_database_opened", "git_executable_invoked", "profile_keys_read",
               "source_execution_attested", "scan_execution_attested", "source_semantics_verified",
               "source_runtime_truth_verified", "snapshot_schema_verified", "snapshot_entry_schema_verified",
               "native_target_digest_rederived", "numerical_execution_reperformed", "numerical_provenance_verified",
               "inference_correctness_verified", "optimizer_state_replayed", "checkpoint_states_verified",
               "full_ancestry_verified", "root_training_population_verified", "replay_population_verified",
               "complete_pretraining_exposure_verified", "heldout_independence_verified",
               "learned_weight_dependence_verified", "learned_quality_improvement_verified",
               "model_selection_performed", "candidate_model_qualified", "promotion_performed", "model_advanced",
               "numerical_reuse_authorized", "complete_scan_verified", "final_population_modified",
               "producer_authentication_verified")
MiB = 1024 * 1024
MAX_ORIGINALS, MAX_FILES, MAX_BYTES = 128, 256, 8 * MiB
AST_FIELDS = {"calls", "diagnostics", "effects", "frontend", "imports", "module", "provenance",
              "references", "schema", "scopes", "symbols", "unsupported"}
MEMBER_FIELDS = {"ast_cid", "entry_cid", "opaque_reason", "parse_status", "path", "raw_path_hex",
                 "source_cid", "source_key", "source_size_bytes"}
HEAD_FIELDS = {"schema", "repository_id", "generation", "ast_revision_id", "snapshot_cid", "manifest_cid", "receipt_cid"}
AUTHORITY_FIELDS = {"admission_authority", "authoritative_cache_eligible", "behavioral_satisfaction", "completion_authority",
                    "decoded_formulas_generated", "execution_authority", "mutation_authority", "proof_authority",
                    "repository_code_executed", "runtime_behavior_verified", "scan_execution_attested",
                    "source_execution_attested", "source_semantics_verified", "training_executed"}
ROOT_FIELDS = {"authority", "head", "head_cid", "implementation", "limits", "members", "membership_cid", "model", "optimized", "schema"}
SELECTION_FIELDS = {"authority", "current_head", "current_membership_cid", "implementation", "inference_performed_here", "model",
                    "model_head_promoted", "numerical_reuse", "optimized", "previous_head", "previous_membership_cid", "previous_model",
                    "previous_training_record_cid", "root_cid", "scan_limits", "schema", "source_delta_cid", "training_performed_here", "training_record_cid"}
PAGE_FIELDS = {"authority", "coverage", "end", "entries", "head_cid", "inference", "membership_cid", "model_artifact_cid",
               "page_membership_cid", "previous_page_cid", "root_cid", "schema", "start", "total_entries", "worker_receipt"}
ENTRY_FIELDS = {"coverage", "disposition", "entry_cid", "inference_index", "member_index", "reason", "source_digest", "source_key", "target_sha256"}
MODEL_FIELDS = {"ancestry", "artifact", "artifact_cid", "contract_sha256", "feature_columns", "feature_space_sha256", "latent_width",
                "projection_ids", "projection_widths", "state_sha256", "variant_id", "version_id"}


class Refused(ValueError):
    """Selected source/export bytes do not satisfy this closed diagnostic profile."""


def require(condition, reason):
    if not condition:
        raise Refused(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def cid(raw, structured=False):
    return "b" + base64.b32encode((b"\x01\xa9\x02\x12\x20" if structured else b"\x01\x55\x12\x20")
                                 + hashlib.sha256(raw).digest()).decode("ascii").lower().rstrip("=")


def object_cid(value):
    return cid(wire(value), True)


def report_bytes(value):
    chunks, size = [], 0
    for chunk in json.JSONEncoder(sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).iterencode(value):
        raw = chunk.encode("utf-8")
        size += len(raw)
        require(size + 1 <= 4 * MiB, "main report allocation bound")
        chunks.append(raw)
    return b"".join(chunks) + b"\n"


def closed(value, fields, reason):
    require(type(value) is dict and set(value) == set(fields), reason)


def document(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate JSON field")
            value[key] = item
        return value

    def integer(token):
        require(len(token) <= 20, "JSON integer allocation bound")
        value = int(token)
        require(abs(value) <= 2**63 - 1, "JSON integer bound")
        return value

    def floating(token):
        require(len(token) <= 64 and math.isfinite(float(token)), "finite JSON number required")
        return float(token)

    def bad(_):
        raise Refused("nonfinite JSON constant")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_int=integer,
                       parse_float=floating, parse_constant=bad)
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        require(depth <= 64 and nodes <= 1000000, "JSON structure budget")
        if type(item) is dict:
            pending.extend((x, depth + 1) for x in item)
            pending.extend((x, depth + 1) for x in item.values())
        elif type(item) is list:
            pending.extend((x, depth + 1) for x in item)
        elif type(item) is str:
            item.encode("utf-8")
    require(type(value) is dict, "JSON object required")
    return value


def descriptor(value):
    closed(value, {"path", "sha256", "size_bytes"}, "closed raw descriptor required")
    require(type(value["path"]) is str and type(value["sha256"]) is str
            and len(value["sha256"]) == 64 and all(x in "0123456789abcdef" for x in value["sha256"])
            and type(value["size_bytes"]) is int and 0 <= value["size_bytes"], "typed exact raw descriptor required")
    return Path(value["path"])


class Reads:
    def __init__(self):
        self.plan, self.raw, self.inodes = {}, {}, {}

    def reserve(self, path, pin, cap):
        path = Path(path)
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical selected file required")
        require(type(pin) is dict and set(pin) == {"sha256", "size_bytes"}
                and type(pin["size_bytes"]) is int and 0 <= pin["size_bytes"] <= cap, "declared preallocation body bound")
        require(type(pin["sha256"]) is str and len(pin["sha256"]) == 64
                and all(x in "0123456789abcdef" for x in pin["sha256"]), "raw SHA required")
        if path in self.plan:
            require(self.plan[path] == pin, "conflicting selected descriptor")
            return
        require(len(self.plan) < MAX_ORIGINALS and 2 * (sum(x["size_bytes"] for x in self.plan.values())
                + pin["size_bytes"]) <= MAX_BYTES, "complete original and copy reservation budget")
        info = path.stat(follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode) and info.st_size == pin["size_bytes"], "regular exact selected size")
        inode = (info.st_dev, info.st_ino)
        require(inode not in self.inodes, "hardlink selected alias")
        self.inodes[inode], self.plan[path] = path, pin

    @staticmethod
    def bounded(path, cap):
        require(path.is_absolute() and path.resolve(strict=True) == path, "canonical bounded read required")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "bounded regular descriptor required")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(cap + 1)
            after, final = os.fstat(fd), path.stat(follow_symlinks=False)
            def identity(value):
                return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
            require(len(raw) == before.st_size and identity(before) == identity(after) == identity(final), "selected descriptor drift")
            return raw
        finally:
            os.close(fd)

    def take(self, path):
        require(path in self.plan, "unreserved read refused")
        if path not in self.raw:
            pin = self.plan[path]
            raw = self.bounded(path, pin["size_bytes"])
            require(sha(raw) == pin["sha256"], "selected raw SHA mismatch")
            self.raw[path] = raw
        return self.raw[path]

    def stable(self):
        for path, raw in self.raw.items():
            require(self.bounded(path, len(raw)) == raw, "late original selected body drift")



def span(value, raw):
    closed(value, {"start_byte", "end_byte", "start_line", "end_line", "start_column", "end_column"}, "closed source span")
    require(all(type(x) is int for x in value.values()), "typed span offsets")
    start, end = value["start_byte"], value["end_byte"]
    require(0 <= start <= end <= len(raw), "source span bounds")
    lines = raw.split(b"\n")
    offsets, total = [], 0
    for line in lines:
        offsets.append(total)
        total += len(line) + 1
    for side, position in (("start", start), ("end", end)):
        line, column = value[side + "_line"], value[side + "_column"]
        require(1 <= line <= len(lines) and 0 <= column <= len(lines[line - 1])
                and offsets[line - 1] + column == position, "source span coordinate preimage")
    return start, end


def syntax(member, raw, captured, source_head):
    base = {"source_sha256": sha(raw) if raw is not None else None, "syntax_disposition": "unavailable",
            "normalized_ast_sha256": None, "template_ast_sha256": None, "label": None,
            "label_binding": None, "label_reason": "source syntax unavailable", "dependency_paths": [], "reference_span_count": 0}
    if raw is None:
        require(member["parse_status"] == "opaque" and captured is None, "missing source is not opaque")
        return base
    require(len(raw) == member["source_size_bytes"] and len(raw) <= 65536, "raw source length binding")
    if captured is None:
        require(member["parse_status"] == "unindexed", "missing AST is not unindexed")
        return dict(base, syntax_disposition="unindexed")
    closed(captured, AST_FIELDS, "closed captured AST")
    require(captured["schema"] == "ipfs-datasets.software-contracts.ast-ir@1.0.0", "unsupported captured AST schema")
    provenance = captured["provenance"]
    require(provenance["repository_id"] == source_head["repository_id"]
            and provenance["repository_tree_cid"] == source_head["snapshot_cid"]
            and provenance["revision"] == "snapshot:" + source_head["snapshot_cid"]
            and provenance["path"] == member["path"] and provenance["source_cid"] == member["source_cid"], "captured AST source provenance")
    require(captured["module"]["module_id"] == "module:" + member["source_cid"]
            and span(captured["module"]["span"], raw) == (0, len(raw)), "module source binding")
    pending, nodes, spans = [captured], 0, 0
    while pending:
        item = pending.pop()
        nodes += 1
        require(nodes <= 16384, "captured AST walk budget")
        if type(item) is dict:
            if "span" in item:
                span(item["span"], raw)
                spans += 1
                require(spans <= 4096, "captured AST span budget")
            pending.extend(v for k, v in item.items() if k != "span")
        elif type(item) is list:
            pending.extend(item)
    try:
        tree = ast.parse(raw.decode("utf-8"), type_comments=True)
    except (SyntaxError, UnicodeDecodeError):
        require(member["parse_status"] == "failed" and bool(captured["diagnostics"])
                and bool(captured["unsupported"]) and captured["references"] == captured["symbols"] == [], "captured failed parse disposition")
        return dict(base, syntax_disposition="parse_failed")
    require(member["parse_status"] == "ok", "parsed source disposition")
    nodes = []
    for node in ast.walk(tree):
        require(len(nodes) < 4096, "source AST allocation budget")
        nodes.append(node)
    offsets, total = [], 0
    for line in raw.split(b"\n"):
        offsets.append(total)
        total += len(line) + 1

    def extent(node):
        return offsets[node.lineno - 1] + node.col_offset, offsets[node.end_lineno - 1] + node.end_col_offset

    type_names = set()
    for node in nodes:
        annotation = node.annotation if isinstance(node, ast.arg | ast.AnnAssign) else node.returns if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) else None
        if annotation is not None:
            type_names.update(id(x) for x in ast.walk(annotation) if isinstance(x, ast.Name))

    def context(node):
        return "type" if id(node) in type_names else "write" if isinstance(node.ctx, ast.Store) else "read"

    references = sorted([(n.id, context(n), *extent(n)) for n in nodes if isinstance(n, ast.Name)]
                        + [(n.func.id, "call", *extent(n.func)) for n in nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)])
    symbols = sorted([("function", n.name, *extent(n)) for n in nodes if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
                     + [("parameter", n.arg, *extent(n)) for n in nodes if isinstance(n, ast.arg)])
    require(sorted((r["name"], r["context"], *span(r["span"], raw)) for r in captured["references"]) == references, "independent reference population")
    require(sorted((r["kind"], r["name"], *span(r["span"], raw)) for r in captured["symbols"]) == symbols, "independent symbol population")
    scopes = {x["scope_id"] for x in captured["scopes"]}
    require(len(scopes) == len(captured["scopes"]) and len({x["symbol_id"] for x in captured["symbols"]}) == len(captured["symbols"])
            and all(x["scope_id"] in scopes for x in captured["references"] + captured["symbols"]), "captured reference scope closure")
    for node in nodes:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbol = next(x for x in captured["symbols"] if x["kind"] == "function" and x["name"] == node.name and span(x["span"], raw) == extent(node))
            signature = symbol["signature"]
            if not node.args.posonlyargs and not node.args.kwonlyargs and not node.args.vararg and not node.args.kwarg and not node.args.defaults:
                parameters = [{"name": arg.arg, "annotation": ast.unparse(arg.annotation) if arg.annotation is not None else None,
                               "position": index, "kind": "positional_or_named", "default_kind": "none"} for index, arg in enumerate(node.args.args)]
                require(wire(signature["parameters"]) == wire(parameters) and signature["return_annotation"] == (ast.unparse(node.returns) if node.returns is not None else None), "independent signature annotations")
    dependencies = sorted({n.module.split(".")[0] + ".py" for n in nodes if isinstance(n, ast.ImportFrom) and n.module}
                          | {a.name.split(".")[0] + ".py" for n in nodes if isinstance(n, ast.Import) for a in n.names})
    template = copy.deepcopy(tree)
    for node in ast.walk(template):
        if isinstance(node, ast.Constant):
            node.value = "constant_type:" + type(node.value).__name__
    try:
        binding, label, reason = derive_source(raw)
    except (ValueError, SyntaxError, RecursionError) as exc:
        binding, label, reason = None, None, str(exc)
    return dict(base, syntax_disposition="parsed", normalized_ast_sha256=sha(ast.dump(tree, include_attributes=False).encode()),
                template_ast_sha256=sha(ast.dump(template, include_attributes=False).encode()), label=label,
                label_binding=binding, label_reason=reason, dependency_paths=dependencies, reference_span_count=len(references))


def typed_equal(a, b):
    return wire(a) == wire(b)


def integer(value, lower, upper, reason):
    require(type(value) is int and lower <= value <= upper, reason)
    return value


def digest(value):
    require(type(value) is str and len(value) == 64 and all(x in "0123456789abcdef" for x in value), "closed SHA digest")
    return value


def source_head(value):
    closed(value, HEAD_FIELDS, "closed declared source head")
    require(value["schema"] == "codebase-head@1", "unsupported source head schema")
    integer(value["generation"], 1, 2**31 - 1, "typed head generation")
    require(type(value["repository_id"]) is str and value["ast_revision_id"] == "rev:" + value["repository_id"]
            + ":snapshot:" + value["snapshot_cid"], "declared head revision identity")


def authority(value):
    closed(value, AUTHORITY_FIELDS, "closed advisory authority vocabulary")
    require(all(x is False for x in value.values()), "advisory authority ceiling")


def envelope(value, fields, schema, raw_codec=False):
    closed(value, {"artifact_cid", "value"}, "closed captured envelope")
    body = value["value"]
    closed(body, fields, "closed captured protocol")
    require(body["schema"] == schema and value["artifact_cid"] == cid(wire(body), not raw_codec), "captured protocol schema/CID")
    authority(body["authority"])
    return body


def model(value):
    closed(value, MODEL_FIELDS, "closed declared model descriptor")
    integer(value["feature_columns"], 1, 4096, "typed feature width")
    integer(value["latent_width"], 1, 384, "typed latent width")
    require(value["latent_width"] == 8 and value["feature_columns"] == 53, "closed CPU8D declaration")
    closed(value["artifact"], {"bytes", "sha256"}, "closed uninspected model-body claim")
    integer(value["artifact"]["bytes"], 1, 64 * MiB, "declared model body size")
    digest(value["artifact"]["sha256"])
    for field in ("contract_sha256", "feature_space_sha256", "state_sha256"):
        digest(value[field])
    require(value["version_id"] == "sha256:" + digest(value["version_id"].removeprefix("sha256:"))
            and value["variant_id"] == "modality-" + value["contract_sha256"], "declared model/variant identities")
    require(value["projection_ids"] == ["codebase_ir.contracts@1", "codebase_ir.program@1"]
            and typed_equal(value["projection_widths"], {"codebase_ir.contracts@1": 2, "codebase_ir.program@1": 51}), "declared projection widths")
    require(type(value["ancestry"]) is list and 1 <= len(value["ancestry"]) <= 2, "bounded declared ancestry")
    for item in value["ancestry"]:
        closed(item, {"artifact", "version_id"}, "closed ancestry declaration")
        closed(item["artifact"], {"bytes", "sha256"}, "closed ancestor body claim")
        integer(item["artifact"]["bytes"], 1, 64 * MiB, "declared ancestor size")
        digest(item["artifact"]["sha256"])
    require(typed_equal(value["ancestry"][0], {"version_id": value["version_id"], "artifact": value["artifact"]}), "declared self ancestry")


def member_list(members):
    require(type(members) is list and 32 <= len(members) <= 512, "bounded complete root population")
    paths, keys = [], []
    for m in members:
        closed(m, MEMBER_FIELDS, "closed root member")
        raw_path = bytes.fromhex(m["raw_path_hex"])
        require(0 < len(raw_path) <= 1024 and b"\0" not in raw_path and raw_path.decode("utf-8") == m["path"]
                and m["source_key"] == "raw:" + m["raw_path_hex"]
                and not PurePosixPath(m["path"]).is_absolute() and ".." not in PurePosixPath(m["path"]).parts, "raw source path/key binding")
        integer(m["source_size_bytes"], 0, 2**63 - 1, "typed declared source length")
        require(m["parse_status"] in {"ok", "unindexed", "failed", "opaque"}, "closed parse disposition")
        paths.append(raw_path)
        keys.append(m["source_key"])
    require(paths == sorted(paths) and len(set(paths)) == len(paths) and len(set(keys)) == len(keys), "ordered unique root membership")


def selection_pair(metadata):
    result = []
    for route in ("optimized", "reference"):
        s = envelope(metadata[route + "_selection"], SELECTION_FIELDS, "codebase-inventory-successor-scan@1")
        r = envelope(metadata[route + "_root"], ROOT_FIELDS, "codebase-inventory-resume-root@1")
        source_head(s["previous_head"])
        source_head(s["current_head"])
        require(s["current_head"]["repository_id"] == s["previous_head"]["repository_id"]
                and s["current_head"]["generation"] == s["previous_head"]["generation"] + 1, "successive declared source heads")
        for field in ("inference_performed_here", "training_performed_here", "model_head_promoted", "numerical_reuse"):
            require(s[field] is False, "selection no-fit/no-inference scope")
        require(s["optimized"] is (route == "optimized") and r["optimized"] is s["optimized"], "exact route declaration")
        model(s["model"])
        model(s["previous_model"])
        parent, child = s["previous_model"], s["model"]
        require(len(parent["ancestry"]) == 1 and typed_equal(child["ancestry"], [child["ancestry"][0], parent["ancestry"][0]])
                and child["version_id"] != parent["version_id"], "declared direct-child ancestry")
        for field in ("contract_sha256", "feature_columns", "feature_space_sha256", "latent_width", "projection_ids", "projection_widths", "variant_id"):
            require(typed_equal(child[field], parent[field]), "declared fixed basis/contract continuity")
        member_list(r["members"])
        require(typed_equal(r["head"], s["current_head"]) and r["head_cid"] == object_cid(r["head"])
                and r["membership_cid"] == object_cid(r["members"]) == s["current_membership_cid"]
                and typed_equal(r["model"], child) and typed_equal(r["limits"], s["scan_limits"])
                and s["root_cid"] == metadata[route + "_root"]["artifact_cid"], "root/selection exact joins")
        integer(r["limits"]["page_entries"], 32, 32, "closed prefix page size")
        result.append((s, r))
    left, right = result
    require(left[0]["root_cid"] != right[0]["root_cid"], "fresh separate route roots")
    for field in SELECTION_FIELDS - {"optimized", "root_cid"}:
        require(typed_equal(left[0][field], right[0][field]), "exact shared successor declaration")
    require(typed_equal(left[1]["members"], right[1]["members"]), "same complete route population")
    return result


def prefix(metadata, route, root, selection):
    p = envelope(metadata[route + "_prefix"], PAGE_FIELDS, "codebase-inventory-resume-page@1", True)
    integer(p["start"], 0, 0, "typed prefix start")
    integer(p["end"], 32, 32, "typed prefix end")
    integer(p["total_entries"], len(root["members"]), len(root["members"]), "typed whole population")
    members = root["members"][:32]
    require(p["root_cid"] == selection["root_cid"] and p["head_cid"] == root["head_cid"]
            and p["membership_cid"] == root["membership_cid"] and p["page_membership_cid"] == object_cid(members)
            and p["previous_page_cid"] is None and p["model_artifact_cid"] == selection["model"]["artifact_cid"], "prefix/root/head joins")
    require(type(p["entries"]) is list and len(p["entries"]) == 32, "exact prefix entry population")
    inf = p["inference"]
    closed(inf, {"admitted", "contract_sha256", "coverage", "decoded_formulas_generated", "feature_space_sha256", "formalized",
                 "promotion_performed", "qualified", "representation", "rows", "schema", "state_sha256", "training_executed"}, "closed returned inference declaration")
    require(inf["schema"] == "native-projection-feature-inference/v1"
            and inf["representation"] == "native_compiler_structural_features_not_semantic_text_embeddings", "closed returned inference representation")
    for field in ("admitted", "decoded_formulas_generated", "formalized", "promotion_performed", "qualified", "training_executed"):
        require(inf[field] is False, "returned inference authority ceiling")
    for field in ("contract_sha256", "feature_space_sha256", "state_sha256"):
        require(inf[field] == selection["model"][field], "returned model fingerprint declaration")
    require(type(inf["rows"]) is list and len(inf["rows"]) <= 32 and type(inf["coverage"]) is list, "bounded returned rows")
    dispositions, joined_rows, all_coverage = Counter(), [], []
    for i, (entry, m) in enumerate(zip(p["entries"], members, strict=True)):
        closed(entry, ENTRY_FIELDS, "closed prefix entry")
        integer(entry["member_index"], i, i, "typed exact member index")
        require(entry["source_key"] == m["source_key"] and entry["entry_cid"] == m["entry_cid"], "prefix source/entry population")
        d = entry["disposition"]
        require(d in {"inferred", "deferred_budget", "unindexed"}, "closed prefix disposition")
        dispositions[d] += 1
        if d == "unindexed":
            require(m["parse_status"] == "unindexed" and m["ast_cid"] is None
                    and entry["source_digest"] is entry["target_sha256"] is entry["inference_index"] is None
                    and entry["coverage"] == [] and entry["reason"] == "captured_source_has_no_ast_projection", "unindexed prefix absence")
            continue
        require(m["parse_status"] == "ok" and m["ast_cid"] is not None, "inference/deferred AST availability")
        digest(entry["source_digest"])
        digest(entry["target_sha256"])
        require(type(entry["coverage"]) is list and len(entry["coverage"]) == 2, "per-entry advisory coverage")
        for c, projection in zip(entry["coverage"], selection["model"]["projection_ids"], strict=True):
            closed(c, {"known_atoms", "projection_id", "unknown_atoms"}, "closed atom coverage")
            require(c["projection_id"] == projection, "ordered projection coverage")
            integer(c["known_atoms"], 0, 4096, "typed known atom count")
            integer(c["unknown_atoms"], 0, 4096, "typed unknown atom count")
        if d == "deferred_budget":
            require(entry["inference_index"] is None and type(entry["reason"]) is str and bool(entry["reason"]), "deferred row absence")
            continue
        index = len(joined_rows)
        integer(entry["inference_index"], index, index, "typed contiguous inference index")
        require(entry["reason"] is None and index < len(inf["rows"]), "inferred reason/row availability")
        row = inf["rows"][index]
        closed(row, {"latent", "reconstructed_projection_features", "source_digest"}, "closed returned numerical row")
        require(row["source_digest"] == entry["source_digest"] and type(row["latent"]) is list and len(row["latent"]) == 8, "returned row source/width join")
        closed(row["reconstructed_projection_features"], selection["model"]["projection_ids"], "closed returned projections")
        arrays = [row["latent"]]
        for key, width in selection["model"]["projection_widths"].items():
            array = row["reconstructed_projection_features"][key]
            require(type(array) is list and len(array) == width, "returned projection width")
            arrays.append(array)
        require(all(type(x) in {int, float} and abs(x) <= 1e100 and math.isfinite(x) for array in arrays for x in array), "bounded finite numerical claims")
        joined_rows.append(row)
        all_coverage.extend(entry["coverage"])
    require(len(joined_rows) == len(inf["rows"]) and typed_equal(inf["coverage"], all_coverage), "exact returned row/coverage population")
    counts = {key: dispositions[key] for key in ("inferred", "deferred_budget", "unindexed")}
    require(typed_equal(p["coverage"], {"dispositions": counts, "inferred_rows": len(joined_rows), "inventory_entries": 32}), "independent prefix disposition counts")
    return p, counts


def child_request(owners, selection):
    closed(owners, {"model_artifacts", "registry", "source"}, "closed captured owner metadata")
    closed(owners["registry"], {"events", "heads", "meta", "operations", "outbox", "runs", "variants", "versions"}, "closed inert registry export")
    require(owners["registry"]["heads"] == [], "captured unpromoted registry declaration")
    require(typed_equal(owners["source"]["current_head"], selection["current_head"]), "captured owner/source head declaration")
    versions, runs = owners["registry"]["versions"], owners["registry"]["runs"]
    require(type(versions) is list and len(versions) == 2 and all(type(v) is list and len(v) == 5 for v in versions), "closed two-version registry rows")
    by_id = {v[0]: v for v in versions}
    child, parent = selection["model"], selection["previous_model"]
    require(set(by_id) == {parent["version_id"], child["version_id"]}, "exact registry version population")
    for declared, predecessor in ((parent, None), (child, parent["version_id"])):
        row = by_id[declared["version_id"]]
        require(row[1] == declared["variant_id"] and row[2] == predecessor
                and typed_equal(document(row[3].encode()), declared["artifact"]), "declared registry parent/artifact joins")
    require(type(runs) is list and len(runs) == 1 and type(runs[0]) is list and len(runs[0]) == 9, "only one child run declaration available")
    row = runs[0]
    require(row[1] == child["variant_id"] and row[2] == parent["version_id"] and row[4] == "completed", "completed child request declaration")
    integer(row[5], 1, 1, "typed declared run attempt")
    integer(row[6], 1, 1, "typed declared run fence")
    request, result = document(row[3].encode()), document(row[8].encode())
    closed(request, {"canary_targets_sha256", "configuration", "contract_sha256", "head", "implementation", "parent_version_id",
                     "schema", "selections", "training_targets_sha256", "tuning_targets_sha256"}, "closed child training request")
    require(request["schema"] == "codebase-source-feature-training@1" and typed_equal(request["head"], selection["current_head"])
            and request["parent_version_id"] == parent["version_id"] and request["contract_sha256"] == child["contract_sha256"], "child request head/parent/contract declarations")
    closed(request["configuration"], {"epochs", "learning_rate", "seed"}, "closed declared setup configuration")
    integer(request["configuration"]["epochs"], 1, 1, "typed declared child setup epoch")
    integer(request["configuration"]["seed"], 0, 2**31 - 1, "typed declared seed")
    rate = request["configuration"]["learning_rate"]
    require(type(rate) in {float, int} and 0 < rate < 1, "typed declared learning rate")
    selections = request["selections"]
    require(type(selections) is list and len(selections) == 3, "exact child declared role population")
    for s in selections:
        closed(s, {"contracts", "path", "role"}, "closed child source selection")
        require(type(s["path"]) is str and s["role"] in {"train", "tune", "canary"} and s["contracts"] == [], "closed child selection roles/contracts")
    require(len({s["path"] for s in selections}) == 3 and Counter(s["role"] for s in selections) == Counter({"train": 1, "tune": 1, "canary": 1}), "unique declared child role paths")
    for field in ("training_targets_sha256", "tuning_targets_sha256", "canary_targets_sha256"):
        digest(request[field])
    for field in ("admitted", "formalized", "promotion_performed", "qualified"):
        require(result[field] is False, "captured training result authority ceiling")
    require(result["training_purpose"] == "feature_pretraining", "declared training purpose")
    for field in ("contract_sha256", "feature_space_sha256", "state_sha256"):
        require(result[field] == child[field], "child result fingerprint declarations")
    return request


def derive(metadata, sources, asts, native, failed):
    pairs = selection_pair(metadata)
    selection, root = pairs[0]
    request = child_request(metadata["owners_before"], selection)
    pages = [prefix(metadata, route, r, s) for route, (s, r) in zip(("optimized", "reference"), pairs, strict=True)]
    require(typed_equal(pages[0][0]["entries"], pages[1][0]["entries"])
            and typed_equal(pages[0][0]["inference"], pages[1][0]["inference"]), "exact same returned prefix population/declarations")
    members, prefix_members = root["members"], root["members"][:32]
    by_path = {m["path"]: m for m in members}
    require(all(s["path"] in by_path for s in request["selections"]), "child role paths in current membership")
    roles = {s["path"]: s["role"] for s in request["selections"]}
    selected = prefix_members + [by_path[path] for path in sorted(roles) if path not in {m["path"] for m in prefix_members}]
    require(len(selected) <= 35 and set(sources) == {m["source_cid"] for m in selected}
            and set(asts) == {m["ast_cid"] for m in selected if m["ast_cid"] is not None}, "exact selected source/AST body population")
    rows = []
    for m in selected:
        raw, captured = sources[m["source_cid"]], asts.get(m["ast_cid"])
        require(cid(raw) == m["source_cid"] and (captured is None or object_cid(captured) == m["ast_cid"]), "source/AST CID preimages")
        rows.append(dict(path=m["path"], source_key=m["source_key"], source_cid=m["source_cid"], ast_cid=m["ast_cid"],
                         child_declared_role=roles.get(m["path"]), in_prefix=m in prefix_members,
                         **syntax(m, raw, captured, selection["current_head"])))
    by_selected_path = {r["path"]: r for r in rows}
    overlaps = []
    template_overlaps = []
    for p in rows[:32]:
        for selected_path, role in sorted(roles.items()):
            s = by_selected_path[selected_path]
            exact = p["source_sha256"] == s["source_sha256"]
            clone = p["normalized_ast_sha256"] is not None and p["normalized_ast_sha256"] == s["normalized_ast_sha256"]
            if exact or clone:
                overlaps.append(dict(prefix_path=p["path"], declared_selection_path=selected_path, declared_child_role=role,
                                     same_path=p["path"] == selected_path, exact_source_equal=exact, normalized_ast_equal=clone))
            if p["template_ast_sha256"] is not None and p["template_ast_sha256"] == s["template_ast_sha256"]:
                template_overlaps.append(dict(prefix_path=p["path"], declared_selection_path=selected_path,
                                              declared_child_role=role, scope="constant_type_masked_syntax_only"))
    groups = defaultdict(list)
    for row in rows:
        if row["normalized_ast_sha256"] is not None:
            groups[row["normalized_ast_sha256"]].append(row["path"])
    for n in (native, failed):
        require(n["schema"] == "codebase-source-successor-native-qualification@1", "closed native attempt schema")
        require(type(n["recorded_seconds"]) in {int, float} and 0 <= n["recorded_seconds"] <= 10**7, "bounded recorded attempt cost")
        require(n["training_attempts_after_setup"] == 0 and type(n["training_attempts_after_setup"]) is int
                and n["inference_attempts_during_selection_or_cold_receiving"] == 0
                and type(n["inference_attempts_during_selection_or_cold_receiving"]) is int, "recorded no-fit receiving declaration")
        attempts = n["setup_training_attempts"]
        require(type(attempts) is list and len(attempts) == 2 and {a["name"] for a in attempts} == {"root", "child"}, "recorded setup attempt population")
        for a in attempts:
            integer(a["requested_epochs"], 1, 1, "typed requested setup epochs")
            integer(a["actual_completed_epochs"], 1, 1, "typed recorded completed setup epochs")
            require(a["unknown_actual_epochs_on_failure"] is False, "closed recorded epoch disposition")
        integer(n["new_fitting_epochs"], 2, 2, "typed recorded total setup epochs")
    require(native["qualified"] is True and failed["qualified"] is False and failed["error_type"] == "LeaseTimeoutError", "successful/failed native attempts remain distinct")
    require(native["parent_version_id"] == selection["previous_model"]["version_id"]
            and native["child_version_id"] == selection["model"]["version_id"]
            and typed_equal(native["current_head"], selection["current_head"])
            and typed_equal(native["previous_head"], selection["previous_head"]), "successful native identity declarations")
    return dict(complete_member_count=len(members), unique_prefix_member_count=32, prefix_page_count=2,
                outside_prefix_member_count=len(members) - 32, selected_path_count=len(selected), source_body_count=len(sources), ast_body_count=len(asts),
                declared_child_role_counts=dict(sorted(Counter(roles.values()).items())), prefix_dispositions=pages[0][1],
                exact_source_role_overlap_count=sum(x["exact_source_equal"] for x in overlaps),
                normalized_clone_role_overlap_count=sum(x["normalized_ast_equal"] for x in overlaps), normalized_ast_group_count=len(groups),
                template_role_overlap_count=len(template_overlaps), template_role_overlaps=template_overlaps,
                declared_parent_version_id=selection["previous_model"]["version_id"], declared_child_version_id=selection["model"]["version_id"],
                declared_feature_columns=selection["model"]["feature_columns"], claimed_successful_setup_epochs=native["new_fitting_epochs"],
                claimed_failed_setup_epochs=failed["new_fitting_epochs"], claimed_total_native_setup_epochs=native["new_fitting_epochs"] + failed["new_fitting_epochs"],
                root_exposure_disposition="unknown_missing_root_selection_and_source_targets", replay_exposure_disposition="unknown_missing_replay_population",
                selected_sources=rows, declared_role_overlaps=overlaps,
                normalized_clone_groups=[{"sha256": k, "paths": v} for k, v in sorted(groups.items()) if len(v) > 1],
                prefix_paths=[m["path"] for m in prefix_members], outside_prefix_paths=[m["path"] for m in members[32:]],
                child_request_declaration=request, model_declarations={"parent": selection["previous_model"], "child": selection["model"]},
                native_target_digest_disposition="opaque_returned_declaration_not_independently_rederived",
                snapshot_schema_disposition="unavailable_excluded_1421504_byte_manifest",
                source_label_scope="source_only_closed_annotation_profile_not_runtime_semantics",
                receiving_declarations={"new_post_setup_training_attempts": 0, "selection_and_cold_receiving_inference_attempts": 0},
                historical_attempt_costs={"successful_recorded_seconds": native["recorded_seconds"], "failed_recorded_seconds": failed["recorded_seconds"]})


def archive_pins(value):
    require(value["schema"] == "codebase-source-successor-independent-audit@1", "closed independent audit schema")
    files = value["archive"]["files"]
    require(type(files) is list and len(files) <= 2048, "bounded archive declaration metadata")
    result = {}
    for item in files:
        require(type(item) is dict and type(item.get("path")) is str and item["path"] not in result, "unique declared archive selectors")
        result[item["path"]] = item
    return result


def checkpoint(stage, output):
    """Explicit receiving boundary for authored late-drift controls."""


def population(output, expected):
    require(output.is_absolute() and output.resolve(strict=True) == output
            and stat.S_ISDIR(output.stat(follow_symlinks=False).st_mode), "canonical output directory guard")
    files, dirs = set(), set()
    for parent, children, names in os.walk(output, followlinks=False):
        require(len(files) + len(dirs) + len(children) + len(names) <= MAX_FILES, "bounded output population")
        for name in children:
            p = Path(parent) / name
            require(stat.S_ISDIR(p.stat(follow_symlinks=False).st_mode), "regular nonsymlink output directory")
            dirs.add(p.relative_to(output).as_posix())
        for name in names:
            p = Path(parent) / name
            require(stat.S_ISREG(p.stat(follow_symlinks=False).st_mode), "regular nonsymlink output body")
            files.add(p.relative_to(output).as_posix())
    require(files == set(expected) and dirs == {"inputs"}, "exact closed output population")


def evaluate(manifest_path, output):
    manifest_path, output = Path(manifest_path), Path(output)
    raw_manifest = Reads.bounded(manifest_path, 128 * 1024)
    manifest = document(raw_manifest)
    closed(manifest, {"schema", "metadata", "source_artifacts", *ROLES}, "closed successor cohort manifest")
    require(manifest["schema"] == INPUT_SCHEMA, "unsupported cohort input schema")
    closed(manifest["metadata"], METADATA, "closed selected metadata roles")
    require(type(manifest["source_artifacts"]) is list and len(manifest["source_artifacts"]) <= 69, "bounded exact source artifact selectors")
    reads, planned = Reads(), []
    for role in ROLES:
        d = manifest[role]
        p = descriptor(d)
        require(d["sha256"] == ANCHORS[role], "fixed outer original receipt anchor")
        reads.reserve(p, {k: d[k] for k in ("sha256", "size_bytes")}, MiB)
        planned.append((role, p, None))
    for role in METADATA:
        d = manifest["metadata"][role]
        p = descriptor(d)
        reads.reserve(p, {k: d[k] for k in ("sha256", "size_bytes")}, MiB)
        planned.append((role, p, METADATA[role]))
    for index, d in enumerate(manifest["source_artifacts"]):
        closed(d, {"path", "sha256", "size_bytes", "selector"}, "closed selected source descriptor")
        selector = d["selector"]
        require(type(selector) is str and selector.startswith(("private/source-artifacts/source/", "private/source-artifacts/structured/"))
                and len(PurePosixPath(selector).parts) == 5 and ".." not in PurePosixPath(selector).parts, "explicit source-only selector")
        p = descriptor({k: d[k] for k in ("path", "sha256", "size_bytes")})
        reads.reserve(p, {k: d[k] for k in ("sha256", "size_bytes")}, 65536 if "/source/" in selector else 128 * 1024)
        planned.append(("artifact_" + str(index), p, selector))
    require(len(reads.plan) == len(planned), "distinct selected body paths")
    bodies = {label: reads.take(p) for label, p, _ in planned}
    outer = {role: document(bodies[role]) for role in ROLES}
    require(outer["review"]["schema"] == "repository-proof-index-source-successor-review@1", "review schema")
    for review_field, role in (("native_result", "native_result"), ("independent_closed_audit", "independent_audit"), ("failed_native_attempt", "failed_result")):
        claim = outer["review"][review_field]
        if role == "failed_result":
            claim = claim["result"]
        require(claim["sha256"] == manifest[role]["sha256"] and claim["bytes"] == manifest[role]["size_bytes"], "review/selected receipt raw bindings")
    require(outer["independent_audit"]["audited_result"]["sha256"] == manifest["native_result"]["sha256"]
            and outer["independent_audit"]["audited_result"]["bytes"] == manifest["native_result"]["size_bytes"], "audit/native result raw binding")
    pins = archive_pins(outer["independent_audit"])
    sources, asts, selectors = {}, {}, set()
    for label, _p, selector in planned:
        if selector is None:
            continue
        require(selector in pins and pins[selector]["kind"] == "file" and pins[selector]["bytes"] == len(bodies[label])
                and pins[selector]["sha256"] == sha(bodies[label]), "exact audit-declared child raw pin")
        require(selector not in selectors, "duplicate explicit child selector")
        selectors.add(selector)
        if label.startswith("artifact_"):
            identity = PurePosixPath(selector).name
            require(selector == "private/source-artifacts/" + ("source" if "/source/" in selector else "structured") + "/" + identity[:4] + "/" + identity, "exact source artifact selector")
            if "/source/" in selector:
                require(cid(bodies[label]) == identity, "exact raw source CID")
                sources[identity] = bodies[label]
            else:
                captured = document(bodies[label])
                require(object_cid(captured) == identity and cid(bodies[label], True) == identity, "exact captured AST CID")
                asts[identity] = captured
    metadata = {role: document(bodies[role]) for role in METADATA}
    derived = derive(metadata, sources, asts, outer["native_result"], outer["failed_result"])
    native, captured_audit = outer["native_result"], outer["independent_audit"]
    require(native["root_cid"] == metadata["optimized_root"]["artifact_cid"]
            and native["prefix_page_cid"] == metadata["optimized_prefix"]["artifact_cid"]
            and native["successor_selection_cid"] == metadata["optimized_selection"]["artifact_cid"], "native/default captured artifact joins")
    for audit_field, role in (("default_root", "optimized_root"), ("reference_root", "reference_root"),
                             ("default_prefix_page", "optimized_prefix"), ("reference_prefix_page", "reference_prefix"),
                             ("default_selection", "optimized_selection"), ("reference_selection", "reference_selection")):
        require(captured_audit["native_artifact_cids"][audit_field] == metadata[role]["artifact_cid"], "audit/captured artifact joins")
    require(not output.exists() and not output.is_symlink() and output.is_absolute()
            and output.parent.resolve(strict=True) == output.parent, "fresh canonical output path required")
    protected = {manifest_path.parent, *(p.parent for _, p, _ in planned)}
    require(all(output != scope and scope not in output.parents and output not in scope.parents for scope in protected), "protected selected input scope")
    output.mkdir()
    (output / "inputs").mkdir()
    retained = []
    input_copy = output / "input.json"
    with input_copy.open("xb") as stream:
        stream.write(raw_manifest)
    expected = {"input.json"}
    for index, (label, p, selector) in enumerate(planned):
        relative = "inputs/" + f"{index:03d}-{label}.body"
        target = output / relative
        with target.open("xb") as stream:
            stream.write(bodies[label])
        expected.add(relative)
        retained.append({"role": label, "path": str(p), "retained_path": str(target), "sha256": sha(bodies[label]),
                         "size_bytes": len(bodies[label]), "selector": selector})
    checkpoint("after_copy", output)
    report = dict(schema=REPORT_SCHEMA, status="passed", manifest_sha256=sha(raw_manifest),
                  **{role + "_sha256": manifest[role]["sha256"] for role in ROLES},
                  **dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False),
                  runtime_fact_count=0, tasks_omitted_count=0, additional_attempted_training_epochs=0, new_final_assignments=0,
                  selected_original_count=len(planned), selected_original_bytes=sum(len(b) for b in bodies.values()), input_files=retained,
                  selected_original_manifest={"path": str(manifest_path), "sha256": sha(raw_manifest), "size_bytes": len(raw_manifest), "retained_path": str(input_copy)},
                  **derived)
    encoded = report_bytes(report)
    reads.stable()
    require(Reads.bounded(manifest_path, 128 * 1024) == raw_manifest, "late original input manifest drift")
    checkpoint("after_final_originals", output)
    require(Reads.bounded(input_copy, len(raw_manifest)) == raw_manifest, "late retained manifest drift")
    for item in retained:
        require(Reads.bounded(Path(item["retained_path"]), item["size_bytes"]) == bodies[item["role"]], "late retained selected body drift")
    checkpoint("after_final_copies", output)
    population(output, expected)
    report_path = output / "successor_cohort_audit.json"
    with report_path.open("xb") as stream:
        stream.write(encoded)
    published = report_path.stat(follow_symlinks=False)
    try:
        checkpoint("after_publish", output)
        reads.stable()
        require(Reads.bounded(manifest_path, 128 * 1024) == raw_manifest, "closing original manifest drift")
        require(Reads.bounded(input_copy, len(raw_manifest)) == raw_manifest, "closing retained manifest drift")
        for item in retained:
            require(Reads.bounded(Path(item["retained_path"]), item["size_bytes"]) == bodies[item["role"]], "closing retained selected body drift")
        require(Reads.bounded(report_path, 4 * MiB) == encoded, "final report raw body drift")
        population(output, expected | {report_path.name})
    except (OSError, ValueError, TypeError):
        if output.resolve(strict=True) == output and report_path.exists():
            current = report_path.stat(follow_symlinks=False)
            if (published.st_dev, published.st_ino) == (current.st_dev, current.st_ino):
                report_path.unlink()
        raise
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (Refused, OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError, RecursionError, OverflowError) as exc:
        print(json.dumps({"schema": REPORT_SCHEMA, "status": "refused", "reason": str(exc),
                          "unknown_pretraining_exposure": True, **dict.fromkeys(FALSE_FLAGS, False)}))
        return 2
    print(json.dumps({"status": report["status"], "unique_prefix_member_count": report["unique_prefix_member_count"],
                      "normalized_clone_role_overlap_count": report["normalized_clone_role_overlap_count"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
