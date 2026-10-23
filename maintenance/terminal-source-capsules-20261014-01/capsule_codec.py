"""Bounded reversible source display using the actual conservative native view.

NAME aliases encode display text, not alpha-renamed Python. Every expansion
restores exact selected bytes; the caller establishes current source ownership.
No target source is imported, executed, rewritten or authorized by this codec.
"""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import io
import json
import keyword
from pathlib import Path, PurePosixPath
import re
import token
import tokenize

SCHEMA = "terminal-reversible-source-display-capsule@1"
SIDECAR_SCHEMA = "terminal-source-display-expansion@1"
MAX_SOURCE_BYTES = 32768
MAX_RECORD_BYTES = 1024 * 1024
MAX_OPERATIONS = 8192
MAX_ALIASES = 128
CLAIMS = {name: False for name in (
    "proof_authority", "execution_authority", "completion_authority", "omission_authority",
    "source_authentication_claimed", "source_origin_proved", "current_owner_verified",
    "source_path_authentication_proved",
    "semantic_equivalence_claimed", "cpython_equivalence_proved", "alpha_renaming_semantics_proved",
    "full_task_satisfaction_proved", "token_savings_measured", "provider_usage_measured")}
FIELDS = {"schema", "view_text", "expansion_sidecar", "bindings", "claims", "native_preview",
    "unresolved_residuals", "record_sha256"}
SIDECAR_FIELDS = {"schema", "deletions", "aliases", "minified_view_bytes", "minified_view_sha256", "guidance"}
BINDING_FIELDS = {"head", "head_sha256", "path", "source_cid", "source_sha256", "source_bytes",
    "span", "fragment_sha256", "fragment_bytes", "native_preview_implementation_sha256"}
GUIDANCE = ("DISPLAY ENCODING ONLY. NAME markers are dictionary references, not executable Python. "
    "Reverse only the listed alias occurrences, then insert each deleted byte span at its minified-view "
    "offset. Validate the exact fragment hash and full native head/source identities. "
    "Read original source before edits; hashes and AST/token checks confer no semantic or execution authority.")


class CapsuleCodecError(ValueError):
    """A closed source/display identity or byte-exact restoration differs."""


def _need(condition, message):
    if not condition:
        raise CapsuleCodecError(message)


def _wire(value):
    nodes = 0
    def check(item, depth=0):
        nonlocal nodes
        nodes += 1
        _need(depth <= 40 and nodes <= 200000, "record structure exceeds finite bound")
        if type(item) is dict:
            _need(all(type(key) is str for key in item), "exact string mapping keys required")
            for child in item.values(): check(child, depth + 1)
        elif type(item) is list:
            for child in item: check(child, depth + 1)
        else:
            _need(type(item) in {str, int, bool, type(None)}, "closed finite JSON types required")
            if type(item) is str:
                _need(len(item) <= MAX_RECORD_BYTES, "record string exceeds bound")
            elif type(item) is int:
                _need(item.bit_length() <= 64, "record integer exceeds bound")
    try:
        check(value)
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        if isinstance(error, CapsuleCodecError): raise
        raise CapsuleCodecError("bounded ordinary UTF-8 JSON required") from error
    _need(len(raw) <= MAX_RECORD_BYTES, "complete capsule record exceeds byte bound")
    return raw


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _copy(value):
    return json.loads(_wire(value))


def _hash(value, name):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), name + " must be exact SHA-256")
    return value


def _head(value):
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    _need(type(value) is dict, "complete native head dictionary required")
    raw = _wire(value)
    try:
        native = CodebaseHead.from_dict(json.loads(raw)).to_dict()
    except (ValueError, TypeError, KeyError) as error:
        raise CapsuleCodecError("validated complete native head required") from error
    _need(_wire(native) == raw, "closed full native head representation differs")
    return native


