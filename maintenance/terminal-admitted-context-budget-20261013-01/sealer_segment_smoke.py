"""Pure owned-fixture tests of the audit shard decoder; never create a seal."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

STAGE = Path(__file__).resolve().parent
SOURCE = STAGE / "seal_evidence.py"
OUTPUT = STAGE / "sealer-segment-smoke-report.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def file_pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)


def main():
    os.umask(0o077)
    fd = os.open(SOURCE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    before = os.fstat(fd)
    assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == os.geteuid()
    source = os.pread(fd, 8388609, 0)
    assert len(source) == before.st_size <= 8388608
    source_pin = {"path": str(SOURCE), "bytes": len(source), "sha256": hashlib.sha256(source).hexdigest()}
    namespace = {"__name__": "sealer_segment_smoke_target", "__file__": str(SOURCE)}
    exec(compile(source, str(SOURCE), "exec"), namespace)
    decoder, Custody = namespace["decode_audit_review"], namespace["Custody"]
    outcomes = []
    arrays = {"checks": [
        {"name": "Unicode δ 源 test", "passed": True},
        {"name": "same occurrence", "passed": True},
        {"name": "same occurrence", "passed": True},
        {"name": "last check", "passed": True, "detail": {"retained": [True, 1, "α"]}},
    ], "declared_pin_occurrences": [
        {"where": "origin/0", "path": "callee.py", "bytes": 47, "sha256": "1" * 64},
        {"where": "origin/0", "path": "callee.py", "bytes": 47, "sha256": "1" * 64},
    ]}
    with tempfile.TemporaryDirectory(prefix="sealer-shard-smoke-", dir=STAGE) as temporary:
        base = Path(temporary)

        def fixture():
            root = base / ("case-%02d" % len(outcomes))
            root.mkdir(mode=0o700)
            report_path = root / "review.json"
            directory = root / "review.arrays"
            directory.mkdir(mode=0o700)
            report = {"schema": "terminal-admitted-context-independent-review@2", "passed": True,
                "qualified": True, "check_count": 4, "passed_checks": 4, "failed_checks": 0,
                "blockers": [], "counts": {"declared_pin_occurrences": 2}, "read_pins": [],
                "explicit_container_host_exports": {}, "metadata_only_descriptors": [],
                "input_custody": "Authored pure fixture; no original/native audit origin claimed.",
                "review_independence_scope": "Decoder tests only", "read_only_execution": {}, "limits": {}}
            for name, values in arrays.items():
                chunks = [values[:2], values[2:]] if name == "checks" else [values]
                segments, start = [], 0
                for index, items in enumerate(chunks):
                    path = directory / (name + "-%04d.json" % index)
                    part = {"schema": "terminal-audit-ordered-array-segment@1", "array": name,
                            "index": index, "start": start, "items": deepcopy(items)}
                    write(path, canonical(part) + b"\n")
                    segments.append({"index": index, "start": start, "count": len(items), "pin": file_pin(path)})
                    start += len(items)
                encoded = canonical(values)
                report[name] = {"schema": "terminal-audit-ordered-array@1", "name": name,
                    "count": len(values), "canonical_bytes": len(encoded),
                    "canonical_sha256": hashlib.sha256(encoded).hexdigest(), "segments": segments}
            return report_path, report

        def rewrite_part(report, alter=None, raw_alter=None):
            row = report["checks"]["segments"][0]
            path = Path(row["pin"]["path"])
            part = json.loads(path.read_bytes())
            if alter:
                alter(part)
            raw = canonical(part) + b"\n"
            if raw_alter:
                raw = raw_alter(raw)
            path.write_bytes(raw)
            row["pin"] = file_pin(path)

        def rebind_array(report):
            values = []
            for row in report["checks"]["segments"]:
                values.extend(json.loads(Path(row["pin"]["path"]).read_bytes())["items"])
            raw = canonical(values)
            report["checks"].update(count=len(values), canonical_bytes=len(raw),
                                    canonical_sha256=hashlib.sha256(raw).hexdigest())

        def run(name, mutation=None, expect=True, closing=None):
            path, report = fixture()
            if mutation:
                mutation(report, path)
            custody = Custody()
            refused = False
            try:
                decoded, count = decoder(custody, path, report)
                if closing:
                    closing(report, path)
                custody.recheck()
                if expect:
                    assert decoded["checks"] == arrays["checks"]
                    assert decoded["declared_pin_occurrences"] == arrays["declared_pin_occurrences"]
                    assert count == 3 and len(custody.selected) == 3
            except (ValueError, OSError, KeyError, TypeError):
                refused = True
            finally:
                custody.close()
            assert refused is (not expect), (name, refused, expect)
            outcomes.append({"name": name, "passed": True, "rejected": refused})

        run("Unicode canonical reconstruction and duplicate occurrence preservation")
        run("descriptor unknown field", lambda r, p: r["checks"].update(extra=True), False)
        run("main unknown field", lambda r, p: r.update(extra=True), False)
        run("unsupported report schema", lambda r, p: r.update(schema="terminal-admitted-context-independent-review@9"), False)
        run("wrong array name", lambda r, p: r["checks"].update(name="declared_pin_occurrences"), False)
        run("Boolean descriptor count", lambda r, p: r["checks"].update(count=True), False)
        run("Boolean canonical byte count", lambda r, p: r["checks"].update(canonical_bytes=True), False)
        run("Boolean segment index", lambda r, p: r["checks"]["segments"][0].update(index=False), False)
        run("Boolean segment start", lambda r, p: r["checks"]["segments"][0].update(start=False), False)
        run("zero segment count", lambda r, p: r["checks"]["segments"][0].update(count=0), False)
        run("negative segment count", lambda r, p: r["checks"]["segments"][0].update(count=-1), False)
        run("segment gap", lambda r, p: r["checks"]["segments"][1].update(start=3), False)
        run("reordered segments", lambda r, p: r["checks"]["segments"].reverse(), False)
        run("dropped last segment", lambda r, p: r["checks"]["segments"].pop(), False)
        run("duplicate segment pin", lambda r, p: r["checks"]["segments"][1].update(pin=r["checks"]["segments"][0]["pin"]), False)
        run("unknown segment row field", lambda r, p: r["checks"]["segments"][0].update(extra=1), False)
        run("unknown segment pin field", lambda r, p: r["checks"]["segments"][0]["pin"].update(extra=1), False)
        run("declared segment over8MiB", lambda r, p: r["checks"]["segments"][0]["pin"].update(bytes=8388609), False)
        run("whole array digest mismatch", lambda r, p: r["checks"].update(canonical_sha256="0" * 64), False)
        run("whole canonical size mismatch", lambda r, p: r["checks"].update(canonical_bytes=r["checks"]["canonical_bytes"] + 1), False)
        run("part digest mismatch", lambda r, p: r["checks"]["segments"][0]["pin"].update(sha256="0" * 64), False)
        run("rehashed wrong part index", lambda r, p: rewrite_part(r, lambda v: v.update(index=True)), False)
        run("rehashed wrong part array", lambda r, p: rewrite_part(r, lambda v: v.update(array="other")), False)
        run("rehashed unknown part field", lambda r, p: rewrite_part(r, lambda v: v.update(extra=1)), False)
        run("rehashed noncanonical whitespace", lambda r, p: rewrite_part(r, raw_alter=lambda v: b" " + v), False)
        run("rehashed trailing JSON", lambda r, p: rewrite_part(r, raw_alter=lambda v: v + b"{}"), False)
        run("rehashed duplicate JSON member", lambda r, p: rewrite_part(r, raw_alter=lambda v: b'{"array":"checks",' + v[1:]), False)

        def bool_verdict(r, p):
            rewrite_part(r, lambda v: v["items"][0].update(passed=1))
            rebind_array(r)
        run("rebound integer check verdict", bool_verdict, False)

        def hidden_failure(r, p):
            rewrite_part(r, lambda v: v["items"][0].update(passed=False))
            rebind_array(r)
        run("rebound late hidden failure against passed main", hidden_failure, False)
        run("forged passed count", lambda r, p: r.update(passed_checks=3), False)
        run("Boolean main check count", lambda r, p: r.update(check_count=True), False)
        run("forged blockers", lambda r, p: r.update(blockers=[{"name": "forged", "passed": False}]), False)
        run("wrong declared occurrence census", lambda r, p: r["counts"].update(declared_pin_occurrences=1), False)

        def foreign(r, p):
            old = Path(r["checks"]["segments"][0]["pin"]["path"])
            target = p.parent / "outside.json"
            write(target, old.read_bytes())
            r["checks"]["segments"][0]["pin"] = file_pin(target)
        run("foreign segment outside sibling directory", foreign, False)

        def symlink(r, p):
            row = r["checks"]["segments"][0]
            old = Path(row["pin"]["path"])
            alias = old.parent / "alias.json"
            alias.symlink_to(old)
            row["pin"] = {**row["pin"], "path": str(alias)}
        run("segment symlink", symlink, False)

        def hardlink(r, p):
            row = r["checks"]["segments"][0]
            old = Path(row["pin"]["path"])
            alias = old.parent / "hardlink.json"
            os.link(old, alias)
            row["pin"] = {**row["pin"], "path": str(alias)}
        run("segment hardlink", hardlink, False)
        run("same-byte part replacement at closing", expect=False,
            closing=lambda r, p: replace_same_bytes(Path(r["checks"]["segments"][0]["pin"]["path"])))
    fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    assert tuple(getattr(before, k) for k in fields) == tuple(getattr(os.fstat(fd), k) for k in fields) == tuple(getattr(SOURCE.lstat(), k) for k in fields)
    assert os.pread(fd, 8388609, 0) == source
    os.close(fd)
    assert not (STAGE / "evidence-manifest.json").exists()
    report = {"schema": "terminal-audit-sealer-segment-smoke@1", "qualified": True,
        "counts": {"tests": len(outcomes), "unique_tests": len(outcomes), "failures": 0, "errors": 0, "skips": 0},
        "cases": outcomes, "sealer_before": source_pin, "sealer_after": file_pin(SOURCE),
        "producer": file_pin(Path(__file__).resolve()), "source_bytes_unchanged": True,
        "genuine_owned_fixture_FD_stat_hash_checks_used": True,
        "audit_or_seal_invocations": 0, "native_service_calls": 0, "native_prover_invocations": 0,
        "provider_calls": 0, "runtime_sources_or_tests_edited": False,
        "scope": "Pure decoder fixtures only; no real audit outcome, runtime origin or final evidence seal claimed."}
    write(OUTPUT, canonical(report) + b"\n")
    print(json.dumps({"qualified": True, "counts": report["counts"], "report": file_pin(OUTPUT),
                      "sealer": source_pin}, sort_keys=True))


def replace_same_bytes(path):
    replacement = path.with_name(path.name + ".replacement")
    write(replacement, path.read_bytes())
    os.replace(replacement, path)


if __name__ == "__main__":
    main()
