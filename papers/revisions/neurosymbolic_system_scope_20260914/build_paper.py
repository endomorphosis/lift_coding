"""Build the working revision in a new, retained directory and check citations."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-id", required=True)
    args = parser.parse_args()
    assert re.fullmatch(r"[A-Za-z0-9_-]+", args.build_id)
    build = ROOT / "build" / args.build_id
    build.mkdir(parents=True)
    # Each successful build retains the complete input tree. Hashes alone are
    # insufficient to rebuild an older increment after subsequent editing.
    manuscript = build / "source_snapshot"
    shutil.copytree(ROOT / "manuscript", manuscript)
    manifest = {str(p.relative_to(manuscript)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(manuscript.rglob("*")) if p.is_file()}
    (build / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copyfile(manuscript / "verified_references.bib", build / "verified_references.bib")
    latex = ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error",
             "-file-line-error", "-output-directory=" + str(build), "main.tex"]
    commands = [(latex, manuscript), (["bibtex", "main"], build), (latex, manuscript), (latex, manuscript)]
    observed = []
    for index, (cmd, cwd) in enumerate(commands, 1):
        with (build / f"command-{index}.log").open("w") as log:
            result = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        observed.append({"argv": cmd, "cwd": str(cwd), "returncode": result.returncode})
        (build / "commands.json").write_text(json.dumps(observed, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"Build command {index} failed; see retained log")
    log = (build / "main.log").read_text()
    assert not re.search(r"(?:Citation|Reference) .+ undefined|There were undefined", log)
    assert "Overfull" not in log, "Inspect and repair overflowing content"
    subprocess.run(["pdftotext", "-layout", str(build / "main.pdf"), str(build / "paper.txt")], check=True)
    text = (build / "paper.txt").read_text()
    assert "50.05%" in text and "4,865" in text and "2,430" in text
    assert "Proof-Carrying Neurosymbolic Supervision" in text
    assert "[TBD]" not in text and "[TO BE FILLED]" not in text
    main_page = re.search(r"newlabel\{paper:main-end\}\{\{[^}]*\}\{(\d+)\}", (build / "main.aux").read_text())
    result = {"source_manifest_sha256": hashlib.sha256((build / "source_manifest.json").read_bytes()).hexdigest(),
              "pdf_sha256": hashlib.sha256((build / "main.pdf").read_bytes()).hexdigest(),
              "main_text_pages": int(main_page.group(1)) if main_page else None,
              "undefined_citations_or_references": False, "overfull_boxes": False,
              "token_figures_present": True, "visual_inspection": "pending",
              "scope": "working revision, not a submission or complete research goal"}
    (build / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    shutil.copyfile(build / "main.pdf", ROOT / "paper.pdf")
    (ROOT / "latest_build.json").write_text(json.dumps({"build": str(build.relative_to(ROOT)), **result}, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
