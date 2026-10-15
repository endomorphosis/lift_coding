"""Inventory explicitly exported AA evidence without opening native stores.

Run only after the selected actual invocation succeeds: --config /absolute/file.
The closed config names model_report, fixture_report, actual_report,
boundary_report, source_copy_inventory, runtime_freeze,
proof_source_provision_report, tool_mappings, metadata_only_tool_paths.
Report fields are absolute named JSON paths. A tool mapping is exactly
{container_path, host_pin:{path,bytes,sha256}}. No payload paths are rewritten.
The output reports are exclusive. This utility invokes no native imports/jobs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

AA = Path(__file__).resolve().parent
CHECKOUT = AA / "checkout"
Z = AA.parent / "terminal-checked-worker-context-20261013-01"
BOUND = 8 * 1024 * 1024
SIGNATURE = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
             "st_size", "st_mtime_ns", "st_ctime_ns")
PRODUCERS = (
    "ipfs_accelerate_py/agent_supervisor/runtime/checked_observer_budget.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/checked_context_dispatch.py",
    "ipfs_accelerate_py/agent_supervisor/entrypoints/admitted_benchmark_runtime.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/model_input_observation_receipt.py",
    "benchmarks/agent_supervisor/container_coding/container_worker_deployment.py",
    "ipfs_accelerate_py/agent_supervisor/todo_daemon/supervisor_runtime.py",
    "ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py",
    "benchmarks/agent_supervisor/container_coding/terminal_checked_worker_budget.py",
)
PROOF_SOURCES = tuple("benchmarks/agent_supervisor/container_coding/" + name for name in (
    "terminal_source_ir_lowering.py", "terminal_source_ir_projection.py",
    "terminal_revision_proof_cache.py"))
FIXTURE_NAMES = {
    "source.gitbundle", "manifest.json", "graph.json", "admission.json", "materialization.json",
    "context-preparation.json", "task-readback.json", "native-prompt.txt", "native-capsule.json",
    "compilation-receipt.json", "instruction-descriptor.json", "context-bundle.json", "owner-receipt.json",
}
CONFIG_FIELDS = {"schema", "model_report", "fixture_report", "actual_report", "boundary_report",
                 "source_copy_inventory", "runtime_freeze", "proof_source_provision_report",
                 "tool_mappings", "metadata_only_tool_paths"}


def need(value, message):
    if not value:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def strict_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            need(key not in result, "duplicate JSON member refused")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON refused")))


def signature(info):
    return tuple(getattr(info, name) for name in SIGNATURE)


def sha(value):
    need(type(value) is str, "SHA256 string required")
    result = value.removeprefix("sha256:")
    need(re.fullmatch(r"[0-9a-f]{64}", result), "canonical SHA256 required")
    return result


def file_pin(value):
    need(type(value) is dict and set(value) == {"path", "bytes", "sha256"}, "closed file pin required")
    need(type(value["path"]) is str and type(value["bytes"]) is int and 0 <= value["bytes"] <= BOUND,
         "bounded exact integer file length required")
    need(sha(value["sha256"]) == value["sha256"], "unprefixed file SHA256 required")
    return value


def relative(value):
    need(type(value) is str and 0 < len(value) <= 4096, "bounded relative path required")
    path = PurePosixPath(value)
    need(not path.is_absolute() and path.as_posix() == value and ".." not in path.parts,
         "canonical relative path required")
    return path


def container_path(value):
    need(type(value) is str and 0 < len(value) <= 4096, "bounded container path required")
    path = PurePosixPath(value)
    need(path.is_absolute() and path.as_posix() == value and ".." not in path.parts,
         "canonical absolute container identity required")
    return value


def private_path(value):
    path = PurePosixPath(value)
    return bool(set(path.parts) & {"cas", "lake", ".git"}) or path.suffix in {
        ".db", ".duckdb", ".parquet", ".wal"}


class Retained:
    def __init__(self):
        self.witnesses = []

    def read(self, path, expected=None):
        path = Path(path)
        need(path.is_absolute() and path.resolve(strict=True) == path,
             "canonical explicitly named file required")
        need(not private_path(str(path)), "private store body read refused")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(fd)
        self.witnesses.append((path, fd, before, None))
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == os.geteuid()
             and 0 <= before.st_size <= BOUND, "bounded owned single-link regular file required")
        raw = self._bytes(fd)
        need(len(raw) == before.st_size
             and signature(before) == signature(os.fstat(fd)) == signature(path.lstat()),
             "named file custody changed during capture")
        pin = {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        self.witnesses[-1] = (path, fd, before, pin["sha256"])
        if expected is not None:
            need(file_pin(expected) == pin, "expected named file pin differs")
        return pin, raw

    @staticmethod
    def _bytes(fd):
        os.lseek(fd, 0, os.SEEK_SET)
        chunks, count = [], 0
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            chunks.append(block)
            count += len(block)
            need(count <= BOUND, "named file bound exceeded")
        return b"".join(chunks)

    def json(self, path):
        pin, raw = self.read(path)
        return pin, strict_json(raw)

    def recheck(self):
        for path, fd, before, digest in self.witnesses:
            need(path.resolve(strict=True) == path
                 and signature(before) == signature(os.fstat(fd)) == signature(path.lstat()),
                 "retained file stat witness changed")
            raw = self._bytes(fd)
            need(len(raw) == before.st_size and hashlib.sha256(raw).hexdigest() == digest
                 and signature(before) == signature(os.fstat(fd)) == signature(path.lstat()),
                 "retained file bytes/stat changed")
            fresh = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                need(signature(os.fstat(fresh)) == signature(before) and self._bytes(fresh) == raw
                     and signature(os.fstat(fresh)) == signature(before)
                     and signature(path.lstat()) == signature(before), "fresh named file witness differs")
            finally:
                os.close(fresh)

    def close(self):
        for _, fd, _, _ in self.witnesses:
            os.close(fd)


def write_exclusive(path, value):
    raw = wire(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    retained = Retained()
    try:
        producer_pin, _ = retained.read(Path(__file__).resolve())
        config_pin, config = retained.json(args.config)
        need(type(config) is dict and set(config) == CONFIG_FIELDS
             and config["schema"] == "terminal-admitted-context-evidence-inventory-config@1",
             "closed inventory config required")
        reports, report_pins = {}, {}
        for key in sorted(CONFIG_FIELDS - {"schema", "tool_mappings", "metadata_only_tool_paths"}):
            path = Path(config[key])
            need(path.is_relative_to(AA) and path.suffix == ".json", "AA named report required")
            report_pins[key], reports[key] = retained.json(path)
        model_report, fixture_report, actual_report = (reports[key] for key in (
            "model_report", "fixture_report", "actual_report"))
        for key in ("model_report", "fixture_report", "actual_report", "boundary_report",
                    "proof_source_provision_report"):
            need(reports[key].get("qualified") is True, "selected qualified report required: " + key)
        need(model_report["schema"] == "admitted-budget-container-model-execution@1"
             and fixture_report["schema"] == "admitted-budget-native-fixture-preparation@1"
             and actual_report["schema"] == "admitted-budget-actual-owner-invocation@1",
             "selected execution report schemas differ")
        boundary = reports["boundary_report"]
        need(actual_report["container"] == boundary["container"]
             and actual_report["container_disposal"]["container_absent"] is True
             and actual_report["container_disposal"]["only_exact_owned_container_removed"] is True,
             "exact selected owned boundary cleanup required")

        baseline_pin, baseline = retained.json(AA / "preservation-baseline.json")
        prior_pin, prior = retained.json(Z / "preservation-final.json")
        need(baseline["verified_file_occurrences"] == len(baseline["sealed_previous_files"]) == 650,
             "complete 650-occurrence AA preservation baseline required")
        need(prior["qualified"] is True and prior["checked_occurrences"] == len(prior["occurrences"]),
             "complete sealed Z final occurrence inventory required")
        occurrences = []
        for group, rows in (("AA_preservation_baseline", baseline["sealed_previous_files"]),
                            ("sealed_Z_preservation_final_expected_occurrences",
                             [row["expected"] for row in prior["occurrences"]])):
            for ordinal, expected in enumerate(rows):
                actual, _ = retained.read(expected["path"], expected)
                occurrences.append({"group": group, "ordinal": ordinal, "expected": expected,
                                    "actual": actual, "unchanged": True})

        pattern_pin, pattern = retained.json(Z / "actual-public-inventory.json")
        pattern_base = Z / "actual-public-checked-01"
        need(pattern["explicit_named_file_count"] == len(pattern["files"]) == 113,
             "exact predecessor 113-file public path pattern required")
        selected_names = []
        for row in pattern["files"]:
            path = Path(row["path"])
            need(path.is_relative_to(pattern_base), "predecessor public path pattern escaped")
            name = relative(path.relative_to(pattern_base).as_posix())
            need(not private_path(str(name)) and (name.suffix in {".json", ".jsonl", ".py", ".lean", ".olean"}
                 or str(name) in {"model/candidate-cache/artifact.bin", "model/callee/candidate-cache/artifact.bin"}),
                 "unrecognized or private model public path refused")
            selected_names.append(str(name))
        need(len(set(selected_names)) == 113, "unique predecessor path pattern required")

        public_files, mappings, raw_by_container, group_counts = [], {}, {}, {}

        def add_mapping(identity, host_pin, raw, group):
            identity = container_path(identity)
            need(not private_path(identity), "private storage mapping refused")
            if identity in mappings:
                need(mappings[identity]["host_pin"] == host_pin, "conflicting public identity mapping")
                return
            mappings[identity] = {"container_path": identity, "host_pin": host_pin, "group": group}
            raw_by_container[identity] = raw

        def capture_group(rows, expected_parent, group, make_identity):
            need(type(rows) is list, "explicit selected public pins required")
            captured, names = [], set()
            for row in rows:
                file_pin(row)
                path = Path(row["path"])
                need(path.is_relative_to(expected_parent), "selected public export escaped its namespace")
                name = relative(path.relative_to(expected_parent).as_posix())
                need(str(name) not in names and not private_path(str(name)), "duplicate/private public export refused")
                names.add(str(name))
                pin, raw = retained.read(path, row)
                add_mapping(make_identity(name), pin, raw, group)
                captured.append(pin)
            public_files.extend(captured)
            group_counts[group] = len(captured)
            return names

        model_parent = Path(config["model_report"]).parent / "public"
        exported = model_report["public_export"]
        model_root = container_path(exported["private_model_state"])
        need(re.fullmatch(r"/opt/ipfs-supervisor/state/aa-model-[0-9]{2}", model_root)
             and exported["source_repository"] == "/app" and exported["directory_walk_used"] is False
             and exported["database_cas_lake_bodies_exported"] is False, "selected model export profile differs")

        def model_identity(name):
            return "/app/" + str(PurePosixPath(*name.parts[1:])) if name.parts[0] == "repository" else model_root + "/" + str(name)

        captured_names = capture_group(model_report["public_files"], model_parent, "model", model_identity)
        need(captured_names == set(selected_names), "current public export differs from exact 113-file pattern")
        export_rows = {row["relative_path"]: row for row in exported["files"]}
        need(len(export_rows) == len(exported["files"]) == 113 and set(export_rows) == captured_names,
             "container export relative inventory differs")
        for name, row in export_rows.items():
            identity = model_identity(relative(name))
            need(row["container_path"] == identity and row["bytes"] == mappings[identity]["host_pin"]["bytes"]
                 and row["sha256"] == mappings[identity]["host_pin"]["sha256"], "container/host model export pin differs")

        fixture_root = container_path(fixture_report["native_summary"]["public_directory"])
        need(re.fullmatch(r"/opt/ipfs-supervisor/public-fixture-aa[0-9]{2}", fixture_root),
             "known fixture public namespace required")
        fixture_parent = Path(config["fixture_report"]).parent / "public"
        need(capture_group(fixture_report["public_exports"], fixture_parent, "fixture",
             lambda name: fixture_root + "/" + str(name)) == FIXTURE_NAMES, "exact thirteen fixture exports required")
        actual_root = container_path(actual_report["owner_execution"]["public_directory"])
        need(re.fullmatch(r"/opt/ipfs-supervisor/state/aa-start-[0-9]{2}/public", actual_root),
             "known actual public namespace required")
        actual_parent = Path(config["actual_report"]).parent / "public"
        actual_names = actual_report["owner_execution"]["public_files"]
        need(type(actual_names) is list and 1 <= len(actual_names) <= 80 and len(set(actual_names)) == len(actual_names),
             "bounded unique actual public inventory required")
        for name in actual_names:
            path = relative(name)
            need(len(path.parts) == 1 and path.suffix in {".json", ".txt", ".log", ".stdout", ".stderr"},
                 "actual public name refused")
        need(capture_group(actual_report["public_exports"], actual_parent, "actual",
             lambda name: actual_root + "/" + str(name)) == set(actual_names), "actual public exports differ")

        declared_model = set()

        def public(identity):
            container_path(identity)
            need(identity in mappings, "public declaration outside explicit identity mapping: " + identity)
            if mappings[identity]["group"] == "model":
                declared_model.add(identity)
            return mappings[identity]["host_pin"]

        def literal(identity):
            public(identity)
            return strict_json(raw_by_container[identity])

        def descriptor(row):
            pin = public(row["path"])
            length = row.get("bytes", row.get("size_bytes"))
            need(type(length) is int and pin["bytes"] == length and pin["sha256"] == sha(row["sha256"]),
                 "public artifact descriptor differs")

        model = literal(model_root + "/model/result.json")
        need(model["qualified"] is True and model["model_status"] == "model_proved", "selected checked model required")
        child = literal(model["callee"]["output"] + "/result.json")
        need(wire(child) == wire(model["callee"]), "retained native callee result differs")
        for record in (model, child):
            output = record["output"]
            for name in ("cache-report.json", "cache-dimensions.json"):
                public(output + "/" + name)
            for name in ("projection", "generated", "source", "callee_object", "caller_object", "process", "native_proof"):
                if name in record:
                    descriptor(record[name])
            cache = record["advisory_cache"]
            descriptor(cache["artifact"])
            public(cache["output"] + "/artifact.bin")
            literal(cache["output"] + "/manifest.json")
            need(public(cache["output"] + "/manifest.json")["sha256"] == sha(cache["manifest_sha256"]),
                 "candidate manifest declaration differs")
            for report in (record["metadata"], cache["metadata"]):
                directory = report["output"]
                manifest = literal(directory + "/manifest.json")
                need(public(directory + "/manifest.json")["sha256"] == sha(report["manifest_sha256"])
                     and manifest["output"] == directory, "native metadata manifest declaration differs")
                for family, family_record in manifest["families"].items():
                    export = family_record["export"]
                    need(wire(export) == wire(report["exports"][family]), "metadata export/report differs")
                    target = directory + "/" + str(relative(export["relative_path"]))
                    pin = public(target)
                    need(pin["bytes"] == export["bytes"] and pin["sha256"] == sha(export["sha256"]),
                         "metadata public export pin differs")
                for batch in manifest["batches"]:
                    target = directory + "/" + str(relative(batch["relative_path"]))
                    pin = public(target)
                    need(pin["bytes"] == batch["bytes"] and pin["sha256"] == sha(batch["sha256"]),
                         "native public batch pin differs")
        native = literal(child["native_proof"]["path"])
        literal(native["output"] + "/result.json")
        for row in native["artifacts"].values():
            descriptor(row)
        public(child["output"] + "/checked-object.olean")
        metadata = literal(model["metadata"]["output"] + "/manifest.json")
        source_rows = metadata["source_snapshot"]["revision"]["sources"]
        need(sorted(row["path"] for row in source_rows) == model["paths"] == ["callee.py", "caller.py", "dynamic.py"],
             "whole authored Python scope differs")
        for row in source_rows:
            pin = public("/app/" + str(relative(row["path"])))
            need(pin["bytes"] == row["bytes"] and pin["sha256"] == sha(row["sha256"]), "source leaf differs")
        public(model_root + "/prepared.json")
        public(model_root + "/qualification-summary.json")
        need(declared_model == {key for key, row in mappings.items() if row["group"] == "model"},
             "exact113 native public declaration closure differs")

        owner = literal(fixture_root + "/owner-receipt.json")
        signed_manifest = literal(fixture_root + "/manifest.json")["payload"]
        inventory = owner["source_inventory"]
        need(set(inventory) == set(signed_manifest["sources"]) == {
            "callee.py", "caller.py", "dynamic.py", "build/task-instruction.txt"}, "signed native source domain differs")
        for name, row in inventory.items():
            need(row["sha256"] == signed_manifest["sources"][name]["sha256"], "signed source declaration differs")
            if name != "build/task-instruction.txt":
                pin = public("/app/" + name)
                need(pin["bytes"] == row["bytes"] and pin["sha256"] == row["sha256"], "signed Python source differs")
        instruction = owner["instruction_text"].encode("utf-8")
        need(len(instruction) == inventory["build/task-instruction.txt"]["bytes"] == owner["instruction_bytes"]
             and hashlib.sha256(instruction).hexdigest() == inventory["build/task-instruction.txt"]["sha256"],
             "public retained instruction text differs from signed source pin")
        summary = literal(actual_root + "/summary.json")
        need(wire(summary) == wire(actual_report["actual_summary"]) and summary["qualified"] is True
             and summary["public_files"] == actual_names, "actual summary/host report differs")
        need(summary["native_admitted_benchmark_runtime_START_used"] is True
             and summary["actual_native_worker_observer_invocations"] == 1 and summary["provider_calls"] == 0,
             "selected actual one-observer zero-provider result required")
        for name, data in (("checked-context-public-artifact.json", literal(actual_root + "/native-checked-descriptor.json")),
                           ("public-instruction-artifact.json", owner["public_instruction"])):
            exported_identity = actual_root + "/" + name
            pin = public(exported_identity)
            need(pin["sha256"] == sha(data["sha256"]), "exported immutable artifact digest differs")
            add_mapping(data["artifact"], pin, raw_by_container[exported_identity], "immutable_artifact_alias")

        freeze = reports["runtime_freeze"]
        need(freeze["schema"] == "terminal-admitted-context-runtime-freeze@1" and len(freeze["files"]) == 6,
             "selected six-file runtime freeze required")
        frozen = {row["relative_path"]: row for row in freeze["files"]}
        need(len(frozen) == 6 and set(frozen) <= set(PRODUCERS), "frozen producer subset differs")
        execution_freezes = []
        for key in ("model_report", "fixture_report", "actual_report", "boundary_report",
                    "proof_source_provision_report"):
            expected = file_pin(reports[key]["runtime_freeze"])
            pin, raw = retained.read(expected["path"], expected)
            declared_freeze = strict_json(raw)
            need(declared_freeze["schema"] == "terminal-admitted-context-runtime-freeze@1"
                 and wire(declared_freeze["files"]) == wire(freeze["files"]),
                 "selected execution freeze production files differ")
            execution_freezes.append({"report": key, "freeze": pin, "six_production_pins_equal": True})
        copy_map = {}
        for row in reports["source_copy_inventory"]["files"]:
            target = relative(row["target"])
            need(target.parts[0] in {"source", "datasets", "kit"}, "unknown public source inventory domain")
            identity = "/opt/ipfs-supervisor/" + str(target)
            need(identity not in copy_map, "duplicate copied source identity")
            copy_map[identity] = {"path": row["source"], "bytes": row["bytes"], "sha256": row["sha256"]}
        producer_record = literal(actual_root + "/container-producer-pins.json")
        need(producer_record["loaded_module_code_attested"] is False
             and producer_record["transitive_dependency_closure_attested"] is False,
             "declared producer attestation ceiling differs")
        deployed = producer_record["files"]
        need(len(deployed) == 9 and {row["relative_path"] for row in deployed} == set(PRODUCERS),
             "exact nine deployed producer declarations required")
        producer_joins = []
        for row in deployed:
            name = row["relative_path"]
            identity = "/opt/ipfs-supervisor/source/" + name
            expected = {"path": str(CHECKOUT / name), "bytes": row["bytes"], "sha256": row["sha256"]}
            need(row["path"] == identity and row["uid"] == 0 and row["mode"] == "0o444"
                 and copy_map[identity] == expected, "deployed root-owned file/source inventory differs")
            pin, raw = retained.read(expected["path"], expected)
            if name in frozen:
                need({key: frozen[name][key] for key in ("path", "bytes", "sha256")} == pin,
                     "deployed producer differs from six-file runtime freeze")
            add_mapping(identity, pin, raw, "declared_production_source")
            producer_joins.append({"relative_path": name, "deployed": row, "host_pin": pin,
                                   "in_six_file_freeze": name in frozen, "root_owned_ancestor_attested": False})

        provision = reports["proof_source_provision_report"]["provision"]
        need(provision["qualified"] is True and set(provision["proof_files"]) == set(PROOF_SOURCES)
             and set(provision["runtime_files"]) == set(PRODUCERS)
             and provision["root_owned_source_ancestor_attestation"] is False
             and provision["trusted_original_owner_parent"] is True
             and provision["recursive_chown_used"] is False, "narrow proof source ownership provision differs")
        need(set(provision["after"]) == set(provision["before"]) == set(PROOF_SOURCES) | set(PRODUCERS)
             and provision["source_bytes_unchanged"] is True
             and provision["runtime_nine_files_root_owned"] is True,
             "complete twelve-file proof provision witness required")
        parent_after, parent_before = provision["parent_after"], provision["parent_before"]
        need(parent_after["path"] == parent_before["path"] == "/opt/ipfs-supervisor/source/benchmarks/agent_supervisor/container_coding"
             and parent_before["uid"] == 0 and parent_before["mode"] == "0o755"
             and parent_after["uid"] == 1000 and parent_after["mode"] == "0o555",
             "exact trusted-owner proof parent provision differs")
        for name, row in provision["after"].items():
            previous = provision["before"][name]
            need(all(row[key] == previous[key] for key in ("path", "bytes", "sha256", "inode", "device"))
                 and row["uid"] == (1000 if name in PROOF_SOURCES else 0) and row["mode"] == "0o444",
                 "proof provision changed bytes or runtime ownership")
            need(copy_map[row["path"]] == {"path": str(CHECKOUT / name), "bytes": row["bytes"], "sha256": row["sha256"]},
                 "proof provision/current copied source pin differs")

        need(type(config["tool_mappings"]) is list and type(config["metadata_only_tool_paths"]) is list,
             "explicit tool mappings and metadata-only identities required")
        for row in config["tool_mappings"]:
            need(type(row) is dict and set(row) == {"container_path", "host_pin"}, "closed tool mapping required")
            identity = container_path(row["container_path"])
            need(not identity.endswith(".py") and identity not in mappings, "tool/source mapping overlap refused")
            pin, raw = retained.read(row["host_pin"]["path"], file_pin(row["host_pin"]))
            add_mapping(identity, pin, raw, "explicit_public_tool")
        metadata_tools = {container_path(value) for value in config["metadata_only_tool_paths"]}
        need(len(metadata_tools) == len(config["metadata_only_tool_paths"])
             and not metadata_tools & set(mappings), "duplicate/mapped metadata-only tool identity")

        dependencies, metadata_only = [], []

        def walk(value, origin, pointer="", depth=0):
            need(depth <= 128, "bounded public descriptor nesting required")
            if type(value) is dict:
                if type(value.get("path")) is str and type(value.get("sha256")) is str and (
                        "bytes" in value or "size_bytes" in value):
                    identity = value["path"]
                    length = value.get("bytes", value.get("size_bytes"))
                    digest = sha(value["sha256"])
                    need(type(length) is int and length >= 0, "exact descriptor byte length required")
                    if not PurePosixPath(identity).is_absolute():
                        need(identity in {"callee.py", "caller.py", "dynamic.py"},
                             "unknown relative source descriptor refused")
                        identity = "/app/" + identity
                    container_path(identity)
                    if identity in metadata_tools or private_path(identity):
                        metadata_only.append({"origin": origin, "pointer": pointer, "descriptor": value,
                            "reason": "explicit_tool_metadata_only" if identity in metadata_tools else "private_storage_body_excluded",
                            "body_opened": False})
                    else:
                        if identity not in mappings and identity in copy_map:
                            pin, raw = retained.read(copy_map[identity]["path"], copy_map[identity])
                            add_mapping(identity, pin, raw, "declared_public_source_dependency")
                        need(identity in mappings, "descriptor has no exact public mapping: " + identity)
                        pin = mappings[identity]["host_pin"]
                        need(pin["bytes"] == length and pin["sha256"] == digest,
                             "public descriptor/body identity differs: " + identity)
                        dependencies.append({"origin": origin, "pointer": pointer, "container_path": identity,
                                             "host_pin": pin, "descriptor": value})
                for key, child in value.items():
                    walk(child, origin, pointer + "/" + key.replace("~", "~0").replace("/", "~1"), depth + 1)
            elif type(value) is list:
                for ordinal, child in enumerate(value):
                    walk(child, origin, pointer + "/" + str(ordinal), depth + 1)

        # All model bodies were explicitly selected above. No store scan or
        # arbitrary descriptor path is opened; aliases require the copied list.
        for identity, mapping in list(mappings.items()):
            if mapping["group"] != "model":
                continue
            if identity.endswith(".json"):
                walk(strict_json(raw_by_container[identity]), identity)
            elif identity.endswith(".jsonl"):
                for ordinal, line in enumerate(raw_by_container[identity].splitlines()):
                    if line:
                        walk(strict_json(line), identity + ":line:" + str(ordinal))

        retained.recheck()
        result = {"schema": "terminal-admitted-context-public-artifacts@1", "qualified": True,
            "producer": producer_pin, "config": config_pin, "selected_reports": report_pins,
            "selected_execution_freeze_joins": execution_freezes,
            "explicit_named_file_count": len(public_files), "public_group_counts": group_counts,
            "files": public_files, "container_host_mappings": list(mappings.values()),
            "model_public_pattern": pattern_pin, "model_public_declared_closure_matched": True,
            "deployed_nine_producer_joins": producer_joins, "public_descriptor_occurrence_count": len(dependencies),
            "public_descriptor_occurrences": dependencies, "metadata_only_descriptors": metadata_only,
            "retained_nofollow_regular_singlelink_fd_stat_hash_witnesses_rechecked": True,
            "recursive_traversal": False, "payload_paths_rewritten": False,
            "database_bodies_included": False, "cas_bodies_included": False, "ducklake_parquet_bodies_included": False,
            "native_store_validation_performed_by_inventory": False,
            "root_owned_source_ancestors_attested": False,
            "inventory_domains": {"semantic_python_snapshot": ["callee.py", "caller.py", "dynamic.py"],
                "signed_native_sources": sorted(inventory), "instruction_body_scope": "Exact UTF-8 owner-receipt text joined to signed SHA/length; no invented standalone host file."},
            "scope": "Named exported bytes and exact declared aliases; current owner/proof/worker claims remain in selected native receipts, not conferred by this inventory.",
            "proof_authority": False, "source_origin_proved": False, "full_task_satisfaction": False,
            "global_task_budget_qualified": False, "training_convergence_proved": False, "provider_calls": 0}
        preservation = {"schema": "terminal-admitted-context-final-preservation@1", "qualified": True,
            "producer": producer_pin, "AA_baseline": baseline_pin, "sealed_Z_preservation": prior_pin,
            "AA_baseline_occurrences": 650, "sealed_Z_final_expected_occurrences": len(prior["occurrences"]),
            "checked_occurrences": len(occurrences), "occurrences_deduplicated": False,
            "all_expected_pins_unchanged": True, "occurrences": occurrences,
            "retained_nofollow_regular_singlelink_fd_stat_hash_witnesses_rechecked": True,
            "scope": "All named expected pin occurrences retained separately; present-call FD/stat/hash custody, no historical mode/inode or recursive store claim.",
            "recursive_traversal": False, "database_bodies_included": False, "cas_bodies_included": False,
            "ducklake_parquet_bodies_included": False}
        outputs = [AA / "actual-public-inventory.json", AA / "preservation-final.json"]
        need(not any(path.exists() for path in outputs), "exclusive reports already exist")
        pins = [write_exclusive(outputs[0], result), write_exclusive(outputs[1], preservation)]
        retained.recheck()
        print(json.dumps({"qualified": True, "outputs": pins, "public_files": len(public_files),
                          "preservation_occurrences": len(occurrences)}, sort_keys=True))
    finally:
        retained.close()


if __name__ == "__main__":
    main()
