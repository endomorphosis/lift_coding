"""Freeze completed positive-retention research artifacts without model calls.

Run only after the actual result and independent review files exist. Inputs are
copied byte-exact into a fresh release directory, with explicit original paths.
This helper imports no numerical package and grants no runtime or legal approval.
"""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import xml.etree.ElementTree as ET

F = Path(__file__).resolve().parent
SOURCE_MAIN = "a1b5c73e5b687d8bd6c3b3051788860fd6e2f07a"
REPO = "Publicus/legal-ir-autoencoder"
PREFIX = "experiments/positive-retention-20261011/run-01"
ARMS = ("bce", "positive_margin")
STEPS = (0, 120, 240)
COHORTS = ("fresh_final", "earlier_scope", "earlier_trigger",
           "earlier_support_action", "earlier_support_gate")
PARENT_SHA = "48559399bb22de0fe68908919d225d391880a38f4fab659026d526e19ffc9155"
CORE_SOURCE = (
    "ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_retention_gate.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_retention_selection.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_span_decoder.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_span_proposal.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_trigger_readout.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_support_action.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_support_gate.py",
    "ipfs_datasets_py/logic/legal_ir/canonical_statement_scope.py",
    "ipfs_datasets_py/logic/deontic/utils/deontic_parser.py",
)
TEST_SOURCE = (
    "tests/unit/logic/test_legal_scope_retention_gate.py",
    "tests/unit/logic/test_legal_scope_retention_selection.py",
    "tests/unit/logic/test_legal_scope_support_gate.py",
)
EVIDENCE = (
    "corpus-builder.py", "corpus-author-review.json",
    "corpus-builder-draft-01.py", "corpus-author-review-draft-01.json",
    "run_retention_experiment.py", "prepare_plan.py", "experiment-plan.json",
    "protocol-artifact-bindings.json", "model-selector-review.json",
    "independent-corpus-review.json", "training-design-review.json",
    "real-code-data-review.json", "progress-review.json", "intake.json",
    "remote-intake.json", "retention-module-build.json", "selector-build.json",
    "validation.json", "model-tests.xml", "selection-tests.xml",
    "resource-compatibility.json", "run_scope_guardian.py", "test_scope_guardian.py",
    "trial-artifact-audit.json", "replay_retention_gate.py",
    "protocol-review.json", "replay-source-review.json", "replay-helper-build.json",
    "selected-checkpoint-replay.json", "audit_trial.py", "write_reports.py",
    "incoming-main-integration.json",
    "prepare_release.py", "publish_release.py", "release-helper-build.json",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def byte_pin(raw):
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def file_pin(path):
    path = Path(path).resolve(strict=True)
    require(path.is_file(), "ordinary input file required: " + str(path))
    return {"path": str(path), **byte_pin(path.read_bytes())}


def closed_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=closed_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def checked_reference(reference):
    require(type(reference) is dict and set(reference) == {"path", "bytes", "sha256"},
            "closed artifact reference required")
    require(file_pin(reference["path"]) == reference, "artifact reference changed: " + reference["path"])
    return Path(reference["path"])


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Collector:
    def __init__(self, destination):
        self.destination = Path(destination).resolve()
        require(not self.destination.exists(), "fresh release directory required")
        self.destination.mkdir(parents=True)
        self.records = {}
        self.originals = {}

    def raw(self, raw, relative, *, original, derived=False):
        relative = str(PurePosixPath(relative))
        require(not relative.startswith("/") and ".." not in PurePosixPath(relative).parts,
                "bounded relative release path required")
        target = self.destination / relative
        require(relative not in self.records and not target.exists(), "release path already exists: " + relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(target.parent)
        self.records[relative] = {**byte_pin(raw), "original": original, "derived": derived}
        self.originals.setdefault(original, []).append(relative)
        return relative

    def copy(self, source, relative, *, duplicate=False):
        source = Path(source).resolve(strict=True)
        original = str(source)
        raw = source.read_bytes()
        if original in self.originals and not duplicate:
            previous = self.originals[original][0]
            require(byte_pin(raw) == {key: self.records[previous][key] for key in ("bytes", "sha256")},
                    "original changed during release freeze")
            return previous
        return self.raw(raw, relative, original=original)

    def generated(self, value, relative, *, origin):
        raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                          allow_nan=False) + "\n").encode("utf-8")
        return self.raw(raw, relative, original=origin, derived=True)


