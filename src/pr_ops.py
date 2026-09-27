"""All GitHub-side effects: writing patched files, committing, pushing, opening the PR,
and posting the review-summary comment on the triggering PR (if any)."""
from __future__ import annotations

import os
import subprocess
import time

from github import Github


def apply_patch_to_file(file_path: str, start_line: int, end_line: int, new_body: str) -> None:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    heading_line = lines[start_line] if start_line < len(lines) else ""
    new_lines = lines[:start_line] + [heading_line] + [new_body if new_body.endswith("\n") else new_body + "\n"]
    new_lines += lines[end_line:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def _run(cmd: list[str], cwd: str | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def commit_and_push_fixes(repo_dir: str, branch_name: str, token: str, repo_full_name: str,
                           changed_files: list[str], commit_message: str) -> bool:
    if not changed_files:
        return False
    _run(["git", "config", "user.name", "self-healing-docs-bot"], cwd=repo_dir)
    _run(["git", "config", "user.email", "actions@users.noreply.github.com"], cwd=repo_dir)
    _run(["git", "checkout", "-b", branch_name], cwd=repo_dir)
    _run(["git", "add"] + changed_files, cwd=repo_dir)
    _run(["git", "commit", "-m", commit_message], cwd=repo_dir)
    remote_url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
    _run(["git", "push", remote_url, branch_name, "--force"], cwd=repo_dir)
    return True


def open_fix_pr(token: str, repo_full_name: str, branch_name: str, base_branch: str,
                 title: str, body: str, auto_merge: bool) -> str:
    gh = Github(token)
    repo = gh.get_repo(repo_full_name)
    pr = repo.create_pull(title=title, body=body, head=branch_name, base=base_branch)
    if auto_merge:
        for _ in range(10):
            pr.update()
            if pr.mergeable is not None:
                break
            time.sleep(2)
        if pr.mergeable:
            pr.merge(merge_method="squash")
    return pr.html_url


def post_pr_comment(token: str, repo_full_name: str, pr_number: int, body: str) -> None:
    gh = Github(token)
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    pr.create_issue_comment(body)


def current_pr_number() -> int | None:
    ref = os.environ.get("GITHUB_REF", "")
    if "pull" in ref:
        try:
            return int(ref.split("/")[2])
        except (IndexError, ValueError):
            return None
    return None
