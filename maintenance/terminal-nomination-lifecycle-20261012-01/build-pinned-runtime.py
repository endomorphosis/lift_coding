"""Build this stage's provider-free runtime; no model weights or Lean toolchain."""
import hashlib
import argparse
import json
from pathlib import Path
import tarfile
import time

from benchmarks.agent_supervisor.container_coding.terminal_deployment import build_runtime_archive

STAGE = Path(__file__).resolve().parent
BASE = STAGE.parent
CHECKOUT = BASE / "terminal-token-reduction-20261007-01/checkout"
PRIOR = BASE / "terminal-compact-retrieval-20261011-01"
ASSETS = BASE / "terminal-frontier-runtime-20261011-01"
SOURCE_ROOTS = {"source": CHECKOUT, "datasets": PRIOR / "pinned-dependencies-v10/datasets",
    "kit": PRIOR / "pinned-dependencies-v10/kit"}
started = time.monotonic()
parser=argparse.ArgumentParser()
parser.add_argument('--archive-name',default='runtime-archive')
args=parser.parse_args()
assert args.archive_name in {'runtime-archive','runtime-archive-final-02'}
archive_dir=STAGE/args.archive_name
manifest = build_runtime_archive(output=archive_dir, source=CHECKOUT,
    datasets=SOURCE_ROOTS["datasets"], kit=SOURCE_ROOTS["kit"],
    extension_dir=ASSETS / "pinned-assets-v8/extensions",
    codex_native_dir=ASSETS / "native-codex-arm64-bin-02")
records = {row["path"]: row for row in manifest["files"]}
assert len(records) == len(manifest["files"])
seen = set()
with tarfile.open(archive_dir / "runtime.tar.gz", "r:gz") as archive:
    for member in archive:
        assert member.name not in seen and member.name in records and member.isfile()
        seen.add(member.name)
        expected = records[member.name]
        assert (member.size, member.mode, member.uid, member.gid) == (expected["bytes"], expected["mode"], 0, 0)
        with archive.extractfile(member) as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == expected["sha256"]
        prefix, relative = member.name.split("/", 1) if "/" in member.name else (None, None)
        if prefix in SOURCE_ROOTS:
            path = SOURCE_ROOTS[prefix] / relative
            assert path.is_file() and not path.is_symlink() and path.stat().st_size == expected["bytes"]
            with path.open("rb") as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == expected["sha256"]
assert seen == set(records)
assert not manifest["credentials_in_archive"] and not manifest["task_inputs_in_archive"]
receipt = {"schema": "nomination-lifecycle-runtime-archive-verification@1",
    "archive_sha256": manifest["archive_sha256"], "files_verified": len(seen),
    "all_members_match_declared_bytes_modes_and_digests": True,
    "all_packaged_source_matches_checkout_after_build": True,
    "runtime_python_version": manifest["runtime_python_version"],
    "base_requirements": manifest["base_requirements"],
    "credentials_in_archive": False, "task_inputs_in_archive": False,
    "lean_toolchain_selected_or_executed": False, "model_weights_selected": False,
    "provider_calls": 0, "training_steps": 0, "prover_invocations": 0,
    "elapsed_seconds": time.monotonic() - started}
verification=STAGE/(args.archive_name+'-verification.json')
assert not verification.exists()
verification.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
print(json.dumps(receipt), flush=True)
