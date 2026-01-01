from typing import Any, Dict, List, Optional
from collections import Counter

from mcp.server.fastmcp import FastMCP
from tools.git_commit_history import get_commit_history_raw, parse_commit_history
from git_runner import ensure_is_git_repo


def analyze_developer_stats(commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze commits to build developer statistics."""
    if not commits:
        return {
            "total_commits": 0,
            "total_files_changed": 0,
            "total_additions": 0,
            "total_deletions": 0,
            "most_active_files": [],
            "file_types": {}
        }

    total_commits = len(commits)
    total_files_changed = sum(c["stats"]["total_files"] for c in commits)
    total_additions = sum(c["stats"]["total_additions"] for c in commits)
    total_deletions = sum(c["stats"]["total_deletions"] for c in commits)

    file_stats: Dict[str, Dict[str, int]] = {}

    for commit in commits:
        for file in commit["files"]:
            path = file["path"]

            if path not in file_stats:
                file_stats[path] = {
                    "commits": 0,
                    "additions": 0,
                    "deletions": 0
                }

            file_stats[path]["commits"] += 1
            file_stats[path]["additions"] += file["additions"]
            file_stats[path]["deletions"] += file["deletions"]

    most_active_files = [
        {
            "path": path,
            "commits": stats["commits"],
            "additions": stats["additions"],
            "deletions": stats["deletions"]
        }
        for path, stats in file_stats.items()
    ]
    most_active_files.sort(key=lambda x: x["commits"], reverse=True)

    file_type_counter = Counter()
    for path in file_stats.keys():
        if "." in path:
            ext = "." + path.split(".")[-1]
            file_type_counter[ext] += 1
        else:
            file_type_counter["(no extension)"] += 1

    return {
        "total_commits": total_commits,
        "total_files_changed": total_files_changed,
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "most_active_files": most_active_files[:20],
        "file_types": dict(file_type_counter.most_common(10))
    }


def build_developer_stats_json(
    repo_path: str,
    author: str,
    commits_raw: str,
    since: Optional[str] = None,
    until: Optional[str] = None
) -> Dict[str, Any]:
    """Build final JSON response for developer stats."""
    commits = parse_commit_history(commits_raw)
    stats = analyze_developer_stats(commits)

    matched_authors = {f"{c['author_name']} <{c['author_email']}>" for c in commits}

    actual_range = {
        "first_commit": None,
        "last_commit": None
    }

    if commits:
        actual_range["last_commit"] = commits[0]["date"]
        actual_range["first_commit"] = commits[-1]["date"]

    return {
        "repo": {"path": repo_path},
        "developer": {
            "identifier": author,
            "matched_as": sorted(list(matched_authors))
        },
        "time_range": {
            "since": since,
            "until": until,
            "actual_range": actual_range
        },
        "stats": stats
    }


def register(mcp: FastMCP) -> None:
    """Register developer statistics tools with MCP server."""
    @mcp.tool()
    async def get_developer_stats(
        repo_path: str,
        author: str,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed statistics about a specific developer's contributions.

        Args:
            repo_path: Absolute path to git repository
            author: Developer name or email (e.g., "John Doe", "john@example.com")
            since: Commits since date (e.g., "2025-01-01", "1 month ago")
            until: Commits until date (e.g., "yesterday", "today")

        Returns statistics including total commits, files changed, additions/deletions,
        most active files, and file types worked on.
        """
        await ensure_is_git_repo(repo_path)

        raw = await get_commit_history_raw(
            repo_path=repo_path,
            author=author,
            since=since,
            until=until
        )

        return build_developer_stats_json(
            repo_path=repo_path,
            author=author,
            commits_raw=raw,
            since=since,
            until=until
        )
