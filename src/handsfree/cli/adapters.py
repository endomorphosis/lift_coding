"""Adapters that translate product intents into CLI-backed results."""

from typing import Any

from handsfree.cli.executor import CLIExecutor
from handsfree.cli.parsers import parse_output
from handsfree.commands.profiles import ProfileConfig


class GitHubCLIAdapter:
    """CLI-backed GitHub read workflows."""

    def __init__(self, executor: CLIExecutor | None = None) -> None:
        self.executor = executor or CLIExecutor()

    def summarize_pr(self, pr_number: int, profile_config: ProfileConfig) -> dict[str, Any]:
        """Summarize a pull request through `gh pr view`."""
        result = self.executor.execute("gh.pr.view", "gh", pr_number=pr_number)
        if not result.ok:
            raise RuntimeError(result.stderr or "gh pr view failed")

        parsed = parse_output("gh_pr_view", result.stdout)
        spoken_text = self._build_spoken_summary(parsed)
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "spoken_text": spoken_text,
            "title": parsed["title"],
            "author": parsed["author"],
            "state": parsed["state"],
            "changed_files": parsed["changed_files"],
            "additions": parsed["additions"],
            "deletions": parsed["deletions"],
            "trace": {
                "provider": "github_cli",
                "command_id": result.command_id,
                "source": result.source,
                "duration_ms": result.duration_ms,
            },
        }

    def _build_spoken_summary(self, parsed: dict[str, Any]) -> str:
        checks = parsed["checks"]
        reviews = parsed["reviews"]
        spoken = (
            f"PR {parsed['pr_number']}: {parsed['title']}. "
            f"By {parsed['author']}. "
            f"{parsed['changed_files']} files changed, "
            f"{parsed['additions']} additions, {parsed['deletions']} deletions. "
        )
        if checks["failed"] > 0:
            spoken += f"Checks: {checks['failed']} failing, {checks['passed']} passing. "
        elif checks["pending"] > 0:
            spoken += f"Checks: {checks['pending']} pending, {checks['passed']} passing. "
        elif checks["total"] > 0:
            spoken += f"All {checks['passed']} checks passing. "

        if reviews["changes_requested"] > 0:
            spoken += f"Reviews: {reviews['changes_requested']} requested changes. "
        elif reviews["approved"] > 0:
            spoken += f"Reviews: {reviews['approved']} approved. "

        return spoken.strip()

    def request_review(self, repo: str, pr_number: int, reviewers: list[str]) -> dict[str, Any]:
        """Request reviewers through `gh pr edit`."""
        result = self.executor.execute(
            "gh.pr.request_review",
            "gh",
            repo=repo,
            pr_number=pr_number,
            reviewers=reviewers,
        )
        if not result.ok:
            return {
                "ok": False,
                "message": result.stderr or "gh pr edit failed",
                "status_code": result.exit_code,
                "trace": {
                    "provider": "github_cli",
                    "command_id": result.command_id,
                    "source": result.source,
                    "duration_ms": result.duration_ms,
                },
            }

        parsed = parse_output("gh_action_result", result.stdout)
        return {
            "ok": True,
            "message": parsed.get("message", f"Review requested from {', '.join(reviewers)}"),
            "url": parsed.get("url"),
            "response_data": parsed,
            "trace": {
                "provider": "github_cli",
                "command_id": result.command_id,
                "source": result.source,
                "duration_ms": result.duration_ms,
            },
        }

    def merge_pr(self, repo: str, pr_number: int, merge_method: str) -> dict[str, Any]:
        """Merge a PR through `gh pr merge`."""
        result = self.executor.execute(
            "gh.pr.merge",
            "gh",
            repo=repo,
            pr_number=pr_number,
            merge_method=merge_method,
        )
        if not result.ok:
            return {
                "ok": False,
                "message": result.stderr or "gh pr merge failed",
                "status_code": result.exit_code,
                "trace": {
                    "provider": "github_cli",
                    "command_id": result.command_id,
                    "source": result.source,
                    "duration_ms": result.duration_ms,
                },
            }

        parsed = parse_output("gh_action_result", result.stdout)
        return {
            "ok": True,
            "message": parsed.get("message", f"PR #{pr_number} merged successfully"),
            "url": parsed.get("url"),
            "response_data": parsed,
            "trace": {
                "provider": "github_cli",
                "command_id": result.command_id,
                "source": result.source,
                "duration_ms": result.duration_ms,
            },
        }

    def comment_on_pr(self, repo: str, pr_number: int, comment_body: str) -> dict[str, Any]:
        """Post a PR comment through `gh pr comment`."""
        result = self.executor.execute(
            "gh.pr.comment",
            "gh",
            repo=repo,
            pr_number=pr_number,
            comment_body=comment_body,
        )
        if not result.ok:
            return {
                "ok": False,
                "message": result.stderr or "gh pr comment failed",
                "status_code": result.exit_code,
                "trace": {
                    "provider": "github_cli",
                    "command_id": result.command_id,
                    "source": result.source,
                    "duration_ms": result.duration_ms,
                },
            }

        parsed = parse_output("gh_action_result", result.stdout)
        return {
            "ok": True,
            "message": parsed.get("message", "Comment posted"),
            "url": parsed.get("url"),
            "response_data": parsed,
            "trace": {
                "provider": "github_cli",
                "command_id": result.command_id,
                "source": result.source,
                "duration_ms": result.duration_ms,
            },
        }


class CopilotCLIAdapter:
    """CLI-backed Copilot read-only workflows."""

    def __init__(self, executor: CLIExecutor | None = None) -> None:
        self.executor = executor or CLIExecutor()

    def explain_pr(self, pr_number: int, profile_config: ProfileConfig) -> dict[str, Any]:
        """Explain a PR using a fixture-backed `gh copilot explain` flow."""
        return self._run_read_command("gh.copilot.explain_pr", pr_number, profile_config)

    def summarize_diff(self, pr_number: int, profile_config: ProfileConfig) -> dict[str, Any]:
        """Summarize the diff for a PR using Copilot CLI."""
        return self._run_read_command("gh.copilot.summarize_diff", pr_number, profile_config)

    def explain_failure(
        self,
        pr_number: int,
        profile_config: ProfileConfig,
        failure_target: str | None = None,
        failure_target_type: str | None = None,
    ) -> dict[str, Any]:
        """Explain failing checks for a PR using Copilot CLI."""
        return self._run_read_command(
            "gh.copilot.explain_failure",
            pr_number,
            profile_config,
            failure_target=failure_target,
            failure_target_type=failure_target_type,
        )

    def _run_read_command(
        self,
        command_id: str,
        pr_number: int,
        profile_config: ProfileConfig,
        **kwargs: object,
    ) -> dict[str, Any]:
        """Execute a Copilot CLI read command and normalize its response."""
        result = self.executor.execute(command_id, "copilot", pr_number=pr_number, **kwargs)
        if not result.ok:
            raise RuntimeError(result.stderr or "gh copilot explain failed")

        parsed = parse_output("gh_copilot_response", result.stdout)
        spoken_text = parsed["spoken_text"] or parsed["summary"] or parsed["headline"]
        spoken_text = profile_config.truncate_spoken_text(spoken_text)
        return {
            "spoken_text": spoken_text,
            "headline": parsed["headline"],
            "summary": parsed["summary"],
            "trace": {
                "provider": "copilot_cli",
                "command_id": result.command_id,
                "source": result.source,
                "duration_ms": result.duration_ms,
            },
        }
