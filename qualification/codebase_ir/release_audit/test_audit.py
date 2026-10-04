from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit import Closure, Repository, compare_files, file_inclusion, probe_import, run, snapshot


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codebase-ir-release-audit-test-")
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.repos = []

    def tearDown(self):
        for repo in self.repos:
            repo.close()
        self.temp.cleanup()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self):
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Qualification Test",
                "-c",
                "user.email=qualification@example.invalid",
                "commit",
                "-qm",
                "test source",
            ],
            check=True,
        )

    def repo(self, ref=None):
        result = Repository("test", self.root, ["pkg"], ref)
        self.repos.append(result)
        return result

    def closure(self, seed="pkg.core", ref=None, **limits):
        result = Closure([self.repo(ref)], **limits)
        return result, result.run([seed])

    def test_relative_nested_imports_and_package_initializers(self):
        self.write("pkg/__init__.py", "from . import sentinel\n")
        self.write("pkg/sentinel.py", "VALUE = 1\n")
        self.write("pkg/core.py", "def lazy():\n    from . import helper\n    return helper\n")
        self.write("pkg/helper.py", "from .leaf import VALUE\n")
        self.write("pkg/leaf.py", "VALUE = 2\n")
        self.commit()
        _, manifest = self.closure()
        self.assertTrue(manifest["static_closure_complete"])
        self.assertEqual(
            {x["path"] for x in manifest["files"]},
            {"pkg/__init__.py", "pkg/sentinel.py", "pkg/core.py", "pkg/helper.py", "pkg/leaf.py"},
        )
        nested = [x for x in manifest["imports"] if x["module"] == "pkg.helper"]
        self.assertEqual(nested[0]["scope"], ["function:lazy"])

    def test_git_reference_excludes_untracked_required_modules(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "from .new import VALUE\n")
        self.commit()
        self.write("pkg/new.py", "VALUE = 3\n")
        _, current = self.closure()
        _, clean = self.closure(ref="HEAD")
        self.assertFalse(clean["static_closure_complete"])
        self.assertIn("missing_local_module", {x["disposition"] for x in clean["frontier"]})
        gap = next(x for x in compare_files(current, clean)["files"] if x["path"] == "pkg/new.py")
        self.assertEqual(gap["disposition"], "absent_in_reference_closure")
        new = next(x for x in current["files"] if x["path"] == "pkg/new.py")
        self.assertEqual(new["git_status"], "untracked")

    def test_dirty_bytes_and_reference_dependency_change(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "from .old import VALUE\n")
        self.write("pkg/old.py", "VALUE = 1\n")
        self.commit()
        self.write("pkg/core.py", "from .new import VALUE\n")
        self.write("pkg/new.py", "VALUE = 2\n")
        _, current = self.closure()
        _, clean = self.closure(ref="HEAD")
        counts = compare_files(current, clean)["counts"]
        self.assertEqual(counts["different_bytes"], 1)
        self.assertEqual(counts["reference_only_dependency"], 1)
        self.assertEqual(counts["absent_in_reference_closure"], 1)
        self.assertEqual(
            next(x for x in current["files"] if x["path"] == "pkg/core.py")["git_status"],
            "tracked_dirty",
        )

    def test_missing_seed_preserves_executed_ancestor_initializer(self):
        self.write("pkg/__init__.py", "VALUE=1\n")
        self.commit()
        self.write("pkg/core.py", "VALUE=2\n")
        closure, manifest = self.closure(ref="HEAD")
        self.assertEqual([x["path"] for x in manifest["files"]], ["pkg/__init__.py"])
        saved = self.base / "snapshot"
        snapshot(closure, saved)
        result = probe_import("pkg.core", saved, ["test"], ["pkg"], self.base / "probe")
        self.assertEqual(result["missing_module"], "pkg.core")

    def test_syntax_and_size_failures_remain_explicit(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "def invalid(:\n")
        self.commit()
        _, invalid = self.closure()
        self.assertFalse(invalid["static_closure_complete"])
        self.assertIn("syntax_error", {x["disposition"] for x in invalid["frontier"]})
        self.write("pkg/core.py", "#" * 1000)
        _, bounded = self.closure(max_file_bytes=128)
        self.assertFalse(bounded["static_closure_complete"])
        self.assertIn("byte_limit", {x["disposition"] for x in bounded["frontier"]})
        _, bounded_git = self.closure(ref="HEAD", max_file_bytes=8)
        self.assertIn("byte_limit", {x["disposition"] for x in bounded_git["frontier"]})

    def test_module_limit_and_dynamic_frontiers(self):
        self.write("pkg/__init__.py", "")
        self.write(
            "pkg/core.py",
            "import importlib\nname = 'pkg.helper'\nimportlib.import_module(name)\nfrom .helper import *\n",
        )
        self.write("pkg/helper.py", "VALUE=1\n")
        self.commit()
        _, manifest = self.closure()
        self.assertIn("dynamic_import_unresolved", {x["disposition"] for x in manifest["frontier"]})
        self.assertIn("star_export_unresolved", {x["disposition"] for x in manifest["frontier"]})
        _, bounded = self.closure(max_modules=1)
        self.assertFalse(bounded["static_closure_complete"])
        self.assertIn("module_limit", {x["disposition"] for x in bounded["frontier"]})

    def test_source_stability_detects_same_head_edits(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE = 1\n")
        self.commit()
        closure, _ = self.closure()
        self.assertTrue(closure.stability()["stable"])
        self.write("pkg/core.py", "VALUE = 2\n")
        stability = closure.stability()
        self.assertFalse(stability["stable"])
        self.assertTrue(all(x["before"] == x["after"] for x in stability["heads"]))

    def test_index_change_is_dirty_even_when_working_bytes_match_head(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.commit()
        self.write("pkg/core.py", "VALUE=2\n")
        subprocess.run(["git", "-C", str(self.root), "add", "pkg/core.py"], check=True)
        self.write("pkg/core.py", "VALUE=1\n")
        _, manifest = self.closure()
        self.assertEqual(
            next(x for x in manifest["files"] if x["path"] == "pkg/core.py")["git_status"],
            "tracked_dirty",
        )

    def test_file_inclusion_distinguishes_unreached_from_unreleased_file(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.commit()
        self.write("pkg/core.py", "from .new import VALUE\n")
        self.write("pkg/new.py", "VALUE=2\n")
        _, current = self.closure()
        reference, _ = self.closure(seed="pkg", ref="HEAD")
        result = file_inclusion(current, reference)
        core = next(x for x in result["files"] if x["path"] == "pkg/core.py")
        self.assertEqual(core["disposition"], "different_bytes")
        self.assertFalse(core["in_reference_dependency_closure"])
        self.assertEqual(
            next(x for x in result["files"] if x["path"] == "pkg/new.py")["disposition"],
            "missing_in_reference_source",
        )

    def test_probe_separates_bound_omission_from_absent_source(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.commit()
        config = {
            "repositories": [{"name": "test", "root": str(self.root), "packages": ["pkg"]}],
            "seeds": ["pkg.core"],
        }
        result = run(config, self.base / "bounded", with_probes=True, max_modules=1)
        probe = result["observations"]["working"]["imports"][0]
        self.assertEqual(probe["disposition"], "incomplete_snapshot")
        self.assertEqual(probe["snapshot_frontier_causes"], ["module_limit"])

    def test_snapshot_resolves_seed_dependency_without_live_checkout(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "from .other import VALUE\n")
        self.write("pkg/other.py", "VALUE=1\n")
        self.commit()
        closure, _ = self.closure()
        saved = self.base / "snapshot"
        snapshot(closure, saved)
        self.write("pkg/other.py", "raise AssertionError('live fallback')\n")
        result = probe_import("pkg.core", saved, ["test"], ["pkg"], self.base / "probe")
        self.assertEqual(result["disposition"], "imported", result)
        self.assertTrue(result["resolved_local_modules"])
        self.assertTrue(all(str(self.root) not in path for path in result["isolated_sys_path"]))
        self.assertTrue(
            all(
                not x["file"] or Path(x["file"]).is_relative_to(saved)
                for x in result["resolved_local_modules"]
            )
        )

    def test_probe_refuses_dynamic_fallback_to_live_module(self):
        self.write("pkg/__init__.py", "")
        self.write(
            "pkg/core.py", "import importlib\nname = 'pkg.secret'\nimportlib.import_module(name)\n"
        )
        self.write("pkg/secret.py", "raise AssertionError('live fallback')\n")
        self.commit()
        closure, _ = self.closure()
        saved = self.base / "snapshot"
        snapshot(closure, saved)
        self.assertFalse((saved / "test/pkg/secret.py").exists())
        result = probe_import("pkg.core", saved, ["test"], ["pkg"], self.base / "probe")
        self.assertEqual(result["disposition"], "absent_local_module", result)
        self.assertEqual(result["missing_module"], "pkg.secret")

    def test_probe_classifies_missing_external_environment(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "import qualification_nonexistent_dependency\n")
        self.commit()
        closure, _ = self.closure()
        saved = self.base / "snapshot"
        snapshot(closure, saved)
        result = probe_import("pkg.core", saved, ["test"], ["pkg"], self.base / "probe")
        self.assertEqual(result["disposition"], "environment_unavailable", result)
        self.assertEqual(result["missing_module"], "qualification_nonexistent_dependency")

    def test_probe_denies_live_filesystem_write(self):
        live_marker = self.root / "live-marker"
        self.write("pkg/__init__.py", "")
        self.write(
            "pkg/core.py",
            f"from pathlib import Path\nPath({str(live_marker)!r}).write_text('bad')\n",
        )
        self.commit()
        closure, _ = self.closure()
        saved = self.base / "snapshot"
        snapshot(closure, saved)
        result = probe_import("pkg.core", saved, ["test"], ["pkg"], self.base / "probe")
        self.assertEqual(result["disposition"], "isolated_import_error", result)
        self.assertTrue(result["forbidden_operations"])
        self.assertFalse(live_marker.exists())

    def test_run_refuses_existing_output_and_retains_clean_probe(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "from .new import VALUE\n")
        self.commit()
        self.write("pkg/new.py", "VALUE=4\n")
        config = {
            "repositories": [{"name": "test", "root": str(self.root), "packages": ["pkg"]}],
            "seeds": ["pkg.core"],
        }
        output = self.base / "run"
        summary = run(config, output, with_snapshot=True, with_probes=True)
        self.assertEqual(
            summary["observations"]["working"]["imports"][0]["disposition"], "imported"
        )
        self.assertEqual(
            summary["observations"]["head"]["imports"][0]["disposition"], "absent_local_module"
        )
        self.assertEqual(
            json.loads((output / "summary.json").read_text())["schema"],
            "codebase-ir-release-audit/v1",
        )
        with self.assertRaises(FileExistsError):
            run(config, output)


if __name__ == "__main__":
    unittest.main()
