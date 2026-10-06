#!/usr/bin/env python3
"""Extend the existing16-study review using pinned ordinary local evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path("/home/barberb/lift_coding")
OUT = ROOT / "artifacts/autoencoder-progress-reconciliation-20261006/semantic"
DATA = ROOT / "external/ipfs_datasets"
CONTEXT = ROOT / ".worktrees/contextual-legal-runtime-datasets-20261006"
PATCH = ROOT / ".worktrees/autoencoder-progress-reconciliation-datasets-20261006"
ACCEL = ROOT / ".worktrees/contextual-legal-runtime-accelerate-20261006"


def observe(path):
    if not path.is_file():
        return {"path": str(path), "exists": False, "bytes": None, "sha256": None}
    before = path.stat()
    if before.st_size > 32 * 1024 * 1024:
        raise ValueError("ordinary evidence exceeds32MiB: " + str(path))
    raw = path.read_bytes()
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError("evidence changed during observation: " + str(path))
    return {"path": str(path), "exists": True, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    prior_path = ROOT / "artifacts/autoencoder-integration-review-20261006/findings/evidence-matrix.json"
    prior = json.loads(prior_path.read_bytes())
    assert len(prior["entries"]) == 16
    paths = {
        "prior-matrix": prior_path,
        "prior-workspace-guide": ROOT / "implementation_plan/docs/58-autoencoder-progress-integration-2026-10-06.md",
        "prior-findings-guide": ROOT / "artifacts/autoencoder-integration-review-20261006/findings/README.md",
        "datasets-survey": ROOT / "artifacts/autoencoder-progress-reconciliation-20261006/datasets/survey.json",
        "datasets-findings": ROOT / "artifacts/autoencoder-progress-reconciliation-20261006/datasets/reconciliation-findings.json",
        "datasets-effective-contextual39": ROOT / "artifacts/autoencoder-progress-reconciliation-20261006/datasets/effective-39f25777d557.json",
        "datasets-effective795": ROOT / "artifacts/autoencoder-progress-reconciliation-20261006/datasets/effective-795d96017021.json",
        "accelerate-survey": ROOT / "artifacts/autoencoder-progress-reconciliation-20261006/accelerate/survey.json",
        "accelerate-findings": ROOT / "artifacts/autoencoder-progress-reconciliation-20261006/accelerate/findings.json",
        "contextual-generation": ROOT / "artifacts/contextual-legal-runtime-20261006/generation-qualification.json",
        "contextual-evaluation": ROOT / "artifacts/contextual-legal-runtime-20261006/separate-evaluation.json",
        "contextual-frozen-source": ROOT / "artifacts/contextual-legal-runtime-20261006/committed-source-qualification.json",
        "contextual-document37": CONTEXT / "docs/autoencoders/contextual_legal_reconstruction_runtime.md",
        "candidate-contextual-document": PATCH / "docs/autoencoders/contextual_legal_reconstruction_runtime.md",
        "candidate-paraphrase-document": PATCH / "docs/autoencoders/paraphrase_modality_diagnostics.md",
        "original-modelmanager-registration": ROOT / "artifacts/decoder-profile-recovery-20261006/model-manager-registration.json",
        "original-dimension-mirrors": ROOT / "artifacts/decoder-profile-recovery-20261006/dimension-mirrors/publication-summary.json",
        "original-native-profile-metadata": ROOT / "artifacts/decoder-profile-recovery-20261006/native-owner/qualification.json",
        "original-registration-document": ACCEL / "docs/agent_supervisor/contextual_ir_checkpoint_recovery.md",
        "normative-document": DATA / "docs/autoencoders/normative_wording_training.md",
        "normative-results": DATA / "docs/implementation/reports/evidence/decoder-normative-wording-20261006/results.json",
        "modality-margins-results": DATA / "docs/implementation/reports/evidence/decoder-paraphrase-modality-margins-20261006/results.json",
        "source-only-expansion": ROOT / "artifacts/autoformalization-publication-20261004/expansion/expanded-summary-01.json",
        "joint-condition-control": ROOT / "artifacts/autoformalization-publication-20261004/joint_conditioning/results-01/summary-01.json",
        "logic-output-policy": DATA / "docs/autoencoders/logic_output_requirements.md",
        "native-projection-v3": DATA / "docs/autoencoders/native_semantic_projections_v3.md",
        "native-formal-readout": DATA / "docs/autoencoders/native_formal_decoders.md",
        "legacy-teacher-fidelity": DATA / "docs/autoencoders/legacy_teacher_fidelity.md",
        "linguistic-teacher-validation": DATA / "docs/autoencoders/legacy_linguistic_validation_20261001.md",
        "formula-visibility-audit": DATA / "docs/autoencoders/formal_logic_visibility_audit.md",
        "dual-donor-replay": DATA / "docs/autoencoders/gte_decoder_knowledge_transfer.md",
        "gte-migration-plan": DATA / "docs/autoencoders/gte_multilingual_migration_plan.md",
        "ir-recovery-interface": DATA / "docs/autoencoders/ir_progress_recovery.md",
        "family-cell-proof-index-plan": DATA / "docs/autoencoders/codebase_ir_proof_index_improvement_plan.md",
        "repository-pipeline-plan": DATA / "docs/autoencoders/codebase_ir_repository_pipeline_improvement_plan.md",
        "intent-text-roundtrip": DATA / "docs/intent_roundtrip_training.md",
        "security-formula-document": DATA / "docs/security_formula_decoder.md",
        "codebase-live300-document": ROOT / "external/ipfs_accelerate/docs/agent_supervisor/codebase_full300_companion_and_linear_observation_qualification_v2.md",
        "codebase-live-larger-head-document": ROOT / "external/ipfs_accelerate/docs/agent_supervisor/codebase_larger_head_native_owner_integration_note.md",
        "paragraph-caller-pin-control": OUT / "paragraph-pin-boundary.json",
        "honesty-patch-review": OUT / "honesty-patch-independent-review.json",
        "honesty-original-metadata-control": OUT / "honesty-original-metadata-controls.json",
        "honesty-original-metadata-reproducer": OUT / "check_metadata_honesty_patch.py",
        "paragraph-control-reproducer": OUT / "reproduce_paragraph_pin_boundary.py",
        "ordinary-matrix-verifier": OUT / "verify_semantic_matrix.py",
        "matrix-builder": Path(__file__),
    }
    for entry in prior["entries"]:
        source = entry["source"]
        paths["prior-source:" + entry["id"]] = Path(source["repository"]) / source["path"]
    for name in ("runtime", "numeric", "output"):
        paths["published-contextual-owner:" + name] = CONTEXT / (
            "ipfs_datasets_py/logic/formalization/autoencoder/contextual_legal_ir_" + name + ".py")
        paths["live-contextual-owner:" + name] = DATA / (
            "ipfs_datasets_py/logic/formalization/autoencoder/contextual_legal_ir_" + name + ".py")
    paths["live-contextual-document"] = DATA / "docs/autoencoders/contextual_legal_reconstruction_runtime.md"
    paths["candidate-contextual-owner"] = PATCH / "ipfs_datasets_py/logic/formalization/autoencoder/contextual_legal_ir_runtime.py"
    sources = {identity: observe(path) for identity, path in paths.items()}
    inherited = deepcopy(prior["entries"])
    for entry in inherited:
        observed = sources["prior-source:" + entry["id"]]
        expected = entry["source"]
        entry["current_local_ordinary_bytes"] = observed
        entry["prior_report_bytes_retained_locally"] = observed["exists"] and observed["bytes"] == expected["bytes"] and observed["sha256"] == expected["sha256"]
        entry["reachability_scope"] = "Original prior5171/3b0162 review; current effective-tree status is separately sourced from the new branch-agent receipts."
    metrics = runpy.run_path(str(paths["ordinary-matrix-verifier"]))["metrics"](sources)
    assert [(lane["ordered_ir_exact"], lane["utf8_text_exact"]) for lane in metrics["original_contextual"]] == [(48, 0), (48, 0)]
    assert [(panel["dimension"], panel["exact"]) for panel in metrics["prospective_wording_selected"]] == [(384, 55), (384, 60), (768, 60), (768, 60)]
    assert all(value == 0 for value in metrics["source_only64"]["masks"].values())
    new = [
        {"id": "original-contextual-registration-and-publication", "sources": ["original-modelmanager-registration", "original-dimension-mirrors", "original-native-profile-metadata"],
         "kind": "byte_custody_and_metadata_integration", "scope": "Two original selected32-entry Legal384/768 states; retained API registration668→670 and two existing public dimension mirrors.",
         "reusable": "Exact asset IDs, immutable state hashes, detached source-bound profile exports, unchanged12 lane declarations and separate original384 Intent/Security fragment contracts.",
         "limit": "Native schema/profile/format remainsnull for contextual states; runtime/teacher/proof remainsfalse. Historical670 and Hub commits are retained observations, not a new live catalog/Hub read by this semantic reviewer. Per-cell12 physical stores are not established."},
        {"id": "original-contextual48-ir-versus-prose", "sources": ["contextual-generation", "contextual-evaluation", "contextual-frozen-source", "contextual-document37"],
         "kind": "actual_frozen_original_asset_source_only_regression", "scope": "Original48 exposed paragraphs and180 literal clause occurrences per384/768 lane; frozen37c2 source, publication39f257.",
         "reusable": "Original raw384 donor, width-specific paragraph/clause caches, saved TRAIN transforms, independent paragraph/clause feature norms, exact32 selected tensors and512 output budget;244 new/source-value and210 old-owner controls.",
         "observed": "Each lane48/48 ordered and canonical IR,180/180 rules,720/720 actor/action/modality/object fields;48 source-withheld rendered texts but0/48 UTF8 and0/48 NFC/whitespace prose matches.",
         "limit": "All qualifiers empty, clause counts1/2/4/8; no fresh semantic holdout, arbitrary prose decoder, native8192 span, independent teacher or proof qualification. Canonical sorting differs from ordered exactness."},
        {"id": "paraphrase-source-recurrent-modality-diagnosis", "sources": ["modality-margins-results", "candidate-paraphrase-document"],
         "kind": "same_pass_component_observation", "scope": "Previously exposedv3 wording; four selected arm observations from the earlier parity-preserved384/768 head experiments.",
         "reusable": "Reference barrier, full32-vocabulary source/recurrent/combined logits, durable same-pass traces, no extra forward/model copy, independent66,467 scalar checks.",
         "observed": "384 exact20→19/48 and modality source139→137/180 versus combined139→136/180;768 exact46→46/48 and modality178/180. One positive384 additive override changes a correct source preference into a wrong emitted modality.",
         "limit": "Recurrent uncombined argmax is often a grammar token and is not another formula decoder; trace does not causally isolate paragraph/clause/history effects. No fitting/encoder/Lake here."},
        {"id": "normative60-broader-wording-training", "sources": ["normative-results", "normative-document", "datasets-findings"],
         "kind": "actual_decoder_training_and_separate_native_preparation", "scope": "90 old TRAIN rules rendered as180 balanced empty-qualifier clauses; separately sealed60 new wordings over30 already exposed DEV meanings.",
         "reusable": "Four paired170-update fits; exact zero control replay; same original batches/codec/parents, TRAIN-only additional modality loss, native frozen offline512 encoder caches276 vectors/width, durable eight endpoint panels before references.",
         "observed": "38455/60→60/60 with69.92% lowerCE;76860/60→60/60 with2.45% higherCE. Original48 exact retained; selected/last states alias, so four fits/four unique tensors are not eight independent repetitions.",
         "limit": "Prospective wording is not fresh semantic holdout; no qualifier capability, decoder promotion, bridge/projection/Lake or encoder weight update. New auxiliary state hashes6cab6f…/aa2f75… differ from registered original0ac5…/8892…; record/publication currentness must be independently joined before selection."},
        {"id": "codebase-native-structural-and-larger-width-prerequisites", "sources": ["codebase-live300-document", "codebase-live-larger-head-document", "accelerate-findings", "repository-pipeline-plan"],
         "kind": "scoped_native_structural_scanning_and_source_owner_prerequisites", "scope": "Authored300 members,53 compiler features and8-wide structural latent; separate one-row native4096 CPU completed-owner boundary.",
         "reusable": "Exact source/CAS/AST manifests, five pages64/64/64/64/44 per mode, cold resume, signed companion joins, default/reference equality and explicit current source/checker drift refusal.",
         "observed": "Latest branch-agent notes distinguish full300 member accounting from110 encoded/184 deferred rows per mode; zero formalized/checked properties, no worker launch/install.4096 native owner hashes full assets and supplies a process/thread-bound capability, not a trained Codebase head.",
         "limit": "Some live source/docs are still unreviewed/unpublished candidates. No complete working-repository semantic scan, trained384/768/4096 Codebase lineage, independent reproof or accepted proof-cache claims are supplied."},
    ]
    cells = [
        {"family": "legal_ir", "dimension": 8, "roles": "Historical explicit8D sparse/linguistic representation; separately learned18-token formula head; separately source-only8→16→4 MLP.", "status": "Preserved teacher replay; teacher semantic defects remain. Formula sidecar original1/48/exposed0/48. These are different owners.", "missing": "Independently reviewed teacher scope, nonempty qualifiers and compatible task-specific distillation targets."},
        {"family": "legal_ir", "dimension": 384, "roles": "GTE-small input384/token512; source GRU, parser-assisted64-token package, contextual32-entry semantic decoder/output512, residual8 view and source-only latent32 are distinct.", "status": "Original contextual48 exact/prose0; new normative selected60 exact under restricted grammar. Original complete state registered/public.", "missing": "Richer source/qualifier vocabulary and lossless schema, fresh grouped holdout, trained prose task and candidate-state registry/routing joins."},
        {"family": "legal_ir", "dimension": 768, "roles": "Native multilingual768 input; current bounded512 caches; contextual decoder, dual-donor inherited interfaces, source-only latent64 and copied-span native head are distinct.", "status": "Original contextual48 exact/prose0; normative control/auxiliary60 exact with no auxCE gain; original state registered/public.", "missing": "Task-aware selected-state/codec and cache alignment, scoped teacher KD, native long-span8192/output curriculum and production ABI."},
        {"family": "codebase_ir", "dimension": 8, "roles": "53 structural compiler-input features and8-wide learned latent, not necessarily8-wide semantic source input.", "status": "Bounded structural native scans/resume/companion observations exist; zero formalized/checked properties.", "missing": "Source/native semantic correspondence, formal decoder, complete declared inventory integration and independent checker admission."},
        {"family": "codebase_ir", "dimension": 384, "roles": "Semantic source384 bridge may own Codebase IR while reusing Security numerical payload; this ownership must remain explicit.", "status": "Encoder/head prerequisites and narrow wrappers exist; broader admitted native Codebase grammar/task is not established by the reviewed evidence.", "missing": "Dedicated task/codec, source-to-native head lineage, complete scan/dispatch and source-bound proof index adapter."},
        {"family": "codebase_ir", "dimension": 768, "roles": "Larger semantic source representation is separate from structural latent8 and Legal768 heads.", "status": "Source/encoder and narrow head protocol observations exist; a trained admitted repository-native formal decoder is not established.", "missing": "Representative source/target corpus, inherited parent and optimizer continuation, Codebase-native grammar, full task and scanner qualification."},
        {"family": "security_ir", "dimension": 8, "roles": "52-input/8-latent compiler-conditional path/value model; richer289-input variant is another basis.", "status": "Structural numerical reconstruction/native fixed-tree readout exists, conditioned on compiler-prepared inputs.", "missing": "Independent source-to-IR scope, variable tree presence/length and source-specific native/code applicability gates."},
        {"family": "security_ir", "dimension": 384, "roles": "ProgramIR expression GRU/native fragment; advisory44-AST-feature classifier; separate bounded source production grammar head.", "status": "Original program-ir/v1 fragment route authenticates; complete Python function/byte-map adapters and reviewed header/integer native obligations exist.", "missing": "Preserve classifier/formula identities; broaden source grammar/coverage without converting CVE labels into function-level truths or compiler scaffolding into learned specifications."},
        {"family": "security_ir", "dimension": 768, "roles": "Declared family/input-role lane, independent from Legal768 and Codebase source bridges.", "status": "No authenticated trained family-specific full-document head established by this review; lane declaration alone is insufficient.", "missing": "Compatible native task/schema/codec parent, source/cache corpus and separate training/evaluation/checker evidence."},
        {"family": "intent_ir", "dimension": 8, "roles": "12 compiler-input features and8-wide structural latent; frozen lexical width8 in sequence models is another role.", "status": "Compiler-conditional numerical path exists; cannot substitute for an independent intent understanding head.", "missing": "Source-bound goals/preconditions/effects/workflows and current repository symbol/evidence correspondence."},
        {"family": "intent_ir", "dimension": 384, "roles": "Source-conditioned GRU/rich AST fragment, fixed-schema ridge and separate learned frame→normalized instruction inverse.", "status": "intent-rich-grammar/v1 replay and24/24 fixed-composition ridge controls exist. Paired inverse authored75/75 versus weak public0/3 reflects narrow language/OOV scope.", "missing": "Full workflow/conditional documents, case-sensitive code symbols, richer source fidelity and typed current/post-change repository grounding."},
        {"family": "intent_ir", "dimension": 768, "roles": "Declared separate source representation/task lane, not a relabeled Legal student.", "status": "No authenticated trained full-document family head established by reviewed evidence.", "missing": "Native codec/schema and exact source-to-Codebase binding contract, compatible warm-start map, paired inputs and family-specific checks."},
    ]
    reconciliation = [
        {"id": "cohorts-and-losses", "finding": "Original48 contextual, exposedv348, prospective60 wording, source-only64 and broader4096DEV12 have different checkpoints/objectives/populations.", "action": "Never pool exact,CE,MSE,proposal,Lake or repeated seed/alias counts; keep source-group exposure/selection ledgers."},
        {"id": "historical-plan-readiness", "finding": "The October2 family plan's Legal768 unavailable observation predates authenticated retained selected768 states and October6 original-asset replay.", "action": "Preserve dated tables, append new exact state/producer/task observations; no blanket all-family768 readiness claim."},
        {"id": "inverse-source-access", "finding": "Legacy provenance decompilation can reproduce bytes despite wrong formulas. Source-withheld semantic rendering has48 outputs but0 exact prose matches.", "action": "Separate retained-source restoration, semantic paraphrase and learned original-prose decoder tasks; expose all residual information and collisions."},
        {"id": "paragraph-producer-custody", "finding": "Caller paragraph file SHA establishes selected bytes; saved source/text inventory and clause-context SHA do not independently bind original paragraph vector production.", "action": "Reviewed honesty patch exposesfalse producer authentication in prepare/describe. Require independent producer/vector receipt joins for stronger/new input admission; preserve original44 replay pins.", "sources": ["paragraph-caller-pin-control", "honesty-patch-review"]},
        {"id": "wording-scratch-status", "finding": "Earlier diagnostic prose mixed a completed successor with unexecuted scratch wording; the reviewed patch attributes execution only to the separately sealed normative successor.", "action": "Retain scratch as proposal with its own recipe identity, completed successor as actual execution; do not claim they are identical artifacts."},
        {"id": "currentness-versus-local-checkout", "finding": "Branch-agent795 effective-tree review preserves all103 sampled relevant paths, including published contextual39. Older dirty live checkout can lack those files.", "action": "Treat local absence as checkout drift; use fresh owned current-main checkouts, preserve dirtywork, and compare effective trees separately from ancestry."},
        {"id": "source-publication-versus-active-work", "finding": "Datasets grouped-span/deontic and accelerate larger-head/preview candidates remain active or unreviewed; source presence, Hub presence and catalog presence are independent stages.", "action": "Do not merge old broad trees or infer qualification from uploaded weights. Require exact owner/source/dependency/test review and fresh state/task bindings."},
        {"id": "unknown-native-identities", "finding": "Contextual private state serialization is known, while registered native output schema/profile/format remainsnull and all quality/runtime/proof flagsfalse.", "action": "Keep operators/tasks/assets separate; byte and shape authentication cannot invent an ABI/native profile or planner proof fact."},
        {"id": "logic-taxonomy-scope", "finding": "Historical35 family inventory, later40-family capability accounting, eight Legal floors and14 code routes describe different catalog/profile/version scopes.", "action": "Pin family catalog/version, applicable profiles, emitted distinctive operators and actual native checks; opaque atom/syntax/count success does not establish full semantics."},
        {"id": "corrected-reviewer-count", "finding": "The inherited matrix contains16 entries. An earlier reviewer message miscounted them as18.", "action": "Corrected by direct JSON count and SHA4ea1c62d…; no guide-count defect is claimed."},
    ]
    priorities = [
        {"priority": 0, "work": "Preserve and integrate exact current contributions", "reuse": "Prior16-study review; current795/effective39 and acceleratee3→d5 receipts; reviewed two-line honesty patch.", "deliver": "Effective-tree/lineage manifest, reviewed clean source selection, active-owner handoffs and exact source+asset+task pins.", "gate": "No automatic old branch replay or dirtytree reset; no numerical/teacher/proof promotion."},
        {"priority": 1, "work": "Admit complete paired formal targets and fresh source groups", "reuse": "Existing64 native source caches, reference barrier, source/recurrent traces and provenance/review owners.", "deliver": "Independently reviewed roles,modality/negation,qualifier presence/scope,binders,multiple rules and source/citation spans; TRAIN/tune/final grouped exposure ledger.", "gate": "All five64-source semantic masks arezero until valid review; never invent labels, simplify qualifiers or self-certify compiler/teacher agreement."},
        {"priority": 2, "work": "Make the decoder output contract lossless for those targets", "reuse": "Restricted32-vocabulary/512 Legal baseline; richer Intent/Security native codecs and fixed-tree coverage diagnostics.", "deliver": "Separate schema/version/task heads with vocabulary migration, presence/length/order/symbol binding and unsupported ledgers; separate legal_text_reconstruction information contract.", "gate": "Complete target must encode; encoder8192 or lower vectorMSE cannot repair an incompatible output grammar."},
        {"priority": 3, "work": "Compare compatible warm-started heads and retention", "reuse": "Original8D/384D donors, complete384/768 states, new normative endpoints and exact cached width-specific vectors.", "deliver": "Tensor/name/shape/dtype/codec transfer manifest; matched raw/PCA/AE/source-only conditioning and paragraph/clause/order controls; exposedv3 retention before candidate selection.", "gate": "Keep original controls; copied-head KL zero is preservation, not adapter learning; teacher-output KD needs screened qualified scope; rejected final attempts and aliases cannot be promoted."},
        {"priority": 4, "work": "Connect explicit experimental runtime selection to the supervisor", "reuse": "Exact ModelManager10 selectors and byte authentication, typed cached Legal facade, original fragment routes, current native planner/obligation adapters.", "deliver": "Opt-in candidate producer with exact source/cache/decoder IO/profile/task bindings, resource leases and truthful unavailable/refusal states; fresh reviewed task context after catalog/source generation changes.", "gate": "No accelerate contextual numerical callsite is established by the branch review. Unknown IDs stayunknown; generated IR remains candidate until source/native/checker gates pass."},
        {"priority": 5, "work": "Publish current-state proof indexing and intent grounding", "reuse": "RepositoryCodebaseIndex/CAS/AST captures, conditional evidence keys/reverse dependencies, signed companion/currentness and native family checkers.", "deliver": "Candidate index separate from attempt/proof index; source/model/checker/version/assumption hashes; dependent invalidation; current and desired post-change Intent symbol bindings.", "gate": "Whole declared inventory denominators and unsupported/deferred members remain visible. Embeddings,53→8 reconstruction or a source hash discharge no obligations."},
        {"priority": 6, "work": "Instantiate12 independent cells and stage model publication", "reuse": "Existing family/width declarations, AutoencoderRegistry/index owners, central ModelManager and immutable CAS/Hub receipts.", "deliver": "Separate family8/384/768 manifests, physically configured registry/index/DuckLake/catalog prefixes and public repositories; within each cell separate schema/task/profile/run/asset records.", "gate": "Declarative12 slots or670 central records do not prove12 stores/full decoders. Check new normative/grouped state catalog/Hub presence independently; append new asset records and preserve prior defaults."},
        {"priority": 7, "work": "Adapt repository-specific Codebase models in shadow", "reuse": "Compatible inherited structural/native parent, exact repository generation/caches, finite corpus/replay and existing owner leases.", "deliver": "Mandatory inherited policy, unknown-atom/basis/grammar gate, explicit optimizer-state policy, immutable new run and regression/canary comparison while prior admitted planner generation staysactive.", "gate": "Weights-only sidecars cannot claim Adam exact-resume; no online fitting inside planning requests or in-place sealed-context/checkpoint mutation."},
        {"priority": 8, "work": "Increase source and output spans independently", "reuse": "Current512 frozen encoder/cached decoder baselines and separately authenticated native768/4096 producer prerequisites.", "deliver": "Family-specific span curriculum, source token/offset/dependency accounting, output length/rule capacity and memory/cost comparisons, then8192 source experiment.", "gate": "768 is the actual GTE dimension; existing small source and max8-clause/512 output experiments do not qualify8192.4096 remains an independent lineage, not an extension of three requested cell widths."},
    ]
    connections = [
        {"family": "legal_ir", "contribution": "Learned source-only contextual/native rule candidates; existing deterministic canonical inverse and source-locked numeric Lake routes.", "formalization_handoff": "Validate complete native IR, retain source correspondence and nonempty qualifiers, generate actual applicable FOL/TDFOL/DCEC/CEC/frame/etc projections with loss/omission records, then trusted checks.", "remaining": "Original prose inverse, richer grammar/meaning, fresh groups and independently qualified teacher scope."},
        {"family": "codebase_ir", "contribution": "Current exact captured source/AST/dependency/structural representation and partial conditional proof index.", "formalization_handoff": "Bind a Codebase-native task/decoder and exact units to typed program/state/contract/trace obligations and verified source maps; cache checker outcomes with current dependency keys.", "remaining": "Independent source-to-formal semantics, complete inventory/worker dispatch and admitted larger heads; structural scan coverage remains separate from encoded/checked coverage."},
        {"family": "security_ir", "contribution": "Native fixed-shape projection readouts, source-scaffolded learned production choices and explicit complete-function/byte-map recovery.", "formalization_handoff": "Independent AST replay/source binding, reviewed header/security assumptions and eligible arithmetic/string/program/code projection checkers.", "remaining": "Unsupported source/topology coverage, variable grammar, source security specification and broad property claims; classifier/CVE/CWE labels are not proof."},
        {"family": "intent_ir", "contribution": "Narrow learned frame/normalized-text inverse, rich native fragment/reconstruction heads and deterministic workflow/action projections.", "formalization_handoff": "Ground intent goals/preconditions/effects against current Codebase symbols/source state and scoped checked facts, then compile residual/review obligations into the symbolic planner.", "remaining": "Open vocabulary/case-sensitive symbols/full workflows and independently derived satisfaction evidence; ID-presence or Lake syntax alone cannot satisfy intent."},
    ]
    result = {
        "schema": "autoencoder-progress-reconciliation-semantic-map/v1", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Extends the prior16-study review; pinned local ordinary evidence and peer effective-tree receipts. No new model inference/training, encoder, database, Hub or Git-ref mutation by this synthesis.",
        "sources": sources, "prior_reviewed_heads": prior["reviewed_remote_heads"],
        "current_peer_reviewed_heads": {"datasets": "795d960170214d03e2eaf4c0a13ad4eb922c5c08", "accelerate_initial": "e3a44a6ddf8a1373223eee015b2a2066f4ddd9fa", "accelerate_later_docs": "d5c59e961d1a0ca8d09296b520cbd414a2078235"},
        "inherited_prior_entry_count": 16, "inherited_prior_entries": inherited,
        "new_contribution_count": len(new), "new_contributions": new,
        "recomputed_metric_panels": metrics, "family_dimension_cells": cells,
        "claim_reconciliation": reconciliation, "cross_family_autoformalization_connections": connections,
        "prioritized_missing_integration": priorities,
        "logic_and_proof_boundaries": [
            "Eight distinct Legal floor capabilities and applicable14 code routes require exact family/profile/schema semantics. A particular source need only its applicable constructs; eight fabricated translations are not required.",
            "Nativev3 default63/66 supported checks still blocks all four full training panels. Separate authored smoke198 occurrences/12 builds/9 SANY establishes a gated handoff, not broad source fidelity or all40 families.",
            "Only actual applicable source-bound lake build<Lib> grants Lean admission; raw lean--json,PROOF enum,JSON schema,compiler rows and reconstruction loss cannot replace it.",
            "Logic projection features can reconstruct compiler targets or fixed trees while source-to-formula meaning remains wrong. Wrong UI candidates passing Lake demonstrate the need for independent source fidelity.",
            "Proof index must retain assumptions,backend/toolchain/profile,exact artifact/source/dependencies and current eligibility separately from model candidate/retrieval/parse observations.",
        ],
        "non_aggregation_rules": prior["non_aggregation_rules"] + [
            "Same semantic meanings under new wording are prospective wording evidence, not an untouched semantic holdout.",
            "Selected/last equal tensors,seed repeats,shared64 sources and duplicate8c02/3b39 artifact trees are controls or aliases, not independent studies.",
            "Native encoder preparation,decoder fitting,greedy observation,posthoc scoring,resource admission and cached/compiler/native-backend work need separate timing scopes.",
            "8D input,8D structural latent,8D token lexical rows and residual8 with a384 skip do not select interchangeable checkpoints or token budgets.",
        ],
        "reviewer_correction": "Prior matrix count is16; earlier messages claiming18 were a reviewer counting mistake and are superseded.",
        "operations": {"model_inference_executed": False, "training_executed": False, "encoder_executed": False,
            "database_or_network_executed": False, "repository_source_mutated": False, "git_refs_mutated": False,
            "proof_authority": False, "independent_metadata_controls_executed": True},
        "limitations": [
            "Peer branch reviews are sampled/bounded source-presence observations, not exhaustive qualification of unrelated branches. Dirty active work remains preserved and unqualified.",
            "Retained historical execution receipts are attributed to their exact source/corpus/model generations; rehashing JSON does not attest execution origin or fresh current runtime/Hub presence.",
            "This reviewer additionally executed only synthetic and original48 metadata controls under import/effect bombs. Those do not establish a new numerical replay or producer provenance.",
            "Sources are cooperative endpoint observations rather than an atomic cross-repository snapshot. Later documentation/source/publication changes need fresh verification.",
            "US Constitution formalization, global convergence,production teacher/runtime and broad source-to-law/code proof authority remain unestablished.",
        ],
    }
    if sources != {identity: observe(path) for identity, path in paths.items()}:
        raise ValueError("source evidence changed during synthesis")
    result["source_endpoints_unchanged"] = True
    target = OUT / "semantic-evidence-matrix.json"
    if target.exists():
        raise ValueError("do not overwrite a completed matrix")
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(observe(target)))


if __name__ == "__main__":
    main()
