"""Freeze only the named new evidence roots; no source writes or remote mutation."""
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import traceback
import types

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[3]
QUALIFICATION = WORKSPACE / "qualification/codebase_ir"
HF = ROOT.parent
SCOPES = [QUALIFICATION / name for name in (
    "selector-semantics-20261004-01", "full-task-source-20261004-01",
    "full-task-source-20261004-02", "full-task-source-20261004-03",
    "global-shape-reference-20261004-01", "source-model-next-stage-20261004-01")]
ACCELERATOR = WORKSPACE / "external/ipfs_accelerate"
SOURCE_FILES = [ACCELERATOR / prefix / (name + ".py")
                for prefix, names in (
                    ("benchmarks/agent_supervisor/container_coding", (
                        "terminal_codebase_selector_semantics",
                        "terminal_codebase_ranker_step_certificate",
                        "terminal_codebase_batching_contract_reference")),
                    ("test/api", (
                        "test_terminal_codebase_selector_semantics",
                        "test_terminal_codebase_ranker_step_certificate",
                        "test_terminal_codebase_batching_contract_reference")))
                for name in names]
EXPECTED_HELPER = "f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036"
EXPECTED_CLASSIFIER = "dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8"
BLOCK = 1024 * 1024
FILE_MAX = 256 * 1024 * 1024
TAR_MAX = 252 * 1024 * 1024
SHARD_MAX = 256 * 1024 * 1024
TOTAL_MAX = 1024 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode() + b"\n"


def write(path, value):
    raw = wire(value)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def signature(s):
    return {k: getattr(s, "st_" + k) for k in
            ("dev", "ino", "mode", "nlink", "uid", "gid", "size", "mtime_ns", "ctime_ns")}


def read_regular(path):
    assert path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_size <= FILE_MAX
        chunks = []
        count = 0
        while block := os.read(fd, BLOCK):
            count += len(block)
            assert count <= FILE_MAX
            chunks.append(block)
        assert signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
        raw = b"".join(chunks)
        assert len(raw) == before.st_size
        return raw, signature(before)
    finally:
        os.close(fd)


def pin(path):
    raw, _ = read_regular(path)
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def inventory():
    files = []
    exclusions = []
    directories = []
    def visit(path):
        info = path.lstat()
        if path.name == "__pycache__":
            exclusions.append({"path": str(path), "kind": "directory_subtree",
                               "reason": "transient_python_bytecode", "stat": signature(info)})
            return
        if stat.S_ISDIR(info.st_mode):
            assert path.resolve(strict=True) == path
            directories.append({"path": str(path), "stat": signature(info)})
            for child in sorted(path.iterdir(), key=lambda p: os.fsencode(p.name)):
                visit(child)
        elif path.name.endswith(".lock"):
            exclusions.append({"path": str(path), "kind": "transient_lock",
                               "reason": "closed_runtime_lock_not_durable_evidence", "stat": signature(info)})
        elif stat.S_ISREG(info.st_mode):
            files.append(path)
        else:
            raise ValueError("unsupported selected source node type; no traversal")
    for scope in SCOPES:
        visit(scope)
    for source in SOURCE_FILES:
        visit(source)
    assert len(files) <= 5000 and len(set(files)) == len(files)
    return sorted(files, key=lambda p: os.fsencode(str(p.relative_to(WORKSPACE)))), exclusions, directories


