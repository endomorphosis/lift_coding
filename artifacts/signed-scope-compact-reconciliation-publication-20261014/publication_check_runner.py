"""Check publication custody and explicit parent links; never run product tests."""
from __future__ import annotations
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PHASE = Path(__file__).resolve().parent
ACCEL = Path("/home/barberb/lift_coding/.worktrees/signed-scope-compact-reconciliation-20261014")
DATASETS = Path("/home/barberb/lift_coding/.worktrees/terminal-worker-scope-datasets-20261013")
KIT = Path("/home/barberb/lift_coding/.worktrees/publication-main-20261004/kit")
BASE = "9fd25a0d77465782cbe53e50e81674c2d0c01efa"
LEAF = "2ceac1afc3d66b54204656ee8d7f758780231ff1"
PUBLICATION = "2ceac1afc3d66b54204656ee8d7f758780231ff1"
DATASETS_REVISION = "59561dd2979e49fd26aa3fcfed6a5edbca1f718f"
DATASETS_PIN = "d8f9e3dfc77901162e3d32343860aa4678374db0"
KIT_REVISION = "8ac00bb1974b1378e12091d546d8425af34049e0"
CHILD_PHASE = "docs/agent_supervisor/evidence/signed-scope-compact-reconciliation-20261014/"
NOTE = ROOT / "implementation_plan/docs/119-supervisor-signed-compact-reconciliation-2026-10-14.md"
RECEIPT = PHASE / "parent-checks.json"
MANIFEST = PHASE / "manifest.json"


