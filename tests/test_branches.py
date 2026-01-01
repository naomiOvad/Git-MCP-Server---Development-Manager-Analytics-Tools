import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.git_branches import get_branches_raw, parse_branches, build_branch_list_json


@pytest.mark.asyncio
async def test_get_branches_raw(test_repo):
    """Test that get_branches_raw returns valid git branch output."""
    raw_output = await get_branches_raw(test_repo)

    assert isinstance(raw_output, str)
    assert len(raw_output) > 0

    lines = raw_output.strip().split("\n")
    assert len(lines) > 0

    for line in lines:
        assert "|" in line
        parts = line.split("|")
        assert len(parts) == 2
        assert len(parts[0]) > 0
        assert len(parts[1]) > 0


@pytest.mark.asyncio
async def test_parse_branches(test_repo):
    """Test that parse_branches correctly parses git branch output."""
    raw_output = await get_branches_raw(test_repo)
    branches = parse_branches(raw_output)

    assert isinstance(branches, list)
    assert len(branches) > 0

    for branch in branches:
        assert isinstance(branch, dict)
        assert "name" in branch
        assert "last_commit_date" in branch
        assert isinstance(branch["name"], str)
        assert len(branch["name"]) > 0


@pytest.mark.asyncio
async def test_build_branch_list_json(test_repo):
    """Test that build_branch_list_json creates correct final JSON."""
    raw_output = await get_branches_raw(test_repo)
    result = build_branch_list_json(test_repo, raw_output)

    assert isinstance(result, dict)

    assert "repo" in result
    assert isinstance(result["repo"], dict)
    assert result["repo"]["path"] == test_repo

    assert "branches" in result
    assert isinstance(result["branches"], list)
    assert len(result["branches"]) > 0

    assert "total_branches" in result
    assert isinstance(result["total_branches"], int)
    assert result["total_branches"] == len(result["branches"])

    first_branch = result["branches"][0]
    assert "name" in first_branch
    assert "last_commit_date" in first_branch
