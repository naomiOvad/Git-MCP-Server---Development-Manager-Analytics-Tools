from typing import Any, Dict, Optional
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from git_runner import run_git, ensure_is_git_repo


async def sync_repository_fetch(repo_path: str) -> str:
    """Run git fetch to sync with all remotes."""
    args = ["fetch", "--all", "--prune", "--verbose"]
    return await run_git(repo_path, args)


async def sync_repository_pull(repo_path: str, branch: Optional[str] = None) -> str:
    """Run git pull to sync and update the current branch."""
    output_parts = []

    if branch:
        checkout_args = ["checkout", branch]
        checkout_output = await run_git(repo_path, checkout_args)
        output_parts.append(f"CHECKOUT:\n{checkout_output}")

    pull_args = ["pull", "--verbose"]
    pull_output = await run_git(repo_path, pull_args)
    output_parts.append(f"PULL:\n{pull_output}")

    return "\n\n".join(output_parts)


async def get_sync_status(repo_path: str) -> str:
    """Get current sync status by checking commits ahead/behind remote."""
    args = ["status", "--branch", "--short"]
    return await run_git(repo_path, args)


def parse_fetch_output(raw: str) -> Dict[str, Any]:
    """Parse git fetch output to extract sync information."""
    if not raw:
        return {
            "remotes_synced": [],
            "branches_updated": [],
            "branches_pruned": [],
            "raw_output": ""
        }

    remotes_set = set()
    branches_updated = []
    branches_pruned = []

    for line in raw.splitlines():
        line_stripped = line.strip()

        if not line_stripped:
            continue

        if "Fetching" in line_stripped:
            parts = line_stripped.split()
            if len(parts) >= 2:
                remotes_set.add(parts[1])

        if "->" in line_stripped:
            if "[new branch]" in line_stripped:
                parts = line_stripped.split("->")
                if len(parts) == 2:
                    branch_info = parts[1].strip()
                    if "/" in branch_info:
                        remote, branch = branch_info.split("/", 1)
                        branches_updated.append({
                            "remote": remote,
                            "branch": branch,
                            "action": "new"
                        })

            elif "[deleted]" in line_stripped or "x " in line_stripped:
                parts = line_stripped.split("->")
                if len(parts) == 2:
                    branch_info = parts[1].strip()
                    if "/" in branch_info:
                        remote, branch = branch_info.split("/", 1)
                        branches_pruned.append(branch)

            else:
                parts = line_stripped.split("->")
                if len(parts) == 2:
                    branch_info = parts[1].strip()
                    if "/" in branch_info:
                        remote, branch = branch_info.split("/", 1)
                        branches_updated.append({
                            "remote": remote,
                            "branch": branch,
                            "action": "updated"
                        })

    return {
        "remotes_synced": sorted(list(remotes_set)),
        "branches_updated": branches_updated,
        "branches_pruned": branches_pruned,
        "raw_output": raw
    }


def parse_status_output(raw: str) -> Dict[str, Any]:
    """Parse git status --branch output."""
    if not raw:
        return {
            "current_branch": None,
            "tracking": None,
            "ahead": 0,
            "behind": 0,
            "sync_status": "unknown"
        }

    lines = raw.splitlines()

    if not lines:
        return {
            "current_branch": None,
            "tracking": None,
            "ahead": 0,
            "behind": 0,
            "sync_status": "unknown"
        }

    branch_line = lines[0].strip()

    if not branch_line.startswith("##"):
        return {
            "current_branch": None,
            "tracking": None,
            "ahead": 0,
            "behind": 0,
            "sync_status": "unknown"
        }

    branch_info = branch_line[3:].strip()

    current_branch = None
    tracking = None
    ahead = 0
    behind = 0

    if "..." in branch_info:
        parts = branch_info.split("...")
        current_branch = parts[0].strip()

        rest = parts[1].strip()

        if "[" in rest:
            tracking = rest.split("[")[0].strip()
            status_part = rest.split("[")[1].split("]")[0]

            if "ahead" in status_part:
                ahead_str = status_part.split("ahead")[1].strip().split(",")[0].strip()
                ahead = int(ahead_str) if ahead_str.isdigit() else 0

            if "behind" in status_part:
                behind_str = status_part.split("behind")[1].strip().split(",")[0].strip()
                behind = int(behind_str) if behind_str.isdigit() else 0
        else:
            tracking = rest
    else:
        current_branch = branch_info.split()[0] if branch_info else None

    sync_status = "up-to-date"
    if ahead > 0 and behind > 0:
        sync_status = "diverged"
    elif ahead > 0:
        sync_status = "ahead"
    elif behind > 0:
        sync_status = "behind"

    return {
        "current_branch": current_branch,
        "tracking": tracking,
        "ahead": ahead,
        "behind": behind,
        "sync_status": sync_status
    }


async def build_sync_json(
    repo_path: str,
    operation: str,
    raw_output: str,
    status_output: str
) -> Dict[str, Any]:
    """Build final JSON response for sync operation."""
    sync_result = parse_fetch_output(raw_output)
    status_after = parse_status_output(status_output)

    success = True
    remotes_count = len(sync_result["remotes_synced"])
    branches_updated_count = len(sync_result["branches_updated"])
    branches_pruned_count = len(sync_result["branches_pruned"])

    if operation == "fetch":
        message = f"Successfully fetched from {remotes_count} remote(s)"
        if branches_updated_count > 0:
            message += f", {branches_updated_count} branch(es) updated"
        if branches_pruned_count > 0:
            message += f", {branches_pruned_count} branch(es) pruned"
    else:
        message = f"Successfully pulled latest changes"
        if "Already up to date" in raw_output or "Already up-to-date" in raw_output:
            message = "Already up to date with remote"

    return {
        "repo": {"path": repo_path},
        "operation": operation,
        "timestamp": datetime.now().isoformat(),
        "sync_result": sync_result,
        "status_after": status_after,
        "summary": {
            "success": success,
            "remotes_synced": remotes_count,
            "branches_updated": branches_updated_count,
            "branches_pruned": branches_pruned_count,
            "message": message
        }
    }


def register(mcp: FastMCP) -> None:
    """Register repository sync tools with MCP server."""
    @mcp.tool()
    async def sync_repository(
        repo_path: str,
        operation: str = "fetch"
    ) -> Dict[str, Any]:
        """
        Sync the repository with remote server to ensure latest information.

        Args:
            repo_path: Absolute path to git repository
            operation: Type of sync - "fetch" (safe, recommended) or "pull" (updates files)

        Returns sync results including remotes synced, branches updated/pruned, and current
        sync status (ahead/behind remote).

        "fetch" downloads updates without changing files. "pull" updates local files.
        """
        await ensure_is_git_repo(repo_path)

        if operation not in ["fetch", "pull"]:
            raise ValueError(f"Invalid operation '{operation}'. Must be 'fetch' or 'pull'")

        if operation == "fetch":
            raw_output = await sync_repository_fetch(repo_path)
        else:
            raw_output = await sync_repository_pull(repo_path)

        status_output = await get_sync_status(repo_path)

        return await build_sync_json(
            repo_path=repo_path,
            operation=operation,
            raw_output=raw_output,
            status_output=status_output
        )
