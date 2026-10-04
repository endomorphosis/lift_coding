"""Disposable Git fixtures, without model execution or publication."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def owner():
    path = Path(__file__).with_name("restore_leaf_trees.py")
    spec = importlib.util.spec_from_file_location("fixture_restore_leaf_trees", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, *, new_invalid=False):
    module = owner()
    repository = tmp_path / "source"
    repository.mkdir()
    module.git(repository, "init", "-b", "main")
    module.git(repository, "config", "user.name", "Disposable fixture")
    module.git(repository, "config", "user.email", "fixture@example.invalid")
    files = {"keep.py": "VALUE = 1\n", "shared.py": "VALUE = 2\n", "legacy.py": "VALUE = 0\n",
             "namespace": "canonical namespace file\n", "gone.py": "VALUE = 3\n",
             "templates/template.py": "VALUE = 0\n"}
    for name, body in files.items():
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    module.git(repository, "add", "--", *files)
    module.git(repository, "commit", "-m", "Disposable initial source")
    baseline = module.git(repository, "rev-parse", "HEAD").stdout.decode().strip()
    module.git(repository, "rm", "gone.py")
    (repository / "legacy.py").write_text("def existing(:\n")
    (repository / "templates/template.py").write_text("{{syntactic placeholder}}\n")
    module.git(repository, "add", "--", "legacy.py", "templates/template.py")
    module.git(repository, "commit", "-m", "Intentional canonical deletion")
    snapshot = module.git(repository, "rev-parse", "HEAD").stdout.decode().strip()
    worktree = tmp_path / "fresh-integration"
    module.git(repository, "worktree", "add", "-b", "fixture-integration", str(worktree), snapshot)
    module.git(worktree, "rm", "keep.py", "namespace")
    (worktree / "shared.py").write_text("VALUE = 99\n")
    (worktree / "namespace").mkdir()
    (worktree / "namespace/branch_child.py").write_text("VALUE = 4\n")
    (worktree / "unique.py").write_text("VALUE = 5\n")
    (worktree / "gone.py").write_text("VALUE = 6\n")
    if new_invalid:
        (worktree / "new_invalid.py").write_text("def new(:\n")
    module.git(worktree, "add", "--", ".")
    module.git(worktree, "commit", "-m", "Disposable archival source changes")
    before = module.git(worktree, "rev-parse", "HEAD").stdout.decode().strip()
    base = tmp_path / "receipts"
    old = base / "main-preparation/fixture"
    (old / "integration-01").mkdir(parents=True)
    plan = {"canonical_repository": str(repository), "origin_main_sha256_or_git_oid": baseline,
            "authoritative_source": {"snapshot_commit": snapshot, "selected_files": []}, "heads": []}
    prepared = {"fresh_worktree": str(worktree), "integrated_tip": before, "python_syntax_errors": []}
    (old / "plan.json").write_text(json.dumps(plan))
    (old / "integration-01/prepared.json").write_text(json.dumps(prepared))
    rows = []
    for name, entry in module.tree(repository, snapshot).items():
        data = module.git(repository, "show", snapshot + ":" + name).stdout
        rows.append({"state": "present", "path": name, "mode": entry["mode"], "git_oid": entry["git_oid"],
                     "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    rows.append({"state": "deleted", "path": "gone.py"})
    manifest = {"authoritative_source": {"snapshot_commit": snapshot, "selected_files": rows}}
    path = base / "full-tree-pins/fixture.json"
    path.parent.mkdir()
    path.write_text(json.dumps(manifest))
    module.BASE = base
    module.MANIFEST_SHA = {"fixture": module.binding(path)["sha256"]}
    return module, repository, worktree, path, snapshot, before


def test_fulltree_restores_deletes_and_conflicting_descendants_preserving_additions(tmp_path):
    module, repository, worktree, _, snapshot, before = fixture(tmp_path)
    original_head = module.git(repository, "rev-parse", "HEAD").stdout
    index = module.git(repository, "rev-parse", "--git-path", "index").stdout.decode().strip()
    original_index = module.binding(repository / index)
    module.restore("fixture")
    current = module.tree(worktree, "HEAD")
    canonical = module.tree(repository, snapshot)
    assert all(current[path] == entry for path, entry in canonical.items())
    assert "unique.py" in current
    assert "namespace/branch_child.py" not in current
    assert "gone.py" not in current
    assert not (worktree / "gone.py").exists()
    assert (worktree / "namespace").is_file()
    module.git(worktree, "merge-base", "--is-ancestor", before, "HEAD")
    assert module.git(repository, "rev-parse", "HEAD").stdout == original_head
    assert module.binding(repository / index) == original_index
    report = json.loads((module.BASE / "main-restoration/fixture/prepared-v2.json").read_text())
    assert report["eligible_for_root_prepublication_review"] is True
    assert len(report["syntax_qualification"]["inherited_canonical_syntax_findings"]) == 1
    assert report["syntax_qualification"]["excluded_fixture_vendor_and_template_paths"] == ["templates/template.py"]
    assert report["origin_push_executed"] is False
    assert report["training_executed"] is False


def test_fulltree_new_invalid_branch_source_keeps_publication_ineligible(tmp_path):
    module, _, _, _, _, _ = fixture(tmp_path, new_invalid=True)
    module.restore("fixture")
    report = json.loads((module.BASE / "main-restoration/fixture/prepared-v2.json").read_text())
    assert report["eligible_for_root_prepublication_review"] is False
    assert [row["path"] for row in report["python_syntax_errors"]] == ["new_invalid.py"]
    assert report["all_source_python_parses_claimed"] is False


def test_fulltree_resealed_manifest_cannot_substitute_canonical_object(tmp_path):
    module, _, worktree, manifest_path, _, before = fixture(tmp_path)
    value = json.loads(manifest_path.read_text())
    value["authoritative_source"]["selected_files"][0]["git_oid"] = "1" * 40
    manifest_path.write_text(json.dumps(value))
    module.MANIFEST_SHA["fixture"] = module.binding(manifest_path)["sha256"]
    with pytest.raises(ValueError, match="differs from canonical snapshot"):
        module.restore("fixture")
    assert module.git(worktree, "rev-parse", "HEAD").stdout.decode().strip() == before
    assert not (module.BASE / "main-restoration").exists()
