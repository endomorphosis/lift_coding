from __future__ import annotations

import copy
import hashlib
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_children as children
import finite_proof_toolchain_custody as tool
import portable_evidence_children as capsule
import portable_review as portable
import release_matrix as matrix
import test_evidence_children as fixtures


def fixture_group(group, offset):
    # Synthetic producer declarations; binary and Python payloads are deliberately inert.
    source = b"raise RuntimeError('fixture source must never execute')\n"
    driver = b"raise RuntimeError('fixture driver must never execute')\n"
    domain = [-2, -1, 0, 1, 2]
    domain_cid = tool.cid({"unavailable_domain_preimage_recipe": domain})
    rows = [
        {"input": n, "input_type": "int", "output": n + offset, "output_type": "int"}
        for n in domain
    ]
    contract = {
        "schema": "codebase-integer-offset-contract@1",
        "function_name": "increment",
        "offset": 2,
        "parameter": "n",
        "path": "calc.py",
        "profile": "python-integer-offset@1",
    }
    declarations = {
        "lean": {
            "path": "/unavailable/toolchain/bin/lean",
            "sha256": "a" * 64,
            "size_bytes": 13824,
        },
        "python": {
            "path": "/unavailable/python/bin/python",
            "sha256": "b" * 64,
            "size_bytes": 7000000,
        },
    }
    policy = {
        "schema": "codebase-finite-integer-tools@1",
        "profile": "python-integer-offset-finite@1",
        **declarations,
        "environment": {
            "LANG": "C",
            "LC_ALL": "C",
            "LEAN_NUM_THREADS": "1",
            "LEAN_STACK_SIZE_KB": "8192",
            "PATH": "/usr/bin:/bin",
        },
        "process_limits": {
            "lean": {"address_space_bytes": 4096, "resident_memory_bytes": 2048},
            "python": {"address_space_bytes": 2048, "resident_memory_bytes": 1024},
            "lean_arguments": ["-j", "1", "-o", "FiniteInteger.olean", "FiniteInteger.lean"],
            "max_input_bytes": 262144,
            "max_output_bytes": 262144,
            "max_output_files": 8,
            "max_workspace_bytes": 4194304,
            "memory_control": "Recorded finite limits, no hard aggregate assurance",
        },
        "dependency_scope": "Compiled imports, stdlib and shared libraries are not transitively attested.",
    }
    policy["policy_cid"] = tool.cid(policy)

    def process(command, kind, stdout=""):
        return {
            "cancelled": False,
            "command": command,
            "elapsed_ms": 1,
            "error": "",
            "interface_version": "bounded-tool-runner/v1",
            "limits": {
                **policy["process_limits"][kind],
                "cpu_seconds": 120,
                "timeout_ms": 1000,
                **{
                    k: policy["process_limits"][k]
                    for k in (
                        "max_input_bytes",
                        "max_output_bytes",
                        "max_output_files",
                        "max_workspace_bytes",
                    )
                },
            },
            "output_truncated": False,
            "process_tree_terminated": False,
            "resource_exhausted": False,
            "returncode": 0,
            "stderr": "",
            "stdout": stdout,
            "termination_reason": "completed",
            "timed_out": False,
            "unavailable": False,
            "workspace_cleaned": True,
            "workspace_limit_exceeded": False,
        }

    trace = {
        "schema": "codebase-finite-integer-trace@1",
        "status": "complete",
        "exception_type": None,
        "inputs": domain,
        "observations": rows,
        "domain_cid": domain_cid,
        "source_cid": tool.raw_cid(source),
        "source_sha256": matrix.sha(source),
        "python": {
            "cache_tag": "cpython-312",
            "executable": declarations["python"]["path"],
            "implementation": "cpython",
            "version": "3.12.3 recorded synthetic fixture",
        },
    }
    request = {
        "domain_cid": domain_cid,
        "function_name": "increment",
        "inputs": domain,
        "source_cid": tool.raw_cid(source),
        "source_sha256": matrix.sha(source),
    }
    compiled = {
        "schema": "codebase-integer-offset-compilation@1",
        "assumptions": ["Recorded finite fixture assumption"],
        "behavior_authority": False,
        "body_offset": offset,
        "compilation": {"opaque": "retained typed model declaration"},
        "contract": contract,
        "contract_cid": tool.cid(contract),
        "kernel_checked": False,
        "parser": "cpython-312",
        "profile": "python-integer-offset@1",
        "revision": "snapshot:fixture",
        "source_binding": {"content_sha256": matrix.sha(source)},
        "source_cid": tool.raw_cid(source),
    }
    names = [
        "domain_coverage",
        "recorded_integer_types",
        "observed_body_offset",
        "offset_clause" if offset == 2 else "offset_counterexample",
    ]
    lean = (
        "import Init\n" + "".join("theorem " + n + " : True := by trivial\n" for n in names)
    ).encode()
    olean = b"not-a-loadable-proof-binary\x00" + str(offset).encode()
    lean_proc = {
        "process": process(
            [declarations["lean"]["path"], *policy["process_limits"]["lean_arguments"]], "lean"
        ),
        "version_process": process(
            [declarations["lean"]["path"], "--version"],
            "lean",
            "Lean (version 4.34.1, aarch64-unknown-linux-gnu, synthetic recorded fixture)\n",
        ),
    }
    certificate = {
        "schema": "codebase-finite-integer-table-certificate@1",
        "scope": "Recorded finite table only",
        "domain_cid": domain_cid,
        "olean_cid": tool.raw_cid(olean),
        "source_cid": tool.raw_cid(lean),
        "trace_cid": tool.cid(trace),
        "theorems": names,
        "tool": declarations["lean"],
        **lean_proc,
    }
    py_proc = process(
        [declarations["python"]["path"], "-I", "-S", "driver.py"],
        "python",
        tool.canonical_json(trace).decode() + "\n",
    )
    raw = {
        "source": source,
        "driver": driver,
        "lean_source": lean,
        "lean_olean": olean,
        **{
            name: matrix.json_bytes(value)
            for name, value in (
                ("compiled", compiled),
                ("request", request),
                ("trace", trace),
                ("python_process", py_proc),
                ("lean_certificate", certificate),
                ("lean_process", lean_proc),
                ("tool_policy", policy),
            )
        },
    }
    output = "/recorded/native/" + group
    result = {
        "artifacts": {
            role: {
                "path": output + "/" + tool.ROLES[role],
                "sha256": matrix.sha(body),
                "size_bytes": len(body),
                "cid": tool.raw_cid(body),
            }
            for role, body in raw.items()
        },
        **{
            flag: False
            for flag in (
                "behavior_authority",
                "completion_authority",
                "execution_authority",
                "mutation_authority",
                "proof_authority",
                "runtime_behavior_verified",
                "source_semantics_verified",
            )
        },
        "compiled_cid": tool.cid(compiled),
        "contract": contract,
        "contract_cid": tool.cid(contract),
        "counterexample": {"input": -2, "observed_output": -1, "required_output": 0}
        if offset == 1
        else None,
        "diagnostics": [],
        "domain_cid": domain_cid,
        "domain_inputs": domain,
        "head": {"schema": "codebase-head@1", "generation": 1, "snapshot_cid": "recorded:fixture"},
        "kernel_checked_model_table": True,
        "lean_certificate": certificate,
        "observations": rows,
        "offset_clause_satisfied": offset == 2,
        "output": output,
        "profile": "python-integer-offset-finite@1",
        "python_process": py_proc,
        "runtime_observation_coverage_complete": True,
        "schema": "codebase-finite-integer-observation@1",
        "scope": "Recorded finite table, no runtime theorem",
        "source_cid": tool.raw_cid(source),
        "source_path": "calc.py",
        "source_sha256": matrix.sha(source),
        "status": "observed",
        "tool_policy": policy,
        "tool_policy_cid": policy["policy_cid"],
        "trace": trace,
        "trace_cid": tool.cid(trace),
        "type_clause_satisfied": True,
    }
    result["result_cid"] = tool.cid(result)
    raw["result"] = matrix.json_bytes(result)
    return raw


