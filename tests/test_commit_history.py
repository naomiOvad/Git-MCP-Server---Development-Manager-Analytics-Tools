import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.git_commit_history import get_commit_history_raw, parse_commit_history, build_commit_history_json


@pytest.mark.asyncio
async def test_get_commit_history_raw(test_repo):
    """Test that get_commit_history_raw returns valid git log output."""
    raw_output = await get_commit_history_raw(test_repo, max_count=5)

    assert isinstance(raw_output, str)
    assert len(raw_output) > 0
    assert "COMMIT|" in raw_output

    commit_count = raw_output.count("COMMIT|")
    assert commit_count <= 5
    assert commit_count > 0


@pytest.mark.asyncio
async def test_parse_commit_history(test_repo):
    """Test that parse_commit_history correctly parses git log output."""
    raw_output = await get_commit_history_raw(test_repo, max_count=5)
    commits = parse_commit_history(raw_output)

    assert isinstance(commits, list)
    assert len(commits) > 0
    assert len(commits) <= 5

    for commit in commits:
        assert isinstance(commit, dict)
        assert "hash" in commit
        assert "author_name" in commit
        assert "author_email" in commit
        assert "date" in commit
        assert "message" in commit
        assert "files" in commit
        assert "stats" in commit

        assert isinstance(commit["hash"], str)
        assert isinstance(commit["author_name"], str)
        assert isinstance(commit["author_email"], str)
        assert isinstance(commit["date"], str)
        assert isinstance(commit["message"], str)
        assert isinstance(commit["files"], list)
        assert isinstance(commit["stats"], dict)

        assert len(commit["hash"]) > 0
        assert len(commit["author_name"]) > 0
        assert len(commit["message"]) > 0

        for file in commit["files"]:
            assert "path" in file
            assert "additions" in file
            assert "deletions" in file

        assert "total_files" in commit["stats"]
        assert "total_additions" in commit["stats"]
        assert "total_deletions" in commit["stats"]
        assert commit["stats"]["total_files"] == len(commit["files"])


@pytest.mark.asyncio
async def test_parse_with_filters(test_repo):
    """Test that filters work correctly."""
    raw = await get_commit_history_raw(test_repo, since="1 week ago", max_count=10)
    commits = parse_commit_history(raw)
    assert len(commits) <= 10

    raw = await get_commit_history_raw(test_repo, max_count=3)
    commits = parse_commit_history(raw)
    assert len(commits) <= 3

    raw = await get_commit_history_raw(test_repo, branch="main", max_count=5)
    commits = parse_commit_history(raw)
    assert len(commits) <= 5


@pytest.mark.asyncio
async def test_build_commit_history_json(test_repo):
    """Test that build_commit_history_json creates correct final JSON."""
    raw_output = await get_commit_history_raw(test_repo, max_count=10, since="1 week ago")
    result = build_commit_history_json(
        repo_path=test_repo,
        commits_raw=raw_output,
        max_count=10,
        since="1 week ago"
    )

    assert isinstance(result, dict)

    assert "repo" in result
    assert result["repo"]["path"] == test_repo

    assert "filters" in result
    assert result["filters"]["max_count"] == 10
    assert result["filters"]["since"] == "1 week ago"

    assert "commits" in result
    assert isinstance(result["commits"], list)
    assert len(result["commits"]) <= 10

    assert "summary" in result
    summary = result["summary"]

    assert "total_commits" in summary
    assert "total_files_changed" in summary
    assert "total_additions" in summary
    assert "total_deletions" in summary
    assert "authors" in summary
    assert "date_range" in summary

    assert summary["total_commits"] == len(result["commits"])

    expected_files = sum(c["stats"]["total_files"] for c in result["commits"])
    expected_additions = sum(c["stats"]["total_additions"] for c in result["commits"])
    expected_deletions = sum(c["stats"]["total_deletions"] for c in result["commits"])

    assert summary["total_files_changed"] == expected_files
    assert summary["total_additions"] == expected_additions
    assert summary["total_deletions"] == expected_deletions