class ImportClosure:
    """Static module-initialization closure, with minimal optional imports off.

    Read sparse missing files through exact Git objects. Never expand/check out
    the source tree. Imports inside function bodies remain lazy; numerical leaf
    modules and the parser-denial leaf are explicit roots. No module executes.
    """
    FLAGS = {"_MINIMAL_IMPORTS": True, "_ENABLE_MCP_IMPORTS": False,
             "_ENABLE_FASTAPI_IMPORTS": False, "_ENABLE_FINANCE_DASHBOARD_IMPORTS": False,
             "_ENABLE_LLM_IMPORTS": False}

    def __init__(self, source):
        self.source = Path(source).resolve(strict=True)
        self.current = subprocess.check_output(["git", "-C", str(self.source), "rev-parse", "HEAD"], text=True).strip()
        require(len(self.current) == 40 and all(char in "0123456789abcdef" for char in self.current),
                "actual current package source revision required")
        self.cache = {}

    def read(self, relative):
        if relative not in self.cache:
            path = self.source / relative
            if path.is_file():
                require(not path.is_symlink(), "source symlinks are outside replay closure")
                self.cache[relative] = (path.read_bytes(), str(path.resolve()))
            else:
                result = subprocess.run(["git", "-C", str(self.source), "cat-file", "blob", self.current + ":" + relative],
                                        capture_output=True, check=False)
                self.cache[relative] = ((result.stdout, "git:" + str(self.source) + "@" + self.current + ":" + relative)
                                        if result.returncode == 0 else None)
        return self.cache[relative]

    def module_file(self, module):
        for relative in (module.replace(".", "/") + ".py", module.replace(".", "/") + "/__init__.py"):
            if self.read(relative) is not None:
                return relative
        return None

    def truth(self, expression):
        if isinstance(expression, ast.Name):
            return self.FLAGS.get(expression.id)
        if isinstance(expression, ast.UnaryOp) and isinstance(expression.op, ast.Not):
            value = self.truth(expression.operand)
            return None if value is None else not value
        if isinstance(expression, ast.BoolOp):
            values = [self.truth(value) for value in expression.values]
            if isinstance(expression.op, ast.And):
                return False if False in values else (True if all(value is True for value in values) else None)
            return True if True in values else (False if all(value is False for value in values) else None)
        return expression.value if isinstance(expression, ast.Constant) and type(expression.value) is bool else None

    def eager_imports(self, statements):
        for node in statements:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                yield node
            elif isinstance(node, ast.If):
                truth = self.truth(node.test)
                yield from self.eager_imports(node.body if truth is True else node.orelse if truth is False
                                              else [*node.body, *node.orelse])
            elif isinstance(node, ast.Try):
                yield from self.eager_imports([*node.body, *node.orelse, *node.finalbody])
                for handler in node.handlers:
                    yield from self.eager_imports(handler.body)
            elif isinstance(node, ast.ClassDef):
                yield from self.eager_imports(node.body)

    def collect(self, roots):
        pending, seen, external = list(roots), {}, set()
        while pending:
            relative = pending.pop()
            if relative in seen:
                continue
            record = self.read(relative)
            require(record is not None, "required replay source missing: " + relative)
            seen[relative] = record
            require(len(seen) <= 256, "replay initialization closure exceeds bounded scope")
            parts = PurePosixPath(relative).parts
            for index in range(1, len(parts)):
                parent = "/".join(parts[:index]) + "/__init__.py"
                if self.read(parent) is not None and parent not in seen:
                    pending.append(parent)
            module_parts = list(parts[:-1])
            for node in self.eager_imports(ast.parse(record[0]).body):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif node.level:
                    package = module_parts[:len(module_parts) - node.level + 1]
                    base = ".".join([*package, *(node.module.split(".") if node.module else [])])
                    modules = [base] + [base + "." + alias.name for alias in node.names if alias.name != "*"]
                else:
                    modules = ([node.module] if node.module else []) + [node.module + "." + alias.name for alias in node.names if alias.name != "*"]
                for module in modules:
                    if module.startswith("ipfs_datasets_py"):
                        child = self.module_file(module)
                        if child is not None and child not in seen:
                            pending.append(child)
                    elif module:
                        external.add(module.split(".")[0])
        require(subprocess.check_output(["git", "-C", str(self.source), "rev-parse", "HEAD"], text=True).strip() == self.current,
                "package source revision changed during static closure read")
        return seen, sorted(external)


