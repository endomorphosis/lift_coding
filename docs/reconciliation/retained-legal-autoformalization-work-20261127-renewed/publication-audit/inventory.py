from pathlib import Path
import hashlib
import json
import os
import re
import stat
from support import WORK, PREVIOUS, CONTROLS, git, save, tree

LAST_PUBLISHED = WORK / "base.json"
HEADS = json.loads(LAST_PUBLISHED.read_bytes())["remote_main"]
PREFIX = "docs/reconciliation/retained-legal-autoformalization-work-20261127-renewed/"
MAIN = Path("/tmp/Main-board-stall-evidence-refresh-private-v01")
PATHS = {
    CONTROLS: "coordination",
    MAIN / "owner-wait-consumer-integration-private-v01": "Main-owner-controls",
    Path("/tmp/P1-Lean-current580-diagnostics-guarded-private-jnBwI2TZ"): "Lean-diagnostic-probes",
    Path("/tmp/P1-proof-cache-translation-current-6btZZr/lean-json-diagnostics"): "Root-Lean-qualification",
    Path("/tmp/Main-existing-invoke-once-unloaded-hydration-private-v01"): "Main-caller-controls",
    Path("/tmp/legal-refusal-recovery-j_10md5l"): "agent-turn-recovery",
}
EXTRA = {}
r = Path("/tmp/legal-refusal-recovery-j_10md5l/repo")
for rel in ("ipfs_datasets_py/logic/autoformal/supervisor_loop.py", "scripts/ops/legal_ir/run_autoformal_supervisor.py", "tests/unit/logic/test_supervisor_agent_turn_recovery.py"):
    EXTRA[r / rel] = "agent-turn-recovery/authored/" + str(Path(rel).parent)
SKIP = {"project", "checkout", "dataset", "datasets", "normal-checkout", "models",
        "assets", "workspace", "site-packages", "__pycache__", ".git", "tmp", ".venv", "repo", "inputs", "rawcache", "repositories", ".pytest_cache"}
EXT = {".data", ".diff", ".fragment", ".json", ".md", ".patch", ".py", ".selectors", ".sh", ".xml"}
EXCLUDED_NAME = re.compile(r"(?:^|[.-])(?:index|passwd|credential|transcript|secret|token)(?:[.-]|$)"
                           r"|^(?:actual-live-reconciled|Root-selected|std(?:out|err)(?:\.|$))", re.I)
SENSITIVE = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{30,}|"
                       rb"github_pat_[A-Za-z0-9_]{35,}|AKIA[A-Z0-9]{16}|sk-(?:proj-)?[A-Za-z0-9_-]{30,})\b"
                       rb"|https?://[^\s/@:]+:[^\s/@]+@", re.I)

def read_exact(path, limit=4 * 1024 * 1024):
    if path.resolve(strict=True) != path:
        raise ValueError("symlink")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as f:
        before = os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid != os.getuid():
            raise ValueError("outside_owned_regular_file_scope")
        if before.st_size > limit:
            raise ValueError("oversize_for_text_inventory")
        raw = f.read(limit + 1)
        after = os.fstat(f.fileno())
    attrs = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid", "st_size",
             "st_mtime_ns", "st_ctime_ns")
    if len(raw) != before.st_size or any(getattr(before, key) != getattr(after, key) for key in attrs):
        raise ValueError("unstable")
    return raw, before

def blob(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()

def selections():
    for folder, section in sorted(PATHS.items()):
        assert folder.is_dir() and not folder.is_symlink(), folder
        for directory, children, files in os.walk(folder, followlinks=False):
            directory = Path(directory)
            relative = directory.relative_to(folder)
            children[:] = [c for c in children if c not in SKIP and len(relative.parts) < 7
                           and not ((directory / c) / ".git").exists()]
            for name in sorted(files):
                path = directory / name
                if path.suffix.lower() in EXT and not EXCLUDED_NAME.search(name):
                    yield path, (Path(section) / relative / (name + ".DATA")).as_posix()
    for path, section in EXTRA.items():
        assert path.is_file(), path
        yield path, section + "/" + path.name + ".DATA"

def inventory():
    trees = {repo: tree(repo, head) for repo, head in HEADS.items()}
    published_blobs = {}
    for repo, entries in trees.items():
        for name, (mode, oid) in entries.items():
            if mode in {"100644", "100755"}:
                published_blobs.setdefault(oid, (repo, name))
    older = {}
    output = WORK / "retained"
    output.mkdir(mode=0o700)
    sources, excluded, unique = {}, {}, {}
    for path, relative in selections():
        if str(path) in sources:
            continue
        try:
            raw, status = read_exact(path)
            if not raw:
                continue
            raw.decode("utf-8")
            if b"\0" in raw or SENSITIVE.search(raw):
                raise ValueError("binary_or_sensitive_marker")
        except (OSError, ValueError) as error:
            excluded[str(path)] = f"{type(error).__name__}:{error}"[:220]
            continue
        sha = hashlib.sha256(raw).hexdigest()
        oid = blob(raw)
        row = {"sha256": sha, "bytes": len(raw), "git_blob": oid,
               "original_mode": oct(stat.S_IMODE(status.st_mode))}
        if sha in older:
            archive, size = older[sha]
            assert (len(raw), oid) == (size, trees["root"][archive][1]), path
            row["published"] = {"repo": "root", "path": archive}
        elif oid in published_blobs:
            repo, name = published_blobs[oid]
            row["published"] = {"repo": repo, "path": name}
        elif sha in unique:
            row["archive"] = unique[sha]
        else:
            unique[sha] = row["archive"] = relative
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
            target.chmod(0o400)
        sources[str(path)] = row
    main_packets = {}
    pins = {r["archive"]: (r["bytes"], r["sha256"]) for r in sources.values() if "archive" in r}
    assert len(pins) == len(unique)
    report = {"schema": "legal-autoformalization-retained-work-followup/v1",
              "verified_base_heads": HEADS,
              "source_roots": {str(p): label for p, label in PATHS.items()},
              "sources": sources, "exceptions": excluded,
              "prior_Main_packet_readbacks": main_packets,
              "new_payload_count": len(pins),
              "new_payload_bytes": sum(size for size, _ in pins.values()),
              "prior_publication": str(LAST_PUBLISHED),
              "archived_candidates_adopted": False}
    save("private-inventory.json", report)
    print(json.dumps({"folders": len(PATHS), "checked": len(sources), "new": len(pins),
                      "bytes": report["new_payload_bytes"], "exceptions": excluded}, indent=2))

if __name__ == "__main__":
    inventory()
