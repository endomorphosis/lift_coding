from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

try:  # pragma: no cover - optional integration surface
    from ipfs_datasets_py.logic.api import compile_nl_to_policy
except Exception:  # pragma: no cover - import is environment-dependent
    compile_nl_to_policy = None  # type: ignore[assignment]

try:  # pragma: no cover - optional integration surface
    from ipfs_datasets_py.logic.integration.nl_ucan_policy_compiler import NLUCANPolicyCompiler
except Exception:  # pragma: no cover - import is environment-dependent
    NLUCANPolicyCompiler = None  # type: ignore[assignment]


STRICT_TEMPLATE_PROFILE = "control-surface-strict-template-v0.1"
GENERAL_NL_PROFILE = "control-surface-nl-ucan-fallback-v0.1"

STRICT_TEMPLATE_EXAMPLES = (
    "Ignore my {surface} at {time_window}.",
    "Allow {surface} to {method} only when {state}.",
    "Require confirmation before {method}.",
    "Never let agents {method} unless I said yes.",
)


def _stable_policy_id(text: str, profile: str) -> str:
    digest = hashlib.sha256(f"{profile}\n{text.strip().lower()}".encode()).hexdigest()[:16]
    return f"control-surface-policy-{digest}"


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" .!?")).strip()


def _canonical_token(value: str) -> str:
    cleaned = _clean_value(value).lower()
    cleaned = cleaned.replace("/", " ")
    cleaned = re.sub(r"[^a-z0-9_.:-]+", "_", cleaned)
    return cleaned.strip("_")


def _canonical_surface(value: str) -> tuple[str, str]:
    detail = _canonical_token(value)
    if "agent" in detail:
        return "agent", detail
    if "voice" in detail or "utterance" in detail or "speech" in detail:
        return "voice", detail
    if "mouse" in detail or "pointer" in detail or "click" in detail:
        return "mouse", detail
    if "gesture" in detail or "wrist" in detail or "tap" in detail or "swipe" in detail:
        return "gesture", detail
    return detail, detail


def _summarize_optional_logic_result(result: Any) -> dict[str, Any]:
    if result is None:
        return {}
    metadata = getattr(result, "metadata", {}) or {}
    return {
        "success": bool(getattr(result, "success", False)),
        "errors": [str(item) for item in getattr(result, "errors", []) or []],
        "warnings": [str(item) for item in getattr(result, "warnings", []) or []],
        "clause_count": len(getattr(result, "clauses", []) or []),
        "formula_count": len(getattr(result, "dcec_formulas", []) or []),
        "metadata": dict(metadata) if isinstance(metadata, dict) else {},
    }


@dataclass(frozen=True)
class TemplatePolicyRule:
    """Deterministic policy rule emitted by the strict control-surface profile."""

    template_id: str
    source_text: str
    decision: str
    clause_type: str
    canonical_sentence: str
    surface: str = "*"
    method: str = "*"
    conditions: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "source_text": self.source_text,
            "decision": self.decision,
            "clause_type": self.clause_type,
            "canonical_sentence": self.canonical_sentence,
            "surface": self.surface,
            "method": self.method,
            "conditions": dict(self.conditions),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class CompiledControlSurfacePolicy:
    """Compiled policy bundle consumed by the mediation runtime."""

    policy_id: str
    profile: str
    source_text: str
    success: bool
    rules: tuple[TemplatePolicyRule, ...] = ()
    fallback_result: Any = None
    explanation: str = ""
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "policy_id": self.policy_id,
            "profile": self.profile,
            "source_text": self.source_text,
            "success": self.success,
            "rules": [rule.as_dict() for rule in self.rules],
            "explanation": self.explanation,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }
        if self.fallback_result is not None:
            payload["fallback"] = {
                "success": bool(getattr(self.fallback_result, "success", False)),
                "errors": [str(item) for item in getattr(self.fallback_result, "errors", []) or []],
                "warnings": [
                    str(item) for item in getattr(self.fallback_result, "warnings", []) or []
                ],
                "metadata": dict(getattr(self.fallback_result, "metadata", {}) or {}),
            }
        return payload


@dataclass(frozen=True)
class _TemplateSpec:
    template_id: str
    pattern: re.Pattern[str]
    builder: Callable[[str, re.Match[str]], TemplatePolicyRule]


