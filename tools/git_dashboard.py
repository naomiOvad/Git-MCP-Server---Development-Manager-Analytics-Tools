import asyncio
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import Counter, defaultdict

from mcp.server.fastmcp import FastMCP
from tools.git_commit_history import get_commit_history_raw, parse_commit_history
from git_runner import ensure_is_git_repo


# Configuration thresholds - adjust these for your company's needs
RISK_HIGH_COMMITS = 15
RISK_MEDIUM_COMMITS = 8
RISK_HIGH_DEVELOPERS = 5
RISK_MEDIUM_DEVELOPERS = 3
LOW_ACTIVITY_PERCENTAGE = 5
LOW_ACTIVITY_COMMITS = 3
HIGH_CHURN_THRESHOLD = 100
STABILITY_THRESHOLD = 0.3


async def collect_dashboard_data(
    repo_path: str,
    since: Optional[str] = None,
    until: Optional[str] = None
) -> Dict[str, Any]:
    """Collect all raw commit data for dashboard analysis."""
    commits_raw = await get_commit_history_raw(
        repo_path=repo_path,
        since=since,
        until=until
    )

    commits = parse_commit_history(commits_raw)

    return {
        "commits": commits,
        "repo_path": repo_path,
        "since": since,
        "until": until
    }


def analyze_executive_summary(commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate high-level statistics for executive summary."""
    if not commits:
        return {
            "total_commits": 0,
            "total_developers": 0,
            "total_files_changed": 0,
            "total_additions": 0,
            "total_deletions": 0,
            "net_lines": 0,
            "avg_commits_per_day": 0
        }

    developers = {c["author_name"] for c in commits}

    all_files = set()
    total_additions = 0
    total_deletions = 0

    for commit in commits:
        for file_info in commit.get("files", []):
            all_files.add(file_info["path"])
            total_additions += file_info.get("additions", 0)
            total_deletions += file_info.get("deletions", 0)

    if commits:
        latest_date = commits[0]["date"]
        earliest_date = commits[-1]["date"]

        try:
            latest = datetime.fromisoformat(latest_date.rsplit(' ', 1)[0])
            earliest = datetime.fromisoformat(earliest_date.rsplit(' ', 1)[0])

            days = max(1, (latest - earliest).days + 1)
            avg_commits_per_day = len(commits) / days
        except:
            avg_commits_per_day = 0
    else:
        avg_commits_per_day = 0

    return {
        "total_commits": len(commits),
        "total_developers": len(developers),
        "total_files_changed": len(all_files),
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "net_lines": total_additions - total_deletions,
        "avg_commits_per_day": round(avg_commits_per_day, 1)
    }


def analyze_team_performance(commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze developer contributions and identify top performers."""
    if not commits:
        return {
            "top_contributors": [],
            "developer_count": 0,
            "active_developers": 0,
            "alerts": []
        }

    dev_stats = defaultdict(lambda: {
        "commits": 0,
        "additions": 0,
        "deletions": 0,
        "files": set()
    })

    for commit in commits:
        dev_name = commit["author_name"]
        dev_stats[dev_name]["commits"] += 1

        for file_info in commit.get("files", []):
            dev_stats[dev_name]["additions"] += file_info.get("additions", 0)
            dev_stats[dev_name]["deletions"] += file_info.get("deletions", 0)
            dev_stats[dev_name]["files"].add(file_info["path"])

    total_commits = len(commits)
    contributors = []

    for dev_name, stats in dev_stats.items():
        activity_score = stats["additions"] + stats["deletions"]
        percentage = round((stats["commits"] / total_commits) * 100, 1) if total_commits > 0 else 0

        contributors.append({
            "developer": dev_name,
            "commits": stats["commits"],
            "percentage": percentage,
            "additions": stats["additions"],
            "deletions": stats["deletions"],
            "files_touched": len(stats["files"]),
            "activity_score": activity_score
        })

    contributors.sort(key=lambda x: x["commits"], reverse=True)
    for i, contrib in enumerate(contributors, 1):
        contrib["rank"] = i

    top_contributors = contributors[:5]
    active_developers = len(dev_stats)

    alerts = []
    for contrib in contributors:
        if contrib["percentage"] < LOW_ACTIVITY_PERCENTAGE and contrib["commits"] < LOW_ACTIVITY_COMMITS:
            alerts.append({
                "type": "low_activity",
                "developer": contrib["developer"],
                "message": f"Only {contrib['commits']} commits - low activity",
                "severity": "warning"
            })

    return {
        "top_contributors": top_contributors,
        "developer_count": len(dev_stats),
        "active_developers": active_developers,
        "alerts": alerts
    }


def analyze_code_health(commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze code health: hotspots, high churn files, file type distribution."""
    if not commits:
        return {
            "hotspots": [],
            "high_churn_files": [],
            "file_types_distribution": {}
        }

    file_stats = defaultdict(lambda: {
        "commits": 0,
        "developers": set(),
        "additions": 0,
        "deletions": 0
    })

    for commit in commits:
        developer = commit["author_name"]

        for file_info in commit.get("files", []):
            path = file_info["path"]
            file_stats[path]["commits"] += 1
            file_stats[path]["developers"].add(developer)
            file_stats[path]["additions"] += file_info.get("additions", 0)
            file_stats[path]["deletions"] += file_info.get("deletions", 0)

    hotspots = []
    for path, stats in file_stats.items():
        churn = stats["additions"] + stats["deletions"]
        developer_count = len(stats["developers"])

        if stats["commits"] > RISK_HIGH_COMMITS or developer_count > RISK_HIGH_DEVELOPERS:
            risk_level = "high"
        elif stats["commits"] > RISK_MEDIUM_COMMITS or developer_count > RISK_MEDIUM_DEVELOPERS:
            risk_level = "medium"
        else:
            risk_level = "low"

        hotspots.append({
            "path": path,
            "commits": stats["commits"],
            "developers": developer_count,
            "additions": stats["additions"],
            "deletions": stats["deletions"],
            "churn": churn,
            "risk_level": risk_level
        })

    hotspots.sort(key=lambda x: x["commits"], reverse=True)
    for i, hotspot in enumerate(hotspots[:10], 1):
        hotspot["rank"] = i

    top_hotspots = hotspots[:10]

    high_churn = []
    for path, stats in file_stats.items():
        churn = stats["additions"] + stats["deletions"]
        net_change = abs(stats["additions"] - stats["deletions"])

        if churn > HIGH_CHURN_THRESHOLD:
            stability_ratio = net_change / churn if churn > 0 else 0
            stability = "stable" if stability_ratio > STABILITY_THRESHOLD else "unstable"

            high_churn.append({
                "path": path,
                "additions": stats["additions"],
                "deletions": stats["deletions"],
                "churn": churn,
                "net_change": stats["additions"] - stats["deletions"],
                "stability": stability
            })

    high_churn.sort(key=lambda x: x["churn"], reverse=True)
    high_churn_files = high_churn[:5]

    file_types = Counter()
    for path in file_stats.keys():
        if '.' in path:
            ext = '.' + path.rsplit('.', 1)[1]
            file_types[ext] += 1
        else:
            file_types["(no extension)"] += 1

    total_files = sum(file_types.values())
    file_types_distribution = {}

    for ext, count in file_types.most_common(10):
        percentage = round((count / total_files) * 100, 1) if total_files > 0 else 0
        file_types_distribution[ext] = {
            "count": count,
            "percentage": percentage
        }

    return {
        "hotspots": top_hotspots,
        "high_churn_files": high_churn_files,
        "file_types_distribution": file_types_distribution
    }


async def build_dashboard_json(
    repo_path: str,
    since: str = "30 days ago",
    until: Optional[str] = None
) -> Dict[str, Any]:
    """Build complete dashboard JSON with all analyses."""
    raw_data = await collect_dashboard_data(repo_path, since, until)
    commits = raw_data["commits"]

    executive_summary = analyze_executive_summary(commits)
    team_performance = analyze_team_performance(commits)
    code_health = analyze_code_health(commits)

    repo_name = os.path.basename(repo_path)

    return {
        "repo": {
            "path": repo_path,
            "name": repo_name
        },
        "period": {
            "since": since,
            "until": until or "now",
            "total_commits_analyzed": len(commits)
        },
        "executive_summary": executive_summary,
        "team_performance": team_performance,
        "code_health": code_health,
        "visualization_hints": {
            "developer_activity": {
                "type": "horizontal_bar",
                "title": "Top Contributors",
                "description": "Show top 5 developers by commit count",
                "data_path": "team_performance.top_contributors",
                "x_field": "commits",
                "y_field": "developer"
            },
            "file_types": {
                "type": "pie_chart",
                "title": "File Types Distribution",
                "description": "Breakdown of file types in changed files",
                "data_path": "code_health.file_types_distribution"
            },
            "hotspots": {
                "type": "table",
                "title": "Code Hotspots",
                "description": "Files with high activity (potential issues)",
                "data_path": "code_health.hotspots",
                "columns": ["rank", "path", "commits", "developers", "risk_level"]
            }
        }
    }


def register(mcp: FastMCP) -> None:
    """Register project dashboard tools with MCP server."""
    @mcp.tool()
    async def get_project_dashboard(
        repo_path: str,
        since: str = "30 days ago",
        until: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive project dashboard with analytics and insights.

        Args:
            repo_path: Absolute path to git repository
            since: Analyze commits since this date (default: "30 days ago")
            until: Analyze commits until this date (default: now)

        Returns complete dashboard with executive summary (commits, developers, lines changed),
        team performance (top contributors, activity alerts), code health (hotspots, churn files,
        file types), and visualization hints for charts.
        """
        await ensure_is_git_repo(repo_path)

        return await build_dashboard_json(
            repo_path=repo_path,
            since=since,
            until=until
        )
