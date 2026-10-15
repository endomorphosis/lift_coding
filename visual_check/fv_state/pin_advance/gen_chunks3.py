#!/usr/bin/env python3
"""Pass-3 chunk generator: from the NOT-DONE pass-2 chunks, re-split into
coarser chunks (dirs <=600 tip-tree files; lists <=300 specs) and partition
round-robin into 3 disjoint sets for parallel drivers with private indexes."""
import subprocess
from collections import OrderedDict

TIP = "f4a823231ad52c9252504810a1b00ed4738346b6"
REPO = "/home/hatch/workspace/lift_coding/external/ipfs_datasets"
PA = "/home/hatch/workspace/lift_coding/visual_check/fv_state/pin_advance"
MAX_DIR_FILES = 600
MAX_LIST = 300

def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO).stdout

def tree_entries(dirpath):
    spec = TIP + ":" + dirpath if dirpath else TIP + ":"
    res = []
    for line in git("ls-tree", spec).splitlines():
        meta, name = line.split("\t", 1)
        res.append((meta.split()[1], f"{dirpath}/{name}" if dirpath else name))
    return res

def count_files(path):
    return len([l for l in git("ls-tree", "-r", "--name-only", TIP, path).splitlines() if l])

def spec_kind(path):
    out = git("ls-tree", TIP, path)
    if not out:
        return None
    return out.split()[1]

done2 = set()
with open(f"{PA}/chunks2.done") as fh:
    done2 = {l.strip() for l in fh if l.strip()}

specs_by_chunk = OrderedDict()
with open(f"{PA}/chunks2.tsv") as fh:
    for line in fh:
        chunk, spec = line.rstrip("\n").split("\t")
        if chunk in done2:
            continue
        specs_by_chunk.setdefault(chunk, []).append(spec)

rows = []

def emit_list(name, specs):
    for i in range(0, len(specs), MAX_LIST):
        part = specs[i:i + MAX_LIST]
        cname = name if len(specs) <= MAX_LIST else f"{name}#{i // MAX_LIST}"
        for s in part:
            rows.append((cname, s))

def emit_dir(name, dirpath):
    if count_files(dirpath) <= MAX_DIR_FILES:
        rows.append((name, dirpath))
        return
    files = [p for t, p in tree_entries(dirpath) if t == "blob"]
    if files:
        emit_list(f"{name}/__files__", files)
    for t, p in tree_entries(dirpath):
        if t == "tree":
            emit_dir(f"{name}/{p.split('/')[-1]}", p)

for chunk, specs in specs_by_chunk.items():
    if len(specs) == 1 and spec_kind(specs[0]) == "tree":
        emit_dir(chunk, specs[0])
    else:
        emit_list(chunk, specs)

chunks = OrderedDict()
for c, s in rows:
    chunks.setdefault(c, []).append(s)
names = list(chunks.keys())
parts = {1: [], 2: [], 3: []}
for i, name in enumerate(names):
    parts[i % 3 + 1].append(name)
for p in (1, 2, 3):
    with open(f"{PA}/chunks3.p{p}.tsv", "w") as fh:
        for name in parts[p]:
            for s in chunks[name]:
                fh.write(f"{name}\t{s}\n")
    print(f"partition {p}: {len(parts[p])} chunks")
print(f"pass3 total: {len(names)} chunks, {len(rows)} pathspecs (from {len(specs_by_chunk)} unfinished pass-2 chunks)")