def _path(value):
    _need(type(value) is str and 0 < len(value.encode("utf-8")) <= 4096
        and "\\" not in value and not any(c in value for c in "\r\n\x00"), "canonical source path required")
    path = PurePosixPath(value)
    _need(not path.is_absolute() and str(path) == value and path.suffix == ".py"
        and all(part not in {".", "..", ".git"} for part in path.parts), "canonical relative Python source path required")
    return value


def _source_cid(value):
    from ipfs_datasets_py.logic.software_contracts.content import validate_cid
    try:
        return validate_cid(value, codecs={"raw"})
    except (ValueError, TypeError) as error:
        raise CapsuleCodecError("canonical raw-byte source CID required") from error


def _preview(fragment):
    from ipfs_accelerate_py.agent_supervisor.runtime import code_view_minification as native
    try:
        text = fragment.decode("utf-8")
        result = native.build_code_view_preview(text, max_bytes=MAX_SOURCE_BYTES)
    except (UnicodeError, native.CodeViewMinificationError) as error:
        raise CapsuleCodecError("native display profile requires standalone UTF-8 Python; no implicit dedent") from error
    return _copy(result), _sha(Path(native.__file__).read_bytes())


def _deletions(original, view):
    """Linear deletion-only witness; hex retains even partial UTF-8 byte spans."""
    i, j, rows = 0, 0, []
    while j < len(view):
        if i < len(original) and original[i] == view[j]:
            i += 1
            j += 1
            continue
        end = original.find(view[j:j + 1], i)
        _need(end >= i, "native view is outside deletion-only display profile")
        rows.append({"view_offset": j, "removed_hex": original[i:end].hex()})
        i = end
    if i < len(original):
        rows.append({"view_offset": j, "removed_hex": original[i:].hex()})
    _need(len(rows) <= MAX_OPERATIONS, "deletion witness operation bound exceeded")
    return rows


def _restore_deletions(view, rows):
    _need(type(rows) is list and len(rows) <= MAX_OPERATIONS, "bounded deletion witness required")
    output, cursor, prior, inserted = [], 0, -1, 0
    for row in rows:
        _need(type(row) is dict and set(row) == {"view_offset", "removed_hex"}, "closed deletion operation required")
        offset, encoded = row["view_offset"], row["removed_hex"]
        _need(type(offset) is int and prior < offset <= len(view), "ordered deletion offsets differ")
        _need(type(encoded) is str and 0 < len(encoded) <= 2 * MAX_SOURCE_BYTES
            and len(encoded) % 2 == 0 and re.fullmatch("[0-9a-f]+", encoded), "bounded nonempty deleted bytes required")
        removed = bytes.fromhex(encoded)
        inserted += len(removed)
        _need(len(view) + inserted <= MAX_SOURCE_BYTES, "expanded selected source exceeds bound")
        output.extend((view[cursor:offset], removed))
        cursor, prior = offset, offset
    output.append(view[cursor:])
    return b"".join(output)


def _name_occurrences(text):
    """NAME-token spans excluding complete string/f-string AST regions."""
    try:
        tree = ast.parse(text, type_comments=True)
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (SyntaxError, ValueError, tokenize.TokenError, IndentationError, RecursionError) as error:
        raise CapsuleCodecError("native minified Python could not be independently tokenized") from error
    lines = list(io.StringIO(text).readlines())
    byte_offsets, cursor = [], 0
    for line in lines:
        byte_offsets.append(cursor)
        cursor += len(line.encode("utf-8"))
    def ast_byte(node, endpoint):
        line = node.lineno if endpoint == "start" else node.end_lineno
        column = node.col_offset if endpoint == "start" else node.end_col_offset
        return byte_offsets[line - 1] + column
    protected = [(ast_byte(node, "start"), ast_byte(node, "end")) for node in ast.walk(tree)
        if isinstance(node, ast.JoinedStr) or isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes))]
    def token_byte(position):
        line, column = position
        return byte_offsets[line - 1] + len(lines[line - 1][:column].encode("utf-8"))
    found = []
    for item in tokens:
        if item.type != token.NAME or keyword.iskeyword(item.string) or keyword.issoftkeyword(item.string):
            continue
        start, end = token_byte(item.start), token_byte(item.end)
        if any(left <= start < right or left < end <= right for left, right in protected):
            continue
        found.append({"name": item.string, "start": start, "end": end})
    _need(len(found) <= MAX_OPERATIONS, "NAME-token display operation bound exceeded")
    return found


