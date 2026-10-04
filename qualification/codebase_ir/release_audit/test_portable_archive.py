from __future__ import annotations

import copy
import io
import os
import shutil
import stat
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portable_archive as archive
import portable_review as portable
import release_matrix as matrix
import test_portable_review as fixtures


class PortableArchiveTests(unittest.TestCase):
    def setUp(self):
        self.factory = fixtures.PortableReviewTests("runTest")
        self.factory.setUp()
        self.addCleanup(self.factory.doCleanups)
        self.root = self.factory.root
        self.bundle, self.identity = self.factory.build()
        self.sequence = 0
        self.inputs = self.root / "archive_inputs"
        self.inputs.mkdir()
        self.build_spec = self.inputs / "build.json"
        self.build_spec.write_bytes(matrix.json_bytes({"schema": archive.BUILD_INPUT_SCHEMA,
            "bundle_root": str(self.bundle), "bundle_manifest_sha256": self.identity}))

    def build(self):
        self.sequence += 1
        output = self.root / f"archive-build-{self.sequence}"
        report = archive.build(self.build_spec, output)
        return output, report

    def verify(self, manifest):
        self.sequence += 1
        output = self.root / f"archive-verify-{self.sequence}"
        self.addCleanup(self.factory.unseal, output / "bundle")
        return archive.verify(manifest, output)

    def altered(self, output, mutate):
        spec = matrix.document((output / "archive_input.json").read_bytes())
        original = Path(spec["archive"]["path"]).read_bytes()
        raw = mutate(original)
        self.sequence += 1
        path = self.inputs / f"altered-{self.sequence}.zip"
        path.write_bytes(raw)
        spec["archive"] = {"path": str(path), "sha256": matrix.sha(raw), "size_bytes": len(raw)}
        manifest = self.inputs / f"altered-{self.sequence}.json"
        manifest.write_bytes(matrix.json_bytes(spec))
        return manifest

    @staticmethod
    def rewrite(raw, mutate):
        entries = archive.decode(raw)
        mutate(entries)
        return archive.encode(entries)

    def test_deterministic_standard_zip_and_exact_roundtrip(self):
        first, report = self.build()
        second, other = self.build()
        raw = (first / "portable_review.zip").read_bytes()
        self.assertEqual(raw, (second / "portable_review.zip").read_bytes())
        self.assertEqual(report["archive_sha256"], other["archive_sha256"])
        with zipfile.ZipFile(io.BytesIO(raw)) as standard:
            self.assertIsNone(standard.testzip())
            self.assertTrue(all(row.compress_type == zipfile.ZIP_STORED for row in standard.infolist()))
            self.assertTrue(all(row.date_time == (1980, 1, 1, 0, 0, 0) for row in standard.infolist()))
        restored = self.verify(first / "archive_input.json")
        self.assertTrue(restored["archive_roundtrip_verified"])
        self.assertTrue(restored["portable_scope_complete"])
        self.assertEqual(restored["source_dispositions"], {"identical": 1})
        self.assertEqual(restored["evidence_dispositions"], {"identical": 1})
        self.assertTrue(all(restored[flag] is False for flag in archive.FALSE_FLAGS))
        root = Path(restored["restored_bundle"])
        self.assertEqual((root / portable.MANIFEST_FILENAME).read_bytes(), (self.bundle / portable.MANIFEST_FILENAME).read_bytes())
        for path in [root, *root.rglob("*")]:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o555 if path.is_dir() else 0o444)

    def test_roundtrip_without_original_bundle_owner_sources_git_or_process(self):
        output, _report = self.build()
        self.factory.unseal(self.bundle)
        shutil.rmtree(self.bundle)
        shutil.rmtree(self.factory.factory.repo)
        shutil.rmtree(self.factory.factory.current.parent)
        shutil.rmtree(self.factory.factory.retained.parent)
        self.factory.spec.unlink()
        self.factory.report.unlink()
        with patch.object(matrix.shutil, "which", side_effect=AssertionError("Git lookup forbidden")), patch.object(subprocess, "Popen", side_effect=AssertionError("subprocess forbidden")):
            result = self.verify(output / "archive_input.json")
        self.assertFalse(result["original_paths_read"])
        self.assertFalse(result["git_executable_invoked"])

    def test_missing_source_disposition_is_preserved(self):
        source = self.factory.factory.spec["source_profiles"][0]["files"][0]
        source["path"] = "pkg/missing.py"
        self.factory.factory.write_spec()
        self.factory.report.write_bytes(matrix.json_bytes(matrix.reconcile(self.factory.spec)))
        self.bundle, self.identity = self.factory.build()
        self.build_spec.write_bytes(matrix.json_bytes({"schema": archive.BUILD_INPUT_SCHEMA,
            "bundle_root": str(self.bundle), "bundle_manifest_sha256": self.identity}))
        output, _report = self.build()
        self.assertEqual(self.verify(output / "archive_input.json")["source_dispositions"], {"missing": 1})

    def test_external_archive_and_bundle_pins_are_independent(self):
        output, _report = self.build()
        original = matrix.document((output / "archive_input.json").read_bytes())
        for mutation in (lambda value: value["archive"].__setitem__("sha256", "a" * 64),
                         lambda value: value["archive"].__setitem__("size_bytes", value["archive"]["size_bytes"] + 1),
                         lambda value: value.__setitem__("bundle_manifest_sha256", "b" * 64)):
            spec = copy.deepcopy(original)
            mutation(spec)
            manifest = self.inputs / "bad-pin.json"
            manifest.write_bytes(matrix.json_bytes(spec))
            with self.assertRaises(ValueError):
                self.verify(manifest)

    def test_closed_input_schema_boolean_counts_and_duplicate_json_refused(self):
        output, _report = self.build()
        original = matrix.document((output / "archive_input.json").read_bytes())
        for mutation in (lambda value: value.__setitem__("extra", True),
                         lambda value: value["archive"].__setitem__("size_bytes", True),
                         lambda value: value["archive"].__setitem__("extra", 0)):
            spec = copy.deepcopy(original)
            mutation(spec)
            manifest = self.inputs / "bad-type.json"
            manifest.write_bytes(matrix.json_bytes(spec))
            with self.assertRaises(ValueError):
                self.verify(manifest)
        manifest.write_bytes(b'{"schema": 1, "schema": 2}')
        with self.assertRaises(ValueError):
            self.verify(manifest)

    def test_count_and_central_bounds_precede_member_decode(self):
        raw = archive.encode({"a": b"a"})
        values = list(archive.END.unpack_from(raw, len(raw) - archive.END.size))
        for position, value in ((3, archive.MAX_ENTRIES + 1), (4, archive.MAX_ENTRIES + 1),
                                (5, archive.MAX_CENTRAL_BYTES + 1), (6, 0xffffffff)):
            changed = values.copy()
            changed[position] = value
            with patch.object(archive, "name", side_effect=AssertionError("name allocation before EOCD bounds")), self.assertRaises(ValueError):
                archive.decode(raw[:-archive.END.size] + archive.END.pack(*changed))

    def test_trailing_garbage_comments_padding_and_prepended_data_refused(self):
        raw = archive.encode({"a": b"abc"})
        for changed in (raw + b"trailing", b"prefix" + raw, raw[:-archive.END.size] + b"padding" + raw[-archive.END.size:]):
            with self.assertRaises(ValueError):
                archive.decode(changed)
        values = list(archive.END.unpack_from(raw, len(raw) - archive.END.size))
        values[-1] = 1
        with self.assertRaises(ValueError):
            archive.decode(raw[:-archive.END.size] + archive.END.pack(*values))

    def test_central_encryption_compression_zip64_modes_and_optional_records_refused(self):
        raw = archive.encode({"a": b"abc"})
        central_offset = archive.END.unpack_from(raw, len(raw) - archive.END.size)[6]
        original = list(archive.CENTRAL.unpack_from(raw, central_offset))
        for index, value in ((3, 0x801), (4, 8), (2, 45), (8, 0xffffffff), (9, 0xffffffff),
                             (11, 1), (12, 1), (13, 1), (14, 1),
                             (15, (stat.S_IFLNK | 0o444) << 16),
                             (15, (stat.S_IFIFO | 0o444) << 16),
                             (15, (stat.S_IFREG | 0o644) << 16)):
            values = original.copy()
            values[index] = value
            changed = raw[:central_offset] + archive.CENTRAL.pack(*values) + raw[central_offset + archive.CENTRAL.size:]
            with self.assertRaises(ValueError):
                archive.decode(changed)

    def test_local_header_name_crc_and_payload_corruption_refused(self):
        raw = archive.encode({"a": b"abc"})
        for position in (4, 6, 14, archive.LOCAL.size, archive.LOCAL.size + 1):
            changed = bytearray(raw)
            changed[position] ^= 1
            with self.assertRaises(ValueError):
                archive.decode(bytes(changed))

    def test_duplicate_unsorted_and_local_offset_aliases_refused(self):
        raw = archive.encode({"a": b"a", "b": b"b"})
        central = archive.END.unpack_from(raw, len(raw) - archive.END.size)[6]
        second = central + archive.CENTRAL.size + 1
        for change in ("duplicate", "unsorted", "offset"):
            altered = bytearray(raw)
            values = list(archive.CENTRAL.unpack_from(raw, second))
            if change in ("duplicate", "unsorted"):
                altered[second + archive.CENTRAL.size] = ord("a" if change == "duplicate" else "0")
            else:
                values[-1] = 0
                altered[second:second + archive.CENTRAL.size] = archive.CENTRAL.pack(*values)
            with self.assertRaises(ValueError):
                archive.decode(bytes(altered))

    def test_absolute_traversal_platform_controls_and_deep_names_refused(self):
        for relative in ("/escape", "../escape", "a/../escape", "a\\escape", "C:escape", "a\x00b", "a\nb", "/".join(["a"] * 33)):
            with self.assertRaises(ValueError):
                archive.encode({relative: b"bad"})
        # Use standard writer to ensure unsafe names also refuse at decode.
        for relative in ("../escape", "a\\escape", "C:escape"):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as standard:
                item = zipfile.ZipInfo(relative, (1980, 1, 1, 0, 0, 0))
                item.create_system = 3
                item.external_attr = (stat.S_IFREG | 0o444) << 16
                standard.writestr(item, b"bad")
            with self.assertRaises(ValueError):
                archive.decode(stream.getvalue())

    def test_extra_file_empty_directory_and_missing_body_refused(self):
        output, _report = self.build()
        mutations = (lambda entries: entries.__setitem__("unselected", b"bad"),
                     lambda entries: entries.__setitem__("unselected/", b""),
                     lambda entries: entries.pop(next(value for value in entries if value.startswith("git_objects/") and not value.endswith("/"))))
        for mutation in mutations:
            manifest = self.altered(output, lambda raw, mutation=mutation: self.rewrite(raw, mutation))
            with self.assertRaises(ValueError):
                self.verify(manifest)

    def test_recomputed_crc_and_archive_hash_cannot_hide_selected_body_change(self):
        output, _report = self.build()
        def change(entries):
            relative = next(value for value in entries if value.startswith("git_objects/") and not value.endswith("/"))
            entries[relative] += b"corrupt"
        manifest = self.altered(output, lambda raw: self.rewrite(raw, change))
        with self.assertRaises(ValueError):
            self.verify(manifest)

    def test_archive_body_file_population_and_manifest_budgets_refused(self):
        output, _report = self.build()
        manifest = output / "archive_input.json"
        with patch.object(archive, "MAX_ARCHIVE_BYTES", 100), self.assertRaises(ValueError):
            self.verify(manifest)
        with patch.object(archive, "MAX_MANIFEST_BYTES", 10), self.assertRaises(ValueError):
            self.verify(manifest)
        with patch.object(portable, "MAX_FILES", 1), self.assertRaises(ValueError):
            self.verify(manifest)
        with patch.object(matrix, "MAX_FILE_BYTES", 1), self.assertRaises(ValueError):
            self.verify(manifest)
        with patch.object(portable, "MAX_BYTES", 1), self.assertRaises(ValueError):
            self.verify(manifest)

    def test_output_scopes_existing_and_alias_refused_before_writes(self):
        output, _report = self.build()
        manifest = output / "archive_input.json"
        for target in (output / "bad", self.factory.factory.repo / "bad", self.factory.factory.retained.parent / "bad", self.bundle / "bad"):
            with self.assertRaises(ValueError):
                archive.verify(manifest, target)
            self.assertFalse(target.exists())
        alias = self.root / "output-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            archive.verify(manifest, alias / "bad")
        with self.assertRaises(ValueError):
            archive.verify(manifest, output)
        for target in (self.factory.factory.repo / "bad-build", self.factory.factory.retained.parent / "bad-build", self.bundle / "bad-build"):
            with self.assertRaises(ValueError):
                archive.build(self.build_spec, target)
            self.assertFalse(target.exists())

    def test_symlink_fifo_manifest_archive_and_source_seals_refused(self):
        output, _report = self.build()
        original = matrix.document((output / "archive_input.json").read_bytes())
        for kind in ("symlink", "fifo"):
            path = self.inputs / kind
            if kind == "symlink":
                path.symlink_to(original["archive"]["path"])
            else:
                os.mkfifo(path)
            spec = copy.deepcopy(original)
            spec["archive"]["path"] = str(path)
            manifest = self.inputs / f"{kind}.json"
            manifest.write_bytes(matrix.json_bytes(spec))
            with self.assertRaises(ValueError):
                self.verify(manifest)
        self.bundle.chmod(0o755)
        with self.assertRaises(ValueError):
            self.build()
        self.bundle.chmod(0o555)
        (self.bundle / portable.MANIFEST_FILENAME).chmod(0o544)
        with self.assertRaises(ValueError):
            self.build()

    def test_late_archive_or_input_manifest_drift_refuses_report(self):
        for which in ("archive", "manifest"):
            output, _report = self.build()
            manifest = output / "archive_input.json"
            original = portable.verify
            def mutate(*args, which=which, original=original, output=output, manifest=manifest, **kwargs):
                result = original(*args, **kwargs)
                target = output / "portable_review.zip" if which == "archive" else manifest
                target.chmod(0o644)
                target.write_bytes(target.read_bytes() + b" ")
                return result
            with patch.object(portable, "verify", mutate), self.assertRaises(ValueError):
                self.verify(manifest)

    def test_late_restored_byte_directory_or_permission_drift_refuses_report(self):
        for operation in ("body", "directory", "permission"):
            output, _report = self.build()
            original = archive.PinnedReader.stability
            touched = set()
            def mutate(reader, operation=operation, original=original, touched=touched):
                result = original(reader)
                roots = sorted(self.root.glob("archive-verify-*/bundle"))
                root = roots[-1]
                if root in touched:
                    return result
                touched.add(root)
                if operation == "body":
                    path = root / portable.MANIFEST_FILENAME
                    path.chmod(0o644)
                    path.write_bytes(path.read_bytes() + b" ")
                    path.chmod(0o444)
                elif operation == "directory":
                    root.chmod(0o755)
                    extra = root / "late-extra"
                    extra.mkdir()
                    extra.chmod(0o555)
                    root.chmod(0o555)
                else:
                    (root / "tools").chmod(0o755)
                return result
            with patch.object(archive.PinnedReader, "stability", mutate), self.assertRaises(ValueError):
                self.verify(output / "archive_input.json")

    def test_build_input_digest_and_source_capture_drift_refused(self):
        spec = matrix.document(self.build_spec.read_bytes())
        spec["bundle_manifest_sha256"] = "a" * 64
        self.build_spec.write_bytes(matrix.json_bytes(spec))
        with self.assertRaises(ValueError):
            self.build()
        spec["bundle_manifest_sha256"] = self.identity
        self.build_spec.write_bytes(matrix.json_bytes(spec))
        original = archive.encode
        def drift(entries):
            result = original(entries)
            path = self.bundle / portable.MANIFEST_FILENAME
            path.chmod(0o644)
            path.write_bytes(path.read_bytes() + b" ")
            path.chmod(0o444)
            return result
        with patch.object(archive, "encode", drift), self.assertRaises(ValueError):
            self.build()

    def test_late_build_manifest_drift_before_report_refused(self):
        original = archive.exact_seals
        calls = 0
        def drift(*args):
            nonlocal calls
            result = original(*args)
            calls += 1
            if calls == 3:
                self.build_spec.write_bytes(self.build_spec.read_bytes() + b" ")
            return result
        with patch.object(archive, "exact_seals", drift), self.assertRaises(ValueError):
            self.build()

    def test_retained_manifest_can_share_parent_with_fresh_runner_destination(self):
        output, _report = self.build()
        retained = self.root / "retained-archive-input.json"
        retained.write_bytes((output / "archive_input.json").read_bytes())
        result = self.verify(retained)
        self.assertTrue(result["archive_roundtrip_verified"])


if __name__ == "__main__":
    unittest.main()
