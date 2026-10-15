#!/usr/bin/env python3
"""Pass-2 chunk generator: take the NOT-DONE chunks from chunks.tsv and
re-split them into fine-grained chunks (dir subtrees of <=250 tip-tree
files; file lists chunked at <=120 pathspecs). Completion ground truth at
the end is `git status` vs the tip, not chunk bookkeeping."""
import subprocess
from collections import OrderedDict

TIP = "f4a823231ad52c9252504810a1b00ed4738346b6"
REPO = "/home/hatch/workspace/lift_coding/external/ipfs_datasets"
PA = "/home/hatch/workspace/lift_coding/visual_check/fv_state/pin_advance"
MAX_DIR_FILES = 250
MAX_LIST = 120

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

def is_dir_in_tip(path):
    out = git("ls-tree", TIP, path)
    return bool(out) and out.split()[1] == "tree" if out else False

done = set()
try:
    with open(f"{PA}/chunks.done") as fh:
        done = {l.strip() for l in fh if l.strip()}
except FileNotFoundError:
    pass

specs_by_chunk = OrderedDict()
with open(f"{PA}/chunks.tsv") as fh:
    for line in fh:
        chunk, spec = line.rstrip("\n").split("\t")
        if chunk in done:
            continue
        specs_by_chunk.setdefault(chunk, []).append(spec)

rows = []  # (chunk2_name, pathspec)

def emit_list(name, specs):
    for i in range(0, len(specs), MAX_LIST):
        part = specs[i:i + MAX_LIST]
        cname = name if len(specs) <= MAX_LIST else f"{name}#{i // MAX_LIST}"
        for s in part:
            rows.append((cname, s))

def emit_dir(name, dirpath):
    n = count_files(dirpath)
    if n <= MAX_DIR_FILES:
        rows.append((name, dirpath))
        return
    # split: immediate files as a list chunk, each child dir recursively
    files = [p for t, p in tree_entries(dirpath) if t == "blob"]
    if files:
        emit_list(f"{name}/__files__", files)
    for t, p in tree_entries(dirpath):
        if t == "tree":
            emit_dir(f"{name}/{p.split('/')[-1]}", p)

for chunk, specs in specs_by_chunk.items():
    if len(specs) == 1 and is_dir_in_tip(specs[0]):
        emit_dir(chunk, specs[0])
    else:
        emit_list(chunk, specs)

out_path = f"{PA}/chunks2.tsv"
with open(out_path, "w") as fh:
    for c, s in rows:
        fh.write(f"{c}\t{s}\n")
chunks = OrderedDict()
for c, s in rows:
    chunks.setdefault(c, []).append(s)
print(f"pass2: {len(chunks)} chunks, {len(rows)} pathspecs (from {len(specs_by_chunk)} unfinished pass-1 chunks)")