def _aliases(view, enabled):
    _need(type(enabled) is bool, "aliases must be an exact boolean")
    if not enabled:
        return view, {"enabled": False, "prefix": "", "dictionary": [], "occurrences": [],
            "literal_collision_policy": "no_aliases"}
    text = view.decode("utf-8")
    occurrences = _name_occurrences(text)
    counts = Counter(row["name"] for row in occurrences)
    names = sorted(name for name, count in counts.items() if count >= 2 and len(name.encode()) >= 8)
    _need(len(names) <= MAX_ALIASES, "alias dictionary bound exceeded")
    prefix = "@A"
    while prefix.encode() in view:
        prefix += "_"
        _need(len(prefix) <= 64, "cannot allocate collision-free display prefix")
    dictionary = [{"alias": prefix + str(index) + "@", "name": name} for index, name in enumerate(names)]
    aliases = {row["name"]: row["alias"] for row in dictionary}
    output, ledger, cursor, size = [], [], 0, 0
    for row in occurrences:
        if row["name"] not in aliases:
            continue
        literal = view[cursor:row["start"]]
        alias = aliases[row["name"]].encode()
        output.extend((literal, alias))
        size += len(literal)
        ledger.append({"start": size, "end": size + len(alias), "alias": aliases[row["name"]]})
        size += len(alias)
        cursor = row["end"]
    output.append(view[cursor:])
    return b"".join(output), {"enabled": True, "prefix": prefix, "dictionary": dictionary,
        "occurrences": ledger, "literal_collision_policy": "prefix_absent_in_unaliased_view_no_string_or_comment_substitution"}


def _restore_aliases(view, payload):
    _need(type(payload) is dict and set(payload) == {"enabled", "prefix", "dictionary", "occurrences", "literal_collision_policy"},
        "closed alias witness required")
    if payload["enabled"] is False:
        _need(payload == {"enabled": False, "prefix": "", "dictionary": [], "occurrences": [],
            "literal_collision_policy": "no_aliases"}, "disabled alias witness differs")
        return view
    _need(payload["enabled"] is True and payload["literal_collision_policy"] ==
        "prefix_absent_in_unaliased_view_no_string_or_comment_substitution", "display-only alias policy differs")
    prefix = payload["prefix"]
    _need(type(prefix) is str and re.fullmatch("@A_{0,62}", prefix), "bounded display prefix required")
    dictionary, ledger = payload["dictionary"], payload["occurrences"]
    _need(type(dictionary) is list and len(dictionary) <= MAX_ALIASES and type(ledger) is list
        and len(ledger) <= MAX_OPERATIONS, "alias witness bound exceeded")
    names, aliases = [], {}
    for index, row in enumerate(dictionary):
        _need(type(row) is dict and set(row) == {"alias", "name"} and type(row["name"]) is str
            and row["name"].isidentifier() and not keyword.iskeyword(row["name"])
            and not keyword.issoftkeyword(row["name"]) and 8 <= len(row["name"].encode()) <= MAX_SOURCE_BYTES
            and row["alias"] == prefix + str(index) + "@", "canonical alias dictionary differs")
        names.append(row["name"])
        aliases[row["alias"]] = row["name"].encode()
    _need(names == sorted(set(names)), "duplicate or noncanonical alias names")
    pieces, cursor, seen, expanded_bytes = [], 0, Counter(), 0
    for row in ledger:
        _need(type(row) is dict and set(row) == {"start", "end", "alias"}
            and type(row["start"]) is int and type(row["end"]) is int
            and cursor <= row["start"] < row["end"] <= len(view)
            and type(row["alias"]) is str and row["alias"] in aliases,
            "ordered in-scope alias occurrence required")
        start, end, alias = row["start"], row["end"], row["alias"]
        _need(view[start:end] == alias.encode(), "alias occurrence bytes differ")
        literal = view[cursor:start]
        _need(prefix.encode() not in literal, "unlisted or unknown alias in display")
        expanded_bytes += len(literal) + len(aliases[alias])
        _need(expanded_bytes <= MAX_SOURCE_BYTES, "alias expansion exceeds bound before assembly")
        pieces.extend((literal, aliases[alias]))
        cursor = end
        seen[alias] += 1
    _need(prefix.encode() not in view[cursor:] and all(seen[name] >= 2 for name in aliases),
        "unlisted, unused or insufficiently repeated alias")
    expanded_bytes += len(view[cursor:])
    _need(expanded_bytes <= MAX_SOURCE_BYTES, "alias expansion exceeds bound before assembly")
    pieces.append(view[cursor:])
    result = b"".join(pieces)
    _need(len(result) <= MAX_SOURCE_BYTES and prefix.encode() not in result,
        "alias expansion byte bound or literal collision differs")
    # Independently regenerate token positions and deterministic dictionary.
    encoded, expected = _aliases(result, True)
    _need(encoded == view and _wire(expected) == _wire(payload), "NAME-only alias replay differs")
    return result


