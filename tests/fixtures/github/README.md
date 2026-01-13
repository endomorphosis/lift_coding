# GitHub Integration - Fixtures and Testing

This document explains how to work with GitHub fixtures and run tests for the GitHub integration.

## Overview

The GitHub integration uses a fixture-based approach for testing. This allows us to:
- Test without requiring GitHub API credentials
- Have consistent, reproducible test results
- Test edge cases and failure scenarios easily
- Develop offline

## Fixture Structure

Fixtures are stored in `tests/fixtures/github/api/` with the following naming convention:

```
tests/fixtures/github/api/
├── user_prs.json                 # List of PRs for a user
├── pr_{number}_details.json      # PR details for PR #{number}
├── pr_{number}_checks.json       # Check runs for PR #{number}
└── pr_{number}_reviews.json      # Reviews for PR #{number}
```

### Fixture Files

#### `user_prs.json`
Contains an array of PR summaries for the authenticated user, including:
- PRs where the user is a requested reviewer
- PRs where the user is assigned
- Basic PR metadata (title, repo, labels, etc.)

Example:
```json
[
  {
    "repo": "owner/repo",
    "pr_number": 123,
    "title": "Add new feature X",
    "url": "https://github.com/owner/repo/pull/123",
    "state": "open",
    "author": "contributor",
    "requested_reviewer": true,
    "assignee": false,
    "updated_at": "2026-01-10T15:30:00Z",
    "labels": ["feature", "needs-review"]
  }
]
```

#### `pr_{number}_details.json`
Contains detailed information about a specific PR:
- Title and description
- Base and head branches
- Diff statistics (additions, deletions, changed files)
- Labels and state

#### `pr_{number}_checks.json`
Contains check run information:
- Check name
- Status (completed, in_progress, etc.)
- Conclusion (success, failure, etc.)
- Timestamps and URLs

#### `pr_{number}_reviews.json`
Contains review information:
- Reviewer username
- Review state (APPROVED, CHANGES_REQUESTED, COMMENTED)
- Submission timestamp
- Review body/comments

## Adding New Fixtures

To add a new fixture for testing:

1. **Create the fixture files** for a new PR number:
   ```bash
   cd tests/fixtures/github/api
   # Copy existing fixtures as templates
   cp pr_123_details.json pr_456_details.json
   cp pr_123_checks.json pr_456_checks.json
   cp pr_123_reviews.json pr_456_reviews.json
   ```

2. **Edit the fixture data** to match your test scenario:
   - Update PR numbers
   - Modify titles, descriptions, labels
   - Set check statuses (success, failure, pending)
   - Configure review states

3. **Update `user_prs.json`** to include the new PR in the list

4. **Write tests** that use the new fixture

## Running Tests

### Run all tests:
```bash
make test
# or
python3 -m pytest
```

### Run specific test files:
```bash
python3 -m pytest tests/test_inbox.py
python3 -m pytest tests/test_pr_summary.py
python3 -m pytest tests/test_github_provider.py
```

### Run specific test cases:
```bash
python3 -m pytest tests/test_inbox.py::test_inbox_list_spoken_text
python3 -m pytest tests/test_pr_summary.py::test_pr_summarize_basic
```

### Run with verbose output:
```bash
python3 -m pytest -v
```

### Run with output from print statements:
```bash
python3 -m pytest -s
```

## Golden Tests

"Golden tests" verify that the spoken text output remains stable and consistent. These tests:
- Capture the expected spoken output as a string literal in the test
- Assert that the actual output matches exactly
- Help catch unintended changes to user-facing text

Example:
```python
def test_inbox_list_spoken_text(github_provider):
    """Test spoken text output for inbox (golden test)."""
    result = handle_inbox_list(github_provider, user="testuser")
    
    expected_spoken = (
        "You have 3 items in your inbox. 1 high priority. "
        "1. Fix critical bug in authentication in repo. "
        "2. Update documentation for API v2 in other-repo. "
        "3. Add new feature X in repo."
    )
    
    assert result["spoken_text"] == expected_spoken
```

### Updating Golden Tests

If you intentionally change the spoken text format:
1. Run the tests to see the actual output
2. Verify the new output is correct
3. Update the expected string in the test
4. Commit both code and test changes together

## Privacy Mode

All handlers default to `privacy_mode=True`, which means:
- No code snippets are included in responses
- Descriptions are excluded from spoken text (by default)
- Only metadata and statistics are shared

This is tested in `test_inbox_privacy_mode()` and `test_pr_summary_privacy_mode()`.

## Test Coverage

Current test coverage includes:

### GitHub Provider (`test_github_provider.py`)
- Provider initialization
- Loading fixtures
- Error handling for missing fixtures

### Inbox Handler (`test_inbox.py`)
- Basic inbox listing
- Spoken text output (golden test)
- Item structure validation
- Priority ordering
- Privacy mode

### PR Summary Handler (`test_pr_summary.py`)
- Basic PR summarization
- Spoken text output for passing checks (golden test)
- Spoken text output for failing checks (golden test)
- Summary structure validation
- Check run analysis (passing and failing)
- Review analysis (approved, changes requested, commented)
- Diff statistics
- Privacy mode

## CI Integration

All tests run as part of the CI pipeline:
```bash
make fmt-check    # Check code formatting
make lint         # Run linter
make test         # Run all tests
make openapi-validate  # Validate OpenAPI spec
```

These checks must pass before merging any changes.

## Example Test Session

```bash
# Install dependencies
make deps

# Run all tests
make test

# Run specific test with verbose output
python3 -m pytest tests/test_inbox.py::test_inbox_list_spoken_text -v

# Run tests and show print output
python3 -m pytest tests/test_pr_summary.py -s
```

## Troubleshooting

### Import errors
If you see `ModuleNotFoundError: No module named 'handsfree'`:
```bash
python3 -m pip install -e .
```

### Fixture not found errors
Verify that:
1. Fixture files exist in `tests/fixtures/github/api/`
2. File names match the expected pattern
3. JSON is valid (use `python3 -m json.tool < file.json`)

### Test failures after code changes
1. Check if the output actually improved or is a regression
2. Update golden tests if the change was intentional
3. Verify privacy mode is still respected
