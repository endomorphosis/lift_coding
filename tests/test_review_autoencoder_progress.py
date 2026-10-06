"""Real Git fixtures for ancestral history whose source disappeared later."""
import importlib.util
from pathlib import Path
import subprocess

import pytest


OWNER = Path(__file__).resolve().parents[1] / "scripts/review_autoencoder_progress.py"
spec = importlib.util.spec_from_file_location("progress_review", OWNER)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init", "--quiet")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    (tmp_path / "decoder.py").write_text("version = 1\n")
    (tmp_path / "retained evidence.json").write_text('{"admitted": false}\n')
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
