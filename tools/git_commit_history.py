from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from git_runner import run_git, ensure_is_git_repo


async def get_commit_history_raw(
    repo_path: str,
    branch: Optional[str] = None,
    max_count: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    author: Optional[str] = None
) -> str:
    """Execute git log with filters and return raw output."""
    args = ["log", "--numstat", "--pretty=format:COMMIT|%H|%an|%ae|%ai|%s"]

    args.append(branch if branch else "--all")

    if max_count:
        args.append(f"-{max_count}")
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if author:
        args.append(f"--author={author}")

    return await run_git(repo_path, args)


def parse_commit_history(raw: str) -> List[Dict[str, Any]]:
    """Parse git log output into structured commit list."""
    commits = []
    if not raw:
        return commits

    current_commit = None

    for line in raw.splitlines():
        line = line.strip()

        if line.startswith("COMMIT|"):
            if current_commit:
                total_additions = sum(f["additions"] for f in current_commit["files"])
                total_deletions = sum(f["deletions"] for f in current_commit["files"])
                current_commit["stats"] = {
                    "total_files": len(current_commit["files"]),
                    "total_additions": total_additions,
                    "total_deletions": total_deletions
                }
                commits.append(current_commit)

            parts = line.split("|", 5)
            if len(parts) != 6:
                current_commit = None
                continue

            current_commit = {
                "hash": parts[1].strip(),
                "author_name": parts[2].strip(),
                "author_email": parts[3].strip(),
                "date": parts[4].strip(),
                "message": parts[5].strip(),
                "files": []
            }

        elif current_commit and line:
            parts = line.split("\t")
            if len(parts) == 3:
                additions_str, deletions_str, filepath = parts
                additions = 0 if additions_str.strip() == "-" else int(additions_str)
                deletions = 0 if deletions_str.strip() == "-" else int(deletions_str)

                current_commit["files"].append({
                    "path": filepath.strip(),
                    "additions": additions,
                    "deletions": deletions
                })

    if current_commit:
        total_additions = sum(f["additions"] for f in current_commit["files"])
        total_deletions = sum(f["deletions"] for f in current_commit["files"])
        current_commit["stats"] = {
            "total_files": len(current_commit["files"]),
            "total_additions": total_additions,
            "total_deletions": total_deletions
        }
        commits.append(current_commit)

    return commits


def build_commit_history_json(
    repo_path: str,
    commits_raw: str,
    branch: Optional[str] = None,
    max_count: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    author: Optional[str] = None
) -> Dict[str, Any]:
    """Build final JSON response for commit history."""
    commits = parse_commit_history(commits_raw)

    summary = {
        "total_commits": len(commits),
        "total_files_changed": 0,
        "total_additions": 0,
        "total_deletions": 0,
        "authors": [],
        "date_range": {"earliest": None, "latest": None}
    }

    if commits:
        summary["total_files_changed"] = sum(c["stats"]["total_files"] for c in commits)
        summary["total_additions"] = sum(c["stats"]["total_additions"] for c in commits)
        summary["total_deletions"] = sum(c["stats"]["total_deletions"] for c in commits)

        authors_set = {f"{c['author_name']} <{c['author_email']}>" for c in commits}
        summary["authors"] = sorted(authors_set)

        summary["date_range"]["latest"] = commits[0]["date"]
        summary["date_range"]["earliest"] = commits[-1]["date"]

    return {
        "repo": {"path": repo_path},
        "filters": {
            "branch": branch,
            "max_count": max_count,
            "since": since,
            "until": until,
            "author": author
        },
        "commits": commits,
        "summary": summary
    }


def register(mcp: FastMCP) -> None:
    """Register git commit history tools with MCP server."""
    @mcp.tool()
    async def get_commit_history(
        repo_path: str,
        branch: Optional[str] = None,
        max_count: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed commit history with file changes and statistics.

        Args:
            repo_path: Absolute path to git repository
            branch: Specific branch (default: all branches)
            max_count: Maximum commits to return (recommended: 50-100)
            since: Commits since date (e.g., "2025-01-01", "1 week ago")
            until: Commits until date (e.g., "yesterday", "2 days ago")
            author: Filter by author name or email

        Returns commits with file changes, statistics, and summary including total changes,
        unique authors, and date range.
        """
        await ensure_is_git_repo(repo_path)

        raw = await get_commit_history_raw(
            repo_path=repo_path,
            branch=branch,
            max_count=max_count,
            since=since,
            until=until,
            author=author
        )

        return build_commit_history_json(
            repo_path=repo_path,
            commits_raw=raw,
            branch=branch,
            max_count=max_count,
            since=since,
            until=until,
            author=author
        )