def validate_tests(root):
    receipts = []
    for name, expected in (("model-tests.xml", 78), ("selection-tests.xml", 101)):
        path = root / name
        xml = ET.fromstring(path.read_bytes())
        cases = list(xml.iter("testcase"))
        identities = {(case.get("classname"), case.get("name")) for case in cases}
        require(len(cases) == len(identities) == expected and not list(xml.iter("failure"))
                and not list(xml.iter("error")) and not list(xml.iter("skipped")), "primary helper test receipt differs")
        receipts.append({**file_pin(path), "passed": expected, "rerun_by_release_builder": False})
    return receipts


def validate_completed(results, plan, root):
    require(results["schema"] == "support-retention-training-results/v1" and results["status"] == "completed",
            "completed actual experiment required")
    require(tuple(results["arms"]) == ARMS or set(results["arms"]) == set(ARMS), "two actual objective arms required")
    require(results["actual_optimizer_updates"] == 480 and results["support_head_updates"] == 480
            and results["action_head_updates"] == 0, "actual support update accounting differs")
    require(results["source_only"] is True and results["latent_conditioned"] is False
            and results["legal_gold"] is False and results["semantic_admission"] is False
            and results["Lake_executed"] is False, "release claim boundary differs")
    require(results["plan"] == file_pin(root / "experiment-plan.json")
            and results["producer_pins"] == plan["producer_pins"], "frozen result/plan/producer binding differs")
    require(set(results["scores"]) == set(COHORTS), "all five evaluation cohorts required")
    for barrier, flag in ((results["selection_barrier"], "references_parsed"),
                          (results["predictions_barrier"], "evaluation_references_parsed")):
        require(read_json(checked_reference(barrier))[flag] is False, "durable pre-reference barrier differs")
    prediction_barrier = read_json(checked_reference(results["predictions_barrier"]))
    require(set(prediction_barrier["panels"]) == {arm + "/" + cohort for arm in ("parent", *ARMS) for cohort in COHORTS},
            "all fifteen parent/selected panels required")
    for ref in prediction_barrier["panels"].values():
        checked_reference(ref)


