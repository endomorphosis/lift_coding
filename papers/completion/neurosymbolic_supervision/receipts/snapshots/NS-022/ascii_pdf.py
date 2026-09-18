#!/usr/bin/env python3.12
"""Rewrite a classic (non-object-stream) PDF so Git treats it as UTF-8 text.

Hex-encodes non-ASCII streams with ASCIIHexDecode and rebuilds xref.
Does not change page content, fonts, or scientific bytes of the source TeX.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

OBJ_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj\b", re.S)
STARTXREF_RE = re.compile(rb"startxref\s+(\d+)\s*%%EOF", re.S)


def _ascii_ok(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _hex_payload(data: bytes) -> bytes:
    hexed = data.hex().encode("ascii")
    lines = [hexed[i : i + 80] for i in range(0, len(hexed), 80)]
    return b"\n".join(lines) + b"\n>\n"


def _rewrite_dict_for_hex(header: bytes, new_length: int) -> bytes:
    text = header.decode("latin-1")
    if re.search(r"/Filter\s*\[", text):
        text = re.sub(r"/Filter\s*\[", "/Filter [/ASCIIHexDecode ", text, count=1)
    elif re.search(r"/Filter\s*/[A-Za-z0-9]+", text):
        text = re.sub(
            r"/Filter\s*(/[A-Za-z0-9]+)",
            r"/Filter [/ASCIIHexDecode \1]",
            text,
            count=1,
        )
    else:
        text = text.replace(">>", "/Filter /ASCIIHexDecode >>", 1)
        if "/Filter /ASCIIHexDecode >>" not in text:
            raise ValueError("unable to insert ASCIIHexDecode filter")
    if re.search(r"/Length\s+\d+", text):
        text = re.sub(r"/Length\s+\d+", f"/Length {new_length}", text, count=1)
    else:
        text = text.replace(">>", f"/Length {new_length} >>", 1)
    return text.encode("latin-1")


def convert(raw: bytes) -> bytes:
    if not raw.startswith(b"%PDF-"):
        raise ValueError("not a PDF")
    # Drop the conventional binary marker comment so the file is UTF-8.
    body = raw
    m = re.match(rb"%PDF-\d\.\d\r?\n(?:%[^\n]*\n)?", body)
    version = b"%PDF-1.4\n"
    if m:
        first = body[: m.end()]
        ver = re.match(rb"%PDF-\d\.\d", first)
        if ver:
            version = ver.group(0) + b"\n"
        body = body[m.end() :]
    # Work only on the object body; drop existing xref.
    xref_at = body.rfind(b"\nxref\n")
    if xref_at < 0:
        xref_at = body.rfind(b"\nxref\r\n")
    if xref_at < 0:
        raise ValueError("classic xref table not found; rebuild with pdfobjcompresslevel=0")
    objects_blob = body[: xref_at + 1]
    trailer_blob = body[xref_at:]
    trailer_m = re.search(rb"trailer\s*(<<.*?>>)\s*startxref", trailer_blob, re.S)
    if not trailer_m:
        raise ValueError("trailer dictionary not found")
    trailer_dict = trailer_m.group(1)

    matches = list(OBJ_RE.finditer(objects_blob))
    if not matches:
        raise ValueError("no PDF objects")
    rewritten: dict[tuple[int, int], bytes] = {}
    max_obj = 0
    for i, match in enumerate(matches):
        obj_num = int(match.group(1))
        gen = int(match.group(2))
        max_obj = max(max_obj, obj_num)
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(objects_blob)
        chunk = objects_blob[start:end]
        # Isolate through endobj
        endobj = chunk.find(b"endobj")
        if endobj < 0:
            raise ValueError(f"object {obj_num} missing endobj")
        chunk = chunk[: endobj + len(b"endobj")] + b"\n"
        stream_at = chunk.find(b"stream")
        if stream_at < 0:
            rewritten[(obj_num, gen)] = chunk
            continue
        header = chunk[:stream_at]
        rest = chunk[stream_at + len(b"stream") :]
        if rest.startswith(b"\r\n"):
            rest = rest[2:]
        elif rest.startswith(b"\n"):
            rest = rest[1:]
        elif rest.startswith(b"\r"):
            rest = rest[1:]
        endstream = rest.rfind(b"endstream")
        if endstream < 0:
            raise ValueError(f"object {obj_num} missing endstream")
        payload = rest[:endstream]
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        elif payload.endswith(b"\n") or payload.endswith(b"\r"):
            payload = payload[:-1]
        if _ascii_ok(payload):
            rewritten[(obj_num, gen)] = chunk
            continue
        hexed = _hex_payload(payload)
        new_header = _rewrite_dict_for_hex(header, len(hexed))
        rewritten[(obj_num, gen)] = (
            new_header + b"stream\n" + hexed + b"endstream\nendobj\n"
        )

    out = bytearray(version)
    offsets: dict[int, int] = {}
    for obj_num in range(1, max_obj + 1):
        key = (obj_num, 0)
        if key not in rewritten:
            continue
        offsets[obj_num] = len(out)
        out.extend(rewritten[key])
        if not out.endswith(b"\n"):
            out.extend(b"\n")

    xref_pos = len(out)
    size = max_obj + 1
    out.extend(f"xref\n0 {size}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for obj_num in range(1, size):
        if obj_num in offsets:
            out.extend(f"{offsets[obj_num]:010d} 00000 n \n".encode("ascii"))
        else:
            out.extend(b"0000000000 65535 f \n")
    # Preserve Root/Info/ID; replace Size.
    trailer = re.sub(rb"/Size\s+\d+", f"/Size {size}".encode("ascii"), trailer_dict, count=1)
    out.extend(b"trailer\n")
    out.extend(trailer)
    if not trailer.endswith(b"\n"):
        out.extend(b"\n")
    out.extend(f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii"))
    result = bytes(out)
    if not _ascii_ok(result):
        bad = [b for b in result if b > 127 or b == 0]
        raise ValueError(f"result is not UTF-8 ASCII: {len(bad)} offending bytes")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("dest", type=Path)
    args = parser.parse_args()
    args.dest.write_bytes(convert(args.source.read_bytes()))
    print(f"wrote {args.dest} ({args.dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
