"""Bounded metadata I/O. No native, provider, scorer or signing imports."""
import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path

MAXIMUM = 4 * 1024 * 1024

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()

def pairs(values):
    out = {}
    for key, value in values:
        if key in out:
            raise ValueError('duplicate JSON key')
        out[key] = value
    return out

def decode(raw):
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))

def read_bytes(path, expected=None):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        assert stat.S_ISREG(before.st_mode) and before.st_size <= MAXIMUM
        raw = stream.read(MAXIMUM + 1)
        after = os.fstat(stream.fileno())
    assert len(raw) == before.st_size <= MAXIMUM
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    assert expected is None or digest(raw) == expected, 'source hash mismatch'
    return raw

def binding(path, expected=None):
    raw = read_bytes(path, expected)
    return dict(path=str(Path(path).absolute()), sha256=digest(raw), bytes=len(raw))

def write(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def public_check(raw):
    text = raw.decode('utf-8')
    # Private author/workspace markers, secret material and signature envelopes.
    # Upstream copyright/license attribution is not classified as author identity.
    assert not re.search(r'/(?:home|Users)/[A-Za-z0-9_.-]+/|BEGIN [A-Z ]*PRIVATE KEY|(?:sk|xai)-[A-Za-z0-9]{20,}', text, re.I), 'private identity or secret marker'
    # This scalar component has no declared project links. An unexpected link
    # requires classification; never erase an upstream license or attribution.
    assert not re.search(r'https?://(?:www\.)?github[.]com/[A-Za-z0-9_.-]+/', text, re.I), 'unclassified project link'
    assert not re.search(r'"(?:signature|private_key|api_key|access_token)"\s*:', text), 'signature/secret envelope not a public scalar projection'

def number(value, nullable=True):
    if value is None and nullable:
        return None
    assert type(value) in (int, float) and math.isfinite(value) and value >= 0
    return value

def numeric_tree(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return {key: numeric_tree(v) for key, v in value.items()}
    return number(value, nullable=False)
