from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from tools.git_commit_history import get_commit_history_raw, parse_commit_history
from tools.git_developer_stats import analyze_developer_stats
from git_runner import ensure_is_git_repo


def compare_developers(developer_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare statistics between multiple developers."""
    if not developer_stats:
        return {
            "rankings": {
                "most_commits": None,
                "most_files_changed": None,
                "most_additions": None,
                "most_deletions": None,
                "most_active": None
            },
            "totals": {
                "total_commits": 0,
                "total_files_changed": 0,
                "total_additions": 0,
                "total_deletions": 0
            }
        }

    for dev_stat in developer_stats:
        stats = dev_stat["stats"]
        stats["activity_score"] = stats["total_additions"] + stats["total_deletions"]

    most_commits = max(developer_stats, key=lambda x: x["stats"]["total_commits"])
    most_files = max(developer_stats, key=lambda x: x["stats"]["total_files_changed"])
    most_additions = max(developer_stats, key=lambda x: x["stats"]["total_additions"])
    most_deletions = max(developer_stats, key=lambda x: x["stats"]["total_deletions"])
    most_active = max(developer_stats, key=lambda x: x["stats"]["activity_score"])

    totals = {
        "total_commits": sum(d["stats"]["total_commits"] for d in developer_stats),
        "total_files_changed": sum(d["stats"]["total_files_changed"] for d in developer_stats),
        "total_additions": sum(d["stats"]["total_additions"] for d in developer_stats),
        "total_deletions": sum(d["stats"]["total_deletions"] for d in developer_stats)
    }

    return {
        "rankings": {
            "most_commits": {
                "developer": most_commits["developer"],
                "value": most_commits["stats"]["total_commits"]
            },
            "most_files_changed": {
                "developer": most_files["developer"],
                "value": most_files["stats"]["total_files_changed"]
            },
            "most_additions": {
                "developer": most_additions["developer"],
                "value": most_additions["stats"]["total_additions"]
            },
            "most_deletions": {
                "developer": most_deletions["developer"],
                "value": most_deletions["stats"]["total_deletions"]
            },
            "most_active": {
                "developer": most_active["developer"],
                "value": most_active["stats"]["activity_score"]
            }
        },
        "totals": totals
    }


async def build_comparison_json(
    repo_path: str,
    authors: List[str],
    since: Optional[str] = None,
    until: Optional[str] = None
) -> Dict[str, Any]:
    """Build final JSON response for developer comparison."""
    developer_stats = []

    for author in authors:
        raw = await get_commit_history_raw(
            repo_path=repo_path,
            author=author,
            since=since,
            until=until
        )

        commits = parse_commit_history(raw)
        stats = analyze_developer_stats(commits)

        developer_stats.append({
            "developer": author,
            "stats": stats
        })

    comparison = compare_developers(developer_stats)

    return {
        "repo": {"path": repo_path},
        "time_range": {
            "since": since,
            "until": until
        },
        "developers": developer_stats,
        "comparison": comparison
    }


def register(mcp: FastMCP) -> None:
    """Register developer comparison tools with MCP server."""
    @mcp.tool()
    async def compare_developer_stats(
        repo_path: str,
        authors: List[str],
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare contribution statistics between multiple developers.

        Args:
            repo_path: Absolute path to git repository
            authors: List of 2-10 developer names or emails to compare
            since: Commits since date (e.g., "2025-01-01", "1 month ago")
            until: Commits until date (e.g., "yesterday", "today")

        Returns comparison with rankings (most commits, most files changed, etc.),
        individual developer stats, and totals across all developers.
        """
        await ensure_is_git_repo(repo_path)

        if not authors or len(authors) < 2:
            raise ValueError("Must provide at least 2 developers to compare")

        if len(authors) > 10:
            raise ValueError("Cannot compare more than 10 developers at once")

        return await build_comparison_json(
            repo_path=repo_path,
            authors=authors,
            since=since,
            until=until
        )
