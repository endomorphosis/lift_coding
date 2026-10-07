"""Pure byte-contract mutation controls; no numerical owners or resource tools."""
import gzip
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

SOURCE = Path(__file__).with_name("audit_archive-r2.py")
SPEC = importlib.util.spec_from_file_location("private_archive_auditor", SOURCE)
AUDITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDITOR)


class ArchiveContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.archive = self.root / "evidence.tar.gz"
        self.body = b"saved authored output, not model execution\n"
        self.name = "owned/evidence.json"
        self.entry = {"path": self.name, "bytes": len(self.body), "sha256": hashlib.sha256(self.body).hexdigest()}
        (self.root / "owned").mkdir()
        (self.root / self.name).write_bytes(self.body)

    def write_archive(self, members=None, tail=b""):
        members = [(self.name, self.body, "file")] if members is None else members
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name, body, kind in members:
                member = tarfile.TarInfo(name)
                member.mode = 0o644
                member.mtime = 0
                if kind == "symlink":
                    member.type = tarfile.SYMTYPE
                    member.linkname = "other"
                    archive.addfile(member)
                else:
                    member.size = len(body)
                    archive.addfile(member, io.BytesIO(body))
        self.archive.write_bytes(gzip.compress(stream.getvalue() + tail, mtime=0))

    def verify(self, entries=None, **kwargs):
        return AUDITOR.verify_archive(self.archive, [self.entry] if entries is None else entries, self.root, ["owned"], **kwargs)

    def test_path_component_sort_matches_authentic_retainer(self):
        other = "owned/group.json"
        nested = "owned/group/evidence.json"
        body = b"nested retained file"
        (self.root / "owned/group").mkdir()
        (self.root / other).write_bytes(self.body)
        (self.root / nested).write_bytes(body)
        entries = [
            {"path": nested, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()},
            {"path": other, "bytes": len(self.body), "sha256": hashlib.sha256(self.body).hexdigest()},
        ]
        self.write_archive([(nested, body, "file"), (other, self.body, "file")])
        result = self.verify(entries)
        self.assertEqual(result["member_count"], 2)
        self.assertNotEqual([e["path"] for e in entries], sorted(e["path"] for e in entries))

    def test_complete_stream_hashes_and_source_match(self):
        self.write_archive()
        result = self.verify()
        self.assertEqual(result["member_count"], 1)
        self.assertEqual(result["source_bytes"], len(self.body))
        self.assertTrue(result["every_member_matches_current_source"])

    def test_wrong_payload_sha_refused(self):
        self.write_archive()
        with self.assertRaises(ValueError):
            self.verify([{**self.entry, "sha256": "0" * 64}])

    def test_wrong_payload_size_refused(self):
        self.write_archive()
        with self.assertRaises(ValueError):
            self.verify([{**self.entry, "bytes": len(self.body) + 1}])

    def test_duplicate_manifest_member_refused(self):
        self.write_archive()
        with self.assertRaises(ValueError):
            self.verify([self.entry, self.entry])

    def test_duplicate_tar_member_refused(self):
        self.write_archive([(self.name, self.body, "file")] * 2)
        with self.assertRaises(ValueError):
            self.verify()

    def test_traversal_name_refused(self):
        for name in ("owned/../foreign.json", "/owned/evidence.json", "owned//evidence.json", "owned/./evidence.json"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    AUDITOR.safe_name(name, ["owned"])

    def test_foreign_scope_refused(self):
        with self.assertRaises(ValueError):
            AUDITOR.safe_name("foreign/evidence.json", ["owned"])

    def test_tar_symlink_refused(self):
        self.write_archive([(self.name, b"", "symlink")])
        with self.assertRaises(ValueError):
            self.verify([{**self.entry, "bytes": 0}])

    def test_unexpected_tar_member_refused(self):
        self.write_archive([(self.name, self.body, "file"), ("owned/unmanifested.json", b"extra", "file")])
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_tar_member_refused(self):
        self.write_archive([])
        with self.assertRaises(ValueError):
            self.verify()

    def test_current_source_drift_refused(self):
        self.write_archive()
        (self.root / self.name).write_bytes(b"different current source")
        with self.assertRaises(ValueError):
            self.verify()

    def test_current_source_symlink_refused(self):
        self.write_archive()
        original = self.root / self.name
        original.unlink()
        original.symlink_to(self.root / "other.json")
        (self.root / "other.json").write_bytes(self.body)
        with self.assertRaises(ValueError):
            self.verify()

    def test_both_caps_enforced(self):
        self.write_archive()
        with self.assertRaises(ValueError):
            self.verify(max_archive=1)
        with self.assertRaises(ValueError):
            self.verify(max_source=1)

    def test_nonzero_gzip_tail_refused(self):
        self.write_archive(tail=b"nonzero appended payload")
        with self.assertRaises(ValueError):
            self.verify()

    def test_gzip_footer_corruption_refused(self):
        self.write_archive()
        data = bytearray(self.archive.read_bytes())
        data[-5] ^= 0x7F
        self.archive.write_bytes(data)
        with self.assertRaises((ValueError, OSError, EOFError)):
            self.verify()

    def test_manifest_member_schema_and_digest_refused(self):
        self.write_archive()
        for entry in ({**self.entry, "extra": True}, {**self.entry, "sha256": "g" * 64}, {**self.entry, "bytes": True}):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError):
                    self.verify([entry])


if __name__ == "__main__":
    unittest.main()
