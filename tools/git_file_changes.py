import os
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from git_runner import run_git, ensure_is_git_repo


async def get_file_history_raw(
    repo_path: str,
    file_path: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    max_count: Optional[int] = None
) -> str:
    """Execute git log for a specific file and return raw output."""
    args = [
        "log",
        "--follow",
        "--numstat",
        "--pretty=format:COMMIT|%H|%an|%ae|%ai|%s"
    ]

    if max_count:
        args.append(f"-{max_count}")

    if since:
        args.append(f"--since={since}")

    if until:
        args.append(f"--until={until}")

    args.append("--")
    args.append(file_path)

    return await run_git(repo_path, args)


def parse_file_history(raw: str, target_file: str) -> List[Dict[str, Any]]:
    """Parse git log output for a specific file."""
    commits: List[Dict[str, Any]] = []

    if not raw:
        return commits

    lines = raw.splitlines()
    current_commit: Optional[Dict[str, Any]] = None

    for line in lines:
        line_stripped = line.strip()

        if line_stripped.startswith("COMMIT|"):
            if current_commit is not None:
                commits.append(current_commit)

            parts = line_stripped.split("|", 5)

            if len(parts) != 6:
                current_commit = None
                continue

            current_commit = {
                "hash": parts[1].strip(),
                "author_name": parts[2].strip(),
                "author_email": parts[3].strip(),
                "date": parts[4].strip(),
                "message": parts[5].strip(),
                "changes": {
                    "additions": 0,
                    "deletions": 0,
                    "file_path": None
                }
            }

        elif current_commit is not None and line_stripped:
            parts = line_stripped.split("\t")

            if len(parts) == 3:
                additions_str = parts[0].strip()
                deletions_str = parts[1].strip()
                filepath = parts[2].strip()

                additions = 0 if additions_str == "-" else int(additions_str)
                deletions = 0 if deletions_str == "-" else int(deletions_str)

                current_commit["changes"]["additions"] = additions
                current_commit["changes"]["deletions"] = deletions
                current_commit["changes"]["file_path"] = filepath

    if current_commit is not None:
        commits.append(current_commit)

    return commits


async def build_file_history_json(
    repo_path: str,
    file_path: str,
    file_history_raw: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    max_count: Optional[int] = None
) -> Dict[str, Any]:
    """Build final JSON response for file history."""
    commits = parse_file_history(file_history_raw, file_path)

    full_path = os.path.join(repo_path, file_path)
    file_exists = os.path.exists(full_path)

    summary: Dict[str, Any] = {
        "total_commits": len(commits),
        "total_additions": 0,
        "total_deletions": 0,
        "unique_authors": [],
        "first_change": None,
        "last_change": None
    }

    if commits:
        summary["total_additions"] = sum(c["changes"]["additions"] for c in commits)
        summary["total_deletions"] = sum(c["changes"]["deletions"] for c in commits)

        authors_set = {f"{c['author_name']} <{c['author_email']}>" for c in commits}
        summary["unique_authors"] = sorted(list(authors_set))

        summary["last_change"] = commits[0]["date"]
        summary["first_change"] = commits[-1]["date"]

    return {
        "repo": {"path": repo_path},
        "file": {
            "path": file_path,
            "exists": file_exists
        },
        "time_range": {
            "since": since,
            "until": until,
            "max_count": max_count
        },
        "commits": commits,
        "summary": summary
    }


def register(mcp: FastMCP) -> None:
    """Register file change tracking tools with MCP server."""
    @mcp.tool()
    async def get_file_changes(
        repo_path: str,
        file_path: str,
        since: Optional[str] = None,
        until: Optional[str] = None,
        max_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get the history of changes to a specific file in a git repository.

        Args:
            repo_path: Absolute path to git repository
            file_path: Relative path to file from repository root (e.g., "src/main.py")
            since: Commits since date (e.g., "2025-01-01", "1 week ago")
            until: Commits until date (e.g., "yesterday", "2 days ago")
            max_count: Maximum number of commits to return

        Returns commit history including changes, authors, and summary statistics.
        Follows file renames automatically.
        """
        await ensure_is_git_repo(repo_path)

        raw = await get_file_history_raw(
            repo_path=repo_path,
            file_path=file_path,
            since=since,
            until=until,
            max_count=max_count
        )

        return await build_file_history_json(
            repo_path=repo_path,
            file_path=file_path,
            file_history_raw=raw,
            since=since,
            until=until,
            max_count=max_count
        )
