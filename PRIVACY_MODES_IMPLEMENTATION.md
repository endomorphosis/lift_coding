# Privacy Modes Implementation Summary

## Overview
Implemented first-class privacy modes (strict/balanced/debug) enforced across summaries and logs as specified in the implementation plan.

## Changes Made

### 1. Model + API Surface
- **File**: `src/handsfree/models.py`
  - Added `PrivacyMode` enum with three values:
    - `STRICT = "strict"` - No images, no code snippets, summaries only (default)
    - `BALANCED = "balanced"` - Small excerpts permitted with redaction
    - `DEBUG = "debug"` - Verbose, includes more diagnostics
  - Added `privacy_mode: PrivacyMode = PrivacyMode.STRICT` field to `ClientContext`
  - Default is STRICT as required

- **File**: `spec/openapi.yaml`
  - Added `PrivacyMode` schema definition with enum values and descriptions
  - Added `privacy_mode` field to `ClientContext` schema with reference to PrivacyMode
  - Validated with `make openapi-validate` ✅

### 2. Enforcement in Handlers

#### PR Summary Handler (`src/handsfree/handlers/pr_summary.py`)
- Updated `handle_pr_summarize()` to accept `privacy_mode: PrivacyMode` parameter
- **Strict mode**: No description excerpts in spoken text
- **Balanced mode**: 
  - Includes short description excerpts (first 100 chars) with `redact_secrets()` applied
  - Adds "Description: {excerpt}" to spoken text
- **Debug mode**:
  - Includes full description in `debug_description` field (separate from spoken text)
  - Description is redacted via `redact_secrets()`
- All modes prevent code snippets in spoken text

#### Inbox Handler (`src/handsfree/handlers/inbox.py`)
- Updated `handle_inbox_list()` to accept `privacy_mode: PrivacyMode` parameter
- **Strict mode**: Redacts summaries, no code snippets
- **Balanced mode**: Redacts summaries with `redact_secrets()`
- **Debug mode**: 
  - Includes `debug_info` field in each item with:
    - labels
    - requested_reviewer status
    - assignee status
- All modes prevent code snippets in summaries

### 3. API Integration
- **File**: `src/handsfree/api.py`
  - Updated `_convert_router_response_to_command_response()` to accept and pass `privacy_mode` parameter
  - Extracts `privacy_mode` from `request.client_context.privacy_mode` in `submit_command()`
  - Passes privacy_mode to both `handle_inbox_list()` and `handle_pr_summarize()` handlers

### 4. Logging and Redaction
- **File**: `src/handsfree/logging_utils.py`
  - Already implements `redact_secrets()` function that removes:
    - GitHub personal access tokens (ghp_*)
    - GitHub App tokens (ghs_*)
    - GitHub OAuth tokens (gho_*)
    - Fine-grained PATs (github_pat_*)
    - Authorization header values
  - Transcript logging already gated by `client_context.debug` flag (line 661 in api.py)

### 5. Tests

#### Unit Tests for PR Summary (`tests/test_pr_summary.py`)
- `test_pr_summary_privacy_mode_strict`: Verifies no description in strict mode
- `test_pr_summary_privacy_mode_balanced`: Verifies description excerpt in balanced mode
- `test_pr_summary_privacy_mode_debug`: Verifies debug_description field in debug mode
- `test_pr_summary_privacy_mode_default`: Verifies default is strict
- `test_pr_summary_privacy_mode_redaction`: Verifies redaction is applied

#### Unit Tests for Inbox (`tests/test_inbox.py`)
- `test_inbox_privacy_mode_strict`: Verifies no debug_info in strict mode
- `test_inbox_privacy_mode_balanced`: Verifies redaction in balanced mode
- `test_inbox_privacy_mode_debug`: Verifies debug_info field in debug mode
- `test_inbox_privacy_mode_default`: Verifies default is strict
- `test_inbox_privacy_mode_redaction`: Verifies redaction is applied

#### Integration Tests (`tests/test_privacy_mode_integration.py`)
- `test_privacy_mode_default_strict`: Verifies default behavior
- `test_privacy_mode_explicit_strict`: Verifies explicit strict mode
- `test_privacy_mode_balanced`: Verifies balanced mode with kitchen profile
- `test_privacy_mode_debug`: Verifies debug mode includes transcript
- `test_privacy_mode_balanced_redacts_secrets`: Verifies no tokens in output
- `test_privacy_mode_invalid_value`: Verifies validation rejects invalid values
- `test_privacy_mode_pr_summarize_all_modes`: Tests all modes for PR summary
- `test_privacy_mode_inbox_list_all_modes`: Tests all modes for inbox list

## Test Results
- **869 tests passing** (added 18 new tests)
- **0 tests broken** by changes
- All privacy mode tests passing ✅
- OpenAPI validation passing ✅
- Formatting checked ✅

## Behavioral Changes
- **Default privacy mode is STRICT** - no description excerpts by default
- **Balanced mode** allows short excerpts with redaction
- **Debug mode** adds debug_info/debug_description fields
- **All modes** always redact secrets via `redact_secrets()`
- **Profile truncation** still applies after privacy mode processing

## Backwards Compatibility
- New field `privacy_mode` has default value `PrivacyMode.STRICT`
- Existing API calls without `privacy_mode` will use strict mode
- No breaking changes to existing functionality
- All existing tests still pass

## Security Guarantees
✅ Never log/store raw secrets (always redacted)  
✅ Never include code snippets in responses  
✅ Default is strictest mode (strict)  
✅ Debug mode never default (must be explicitly requested)  
✅ Transcript logging gated by debug flag  
✅ All excerpts in balanced/debug modes are redacted  

## Files Changed
1. `src/handsfree/models.py` - Added PrivacyMode enum and field
2. `src/handsfree/api.py` - Pass privacy_mode to handlers
3. `src/handsfree/handlers/pr_summary.py` - Enforce privacy modes
4. `src/handsfree/handlers/inbox.py` - Enforce privacy modes
5. `spec/openapi.yaml` - Added PrivacyMode schema
6. `tests/test_pr_summary.py` - Added privacy mode tests
7. `tests/test_inbox.py` - Added privacy mode tests
8. `tests/test_privacy_mode_integration.py` - Added integration tests (new file)

## Validation Commands
```bash
make fmt-check  # ✅ Formatting verified
make lint       # ✅ No new lint errors
make test       # ✅ 869 passing, 18 new tests
make openapi-validate  # ✅ OpenAPI spec valid
```

## Implementation Notes
- Privacy mode enforcement happens at the handler level, before profile truncation
- Profile truncation (max_spoken_words) applies after privacy mode processing
- Debug mode requires both `privacy_mode: debug` AND `client_context.debug: true` for full functionality
- Redaction is always applied regardless of privacy mode for security
