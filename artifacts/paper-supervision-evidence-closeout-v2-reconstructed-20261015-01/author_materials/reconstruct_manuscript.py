#!/usr/bin/env python3
"""Reconstruct a labeled reading view from one retained paper snapshot.

Standard-library Python plus the already-installed pdftotext executable.
No TeX build, solver, model, package-root import, or source mutation occurs.
Every output is created exclusively: choose a fresh output directory to rerun.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


TITLE = "Proof-Carrying Neurosymbolic Supervision: State, Reasoning, and Evidence Reuse"
PDF_SHA256 = "51a72d60c7dcb23faa17918091fe172f6cbacf8f25df10e94d1b4071dce05ce7"
MANIFEST_SHA256 = "2f774bd2b3b32b868e3ff72775cbfbbf205921ca387267f7d6c51e61c2390f8b"
INPUT_PATTERN = re.compile(r"\\input\{([^}]+)\}")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular nonsymlink file: {path}")
    return path.read_bytes()


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink():
        raise ValueError(f"Refusing symlink output directory: {path.parent}")
    with path.open("xb") as stream:
        stream.write(data)
    path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected-build", required=True, type=Path)
    parser.add_argument("--output-package", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    build = args.selected_build.resolve(strict=True)
    target = args.output_package.resolve()
    snapshot = build / "source_snapshot"
    if snapshot.is_symlink():
        raise ValueError("Source snapshot must not be a symlink")
    manifest_bytes = read_regular(build / "source_manifest.json")
    if digest(manifest_bytes) != MANIFEST_SHA256:
        raise ValueError("Selected manifest differs from increment-016 identity")
    manifest = json.loads(manifest_bytes)
    checked = []
    for relative, expected in sorted(manifest.items()):
        path = snapshot / relative
        if path.resolve().is_relative_to(snapshot.resolve()) is False:
            raise ValueError("Manifest member escapes selected source snapshot")
        actual = digest(read_regular(path))
        if actual != expected:
            raise ValueError(f"Retained manifest mismatch: {relative}")
        checked.append({"path": relative, "sha256": actual})
    pdf = read_regular(build / "main.pdf")
    if digest(pdf) != PDF_SHA256:
        raise ValueError("Selected PDF differs from increment-016 identity")

    extraction = subprocess.run(
        ["pdftotext", "-layout", str(build / "main.pdf"), "-"],
        check=True, capture_output=True,
    )
    retained_text = read_regular(build / "paper.txt")
    if extraction.stdout != retained_text:
        raise ValueError("Fresh text extraction differs from retained paper.txt")
    version = subprocess.run(
        ["pdftotext", "-v"], check=True, capture_output=True, text=True,
    ).stderr.splitlines()[0]
    pages = retained_text.decode("utf-8").split("\f")
    if pages[-1].strip():
        raise ValueError("Expected a final empty form-feed segment")
    pages.pop()
    if len(pages) != 37:
        raise ValueError("Expected exactly 37 retained PDF pages")
    if not re.search(r"^\s*412\s+References\s*$", pages[10], re.MULTILINE):
        raise ValueError("References boundary does not match selected snapshot")
    if not re.search(r"^\s*454\s+A\s+Full conditional argument record\s*$", pages[11], re.MULTILINE):
        raise ValueError("Appendix boundary does not match selected snapshot")
    if "NeurIPS Paper Checklist" not in pages[30]:
        raise ValueError("Checklist boundary does not match selected snapshot")

    header = read_regular(snapshot / "header.tex").decode("utf-8")
    title = re.search(r"\\title\{([^\n]+)\}", header).group(1)
    title = " ".join(title.replace("\\\\", " ").split())
    if title != TITLE:
        raise ValueError("Selected LaTeX title does not match expected title")
    abstract_source = read_regular(snapshot / "fragments/abstract.tex").decode("utf-8")
    abstract = abstract_source.removeprefix("\\begin{abstract}\n")
    abstract = abstract.removesuffix("\\end{abstract}\n").replace("\\%", "%")
    abstract = " ".join(abstract.split()) + "\n"
    if "\\" in abstract:
        raise ValueError("Unexpected LaTeX construct in abstract normalization")
    main_source = read_regular(snapshot / "main.tex").decode("utf-8")
    main_prefix, appendix_suffix = main_source.split("\\appendix\n", 1)
    orders = {"main": [], "appendices": []}

    def expand(text, section, active=()):
        def replace(match):
            relative = match.group(1) + ".tex"
            if relative not in manifest or relative in active:
                raise ValueError(f"Unmanifested or recursive input: {relative}")
            content = read_regular(snapshot / relative).decode("utf-8")
            orders[section].append({"path": relative, "sha256": manifest[relative]})
            return (
                "\n% BEGIN retained input: " + relative + "\n"
                + expand(content, section, active + (relative,))
                + "\n% END retained input: " + relative + "\n"
            )
        return INPUT_PATTERN.sub(replace, text)

    main_assembly = expand(main_prefix, "main")
    appendix_assembly = "\\appendix\n" + expand(appendix_suffix, "appendices")
    common = (
        "> Reconstructed local reading view, created after the operator requested a new package. "
        "This is not the missing supplied v2 revision package. It uses only retained increment-016; "
        "its relationship to the originally supplied named PDF is unverified. Historical claims "
        "are transcribed, not newly authenticated or rerun.\n\n"
        "The selected [PDF](../source_reference/main.pdf) and "
        "[LaTeX source snapshot](../source_reference/source_snapshot/main.tex) are preserved separately. "
        "The first part below is the exact `pdftotext -layout` reading view with page boundaries and "
        "original line numbers. PDF extraction can alter mathematical glyphs, ligatures, table layout, "
        "and hyphenation; do not use that text to reconstruct equations. The second part preserves "
        "the mathematical LaTeX expressions in an ordered source assembly. Original individual "
        "file bytes, not the inserted boundary comments, remain authoritative.\n\n"
    )

    def page_view(indices):
        sections = []
        for index in indices:
            sections.append(f"### PDF page {index + 1}\n\n````text\n{pages[index]}\n````\n")
        return "\n".join(sections)

    assembly_note = (
        "This partial assembly replaces only manifest-listed `\\input{...}` directives with their "
        "verbatim UTF-8 source text in `main.tex` order and inserts labeled comments. It is provided "
        "for exact formulas and source review, not as a standalone compilable document. Bibliography "
        "and figure commands remain as in the original; their retained files are in the source snapshot. "
        "No empirical sentence or equation is editorially corrected here.\n\n"
    )
    main_md = (
        "# " + TITLE + "\n\n" + common
        + "The main body occupies PDF pages 1–10; References occupies page 11. "
        "This observed main-text span exceeds the requested nine-page limit. No new build or "
        "style-conformance check was performed.\n\n"
        + "## PDF reading view: main body and references\n\n" + page_view(range(11))
        + "\n## Exact ordered LaTeX source: main assembly\n\n" + assembly_note
        + "````latex\n" + main_assembly + "\n````\n"
    )
    appendices_md = (
        "# Appendices and checklist — retained increment-016\n\n" + common
        + "Appendices occupy PDF pages 12–30; the original checklist occupies pages 31–37. "
        "These labels describe the selected historical document, not the missing v2 manuscript.\n\n"
        + "## PDF reading view: appendices and checklist\n\n" + page_view(range(11, 37))
        + "\n## Exact ordered LaTeX source: appendix assembly\n\n" + assembly_note
        + "````latex\n" + appendix_assembly + "\n````\n"
    )
    outputs = {
        "manuscript/main.md": main_md.encode("utf-8"),
        "manuscript/appendices.md": appendices_md.encode("utf-8"),
        "manuscript/abstract.txt": abstract.encode("utf-8"),
    }
    record = {
        "schema": "paper-manuscript-reconstruction/v1",
        "status": "reconstructed_local_base_not_supplied_v2",
        "title": TITLE,
        "selected_build": str(build),
        "selection_basis": "Operator requested a new package; increment-016 selected as one exact-title retained 37-page base, not as an identity proof.",
        "supplied_pdf_identity_bound": False,
        "selected_pdf_sha256": PDF_SHA256,
        "source_manifest_sha256": MANIFEST_SHA256,
        "source_manifest_members_verified": len(checked),
        "source_manifest_members": checked,
        "retained_text_sha256": digest(retained_text),
        "fresh_pdftotext_equals_retained_text": True,
        "pdftotext_version": version,
        "pdftotext_stderr_bytes": len(extraction.stderr),
        "commands": [
            ["pdftotext", "-layout", str(build / "main.pdf"), "-"],
            ["pdftotext", "-v"],
            ["python3", "author_materials/reconstruct_manuscript.py", "--selected-build", str(build), "--output-package", "FRESH_OUTPUT_DIRECTORY"],
        ],
        "script_sha256": digest(Path(__file__).read_bytes()),
        "page_count": 37,
        "main_text_pages_observed": 10,
        "page_split": {
            "main_body": [1, 10], "references": [11, 11],
            "appendices": [12, 30], "checklist": [31, 37],
        },
        "split_rules": [
            "Split retained text on form feed; remove only the last empty segment.",
            "Require 37 pages, line 412 References on page 11, line 454 Appendix A heading on page 12, and checklist heading on page 31.",
            "Preserve every page's extracted text inside a fenced block; add Markdown page labels.",
            "Split original main.tex once at its literal appendix directive; recursively expand only manifest-listed input directives in original order.",
            "Preserve all non-input source text, with inserted BEGIN/END comments identifying each included file.",
            "Normalize abstract whitespace, remove its abstract environment, and replace only the escaped percent sign.",
        ],
        "source_include_order": orders,
        "abstract_source_sha256": manifest["fragments/abstract.tex"],
        "abstract_is": "Whitespace-normalized author-written abstract, not a model prediction or new summary.",
        "cross_ir_named_terms_in_selected_main_source": {
            term: term in main_assembly
            for term in ["IntentIR", "CodebaseIR", "SecurityIR", "LegalIR", "UI/UX IR"]
        },
        "limitations": [
            "The supplied v2 package and its PDF-to-source identity remain unavailable; this reconstruction does not establish that relationship.",
            "The exact-title candidate increment-015 also has 37 pages; selection of increment-016 does not prove which one the user originally supplied.",
            "Fresh extraction equality binds this reading view to the retained selected PDF, not to originating experiments or a new build.",
            "PDF text can damage mathematical typography; the original LaTeX expressions are preserved separately in the source assembly and copied snapshot.",
            "The body of selected Section 2 does not explicitly name the requested five-IR chain; the missing v2 Section 2 and Appendix G must not be inferred from this base.",
            "No historical result, checklist answer, proof-scope claim, or training status was updated during reconstruction.",
            "Ten observed main-text pages exceed the requested nine-page limit; original style authenticity and anonymity were not independently established.",
            "The expanded LaTeX segments are review derivatives, not standalone compilation inputs and not signed originals.",
        ],
        "outputs": [
            {"path": path, "bytes": len(data), "sha256": digest(data)}
            for path, data in outputs.items()
        ],
        "source_mutated": False,
        "new_build_run": False,
        "solver_run": False,
        "model_call_run": False,
    }
    for relative, data in outputs.items():
        write_new(target / relative, data)
    write_new(
        target / "author_materials/manuscript_reconstruction.json",
        (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )
    print(json.dumps({
        "status": record["status"], "verified_manifest_members": len(checked),
        "page_count": 37, "main_text_pages": 10,
        "outputs": record["outputs"],
    }, indent=2))


if __name__ == "__main__":
    main()
