import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.git_file_changes import get_file_history_raw, parse_file_history, build_file_history_json

TEST_FILE = "README.md"


@pytest.mark.asyncio
async def test_get_file_history_raw(test_repo):
    """Test that get_file_history_raw returns valid output for a specific file."""
    raw_output = await get_file_history_raw(test_repo, TEST_FILE, max_count=10)

    assert isinstance(raw_output, str)

    if raw_output:
        assert "COMMIT|" in raw_output
        commit_count = raw_output.count("COMMIT|")
        assert commit_count <= 10


@pytest.mark.asyncio
async def test_parse_file_history(test_repo):
    """Test that parse_file_history correctly parses git log output for a file."""
    raw_output = await get_file_history_raw(test_repo, TEST_FILE, max_count=10)

    if not raw_output:
        pytest.skip("File has no history")

    commits = parse_file_history(raw_output, TEST_FILE)

    assert isinstance(commits, list)
    assert len(commits) > 0
    assert len(commits) <= 10

    for commit in commits:
        assert "hash" in commit
        assert "author_name" in commit
        assert "author_email" in commit
        assert "date" in commit
        assert "message" in commit
        assert "changes" in commit

        changes = commit["changes"]
        assert "additions" in changes
        assert "deletions" in changes
        assert "file_path" in changes

        assert isinstance(commit["hash"], str)
        assert isinstance(commit["author_name"], str)
        assert isinstance(commit["author_email"], str)
        assert isinstance(commit["date"], str)
        assert isinstance(commit["message"], str)
        assert isinstance(changes["additions"], int)
        assert isinstance(changes["deletions"], int)
        assert isinstance(changes["file_path"], str)


@pytest.mark.asyncio
async def test_build_file_history_json(test_repo):
    """Test that build_file_history_json creates correct final JSON."""
    raw_output = await get_file_history_raw(test_repo, TEST_FILE, max_count=20)

    if not raw_output:
        pytest.skip("File has no history")

    result = await build_file_history_json(
        repo_path=test_repo,
        file_path=TEST_FILE,
        file_history_raw=raw_output,
        max_count=20
    )

    assert isinstance(result, dict)

    assert "repo" in result
    assert result["repo"]["path"] == test_repo

    assert "file" in result
    assert "path" in result["file"]
    assert "exists" in result["file"]
    assert result["file"]["path"] == TEST_FILE

    assert "time_range" in result

    assert "commits" in result
    assert isinstance(result["commits"], list)
    assert len(result["commits"]) > 0
    assert len(result["commits"]) <= 20

    assert "summary" in result
    summary = result["summary"]

    assert "total_commits" in summary
    assert "total_additions" in summary
    assert "total_deletions" in summary
    assert "unique_authors" in summary
    assert "first_change" in summary
    assert "last_change" in summary

    assert summary["total_commits"] == len(result["commits"])

    expected_additions = sum(c["changes"]["additions"] for c in result["commits"])
    expected_deletions = sum(c["changes"]["deletions"] for c in result["commits"])

    assert summary["total_additions"] == expected_additions
    assert summary["total_deletions"] == expected_deletions


@pytest.mark.asyncio
async def test_specific_file(test_repo):
    """Test with a specific commonly-changed file."""
    test_files = ["CMakeLists.txt", "README.md", "cmake/onnxruntime.cmake"]

    for file_path in test_files:
        raw_output = await get_file_history_raw(test_repo, file_path, max_count=5)

        if not raw_output:
            continue

        commits = parse_file_history(raw_output, file_path)

        assert isinstance(commits, list)
        assert len(commits) <= 5

        if commits:
            assert "author_name" in commits[0]
            assert "date" in commits[0]
            assert "message" in commits[0]
            assert "changes" in commits[0]

            total_additions = sum(c["changes"]["additions"] for c in commits)
            total_deletions = sum(c["changes"]["deletions"] for c in commits)

            assert isinstance(total_additions, int)
            assert isinstance(total_deletions, int)

        break
