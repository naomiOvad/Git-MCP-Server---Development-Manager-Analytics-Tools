import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.git_developer_stats import analyze_developer_stats, build_developer_stats_json
from tools.git_commit_history import get_commit_history_raw, parse_commit_history


def assert_stats_structure(stats):
    """Verify stats dictionary has all required fields."""
    required_fields = [
        "total_commits",
        "total_files_changed",
        "total_additions",
        "total_deletions",
        "most_active_files",
        "file_types"
    ]
    for field in required_fields:
        assert field in stats

    assert isinstance(stats["total_commits"], int)
    assert isinstance(stats["total_files_changed"], int)
    assert isinstance(stats["total_additions"], int)
    assert isinstance(stats["total_deletions"], int)
    assert isinstance(stats["most_active_files"], list)
    assert isinstance(stats["file_types"], dict)


@pytest.mark.asyncio
async def test_analyze_developer_stats(test_repo):
    """Test that analyze_developer_stats correctly analyzes commit data."""
    raw_output = await get_commit_history_raw(test_repo, max_count=20, since="1 month ago")
    commits = parse_commit_history(raw_output)

    if not commits:
        pytest.skip("No commits available for testing")

    stats = analyze_developer_stats(commits)

    assert isinstance(stats, dict)
    assert_stats_structure(stats)

    assert stats["total_commits"] == len(commits)

    expected_files = sum(c["stats"]["total_files"] for c in commits)
    expected_additions = sum(c["stats"]["total_additions"] for c in commits)
    expected_deletions = sum(c["stats"]["total_deletions"] for c in commits)

    assert stats["total_files_changed"] == expected_files
    assert stats["total_additions"] == expected_additions
    assert stats["total_deletions"] == expected_deletions

    if stats["most_active_files"]:
        for file_info in stats["most_active_files"]:
            assert "path" in file_info
            assert "commits" in file_info
            assert "additions" in file_info
            assert "deletions" in file_info

        for i in range(len(stats["most_active_files"]) - 1):
            assert stats["most_active_files"][i]["commits"] >= stats["most_active_files"][i + 1]["commits"]

        assert len(stats["most_active_files"]) <= 20

    if stats["file_types"]:
        assert len(stats["file_types"]) <= 10


def test_analyze_developer_stats_empty():
    """Test that analyze_developer_stats handles empty input correctly."""
    stats = analyze_developer_stats([])

    assert stats["total_commits"] == 0
    assert stats["total_files_changed"] == 0
    assert stats["total_additions"] == 0
    assert stats["total_deletions"] == 0
    assert stats["most_active_files"] == []
    assert stats["file_types"] == {}


@pytest.mark.asyncio
async def test_build_developer_stats_json(test_repo):
    """Test that build_developer_stats_json creates correct final JSON."""
    raw_all = await get_commit_history_raw(test_repo, max_count=50, since="1 month ago")
    commits_all = parse_commit_history(raw_all)

    if not commits_all:
        pytest.skip("No commits available for testing")

    test_author = commits_all[0]["author_name"]

    raw_output = await get_commit_history_raw(test_repo, author=test_author, since="1 month ago")

    result = build_developer_stats_json(
        repo_path=test_repo,
        author=test_author,
        commits_raw=raw_output,
        since="1 month ago",
        until=None
    )

    assert isinstance(result, dict)

    assert "repo" in result
    assert result["repo"]["path"] == test_repo

    assert "developer" in result
    assert "identifier" in result["developer"]
    assert "matched_as" in result["developer"]

    assert result["developer"]["identifier"] == test_author
    assert isinstance(result["developer"]["matched_as"], list)

    assert "time_range" in result
    assert "since" in result["time_range"]
    assert "until" in result["time_range"]
    assert "actual_range" in result["time_range"]

    assert result["time_range"]["since"] == "1 month ago"
    assert result["time_range"]["until"] is None

    assert "stats" in result
    assert_stats_structure(result["stats"])


@pytest.mark.asyncio
async def test_file_type_analysis(test_repo):
    """Test that file type analysis works correctly."""
    raw_output = await get_commit_history_raw(test_repo, max_count=30)
    commits = parse_commit_history(raw_output)

    if not commits:
        pytest.skip("No commits available for testing")

    stats = analyze_developer_stats(commits)

    if stats["file_types"]:
        for ext, count in stats["file_types"].items():
            assert ext.startswith(".") or ext == "(no extension)"
            assert isinstance(count, int)
            assert count > 0
