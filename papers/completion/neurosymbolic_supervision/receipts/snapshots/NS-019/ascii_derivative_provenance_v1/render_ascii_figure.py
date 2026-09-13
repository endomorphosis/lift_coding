from pathlib import Path
import hashlib, json

results = json.loads(Path("papers/completion/neurosymbolic_supervision/analysis/results.json").read_text())
groups = {(g["unit"], g["arm"]): float(g["useful_mean"]) for g in results["groups"]}
units = [row["unit"] for row in results["paired_family_rows"]]
assert units == [
    "ns-hist-09-tomlkit",
    "ns-hist-10-installer",
    "ns-hist-11-tornado",
    "ns-hist-12-more-itertools",
    "ns-hist-13-charset_normalizer",
    "ns-hist-14-iniconfig",
    "ns-hist-15-wheel",
    "ns-hist-16-jinja",
]

# Page matches the matplotlib SVG canvas (pt).
W, H = 460.8, 302.4
left, right, bottom, top = 132.0, 448.0, 42.0, 268.0
plot_w = right - left
plot_h = top - bottom


def x_of(value: float) -> float:
    return left + (value - (-0.08)) / (1.08 - (-0.08)) * plot_w


def y_of(index: int) -> float:
    # Family 0 at the top, matching invert_yaxis.
    return top - (index + 0.5) * (plot_h / 8.0)


def fmt(n: float) -> str:
    text = f"{n:.3f}"
    text = text.rstrip("0").rstrip(".")
    return text


ops = []
# White background
ops.append("1 1 1 rg 0 0 {:.3f} {:.3f} re f".format(W, H))
# Axes box
ops.append("0 0 0 RG 0.8 w {:.3f} {:.3f} {:.3f} {:.3f} re S".format(left, bottom, plot_w, plot_h))
# X ticks at 0, 0.5, 1
ops.append("/F1 8 Tf 0 0 0 rg")
for tick in (0.0, 0.5, 1.0):
    x = x_of(tick)
    ops.append("0.6 w 0.7 0.7 0.7 RG {:.3f} {:.3f} m {:.3f} {:.3f} l S".format(x, bottom, x, top))
    ops.append("0 0 0 rg BT /F1 8 Tf {:.3f} {:.3f} Td ({}) Tj ET".format(x - 6, bottom - 12, fmt(tick)))
ops.append("BT /F1 8 Tf {:.3f} {:.3f} Td (Useful fraction across two nested repetitions) Tj ET".format(left + 18, 14))
ops.append("BT /F1 9 Tf {:.3f} {:.3f} Td (Eight family blocks: descriptive A/B outcomes) Tj ET".format(left + 28, H - 16))

for i, unit in enumerate(units):
    y = y_of(i)
    label = unit.removeprefix("ns-hist-")
    ops.append("BT /F1 8 Tf 14 {:.3f} Td ({}) Tj ET".format(y - 3, label))
    xa, xb = x_of(groups[unit, "A"]), x_of(groups[unit, "B"])
    ops.append("0.7 0.7 0.7 RG 1 w {:.3f} {:.3f} m {:.3f} {:.3f} l S".format(xa, y, xb, y))
    # A: open circle via four-arc approximation
    r = 4.2
    k = 0.5523 * r
    ops.append("0.141 0.353 0.506 RG 1.2 w")
    ops.append("{0:.3f} {1:.3f} m {2:.3f} {3:.3f} {4:.3f} {5:.3f} {6:.3f} {7:.3f} c {8:.3f} {9:.3f} {10:.3f} {11:.3f} {12:.3f} {13:.3f} c {14:.3f} {15:.3f} {16:.3f} {17:.3f} {18:.3f} {19:.3f} c {20:.3f} {21:.3f} {22:.3f} {23:.3f} {24:.3f} {25:.3f} c S".format(
        xa, y + r,
        xa + k, y + r, xa + r, y + k, xa + r, y,
        xa + r, y - k, xa + k, y - r, xa, y - r,
        xa - k, y - r, xa - r, y - k, xa - r, y,
        xa - r, y + k, xa - k, y + r, xa, y + r,
    ))
    # B: x marker
    s = 3.6
    ops.append("0.651 0.263 0.141 RG 1.2 w {:.3f} {:.3f} m {:.3f} {:.3f} l {:.3f} {:.3f} m {:.3f} {:.3f} l S".format(
        xb - s, y - s, xb + s, y + s, xb - s, y + s, xb + s, y - s
    ))

# Legend
ops.append("0.141 0.353 0.506 RG 1.2 w 360 278 m 360 286 366 292 374 292 c 382 292 388 286 388 278 c 388 270 382 264 374 264 c 366 264 360 270 360 278 c S")
ops.append("0 0 0 rg BT /F1 8 Tf 394 274 Td (A) Tj ET")
ops.append("0.651 0.263 0.141 RG 1.2 w 412 272 m 422 284 l 412 284 m 422 272 l S")
ops.append("0 0 0 rg BT /F1 8 Tf 426 274 Td (B) Tj ET")

content = "\n".join(ops) + "\n"
stream = content.encode("ascii")

objects = []

def add_obj(body: bytes) -> int:
    objects.append(body)
    return len(objects)

add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
add_obj(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
add_obj(
    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 460.8 302.4] "
    b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
)
add_obj(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream")
add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

out = bytearray(b"%PDF-1.4\n")
offsets = [0]
for i, body in enumerate(objects, start=1):
    offsets.append(len(out))
    out.extend(f"{i} 0 obj\n".encode("ascii"))
    out.extend(body)
    if not body.endswith(b"\n"):
        out.extend(b"\n")
    out.extend(b"endobj\n")
startxref = len(out)
out.extend(b"xref\n")
out.extend(f"0 {len(objects)+1}\n".encode("ascii"))
out.extend(b"0000000000 65535 f \n")
for off in offsets[1:]:
    out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
out.extend(b"trailer\n")
out.extend(f"<< /Size {len(objects)+1} /Root 1 0 R >>\n".encode("ascii"))
out.extend(b"startxref\n")
out.extend(f"{startxref}\n".encode("ascii"))
out.extend(b"%%EOF\n")
pdf = bytes(out)

assert pdf.startswith(b"%PDF-")
assert b"\x00" not in pdf
assert pdf.decode("ascii")
controls = sum(byte < 32 and byte not in {9, 10, 12, 13} for byte in pdf[:8192])
assert controls * 20 <= len(pdf[:8192]), controls
print("pdf_bytes", len(pdf), "sha256", hashlib.sha256(pdf).hexdigest())
print("nul", pdf.count(b"\\x00"), "high", sum(1 for b in pdf if b > 127))

paths = [
    Path("papers/completion/neurosymbolic_supervision/manuscript/generated/figures/family_useful.pdf"),
    Path("papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-019/rendered_final32/manuscript/generated/figures/family_useful.pdf"),
]
for path in paths:
    path.write_bytes(pdf)
    print("wrote", path, path.stat().st_size)
