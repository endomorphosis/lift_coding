"""Structural audit for NS-021 reference, artifact-citation, and overlap records.

This program reads local paper-completion files only. It does not call Crossref,
edit the manuscript, invoke a prover, or treat snapshot presence as a scientific
result. Stdlib only: sealed validation PATH has no extra packages.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
AUDIT = PAPER / "audit"
EXTRACT = PAPER / "paper_extracted.txt"
SNAPSHOT = PAPER / "receipts/snapshots/NS-021"
CURRENT = {
    "reference_audit.md": AUDIT / "reference_audit.md",
    "artifact_citation_map.json": AUDIT / "artifact_citation_map.json",
    "related_paper_overlap.md": AUDIT / "related_paper_overlap.md",
    "verified_references.bib": AUDIT / "verified_references.bib",
}
EXPECTED_KEYS = [f"baseline{i:02d}" for i in range(1, 13)]
EXPECTED_DOI = {
    "baseline01": "10.1145/263699.263712",
    "baseline02": "10.1145/512950.512973",
    "baseline03": "10.1007/10722167_15",
    "baseline04": "10.1007/BFb0054170",
    "baseline06": "10.1145/3434304",
    "baseline07": "10.1145/3236774",
    "baseline08": "10.52202/079017-1601",
    "baseline09": "10.52202/075280-0944",
    "baseline10": "10.52202/068431-0608",
    "baseline11": "10.52202/079017-2601",
    "baseline12": "10.18653/v1/2024.findings-acl.57",
}
DISSERTATION_MARKERS = ("Solar-Lezama", "Program Synthesis by Sketching", "EECS-2008-176", "2008")
FORBIDDEN_IN_OUTPUTS = (
    "github.com",
    "overleaf.com",
    "hallucinate_app",
    "/home/barberb",
    "ipfs_accelerate_py",
    "ipfs_datasets_py",
    "ipfs_kit_py",
)
NOVELTY_FORBIDDEN = (
    "first neurosymbolic agent",
    "first-of-kind",
    "first of its kind",
    "we are the first",
    "novel algorithm for proof-carrying",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise AssertionError(message)


def parse_bib(text: str) -> dict[str, str]:
    uncommented = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))
    entries: dict[str, str] = {}
    for match in re.finditer(
        r"@(?P<kind>[A-Za-z]+)\s*\{\s*(?P<key>baseline\d{2})\s*,(?P<body>.*?)\n\}",
        uncommented,
        re.S,
    ):
        key = match.group("key").strip()
        entries[key] = match.group("kind").lower() + "\n" + match.group("body")
    return entries


def field(body: str, name: str) -> str | None:
    match = re.search(rf"{name}\s*=\s*[\{{](.+?)[\}}]\s*,?", body, re.S | re.I)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def expand_labels(text: str) -> set[str]:
    labels: set[str] = set()
    for raw in re.findall(r"\[([^\[\]]{1,120})\]", text):
        blob = re.sub(r"\s+", "", raw)
        if not re.search(r"[A-Z]{1,5}\d", blob):
            continue
        for match in re.finditer(r"([A-Z]{1,5})(\d+)(?:[–—-](\d+))?", blob):
            prefix, start, end = match.group(1), int(match.group(2)), match.group(3)
            last = int(end) if end else start
            if last < start or last - start > 20:
                fail(f"implausible label range {match.group(0)}")
            for number in range(start, last + 1):
                labels.add(f"{prefix}{number}")
    for name in ("ASEH", "DOEP", "PCPR", "PCSM", "PCTDD"):
        if re.search(rf"\b{name}\b", text):
            labels.add(name)
    if re.search(r"\bM[123]\b", text):
        labels.update({"M1", "M2", "M3"})
    return labels


def check_bib(text: str) -> None:
    if "@misc{baseline01" in text and "note = {George C. Necula" in text:
        fail("verified bibliography still contains unrecovered note-only transcriptions")
    entries = parse_bib(text)
    if list(entries) != EXPECTED_KEYS:
        fail(f"expected keys {EXPECTED_KEYS}, found {list(entries)}")
    kinds = {key: entries[key].split("\n", 1)[0] for key in EXPECTED_KEYS}
    if kinds["baseline05"] != "phdthesis":
        fail("baseline05 must be a phdthesis record")
    if kinds["baseline01"] != "inproceedings" or kinds["baseline06"] != "article":
        fail("baseline01/baseline06 record types are wrong")
    for key, body in entries.items():
        if field(body, "author") is None or field(body, "title") is None or field(body, "year") is None:
            fail(f"{key} missing author/title/year")
        if "github.com" in body.lower() or "overleaf.com" in body.lower():
            fail(f"{key} contains an identifying repository link")
        if key == "baseline05":
            blob = body
            if any(marker not in blob and marker not in text for marker in DISSERTATION_MARKERS[:3]):
                if "EECS-2008-176" not in text or "Solar-Lezama" not in body:
                    fail("dissertation record missing verified catalog identity")
            if "EECS-2008-164" in body:
                fail("dissertation cites the wrong EECS report number")
            continue
        doi = field(body, "doi")
        if doi is None:
            fail(f"{key} missing doi")
        if doi != EXPECTED_DOI[key]:
            fail(f"{key} doi {doi} != {EXPECTED_DOI[key]}")
    if "et al." in field(entries["baseline12"], "author") or "et al." in entries["baseline12"]:
        fail("baseline12 still uses et al. instead of the verified author list")
    if "263699.263712" not in entries["baseline01"] or "10.1145/ " in text:
        fail("baseline01 DOI still contains the draft line-wrap space")


def check_audit(text: str, bib: str) -> None:
    for key, doi in EXPECTED_DOI.items():
        if doi not in text:
            fail(f"reference_audit.md missing {key} DOI {doi}")
    for marker in DISSERTATION_MARKERS:
        if marker not in text:
            fail(f"reference_audit.md missing dissertation marker {marker}")
    if "EECS-2008-164" in text and "different" not in text.lower():
        fail("reference_audit.md cites EECS-2008-164 without rejecting it")
    if text.lower().count("supported") < 12:
        fail("reference_audit.md does not record support for each of the 12 entries")
    for phrase in (
        "not newly invented algorithms",
        "do not claim that this is the first neurosymbolic agent",
        "composition at the agent's operational boundary",
        "does not add a priority claim",
    ):
        if phrase not in text.lower() and phrase not in text:
            # allow curly apostrophe
            folded = text.replace("’", "'").lower()
            if phrase.lower() not in folded:
                fail(f"reference_audit.md missing novelty bound: {phrase}")
    if "NS-022" not in text:
        fail("reference_audit.md must assign manuscript integration to NS-022")
    if field(parse_bib(bib)["baseline12"], "author") is None:
        fail("audit/bib inconsistency")


def check_map(data: dict, extract: str) -> None:
    if data.get("schema") != "neurosymbolic-supervision/artifact-citation-map@1":
        fail("artifact map schema mismatch")
    if data.get("unresolved_internal_shorthand_in_these_outputs") is not False:
        fail("map must declare unresolved shorthand false")
    if data.get("identifying_repository_link_in_these_outputs") is not False:
        fail("map must declare identifying links false")
    labels = data.get("labels")
    if not isinstance(labels, list) or not labels:
        fail("artifact map has no labels")
    by_id = {}
    for item in labels:
        if not isinstance(item, dict) or not item.get("id"):
            fail("label entry missing id")
        lid = item["id"]
        if lid in by_id:
            fail(f"duplicate label {lid}")
        by_id[lid] = item
        disposition = item.get("disposition")
        if disposition not in {
            "replace_with_anonymous_artifact",
            "replace_with_scientific_description",
            "remove_from_submission",
        }:
            fail(f"{lid} has invalid disposition {disposition}")
        rec = item.get("recommended_in_text")
        if not isinstance(rec, str) or not rec.strip():
            fail(f"{lid} missing recommended_in_text")
        if disposition != "remove_from_submission":
            if not item.get("scientific_role"):
                fail(f"{lid} missing scientific_role")
            anon = item.get("anonymous_citation")
            if anon is not None and not str(anon).startswith("anon-supplement:"):
                fail(f"{lid} anonymous_citation is not an anonymous supplement id")
            if item.get("identifying") is True:
                fail(f"{lid} marked identifying but not removed")
        if item.get("identifying") is True and disposition != "remove_from_submission":
            fail(f"identifying label {lid} must be removed")
        if any(bad in json.dumps(item).lower() for bad in ("github.com", "overleaf.com")):
            fail(f"{lid} contains an identifying URL")
    required = expand_labels(extract)
    missing = sorted(required - set(by_id))
    if missing:
        fail(f"artifact map missing extract labels: {missing}")
    for name in ("ASEH", "DOEP", "PCPR", "PCSM", "PCTDD", "B1", "D1", "W1", "N9"):
        if name not in by_id:
            fail(f"artifact map missing required token {name}")
    if by_id["B1"]["disposition"] != "remove_from_submission":
        fail("B1 author-local worktree must be removed")
    if not data.get("author_only_material"):
        fail("author-only H.3/K.2 material must be listed")
    if data.get("manuscript_application") != "NS-022":
        fail("manuscript application must remain NS-022")


def check_overlap(text: str) -> None:
    folded = text.replace("’", "'").lower()
    for phrase in (
        "do not triple-count",
        "not shared experiments",
        "distinct research question",
        "not the first neurosymbolic agent",
        "table 5",
        "translation validation",
        "thor",
        "independent oracles",
        "unavailable proving is not three independent negative results",
    ):
        if phrase not in folded:
            fail(f"related_paper_overlap.md missing {phrase}")
    if "double-count" not in folded and "triple-count" not in folded:
        fail("overlap audit does not forbid double-counting shared evidence")
    if "github.com" in folded or "overleaf.com" in folded:
        fail("overlap audit contains an identifying repository link")


def check_anonymity(outputs: dict[str, str]) -> None:
    for name, text in outputs.items():
        lowered = text.lower()
        for bad in FORBIDDEN_IN_OUTPUTS:
            if bad.lower() in lowered:
                fail(f"{name} contains identifying token {bad}")
        for phrase in NOVELTY_FORBIDDEN:
            if phrase not in lowered:
                continue
            negated = any(
                token in lowered
                for token in (
                    "do not claim that this is the first neurosymbolic agent",
                    "does not claim to be the first neurosymbolic agent",
                    "without invented first-of-kind",
                    "no invented first-of-kind",
                    "does not add a priority claim",
                )
            )
            if not negated:
                fail(f"{name} contains unbounded novelty language: {phrase}")


def check_snapshots() -> None:
    for name, current in CURRENT.items():
        snap = SNAPSHOT / name
        if not snap.is_file():
            fail(f"missing snapshot {snap}")
        if digest(current) != digest(snap):
            fail(f"current {name} differs from snapshot")


def main() -> None:
    if not EXTRACT.is_file():
        fail("missing paper_extracted.txt")
    extract = EXTRACT.read_text(encoding="utf-8")
    outputs = {name: path.read_text(encoding="utf-8") for name, path in CURRENT.items()}
    check_bib(outputs["verified_references.bib"])
    check_audit(outputs["reference_audit.md"], outputs["verified_references.bib"])
    check_map(json.loads(outputs["artifact_citation_map.json"]), extract)
    check_overlap(outputs["related_paper_overlap.md"])
    check_anonymity(outputs)
    check_snapshots()
    print("NS-021 reference/artifact/overlap audit: OK")
    print("entries=12; internal_labels_mapped=yes; identifying_links_in_outputs=no")
    print("novelty_first_of_kind=false; shared_evidence_double_counted=false")
    print("manuscript_not_edited=NS-022")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"NS-021 validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
