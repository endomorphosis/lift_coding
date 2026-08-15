#!/usr/bin/env python3
"""Independent, read-only acceptance oracle for the VGO-001 wire contract."""

from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import math
import os
import selectors
import signal
import stat
import subprocess
import sys
import time
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Any

sys.dont_write_bytecode = True

ORACLE_SCHEMA = "verified-gui-optimizer-vgo001-oracle@1"
MAX_CANDIDATE_SOURCE_BYTES = 1_000_000
MAX_MANIFEST_ITEMS = 512
MAX_CHECKS = 16_000
MAX_ERRORS = 4_096
MAX_DETAIL_CHARS = 360
MAX_OUTPUT_BYTES = 65_536
MAX_CANDIDATE_OUTPUT_BYTES = 65_536
IMPORT_TIMEOUT_SECONDS = 5.0
CALL_TIMEOUT_SECONDS = 2.0
TOTAL_TIMEOUT_SECONDS = 30.0
WORKER_OUTPUT_LIMIT_BYTES = 65_536
_AUDIT_HOOK_INSTALLED = False
_SIDE_EFFECT_ATTEMPTS: list[str] = []
_FORBIDDEN_IMPORT_ATTEMPTS: list[str] = []
_CANDIDATE_TEST_EXEC_ATTEMPTS: list[str] = []

# Keep trusted references outside the candidate module's reach.  In particular,
# a candidate may mutate the shared ``json`` or ``os`` module objects while it is
# loaded.  The parent runs in a separate process, and the worker uses these saved
# callables only to serialize and emit its final report.
_JSON_DUMPS = json.dumps
_JSON_LOADS = json.loads
_OS_WRITE = os.write
_COMPILE = compile
_EXEC = exec

FORBIDDEN_IMPORT_PARTS = (
    "router_deps",
    "semantic_index",
    "semantic_capsule",
    "proof_cache",
    "proof_corpus",
    "model_routing",
    "ui_ux_ir",
)

SAFE_IMPLEMENTATION_IMPORTS = frozenset(
    {
        "__future__",
        ".schema",
        "collections.abc",
        "copy",
        "dataclasses",
        "enum",
        "json",
        "math",
        "re",
        "types",
        "typing",
        "unicodedata",
    }
)

SAFE_IMPLEMENTATION_FROM_IMPORTS = {
    "__future__": frozenset({"annotations"}),
    "collections.abc": frozenset({"Callable", "Iterable", "Mapping", "Sequence"}),
    "copy": frozenset({"deepcopy"}),
    "dataclasses": frozenset({"dataclass", "field"}),
    "enum": frozenset({"Enum", "StrEnum"}),
    "json": frozenset({"dumps", "loads"}),
    "math": frozenset({"isclose", "isfinite", "nextafter"}),
    "re": frozenset({"compile", "fullmatch"}),
    "types": frozenset({"MappingProxyType"}),
    "typing": frozenset({"Any", "ClassVar", "Final", "TypeVar"}),
    "unicodedata": frozenset({"normalize"}),
}

SAFE_IMPLEMENTATION_MODULE_ATTRIBUTES = {
    "copy": frozenset({"deepcopy"}),
    "json": frozenset({"dumps", "loads"}),
    "math": frozenset({"isclose", "isfinite", "nextafter"}),
    "re": frozenset({"compile", "fullmatch"}),
    "unicodedata": frozenset({"normalize"}),
}

REFLECTIVE_ATTRIBUTE_NAMES = frozenset(
    {
        "__base__",
        "__bases__",
        "__builtins__",
        "__class__",
        "__closure__",
        "__code__",
        "__dict__",
        "__delattr__",
        "__func__",
        "__getattr__",
        "__getattribute__",
        "__globals__",
        "__loader__",
        "__mro__",
        "__module__",
        "__annotations__",
        "__defaults__",
        "__kwdefaults__",
        "__reduce__",
        "__reduce_ex__",
        "__self__",
        "__setattr__",
        "__spec__",
        "__package__",
        "__subclasses__",
        "__traceback__",
        "ag_frame",
        "cr_frame",
        "f_globals",
        "gi_frame",
        "mro",
        "modules",
        "tb_frame",
    }
)

REFLECTIVE_GLOBAL_NAMES = frozenset(
    {
        "__builtins__",
        "__loader__",
        "__spec__",
    }
)

DANGEROUS_CALL_NAMES = frozenset(
    {
        "__import__",
        "compile",
        "eval",
        "exec",
        "open",
        "import_module",
        "spec_from_file_location",
        "globals",
        "breakpoint",
        "locals",
        "vars",
        "setattr",
        "delattr",
    }
)

REQUIRED_INTERFACES = (
    "AccessibilityReceipt@1",
    "GuiApplicationIdentity@1",
    "GuiImprovementProposal@1",
    "GuiImprovementReceipt@1",
    "GuiScreenIdentity@1",
    "InteractionReceipt@1",
    "UiAccessibilityContract@1",
    "UiActionBinding@1",
    "UiBaseline@1",
    "UiChangeSet@1",
    "UiComponentIdentity@1",
    "UiComponentVersion@1",
    "UiConstraintReceipt@1",
    "UiContextPack@1",
    "UiDependencyEdge@1",
    "UiEvaluationScenario@1",
    "UiEventDefinition@1",
    "UiInvalidationPlan@1",
    "UiLayoutConstraint@1",
    "UiSemanticCapsule@1",
    "UiStateDefinition@1",
    "UiTransitionDefinition@1",
    "VisualRegressionReceipt@1",
)

NULL_ARRAY_REGRESSIONS = (
    "AccessibilityReceipt@1.manual_check_ids",
    "AccessibilityReceipt@1.unsupported_criteria",
    "AccessibilityReceipt@1.violation_ids",
    "GuiImprovementProposal@1.expected_screenshot_ids",
    "GuiImprovementProposal@1.expected_test_ids",
    "GuiImprovementProposal@1.state_effect_ids",
    "GuiImprovementReceipt@1.rejection_reasons",
    "InteractionReceipt@1.action_invocation_ids",
    "InteractionReceipt@1.event_ids",
    "InteractionReceipt@1.focus_sequence",
    "InteractionReceipt@1.recovery_ids",
    "InteractionReceipt@1.unresolved_observation_ids",
    "UiAccessibilityContract@1.required_names",
    "UiAccessibilityContract@1.required_roles",
    "UiBaseline@1.artifact_digests",
    "UiChangeSet@1.action_ids",
    "UiChangeSet@1.component_ids",
    "UiChangeSet@1.state_ids",
    "UiConstraintReceipt@1.unsupported_check_ids",
    "UiConstraintReceipt@1.violated_check_ids",
    "UiContextPack@1.acceptance_criteria",
    "UiContextPack@1.affected_test_ids",
    "UiContextPack@1.artifact_digests",
    "UiContextPack@1.capsule_ids",
    "UiContextPack@1.escalation_conditions",
    "UiContextPack@1.invariant_failure_ids",
    "UiContextPack@1.state_machine_ids",
    "UiContextPack@1.style_token_paths",
    "UiEvaluationScenario@1.tags",
    "UiInvalidationPlan@1.affected_check_ids",
    "UiInvalidationPlan@1.affected_component_ids",
    "UiInvalidationPlan@1.affected_scenario_ids",
    "UiSemanticCapsule@1.action_binding_ids",
    "UiSemanticCapsule@1.action_side_effects",
    "UiSemanticCapsule@1.child_component_ids",
    "UiSemanticCapsule@1.dependency_edge_ids",
    "UiSemanticCapsule@1.emitted_event_ids",
    "UiSemanticCapsule@1.keyboard_focus_behavior",
    "UiSemanticCapsule@1.known_violation_ids",
    "UiSemanticCapsule@1.layout_responsive_behavior",
    "UiSemanticCapsule@1.localization_keys",
    "UiSemanticCapsule@1.prop_names",
    "UiSemanticCapsule@1.screenshot_ids",
    "UiSemanticCapsule@1.state_variable_ids",
    "UiSemanticCapsule@1.test_ids",
    "UiSemanticCapsule@1.transition_ids",
    "UiSemanticCapsule@1.unresolved_dynamic_behavior",
    "UiSemanticCapsule@1.visible_state_ids",
    "UiTransitionDefinition@1.effect_ids",
    "VisualRegressionReceipt@1.component_version_ids",
    "VisualRegressionReceipt@1.expected_change_regions",
    "VisualRegressionReceipt@1.forbidden_change_regions",
)

NULL_SCALAR_REGRESSIONS = (
    "GuiApplicationIdentity@1.display_name",
    "GuiApplicationIdentity@1.repository_root",
    "GuiImprovementProposal@1.context_pack_id",
    "GuiImprovementProposal@1.visual_effect_summary",
    "GuiImprovementReceipt@1.context_pack_id",
    "GuiImprovementReceipt@1.invalidation_plan_id",
    "GuiImprovementReceipt@1.patch_digest",
    "GuiScreenIdentity@1.route_id",
    "InteractionReceipt@1.confirmation_id",
    "UiAccessibilityContract@1.component_id",
    "UiAccessibilityContract@1.notes",
    "UiActionBinding@1.component_id",
    "UiActionBinding@1.policy_id",
    "UiChangeSet@1.summary",
    "UiComponentIdentity@1.screen_id",
    "UiComponentVersion@1.localization_digest",
    "UiConstraintReceipt@1.solver_id",
    "UiContextPack@1.baseline_id",
    "UiContextPack@1.excluded_context_explanation",
    "UiDependencyEdge@1.notes",
    "UiEventDefinition@1.description",
    "UiInvalidationPlan@1.fallback_explanation",
    "UiLayoutConstraint@1.breakpoint",
    "UiLayoutConstraint@1.component_id",
    "UiSemanticCapsule@1.accessibility_contract_id",
    "UiSemanticCapsule@1.empty_behavior",
    "UiSemanticCapsule@1.error_behavior",
    "UiSemanticCapsule@1.loading_behavior",
    "UiSemanticCapsule@1.source_revision",
    "UiSemanticCapsule@1.success_behavior",
    "UiStateDefinition@1.description",
    "UiStateDefinition@1.label",
    "UiTransitionDefinition@1.guard",
    "VisualRegressionReceipt@1.browser",
    "VisualRegressionReceipt@1.browser_version",
)

TOKEN_FIELDS = (
    "raw_source_tokens",
    "capsule_tokens",
    "screenshot_analysis_tokens",
    "other_context_tokens",
    "source_tokens_replaced_by_capsules",
    "ordinary_raw_dependency_tokens",
    "total_estimated_prompt_tokens",
    "token_budget",
    "compression_ratio",
)

ENUM_SCALAR_WIRE_CASES = (
    "AccessibilityReceipt@1.analysis_classification",
    "AccessibilityReceipt@1.evidence_level",
    "AccessibilityReceipt@1.keyboard_result",
    "AccessibilityReceipt@1.verification_status",
    "GuiImprovementProposal@1.analysis_classification",
    "GuiImprovementProposal@1.decision",
    "GuiImprovementProposal@1.route_kind",
    "GuiImprovementProposal@1.verification_status",
    "GuiImprovementReceipt@1.analysis_classification",
    "GuiImprovementReceipt@1.decision",
    "GuiImprovementReceipt@1.verification_status",
    "InteractionReceipt@1.analysis_classification",
    "InteractionReceipt@1.evidence_level",
    "InteractionReceipt@1.verification_status",
    "UiComponentIdentity@1.component_kind",
    "UiConstraintReceipt@1.analysis_classification",
    "UiConstraintReceipt@1.evidence_level",
    "UiConstraintReceipt@1.verification_status",
    "UiContextPack@1.analysis_classification",
    "UiContextPack@1.verification_status",
    "UiDependencyEdge@1.confidence",
    "UiDependencyEdge@1.extraction_method",
    "UiDependencyEdge@1.relation",
    "UiEventDefinition@1.kind",
    "UiInvalidationPlan@1.confidence",
    "UiLayoutConstraint@1.kind",
    "UiSemanticCapsule@1.analysis_classification",
    "UiSemanticCapsule@1.completeness_boundary",
    "UiSemanticCapsule@1.verification_status",
    "UiStateDefinition@1.kind",
    "VisualRegressionReceipt@1.analysis_classification",
    "VisualRegressionReceipt@1.decision",
    "VisualRegressionReceipt@1.evidence_level",
    "VisualRegressionReceipt@1.verification_status",
)

ENUM_ARRAY_WIRE_CASES = (
    "UiAccessibilityContract@1.requirement_kinds",
    "UiChangeSet@1.change_kinds",
    "UiConstraintReceipt@1.statuses",
    "UiInvalidationPlan@1.reasons",
)

CONTEXT_NESTED_ENUM_PATHS = (
    ("accessibility_violations", 0, "severity"),
    ("child_capsules", 0, "analysis_classification"),
    ("child_capsules", 0, "completeness_boundary"),
    ("child_capsules", 0, "stable_identity", "component_kind"),
    (
        "child_capsules",
        0,
        "version_identity",
        "stable_identity",
        "component_kind",
    ),
    ("child_capsules", 0, "verification_status"),
    ("formal_invariant_failures", 0, "status"),
    ("parent_capsules", 0, "analysis_classification"),
    ("parent_capsules", 0, "completeness_boundary"),
    ("parent_capsules", 0, "stable_identity", "component_kind"),
    (
        "parent_capsules",
        0,
        "version_identity",
        "stable_identity",
        "component_kind",
    ),
    ("parent_capsules", 0, "verification_status"),
    ("state_machine", "events", 0, "kind"),
    ("state_machine", "states", 0, "kind"),
    ("styles", 0, "style_kind"),
)

EMBEDDED_ENUM_PATHS = (
    ("UiComponentVersion@1", ("stable_identity", "component_kind")),
    ("UiSemanticCapsule@1", ("stable_identity", "component_kind")),
    (
        "UiSemanticCapsule@1",
        ("version_identity", "stable_identity", "component_kind"),
    ),
)

EMBEDDED_REGISTERED_SCHEMA_PATHS = (
    ("UiComponentVersion@1", ("optimizer_schema_version",)),
    ("UiSemanticCapsule@1", ("version_identity", "optimizer_schema_version")),
)

CONTEXT_REGISTERED_SCHEMA_PATHS = (
    ("child_capsules", 0, "version_identity", "optimizer_schema_version"),
    ("parent_capsules", 0, "version_identity", "optimizer_schema_version"),
)

SCHEMA_BY_INTERFACE = MappingProxyType(
    {
        "AccessibilityReceipt@1": "accessibility-receipt/v1",
        "GuiApplicationIdentity@1": "gui-application-identity/v1",
        "GuiImprovementProposal@1": "gui-improvement-proposal/v1",
        "GuiImprovementReceipt@1": "gui-improvement-receipt/v1",
        "GuiScreenIdentity@1": "gui-screen-identity/v1",
        "InteractionReceipt@1": "interaction-receipt/v1",
        "UiAccessibilityContract@1": "ui-accessibility-contract/v1",
        "UiActionBinding@1": "ui-action-binding/v1",
        "UiBaseline@1": "ui-baseline/v1",
        "UiChangeSet@1": "ui-change-set/v1",
        "UiComponentIdentity@1": "ui-component-identity/v1",
        "UiComponentVersion@1": "ui-component-version/v1",
        "UiConstraintReceipt@1": "ui-constraint-receipt/v1",
        "UiContextPack@1": "ui-context-pack/v1",
        "UiDependencyEdge@1": "ui-dependency-edge/v1",
        "UiEvaluationScenario@1": "ui-evaluation-scenario/v1",
        "UiEventDefinition@1": "ui-event-definition/v1",
        "UiInvalidationPlan@1": "ui-invalidation-plan/v1",
        "UiLayoutConstraint@1": "ui-layout-constraint/v1",
        "UiSemanticCapsule@1": "ui-semantic-capsule/v1",
        "UiStateDefinition@1": "ui-state-definition/v1",
        "UiTransitionDefinition@1": "ui-transition-definition/v1",
        "VisualRegressionReceipt@1": "visual-regression-receipt/v1",
    }
)

NESTED_SCHEMA_BY_INTERFACE = MappingProxyType(
    {
        "SourceSpan@1": "gui-source-span/v1",
        "UiContextAccessibilityViolation@1": "ui-context-accessibility-violation/v1",
        "UiContextFormalFailure@1": "ui-context-formal-failure/v1",
        "UiContextMetricBaseline@1": "ui-context-metric-baseline/v1",
        "UiContextRoute@1": "ui-context-route/v1",
        "UiContextScreenshotDescription@1": "ui-context-screenshot-description/v1",
        "UiContextSource@1": "ui-context-source/v1",
        "UiContextStateMachine@1": "ui-context-state-machine/v1",
        "UiContextStyle@1": "ui-context-style/v1",
        "UiContextTest@1": "ui-context-test/v1",
        "UiContextVisualReference@1": "ui-context-visual-reference/v1",
        "ViewportSpec@1": "gui-viewport-spec/v1",
        "VisualChangeRegion@1": "visual-change-region/v1",
    }
)

CONTEXT_PAYLOAD_FIELDS = (
    "raw_sources",
    "styles",
    "affected_tests",
    "parent_capsules",
    "child_capsules",
    "state_machine",
    "formal_invariant_failures",
    "accessibility_violations",
    "visual_references",
    "screenshot_descriptions",
    "affected_routes",
    "action_bindings",
    "metric_baseline",
)

LEGACY_CONTEXT_FIELDS = (
    "affected_test_ids",
    "capsule_ids",
    "invariant_failure_ids",
    "raw_source_paths",
    "replaced_source_tokens",
    "state_machine_ids",
    "style_token_paths",
    "estimated_tokens",
)

LEGACY_CAPSULE_FIELDS = (
    "keyboard_focus_behavior",
    "layout_responsive_behavior",
)