def prepare(args):
    root, source, results_root = args.artifacts_root.resolve(), args.source_root.resolve(), args.results.resolve()
    plan = read_json(root / "experiment-plan.json")
    results = read_json(results_root / "training-results.json")
    validate_completed(results, plan, root)
    test_receipts = validate_tests(root)
    require(len(args.review) >= 3, "supply actual protocol, results and resource review files explicitly")
    require(len({str(path.resolve()) for path in args.review}) == len(args.review), "distinct review artifacts required")
    for path in args.review:
        require(type(read_json(path)) is dict, "actual machine-readable review artifact required")
    collector = Collector(args.output)
    roles = {}
    for arm in ARMS:
        actual = results["arms"][arm]
        require(actual["objective"] == arm and actual["completed_support_updates"] == 240
                and actual["completed_action_updates"] == 0, "arm update/objective truth differs")
        candidates = {row["completed_updates"]: row for row in actual["selection_candidates"]}
        require(set(candidates) == set(STEPS) and len(actual["selection_candidates"]) == 3
                and all(type(row["completed_updates"]) is int for row in actual["selection_candidates"]),
                "three original measured integer states required")
        selected_step = actual["selected"]["completed_updates"]
        require(type(selected_step) is int and selected_step in STEPS
                and actual["selected"] == candidates[selected_step], "actual selected candidate differs")
        require(read_json(results_root / arm / "selected.json") == actual["selected"], "selected receipt differs")
        decision = actual["selection_decision"]
        require(read_json(results_root / arm / "selection-decision.json") == decision
                and decision["selected_completed_updates"] == selected_step
                and decision["selected_checkpoint_sha256"] == actual["selected"]["checkpoint"]["sha256"],
                "selected decision binding differs")
        require(type(decision["selected_fitted_gain"]) is bool
                and (not decision["selected_fitted_gain"] or selected_step > 0
                     and candidates[selected_step]["retention_report"]["has_selection_gain"] is True),
                "declared fitted selection gain differs")
        require(actual["strict_model_full_Adam_resume_exact"] is True,
                "selected full model/Adam restoration receipt required")
        for step in STEPS:
            original = results_root / arm / ("checkpoint-" + str(step) + ".json")
            require(file_pin(original) == candidates[step]["checkpoint"], "original checkpoint reference differs")
            checkpoint = read_json(original)
            require(checkpoint["schema"] == "legal-scope-retention-gate-checkpoint/v1"
                    and type(checkpoint["steps"]) is int and checkpoint["steps"] == step
                    and checkpoint["config"] == {"seed": 24606, "mode": "predicted_trigger", "hidden": 32, "objective": arm},
                    "original checkpoint recipe/progress differs")
            require(type(checkpoint["profile"]["retention_lambda"]) is float
                    and checkpoint["profile"]["retention_lambda"] == (0.0 if arm == "bce" else 1.0)
                    and checkpoint["parent"]["sha256"] == PARENT_SHA
                    and checkpoint["producer"] == results["producer_pins"], "checkpoint objective/parent/producer differs")
            parent_raw = checkpoint["parent"]["json_utf8"].encode("utf-8")
            require(sha256(parent_raw).hexdigest() == PARENT_SHA
                    and len(parent_raw) == checkpoint["parent"]["bytes"] == plan["parent_checkpoint"]["bytes"],
                    "embedded full historical parent bytes differ")
            seal = sha256(canonical({key: value for key, value in checkpoint.items() if key != "checkpoint_sha256"})).hexdigest()
            require(seal == checkpoint["checkpoint_sha256"], "canonical checkpoint seal differs")
            chosen, eligible = step == selected_step, candidates[step]["eligible"]
            require(type(eligible) is bool and (eligible or not chosen), "selection eligibility differs")
            role = ("selected_cold_initial" if chosen else "cold_function_preserving_control") if step == 0 else (
                "selected_trained_research" if chosen else "trained_eligible_unselected_research" if eligible else "trained_selection_ineligible_research")
            relative = collector.copy(original, "checkpoints/" + arm + "/checkpoint-" + str(step) + ".json")
            roles[relative] = {**file_pin(original), "objective": arm, "gate_steps": step, "role": role,
                "trained_this_trial": step > 0, "selection_eligible": eligible, "selected": chosen,
                "evaluated_on_selection": True, "evaluated_on_final_or_retention": chosen,
                "full_new_Adam_preserved": True, "exact_parent_checkpoint_sha256": PARENT_SHA,
                "default_promotion": False, "native_runtime_qualified": False}
        alias = collector.copy(results_root / arm / ("checkpoint-" + str(selected_step) + ".json"),
                               "checkpoints/" + arm + "/checkpoint.json", duplicate=True)
        roles[alias] = {**byte_pin((collector.destination / alias).read_bytes()), "objective": arm,
            "gate_steps": selected_step, "role": "selected_cold_fallback_alias" if selected_step == 0 else "selected_trained_alias",
            "aliases": "checkpoints/" + arm + "/checkpoint-" + str(selected_step) + ".json",
            "selected": True, "trained_this_trial": selected_step > 0,
            "evaluated_on_final_or_retention": True, "independent_fit": False,
            "default_promotion": False, "native_runtime_qualified": False}
    # Only the owned result root and its two shallow arm directories are read.
    for child in sorted(results_root.iterdir()):
        if child.is_file():
            collector.copy(child, "results/" + child.name)
        else:
            require(child.name in ARMS and child.is_dir() and not child.is_symlink(), "unexpected result subtree")
            for path in sorted(child.iterdir()):
                require(path.is_file(), "unexpected nested result artifact")
                if path.name not in {"checkpoint-" + str(step) + ".json" for step in STEPS}:
                    collector.copy(path, "results/" + child.name + "/" + path.name)
    omitted = {}
    omit_names = set(args.omit_guardian_file)
    require(all(name == Path(name).name and name not in (".", "..") for name in omit_names),
            "explicit shallow guardian filenames required")
    require(not omit_names or args.resource_projection is not None,
            "omitted full resource artifacts require a separately reviewed compact projection")
    for path in sorted(args.attempt.resolve().iterdir()):
        if path.is_file():
            if path.name in omit_names:
                omitted[path.name] = {**file_pin(path), "full_body_retained_locally": True}
            else:
                collector.copy(path, "guardian/" + path.name)
    require(set(omitted) == omit_names, "explicit omitted guardian file was not found")
    # Full shared-ledger observations remain local. Their exact pins plus the
    # reviewed foreign-preservation projection carry public resource evidence.
    for name in ("resource-admission-observation.json", "resource-postfinal-observation.json"):
        if (root / name).is_file():
            omitted["artifacts-root/" + name] = {**file_pin(root / name), "full_body_retained_locally": True}
    if omitted:
        require(args.resource_projection is not None,
                "shared-ledger observation pins require a reviewed compact resource projection")
        projection = collector.copy(args.resource_projection, "guardian/resource-preservation-projection.json")
        collector.generated({"schema": "positive-retention-resource-local-retention/v1",
            "full_artifact_pins": omitted, "compact_projection": projection,
            "foreign_state_rewrite_or_release": False, "approval_inferred_by_builder": False},
            "guardian/full-resource-artifact-pins.json", origin="derived:locally retained full resource artifact bindings")
    for name in EVIDENCE:
        collector.copy(root / name, "evidence/" + name)
    for category in ("corpus", "corpus-draft-01"):
        paths = sorted((root / category).glob("*.json"))
        require(len(paths) == 9, "complete nine-file corpus generation required")
        for path in paths:
            collector.copy(path, "evidence/" + category + "/" + path.name)
    collector.copy(checked_reference(plan["parent_checkpoint"]), "inputs/parent-checkpoint.json")
    corpus_manifest = read_json(root / "corpus/corpus-manifest.json")
    for ref in corpus_manifest["versioned_old_source_inputs"]:
        path = checked_reference(ref)
        collector.copy(path, "historical/corpus/" + path.parent.name + "/" + path.name)
    collector.copy(checked_reference(plan["scorer"]), "historical/scorer/run_trigger_experiment.py")
    for cohort, record in plan["retention"].items():
        for role in ("inputs", "references", "archived_parent_predictions"):
            collector.copy(checked_reference(record[role]), "historical/retention/" + cohort + "/" + role + ".json")
    for index, path in enumerate(args.review):
        collector.copy(path, "reviews/" + str(index + 1).zfill(2) + "-" + path.name)
    for path in args.evidence:
        collector.copy(path, "evidence/extra/" + path.name)
    closure_reader = ImportClosure(source)
    closure, external = closure_reader.collect(CORE_SOURCE)
    action_pin = plan["producer_pins"]["support_action_producer"]
    trigger_pin = action_pin["trigger_producer"]
    donor_pin = trigger_pin["donor_producer"]
    numeric_prefix = "ipfs_datasets_py/logic/formalization/autoencoder/"
    expected_producers = {
        numeric_prefix + "legal_scope_retention_gate.py": plan["producer_pins"]["implementation_sha256"],
        numeric_prefix + "legal_scope_retention_selection.py": plan["selection_policy"]["sha256"],
        numeric_prefix + "legal_scope_span_decoder.py": donor_pin["implementation_sha256"],
        numeric_prefix + "legal_scope_span_proposal.py": donor_pin["proposal_sha256"],
        numeric_prefix + "legal_scope_trigger_readout.py": trigger_pin["implementation_sha256"],
        numeric_prefix + "legal_scope_support_action.py": action_pin["implementation_sha256"],
        numeric_prefix + "legal_scope_support_gate.py": plan["producer_pins"]["support_gate_reference"]["implementation_sha256"],
        "ipfs_datasets_py/logic/legal_ir/canonical_statement_scope.py": donor_pin["scope_sha256"],
    }
    for relative, expected_sha in expected_producers.items():
        require(byte_pin(closure[relative][0])["sha256"] == expected_sha,
                "replay producer bytes differ from actual numerical run: " + relative)
    helper_build = read_json(root / "release-helper-build.json")
    for binding in helper_build["source_pins"]:
        require(file_pin(binding["path"]) == binding, "frozen release source/test input changed")
    closure_records = {}
    for relative, (raw, original) in sorted(closure.items()):
        release_path = collector.raw(raw, "source/" + relative, original=original)
        closure_records[relative] = {"release_path": release_path, **byte_pin(raw)}
    for relative in TEST_SOURCE:
        collector.copy(source / relative, "source/" + relative)
    collector.generated({"schema": "positive-retention-replay-source-closure/v1",
        "training_source_main": SOURCE_MAIN, "package_import_source_main": closure_reader.current,
        "scientific_producers_verified_against_actual_trial": expected_producers,
        "files": closure_records, "module_initialization_closure_only": True,
        "environment": {"IPFS_DATASETS_PY_MINIMAL_IMPORTS": "1", "IPFS_DATASETS_PY_ENABLE_MCP_IMPORTS": "0",
                        "IPFS_DATASETS_PY_ENABLE_FASTAPI_IMPORTS": "0", "IPFS_DATASETS_PY_ENABLE_FINANCE_DASHBOARD_IMPORTS": "0"},
        "external_import_roots": external, "torch_version_in_producer": plan["producer_pins"]["support_action_producer"]["trigger_producer"]["donor_producer"]["torch_version"],
        "model_imports_executed_by_builder": False,
        "portability": "Original plans/reviews retain absolute paths. Use the original-artifacts-map to rebind verified paths explicitly; no standalone generic package or training command is asserted."},
        "replay-source-closure.json", origin="derived:static replay package import closure")
    collector.generated({"schema": "positive-retention-checkpoint-role-inventory/v1", "checkpoint_files": roles,
        "original_states": 6, "selected_aliases": 2, "actual_independent_fits": 2,
        "selected_updates_per_arm": {arm: results["arms"][arm]["selected"]["completed_updates"] for arm in ARMS},
        "selected_fitted_gain": {arm: results["arms"][arm]["selection_decision"]["selected_fitted_gain"] for arm in ARMS},
        "default_promotion": False, "native_runtime_qualified": False},
        "checkpoint-roles.json", origin="derived:actual completed checkpoint selections")
    lines = ["# Matched BCE and positive-margin support retention", "",
        "This completed authored source-text trial preserves six original full checkpoint containers and two selected aliases. Both matched 3,169-parameter predicted-trigger gates completed 240 updates. The second objective adds a TRAIN-only online frozen-parent positive squared hinge to the same support BCE; both use the same paired source schedule.", "",
        "| Arm | Selected update | Declared fitted selection gain | Fresh final whole exact /64 | Fresh final unsupported emissions /64 |",
        "| --- | ---: | --- | ---: | ---: |"]
    for arm in ARMS:
        actual = results["arms"][arm]
        score = results["scores"]["fresh_final"][arm]
        lines.append("| " + arm + " | " + str(actual["selected"]["completed_updates"]) + " | " + str(actual["selection_decision"]["selected_fitted_gain"]).lower() + " | " + str(score["positive_exact_count"]) + " | " + str(score["negative_emitted_proposal_count"]) + " |")
    parent = results["scores"]["fresh_final"]["parent"]
    lines += ["", "The same-panel parent has " + str(parent["positive_exact_count"]) + "/64 whole exact positives and " + str(parent["negative_emitted_proposal_count"]) + "/64 unsupported emissions. Selection gains and these final observations are separate: selection floors do not guarantee fresh-final or exposed-retention performance.", "",
        "`checkpoint-roles.json` derives eligibility, selection and evaluation roles from the actual receipts. Every 0/120/240 state was scored on selection; only each chosen checkpoint was evaluated across the fresh final and four exposed old final cohorts. Unselected states remain research artifacts. Aliases are exact copies of selected original containers and are not additional fits. Full new gate Adam/progress and the exact frozen parent remain retained; old Adam was not continued.", "",
        "The release includes complete losses, decisions, saved prediction panels, durable pre-reference barriers, plans, corpus/source hashes, independent reviews and guardian/resource observations. The 78 model/old-gate plus 101 pure selector helper tests have zero failures/errors/skips in their saved XML; they were not rerun by this release builder. Resource peaks remain sampled measurements with the scope recorded in the actual receipts.", "",
        "This is a single-seed authored construction experiment. Shared templates, modal aliases and anagram patterns remain exposed; it has no independent legal gold. The preserved draft corpus generation documents the author formula correction from an omitted square to the intended squared hinge; all six source/reference files and the full schedule remained unchanged. The author's note does not constitute independent corpus approval.", "",
        "These heads consume raw source bytes and explicit caller attachment, with no 8D/384D/768D latent input. They emit occurrence proposals with zero admission masks and null formal output. They supply no native schema/runtime qualification, legal semantic authority, logic-family lowering, Lake/proof authority, default promotion or ModelManager registration.", "",
        "Every nonmanifest file is bound in `release-manifest.json`. `original-artifacts-map.json` maps recorded originals to release files. Historical paths are provenance, not portable commands; replay requires explicit checked path rebinding, the pinned source closure, compatible Torch, exact selected checkpoint bytes and saved source-only panels. No package, checkpoint or prior result is silently reinterpreted.", ""]
    lines += ["| Trained selection state | Whole positive IDs lost | Emitted positive IDs lost | New negative emission IDs | Eligible |",
              "| --- | ---: | ---: | ---: | --- |"]
    for arm in ARMS:
        for candidate in results["arms"][arm]["selection_candidates"]:
            if candidate["completed_updates"] == 0:
                continue
            counts = candidate["retention_report"]["paired_counts"]
            lines.append("| " + arm + " update " + str(candidate["completed_updates"]) + " | "
                + str(counts["whole_lost"]) + " | " + str(counts["positive_emission_lost"]) + " | "
                + str(counts["negative_emission_gained"]) + " | " + str(candidate["eligible"]).lower() + " |")
    lines += ["", "The soft margin and positive case preservation are diagnostics. A state with retained positive IDs can still fail because it introduces unsupported emissions; neither lower loss nor a rejected research state's partial retention is a selected accuracy gain.", ""]
    collector.raw("\n".join(lines).encode("utf-8"), "README.md", original="derived:actual completed result README", derived=True)
    collector.generated({"schema": "positive-retention-original-artifact-map/v1",
        "originals": {original: {"release_paths": paths,
            "sha256": collector.records[paths[0]]["sha256"], "bytes": collector.records[paths[0]]["bytes"]}
            for original, paths in sorted(collector.originals.items())},
        "generated_record_origin": "derived:original artifact mapping", "manifest_self_excluded": True},
        "original-artifacts-map.json", origin="derived:original artifact mapping")
    manifest = {"schema": "positive-retention-release-manifest/v1", "repo": REPO, "prefix": PREFIX,
        "files": dict(sorted(collector.records.items())), "self_excluded": "release-manifest.json",
        "checkpoint_inventory": "checkpoint-roles.json", "original_artifact_map": "original-artifacts-map.json",
        "numerical_checkpoint_files": 8, "original_states": 6, "selected_aliases": 2,
        "actual_independent_fits": 2, "actual_updates_per_arm": 240,
        "selected_updates_per_arm": {arm: results["arms"][arm]["selected"]["completed_updates"] for arm in ARMS},
        "selected_fitted_gain": {arm: results["arms"][arm]["selection_decision"]["selected_fitted_gain"] for arm in ARMS},
        "five_evaluation_cohorts": list(COHORTS), "all_fifteen_parent_selected_panels_retained": True,
        "current_helper_test_executions": 179, "test_receipts": test_receipts,
        "supplied_review_pins": [file_pin(path) for path in args.review],
        "no_review_approval_inferred_by_builder": True, "model_or_test_execution_by_builder": False,
        "source_only": True, "latent_conditioned": False, "native_runtime_qualified": False,
        "legal_gold": False, "default_promotion": False, "formal_output": None,
        "admission_masks": "all five zero"}
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    collector.raw(raw, "release-manifest.json", original="derived:complete release manifest", derived=True)
    require(len(roles) == 8, "exactly eight checkpoint containers required")
    return {"release": str(collector.destination), "files": len(collector.records),
            "bytes": sum(record["bytes"] for record in collector.records.values()),
            "release_manifest": file_pin(collector.destination / "release-manifest.json"),
            "selected_updates_per_arm": manifest["selected_updates_per_arm"],
            "selected_fitted_gain": manifest["selected_fitted_gain"], "Hub_accessed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--attempt", type=Path, required=True)
    parser.add_argument("--review", type=Path, action="append", required=True)
    parser.add_argument("--evidence", type=Path, action="append", default=[])
    parser.add_argument("--omit-guardian-file", action="append", default=[])
    parser.add_argument("--resource-projection", type=Path)
    parser.add_argument("--artifacts-root", type=Path, default=F)
    parser.add_argument("--source-root", type=Path, default=F / "datasets")
    parser.add_argument("--output", type=Path, default=F / "release")
    args = parser.parse_args()
    print(json.dumps(prepare(args), indent=2))


if __name__ == "__main__":
    main()
