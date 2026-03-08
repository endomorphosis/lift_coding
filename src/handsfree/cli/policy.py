"""Allowlist policy for CLI-backed workflows."""

import re

from handsfree.cli.models import CLICommandSpec


def get_command_spec(command_id: str, **kwargs: object) -> CLICommandSpec:
    """Return the allowlisted command spec for a known command."""
    if command_id == "gh.pr.view":
        pr_number = int(kwargs["pr_number"])
        return CLICommandSpec(
            command_id=command_id,
            argv=[
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "number,title,author,state,additions,deletions,changedFiles,labels,reviews,statusCheckRollup,body",
            ],
            fixture_name=f"pr_view_{pr_number}.json",
            parser="gh_pr_view",
            tool_family="gh",
        )

    if command_id == "gh.copilot.explain_pr":
        pr_number = int(kwargs["pr_number"])
        return CLICommandSpec(
            command_id=command_id,
            argv=[
                "gh",
                "copilot",
                "explain",
                f"pull request {pr_number}",
            ],
            fixture_name=f"explain_pr_{pr_number}.json",
            parser="gh_copilot_explain_pr",
            tool_family="gh_copilot",
        )

    if command_id == "gh.copilot.summarize_diff":
        pr_number = int(kwargs["pr_number"])
        return CLICommandSpec(
            command_id=command_id,
            argv=[
                "gh",
                "copilot",
                "explain",
                f"diff for pull request {pr_number}",
            ],
            fixture_name=f"summarize_diff_{pr_number}.json",
            parser="gh_copilot_response",
            tool_family="gh_copilot",
        )

    if command_id == "gh.copilot.explain_failure":
        pr_number = int(kwargs["pr_number"])
        failure_target = str(kwargs.get("failure_target") or "").strip()
        failure_target_type = str(kwargs.get("failure_target_type") or "").strip()
        fixture_suffix = ""
        explain_target = f"failing checks on pull request {pr_number}"
        if failure_target:
            slug = re.sub(r"[^a-z0-9]+", "_", failure_target.lower()).strip("_")
            fixture_suffix = f"_{slug}" if slug else ""
            target_prefix = f"{failure_target_type} " if failure_target_type else ""
            explain_target = f"{target_prefix}{failure_target} failure on pull request {pr_number}"
        return CLICommandSpec(
            command_id=command_id,
            argv=[
                "gh",
                "copilot",
                "explain",
                explain_target,
            ],
            fixture_name=f"explain_failure_{pr_number}{fixture_suffix}.json",
            parser="gh_copilot_response",
            tool_family="gh_copilot",
        )

    if command_id == "gh.pr.request_review":
        pr_number = int(kwargs["pr_number"])
        repo = str(kwargs["repo"])
        reviewers = [str(reviewer) for reviewer in kwargs["reviewers"]]
        argv = ["gh", "pr", "edit", str(pr_number), "--repo", repo]
        for reviewer in reviewers:
            argv.extend(["--add-reviewer", reviewer])
        return CLICommandSpec(
            command_id=command_id,
            argv=argv,
            fixture_name="request_review_success.json",
            parser="gh_action_result",
            tool_family="gh",
        )

    if command_id == "gh.pr.merge":
        pr_number = int(kwargs["pr_number"])
        repo = str(kwargs["repo"])
        merge_method = str(kwargs["merge_method"])
        merge_flag_map = {
            "merge": "--merge",
            "squash": "--squash",
            "rebase": "--rebase",
        }
        merge_flag = merge_flag_map[merge_method]
        return CLICommandSpec(
            command_id=command_id,
            argv=["gh", "pr", "merge", str(pr_number), "--repo", repo, merge_flag],
            fixture_name="merge_success.json",
            parser="gh_action_result",
            tool_family="gh",
        )

    if command_id == "gh.pr.comment":
        pr_number = int(kwargs["pr_number"])
        repo = str(kwargs["repo"])
        comment_body = str(kwargs["comment_body"])
        return CLICommandSpec(
            command_id=command_id,
            argv=["gh", "pr", "comment", str(pr_number), "--repo", repo, "--body", comment_body],
            fixture_name="comment_success.json",
            parser="gh_action_result",
            tool_family="gh",
        )

    raise ValueError(f"Unknown CLI command template: {command_id}")
