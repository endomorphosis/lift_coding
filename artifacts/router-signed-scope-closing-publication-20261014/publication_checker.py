"""Verify frozen signed-scope closing publication; never rerun tests or mutate Git state."""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PHASE = Path(__file__).resolve().parent
ACCEL = Path("/home/barberb/lift_coding/.worktrees/router-signed-scope-closing-20261014")
DATASETS = Path("/home/barberb/lift_coding/.worktrees/repository-proof-context-datasets-20261014")
KIT = Path("/home/barberb/lift_coding/.worktrees/repository-proof-context-kit-20261014")
CHILD_BASE = "b184d30229b3b8f23a390ca24580962d44620536"
DATASETS_REVISION = "a0f60d42f836571a0023515e92dfb0e5724f0d79"
KIT_REVISION = "40c98c71b95be750509ffdb21e7e5494d91b4e79"
CHILD_PHASE = "docs/agent_supervisor/evidence/router-signed-scope-closing-20261014/"
NOTE = ROOT / "implementation_plan/docs/127-supervisor-signed-scope-closing-2026-10-14.md"
RECEIPT = PHASE / "parent-checks.json"
MANIFEST = PHASE / "manifest.json"
LINK_CHECKER_SHA256 = "596a0038b18d592f2e605643890afc85e457558f7b887932a474557d7586819e"
NEW_SUITES = {"benchmarks.agent_supervisor.container_coding.test_terminal_signed_working_set_closing"}
MAX_OBSERVATION_BYTES = 64 * 1024 * 1024
# Loading the pinned documentation utility must not create checkout bytecode.
sys.dont_write_bytecode = True


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def commit(value):
    need(type(value) is str and re.fullmatch(r"[0-9a-f]{40}", value), "exact Git commit required")
    return value


def git(root, *args):
    result = subprocess.run(["git", "--no-optional-locks", *args], cwd=root,
                            capture_output=True, timeout=60)
    need(result.returncode == 0, "Git observation failed: " + repr(args) + ": "
         + result.stderr[:2048].decode("utf-8", "replace"))
    need(len(result.stdout) <= MAX_OBSERVATION_BYTES, "Git observation exceeded byte bound")
    return result.stdout


def load(raw, expected_type=dict):
    need(len(raw) <= MAX_OBSERVATION_BYTES, "JSON observation exceeded byte bound")
    def pairs(rows):
        result = {}
        for key, value in rows:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def nonfinite(_value):
        raise ValueError("nonfinite JSON number")
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    need(type(value) is expected_type, "unexpected JSON root type")
    return value


