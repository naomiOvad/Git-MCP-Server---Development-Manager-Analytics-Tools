from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP
from git_runner import run_git, ensure_is_git_repo


async def get_branches_raw(repo_path: str) -> str:
    """Execute git branch command and return raw output."""
    args = [
        "branch",
        "--all",
        "--format=%(refname:short)|%(committerdate:iso8601)",
        "--sort=-committerdate"
    ]
    return await run_git(repo_path, args)


def parse_branches(raw: str) -> List[Dict[str, Any]]:
    """Parse git branch output into structured list."""
    branches = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split("|", 1)
        if len(parts) != 2 or not parts[0].strip():
            continue

        branches.append({
            "name": parts[0].strip(),
            "last_commit_date": parts[1].strip()
        })

    return branches


def build_branch_list_json(repo_path: str, branches_raw: str) -> Dict[str, Any]:
    """Build final JSON response for branch list."""
    branches = parse_branches(branches_raw)

    return {
        "repo": {"path": repo_path},
        "branches": branches,
        "total_branches": len(branches)
    }


def register(mcp: FastMCP) -> None:
    """Register git branches tools with MCP server."""
    @mcp.tool()
    async def get_branch_list(repo_path: str) -> Dict[str, Any]:
        """
        Get list of all branches in a git repository with their last commit dates.

        Args:
            repo_path: Absolute path to git repository (e.g., "C:\\project" or "/home/user/project")

        Returns all local and remote branches, sorted by most recent activity.
        """
        await ensure_is_git_repo(repo_path)
        raw = await get_branches_raw(repo_path)
        return build_branch_list_json(repo_path, raw)