VISUAL_STRUCTURAL_FIELDS = (
    "pixel_diff_percent",
    "structural_diff_percent",
    "unexpected_layout_shift_count",
    "missing_control_count",
    "extra_control_count",
    "screenshot_width",
    "screenshot_height",
    "max_unexplained_diff_percent",
    "manual_review_threshold_percent",
)

_DIGESTS = tuple(f"sha256:{character * 64}" for character in "abcdef12345678")


def _record(interface: str, /, **fields: Any) -> dict[str, Any]:
    schemas = SCHEMA_BY_INTERFACE | NESTED_SCHEMA_BY_INTERFACE
    return {
        **fields,
        "interface": interface,
        "schema_version": schemas[interface],
    }


def _component_identity(
    qualified_name: str = "apps.agent-supervisor.ConsoleRoot",
) -> dict[str, Any]:
    return _record(
        "UiComponentIdentity@1",
        application_id="app:agent-supervisor",
        qualified_name=qualified_name,
        component_kind="screen",
        package_namespace="swissknife.web.js.apps",
        screen_id="screen:agent-supervisor",
    )


def _component_version(qualified_name: str = "apps.agent-supervisor.ConsoleRoot") -> dict[str, Any]:
    return _record(
        "UiComponentVersion@1",
        stable_identity=_component_identity(qualified_name),
        structure_digest=_DIGESTS[0],
        props_digest=_DIGESTS[1],
        state_digest=_DIGESTS[2],
        handlers_digest=_DIGESTS[3],
        accessibility_digest=_DIGESTS[4],
        styles_digest=_DIGESTS[5],
        actions_digest=_DIGESTS[6],
        localization_digest=_DIGESTS[7],
        extractor_version="1.0.0",
        optimizer_schema_version="ui-component-version/v1",
    )


def _capsule(capsule_id: str, qualified_name: str) -> dict[str, Any]:
    return _record(
        "UiSemanticCapsule@1",
        capsule_id=capsule_id,
        stable_identity=_component_identity(qualified_name),
        version_identity=_component_version(qualified_name),
        application_id="app:agent-supervisor",
        screen_id="screen:agent-supervisor",
        purpose="Bounded Agent Supervisor console surface",
        component_type="screen-root",
        analysis_classification="exact",
        verification_status="unverified",
        completeness_boundary="complete_within_boundary",
        prop_names=["goals", "tasks"],
        emitted_event_ids=["event:submit"],
        state_variable_ids=["state:ready"],
        visible_state_ids=["state:ready", "state:loading"],
        transition_ids=["transition:ready-to-loading"],
        action_binding_ids=["action:dispatch"],
        action_side_effects=["dispatch-goal"],
        layout_role="primary-workspace",
        responsive_behavior=["stack-on-narrow", "preserve-primary-action"],
        keyboard_interactions=["enter-submits", "escape-cancels-dialog"],
        focus_behavior=["restore-trigger-after-close", "trap-focus-in-modal"],
        child_component_ids=["comp:goal-form"],
        dependency_edge_ids=["edge:root-goal-form"],
        test_ids=["test:goal-form-a11y"],
        screenshot_ids=["screenshot:keyboard-desktop"],
        known_violation_ids=["violation:missing-label"],
        unresolved_dynamic_behavior=["plugin:opaque-widget"],
        localization_keys=["agentSupervisor.goal.label"],
        accessibility_contract_id="a11y:goal-form",
        confirmation_required=True,
        loading_behavior="Shows a named progress indicator.",
        empty_behavior="Shows bounded empty-state guidance.",
        success_behavior="Announces confirmed completion.",
        error_behavior="Shows an associated recoverable error.",
        source_revision="deadbeef",
    )


def _owned_fixtures() -> dict[str, dict[str, Any]]:
    identity = _component_identity()
    version = _component_version()
    action = _record(
        "UiActionBinding@1",
        action_id="action:dispatch",
        method="agentSupervisor.dispatch",
        schema_id="schema:dispatch@1",
        requires_confirmation=True,
        confirmation_id="confirm:dispatch",
        policy_id="policy:dispatch",
        depends_on_schema=True,
        is_destructive=False,
        component_id="comp:goal-form",
    )
    state = _record(
        "UiStateDefinition@1",
        state_id="state:ready",
        kind="ready",
        screen_id="screen:agent-supervisor",
        label="Ready",
        is_initial=True,
        is_terminal=False,
        description="The bounded workflow is ready.",
    )
    event = _record(
        "UiEventDefinition@1",
        event_id="event:submit",
        kind="submit",
        name="submit-goal",
        description="Submit the validated goal.",
    )
    transition = _record(
        "UiTransitionDefinition@1",
        transition_id="transition:ready-to-loading",
        from_state_id="state:ready",
        to_state_id="state:loading",
        event_id="event:submit",
        guard="form.valid && confirmation.current",
        effect_ids=["effect:dispatch"],
        is_noop=False,
    )
    parent = _capsule("capsule:console-shell", "apps.agent-supervisor.ConsoleShell")
    child = _capsule("capsule:goal-form", "apps.agent-supervisor.GoalForm")
    raw_content = "  const label = 'Goal';\n\treturn label;\n\n"
    style_content = "\t.primary {\r\n  color: var(--primary);\r\n}\r\n"
    test_content = " describe('goal form', () => {\n\n\tit('labels input', verify);\n}); "
    raw_tokens = 500
    capsule_tokens = 100
    screenshot_tokens = 50
    other_tokens = 25
    replaced_tokens = 900
    total_tokens = raw_tokens + capsule_tokens + screenshot_tokens + other_tokens
    ordinary_tokens = raw_tokens + replaced_tokens + screenshot_tokens + other_tokens
    context = _record(
        "UiContextPack@1",
        pack_id="pack:label-form",
        application_id="app:agent-supervisor",
        screen_id="screen:agent-supervisor",
        objective="Ensure the goal form has an accessible name.",
        baseline_id="baseline:agent-supervisor-v1",
        raw_sources=[
            _record(
                "UiContextSource@1",
                path="swissknife/web/js/apps/agent-supervisor.js",
                content=raw_content,
                component_id="comp:goal-form",
                editable=True,
            )
        ],
        styles=[
            _record(
                "UiContextStyle@1",
                path="swissknife/web/css/tokens.css",
                content=style_content,
                style_kind="design-token",
            )
        ],
        affected_tests=[
            _record(
                "UiContextTest@1",
                path="swissknife/test/unit/apps/agent-supervisor.test.ts",
                content=test_content,
                test_id="test:goal-form-a11y",
            )
        ],
        parent_capsules=[parent],
        child_capsules=[child],
        state_machine=_record(
            "UiContextStateMachine@1",
            machine_id="sm:agent-supervisor",
            initial_state_id="state:ready",
            states=[state],
            events=[event],
            transitions=[transition],
        ),
        formal_invariant_failures=[
            _record(
                "UiContextFormalFailure@1",
                invariant_id="invariant:input-accessible-name",
                status="violated",
                description="Goal input has no accessible name.",
            )
        ],
        accessibility_violations=[
            _record(
                "UiContextAccessibilityViolation@1",
                violation_id="violation:missing-label",
                severity="serious",
                description="Goal input lacks an associated label.",
            )
        ],
        visual_references=[
            _record(
                "UiContextVisualReference@1",
                artifact_digest=_DIGESTS[8],
                description="Desktop baseline before the bounded label repair.",
            )
        ],
        screenshot_descriptions=[
            _record(
                "UiContextScreenshotDescription@1",
                scenario_id="scenario:keyboard-only",
                artifact_digest=_DIGESTS[9],
                description="The goal form is visible at desktop width.",
            )
        ],
        artifact_digests=[_DIGESTS[8], _DIGESTS[9]],
        affected_routes=[
            _record(
                "UiContextRoute@1",
                route_id="route:agent-supervisor",
                path="/agent-supervisor",
            )
        ],
        action_bindings=[action],
        metric_baseline=_record(
            "UiContextMetricBaseline@1",
            metric_id="metric:goal-form",
            metrics={"interaction_steps": 3, "unlabeled_controls": 1},
        ),
        acceptance_criteria=["Goal input has one accessible name."],
        excluded_context_explanation="Unrelated applications are excluded.",
        escalation_conditions=["Escalate if action binding changes."],
        raw_source_tokens=raw_tokens,
        capsule_tokens=capsule_tokens,
        screenshot_analysis_tokens=screenshot_tokens,
        other_context_tokens=other_tokens,
        source_tokens_replaced_by_capsules=replaced_tokens,
        ordinary_raw_dependency_tokens=ordinary_tokens,
        total_estimated_prompt_tokens=total_tokens,
        token_budget=800,
        compression_ratio=(ordinary_tokens - total_tokens) / ordinary_tokens,
        analysis_classification="conservative",
        verification_status="unverified",
    )
    region_expected = _record(
        "VisualChangeRegion@1",
        region_id="region:label",
        x=0.25,
        y=0.25,
        width=0.25,
        height=0.25,
        evidence_reason="The label is the declared change target.",
    )
    region_forbidden = _record(
        "VisualChangeRegion@1",
        region_id="region:navigation",
        x=0.0,
        y=0.0,
        width=0.2,
        height=0.2,
        evidence_reason="Navigation is outside patch scope.",
    )
    viewport = _record(
        "ViewportSpec@1",
        width=1280,
        height=800,
        device_scale_factor=1,
    )
    source_span = _record(
        "SourceSpan@1",
        path="swissknife/web/js/apps/agent-supervisor.js",
        start_line=10,
        start_column=0,
        end_line=40,
        end_column=1,
    )
    fixtures = {
        "AccessibilityReceipt@1": _record(
            "AccessibilityReceipt@1",
            receipt_id="receipt:a11y-1",
            application_id="app:agent-supervisor",
            screen_id="screen:agent-supervisor",
            scenario_id="scenario:keyboard-only",
            repository_revision="deadbeef",
            automated_pass_count=12,
            violation_count=0,
            violation_ids=[],
            manual_check_ids=["manual:focus-order"],
            unsupported_criteria=["WCAG-1.3.5"],
            keyboard_result="satisfied",
            screen_reader_reviewed=False,
            evidence_level="automated",
            analysis_classification="exact",
            verification_status="verified",
        ),
        "GuiApplicationIdentity@1": _record(
            "GuiApplicationIdentity@1",
            application_id="app:agent-supervisor",
            package_namespace="swissknife.web.js.apps",
            display_name="Agent Supervisor",
            repository_root="swissknife",
        ),
        "GuiImprovementProposal@1": _record(
            "GuiImprovementProposal@1",
            proposal_id="proposal:label-form",
            application_id="app:agent-supervisor",
            screen_id="screen:agent-supervisor",
            objective="Ensure the goal form has an accessible name.",
            intended_file_paths=["swissknife/web/js/apps/agent-supervisor.js"],
            intended_component_ids=["comp:goal-form"],
            acceptance_criteria=["Goal input has one accessible name."],
            expected_test_ids=["test:goal-form-a11y"],
            expected_screenshot_ids=["screenshot:keyboard-desktop"],
            state_effect_ids=["state:ready"],
            visual_effect_summary="Adds the declared visible label.",
            route_kind="deterministic_transform",
            context_pack_id="pack:label-form",
            decision="pending",
            analysis_classification="exact",
            verification_status="unverified",
        ),
        "GuiImprovementReceipt@1": _record(
            "GuiImprovementReceipt@1",
            receipt_id="receipt:improvement-1",
            proposal_id="proposal:label-form",
            application_id="app:agent-supervisor",
            screen_id="screen:agent-supervisor",
            repository_revision="deadbeef",
            decision="accept",
            visual_receipt_ids=["receipt:visual-1"],
            accessibility_receipt_ids=["receipt:a11y-1"],
            interaction_receipt_ids=["receipt:interaction-1"],
            constraint_receipt_ids=["receipt:constraint-1"],
            invalidation_plan_id="invalidate:label-form",
            context_pack_id="pack:label-form",
            patch_digest=_DIGESTS[13],
            rejection_reasons=[],
            analysis_classification="exact",
            verification_status="verified",
        ),
        "GuiScreenIdentity@1": _record(
            "GuiScreenIdentity@1",
            application_id="app:agent-supervisor",
            screen_id="screen:agent-supervisor",
            route_id="route:agent-supervisor",
        ),
        "InteractionReceipt@1": _record(
            "InteractionReceipt@1",
            receipt_id="receipt:interaction-1",
            application_id="app:agent-supervisor",
            screen_id="screen:agent-supervisor",
            scenario_id="scenario:keyboard-only",
            repository_revision="deadbeef",
            step_ids=["step:focus-input", "step:activate-submit"],
            focus_sequence=["goal-input", "submit-button"],
            event_ids=["event:focus", "event:keyboard_activation"],
            action_invocation_ids=["invoke:dispatch"],
            confirmation_id="confirm:dispatch",
            recovery_ids=["recovery:return-ready"],
            unresolved_observation_ids=[],
            evidence_level="automated",
            analysis_classification="exact",
            verification_status="verified",
        ),
        "UiAccessibilityContract@1": _record(
            "UiAccessibilityContract@1",
            contract_id="a11y:goal-form",
            requirement_kinds=["accessible_name", "keyboard_activation"],
            required_roles=["form", "button"],
            required_names=["Goal", "Submit goal"],
            component_id="comp:goal-form",
            notes="Automated coverage does not establish full WCAG compliance.",
        ),
        "UiActionBinding@1": action,
        "UiBaseline@1": _record(
            "UiBaseline@1",
            baseline_id="baseline:agent-supervisor-v1",
            application_id="app:agent-supervisor",
            screen_id="screen:agent-supervisor",
            repository_revision="deadbeef",
            scenario_ids=["scenario:keyboard-only", "scenario:initial-load"],
            metric_digest=_DIGESTS[10],
            artifact_digests=[_DIGESTS[8], _DIGESTS[9]],
            extractor_version="1.0.0",
        ),
        "UiChangeSet@1": _record(
            "UiChangeSet@1",
            change_set_id="change:label-fix",
            change_kinds=["component_implementation", "accessibility"],
            file_paths=["swissknife/web/js/apps/agent-supervisor.js"],
            component_ids=["comp:goal-form"],
            state_ids=["state:ready"],
            action_ids=["action:dispatch"],
            summary="Add an accessible name to the goal form.",
        ),
        "UiComponentIdentity@1": identity,
        "UiComponentVersion@1": version,
        "UiConstraintReceipt@1": _record(
            "UiConstraintReceipt@1",
            receipt_id="receipt:constraint-1",
            application_id="app:agent-supervisor",
            screen_id="screen:agent-supervisor",
            repository_revision="deadbeef",
            check_ids=["check:reachable", "check:confirmation", "check:manual"],
            statuses=["satisfied", "violated", "unsupported"],
            violated_check_ids=["check:confirmation"],
            unsupported_check_ids=["check:manual"],
            solver_id="solver:finite-graph",
            evidence_level="structural",
            analysis_classification="exact",
            verification_status="structurally_valid",
        ),
        "UiContextPack@1": context,
        "UiDependencyEdge@1": _record(
            "UiDependencyEdge@1",
            source_component_id="comp:root",
            target_component_id="comp:goal-form",
            relation="contains",
            extraction_method="typescript_compiler_api",
            extractor_version="1.0.0",
            confidence="exact",
            source_span=source_span,
            notes="Exact compiler-derived edge.",
        ),
        "UiEvaluationScenario@1": _record(
            "UiEvaluationScenario@1",
            scenario_id="scenario:keyboard-only",
            name="Keyboard-only navigation",
            application_id="app:agent-supervisor",
            screen_id="screen:agent-supervisor",
            fixture_digest=_DIGESTS[11],
            viewport=viewport,
            locale="en-US",
            timezone="UTC",
            color_scheme="light",
            text_scale_percent=100,
            reduced_motion=True,
            tags=["keyboard", "a11y"],
        ),
        "UiEventDefinition@1": event,
        "UiInvalidationPlan@1": _record(
            "UiInvalidationPlan@1",
            plan_id="invalidate:label-form",
            change_set_id="change:label-fix",
            reasons=["component_changed"],
            affected_component_ids=["comp:goal-form"],
            affected_scenario_ids=["scenario:keyboard-only"],
            affected_check_ids=["check:accessible-name"],
            confidence="exact",
            fallback_triggered=False,
            fallback_explanation="No uncertainty requires broad fallback.",
        ),
        "UiLayoutConstraint@1": _record(
            "UiLayoutConstraint@1",
            constraint_id="layout:no-overflow",
            kind="no_horizontal_overflow",
            expression="content.width <= viewport.width",
            component_id="comp:root",
            breakpoint="mobile",
            lower_bound=320,
            upper_bound=1920,
        ),
        "UiSemanticCapsule@1": _capsule(
            "capsule:console-root", "apps.agent-supervisor.ConsoleRoot"
        ),
        "UiStateDefinition@1": state,
        "UiTransitionDefinition@1": transition,
        "VisualRegressionReceipt@1": _record(
            "VisualRegressionReceipt@1",
            receipt_id="receipt:visual-1",
            application_id="app:agent-supervisor",
            screen_id="screen:agent-supervisor",
            scenario_id="scenario:keyboard-only",
            repository_revision="deadbeef",
            component_version_ids=["version:console-root"],
            viewport=viewport,
            screenshot_digest=_DIGESTS[12],
            baseline_digest=_DIGESTS[13],
            decision="pass",
            evidence_level="heuristic",
            pixel_diff_percent=0.25,
            structural_diff_percent=0.1,
            unexpected_layout_shift_count=0,
            missing_control_count=0,
            extra_control_count=0,
            screenshot_width=1280,
            screenshot_height=800,
            expected_change_regions=[region_expected],
            forbidden_change_regions=[region_forbidden],
            max_unexplained_diff_percent=1.0,
            manual_review_threshold_percent=2.0,
            requires_human_review=False,
            color_scheme="light",
            locale="en-US",
            text_scale_percent=100,
            browser="chromium",
            browser_version="128.0.0",
            analysis_classification="heuristic",
            verification_status="simulated",
        ),
    }
    return {key: fixtures[key] for key in sorted(fixtures)}


