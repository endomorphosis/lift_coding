"""Independent disposable-Git publication checks; remote operations are mocked."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "publish_integration.py"

def digest(data): return hashlib.sha256(data).hexdigest()
def run(repo, *args, data=None, env=None):
    return subprocess.check_output(["git", "-C", str(repo), *args], input=data, env=env, stderr=subprocess.PIPE)
def dump(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def setup_repo(path, package=None):
    path.mkdir(parents=True)
    run(path, "init", "-b", "normal")
    run(path, "config", "user.name", "Synthetic Review")
    run(path, "config", "user.email", "synthetic@example.invalid")
    (path / "selected.py").write_text("original bytes\n")
    (path / "foreign.txt").write_text("base foreign bytes\n")
    run(path, "add", "selected.py", "foreign.txt")
    if package is not None:
        run(path, "update-index", "--add", "--cacheinfo", "160000," + package + ",external/ipfs_datasets")
    run(path, "commit", "-m", "synthetic base")
    base = run(path, "rev-parse", "HEAD").decode().strip()
    # Create an upstream descendant through its own alternate index.
    private = path.parent / (path.name + "-upstream.index")
    env = dict(os.environ, GIT_INDEX_FILE=str(private))
    run(path, "read-tree", base, env=env)
    oid = run(path, "hash-object", "-w", "--stdin", data=b"upstream foreign progress\n").decode().strip()
    run(path, "update-index", "--add", "--cacheinfo", "100644," + oid + ",foreign.txt", env=env)
    tree = run(path, "write-tree", env=env).decode().strip()
    parent = run(path, "commit-tree", tree, "-p", base, data=b"synthetic upstream progress\n").decode().strip()
    run(path, "update-ref", "refs/remotes/origin/main", parent)
    # The ordinary index has unrelated staged work and HEAD stays at base.
    (path / "unrelated.py").write_text("unrelated local work\n")
    run(path, "add", "unrelated.py")
    (path / "selected.py").write_text("selected reviewed progress\n")
    (path / "new-doc.md").write_text("selected new documentation\n")
    return base, parent

def exercise(kind):
    with tempfile.TemporaryDirectory(prefix="autoencoder-publisher-review-") as directory:
        root = Path(directory)
        W, P, R = root / "workspace", root / "datasets", root / "review"
        R.mkdir()
        (R / "pipeline").mkdir()
        pbase, pparent = setup_repo(P)
        wbase, wparent = setup_repo(W, pbase)
        spec = importlib.util.spec_from_file_location("independent_publisher", SOURCE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.W, module.P, module.R = W, P, R
        before = module.normal()
        repository = W if kind == "workspace_success" else P
        scope = {"passed": True, "reviewed": True, "required_reviews": ["pipeline/publication-scope-independent-review.json"]}
        for name, repo, base in (("datasets", P, pbase), ("workspace", W, wbase)):
            files = {}
            for rel in ("selected.py", "new-doc.md"):
                data = (repo / rel).read_bytes()
                files[rel] = {"sha256": digest(data), "bytes": len(data),
                              "parent_sha256": digest(b"original bytes\n") if rel == "selected.py" else None}
            scope[name] = {"parent": base, "files": files}
        if kind == "upstream_preimage_changed":
            env = dict(os.environ, GIT_INDEX_FILE=str(root / "changed-upstream.index"))
            run(P, "read-tree", pparent, env=env)
            oid = run(P, "hash-object", "-w", "--stdin", data=b"concurrent selected-file progress\n").decode().strip()
            run(P, "update-index", "--add", "--cacheinfo", "100644," + oid + ",selected.py", env=env)
            tree = run(P, "write-tree", env=env).decode().strip()
            pparent = run(P, "commit-tree", tree, "-p", pparent, data=b"concurrent selected source change\n").decode().strip()
            run(P, "update-ref", "refs/remotes/origin/main", pparent)
        dump(R / "publication-scope.json", scope)
        review = {"passed": True, "findings": [], "artifacts": {
            str(R / "publication-scope.json"): digest((R / "publication-scope.json").read_bytes()),
            str(SOURCE): digest(SOURCE.read_bytes())}}
        dump(R / "pipeline/publication-scope-independent-review.json", review)
        if kind == "candidate_changed": (P / "selected.py").write_text("unreviewed source modification\n")
        if kind == "scope_changed":
            changed = dict(scope, unexpected="unreviewed mutation")
            dump(R / "publication-scope.json", changed)
        if kind == "unsafe_path":
            scope["datasets"]["files"]["../escaped.txt"] = {"sha256": digest(b"escape"), "bytes": 6, "parent_sha256": None}
            (P.parent / "escaped.txt").write_bytes(b"escape")
            dump(R / "publication-scope.json", scope)
            review["artifacts"][str(R / "publication-scope.json")] = digest((R / "publication-scope.json").read_bytes())
            dump(R / "pipeline/publication-scope-independent-review.json", review)
        remote = {str(P): pparent, str(W): wparent}
        pushes = []
        def mocked_git(repo, *args, data=None, env=None):
            # No remote access or actual push is executed by this validator.
            if "fetch" in args: return b""
            if "ls-remote" in args: return (remote[str(repo)] + "\trefs/heads/main\n").encode()
            if "push" in args:
                target = args[-1]
                assert not target.startswith("+") and "--force" not in args and "-f" not in args
                assert target.endswith(":refs/heads/main")
                commit = target.split(":", 1)[0]
                remote[str(repo)] = commit
                pushes.append({"repository": str(repo), "argv": list(args), "commit": commit})
                return b""
            return run(repo, *args, data=data, env=env)
        if kind == "workspace_success":
            # Prepare a descendant datasets publication without invoking another main.
            env = dict(os.environ, GIT_INDEX_FILE=str(root / "datasets-descendant.index"))
            run(P, "read-tree", pparent, env=env)
            tree = run(P, "write-tree", env=env).decode().strip()
            commit = run(P, "commit-tree", tree, "-p", pparent, data=b"synthetic datasets publication\n").decode().strip()
            remote[str(P)] = commit
            dump(R / "datasets-publication.json", {"commit": commit})
        failure = None
        with patch.object(module, "git", side_effect=mocked_git), patch("sys.argv", ["publisher", "workspace" if kind == "workspace_success" else "datasets", "--attempt", "synthetic01"]):
            try: module.main()
            except (ValueError, subprocess.CalledProcessError) as error: failure = str(error)
        assert module.normal() == before, "ordinary indexes/HEADs changed"
        if kind in ("datasets_success", "workspace_success"):
            assert failure is None and len(pushes) == 1
            commit = pushes[0]["commit"]
            assert run(repository, "show", commit + ":foreign.txt") == b"upstream foreign progress\n"
            assert run(repository, "show", commit + ":selected.py") == b"selected reviewed progress\n"
            assert run(repository, "show", commit + ":new-doc.md") == b"selected new documentation\n"
            assert subprocess.run(["git", "-C", str(repository), "cat-file", "-e", commit + ":unrelated.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
            if kind == "workspace_success":
                assert run(W, "ls-tree", commit, "--", "external/ipfs_datasets").decode().split()[2] == remote[str(P)]
        else:
            assert failure is not None and not pushes, "unreviewed input reached publication"
        return {"case": kind, "passed": True, "normal_state_preserved": True,
                "mocked_pushes": len(pushes), "actual_remote_operations": 0,
                "expected_rejection": failure}

if __name__ == "__main__":
    cases = ["datasets_success", "workspace_success", "upstream_preimage_changed", "candidate_changed", "scope_changed", "unsafe_path"]
    expected_source_digest = digest(SOURCE.read_bytes())
    results = []
    for case in cases:
        assert digest(SOURCE.read_bytes()) == expected_source_digest, "publisher source changed during review"
        results.append(exercise(case))
    assert digest(SOURCE.read_bytes()) == expected_source_digest, "publisher source changed during review"
    report = {"schema": "independent-integration-publisher-synthetic-validation/v1",
              "passed": True, "findings": [], "results": results,
              "actual_remote_operations": 0, "models_or_source_runtime_executed": False,
              "artifacts": {str(SOURCE): {"sha256": digest(SOURCE.read_bytes()), "bytes": SOURCE.stat().st_size}}}
    dump(HERE / "pipeline" / "publisher-synthetic-validation.json", report)
    print(json.dumps({"passed": True, "cases": len(results), "actual_remote_operations": 0}))
