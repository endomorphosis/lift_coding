"""The recovery canary checker only reads an exact scoped regular JSON fixture."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import svf_recovery_canary as canary


class CanaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.relative = "data/agent_supervisor/swissknife_visual_functional/watchdog/canary/fixture.json"
        self.fixture = self.root / self.relative
        self.fixture.parent.mkdir(parents=True)

    def verify(self):
        return canary.verify_fixture(self.relative, root=self.root)

    def test_exact_state_passes_without_modifying_fixture_or_granting_authority(self):
        raw = b'{"recovery_state":"repaired_by_scoped_model"}\n'
        self.fixture.write_bytes(raw)
        before = self.fixture.stat()
        result = self.verify()
        after = self.fixture.stat()
        self.assertTrue(result["verified"])
        self.assertTrue(result["read_only"])
        self.assertFalse(result["work_complete"])
        self.assertFalse(result["completion_authority"])
        self.assertFalse(result["gui_acceptance"])
        self.assertEqual(self.fixture.read_bytes(), raw)
        self.assertEqual((before.st_ino, before.st_mtime_ns, before.st_size), (after.st_ino, after.st_mtime_ns, after.st_size))
        self.assertEqual(sorted(p.name for p in self.fixture.parent.iterdir()), ["fixture.json"])

    def test_pending_other_types_extra_fields_and_duplicate_fields_fail(self):
        for raw in ['{"recovery_state":"pending"}', '{}', '[]', 'true', 'null',
                    '{"recovery_state":"repaired_by_scoped_model","extra":true}',
                    '{"recovery_state":"pending","recovery_state":"repaired_by_scoped_model"}',
                    '{"recovery_state":NaN}', '{"recovery_state":1}', 'not JSON']:
            self.fixture.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(canary.CanaryError):
                self.verify()
            self.assertEqual(self.fixture.read_text(), raw)

    def test_absolute_other_namespace_traversal_and_non_json_paths_fail(self):
        for value in [str(self.fixture), "data/agent_supervisor/other/fixture.json",
                      "data/agent_supervisor/swissknife_visual_functional/../other/fixture.json",
                      self.relative.replace("/watchdog/", "/./watchdog/"), self.relative + ".txt",
                      self.relative.replace("/watchdog/", "//watchdog/"), self.relative.replace("/", "\\")]:
            with self.subTest(value=value), self.assertRaises(canary.CanaryError):
                canary.verify_fixture(value, root=self.root)

    def test_missing_and_oversized_files_fail(self):
        with self.assertRaises(OSError):
            self.verify()
        self.fixture.write_bytes(b" " * (canary.MAX_FIXTURE_BYTES + 1))
        with self.assertRaises(canary.CanaryError):
            self.verify()

    def test_file_and_parent_symlinks_fail_even_inside_runtime(self):
        real = self.fixture.with_name("real.json")
        real.write_text(json.dumps(canary.EXPECTED_STATE))
        self.fixture.symlink_to(real)
        with self.assertRaises(OSError):
            self.verify()
        self.fixture.unlink()
        self.fixture.parent.rmdir() if not list(self.fixture.parent.iterdir()) else None
        parent_link = self.fixture.parent.with_name("linked")
        parent_link.symlink_to(self.fixture.parent, target_is_directory=True)
        with self.assertRaises(OSError):
            canary.verify_fixture(self.relative.replace("/canary/", "/linked/").replace("fixture.json", "real.json"), root=self.root)

    def test_fifo_is_rejected_without_blocking(self):
        os.mkfifo(self.fixture)
        with self.assertRaises(canary.CanaryError):
            self.verify()

    def test_renamed_parent_detected_from_anchored_file_descriptor(self):
        self.fixture.write_text(json.dumps(canary.EXPECTED_STATE))
        with patch.object(canary.os, "readlink", return_value=str(self.root / "foreign/fixture.json")):
            with self.assertRaisesRegex(canary.CanaryError, "path changed"):
                self.verify()

    def test_cli_requires_verify_and_reports_failure_without_mutation(self):
        self.fixture.write_text('{"recovery_state":"pending"}')
        with patch.object(canary, "verify_fixture", side_effect=canary.CanaryError("pending")):
            self.assertEqual(canary.main(["--verify", "--fixture", self.relative]), 1)
        self.assertEqual(self.fixture.read_text(), '{"recovery_state":"pending"}')


if __name__ == "__main__":
    unittest.main()