OWNED_FIXTURES = MappingProxyType(_owned_fixtures())


def _top_level_fields(wire_type: type[Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            f"{interface}.{field}"
            for interface, payload in OWNED_FIXTURES.items()
            for field, value in payload.items()
            if type(value) is wire_type
        )
    )


ARRAY_WIRE_CASES = _top_level_fields(list)
SCALAR_WIRE_CASES = _top_level_fields(str)
DIGEST_WIRE_CASES = tuple(
    field
    for field in SCALAR_WIRE_CASES
    if OWNED_FIXTURES[field.split(".", 1)[0]][field.split(".", 1)[1]].startswith("sha256:")
)


class _WireStringSubclass(str):
    pass


class _WireIntegerSubclass(int):
    pass


class _WireFloatSubclass(float):
    pass


class _WireListSubclass(list[Any]):
    pass


class _WireDictSubclass(dict[str, Any]):
    pass


class _WireEnum(StrEnum):
    VALUE = "screen"


def _wire_enum(value: str) -> StrEnum:
    enum_type = StrEnum("_OracleWireEnum", {"VALUE": value})
    return enum_type.VALUE


@dataclass(frozen=True)
class _WireDataclass:
    value: str = "constructor-only"


class _OracleLimitError(RuntimeError):
    pass


class _OracleSideEffectError(RuntimeError):
    pass


class _BoundedOutputSink:
    encoding = "utf-8"
    errors = "strict"

    def __init__(self) -> None:
        self.byte_count = 0

    @property
    def buffer(self) -> _BoundedOutputSink:
        return self

    def write(self, value: str | bytes) -> int:
        encoded = value.encode() if type(value) is str else bytes(value)
        self.byte_count += len(encoded)
        if self.byte_count > MAX_CANDIDATE_OUTPUT_BYTES:
            raise _OracleLimitError(f"candidate output exceeded {MAX_CANDIDATE_OUTPUT_BYTES} bytes")
        return len(value)

    @staticmethod
    def flush() -> None:
        return None

    @staticmethod
    def isatty() -> bool:
        return False


def _deadline_expired(_signum: int, _frame: Any) -> None:
    raise _OracleLimitError("bounded operation exceeded its deadline")


@contextmanager
def _deadline(seconds: float) -> Iterable[None]:
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _deadline_expired)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous_handler)


@contextmanager
def _candidate_output(sink: _BoundedOutputSink) -> Iterable[None]:
    previous = (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__)
    sys.stdout = sink  # type: ignore[assignment]
    sys.stderr = sink  # type: ignore[assignment]
    sys.__stdout__ = sink  # type: ignore[assignment]
    sys.__stderr__ = sink  # type: ignore[assignment]
    try:
        yield
    finally:
        sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__ = previous


def _audit_side_effects(event: str, args: tuple[Any, ...]) -> None:
    if event == "import" and args:
        module_name = args[0]
        if type(module_name) is str and any(
            part in module_name.lower() for part in FORBIDDEN_IMPORT_PARTS
        ):
            _FORBIDDEN_IMPORT_ATTEMPTS.append(module_name)
            raise _OracleSideEffectError(f"candidate attempted excluded import: {module_name}")
    if event == "exec" and args:
        filename = getattr(args[0], "co_filename", "")
        if type(filename) is str and filename.endswith("test_models.py"):
            _CANDIDATE_TEST_EXEC_ATTEMPTS.append(filename)
            raise _OracleSideEffectError("candidate test code execution is prohibited")
        if type(filename) is str and any(
            part in filename.lower() for part in FORBIDDEN_IMPORT_PARTS
        ):
            _FORBIDDEN_IMPORT_ATTEMPTS.append(filename)
            raise _OracleSideEffectError(f"candidate attempted excluded code execution: {filename}")
    if event == "open":
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else -1
        if type(mode) is str and any(marker in mode for marker in ("w", "a", "x", "+")):
            _SIDE_EFFECT_ATTEMPTS.append("filesystem-write")
            raise _OracleSideEffectError(f"candidate attempted filesystem write: {mode}")
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        if type(flags) is int and flags >= 0 and flags & write_flags:
            _SIDE_EFFECT_ATTEMPTS.append("filesystem-write")
            raise _OracleSideEffectError(f"candidate attempted filesystem write flags: {flags}")
    if event.startswith("socket.") or event in {
        "os.system",
        "os.remove",
        "os.rename",
        "os.replace",
        "os.rmdir",
        "os.mkdir",
        "os.link",
        "os.symlink",
        "os.chdir",
        "os.chmod",
        "os.chown",
        "os.exec",
        "os.fork",
        "os.forkpty",
        "os.kill",
        "os.killpg",
        "os.posix_spawn",
        "os.spawn",
        "os.setxattr",
        "os.removexattr",
        "os.truncate",
        "os.utime",
        "os.putenv",
        "os.unsetenv",
        "shutil.copyfile",
        "shutil.copytree",
        "shutil.move",
        "subprocess.Popen",
        "pty.spawn",
        "_thread.start_new_thread",
    }:
        _SIDE_EFFECT_ATTEMPTS.append(event)
        raise _OracleSideEffectError(f"candidate attempted prohibited side effect: {event}")