def _residuals(span, source_bytes):
    result = ["AST/token preservation is structural, not Python runtime equivalence",
        "complete source dependencies, runtime effects and task satisfaction remain unresolved",
        "caller must verify current complete native owner before and after use",
        "NAME aliases are a non-Python display encoding; restore before any source edit",
        "full head alone does not prove source-path membership; caller must join the native manifest entry"]
    if span["start_byte"] != 0 or span["end_byte"] != source_bytes:
        result.append("fragment expansion alone cannot reestablish complete parent byte ownership")
    return result


def build_capsule_codec(source_bytes, path, source_cid, head, span=None, aliases=False):
    """Encode an exact full file or standalone selected source byte fragment."""
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes
    _need(type(source_bytes) is bytes and 0 < len(source_bytes) <= MAX_SOURCE_BYTES, "bounded exact source bytes required")
    source_path, full_head = _path(path), _head(head)
    _need(_source_cid(source_cid) == cid_for_bytes(source_bytes), "complete source CID differs from bytes")
    if span is None:
        span = {"start_byte": 0, "end_byte": len(source_bytes)}
    _need(type(span) is dict and set(span) == {"start_byte", "end_byte"}
        and type(span["start_byte"]) is int and type(span["end_byte"]) is int
        and 0 <= span["start_byte"] < span["end_byte"] <= len(source_bytes), "exact selected source byte span required")
    fragment = source_bytes[span["start_byte"]:span["end_byte"]]
    preview, producer_hash = _preview(fragment)
    minified = preview["view_text"].encode()
    deleted = _deletions(fragment, minified)
    _need(_restore_deletions(minified, deleted) == fragment, "native minification byte restoration differs")
    displayed, alias_witness = _aliases(minified, aliases)
    _need(len(displayed) <= MAX_SOURCE_BYTES, "alias display exceeds byte bound")
    bindings = {"head": full_head, "head_sha256": _sha(_wire(full_head)), "path": source_path,
        "source_cid": source_cid, "source_sha256": _sha(source_bytes), "source_bytes": len(source_bytes),
        "span": _copy(span), "fragment_sha256": _sha(fragment), "fragment_bytes": len(fragment),
        "native_preview_implementation_sha256": producer_hash}
    record = {"schema": SCHEMA, "view_text": displayed.decode("utf-8"),
        "expansion_sidecar": {"schema": SIDECAR_SCHEMA, "deletions": deleted, "aliases": alias_witness,
            "minified_view_bytes": len(minified), "minified_view_sha256": _sha(minified), "guidance": GUIDANCE},
        "bindings": bindings, "claims": dict(CLAIMS), "native_preview": preview,
        "unresolved_residuals": _residuals(span, len(source_bytes))}
    record["record_sha256"] = _sha(_wire(record))
    result = _copy(record)
    _need(expand_capsule_codec(result, full_head, _sha(source_bytes), source_cid, expected_path=source_path) == fragment,
        "complete experimental capsule replay differs")
    return result


