"""Authored-file custody and byte-observation refusal controls."""

import base64
import copy
import hashlib
import os
from pathlib import Path
import stat

import pytest

import observed_files as observed


@pytest.fixture
def bundle_root(tmp_path):
    root = tmp_path / "authored"
    root.mkdir(mode=0o700)
    for directory in observed.DIRECTORY_PATHS:
        (root / directory).mkdir(mode=0o700)
    for number, path in enumerate(observed.FILE_PATHS):
        (root / path).write_bytes(("{\"case\":%d}\n" % number).encode("ascii"))
    return root


def test_four_owned_exact_files_roundtrip_and_current_reobserve(bundle_root):
    before = observed.observe_bundle(root=bundle_root)
    assert observed.validate_bundle(before) is None
    assert tuple(before["files"]) == observed.FILE_PATHS
    for path in observed.FILE_PATHS:
        assert observed.decode_file(before, path) == (bundle_root / path).read_bytes()
        assert before["files"][path]["identity"]["uid"] == os.geteuid()
        assert before["files"][path]["identity"]["nlink"] == 1
    after = observed.reobserve_bundle(before, root=bundle_root)
    comparison = observed.compare_bundles(before, after)
    assert comparison["same_file_generations"] is True
    assert comparison["unchanged_inputs"] is True
    assert comparison["inputs_bytes_equal"] is True
    assert after["claims"]["current_authority"] is False
    assert after["claims"]["formal_proof"] is False


def test_invalid_utf8_is_retained_as_exact_bytes(bundle_root):
    path = observed.INPUT_PATHS[0]
    raw = b'{"bad":"\xff\x00"}\r\n'
    (bundle_root / path).write_bytes(raw)
    report = observed.observe_bundle(root=bundle_root)
    assert observed.decode_file(report, path) == raw
    assert report["files"][path]["payload_b64"] == base64.b64encode(raw).decode("ascii")


@pytest.mark.parametrize("size", [0, 65_536])
def test_empty_and_exact_maximum_byte_lengths(bundle_root, size):
    path = observed.OUTPUT_PATHS[1]
    (bundle_root / path).write_bytes(b"x" * size)
    report = observed.observe_bundle(root=bundle_root)
    assert len(observed.decode_file(report, path)) == size


def test_oversize_refused_without_read(bundle_root, monkeypatch):
    (bundle_root / observed.FILE_PATHS[0]).write_bytes(b"x" * 65_537)
    monkeypatch.setattr(observed, "_read_bytes", lambda fd: pytest.fail("oversize read"))
    with pytest.raises(observed.ObservationError, match="byte bound"):
        observed.observe_bundle(root=bundle_root)


def test_same_bytes_replacement_is_not_same_generation(bundle_root):
    before = observed.observe_bundle(root=bundle_root)
    path = bundle_root / observed.INPUT_PATHS[0]
    raw = path.read_bytes()
    staged = bundle_root.parent / "replacement"
    staged.write_bytes(raw)
    staged.replace(path)
    after = observed.observe_bundle(root=bundle_root)
    comparison = observed.compare_bundles(before, after)
    assert comparison["inputs_bytes_equal"] is True
    assert comparison["unchanged_inputs"] is False
    assert comparison["same_file_generations"] is False
    assert comparison["files"][observed.INPUT_PATHS[0]]["identity_equal"] is False
    with pytest.raises(observed.ObservationError, match="generation"):
        observed.reobserve_bundle(before, root=bundle_root)


def test_same_size_edit_and_restore_mtime_still_changes_ctime(bundle_root):
    before = observed.observe_bundle(root=bundle_root)
    path = bundle_root / observed.INPUT_PATHS[0]
    original = path.read_bytes()
    timestamp = path.stat()
    path.write_bytes(b"z" * len(original))
    path.write_bytes(original)
    os.utime(path, ns=(timestamp.st_atime_ns, timestamp.st_mtime_ns))
    after = observed.observe_bundle(root=bundle_root)
    comparison = observed.compare_bundles(before, after)
    assert comparison["inputs_bytes_equal"] is True
    assert comparison["files"][observed.INPUT_PATHS[0]]["identity_equal"] is False
    assert comparison["unchanged_inputs"] is False
    with pytest.raises(observed.ObservationError):
        observed.reobserve_bundle(before, root=bundle_root)