class FiniteProofToolchainCustodyTests(unittest.TestCase):
    def setUp(self):
        self.factory = fixtures.ReleasedEvidenceChildrenTests("runTest")
        self.factory.setUp()
        self.addCleanup(self.factory.doCleanups)
        self.root, self.repo = self.factory.root, self.factory.repo
        self.sequence = 0
        self.groups = {g: fixture_group(g, 1 if g == tool.GROUPS[2] else 2) for g in tool.GROUPS}
        files = []
        for group, bodies in self.groups.items():
            directory = self.repo / "docs" / group
            directory.mkdir()
            for role, raw in bodies.items():
                filename = tool.ROLES[role]
                (directory / filename).write_bytes(raw)
                files.append(self.factory.pin(group + "/" + filename, raw))
        parent = {"schema": "repository-evidence-files@1", "files": files}
        parent_raw = matrix.json_bytes(parent)
        (self.repo / "docs/evidence.json").write_bytes(parent_raw)
        self.factory.factory.ledger["evidence"][tool.EVIDENCE_ID] = {
            "path": "docs/evidence.json",
            "sha256": matrix.sha(parent_raw),
            "retention": "repository_evidence",
        }
        self.factory.factory.commit()
        self.factory.spec = {
            "schema": children.INPUT_SCHEMA,
            "repositories": self.factory.factory.spec["repositories"],
            "ledger": self.factory.factory.spec["ledger"],
            "selected_evidence": [tool.EVIDENCE_ID],
            "expansion_policy": children.POLICY,
        }
        self.factory.write_spec()
        self.factory.run_audit()
        report = self.root / f"result-{self.factory.sequence}/evidence_children.json"
        prior_spec = self.next("prior-input")
        prior_spec.mkdir()
        manifest = prior_spec / "manifest.json"
        manifest.write_bytes(
            matrix.json_bytes(
                {
                    "schema": capsule.BUILD_INPUT_SCHEMA,
                    "source_manifest": self.pin(self.factory.manifest),
                    "source_report": self.pin(report),
                }
            )
        )
        self.prior = self.next("prior")
        capsule.build(manifest, self.prior)
        self.caproot = self.prior / "capsule"
        self.manifest = self.make_input(self.caproot)

    def next(self, label):
        self.sequence += 1
        return self.root / f"{label}-{self.sequence}"

    @staticmethod
    def pin(path):
        raw = path.read_bytes()
        return {"path": str(path), "sha256": matrix.sha(raw), "size_bytes": len(raw)}

    def make_input(self, root):
        folder = self.next("input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        manifest.write_bytes(
            matrix.json_bytes(
                {
                    "schema": tool.INPUT_SCHEMA,
                    "custody_capsule_manifest": self.pin(root / capsule.CAPSULE_FILENAME),
                    "evidence_id": tool.EVIDENCE_ID,
                    "selected_groups": list(tool.GROUPS),
                }
            )
        )
        return manifest

    def run_audit(self, manifest=None):
        output = self.next("audit")
        return tool.audit(manifest or self.manifest, output), output

    def refused(self, manifest):
        output = self.next("refused")
        with self.assertRaises((ValueError, OSError, KeyError, TypeError)):
            tool.audit(manifest, output)
        self.assertFalse((output / "finite_proof_toolchain_custody.json").exists())

    def mutant(self, change):
        root = self.next("mutant")
        shutil.copytree(self.caproot, root)
        for path in [root, *root.rglob("*")]:
            path.chmod(0o755 if path.is_dir() else 0o644)
        header_path = root / capsule.CAPSULE_FILENAME
        header = matrix.document(header_path.read_bytes())

        def replace(path, raw):
            (root / path).write_bytes(raw)
            pin = portable.pin(path, raw)
            for key in ("files", "retained_views", "objects", "implementation"):
                for row in header[key]:
                    if row["path"] == path:
                        row.update(pin)
            for key in ("source_manifest", "source_report"):
                if header[key]["path"] == path:
                    header[key].update(pin)

        change(root, header, replace)
        header_path.write_bytes(matrix.json_bytes(header))
        for path in [*root.rglob("*"), root]:
            path.chmod(0o555 if path.is_dir() else 0o444)
        return self.make_input(root)

    def test_public_custody_and_unsupported_dependency_scope_remain_separate(self):
        result, output = self.run_audit()
        self.assertEqual((result["group_count"], result["artifact_membership_count"]), (3, 36))
        self.assertEqual(
            [row["recorded_offset_clause_satisfied"] for row in result["groups"]],
            [True, True, False],
        )
        self.assertEqual(
            result["groups"][2]["recorded_counterexample"],
            {"input": -2, "observed_output": -1, "required_output": 0},
        )
        self.assertTrue(all(result[flag] is False for flag in tool.FALSE_FLAGS))
        self.assertEqual(result["dependency_frontier_count"], 5)
        self.assertEqual(result["dependency_frontiers"][0]["name"], "Init")
        self.assertTrue(result["input_files_unchanged"])
        self.assertTrue(result["retained_copy_stability"]["unchanged"])
        nested = matrix.document(Path(result["selected_custody"]["path"]).read_bytes())
        self.assertEqual(nested["artifact_memberships"], result["artifact_memberships"])
        self.assertTrue((output / "finite_proof_toolchain_custody.json").is_file())

    def test_relocation_works_with_original_repo_removed_and_process_calls_forbidden(self):
        relocated = self.next("relocated")
        shutil.copytree(self.caproot, relocated)
        manifest = self.make_input(relocated)
        shutil.rmtree(self.repo)
        with (
            patch.object(subprocess, "Popen", side_effect=AssertionError("no subprocess")),
            patch.object(shutil, "which", side_effect=AssertionError("no executable discovery")),
        ):
            result, _ = self.run_audit(manifest)
        self.assertTrue(result["git_object_verification_performed"])
        self.assertFalse(result["original_paths_read"])

    def test_source_artifact_and_lean_certificate_source_have_distinct_identity_roles(self):
        bodies = copy.deepcopy(self.groups[tool.GROUPS[0]])
        result = matrix.document(bodies["result"])
        result["lean_certificate"]["source_cid"] = result["source_cid"]
        result["result_cid"] = tool.cid({k: v for k, v in result.items() if k != "result_cid"})
        bodies["result"] = matrix.json_bytes(result)
        with self.assertRaises(ValueError):
            tool.reconcile(tool.GROUPS[0], bodies)

    def test_repaired_mutable_artifact_and_report_pins_cannot_replace_commit_body(self):
        def change(root, cap, replace):
            view = next(
                row
                for row in cap["retained_views"]
                if row["relative_path"].endswith("/cold-observation/captured_source.py")
            )
            raw = b"forged source with repaired outer pins\n"
            replace(view["path"], raw)
            report = matrix.document((root / cap["source_report"]["path"]).read_bytes())
            child = next(
                row
                for row in report["manifests"][0]["children"]
                if row["declared_relative_path"] == "cold-observation/captured_source.py"
            )
            child.update(
                sha256=matrix.sha(raw),
                expected_sha256=matrix.sha(raw),
                size_bytes=len(raw),
                expected_size_bytes=len(raw),
            )
            replace(cap["source_report"]["path"], matrix.json_bytes(report))

        self.refused(self.mutant(change))

    def test_repaired_object_sha_cannot_change_framed_oid(self):
        def change(root, cap, replace):
            row = next(row for row in cap["objects"] if row["kind"] == "commit")
            raw = (root / row["path"]).read_bytes()
            replace(row["path"], raw[:-1] + b"X")

        self.refused(self.mutant(change))

    def test_repaired_blob_oid_cannot_change_immutable_tree_membership(self):
        def change(root, cap, replace):
            view = next(
                row
                for row in cap["retained_views"]
                if row["relative_path"].endswith("/cold-observation/captured_source.py")
            )
            raw = (root / view["path"]).read_bytes()
            row = next(
                row
                for row in cap["objects"]
                if row["kind"] == "blob" and (root / row["path"]).read_bytes() == raw
            )
            forged = b"changed, coherently repinned Git blob\n"
            oid = hashlib.sha1(b"blob " + str(len(forged)).encode() + b"\0" + forged).hexdigest()
            old_path = row["path"]
            new_path = "git_objects/" + row["repository"] + "/" + oid
            (root / old_path).unlink()
            (root / new_path).write_bytes(forged)
            row.update(oid=oid, **portable.pin(new_path, forged))
            next(pin for pin in cap["files"] if pin["path"] == old_path).update(
                portable.pin(new_path, forged)
            )

        self.refused(self.mutant(change))

    def test_missing_required_commit_or_blob_refuses(self):
        for kind in ("commit", "blob"):

            def change(root, cap, replace, kind=kind):
                row = next(row for row in cap["objects"] if row["kind"] == kind)
                cap["objects"].remove(row)

            with self.subTest(kind=kind):
                self.refused(self.mutant(change))

    def test_coherently_repaired_policy_and_certificate_tool_claim_cannot_bypass_public_root(self):
        def change(root, cap, replace):
            policy = next(
                row
                for row in cap["retained_views"]
                if row["relative_path"].endswith("/cold-observation/tool_policy.json")
            )
            value = matrix.document((root / policy["path"]).read_bytes())
            value["lean"]["sha256"] = "f" * 64
            value["policy_cid"] = tool.cid({k: v for k, v in value.items() if k != "policy_cid"})
            replace(policy["path"], matrix.json_bytes(value))

        self.refused(self.mutant(change))

    def test_bool_numeric_alias_and_changed_process_limits_are_refused(self):
        for field, value in (
            ("returncode", False),
            ("elapsed_ms", True),
            ("timeout_ms", False),
            ("max_output_files", 9),
        ):
            raw = copy.deepcopy(self.groups[tool.GROUPS[0]])
            process = matrix.document(raw["lean_process"])
            target = (
                process["process"]["limits"]
                if field in ("timeout_ms", "max_output_files")
                else process["process"]
            )
            target[field] = value
            raw["lean_process"] = matrix.json_bytes(process)
            with self.subTest(field=field), self.assertRaises(ValueError):
                tool.reconcile(tool.GROUPS[0], raw)

    def test_changed_domain_order_source_tool_command_or_embedded_output_refuses(self):
        for role, mutate in (
            ("request", lambda v: v["inputs"].reverse()),
            ("lean_certificate", lambda v: v["process"]["command"].append("--foreign")),
            ("python_process", lambda v: v.update(stdout="{}\n")),
            ("tool_policy", lambda v: v["environment"].update(LEAN_NUM_THREADS="9")),
        ):
            raw = copy.deepcopy(self.groups[tool.GROUPS[0]])
            value = matrix.document(raw[role])
            mutate(value)
            raw[role] = matrix.json_bytes(value)
            with self.subTest(role=role), self.assertRaises(ValueError):
                tool.reconcile(tool.GROUPS[0], raw)

    def test_recorded_refutation_cannot_be_promoted_with_repaired_result_cid(self):
        raw = copy.deepcopy(self.groups[tool.GROUPS[2]])
        result = matrix.document(raw["result"])
        result["offset_clause_satisfied"] = True
        result["counterexample"] = None
        result["result_cid"] = tool.cid({k: v for k, v in result.items() if k != "result_cid"})
        raw["result"] = matrix.json_bytes(result)
        with self.assertRaisesRegex(ValueError, "counterexample"):
            tool.reconcile(tool.GROUPS[2], raw)

    def test_closed_schema_path_and_unlisted_group_changes_refuse(self):
        original = matrix.document(self.manifest.read_bytes())
        for changed in (
            {**original, "extra": True},
            {**original, "selected_groups": ["../cold-observation"]},
            {**original, "evidence_id": "other"},
            {
                **original,
                "custody_capsule_manifest": {
                    **original["custody_capsule_manifest"],
                    "size_bytes": True,
                },
            },
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                tool.spec(matrix.json_bytes(changed))
        for raw in (b'{"schema":1,"schema":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError):
                tool.spec(raw)

    def test_preallocation_caps_refuse_objects_payload_reads_and_retained_population(self):
        for field, ceiling in (
            ("MAX_SELECTED_OBJECTS", 0),
            ("MAX_READ_BYTES", 1),
            ("MAX_READ_FILES", 1),
            ("MAX_RETAINED_FILES", 1),
        ):
            with self.subTest(field=field), patch.object(tool, field, ceiling):
                self.refused(self.manifest)

    def test_output_inside_source_scopes_or_existing_paths_refuses(self):
        for output in (
            self.caproot / "bad",
            self.manifest.parent / "bad",
            self.repo / "bad",
            self.manifest.parent,
        ):
            with self.subTest(output=output), self.assertRaises((ValueError, OSError)):
                tool.audit(self.manifest, output)

    def test_late_nested_receipt_and_copied_source_changes_refuse_publication(self):
        original = tool.output_population
        for target_role in ("nested", "source"):
            calls = 0

            def drift(root, expected, capture, target_role=target_role):
                nonlocal calls
                calls += 1
                result = original(root, expected, capture)
                if calls == 2:
                    target = (
                        root / "selected_custody.json"
                        if target_role == "nested"
                        else next(root.rglob("captured_source.py"))
                    )
                    target.write_bytes(target.read_bytes() + b" ")
                return result

            with (
                self.subTest(target=target_role),
                patch.object(tool, "output_population", side_effect=drift),
            ):
                self.refused(self.manifest)
            self.assertGreaterEqual(calls, 2)

    def test_late_original_manifest_and_prior_report_changes_refuse(self):
        original = tool.output_population
        for target_role in ("input", "report"):
            calls = 0

            def drift(root, expected, capture, target_role=target_role):
                nonlocal calls
                calls += 1
                result = original(root, expected, capture)
                if calls == 2:
                    if target_role == "input":
                        target = self.manifest
                    else:
                        cap = matrix.document(
                            (self.caproot / capsule.CAPSULE_FILENAME).read_bytes()
                        )
                        target = self.caproot / cap["source_report"]["path"]
                        target.chmod(0o644)
                    target.write_bytes(target.read_bytes() + b" ")
                return result

            with (
                self.subTest(target=target_role),
                patch.object(tool, "output_population", side_effect=drift),
            ):
                self.refused(self.manifest)
            self.assertGreaterEqual(calls, 2)
            if target_role == "input":
                self.manifest.write_bytes(self.manifest.read_bytes().rstrip() + b"\n")

    def test_late_population_and_selected_seal_drift_refuses(self):
        original = tool.output_population
        for kind in ("extra", "seal"):
            calls = 0

            def drift(root, expected, capture, kind=kind):
                nonlocal calls
                calls += 1
                result = original(root, expected, capture)
                if calls == 2:
                    if kind == "extra":
                        (root / "unlisted").write_bytes(b"extra")
                    else:
                        (self.caproot / capsule.CAPSULE_FILENAME).chmod(0o644)
                return result

            with (
                self.subTest(kind=kind),
                patch.object(tool, "output_population", side_effect=drift),
            ):
                self.refused(self.manifest)
            self.assertGreaterEqual(calls, 2)
            (self.caproot / capsule.CAPSULE_FILENAME).chmod(0o444)

    def test_final_stability_false_cannot_be_ignored(self):
        original = tool.Capture.stability
        calls = 0

        def unstable(capture):
            nonlocal calls
            calls += 1
            result = original(capture)
            if calls == 4:
                result["unchanged"] = False
            return result

        with patch.object(tool.Capture, "stability", new=unstable):
            self.refused(self.manifest)
        self.assertEqual(calls, 4)

    def test_indented_import_with_repaired_receipt_identities_is_refused(self):
        group = tool.GROUPS[0]
        raw = copy.deepcopy(self.groups[group])
        raw["lean_source"] += b"  import Foreign\n"
        certificate = matrix.document(raw["lean_certificate"])
        certificate["source_cid"] = tool.raw_cid(raw["lean_source"])
        raw["lean_certificate"] = matrix.json_bytes(certificate)
        result = matrix.document(raw["result"])
        result["lean_certificate"] = certificate
        for role in ("lean_source", "lean_certificate"):
            result["artifacts"][role].update(
                sha256=matrix.sha(raw[role]), size_bytes=len(raw[role]), cid=tool.raw_cid(raw[role])
            )
        result["result_cid"] = tool.cid({k: v for k, v in result.items() if k != "result_cid"})
        raw["result"] = matrix.json_bytes(result)
        with self.assertRaisesRegex(ValueError, "import profile"):
            tool.reconcile(group, raw)

    def test_extra_file_injected_during_last_copy_reread_is_refused(self):
        original = tool.Capture.stability
        calls = 0
        injected = False

        def late_extra(capture):
            nonlocal calls, injected
            calls += 1
            result = original(capture)
            if calls == 4:
                receipt = next(
                    path for path in capture.cache if path.name == "selected_custody.json"
                )
                (receipt.parent / "late-extra").write_bytes(b"unselected")
                injected = True
            return result

        with patch.object(tool.Capture, "stability", new=late_extra):
            self.refused(self.manifest)
        self.assertTrue(injected)

    def test_coherent_parent_ledger_report_repinning_still_fails_immutable_roots(self):
        def change(root, cap, replace):
            view = next(
                row
                for row in cap["retained_views"]
                if row["relative_path"].endswith("/cold-observation/captured_source.py")
            )
            forged = b"coherently substituted public child\n"
            replace(view["path"], forged)
            parent_view = next(
                row
                for row in cap["retained_views"]
                if row["relative_path"] == "manifests/" + tool.EVIDENCE_ID + ".json"
            )
            parent = matrix.document((root / parent_view["path"]).read_bytes())
            declaration = next(
                row
                for row in parent["files"]
                if row["path"] == "cold-observation/captured_source.py"
            )
            declaration.update(sha256=matrix.sha(forged), bytes=len(forged))
            parent_raw = matrix.json_bytes(parent)
            replace(parent_view["path"], parent_raw)
            ledger_view = next(
                row for row in cap["retained_views"] if row["relative_path"] == "inputs/ledger.json"
            )
            ledger = matrix.document((root / ledger_view["path"]).read_bytes())
            ledger["evidence"][tool.EVIDENCE_ID]["sha256"] = matrix.sha(parent_raw)
            ledger_raw = matrix.json_bytes(ledger)
            replace(ledger_view["path"], ledger_raw)
            source = matrix.document((root / cap["source_manifest"]["path"]).read_bytes())
            source["ledger"]["sha256"] = matrix.sha(ledger_raw)
            source_raw = matrix.json_bytes(source)
            replace(cap["source_manifest"]["path"], source_raw)
            report = matrix.document((root / cap["source_report"]["path"]).read_bytes())
            report["manifest_sha256"] = matrix.sha(source_raw)
            report["ledger_sha256"] = matrix.sha(ledger_raw)
            parent_row = report["manifests"][0]
            parent_row.update(
                sha256=matrix.sha(parent_raw),
                expected_sha256=matrix.sha(parent_raw),
                size_bytes=len(parent_raw),
                expected_size_bytes=len(parent_raw),
            )
            child = next(
                row
                for row in parent_row["children"]
                if row["declared_relative_path"] == "cold-observation/captured_source.py"
            )
            child.update(
                sha256=matrix.sha(forged),
                expected_sha256=matrix.sha(forged),
                size_bytes=len(forged),
                expected_size_bytes=len(forged),
            )
            replace(cap["source_report"]["path"], matrix.json_bytes(report))

        manifest = self.mutant(change)
        output = self.next("immutable-refusal")
        with self.assertRaisesRegex(ValueError, "immutable parent/ledger proof"):
            tool.audit(manifest, output)
        self.assertFalse((output / "finite_proof_toolchain_custody.json").exists())


if __name__ == "__main__":
    unittest.main()