def expand_capsule_codec(record, expected_head, expected_source_sha256, expected_source_cid, *, expected_path=None):
    """Expand byte-identically; expected identities come from the caller's owner."""
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes
    _need(type(record) is dict and set(record) == FIELDS and record.get("schema") == SCHEMA,
        "closed reversible display capsule required")
    value = _copy(record)
    checksum = _hash(value.pop("record_sha256"), "record_sha256")
    _need(_sha(_wire(value)) == checksum, "complete display capsule integrity differs")
    _need(type(value["claims"]) is dict and set(value["claims"]) == set(CLAIMS)
        and all(value["claims"][key] is False for key in CLAIMS),
        "display codec cannot gain proof, omission or execution authority")
    binding = value["bindings"]
    _need(type(binding) is dict and set(binding) == BINDING_FIELDS, "closed source binding required")
    head = _head(expected_head)
    _need(_wire(_head(binding["head"])) == _wire(head) and binding["head_sha256"] == _sha(_wire(head)),
        "complete expected native head differs")
    _path(binding["path"])
    if expected_path is not None:
        _need(binding["path"] == _path(expected_path), "expected current source path differs")
    _need(binding["source_sha256"] == _hash(expected_source_sha256, "expected_source_sha256")
        and binding["source_cid"] == _source_cid(expected_source_cid), "expected parent source identity differs")
    _need(type(binding["source_bytes"]) is int and 0 < binding["source_bytes"] <= MAX_SOURCE_BYTES,
        "bounded full source byte count required")
    span = binding["span"]
    _need(type(span) is dict and set(span) == {"start_byte", "end_byte"}
        and type(span["start_byte"]) is int and type(span["end_byte"]) is int
        and 0 <= span["start_byte"] < span["end_byte"] <= binding["source_bytes"]
        and type(binding["fragment_bytes"]) is int and binding["fragment_bytes"] == span["end_byte"] - span["start_byte"],
        "bound fragment byte span differs")
    sidecar = value["expansion_sidecar"]
    _need(type(sidecar) is dict and set(sidecar) == SIDECAR_FIELDS and sidecar["schema"] == SIDECAR_SCHEMA
        and sidecar["guidance"] == GUIDANCE, "closed exact expansion sidecar required")
    _need(type(value["view_text"]) is str, "literal display text required")
    displayed = value["view_text"].encode("utf-8")
    _need(len(displayed) <= MAX_SOURCE_BYTES, "display byte bound exceeded")
    minified = _restore_aliases(displayed, sidecar["aliases"])
    _need(type(sidecar["minified_view_bytes"]) is int and len(minified) == sidecar["minified_view_bytes"]
        and _sha(minified) == _hash(sidecar["minified_view_sha256"], "minified_view_sha256"),
        "expanded native minified view differs")
    fragment = _restore_deletions(minified, sidecar["deletions"])
    _need(len(fragment) == binding["fragment_bytes"]
        and _sha(fragment) == _hash(binding["fragment_sha256"], "fragment_sha256"), "expanded exact source fragment differs")
    preview, producer_hash = _preview(fragment)
    _need(_wire(preview) == _wire(value["native_preview"]) and preview["view_text"].encode() == minified
        and producer_hash == binding["native_preview_implementation_sha256"], "actual native preview/policy replay differs")
    _need(_wire(_deletions(fragment, minified)) == _wire(sidecar["deletions"]), "canonical deletion witness differs")
    if span["start_byte"] == 0 and span["end_byte"] == binding["source_bytes"]:
        _need(_sha(fragment) == expected_source_sha256 and cid_for_bytes(fragment) == expected_source_cid,
            "complete restored source hash/CID differs")
    _need(_wire(value["unresolved_residuals"]) == _wire(_residuals(span, binding["source_bytes"])),
        "explicit unresolved display caveats required")
    return fragment
