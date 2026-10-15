#!/usr/bin/env python3
"""Generate chunk list (TSV: chunk_name<TAB>pathspec) for the pin-advance
pathspec checkout, derived from the TARGET tip tree (local objects only).
Uses the `git ls-tree <tip>:<dir>` form (bare entry names)."""
import subprocess
from collections import OrderedDict

TIP = "f4a823231ad52c9252504810a1b00ed4738346b6"
REPO = "/home/hatch/workspace/lift_coding/external/ipfs_datasets"

def entries(dirpath):
    """Immediate children of dirpath ('' = root) as (type, fullpath)."""
    spec = TIP + ":" + dirpath if dirpath else TIP + ":"
    out = subprocess.run(["git", "ls-tree", spec],
                         capture_output=True, text=True, cwd=REPO).stdout
    res = []
    for line in out.splitlines():
        meta, name = line.split("\t", 1)
        typ = meta.split()[1]
        full = f"{dirpath}/{name}" if dirpath else name
        res.append((typ, full))
    return res

rows = []

def files_chunk(chunk, dirpath):
    for typ, full in entries(dirpath):
        if typ == "blob":
            rows.append((chunk, full))

def dir_chunks(prefix, dirpath, skip=()):
    files_chunk(f"{prefix}/__files__", dirpath)
    for typ, full in entries(dirpath):
        if typ == "tree" and full not in skip:
            rows.append((f"{prefix}/{full.split('/')[-1]}", full))

# top level
files_chunk("__toplevel_files__", "")
for typ, full in entries(""):
    if typ == "tree" and full not in ("ipfs_datasets_py", "tests", "docs"):
        rows.append((f"top/{full}", full))

# package
dir_chunks("pkg", "ipfs_datasets_py", skip=("ipfs_datasets_py/processors",))
files_chunk("pkg/processors/__files__", "ipfs_datasets_py/processors")
for typ, full in entries("ipfs_datasets_py/processors"):
    if typ == "tree":
        rows.append((f"pkg/processors/{full.split('/')[-1]}", full))

# tests (split unit one level deeper)
files_chunk("tests/__files__", "tests")
for typ, full in entries("tests"):
    if typ == "tree" and full != "tests/unit":
        rows.append((f"tests/{full.split('/')[-1]}", full))
files_chunk("tests/unit/__files__", "tests/unit")
for typ, full in entries("tests/unit"):
    if typ == "tree":
        rows.append((f"tests/unit/{full.split('/')[-1]}", full))

# docs
dir_chunks("docs", "docs")

seen = set()
uniq = []
for r in rows:
    if r not in seen:
        seen.add(r)
        uniq.append(r)

out_path = "/home/hatch/workspace/lift_coding/visual_check/fv_state/pin_advance/chunks.tsv"
with open(out_path, "w") as fh:
    for chunk, spec in uniq:
        fh.write(f"{chunk}\t{spec}\n")

chunks = OrderedDict()
for chunk, spec in uniq:
    chunks.setdefault(chunk, []).append(spec)
print(f"{len(chunks)} chunks, {len(uniq)} pathspecs -> {out_path}")
for name, specs in chunks.items():
    print(f"  {name}: {len(specs)} pathspec(s)")
