"""Archive completed experiment evidence with bounded streaming and byte bindings.

Model checkpoint bodies and prepared embedding inventories remain in their
owned local attempts. This archive preserves their references, all generated
formula outputs/readout traces, failed attempts, and experiment sources.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import tarfile

R = Path(__file__).resolve().parent
W = R.parents[1]
RUN = W / "external/ipfs_datasets/workspace/test-logs/decoder-balanced-wording-20261007"
SUFFIXES = {".py", ".json", ".jsonl", ".xml", ".diff", ".md", ".log", ".txt"}
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", "assembled-inputs-r1"}
EXCLUDED_NAMES = {
    "production-384.json", "control-bank.json", "balanced-bank.json",
    "root-progress-state.json", "retention-manifest.json",
    "publication-scope.json", "datasets-publication.json", "workspace-publication.json",
}
MAX_SOURCE_BYTES = 300_000_000
MAX_ARCHIVE_BYTES = 90_000_000


def identity(value):
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def file_record(path):
    before = identity(path.stat())
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        if identity(os.fstat(stream.fileno())) != before:
            raise ValueError("replaced evidence: " + str(path))
        for block in iter(lambda: stream.read(1_048_576), b""):
            count += len(block)
            digest.update(block)
        if identity(os.fstat(stream.fileno())) != before:
            raise ValueError("opened evidence changed: " + str(path))
    if identity(path.stat()) != before or count != before[2]:
        raise ValueError("evidence changed: " + str(path))
    return {"bytes": count, "sha256": digest.hexdigest()}


class HashedReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.bytes = 0

    def read(self, size):
        block = self.stream.read(size)
        self.digest.update(block)
        self.bytes += len(block)
        return block


def main():
    for phase in ("preparation-r2", "preflight-384-r2", "training-384-r2", "evaluation-r1"):
        terminal = json.loads((RUN / (phase + "-guardian-exit.json")).read_bytes())
        resource = json.loads((RUN / phase / "resources-final.json").read_bytes())
        if terminal["returncode"] != 0 or resource["status"] != "released":
            raise ValueError("completed owned phase required: " + phase)
    output = R / "balanced-wording-evidence.tar.gz"
    manifest_path = R / "retention-manifest.json"
    if output.exists() or manifest_path.exists():
        raise ValueError("retained evidence is immutable")
    candidates = []
    exclusions = []
    for root in (R, RUN):
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in SUFFIXES:
                continue
            checkpoint_body = root == RUN and path.name in {
                "initial-state.json", "selected-state.json", "last-attempt-state.json",
            }
            if EXCLUDED_PARTS.intersection(path.parts) or path.name in EXCLUDED_NAMES or checkpoint_body:
                exclusions.append(str(path.relative_to(W)))
                continue
            # Publication is a later separately reviewed operation, not a model phase.
            if "pipeline" in path.relative_to(root).parts or path.name in {
                "publish_integration.py", "publisher_review_tests.py", "prepare_publication.py",
            }:
                continue
            candidates.append(path)
    entries = []
    total = 0
    with output.open("xb") as raw_archive:
        with gzip.GzipFile(fileobj=raw_archive, mode="wb", filename="", mtime=0, compresslevel=6) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                for path in sorted(candidates):
                    if path.resolve() != path or any(parent.is_symlink() for parent in path.parents):
                        raise ValueError("symbolic evidence refused: " + str(path))
                    expected = file_record(path)
                    total += expected["bytes"]
                    if total > MAX_SOURCE_BYTES:
                        raise ValueError("bounded archive source bytes exceeded")
                    before = identity(path.stat())
                    info = tarfile.TarInfo(path.relative_to(W).as_posix())
                    info.size = expected["bytes"]
                    info.mode = 0o644
                    info.mtime = 0
                    with path.open("rb") as stream:
                        if identity(os.fstat(stream.fileno())) != before:
                            raise ValueError("archive input replaced")
                        reader = HashedReader(stream)
                        archive.addfile(info, reader)
                        if identity(os.fstat(stream.fileno())) != before:
                            raise ValueError("archive input changed")
                    if identity(path.stat()) != before or {
                        "bytes": reader.bytes, "sha256": reader.digest.hexdigest(),
                    } != expected:
                        raise ValueError("archived bytes differ")
                    entries.append({"path": info.name, **expected})
    retained = file_record(output)
    if retained["bytes"] > MAX_ARCHIVE_BYTES:
        raise ValueError("bounded compressed archive exceeded")
    manifest = {
        "schema": "balanced-wording-evidence-retention/v1", "passed": True, "findings": [],
        "archive": {"path": output.relative_to(W).as_posix(), **retained},
        "entries": entries, "source_bytes": total, "excluded_local_bodies": sorted(exclusions),
        "checkpoint_bodies_archived": False, "prepared_embedding_bodies_archived": False,
        "embedding_exclusion_scope": "raw producer output and prepared source/bank inventories",
        "retained_vector_observations": "inherited reconstructed_input outputs and normalized training feature observations",
        "model_execution_performed": False, "qualification_granted": False,
    }
    with manifest_path.open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"entries": len(entries), "source_bytes": total, "archive_bytes": retained["bytes"]}))


if __name__ == "__main__":
    main()