class Oracle:
    def __init__(self, repo_root: Path) -> None:
        global _AUDIT_HOOK_INSTALLED
        if not _AUDIT_HOOK_INSTALLED:
            sys.addaudithook(_audit_side_effects)
            _AUDIT_HOOK_INSTALLED = True
        _SIDE_EFFECT_ATTEMPTS.clear()
        _FORBIDDEN_IMPORT_ATTEMPTS.clear()
        _CANDIDATE_TEST_EXEC_ATTEMPTS.clear()
        self.repo_root = repo_root
        self.datasets_root = repo_root / "external/ipfs_datasets"
        self.errors: list[dict[str, str]] = []
        self.check_count = 0
        self.started_at = time.monotonic()
        self.output_sink = _BoundedOutputSink()
        self.models: Any = None
        self.schema: Any = None
        self.decode_error: type[BaseException] = ValueError
        self.samples = OWNED_FIXTURES
        self.test_tree: ast.Module | None = None
        self.imported_candidate_modules: tuple[str, ...] = ()
        self.isolated_parent_packages = False

    def _candidate_call(self, operation: Callable[[], Any]) -> Any:
        with _deadline(CALL_TIMEOUT_SECONDS), _candidate_output(self.output_sink):
            return operation()

    def _exception_text(self, exc: BaseException) -> str:
        try:
            value = self._candidate_call(lambda: str(exc))
        except BaseException:  # noqa: BLE001 - exception display is untrusted too
            return "<exception detail unavailable>"
        return value[:MAX_DETAIL_CHARS] if type(value) is str else "<non-string detail>"

    def _model_wire(self, model: Any, code: str, detail: str) -> dict[str, Any] | None:
        value = self.accept(lambda: model.to_dict(), code, detail)
        if type(value) is not dict:
            self.check(
                False,
                f"{code}.type",
                f"{detail}; to_dict returned {type(value).__name__}",
            )
            return None
        return value

    def check(self, condition: bool, code: str, detail: str) -> bool:
        if time.monotonic() - self.started_at > TOTAL_TIMEOUT_SECONDS:
            raise _OracleLimitError(f"total runtime exceeded {TOTAL_TIMEOUT_SECONDS} seconds")
        if self.check_count >= MAX_CHECKS:
            raise _OracleLimitError(f"check limit exceeded ({MAX_CHECKS})")
        self.check_count += 1
        if condition:
            return True
        if len(self.errors) >= MAX_ERRORS:
            raise _OracleLimitError(f"error limit exceeded ({MAX_ERRORS})")
        self.errors.append({"code": code, "detail": detail[:MAX_DETAIL_CHARS]})
        return False

    def reject(self, operation: Callable[[], Any], code: str, detail: str) -> bool:
        try:
            self._candidate_call(operation)
        except (_OracleLimitError, _OracleSideEffectError) as exc:
            return self.check(
                False,
                code,
                f"{detail}; oracle guard fired: {self._exception_text(exc)}",
            )
        except self.decode_error:
            return self.check(True, code, detail)
        except BaseException as exc:  # noqa: BLE001 - classify unsafe rejection
            return self.check(
                False,
                code,
                (
                    f"{detail}; raised {type(exc).__name__}, not "
                    f"{self.decode_error.__name__}: {self._exception_text(exc)}"
                ),
            )
        return self.check(False, code, detail)

    def accept(self, operation: Callable[[], Any], code: str, detail: str) -> Any:
        try:
            value = self._candidate_call(operation)
        except BaseException as exc:  # noqa: BLE001 - produce closed JSON report
            self.check(
                False,
                code,
                f"{detail}; raised {type(exc).__name__}: {self._exception_text(exc)}",
            )
            return None
        self.check(True, code, detail)
        return value

    def check_omission(
        self,
        cls: type[Any],
        payload: dict[str, Any],
        field: str,
        expected_type: type[Any],
        qualified: str,
    ) -> None:
        candidate = copy.deepcopy(payload)
        candidate.pop(field, None)
        try:
            model = self._candidate_call(lambda: cls.from_dict(candidate))
        except (_OracleLimitError, _OracleSideEffectError) as exc:
            self.check(
                False,
                "wire.omission_guard",
                f"{qualified} omission fired oracle guard: {self._exception_text(exc)}",
            )
            return
        except self.decode_error:
            self.check(
                True,
                "wire.omission_required",
                f"{qualified} is required and omission rejected",
            )
            return
        except BaseException as exc:  # noqa: BLE001
            self.check(
                False,
                "wire.omission_exception",
                (f"{qualified} omission raised {type(exc).__name__}: {self._exception_text(exc)}"),
            )
            return
        wire = self._model_wire(
            model,
            "wire.omission_encode",
            f"{qualified} omission result could not serialize",
        )
        if wire is None:
            return
        self.check(
            field in wire and type(wire[field]) is expected_type,
            "wire.omission_default",
            f"{qualified} omission did not produce an exact {expected_type.__name__}",
        )

    def _read_candidate_source(self, path: Path) -> str | None:
        descriptor = -1
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            )
            metadata = os.fstat(descriptor)
        except OSError as exc:
            self.check(False, "source.missing", f"{path}: {exc}")
            return None
        try:
            if not self.check(
                stat.S_ISREG(metadata.st_mode),
                "source.regular_file",
                f"{path} must be an owned regular file",
            ):
                return None
            size = metadata.st_size
            if not self.check(
                0 < size <= MAX_CANDIDATE_SOURCE_BYTES,
                "source.size",
                f"{path} is {size} bytes; limit is {MAX_CANDIDATE_SOURCE_BYTES}",
            ):
                return None
            chunks: list[bytes] = []
            captured = 0
            while captured <= MAX_CANDIDATE_SOURCE_BYTES:
                chunk = os.read(
                    descriptor,
                    min(65_536, MAX_CANDIDATE_SOURCE_BYTES + 1 - captured),
                )
                if not chunk:
                    break
                chunks.append(chunk)
                captured += len(chunk)
            final_metadata = os.fstat(descriptor)
            if not self.check(
                captured == size
                and captured <= MAX_CANDIDATE_SOURCE_BYTES
                and (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)
                == (
                    final_metadata.st_dev,
                    final_metadata.st_ino,
                    final_metadata.st_size,
                    final_metadata.st_mtime_ns,
                ),
                "source.size_race",
                f"{path} changed while being read",
            ):
                return None
            return b"".join(chunks).decode("utf-8")
        except (OSError, UnicodeError) as exc:
            self.check(False, "source.read", f"{path}: {exc}")
            return None
        finally:
            os.close(descriptor)

    def _parse_candidate_source(self, path: Path) -> ast.Module | None:
        source = self._read_candidate_source(path)
        if source is None:
            return None
        try:
            return ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            self.check(False, "source.syntax", f"{path}: {exc}")
            return None

    @staticmethod
    def _owned_top_level_names(tree: ast.Module) -> frozenset[str]:
        imported: set[str] = set()
        declared: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(alias.asname or alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.update(alias.asname or alias.name for alias in node.names)
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                declared.add(node.name)
            elif isinstance(node, ast.Assign):
                targets = node.targets
                declared.update(target.id for target in targets if isinstance(target, ast.Name))
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and isinstance(
                node.target, ast.Name
            ):
                declared.add(node.target.id)
        return frozenset(name for name in declared - imported if not name.startswith("__"))

    def _check_import_boundary(
        self,
        tree: ast.Module,
        path: Path,
        *,
        relative_schema_names: frozenset[str] = frozenset(),
    ) -> bool:
        imports: list[str] = []
        imported_bindings: set[str] = set()
        module_bindings: dict[str, str] = {}
        call_only_bindings: set[str] = set()
        seen_import_bindings: set[str] = set()
        import_shape_errors: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
                    if alias.name not in SAFE_IMPLEMENTATION_MODULE_ATTRIBUTES:
                        import_shape_errors.append(ast.unparse(node))
                        continue
                    binding = alias.asname or alias.name
                    if binding in seen_import_bindings:
                        import_shape_errors.append(ast.unparse(node))
                        continue
                    seen_import_bindings.add(binding)
                    imported_bindings.add(binding)
                    module_bindings[binding] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module_name = ("." * node.level) + (node.module or "")
                imports.append(module_name)
                symbols_are_explicit = all(alias.name != "*" for alias in node.names)
                relative_schema_allowed = module_name == ".schema" and path.name == "models.py"
                if relative_schema_allowed:
                    allowed_symbols: frozenset[str] | None = relative_schema_names
                else:
                    allowed_symbols = SAFE_IMPLEMENTATION_FROM_IMPORTS.get(module_name)
                if (
                    not symbols_are_explicit
                    or allowed_symbols is None
                    or allowed_symbols is not None
                    and any(alias.name not in allowed_symbols for alias in node.names)
                ):
                    import_shape_errors.append(ast.unparse(node))
                    continue
                bindings = [alias.asname or alias.name for alias in node.names]
                if any(binding in seen_import_bindings for binding in bindings):
                    import_shape_errors.append(ast.unparse(node))
                    continue
                seen_import_bindings.update(bindings)
                imported_bindings.update(bindings)
                if module_name in SAFE_IMPLEMENTATION_MODULE_ATTRIBUTES:
                    call_only_bindings.update(alias.asname or alias.name for alias in node.names)
        offenders = sorted(
            name for name in imports if any(part in name.lower() for part in FORBIDDEN_IMPORT_PARTS)
        )
        safe = self.check(
            not offenders,
            "import.forbidden_static",
            f"{path.name} imports excluded modules: {offenders}",
        )
        if path.name in {"models.py", "schema.py"}:
            unexpected = sorted(name for name in imports if name not in SAFE_IMPLEMENTATION_IMPORTS)
            safe = (
                self.check(
                    not unexpected,
                    "import.unsafe_standard_library",
                    f"{path.name} imports non-sealed modules: {unexpected}",
                )
                and safe
            )
            safe = (
                self.check(
                    not import_shape_errors,
                    "import.unsafe_symbol_or_alias",
                    f"{path.name} uses unsealed import symbols or aliases: "
                    f"{sorted(import_shape_errors)}",
                )
                and safe
            )

            parents = {
                child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
            }
            dangerous_calls: list[str] = []
            dangerous_symbol_loads: list[str] = []
            reflective_attributes: list[str] = []
            reflective_globals: list[str] = []
            unsafe_module_attributes: list[str] = []
            module_object_uses: list[str] = []
            imported_binding_mutations: list[str] = []

            def root_name(node: ast.AST) -> str:
                while isinstance(node, (ast.Attribute, ast.Subscript)):
                    node = node.value
                return node.id if isinstance(node, ast.Name) else ""

            def safe_dynamic_self_attribute(node: ast.Call) -> bool:
                if (
                    len(node.args) < 2
                    or not isinstance(node.args[0], ast.Name)
                    or node.args[0].id != "self"
                    or not isinstance(node.args[1], ast.Name)
                ):
                    return False
                field_binding = node.args[1].id
                ancestor: ast.AST = node
                while ancestor in parents:
                    ancestor = parents[ancestor]
                    if isinstance(
                        ancestor,
                        (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda),
                    ):
                        return False
                    if not isinstance(ancestor, ast.For):
                        continue
                    if (
                        not isinstance(ancestor.target, ast.Name)
                        or ancestor.target.id != field_binding
                        or not isinstance(ancestor.iter, (ast.List, ast.Tuple))
                    ):
                        return False
                    field_names = [
                        item.value
                        for item in ancestor.iter.elts
                        if isinstance(item, ast.Constant) and type(item.value) is str
                    ]
                    stores = [
                        candidate
                        for candidate in ast.walk(ancestor)
                        if isinstance(candidate, ast.Name)
                        and isinstance(candidate.ctx, ast.Store)
                        and candidate.id == field_binding
                    ]
                    return (
                        len(field_names) == len(ancestor.iter.elts)
                        and bool(field_names)
                        and len(stores) == 1
                        and stores[0] is ancestor.target
                        and all(
                            name.isidentifier()
                            and not name.startswith("__")
                            and name not in REFLECTIVE_ATTRIBUTE_NAMES
                            for name in field_names
                        )
                    )
                return False

            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    parent = parents.get(node)
                    allowed_frozen_setattr = (
                        node.attr == "__setattr__"
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "object"
                        and isinstance(parent, ast.Call)
                        and parent.func is node
                        and bool(parent.args)
                        and isinstance(parent.args[0], ast.Name)
                        and parent.args[0].id == "self"
                    )
                    if node.attr in REFLECTIVE_ATTRIBUTE_NAMES and not allowed_frozen_setattr:
                        reflective_attributes.append(node.attr)
                    root = root_name(node)
                    if root in module_bindings and (
                        not isinstance(node.value, ast.Name)
                        or node.value.id != root
                        or node.attr
                        not in SAFE_IMPLEMENTATION_MODULE_ATTRIBUTES[module_bindings[root]]
                        or not isinstance(parent, ast.Call)
                        or parent.func is not node
                    ):
                        unsafe_module_attributes.append(ast.unparse(node))

                if isinstance(node, ast.Name):
                    if node.id in REFLECTIVE_GLOBAL_NAMES:
                        reflective_globals.append(node.id)
                    if isinstance(node.ctx, ast.Load) and node.id in DANGEROUS_CALL_NAMES:
                        dangerous_symbol_loads.append(node.id)
                    if isinstance(node.ctx, ast.Load) and node.id in {"getattr", "hasattr"}:
                        parent = parents.get(node)
                        if not (isinstance(parent, ast.Call) and parent.func is node):
                            dangerous_symbol_loads.append(node.id)
                    if isinstance(node.ctx, ast.Load) and node.id in call_only_bindings:
                        parent = parents.get(node)
                        if not (isinstance(parent, ast.Call) and parent.func is node):
                            unsafe_module_attributes.append(node.id)
                    if isinstance(node.ctx, (ast.Store, ast.Del)) and node.id in imported_bindings:
                        imported_binding_mutations.append(node.id)
                    if isinstance(node.ctx, ast.Load) and node.id in module_bindings:
                        parent = parents.get(node)
                        if not (
                            isinstance(parent, ast.Attribute)
                            and parent.value is node
                            and parent.attr
                            in SAFE_IMPLEMENTATION_MODULE_ATTRIBUTES[module_bindings[node.id]]
                        ):
                            module_object_uses.append(node.id)

                rebound_name = ""
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    rebound_name = node.name
                elif isinstance(node, ast.arg):
                    rebound_name = node.arg
                elif isinstance(node, ast.ExceptHandler) and type(node.name) is str:
                    rebound_name = node.name
                elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and type(node.name) is str:
                    rebound_name = node.name
                elif isinstance(node, ast.MatchMapping) and type(node.rest) is str:
                    rebound_name = node.rest
                elif (
                    isinstance(node, (ast.TypeVar, ast.ParamSpec, ast.TypeVarTuple))
                    and type(node.name) is str
                ):
                    rebound_name = node.name
                if rebound_name in imported_bindings:
                    imported_binding_mutations.append(rebound_name)
                if isinstance(node, (ast.Global, ast.Nonlocal)):
                    imported_binding_mutations.extend(
                        name for name in node.names if name in imported_bindings
                    )

                targets: list[ast.AST] = []
                if isinstance(node, ast.Assign):
                    targets = list(node.targets)
                elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                    targets = [node.target]
                elif isinstance(node, ast.Delete):
                    targets = list(node.targets)
                for target in targets:
                    root = root_name(target)
                    if root in imported_bindings:
                        imported_binding_mutations.append(ast.unparse(target))

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "import_module",
                    "open",
                    "spec_from_file_location",
                }:
                    name = node.func.attr
                if name in DANGEROUS_CALL_NAMES:
                    dangerous_calls.append(name)
                if isinstance(node.func, ast.Name) and node.func.id in {"getattr", "hasattr"}:
                    attribute = node.args[1] if len(node.args) > 1 else None
                    base = node.args[0] if node.args else None
                    constant_attribute = (
                        attribute.value
                        if isinstance(attribute, ast.Constant) and type(attribute.value) is str
                        else None
                    )
                    if (
                        constant_attribute in REFLECTIVE_ATTRIBUTE_NAMES
                        or type(constant_attribute) is str
                        and constant_attribute.startswith("__")
                        or root_name(base) in imported_bindings
                        or constant_attribute is None
                        and not safe_dynamic_self_attribute(node)
                    ):
                        dangerous_calls.append(node.func.id)
            safe = (
                self.check(
                    not dangerous_calls and not dangerous_symbol_loads,
                    "import.dynamic_execution",
                    f"{path.name} uses dynamic execution symbols: "
                    f"calls={sorted(dangerous_calls)}, "
                    f"loads={sorted(dangerous_symbol_loads)}",
                )
                and safe
            )
            safe = (
                self.check(
                    not reflective_attributes and not reflective_globals,
                    "import.reflective_attribute",
                    f"{path.name} accesses reflective state: "
                    f"attributes={sorted(reflective_attributes)}, "
                    f"globals={sorted(reflective_globals)}",
                )
                and safe
            )
            safe = (
                self.check(
                    not unsafe_module_attributes and not module_object_uses,
                    "import.shared_module_access",
                    f"{path.name} accesses unsealed shared-module state: "
                    f"attributes={sorted(unsafe_module_attributes)}, "
                    f"objects={sorted(module_object_uses)}",
                )
                and safe
            )
            safe = (
                self.check(
                    not imported_binding_mutations,
                    "import.shared_binding_mutation",
                    f"{path.name} mutates imported bindings: {sorted(imported_binding_mutations)}",
                )
                and safe
            )
        return safe

    @staticmethod
    def _synthetic_package(name: str, path: Path) -> ModuleType:
        package = ModuleType(name)
        package.__package__ = name
        package.__path__ = [str(path)]  # type: ignore[attr-defined]
        return package

    @staticmethod
    def _load_compiled_module(name: str, path: Path, code: Any) -> ModuleType:
        module = ModuleType(name)
        module.__file__ = str(path)
        module.__package__ = name.rpartition(".")[0]
        module.__spec__ = importlib.util.spec_from_loader(name, loader=None)
        sys.modules[name] = module
        _EXEC(code, module.__dict__)
        return module

    def load(self) -> bool:
        package_root = self.datasets_root / "ipfs_datasets_py/logic/gui_optimizer"
        test_path = self.datasets_root / "tests/unit/logic/gui_optimizer/test_models.py"
        try:
            package_metadata = package_root.lstat()
        except OSError as exc:
            self.check(False, "package.missing", f"{package_root}: {exc}")
            return False
        if not self.check(
            stat.S_ISDIR(package_metadata.st_mode),
            "package.regular_directory",
            f"{package_root} must be a real directory, not a link",
        ):
            return False
        schema_path = package_root / "schema.py"
        models_path = package_root / "models.py"
        schema_tree = self._parse_candidate_source(schema_path)
        models_tree = self._parse_candidate_source(models_path)
        self.test_tree = self._parse_candidate_source(test_path)
        if schema_tree is None or models_tree is None or self.test_tree is None:
            return False
        schema_safe = self._check_import_boundary(schema_tree, schema_path)
        models_safe = self._check_import_boundary(
            models_tree,
            models_path,
            relative_schema_names=self._owned_top_level_names(schema_tree),
        )
        test_safe = self._check_import_boundary(self.test_tree, test_path)
        if not schema_safe or not models_safe or not test_safe:
            return False
        try:
            schema_code = _COMPILE(
                schema_tree,
                str(schema_path),
                "exec",
                dont_inherit=True,
                optimize=0,
            )
            models_code = _COMPILE(
                models_tree,
                str(models_path),
                "exec",
                dont_inherit=True,
                optimize=0,
            )
        except (TypeError, ValueError, SyntaxError) as exc:
            self.check(False, "source.compile", f"{type(exc).__name__}: {exc}")
            return False

        package_names = (
            "ipfs_datasets_py",
            "ipfs_datasets_py.logic",
            "ipfs_datasets_py.logic.gui_optimizer",
        )
        module_names = (
            *package_names,
            "ipfs_datasets_py.logic.gui_optimizer.schema",
            "ipfs_datasets_py.logic.gui_optimizer.models",
        )
        missing = object()
        saved = {name: sys.modules.get(name, missing) for name in module_names}
        before = frozenset(sys.modules)
        packages = {
            package_names[0]: self._synthetic_package(
                package_names[0], self.datasets_root / "ipfs_datasets_py"
            ),
            package_names[1]: self._synthetic_package(
                package_names[1], self.datasets_root / "ipfs_datasets_py/logic"
            ),
            package_names[2]: self._synthetic_package(package_names[2], package_root),
        }
        try:
            sys.modules.update(packages)
            with _deadline(IMPORT_TIMEOUT_SECONDS), _candidate_output(self.output_sink):
                schema = self._load_compiled_module(
                    "ipfs_datasets_py.logic.gui_optimizer.schema",
                    schema_path,
                    schema_code,
                )
                models = self._load_compiled_module(
                    "ipfs_datasets_py.logic.gui_optimizer.models",
                    models_path,
                    models_code,
                )
            imported = tuple(sorted(set(sys.modules) - before))
            self.imported_candidate_modules = imported
            self.isolated_parent_packages = all(
                sys.modules.get(name) is package for name, package in packages.items()
            )
            self.check(
                self.isolated_parent_packages,
                "import.parent_init",
                "candidate replaced a synthetic parent package",
            )
            forbidden_loaded = tuple(
                name
                for name in imported
                if any(part in name.lower() for part in FORBIDDEN_IMPORT_PARTS)
            )
            self.check(
                not forbidden_loaded,
                "import.router_deps",
                f"isolated load imported excluded modules: {forbidden_loaded}",
            )
            self.models = models
            self.schema = schema
            decode_error = getattr(schema, "GuiOptimizerDecodeError", None)
            decode_error_safe = (
                isinstance(decode_error, type)
                and issubclass(decode_error, Exception)
                and decode_error is not Exception
                and not issubclass(_OracleLimitError, decode_error)
                and not issubclass(_OracleSideEffectError, decode_error)
                and getattr(decode_error, "__name__", "") == "GuiOptimizerDecodeError"
            )
            if not decode_error_safe:
                self.check(
                    False,
                    "decode_error.unsafe",
                    "GuiOptimizerDecodeError is missing, overly broad, or masks oracle guards",
                )
                return False
            self.decode_error = decode_error
        except BaseException as exc:  # noqa: BLE001
            self.check(
                False,
                "import.failed",
                f"{type(exc).__name__}: {self._exception_text(exc)}",
            )
            return False
        finally:
            for name in tuple(sys.modules):
                if name not in before and name.startswith("ipfs_datasets_py"):
                    sys.modules.pop(name, None)
            for name, value in saved.items():
                if value is missing:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value
        return True

    def check_declared_artifacts(self) -> None:
        package_root = self.datasets_root / "ipfs_datasets_py/logic/gui_optimizer"
        test_root = self.datasets_root / "tests/unit/logic/gui_optimizer"
        package_files = {path.name for path in package_root.glob("*.py")}
        test_files = {path.name for path in test_root.glob("*.py")}
        required_package_files = {"__init__.py", "models.py", "schema.py"}
        allowed_package_files = {
            *required_package_files,
            "formal_adapter.py",
            "identity.py",
            "invariants.py",
            "receipts.py",
        }
        required_test_files = {"test_models.py"}
        allowed_test_files = {
            *required_test_files,
            "test_formal_adapter.py",
            "test_identity.py",
            "test_identity_vectors.py",
            "test_invariants.py",
            "test_receipts.py",
        }
        self.check(
            required_package_files <= package_files <= allowed_package_files,
            "artifacts.package",
            f"missing core or undeclared package artifacts: {sorted(package_files)}",
        )
        self.check(
            required_test_files <= test_files <= allowed_test_files,
            "artifacts.tests",
            f"missing core or undeclared candidate tests: {sorted(test_files)}",
        )
        self.check(
            not any("test_models" in name for name in self.imported_candidate_modules),
            "import.candidate_tests",
            "implementation-owned candidate tests were executed",
        )

    def model_class(self, interface: str) -> type[Any] | None:
        value = getattr(self.models, interface.split("@", 1)[0], None)
        if not isinstance(value, type):
            self.check(False, "model.missing", f"missing class for {interface}")
            return None
        return value

    def payload(self, interface: str) -> dict[str, Any] | None:
        sample = self.samples.get(interface)
        if sample is None:
            self.check(False, "sample.missing", f"missing sample {interface}")
            return None
        return copy.deepcopy(sample)

    def _check_identity_vectors(
        self,
        cls: type[Any],
        payload: dict[str, Any],
        interface: str,
        schema_version: str,
        location: str,
    ) -> None:
        valid_payload = copy.deepcopy(payload)
        model = self.accept(
            lambda c=cls, p=valid_payload: c.from_dict(p),
            "identity.valid",
            f"{location} rejected exact interface/schema_version",
        )
        if model is not None:
            wire = self._model_wire(
                model,
                "identity.valid_roundtrip",
                f"{location} exact identity result could not serialize",
            )
            if wire is not None:
                self.check(
                    wire.get("interface") == interface
                    and wire.get("schema_version") == schema_version,
                    "identity.valid_preservation",
                    f"{location} changed exact interface/schema_version",
                )
        for field in ("interface", "schema_version"):
            missing = copy.deepcopy(payload)
            missing.pop(field, None)
            self.reject(
                lambda c=cls, p=missing: c.from_dict(p),
                "identity.omitted",
                f"{location} synthesized missing {field}",
            )

        other_interface = next(
            item
            for item in (*REQUIRED_INTERFACES, *NESTED_SCHEMA_BY_INTERFACE)
            if item != interface
        )
        other_schema = next(
            item
            for item in (*SCHEMA_BY_INTERFACE.values(), *NESTED_SCHEMA_BY_INTERFACE.values())
            if item != schema_version
        )
        for field, vectors in (
            (
                "interface",
                (
                    ("arbitrary", "not an interface"),
                    ("registered-mismatch", other_interface),
                    ("unregistered", "OracleUnknown@999"),
                ),
            ),
            (
                "schema_version",
                (
                    ("arbitrary", "not a schema"),
                    ("registered-mismatch", other_schema),
                    ("unregistered", "oracle-unknown/v999"),
                ),
            ),
        ):
            for label, invalid in vectors:
                candidate = copy.deepcopy(payload)
                candidate[field] = invalid
                self.reject(
                    lambda c=cls, p=candidate: c.from_dict(p),
                    "identity.wrong_string",
                    f"{location} accepted {label} {field}={invalid!r}",
                )

    def check_inventory(self) -> None:
        self.check(
            len(REQUIRED_INTERFACES) == 23,
            "oracle.required_count",
            "oracle required-model inventory drifted",
        )
        actual = tuple(sorted(self.samples))
        self.check(
            actual == REQUIRED_INTERFACES,
            "models.inventory",
            f"required interfaces differ: expected={REQUIRED_INTERFACES!r} actual={actual!r}",
        )
        registry = tuple(sorted(getattr(self.schema, "REQUIRED_MODEL_INTERFACES", ())))
        self.check(
            registry == REQUIRED_INTERFACES,
            "schema.interface_inventory",
            "authoritative schema registry does not equal the 23 interfaces",
        )
        schema_registry = getattr(self.schema, "SCHEMA_VERSION_BY_INTERFACE", None)
        self.check(
            type(schema_registry) in (dict, MappingProxyType)
            and dict(schema_registry) == dict(SCHEMA_BY_INTERFACE),
            "schema.version_registry",
            "SCHEMA_VERSION_BY_INTERFACE differs from the protected 23-model registry",
        )
        nested_schema_registry = getattr(self.schema, "NESTED_SCHEMA_VERSION_BY_INTERFACE", None)
        self.check(
            type(nested_schema_registry) in (dict, MappingProxyType)
            and dict(nested_schema_registry) == dict(NESTED_SCHEMA_BY_INTERFACE),
            "schema.nested_version_registry",
            "NESTED_SCHEMA_VERSION_BY_INTERFACE differs from the protected registry",
        )
        registered = getattr(self.schema, "REGISTERED_OPTIMIZER_SCHEMA_VERSIONS", None)
        expected_schemas = frozenset(
            (*SCHEMA_BY_INTERFACE.values(), *NESTED_SCHEMA_BY_INTERFACE.values())
        )
        self.check(
            type(registered) is frozenset and registered == expected_schemas,
            "schema.registered_versions",
            "registered optimizer schemas differ from the protected model+nested set",
        )
        model_registry = getattr(self.models, "MODEL_TYPES", None)
        self.check(
            type(model_registry) in (dict, MappingProxyType)
            and tuple(sorted(model_registry)) == REQUIRED_INTERFACES,
            "models.type_registry",
            "MODEL_TYPES must register exactly the 23 protected models",
        )
        nested_registry = getattr(self.models, "NESTED_MODEL_TYPES", None)
        self.check(
            type(nested_registry) in (dict, MappingProxyType)
            and tuple(sorted(nested_registry)) == tuple(sorted(NESTED_SCHEMA_BY_INTERFACE)),
            "models.nested_type_registry",
            "NESTED_MODEL_TYPES must register exactly the protected nested records",
        )
        decode_model = getattr(self.models, "decode_model", None)
        self.check(
            callable(decode_model),
            "models.decode_registry",
            "decode_model is missing",
        )
        for interface in REQUIRED_INTERFACES:
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            self.check(
                payload.get("interface") == interface,
                "wire.interface",
                f"{interface} emits the wrong interface identity",
            )
            self.check(
                payload.get("schema_version") == SCHEMA_BY_INTERFACE[interface],
                "wire.schema",
                f"{interface} has the wrong protected schema identity",
            )
            self.check(
                getattr(cls, "INTERFACE", None) == interface
                and getattr(cls, "SCHEMA_VERSION", None) == SCHEMA_BY_INTERFACE[interface],
                "model.class_identity",
                f"{interface} class identity differs from its registry identity",
            )
            roundtrip_payload = copy.deepcopy(payload)
            model = self.accept(
                lambda c=cls, p=roundtrip_payload: c.from_dict(p),
                "roundtrip.decode",
                f"{interface} rejected its protected fixture",
            )
            if model is not None:
                wire = self._model_wire(
                    model,
                    "roundtrip.encode",
                    f"{interface} could not serialize its protected fixture",
                )
                self.check(
                    type(wire) is dict and wire == payload,
                    "roundtrip.exact",
                    f"{interface} input != roundtrip output",
                )
                if callable(decode_model):
                    registry_payload = copy.deepcopy(payload)
                    decoded = self.accept(
                        lambda p=registry_payload: decode_model(p),
                        "roundtrip.registry_decode",
                        f"decode_model rejected {interface}",
                    )
                    if decoded is not None:
                        decoded_wire = self._model_wire(
                            decoded,
                            "roundtrip.registry_encode",
                            f"decode_model result for {interface} could not serialize",
                        )
                        if decoded_wire is not None:
                            self.check(
                                decoded_wire == payload,
                                "roundtrip.registry_exact",
                                f"decode_model changed {interface}",
                            )
            unknown = copy.deepcopy(payload)
            unknown["__vgo001_oracle_unknown__"] = True
            self.reject(
                lambda c=cls, p=unknown: c.from_dict(p),
                "wire.unknown_field",
                f"{interface} accepted an unknown field",
            )
            self._check_identity_vectors(
                cls,
                payload,
                interface,
                SCHEMA_BY_INTERFACE[interface],
                interface,
            )
            self.reject(
                lambda c=cls, p=payload: c.from_dict(MappingProxyType(p)),
                "wire.mapping_proxy",
                f"{interface} accepted MappingProxyType",
            )
            dict_subclass = _WireDictSubclass(payload)
            self.reject(
                lambda c=cls, p=dict_subclass: c.from_dict(p),
                "wire.dict_subclass",
                f"{interface} accepted a dict subclass",
            )
            if model is not None:
                self.reject(
                    lambda c=cls, s=model: c.from_dict(s),
                    "wire.model_instance",
                    f"{interface} accepted a model instance as wire input",
                )
            self._check_exact_json(payload, interface)
            self._check_defensive_copy(cls, payload, interface)

        if type(nested_registry) in (dict, MappingProxyType):
            for interface, schema_version in NESTED_SCHEMA_BY_INTERFACE.items():
                cls = nested_registry.get(interface)
                self.check(
                    isinstance(cls, type)
                    and getattr(cls, "INTERFACE", None) == interface
                    and getattr(cls, "SCHEMA_VERSION", None) == schema_version,
                    "nested.class_identity",
                    f"nested registry identity mismatch for {interface}",
                )

    def _manifest_values(self, name: str) -> list[Any] | None:
        if self.test_tree is None:
            self.check(False, "manifest.source_missing", "candidate test AST unavailable")
            return None
        expression: ast.expr | None = None
        for statement in self.test_tree.body:
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                targets = (
                    statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                )
                if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                    expression = statement.value
                    break
        if expression is None:
            self.check(False, "manifest.missing", f"candidate tests lack literal {name}")
            return None
        try:
            value = ast.literal_eval(expression)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            self.check(
                False,
                "manifest.nonliteral",
                f"{name} must be an oracle-comparable literal sequence",
            )
            return None
        if type(value) not in (list, tuple):
            self.check(
                False,
                "manifest.type",
                f"{name} must be a literal list or tuple",
            )
            return None
        if not self.check(
            len(value) <= MAX_MANIFEST_ITEMS,
            "manifest.limit",
            f"{name} exceeds {MAX_MANIFEST_ITEMS} items",
        ):
            return None
        return list(value)

    def _manifest_parametrized_and_used(self, name: str) -> bool:
        if self.test_tree is None:
            return False

        def parameter_names(expression: ast.expr) -> tuple[str, ...]:
            if isinstance(expression, ast.Constant) and type(expression.value) is str:
                return tuple(part.strip() for part in expression.value.split(",") if part.strip())
            if isinstance(expression, (ast.List, ast.Tuple)) and all(
                isinstance(item, ast.Constant) and type(item.value) is str
                for item in expression.elts
            ):
                return tuple(item.value for item in expression.elts)  # type: ignore[union-attr]
            return ()

        for function in (
            node
            for node in self.test_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ):
            for decorator in function.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                callable_name = (
                    decorator.func.attr
                    if isinstance(decorator.func, ast.Attribute)
                    else decorator.func.id
                    if isinstance(decorator.func, ast.Name)
                    else ""
                )
                if callable_name != "parametrize":
                    continue
                arguments = {item.arg: item.value for item in decorator.keywords if item.arg}
                argnames = decorator.args[0] if decorator.args else arguments.get("argnames")
                argvalues = (
                    decorator.args[1] if len(decorator.args) > 1 else arguments.get("argvalues")
                )
                if argnames is None or argvalues is None:
                    continue
                if not any(
                    isinstance(node, ast.Name)
                    and isinstance(node.ctx, ast.Load)
                    and node.id == name
                    for node in ast.walk(argvalues)
                ):
                    continue
                parametrized_names = frozenset(parameter_names(argnames))
                function_parameters = {
                    argument.arg
                    for argument in (
                        *function.args.posonlyargs,
                        *function.args.args,
                        *function.args.kwonlyargs,
                    )
                }
                loaded_body_names = {
                    node.id
                    for statement in function.body
                    for node in ast.walk(statement)
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                }
                if (
                    parametrized_names
                    and parametrized_names <= function_parameters
                    and parametrized_names <= loaded_body_names
                ):
                    return True
        return False

    def _literal_manifest(self, name: str, expected: tuple[str, ...]) -> None:
        values = self._manifest_values(name)
        if values is None:
            return
        exact = tuple(values)
        self.check(
            all(type(item) is str for item in exact),
            "manifest.literal_strings",
            f"{name} must contain only exact strings",
        )
        self.check(
            exact == expected,
            "manifest.exact",
            f"{name} does not equal the sealed sorted {len(expected)}-field set",
        )
        self.check(
            len(exact) == len(set(exact)),
            "manifest.duplicates",
            f"{name} contains duplicate fields",
        )
        self.check(
            self._manifest_parametrized_and_used(name),
            "manifest.parametrized_use",
            f"{name} is not consumed by a non-vacuous pytest parametrization",
        )

    def check_manifests_and_wire_fields(self) -> None:
        self.check(
            len(NULL_ARRAY_REGRESSIONS) == 52
            and tuple(sorted(NULL_ARRAY_REGRESSIONS)) == NULL_ARRAY_REGRESSIONS,
            "oracle.null_array_inventory",
            "oracle 52-field array baseline drifted",
        )
        self.check(
            len(NULL_SCALAR_REGRESSIONS) == 35
            and tuple(sorted(NULL_SCALAR_REGRESSIONS)) == NULL_SCALAR_REGRESSIONS,
            "oracle.null_scalar_inventory",
            "oracle 35-field scalar baseline drifted",
        )
        self._literal_manifest("NULL_ARRAY_REGRESSIONS", NULL_ARRAY_REGRESSIONS)
        self._literal_manifest("NULL_SCALAR_REGRESSIONS", NULL_SCALAR_REGRESSIONS)
        self._literal_manifest("ARRAY_WIRE_CASES", ARRAY_WIRE_CASES)
        self._literal_manifest("SCALAR_WIRE_CASES", SCALAR_WIRE_CASES)
        self._literal_manifest("DIGEST_WIRE_CASES", DIGEST_WIRE_CASES)
        self.check(
            (
                len(ARRAY_WIRE_CASES),
                len(SCALAR_WIRE_CASES),
                len(DIGEST_WIRE_CASES),
            )
            == (74, 208, 13),
            "oracle.complete_inventory_counts",
            "protected complete inventories drifted from exact 74/208/13",
        )
        self.check(
            ARRAY_WIRE_CASES == _top_level_fields(list),
            "oracle.array_derived",
            "ARRAY_WIRE_CASES is not exactly derived from all 23 fixtures",
        )
        self.check(
            SCALAR_WIRE_CASES == _top_level_fields(str),
            "oracle.scalar_derived",
            "SCALAR_WIRE_CASES is not exactly derived from all 23 fixtures",
        )
        self.check(
            len(ARRAY_WIRE_CASES) == len(set(ARRAY_WIRE_CASES)),
            "oracle.array_unique",
            "protected array case IDs are not unique",
        )
        self.check(
            len(SCALAR_WIRE_CASES) == len(set(SCALAR_WIRE_CASES)),
            "oracle.scalar_unique",
            "protected scalar case IDs are not unique",
        )
        self.check(
            len(DIGEST_WIRE_CASES) == len(set(DIGEST_WIRE_CASES)),
            "oracle.digest_unique",
            "protected digest case IDs are not unique",
        )

        for qualified in ARRAY_WIRE_CASES:
            interface, field = qualified.split(".", 1)
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            for label, invalid in (
                ("tuple", tuple(payload[field])),
                ("null", None),
                ("object", {}),
                ("string", "not-an-array"),
                ("number", 7),
                ("boolean", True),
                ("list-subclass", _WireListSubclass(payload[field])),
            ):
                candidate = copy.deepcopy(payload)
                candidate[field] = invalid
                self.reject(
                    lambda c=cls, p=candidate: c.from_dict(p),
                    "array_field.strict_type",
                    f"{qualified} accepted {label}",
                )
            self.check_omission(cls, payload, field, list, qualified)

        self._check_empty_string_array_items()

        removed_array_fields = {
            "UiContextPack@1.affected_test_ids",
            "UiContextPack@1.capsule_ids",
            "UiContextPack@1.invariant_failure_ids",
            "UiContextPack@1.state_machine_ids",
            "UiContextPack@1.style_token_paths",
            "UiSemanticCapsule@1.keyboard_focus_behavior",
            "UiSemanticCapsule@1.layout_responsive_behavior",
        }
        for qualified in NULL_ARRAY_REGRESSIONS:
            interface, field = qualified.split(".", 1)
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            if field in payload:
                candidate = copy.deepcopy(payload)
                candidate[field] = None
                self.reject(
                    lambda c=cls, p=candidate: c.from_dict(p),
                    "array_field.null_regression",
                    f"{qualified} accepted explicit null",
                )
            else:
                self.check(
                    qualified in removed_array_fields,
                    "array_field.protected_presence",
                    f"protected fixture unexpectedly omits {qualified}",
                )
                for label, invalid in (("null", None), ("array", [])):
                    candidate = copy.deepcopy(payload)
                    candidate[field] = invalid
                    self.reject(
                        lambda c=cls, p=candidate: c.from_dict(p),
                        "array_field.removed_legacy",
                        f"removed {qualified} accepted legacy {label} value",
                    )

        for qualified in NULL_SCALAR_REGRESSIONS:
            interface, field = qualified.split(".", 1)
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            if field not in payload:
                self.check(
                    False,
                    "scalar_field.missing",
                    f"sample {interface} omits scalar field {field}",
                )
                continue
            candidate = copy.deepcopy(payload)
            candidate[field] = None
            self.reject(
                lambda c=cls, p=candidate: c.from_dict(p),
                "scalar_field.null",
                f"{qualified} accepted explicit null",
            )
            self.check_omission(cls, payload, field, str, qualified)

        self._check_complete_scalar_fields()

    def _check_empty_string_array_items(self) -> None:
        cases = (
            ("AccessibilityReceipt@1", "violation_ids", "violation:oracle"),
            ("GuiImprovementReceipt@1", "rejection_reasons", "reason:oracle"),
            (
                "InteractionReceipt@1",
                "unresolved_observation_ids",
                "observation:oracle",
            ),
        )

        def populated(
            interface: str,
            field: str,
            item: Any,
        ) -> tuple[type[Any] | None, dict[str, Any] | None]:
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                return cls, payload
            payload[field] = [item]
            if interface == "AccessibilityReceipt@1":
                payload["violation_count"] = 1
            elif interface == "GuiImprovementReceipt@1":
                payload["decision"] = "reject"
                payload["verification_status"] = "invalid"
            return cls, payload

        for interface, field, valid_item in cases:
            qualified = f"{interface}.{field}"
            cls, valid = populated(interface, field, valid_item)
            if cls is None or valid is None:
                continue
            self.accept(
                lambda c=cls, p=valid: c.from_dict(p),
                "array_item.valid_string",
                f"{qualified} rejected a valid string item",
            )
            for label, invalid in (
                ("null", None),
                ("integer", 1),
                ("boolean", True),
                ("string-subclass", _WireStringSubclass(valid_item)),
                ("enum", _wire_enum(valid_item)),
            ):
                _, candidate = populated(interface, field, invalid)
                if candidate is None:
                    continue
                self.reject(
                    lambda c=cls, p=candidate: c.from_dict(p),
                    "array_item.strict_string",
                    f"{qualified} accepted {label} item",
                )

    def _check_complete_scalar_fields(self) -> None:
        for qualified in SCALAR_WIRE_CASES:
            interface, field = qualified.split(".", 1)
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            value = payload[field]
            for label, invalid in (
                ("null", None),
                ("array", []),
                ("object", {}),
                ("integer", 7),
                ("boolean", True),
                ("number", 1.5),
                ("bytes", b"wire-bytes"),
                ("string-subclass", _WireStringSubclass(value)),
                ("enum", _wire_enum(value)),
            ):
                candidate = copy.deepcopy(payload)
                candidate[field] = invalid
                self.reject(
                    lambda c=cls, p=candidate: c.from_dict(p),
                    "scalar_field.strict_type",
                    f"{qualified} accepted {label}",
                )

        for qualified in DIGEST_WIRE_CASES:
            interface, field = qualified.split(".", 1)
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            for label, invalid in (
                ("empty", ""),
                ("wrong-algorithm", "cidv1:" + "a" * 64),
                ("short", "sha256:abc"),
                ("uppercase", "sha256:" + "A" * 64),
            ):
                candidate = copy.deepcopy(payload)
                candidate[field] = invalid
                self.reject(
                    lambda c=cls, p=candidate: c.from_dict(p),
                    "digest_field.strict",
                    f"{qualified} accepted {label} digest",
                )

        for interface in REQUIRED_INTERFACES:
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            for field, value in payload.items():
                invalid_values: tuple[tuple[str, Any], ...] = ()
                if type(value) is bool:
                    invalid_values = (
                        ("integer", int(value)),
                        ("string", str(value).lower()),
                        ("null", None),
                    )
                elif type(value) is int:
                    invalid_values = (
                        ("boolean", True),
                        ("float", float(value)),
                        ("integer-subclass", _WireIntegerSubclass(value)),
                        ("unsafe-integer", 1 << 53),
                        ("null", None),
                    )
                elif type(value) is float:
                    invalid_values = (
                        ("boolean", True),
                        ("string", str(value)),
                        ("float-subclass", _WireFloatSubclass(value)),
                        ("nan", float("nan")),
                        ("positive-infinity", float("inf")),
                        ("negative-infinity", float("-inf")),
                        ("null", None),
                    )
                for label, invalid in invalid_values:
                    candidate = copy.deepcopy(payload)
                    candidate[field] = invalid
                    self.reject(
                        lambda c=cls, p=candidate: c.from_dict(p),
                        "numeric_field.strict_type",
                        f"{interface}.{field} accepted {label}",
                    )

        cls = self.model_class("UiComponentIdentity@1")
        payload = self.payload("UiComponentIdentity@1")
        if cls is not None and payload is not None:
            candidate = copy.deepcopy(payload)
            candidate["component_kind"] = _WireEnum.VALUE
            self.reject(
                lambda: cls.from_dict(candidate),
                "wire.enum",
                "UiComponentIdentity accepted a Python Enum on the wire",
            )

    def check_enum_fields(self) -> None:
        self.check(
            ENUM_SCALAR_WIRE_CASES == tuple(sorted(ENUM_SCALAR_WIRE_CASES))
            and len(ENUM_SCALAR_WIRE_CASES) == len(set(ENUM_SCALAR_WIRE_CASES)),
            "oracle.enum_scalar_inventory",
            "protected scalar enum inventory is not sorted and unique",
        )
        self.check(
            ENUM_ARRAY_WIRE_CASES == tuple(sorted(ENUM_ARRAY_WIRE_CASES))
            and len(ENUM_ARRAY_WIRE_CASES) == len(set(ENUM_ARRAY_WIRE_CASES)),
            "oracle.enum_array_inventory",
            "protected array enum inventory is not sorted and unique",
        )
        for qualified in ENUM_SCALAR_WIRE_CASES:
            interface, field = qualified.split(".", 1)
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            self.check(
                field in payload and type(payload[field]) is str,
                "enum.scalar_fixture",
                f"protected enum fixture missing {qualified}",
            )
            candidate = copy.deepcopy(payload)
            candidate[field] = "__vgo001_invalid_enum__"
            self.reject(
                lambda c=cls, p=candidate: c.from_dict(p),
                "enum.invalid_string",
                f"{qualified} accepted an invalid enum string",
            )
        for qualified in ENUM_ARRAY_WIRE_CASES:
            interface, field = qualified.split(".", 1)
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            self.check(
                field in payload and type(payload[field]) is list and bool(payload[field]),
                "enum.array_fixture",
                f"protected enum-array fixture missing {qualified}",
            )
            candidate = copy.deepcopy(payload)
            candidate[field][0] = "__vgo001_invalid_enum__"
            self.reject(
                lambda c=cls, p=candidate: c.from_dict(p),
                "enum.invalid_string",
                f"{qualified} accepted an invalid enum string",
            )
        for interface, path in EMBEDDED_ENUM_PATHS:
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            self.check(
                type(self._get(payload, path)) is str,
                "enum.embedded_fixture",
                f"protected embedded enum fixture missing {interface}:{self._path_text(path)}",
            )
            candidate = copy.deepcopy(payload)
            self._set(candidate, path, "__vgo001_invalid_enum__")
            self.reject(
                lambda c=cls, p=candidate: c.from_dict(p),
                "enum.embedded_invalid_string",
                f"{interface}:{self._path_text(path)} accepted invalid enum string",
            )
        for interface, path in EMBEDDED_REGISTERED_SCHEMA_PATHS:
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            candidate = copy.deepcopy(payload)
            self._set(candidate, path, "oracle-unregistered/v999")
            self.reject(
                lambda c=cls, p=candidate: c.from_dict(p),
                "schema.embedded_unregistered",
                f"{interface}:{self._path_text(path)} accepted unregistered schema",
            )
        context_cls = self.model_class("UiContextPack@1")
        context_payload = self.payload("UiContextPack@1")
        if context_cls is not None and context_payload is not None:
            for path in CONTEXT_NESTED_ENUM_PATHS:
                self.check(
                    type(self._get(context_payload, path)) is str,
                    "enum.nested_fixture",
                    f"protected nested enum fixture missing {self._path_text(path)}",
                )
                candidate = copy.deepcopy(context_payload)
                self._set(candidate, path, "__vgo001_invalid_enum__")
                self.reject(
                    lambda c=context_cls, p=candidate: c.from_dict(p),
                    "enum.nested_invalid_string",
                    f"UiContextPack.{self._path_text(path)} accepted invalid enum string",
                )
            for path in CONTEXT_REGISTERED_SCHEMA_PATHS:
                candidate = copy.deepcopy(context_payload)
                self._set(candidate, path, "oracle-unregistered/v999")
                self.reject(
                    lambda c=context_cls, p=candidate: c.from_dict(p),
                    "schema.context_unregistered",
                    f"UiContextPack.{self._path_text(path)} accepted unregistered schema",
                )

    def _check_exact_json(self, value: Any, path: str) -> None:
        value_type = type(value)
        if value is None or value_type in (bool, int, str):
            return
        if value_type is float:
            self.check(
                math.isfinite(value),
                "json.nonfinite",
                f"{path} emitted a non-finite number",
            )
            return
        if value_type is list:
            for index, item in enumerate(value):
                self._check_exact_json(item, f"{path}[{index}]")
            return
        if value_type is dict:
            for key, item in value.items():
                self.check(
                    type(key) is str,
                    "json.key_type",
                    f"{path} emitted a non-string or string-subclass key",
                )
                if type(key) is str:
                    self.check(
                        unicodedata.normalize("NFC", key) == key,
                        "json.key_nfc",
                        f"{path} emitted non-NFC key {key!r}",
                    )
                    self._check_exact_json(item, f"{path}.{key}")
            return
        self.check(
            False,
            "json.type",
            f"{path} emitted non-JSON type {value_type.__name__}",
        )

    def _check_defensive_copy(
        self, cls: type[Any], payload: dict[str, Any], interface: str
    ) -> None:
        caller = copy.deepcopy(payload)
        model = self.accept(
            lambda: cls.from_dict(caller),
            "roundtrip.decode",
            f"{interface} could not decode its own wire payload",
        )
        if model is None:
            return
        before = self._model_wire(
            model,
            "wire.defensive_snapshot",
            f"{interface} could not serialize before defensive-copy probes",
        )
        if before is None:
            return
        before = copy.deepcopy(before)

        def mutate(value: Any, *, top: bool = False) -> Any:
            if type(value) is list:
                for index, item in enumerate(list(value)):
                    value[index] = mutate(item)
                value.append("__caller_mutation__")
                return value
            elif type(value) is dict:
                for key, item in list(value.items()):
                    value[key] = mutate(item)
                value["__top_mutation__" if top else "__nested_mutation__"] = True
                return value
            elif type(value) is str:
                return value + "__scalar_mutation__"
            elif type(value) is bool:
                return not value
            elif type(value) is int:
                return value + 1
            elif type(value) is float:
                return math.nextafter(value, math.inf)
            elif value is None:
                return "__null_mutation__"
            return _WireDataclass()

        original_caller = copy.deepcopy(caller)
        mutate(caller, top=True)
        self.check(
            caller != original_caller,
            "wire.defensive_input_nonvacuous",
            f"{interface} caller-owned payload mutation was vacuous",
        )
        if interface == "UiContextPack@1":
            for field in ("raw_sources", "styles", "affected_tests"):
                self.check(
                    caller[field][0]["content"] != payload[field][0]["content"],
                    "wire.defensive_content_input",
                    f"caller mutation did not alter exact {field} content",
                )
        after_caller_mutation = self._model_wire(
            model,
            "wire.defensive_input_reread",
            f"{interface} could not serialize after caller mutation",
        )
        if after_caller_mutation is not None:
            self.check(
                after_caller_mutation == before,
                "wire.defensive_copy",
                f"{interface} retained caller-owned mutable data",
            )

        returned = self._model_wire(
            model,
            "wire.defensive_output_snapshot",
            f"{interface} could not provide a mutable output-copy probe",
        )
        if returned is None:
            return
        original_returned = copy.deepcopy(returned)
        mutate(returned, top=True)
        self.check(
            returned != original_returned,
            "wire.defensive_output_nonvacuous",
            f"{interface} returned-payload mutation was vacuous",
        )
        if interface == "UiContextPack@1":
            for field in ("raw_sources", "styles", "affected_tests"):
                self.check(
                    returned[field][0]["content"] != before[field][0]["content"],
                    "wire.defensive_content_output",
                    f"returned mutation did not alter exact {field} content",
                )
        after_output_mutation = self._model_wire(
            model,
            "wire.defensive_output_reread",
            f"{interface} could not serialize after returned-payload mutation",
        )
        if after_output_mutation is not None:
            self.check(
                after_output_mutation == before,
                "wire.defensive_output",
                f"{interface} exposed model-owned mutable data from to_dict()",
            )

    def check_canonical_profile(self) -> None:
        canonical = getattr(self.models, "canonical_model_bytes", None)
        if not self.check(
            callable(canonical),
            "canonical.missing",
            "canonical_model_bytes is missing",
        ):
            return
        for interface, payload in self.samples.items():
            canonical_payload = copy.deepcopy(payload)
            encoded = self.accept(
                lambda p=canonical_payload: canonical(p),
                "canonical.encode",
                f"canonical_model_bytes rejected {interface}",
            )
            if type(encoded) is bytes:
                self.check(
                    encoded
                    == json.dumps(
                        payload,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode(),
                    "canonical.exact",
                    f"canonical bytes differ for {interface}",
                )
            else:
                self.check(
                    False,
                    "canonical.output_type",
                    f"canonical_model_bytes returned {type(encoded).__name__}",
                )
        for label, invalid in (
            ("non-string-key", {1: "value"}),
            ("non-nfc-key", {"e\u0301": 1}),
            ("nfc-collision", {"é": 1, "e\u0301": 2}),
            ("mapping-proxy", MappingProxyType({"value": 1})),
            ("dict-subclass", _WireDictSubclass({"value": 1})),
            ("tuple", {"value": (1,)}),
            ("enum", {"value": _WireEnum.VALUE}),
            ("dataclass", {"value": _WireDataclass()}),
            ("nan", {"value": float("nan")}),
            ("infinity", {"value": float("inf")}),
        ):
            self.reject(
                lambda value=invalid: canonical(value),
                "canonical.strict_json",
                f"canonical_model_bytes accepted {label}",
            )
        cls = self.model_class("UiComponentIdentity@1")
        payload = self.payload("UiComponentIdentity@1")
        if cls is not None and payload is not None:
            model = self.accept(
                lambda: cls.from_dict(payload),
                "canonical.model_fixture",
                "could not build model-instance rejection fixture",
            )
            if model is not None:
                self.reject(
                    lambda: canonical({"value": model}),
                    "canonical.model_instance",
                    "canonical_model_bytes accepted a model instance",
                )

    @staticmethod
    def _walk(value: Any, path: tuple[Any, ...] = ()) -> Iterable[tuple[tuple[Any, ...], Any]]:
        yield path, value
        if type(value) is dict:
            for key, item in value.items():
                yield from Oracle._walk(item, (*path, key))
        elif type(value) is list:
            for index, item in enumerate(value):
                yield from Oracle._walk(item, (*path, index))

    @staticmethod
    def _get(value: Any, path: Sequence[Any]) -> Any:
        current = value
        for part in path:
            current = current[part]
        return current

    @staticmethod
    def _set(value: Any, path: Sequence[Any], replacement: Any) -> None:
        current = value
        for part in path[:-1]:
            current = current[part]
        current[path[-1]] = replacement

    @staticmethod
    def _path_text(path: Sequence[Any]) -> str:
        return ".".join(str(part).lower() for part in path if type(part) is str)

    def check_nested_records(self) -> None:
        all_schemas = dict(SCHEMA_BY_INTERFACE | NESTED_SCHEMA_BY_INTERFACE)
        for interface in REQUIRED_INTERFACES:
            cls = self.model_class(interface)
            payload = self.payload(interface)
            if cls is None or payload is None:
                continue
            for path, value in self._walk(payload):
                if not path:
                    continue
                location = f"{interface}:{self._path_text(path)}"
                if type(value) is list:
                    for label, invalid in (
                        ("tuple", tuple(value)),
                        ("list-subclass", _WireListSubclass(value)),
                        ("null", None),
                        ("mapping", {}),
                        ("string", "not-an-array"),
                        ("integer", 7),
                        ("boolean", True),
                    ):
                        candidate = copy.deepcopy(payload)
                        self._set(candidate, path, invalid)
                        self.reject(
                            lambda c=cls, p=candidate: c.from_dict(p),
                            "recursive.array_type",
                            f"{location} accepted nested {label}",
                        )
                    continue
                if type(value) is str:
                    for label, invalid in (
                        ("string-subclass", _WireStringSubclass(value)),
                        ("enum", _wire_enum(value)),
                        ("null", None),
                        ("array", []),
                        ("mapping", {}),
                        ("integer", 7),
                        ("boolean", True),
                    ):
                        candidate = copy.deepcopy(payload)
                        self._set(candidate, path, invalid)
                        self.reject(
                            lambda c=cls, p=candidate: c.from_dict(p),
                            "recursive.string_type",
                            f"{location} accepted nested {label}",
                        )
                    continue
                if type(value) is bool:
                    for label, invalid in (
                        ("integer", int(value)),
                        ("string", str(value).lower()),
                        ("null", None),
                        ("array", []),
                        ("mapping", {}),
                    ):
                        candidate = copy.deepcopy(payload)
                        self._set(candidate, path, invalid)
                        self.reject(
                            lambda c=cls, p=candidate: c.from_dict(p),
                            "recursive.bool_type",
                            f"{location} accepted nested {label} as boolean",
                        )
                    continue
                if type(value) is int:
                    for label, invalid in (
                        ("integer-subclass", _WireIntegerSubclass(value)),
                        ("boolean", True),
                        ("float", float(value)),
                        ("string", str(value)),
                        ("null", None),
                        ("unsafe-integer", 1 << 53),
                    ):
                        candidate = copy.deepcopy(payload)
                        self._set(candidate, path, invalid)
                        self.reject(
                            lambda c=cls, p=candidate: c.from_dict(p),
                            "recursive.integer_type",
                            f"{location} accepted nested {label}",
                        )
                    continue
                if type(value) is float:
                    for label, invalid in (
                        ("float-subclass", _WireFloatSubclass(value)),
                        ("boolean", True),
                        ("string", str(value)),
                        ("null", None),
                        ("nan", float("nan")),
                        ("infinity", float("inf")),
                    ):
                        candidate = copy.deepcopy(payload)
                        self._set(candidate, path, invalid)
                        self.reject(
                            lambda c=cls, p=candidate: c.from_dict(p),
                            "recursive.number_type",
                            f"{location} accepted nested {label}",
                        )
                    continue
                if type(value) is not dict:
                    continue
                mapping_invalids: list[tuple[str, Any]] = [
                    ("mapping-proxy", MappingProxyType(value)),
                    ("dict-subclass", _WireDictSubclass(value)),
                    ("dataclass", _WireDataclass()),
                    ("array", []),
                    ("tuple", tuple(value)),
                    ("enum", _WireEnum.VALUE),
                ]
                if path != ("source_span",):
                    mapping_invalids.append(("null", None))
                for label, invalid in mapping_invalids:
                    candidate = copy.deepcopy(payload)
                    self._set(candidate, path, invalid)
                    self.reject(
                        lambda c=cls, p=candidate: c.from_dict(p),
                        "recursive.mapping_type",
                        f"{location} accepted nested {label}",
                    )
                if "schema_version" not in value and "interface" not in value:
                    continue
                nested_interface = value.get("interface")
                expected_schema = all_schemas.get(nested_interface)
                self.check(
                    type(nested_interface) is str and nested_interface in all_schemas,
                    "nested.interface",
                    f"unregistered nested interface at {location}: {nested_interface!r}",
                )
                self.check(
                    type(value.get("schema_version")) is str
                    and value.get("schema_version") == expected_schema,
                    "nested.schema",
                    f"wrong nested schema_version at {location}",
                )
                for field in ("interface", "schema_version"):
                    candidate = copy.deepcopy(payload)
                    nested = self._get(candidate, path)
                    nested.pop(field, None)
                    self.reject(
                        lambda c=cls, p=candidate: c.from_dict(p),
                        "nested.identity_required",
                        f"{location} synthesized missing {field}",
                    )
                other_interface = next(
                    item
                    for item in (*REQUIRED_INTERFACES, *NESTED_SCHEMA_BY_INTERFACE)
                    if item != nested_interface
                )
                other_schema = next(
                    item
                    for item in (
                        *SCHEMA_BY_INTERFACE.values(),
                        *NESTED_SCHEMA_BY_INTERFACE.values(),
                    )
                    if item != expected_schema
                )
                for field, vectors in (
                    (
                        "interface",
                        (
                            ("arbitrary", "not an interface"),
                            ("registered-mismatch", other_interface),
                            ("unregistered", "OracleUnknown@999"),
                        ),
                    ),
                    (
                        "schema_version",
                        (
                            ("arbitrary", "not a schema"),
                            ("registered-mismatch", other_schema),
                            ("unregistered", "oracle-unknown/v999"),
                        ),
                    ),
                ):
                    for label, invalid in vectors:
                        candidate = copy.deepcopy(payload)
                        self._get(candidate, path)[field] = invalid
                        self.reject(
                            lambda c=cls, p=candidate: c.from_dict(p),
                            "nested.identity_wrong_string",
                            f"{location} accepted {label} {field}={invalid!r}",
                        )
                unknown = copy.deepcopy(payload)
                self._get(unknown, path)["__vgo001_nested_unknown__"] = True
                self.reject(
                    lambda c=cls, p=unknown: c.from_dict(p),
                    "nested.closed",
                    f"{location} accepted an unknown field",
                )
                nested_cls = getattr(
                    self.models,
                    str(nested_interface).split("@", 1)[0],
                    None,
                )
                if isinstance(nested_cls, type):
                    nested_payload = copy.deepcopy(value)
                    nested_model = self.accept(
                        lambda c=nested_cls, p=nested_payload: c.from_dict(p),
                        "nested.decode",
                        f"nested fixture rejected at {location}",
                    )
                    if nested_model is not None:
                        self._check_identity_vectors(
                            nested_cls,
                            value,
                            str(nested_interface),
                            str(expected_schema),
                            location,
                        )
                        candidate = copy.deepcopy(payload)
                        self._set(candidate, path, nested_model)
                        self.reject(
                            lambda c=cls, p=candidate: c.from_dict(p),
                            "nested.model_instance",
                            f"{location} accepted a nested model instance",
                        )
        edge_cls = self.model_class("UiDependencyEdge@1")
        edge_payload = self.payload("UiDependencyEdge@1")
        if edge_cls is not None and edge_payload is not None:
            edge_payload["source_span"] = None
            edge_model = self.accept(
                lambda: edge_cls.from_dict(edge_payload),
                "nested.nullable_source_span",
                "explicitly nullable source_span rejected null",
            )
            if edge_model is not None:
                edge_wire = self._model_wire(
                    edge_model,
                    "nested.nullable_source_span_encode",
                    "nullable source_span result could not serialize",
                )
                if edge_wire is not None:
                    self.check(
                        edge_wire.get("source_span") is None,
                        "nested.nullable_source_span_roundtrip",
                        "nullable source_span did not roundtrip as null",
                    )

    def check_capsule_contract(self) -> None:
        interface = "UiSemanticCapsule@1"
        cls = self.model_class(interface)
        payload = self.payload(interface)
        if cls is None or payload is None:
            return
        expected_types = {
            "action_side_effects": list,
            "layout_role": str,
            "responsive_behavior": list,
            "keyboard_interactions": list,
            "focus_behavior": list,
        }
        for field, expected_type in expected_types.items():
            self.check(
                type(payload.get(field)) is expected_type and bool(payload[field]),
                "capsule.distinct_field",
                f"UiSemanticCapsule lacks nonempty distinct {field}",
            )
        for field in LEGACY_CAPSULE_FIELDS:
            candidate = copy.deepcopy(payload)
            candidate[field] = ["legacy combined prose"]
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "capsule.legacy_combined",
                f"UiSemanticCapsule accepted removed combined field {field}",
            )

    def check_context_pack(self) -> None:
        interface = "UiContextPack@1"
        cls = self.model_class(interface)
        payload = self.payload(interface)
        if cls is None or payload is None:
            return
        required_fields = (
            *CONTEXT_PAYLOAD_FIELDS,
            "artifact_digests",
            "acceptance_criteria",
            "excluded_context_explanation",
            "escalation_conditions",
            *TOKEN_FIELDS,
        )
        for field in required_fields:
            self.check(
                field in payload,
                "context.required_field",
                f"UiContextPack lacks {field}",
            )
        structured_lists = {
            "raw_sources": "UiContextSource@1",
            "styles": "UiContextStyle@1",
            "affected_tests": "UiContextTest@1",
            "parent_capsules": "UiSemanticCapsule@1",
            "child_capsules": "UiSemanticCapsule@1",
            "formal_invariant_failures": "UiContextFormalFailure@1",
            "accessibility_violations": "UiContextAccessibilityViolation@1",
            "visual_references": "UiContextVisualReference@1",
            "screenshot_descriptions": "UiContextScreenshotDescription@1",
            "affected_routes": "UiContextRoute@1",
            "action_bindings": "UiActionBinding@1",
        }
        for field, nested_interface in structured_lists.items():
            value = payload.get(field)
            self.check(
                type(value) is list
                and bool(value)
                and all(
                    type(item) is dict
                    and item.get("interface") == nested_interface
                    and item.get("schema_version")
                    == (SCHEMA_BY_INTERFACE | NESTED_SCHEMA_BY_INTERFACE)[nested_interface]
                    for item in value
                ),
                "context.structured_list",
                f"UiContextPack.{field} is not a nonempty full {nested_interface} list",
            )
        for field, nested_interface in (
            ("state_machine", "UiContextStateMachine@1"),
            ("metric_baseline", "UiContextMetricBaseline@1"),
        ):
            value = payload.get(field)
            self.check(
                type(value) is dict
                and value.get("interface") == nested_interface
                and value.get("schema_version") == NESTED_SCHEMA_BY_INTERFACE[nested_interface],
                "context.structured_record",
                f"UiContextPack.{field} is not a full {nested_interface}",
            )

        exact_content = {
            "raw_sources": "  const label = 'Goal';\n\treturn label;\n\n",
            "styles": "\t.primary {\r\n  color: var(--primary);\r\n}\r\n",
            "affected_tests": (
                " describe('goal form', () => {\n\n\tit('labels input', verify);\n}); "
            ),
        }
        for field, content in exact_content.items():
            self.check(
                payload.get(field, [{}])[0].get("content") == content,
                "context.protected_content",
                f"protected {field} fixture lost exact content code points",
            )
            candidate = copy.deepcopy(payload)
            candidate[field][0]["content"] = content
            model = self.accept(
                lambda p=candidate: cls.from_dict(p),
                "context.content_decode",
                f"UiContextPack rejected exact {field} content",
            )
            if model is not None:
                wire = self._model_wire(
                    model,
                    "context.content_encode",
                    f"UiContextPack exact {field} result could not serialize",
                )
                if wire is not None:
                    self.check(
                        wire[field][0]["content"] == content,
                        "context.content_preservation",
                        f"UiContextPack changed exact {field} content",
                    )

        for field in ("parent_capsules", "child_capsules"):
            candidate = copy.deepcopy(payload)
            candidate[field] = [candidate[field][0]["capsule_id"]]
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "context.capsule_ids_only",
                f"UiContextPack accepted ID-only {field}",
            )
        for field in (*LEGACY_CONTEXT_FIELDS,):
            candidate = copy.deepcopy(payload)
            candidate[field] = [] if field.endswith(("ids", "paths")) else 1
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "context.legacy_field",
                f"UiContextPack accepted removed field {field}",
            )

        self._check_context_recursive_json(cls, payload, structured_lists)
        self._check_context_accounting(cls, payload)

    def _check_context_recursive_json(
        self,
        cls: type[Any],
        payload: dict[str, Any],
        structured_lists: Mapping[str, str],
    ) -> None:
        for field, nested_interface in structured_lists.items():
            value = payload[field]
            for label, invalid in (
                ("tuple", tuple(value)),
                ("list-subclass", _WireListSubclass(value)),
                ("mapping", {}),
                ("dataclass", _WireDataclass()),
                ("enum", _WireEnum.VALUE),
            ):
                candidate = copy.deepcopy(payload)
                candidate[field] = invalid
                self.reject(
                    lambda p=candidate: cls.from_dict(p),
                    "context.recursive_list",
                    f"UiContextPack.{field} accepted {label}",
                )
            nested_cls = getattr(self.models, nested_interface.split("@", 1)[0], None)
            if isinstance(nested_cls, type):
                nested_payload = copy.deepcopy(value[0])
                nested_model = self.accept(
                    lambda c=nested_cls, p=nested_payload: c.from_dict(p),
                    "context.nested_fixture",
                    f"could not construct nested {nested_interface}",
                )
                if nested_model is not None:
                    candidate = copy.deepcopy(payload)
                    candidate[field][0] = nested_model
                    self.reject(
                        lambda p=candidate: cls.from_dict(p),
                        "context.nested_model",
                        f"UiContextPack.{field} accepted a model instance",
                    )
        for field in ("state_machine", "metric_baseline"):
            value = payload[field]
            for label, invalid in (
                ("mapping-proxy", MappingProxyType(value)),
                ("dict-subclass", _WireDictSubclass(value)),
                ("array", []),
                ("tuple", tuple(value)),
                ("dataclass", _WireDataclass()),
                ("enum", _WireEnum.VALUE),
            ):
                candidate = copy.deepcopy(payload)
                candidate[field] = invalid
                self.reject(
                    lambda p=candidate: cls.from_dict(p),
                    "context.recursive_mapping",
                    f"UiContextPack.{field} accepted {label}",
                )

        metrics_path = ("metric_baseline", "metrics")
        for label, metrics in (
            ("non-string-key", {1: 1}),
            ("non-nfc-key", {"e\u0301": 1}),
            ("nfc-collision", {"é": 1, "e\u0301": 2}),
            ("mapping-proxy", MappingProxyType({"value": 1})),
            ("dict-subclass", _WireDictSubclass({"value": 1})),
            ("dataclass", {"value": _WireDataclass()}),
            ("enum", {"value": _WireEnum.VALUE}),
            ("model", {"value": self}),
            ("tuple", {"value": (1,)}),
            ("nan", {"value": float("nan")}),
            ("infinity", {"value": float("inf")}),
        ):
            candidate = copy.deepcopy(payload)
            self._set(candidate, metrics_path, metrics)
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "context.recursive_json",
                f"UiContextPack metric JSON accepted {label}",
            )

    def _check_context_accounting(self, cls: type[Any], payload: dict[str, Any]) -> None:
        def accounting(
            raw: int,
            capsules: int,
            screenshots: int,
            other: int,
            replaced: int,
        ) -> tuple[dict[str, Any], float]:
            candidate = copy.deepcopy(payload)
            total = raw + capsules + screenshots + other
            ordinary = raw + replaced + screenshots + other
            ratio = (ordinary - total) / ordinary
            candidate.update(
                {
                    "raw_source_tokens": raw,
                    "capsule_tokens": capsules,
                    "screenshot_analysis_tokens": screenshots,
                    "other_context_tokens": other,
                    "source_tokens_replaced_by_capsules": replaced,
                    "ordinary_raw_dependency_tokens": ordinary,
                    "total_estimated_prompt_tokens": total,
                    "token_budget": max(1, total + 10),
                }
            )
            candidate.pop("compression_ratio", None)
            return candidate, ratio

        positive, positive_ratio = accounting(20, 7, 3, 5, 30)
        model = self.accept(
            lambda: cls.from_dict(positive),
            "context.accounting_positive",
            "UiContextPack rejected exact positive accounting",
        )
        if model is not None:
            wire = self._model_wire(
                model,
                "context.accounting_positive_encode",
                "positive accounting result could not serialize",
            )
            if wire is not None:
                self.check(
                    wire.get("total_estimated_prompt_tokens") == 35
                    and wire.get("ordinary_raw_dependency_tokens") == 58
                    and wire.get("compression_ratio") == positive_ratio,
                    "context.accounting_equation",
                    "UiContextPack did not derive the exact token equations",
                )

        negative, negative_ratio = accounting(50, 20, 10, 5, 0)
        model = self.accept(
            lambda: cls.from_dict(negative),
            "context.negative_compression",
            "UiContextPack rejected truthful negative compression",
        )
        if model is not None:
            wire = self._model_wire(
                model,
                "context.negative_compression_encode",
                "negative compression result could not serialize",
            )
            if wire is not None:
                self.check(
                    wire.get("compression_ratio") == negative_ratio < 0,
                    "context.negative_compression_value",
                    "UiContextPack did not preserve derived negative compression",
                )
        supplied = copy.deepcopy(negative)
        supplied["compression_ratio"] = negative_ratio
        self.accept(
            lambda: cls.from_dict(supplied),
            "context.supplied_compression",
            "UiContextPack rejected an exact supplied compression ratio",
        )
        for label, value in (
            ("mismatch", negative_ratio + 0.01),
            ("one-ulp-mismatch", math.nextafter(negative_ratio, math.inf)),
            ("string", str(negative_ratio)),
            ("nan", float("nan")),
            ("infinity", float("inf")),
        ):
            candidate = copy.deepcopy(negative)
            candidate["compression_ratio"] = value
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "context.compression_rejection",
                f"UiContextPack accepted {label} compression_ratio",
            )
        primitive_values = {
            "raw_source_tokens": 10,
            "capsule_tokens": 10,
            "screenshot_analysis_tokens": 10,
            "other_context_tokens": 10,
            "source_tokens_replaced_by_capsules": 10,
        }
        for field in primitive_values:
            values = dict(primitive_values)
            values[field] = -1
            candidate, ratio = accounting(
                values["raw_source_tokens"],
                values["capsule_tokens"],
                values["screenshot_analysis_tokens"],
                values["other_context_tokens"],
                values["source_tokens_replaced_by_capsules"],
            )
            candidate["token_budget"] = 100
            candidate["compression_ratio"] = ratio
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "context.token_negative",
                f"UiContextPack accepted equation-consistent negative {field}",
            )
        zero_total, zero_total_ratio = accounting(0, 0, 0, 0, 1)
        zero_total["compression_ratio"] = zero_total_ratio
        for value in (0, -1):
            candidate = copy.deepcopy(zero_total)
            candidate["token_budget"] = value
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "context.token_budget",
                f"UiContextPack accepted token_budget={value}",
            )
        for field, value in (
            ("total_estimated_prompt_tokens", 86),
            ("ordinary_raw_dependency_tokens", 66),
            ("token_budget", 84),
            ("ordinary_raw_dependency_tokens", 0),
            ("ordinary_raw_dependency_tokens", -1),
            ("total_estimated_prompt_tokens", -1),
        ):
            candidate = copy.deepcopy(negative)
            candidate[field] = value
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "context.accounting_rejection",
                f"UiContextPack accepted invalid accounting field {field}={value}",
            )

    def check_receipts(self) -> None:
        self._check_improvement_receipt()
        self._check_constraint_receipt()
        self._check_visual_receipt()
        self._check_accessibility_receipt()

    def _check_accessibility_receipt(self) -> None:
        interface = "AccessibilityReceipt@1"
        cls = self.model_class(interface)
        payload = self.payload(interface)
        if cls is None or payload is None:
            return
        mismatch = copy.deepcopy(payload)
        mismatch["violation_count"] = len(mismatch["violation_ids"]) + 1
        self.reject(
            lambda: cls.from_dict(mismatch),
            "receipt.accessibility_count",
            "accessibility violation_count disagreed with violation_ids",
        )
        negative = copy.deepcopy(payload)
        negative["automated_pass_count"] = -1
        self.reject(
            lambda: cls.from_dict(negative),
            "receipt.accessibility_negative",
            "accessibility receipt accepted a negative automated pass count",
        )

    def _check_improvement_receipt(self) -> None:
        interface = "GuiImprovementReceipt@1"
        cls = self.model_class(interface)
        payload = self.payload(interface)
        if cls is None or payload is None:
            return
        required_scalars = ("invalidation_plan_id", "context_pack_id", "patch_digest")
        receipt_lists = (
            "visual_receipt_ids",
            "accessibility_receipt_ids",
            "interaction_receipt_ids",
            "constraint_receipt_ids",
        )
        for field in (*required_scalars, *receipt_lists, "verification_status"):
            self.check(
                field in payload,
                "receipt.improvement_field",
                f"GuiImprovementReceipt lacks {field}",
            )
        if not all(field in payload for field in (*required_scalars, *receipt_lists)):
            return
        accepted = copy.deepcopy(payload)
        accepted.update(
            {
                "decision": "accept",
                "verification_status": "verified",
                "invalidation_plan_id": "invalidation:oracle",
                "context_pack_id": "context:oracle",
                "patch_digest": "sha256:" + "a" * 64,
                "rejection_reasons": [],
                "visual_receipt_ids": ["visual:oracle"],
                "accessibility_receipt_ids": ["accessibility:oracle"],
                "interaction_receipt_ids": ["interaction:oracle"],
                "constraint_receipt_ids": ["constraint:oracle"],
            }
        )
        self.accept(
            lambda: cls.from_dict(accepted),
            "receipt.accept_valid",
            "valid automatically accepted receipt was rejected",
        )
        for field in required_scalars:
            candidate = copy.deepcopy(accepted)
            candidate[field] = ""
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "receipt.accept_identity",
                f"automatic acceptance allowed empty {field}",
            )
        for field in receipt_lists:
            candidate = copy.deepcopy(accepted)
            candidate[field] = []
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "receipt.accept_evidence",
                f"automatic acceptance allowed empty {field}",
            )
        for status in (
            "structurally_valid",
            "unverified",
            "stale",
            "invalid",
            "simulated",
        ):
            candidate = copy.deepcopy(accepted)
            candidate["verification_status"] = status
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "receipt.accept_status",
                f"automatic acceptance allowed {status} evidence",
            )
        integrity = copy.deepcopy(accepted)
        integrity["verification_status"] = "integrity_valid"
        self.accept(
            lambda: cls.from_dict(integrity),
            "receipt.integrity_valid",
            "integrity_valid automatic acceptance was rejected",
        )
        reasons = copy.deepcopy(accepted)
        reasons["rejection_reasons"] = ["contradiction"]
        self.reject(
            lambda: cls.from_dict(reasons),
            "receipt.accept_reasons",
            "accepted receipt carried rejection reasons",
        )
        rejected = copy.deepcopy(accepted)
        rejected["decision"] = "reject"
        rejected["verification_status"] = "invalid"
        rejected["rejection_reasons"] = ["target metric did not improve"]
        rejected_model = self.accept(
            lambda: cls.from_dict(rejected),
            "receipt.reject_valid",
            "valid rejected receipt with a nonempty reason was rejected",
        )
        if rejected_model is not None:
            rejected_wire = self._model_wire(
                rejected_model,
                "receipt.reject_encode",
                "valid rejected receipt could not serialize",
            )
            if rejected_wire is not None:
                self.check(
                    rejected_wire.get("rejection_reasons") == rejected["rejection_reasons"],
                    "receipt.reject_reason_preserved",
                    "rejected receipt did not preserve its exact reasons",
                )
        missing_reasons = copy.deepcopy(rejected)
        missing_reasons["rejection_reasons"] = []
        self.reject(
            lambda: cls.from_dict(missing_reasons),
            "receipt.reject_reasons",
            "rejected receipt omitted rejection reasons",
        )

    def _check_constraint_receipt(self) -> None:
        interface = "UiConstraintReceipt@1"
        cls = self.model_class(interface)
        payload = self.payload(interface)
        if cls is None or payload is None:
            return
        required = (
            "check_ids",
            "statuses",
            "violated_check_ids",
            "unsupported_check_ids",
        )
        if not all(
            self.check(
                field in payload,
                "receipt.constraint_field",
                f"UiConstraintReceipt lacks {field}",
            )
            for field in required
        ):
            return
        mismatch = copy.deepcopy(payload)
        mismatch["statuses"] = []
        self.reject(
            lambda: cls.from_dict(mismatch),
            "receipt.constraint_length",
            "constraint status/check lengths can disagree",
        )
        unknown = copy.deepcopy(payload)
        unknown["statuses"] = ["unknown"] * len(unknown["check_ids"])
        self.reject(
            lambda: cls.from_dict(unknown),
            "receipt.constraint_status",
            "constraint receipt accepted an unknown status",
        )
        expected_violated = [
            check_id
            for check_id, status in zip(payload["check_ids"], payload["statuses"], strict=True)
            if status == "violated"
        ]
        expected_unsupported = [
            check_id
            for check_id, status in zip(payload["check_ids"], payload["statuses"], strict=True)
            if status == "unsupported"
        ]
        self.check(
            payload["violated_check_ids"] == expected_violated
            and payload["unsupported_check_ids"] == expected_unsupported,
            "receipt.constraint_fixture",
            "protected constraint fixture does not exactly agree with statuses",
        )
        for field, invalid in (
            ("violated_check_ids", []),
            ("violated_check_ids", [payload["check_ids"][0]]),
            ("unsupported_check_ids", []),
            ("unsupported_check_ids", [payload["check_ids"][0]]),
        ):
            candidate = copy.deepcopy(payload)
            candidate[field] = invalid
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "receipt.constraint_exact_sets",
                f"constraint receipt accepted contradictory {field}={invalid}",
            )
        if payload["check_ids"]:
            check_id = payload["check_ids"][0]
            contradiction = copy.deepcopy(payload)
            contradiction["statuses"] = ["satisfied" for _ in contradiction["check_ids"]]
            contradiction["violated_check_ids"] = [check_id]
            contradiction["unsupported_check_ids"] = [check_id]
            self.reject(
                lambda: cls.from_dict(contradiction),
                "receipt.constraint_contradiction",
                "a constraint was simultaneously satisfied, violated, and unsupported",
            )

    def _check_visual_receipt(self) -> None:
        interface = "VisualRegressionReceipt@1"
        cls = self.model_class(interface)
        payload = self.payload(interface)
        if cls is None or payload is None:
            return
        for field in (
            "browser",
            "browser_version",
            "expected_change_regions",
            "forbidden_change_regions",
            "requires_human_review",
            "decision",
            *VISUAL_STRUCTURAL_FIELDS,
        ):
            self.check(
                field in payload,
                "receipt.visual_field",
                f"VisualRegressionReceipt lacks {field}",
            )
        expected = payload.get("expected_change_regions")
        forbidden = payload.get("forbidden_change_regions")
        structured = (
            type(expected) is list
            and bool(expected)
            and all(
                type(item) is dict
                and item.get("interface") == "VisualChangeRegion@1"
                and item.get("schema_version") == NESTED_SCHEMA_BY_INTERFACE["VisualChangeRegion@1"]
                for item in expected
            )
            and type(forbidden) is list
            and bool(forbidden)
            and all(
                type(item) is dict
                and item.get("interface") == "VisualChangeRegion@1"
                and item.get("schema_version") == NESTED_SCHEMA_BY_INTERFACE["VisualChangeRegion@1"]
                for item in forbidden
            )
        )
        self.check(
            structured,
            "receipt.visual_regions",
            "visual regions must be nonempty closed structured records, not IDs",
        )
        base = copy.deepcopy(payload)
        base["browser"] = "chromium"
        base["browser_version"] = "1.0"
        base["decision"] = "pass"
        base["requires_human_review"] = False
        self.accept(
            lambda: cls.from_dict(base),
            "receipt.visual_valid",
            "valid visual receipt was rejected",
        )
        for field in ("browser", "browser_version"):
            candidate = copy.deepcopy(base)
            candidate[field] = ""
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "receipt.visual_browser",
                f"visual receipt accepted empty {field}",
            )
        candidate = copy.deepcopy(base)
        candidate["requires_human_review"] = True
        self.reject(
            lambda: cls.from_dict(candidate),
            "receipt.visual_pass_review",
            "PASS visual receipt required human review",
        )
        candidate = copy.deepcopy(base)
        candidate["decision"] = "review"
        candidate["requires_human_review"] = False
        self.reject(
            lambda: cls.from_dict(candidate),
            "receipt.visual_review_flag",
            "REVIEW visual receipt omitted human review",
        )
        review = copy.deepcopy(base)
        review["decision"] = "review"
        review["requires_human_review"] = True
        review["pixel_diff_percent"] = review["manual_review_threshold_percent"]
        self.accept(
            lambda: cls.from_dict(review),
            "receipt.visual_review_valid",
            "valid REVIEW visual receipt with human review was rejected",
        )
        if not structured:
            return
        region = expected[0]
        required_region = (
            "interface",
            "schema_version",
            "region_id",
            "x",
            "y",
            "width",
            "height",
            "evidence_reason",
        )
        for field in required_region:
            self.check(
                field in region,
                "region.field",
                f"visual region lacks {field}",
            )
        self.check(
            type(region.get("evidence_reason")) is str and bool(region["evidence_reason"]),
            "region.reason",
            "visual region lacks a nonempty evidence reason",
        )
        if not all(field in region for field in required_region):
            return
        exact = copy.deepcopy(base)
        exact_region = exact["expected_change_regions"][0]
        exact_region.update({"x": 0.5, "y": 0.5, "width": 0.5, "height": 0.5})
        self.accept(
            lambda: cls.from_dict(exact),
            "region.exact_boundary",
            "exact normalized region boundary was rejected",
        )
        overflow = copy.deepcopy(exact)
        overflow["expected_change_regions"][0]["width"] = math.nextafter(
            math.nextafter(0.5, math.inf), math.inf
        )
        self.reject(
            lambda: cls.from_dict(overflow),
            "region.no_epsilon",
            "visual region accepted x + width > 1 under an epsilon",
        )
        vertical_overflow = copy.deepcopy(exact)
        vertical_overflow["expected_change_regions"][0]["height"] = math.nextafter(
            math.nextafter(0.5, math.inf), math.inf
        )
        self.reject(
            lambda: cls.from_dict(vertical_overflow),
            "region.no_epsilon_vertical",
            "visual region accepted y + height > 1 under an epsilon",
        )
        nonfinite = copy.deepcopy(exact)
        nonfinite["expected_change_regions"][0]["x"] = float("nan")
        self.reject(
            lambda: cls.from_dict(nonfinite),
            "region.nonfinite",
            "visual region accepted a non-finite coordinate",
        )
        overlap = copy.deepcopy(base)
        overlap["forbidden_change_regions"] = copy.deepcopy(overlap["expected_change_regions"])
        self.reject(
            lambda: cls.from_dict(overlap),
            "region.unique_across_sets",
            "expected and forbidden region IDs overlap",
        )
        geometric_overlap = copy.deepcopy(base)
        expected_region = geometric_overlap["expected_change_regions"][0]
        forbidden_region = geometric_overlap["forbidden_change_regions"][0]
        forbidden_region.update(
            {
                "region_id": "region:distinct-geometric-overlap",
                "x": expected_region["x"],
                "y": expected_region["y"],
                "width": expected_region["width"],
                "height": expected_region["height"],
            }
        )
        self.reject(
            lambda: cls.from_dict(geometric_overlap),
            "region.geometric_disjointness",
            "distinct expected and forbidden regions geometrically overlap",
        )
        unknown = copy.deepcopy(base)
        unknown["expected_change_regions"][0]["unknown"] = True
        self.reject(
            lambda: cls.from_dict(unknown),
            "region.closed",
            "visual region accepted an unknown field",
        )
        for field, invalid in (
            ("x", -0.01),
            ("y", -0.01),
            ("width", 0.0),
            ("height", 0.0),
            ("x", float("inf")),
            ("height", float("nan")),
        ):
            candidate = copy.deepcopy(base)
            candidate["expected_change_regions"][0][field] = invalid
            self.reject(
                lambda p=candidate: cls.from_dict(p),
                "region.bounds",
                f"visual region accepted {field}={invalid}",
            )
        duplicate = copy.deepcopy(base)
        duplicate["expected_change_regions"].append(
            copy.deepcopy(duplicate["expected_change_regions"][0])
        )
        self.reject(
            lambda: cls.from_dict(duplicate),
            "region.unique_ids",
            "visual receipt accepted duplicate expected region IDs",
        )
        for field in (
            "unexpected_layout_shift_count",
            "missing_control_count",
            "extra_control_count",
        ):
            for label, invalid in (("negative", -1), ("float", 1.0)):
                candidate = copy.deepcopy(base)
                candidate[field] = invalid
                self.reject(
                    lambda p=candidate: cls.from_dict(p),
                    "receipt.visual_structural_count",
                    f"visual receipt accepted {label} {field}",
                )
        for field in ("screenshot_width", "screenshot_height"):
            for label, invalid in (("zero", 0), ("negative", -1), ("float", 1.0)):
                candidate = copy.deepcopy(base)
                candidate[field] = invalid
                self.reject(
                    lambda p=candidate: cls.from_dict(p),
                    "receipt.visual_dimensions",
                    f"visual receipt accepted {label} {field}",
                )
        for field in (
            "pixel_diff_percent",
            "structural_diff_percent",
            "max_unexplained_diff_percent",
            "manual_review_threshold_percent",
        ):
            for label, invalid in (
                ("negative", -0.01),
                ("over-100", 100.01),
                ("nan", float("nan")),
                ("infinity", float("inf")),
            ):
                candidate = copy.deepcopy(base)
                candidate[field] = invalid
                self.reject(
                    lambda p=candidate: cls.from_dict(p),
                    "receipt.visual_threshold",
                    f"visual receipt accepted {label} {field}",
                )
        unexplained = copy.deepcopy(base)
        unexplained["pixel_diff_percent"] = 2.0
        unexplained["max_unexplained_diff_percent"] = 1.0
        unexplained["manual_review_threshold_percent"] = 3.0
        self.reject(
            lambda: cls.from_dict(unexplained),
            "receipt.visual_unexplained_pass",
            "PASS visual receipt exceeded maximum unexplained difference",
        )
        threshold = copy.deepcopy(base)
        threshold["pixel_diff_percent"] = threshold["manual_review_threshold_percent"]
        threshold["requires_human_review"] = False
        self.reject(
            lambda: cls.from_dict(threshold),
            "receipt.visual_manual_threshold",
            "visual receipt reached review threshold without human review",
        )

    def run(self) -> dict[str, Any]:
        try:
            loaded = self.load()
            if loaded:
                self.check_declared_artifacts()
                self.check_inventory()
                self.check_manifests_and_wire_fields()
                self.check_enum_fields()
                self.check_canonical_profile()
                self.check_nested_records()
                self.check_capsule_contract()
                self.check_context_pack()
                self.check_receipts()
                self.check(
                    not _SIDE_EFFECT_ATTEMPTS,
                    "side_effect.attempt",
                    f"blocked side-effect attempts: {_SIDE_EFFECT_ATTEMPTS[:3]}",
                )
                self.check(
                    not _FORBIDDEN_IMPORT_ATTEMPTS,
                    "import.forbidden_runtime",
                    f"blocked excluded imports: {_FORBIDDEN_IMPORT_ATTEMPTS[:3]}",
                )
                self.check(
                    not _CANDIDATE_TEST_EXEC_ATTEMPTS,
                    "import.candidate_test_exec",
                    f"blocked candidate test execution: {_CANDIDATE_TEST_EXEC_ATTEMPTS[:3]}",
                )
                self.check(
                    self.output_sink.byte_count == 0,
                    "candidate.output",
                    f"candidate emitted {self.output_sink.byte_count} suppressed bytes",
                )
        except _OracleLimitError as exc:
            if len(self.errors) < MAX_ERRORS:
                self.errors.append({"code": "oracle.limit", "detail": str(exc)[:MAX_DETAIL_CHARS]})
        raw_errors = tuple(self.errors)
        grouped: dict[str, list[str]] = {}
        for error in raw_errors:
            grouped.setdefault(error["code"], []).append(error["detail"])
        concise_errors = [
            {
                "code": code,
                "count": len(details),
                "examples": details[:3],
            }
            for code, details in sorted(grouped.items())
        ]
        return {
            "schema": ORACLE_SCHEMA,
            "valid": not raw_errors,
            "errors": concise_errors,
            "summary": {
                "check_count": self.check_count,
                "error_count": len(raw_errors),
                "error_group_count": len(concise_errors),
                "required_model_count": len(REQUIRED_INTERFACES),
                "sealed_null_array_count": len(NULL_ARRAY_REGRESSIONS),
                "sealed_null_scalar_count": len(NULL_SCALAR_REGRESSIONS),
                "complete_array_field_count": len(ARRAY_WIRE_CASES),
                "complete_scalar_field_count": len(SCALAR_WIRE_CASES),
                "complete_digest_field_count": len(DIGEST_WIRE_CASES),
                "nested_interface_count": len(NESTED_SCHEMA_BY_INTERFACE),
                "synthetic_package_load": self.isolated_parent_packages,
                "candidate_test_executed": bool(_CANDIDATE_TEST_EXEC_ATTEMPTS),
                "candidate_test_exec_attempt_count": len(_CANDIDATE_TEST_EXEC_ATTEMPTS),
                "forbidden_import_attempt_count": len(_FORBIDDEN_IMPORT_ATTEMPTS),
                "router_deps_loaded": any(
                    "router_deps" in name.lower() for name in self.imported_candidate_modules
                ),
                "side_effect_guard_installed": _AUDIT_HOOK_INSTALLED,
                "side_effect_attempt_count": len(_SIDE_EFFECT_ATTEMPTS),
                "candidate_output_bytes": self.output_sink.byte_count,
                "enum_scalar_field_count": len(ENUM_SCALAR_WIRE_CASES),
                "enum_array_field_count": len(ENUM_ARRAY_WIRE_CASES),
                "embedded_enum_path_count": len(EMBEDDED_ENUM_PATHS)
                + len(CONTEXT_NESTED_ENUM_PATHS),
            },
        }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only independent VGO-001 acceptance oracle")
    parser.add_argument(
        "--check-all",
        action="store_true",
        help="run every sealed VGO-001 contract check",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--_oracle-worker", action="store_true", help=argparse.SUPPRESS)
    return parser


def _bounded_json(payload: dict[str, Any]) -> str:
    encoded = _JSON_DUMPS(payload, separators=(",", ":"), sort_keys=True)
    if len(encoded.encode()) <= MAX_OUTPUT_BYTES:
        return encoded
    bounded = {
        "schema": ORACLE_SCHEMA,
        "valid": False,
        "errors": [
            {
                "code": "oracle.output_limit",
                "count": 1,
                "examples": [f"report exceeded {MAX_OUTPUT_BYTES} bytes"],
            }
        ],
        "summary": payload.get("summary", {}),
    }
    return _JSON_DUMPS(bounded, separators=(",", ":"), sort_keys=True)


def _write_report(payload: dict[str, Any]) -> None:
    remaining = memoryview((_bounded_json(payload) + "\n").encode())
    while remaining:
        written = _OS_WRITE(1, remaining)
        if written <= 0:
            raise RuntimeError("failed to emit oracle report")
        remaining = remaining[written:]


def _watchdog_failure(code: str, detail: str) -> dict[str, Any]:
    return {
        "schema": ORACLE_SCHEMA,
        "valid": False,
        "errors": [{"code": code, "count": 1, "examples": [detail]}],
        "summary": {
            "check_count": 0,
            "error_count": 1,
            "error_group_count": 1,
            "worker_output_limit_bytes": WORKER_OUTPUT_LIMIT_BYTES,
            "worker_timeout_seconds": TOTAL_TIMEOUT_SECONDS,
        },
    }


def _stop_worker(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    try:
        process.wait(timeout=0.5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _worker_protocol_failure(
    stdout: bytes,
    stderr: bytes,
    returncode: int,
) -> dict[str, Any] | None:
    if stderr:
        return _watchdog_failure(
            "oracle.worker_stderr",
            "worker emitted data on stderr",
        )
    try:
        decoded = stdout.decode("utf-8")
    except UnicodeDecodeError:
        return _watchdog_failure(
            "oracle.worker_encoding",
            "worker stdout was not valid UTF-8",
        )
    try:
        payload = _JSON_LOADS(decoded)
    except (TypeError, ValueError):
        return _watchdog_failure(
            "oracle.worker_protocol",
            "worker stdout was not exactly one JSON value",
        )
    if type(payload) is not dict:
        return _watchdog_failure(
            "oracle.worker_protocol",
            "worker JSON result was not an object",
        )
    if stdout != (_bounded_json(payload) + "\n").encode():
        return _watchdog_failure(
            "oracle.worker_protocol",
            "worker stdout was not one canonical JSON result",
        )
    if not (
        payload.get("schema") == ORACLE_SCHEMA
        and type(payload.get("valid")) is bool
        and type(payload.get("errors")) is list
        and type(payload.get("summary")) is dict
    ):
        return _watchdog_failure(
            "oracle.worker_payload",
            "worker JSON result did not match the oracle envelope",
        )
    expected_returncode = 0 if payload["valid"] else 2
    if returncode != expected_returncode:
        return _watchdog_failure(
            "oracle.worker_status",
            "worker exit status did not match its JSON result",
        )
    return None


def _run_worker(repo_root: Path) -> dict[str, Any]:
    command = (
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--check-all",
        "--repo-root",
        str(repo_root),
        "--_oracle-worker",
    )
    try:
        process = subprocess.Popen(  # noqa: S603 - fixed interpreter and local script
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
        )
    except OSError:
        return _watchdog_failure(
            "oracle.worker_spawn",
            "failed to start isolated oracle worker",
        )

    if process.stdout is None or process.stderr is None:
        _stop_worker(process)
        return _watchdog_failure(
            "oracle.worker_io",
            "isolated oracle worker pipes were unavailable",
        )
    selector: selectors.BaseSelector | None = None
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
    failure: dict[str, Any] | None = None
    try:
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = _watchdog_failure(
                    "oracle.worker_timeout",
                    "isolated oracle worker exceeded its total deadline",
                )
                _stop_worker(process)
                break
            for key, _events in selector.select(remaining):
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                captured[key.data].extend(chunk)
                if sum(len(stream) for stream in captured.values()) > WORKER_OUTPUT_LIMIT_BYTES:
                    failure = _watchdog_failure(
                        "oracle.worker_output_limit",
                        "isolated oracle worker exceeded its aggregate output limit",
                    )
                    _stop_worker(process)
                    break
            if failure is not None:
                break

        if failure is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = _watchdog_failure(
                    "oracle.worker_timeout",
                    "isolated oracle worker exceeded its total deadline",
                )
                _stop_worker(process)
            else:
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    failure = _watchdog_failure(
                        "oracle.worker_timeout",
                        "isolated oracle worker exceeded its total deadline",
                    )
                    _stop_worker(process)
    except (OSError, ValueError):
        failure = _watchdog_failure(
            "oracle.worker_io",
            "isolated oracle worker pipe handling failed",
        )
        _stop_worker(process)
    finally:
        if selector is not None:
            selector.close()
        for stream in (process.stdout, process.stderr):
            if not stream.closed:
                stream.close()

    if failure is not None:
        return failure
    stdout = bytes(captured["stdout"])
    stderr = bytes(captured["stderr"])
    protocol_failure = _worker_protocol_failure(stdout, stderr, process.returncode)
    if protocol_failure is not None:
        return protocol_failure
    return _JSON_LOADS(stdout.decode("utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    if not args.check_all:
        payload = {
            "schema": ORACLE_SCHEMA,
            "valid": False,
            "errors": [
                {
                    "code": "usage.check_all_required",
                    "detail": "invoke with --check-all",
                }
            ],
            "summary": {"check_count": 0, "error_count": 1},
        }
        _write_report(payload)
        return 2
    repo_root = args.repo_root.resolve()
    payload = Oracle(repo_root).run() if args._oracle_worker else _run_worker(repo_root)
    _write_report(payload)
    return 0 if payload["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