class StrictTemplateControlSurfacePolicyCompiler:
    """Compile high-confidence multimodal control rules from constrained templates."""

    profile = STRICT_TEMPLATE_PROFILE

    def __init__(self, *, attach_logic_result: bool = True) -> None:
        self.attach_logic_result = attach_logic_result
        self._templates = (
            _TemplateSpec(
                "ignore_surface_at_time",
                re.compile(
                    r"^ignore\s+my\s+(?P<surface>[a-z0-9_.:/ -]+?)"
                    r"(?:\s+at\s+(?P<time_window>[a-z0-9_.:/ -]+))?[.!]?$",
                    re.IGNORECASE,
                ),
                self._build_ignore_surface_rule,
            ),
            _TemplateSpec(
                "allow_surface_method_only_when_state",
                re.compile(
                    r"^allow\s+(?P<surface>[a-z0-9_.:/ -]+?)\s+to\s+"
                    r"(?P<method>[a-z0-9_.:/ -]+?)\s+only\s+when\s+"
                    r"(?P<state>[a-z0-9_.:/ -]+)[.!]?$",
                    re.IGNORECASE,
                ),
                self._build_allow_only_when_rule,
            ),
            _TemplateSpec(
                "require_confirmation_before_method",
                re.compile(
                    r"^require\s+confirmation\s+before\s+(?P<method>[a-z0-9_.:/ -]+)[.!]?$",
                    re.IGNORECASE,
                ),
                self._build_require_confirmation_rule,
            ),
            _TemplateSpec(
                "never_let_agents_method_unless_yes",
                re.compile(
                    r"^never\s+let\s+agents\s+(?P<method>[a-z0-9_.:/ -]+?)"
                    r"\s+unless\s+i\s+said\s+yes[.!]?$",
                    re.IGNORECASE,
                ),
                self._build_agent_confirmation_rule,
            ),
        )

    def compile(self, text: str, *, policy_id: str | None = None) -> CompiledControlSurfacePolicy:
        source_text = _clean_value(text)
        resolved_policy_id = policy_id or _stable_policy_id(source_text, self.profile)

        for spec in self._templates:
            match = spec.pattern.match(source_text)
            if match is None:
                continue

            rule = spec.builder(source_text, match)
            metadata: dict[str, Any] = {
                "template_profile": self.profile,
                "template_examples": list(STRICT_TEMPLATE_EXAMPLES),
                "matched_template": spec.template_id,
            }
            warnings: list[str] = []
            if self.attach_logic_result:
                logic_result, logic_warning = self._compile_canonical_sentence(
                    rule.canonical_sentence,
                    policy_id=resolved_policy_id,
                )
                if logic_warning:
                    warnings.append(logic_warning)
                if logic_result is not None:
                    metadata["compile_nl_to_policy"] = _summarize_optional_logic_result(
                        logic_result
                    )

            return CompiledControlSurfacePolicy(
                policy_id=resolved_policy_id,
                profile=self.profile,
                source_text=source_text,
                success=True,
                rules=(rule,),
                explanation=(
                    f"Matched strict template {spec.template_id}; "
                    f"emit {rule.decision} for surface={rule.surface} method={rule.method}."
                ),
                warnings=tuple(warnings),
                metadata=metadata,
            )

        return CompiledControlSurfacePolicy(
            policy_id=resolved_policy_id,
            profile=self.profile,
            source_text=source_text,
            success=False,
            errors=(f"No strict control-surface policy template matched: {source_text}",),
            metadata={
                "template_profile": self.profile,
                "template_examples": list(STRICT_TEMPLATE_EXAMPLES),
            },
        )

    def _compile_canonical_sentence(
        self, sentence: str, *, policy_id: str
    ) -> tuple[Any | None, str]:
        if compile_nl_to_policy is None:
            return None, "ipfs_datasets_py.logic.api.compile_nl_to_policy unavailable"
        try:
            return compile_nl_to_policy([sentence], policy_id=policy_id, default_actor="user"), ""
        except Exception as exc:  # pragma: no cover - depends on optional compiler internals
            return None, f"compile_nl_to_policy did not accept canonical sentence: {exc}"

    @staticmethod
    def _build_ignore_surface_rule(source_text: str, match: re.Match[str]) -> TemplatePolicyRule:
        surface, surface_detail = _canonical_surface(match.group("surface"))
        raw_time_window = match.groupdict().get("time_window") or ""
        conditions: dict[str, Any] = {"surface_detail": surface_detail}
        if raw_time_window:
            conditions["time_window"] = _canonical_token(raw_time_window)
        return TemplatePolicyRule(
            template_id="ignore_surface_at_time",
            source_text=source_text,
            decision="deny",
            clause_type="prohibition",
            surface=surface,
            method="*",
            conditions=conditions,
            canonical_sentence=f"User must not invoke {surface} controls.",
        )

    @staticmethod
    def _build_allow_only_when_rule(source_text: str, match: re.Match[str]) -> TemplatePolicyRule:
        surface, surface_detail = _canonical_surface(match.group("surface"))
        method = _canonical_token(match.group("method"))
        state = _canonical_token(match.group("state"))
        return TemplatePolicyRule(
            template_id="allow_surface_method_only_when_state",
            source_text=source_text,
            decision="allow",
            clause_type="permission",
            surface=surface,
            method=method,
            conditions={
                "required_state": state,
                "surface_detail": surface_detail,
                "otherwise": "deny",
            },
            canonical_sentence=f"User may invoke {method} from {surface} when {state}.",
        )

    @staticmethod
    def _build_require_confirmation_rule(
        source_text: str, match: re.Match[str]
    ) -> TemplatePolicyRule:
        method = _canonical_token(match.group("method"))
        return TemplatePolicyRule(
            template_id="require_confirmation_before_method",
            source_text=source_text,
            decision="require_confirmation",
            clause_type="obligation",
            method=method,
            conditions={"confirmation": "before_invocation"},
            canonical_sentence=f"System must confirm before invoking {method}.",
        )

    @staticmethod
    def _build_agent_confirmation_rule(
        source_text: str, match: re.Match[str]
    ) -> TemplatePolicyRule:
        method = _canonical_token(match.group("method"))
        return TemplatePolicyRule(
            template_id="never_let_agents_method_unless_yes",
            source_text=source_text,
            decision="require_confirmation",
            clause_type="obligation",
            surface="agent",
            method=method,
            conditions={"confirmation": "explicit_user_yes", "otherwise": "deny"},
            canonical_sentence=f"Agent must confirm with the user before invoking {method}.",
        )


