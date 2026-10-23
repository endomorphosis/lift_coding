"""Seals refuse tampering and aliases without expanding the selected scope."""
import json

import pytest

import seal_training_evidence as evidence


def config(root, files):
    return {"schema": "terminal-codebase-ir-evidence-selection@1", "root": str(root), "files": files}


def test_seal_reopens_and_refuses_modified_selected_artifact(tmp_path):
    source = tmp_path / "public.json"
    source.write_text('{"candidate":true}')
    selected = config(tmp_path, [source.name])
    manifest = tmp_path / "seal.json"
    seal = evidence.seal(selected, manifest)
    assert evidence.seal(selected, manifest, verify=True) == seal
    assert all(seal[field] is False for field in ("authenticated_training_origin", "proof_authority",
        "source_model_equivalence_proved", "asymptotic_optimizer_convergence_proved", "full_task_satisfaction"))
    source.write_text('{"candidate":false}')
    with pytest.raises(ValueError, match="differs"):
        evidence.seal(selected, manifest, verify=True)


@pytest.mark.parametrize("mutation", ["symlink", "hardlink", "escape", "duplicate", "size"])
def test_refuses_aliased_or_overbound_explicit_files(tmp_path, monkeypatch, mutation):
    original = tmp_path / "public.txt"
    original.write_bytes(b"public evidence")
    paths = [original.name]
    if mutation == "symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(original)
        paths = [alias.name]
    elif mutation == "hardlink":
        alias = tmp_path / "alias"
        alias.hardlink_to(original)
        paths = [alias.name]
    elif mutation == "escape":
        paths = ["../other"]
    elif mutation == "duplicate":
        paths += paths
    else:
        monkeypatch.setattr(evidence, "MAX_FILE_BYTES", 2)
    with pytest.raises(ValueError):
        evidence.seal(config(tmp_path, paths), tmp_path / "seal.json")


def test_unselected_files_are_never_opened(tmp_path):
    (tmp_path / "selected").write_bytes(b"known public bytes")
    # A dangling symlink is not opened, resolved, or silently added to a seal.
    (tmp_path / "unselected").symlink_to(tmp_path / "missing-private-file")
    result = evidence.seal(config(tmp_path, ["selected"]), tmp_path / "seal.json")
    assert [row["path"] for row in result["files"]] == ["selected"]


@pytest.mark.parametrize("body", [b'{"schema":1,"schema":2}', b'{"value":NaN}'])
def test_seal_config_refuses_ambiguous_json(body):
    with pytest.raises(ValueError):
        evidence.loads(body)
