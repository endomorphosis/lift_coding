from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit import Repository
from runtime_demand import DemandError, DemandOwner, qualify


class RuntimeDemandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codebase-ir-runtime-demand-test-")
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.repos = []

    def tearDown(self):
        for repo in self.repos:
            repo.close()
        self.temp.cleanup()

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data)

    def commit(self):
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Runtime Qualification",
                "-c",
                "user.email=runtime@example.invalid",
                "commit",
                "-qm",
                "source",
            ],
            check=True,
        )

    def owner(self, **bounds):
        repo = Repository("test", self.root, ["pkg"])
        self.repos.append(repo)
        return DemandOwner([repo], self.base / "snapshots", **bounds)

    def qualify(self, **bounds):
        allow_ctypes = bounds.pop("allow_ctypes_python_handle", False)
        config = {
            "repositories": [{"name": "test", "root": str(self.root), "packages": ["pkg"]}],
            "seeds": ["pkg.core"],
            "bounds": {"max_rounds": 20, "total_timeout": 20},
            "allow_ctypes_python_handle": allow_ctypes,
        }
        with contextlib.redirect_stdout(io.StringIO()):
            return qualify(config, self.base / "run", **bounds)

    def test_transitive_runtime_demands_initializers_and_assets(self):
        self.write("pkg/__init__.py", "from .bootstrap import VALUE\n")
        self.write(
            "pkg/bootstrap.py",
            "import json\nfrom pathlib import Path\nVALUE = json.loads(Path(__file__).with_name('profile.json').read_text())['value']\n",
        )
        self.write("pkg/profile.json", '{"value":3}\n')
        self.write("pkg/core.py", "from .middle import VALUE\n")
        self.write("pkg/middle.py", "from .leaf import VALUE\n")
        self.write("pkg/leaf.py", "VALUE=4\n")
        self.commit()
        result = self.qualify()
        self.assertTrue(result["importability_qualified"], result)
        self.assertEqual(
            {x["path"] for x in result["files"]},
            {
                "pkg/__init__.py",
                "pkg/bootstrap.py",
                "pkg/profile.json",
                "pkg/core.py",
                "pkg/middle.py",
                "pkg/leaf.py",
            },
        )
        self.assertGreaterEqual(len(result["generations"]), 4)
        self.assertTrue(result["source_stability"]["stable"])
        self.assertFalse(result["runtime_closure_proven"])
        snapshot = Path(result["snapshot_root"])
        self.assertFalse((snapshot / "test/pkg/core.py").stat().st_mode & 0o222)
        loaded = result["per_seed"][0]["probe"]["resolved_local_modules"]
        self.assertTrue(
            all(not x["file"] or Path(x["file"]).is_relative_to(snapshot) for x in loaded)
        )

    def test_duplicate_and_stale_probe_payloads_refuse(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.commit()
        owner = self.owner()
        owner.demand_module("pkg.core", origin="seed")
        owner.seal()
        identity = owner.identity("pkg.core", "probe-0")
        result = {"request_identity": identity, "local_import_attempts": []}
        self.assertFalse(owner.receive(result, identity))
        with self.assertRaisesRegex(DemandError, "duplicate"):
            owner.receive(result, identity)
        owner.seal()
        with self.assertRaisesRegex(DemandError, "stale"):
            owner.receive(result, identity)
        wrong = owner.identity("pkg.core", "probe-1")
        with self.assertRaisesRegex(DemandError, "identity"):
            owner.receive({"request_identity": {**wrong, "seed": "pkg.other"}}, wrong)
        for invalid in (
            None,
            {**wrong, "generation": True},
            {**wrong, "extra": "field"},
            {k: v for k, v in wrong.items() if k != "seed"},
        ):
            with self.assertRaisesRegex(DemandError, "shape/types"):
                owner.receive({"request_identity": invalid}, wrong)

    def test_same_head_source_drift_refuses_new_generation(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.commit()
        owner = self.owner()
        owner.demand_module("pkg.core", origin="seed")
        owner.seal()
        self.write("pkg/core.py", "VALUE=2\n")
        self.assertFalse(owner.check_stability()["stable"])
        with self.assertRaisesRegex(DemandError, "source changed"):
            owner.seal()
        self.assertEqual(owner.generation, 0)

    def test_snapshot_tamper_and_unexpected_files_refuse(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.commit()
        owner = self.owner()
        owner.demand_module("pkg.core", origin="seed")
        owner.seal()
        file = owner.snapshot_root / "test/pkg/core.py"
        file.chmod(0o644)
        file.write_text("VALUE=9\n")
        with self.assertRaisesRegex(DemandError, "file identity"):
            owner.verify_snapshot()

    def test_byte_file_and_round_ceilings_remain_unresolved(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "from .middle import VALUE\n")
        self.write("pkg/middle.py", "from .leaf import VALUE\n")
        self.write("pkg/leaf.py", "VALUE=1\n")
        self.commit()
        result = self.qualify(max_rounds=1)
        self.assertEqual(result["disposition"], "round_limit")
        self.assertFalse(result["importability_qualified"])
        self.assertIn("round_limit", {x["disposition"] for x in result["frontier"]})
        byte_owner = self.owner(max_bytes=4)
        byte_owner.demand_module("pkg.core", origin="seed")
        self.assertLessEqual(byte_owner.total_bytes, 4)
        self.assertIn("byte_limit", {x["disposition"] for x in byte_owner.frontier})
        file_owner = self.owner(max_files=1)
        file_owner.demand_module("pkg.core", origin="seed")
        self.assertEqual(len(file_owner.closure.captured), 1)
        self.assertIn("file_limit", {x["disposition"] for x in file_owner.frontier})

    def test_isolation_external_environment_and_source_absence_are_separate(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "import qualification_missing_external\n")
        self.commit()
        result = self.qualify()
        self.assertFalse(result["importability_qualified"])
        self.assertEqual(result["per_seed"][0]["disposition"], "environment_unavailable")
        self.assertFalse(
            any(str(self.root) in x for x in result["per_seed"][0]["probe"]["isolated_sys_path"])
        )
        owner = self.owner()
        owner.demand_module("pkg.not_present", origin="probe")
        self.assertIn("absent_local_source", {x["disposition"] for x in owner.frontier})

    def test_non_python_and_asset_traversal_are_frontiers(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.write(
            "pkg/native" + __import__("importlib").machinery.EXTENSION_SUFFIXES[0],
            "not a real native module",
        )
        self.commit()
        owner = self.owner()
        owner.demand_module("pkg.core", origin="seed")
        owner.demand_module("pkg.native", origin="probe")
        owner.seal()
        self.assertIn(
            "non_python_local_module_unqualified", {x["disposition"] for x in owner.frontier}
        )
        owner.demand_asset(str(self.base / "outside.json"), origin="probe")
        self.assertIn("asset_request_outside_snapshot", {x["disposition"] for x in owner.frontier})
        owner.demand_asset(str(owner.snapshot_root / "test/.git/config.json"), origin="probe")
        self.assertIn("asset_outside_owned_package", {x["disposition"] for x in owner.frontier})

    def test_old_generation_remains_immutable_after_additive_capture(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.write("pkg/extra.py", "VALUE=2\n")
        self.commit()
        owner = self.owner()
        owner.demand_module("pkg.core", origin="seed")
        first = owner.seal()
        old = Path(first["snapshot_root"])
        old_manifest = (old / "snapshot.json").read_bytes()
        owner.demand_module("pkg.extra", origin="probe")
        second = owner.seal()
        self.assertEqual((old / "snapshot.json").read_bytes(), old_manifest)
        self.assertFalse((old / "test/pkg/extra.py").exists())
        self.assertTrue((Path(second["snapshot_root"]) / "test/pkg/extra.py").exists())
        self.assertEqual(
            json.loads((Path(second["snapshot_root"]) / "snapshot.json").read_text())[
                "parent_snapshot_sha256"
            ],
            first["snapshot_sha256"],
        )

    def test_pinned_initial_snapshot_replay_and_source_drift(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.commit()
        owner = self.owner()
        owner.demand_module("pkg.core", origin="seed")
        first = owner.seal()
        repo = Repository("test", self.root, ["pkg"])
        self.repos.append(repo)
        resumed = DemandOwner([repo], self.base / "resumed")
        resumed.load_initial(Path(first["snapshot_root"]), first["snapshot_sha256"])
        self.assertEqual(len(resumed.closure.captured), 2)
        self.assertEqual(resumed.closure.nodes[("test", "pkg/core.py")]["module"], "pkg.core")
        self.write("pkg/core.py", "VALUE=2\n")
        repo2 = Repository("test", self.root, ["pkg"])
        self.repos.append(repo2)
        drifted = DemandOwner([repo2], self.base / "drifted")
        with self.assertRaisesRegex(DemandError, "source drift"):
            drifted.load_initial(Path(first["snapshot_root"]), first["snapshot_sha256"])

    def test_unbound_timeout_is_retained_without_producer_identity_repair(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "VALUE=1\n")
        self.commit()
        with patch(
            "runtime_demand.probe_import",
            return_value={
                "module": "pkg.core",
                "disposition": "timeout",
                "snapshot_root": str(self.base / "unused"),
            },
        ):
            result = self.qualify()
        self.assertFalse(result["importability_qualified"])
        self.assertEqual(result["per_seed"][0]["disposition"], "unbound_probe_result")
        self.assertIsNone(result["per_seed"][0]["request_identity"])

    def test_explicit_ctypes_self_profile_imports_stdlib(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "import ctypes\n")
        self.commit()
        result = self.qualify(allow_ctypes_python_handle=True)
        self.assertTrue(result["importability_qualified"], result)
        self.assertEqual(
            result["per_seed"][0]["probe"]["allowed_native_handles"],
            [{"event": "ctypes.dlopen", "library": None, "scope": "current_process_python_api"}],
        )

    def test_ctypes_named_library_remains_denied_under_self_profile(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/core.py", "import ctypes\nctypes.CDLL('libc.so.6')\n")
        self.commit()
        result = self.qualify(allow_ctypes_python_handle=True)
        self.assertFalse(result["importability_qualified"])
        self.assertIn("ctypes.dlopen", result["per_seed"][0]["probe"]["error"])

    def test_static_nominations_preserve_provenance_and_skip_lazy_optional_scopes(self):
        self.write("pkg/__init__.py", "")
        self.write(
            "pkg/core.py",
            "from .middle import VALUE\ndef lazy():\n    from . import lazy_only\ntry:\n    from .optional import VALUE\nexcept ImportError:\n    pass\n",
        )
        self.write("pkg/middle.py", "from .leaf import VALUE\n")
        self.write("pkg/leaf.py", "VALUE=1\n")
        self.write("pkg/lazy_only.py", "VALUE=2\n")
        self.write("pkg/optional.py", "VALUE=3\n")
        self.commit()
        owner = self.owner()
        owner.demand_module("pkg.core", origin="seed")
        owner.nominate_eager_imports()
        paths = {path for _, path in owner.closure.captured}
        self.assertIn("pkg/leaf.py", paths)
        self.assertNotIn("pkg/lazy_only.py", paths)
        self.assertNotIn("pkg/optional.py", paths)
        self.assertTrue(owner.nominations)
        self.assertTrue(
            all(x["origin"].startswith("nominated_module_body:") for x in owner.nominations)
        )


if __name__ == "__main__":
    unittest.main()
