import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.git_sync import (
    sync_repository_fetch,
    parse_fetch_output,
    parse_status_output,
    build_sync_json,
    get_sync_status
)


@pytest.mark.asyncio
async def test_sync_repository_fetch(test_repo):
    """Test that sync_repository_fetch runs git fetch successfully."""
    raw_output = await sync_repository_fetch(test_repo)

    assert isinstance(raw_output, str)


@pytest.mark.asyncio
async def test_get_sync_status(test_repo):
    """Test that get_sync_status retrieves branch tracking info."""
    status_output = await get_sync_status(test_repo)

    assert isinstance(status_output, str)

    if status_output:
        assert "##" in status_output


def test_parse_fetch_output_empty():
    """Test that parse_fetch_output handles empty output (already up to date)."""
    result = parse_fetch_output("")

    assert isinstance(result, dict)
    assert result["remotes_synced"] == []
    assert result["branches_updated"] == []
    assert result["branches_pruned"] == []


def test_parse_fetch_output_with_data():
    """Test that parse_fetch_output correctly parses fetch output."""
    sample_output = """Fetching origin
remote: Counting objects: 100, done.
remote: Compressing objects: 100% (50/50), done.
   abc123..def456    main       -> origin/main
 * [new branch]      feature-x  -> origin/feature-x
   ghi789..jkl012    dev        -> origin/dev
"""

    result = parse_fetch_output(sample_output)

    assert isinstance(result, dict)
    assert "remotes_synced" in result
    assert "branches_updated" in result
    assert "branches_pruned" in result

    assert "origin" in result["remotes_synced"]

    for branch_info in result["branches_updated"]:
        assert "remote" in branch_info
        assert "branch" in branch_info
        assert "action" in branch_info


def test_parse_status_output():
    """Test that parse_status_output correctly parses git status output."""
    status_up_to_date = "## main...origin/main"
    result1 = parse_status_output(status_up_to_date)

    assert result1["current_branch"] == "main"
    assert result1["tracking"] == "origin/main"
    assert result1["ahead"] == 0
    assert result1["behind"] == 0
    assert result1["sync_status"] == "up-to-date"

    status_behind = "## main...origin/main [behind 5]"
    result2 = parse_status_output(status_behind)

    assert result2["current_branch"] == "main"
    assert result2["behind"] == 5
    assert result2["sync_status"] == "behind"

    status_ahead = "## main...origin/main [ahead 3]"
    result3 = parse_status_output(status_ahead)

    assert result3["current_branch"] == "main"
    assert result3["ahead"] == 3
    assert result3["sync_status"] == "ahead"

    status_diverged = "## main...origin/main [ahead 2, behind 1]"
    result4 = parse_status_output(status_diverged)

    assert result4["current_branch"] == "main"
    assert result4["ahead"] == 2
    assert result4["behind"] == 1
    assert result4["sync_status"] == "diverged"


@pytest.mark.asyncio
async def test_build_sync_json(test_repo):
    """Test that build_sync_json creates correct final JSON."""
    sample_fetch = """Fetching origin
   abc123..def456    main       -> origin/main
"""
    sample_status = "## main...origin/main"

    result = await build_sync_json(
        repo_path=test_repo,
        operation="fetch",
        raw_output=sample_fetch,
        status_output=sample_status
    )

    assert isinstance(result, dict)

    assert "repo" in result
    assert result["repo"]["path"] == test_repo

    assert "operation" in result
    assert result["operation"] == "fetch"

    assert "timestamp" in result

    assert "sync_result" in result
    sync_result = result["sync_result"]

    assert "remotes_synced" in sync_result
    assert "branches_updated" in sync_result
    assert "branches_pruned" in sync_result

    assert "status_after" in result
    status_after = result["status_after"]

    assert "current_branch" in status_after
    assert "sync_status" in status_after

    assert "summary" in result
    summary = result["summary"]

    assert "success" in summary
    assert "remotes_synced" in summary
    assert "branches_updated" in summary
    assert "branches_pruned" in summary
    assert "message" in summary


@pytest.mark.asyncio
async def test_real_sync_operation(test_repo):
    """Test the complete sync operation with real repository."""
    raw_output = await sync_repository_fetch(test_repo)
    status_output = await get_sync_status(test_repo)

    result = await build_sync_json(
        repo_path=test_repo,
        operation="fetch",
        raw_output=raw_output,
        status_output=status_output
    )

    assert isinstance(result, dict)

    assert "operation" in result
    assert "timestamp" in result
    assert "status_after" in result
    assert "summary" in result

    assert isinstance(result["status_after"]["current_branch"], (str, type(None)))
    assert isinstance(result["status_after"]["ahead"], int)
    assert isinstance(result["status_after"]["behind"], int)
