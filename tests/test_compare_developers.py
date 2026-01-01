import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.git_compare_developers import compare_developers, build_comparison_json
from tools.git_commit_history import get_commit_history_raw, parse_commit_history


def test_compare_developers_function():
    """Test that compare_developers correctly compares developer statistics."""
    developer_stats = [
        {
            "developer": "Erik",
            "stats": {
                "total_commits": 45,
                "total_files_changed": 120,
                "total_additions": 2500,
                "total_deletions": 800
            }
        },
        {
            "developer": "John",
            "stats": {
                "total_commits": 30,
                "total_files_changed": 150,
                "total_additions": 1800,
                "total_deletions": 1200
            }
        },
        {
            "developer": "Jane",
            "stats": {
                "total_commits": 38,
                "total_files_changed": 95,
                "total_additions": 2100,
                "total_deletions": 600
            }
        }
    ]

    comparison = compare_developers(developer_stats)

    assert isinstance(comparison, dict)

    assert "rankings" in comparison
    rankings = comparison["rankings"]

    assert "most_commits" in rankings
    assert "most_files_changed" in rankings
    assert "most_additions" in rankings
    assert "most_deletions" in rankings
    assert "most_active" in rankings

    assert rankings["most_commits"]["developer"] == "Erik"
    assert rankings["most_commits"]["value"] == 45

    assert rankings["most_files_changed"]["developer"] == "John"
    assert rankings["most_files_changed"]["value"] == 150

    assert rankings["most_additions"]["developer"] == "Erik"
    assert rankings["most_additions"]["value"] == 2500

    assert rankings["most_deletions"]["developer"] == "John"
    assert rankings["most_deletions"]["value"] == 1200

    assert rankings["most_active"]["developer"] == "Erik"
    assert rankings["most_active"]["value"] == 3300

    assert "totals" in comparison
    totals = comparison["totals"]

    assert totals["total_commits"] == 113
    assert totals["total_files_changed"] == 365
    assert totals["total_additions"] == 6400
    assert totals["total_deletions"] == 2600


def test_compare_developers_empty():
    """Test that compare_developers handles empty input correctly."""
    comparison = compare_developers([])

    assert comparison["rankings"]["most_commits"] is None
    assert comparison["rankings"]["most_files_changed"] is None
    assert comparison["rankings"]["most_additions"] is None
    assert comparison["rankings"]["most_deletions"] is None
    assert comparison["rankings"]["most_active"] is None

    assert comparison["totals"]["total_commits"] == 0
    assert comparison["totals"]["total_files_changed"] == 0
    assert comparison["totals"]["total_additions"] == 0
    assert comparison["totals"]["total_deletions"] == 0


@pytest.mark.asyncio
async def test_build_comparison_json(test_repo):
    """Test that build_comparison_json creates correct final JSON with real data."""
    raw_all = await get_commit_history_raw(test_repo, max_count=100, since="1 month ago")
    commits_all = parse_commit_history(raw_all)

    if not commits_all:
        pytest.skip("No commits available for testing")

    authors_set = {c["author_name"] for c in commits_all}
    authors_list = list(authors_set)

    if len(authors_list) < 2:
        pytest.skip("Need at least 2 developers for comparison")

    test_authors = authors_list[:min(3, len(authors_list))]

    result = await build_comparison_json(
        repo_path=test_repo,
        authors=test_authors,
        since="1 month ago",
        until=None
    )

    assert isinstance(result, dict)

    assert "repo" in result
    assert result["repo"]["path"] == test_repo

    assert "time_range" in result
    assert result["time_range"]["since"] == "1 month ago"
    assert result["time_range"]["until"] is None

    assert "developers" in result
    assert isinstance(result["developers"], list)
    assert len(result["developers"]) == len(test_authors)

    for dev_stat in result["developers"]:
        assert "developer" in dev_stat
        assert "stats" in dev_stat

        stats = dev_stat["stats"]
        assert "total_commits" in stats
        assert "total_files_changed" in stats
        assert "total_additions" in stats
        assert "total_deletions" in stats

    assert "comparison" in result
    comparison = result["comparison"]

    assert "rankings" in comparison
    assert "totals" in comparison

    totals = comparison["totals"]
    expected_commits = sum(d["stats"]["total_commits"] for d in result["developers"])
    expected_files = sum(d["stats"]["total_files_changed"] for d in result["developers"])
    expected_additions = sum(d["stats"]["total_additions"] for d in result["developers"])
    expected_deletions = sum(d["stats"]["total_deletions"] for d in result["developers"])

    assert totals["total_commits"] == expected_commits
    assert totals["total_files_changed"] == expected_files
    assert totals["total_additions"] == expected_additions
    assert totals["total_deletions"] == expected_deletions


@pytest.mark.asyncio
async def test_compare_two_specific_developers(test_repo):
    """Test comparing two specific developers by name."""
    test_authors = ["Erik", "snnn"]

    result = await build_comparison_json(
        repo_path=test_repo,
        authors=test_authors,
        since="2 months ago"
    )

    assert isinstance(result, dict)

    assert "developers" in result
    assert len(result["developers"]) == len(test_authors)

    for dev_stat in result["developers"]:
        assert "developer" in dev_stat
        assert "stats" in dev_stat

        stats = dev_stat["stats"]
        assert isinstance(stats["total_commits"], int)
        assert isinstance(stats["total_files_changed"], int)
        assert isinstance(stats["total_additions"], int)
        assert isinstance(stats["total_deletions"], int)

    assert "comparison" in result
    assert "rankings" in result["comparison"]
    assert "totals" in result["comparison"]
