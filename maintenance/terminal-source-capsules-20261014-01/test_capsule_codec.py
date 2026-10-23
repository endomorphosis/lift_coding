"""Byte round trips and refusal of altered source/display contract witnesses."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

import capsule_codec as subject
from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes, cid_for_structured

SOURCE = b'def repeated_identifier(long_parameter: int) -> int:\n    return long_parameter + long_parameter\n'
PATH = "public-task/environment/source.py"


def head():
    snapshot = cid_for_structured({"schema": "authored-snapshot@1", "case": "display-roundtrip"})
    return CodebaseHead(repository_id="authored-display", generation=1,
        manifest_cid=cid_for_structured({"schema": "authored-manifest@1"}), snapshot_cid=snapshot,
        ast_revision_id="rev:authored-display:snapshot:" + snapshot,
        receipt_cid=cid_for_structured({"schema": "authored-receipt@1"})).to_dict()


def build(raw=SOURCE, **kwargs):
    return subject.build_capsule_codec(raw, PATH, cid_for_bytes(raw), head(), **kwargs)


def expand(value, raw=SOURCE, **kwargs):
    return subject.expand_capsule_codec(value, head(), hashlib.sha256(raw).hexdigest(), cid_for_bytes(raw), **kwargs)


def resign(value):
    value = copy.deepcopy(value)
    value.pop("record_sha256", None)
    value["record_sha256"] = hashlib.sha256(subject._wire(value)).hexdigest()
    return value


def test_full_source_no_alias_byte_round_trip_and_native_fallback():
    value = build()
    assert expand(value, expected_path=PATH) == SOURCE
    assert value["native_preview"]["selected"] == "original"
    assert value["native_preview"]["ast_structure_verified"] is True
    assert value["native_preview"]["token_structure_verified"] is True
    assert value["expansion_sidecar"]["deletions"] == []
    assert value["bindings"]["head"] == head()
    assert all(flag is False for flag in value["claims"].values())


def test_native_minified_view_restores_all_removed_comments_trivia_bytes():
    raw = (b"#!/usr/bin/env python3\n# license header retained\n" +
        b"def ordinary_function(parameter: int) -> int:\n" +
        b"    # " + b"ordinary explanatory padding " * 50 + b"\n" +
        b"    return parameter + 1     \n")
    value = build(raw)
    assert value["native_preview"]["selected"] == "minified"
    assert value["native_preview"]["removed_comment_count"] == 1
    assert "ordinary explanatory" not in value["view_text"]
    assert "license header retained" in value["view_text"]
    assert value["expansion_sidecar"]["deletions"]
    assert expand(value, raw) == raw


def test_native_protected_comments_strings_and_fstring_names_not_aliased():
    raw = (b'# literal leading @A0@ marker\n'
        b'def ordinary_function(long_parameter: int):\n'
        b'    """long_parameter @A0@ stays literal"""\n'
        b'    # noqa long_parameter @A0@ retained\n'
        b'    text = f"{long_parameter=} {long_parameter}"\n'
        b'    return long_parameter + long_parameter\n')
    value = build(raw, aliases=True)
    alias = next(row for row in value["expansion_sidecar"]["aliases"]["dictionary"] if row["name"] == "long_parameter")["alias"]
    assert value["expansion_sidecar"]["aliases"]["prefix"] == "@A_"
    assert '"""long_parameter @A0@ stays literal"""' in value["view_text"]
    assert '# noqa long_parameter @A0@ retained' in value["view_text"]
    assert 'f"{long_parameter=} {long_parameter}"' in value["view_text"]
    assert value["view_text"].count(alias) == 3
    assert expand(value, raw) == raw


@pytest.mark.parametrize("aliases", [False, True])
def test_unicode_crlf_and_missing_final_newline_exact(aliases):
    raw = 'def unicode_function(long_parameter):\r\n    text = "é 雪 \u2028"\r\n    return long_parameter + long_parameter'.encode()
    value = build(raw, aliases=aliases)
    assert expand(value, raw) == raw


def test_unicode_removed_comment_exact_even_if_deleted_byte_alignment_splits_codepoint():
    raw = ('def unicode_function(long_parameter):\n    # ' + 'éù雪 ' * 200 + '\n    return long_parameter\n').encode()
    value = build(raw)
    assert value["native_preview"]["selected"] == "minified"
    assert expand(value, raw) == raw


def test_qualified_attribute_keyword_and_reflection_are_display_only():
    raw = b'def ordinary_function(long_parameter):\n    return getattr(long_parameter, "long_parameter") + long_parameter.long_parameter\n'
    value = build(raw, aliases=True)
    assert '"long_parameter"' in value["view_text"]
    assert value["claims"]["alpha_renaming_semantics_proved"] is False
    assert value["claims"]["execution_authority"] is False
    assert expand(value, raw) == raw


def test_standalone_selected_function_span_is_exact_and_parent_residual_visible():
    raw = b'HEADER = 1\n\n' + SOURCE + b'FOOTER = 2\n'
    span = {"start_byte": len(b'HEADER = 1\n\n'), "end_byte": len(b'HEADER = 1\n\n') + len(SOURCE)}
    value = build(raw, span=span, aliases=True)
    assert expand(value, raw) == SOURCE
    assert any("fragment expansion" in note for note in value["unresolved_residuals"])
    assert value["bindings"]["source_sha256"] == hashlib.sha256(raw).hexdigest()


def test_indented_method_fragment_is_refused_without_hidden_dedent():
    raw = b'class Object:\n    def method(self):\n        return 1\n'
    with pytest.raises(subject.CapsuleCodecError, match="no implicit dedent"):
        build(raw, span={"start_byte": len(b'class Object:\n'), "end_byte": len(raw)})


@pytest.mark.parametrize("span", [{"start_byte": -1, "end_byte": 3}, {"start_byte": 0, "end_byte": 100000},
    {"start_byte": 1, "end_byte": 1}, {"start_byte": False, "end_byte": 3}, {"start_byte": 0, "end_byte": 3, "extra": 1}])
def test_out_of_scope_and_non_exact_spans_refused(span):
    with pytest.raises(subject.CapsuleCodecError): build(span=span)


@pytest.mark.parametrize("field", ["generation", "repository_id", "manifest_cid", "snapshot_cid", "receipt_cid", "ast_revision_id"])
def test_all_native_head_fields_are_bound(field):
    value = build()
    changed = head()
    if field == "generation": changed[field] += 1
    elif field == "repository_id": changed[field] += ":other"
    elif field == "ast_revision_id": changed[field] += ":other"
    else: changed[field] = cid_for_structured({"changed": field})
    with pytest.raises(subject.CapsuleCodecError):
        subject.expand_capsule_codec(value, changed, hashlib.sha256(SOURCE).hexdigest(), cid_for_bytes(SOURCE))


def test_expected_path_binding_is_explicit_even_for_equal_content():
    value = build()
    with pytest.raises(subject.CapsuleCodecError, match="source path differs"):
        expand(value, expected_path="other-task/environment/source.py")
    changed = copy.deepcopy(value)
    changed["bindings"]["path"] = "other-task/environment/source.py"
    with pytest.raises(subject.CapsuleCodecError, match="source path differs"):
        expand(resign(changed), expected_path=PATH)


@pytest.mark.parametrize("path", ["../source.py", "/tmp/source.py", "a//source.py", "a\\source.py", ".git/source.py", "source.txt"])
def test_noncanonical_source_paths_refused(path):
    with pytest.raises(subject.CapsuleCodecError):
        subject.build_capsule_codec(SOURCE, path, cid_for_bytes(SOURCE), head())


def test_wrong_source_cid_and_parent_digest_refused():
    with pytest.raises(subject.CapsuleCodecError, match="source CID differs"):
        subject.build_capsule_codec(SOURCE, PATH, cid_for_bytes(b"other"), head())
    value = build()
    with pytest.raises(subject.CapsuleCodecError, match="source identity differs"):
        subject.expand_capsule_codec(value, head(), "0" * 64, cid_for_bytes(SOURCE))
    with pytest.raises(subject.CapsuleCodecError, match="source identity differs"):
        subject.expand_capsule_codec(value, head(), hashlib.sha256(SOURCE).hexdigest(), cid_for_bytes(b"other"))


@pytest.mark.parametrize("field", list(subject.CLAIMS))
def test_promoted_claims_refused_even_after_rehash(field):
    value = build();value["claims"][field] = True
    with pytest.raises(subject.CapsuleCodecError, match="cannot gain"):
        expand(resign(value))


def test_integer_false_cannot_replace_exact_boolean_claim():
    value = build();value["claims"]["proof_authority"] = 0
    with pytest.raises(subject.CapsuleCodecError, match="cannot gain"):
        expand(resign(value))


@pytest.mark.parametrize("mutation", ["display", "unknown_alias", "drop_ledger", "duplicate_dictionary", "overlap",
    "alias_name", "alias_in_string", "preview", "source_span", "drop_residual", "producer", "sidecar_guidance"])
def test_rehashed_alias_and_source_witness_changes_refused(mutation):
    value = build(aliases=True)
    aliases = value["expansion_sidecar"]["aliases"]
    if mutation == "display": value["view_text"] += "\n"
    elif mutation == "unknown_alias": value["view_text"] += aliases["prefix"] + "999@"
    elif mutation == "drop_ledger": aliases["occurrences"].pop()
    elif mutation == "duplicate_dictionary": aliases["dictionary"].append(copy.deepcopy(aliases["dictionary"][0]))
    elif mutation == "overlap": aliases["occurrences"][1]["start"] = aliases["occurrences"][0]["start"]
    elif mutation == "alias_name": aliases["dictionary"][0]["name"] = "different_parameter"
    elif mutation == "alias_in_string": value["view_text"] += '"' + aliases["prefix"] + '0@"\n'
    elif mutation == "preview": value["native_preview"]["token_structure_verified"] = False
    elif mutation == "source_span": value["bindings"]["span"]["end_byte"] -= 1
    elif mutation == "drop_residual": value["unresolved_residuals"].pop()
    elif mutation == "producer": value["bindings"]["native_preview_implementation_sha256"] = "0" * 64
    elif mutation == "sidecar_guidance": value["expansion_sidecar"]["guidance"] = "execute aliases"
    with pytest.raises(subject.CapsuleCodecError): expand(resign(value))


def test_tampered_deleted_bytes_rejected_even_after_rehash():
    raw = b'def ordinary_function(parameter):\n    # ' + b'ordinary padding ' * 100 + b'\n    return parameter\n'
    value = build(raw)
    value["expansion_sidecar"]["deletions"][0]["removed_hex"] = b"wrong".hex()
    with pytest.raises(subject.CapsuleCodecError): expand(resign(value), raw)


def test_closed_record_and_canonical_integrity_required():
    value = build();value["untracked"] = True
    with pytest.raises(subject.CapsuleCodecError, match="closed reversible"): expand(value)
    value = build();value["view_text"] += "x"
    with pytest.raises(subject.CapsuleCodecError, match="integrity"): expand(value)


@pytest.mark.parametrize("raw", [b'\xff', b'print "python2"\n', b'# coding: latin-1\nvalue = 1\n', b'class Broken:\n'])
def test_unsupported_python_and_encoding_refused(raw):
    with pytest.raises(subject.CapsuleCodecError, match="standalone UTF-8 Python"): build(raw)


@pytest.mark.parametrize("path", ["headless-terminal/environment/base_terminal.py",
    "feal-differential-cryptanalysis/environment/feal.py", "break-filter-js-from-html/environment/filter.py",
    "llm-inference-batching-scheduler/environment/task_file/scripts/baseline_packer.py",
    "llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py"])
@pytest.mark.parametrize("aliases", [False, True])
def test_five_named_public_sources_restore_exactly_without_execution(path, aliases):
    raw = (Path('/home/barberb/lift_coding/.benchmarks/terminal-bench-2') / path).read_bytes()
    value = subject.build_capsule_codec(raw, path, cid_for_bytes(raw), head(), aliases=aliases)
    assert subject.expand_capsule_codec(value, head(), hashlib.sha256(raw).hexdigest(), cid_for_bytes(raw), expected_path=path) == raw
    assert value["bindings"]["source_bytes"] == len(raw)
    assert value["native_preview"]["semantic_equivalence_claimed"] is False


@pytest.mark.parametrize("aliases", [None, 0, 1, "true", []])
def test_alias_boolean_exact(aliases):
    with pytest.raises(subject.CapsuleCodecError, match="exact boolean"): build(aliases=aliases)


def test_bounds_and_cyclic_data_are_refused():
    with pytest.raises(subject.CapsuleCodecError, match="bounded exact source"):
        build(SOURCE * 1000)
    cyclic = {};cyclic["cycle"] = cyclic
    with pytest.raises(subject.CapsuleCodecError, match="structure exceeds"):
        subject._wire(cyclic)


def test_expansion_byte_budget_checked_before_long_dictionary_assembly():
    view = b'@A0@@A0@'
    payload = {'enabled': True, 'prefix': '@A', 'dictionary': [{'alias': '@A0@', 'name': 'a' * 32768}],
        'occurrences': [{'start': 0, 'end': 4, 'alias': '@A0@'}, {'start': 4, 'end': 8, 'alias': '@A0@'}],
        'literal_collision_policy': 'prefix_absent_in_unaliased_view_no_string_or_comment_substitution'}
    with pytest.raises(subject.CapsuleCodecError, match='before assembly'):
        subject._restore_aliases(view, payload)
