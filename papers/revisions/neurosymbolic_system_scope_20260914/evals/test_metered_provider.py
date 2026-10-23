"""Accounting/dispatch safety tests; these are not scientific provider results."""
import json

import pytest

import metered_provider as m


def test_total_preserves_nonadditive_provider_semantics():
    usage = m.normalize_usage({"prompt_tokens": 32, "completion_tokens": 9,
        "total_tokens": 135, "completion_tokens_details": {"reasoning_tokens": 94},
        "prompt_tokens_details": {"cached_tokens": 20}, "cost_in_usd_ticks": 37756000})
    assert usage["total_tokens"] == 135
    assert usage["reasoning_tokens"] == 94
    assert usage["cached_input_tokens"] == 20
    assert usage["cost_usd_decimal"] == "0.0037756000"


def test_missing_usage_is_never_zero_or_derived_total():
    assert m.normalize_usage(None)["total_tokens"] is None
    assert m.normalize_usage({"prompt_tokens": 12, "completion_tokens": 3})["total_tokens"] is None
    assert m.normalize_usage({"total_tokens": True})["total_tokens"] is None


def test_call_identity_cannot_be_replayed(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "_credential", lambda: (None, {"source": None, "expires_at": None}))
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"schema": "ns-development-provider/v1", "model": "grok-4.6",
        "call_ids": ["only-call"], "max_output_tokens": 100, "timeout_seconds": 5,
        "max_request_bytes": 1024, "reasoning_effort": "low"}))
    request = [{"role": "user", "content": "development-only"}]
    result = m.call(profile, tmp_path / "calls", "only-call", request)
    assert result["status"] == "unavailable_credential"
    assert result["attempted_posts"] == 0
    assert result["normalized_usage"]["total_tokens"] is None
    with pytest.raises(FileExistsError):
        m.call(profile, tmp_path / "calls", "only-call", request)
    assert not (tmp_path / "calls/only-call/dispatch_intent.json").exists()


def test_profile_or_source_change_needs_distinct_run_root(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "_credential", lambda: (None, {"source": None, "expires_at": None}))
    profile = tmp_path / "profile.json"
    values = {"schema": "ns-development-provider/v1", "model": "grok-4.6",
        "call_ids": ["a", "b"], "max_output_tokens": 100, "timeout_seconds": 5,
        "max_request_bytes": 1024, "reasoning_effort": "low"}
    profile.write_text(json.dumps(values))
    m.call(profile, tmp_path / "calls", "a", [{"role": "user", "content": "test"}])
    values["max_output_tokens"] = 101
    profile.write_text(json.dumps(values))
    with pytest.raises(AssertionError, match="new source/profile"):
        m.call(profile, tmp_path / "calls", "b", [{"role": "user", "content": "test"}])
