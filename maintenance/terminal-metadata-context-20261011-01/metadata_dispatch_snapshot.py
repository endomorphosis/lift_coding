"""Frozen read-only collector observation; see metadata-observation-provenance.json."""
import re

def validate_semantic_metadata_view(value):
    if type(value) is not str or value not in {'legacy', 'common-bindings@1'}:
        raise ValueError('unsupported metadata view')
    return value

def _metadata_dispatch_observation(report, requested_mode: str) -> dict:
    """Join retained selection receipts to the separate exact-input audit.

    This read-only observation does not rerun the source audit or measure usage.
    A valid legacy fallback remains a completed requested-arm attempt; only
    verified common-bindings inputs count as an effective metadata treatment.
    """
    validate_semantic_metadata_view(requested_mode)
    report = report if type(report) is dict else {}
    declaration = report.get("semantic_metadata_view")
    declared = declaration.get("requested_mode") if type(declaration) is dict else None
    declared_matches = (declared == requested_mode if requested_mode != "legacy"
                        else declaration is None or declared == "legacy")
    problems = [] if declared_matches else ["requested_mode_report_mismatch"]
    if report.get("unreceipted_provider_attempt"):
        problems.append("unreceipted_provider_attempt")
    population = report.get("provider_invocations")
    if type(population) is not list or len(population) > 4096:
        problems.append("provider_invocation_population_unavailable_or_unbounded")
        population = []
    if any(type(row) is not dict for row in population):
        problems.append("malformed_provider_invocation")
    coding = [row for row in population if type(row) is dict and row.get("phase") == "coding"]
    audit = report.get("context_input_audit")
    audit = audit if type(audit) is dict else {}
    audit_rows, matches = audit.get("invocations"), audit.get("matches")
    audit_rows = audit_rows if type(audit_rows) is list and len(audit_rows) <= 16 else []
    matches = matches if type(matches) is list and len(matches) <= 512 else []
    identities = [row.get("invocation_id") for row in coding]
    valid_id = lambda value: type(value) is str and 0 < len(value) <= 4096
    valid_hash = lambda value: type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None
    valid_bytes = lambda value: type(value) is int and 0 < value <= 2_000_000
    distinct = all(valid_id(value) for value in identities) and len(set(identities)) == len(identities)
    audit_ids = [row.get("invocation_id") for row in audit_rows if type(row) is dict]
    audit_population = (distinct and len(audit_rows) == len(coding) == len(audit_ids)
        and all(valid_id(value) for value in audit_ids) and set(audit_ids) == set(identities)
        and len(set(audit_ids)) == len(audit_ids)
        and audit.get("status") == "verified_all_observed_model_inputs"
        and audit.get("all_observed_coding_inputs_verified") is True
        and type(audit.get("coding_receipts_seen")) is int and audit["coding_receipts_seen"] == len(coding)
        and type(audit.get("usable_coding_receipts")) is int and audit["usable_coding_receipts"] == len(coding)
        and audit.get("read_errors") == [])
    if not coding:
        problems.append("no_observed_coding_receipts")
    elif not distinct:
        problems.append("coding_invocation_identities_missing_or_duplicate")
    observations = []
    for row in coding:
        identity = row.get("invocation_id")
        selection = row.get("semantic_metadata_view")
        selection = selection if type(selection) is dict else {}
        mode, fallback = selection.get("selected_mode"), selection.get("fallback_reason")
        valid_selection = (selection.get("schema") == "supervisor-semantic-metadata-selection@1"
            and type(mode) is str and mode in {"legacy", "common-bindings@1"}
            and selection.get("candidate_only") is True
            and selection.get("token_proxy") == "utf8-bytes-ceil-div4@1"
            and all(selection.get(key) is False for key in (
                "source_freshness_verified", "program_semantics_proved", "omission_authority",
                "proof_authority", "execution_authority", "completion_authority", "publication_authority"))
            and all(valid_hash(selection.get(key)) for key in (
                "view_receipt_sha256", "native_complete_sha256", "candidate_complete_sha256", "selected_complete_sha256"))
            and all(valid_bytes(selection.get(key)) for key in (
                "native_complete_bytes", "candidate_complete_bytes", "selected_complete_bytes"))
            and all(type(selection.get(prefix + "_complete_proxy_tokens")) is int
                and selection[prefix + "_complete_proxy_tokens"] == (selection[prefix + "_complete_bytes"] + 3) // 4
                for prefix in ("native", "candidate", "selected")))
        if valid_selection:
            smaller = selection["candidate_complete_bytes"] < selection["native_complete_bytes"] and (
                (selection["candidate_complete_bytes"] + 3) // 4 < (selection["native_complete_bytes"] + 3) // 4)
            prefix = "candidate" if mode == "common-bindings@1" else "native"
            valid_selection = (smaller == (mode == "common-bindings@1")
                and fallback == (None if smaller else "complete_input_not_smaller_under_bytes_and_proxy")
                and selection["selected_complete_sha256"] == selection[prefix + "_complete_sha256"]
                and selection["selected_complete_bytes"] == selection[prefix + "_complete_bytes"])
        bound = (valid_selection and valid_hash(row.get("model_prompt_sha256"))
            and valid_bytes(row.get("model_prompt_bytes"))
            and selection["selected_complete_sha256"] == row["model_prompt_sha256"]
            and selection["selected_complete_bytes"] == row["model_prompt_bytes"])
        per_audit = [item for item in audit_rows if type(item) is dict and item.get("invocation_id") == identity]
        per_matches = [item for item in matches if type(item) is dict and item.get("invocation_id") == identity]
        def verified_match(item):
            checks = item.get("model_input_checks")
            return (item.get("model_input_verified") is True
                and item.get("model_prompt_sha256") == row.get("model_prompt_sha256")
                and type(item.get("model_prompt_bytes")) is int
                and item.get("model_prompt_bytes") == row.get("model_prompt_bytes")
                and type(checks) is dict and checks.get("semantic_metadata_selection_receipt") is True
                and all(value is True for value in checks.values()))
        verified = (bound and audit_population and len(per_audit) == 1
            and per_audit[0].get("model_input_verified") is True
            and per_audit[0].get("status") == "verified_exact_model_input"
            and bool(per_matches) and all(verified_match(item) for item in per_matches))
        row_problems = []
        if not valid_selection: row_problems.append("metadata_selection_missing_or_invalid")
        elif not bound: row_problems.append("selected_input_binding_mismatch")
        if not verified: row_problems.append("retained_exact_input_audit_not_correlated")
        observations.append({"invocation_id": identity if valid_id(identity) else None,
            "selected_mode": mode if type(mode) is str and mode in {"legacy", "common-bindings@1"} else None,
            "fallback_reason": fallback if fallback in (None, "complete_input_not_smaller_under_bytes_and_proxy") else "unrecognized",
            "selection_receipt_matches_model_input": bool(bound),
            "retained_exact_input_audit_verified": bool(verified), "problems": row_problems})
    modes = sorted({row["selected_mode"] for row in observations if row["selected_mode"] is not None})
    bound = bool(observations) and all(row["selection_receipt_matches_model_input"] for row in observations)
    verified = (not problems and bound
        and all(row["retained_exact_input_audit_verified"] for row in observations))
    status = ("verified_treatment" if modes == ["common-bindings@1"] else
              "verified_fallback" if modes == ["legacy"] else "verified_mixed_selection") if verified else "unverified"
    return {"schema": "terminal-semantic-metadata-dispatch-observation@1", "requested_mode": requested_mode,
        "requested_mode_matches_report": declared_matches, "coding_receipts_seen": len(coding),
        "invocations": observations, "selected_modes": modes,
        "fallback_reasons": sorted({row["fallback_reason"] for row in observations if row["fallback_reason"] is not None}),
        "all_selection_receipts_bound_to_model_inputs": bound,
        "all_coding_inputs_verified_by_retained_audit": verified,
        "effective_treatment_observed": verified and modes == ["common-bindings@1"],
        "status": status, "problems": problems, "source_audit_rerun": False,
        "provider_usage_modified": False, "token_savings_established": False}