def need(value, message):
    if not value:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def main():
    need(not RECEIPT.exists() and not MANIFEST.exists(), "refusing to overwrite publication checks")
    need(git(ROOT, "rev-parse", "HEAD").decode().strip() == BASE, "parent base changed")
    need(not git(ROOT, "diff", "--cached", "--name-only"), "unexpected staged parent changes")
    remotes = []
    for root, expected in ((ACCEL, PUBLICATION), (DATASETS, DATASETS_REVISION), (KIT, KIT_REVISION)):
        remote = git(root, "ls-remote", "origin", "refs/heads/main").decode().split()
        need(len(remote) == 2 and remote[1] == "refs/heads/main", "unambiguous main ref required")
        subprocess.run(["git", "fetch", "--quiet", "origin", "main"], cwd=root, check=True)
        subprocess.run(["git", "merge-base", "--is-ancestor", expected, remote[0]], cwd=root, check=True)
        need(git(root, "rev-parse", "HEAD").decode().strip() == expected, "execution/publication checkout moved")
        need(not git(root, "status", "--porcelain"), "owned checkout is dirty")
        remotes.append(dict(path=str(root), head=expected, observed_origin_main=remote[0], published_ancestor=True))
    subprocess.run(["git", "merge-base", "--is-ancestor", DATASETS_PIN, git(DATASETS, "rev-parse", "origin/main").decode().strip()], cwd=DATASETS, check=True)
    manifest_raw = git(ACCEL, "show", LEAF + ":" + CHILD_PHASE + "manifest.json")
    child_manifest = json.loads(manifest_raw)
    owned = []
    for row in child_manifest["files"]:
        raw = git(ACCEL, "show", LEAF + ":" + row["path"])
        need(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "qualified file binding changed")
        need(raw == git(ACCEL, "show", PUBLICATION + ":" + row["path"]), "qualified file changed at publication")
        owned.append(row)
    need(manifest_raw == git(ACCEL, "show", PUBLICATION + ":" + CHILD_PHASE + "manifest.json"), "child manifest changed")
    q = json.loads(git(ACCEL, "show", LEAF + ":" + CHILD_PHASE + "qualification-03/commands.json"))
    docs = json.loads(git(ACCEL, "show", LEAF + ":" + CHILD_PHASE + "documentation-checks.json"))
    need(q["status"] == docs["status"] == "pass", "retained qualification or documentation failed")
    need(q["before"] == q["after"] and len(q["before"]) == 254, "qualification custody changed")
    for row in q["before"]:
        root = ACCEL if row["repository"] == "accelerator" else DATASETS
        rev = LEAF if root == ACCEL else DATASETS_REVISION
        raw = git(root, "show", rev + ":" + row["path"])
        need(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "execution revision source differs")
    xml = ET.fromstring(git(ACCEL, "show", LEAF + ":" + CHILD_PHASE + "qualification-03/junit.xml"))
    cases = [(c.get("classname"), c.get("name")) for c in xml.iter("testcase")]
    need(len(cases) == len(set(cases)) == q["distinct_junit_cases"] == 1722, "distinct test identities differ")
    need(q["junit"] == dict(tests=1722, failures=0, errors=0, skipped=0), "JUnit outcome differs")
    need(len(docs["steps"]) == 4 and all(r["exit_code"] == 0 for r in docs["steps"]), "local gates differ")
    need(docs["relative_links"] > 0, "link checks missing")
    merge = json.loads((PHASE / "merge-compatibility.json").read_bytes())
    ci = json.loads((PHASE / "hosted-ci.json").read_bytes())
    need(merge["publication_revision"] == ci["head_sha"] == PUBLICATION, "publication receipt revision differs")
    need(merge["qualified_files_preserved"] == len(child_manifest["files"])+1 and merge["incoming_files_preserved"] == len(merge["incoming_file_bindings"]), "merge custody counts differ")
    need(ci["billing_lock_observed"] is True and ci["hosted_steps_executed"] is False, "hosted CI observation differs")
    checker_path = ACCEL / "scripts/docs/check_current_docs_links.py"
    checker_raw = checker_path.read_bytes()
    need(sha(checker_raw) == "596a0038b18d592f2e605643890afc85e457558f7b887932a474557d7586819e", "checker changed")
    spec = importlib.util.spec_from_file_location("publication_link_checker", checker_path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    checker.ROOT = ROOT
    before = [binding(p) for p in (NOTE, PHASE / "hosted-ci.json", PHASE / "merge-compatibility.json", Path(__file__))]
    subprocess.run(["git", "update-index", "--cacheinfo", "160000," + PUBLICATION + ",external/ipfs_accelerate"], cwd=ROOT, check=True)
    subprocess.run(["git", "update-index", "--skip-worktree", "external/ipfs_accelerate"], cwd=ROOT, check=True)
    expected_pins = dict(zip(("external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit"),
        (PUBLICATION, DATASETS_PIN, KIT_REVISION)))
    index_rows = git(ROOT, "ls-files", "--stage", *expected_pins).decode().splitlines()
    need(len(index_rows) == 3, "missing dependency pin")
    for line in index_rows:
        metadata, path = line.split("\t")
        need(metadata == "160000 " + expected_pins[path] + " 0", "dependency pin differs")
    # Create the relative-link target exactly once, then write the observed checks.
    with RECEIPT.open("x", encoding="utf-8") as handle:
        errors = checker.check_file(NOTE, check_anchors=True)
        need(not errors, "parent report links failed: " + repr(errors))
        links = [checker.split_target(m.group("target")) for m in checker.LINK_RE.finditer(checker.strip_markup_noise(NOTE.read_text()))]
        relative = [(p, f) for p, f in links if not checker.is_external(p, f)]
        github_objects = []
        prefix = "https://github.com/endomorphosis/ipfs_accelerate_py/blob/" + PUBLICATION + "/"
        for target, fragment in links:
            if not target.startswith(prefix):
                continue
            path = urllib.parse.unquote(target[len(prefix):])
            raw = git(ACCEL, "show", PUBLICATION + ":" + path)
            if fragment:
                # This repository's checker reads the identical published file.
                need((ACCEL / path).read_bytes() == raw, "anchor source differs from published object")
                need(fragment in checker.collect_markdown_anchors(ACCEL / path), "missing published anchor")
            github_objects.append(dict(path=path, bytes=len(raw), sha256=sha(raw), fragment=fragment, status="pass"))
        need(len(github_objects) == 4, "expected four exact child object links")
        after = [binding(p) for p in (NOTE, PHASE / "hosted-ci.json", PHASE / "merge-compatibility.json", Path(__file__))]
        need(before == after, "read guards changed during publication checks")
        receipt = dict(schema="signed-compact-parent-checks@1", checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            parent_base=BASE, qualified_leaf=LEAF, accelerator_publication=PUBLICATION,
            dependencies=remotes, staged_gitlinks=index_rows, relative_links_passed=True,
            relative_link_count=len(relative), relative_anchor_count=sum(bool(f) for _, f in relative),
            published_child_objects=github_objects, checker=dict(path=str(checker_path), sha256=sha(checker_raw), api="check_file(path, check_anchors=True)", root_override=str(ROOT)),
            retained_tests=1722, retained_new_cases=159, retained_suites=47, retained_source_bindings=254,
            qualified_source_git_objects_match=True, qualified_child_paths_unchanged=len(child_manifest["files"])+1,
            local_doc_gates_on_qualified_leaf=4, local_doc_relative_links=docs["relative_links"], local_doc_anchors=docs["anchors"],
            tests_or_workflow_rerun=False, hosted_steps_executed=False, billing_lock_observed=True,
            read_guards_before=before, read_guards_after=after, read_guards_unchanged=True,
            status="pass", model_provider_solver_docker_calls=0, total_session_token_savings_established=False)
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    files = [NOTE, PHASE / "hosted-ci.json", PHASE / "merge-compatibility.json", Path(__file__), RECEIPT]
    manifest = dict(schema="signed-compact-parent-manifest@1", parent_base=BASE,
        accelerator_publication=PUBLICATION, qualified_leaf=LEAF, files=[binding(p) for p in files],
        manifest_self_excluded=True, changed_gitlinks={"external/ipfs_accelerate": PUBLICATION},
        preserved_gitlinks={k:v for k,v in expected_pins.items() if k != "external/ipfs_accelerate"})
    with MANIFEST.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    expected = {str(p.relative_to(ROOT)) for p in [*files, MANIFEST]} | {"external/ipfs_accelerate"}
    subprocess.run(["git", "add", "--sparse", "-f", "--", *sorted(expected - {"external/ipfs_accelerate"})], cwd=ROOT, check=True)
    staged = set(git(ROOT, "diff", "--cached", "--name-only").decode().splitlines())
    need(staged == expected, "unexpected staged publication files: " + repr(staged ^ expected))
    for row in manifest["files"]:
        raw = git(ROOT, "show", ":" + row["path"])
        need(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "staged parent binding differs")
    subprocess.run(["git", "diff", "--cached", "--check"], cwd=ROOT, check=True)
    print(json.dumps(dict(status="pass", staged_files=len(staged), parent_relative_links=len(relative), published_child_objects=len(github_objects), qualified_leaf=LEAF, accelerator_publication=PUBLICATION)))


if __name__ == "__main__":
    main()