def test_output_change_keeps_input_distinction_but_invalidates_bracket(bundle_root):
    before = observed.observe_bundle(root=bundle_root)
    (bundle_root / observed.OUTPUT_PATHS[0]).write_bytes(b'{"changed":true}\n')
    after = observed.observe_bundle(root=bundle_root)
    comparison = observed.compare_bundles(before, after)
    assert comparison["unchanged_inputs"] is True
    assert comparison["same_file_generations"] is False
    assert comparison["files"][observed.OUTPUT_PATHS[0]]["bytes_equal"] is False
    with pytest.raises(observed.ObservationError):
        observed.reobserve_bundle(before, root=bundle_root)


@pytest.mark.parametrize("location", ["root", "input_data", "output_data"])
def test_unknown_leaf_is_refused_without_opening_it(bundle_root, location):
    directory = bundle_root if location == "root" else bundle_root / location
    (directory / "unknown-leaf").write_bytes(b"not read")
    with pytest.raises(observed.ObservationError, match="unknown leaf"):
        observed.observe_bundle(root=bundle_root)


@pytest.mark.parametrize("path", observed.FILE_PATHS)
def test_missing_file_refused(bundle_root, path):
    (bundle_root / path).unlink()
    with pytest.raises(observed.ObservationError):
        observed.observe_bundle(root=bundle_root)


@pytest.mark.parametrize("path", observed.FILE_PATHS)
def test_symlink_leaf_refused(bundle_root, path):
    leaf = bundle_root / path
    target = bundle_root.parent / "outside-target"
    target.write_bytes(leaf.read_bytes())
    leaf.unlink()
    leaf.symlink_to(target)
    with pytest.raises(observed.ObservationError, match="regular file"):
        observed.observe_bundle(root=bundle_root)


@pytest.mark.parametrize("directory", observed.DIRECTORY_PATHS)
def test_symlink_required_parent_refused(bundle_root, directory):
    outside = bundle_root.parent / "detached-directory"
    (bundle_root / directory).rename(outside)
    (bundle_root / directory).symlink_to(outside, target_is_directory=True)
    with pytest.raises(observed.ObservationError, match="path component"):
        observed.observe_bundle(root=bundle_root)


def test_symlink_root_refused(bundle_root):
    alias = bundle_root.parent / "alias"
    alias.symlink_to(bundle_root, target_is_directory=True)
    with pytest.raises(observed.ObservationError, match="path component"):
        observed.observe_bundle(root=alias)


def test_symlink_ancestor_refused(bundle_root):
    alias = bundle_root.parent.parent / (bundle_root.parent.name + "-alias")
    alias.symlink_to(bundle_root.parent, target_is_directory=True)
    with pytest.raises(observed.ObservationError, match="path component"):
        observed.observe_bundle(root=alias / bundle_root.name)


def test_hardlink_file_refused(bundle_root):
    os.link(bundle_root / observed.FILE_PATHS[0], bundle_root.parent / "second-link")
    with pytest.raises(observed.ObservationError, match="one link"):
        observed.observe_bundle(root=bundle_root)


def test_fifo_refused_before_open_and_without_blocking(bundle_root, monkeypatch):
    leaf = bundle_root / observed.FILE_PATHS[0]
    leaf.unlink()
    os.mkfifo(leaf)
    original_open = os.open

    def guarded_open(path, flags, *args, **kwargs):
        assert path != leaf.name, "FIFO must be refused before open"
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", guarded_open)
    with pytest.raises(observed.ObservationError, match="regular file"):
        observed.observe_bundle(root=bundle_root)


