#!/usr/bin/env python3
"""Retain exact historical source/doc Git blobs; no capsule code is executed."""
import argparse
import ast
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile

SOURCE_CATEGORIES = {"additional_decoder_model_card", "additional_decoder_release_documentation", "historical_source_capsule"}
REFERENCE_CATEGORIES = {"additional_decoder_checkpoint_json", "alignment_checkpoint_or_control_json"}
MAX_BYTES = 10000000
FALSE = dict(qualified=False, admitted=False, proof_authority=False, source_semantics_verified=False,
    training_admission=False, execution_readiness=False, checkpoint_promoted=False, formalized=False,
    model_or_encoder_imported=False, model_or_encoder_executed=False, capsule_code_executed=False,
    canonical_code_restored=False, current_runtime_compatibility_reviewed=False)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def git(repo, *argv):
    result = subprocess.run(["git", "-C", str(repo), *argv], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return result.stdout


def normal_state(repo):
    index = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "index").decode().strip())
    return dict(head=git(repo, "rev-parse", "HEAD").decode().strip(), index_path=str(index),
        index_sha256=sha(index), index_bytes=index.stat().st_size)


def safe_path(path):
    value = PurePosixPath(path)
    require(type(path) is str and path and not value.is_absolute() and str(value) == path
        and ".." not in value.parts and "\\" not in path and "\x00" not in path,
        "normalized repository-relative historical path required")
    return path


def tree_binding(repo, commit, path, blob, mode):
    require(re.fullmatch(r"[0-9a-f]{40}", commit) and re.fullmatch(r"[0-9a-f]{40}", blob)
        and mode in ("100644", "100755"), "exact local regular Git commit/blob/mode required")
    raw = git(repo, "ls-tree", "-z", commit, "--", ":(literal)" + safe_path(path))
    expected = (mode + " blob " + blob + "\t" + path).encode() + b"\0"
    require(raw == expected, "historical retained-tip tree binding differs: " + path)


