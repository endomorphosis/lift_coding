"""Select only named public tooling source and closed audit metadata; no upload."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import types

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
SOURCES = [
    "classify_and_prepare_public_archive_07.py", "build_evidence_archive_02.py",
    "run_frozen_publication_phase.py", "publish_qualified_archive_02.py",
    "review_closed_public_archive_01.py", "publish_successor_evidence_01.py",
    "publish_successor_evidence_02.py", "prepare_successor_publication_01.py",
    "prepare_successor_publication_02.py", "prepare_successor_publication_03.py",
    "prepare_successor_publication_04.py", "successor-source-model-package-01/build_package.py",
    "successor-source-model-package-02/build_package.py", "successor-source-model-package-02/review_package.py",
    "successor-source-model-package-03/build_package.py", "successor-source-model-package-03/review_package.py",
    "run_decoder_controls_05.py", "successor-tooling-file-review-01/prepare_tooling_manifest.py",
]
AUDITS = [
    "successor-publisher-source-review-01/review.json", "successor-publisher-source-review-02/review.json",
    "successor-publisher-reader-controls-01/closed.json", "independent-source-review-01/review.json",
    "independent-source-review-02/review.json", "root-physical-review-01/review.json",
    "root-physical-review-controls-02/review.json", "root-physical-review-negative-01/control-result.json",
    "successor-source-model-package-01/closed.json", "successor-source-model-package-02/closed.json",
    "successor-source-model-package-03/closed.json", "successor-source-model-package-02/file-only-review-01.json",
    "successor-source-model-package-03/file-only-review-01.json", "successor-preparer-source-review-04/review.json",
    "decoder-controls-05/closed.json", "classification-source-freeze-01.json",
    "publication-phase-wrapper-freeze-01.json",
]


def read(path):
    assert path.is_absolute() and path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_size <= 2 * 1024 * 1024
        chunks = []
        while block := os.read(fd, 1024 * 1024):
            chunks.append(block)
            assert sum(map(len, chunks)) <= 2 * 1024 * 1024
        fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        assert all(getattr(before, key) == getattr(os.fstat(fd), key) == getattr(path.lstat(), key) for key in fields)
        raw = b"".join(chunks)
        return raw, {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    finally:
        os.close(fd)


def pin(path):
    return read(path)[1]


def save(path, value):
    with path.open("xb") as output:
        output.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
        output.flush()
        os.fsync(output.fileno())


def frozen(path, expected, name):
    raw, binding = read(path)
    assert binding["sha256"] == expected
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    assert pin(path) == binding
    return module, binding


def main():
    start = time.monotonic()
    assert len(SOURCES + AUDITS) <= 40 and len(set(SOURCES + AUDITS)) == len(SOURCES + AUDITS)
    api, helper = frozen(BASE / "build_evidence_archive_02.py",
        "f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036", "tooling_frozen_archive")
    classifier, classifier_pin = frozen(BASE / "classify_and_prepare_public_archive_07.py",
        "dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8", "tooling_frozen_classifier")
    scanner = api.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in api.PATTERNS if name != "private_key_pem"]
    budget = classifier.Budget(seconds=60, decoded_bytes=8 * 1024**2,
                              container_bytes=2 * 1024**2, members=1000, depth=6)
    files = []
    roles = {}
    relative_paths = {}
    scans = []
    exclusions = []
    for relative in SOURCES + AUDITS:
        path = BASE / relative
        raw, binding = read(path)
        if path.suffix == ".py":
            ast.parse(raw)
        else:
            json.loads(raw)
        inspection = classifier.Classifier(scanner, budget, ROOT)
        try:
            with path.open("rb") as stream:
                inspection.inspect(stream)
        except classifier.Refusal as problem:
            exclusions.append({"binding": binding, "reason": "bounded_container_scan_unresolved",
                               "error_type": type(problem).__name__})
            continue
        if inspection.hits:
            exclusions.append({"binding": binding, "reason": "credential_pattern_or_exact_cached_credential_candidate",
                               "hits": [{"pattern": name, "match_sha256": digest} for name, digest in sorted(inspection.hits)]})
            continue
        assert pin(path) == binding
        files.append(binding)
        roles[str(path)] = "tooling_source" if relative in SOURCES else "closed_source_audit_or_frozen_binding"
        relative_paths[str(path)] = relative
        scans.append({"binding": binding, "scan_hits": [], "scan_counts": dict(inspection.counts)})
    assert len(files) <= 40 and sum(row["bytes"] for row in files) <= 8 * 1024**2
    metadata = {"schema": "terminal-successor-publication-tooling-exact-file-manifest@1",
        "status": "closed_local_public_tooling_selection_not_uploaded", "base": str(BASE),
        "files": files, "relative_paths": relative_paths, "roles": roles,
        "file_count": len(files), "bytes": sum(row["bytes"] for row in files),
        "explicit_candidates": len(SOURCES + AUDITS), "exclusions": exclusions,
        "frozen_scanner_helper": helper, "frozen_scanner_classifier": classifier_pin,
        "exact_available_cached_credential_veto": True, "producer": pin(Path(__file__).resolve()),
        "scope": "Named publication tooling Python sources and closed audits only; no logs, raw candidate bodies, private databases or network download caches.",
        "universal_secret_absence_claimed": False, "remote_mutations": 0,
        "native_SQL_model_optimizer_prover_jobs": 0}
    manifest_path = ROOT / "manifest.json"
    save(manifest_path, metadata)
    for binding in files:
        assert pin(Path(binding["path"])) == binding
    # Verify generated public manifest bytes with the same exact-credential veto.
    metadata_scan = classifier.Classifier(scanner, budget, ROOT)
    with manifest_path.open("rb") as stream:
        metadata_scan.inspect(stream)
    assert not metadata_scan.hits
    review = {"schema": "terminal-successor-publication-tooling-file-only-review@1", "status": "passed",
        "manifest": pin(manifest_path), "file_count": len(files), "bytes": metadata["bytes"],
        "files_all_exact_before_after": True, "new_source_ast_syntax_passed": True,
        "audit_JSON_syntax_passed": True, "bounded_scans": scans,
        "manifest_scan_hits": [], "manifest_scan_counts": dict(metadata_scan.counts),
        "candidate_exclusions": exclusions, "frozen_scanner_helper": helper,
        "frozen_scanner_classifier": classifier_pin, "exact_available_cached_credential_veto": True,
        "scan_budget": {"wall_seconds": 60, "decoded_bytes": 8 * 1024**2,
                        "container_bytes": 2 * 1024**2, "members": 1000, "depth": 6,
                        "actual_decoded_bytes": budget.decoded, "actual_members": budget.members},
        "tooling_behaviors_rerun": False, "remote_mutations": 0,
        "native_SQL_model_optimizer_prover_jobs": 0, "old_sources_or_evidence_modified": False,
        "actual_file_only_elapsed_seconds": time.monotonic() - start,
        "scope_limits": ["Exact individually stable selected source files, not atomic all-file capture or universal secret absence.",
                         "Code syntax and credential byte scan only; no new claim that all earlier candidate tooling versions passed source review.",
                         "Earlier rejected source versions and failed local attempts remain labeled in their closed audit receipts."]}
    review_path = ROOT / "review.json"
    save(review_path, review)
    print(json.dumps({"status": review["status"], "manifest": pin(manifest_path), "review": pin(review_path),
                      "file_count": len(files), "bytes": metadata["bytes"], "excluded": len(exclusions)}))


if __name__ == "__main__":
    main()
