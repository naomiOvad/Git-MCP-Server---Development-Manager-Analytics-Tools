"""Pre-configured prompts for common development manager tasks."""


def register_prompts(mcp):
    """Register all prompts with the MCP server."""

    @mcp.prompt()
    def executive_dashboard() -> str:
        """Visual project dashboard with charts and metrics."""
        return """Show project dashboard for last 7 days with visual charts.

Use the repository we're discussing, or ask which repo if unclear.

Include:
- Bar chart showing commits per developer with week-over-week comparison (vs previous 7 days, show percentage change)
- Bar chart showing code churn per developer (additions + deletions)
- Bar chart showing top 5 most changed files
- Summary table: Total commits, lines changed, active developers, files modified

Present the data visually so it's easy to understand at a glance."""

    @mcp.prompt()
    def code_review_priority(days: int = 7, max_files: int = 10) -> str:
        """Files requiring code review attention."""
        return f"""Show top {max_files} files changed most in last {days} days.

Use the repository we're discussing, or ask which repo if unclear.

For each file:
- Modification count
- Total lines changed
- Contributors

Sort by activity (highest first)."""

    @mcp.prompt()
    def developer_spotlight(developer_email: str, days: int = 30) -> str:
        """Individual developer contribution analysis."""
        return f"""Analyze {developer_email} contributions over last {days} days.

Use the repository we're discussing, or ask which repo if unclear.

Include:
- Personal stats: Commits, lines added/deleted, files changed
- Team comparison: vs average developer
- Contributions: Files worked on, what they contributed
- Focus areas: Most active codebase sections
- Trend: Activity change vs previous {days} days"""

    @mcp.prompt()
    def active_branches_status(days: int = 30) -> str:
        """Active branch tracking and status."""
        return f"""Show branches with activity in last {days} days.

Use the repository we're discussing, or ask which repo if unclear.

For each branch:
- Name
- Last commit date
- Contributors
- Commit count

Exclude branches inactive for {days}+ days."""

    @mcp.prompt()
    def quick_daily_sync() -> str:
        """Today's repository activity summary."""
        return """Sync repository and show today's activity.

Use the repository we're discussing, or ask which repo if unclear.

Include:
- Commit count
- Contributors
- Changed files
- Commit messages (brief)"""