class ControlSurfacePolicyCompiler:
    """Two-lane compiler for multimodal UI and device-control policy rules."""

    def __init__(
        self,
        *,
        strict_compiler: StrictTemplateControlSurfacePolicyCompiler | None = None,
        fallback_compiler: Any | None = None,
        allow_fallback: bool = True,
    ) -> None:
        self.strict_compiler = strict_compiler or StrictTemplateControlSurfacePolicyCompiler()
        self.fallback_compiler = fallback_compiler
        self.allow_fallback = allow_fallback

    def compile(self, text: str, *, policy_id: str | None = None) -> CompiledControlSurfacePolicy:
        strict_result = self.strict_compiler.compile(text, policy_id=policy_id)
        if strict_result.success or not self.allow_fallback:
            return strict_result
        fallback_result = self.compile_freeform(text, policy_id=policy_id)
        if fallback_result.success:
            return fallback_result
        return CompiledControlSurfacePolicy(
            policy_id=strict_result.policy_id,
            profile=strict_result.profile,
            source_text=strict_result.source_text,
            success=False,
            errors=tuple([*strict_result.errors, *fallback_result.errors]),
            warnings=tuple([*strict_result.warnings, *fallback_result.warnings]),
            metadata={
                "strict": strict_result.as_dict(),
                "fallback": fallback_result.as_dict(),
            },
        )

    def compile_freeform(
        self, text: str, *, policy_id: str | None = None
    ) -> CompiledControlSurfacePolicy:
        source_text = _clean_value(text)
        resolved_policy_id = policy_id or _stable_policy_id(source_text, GENERAL_NL_PROFILE)
        compiler = self.fallback_compiler
        if compiler is None:
            if NLUCANPolicyCompiler is None:
                return CompiledControlSurfacePolicy(
                    policy_id=resolved_policy_id,
                    profile=GENERAL_NL_PROFILE,
                    source_text=source_text,
                    success=False,
                    errors=(
                        "NLUCANPolicyCompiler unavailable for freeform control-surface policy.",
                    ),
                )
            compiler = NLUCANPolicyCompiler(policy_id=resolved_policy_id, default_actor="user")

        try:
            result, explanation = compiler.compile_explain(
                [source_text], policy_id=resolved_policy_id
            )
        except AttributeError:
            try:
                result = compiler.compile([source_text], policy_id=resolved_policy_id)
                explanation = result.explain() if hasattr(result, "explain") else ""
            except Exception as exc:
                return CompiledControlSurfacePolicy(
                    policy_id=resolved_policy_id,
                    profile=GENERAL_NL_PROFILE,
                    source_text=source_text,
                    success=False,
                    errors=(f"NLUCANPolicyCompiler failed: {exc}",),
                )
        except Exception as exc:
            return CompiledControlSurfacePolicy(
                policy_id=resolved_policy_id,
                profile=GENERAL_NL_PROFILE,
                source_text=source_text,
                success=False,
                errors=(f"NLUCANPolicyCompiler failed: {exc}",),
            )

        return CompiledControlSurfacePolicy(
            policy_id=resolved_policy_id,
            profile=GENERAL_NL_PROFILE,
            source_text=source_text,
            success=bool(getattr(result, "success", False)),
            fallback_result=result,
            explanation=str(explanation),
            errors=tuple(str(item) for item in getattr(result, "errors", []) or []),
            warnings=tuple(str(item) for item in getattr(result, "warnings", []) or []),
            metadata={"compiler": "NLUCANPolicyCompiler"},
        )


def compile_user_policy_template(
    text: str, *, policy_id: str | None = None
) -> CompiledControlSurfacePolicy:
    """Compile only the deterministic strict-template profile."""

    return StrictTemplateControlSurfacePolicyCompiler().compile(text, policy_id=policy_id)


def compile_control_surface_policy(
    text: str,
    *,
    policy_id: str | None = None,
    allow_fallback: bool = True,
) -> CompiledControlSurfacePolicy:
    """Compile a user-authored multimodal control policy with strict templates first."""

    return ControlSurfacePolicyCompiler(allow_fallback=allow_fallback).compile(
        text, policy_id=policy_id
    )
