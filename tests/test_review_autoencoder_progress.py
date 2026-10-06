"""Real Git fixtures for ancestral history whose source disappeared later."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest


OWNER = Path(__file__).resolve().parents[1] / "scripts/review_autoencoder_progress.py"
spec = importlib.util.spec_from_file_location("progress_review", OWNER)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def forbid_file_reads(monkeypatch):
    original = owner.os.read
    def read(descriptor, size):
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            pytest.fail("unexpected regular-file read")
        return original(descriptor, size)  # Git subprocess error/stdout pipes.
    monkeypatch.setattr(owner.os, "read", read)


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init", "--quiet")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    (tmp_path / "decoder.py").write_text("version = 1\n")
    (tmp_path / "retained evidence.json").write_text('{"admitted": false}\n')
    (tmp_path / "stable.py").write_text("stable = True\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "--quiet", "-m", "Initial decoder")
    return tmp_path, git(tmp_path, "rev-parse", "HEAD")


def test_ancestor_can_have_missing_source(repository):
    repo, parent = repository
    (repo / "decoder.py").unlink()
    git(repo, "add", "-u")
    git(repo, "commit", "--quiet", "-m", "Snapshot accidentally omits decoder")
    result = owner.review(repo, parent, "HEAD", ["decoder.py", "retained evidence.json"])
    assert result["source_history_reachable_from_target"] is True
    assert result["counts"] == {"identical": 1, "modified": 0, "missing": 1}
    assert result["paths"][0]["target"] is None
    assert not result["semantic_qualification_granted"]
    assert not result["lean_admission_granted"]


def test_later_improvement_is_reviewed_without_mutation(repository):
    repo, parent = repository
    (repo / "decoder.py").write_text("version = 2\n")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "New decoder version")
    head = git(repo, "rev-parse", "HEAD")
    index = (repo / ".git/index").read_bytes()
    result = owner.review(repo, parent, head, ["decoder.py"])
    assert result["counts"]["modified"] == 1
    assert (repo / "decoder.py").read_text() == "version = 2\n"
    assert git(repo, "rev-parse", "HEAD") == head
    assert (repo / ".git/index").read_bytes() == index


def test_identical_blob_does_not_require_ancestry(repository):
    repo, parent = repository
    git(repo, "checkout", "--quiet", "--orphan", "independent")
    git(repo, "commit", "--quiet", "-m", "Independent identical source")
    result = owner.review(repo, parent, "HEAD", ["decoder.py"])
    assert result["source_history_reachable_from_target"] is False
    assert result["counts"]["identical"] == 1


@pytest.mark.parametrize("relative", ["../decoder.py", "/decoder.py", "./decoder.py", ".git/config"])
def test_unsafe_paths_refused(repository, relative):
    repo, parent = repository
    with pytest.raises(ValueError):
        owner.review(repo, parent, "HEAD", [relative])


def test_duplicate_and_unknown_sources_refused(repository):
    repo, parent = repository
    with pytest.raises(ValueError):
        owner.review(repo, parent, "HEAD", ["decoder.py", "decoder.py"])
    with pytest.raises(ValueError):
        owner.review(repo, parent, "HEAD", ["unknown.py"])


def test_literal_pathspec_and_symbolic_file_boundary(repository):
    repo, _ = repository
    (repo / ":(glob)decoder*").write_text("literal file\n")
    (repo / "link").symlink_to("decoder.py")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "Literal and symbolic files")
    parent = git(repo, "rev-parse", "HEAD")
    result = owner.review(repo, parent, "HEAD", [":(glob)decoder*"])
    assert result["counts"]["identical"] == 1
    with pytest.raises(ValueError):
        owner.review(repo, parent, "HEAD", ["link"])


def test_default_result_preserves_v1_without_working_fields(repository):
    repo, parent = repository
    old = owner.review(repo, parent, "HEAD", ["decoder.py"])
    explicit = owner.review(repo, parent, "HEAD", ["decoder.py"], working_tree=False)
    assert old == explicit
    assert old["schema"] == "autoencoder-effective-tree-review/v1"
    assert "working_counts" not in old and "working_tree" not in old["paths"][0]


def test_published_git_files_are_missing_or_dirty_in_live_tree_without_git_mutation(repository):
    repo, parent = repository
    head, index = git(repo, "rev-parse", "HEAD"), (repo / ".git/index").read_bytes()
    (repo / "retained evidence.json").unlink()
    (repo / "decoder.py").write_text("version = 3\n")
    (repo / "decoder.py").chmod(0o755)
    result = owner.review(repo, parent, "HEAD",
                          ["decoder.py", "retained evidence.json", "stable.py"], working_tree=True)
    assert result["counts"] == {"identical": 3, "modified": 0, "missing": 0}
    assert result["working_counts"] == {"identical": 1, "modified": 1, "missing": 1}
    live = result["paths"][0]["working_tree"]
    assert live["sha256"] == hashlib.sha256(b"version = 3\n").hexdigest()
    assert live["bytes"] == len(b"version = 3\n") and live["mode"] == "100755"
    assert live["comparison_reference"] == "target" and live["expected_revision"] == head
    missing = result["paths"][1]["working_tree"]
    assert missing["status"] == "missing" and missing["sha256"] is None
    assert git(repo, "rev-parse", "HEAD") == head
    assert (repo / ".git/index").read_bytes() == index
    assert not result["git_state_mutated"] and not result["model_executed"]


def test_ancestor_deleted_from_git_keeps_source_reference_explicit(repository):
    repo, parent = repository
    original = (repo / "decoder.py").read_bytes()
    (repo / "decoder.py").unlink()
    git(repo, "add", "-u")
    git(repo, "commit", "--quiet", "-m", "Published target omits ancestral source")
    absent = owner.review(repo, parent, "HEAD", ["decoder.py"], working_tree=True)
    assert absent["counts"]["missing"] == absent["working_counts"]["missing"] == 1
    (repo / "decoder.py").write_bytes(original)
    restored = owner.review(repo, parent, "HEAD", ["decoder.py"], working_tree=True)
    assert restored["counts"]["missing"] == 1
    assert restored["working_counts"]["identical"] == 1
    working = restored["paths"][0]["working_tree"]
    assert working["comparison_reference"] == "source"
    assert working["expected_revision"] == parent


def test_working_git_mode_is_compared_even_when_bytes_match(repository):
    repo, parent = repository
    (repo / "decoder.py").chmod(0o755)
    result = owner.review(repo, parent, "HEAD", ["decoder.py"], working_tree=True)
    row = result["paths"][0]
    assert row["status"] == "identical" and row["working_tree"]["status"] == "modified"
    assert row["working_tree"]["sha256"] == row["target"]["sha256"]


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_working_aliases_and_nonregular_files_refuse_without_reading(repository, monkeypatch, kind):
    repo, parent = repository
    path = repo / "decoder.py"
    path.unlink()
    if kind == "symlink":
        path.symlink_to("retained evidence.json")
    elif kind == "directory":
        path.mkdir()
    elif kind == "fifo":
        os.mkfifo(path)
    forbid_file_reads(monkeypatch)
    with pytest.raises(ValueError, match="regular file"):
        owner.review(repo, parent, "HEAD", ["decoder.py"], working_tree=True)


def test_stable_hardlinked_source_is_read_only_and_identical(repository):
    repo, parent = repository
    path = repo / "decoder.py"
    os.link(path, repo / "retained-source-copy.py")
    head, index = git(repo, "rev-parse", "HEAD"), (repo / ".git/index").read_bytes()
    result = owner.review(repo, parent, "HEAD", ["decoder.py"], working_tree=True)
    assert path.stat().st_nlink == 2
    assert result["working_counts"] == {"identical": 1, "modified": 0, "missing": 0}
    assert result["paths"][0]["working_tree"]["sha256"] == result["paths"][0]["target"]["sha256"]
    assert git(repo, "rev-parse", "HEAD") == head
    assert (repo / ".git/index").read_bytes() == index


def test_working_parent_symlink_and_repository_alias_refuse(repository, monkeypatch):
    repo, _ = repository
    (repo / "source").mkdir()
    (repo / "source/decoder.py").write_text("bound = True\n")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "Nested source")
    source = git(repo, "rev-parse", "HEAD")
    (repo / "source").rename(repo / "original-source")
    (repo / "source").symlink_to("original-source", target_is_directory=True)
    forbid_file_reads(monkeypatch)
    with pytest.raises(ValueError, match="actual directories"):
        owner.review(repo, source, "HEAD", ["source/decoder.py"], working_tree=True)
    alias = repo.parent / (repo.name + "-alias")
    alias.symlink_to(repo, target_is_directory=True)
    with pytest.raises(ValueError, match="canonical directory"):
        owner.review(alias, source, "HEAD", ["decoder.py"], working_tree=True)


@pytest.mark.parametrize("relative", ["../decoder.py", "source/../decoder.py", "/decoder.py",
                                        "./decoder.py", ".git/index"])
def test_working_parent_traversal_refuses_before_live_hashing(repository, monkeypatch, relative):
    repo, parent = repository
    monkeypatch.setattr(owner, "working_entry", lambda *_: pytest.fail("unsafe live hash attempted"))
    with pytest.raises(ValueError, match="normalized repository-relative"):
        owner.review(repo, parent, "HEAD", [relative], working_tree=True)


@pytest.mark.parametrize("mutation", ["grow", "metadata", "replace", "link"])
def test_working_race_refuses_changed_file_metadata(repository, monkeypatch, mutation):
    repo, parent = repository
    path = repo / "decoder.py"
    inode, original_read = path.stat().st_ino, owner.os.read
    changed = False
    def read(descriptor, size):
        nonlocal changed
        content = original_read(descriptor, size)
        if not changed and os.fstat(descriptor).st_ino == inode:
            changed = True
            if mutation == "grow":
                with path.open("ab") as stream:
                    stream.write(b"unexpected growth\n")
            elif mutation == "metadata":
                info = path.stat()
                os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000))
            elif mutation == "replace":
                path.unlink()
                path.write_text("version = 1\n")
            else:
                os.link(path, repo / "concurrent-link.py")
        return content
    monkeypatch.setattr(owner.os, "read", read)
    with pytest.raises(ValueError, match="grew|metadata changed"):
        owner.review(repo, parent, "HEAD", ["decoder.py"], working_tree=True)
    assert changed


def test_working_bound_is_checked_before_read(repository, monkeypatch):
    repo, parent = repository
    with (repo / "decoder.py").open("wb") as stream:
        stream.truncate(owner.MAX_BLOB_BYTES + 1)
    forbid_file_reads(monkeypatch)
    with pytest.raises(ValueError, match="32 MiB"):
        owner.review(repo, parent, "HEAD", ["decoder.py"], working_tree=True)


def test_cli_missing_guard_requires_opt_in_and_emits_actual_hashes(repository, tmp_path):
    repo, parent = repository
    command = [sys.executable, str(OWNER), "--repository", str(repo), "--source", parent,
               "--target", "HEAD", "--path", "decoder.py", "--path", "stable.py",
               "--fail-on-working-tree-missing"]
    refused = subprocess.run(command, capture_output=True, text=True)
    assert refused.returncode == 2 and "requires --working-tree" in refused.stderr
    head, index = git(repo, "rev-parse", "HEAD"), (repo / ".git/index").read_bytes()
    (repo / "decoder.py").unlink()
    output = tmp_path / "working-review.json"
    observed = subprocess.run(command + ["--working-tree", "--output", str(output)],
                              capture_output=True, text=True)
    assert observed.returncode == 1
    summary, report = json.loads(observed.stdout), json.loads(output.read_text())
    assert summary["working_counts"] == {"identical": 1, "modified": 0, "missing": 1}
    assert summary["working_paths"][1]["sha256"] == hashlib.sha256(b"stable = True\n").hexdigest()
    assert report["paths"][0]["target"] is not None
    assert report["paths"][0]["working_tree"]["sha256"] is None
    assert git(repo, "rev-parse", "HEAD") == head
    assert (repo / ".git/index").read_bytes() == index