def stream_blob(repo, entry):
    blob = entry["blob_oid"]
    require(git(repo, "cat-file", "-t", blob).strip() == b"blob"
        and int(git(repo, "cat-file", "-s", blob)) == entry["bytes"]
        and 0 <= entry["bytes"] <= MAX_BYTES, "bounded expected local Git blob required")
    proc = subprocess.Popen(["git", "-C", str(repo), "cat-file", "blob", blob],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    chunks = []; count = 0; h = hashlib.sha256()
    object_hash = hashlib.sha1(("blob " + str(entry["bytes"]) + "\0").encode())
    try:
        while True:
            block = proc.stdout.read(65536)
            if not block:
                break
            count += len(block)
            require(count <= entry["bytes"] and count <= MAX_BYTES, "Git blob byte bound exceeded")
            h.update(block); object_hash.update(block); chunks.append(block)
        error = proc.stderr.read()
        require(proc.wait() == 0, "local Git blob extraction failed: " + error.decode(errors="replace")[:128])
    finally:
        proc.stdout.close(); proc.stderr.close()
        if proc.poll() is None:
            proc.kill(); proc.wait()
    require(count == entry["bytes"] and h.hexdigest() == entry["sha256"]
        and object_hash.hexdigest() == blob, "exact Git object/body SHA/byte authentication failed")
    return b"".join(chunks)


def inspect_body(entry, body):
    """Static source/doc inspection only; never import/eval/execute a capsule."""
    text = body.decode("utf-8")
    require("\x00" not in text, "binary/non-text body cannot be archived as a source capsule")
    findings = []
    if entry["category"] == "historical_source_capsule":
        require(entry["path"].endswith(".py") and PurePosixPath(entry["path"]).name[:64] == entry["sha256"],
            "source capsule filename/content SHA differs")
        tree = ast.parse(text, filename=entry["path"])
        for node in ast.walk(tree):
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                numeric = [n for n in node.elts if isinstance(n, ast.Constant) and type(n.value) in (int, float)]
                if len(numeric) >= 32:
                    findings.append("line " + str(node.lineno) + ": dense literal container with " + str(len(numeric)) +
                        " numeric values; potential embedded tensor/weight body requires exclusion and owner review")
            if isinstance(node, ast.Constant) and ((type(node.value) is bytes and len(node.value) >= 256)
                or (type(node.value) is str and len(node.value) >= 32768)):
                findings.append("line " + str(node.lineno) + ": embedded literal payload " + str(len(node.value)) +
                    " bytes/characters; unresolved serialized payload excluded from source-only retention")
    else:
        require(entry["path"].endswith(".md"), "only declared Markdown cards/docs are source retention candidates")
        for match in re.finditer(r"(?:model_state|state_dict|model_weights|tensor_data)\s*[\"']?\s*:\s*[\[{]", text):
            block = text[match.start():match.start() + 16384]
            if len(re.findall(r"-?\d+\.\d+(?:[eE][+-]?\d+)?", block)) >= 32:
                findings.append("Markdown serialized model/tensor field with dense numeric payload; excluded")
    return dict(method="UTF-8 and source AST/data-literal inspection; no code execution or semantic recertification",
        detected_serialized_tensor_or_unresolved_payload=bool(findings), findings=findings,
        semantic_provenance_reviewed=False, runtime_compatibility_reviewed=False)


def save_new(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    with Path(path).open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return dict(path=str(Path(path).resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def extract(repo, intake_path, output):
    repo, intake_path, output = map(lambda p: Path(p).resolve(), (repo, intake_path, output))
    intake_sha = sha(intake_path); intake = json.loads(intake_path.read_bytes())
    require(intake["schema"] == "historical-autoencoder-path-intake/v1" and intake["complete"] is True
        and intake["passed"] is True and intake["no_same_loose_blob_on_either_current_main"] == 73,
        "exact completed historical intake required")
    absent = [e for e in intake["entries"] if not e["same_blob_elsewhere_on_current_main"]]
    selected = sorted((e for e in absent if e["category"] in SOURCE_CATEGORIES), key=lambda e: e["path"])
    references = sorted((e for e in absent if e["category"] in REFERENCE_CATEGORIES), key=lambda e: e["path"])
    require(len(selected) == 22 and len(references) == 51 and len(absent) == 73
        and len({e["path"] for e in selected}) == 22, "exact22 noncheckpoint and51 reference-only intake entries required")
    require(sum(e["bytes"] for e in selected) <= MAX_BYTES, "uncompressed candidate source evidence exceeds10MB")
    before = normal_state(repo); retained, excluded, bodies = [], [], []
    for entry in selected:
        path = safe_path(entry["path"])
        for tip in entry["retained_tip_postimages"]:
            require(tip["path"] == path and tip["blob_oid"] == entry["blob_oid"], "retained tip declaration changed")
            tree_binding(repo, tip["commit"], path, entry["blob_oid"], entry["mode"])
        body = stream_blob(repo, entry); inspection = inspect_body(entry, body)
        common = dict(original_path=path, mode=entry["mode"], blob_oid=entry["blob_oid"],
            sha256=entry["sha256"], bytes=entry["bytes"], category=entry["category"],
            retained_tip_postimages=entry["retained_tip_postimages"],
            representative_retained_commit=entry["retained_tip_postimages"][0]["commit"],
            first_creation_commit_claimed=False, github_reachability_claimed=False,
            archived_evidence_only=True, unreviewed_historical_body=True, static_inspection=inspection, **FALSE)
        if inspection["findings"]:
            excluded.append(dict(common, excluded=True, exact_reasons=inspection["findings"]))
        else:
            retained.append(dict(common, archive_member=path)); bodies.append((entry, body))
    require(normal_state(repo) == before and sha(intake_path) == intake_sha, "normal HEAD/index or frozen intake changed")
    require(not (output / "historical-source-evidence.tar.gz").exists()
        and not (output / "manifest.json").exists(), "fresh historical archive/manifest required")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "historical-source-evidence.tar.gz"
    with archive.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as zipped:
            with tarfile.open(fileobj=zipped, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                for entry, body in bodies:
                    info = tarfile.TarInfo(entry["path"]); info.size = len(body)
                    info.mode = int(entry["mode"], 8) & 0o777; info.mtime = 0
                    info.uid = info.gid = 0; info.uname = info.gname = ""
                    tar.addfile(info, io.BytesIO(body))
        raw.flush(); os.fsync(raw.fileno())
    require(archive.stat().st_size <= MAX_BYTES, "compressed historical source archive exceeds10MB")
    refs = [dict(original_path=e["path"], mode=e["mode"], blob_oid=e["blob_oid"], sha256=e["sha256"],
        bytes=e["bytes"], category=e["category"], retained_tip_postimages=e["retained_tip_postimages"],
        representative_retained_commit=e["retained_tip_postimages"][0]["commit"],
        body_read_or_extracted=False, body_archived=False, archived_as_reference_only=True,
        first_creation_commit_claimed=False, github_reachability_claimed=False, **FALSE) for e in references]
    after = normal_state(repo); require(after == before and sha(intake_path) == intake_sha,
        "normal HEAD/index or frozen intake changed during archive creation")
    manifest = dict(schema="historical-autoencoder-source-evidence-retention/v1", complete=True,
        historical_git_repository=str(repo), intake=dict(path=str(intake_path), sha256=intake_sha, bytes=intake_path.stat().st_size),
        source_candidates=22, retained_source_members=len(retained), excluded_source_members=len(excluded),
        checkpoint_control_reference_count=51, source_member_bytes=sum(e["bytes"] for e in retained),
        archive=dict(path=str(archive), sha256=sha(archive), bytes=archive.stat().st_size),
        members=retained, exclusions=excluded, checkpoint_control_references=refs,
        current_main_pins_at_intake=intake["current_main_pins"],
        normal_git_before=before, normal_git_after=after, normal_HEAD_index_unchanged=True,
        deterministic_format="sorted original paths; PAX regular members; zero uid/gid/mtime; gzip mtime0 filename empty",
        existing_frozen_publication_files_modified=False, existing_main_archive_modified=False,
        all_historical_progress_merged_claim=False, checkpoints_retained_as_bodies=False,
        no_model_port_or_restoration=True, semantic_review_pending=True, independent_archive_review_pending=True,
        extracted_capsules_never_imported_or_executed=True, archived_evidence_only=True, **FALSE)
    manifest_ref = save_new(output / "manifest.json", manifest)
    return dict(manifest=manifest_ref, archive=manifest["archive"], retained=len(retained), excluded=len(excluded),
        checkpoint_control_references=51, uncompressed_bytes=manifest["source_member_bytes"], **FALSE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "intake", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(extract(args.repo, args.intake, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