def test_regular_to_fifo_open_race_uses_nonblocking_and_refuses(bundle_root, monkeypatch):
    leaf = bundle_root / observed.FILE_PATHS[0]
    original_open = os.open
    raced = False

    def racing_open(path, flags, *args, **kwargs):
        nonlocal raced
        if path == leaf.name and not raced:
            raced = True
            assert flags & os.O_NONBLOCK
            leaf.unlink()
            os.mkfifo(leaf)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", racing_open)
    with pytest.raises(observed.ObservationError, match="regular file"):
        observed.observe_bundle(root=bundle_root)
    assert raced


def test_directory_in_place_of_file_refused(bundle_root):
    leaf = bundle_root / observed.FILE_PATHS[0]
    leaf.unlink()
    leaf.mkdir()
    with pytest.raises(observed.ObservationError, match="regular file"):
        observed.observe_bundle(root=bundle_root)


@pytest.mark.parametrize("root", ["relative", "/", "/tmp/../tmp", "//tmp"])
def test_noncanonical_root_refused(root):
    with pytest.raises(observed.ObservationError, match="canonical"):
        observed.observe_bundle(root=root)


def test_mutation_during_read_is_refused(bundle_root, monkeypatch):
    original_read = observed._read_bytes
    leaf = bundle_root / observed.FILE_PATHS[0]
    changed = False

    def mutation(fd):
        nonlocal changed
        raw = original_read(fd)
        if not changed:
            changed = True
            leaf.write_bytes(b"z" * len(raw))
        return raw

    monkeypatch.setattr(observed, "_read_bytes", mutation)
    with pytest.raises(observed.ObservationError, match="generation"):
        observed.observe_bundle(root=bundle_root)
    assert changed


def test_earlier_file_changes_while_later_file_read_is_refused(bundle_root, monkeypatch):
    original_read = observed._read_bytes
    leaf = bundle_root / observed.FILE_PATHS[0]
    reads = 0

    def mutation(fd):
        nonlocal reads
        reads += 1
        raw = original_read(fd)
        if reads == 4:
            original = leaf.read_bytes()
            leaf.write_bytes(b"x" * len(original))
            leaf.write_bytes(original)
        return raw

    monkeypatch.setattr(observed, "_read_bytes", mutation)
    with pytest.raises(observed.ObservationError, match="generation"):
        observed.observe_bundle(root=bundle_root)


def test_same_bytes_replacement_during_read_is_refused(bundle_root, monkeypatch):
    original_read = observed._read_bytes
    leaf = bundle_root / observed.FILE_PATHS[0]
    replaced = False

    def mutation(fd):
        nonlocal replaced
        raw = original_read(fd)
        if not replaced:
            replaced = True
            other = bundle_root.parent / "read-race-replacement"
            other.write_bytes(raw)
            other.replace(leaf)
        return raw

    monkeypatch.setattr(observed, "_read_bytes", mutation)
    with pytest.raises(observed.ObservationError, match="generation"):
        observed.observe_bundle(root=bundle_root)


def test_file_growth_during_read_is_bounded(bundle_root, monkeypatch):
    original_read = observed._read_bytes
    leaf = bundle_root / observed.FILE_PATHS[0]
    changed = False

    def mutation(fd):
        nonlocal changed
        if not changed:
            changed = True
            with leaf.open("ab") as stream:
                stream.write(b"x" * 65_537)
        return original_read(fd)

    monkeypatch.setattr(observed, "_read_bytes", mutation)
    with pytest.raises(observed.ObservationError, match="byte bound"):
        observed.observe_bundle(root=bundle_root)


def test_parent_inventory_mutation_during_read_is_refused(bundle_root, monkeypatch):
    original_read = observed._read_bytes
    changed = False

    def mutation(fd):
        nonlocal changed
        raw = original_read(fd)
        if not changed:
            changed = True
            (bundle_root / "input_data" / "transient").write_bytes(b"unread")
        return raw

    monkeypatch.setattr(observed, "_read_bytes", mutation)
    with pytest.raises(observed.ObservationError, match="unknown leaf"):
        observed.observe_bundle(root=bundle_root)


