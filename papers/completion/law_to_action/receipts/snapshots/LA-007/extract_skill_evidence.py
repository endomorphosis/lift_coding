#!/usr/bin/python3.12
"""Extract bounded SkillCenter evidence from the pinned LA-004 SQLite bundle.

The bundle is untrusted. This reader opens it read-only and immutable, disables
extension loading, and treats skill_md as inert text. Commands appearing in
Markdown are recorded as quoted data and are never executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/law_to_action"
SOURCES = PAPER / "benchmark/manifests/sources.json"
SPLITS = PAPER / "benchmark/manifests/splits.json"
BUNDLE_SHA256 = "8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4"
BUNDLE_BYTES = 7892992
DATASET_ID = "Tommysha/skillcenter-bundles"
DATASET_REVISION = "f9dd4fec3c86d85ebf116c7408ac5ce602c418a1"
REPOSITORY_FILE = "clawskills-bundle-lite-security-v20260227.sqlite"
SQLITE_HEADER = b"SQLite format 3\x00"
TEXT_BASIS = "exact UTF-8 skill_md; whitespace collapsed with re.sub(r'\\\\s+', ' ', text) for span offsets"
_METADATA_SCALAR_RE = re.compile(
    r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):[ \t]*(?P<value>.*)$",
    re.MULTILINE,
)
_HEADING_RE = re.compile(r"^[ \t]{0,3}(?P<marks>#{1,6})[ \t]+(?P<text>.*?)\s*$")
_COMMAND_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*`>#]+[ \t]+)?("
    r"(?:git clone|composer |pnpm |npm |forge |foundryup|go run|go build|"
    r"python[3]? |uv |docker |pipx |curl |wget |systemctl |php |"
    r"cargo |mvn |make ).+)$"
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def metadata_scalar(yaml_text: str, key: str) -> str:
    for match in _METADATA_SCALAR_RE.finditer(yaml_text or ""):
        if match.group("key") == key:
            return match.group("value").strip().strip("\"'")
    return ""


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def connect_readonly(path: Path) -> sqlite3.Connection:
    if path.read_bytes()[:16] != SQLITE_HEADER:
        raise SystemExit("SkillCenter bundle is not a SQLite 3 database")
    uri = path.resolve().as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.enable_load_extension(False)
    connection.execute("PRAGMA query_only = ON")
    return connection


def section_map(markdown: str) -> dict[str, str]:
    parts: dict[str, str] = {"title": ""}
    fenced = False
    fence_mark = ""
    visible: list[str] = []
    for line in markdown.splitlines():
        fence = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})", line)
        if fence:
            mark = fence.group(1)[0] * len(fence.group(1))
            if not fenced:
                fenced = True
                fence_mark = mark
            elif line.strip().startswith(fence_mark[0] * len(fence_mark)):
                fenced = False
                fence_mark = ""
            visible.append("")
            continue
        visible.append("" if fenced else line)
    chunks = re.split(r"(?m)^(?=#{1,6} )", "\n".join(visible))
    for chunk in chunks:
        if not chunk.strip():
            continue
        first = chunk.splitlines()[0]
        match = _HEADING_RE.match(first)
        if not match:
            continue
        heading = match.group("text").strip()
        body = chunk[len(first) :].strip()
        if match.group("marks") == "#":
            if not parts["title"]:
                parts["title"] = heading
                parts.setdefault("lead", body)
        else:
            parts.setdefault(heading.lower(), body)
    return parts


def unique_quote(normal: str, quote: str) -> dict | None:
    collapsed = normalize(quote).strip()
    if len(collapsed) < 24:
        return None
    if normal.count(collapsed) != 1:
        return None
    start = normal.find(collapsed)
    return {
        "quoted_text": collapsed,
        "normalized_char_start": start,
        "normalized_char_end": start + len(collapsed),
        "quoted_sha256": sha256_text(collapsed),
        "encoding": "utf-8",
        "text_basis": TEXT_BASIS,
        "unique_in_normalized_source": True,
    }


def bullets(text: str) -> list[str]:
    items = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        stripped = re.sub(r"^[-*+]\s+", "", stripped)
        stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
        stripped = stripped.strip("`").strip()
        if stripped:
            items.append(stripped)
    return items


def numbered_steps(text: str) -> list[tuple[int, str]]:
    steps = []
    for match in re.finditer(r"(?m)^\s*(\d+)[.)]\s+(.+)$", text or ""):
        steps.append((int(match.group(1)), match.group(2).strip()))
    return steps


def unique_window(normal: str, section: str, *, min_len: int = 40, max_len: int = 180) -> dict | None:
    collapsed = normalize(section).strip()
    if len(collapsed) < 24:
        return None
    if normal.count(collapsed) == 1:
        quote = collapsed if len(collapsed) <= max_len else collapsed[:max_len].rsplit(" ", 1)[0]
        found = unique_quote(normal, quote)
        if found:
            return found
    length = min(max_len, len(collapsed))
    while length >= min_len:
        for offset in range(0, max(1, len(collapsed) - length + 1), 8):
            candidate = collapsed[offset : offset + length].strip()
            found = unique_quote(normal, candidate)
            if found:
                return found
        length -= 12
    return unique_quote(normal, collapsed)


def first_unique(normal: str, texts: list[str]) -> dict | None:
    for text in texts:
        found = unique_quote(normal, text)
        if found:
            return found
    return None


def collect_quotes(normal: str, sections: dict[str, str], markdown: str) -> list[dict]:
    quotes: list[dict] = []

    def add(role: str, payload: dict | None) -> None:
        if payload is None:
            return
        item = dict(payload)
        item["role"] = role
        item["span_id"] = f"{role}-{len([q for q in quotes if q['role'] == role])}"
        quotes.append(item)

    title = sections.get("title") or ""
    add("goal", unique_quote(normal, title) or unique_window(normal, title or markdown[:180], min_len=24))
    add("assumption", first_unique(normal, bullets(sections.get("background", ""))) or unique_window(normal, sections.get("background", "")))
    for item in bullets(sections.get("use cases", ""))[:2]:
        add("goal", unique_quote(normal, item))
    add("precondition", first_unique(normal, bullets(sections.get("inputs", ""))) or unique_window(normal, sections.get("inputs", "")))
    add("postcondition", first_unique(normal, bullets(sections.get("outputs", ""))) or unique_window(normal, sections.get("outputs", "")))
    add("effect", first_unique(normal, bullets(sections.get("outputs", ""))) or unique_window(normal, sections.get("outputs", "")))
    add("guard", first_unique(normal, bullets(sections.get("safety", ""))) or unique_window(normal, sections.get("safety", "")))
    add("failure", unique_quote(normal, "verification/validation failure") or first_unique(normal, bullets(sections.get("safety", ""))) or unique_window(normal, sections.get("safety", "") or sections.get("outputs", "")))
    add("verification", unique_window(normal, sections.get("verification", ""), min_len=32, max_len=160))
    for index, text in numbered_steps(sections.get("steps", ""))[:4]:
        found = unique_quote(normal, text) or unique_window(normal, text, min_len=24, max_len=160)
        if found:
            found = dict(found)
            found["step_number"] = index
            add("action", found)
    for match in _COMMAND_RE.finditer(markdown):
        found = unique_quote(normal, match.group(1))
        if found:
            add("untrusted_command_text", found)
            break
    sources_section = sections.get("sources", "")
    add("source_locator", first_unique(normal, bullets(sources_section)) or unique_window(normal, sources_section, min_len=24, max_len=120))
    return quotes


def extract_row(family: dict, assignment: dict, artifact: dict, row: sqlite3.Row) -> dict:
    markdown = row["skill_md"] or ""
    library = row["library_md"] or ""
    yaml_text = row["metadata_yaml"] or ""
    normal = normalize(markdown)
    if sha256_text(normal) != family["normalized_source_sha256"]:
        raise SystemExit(f"normalized hash mismatch for {family['source_id']}")
    sections = section_map(markdown)
    quotes = collect_quotes(normal, sections, markdown)
    required = {"goal", "precondition", "postcondition", "guard", "effect", "verification", "action"}
    missing = required - {q["role"] for q in quotes}
    if missing:
        raise SystemExit(f"{family['source_id']} missing unique quotes for {sorted(missing)}")
    command_present = any(q["role"] == "untrusted_command_text" for q in quotes) or bool(
        _COMMAND_RE.search(markdown)
    )
    return {
        "source_id": family["source_id"],
        "lineage_family_id": family["lineage_family_id"],
        "split": assignment["split"],
        "held_out": assignment["split"] != "development",
        "planned_case_ids": assignment["planned_case_ids"],
        "source_locator": family["source_locator"],
        "source_record_sha256": family["source_record_sha256"],
        "normalized_source_sha256": family["normalized_source_sha256"],
        "content_sha256": sha256_text(markdown),
        "library_md_sha256": sha256_text(library),
        "library_md_empty": library == "",
        "skill_md_chars": len(markdown),
        "normalized_chars": len(normal),
        "title": row["title"],
        "domain": row["domain"],
        "profile": row["profile"],
        "skill_kind": row["skill_kind"],
        "language": row["language"],
        "source_type": row["source_type"],
        "source_url": row["source_url"],
        "overall_score": row["overall_score"],
        "license_spdx": metadata_scalar(yaml_text, "license_spdx") or metadata_scalar(yaml_text, "license"),
        "license_risk": metadata_scalar(yaml_text, "license_risk"),
        "llm_provider": metadata_scalar(yaml_text, "llm_provider"),
        "llm_model": metadata_scalar(yaml_text, "llm_model"),
        "word_permitted_present": bool(re.search(r"\bpermitted\b", markdown, re.I)),
        "source_contains_markdown_commands": command_present,
        "ingestion_executed_markdown_commands": False,
        "quotes": quotes,
        "section_names": sorted(k for k in sections if k not in {"lead"}),
        "artifact": {
            "artifact_id": artifact["artifact_id"],
            "sha256": artifact["sha256"],
            "size_bytes": artifact["size_bytes"],
            "source_uri": artifact["source_uri"],
            "revision": artifact["revision"],
            "dataset_id": DATASET_ID,
            "repository_file": REPOSITORY_FILE,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    sqlite_path = Path(args.sqlite)
    if not sqlite_path.is_file():
        raise SystemExit(f"missing SkillCenter bundle: {sqlite_path}")
    if sqlite_path.stat().st_size != BUNDLE_BYTES or file_sha256(sqlite_path) != BUNDLE_SHA256:
        raise SystemExit("SkillCenter bundle SHA-256 or size does not match the LA-004 pin")
    sources = load_json(SOURCES)
    splits = load_json(SPLITS)
    artifact = next(row for row in sources["source_artifacts"] if row["artifact_id"] == "skill-security-bundle")
    families = {row["source_id"]: row for row in sources["source_records"] if row["population"] == "skill"}
    assignments = [row for row in splits["assignments"] if row["population"] == "skill"]
    if len(families) != 12 or len(assignments) != 12:
        raise SystemExit("expected 12 frozen skill families")
    wanted = [families[row["source_id"]]["source_locator"]["skill_id"] for row in assignments]
    connection = connect_readonly(sqlite_path)
    try:
        fetched = {
            row["skill_id"]: row
            for row in connection.execute(
                "SELECT i.skill_id, i.domain, i.profile, i.source_type, i.source_url, "
                "i.title, i.overall_score, i.skill_kind, i.language, i.source_id, "
                "i.primary_source_id, c.metadata_yaml, c.skill_md, c.library_md "
                "FROM skills_index AS i INNER JOIN skills_content AS c USING(skill_id) "
                f"WHERE i.skill_id IN ({','.join('?' * len(wanted))})",
                wanted,
            )
        }
    finally:
        connection.close()
    if set(fetched) != set(wanted):
        raise SystemExit("pinned skill_id set was not recovered from the bundle")
    records = []
    for assignment in assignments:
        family = families[assignment["source_id"]]
        skill_id = family["source_locator"]["skill_id"]
        records.append(extract_row(family, assignment, artifact, fetched[skill_id]))
    payload = {
        "schema": "law-to-action-skill-row-evidence/v1",
        "task_id": "LA-007",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "bundle": {
            "dataset_id": DATASET_ID,
            "dataset_revision": DATASET_REVISION,
            "repository_file": REPOSITORY_FILE,
            "sha256": BUNDLE_SHA256,
            "size_bytes": BUNDLE_BYTES,
            "sqlite_open": "mode=ro&immutable=1; PRAGMA query_only=ON; enable_load_extension(False)",
            "markdown_executed": False,
            "extensions_loaded": False,
        },
        "text_basis": TEXT_BASIS,
        "redistribution": "quoted spans and hashes only; SQLite body remains retrieval_only",
        "records": records,
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = (Path.cwd() / output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    wrote = str(output)
    try:
        wrote = str(output.relative_to(ROOT))
    except ValueError:
        pass
    print(json.dumps({"wrote": wrote, "records": len(records), "markdown_executed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