def load_frozen(path, expected, name):
    raw, _ = read_regular(path)
    assert sha(raw) == expected
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module, {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def collect_old_references(value, found):
    if isinstance(value, dict):
        for item in value.values():
            collect_old_references(item, found)
    elif isinstance(value, list):
        for item in value:
            collect_old_references(item, found)
    elif isinstance(value, str) and value.startswith(str(WORKSPACE / "artifacts/codebase_ir_terminal_bench") + "/"):
        found.add(value)


def check_closed_bindings():
    review = SCOPES[0] / "closed-file-review-01/review.json"
    assert pin(review)["sha256"] == "424175d6bf468948992c501db1005954cae7ad7b60d9afb33ac145adc28dd550"
    checks = [{"kind": "closed_selector_step_review", **pin(review)}]
    for scope in (SCOPES[3], SCOPES[4]):
        seal = scope / "file-seal.json"
        body = json.loads(read_regular(seal)[0])
        for row in body["files"]:
            assert pin(Path(row["path"])) == row
        checks.append({"kind": "closed_file_seal", **pin(seal), "bound_file_count": len(body["files"])})
    return checks


def build():
    started = time.monotonic()
    record = {"schema": "terminal-source-model-package-outer-attempt@1", "status": "started",
              "error": None, "cleanup_errors": [], "remote_mutations": 0,
              "model_optimizer_prover_native_SQL_jobs": 0}
    try:
        builder_pin = pin(Path(__file__).resolve())
        write(ROOT / "started.json", {"argv": [str(Path(__file__).resolve())],
                                      "builder": builder_pin, "scope_roots": [str(p) for p in SCOPES],
                                      "source_files": [str(p) for p in SOURCE_FILES]})
        api, helper_pin = load_frozen(HF / "build_evidence_archive_02.py", EXPECTED_HELPER, "source_model_archive_helper")
        classifier, classifier_pin = load_frozen(HF / "classify_and_prepare_public_archive_07.py", EXPECTED_CLASSIFIER, "source_model_archive_classifier")
        scanner = api.Scanner()
        scanner.patterns = [(name, pattern) for name, pattern in api.PATTERNS if name != "private_key_pem"]
        budget = classifier.Budget(seconds=180, decoded_bytes=TOTAL_MAX,
                                   container_bytes=FILE_MAX, members=10000, depth=6)
        staging = ROOT / "private-staging"
        staging.mkdir(mode=0o700)
        public = ROOT / "package"
        public.mkdir(mode=0o700)
        checks = check_closed_bindings()
        files, exclusions, directories = inventory()
        old_references = set()
        manifest_rows = []
        source_hints = {}
        count = 0
        for index, path in enumerate(files):
            budget.check()
            raw, before = read_regular(path)
            count += len(raw)
            assert count <= TOTAL_MAX
            target = staging / ("file-%06d" % index)
            with target.open("xb") as stream:
                stream.write(raw)
            target.chmod(0o600)
            inspection = classifier.Classifier(scanner, budget, staging)
            with target.open("rb") as stream:
                inspection.inspect(stream)
            if inspection.hits:
                write(ROOT / ("refused-file-%06d.json" % index), {
                    "path": str(path), "file_sha256": sha(raw),
                    "hits": [{"pattern": name, "match_sha256": digest} for name, digest in sorted(inspection.hits)]})
                raise ValueError("credential-pattern candidate prevents package export")
            assert signature(path.lstat()) == before
            arcname = str(path.relative_to(WORKSPACE))
            row = {"path": arcname, "source_path": str(path), "bytes": len(raw),
                   "sha256": sha(raw), "source_stat_before": before,
                   "scan_profile": "frozen-classifier07-bounded-recursive-containers-and-exact-cached-veto",
                   "scan_hits": [], "scan_counts": dict(inspection.counts)}
            manifest_rows.append(row)
            source_hints[arcname] = target
            if path.suffix == ".json":
                body = json.loads(raw)
                collect_old_references(body, old_references)
        zstd = Path("/usr/bin/zstd")
        zstd_pin = pin(zstd)
        shards = []
        group = []
        estimated = 10240
        def close_group():
            if not group:
                return
            number = len(shards)
            tarpath = staging / ("data-%06d.tar" % number)
            archivepath = public / ("data-%06d.tar.zst" % number)
            with tarfile.open(tarpath, "w", format=tarfile.GNU_FORMAT) as archive:
                for row in group:
                    item = tarfile.TarInfo(row["path"])
                    item.size = row["bytes"]
                    item.mode = 0o644
                    item.uid = item.gid = item.mtime = 0
                    item.uname = item.gname = ""
                    with source_hints[row["path"]].open("rb") as stream:
                        archive.addfile(item, stream)
            assert tarpath.stat().st_size <= SHARD_MAX
            with archivepath.open("xb") as output:
                subprocess.run([str(zstd), "-T1", "-3", "--quiet", "--stdout", str(tarpath)],
                               stdout=output, stderr=subprocess.PIPE, check=True, timeout=60)
            binding = pin(archivepath)
            assert binding["bytes"] <= SHARD_MAX and pin(zstd) == zstd_pin
            inspection = classifier.Classifier(scanner, budget, staging)
            with archivepath.open("rb") as stream:
                inspection.inspect(stream)
            assert not inspection.hits
            tar_binding = api.fingerprint(tarpath)
            with archivepath.open("rb") as encoded, tempfile.TemporaryFile(dir=staging) as decoded:
                inspection.zstd(encoded, decoded)
                decoded.seek(0)
                digest = hashlib.sha256()
                decoded_count = 0
                while block := decoded.read(BLOCK):
                    decoded_count += len(block)
                    assert decoded_count <= SHARD_MAX
                    digest.update(block)
                assert decoded_count == tar_binding["bytes"] and digest.hexdigest() == tar_binding["sha256"]
                decoded.seek(0)
                with tarfile.open(fileobj=decoded, mode="r:") as archive:
                    members = archive.getmembers()
                    assert len(members) == len(group)
                    for row, member in zip(group, members):
                        assert member.isfile() and member.name == row["path"] and member.size == row["bytes"]
                        stream = archive.extractfile(member)
                        digest = hashlib.sha256()
                        while block := stream.read(BLOCK):
                            digest.update(block)
                        assert digest.hexdigest() == row["sha256"]
            for row in group:
                row["archive"] = archivepath.name
                row["member"] = row["path"]
            shards.append({**binding, "archive": archivepath.name, "tar_bytes": tarpath.stat().st_size,
                           "tar_sha256": tar_binding["sha256"], "decoded_per_file_readback_verified": True,
                           "members": len(group), "recursive_scan_hits": [], "scan_counts": dict(inspection.counts)})
        for row in manifest_rows:
            # GNU long-name records add <=3KiB for these explicitly bounded paths.
            assert len(os.fsencode(row["path"])) < 1024
            needed = 4096 + ((row["bytes"] + 511) // 512) * 512
            if group and estimated + needed > TAR_MAX:
                close_group()
                group = []
                estimated = 10240
            group.append(row)
            estimated += needed
        close_group()
        after_files, after_exclusions, after_directories = inventory()
        assert files == after_files and exclusions == after_exclusions and directories == after_directories
        for row in manifest_rows:
            assert pin(Path(row["source_path"])) == {"path": row["source_path"], "bytes": row["bytes"], "sha256": row["sha256"]}
            row["source_stat_after"] = signature(Path(row["source_path"]).lstat())
            assert row["source_stat_after"] == row["source_stat_before"]
        assert check_closed_bindings() == checks
        assert pin(Path(helper_pin["path"])) == helper_pin and pin(Path(classifier_pin["path"])) == classifier_pin
        assert pin(Path(builder_pin["path"])) == builder_pin
        scope_counts = [{"root": str(scope), "files": sum(Path(r["source_path"]).is_relative_to(scope) for r in manifest_rows),
                         "bytes": sum(r["bytes"] for r in manifest_rows if Path(r["source_path"]).is_relative_to(scope))}
                        for scope in SCOPES]
        manifest = {"schema": "terminal-source-model-frozen-evidence-package@1",
                    "status": "closed_scanned_local_package_not_uploaded", "files": manifest_rows,
                    "file_count": len(manifest_rows), "original_file_bytes": count, "data_shards": shards,
                    "compressed_bytes": sum(s["bytes"] for s in shards), "scope_counts": scope_counts,
                    "six_source_test_files": [pin(p) for p in SOURCE_FILES], "exclusions": exclusions,
                    "old_sealed_root_references_not_copied": sorted(old_references),
                    "CAP08_full_closure_duplicated": False, "source_pins_before_after_match": True,
                    "closed_review_and_file_seal_checks": checks, "helper": helper_pin,
                    "classifier": classifier_pin, "builder": builder_pin, "zstd_executable": zstd_pin,
                    "scanner_profile": {"patterns": [name for name, _ in scanner.patterns] + ["complete_private_key_pem_or_escaped"],
                                        "exact_available_cached_credential_veto": True, "candidate_digest_values_printed": False,
                                        "seconds": 180, "decoded_bytes": TOTAL_MAX, "container_bytes": FILE_MAX,
                                        "members": 10000, "depth": 6, "overlap_bytes": 65536,
                                        "parser_metadata_read_bytes": 8388608, "scan_hits": []},
                    "deterministic_tar_profile": {"format": "GNU", "uid": 0, "gid": 0, "mtime": 0, "mode": "0644",
                                                  "zstd_args": ["-T1", "-3"], "shard_max_bytes": SHARD_MAX},
                    "scope_limits": ["Only six explicitly named new qualification roots and six source/test files.",
                                     "No symlinks followed, no original hardlinks/chmod/index changes; postwalk stability is not an atomic snapshot.",
                                     "Native database, parquet and .olean leaves are scanned as opaque bytes; this is no new SQL/prover/semantic inspection.",
                                     "Audited bounded decoder covers supported archive formats and declared credential patterns; not universal secret absence.",
                                     "Old CAP08 and sealed roots remain references; no old qualification transfer, training or planning activation."]}
        manifest_pin = write(public / "manifest.json", manifest)
        record.update(status="passed_local_frozen_package", manifest=manifest_pin,
                      files=len(manifest_rows), original_file_bytes=count, shards=len(shards),
                      compressed_bytes=manifest["compressed_bytes"], excluded_nodes=len(exclusions),
                      data_shards=shards, source_drift_count=0, candidate_hits=0,
                      scan_budget_decoded_bytes=budget.decoded, scan_budget_members=budget.members,
                      public_upload_performed=False)
        for path in staging.iterdir():
            path.unlink()
        staging.rmdir()
    except BaseException as error:
        record["status"] = "failed"
        record["error"] = {"type": type(error).__name__, "traceback": traceback.format_exc()}
    finally:
        record["actual_outer_elapsed_seconds"] = time.monotonic() - started
        write(ROOT / "closed.json", record)
    print(json.dumps({"status": record["status"], "closed": pin(ROOT / "closed.json"),
                      "elapsed_seconds": record["actual_outer_elapsed_seconds"], "manifest": record.get("manifest")}))
    return 0 if record["status"] == "passed_local_frozen_package" else 1


if __name__ == "__main__":
    raise SystemExit(build())