def test_root_replacement_during_read_is_refused(bundle_root, monkeypatch):
    original_read = observed._read_bytes
    changed = False

    def mutation(fd):
        nonlocal changed
        raw = original_read(fd)
        if not changed:
            changed = True
            bundle_root.rename(bundle_root.parent / "retained-old-root")
            bundle_root.mkdir()
        return raw

    monkeypatch.setattr(observed, "_read_bytes", mutation)
    with pytest.raises(observed.ObservationError, match="generation"):
        observed.observe_bundle(root=bundle_root)


def test_serialized_dict_can_only_prove_internal_bytes_not_current_disk(bundle_root):
    before = observed.observe_bundle(root=bundle_root)
    forged = copy.deepcopy(before)
    path = observed.INPUT_PATHS[0]
    raw = b"z" * forged["files"][path]["bytes"]
    forged["files"][path]["payload_b64"] = base64.b64encode(raw).decode("ascii")
    forged["files"][path]["sha256"] = hashlib.sha256(raw).hexdigest()
    # Internal consistency deliberately permits authored, unauthenticated evidence.
    assert observed.validate_bundle(forged) is None
    assert observed.compare_bundles(forged, forged)["same_file_generations"] is True
    with pytest.raises(observed.ObservationError, match="generation"):
        observed.reobserve_bundle(forged, root=bundle_root)


@pytest.mark.parametrize("mutation", [
    lambda report: report.update(unexpected=True),
    lambda report: report.update(root=Path(report["root"])),
    lambda report: report["files"].pop(observed.FILE_PATHS[0]),
    lambda report: report["files"].update({"../outside": {}}),
    lambda report: report["files"][observed.FILE_PATHS[0]].update(bytes=True),
    lambda report: report["files"][observed.FILE_PATHS[0]].update(sha256="0" * 64),
    lambda report: report["files"][observed.FILE_PATHS[0]].update(payload_b64="!"),
    lambda report: report["files"][observed.FILE_PATHS[0]].update(payload_b64="é"),
    lambda report: report["files"][observed.FILE_PATHS[0]]["identity"].update(nlink=2),
    lambda report: report["files"][observed.FILE_PATHS[0]]["identity"].update(uid=True),
    lambda report: report["files"][observed.FILE_PATHS[0]]["identity"].update(mode=stat.S_IFIFO),
    lambda report: report["observer"].update(pid=0),
    lambda report: report["claims"].update(current_authority=True),
    lambda report: report["claims"].update(formal_proof=0),
])
def test_malformed_evidence_refused(bundle_root, mutation):
    report = observed.observe_bundle(root=bundle_root)
    mutation(report)
    with pytest.raises(observed.ObservationError):
        observed.validate_bundle(report)


def test_noncanonical_base64_pad_bits_refused(bundle_root):
    path = observed.FILE_PATHS[0]
    (bundle_root / path).write_bytes(b"a")
    report = observed.observe_bundle(root=bundle_root)
    report["files"][path]["payload_b64"] = "YR=="  # decodes as a, nonzero pad bits
    with pytest.raises(observed.ObservationError, match="canonical"):
        observed.validate_bundle(report)


@pytest.mark.parametrize("path", ["../outside", "/input_data/requests_bucket_1.jsonl", "", 1])
def test_decode_file_cannot_expand_the_allowlist(bundle_root, path):
    report = observed.observe_bundle(root=bundle_root)
    with pytest.raises(observed.ObservationError, match="four-file"):
        observed.decode_file(report, path)


def test_reobserve_requires_exact_original_root(bundle_root, tmp_path):
    report = observed.observe_bundle(root=bundle_root)
    with pytest.raises(observed.ObservationError, match="root differs"):
        observed.reobserve_bundle(report, root=tmp_path / "another")


def test_oserror_is_public_refusal_and_descriptors_are_closed(bundle_root, monkeypatch):
    original_read = observed._read_bytes
    read_fds = []

    def failure(fd):
        read_fds.append(fd)
        original_read(fd)
        raise OSError("authored injected read failure")

    monkeypatch.setattr(observed, "_read_bytes", failure)
    with pytest.raises(observed.ObservationError, match="observation failed"):
        observed.observe_bundle(root=bundle_root)
    assert read_fds
    for descriptor in read_fds:
        with pytest.raises(OSError):
            os.fstat(descriptor)