def binding(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def object_binding(root, revision, row):
    raw = git(root, "show", revision + ":" + row["path"])
    need(type(row["bytes"]) is int and len(raw) == row["bytes"]
         and sha(raw) == row["sha256"], "Git object differs from retained binding: " + row["path"])
    return raw


def refs_and_index(root):
    return dict(index_sha256=sha(git(root, "ls-files", "--stage", "-z")),
                refs_sha256=sha(git(root, "for-each-ref", "--format=%(refname) %(objectname)")),
                head=git(root, "rev-parse", "HEAD").decode().strip())


def tree_entries(root, revision, prefix):
    entries = {}
    for row in git(root, "ls-tree", "-r", "-z", revision, "--", prefix).split(b"\0"):
        if row:
            metadata, path = row.split(b"\t", 1)
            need(path not in entries, "duplicate retained Git path")
            entries[path] = metadata
    return entries


def parent_paths():
    rows = git(ROOT, "status", "--porcelain=v1", "-z", "--untracked-files=all").split(b"\0")
    result = set()
    for row in rows:
        if row:
            need(row[:2] not in (b"R ", b" R", b"C ", b" C"), "parent publication cannot rename files")
            result.add(row[3:].decode("utf-8", "strict"))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child-revision", help="optional independently selected publication SHA")
    parser.add_argument("--qualification", required=True, help="independently selected complete qualification")
    args = parser.parse_args(argv)
    need(re.fullmatch(r"qualification-[0-9]{2,3}", args.qualification), "exact qualification directory required")
    need(not RECEIPT.exists() and not MANIFEST.exists(), "refusing to overwrite publication evidence")
    merge = load((PHASE / "fresh-main-compatibility.json").read_bytes())
    ci = load((PHASE / "child-ci-observation.json").read_bytes())
    need(merge["selected_qualification"] == args.qualification, "selected qualification differs")
    note_name = merge.get("parent_note", str(NOTE.relative_to(ROOT)))
    need(type(note_name) is str and note_name == str(NOTE.relative_to(ROOT)),
         "independently selected parent note filename differs")
    publication = commit(merge["publication_revision"])
    leaf = commit(merge["qualified_leaf"])
    base = commit(merge.get("parent_publication_base", merge.get("parent_base")))
    preserved_evidence_revision = commit(merge["preserved_evidence_revision"])
    need(preserved_evidence_revision == "b184d30229b3b8f23a390ca24580962d44620536",
         "independently reviewed incoming evidence baseline differs")
    if args.child_revision is not None:
        need(commit(args.child_revision) == publication, "independent publication revision differs")
    need(git(ROOT, "rev-parse", "HEAD").decode().strip() == base, "parent publication base changed")
    preserved = merge["preserved_parent_gitlinks"]
    need(set(preserved) == {"external/ipfs_datasets", "external/ipfs_kit"}, "exact preserved dependency pins required")
    datasets_pin = commit(preserved["external/ipfs_datasets"])
    kit_pin = commit(preserved["external/ipfs_kit"])
    expected_pins = {"external/ipfs_accelerate": publication, **preserved}
    index_rows = git(ROOT, "ls-files", "--stage", *expected_pins).decode().splitlines()
    need(len(index_rows) == 3, "three staged dependency pins required")
    for row in index_rows:
        metadata, path = row.split("\t")
        need(metadata == "160000 " + expected_pins[path] + " 0", "dependency index pin differs")
    for path, revision in preserved.items():
        need(git(ROOT, "rev-parse", base + ":" + path).decode().strip() == revision,
             "incoming parent dependency pin was replaced")
    files = [NOTE, PHASE / "observe_hosted_ci.py", PHASE / "child-ci-observation.json", PHASE / "fresh-main-compatibility.json", Path(__file__), RECEIPT]
    expected_paths = {str(path.relative_to(ROOT)) for path in [*files, MANIFEST]} | {"external/ipfs_accelerate"}
    need(parent_paths() <= expected_paths, "foreign parent paths changed during publication")
    guards = [NOTE, PHASE / "observe_hosted_ci.py", PHASE / "child-ci-observation.json", PHASE / "fresh-main-compatibility.json", Path(__file__)]
    before = [binding(path) for path in guards]
    roots = (ROOT, ACCEL, DATASETS, KIT)
    git_before = {str(root): refs_and_index(root) for root in roots}
    remotes = []
    for root, revision in ((ACCEL, publication), (DATASETS, DATASETS_REVISION), (KIT, KIT_REVISION)):
        remote = git(root, "ls-remote", "origin", "refs/heads/main").decode().split()
        need(len(remote) == 2 and remote[1] == "refs/heads/main", "unambiguous published main required")
        remote_revision = commit(remote[0])
        # Root fetches metadata beforehand if needed. This checker never fetches
        # or changes refs, checkouts, the index, or executable source bytes.
        git(root, "merge-base", "--is-ancestor", revision, remote_revision)
        need(git(root, "rev-parse", "HEAD").decode().strip() == revision, "owned checkout moved")
        need(not git(root, "status", "--porcelain"), "owned dependency checkout is dirty")
        remotes.append(dict(path=str(root), head=revision, observed_origin_main=remote_revision,
                            published_ancestor=True))
        if root == DATASETS:
            git(root, "merge-base", "--is-ancestor", datasets_pin, remote_revision)
        if root == KIT:
            git(root, "merge-base", "--is-ancestor", kit_pin, remote_revision)
    git(ACCEL, "merge-base", "--is-ancestor", CHILD_BASE, publication)
    git(ACCEL, "merge-base", "--is-ancestor", leaf, publication)
    child_manifest_raw = git(ACCEL, "show", leaf + ":" + CHILD_PHASE + "manifest.json")
    child_manifest = load(child_manifest_raw)
    need(type(child_manifest["files"]) is list
         and len({row["path"] for row in child_manifest["files"]}) == len(child_manifest["files"]),
         "qualified child manifest contains duplicate paths")
    need(child_manifest_raw == git(ACCEL, "show", publication + ":" + CHILD_PHASE + "manifest.json"),
         "qualified child manifest changed at publication")
    for row in child_manifest["files"]:
        raw = object_binding(ACCEL, leaf, row)
        need(raw == git(ACCEL, "show", publication + ":" + row["path"]), "qualified child path changed")
    git(ACCEL, "merge-base", "--is-ancestor", CHILD_BASE, preserved_evidence_revision)
    git(ACCEL, "merge-base", "--is-ancestor", preserved_evidence_revision, publication)
    prior = tree_entries(ACCEL, preserved_evidence_revision, "docs/agent_supervisor/evidence/")
    current = tree_entries(ACCEL, publication, "docs/agent_supervisor/evidence/")
    need(prior and all(current.get(path) == metadata for path, metadata in prior.items()),
         "prior child evidence objects changed")
    qraw = git(ACCEL, "show", leaf + ":" + CHILD_PHASE + args.qualification + "/commands.json")
    q = load(qraw)
    selected_documentation = merge["selected_documentation"]
    need(type(selected_documentation) is str
         and re.fullmatch(r"documentation-checks(?:-[0-9]{2})?\.json", selected_documentation),
         "exact selected documentation receipt filename required")
    docs_raw = git(ACCEL, "show", leaf + ":" + CHILD_PHASE + selected_documentation)
    docs = load(docs_raw)
    need(q["status"] == docs["status"] == "pass" and q["pytest_exit_code"] == 0,
         "retained qualification or docs failed")
    doc_before = docs["before"]
    need(type(doc_before) is dict and doc_before == docs["after"]
         and doc_before["qualification_path"] == CHILD_PHASE + args.qualification
         and doc_before["qualification_sha256"] == sha(qraw)
         and doc_before["source_bindings"] == q["before"],
         "documentation custody does not bind the selected qualification")
    doc_preserved = doc_before["preserved_evidence"]
    need(type(doc_preserved) is list and len(doc_preserved) == 1
         and doc_preserved[0]["revision"] == preserved_evidence_revision
         and doc_preserved[0]["all_git_objects_match"] is True
         and type(doc_preserved[0]["file_count"]) is int
         and doc_preserved[0]["file_count"] == len(prior),
         "documentation custody names another preserved evidence baseline")
    doc_inputs = []
    for name in ("read_guards", "documents", "current_evidence"):
        rows = doc_before[name]
        need(type(rows) is list and rows
             and len({row["path"] for row in rows}) == len(rows),
             "documentation input population differs: " + name)
        for row in rows:
            actual = object_binding(ACCEL, leaf, row)
            need(actual == git(ACCEL, "show", publication + ":" + row["path"]),
                 "qualified documentation input changed at publication: " + row["path"])
            doc_inputs.append(dict(row, documentation_input_kind=name))
    doc_log = docs["log_binding"]
    actual = object_binding(ACCEL, leaf, doc_log)
    need(actual == git(ACCEL, "show", publication + ":" + doc_log["path"]),
         "qualified documentation log changed at publication")
    need(q["datasets_execution_revision"] == DATASETS_REVISION
         and q["kit_execution_revision"] == KIT_REVISION, "actual execution dependency changed")
    need(q["before"] == q["after"] and len(q["before"]) == 268, "qualification custody changed")
    need(len({(row["repository"], row["path"]) for row in q["before"]}) == len(q["before"]),
         "qualification source bindings contain duplicate identities")
    counts = collections.Counter(row["repository"] for row in q["before"])
    need(counts == {"accelerator": 217, "datasets_execution_checkout": 51}, "source binding scopes differ")
    inventory = load(git(ACCEL, "show", leaf + ":" + CHILD_PHASE + "source-inventory.json"), list)
    source_ids = [(row["repository"], row["path"]) for row in inventory]
    need(len(source_ids) == len(set(source_ids)) == 268
         and set(source_ids) == {(row["repository"], row["path"]) for row in q["before"]},
         "qualified listed dependency roster differs")
    selected_targets = load(git(ACCEL, "show", leaf + ":" + CHILD_PHASE + "targets.json"), list)
    need(q["targets"] == selected_targets
         and len(q["targets"]) == len(set(q["targets"])) > 0
         and all(type(target) is str and target.endswith(".py") and "::" not in target
                 for target in selected_targets), "complete qualification suite population differs")
    need(q["accelerator_base"] == CHILD_BASE
         and q["pytest_invocations"] == 1 and q["separate_collection"] is False
         and q["source_before_after_equal"] is True
         and q["collection_execution_agrees"] is True
         and q["historical_codec_and_edit_mapper_unchanged"] is True
         and q["source_binding_scope"] == "listed_dependencies_not_complete_import_closure"
         and q["datasets_execution_path"] == str(DATASETS)
         and q["kit_execution_path"] == str(KIT), "retained execution contract differs")
    for name in ("junit.xml", "tests.stdout.log", "tests.stderr.log"):
        actual = git(ACCEL, "show", leaf + ":" + CHILD_PHASE + args.qualification + "/" + name)
        need(type(q[name]) is dict and q[name]["bytes"] == len(actual)
             and q[name]["sha256"] == sha(actual), "raw qualification artifact differs: " + name)
    for row in q["frozen_changed_source_snapshots"]:
        original = object_binding(ACCEL, leaf, row)
        need(original == git(ACCEL, "show", leaf + ":" + row["snapshot"]),
             "frozen qualified source snapshot differs: " + row["path"])

    ds_comparison = []
    for row in q["before"]:
        root = ACCEL if row["repository"] == "accelerator" else DATASETS
        revision = publication if root == ACCEL else DATASETS_REVISION
        raw = object_binding(root, revision, row)
        if root == DATASETS:
            need(raw == git(DATASETS, "show", datasets_pin + ":" + row["path"]),
                 "used datasets object differs at preserved parent pin: " + row["path"])
            ds_comparison.append(dict(row, preserved_parent_pin=datasets_pin, same_used_object=True))
    xml = ET.fromstring(git(ACCEL, "show", leaf + ":" + CHILD_PHASE + args.qualification + "/junit.xml"))
    cases = [(case.get("classname"), case.get("name")) for case in xml.iter("testcase")]
    tests = len(cases)
    need(all(type(name) is str and name and type(case) is str and case for name, case in cases),
         "exact JUnit case names required")
    need(tests > 0 and len(set(cases)) == tests == q["distinct_junit_cases"] == q["collected_tests"], "distinct JUnit identities differ")
    outcome = dict(tests=tests, failures=sum(1 for _ in xml.iter("failure")),
                   errors=sum(1 for _ in xml.iter("error")), skipped=sum(1 for _ in xml.iter("skipped")))
    need(outcome == q["junit"] and outcome == dict(tests=tests, failures=0, errors=0, skipped=0),
         "retained JUnit outcome differs")
    targets = {name.removesuffix(".py").replace("/", ".") for name in q["targets"]}
    need({name for name, _ in cases} <= targets, "JUnit case lies outside retained suites")
    new_cases = sum(name in NEW_SUITES for name, _ in cases)
    need(NEW_SUITES <= {name for name, _ in cases}
         and type(child_manifest["new_cases"]) is int
         and type(merge["retained_new_cases"]) is int
         and new_cases > 0
         and new_cases == child_manifest["new_cases"] == merge["retained_new_cases"],
         "new signed-scope cases differ from retained JUnit and publication metadata")
    need(type(child_manifest["selected_tests"]) is int
         and type(merge["retained_tests"]) is int
         and tests == child_manifest["selected_tests"] == merge["retained_tests"],
         "total case count differs from retained JUnit and publication metadata")
    baseline_raw = git(ACCEL, "show", leaf + ":" + CHILD_PHASE + "baseline-01/commands.json")
    baseline = load(baseline_raw)
    need(baseline["baseline_control"] is True and baseline["status"] == "expected_regression"
         and baseline["accelerator_execution_head"] == CHILD_BASE
         and baseline["unpatched_omitted_source_drift_reaches_authored_provider"] is True
         and baseline["source_before_after_equal"] is True
         and baseline["junit"] == dict(tests=1, failures=1, errors=0, skipped=0),
         "unpatched regression control differs")
    need(doc_before["baseline_controls"] == [dict(path=CHILD_PHASE+"baseline-01/commands.json",
         bytes=len(baseline_raw), sha256=sha(baseline_raw))], "documentation baseline control binding differs")
    for name in ("junit.xml", "tests.stdout.log", "tests.stderr.log"):
        raw = git(ACCEL, "show", leaf + ":" + CHILD_PHASE + "baseline-01/" + name)
        need(baseline[name] == dict(bytes=len(raw), sha256=sha(raw)), "baseline raw artifact differs")
    for row in baseline["frozen_changed_source_snapshots"]:
        raw = git(ACCEL, "show", leaf + ":" + row["snapshot"])
        need(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "baseline source snapshot differs")
        if row["path"] == "ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py":
            need(raw == git(ACCEL, "show", CHILD_BASE+":"+row["path"]), "baseline router is not the published parent")
    need(type(doc_before["selected_tests"]) is int
         and type(doc_before["suites"]) is int
         and type(doc_before["new_cases"]) is int
         and doc_before["selected_tests"] == tests
         and doc_before["suites"] == len(selected_targets)
         and doc_before["new_cases"] == new_cases,
         "documentation counters differ from selected JUnit and suite roster")
    need(type(q["elapsed_seconds"]) in (int, float) and q["elapsed_seconds"] >= 0,
         "retained qualification duration missing")
    need(q["actual_inert_child_probes"] is True
         and q["authored_provider_stubs_exercised"] is True
         and q["authored_pinned_prover_transcripts"] is False
         and q["authored_legacy_recording_index_seam"] is True
         and q["authored_listener_and_deployment_metadata_seams"] is True
         and q["worker_uid_qualified"] is False
         and q["production_coding_child_adoption"] is False
         and q["docker_run"] is False
         and q["runtime_databases_published"] is False
         and q["historical_evidence_result_reused"] is False
         and q["official_task_result"] is None
         and q["total_session_token_savings_established"] is False
         and q["proof_authority"] is False and q["completion_authority"] is False,
         "retained authored signed-scope qualification limits changed")
    need(all(type(q[field]) is int and q[field] == 0 for field in (
        "provider_calls", "external_provider_calls", "model_calls", "training_steps", "solver_calls",
        "native_solver_or_kernel_executions")),
        "retained qualification called an external provider/model/trainer/solver")
    need(len(docs["steps"]) == 4 and all(row["exit_code"] == 0 for row in docs["steps"]), "local doc gates differ")
    need(type(docs["relative_links"]) is int and docs["relative_links"] > 0
         and type(docs["anchors"]) is int and docs["anchors"] >= 0, "doc observations missing")
    need(ci["head_sha"] == ci["run"]["head_sha"] == ci["check_run"]["head_sha"] == publication,
         "CI observation names another publication")
    need(type(ci["run_id"]) is int and ci["run_id"] > 0
         and type(ci["run"]["id"]) is int and ci["run"]["id"] == ci["run_id"]
         and ci["status"] == ci["run"]["status"]
         and ci["conclusion"] == ci["run"]["conclusion"],
         "CI run identity or raw status differs")
    jobs = ci["jobs"]["jobs"]
    need(type(jobs) is list and len(jobs) == ci["jobs"]["total_count"], "CI job population differs")
    need(all(job["head_sha"] == publication and job["run_id"] == ci["run_id"]
             and type(job["run_id"]) is int and type(job["id"]) is int and job["id"] > 0
             and job["run_url"] == ci["run"]["url"]
             and type(job["steps"]) is list and type(job["runner_id"]) is int for job in jobs)
         and len({job["id"] for job in jobs}) == len(jobs),
         "CI job head or steps differ")
    check = ci["check_run"]
    selected_jobs = [job for job in jobs if job["check_run_url"] == check["url"]]
    need(type(check["id"]) is int and check["id"] > 0
         and len(selected_jobs) == 1
         and selected_jobs[0]["id"] == check["id"]
         and check["status"] == selected_jobs[0]["status"]
         and check["conclusion"] == selected_jobs[0]["conclusion"],
         "raw CI check does not belong to its retained workflow job")
    repository_api = "https://api.github.com/repos/endomorphosis/ipfs_accelerate_py/"
    need(ci["run"]["url"] == repository_api + "actions/runs/" + str(ci["run_id"])
         and check["url"] == repository_api + "check-runs/" + str(check["id"]),
         "CI run or check endpoint identity differs")
    steps_executed = any(job["steps"] for job in jobs)
    billing_locked = any("billing" in row.get("message", "").lower()
                         and row.get("annotation_level") == "failure" for row in ci["annotations"])
    hosted_passed = bool(jobs) and ci["status"] == "completed" and ci["conclusion"] == "success" and all(
        job["conclusion"] == "success" and job["runner_id"] > 0 and job["steps"] for job in jobs)
    need(ci["hosted_steps_executed"] is steps_executed
         and ci["billing_lock_observed"] is billing_locked
         and ci["hosted_gates_passed"] is hosted_passed, "CI summary does not match actual jobs/annotations")
    checker_path = ACCEL / "scripts/docs/check_current_docs_links.py"
    checker_raw = checker_path.read_bytes()
    need(sha(checker_raw) == LINK_CHECKER_SHA256
         and checker_raw == git(ACCEL, "show", publication + ":scripts/docs/check_current_docs_links.py"),
         "trusted documentation checker changed")
    spec = importlib.util.spec_from_file_location("publication_link_checker", checker_path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    checker.ROOT = ROOT
    note_raw = NOTE.read_bytes()
    need(note_raw.endswith(b"\n") and not note_raw.endswith(b"\n\n")
         and all(not line.endswith((b" ", b"\t")) for line in note_raw.splitlines()), "note whitespace differs")
    # Empty exclusive output files let the link checker resolve these local
    # report targets. Failure artifacts remain for review and cannot be reused.
    with RECEIPT.open("x", encoding="utf-8") as receipt_handle, MANIFEST.open("x", encoding="utf-8") as manifest_handle:
        errors = checker.check_file(NOTE, check_anchors=True)
        need(not errors, "parent note links failed: " + repr(errors))
        links = [checker.split_target(match.group("target")) for match in
                 checker.LINK_RE.finditer(checker.strip_markup_noise(NOTE.read_text()))]
        relative = [(path, fragment) for path, fragment in links if not checker.is_external(path, fragment)]
        prefix = "https://github.com/endomorphosis/ipfs_accelerate_py/blob/" + publication + "/"
        objects = []
        for target, fragment in links:
            if target.startswith(prefix):
                path = urllib.parse.unquote(target[len(prefix):])
                raw = git(ACCEL, "show", publication + ":" + path)
                if fragment:
                    need((ACCEL / path).read_bytes() == raw, "published anchor file differs")
                    need(fragment in checker.collect_markdown_anchors(ACCEL / path), "published anchor missing")
                objects.append(dict(path=path, bytes=len(raw), sha256=sha(raw), fragment=fragment, status="pass"))
        need(objects, "at least one exact publication object link required")
        after = [binding(path) for path in guards]
        git_after = {str(root): refs_and_index(root) for root in roots}
        need(before == after and git_before == git_after, "input bytes or Git refs/index changed")
        need(all(not git(root, "status", "--porcelain") for root in roots[1:]),
             "owned dependency working state changed during publication checks")
        need(parent_paths() <= expected_paths, "foreign parent paths changed during checks")
        receipt = dict(schema="router-signed-scope-closing-parent-checks@1",
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), parent_base=base,
            qualified_leaf=leaf, accelerator_publication=publication, dependencies=remotes,
            staged_gitlinks=index_rows, retained_tests=tests, retained_new_cases=new_cases,
            retained_suites=len(q["targets"]), retained_source_bindings=len(q["before"]),
            retained_accelerator_bindings=counts["accelerator"], retained_datasets_bindings=counts["datasets_execution_checkout"],
            qualified_source_git_objects_match=True, qualified_child_paths_unchanged=len(child_manifest["files"])+1,
            prior_evidence_git_objects_preserved=len(prior),
            preserved_evidence_revision=preserved_evidence_revision,
            datasets_execution_revision=DATASETS_REVISION,
            preserved_parent_datasets_pin=datasets_pin, datasets_same_used_objects=ds_comparison,
            kit_execution_revision=KIT_REVISION, preserved_parent_kit_pin=kit_pin,
            listed_kit_source_bindings=0,
            complete_import_closure_attested=False, relative_links_passed=True,
            relative_link_count=len(relative), relative_anchor_count=sum(bool(fragment) for _, fragment in relative),
            published_child_objects=objects, checker=dict(path=str(checker_path), sha256=sha(checker_raw),
                api="check_file(path, check_anchors=True)", root_override=str(ROOT)),
            local_doc_gates_on_qualified_leaf=len(docs["steps"]), local_doc_relative_links=docs["relative_links"],
            local_doc_anchors=docs["anchors"], retained_elapsed_seconds=q["elapsed_seconds"],
            documentation_selected_qualification_bound=True,
            selected_documentation=selected_documentation,
            documentation_receipt_sha256=sha(docs_raw),
            documentation_qualification_sha256=sha(qraw),
            documentation_inputs_git_objects_match=doc_inputs,
            documentation_log_git_object_matches=True,
            retained_actual_inert_child_probes=True, retained_authored_provider_stubs_exercised=True,
            retained_authored_pinned_prover_transcripts=False, retained_native_solver_or_kernel_executions=0,
            selected_qualification=args.qualification,
            baseline_control_status=baseline["status"], baseline_control_count_added_to_final_tests=False,
            unpatched_omitted_source_drift_reaches_authored_provider=True,
            retained_authored_listener_and_deployment_metadata_seams=True,
            retained_worker_uid_qualified=False, retained_production_coding_child_adoption=False,
            retained_external_provider_calls=0, retained_model_calls=0, retained_training_steps=0,
            retained_solver_calls=0, retained_docker_run=False, retained_official_task_result=None,
            runtime_databases_published=False, generic_git_cache_keys_supported=False,
            git_tree_equivalence_verified=False, complete_multi_ir_qualification=False,
            hosted_steps_executed=steps_executed,
            hosted_gates_passed=hosted_passed, billing_lock_observed=billing_locked,
            tests_or_workflow_rerun=False, read_guards_before=before, read_guards_after=after,
            read_guards_unchanged=True, git_state_before=git_before, git_state_after=git_after,
            git_refs_and_index_mutated=False, status="pass", model_provider_solver_docker_calls=0,
            proof_authority=False, execution_authority=False, completion_authority=False,
            total_session_token_savings_established=False)
        json.dump(receipt, receipt_handle, indent=2, sort_keys=True)
        receipt_handle.write("\n")
        receipt_handle.flush()
        manifest = dict(schema="router-signed-scope-closing-parent-manifest@1", parent_base=base,
            accelerator_publication=publication, qualified_leaf=leaf, files=[binding(path) for path in files],
            manifest_self_excluded=True, changed_gitlinks={"external/ipfs_accelerate": publication},
            preserved_gitlinks=preserved)
        json.dump(manifest, manifest_handle, indent=2, sort_keys=True)
        manifest_handle.write("\n")
    print(json.dumps(dict(status="pass", parent_paths=len(expected_paths), retained_tests=tests,
        retained_new_cases=new_cases, retained_suites=len(q["targets"]), qualified_leaf=leaf,
        accelerator_publication=publication, git_refs_and_index_mutated=False)))


if __name__ == "__main__":
    main()
